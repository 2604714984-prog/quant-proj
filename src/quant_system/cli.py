"""One small command line for local data access and append-only imports."""

from __future__ import annotations

import argparse
from datetime import date, datetime
from decimal import Decimal
import json
from pathlib import Path
from typing import Any

from . import __version__
from .config import AppSettings, load_settings
from .data import append_rows, database_info, query


def _json_default(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"cannot JSON encode {type(value).__name__}")


def _print(value: Any) -> None:
    print(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            default=_json_default,
        )
    )


def _rows(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".jsonl":
        raw = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        raw = json.loads(text)
    if not isinstance(raw, list) or any(not isinstance(row, dict) for row in raw):
        raise ValueError("input must be a JSON array or JSONL objects")
    return raw


def _database(args: argparse.Namespace, settings: AppSettings) -> Path:
    return args.db.expanduser().resolve(strict=False) if args.db else settings.paths.database


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="quant")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("info", help="show resolved local paths")

    data = commands.add_parser("data", help="inspect, query, or append external DuckDB data")
    data_commands = data.add_subparsers(dest="data_command", required=True)
    inspect = data_commands.add_parser("inspect")
    inspect.add_argument("--db", type=Path)
    inspect.add_argument("--hash", action="store_true")

    query_parser = data_commands.add_parser("query")
    query_parser.add_argument("--db", type=Path)
    query_parser.add_argument("--sql", required=True)
    query_parser.add_argument("--max-rows", type=int, default=1000)

    append = data_commands.add_parser("append")
    append.add_argument("--db", type=Path)
    append.add_argument("--schema", required=True)
    append.add_argument("--table", required=True)
    append.add_argument("--keys", required=True, help="comma-separated natural keys")
    append.add_argument("--input", type=Path, required=True)
    append.add_argument("--batch-id", required=True)
    append.add_argument("--source-sha256", required=True)
    append.add_argument("--execute", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    settings = load_settings(args.config)

    if args.command == "info":
        _print(
            {
                "version": __version__,
                "project_root": str(settings.paths.project_root),
                "data_root": str(settings.paths.data_root),
                "database": str(settings.paths.database),
                "database_exists": settings.paths.database.exists(),
                "config": str(settings.config_path),
            }
        )
        return 0
    db_path = _database(args, settings)
    if args.data_command == "inspect":
        _print(database_info(db_path, include_hash=args.hash).to_dict())
        return 0
    if args.data_command == "query":
        _print(query(db_path, args.sql, max_rows=args.max_rows).to_dict())
        return 0
    rows = _rows(args.input)
    keys = tuple(key.strip() for key in args.keys.split(",") if key.strip())
    if not args.execute:
        _print(
            {
                "status": "DRY_RUN",
                "writes": False,
                "database": str(db_path),
                "target": f"{args.schema}.{args.table}",
                "row_count": len(rows),
                "batch_id": args.batch_id,
                "natural_keys": list(keys),
            }
        )
        return 0
    result = append_rows(
        db_path,
        schema=args.schema,
        table=args.table,
        natural_keys=keys,
        rows=rows,
        batch_id=args.batch_id,
        source_sha256=args.source_sha256,
        max_rows=settings.writer.max_rows_per_batch,
        lock_timeout_seconds=settings.writer.lock_timeout_seconds,
    )
    _print(result.to_dict())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
