#!/usr/bin/env python3
"""Validate explicit branch-head or merge-ref CI identity records."""

from __future__ import annotations

import argparse
import json
import re
import subprocess


HEX40 = re.compile(r"[0-9a-f]{40}")


class CiIdentityError(ValueError):
    pass


def validate(
    record: dict[str, str],
    *,
    checked_out_sha: str,
    direct_parent_shas: tuple[str, ...] = (),
) -> None:
    if record.get("mode") not in {"head", "merge"}:
        raise CiIdentityError("CI identity mode differs")
    expected = {"mode", "branch_head_sha", "base_sha", "tested_merge_sha"}
    if set(record) != expected:
        raise CiIdentityError("CI identity fields differ")
    for name in ("branch_head_sha", "base_sha"):
        if HEX40.fullmatch(str(record[name])) is None:
            raise CiIdentityError(f"{name} is missing or invalid")
    if record["mode"] == "head":
        if record["tested_merge_sha"] != "NOT_APPLICABLE":
            raise CiIdentityError("head job must not claim a merge SHA")
        if checked_out_sha != record["branch_head_sha"]:
            raise CiIdentityError("checked-out head SHA differs")
    else:
        if HEX40.fullmatch(str(record["tested_merge_sha"])) is None:
            raise CiIdentityError("tested_merge_sha is missing or invalid")
        if checked_out_sha != record["tested_merge_sha"]:
            raise CiIdentityError("checked-out merge SHA differs")
        if record["tested_merge_sha"] in {record["branch_head_sha"], record["base_sha"]}:
            raise CiIdentityError("merge SHA does not identify a distinct merge ref")
        if len(direct_parent_shas) != 2:
            raise CiIdentityError("tested merge must have exactly two direct parents")
        if set(direct_parent_shas) != {record["base_sha"], record["branch_head_sha"]}:
            raise CiIdentityError("tested merge direct parents differ from base and head")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("head", "merge"), required=True)
    parser.add_argument("--branch-head-sha", required=True)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--tested-merge-sha", default="NOT_APPLICABLE")
    args = parser.parse_args()
    checked_out = subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    for identity in (args.branch_head_sha, args.base_sha, checked_out):
        subprocess.run(["git", "cat-file", "-e", f"{identity}^{{commit}}"], check=True)
    parents = tuple(
        subprocess.run(
            ["git", "show", "-s", "--format=%P", checked_out],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.split()
    )
    record = {
        "mode": args.mode,
        "branch_head_sha": args.branch_head_sha,
        "base_sha": args.base_sha,
        "tested_merge_sha": args.tested_merge_sha,
    }
    validate(record, checked_out_sha=checked_out, direct_parent_shas=parents)
    print(json.dumps(record, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
