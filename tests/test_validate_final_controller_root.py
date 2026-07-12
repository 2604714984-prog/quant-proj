from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from scripts.validate_final_controller_root import FinalRootError, validate


REPOSITORIES = {
    "quant-proj",
    "A_Share_Monitor",
    "market_data",
    "quant_research_lab",
    "strategy_work",
    "US_Stock_Monitor",
    "us_stock_30w",
}


def _payload(tmp_path: Path) -> dict:
    artifact = tmp_path / "evidence.json"
    artifact.write_text("{}\n", encoding="utf-8")
    external_report = tmp_path / "reports" / "remediation" / "EXTERNAL_REAUDIT_VERDICT_20260712.md"
    external_report.parent.mkdir(parents=True, exist_ok=True)
    external_report.write_bytes(b"external verdict fixture\n")
    repositories = []
    for index, name in enumerate(sorted(REPOSITORIES), start=1):
        commit = f"{index:040x}"
        repositories.append(
            {
                "name": name,
                "remote": f"https://github.com/2604714984-prog/{name}.git",
                "branch": f"agent/remediation-{index}",
                "commit": commit,
                "tree": f"{index + 20:040x}",
                "pull_request": {
                    "number": index,
                    "url": f"https://github.com/2604714984-prog/{name}/pull/{index}",
                    "draft": True,
                },
                "ci": {
                    "run_id": index,
                    "url": f"https://github.com/2604714984-prog/{name}/actions/runs/{index}",
                    "head_sha": commit,
                    "conclusion": "success",
                    "jobs": [
                        {"name": job, "conclusion": "success"}
                        for job in sorted(
                            {
                                "static-unit",
                                "integration-identity",
                                "controlled-fixture-reproduction",
                            }
                        )
                    ],
                },
            }
        )
    return {
        "schema_version": "remediation-final-controller-root-v2",
        "stage_id": "REMEDIATION_AND_REAUDIT_READINESS_R1_20260712",
        "authoritative": True,
        "status": "TARGETED_REAUDIT_PENDING",
        "final_external_audit_verdict": "NOT_PASSED",
        "strategy_candidate_available": False,
        "external_reaudit": {
            "review_target": "quant-proj#11",
            "source_report_path": "reports/remediation/EXTERNAL_REAUDIT_VERDICT_20260712.md",
            "source_report_sha256": hashlib.sha256(external_report.read_bytes()).hexdigest(),
            "review": "CHANGES_REQUESTED",
            "status": "REWORK_REQUIRED",
            "new_critical": 0,
            "new_high_total": 1,
            "new_high_closed": 1,
            "new_medium_total": 1,
            "new_medium_closed": 1,
            "evidence_blocker_total": 1,
            "evidence_blocker_closed": 0,
            "targeted_reaudit_allowed": True,
        },
        "research_boundary": {
            "new_strategy_research_executed": False,
            "frozen_strategy_outcomes_reopened": False,
            "provider_or_network_ingestion_executed": False,
            "broker_order_paper_live_auto_enabled": False,
        },
        "repositories": repositories,
        "artifacts": [
            {
                "path": "evidence.json",
                "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
            },
            {
                "path": "reports/remediation/EXTERNAL_REAUDIT_VERDICT_20260712.md",
                "sha256": hashlib.sha256(external_report.read_bytes()).hexdigest(),
            },
        ],
        "finding_summary": {
            "original_total": 13,
            "open_critical": 0,
            "open_high": 0,
            "external_open_high": 0,
            "external_open_medium": 0,
            "external_evidence_blockers": 1,
            "strategy_candidate_available": False,
        },
        "gate_summary": {
            "unexpected_test_skips": 0,
            "unclassified_current_branch_binaries": 0,
            "stale_authoritative_refs": 0,
            "new_shadow_critical": 0,
            "new_shadow_high": 0,
            "historical_secret_candidates": 0,
            "rotated_or_revoked_secret_candidates": 0,
        },
        "residual_blockers": [
            {
                "id": "EA-001",
                "severity": "Medium",
                "requires_user_action": False,
                "status": "OPEN",
                "description": "External reviewer byte verification is pending.",
                "evidence_refs": ["evidence.json"],
            }
        ],
    }


def test_valid_controller_root(tmp_path: Path) -> None:
    validate(_payload(tmp_path), repository_root=tmp_path)


@pytest.mark.parametrize(
    "mutation",
    [
        "ci_head",
        "skip_count",
        "candidate",
        "artifact_hash",
        "branch_path",
        "research_execution",
    ],
)
def test_controller_root_mutations_fail_closed(tmp_path: Path, mutation: str) -> None:
    payload = _payload(tmp_path)
    if mutation == "ci_head":
        payload["repositories"][0]["ci"]["head_sha"] = "f" * 40
    elif mutation == "skip_count":
        payload["gate_summary"]["unexpected_test_skips"] = 1
    elif mutation == "candidate":
        payload["strategy_candidate_available"] = True
    elif mutation == "artifact_hash":
        payload["artifacts"][0]["sha256"] = "f" * 64
    elif mutation == "branch_path":
        payload["repositories"][0]["branch"] = "main"
    elif mutation == "research_execution":
        payload["research_boundary"]["new_strategy_research_executed"] = True
    with pytest.raises(FinalRootError):
        validate(payload, repository_root=tmp_path)


def test_ready_or_passed_external_claims_fail(tmp_path: Path) -> None:
    payload = _payload(tmp_path)
    payload["status"] = "REAUDIT_READY"
    with pytest.raises(FinalRootError, match="targeted re-audit pending"):
        validate(payload, repository_root=tmp_path)
    payload = _payload(tmp_path)
    payload["final_external_audit_verdict"] = "PASSED"
    with pytest.raises(FinalRootError, match="NOT_PASSED"):
        validate(payload, repository_root=tmp_path)


def test_unrotated_historical_secret_requires_explicit_blocker(tmp_path: Path) -> None:
    payload = _payload(tmp_path)
    payload["gate_summary"]["historical_secret_candidates"] = 1
    with pytest.raises(FinalRootError, match="lacks a blocker"):
        validate(payload, repository_root=tmp_path)

    payload["residual_blockers"].append(
        {
            "id": "HISTORICAL_SECRET_ROTATION",
            "severity": "High",
            "requires_user_action": True,
            "status": "OPEN",
            "description": "The credential owner must revoke or rotate the candidate.",
            "evidence_refs": ["reports/remediation/SECRET_SCAN_INDEX.json"],
        }
    )
    with pytest.raises(FinalRootError, match="only the independent"):
        validate(payload, repository_root=tmp_path)
