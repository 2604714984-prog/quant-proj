from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

import scripts.inventory_legacy_workspace as inventory_module
from scripts.inventory_legacy_workspace import build_inventory


def _git(path: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True)


def test_inventory_records_git_identity_without_reading_file_contents(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.invalid")
    (repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    _git(repo, "add", "tracked.txt")
    _git(repo, "commit", "-m", "initial")

    inventory = build_inventory(tmp_path, hash_database=False)

    assert inventory["summary"]["top_level_git_worktrees"] == 1
    record = inventory["repositories"][0]
    assert record["branch"] == "main"
    assert len(record["head"]) == 40
    assert len(record["tree"]) == 40
    assert record["dirty_entry_count"] == 0
    assert record["git_common_dir"] == str(repo / ".git")


def test_inventory_distinguishes_linked_worktree_from_main_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    worktree = tmp_path / "linked"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.invalid")
    (repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    _git(repo, "add", "tracked.txt")
    _git(repo, "commit", "-m", "initial")
    _git(repo, "worktree", "add", "-b", "linked", str(worktree), "HEAD")

    inventory = build_inventory(tmp_path, hash_database=False)
    records = {Path(item["path"]).name: item for item in inventory["repositories"]}

    assert records["repo"]["is_linked_worktree"] is False
    assert records["linked"]["is_linked_worktree"] is True
    assert records["linked"]["git_common_dir"] == str(repo / ".git")


def test_inventory_output_is_json_serializable(tmp_path: Path) -> None:
    assert json.loads(json.dumps(build_inventory(tmp_path, False)))["schema_version"] == 1


def test_inventory_redacts_origin_userinfo_query_and_fragment(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.invalid")
    (repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    _git(repo, "add", "tracked.txt")
    _git(repo, "commit", "-m", "initial")
    _git(
        repo,
        "remote",
        "add",
        "origin",
        "https://user:secret@example.invalid/owner/repo.git?token=secret#fragment",
    )

    record = build_inventory(tmp_path, hash_database=False)["repositories"][0]

    assert record["origin"] == "https://example.invalid/owner/repo.git"
    assert "secret" not in json.dumps(record)


def test_inventory_captures_database_metadata_and_hash_from_one_file(
    tmp_path: Path,
) -> None:
    root = tmp_path / "quant-data"
    root.mkdir()
    database = root / "quant_research.duckdb"
    value = b"duckdb-fixture"
    database.write_bytes(value)
    database.chmod(0o600)

    record = build_inventory(tmp_path, hash_database=True)["database_candidates"][0]

    assert record == {
        "path": str(database),
        "size_bytes": len(value),
        "mode": "0600",
        "sha256": hashlib.sha256(value).hexdigest(),
    }


def test_inventory_rejects_database_path_replacement(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "quant-data"
    root.mkdir()
    database = root / "quant_research.duckdb"
    moved = root / "moved.duckdb"
    database.write_bytes(b"original-database")
    original_inode = database.stat().st_ino
    real_read = inventory_module.os.read
    replaced = False

    def replacing_read(descriptor: int, size: int) -> bytes:
        nonlocal replaced
        if not replaced and os.fstat(descriptor).st_ino == original_inode:
            replaced = True
            os.replace(database, moved)
            database.write_bytes(b"replacement-database")
        return real_read(descriptor, size)

    monkeypatch.setattr(inventory_module.os, "read", replacing_read)
    with pytest.raises(ValueError, match="changed during inventory"):
        build_inventory(tmp_path, hash_database=True)
