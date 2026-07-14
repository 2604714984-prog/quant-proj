"""Read-only access and a single append-only DuckDB writer."""

from .reader import DatabaseInfo, QueryResult, database_info, query
from .writer import AppendResult, DataWriteError, append_rows

__all__ = [
    "AppendResult",
    "DatabaseInfo",
    "DataWriteError",
    "QueryResult",
    "append_rows",
    "database_info",
    "query",
]
