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
        "schema_version": "remediation-final-controller-root-v1",
        "stage_id": "REMEDIATION_AND_REAUDIT_READINESS_R1_20260712",
        "authoritative": True,
        "status": "REMEDIATION_COMPLETE_PENDING_EXTERNAL_REAUDIT",
        "final_external_audit_verdict": "NOT_YET_PASSED",
        "strategy_candidate_available": False,
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
            }
        ],
        "finding_summary": {
            "original_total": 13,
            "open_critical": 0,
            "open_high": 0,
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
        "residual_blockers": [],
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


def test_blockers_forbid_reaudit_ready_status(tmp_path: Path) -> None:
    payload = _payload(tmp_path)
    payload["status"] = "REAUDIT_READY"
    payload["residual_blockers"] = [
        {
            "id": "CANONICAL_REBUILD",
            "severity": "High",
            "requires_user_action": False,
            "status": "OPEN",
            "description": "Canonical rebuild remains deliberately disabled.",
            "evidence_refs": [],
        }
    ]
    with pytest.raises(FinalRootError, match="cannot claim REAUDIT_READY"):
        validate(payload, repository_root=tmp_path)


def test_unrotated_historical_secret_requires_explicit_blocker(tmp_path: Path) -> None:
    payload = _payload(tmp_path)
    payload["gate_summary"]["historical_secret_candidates"] = 1
    with pytest.raises(FinalRootError, match="lacks a blocker"):
        validate(payload, repository_root=tmp_path)

    payload["residual_blockers"] = [
        {
            "id": "HISTORICAL_SECRET_ROTATION",
            "severity": "High",
            "requires_user_action": True,
            "status": "OPEN",
            "description": "The credential owner must revoke or rotate the candidate.",
            "evidence_refs": ["reports/remediation/SECRET_SCAN_INDEX.json"],
        }
    ]
    validate(payload, repository_root=tmp_path)
