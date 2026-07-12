#!/usr/bin/env python3
"""Create one lock-coordinated byte-identical central DuckDB backup."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import os
from pathlib import Path
import shutil
import stat


class BackupError(RuntimeError):
    """Raised when any recorded-execution precondition fails."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def regular_file_identity(path: Path, *, role: str, expected_mode: int = 0o600) -> os.stat_result:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise BackupError(f"{role}_must_be_regular_non_symlink")
    if stat.S_IMODE(info.st_mode) != expected_mode:
        raise BackupError(f"{role}_mode_mismatch")
    if info.st_nlink != 1:
        raise BackupError(f"{role}_multiple_links_rejected")
    return info


def backup(
    *,
    database: Path,
    backup_path: Path,
    lock_path: Path,
    expected_sha256: str,
    expected_bytes: int,
    allow_write: bool,
) -> dict[str, object]:
    if not allow_write:
        raise BackupError("allow_write_required")
    if backup_path.exists() or backup_path.is_symlink():
        raise BackupError("backup_path_exists")
    if backup_path.parent.resolve(strict=True) != backup_path.parent.absolute():
        raise BackupError("backup_parent_resolution_mismatch")
    parent_info = backup_path.parent.lstat()
    if stat.S_ISLNK(parent_info.st_mode) or stat.S_IMODE(parent_info.st_mode) != 0o700:
        raise BackupError("backup_parent_must_be_mode_0700_non_symlink")

    lock_info = regular_file_identity(lock_path, role="writer_lock")
    before = regular_file_identity(database, role="database")
    if before.st_size != expected_bytes:
        raise BackupError("source_size_drift")

    partial = backup_path.with_name(f".{backup_path.name}.partial.{os.getpid()}")
    if partial.exists() or partial.is_symlink():
        raise BackupError("partial_path_exists")

    with lock_path.open("r+b") as lock_handle:
        if os.fstat(lock_handle.fileno()).st_ino != lock_info.st_ino:
            raise BackupError("writer_lock_identity_drift")
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise BackupError("writer_lock_unavailable") from exc
        try:
            source_hash = sha256_file(database)
            if source_hash != expected_sha256:
                raise BackupError("source_hash_drift")
            current = regular_file_identity(database, role="database")
            if (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns) != (
                before.st_dev,
                before.st_ino,
                before.st_size,
                before.st_mtime_ns,
            ):
                raise BackupError("source_identity_drift_before_copy")

            try:
                shutil.copyfile(database, partial, follow_symlinks=False)
                os.chmod(partial, 0o600)
                with partial.open("rb") as handle:
                    os.fsync(handle.fileno())
                copied = regular_file_identity(partial, role="partial_backup")
                if copied.st_size != expected_bytes or sha256_file(partial) != expected_sha256:
                    raise BackupError("backup_hash_or_size_mismatch")
                os.replace(partial, backup_path)
                directory_fd = os.open(backup_path.parent, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            finally:
                if partial.exists() and not partial.is_symlink():
                    partial.unlink()

            final = regular_file_identity(backup_path, role="backup")
            after = regular_file_identity(database, role="database")
            if (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) != (
                before.st_dev,
                before.st_ino,
                before.st_size,
                before.st_mtime_ns,
            ):
                raise BackupError("source_identity_drift_after_copy")
            if sha256_file(database) != expected_sha256:
                raise BackupError("source_hash_drift_after_copy")
            return {
                "status": "PASS_BYTE_IDENTICAL",
                "database": str(database),
                "backup": str(backup_path),
                "sha256": expected_sha256,
                "bytes": final.st_size,
                "mode": f"{stat.S_IMODE(final.st_mode):04o}",
                "writer_lock_acquired": True,
                "source_unchanged": True,
                "network_calls": 0,
                "database_writes": 0,
                "strategy_process_invocations": 0,
            }
        finally:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--lock-file", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--expected-bytes", type=int, required=True)
    parser.add_argument("--allow-write", action="store_true")
    args = parser.parse_args()
    result = backup(
        database=args.database.absolute(),
        backup_path=args.backup.absolute(),
        lock_path=args.lock_file.absolute(),
        expected_sha256=args.expected_sha256,
        expected_bytes=args.expected_bytes,
        allow_write=args.allow_write,
    )
    for key in sorted(result):
        print(f"{key}={result[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
