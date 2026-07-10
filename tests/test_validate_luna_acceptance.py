import json

import pytest

from scripts.validate_luna_acceptance import CONFLICT, INSUFFICIENT, validate_payload


SHA_A = "0123456789abcdef" * 4
SHA_B = "fedcba9876543210" * 4


def _record() -> dict:
    return {
        "schema_version": 1,
        "acceptance_id": "A-1",
        "acceptance_task_id": "019f4cc3-e022-7f21-9f4d-0b3e036b7bf3",
        "task_id": "TASK-1",
        "model_role": "acceptance",
        "model": "gpt-5.6-luna",
        "reasoning_effort": "high",
        "sandbox_mode": "read-only",
        "approval_policy": "never",
        "final_owner": "LUNA",
        "stage": "ROUTINE",
        "decision": "LUNA_ACCEPTANCE",
        "workspace_root": "/tmp/workspace",
        "gate_manifest_path": "gate.json",
        "gate_manifest_sha256": SHA_A,
        "evidence_rework_count": 0,
        "missing_evidence": [],
        "evidence_conflicts": [],
        "escalation_reason": None,
        "disputed_evidence_refs": [],
        "return_to": None,
        "prior_luna_rework": None,
        "deterministic_check": None,
        "sol_ruling": None,
    }


def test_routine_luna_acceptance_passes():
    validate_payload(_record())


def test_deterministic_or_missing_issue_stays_rework():
    record = _record()
    record["decision"] = "REWORK_REQUIRED"
    record["missing_evidence"] = ["focused test output"]
    validate_payload(record)


def test_insufficient_evidence_needs_one_rework():
    record = _record()
    record.update(
        decision="SOL_ESCALATION_REQUEST",
        escalation_reason=INSUFFICIENT,
        missing_evidence=["one unresolved claim"],
        disputed_evidence_refs=[{"path": "evidence-a.json", "sha256": SHA_A}],
        return_to="LUNA_FINAL_ACCEPTANCE",
        prior_luna_rework={"path": "prior.json", "sha256": SHA_B},
    )
    with pytest.raises(ValueError, match="exactly one"):
        validate_payload(record)
    record["evidence_rework_count"] = 1
    validate_payload(record)


def test_conflict_needs_two_distinct_hashes():
    record = _record()
    record.update(
        decision="SOL_ESCALATION_REQUEST",
        escalation_reason=CONFLICT,
        evidence_conflicts=["A vs B"],
        disputed_evidence_refs=[{"path": "a", "sha256": SHA_A}],
        return_to="LUNA_FINAL_ACCEPTANCE",
        deterministic_check={"path": "conflict.json", "sha256": SHA_B},
    )
    with pytest.raises(ValueError, match="two distinct"):
        validate_payload(record)
    record["disputed_evidence_refs"].append({"path": "b", "sha256": SHA_B})
    validate_payload(record)


def test_final_after_sol_is_still_luna_owned():
    record = _record()
    record["stage"] = "FINAL_AFTER_SOL"
    record["sol_ruling"] = {"path": "ruling.json", "sha256": SHA_B}
    validate_payload(record)


def test_executor_cannot_claim_acceptance():
    record = _record()
    record["model_role"] = "executor"
    with pytest.raises(ValueError, match="acceptance identity"):
        validate_payload(record)


def test_superseded_acceptance_is_not_final():
    record = _record()
    record["superseded"] = True
    with pytest.raises(ValueError, match="superseded"):
        validate_payload(record)


def test_current_acceptance_uses_canonical_singleton(monkeypatch, tmp_path):
    record = _record()
    record["workspace_root"] = str(tmp_path)
    gate = tmp_path / "gate.json"
    gate.write_text(json.dumps({"task_id": "TASK-1"}), encoding="utf-8")
    record["gate_manifest_path"] = "gate.json"
    record["gate_manifest_sha256"] = __import__("hashlib").sha256(gate.read_bytes()).hexdigest()
    acceptance = tmp_path / "luna_acceptance.json"
    acceptance.write_text(json.dumps(record), encoding="utf-8")
    (tmp_path / "spec.md").write_text("STATUS: LUNA_ACCEPTED_CODE_ONLY\n", encoding="utf-8")
    monkeypatch.setattr("scripts.validate_automated_gate_manifest.validate_file", lambda *_args, **_kwargs: None)
    from scripts.validate_luna_acceptance import validate_file

    validate_file(acceptance)
    duplicate = tmp_path / "luna_acceptance_old.json"
    duplicate.write_text(acceptance.read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(ValueError, match="exactly one"):
        validate_file(acceptance)
