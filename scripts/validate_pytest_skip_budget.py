#!/usr/bin/env python3
"""Require the exact preregistered pytest skip set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def observed_skips(junit_path: Path) -> list[str]:
    root = ET.parse(junit_path).getroot()
    identifiers = []
    for case in root.iter("testcase"):
        if case.find("skipped") is not None:
            classname = case.attrib.get("classname", "")
            name = case.attrib.get("name", "")
            identifiers.append(f"{classname}::{name}")
    return sorted(identifiers)


def validate(junit_path: Path, allowlist_path: Path) -> None:
    policy = json.loads(allowlist_path.read_text(encoding="utf-8"))
    if set(policy) != {"schema_version", "allowed_skips", "skip_budget"}:
        raise ValueError("skip allowlist has unexpected fields")
    if policy["schema_version"] != 1:
        raise ValueError("skip allowlist schema_version must be 1")
    allowed = policy["allowed_skips"]
    budget = policy["skip_budget"]
    if (
        not isinstance(allowed, list)
        or any(not isinstance(item, str) or not item for item in allowed)
        or len(allowed) != len(set(allowed))
        or type(budget) is not int
        or budget < 0
        or budget != len(allowed)
    ):
        raise ValueError("skip allowlist and budget are inconsistent")
    actual = observed_skips(junit_path)
    if actual != sorted(allowed):
        raise ValueError(
            f"pytest skip set changed: allowed={sorted(allowed)}, observed={actual}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--allowlist", type=Path, required=True)
    args = parser.parse_args()
    validate(args.junit, args.allowlist)
    print(f"pytest skip budget: PASS; skipped={len(observed_skips(args.junit))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

