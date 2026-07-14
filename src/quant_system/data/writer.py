"""One append-only DuckDB writer with transaction, lock, and idempotent batches."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any, Iterator, Sequence

import duckdb


class DataWriteError(RuntimeError):
    """Raised when an append cannot be completed without mutation ambiguity."""


IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
BATCH_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class AppendResult:
    batch_id: str
    target: str
    row_count: int
    inserted_rows: int
    existing_rows: int
    batch_sha256: str
    source_sha256: str
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _identifier(value: str, label: str) -> str:
    if not isinstance(value, str) or IDENTIFIER.fullmatch(value) is None:
        raise DataWriteError(f"unsafe {label}")
    return value


def _quote(value: str) -> str:
    return f'"{_identifier(value, "SQL identifier")}"'


def _database_path(path: Path) -> Path:
    candidate = path.expanduser()
    if not candidate.exists() or not candidate.is_file() or candidate.is_symlink():
        raise DataWriteError(f"database is not a regular file: {candidate}")
    return candidate.resolve()


@contextmanager
def _writer_lock(path: Path, timeout_seconds: float) -> Iterator[None]:
    lock_path = path.with_suffix(path.suffix + ".writer.lock")
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(lock_path, flags, 0o600)
    except OSError as exc:
        raise DataWriteError("cannot open writer lock") from exc
    try:
        os.fchmod(fd, 0o600)
        deadline = time.monotonic() + timeout_seconds
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError as exc:
                if time.monotonic() >= deadline:
                    raise DataWriteError("writer lock is held") from exc
                time.sleep(min(0.05, max(deadline - time.monotonic(), 0)))
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def _canonical(rows: Sequence[dict[str, Any]], keys: Sequence[str]) -> bytes:
    try:
        ordered = sorted(
            rows,
            key=lambda row: tuple(
                json.dumps(row[key], sort_keys=True, default=str) for key in keys
            ),
        )
        text = json.dumps(
            ordered,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
            allow_nan=False,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise DataWriteError("rows are not canonically serializable") from exc
    return text.encode("utf-8")


def _validate_inputs(
    rows: Sequence[dict[str, Any]],
    natural_keys: Sequence[str],
    *,
    batch_id: str,
    source_sha256: str,
    max_rows: int,
) -> tuple[tuple[str, ...], str]:
    if not BATCH_ID.fullmatch(batch_id):
        raise DataWriteError("invalid batch_id")
    if not SHA256.fullmatch(source_sha256):
        raise DataWriteError("invalid source_sha256")
    if not rows or len(rows) > max_rows:
        raise DataWriteError("batch is empty or exceeds max_rows")
    if not natural_keys or len(set(natural_keys)) != len(natural_keys):
        raise DataWriteError("natural keys are empty or duplicated")
    keys = tuple(_identifier(key, "natural key") for key in natural_keys)
    first = rows[0]
    if not isinstance(first, dict) or not first:
        raise DataWriteError("rows must be non-empty objects")
    columns = tuple(first)
    if len(set(columns)) != len(columns):
        raise DataWriteError("duplicate columns")
    for column in columns:
        _identifier(column, "column")
    if not set(keys) <= set(columns):
        raise DataWriteError("natural key column is absent")
    seen: set[tuple[Any, ...]] = set()
    for row in rows:
        if not isinstance(row, dict) or tuple(row) != columns:
            raise DataWriteError("all rows must have identical ordered columns")
        key = tuple(row[item] for item in keys)
        if any(value is None for value in key):
            raise DataWriteError("natural keys cannot be null")
        try:
            duplicate = key in seen
            seen.add(key)
        except TypeError as exc:
            raise DataWriteError("natural keys must be scalar/hashable") from exc
        if duplicate:
            raise DataWriteError("batch contains duplicate natural keys")
    digest = hashlib.sha256(_canonical(rows, keys)).hexdigest()
    return columns, digest


def _target_columns(
    connection: duckdb.DuckDBPyConnection,
    schema: str,
    table: str,
) -> tuple[str, ...]:
    rows = connection.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = ? AND table_name = ? ORDER BY ordinal_position",
        [schema, table],
    ).fetchall()
    if not rows:
        raise DataWriteError("target table does not exist")
    return tuple(str(row[0]) for row in rows)


def _ensure_metadata(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute("CREATE SCHEMA IF NOT EXISTS _quant_meta")
    connection.execute(
        "CREATE TABLE IF NOT EXISTS _quant_meta.ingest_runs ("
        "batch_id VARCHAR PRIMARY KEY, target VARCHAR NOT NULL, "
        "source_sha256 VARCHAR NOT NULL, batch_sha256 VARCHAR NOT NULL, "
        "row_count BIGINT NOT NULL, inserted_rows BIGINT NOT NULL, "
        "existing_rows BIGINT NOT NULL, completed_at TIMESTAMPTZ NOT NULL)"
    )


def append_rows(
    db_path: Path,
    *,
    schema: str,
    table: str,
    natural_keys: Sequence[str],
    rows: Sequence[dict[str, Any]],
    batch_id: str,
    source_sha256: str,
    max_rows: int = 100_000,
    lock_timeout_seconds: float = 5.0,
) -> AppendResult:
    """Append one batch; exact replays are no-ops and key conflicts fail."""

    schema = _identifier(schema, "schema")
    table = _identifier(table, "table")
    if type(max_rows) is not int or not 1 <= max_rows <= 1_000_000:
        raise DataWriteError("max_rows must be 1..1000000")
    if (
        type(lock_timeout_seconds) not in {int, float}
        or not 0 <= float(lock_timeout_seconds) <= 300
    ):
        raise DataWriteError("lock_timeout_seconds must be 0..300")
    columns, batch_sha256 = _validate_inputs(
        rows,
        natural_keys,
        batch_id=batch_id,
        source_sha256=source_sha256,
        max_rows=max_rows,
    )
    keys = tuple(natural_keys)
    path = _database_path(db_path)
    target = f"{schema}.{table}"
    qualified = f"{_quote(schema)}.{_quote(table)}"

    with _writer_lock(path, float(lock_timeout_seconds)):
        connection = duckdb.connect(str(path))
        try:
            connection.execute("BEGIN")
            expected_columns = _target_columns(connection, schema, table)
            if columns != expected_columns:
                raise DataWriteError("input columns do not match target order")
            _ensure_metadata(connection)
            previous = connection.execute(
                "SELECT target, source_sha256, batch_sha256, row_count, "
                "inserted_rows, existing_rows FROM _quant_meta.ingest_runs "
                "WHERE batch_id = ?",
                [batch_id],
            ).fetchone()
            if previous is not None:
                if previous[:4] != (
                    target,
                    source_sha256,
                    batch_sha256,
                    len(rows),
                ):
                    raise DataWriteError("batch_id is already bound to different input")
                connection.execute("ROLLBACK")
                return AppendResult(
                    batch_id=batch_id,
                    target=target,
                    row_count=int(previous[3]),
                    inserted_rows=int(previous[4]),
                    existing_rows=int(previous[5]),
                    batch_sha256=batch_sha256,
                    source_sha256=source_sha256,
                    status="IDEMPOTENT_REPLAY",
                )

            connection.execute(
                f"CREATE TEMP TABLE _incoming AS SELECT * FROM {qualified} WHERE FALSE"
            )
            column_sql = ",".join(_quote(column) for column in columns)
            placeholders = ",".join("?" for _ in columns)
            connection.executemany(
                f"INSERT INTO _incoming ({column_sql}) VALUES ({placeholders})",
                [[row[column] for column in columns] for row in rows],
            )
            join = " AND ".join(
                f"i.{_quote(key)} = t.{_quote(key)}" for key in keys
            )
            same = " AND ".join(
                f"i.{_quote(column)} IS NOT DISTINCT FROM t.{_quote(column)}"
                for column in columns
            )
            conflict_count = int(
                connection.execute(
                    f"SELECT count(*) FROM _incoming i JOIN {qualified} t "
                    f"ON {join} WHERE NOT ({same})"
                ).fetchone()[0]
            )
            if conflict_count:
                raise DataWriteError(
                    f"{conflict_count} natural-key conflict(s); batch rolled back"
                )
            existing_rows = int(
                connection.execute(
                    f"SELECT count(*) FROM _incoming i JOIN {qualified} t ON {join}"
                ).fetchone()[0]
            )
            inserted_rows = len(rows) - existing_rows
            if inserted_rows:
                connection.execute(
                    f"INSERT INTO {qualified} ({column_sql}) "
                    f"SELECT {column_sql} FROM _incoming i "
                    f"WHERE NOT EXISTS (SELECT 1 FROM {qualified} t WHERE {join})"
                )
            connection.execute(
                "INSERT INTO _quant_meta.ingest_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    batch_id,
                    target,
                    source_sha256,
                    batch_sha256,
                    len(rows),
                    inserted_rows,
                    existing_rows,
                    datetime.now(timezone.utc),
                ],
            )
            connection.execute("COMMIT")
        except Exception:
            try:
                connection.execute("ROLLBACK")
            except duckdb.Error:
                pass
            raise
        finally:
            connection.close()
    return AppendResult(
        batch_id=batch_id,
        target=target,
        row_count=len(rows),
        inserted_rows=inserted_rows,
        existing_rows=existing_rows,
        batch_sha256=batch_sha256,
        source_sha256=source_sha256,
        status="COMPLETED",
    )
