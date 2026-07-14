from __future__ import annotations

import json
import os
import subprocess
import tarfile
from pathlib import Path

import pytest

import scripts.capture_legacy_dirty_state as capture_module
from scripts.capture_legacy_dirty_state import _write_private, capture_repo


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

    assert receipt["schema_version"] == 2
    assert len(receipt["state_fingerprint_sha256"]) == 64
    assert receipt["tracked_patch_sha256"]
    assert receipt["untracked_archive_sha256"]
    assert "new.txt" in receipt["untracked_files"]
    assert json.loads((captured / "identity.json").read_text())["head"] == receipt["head"]
    assert "after" in (captured / "tracked.patch").read_text()
    with tarfile.open(captured / "untracked.tar.gz", "r:gz") as archive:
        assert archive.extractfile("new.txt").read() == b"new\n"


def test_private_write_handles_short_writes_and_fsyncs(
    tmp_path: Path, monkeypatch
) -> None:
    target = tmp_path / "private.bin"
    value = b"0123456789"
    real_write = capture_module.os.write
    real_fsync = capture_module.os.fsync
    fsynced: list[int] = []

    def short_write(descriptor: int, chunk: bytes | memoryview) -> int:
        return real_write(descriptor, bytes(chunk[:2]))

    def recording_fsync(descriptor: int) -> None:
        fsynced.append(descriptor)
        real_fsync(descriptor)

    monkeypatch.setattr(capture_module.os, "write", short_write)
    monkeypatch.setattr(capture_module.os, "fsync", recording_fsync)
    _write_private(target, value)

    assert target.read_bytes() == value
    assert fsynced
    assert oct(target.stat().st_mode & 0o777) == "0o600"


def test_capture_rejects_untracked_path_replacement(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    output = tmp_path / "output"
    moved = tmp_path / "moved.txt"
    repo.mkdir()
    output.mkdir(mode=0o700)
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.invalid")
    (repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    _git(repo, "add", "tracked.txt")
    _git(repo, "commit", "-m", "initial")
    untracked = repo / "new.txt"
    untracked.write_text("original\n", encoding="utf-8")
    original_inode = untracked.stat().st_ino
    real_read = capture_module.os.read
    replaced = False

    def replacing_read(descriptor: int, size: int) -> bytes:
        nonlocal replaced
        if not replaced and os.fstat(descriptor).st_ino == original_inode:
            replaced = True
            os.replace(untracked, moved)
            untracked.write_text("replacement\n", encoding="utf-8")
        return real_read(descriptor, size)

    monkeypatch.setattr(capture_module.os, "read", replacing_read)
    with pytest.raises(ValueError, match="changed during capture"):
        capture_repo(repo, output)
    assert not (output / "repo").exists()
    assert list(output.iterdir()) == []


def test_capture_rejects_concurrent_commit_and_removes_partial_output(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    output = tmp_path / "output"
    repo.mkdir()
    output.mkdir(mode=0o700)
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.invalid")
    tracked = repo / "tracked.txt"
    tracked.write_text("before\n", encoding="utf-8")
    _git(repo, "add", "tracked.txt")
    _git(repo, "commit", "-m", "initial")
    tracked.write_text("after\n", encoding="utf-8")
    (repo / "new.txt").write_text("new\n", encoding="utf-8")
    real_capture = capture_module._capture_regular
    committed = False

    def capture_then_commit(path: Path, root: Path):
        nonlocal committed
        captured = real_capture(path, root)
        if not committed:
            committed = True
            _git(repo, "add", "-A")
            _git(repo, "commit", "-m", "concurrent")
        return captured

    monkeypatch.setattr(capture_module, "_capture_regular", capture_then_commit)
    with pytest.raises(ValueError, match="repository changed during capture"):
        capture_repo(repo, output)

    assert not (output / "repo").exists()
    assert list(output.iterdir()) == []


def test_capture_redacts_credentials_from_origin(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    output = tmp_path / "output"
    repo.mkdir()
    output.mkdir(mode=0o700)
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.invalid")
    tracked = repo / "tracked.txt"
    tracked.write_text("before\n", encoding="utf-8")
    _git(repo, "add", "tracked.txt")
    _git(repo, "commit", "-m", "initial")
    _git(
        repo,
        "remote",
        "add",
        "origin",
        "https://user:secret@example.invalid/owner/repo.git?token=secret#fragment",
    )
    tracked.write_text("after\n", encoding="utf-8")

    receipt = capture_repo(repo, output)
    identity_text = (output / "repo" / "identity.json").read_text(encoding="utf-8")

    assert receipt["origin"] == "https://example.invalid/owner/repo.git"
    assert "secret" not in identity_text
