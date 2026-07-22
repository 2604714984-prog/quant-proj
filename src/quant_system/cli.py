"""One small command line for local data access and append-only imports."""

from __future__ import annotations

import argparse
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any

from . import __version__
from .config import AppSettings, load_settings
from .data import append_rows, capture_source_file, database_info, query


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
            allow_nan=False,
        )
    )


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON value is forbidden: {value}")


def _loads(value: str) -> Any:
    return json.loads(
        value,
        object_pairs_hook=_strict_object,
        parse_constant=_reject_constant,
    )


def _signature(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _capture_bytes(path: Path) -> bytes:
    candidate = path.expanduser()
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(candidate, flags)
    except OSError as exc:
        raise ValueError(f"input is not a regular file: {candidate}") from exc
    try:
        before = os.fstat(descriptor)
        linked = os.stat(candidate, follow_symlinks=False)
        if (
            not stat.S_ISREG(before.st_mode)
            or not stat.S_ISREG(linked.st_mode)
            or (before.st_dev, before.st_ino) != (linked.st_dev, linked.st_ino)
        ):
            raise ValueError(f"input is not a regular file: {candidate}")
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        after = os.fstat(descriptor)
        linked_after = os.stat(candidate, follow_symlinks=False)
        if _signature(before) != _signature(after) or _signature(before) != _signature(
            linked_after
        ):
            raise ValueError("input changed while it was being captured")
        return b"".join(chunks)
    except OSError as exc:
        raise ValueError("input changed while it was being captured") from exc
    finally:
        os.close(descriptor)


def _rows(path: Path) -> tuple[list[dict[str, Any]], str]:
    raw_bytes = _capture_bytes(path)
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("input must be UTF-8") from exc
    if path.suffix.lower() == ".jsonl":
        raw = [_loads(line) for line in text.splitlines() if line.strip()]
    else:
        raw = _loads(text)
    if not isinstance(raw, list) or any(not isinstance(row, dict) for row in raw):
        raise ValueError("input must be a JSON array or JSONL objects")
    return raw, hashlib.sha256(raw_bytes).hexdigest()


def _inside(path: Path, root: Path) -> bool:
    return path == root or path.is_relative_to(root)


def _database(args: argparse.Namespace, settings: AppSettings) -> Path:
    project_root = settings.paths.project_root.resolve(strict=False)
    data_root = settings.paths.data_root.resolve(strict=False)
    if _inside(data_root, project_root) or _inside(project_root, data_root):
        raise ValueError("project and data roots must not overlap")
    candidate = (
        args.db.expanduser().resolve(strict=False)
        if args.db
        else settings.paths.database.resolve(strict=False)
    )
    if not _inside(candidate, data_root) or _inside(candidate, project_root):
        raise ValueError("database override must stay inside the configured data root")
    return candidate


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
    append.add_argument("--publication-evidence", type=Path)
    append.add_argument("--source-url")
    append.add_argument("--available-at")
    append.add_argument("--retrieved-at")
    append.add_argument("--revision-id")
    append.add_argument("--source-family-id")
    append.add_argument("--provider-id")
    append.add_argument("--subject-id")
    append.add_argument("--code-sha256")
    append.add_argument("--config-sha256")
    append.add_argument("--canonical-owner")
    append.add_argument("--contract-version")
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
    rows, input_sha256 = _rows(args.input)
    if args.source_sha256 != input_sha256:
        raise ValueError("source_sha256 does not match the captured input bytes")
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
    controlled_fields = (
        "publication_evidence",
        "source_url",
        "available_at",
        "retrieved_at",
        "revision_id",
        "source_family_id",
        "provider_id",
        "subject_id",
        "code_sha256",
        "config_sha256",
        "canonical_owner",
        "contract_version",
    )
    missing = tuple(name for name in controlled_fields if getattr(args, name) is None)
    if missing:
        raise ValueError(f"controlled append is missing required fields: {', '.join(missing)}")
    source_receipt = capture_source_file(
        args.input,
        publication_evidence_path=args.publication_evidence,
        source_url=args.source_url,
        available_at=datetime.fromisoformat(args.available_at),
        retrieved_at=datetime.fromisoformat(args.retrieved_at),
        revision_id=args.revision_id,
        source_family_id=args.source_family_id,
        provider_id=args.provider_id,
        subject_id=args.subject_id,
    )
    if source_receipt.source.content_sha256 != input_sha256:
        raise ValueError("captured source changed after row parsing")
    result = append_rows(
        db_path,
        schema=args.schema,
        table=args.table,
        natural_keys=keys,
        rows=rows,
        batch_id=args.batch_id,
        source_identity=source_receipt.source,
        code_sha256=args.code_sha256,
        config_sha256=args.config_sha256,
        canonical_owner=args.canonical_owner,
        contract_version=args.contract_version,
        max_rows=settings.writer.max_rows_per_batch,
        lock_timeout_seconds=settings.writer.lock_timeout_seconds,
    )
    _print(result.to_dict())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
