#!/usr/bin/env python3
"""Fail-closed validation for the single remediation controller root."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import Any


SCHEMA_VERSION = "remediation-final-controller-root-v2"
STAGE_ID = "REMEDIATION_AND_REAUDIT_READINESS_R1_20260712"
EXPECTED_REPOSITORIES = {
    "quant-proj",
    "A_Share_Monitor",
    "market_data",
    "quant_research_lab",
    "strategy_work",
    "US_Stock_Monitor",
    "us_stock_30w",
}
EXPECTED_JOBS = {
    "static-unit",
    "integration-identity",
    "controlled-fixture-reproduction",
}
HEX40 = re.compile(r"[0-9a-f]{40}")
HEX64 = re.compile(r"[0-9a-f]{64}")
SAFE_NAME = re.compile(r"[A-Za-z0-9._/-]+")


class FinalRootError(ValueError):
    """Raised when the declared controller root is not independently usable."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise FinalRootError(
            f"{label} keys differ: expected={sorted(expected)}, actual={sorted(value)}"
        )


def _safe_relative_path(value: object, *, label: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or SAFE_NAME.fullmatch(value) is None:
        raise FinalRootError(f"{label} is not a safe repository-relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise FinalRootError(f"{label} escapes the repository root")
    return path


def _validate_ci(ci: object, *, repository: str) -> None:
    if not isinstance(ci, dict):
        raise FinalRootError(f"{repository} CI record is not an object")
    _require_keys(ci, {"run_id", "url", "head_sha", "conclusion", "jobs"}, f"{repository}.ci")
    if type(ci["run_id"]) is not int or ci["run_id"] <= 0:
        raise FinalRootError(f"{repository} CI run id is invalid")
    if ci["conclusion"] != "success" or not HEX40.fullmatch(str(ci["head_sha"])):
        raise FinalRootError(f"{repository} CI is not a successful immutable run")
    expected_url = f"https://github.com/2604714984-prog/{repository}/actions/runs/{ci['run_id']}"
    if ci["url"] != expected_url:
        raise FinalRootError(f"{repository} CI URL is not canonical")
    jobs = ci["jobs"]
    if not isinstance(jobs, list) or {item.get("name") for item in jobs if isinstance(item, dict)} != EXPECTED_JOBS:
        raise FinalRootError(f"{repository} CI job set differs")
    for item in jobs:
        if set(item) != {"name", "conclusion"} or item["conclusion"] != "success":
            raise FinalRootError(f"{repository} CI contains a non-successful job")


def validate(payload: dict[str, Any], *, repository_root: Path) -> None:
    expected_top = {
        "schema_version",
        "stage_id",
        "authoritative",
        "status",
        "final_external_audit_verdict",
        "strategy_candidate_available",
        "external_reaudit",
        "research_boundary",
        "repositories",
        "artifacts",
        "finding_summary",
        "gate_summary",
        "residual_blockers",
    }
    _require_keys(payload, expected_top, "root")
    if payload["schema_version"] != SCHEMA_VERSION or payload["stage_id"] != STAGE_ID:
        raise FinalRootError("controller root identity differs")
    if payload["authoritative"] is not True or payload["strategy_candidate_available"] is not False:
        raise FinalRootError("authoritative or candidate boundary differs")
    if payload["status"] != "TARGETED_REAUDIT_PENDING":
        raise FinalRootError("controller root is not in the targeted re-audit pending state")
    if payload["final_external_audit_verdict"] != "NOT_PASSED":
        raise FinalRootError("remediation cannot alter the external NOT_PASSED verdict")
    external = payload["external_reaudit"]
    if not isinstance(external, dict):
        raise FinalRootError("external re-audit record is not an object")
    _require_keys(
        external,
        {
            "review_target",
            "source_report_path",
            "source_report_sha256",
            "review",
            "status",
            "new_critical",
            "new_high_total",
            "new_high_closed",
            "new_medium_total",
            "new_medium_closed",
            "evidence_blocker_total",
            "evidence_blocker_closed",
            "targeted_reaudit_allowed",
        },
        "external_reaudit",
    )
    expected_external = {
        "review_target": "quant-proj#11",
        "source_report_path": "reports/remediation/EXTERNAL_REAUDIT_VERDICT_20260712.md",
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
    }
    if any(external.get(key) != value for key, value in expected_external.items()):
        raise FinalRootError("external re-audit tuple or closure counts differ")
    if not HEX64.fullmatch(str(external["source_report_sha256"])):
        raise FinalRootError("external re-audit report hash is invalid")
    boundary = payload["research_boundary"]
    if not isinstance(boundary, dict):
        raise FinalRootError("research boundary is not an object")
    _require_keys(
        boundary,
        {
            "new_strategy_research_executed",
            "frozen_strategy_outcomes_reopened",
            "provider_or_network_ingestion_executed",
            "broker_order_paper_live_auto_enabled",
        },
        "research_boundary",
    )
    if any(value is not False for value in boundary.values()):
        raise FinalRootError("remediation crossed the frozen research boundary")

    repositories = payload["repositories"]
    if not isinstance(repositories, list) or {item.get("name") for item in repositories if isinstance(item, dict)} != EXPECTED_REPOSITORIES:
        raise FinalRootError("repository set differs")
    for item in repositories:
        _require_keys(
            item,
            {"name", "remote", "branch", "commit", "tree", "pull_request", "ci"},
            "repository",
        )
        name = item["name"]
        if item["remote"] != f"https://github.com/2604714984-prog/{name}.git":
            raise FinalRootError(f"{name} remote differs")
        if not HEX40.fullmatch(str(item["commit"])) or not HEX40.fullmatch(str(item["tree"])):
            raise FinalRootError(f"{name} commit/tree identity is invalid")
        if not isinstance(item["branch"], str) or not item["branch"].startswith("agent/"):
            raise FinalRootError(f"{name} branch is not a remediation navigation ref")
        pull_request = item["pull_request"]
        if not isinstance(pull_request, dict) or set(pull_request) != {"number", "url", "draft"}:
            raise FinalRootError(f"{name} pull-request record differs")
        if type(pull_request["number"]) is not int or pull_request["number"] <= 0 or pull_request["draft"] is not True:
            raise FinalRootError(f"{name} pull-request state differs")
        if pull_request["url"] != f"https://github.com/2604714984-prog/{name}/pull/{pull_request['number']}":
            raise FinalRootError(f"{name} pull-request URL differs")
        _validate_ci(item["ci"], repository=name)
        if item["ci"]["head_sha"] != item["commit"]:
            raise FinalRootError(f"{name} CI does not bind the final commit")

    artifacts = payload["artifacts"]
    if not isinstance(artifacts, list) or not artifacts:
        raise FinalRootError("supporting artifact inventory is empty")
    artifact_paths: list[str] = []
    for item in artifacts:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise FinalRootError("artifact record differs")
        rel = _safe_relative_path(item["path"], label="artifact.path")
        path = repository_root.joinpath(*rel.parts)
        if not path.is_file() or path.is_symlink():
            raise FinalRootError(f"artifact is missing or aliased: {rel}")
        if not HEX64.fullmatch(str(item["sha256"])) or _sha256(path) != item["sha256"]:
            raise FinalRootError(f"artifact identity differs: {rel}")
        artifact_paths.append(str(rel))
    if len(artifact_paths) != len(set(artifact_paths)):
        raise FinalRootError("artifact inventory contains duplicate paths")
    if external["source_report_path"] not in artifact_paths:
        raise FinalRootError("external re-audit report is absent from the artifact inventory")
    external_record = next(
        item for item in artifacts if item["path"] == external["source_report_path"]
    )
    if external_record["sha256"] != external["source_report_sha256"]:
        raise FinalRootError("external re-audit report hash is not consistently bound")

    finding = payload["finding_summary"]
    if finding != {
        "original_total": 13,
        "open_critical": 0,
        "open_high": 0,
        "external_open_high": 0,
        "external_open_medium": 0,
        "external_evidence_blockers": 1,
        "strategy_candidate_available": False,
    }:
        raise FinalRootError("finding summary is not fail-closed")
    gate = payload["gate_summary"]
    if not isinstance(gate, dict) or set(gate) != {
        "unexpected_test_skips",
        "unclassified_current_branch_binaries",
        "stale_authoritative_refs",
        "new_shadow_critical",
        "new_shadow_high",
        "historical_secret_candidates",
        "rotated_or_revoked_secret_candidates",
    }:
        raise FinalRootError("gate summary differs")
    zero_gates = {
        "unexpected_test_skips",
        "unclassified_current_branch_binaries",
        "stale_authoritative_refs",
        "new_shadow_critical",
        "new_shadow_high",
    }
    if any(type(gate[name]) is not int or gate[name] != 0 for name in zero_gates):
        raise FinalRootError("one or more final zero-tolerance gates are non-zero")
    for name in {
        "historical_secret_candidates",
        "rotated_or_revoked_secret_candidates",
    }:
        if type(gate[name]) is not int or gate[name] < 0:
            raise FinalRootError("historical secret counts are invalid")
    if gate["rotated_or_revoked_secret_candidates"] > gate["historical_secret_candidates"]:
        raise FinalRootError("secret remediation count exceeds candidate count")
    blockers = payload["residual_blockers"]
    if not isinstance(blockers, list):
        raise FinalRootError("residual blockers are not a list")
    blocker_ids = set()
    for blocker in blockers:
        if not isinstance(blocker, dict) or set(blocker) != {
            "id",
            "severity",
            "requires_user_action",
            "status",
            "description",
            "evidence_refs",
        }:
            raise FinalRootError("residual blocker record differs")
        if (
            not isinstance(blocker["id"], str)
            or not blocker["id"]
            or blocker["id"] in blocker_ids
            or blocker["status"] != "OPEN"
            or blocker["severity"] not in {"Critical", "High", "Medium", "Low"}
            or type(blocker["requires_user_action"]) is not bool
            or not isinstance(blocker["description"], str)
            or not blocker["description"]
            or not isinstance(blocker["evidence_refs"], list)
        ):
            raise FinalRootError("residual blocker content differs")
        blocker_ids.add(blocker["id"])
    unresolved_secrets = (
        gate["historical_secret_candidates"]
        - gate["rotated_or_revoked_secret_candidates"]
    )
    if unresolved_secrets and "HISTORICAL_SECRET_ROTATION" not in blocker_ids:
        raise FinalRootError("unremediated historical secret lacks a blocker record")
    if not unresolved_secrets and "HISTORICAL_SECRET_ROTATION" in blocker_ids:
        raise FinalRootError("resolved historical secret retains a stale blocker")
    if {item["id"] for item in blockers} != {"EA-001"}:
        raise FinalRootError("only the independent data-room verification blocker may remain")
    if blockers[0]["severity"] != "Medium" or blockers[0]["requires_user_action"] is not False:
        raise FinalRootError("EA-001 blocker classification differs")


def validate_online(payload: dict[str, Any]) -> None:
    """Resolve remote refs and GitHub Actions metadata from immutable records."""

    for item in payload["repositories"]:
        branch_ref = f"refs/heads/{item['branch']}"
        output = subprocess.run(
            ["git", "ls-remote", item["remote"], branch_ref],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if output != f"{item['commit']}\t{branch_ref}":
            raise FinalRootError(f"remote ref differs: {item['name']}")
        owner_repo = f"2604714984-prog/{item['name']}"
        run = json.loads(
            subprocess.run(
                ["gh", "api", f"repos/{owner_repo}/actions/runs/{item['ci']['run_id']}"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
        )
        if run.get("head_sha") != item["commit"] or run.get("conclusion") != "success":
            raise FinalRootError(f"remote CI identity differs: {item['name']}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--online", action="store_true")
    args = parser.parse_args()
    payload = json.loads(args.root.read_text(encoding="utf-8"))
    validate(payload, repository_root=args.repository_root.resolve())
    if args.online:
        validate_online(payload)
    print("final controller root: VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
