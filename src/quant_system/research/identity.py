"""Canonical research-dataset identity without a controller dependency."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from dataclasses import field
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from quant_system.data.source_identity import (
    SourceIdentity,
    capture_file_bytes,
    capture_file_digest,
    require_aware_utc,
    require_provider_qualified_source,
    require_trusted_source,
)
from quant_system.research.splits import (
    SplitManifest,
    load_split_manifest,
    serialize_split_manifest,
)


_SHA256 = re.compile(r"[0-9a-f]{64}")
_DATASET_MANIFEST_TOKEN = object()
_CAPTURED_SEMANTICS_TOKEN = object()
_VERIFIED_SPLIT_TOKEN = object()
_TRANSFORMATION_TOKEN = object()


@dataclass(frozen=True)
class TransformationReceipt:
    raw_sources: tuple[SourceIdentity, ...]
    program_sha256: str
    feature_program_sha256: str
    label_program_sha256: str
    config_sha256: str
    schema: tuple[tuple[str, str], ...]
    field_contracts: tuple[tuple[str, str, str, str], ...]
    row_count: int
    output_partition_sha256: str
    feature_artifact_sha256: str
    label_artifact_sha256: str
    row_pit_enforced: bool
    dataset_as_of: datetime
    executed_at: datetime
    runtime_identity_sha256: str
    receipt_sha256: str
    _program_path: Path = field(repr=False, compare=False)
    _feature_program_path: Path = field(repr=False, compare=False)
    _label_program_path: Path = field(repr=False, compare=False)
    _config_path: Path = field(repr=False, compare=False)
    _raw_paths: tuple[Path, ...] = field(repr=False, compare=False)
    _output_path: Path = field(repr=False, compare=False)
    _token: object | None = field(default=None, repr=False, compare=False)

    @property
    def is_authoritative(self) -> bool:
        return bool(self.raw_sources) and all(
            source.is_provider_qualified_capture for source in self.raw_sources
        )

    def verify(self) -> None:
        if self._token is not _TRANSFORMATION_TOKEN:
            raise ValueError("TransformationReceipt must come from execute_transformation")
        if len(self.raw_sources) != len(self._raw_paths) or not self.raw_sources:
            raise ValueError("transformation raw source coverage is incomplete")
        for source, path in zip(self.raw_sources, self._raw_paths, strict=True):
            require_trusted_source(source)
            if (
                capture_file_digest(path)[0] != source.content_sha256
                or source.available_at > self.dataset_as_of
            ):
                raise ValueError("transformation raw source bytes or PIT time changed")
        if capture_file_digest(self._program_path)[0] != self.program_sha256:
            raise ValueError("transformation program bytes changed")
        if (
            capture_file_digest(self._feature_program_path)[0]
            != self.feature_program_sha256
            or capture_file_digest(self._label_program_path)[0]
            != self.label_program_sha256
        ):
            raise ValueError("feature or label program bytes changed")
        if capture_file_digest(self._config_path)[0] != self.config_sha256:
            raise ValueError("transformation config bytes changed")
        if capture_file_digest(self._output_path)[0] != self.output_partition_sha256:
            raise ValueError("transformation output partition bytes changed")
        if self.runtime_identity_sha256 != _pure_runtime_identity():
            raise ValueError("transformation runtime identity changed")
        with tempfile.TemporaryDirectory(prefix="quant-transform-verify-") as directory:
            replay = Path(directory) / "partition.jsonl"
            feature_bytes, label_bytes, partition_bytes = (
                _run_pure_transformation_artifacts(
                    self._program_path,
                    self._feature_program_path,
                    self._label_program_path,
                    self._config_path,
                    self._raw_paths,
                )
            )
            replay.write_bytes(partition_bytes)
            row_count = _validate_partition(
                replay,
                self.field_contracts,
                self.dataset_as_of,
            )
            if (
                row_count != self.row_count
                or capture_file_digest(replay)[0] != self.output_partition_sha256
                or hashlib.sha256(feature_bytes).hexdigest()
                != self.feature_artifact_sha256
                or hashlib.sha256(label_bytes).hexdigest()
                != self.label_artifact_sha256
            ):
                raise ValueError("transformation replay does not reproduce the partition")
        payload = _transformation_payload(self)
        if hashlib.sha256(payload).hexdigest() != self.receipt_sha256:
            raise ValueError("transformation receipt hash mismatch")


def _transformation_payload(receipt: TransformationReceipt) -> bytes:
    return json.dumps(
        {
            "config_sha256": receipt.config_sha256,
            "dataset_as_of": receipt.dataset_as_of.isoformat(),
            "executed_at": receipt.executed_at.isoformat(),
            "output_partition_sha256": receipt.output_partition_sha256,
            "feature_artifact_sha256": receipt.feature_artifact_sha256,
            "label_artifact_sha256": receipt.label_artifact_sha256,
            "row_pit_enforced": receipt.row_pit_enforced,
            "program_sha256": receipt.program_sha256,
            "feature_program_sha256": receipt.feature_program_sha256,
            "label_program_sha256": receipt.label_program_sha256,
            "raw_source_receipt_sha256s": tuple(
                source.capture_receipt_sha256 for source in receipt.raw_sources
            ),
            "row_count": receipt.row_count,
            "runtime_identity_sha256": receipt.runtime_identity_sha256,
            "schema": receipt.schema,
            "field_contracts": receipt.field_contracts,
            "version": 1,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def _pure_runtime_identity() -> str:
    payload = {
        "engine_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "implementation": sys.implementation.name,
        "interpreter_cache_tag": sys.implementation.cache_tag,
        "python_version": tuple(sys.version_info[:3]),
        "version": 1,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _pure_step_bytes(spec_bytes: bytes, inputs: tuple[bytes, ...]) -> bytes:
    try:
        spec = json.loads(spec_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("pure transformation spec must be valid JSON") from exc
    if (
        type(spec) is not dict
        or spec.get("version") != 1
        or spec.get("operation")
        not in {
            "identity_bytes",
            "json_array_to_canonical_jsonl",
            "csv_to_canonical_jsonl",
            "join_jsonl",
        }
    ):
        raise ValueError("unsupported controlled pure transformation operation")
    if spec["operation"] == "identity_bytes":
        if set(spec) != {"operation", "version"}:
            raise ValueError("identity transformation spec has unexpected fields")
        return b"".join(inputs)
    if spec["operation"] == "join_jsonl":
        if (
            set(spec) != {"keys", "operation", "version"}
            or type(spec["keys"]) is not list
            or len(inputs) != 2
        ):
            raise ValueError("controlled join spec is invalid")
        keys = tuple(str(key) for key in spec["keys"])

        def indexed(payload: bytes) -> dict[tuple[object, ...], dict[str, object]]:
            rows = {}
            for line in payload.splitlines():
                try:
                    row = json.loads(line)
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise ValueError("join input must be canonical JSONL") from exc
                if type(row) is not dict:
                    raise ValueError("join input rows must be objects")
                key = tuple(row[name] for name in keys)
                if key in rows:
                    raise ValueError("join input keys must be unique")
                rows[key] = row
            return rows

        left, right = (indexed(payload) for payload in inputs)
        if set(left) != set(right):
            raise ValueError("feature and label artifacts have different join keys")
        joined = []
        for key in sorted(left):
            overlap = (set(left[key]) & set(right[key])) - set(keys)
            if overlap:
                raise ValueError("feature and label artifacts overlap outside join keys")
            joined.append({**left[key], **right[key]})
        return b"".join(
            json.dumps(row, sort_keys=True, separators=(",", ":")).encode() + b"\n"
            for row in joined
        )
    if spec["operation"] == "csv_to_canonical_jsonl":
        if set(spec) != {
            "constant_fields",
            "drop_missing_numeric",
            "numeric_fields",
            "operation",
            "output_fields",
            "rename",
            "sort_keys",
            "version",
        } or len(inputs) != 1:
            raise ValueError("CSV transformation spec is invalid")
        try:
            decoded_csv = inputs[0].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("CSV transformation input must be UTF-8") from exc
        rename = spec["rename"]
        constants = spec["constant_fields"]
        numeric_fields = set(spec["numeric_fields"])
        if (
            type(rename) is not dict
            or type(constants) is not dict
            or type(spec["sort_keys"]) is not list
            or type(spec["numeric_fields"]) is not list
            or type(spec["output_fields"]) is not list
            or type(spec["drop_missing_numeric"]) is not bool
        ):
            raise ValueError("CSV transformation mappings are invalid")
        rows = []
        for source_row in csv.DictReader(io.StringIO(decoded_csv)):
            if spec["drop_missing_numeric"] and any(
                source_row.get(name) in {"", ".", None}
                for name in numeric_fields
            ):
                continue
            row = {
                str(rename.get(name, name)): (
                    float(value) if name in numeric_fields else value
                )
                for name, value in source_row.items()
                if str(rename.get(name, name)) in set(spec["output_fields"])
            }
            row.update(
                {
                    name: value
                    for name, value in constants.items()
                    if name in set(spec["output_fields"])
                }
            )
            rows.append(row)
        sort_keys = tuple(str(rename.get(name, name)) for name in spec["sort_keys"])
        rows.sort(key=lambda row: tuple(row[name] for name in sort_keys))
        return b"".join(
            json.dumps(row, sort_keys=True, separators=(",", ":")).encode() + b"\n"
            for row in rows
        )
    if (
        set(spec)
        != {
            "operation",
            "output_fields",
            "sort_keys",
            "version",
        }
        or type(spec["sort_keys"]) is not list
        or type(spec["output_fields"]) is not list
    ):
        raise ValueError("JSON transformation spec is invalid")
    rows = []
    for payload in inputs:
        try:
            decoded = json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("pure transformation input must be JSON") from exc
        if type(decoded) is not list or any(type(row) is not dict for row in decoded):
            raise ValueError("JSON transformation input must be an array of objects")
        output_fields = tuple(str(name) for name in spec["output_fields"])
        rows.extend(
            {name: row[name] for name in output_fields}
            for row in decoded
        )
    sort_keys = tuple(str(name) for name in spec["sort_keys"])
    try:
        rows.sort(key=lambda row: tuple(row[name] for name in sort_keys))
    except KeyError as exc:
        raise ValueError("pure transformation sort key is absent") from exc
    return b"".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        for row in rows
    )


def replay_pure_transformation_bytes(
    *,
    program_bytes: bytes,
    feature_program_bytes: bytes,
    label_program_bytes: bytes,
    config_bytes: bytes,
    raw_bytes: tuple[bytes, ...],
) -> bytes:
    """Recompute the controlled pure transform without filesystem capabilities."""

    return replay_pure_transformation_artifacts_bytes(
        program_bytes=program_bytes,
        feature_program_bytes=feature_program_bytes,
        label_program_bytes=label_program_bytes,
        config_bytes=config_bytes,
        raw_bytes=raw_bytes,
    )[2]


def replay_pure_transformation_artifacts_bytes(
    *,
    program_bytes: bytes,
    feature_program_bytes: bytes,
    label_program_bytes: bytes,
    config_bytes: bytes,
    raw_bytes: tuple[bytes, ...],
) -> tuple[bytes, bytes, bytes]:
    try:
        config = json.loads(config_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("pure transformation config must be valid JSON") from exc
    if type(config) is not dict:
        raise ValueError("pure transformation config must be an object")
    features = _pure_step_bytes(feature_program_bytes, raw_bytes)
    labels = _pure_step_bytes(label_program_bytes, raw_bytes)
    partition = _pure_step_bytes(program_bytes, (features, labels))
    return features, labels, partition


def _run_pure_transformation(
    program_path: Path,
    feature_program_path: Path,
    label_program_path: Path,
    config_path: Path,
    raw_paths: tuple[Path, ...],
) -> bytes:
    return _run_pure_transformation_artifacts(
        program_path,
        feature_program_path,
        label_program_path,
        config_path,
        raw_paths,
    )[2]


def _run_pure_transformation_artifacts(
    program_path: Path,
    feature_program_path: Path,
    label_program_path: Path,
    config_path: Path,
    raw_paths: tuple[Path, ...],
) -> tuple[bytes, bytes, bytes]:
    return replay_pure_transformation_artifacts_bytes(
        program_bytes=capture_file_bytes(program_path),
        feature_program_bytes=capture_file_bytes(feature_program_path),
        label_program_bytes=capture_file_bytes(label_program_path),
        config_bytes=capture_file_bytes(config_path),
        raw_bytes=tuple(
            capture_file_bytes(path, max_bytes=64 * 1024 * 1024)
            for path in raw_paths
        ),
    )


def _validate_partition(
    path: Path,
    field_contracts: tuple[tuple[str, str, str, str], ...],
    dataset_as_of: datetime,
) -> int:
    expected = {name for name, _, _, _ in field_contracts}
    rows = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError("transformation output must be JSON Lines") from exc
        if type(row) is not dict or set(row) != expected:
            raise ValueError("transformation output does not match the declared schema")
        for name, data_type, unit, timezone_name in field_contracts:
            value = row[name]
            _validate_field_value(
                name,
                value,
                data_type,
                unit,
                timezone_name,
            )
            if name.endswith("available_at"):
                observed = require_aware_utc(
                    datetime.fromisoformat(str(value)),
                    name,
                )
                if observed > dataset_as_of:
                    raise ValueError("transformation output contains post-as-of evidence")
        feature_availability_fields = tuple(
            name for name in expected if name.endswith("feature_available_at")
        )
        reference_name = (
            "decision_at"
            if "decision_at" in row
            else "observed_at"
            if "observed_at" in row
            else None
        )
        if feature_availability_fields and reference_name is None:
            raise ValueError(
                "feature availability requires observed_at or decision_at per row"
            )
        if reference_name is not None:
            reference = require_aware_utc(
                datetime.fromisoformat(str(row[reference_name])),
                reference_name,
            )
            for name in feature_availability_fields:
                available = require_aware_utc(
                    datetime.fromisoformat(str(row[name])),
                    name,
                )
                if available > reference:
                    raise ValueError(
                        "feature evidence is unavailable at the row decision time"
                    )
        rows += 1
    if rows < 1:
        raise ValueError("transformation output partition must not be empty")
    return rows


def _row_pit_enforced(
    field_contracts: tuple[tuple[str, str, str, str], ...],
) -> bool:
    names = {name for name, _, _, _ in field_contracts}
    return any(name.endswith("feature_available_at") for name in names) and bool(
        {"observed_at", "decision_at"} & names
    )


def _validate_field_value(
    name: str,
    value: object,
    data_type: str,
    unit: str,
    timezone_name: str,
) -> None:
    if not unit or not timezone_name:
        raise ValueError("schema fields require explicit unit and timezone contracts")
    normalized_type = data_type.upper()
    if normalized_type in {"DOUBLE", "FLOAT", "REAL"}:
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
        ):
            raise ValueError(f"{name} violates its numeric schema")
    elif normalized_type in {"INTEGER", "BIGINT"}:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{name} violates its integer schema")
    elif normalized_type in {"VARCHAR", "TEXT"}:
        if not isinstance(value, str):
            raise ValueError(f"{name} violates its text schema")
    elif normalized_type in {"TIMESTAMP", "TIMESTAMPTZ"}:
        try:
            parsed = datetime.fromisoformat(str(value))
        except ValueError as exc:
            raise ValueError(f"{name} violates its timestamp schema") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError(f"{name} timestamp must carry an explicit timezone")
        try:
            ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"{name} timezone contract is not an IANA zone") from exc
    elif normalized_type == "DATE":
        try:
            date.fromisoformat(str(value))
        except ValueError as exc:
            raise ValueError(f"{name} violates its date schema") from exc
        if timezone_name != "NA":
            raise ValueError(f"{name} DATE timezone contract must be NA")
    elif normalized_type == "BOOLEAN":
        if type(value) is not bool:
            raise ValueError(f"{name} violates its boolean schema")
    else:
        raise ValueError(f"{name} uses an unsupported schema data type")


def execute_transformation(
    *,
    raw_paths: Sequence[Path],
    raw_sources: Sequence[SourceIdentity],
    program_path: Path,
    feature_program_path: Path,
    label_program_path: Path,
    config_path: Path,
    output_path: Path,
    schema: Sequence[tuple[str, str]],
    field_metadata: Sequence[tuple[str, str, str]],
    dataset_as_of: datetime,
    executed_at: datetime,
) -> TransformationReceipt:
    """Execute one frozen program and retain a replayable lineage receipt."""

    frozen_raw_paths = tuple(raw_paths)
    frozen_sources = tuple(raw_sources)
    frozen_schema = tuple(schema)
    frozen_metadata = tuple(field_metadata)
    metadata_by_name = {
        name: (unit, timezone_name)
        for name, unit, timezone_name in frozen_metadata
    }
    if (
        len(metadata_by_name) != len(frozen_metadata)
        or set(metadata_by_name) != {name for name, _ in frozen_schema}
    ):
        raise ValueError("field metadata must cover every schema field exactly once")
    field_contracts = tuple(
        (name, data_type, *metadata_by_name[name])
        for name, data_type in frozen_schema
    )
    as_of = require_aware_utc(dataset_as_of, "dataset_as_of")
    executed = require_aware_utc(executed_at, "executed_at")
    if output_path.exists():
        raise ValueError("transformation output path must not already exist")
    if len(frozen_raw_paths) != len(frozen_sources) or not frozen_sources:
        raise ValueError("raw paths and source receipts must have one nonempty length")
    for path, source in zip(frozen_raw_paths, frozen_sources, strict=True):
        require_trusted_source(source)
        if capture_file_digest(path)[0] != source.content_sha256:
            raise ValueError("raw source receipt does not bind its bytes")
        if source.available_at > as_of:
            raise ValueError("raw source was unavailable at dataset_as_of")
    program_sha = capture_file_digest(program_path)[0]
    feature_program_sha = capture_file_digest(feature_program_path)[0]
    label_program_sha = capture_file_digest(label_program_path)[0]
    config_sha = capture_file_digest(config_path)[0]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="quant-transform-",
        dir=output_path.parent,
    ) as directory:
        generated = Path(directory) / "partition.jsonl"
        feature_bytes, label_bytes, partition_bytes = (
            _run_pure_transformation_artifacts(
                program_path,
                feature_program_path,
                label_program_path,
                config_path,
                frozen_raw_paths,
            )
        )
        generated.write_bytes(partition_bytes)
        row_count = _validate_partition(generated, field_contracts, as_of)
        output_sha = capture_file_digest(generated)[0]
        os.replace(generated, output_path)
    values = {
        "raw_sources": frozen_sources,
        "program_sha256": program_sha,
        "feature_program_sha256": feature_program_sha,
        "label_program_sha256": label_program_sha,
        "config_sha256": config_sha,
        "schema": frozen_schema,
        "field_contracts": field_contracts,
        "row_count": row_count,
        "output_partition_sha256": output_sha,
        "feature_artifact_sha256": hashlib.sha256(feature_bytes).hexdigest(),
        "label_artifact_sha256": hashlib.sha256(label_bytes).hexdigest(),
        "row_pit_enforced": _row_pit_enforced(field_contracts),
        "dataset_as_of": as_of,
        "executed_at": executed,
        "runtime_identity_sha256": _pure_runtime_identity(),
        "_program_path": program_path,
        "_feature_program_path": feature_program_path,
        "_label_program_path": label_program_path,
        "_config_path": config_path,
        "_raw_paths": frozen_raw_paths,
        "_output_path": output_path,
    }
    provisional = object.__new__(TransformationReceipt)
    for name, value in values.items():
        object.__setattr__(provisional, name, value)
    receipt = TransformationReceipt(
        **values,
        receipt_sha256=hashlib.sha256(
            _transformation_payload(provisional)
        ).hexdigest(),
        _token=_TRANSFORMATION_TOKEN,
    )
    receipt.verify()
    return receipt


@dataclass(frozen=True)
class DatasetManifest:
    dates: tuple[date | datetime, ...]
    frequency: str
    schema: tuple[tuple[str, str], ...]
    source_snapshot_sha256s: tuple[str, ...]
    universe_snapshot_sha256: str
    feature_code_sha256: str
    label_code_sha256: str
    split_manifest_sha256: str
    calendar_policy_sha256: str
    action_policy_sha256: str
    cost_policy_sha256: str
    partition_sha256s: tuple[str, ...]
    identity_sha256: str
    dataset_as_of: datetime | None = None
    partition_sources: tuple[SourceIdentity, ...] = ()
    partition_parser_sha256s: tuple[str, ...] = ()
    schema_sha256: str | None = None
    transformation_receipts: tuple[TransformationReceipt, ...] = ()
    _token: object | None = field(default=None, repr=False, compare=False, hash=False)
    _semantic_paths: tuple[tuple[str, Path], ...] = field(
        default=(),
        repr=False,
        compare=False,
        hash=False,
    )
    _partition_paths: tuple[Path, ...] = field(
        default=(),
        repr=False,
        compare=False,
        hash=False,
    )
    _partition_parser_paths: tuple[Path, ...] = field(
        default=(),
        repr=False,
        compare=False,
        hash=False,
    )
    _captured_semantics_token: object | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    _split_manifest_path: Path | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    _verified_split_token: object | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if self._token is not _DATASET_MANIFEST_TOKEN:
            raise ValueError("DatasetManifest must be created by build_dataset_manifest")
        if self._captured_semantics_token not in {None, _CAPTURED_SEMANTICS_TOKEN}:
            raise ValueError("dataset semantic capture token is invalid")

    @property
    def has_captured_semantics(self) -> bool:
        return self._captured_semantics_token is _CAPTURED_SEMANTICS_TOKEN

    @property
    def has_pit_partitions(self) -> bool:
        return (
            self.dataset_as_of is not None
            and len(self.transformation_receipts) == len(self.partition_sha256s)
            and all(
                receipt.is_authoritative and receipt.row_pit_enforced
                for receipt in self.transformation_receipts
            )
            and self.schema_sha256 is not None
        )

    @property
    def has_verified_split_manifest(self) -> bool:
        return self._verified_split_token is _VERIFIED_SPLIT_TOKEN

    def verify_identity(self) -> None:
        observed = dataset_identity_sha256(
            dates=self.dates,
            frequency=self.frequency,
            schema=self.schema,
            source_snapshot_sha256s=self.source_snapshot_sha256s,
            universe_snapshot_sha256=self.universe_snapshot_sha256,
            feature_code_sha256=self.feature_code_sha256,
            label_code_sha256=self.label_code_sha256,
            split_manifest_sha256=self.split_manifest_sha256,
            calendar_policy_sha256=self.calendar_policy_sha256,
            action_policy_sha256=self.action_policy_sha256,
            cost_policy_sha256=self.cost_policy_sha256,
            partition_sha256s=self.partition_sha256s,
            dataset_as_of=self.dataset_as_of,
            partition_source_receipt_sha256s=tuple(
                source.capture_receipt_sha256 or ""
                for source in self.partition_sources
            ),
            partition_available_ats=tuple(
                source.available_at for source in self.partition_sources
            ),
            partition_parser_sha256s=self.partition_parser_sha256s,
            schema_sha256=self.schema_sha256,
            transformation_receipt_sha256s=tuple(
                receipt.receipt_sha256 for receipt in self.transformation_receipts
            ),
        )
        if observed != self.identity_sha256:
            raise ValueError("dataset manifest semantic identity mismatch")
        if self.has_captured_semantics:
            expected = {
                "feature_code_sha256": self.feature_code_sha256,
                "label_code_sha256": self.label_code_sha256,
                "calendar_policy_sha256": self.calendar_policy_sha256,
                "action_policy_sha256": self.action_policy_sha256,
                "cost_policy_sha256": self.cost_policy_sha256,
            }
            if not self.has_verified_split_manifest:
                expected["split_manifest_sha256"] = self.split_manifest_sha256
            if dict(self._semantic_paths).keys() != expected.keys():
                raise ValueError("dataset semantic path coverage is incomplete")
            for field_name, path in self._semantic_paths:
                if capture_file_digest(path)[0] != expected[field_name]:
                    raise ValueError(f"{field_name} no longer matches captured bytes")
            if len(self._partition_paths) != len(self.partition_sha256s) or any(
                capture_file_digest(path)[0] != digest
                for path, digest in zip(
                    self._partition_paths,
                    self.partition_sha256s,
                    strict=True,
                )
            ):
                raise ValueError("dataset partition bytes no longer match manifest")
            if self.has_verified_split_manifest:
                if self._split_manifest_path is None:
                    raise ValueError("verified split manifest path is missing")
                split = load_split_manifest(capture_file_bytes(self._split_manifest_path))
                if split.manifest_sha256 != self.split_manifest_sha256:
                    raise ValueError("canonical split manifest no longer matches dataset")
        if self.has_pit_partitions:
            assert self.dataset_as_of is not None
            for digest, receipt in zip(
                self.partition_sha256s,
                self.transformation_receipts,
                strict=True,
            ):
                receipt.verify()
                if receipt.output_partition_sha256 != digest:
                    raise ValueError(
                        "transformation receipt does not bind partition bytes"
                    )


def _canonical_timestamp(value: date | datetime) -> str:
    if type(value) is datetime:
        assert isinstance(value, datetime)
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("datetime identities must be timezone-aware")
        return value.astimezone(timezone.utc).isoformat(timespec="microseconds")
    if type(value) is date:
        return value.isoformat()
    raise TypeError("dates must contain only date or timezone-aware datetime values")


def dataset_identity_sha256(
    *,
    dates: Sequence[date | datetime],
    frequency: str,
    schema: Sequence[tuple[str, str]],
    source_snapshot_sha256s: Sequence[str],
    universe_snapshot_sha256: str,
    feature_code_sha256: str,
    label_code_sha256: str,
    split_manifest_sha256: str,
    calendar_policy_sha256: str,
    action_policy_sha256: str,
    cost_policy_sha256: str,
    partition_sha256s: Sequence[str],
    dataset_as_of: datetime | None = None,
    partition_source_receipt_sha256s: Sequence[str] = (),
    partition_available_ats: Sequence[datetime] = (),
    partition_parser_sha256s: Sequence[str] = (),
    schema_sha256: str | None = None,
    transformation_receipt_sha256s: Sequence[str] = (),
) -> str:
    """Hash exact partitions and every dataset-semantic artifact."""

    frozen_dates = tuple(dates)
    if not frozen_dates:
        raise ValueError("dates must not be empty")
    expected_type = type(frozen_dates[0])
    if expected_type not in (date, datetime) or any(
        type(value) is not expected_type for value in frozen_dates
    ):
        raise TypeError("dates must use one consistent temporal type")
    if frozen_dates != tuple(sorted(frozen_dates)):
        raise ValueError("dates must be ordered chronologically")
    if len(frozen_dates) != len(set(frozen_dates)):
        raise ValueError("dates must be unique")
    canonical_dates = tuple(_canonical_timestamp(value) for value in frozen_dates)
    if not isinstance(frequency, str) or not frequency.strip():
        raise ValueError("frequency must be a nonempty string")

    canonical_schema: list[dict[str, str]] = []
    seen_columns: set[str] = set()
    for item in schema:
        if not isinstance(item, tuple) or len(item) != 2:
            raise TypeError("schema entries must be (name, type) tuples")
        name, data_type = item
        if not isinstance(name, str) or not name.strip():
            raise ValueError("schema column names must be nonempty strings")
        if not isinstance(data_type, str) or not data_type.strip():
            raise ValueError("schema data types must be nonempty strings")
        if name in seen_columns:
            raise ValueError("schema column names must be unique")
        seen_columns.add(name)
        canonical_schema.append({"name": name, "type": data_type})
    if not canonical_schema:
        raise ValueError("schema must not be empty")

    frozen_partitions = tuple(partition_sha256s)
    if len(frozen_partitions) != len(canonical_dates):
        raise ValueError("partition_sha256s must contain exactly one hash per date partition")
    if any(
        not isinstance(value, str) or _SHA256.fullmatch(value) is None
        for value in frozen_partitions
    ):
        raise ValueError("partition_sha256s must contain lowercase SHA-256 values")

    frozen_sources = tuple(source_snapshot_sha256s)
    if not frozen_sources:
        raise ValueError("source_snapshot_sha256s must not be empty")
    semantic_hashes = {
        "universe_snapshot_sha256": universe_snapshot_sha256,
        "feature_code_sha256": feature_code_sha256,
        "label_code_sha256": label_code_sha256,
        "split_manifest_sha256": split_manifest_sha256,
        "calendar_policy_sha256": calendar_policy_sha256,
        "action_policy_sha256": action_policy_sha256,
        "cost_policy_sha256": cost_policy_sha256,
    }
    for field_name, value in (
        *(semantic_hashes.items()),
        *(("source_snapshot_sha256s", value) for value in frozen_sources),
    ):
        if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
            raise ValueError(f"{field_name} must contain lowercase SHA-256 values")

    payload = {
        **semantic_hashes,
        "dates": canonical_dates,
        "frequency": frequency,
        "partition_sha256s": frozen_partitions,
        "schema": canonical_schema,
        "source_snapshot_sha256s": frozen_sources,
        "version": 2,
    }
    pit_receipts = tuple(partition_source_receipt_sha256s)
    pit_available = tuple(partition_available_ats)
    pit_parsers = tuple(partition_parser_sha256s)
    transformations = tuple(transformation_receipt_sha256s)
    if any(
        (
            dataset_as_of is not None,
            pit_receipts,
            pit_available,
            pit_parsers,
            schema_sha256,
            transformations,
        )
    ):
        if (
            dataset_as_of is None
            or schema_sha256 is None
            or (
                not transformations
                and (
                    len(pit_receipts) != len(frozen_partitions)
                    or len(pit_available) != len(frozen_partitions)
                    or len(pit_parsers) != len(frozen_partitions)
                )
            )
            or (transformations and len(transformations) != len(frozen_partitions))
        ):
            raise ValueError("PIT partition identity fields must cover every partition")
        as_of = require_aware_utc(dataset_as_of, "dataset_as_of")
        available = tuple(
            require_aware_utc(value, "partition_available_at")
            for value in pit_available
        )
        if any(value > as_of for value in available):
            raise ValueError("partition was unavailable at dataset_as_of")
        for label, values in (
            ("partition_source_receipt_sha256s", pit_receipts),
            ("partition_parser_sha256s", pit_parsers),
            ("schema_sha256", (schema_sha256,)),
            ("transformation_receipt_sha256s", transformations),
        ):
            if any(_SHA256.fullmatch(value) is None for value in values):
                raise ValueError(f"{label} must contain lowercase SHA-256 values")
        payload.update(
            {
                "dataset_as_of": as_of.isoformat(timespec="microseconds"),
                "partition_available_ats": tuple(
                    value.isoformat(timespec="microseconds") for value in available
                ),
                "partition_parser_sha256s": pit_parsers,
                "partition_source_receipt_sha256s": pit_receipts,
                "schema_sha256": schema_sha256,
                "version": 3,
            }
        )
        if transformations:
            payload["transformation_receipt_sha256s"] = transformations
            payload["version"] = 4
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_dataset_manifest(
    **inputs: object,
) -> DatasetManifest:
    """Build an immutable dataset receipt from validated semantic identities."""

    identity_inputs = {
        key: value
        for key, value in inputs.items()
        if key not in {"partition_sources", "transformation_receipts"}
    }
    if inputs.get("transformation_receipts"):
        identity_inputs["transformation_receipt_sha256s"] = tuple(
            receipt.receipt_sha256
            for receipt in inputs["transformation_receipts"]  # type: ignore[union-attr]
        )
    identity = dataset_identity_sha256(**identity_inputs)  # type: ignore[arg-type]
    return DatasetManifest(
        dates=tuple(inputs["dates"]),  # type: ignore[arg-type]
        frequency=str(inputs["frequency"]),
        schema=tuple(inputs["schema"]),  # type: ignore[arg-type]
        source_snapshot_sha256s=tuple(inputs["source_snapshot_sha256s"]),  # type: ignore[arg-type]
        universe_snapshot_sha256=str(inputs["universe_snapshot_sha256"]),
        feature_code_sha256=str(inputs["feature_code_sha256"]),
        label_code_sha256=str(inputs["label_code_sha256"]),
        split_manifest_sha256=str(inputs["split_manifest_sha256"]),
        calendar_policy_sha256=str(inputs["calendar_policy_sha256"]),
        action_policy_sha256=str(inputs["action_policy_sha256"]),
        cost_policy_sha256=str(inputs["cost_policy_sha256"]),
        partition_sha256s=tuple(inputs["partition_sha256s"]),  # type: ignore[arg-type]
        identity_sha256=identity,
        dataset_as_of=inputs.get("dataset_as_of"),  # type: ignore[arg-type]
        partition_sources=tuple(inputs.get("partition_sources", ())),  # type: ignore[arg-type]
        partition_parser_sha256s=tuple(
            inputs.get("partition_parser_sha256s", ())
        ),  # type: ignore[arg-type]
        schema_sha256=inputs.get("schema_sha256"),  # type: ignore[arg-type]
        transformation_receipts=tuple(
            inputs.get("transformation_receipts", ())
        ),  # type: ignore[arg-type]
        _token=_DATASET_MANIFEST_TOKEN,
    )


def capture_dataset_manifest(
    *,
    dates: Sequence[date | datetime],
    frequency: str,
    schema: Sequence[tuple[str, str]],
    source_snapshot_sha256s: Sequence[str],
    universe_snapshot_sha256: str,
    feature_code_path: Path,
    label_code_path: Path,
    split_manifest_path: Path,
    split_manifest_receipt: SplitManifest | None = None,
    calendar_policy_path: Path,
    action_policy_path: Path,
    cost_policy_path: Path,
    partition_paths: Sequence[Path],
    partition_sources: Sequence[SourceIdentity] = (),
    partition_parser_paths: Sequence[Path] = (),
    dataset_as_of: datetime | None = None,
    transformation_receipts: Sequence[TransformationReceipt] = (),
) -> DatasetManifest:
    """Capture all dataset-semantic and partition bytes into a revalidated manifest."""

    semantic_paths = (
        ("feature_code_sha256", feature_code_path),
        ("label_code_sha256", label_code_path),
        *((("split_manifest_sha256", split_manifest_path),) if split_manifest_receipt is None else ()),
        ("calendar_policy_sha256", calendar_policy_path),
        ("action_policy_sha256", action_policy_path),
        ("cost_policy_sha256", cost_policy_path),
    )
    hashes = {
        field_name: capture_file_digest(path)[0]
        for field_name, path in semantic_paths
    }
    verified_split = split_manifest_receipt is not None
    if split_manifest_receipt is None:
        hashes["split_manifest_sha256"] = capture_file_digest(split_manifest_path)[0]
    else:
        split_manifest_receipt.verify()
        if capture_file_bytes(split_manifest_path) != serialize_split_manifest(
            split_manifest_receipt
        ):
            raise ValueError("split manifest path is not the canonical split receipt")
        hashes["split_manifest_sha256"] = split_manifest_receipt.manifest_sha256
    frozen_partitions = tuple(partition_paths)
    partition_hashes = tuple(
        capture_file_digest(path)[0] for path in frozen_partitions
    )
    frozen_sources = tuple(partition_sources)
    frozen_parser_paths = tuple(partition_parser_paths)
    frozen_transformations = tuple(transformation_receipts)
    pit_inputs: dict[str, object] = {}
    if frozen_transformations:
        if (
            dataset_as_of is None
            or len(frozen_transformations) != len(frozen_partitions)
        ):
            raise ValueError(
                "transformation receipts must cover every partition and dataset_as_of"
            )
        as_of = require_aware_utc(dataset_as_of, "dataset_as_of")
        for digest, receipt in zip(
            partition_hashes,
            frozen_transformations,
            strict=True,
        ):
            if not isinstance(receipt, TransformationReceipt):
                raise TypeError("invalid transformation receipt")
            receipt.verify()
            if (
                receipt.output_partition_sha256 != digest
                or receipt.dataset_as_of != as_of
                or receipt.schema != tuple(schema)
                or receipt.feature_program_sha256
                != hashes["feature_code_sha256"]
                or receipt.label_program_sha256 != hashes["label_code_sha256"]
            ):
                raise ValueError(
                    "transformation receipt does not bind feature, label, partition, "
                    "schema, or as-of"
                )
        canonical_schema = json.dumps(tuple(schema), separators=(",", ":")).encode()
        pit_inputs = {
            "dataset_as_of": as_of,
            "transformation_receipts": frozen_transformations,
            "schema_sha256": hashlib.sha256(canonical_schema).hexdigest(),
        }
    elif any((frozen_sources, frozen_parser_paths, dataset_as_of is not None)):
        if (
            dataset_as_of is None
            or len(frozen_sources) != len(frozen_partitions)
            or len(frozen_parser_paths) != len(frozen_partitions)
        ):
            raise ValueError("PIT source and parser paths must cover every partition")
        as_of = require_aware_utc(dataset_as_of, "dataset_as_of")
        for digest, source in zip(partition_hashes, frozen_sources, strict=True):
            require_provider_qualified_source(source)
            if source.content_sha256 != digest:
                raise ValueError("partition source receipt does not bind partition bytes")
            if source.available_at > as_of:
                raise ValueError("partition source was unavailable at dataset_as_of")
        canonical_schema = json.dumps(
            tuple(schema),
            separators=(",", ":"),
        ).encode()
        pit_inputs = {
            "dataset_as_of": as_of,
            "partition_available_ats": tuple(
                source.available_at for source in frozen_sources
            ),
            "partition_parser_sha256s": tuple(
                capture_file_digest(path)[0] for path in frozen_parser_paths
            ),
            "partition_source_receipt_sha256s": tuple(
                source.capture_receipt_sha256 for source in frozen_sources
            ),
            "schema_sha256": hashlib.sha256(canonical_schema).hexdigest(),
        }
    manifest = build_dataset_manifest(
        dates=dates,
        frequency=frequency,
        schema=schema,
        source_snapshot_sha256s=source_snapshot_sha256s,
        universe_snapshot_sha256=universe_snapshot_sha256,
        partition_sha256s=partition_hashes,
        partition_sources=frozen_sources,
        **pit_inputs,
        **hashes,
    )
    values = {
        name: getattr(manifest, name)
        for name in manifest.__dataclass_fields__
        if not name.startswith("_")
    }
    return DatasetManifest(
        **values,
        _token=_DATASET_MANIFEST_TOKEN,
        _semantic_paths=semantic_paths,
        _partition_paths=frozen_partitions,
        _partition_parser_paths=frozen_parser_paths,
        _captured_semantics_token=_CAPTURED_SEMANTICS_TOKEN,
        _split_manifest_path=split_manifest_path,
        _verified_split_token=(
            _VERIFIED_SPLIT_TOKEN if verified_split else None
        ),
    )
