from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import stat
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit


def _git(path: Path, *args: str, text: bool = True) -> str | bytes:
    result = subprocess.run(
        ["git", "-C", str(path), *args],
        check=True,
        capture_output=True,
        text=text,
    )
    return result.stdout


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _safe_name(path: Path) -> str:
    return path.name.replace("/", "_").replace("\\", "_")


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
    try:
        port = parsed.port
    except ValueError:
        port = None
    netloc = f"{hostname}:{port}" if port is not None else hostname
    sanitized = urlunsplit((parsed.scheme, netloc, parsed.path, "", ""))
    return sanitized or None


def _write_private(path: Path, value: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    complete = False
    try:
        remaining = memoryview(value)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("private write made no progress")
            remaining = remaining[written:]
        os.fsync(descriptor)
        complete = True
    finally:
        os.close(descriptor)
        if not complete:
            path.unlink(missing_ok=True)


def _capture_regular(path: Path, root: Path) -> tuple[bytes, os.stat_result]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ValueError(f"untracked path is not a regular file: {path}") from exc
    try:
        before = os.fstat(descriptor)
        linked = os.stat(path, follow_symlinks=False)
        resolved = Path(os.path.realpath(path))
        if (
            not resolved.is_relative_to(root)
            or not stat.S_ISREG(before.st_mode)
            or not stat.S_ISREG(linked.st_mode)
            or (before.st_dev, before.st_ino) != (linked.st_dev, linked.st_ino)
        ):
            raise ValueError(f"unsafe untracked path: {path}")
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        after = os.fstat(descriptor)
        linked_after = os.stat(path, follow_symlinks=False)
        before_signature = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        if before_signature != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ) or before_signature != (
            linked_after.st_dev,
            linked_after.st_ino,
            linked_after.st_size,
            linked_after.st_mtime_ns,
            linked_after.st_ctime_ns,
        ):
            raise ValueError(f"untracked path changed during capture: {path}")
        return b"".join(chunks), before
    except OSError as exc:
        raise ValueError(f"untracked path changed during capture: {path}") from exc
    finally:
        os.close(descriptor)


def _repo_state(path: Path) -> dict[str, str | bytes]:
    return {
        "branch": str(_git(path, "branch", "--show-current")).strip(),
        "head": str(_git(path, "rev-parse", "HEAD")).strip(),
        "tree": str(_git(path, "rev-parse", "HEAD^{tree}")).strip(),
        "status": bytes(
            _git(path, "status", "--porcelain=v1", "-z", text=False)
        ),
        "patch": bytes(_git(path, "diff", "--binary", "HEAD", text=False)),
        "untracked": bytes(
            _git(path, "ls-files", "--others", "--exclude-standard", "-z", text=False)
        ),
    }


def _untracked_names(value: bytes) -> list[str]:
    return [
        item.decode("utf-8", errors="strict")
        for item in value.split(b"\0")
        if item
    ]


def _state_fingerprint(
    state: dict[str, str | bytes], untracked_hashes: dict[str, str]
) -> str:
    payload = {
        "branch": state["branch"],
        "head": state["head"],
        "tree": state["tree"],
        "status_sha256": _sha256_bytes(bytes(state["status"])),
        "patch_sha256": _sha256_bytes(bytes(state["patch"])),
        "untracked_list_sha256": _sha256_bytes(bytes(state["untracked"])),
        "untracked_files": untracked_hashes,
    }
    return _sha256_bytes(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def capture_repo(path: Path, output_root: Path) -> dict[str, Any]:
    path = path.resolve()
    before = _repo_state(path)
    if not before["status"]:
        raise ValueError(f"repository is clean: {path}")

    target = output_root / _safe_name(path)
    if target.exists():
        raise FileExistsError(f"capture target already exists: {target}")
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{_safe_name(path)}.capture-", dir=output_root)
    )
    os.chmod(temporary, 0o700)
    published = False
    try:
        patch = bytes(before["patch"])
        if patch:
            _write_private(temporary / "tracked.patch", patch)

        untracked = _untracked_names(bytes(before["untracked"]))
        hashes: dict[str, str] = {}
        archive_buffer = io.BytesIO()
        with tarfile.open(fileobj=archive_buffer, mode="w:gz") as archive:
            for relative in untracked:
                relative_path = Path(relative)
                if relative_path.is_absolute() or ".." in relative_path.parts:
                    raise ValueError(f"unsafe untracked path: {relative}")
                source = path / relative
                value, source_stat = _capture_regular(source, path)
                hashes[relative] = _sha256_bytes(value)
                member = tarfile.TarInfo(relative)
                member.size = len(value)
                member.mode = stat.S_IMODE(source_stat.st_mode)
                member.mtime = int(source_stat.st_mtime)
                archive.addfile(member, io.BytesIO(value))
        archive_value = archive_buffer.getvalue()
        if untracked:
            _write_private(temporary / "untracked.tar.gz", archive_value)

        after = _repo_state(path)
        post_hashes = {
            relative: _sha256_bytes(_capture_regular(path / relative, path)[0])
            for relative in _untracked_names(bytes(after["untracked"]))
        }
        if before != after or hashes != post_hashes:
            raise ValueError("repository changed during capture")
        fingerprint = _state_fingerprint(before, hashes)
        status = [
            item.decode("utf-8", errors="strict")
            for item in bytes(before["status"]).split(b"\0")
            if item
        ]
        remote = str(
            subprocess.run(
                ["git", "-C", str(path), "remote", "get-url", "origin"],
                check=False,
                capture_output=True,
                text=True,
            ).stdout
        )
        identity = {
            "schema_version": 2,
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_path": str(path),
            "branch": before["branch"],
            "head": before["head"],
            "tree": before["tree"],
            "origin": _sanitize_origin(remote),
            "status": status,
            "state_fingerprint_sha256": fingerprint,
            "tracked_patch_sha256": _sha256_bytes(patch) if patch else None,
            "untracked_archive_sha256": (
                _sha256_bytes(archive_value) if untracked else None
            ),
            "untracked_files": hashes,
        }
        identity_value = (
            json.dumps(identity, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        _write_private(temporary / "identity.json", identity_value)
        if target.exists():
            raise FileExistsError(f"capture target already exists: {target}")
        os.rename(temporary, target)
        published = True
        _fsync_directory(output_root)
        return identity
    finally:
        if not published:
            shutil.rmtree(temporary, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    repositories = [
        Path(item["path"])
        for item in inventory["repositories"]
        if item["dirty_entry_count"] > 0
    ]
    args.output.mkdir(parents=True, mode=0o700)
    os.chmod(args.output, 0o700)
    if any(args.output.iterdir()):
        raise ValueError("output directory must be empty")
    receipts = [capture_repo(path, args.output) for path in repositories]
    summary = {
        "schema_version": 1,
        "repository_count": len(receipts),
        "repositories": [
            {
                "source_path": item["source_path"],
                "head": item["head"],
                "tree": item["tree"],
            }
            for item in receipts
        ],
    }
    _write_private(
        args.output / "SUMMARY.json",
        (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
