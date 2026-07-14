#!/usr/bin/env python3
"""Validate the detached checksum chain for the re-audit package."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path, PurePosixPath
import re


LINE = re.compile(r"([0-9a-f]{64})  ([A-Za-z0-9._/-]+)")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(checksums: Path, *, repository_root: Path) -> int:
    entries: dict[str, str] = {}
    for line_number, raw in enumerate(
        checksums.read_text(encoding="utf-8").splitlines(), start=1
    ):
        match = LINE.fullmatch(raw)
        if match is None:
            raise ValueError(f"invalid checksum line {line_number}")
        digest, name = match.groups()
        rel = PurePosixPath(name)
        if rel.is_absolute() or ".." in rel.parts or "." in rel.parts:
            raise ValueError(f"checksum path escapes repository: {name}")
        if name in entries:
            raise ValueError(f"duplicate checksum path: {name}")
        if Path(name).name == checksums.name:
            raise ValueError("checksum manifest cannot contain itself")
        entries[name] = digest
    if not entries:
        raise ValueError("checksum manifest is empty")
    if "reports/remediation/FINAL_CONTROLLER_ROOT.json" not in entries:
        raise ValueError("authoritative controller root is not checksummed")
    for name, expected in entries.items():
        path = repository_root.joinpath(*PurePosixPath(name).parts)
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"checksummed artifact is missing or aliased: {name}")
        if sha256(path) != expected:
            raise ValueError(f"checksummed artifact identity differs: {name}")
    return len(entries)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checksums", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    count = validate(args.checksums, repository_root=args.repository_root.resolve())
    print(f"remediation checksum chain: VALID; artifacts={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
