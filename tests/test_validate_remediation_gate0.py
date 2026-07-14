from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_remediation_gate0 import validate_root


ROOT = Path(__file__).resolve().parents[1]
REPORT_NAMES = (
    "REMEDIATION_STAGE_POLICY.json",
    "REMEDIATION_BASELINE_MANIFEST.json",
    "FINDING_CLOSURE_MATRIX.json",
    "ARTIFACT_INVALIDATION_AND_SUPERSESSION_LEDGER.json",
    "CAPABILITY_MATRIX.json",
)


def _copy_gate(tmp_path: Path) -> Path:
    report = tmp_path / "reports" / "remediation"
    report.mkdir(parents=True)
    for name in REPORT_NAMES:
        payload = json.loads((ROOT / "reports" / "remediation" / name).read_text(encoding="utf-8"))
        if name == "ARTIFACT_INVALIDATION_AND_SUPERSESSION_LEDGER.json":
            payload["inventory_complete"] = True
            payload["pending_inventory"] = []
        (report / name).write_text(json.dumps(payload), encoding="utf-8")
    (report / "CAPABILITY_BOUNDARY_ADR.md").write_text(
        (ROOT / "reports" / "remediation" / "CAPABILITY_BOUNDARY_ADR.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return tmp_path


def test_complete_gate0_fixture_passes(tmp_path: Path) -> None:
    validate_root(_copy_gate(tmp_path))


def test_incomplete_invalidation_inventory_fails(tmp_path: Path) -> None:
    root = _copy_gate(tmp_path)
    path = root / "reports" / "remediation" / "ARTIFACT_INVALIDATION_AND_SUPERSESSION_LEDGER.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["inventory_complete"] = False
    payload["pending_inventory"] = ["one unresolved artifact"]
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="inventory is incomplete"):
        validate_root(root)


def test_missing_finding_fails(tmp_path: Path) -> None:
    root = _copy_gate(tmp_path)
    path = root / "reports" / "remediation" / "FINDING_CLOSURE_MATRIX.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["findings"].pop()
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="each F-001 through F-013"):
        validate_root(root)


def test_unfrozen_strategy_work_fails(tmp_path: Path) -> None:
    root = _copy_gate(tmp_path)
    path = root / "reports" / "remediation" / "REMEDIATION_STAGE_POLICY.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["freeze"]["new_strategy_families"] = False
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="freeze flag"):
        validate_root(root)


def test_candidate_promotion_fails(tmp_path: Path) -> None:
    root = _copy_gate(tmp_path)
    path = root / "reports" / "remediation" / "CAPABILITY_MATRIX.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["strategy_candidate_available"] = True
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="must be false"):
        validate_root(root)


@pytest.mark.parametrize("finding_id", ["F-008", "F-009"])
def test_load_bearing_closure_requires_exact_blob_and_runtime_binding(
    tmp_path: Path, finding_id: str
) -> None:
    root = _copy_gate(tmp_path)
    path = root / "reports" / "remediation" / "FINDING_CLOSURE_MATRIX.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    finding = next(item for item in payload["findings"] if item["finding_id"] == finding_id)
    finding["fixed_blob_sha"] = "descriptive-not-a-blob"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="not a Git blob id"):
        validate_root(root)

    root = _copy_gate(tmp_path / "split")
    path = root / "reports" / "remediation" / "FINDING_CLOSURE_MATRIX.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    finding = next(item for item in payload["findings"] if item["finding_id"] == finding_id)
    finding["runtime_factory_binding"]["same_implementation"] = False
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="implementation remains split"):
        validate_root(root)


def test_descriptive_test_names_cannot_replace_exact_node_ids(tmp_path: Path) -> None:
    root = _copy_gate(tmp_path)
    path = root / "reports" / "remediation" / "FINDING_CLOSURE_MATRIX.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    finding = next(item for item in payload["findings"] if item["finding_id"] == "F-008")
    finding["test_node_ids"] = ["CSV boundary tests pass"]
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="not exact or unique"):
        validate_root(root)


def test_gate0_cannot_complete_before_code_kill_switches(tmp_path: Path) -> None:
    root = _copy_gate(tmp_path)
    path = root / "reports" / "remediation" / "REMEDIATION_STAGE_POLICY.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["gate0"]["gate0_complete"] = True
    payload["gate0"]["code_kill_switches_complete"] = False
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="code kill-switches"):
        validate_root(root)
