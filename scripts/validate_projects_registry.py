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
    "quant_research_lab",
    "strategy_work",
    "central_data_ingestion",
}
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


def load_registry() -> dict:
    payload = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("projects"), dict):
        raise ValueError("registry/projects.yaml must contain a projects mapping")
    return payload


def validate(*, verify_local_git: bool, verify_remote_git: bool = False) -> None:
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
        expected = facts.get("commit")
        if not isinstance(expected, str) or not SHA1_RE.fullmatch(expected):
            raise ValueError(f"{name} must declare a full pinned commit")
        tree = facts.get("tree")
        if not isinstance(tree, str) or not SHA1_RE.fullmatch(tree):
            raise ValueError(f"{name} must declare a full pinned tree")
        if facts.get("identity_kind", "local_head_remote_exact") not in {
            "local_head_remote_exact",
            "remote_ref_authoritative",
        }:
            raise ValueError(f"{name} identity kind differs")

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
        expected_tree = subprocess.run(
            ["git", "-C", str(path), "rev-parse", f"{expected}^{{tree}}"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if expected_tree != facts["tree"]:
            raise ValueError(f"{name} pinned tree mismatch: {expected_tree} != {facts['tree']}")
        if facts.get("identity_kind", "local_head_remote_exact") == "remote_ref_authoritative":
            upstream = facts.get("upstream_ref")
            if not upstream:
                raise ValueError(f"{name} remote-authoritative entry lacks upstream_ref")
            local_upstream = subprocess.run(
                ["git", "-C", str(path), "rev-parse", upstream],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            if local_upstream != expected:
                raise ValueError(
                    f"{name} local remote-tracking ref mismatch: {local_upstream} != {expected}"
                )
            continue
        actual = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if actual != expected:
            raise ValueError(f"{name} commit mismatch: {actual} != {expected}")
        actual_tree = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD^{tree}"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if actual_tree != facts["tree"]:
            raise ValueError(f"{name} tree mismatch: {actual_tree} != {facts['tree']}")

    if verify_remote_git:
        for name, facts in payload["projects"].items():
            upstream = facts.get("upstream_ref")
            if not upstream:
                continue
            remote, branch = upstream.split("/", 1)
            output = subprocess.run(
                ["git", "-C", str(facts["path"]), "ls-remote", remote, f"refs/heads/{branch}"],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            ).stdout.strip()
            if output != f"{facts['commit']}\trefs/heads/{branch}":
                raise ValueError(f"{name} remote ref mismatch")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-local-git", action="store_true")
    parser.add_argument("--verify-remote-git", action="store_true")
    args = parser.parse_args()
    validate(
        verify_local_git=args.verify_local_git,
        verify_remote_git=args.verify_remote_git,
    )
    print("projects registry validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
