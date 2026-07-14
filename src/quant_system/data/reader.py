"""Cheap read-only DuckDB inspection and query helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
from typing import Any, Iterable

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


def _database_path(path: Path) -> Path:
    candidate = path.expanduser()
    if not candidate.exists() or not candidate.is_file() or candidate.is_symlink():
        raise DataReadError(f"database is not a regular file: {candidate}")
    return candidate.resolve()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def database_info(path: Path, *, include_hash: bool = False) -> DatabaseInfo:
    db_path = _database_path(path)
    try:
        with duckdb.connect(str(db_path), read_only=True) as connection:
            rows = connection.execute(
                "SELECT schema_name, table_name, estimated_size "
                "FROM duckdb_tables() WHERE NOT internal "
                "ORDER BY schema_name, table_name"
            ).fetchall()
    except duckdb.Error as exc:
        raise DataReadError(f"cannot inspect database: {db_path}") from exc
    tables = tuple(TableInfo(str(s), str(t), int(n or 0)) for s, t, n in rows)
    return DatabaseInfo(
        path=str(db_path),
        size_bytes=db_path.stat().st_size,
        tables=tables,
        sha256=sha256_file(db_path) if include_hash else None,
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
    db_path = _database_path(path)
    try:
        with duckdb.connect(str(db_path), read_only=True) as connection:
            statements = connection.extract_statements(sql)
            if len(statements) != 1 or statements[0].type != duckdb.StatementType.SELECT:
                raise DataReadError("exactly one read-only SELECT statement is required")
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
    return QueryResult(
        columns=tuple(str(column[0]) for column in description),
        rows=tuple(tuple(row) for row in rows[:max_rows]),
        truncated=len(rows) > max_rows,
    )
