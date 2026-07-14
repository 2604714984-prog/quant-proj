from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit


def _git(path: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), *args],
        check=check,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _is_repo(path: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def _sanitize_origin(value: str) -> str | None:
    origin = value.strip()
    if not origin:
        return None
    if "://" not in origin:
        origin = origin.split("#", 1)[0].split("?", 1)[0]
        if "@" in origin and ":" in origin.split("@", 1)[1]:
            origin = origin.split("@", 1)[1]
        return origin or None
    parsed = urlsplit(origin)
    hostname = parsed.hostname or ""
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    netloc = hostname
    try:
        port = parsed.port
    except ValueError:
        port = None
    if port is not None:
        netloc = f"{netloc}:{port}"
    sanitized = urlunsplit((parsed.scheme, netloc, parsed.path, "", ""))
    return sanitized or None


def _repo_record(path: Path) -> dict[str, Any]:
    status = _git(path, "status", "--porcelain=v1").splitlines()
    remote = _git(path, "remote", "get-url", "origin", check=False)
    common_dir = Path(
        _git(path, "rev-parse", "--path-format=absolute", "--git-common-dir")
    )
    git_dir = Path(_git(path, "rev-parse", "--absolute-git-dir"))
    return {
        "path": str(path),
        "branch": _git(path, "branch", "--show-current"),
        "head": _git(path, "rev-parse", "HEAD"),
        "tree": _git(path, "rev-parse", "HEAD^{tree}"),
        "origin": _sanitize_origin(remote),
        "dirty_entry_count": len(status),
        "is_linked_worktree": git_dir != common_dir,
        "git_common_dir": str(common_dir),
    }


def _signature(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _sha256(descriptor: int) -> str:
    digest = hashlib.sha256()
    while chunk := os.read(descriptor, 8 * 1024 * 1024):
        digest.update(chunk)
    return digest.hexdigest()


def _data_record(path: Path, hash_database: bool) -> dict[str, Any]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ValueError(f"database candidate is not a regular file: {path}") from exc
    try:
        before = os.fstat(descriptor)
        linked = os.stat(path, follow_symlinks=False)
        if (
            not stat.S_ISREG(before.st_mode)
            or not stat.S_ISREG(linked.st_mode)
            or (before.st_dev, before.st_ino) != (linked.st_dev, linked.st_ino)
        ):
            raise ValueError(f"database candidate is not a regular file: {path}")
        record: dict[str, Any] = {
            "path": str(path),
            "size_bytes": before.st_size,
            "mode": f"{stat.S_IMODE(before.st_mode):04o}",
        }
        if hash_database:
            record["sha256"] = _sha256(descriptor)
        after = os.fstat(descriptor)
        linked_after = os.stat(path, follow_symlinks=False)
        if _signature(before) != _signature(after) or _signature(before) != _signature(
            linked_after
        ):
            raise ValueError(f"database candidate changed during inventory: {path}")
        return record
    except OSError as exc:
        raise ValueError(f"database candidate changed during inventory: {path}") from exc
    finally:
        os.close(descriptor)


def build_inventory(workspace: Path, hash_database: bool) -> dict[str, Any]:
    repositories = []
    for path in sorted(workspace.iterdir()):
        if path.name == ".quant-rebuild" or not path.is_dir():
            continue
        if _is_repo(path):
            repositories.append(_repo_record(path))

    database_candidates = []
    for root_name in ("quant_data", "quant-data"):
        root = workspace / root_name
        if root.is_dir():
            for path in sorted(root.glob("*.duckdb")):
                database_candidates.append(_data_record(path, hash_database))

    linked = sum(item["is_linked_worktree"] for item in repositories)
    dirty = sum(item["dirty_entry_count"] > 0 for item in repositories)
    return {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "workspace": str(workspace),
        "target_layout": {
            "active_repository": str(workspace / "quant-proj"),
            "external_data_root": str(workspace / "quant-data"),
        },
        "summary": {
            "top_level_git_worktrees": len(repositories),
            "linked_top_level_worktrees": linked,
            "dirty_top_level_worktrees": dirty,
        },
        "repositories": repositories,
        "database_candidates": database_candidates,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--hash-database", action="store_true")
    args = parser.parse_args()

    inventory = build_inventory(args.workspace.resolve(), args.hash_database)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(inventory, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
