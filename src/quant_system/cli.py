"""One small command line for local data access and append-only imports."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any, Iterator

from . import __version__
from .config import AppSettings, load_settings
from .data import (
    append_rows,
    capture_file_digest,
    capture_source_file,
    database_info,
    query,
)


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


@contextmanager
def _pinned_input(path: Path) -> Iterator[int]:
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
        yield descriptor
        after = os.fstat(descriptor)
        linked_after = os.stat(candidate, follow_symlinks=False)
        if _signature(before) != _signature(after) or _signature(before) != _signature(
            linked_after
        ):
            raise ValueError("input changed while it was being captured")
    except OSError as exc:
        raise ValueError("input changed while it was being captured") from exc
    finally:
        os.close(descriptor)


def _capture_bytes(path: Path, *, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    byte_count = 0
    with _pinned_input(path) as descriptor:
        while chunk := os.read(descriptor, min(64 * 1024, max_bytes + 1 - byte_count)):
            byte_count += len(chunk)
            if byte_count > max_bytes:
                raise ValueError(f"input exceeds byte limit: {max_bytes}")
            chunks.append(chunk)
    return b"".join(chunks)


def _jsonl_rows(
    path: Path,
    *,
    max_bytes: int,
    max_rows: int,
) -> tuple[list[dict[str, Any]], str]:
    rows: list[dict[str, Any]] = []
    digest = hashlib.sha256()
    buffer = b""
    byte_count = 0

    def add_line(raw_line: bytes) -> None:
        if not raw_line.strip():
            return
        try:
            value = _loads(raw_line.decode("utf-8"))
        except UnicodeDecodeError as exc:
            raise ValueError("input must be UTF-8") from exc
        if not isinstance(value, dict):
            raise ValueError("input must be a JSON array or JSONL objects")
        rows.append(value)
        if len(rows) > max_rows:
            raise ValueError(f"input exceeds row limit: {max_rows}")

    with _pinned_input(path) as descriptor:
        while chunk := os.read(descriptor, min(64 * 1024, max_bytes + 1 - byte_count)):
            byte_count += len(chunk)
            if byte_count > max_bytes:
                raise ValueError(f"input exceeds byte limit: {max_bytes}")
            digest.update(chunk)
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                add_line(line)
        add_line(buffer)
    return rows, digest.hexdigest()


def _rows(
    path: Path,
    *,
    max_bytes: int,
    max_rows: int,
) -> tuple[list[dict[str, Any]], str]:
    if path.suffix.lower() == ".jsonl":
        return _jsonl_rows(path, max_bytes=max_bytes, max_rows=max_rows)
    raw_bytes = _capture_bytes(path, max_bytes=max_bytes)
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("input must be UTF-8") from exc
    raw = _loads(text)
    if not isinstance(raw, list) or any(not isinstance(row, dict) for row in raw):
        raise ValueError("input must be a JSON array or JSONL objects")
    if len(raw) > max_rows:
        raise ValueError(f"input exceeds row limit: {max_rows}")
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


def _binding_status(settings: AppSettings) -> str:
    return "EXPLICIT_DATA_ROOT" if settings.paths.data_root_bound else "UNBOUND_DATA_ROOT"


def _package_code_sha256() -> str:
    package_root = Path(__file__).resolve().parent
    files = tuple(sorted(package_root.rglob("*.py")))
    if not files:
        raise ValueError("installed package contains no Python code artifacts")
    entries = []
    for path in files:
        digest, byte_count = capture_file_digest(path)
        entries.append((path.relative_to(package_root).as_posix(), digest, byte_count))
    encoded = json.dumps(
        {"files": entries, "version": 1},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _settings_sha256(settings: AppSettings) -> str:
    config_file_sha256 = None
    if settings.config_path.is_file():
        config_file_sha256 = capture_file_digest(settings.config_path)[0]
    payload = {
        "config_file_sha256": config_file_sha256,
        "data_root": str(settings.paths.data_root),
        "data_root_bound": settings.paths.data_root_bound,
        "database": str(settings.paths.database),
        "database_filename": settings.database.filename,
        "lock_timeout_seconds": settings.writer.lock_timeout_seconds,
        "max_input_bytes": settings.writer.max_input_bytes,
        "max_rows_per_batch": settings.writer.max_rows_per_batch,
        "target_data_grades": settings.writer.target_data_grades,
        "version": 1,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


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
                "data_root_binding": _binding_status(settings),
                "database": str(settings.paths.database),
                "database_exists": settings.paths.database.exists(),
                "config": str(settings.config_path),
            }
        )
        return 0
    db_path = _database(args, settings)
    if args.data_command == "inspect":
        _print(
            database_info(db_path, include_hash=args.hash).to_dict()
            | {"data_root_binding": _binding_status(settings)}
        )
        return 0
    if args.data_command == "query":
        _print(
            query(db_path, args.sql, max_rows=args.max_rows).to_dict()
            | {"data_root_binding": _binding_status(settings)}
        )
        return 0
    if args.execute and not settings.paths.data_root_bound:
        raise ValueError(
            "append --execute requires QUANT_DATA_ROOT or configured paths.data_root"
        )
    target = f"{args.schema}.{args.table}"
    minimum_capture_level = dict(settings.writer.target_data_grades).get(target)
    if args.execute and minimum_capture_level is None:
        raise ValueError(
            f"append --execute requires writer.target_data_grades for {target}"
        )
    rows, input_sha256 = _rows(
        args.input,
        max_bytes=settings.writer.max_input_bytes,
        max_rows=settings.writer.max_rows_per_batch,
    )
    if args.source_sha256 != input_sha256:
        raise ValueError("source_sha256 does not match the captured input bytes")
    keys = tuple(key.strip() for key in args.keys.split(",") if key.strip())
    if not args.execute:
        _print(
            {
                "status": "DRY_RUN",
                "writes": False,
                "data_root_binding": _binding_status(settings),
                "database": str(db_path),
                "target": f"{args.schema}.{args.table}",
                "minimum_capture_level": minimum_capture_level,
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
        code_sha256=_package_code_sha256(),
        config_sha256=_settings_sha256(settings),
        contract_version=args.contract_version,
        minimum_capture_level=minimum_capture_level,
        max_rows=settings.writer.max_rows_per_batch,
        lock_timeout_seconds=settings.writer.lock_timeout_seconds,
    )
    _print(result.to_dict())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
