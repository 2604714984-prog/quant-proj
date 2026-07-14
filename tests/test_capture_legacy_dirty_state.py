from __future__ import annotations

import json
import subprocess
import tarfile
from pathlib import Path

from scripts.capture_legacy_dirty_state import capture_repo


def _git(path: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True)


def test_capture_preserves_tracked_patch_and_untracked_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    output = tmp_path / "output"
    repo.mkdir()
    output.mkdir(mode=0o700)
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.invalid")
    (repo / "tracked.txt").write_text("before\n", encoding="utf-8")
    _git(repo, "add", "tracked.txt")
    _git(repo, "commit", "-m", "initial")
    (repo / "tracked.txt").write_text("after\n", encoding="utf-8")
    (repo / "new.txt").write_text("new\n", encoding="utf-8")

    receipt = capture_repo(repo, output)
    captured = output / "repo"

    assert receipt["tracked_patch_sha256"]
    assert receipt["untracked_archive_sha256"]
    assert "new.txt" in receipt["untracked_files"]
    assert json.loads((captured / "identity.json").read_text())["head"] == receipt["head"]
    assert "after" in (captured / "tracked.patch").read_text()
    with tarfile.open(captured / "untracked.tar.gz", "r:gz") as archive:
        assert archive.extractfile("new.txt").read() == b"new\n"
