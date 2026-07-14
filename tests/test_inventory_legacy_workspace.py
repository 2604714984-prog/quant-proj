from __future__ import annotations

import json
import subprocess
from pathlib import Path

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
