"""Canonical research-dataset identity without a controller dependency."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from dataclasses import field
from datetime import date, datetime, timezone
from pathlib import Path

from quant_system.data.source_identity import (
    SourceIdentity,
    capture_file_bytes,
    capture_file_digest,
    require_aware_utc,
    require_provider_qualified_source,
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
            and len(self.partition_sources) == len(self.partition_sha256s)
            and len(self.partition_parser_sha256s) == len(self.partition_sha256s)
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
            for digest, source in zip(
                self.partition_sha256s,
                self.partition_sources,
                strict=True,
            ):
                require_provider_qualified_source(source)
                if source.content_sha256 != digest:
                    raise ValueError("partition source bytes do not match partition hash")
                if source.available_at > self.dataset_as_of:
                    raise ValueError("partition source was unavailable at dataset_as_of")
            if len(self._partition_parser_paths) != len(self.partition_parser_sha256s):
                raise ValueError("partition parser path coverage is incomplete")
            if any(
                capture_file_digest(path)[0] != digest
                for path, digest in zip(
                    self._partition_parser_paths,
                    self.partition_parser_sha256s,
                    strict=True,
                )
            ):
                raise ValueError("partition parser bytes no longer match manifest")


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
    if any((dataset_as_of is not None, pit_receipts, pit_available, pit_parsers, schema_sha256)):
        if (
            dataset_as_of is None
            or schema_sha256 is None
            or len(pit_receipts) != len(frozen_partitions)
            or len(pit_available) != len(frozen_partitions)
            or len(pit_parsers) != len(frozen_partitions)
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
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_dataset_manifest(
    **inputs: object,
) -> DatasetManifest:
    """Build an immutable dataset receipt from validated semantic identities."""

    identity_inputs = {
        key: value for key, value in inputs.items() if key != "partition_sources"
    }
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
    pit_inputs: dict[str, object] = {}
    if any((frozen_sources, frozen_parser_paths, dataset_as_of is not None)):
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
