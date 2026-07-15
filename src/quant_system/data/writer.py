"""One append-only DuckDB writer with transaction, lock, and idempotent batches."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import time
from typing import Any, Iterator, Sequence

import duckdb


class DataWriteError(RuntimeError):
    """Raised when an append cannot be completed without mutation ambiguity."""


IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
BATCH_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
METADATA_COLUMNS = (
    ("batch_id", "VARCHAR", "NO"),
    ("target", "VARCHAR", "NO"),
    ("source_sha256", "VARCHAR", "NO"),
    ("batch_sha256", "VARCHAR", "NO"),
    ("row_count", "BIGINT", "NO"),
    ("inserted_rows", "BIGINT", "NO"),
    ("existing_rows", "BIGINT", "NO"),
    ("completed_at", "TIMESTAMP WITH TIME ZONE", "NO"),
)


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


def _inode(value: os.stat_result) -> tuple[int, int]:
    return value.st_dev, value.st_ino


def _assert_path_identity(path: Path, descriptor: int, identity: tuple[int, int]) -> None:
    try:
        descriptor_stat = os.fstat(descriptor)
        path_stat = os.stat(path, follow_symlinks=False)
    except OSError as exc:
        raise DataWriteError("database path identity changed") from exc
    if (
        not stat.S_ISREG(descriptor_stat.st_mode)
        or not stat.S_ISREG(path_stat.st_mode)
        or descriptor_stat.st_nlink != 1
        or path_stat.st_nlink != 1
        or _inode(descriptor_stat) != identity
        or _inode(path_stat) != identity
    ):
        raise DataWriteError("database path identity changed")


def _assert_committed_path_identity(
    path: Path, descriptor: int, identity: tuple[int, int]
) -> None:
    try:
        _assert_path_identity(path, descriptor, identity)
    except DataWriteError as exc:
        raise DataWriteError(
            "append committed but the active database path changed; "
            "the published result is ambiguous"
        ) from exc


@contextmanager
def _pinned_database(path: Path) -> Iterator[tuple[Path, str, int, tuple[int, int]]]:
    candidate = path.expanduser()
    flags = os.O_RDWR | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(candidate, flags)
    except OSError as exc:
        raise DataWriteError(f"database is not a regular file: {candidate}") from exc
    try:
        descriptor_stat = os.fstat(descriptor)
        path_stat = os.stat(candidate, follow_symlinks=False)
        if (
            not stat.S_ISREG(descriptor_stat.st_mode)
            or not stat.S_ISREG(path_stat.st_mode)
            or descriptor_stat.st_nlink != 1
            or path_stat.st_nlink != 1
            or _inode(descriptor_stat) != _inode(path_stat)
        ):
            raise DataWriteError(
                f"database must be a single-link regular file: {candidate}"
            )
        resolved = Path(os.path.realpath(candidate))
        identity = _inode(descriptor_stat)
        yield resolved, f"/proc/self/fd/{descriptor}", descriptor, identity
    finally:
        os.close(descriptor)


@contextmanager
def _writer_lock(path: Path, timeout_seconds: float) -> Iterator[None]:
    lock_path = path.with_suffix(path.suffix + ".writer.lock")
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(lock_path, flags, 0o600)
    except OSError as exc:
        raise DataWriteError("cannot open writer lock") from exc
    try:
        opened = os.fstat(fd)
        try:
            linked = os.stat(lock_path, follow_symlinks=False)
        except OSError as exc:
            raise DataWriteError("writer lock path identity changed") from exc
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
            or not stat.S_ISREG(linked.st_mode)
            or linked.st_nlink != 1
            or _inode(opened) != _inode(linked)
        ):
            raise DataWriteError("writer lock must be a single-link regular file")
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
        opened = os.fstat(fd)
        linked = os.stat(lock_path, follow_symlinks=False)
        if (
            opened.st_nlink != 1
            or linked.st_nlink != 1
            or _inode(opened) != _inode(linked)
        ):
            raise DataWriteError("writer lock path identity changed")
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
        if any(
            (isinstance(value, float) and not math.isfinite(value))
            or (isinstance(value, Decimal) and not value.is_finite())
            for value in key
        ):
            raise DataWriteError("natural keys must be finite")
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


def _floating_columns(
    connection: duckdb.DuckDBPyConnection,
    schema: str,
    table: str,
) -> tuple[str, ...]:
    rows = connection.execute(
        "SELECT column_name, upper(data_type) FROM information_schema.columns "
        "WHERE table_schema = ? AND table_name = ? ORDER BY ordinal_position",
        [schema, table],
    ).fetchall()
    return tuple(
        str(column_name)
        for column_name, data_type in rows
        if str(data_type) in {"FLOAT", "REAL", "DOUBLE"}
    )


def _ensure_metadata(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute("CREATE SCHEMA IF NOT EXISTS _quant_meta")
    connection.execute(
        "CREATE TABLE IF NOT EXISTS _quant_meta.ingest_runs ("
        "batch_id VARCHAR PRIMARY KEY, target VARCHAR NOT NULL, "
        "source_sha256 VARCHAR NOT NULL, batch_sha256 VARCHAR NOT NULL, "
        "row_count BIGINT NOT NULL, inserted_rows BIGINT NOT NULL, "
        "existing_rows BIGINT NOT NULL, completed_at TIMESTAMPTZ NOT NULL)"
    )
    columns = tuple(
        tuple(str(value) for value in row)
        for row in connection.execute(
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_schema='_quant_meta' AND table_name='ingest_runs' "
            "ORDER BY ordinal_position"
        ).fetchall()
    )
    primary_keys = tuple(
        tuple(str(value) for value in row[0])
        for row in connection.execute(
            "SELECT constraint_column_names FROM duckdb_constraints() "
            "WHERE schema_name='_quant_meta' AND table_name='ingest_runs' "
            "AND constraint_type='PRIMARY KEY' ORDER BY constraint_index"
        ).fetchall()
    )
    if columns != METADATA_COLUMNS or primary_keys != (("batch_id",),):
        raise DataWriteError("metadata table does not match the immutable contract")


def _validate_previous(
    previous: tuple[Any, ...],
    *,
    target: str,
    source_sha256: str,
    batch_sha256: str,
    row_count: int,
) -> tuple[int, int, int]:
    if previous[:4] != (target, source_sha256, batch_sha256, row_count):
        raise DataWriteError("batch_id is already bound to different input")
    stored = tuple(int(value) for value in previous[3:6])
    stored_rows, stored_inserted, stored_existing = stored
    if (
        min(stored) < 0
        or stored_inserted + stored_existing != stored_rows
        or stored_rows != row_count
    ):
        raise DataWriteError("metadata replay counts violate the immutable contract")
    return stored


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
    if schema.lower() == "_quant_meta":
        raise DataWriteError("the _quant_meta schema is private")
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
    target = f"{schema}.{table}"
    qualified = f"{_quote(schema)}.{_quote(table)}"

    with _pinned_database(db_path) as (path, pinned_path, descriptor, identity):
        with _writer_lock(path, float(lock_timeout_seconds)):
            _assert_path_identity(path, descriptor, identity)
            connection = duckdb.connect(pinned_path)
            committed = False
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
                stored_counts = (
                    _validate_previous(
                        previous,
                        target=target,
                        source_sha256=source_sha256,
                        batch_sha256=batch_sha256,
                        row_count=len(rows),
                    )
                    if previous is not None
                    else None
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
                floating_columns = _floating_columns(connection, schema, table)
                if floating_columns:
                    nonfinite = " OR ".join(
                        f"({_quote(column)} IS NOT NULL "
                        f"AND NOT isfinite({_quote(column)}))"
                        for column in floating_columns
                    )
                    nonfinite_rows = int(
                        connection.execute(
                            f"SELECT count(*) FROM _incoming WHERE {nonfinite}"
                        ).fetchone()[0]
                    )
                    if nonfinite_rows:
                        raise DataWriteError(
                            "staging conversion produced nonfinite floating values"
                        )
                incoming_keys = ",".join(_quote(key) for key in keys)
                duplicate_incoming_keys = int(
                    connection.execute(
                        "SELECT count(*) FROM ("
                        f"SELECT {incoming_keys} FROM _incoming "
                        f"GROUP BY {incoming_keys} HAVING count(*) > 1) duplicate_keys"
                    ).fetchone()[0]
                )
                if duplicate_incoming_keys:
                    raise DataWriteError(
                        "staging conversion produced duplicate natural keys"
                    )
                join = " AND ".join(
                    f"i.{_quote(key)} = t.{_quote(key)}" for key in keys
                )
                same = " AND ".join(
                    f"i.{_quote(column)} IS NOT DISTINCT FROM t.{_quote(column)}"
                    for column in columns
                )
                grouped_keys = ",".join(f"t.{_quote(key)}" for key in keys)
                duplicate_target_keys = int(
                    connection.execute(
                        "SELECT count(*) FROM ("
                        f"SELECT {grouped_keys} FROM {qualified} t "
                        f"JOIN _incoming i ON {join} GROUP BY {grouped_keys} "
                        "HAVING count(*) > 1) duplicate_keys"
                    ).fetchone()[0]
                )
                if duplicate_target_keys:
                    raise DataWriteError(
                        "target contains duplicate rows for incoming natural keys"
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
                if previous is not None:
                    if existing_rows != len(rows):
                        raise DataWriteError(
                            "idempotent replay target rows are missing"
                        )
                    if stored_counts is None or stored_counts[0] != existing_rows:
                        raise DataWriteError(
                            "metadata replay count does not match the current target"
                        )
                    _assert_path_identity(path, descriptor, identity)
                    connection.execute("ROLLBACK")
                    return AppendResult(
                        batch_id=batch_id,
                        target=target,
                        row_count=stored_counts[0],
                        inserted_rows=0,
                        existing_rows=existing_rows,
                        batch_sha256=batch_sha256,
                        source_sha256=source_sha256,
                        status="IDEMPOTENT_REPLAY",
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
                _assert_path_identity(path, descriptor, identity)
                connection.execute("COMMIT")
                committed = True
                _assert_committed_path_identity(path, descriptor, identity)
            except Exception:
                if not committed:
                    try:
                        connection.execute("ROLLBACK")
                    except duckdb.Error:
                        pass
                raise
            finally:
                try:
                    connection.close()
                except Exception as exc:
                    if committed:
                        raise DataWriteError(
                            "append committed but database close failed; "
                            "the published result is ambiguous"
                        ) from exc
                    raise
            if committed:
                _assert_committed_path_identity(path, descriptor, identity)
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
