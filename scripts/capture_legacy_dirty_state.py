from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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


def _write_private(path: Path, value: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(descriptor, value)
    finally:
        os.close(descriptor)


def capture_repo(path: Path, output_root: Path) -> dict[str, Any]:
    path = path.resolve()
    status = str(_git(path, "status", "--porcelain=v1")).splitlines()
    if not status:
        raise ValueError(f"repository is clean: {path}")

    target = output_root / _safe_name(path)
    target.mkdir(mode=0o700)

    patch = bytes(_git(path, "diff", "--binary", "HEAD", text=False))
    if patch:
        _write_private(target / "tracked.patch", patch)

    raw_untracked = bytes(
        _git(path, "ls-files", "--others", "--exclude-standard", "-z", text=False)
    )
    untracked = [
        item.decode("utf-8", errors="strict")
        for item in raw_untracked.split(b"\0")
        if item
    ]
    hashes: dict[str, str] = {}
    archive_buffer = io.BytesIO()
    with tarfile.open(fileobj=archive_buffer, mode="w:gz") as archive:
        for relative in untracked:
            source = path / relative
            resolved = source.resolve()
            if not resolved.is_relative_to(path) or source.is_symlink():
                raise ValueError(f"unsafe untracked path: {relative}")
            if not source.is_file():
                raise ValueError(f"untracked path is not a regular file: {relative}")
            value = source.read_bytes()
            hashes[relative] = _sha256_bytes(value)
            archive.add(source, arcname=relative, recursive=False)
    archive_value = archive_buffer.getvalue()
    if untracked:
        _write_private(target / "untracked.tar.gz", archive_value)

    identity = {
        "schema_version": 1,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_path": str(path),
        "branch": str(_git(path, "branch", "--show-current")).strip(),
        "head": str(_git(path, "rev-parse", "HEAD")).strip(),
        "tree": str(_git(path, "rev-parse", "HEAD^{tree}")).strip(),
        "origin": str(
            subprocess.run(
                ["git", "-C", str(path), "remote", "get-url", "origin"],
                check=False,
                capture_output=True,
                text=True,
            ).stdout
        ).strip()
        or None,
        "status": status,
        "tracked_patch_sha256": _sha256_bytes(patch) if patch else None,
        "untracked_archive_sha256": (
            _sha256_bytes(archive_value) if untracked else None
        ),
        "untracked_files": hashes,
    }
    identity_value = (
        json.dumps(identity, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    _write_private(target / "identity.json", identity_value)
    return identity


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
