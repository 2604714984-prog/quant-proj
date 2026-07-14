#!/usr/bin/env python3
"""Validate the small licensed fixture used by cross-repository CI."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures/cross_repo_identity_v1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate() -> None:
    manifest = json.loads((FIXTURE / "MANIFEST.json").read_text(encoding="utf-8"))
    if manifest.get("fixture_id") != "CROSS_REPO_IDENTITY_V1":
        raise ValueError("fixture identity changed")
    if (
        manifest.get("license_spdx") != "CC0-1.0"
        or manifest.get("synthetic_data") is not True
        or manifest.get("strategy_evidence") is not False
    ):
        raise ValueError("fixture license or evidence boundary changed")
    expected_files = {"LICENSE.txt", "corporate_actions.csv", "daily_ohlcv.csv"}
    if set(manifest.get("files", {})) != expected_files:
        raise ValueError("fixture file set changed")
    for name, identity in manifest["files"].items():
        path = FIXTURE / name
        if not path.is_file():
            raise ValueError(f"fixture file missing: {name}")
        if identity != {"bytes": path.stat().st_size, "sha256": sha256(path)}:
            raise ValueError(f"fixture identity mismatch: {name}")
    with (FIXTURE / "daily_ohlcv.csv").open(encoding="utf-8", newline="") as handle:
        bars = list(csv.DictReader(handle))
    with (FIXTURE / "corporate_actions.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        actions = list(csv.DictReader(handle))
    if len(bars) != 6 or len(actions) != 2:
        raise ValueError("fixture row shape changed")
    if any(not row["available_at"].endswith("Z") for row in actions):
        raise ValueError("fixture available_at must be UTC")


def main() -> int:
    validate()
    print("cross-repository fixture: VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
