#!/usr/bin/env python3
"""Fail-closed validator for the R2 Wave 0 controller contract."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
REPORT_ROOT = ROOT / "reports" / "remediation_r2"
TASK_ROOT = ROOT / "tasks" / "backlog" / "REMEDIATION_R2_WAVE0_20260713"

BASELINE = REPORT_ROOT / "R2_BASELINE_FREEZE_20260713.json"
MATRIX = REPORT_ROOT / "R2_FINDING_CLOSURE_MATRIX_20260713.json"
RUNTIME_CONTRACT = REPORT_ROOT / "RUNTIME_BINDING_CONTRACT_20260713.json"
RUNTIME_RESULT = REPORT_ROOT / "RUNTIME_BINDING_RESULT_20260713.json"
DB_BASELINE = REPORT_ROOT / "CENTRAL_DATABASE_BASELINE_20260713.json"
HG_RECORD = TASK_ROOT / "hg_exec_record.json"
DECISIONS = ROOT / "reports" / "human_gate" / "decisions.jsonl"
REGISTRY = ROOT / "registry" / "projects.yaml"

EXPECTED_STAGE = "REPOSITORY_WIDE_REMEDIATION_R2_AND_TUSHARE_BACKFILL"
EXPECTED_FINDINGS = {"RW-001", "RW-002", "RW-003", "RW-004", "RW-005", "RW-006", "EA-001"}
EXPECTED_REPOSITORIES = {
    "quant-proj",
    "A_Share_Monitor",
    "market_data",
    "quant_research_lab",
    "strategy_work",
    "US_Stock_Monitor",
    "us_stock_30w",
}
EXPECTED_REGISTRY_REPOSITORIES = EXPECTED_REPOSITORIES | {"central-data-ingestion"}
EXPECTED_REGISTRY_PROJECT_KEYS = {
    "quant_proj", "a_share_monitor", "us_stock_monitor", "us_stock_30w",
    "market_data", "quant_research_lab", "strategy_work", "central_data_ingestion",
}
EXPECTED_DB_SHA = "65e2c1354380b69b563b1846ec61871c6f99c46156736dc1954939278093c5c5"
EXPECTED_DB_BYTES = 1_001_926_656
EXPECTED_DECISION_ID = "HG-EXEC-TASK-REMEDIATION-R2-DB-BASELINE-BACKUP-20260713"


class ContractError(ValueError):
    """Raised when Wave 0 evidence drifts or overclaims state."""


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ContractError(f"object_required:{path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_baseline(value: dict[str, Any]) -> None:
    if value.get("stage_id") != EXPECTED_STAGE:
        raise ContractError("baseline_stage_mismatch")
    if value.get("status") != "WAVE0_BASELINE_FROZEN":
        raise ContractError("baseline_not_frozen")
    if value.get("current_external_verdict") != "NOT_PASSED_REWORK_REQUIRED":
        raise ContractError("external_verdict_overclaim")
    if value.get("strategy_candidate_available") is not False:
        raise ContractError("candidate_flag_must_be_false")
    audit_refs = value.get("audit_refs")
    live = value.get("live_checkouts")
    if not isinstance(audit_refs, list) or {item.get("repository") for item in audit_refs} != EXPECTED_REPOSITORIES:
        raise ContractError("audit_repository_set_mismatch")
    if not isinstance(live, list) or {item.get("repository") for item in live} != EXPECTED_REPOSITORIES:
        raise ContractError("live_repository_set_mismatch")
    if any(item.get("remote_ref_exact") is not True for item in audit_refs):
        raise ContractError("audit_remote_ref_not_exact")
    if any(item.get("dirty_entries") != 0 for item in live):
        raise ContractError("live_checkout_not_clean")
    freeze = value.get("freeze_rules", {})
    for key in ("new_strategy_research", "old_holdout_rerun", "tushare_network_calls", "central_database_writes", "publisher_enabled", "database_data_may_change_strategy_state"):
        if freeze.get(key) is not False:
            raise ContractError(f"freeze_rule_not_false:{key}")


def validate_matrix(value: dict[str, Any]) -> None:
    if value.get("stage_id") != EXPECTED_STAGE:
        raise ContractError("matrix_stage_mismatch")
    if value.get("strategy_candidate_available") is not False:
        raise ContractError("matrix_candidate_flag_must_be_false")
    findings = value.get("findings")
    if not isinstance(findings, list) or {item.get("id") for item in findings} != EXPECTED_FINDINGS:
        raise ContractError("finding_set_mismatch")
    if len(findings) != len(EXPECTED_FINDINGS):
        raise ContractError("duplicate_finding_id")
    for finding in findings:
        status = str(finding.get("status", ""))
        if status.startswith("CLOSED") or status in {"PASS", "ACCEPTED"}:
            raise ContractError(f"finding_closed_without_evidence:{finding.get('id')}")


def validate_database(value: dict[str, Any], *, require_backup: bool) -> None:
    if value.get("database_sha256") != EXPECTED_DB_SHA or value.get("database_bytes") != EXPECTED_DB_BYTES:
        raise ContractError("database_identity_mismatch")
    if value.get("database_mode") != "0600":
        raise ContractError("database_mode_mismatch")
    if value.get("network_calls") != 0 or value.get("database_writes") != 0:
        raise ContractError("wave0_data_action_overclaim")
    if value.get("strategy_candidate_available") is not False:
        raise ContractError("database_candidate_flag_must_be_false")
    backup = value.get("backup", {})
    path = Path(str(backup.get("path", "")))
    if backup.get("expected_sha256") != EXPECTED_DB_SHA or backup.get("expected_bytes") != EXPECTED_DB_BYTES:
        raise ContractError("backup_expectation_mismatch")
    if require_backup:
        if backup.get("status") != "PASS_BYTE_IDENTICAL":
            raise ContractError("backup_status_not_pass")
        if not path.is_file():
            raise ContractError("backup_missing")
        if path.stat().st_size != EXPECTED_DB_BYTES:
            raise ContractError("backup_size_mismatch")
        if path.stat().st_mode & 0o777 != 0o600:
            raise ContractError("backup_mode_mismatch")
        if sha256_file(path) != EXPECTED_DB_SHA:
            raise ContractError("backup_sha_mismatch")


def validate_hg(record: dict[str, Any], decisions: list[dict[str, Any]]) -> None:
    if record.get("decision_id") != EXPECTED_DECISION_ID or record.get("approved_by_user") is not True:
        raise ContractError("human_gate_invalid")
    if record.get("database_pre_sha256") != EXPECTED_DB_SHA or record.get("database_pre_bytes") != EXPECTED_DB_BYTES:
        raise ContractError("human_gate_database_identity_mismatch")
    if record.get("one_time_use") is not True or record.get("strategy_candidate_available") is not False:
        raise ContractError("human_gate_boundary_mismatch")
    matches = [item for item in decisions if item.get("decision_id") == EXPECTED_DECISION_ID]
    if len(matches) != 1 or matches[0] != record:
        raise ContractError("human_gate_durable_record_mismatch")


def validate_registry(value: dict[str, Any]) -> None:
    projects = value.get("projects")
    if not isinstance(projects, dict):
        raise ContractError("registry_projects_missing")
    if set(projects) != EXPECTED_REGISTRY_PROJECT_KEYS:
        raise ContractError("registry_repository_set_mismatch")
    central = value.get("central_database", {})
    if central.get("sha256") != EXPECTED_DB_SHA or central.get("bytes") != EXPECTED_DB_BYTES:
        raise ContractError("registry_database_identity_mismatch")
    if central.get("publisher_enabled") is not False:
        raise ContractError("registry_publisher_must_be_disabled")
    if not str(central.get("access", "")).startswith(
        "single future writer central-data-ingestion; publisher absent/disabled"
    ):
        raise ContractError("registry_writer_boundary_mismatch")
    boundaries = value.get("boundaries", {})
    if boundaries.get("strategy_candidate_available") is not False:
        raise ContractError("registry_candidate_flag_must_be_false")
    if boundaries.get("provider_network_calls_wave0") is not False or boundaries.get("central_database_writes_wave0") is not False:
        raise ContractError("registry_wave0_boundary_mismatch")


def read_decisions() -> list[dict[str, Any]]:
    return [json.loads(line) for line in DECISIONS.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate(*, require_backup: bool) -> None:
    validate_baseline(load_json(BASELINE))
    matrix = load_json(MATRIX)
    validate_matrix(matrix)
    module_path = ROOT / "scripts" / "validate_r2_closure_coverage.py"
    spec = importlib.util.spec_from_file_location("r2_closure_coverage", module_path)
    if spec is None or spec.loader is None:
        raise ContractError("closure_validator_unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.validate(
        matrix,
        runtime_result=load_json(RUNTIME_RESULT),
        runtime_contract=load_json(RUNTIME_CONTRACT),
        runtime_contract_sha256=sha256_file(RUNTIME_CONTRACT),
    )
    validate_database(load_json(DB_BASELINE), require_backup=require_backup)
    validate_hg(load_json(HG_RECORD), read_decisions())
    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    if not isinstance(registry, dict):
        raise ContractError("registry_object_required")
    validate_registry(registry)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-backup", action="store_true")
    args = parser.parse_args()
    validate(require_backup=args.require_backup)
    print("REMEDIATION_R2_WAVE0_CONTRACT_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
