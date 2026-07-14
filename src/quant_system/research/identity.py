"""Canonical research-dataset identity without a controller dependency."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timezone


_SHA256 = re.compile(r"[0-9a-f]{64}")


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
    config_ids: Mapping[str, str],
    partition_sha256s: Sequence[str],
) -> str:
    """Hash exact date partitions, ordered schema, config, and partition contents."""

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

    if not isinstance(config_ids, Mapping) or not config_ids:
        raise ValueError("config_ids must not be empty")
    canonical_config: dict[str, str] = {}
    for name, value in config_ids.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("config identity names must be nonempty strings")
        if not isinstance(value, str) or not value.strip():
            raise ValueError("config identity values must be nonempty strings")
        canonical_config[name] = value
    canonical_config = dict(sorted(canonical_config.items()))

    frozen_partitions = tuple(partition_sha256s)
    if len(frozen_partitions) != len(canonical_dates):
        raise ValueError("partition_sha256s must contain exactly one hash per date partition")
    if any(
        not isinstance(value, str) or _SHA256.fullmatch(value) is None
        for value in frozen_partitions
    ):
        raise ValueError("partition_sha256s must contain lowercase SHA-256 values")

    payload = {
        "config_ids": canonical_config,
        "dates": canonical_dates,
        "frequency": frequency,
        "partition_sha256s": frozen_partitions,
        "schema": canonical_schema,
        "version": 1,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
