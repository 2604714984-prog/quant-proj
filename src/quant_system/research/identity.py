"""Canonical research-dataset identity without a controller dependency."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from dataclasses import field
from datetime import date, datetime, timezone


_SHA256 = re.compile(r"[0-9a-f]{64}")
_DATASET_MANIFEST_TOKEN = object()


@dataclass(frozen=True)
class DatasetManifest:
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
    _token: object | None = field(default=None, repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        if self._token is not _DATASET_MANIFEST_TOKEN:
            raise ValueError("DatasetManifest must be created by build_dataset_manifest")


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
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_dataset_manifest(
    **inputs: object,
) -> DatasetManifest:
    """Build an immutable dataset receipt from validated semantic identities."""

    identity = dataset_identity_sha256(**inputs)  # type: ignore[arg-type]
    return DatasetManifest(
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
        _token=_DATASET_MANIFEST_TOKEN,
    )
