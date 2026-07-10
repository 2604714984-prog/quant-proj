#!/usr/bin/env python3
"""Validate controller project registry structure and, locally, pinned Git objects."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess

import yaml


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry" / "projects.yaml"


def load_registry() -> dict:
    payload = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("projects"), dict):
        raise ValueError("registry/projects.yaml must contain a projects mapping")
    return payload


def validate(*, verify_local_git: bool) -> None:
    payload = load_registry()
    required = {
        "quant_proj",
        "a_share_monitor",
        "us_stock_monitor",
        "market_data",
        "strategy_work",
    }
    missing = required - set(payload["projects"])
    if missing:
        raise ValueError(f"missing registry projects: {sorted(missing)}")
    if payload.get("boundaries", {}).get("strategy_candidate_available") is not False:
        raise ValueError("strategy_candidate_available must remain false")

    if not verify_local_git:
        return
    for name, facts in payload["projects"].items():
        expected = facts.get("commit")
        if not expected:
            continue
        path = Path(facts["path"])
        actual = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if actual != expected:
            raise ValueError(f"{name} commit mismatch: {actual} != {expected}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-local-git", action="store_true")
    args = parser.parse_args()
    validate(verify_local_git=args.verify_local_git)
    print("projects registry validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
