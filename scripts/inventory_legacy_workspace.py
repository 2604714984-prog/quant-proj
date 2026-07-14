from __future__ import annotations

import argparse
import hashlib
import json
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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
        "origin": remote or None,
        "dirty_entry_count": len(status),
        "is_linked_worktree": git_dir != common_dir,
        "git_common_dir": str(common_dir),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _data_record(path: Path, hash_database: bool) -> dict[str, Any]:
    mode = stat.S_IMODE(path.stat().st_mode)
    record: dict[str, Any] = {
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "mode": f"{mode:04o}",
    }
    if hash_database:
        record["sha256"] = _sha256(path)
    return record


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
