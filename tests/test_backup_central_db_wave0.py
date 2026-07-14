from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from scripts.backup_central_db_wave0 import BackupError, backup


def make_paths(tmp_path: Path) -> tuple[Path, Path, Path, str]:
    os.chmod(tmp_path, 0o700)
    database = tmp_path / "central.duckdb"
    database.write_bytes(b"duckdb-fixture\n" * 1024)
    os.chmod(database, 0o600)
    lock = tmp_path / "central.duckdb.writer.lock"
    lock.touch(mode=0o600)
    destination = tmp_path / "backups"
    destination.mkdir(mode=0o700)
    backup_path = destination / "before.duckdb"
    digest = hashlib.sha256(database.read_bytes()).hexdigest()
    return database, lock, backup_path, digest


def invoke(tmp_path: Path, *, allow_write: bool = True) -> dict[str, object]:
    database, lock, backup_path, digest = make_paths(tmp_path)
    return backup(
        database=database,
        backup_path=backup_path,
        lock_path=lock,
        expected_sha256=digest,
        expected_bytes=database.stat().st_size,
        allow_write=allow_write,
    )


def test_creates_byte_identical_mode_0600_backup(tmp_path: Path) -> None:
    result = invoke(tmp_path)
    backup_path = Path(str(result["backup"]))
    assert result["status"] == "PASS_BYTE_IDENTICAL"
    assert result["source_unchanged"] is True
    assert backup_path.read_bytes() == (tmp_path / "central.duckdb").read_bytes()
    assert backup_path.stat().st_mode & 0o777 == 0o600


def test_allow_write_is_required(tmp_path: Path) -> None:
    with pytest.raises(BackupError, match="allow_write_required"):
        invoke(tmp_path, allow_write=False)


def test_existing_backup_is_rejected(tmp_path: Path) -> None:
    database, lock, backup_path, digest = make_paths(tmp_path)
    backup_path.write_bytes(b"existing")
    with pytest.raises(BackupError, match="backup_path_exists"):
        backup(database=database, backup_path=backup_path, lock_path=lock, expected_sha256=digest, expected_bytes=database.stat().st_size, allow_write=True)


def test_source_hash_drift_is_rejected_without_backup(tmp_path: Path) -> None:
    database, lock, backup_path, _ = make_paths(tmp_path)
    with pytest.raises(BackupError, match="source_hash_drift"):
        backup(database=database, backup_path=backup_path, lock_path=lock, expected_sha256="0" * 64, expected_bytes=database.stat().st_size, allow_write=True)
    assert not backup_path.exists()


def test_database_symlink_is_rejected(tmp_path: Path) -> None:
    database, lock, backup_path, digest = make_paths(tmp_path)
    link = tmp_path / "database-link.duckdb"
    link.symlink_to(database)
    with pytest.raises(BackupError, match="database_must_be_regular_non_symlink"):
        backup(database=link, backup_path=backup_path, lock_path=lock, expected_sha256=digest, expected_bytes=database.stat().st_size, allow_write=True)
