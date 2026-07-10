#!/usr/bin/env python3
"""Validate controller project registry structure and, locally, pinned Git objects."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess

import yaml


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry" / "projects.yaml"
REQUIRED_PROJECTS = {
    "quant_proj",
    "a_share_monitor",
    "us_stock_monitor",
    "us_stock_30w",
    "market_data",
    "strategy_work",
}
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


def load_registry() -> dict:
    payload = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("projects"), dict):
        raise ValueError("registry/projects.yaml must contain a projects mapping")
    return payload


def validate(*, verify_local_git: bool) -> None:
    payload = load_registry()
    missing = REQUIRED_PROJECTS - set(payload["projects"])
    if missing:
        raise ValueError(f"missing registry projects: {sorted(missing)}")
    boundaries = payload.get("boundaries", {})
    for key in (
        "strategy_candidate_available",
        "recommendation_or_ticket",
        "broker_order_paper_live_auto",
        "daily_signal_push",
        "product_route_or_readiness_activation",
        "secret_access_or_output",
    ):
        if boundaries.get(key) is not False:
            raise ValueError(f"boundary {key} must remain false")

    for name, facts in payload["projects"].items():
        if not isinstance(facts, dict):
            raise ValueError(f"{name} registry entry must be a mapping")
        if not facts.get("path") or not facts.get("branch"):
            raise ValueError(f"{name} must declare path and branch")
        if name == "quant_proj":
            continue
        expected = facts.get("commit")
        if not isinstance(expected, str) or not SHA1_RE.fullmatch(expected):
            raise ValueError(f"{name} must declare a full pinned commit")

    if not verify_local_git:
        return
    for name, facts in payload["projects"].items():
        expected = facts.get("commit")
        if not expected:
            continue
        path = Path(facts["path"])
        if not path.is_dir():
            raise ValueError(f"{name} path does not exist: {path}")
        object_type = subprocess.run(
            ["git", "-C", str(path), "cat-file", "-t", expected],
            check=False,
            capture_output=True,
            text=True,
        )
        if object_type.returncode != 0 or object_type.stdout.strip() != "commit":
            raise ValueError(f"{name} pinned commit is unavailable locally: {expected}")
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
