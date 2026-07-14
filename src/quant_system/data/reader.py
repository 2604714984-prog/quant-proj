"""Cheap read-only DuckDB inspection and query helpers."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
import hashlib
import os
from pathlib import Path
import stat
from typing import Any, Iterable, Iterator

import duckdb


class DataReadError(RuntimeError):
    """Raised when the external database cannot be read safely."""


@dataclass(frozen=True)
class TableInfo:
    schema: str
    table: str
    estimated_rows: int


@dataclass(frozen=True)
class DatabaseInfo:
    path: str
    size_bytes: int
    tables: tuple[TableInfo, ...]
    sha256: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["table_count"] = len(self.tables)
        return value


@dataclass(frozen=True)
class QueryResult:
    columns: tuple[str, ...]
    rows: tuple[tuple[Any, ...], ...]
    truncated: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "columns": list(self.columns),
            "rows": [list(row) for row in self.rows],
            "truncated": self.truncated,
        }


def _signature(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _assert_stable(path: Path, descriptor: int, original: tuple[int, ...]) -> None:
    try:
        descriptor_stat = os.fstat(descriptor)
        path_stat = os.stat(path, follow_symlinks=False)
    except OSError as exc:
        raise DataReadError("database changed while it was being read") from exc
    if (
        not stat.S_ISREG(descriptor_stat.st_mode)
        or not stat.S_ISREG(path_stat.st_mode)
        or _signature(descriptor_stat) != original
        or _signature(path_stat) != original
    ):
        raise DataReadError("database changed while it was being read")


@contextmanager
def _pinned_database(path: Path) -> Iterator[tuple[Path, str, int, tuple[int, ...]]]:
    candidate = path.expanduser()
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(candidate, flags)
    except OSError as exc:
        raise DataReadError(f"database is not a regular file: {candidate}") from exc
    try:
        descriptor_stat = os.fstat(descriptor)
        try:
            path_stat = os.stat(candidate, follow_symlinks=False)
        except OSError as exc:
            raise DataReadError(f"database is not a regular file: {candidate}") from exc
        if (
            not stat.S_ISREG(descriptor_stat.st_mode)
            or not stat.S_ISREG(path_stat.st_mode)
            or (descriptor_stat.st_dev, descriptor_stat.st_ino)
            != (path_stat.st_dev, path_stat.st_ino)
        ):
            raise DataReadError(f"database is not a regular file: {candidate}")
        resolved = Path(os.path.realpath(candidate))
        yield (
            resolved,
            f"/proc/self/fd/{descriptor}",
            descriptor,
            _signature(descriptor_stat),
        )
    finally:
        os.close(descriptor)


def _sha256_descriptor(descriptor: int) -> str:
    digest = hashlib.sha256()
    os.lseek(descriptor, 0, os.SEEK_SET)
    while block := os.read(descriptor, 1024 * 1024):
        digest.update(block)
    return digest.hexdigest()


def sha256_file(path: Path) -> str:
    with _pinned_database(path) as (db_path, _, descriptor, original):
        digest = _sha256_descriptor(descriptor)
        _assert_stable(db_path, descriptor, original)
        return digest


def database_info(path: Path, *, include_hash: bool = False) -> DatabaseInfo:
    with _pinned_database(path) as (db_path, pinned_path, descriptor, original):
        try:
            with duckdb.connect(pinned_path, read_only=True) as connection:
                rows = connection.execute(
                    "SELECT schema_name, table_name, estimated_size "
                    "FROM duckdb_tables() WHERE NOT internal "
                    "ORDER BY schema_name, table_name"
                ).fetchall()
        except duckdb.Error as exc:
            raise DataReadError(f"cannot inspect database: {db_path}") from exc
        digest = _sha256_descriptor(descriptor) if include_hash else None
        _assert_stable(db_path, descriptor, original)
        tables = tuple(TableInfo(str(s), str(t), int(n or 0)) for s, t, n in rows)
        return DatabaseInfo(
            path=str(db_path),
            size_bytes=int(original[2]),
            tables=tables,
            sha256=digest,
        )


def query(
    path: Path,
    sql: str,
    parameters: Iterable[Any] = (),
    *,
    max_rows: int = 1000,
) -> QueryResult:
    if not isinstance(sql, str) or not sql.strip():
        raise DataReadError("SQL is empty")
    if not 1 <= max_rows <= 100_000:
        raise DataReadError("max_rows must be 1..100000")
    with _pinned_database(path) as (db_path, pinned_path, descriptor, original):
        try:
            with duckdb.connect(pinned_path, read_only=True) as connection:
                statements = connection.extract_statements(sql)
                if (
                    len(statements) != 1
                    or statements[0].type != duckdb.StatementType.SELECT
                ):
                    raise DataReadError(
                        "exactly one read-only SELECT statement is required"
                    )
                connection.execute("SET enable_external_access = false")
                cursor = connection.execute(statements[0].query, list(parameters))
                description = cursor.description
                if description is None:
                    raise DataReadError("query did not return a relation")
                rows = cursor.fetchmany(max_rows + 1)
        except DataReadError:
            raise
        except duckdb.Error as exc:
            raise DataReadError("read-only query failed") from exc
        _assert_stable(db_path, descriptor, original)
        return QueryResult(
            columns=tuple(str(column[0]) for column in description),
            rows=tuple(tuple(row) for row in rows[:max_rows]),
            truncated=len(rows) > max_rows,
        )
