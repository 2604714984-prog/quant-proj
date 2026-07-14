#!/usr/bin/env python3
"""Fail-closed validator for Remediation R1 Gate 0 artifacts."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any


FINDING_IDS = {f"F-{number:03d}" for number in range(1, 14)}
SEVERITY_COUNTS = {"Critical": 2, "High": 4, "Medium": 6, "Low": 1}
REPOSITORIES = {
    "quant-proj",
    "A_Share_Monitor",
    "US_Stock_Monitor",
    "market_data",
    "quant_research_lab",
    "strategy_work",
    "us_stock_30w",
}
SHA256_RE = re.compile(r"[0-9a-f]{64}")
GIT_BLOB_RE = re.compile(r"[0-9a-f]{40}")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON artifact: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON artifact must be an object: {path}")
    return value


def _require_false(payload: dict[str, Any], field: str, label: str) -> None:
    if payload.get(field) is not False:
        raise ValueError(f"{label}.{field} must be false")


def validate_root(root: Path) -> None:
    root = root.resolve()
    report = root / "reports" / "remediation"
    policy = _read_json(report / "REMEDIATION_STAGE_POLICY.json")
    baseline = _read_json(report / "REMEDIATION_BASELINE_MANIFEST.json")
    matrix = _read_json(report / "FINDING_CLOSURE_MATRIX.json")
    invalidation = _read_json(report / "ARTIFACT_INVALIDATION_AND_SUPERSESSION_LEDGER.json")
    capabilities = _read_json(report / "CAPABILITY_MATRIX.json")
    adr = (report / "CAPABILITY_BOUNDARY_ADR.md").read_text(encoding="utf-8")

    if policy.get("stage_status") not in {"REMEDIATION_IN_PROGRESS", "GATE_0_FROZEN"}:
        raise ValueError("remediation stage status is not a Gate 0 state")
    if policy.get("external_audit_status") != "FAIL_REMEDIATION_REQUIRED":
        raise ValueError("external audit failure state must remain explicit")
    _require_false(policy, "strategy_candidate_available", "policy")
    freeze = policy.get("freeze")
    if not isinstance(freeze, dict) or not freeze or set(freeze.values()) != {True}:
        raise ValueError("every remediation freeze flag must be true")
    inputs = policy.get("external_audit_inputs")
    if not isinstance(inputs, list) or len(inputs) != 2:
        raise ValueError("exactly two user-supplied audit inputs are required")
    if any(not SHA256_RE.fullmatch(str(item.get("sha256", ""))) for item in inputs):
        raise ValueError("audit input hashes must be lowercase SHA-256")
    gate0 = policy.get("gate0")
    if not isinstance(gate0, dict):
        raise ValueError("policy.gate0 is required")
    control_fields = {
        "baseline_manifest_valid",
        "artifact_invalidation_inventory_complete",
        "boundary_adr_accepted",
        "finding_tracker_complete",
    }
    if any(gate0.get(field) is not True for field in control_fields):
        raise ValueError("Gate 0 control artifacts are incomplete")
    if gate0.get("gate0_complete") is True and gate0.get("code_kill_switches_complete") is not True:
        raise ValueError("Gate 0 cannot complete before code kill-switches")

    repositories = baseline.get("repositories")
    if not isinstance(repositories, list):
        raise ValueError("baseline repositories must be a list")
    names = {item.get("name") for item in repositories if isinstance(item, dict)}
    if names != REPOSITORIES:
        raise ValueError(f"baseline repository set differs: {names ^ REPOSITORIES}")
    if any(item.get("worktree_clean") is not True for item in repositories):
        raise ValueError("every baseline worktree must be recorded clean")

    findings = matrix.get("findings")
    if not isinstance(findings, list):
        raise ValueError("finding matrix must contain a list")
    ids = [item.get("finding_id") for item in findings if isinstance(item, dict)]
    if len(ids) != 13 or set(ids) != FINDING_IDS or len(ids) != len(set(ids)):
        raise ValueError("finding matrix must contain each F-001 through F-013 exactly once")
    observed: dict[str, int] = {}
    for item in findings:
        severity = item.get("severity")
        observed[severity] = observed.get(severity, 0) + 1
        for field in (
            "audited_ref",
            "root_cause",
            "affected_paths",
            "remediation_branch",
            "positive_tests",
            "negative_tests",
            "superseded_artifacts",
            "remaining_limitations",
            "semantic_review",
            "independent_acceptance",
        ):
            if field not in item:
                raise ValueError(f"{item.get('finding_id')} is missing {field}")
        if item.get("finding_id") in {"F-008", "F-009"}:
            for field in (
                "audited_path",
                "audited_blob_sha",
                "fixed_path",
                "fixed_blob_sha",
                "test_file_path",
                "test_file_blob_sha",
                "test_node_ids",
                "runtime_factory_binding",
                "external_reaudit_links",
            ):
                if field not in item:
                    raise ValueError(f"{item.get('finding_id')} is missing {field}")
            for field in ("audited_path", "fixed_path", "test_file_path"):
                value = item[field]
                path = Path(value)
                if (
                    not isinstance(value, str)
                    or not value
                    or path.is_absolute()
                    or ".." in path.parts
                ):
                    raise ValueError(f"{item['finding_id']}.{field} is not a safe relative path")
            for field in ("audited_blob_sha", "fixed_blob_sha", "test_file_blob_sha"):
                if not GIT_BLOB_RE.fullmatch(str(item[field])):
                    raise ValueError(f"{item['finding_id']}.{field} is not a Git blob id")
            nodes = item["test_node_ids"]
            if (
                not isinstance(nodes, list)
                or not nodes
                or len(nodes) != len(set(nodes))
                or any(
                    not isinstance(node, str)
                    or not node.startswith(f"{item['test_file_path']}::")
                    for node in nodes
                )
            ):
                raise ValueError(f"{item['finding_id']} test node ids are not exact or unique")
            binding = item["runtime_factory_binding"]
            if not isinstance(binding, dict) or binding.get("same_implementation") is not True:
                raise ValueError(f"{item['finding_id']} runtime implementation remains split")
            links = item["external_reaudit_links"]
            if not isinstance(links, list) or not links or len(links) != len(set(links)):
                raise ValueError(f"{item['finding_id']} external re-audit links are missing")
    if observed != SEVERITY_COUNTS:
        raise ValueError(f"severity counts differ: {observed}")
    _require_false(matrix, "strategy_candidate_available", "matrix")

    if invalidation.get("inventory_complete") is not True:
        raise ValueError("artifact invalidation inventory is incomplete")
    if invalidation.get("pending_inventory") not in ([], None):
        raise ValueError("artifact invalidation ledger still has pending inventory")
    entries = invalidation.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("artifact invalidation ledger must not be empty")
    for item in entries:
        members = item.get("members")
        if members is not None:
            if not isinstance(members, list) or not members:
                raise ValueError(f"artifact set is empty: {item.get('artifact_id')}")
            for member in members:
                if not member.get("path") or not SHA256_RE.fullmatch(str(member.get("sha256", ""))):
                    raise ValueError(f"invalid artifact-set member: {item.get('artifact_id')}")
        elif not item.get("path") or not SHA256_RE.fullmatch(str(item.get("sha256", ""))):
            raise ValueError(f"invalid artifact hash: {item.get('artifact_id')}")
        for field in ("artifact_id", "repository", "state", "reason", "relation"):
            if not item.get(field):
                raise ValueError(f"invalidation entry is missing {field}")
    _require_false(invalidation, "strategy_candidate_available", "invalidation")

    capabilities_list = capabilities.get("capabilities")
    if not isinstance(capabilities_list, list) or not capabilities_list:
        raise ValueError("capability matrix must not be empty")
    keys = {(item.get("repository"), item.get("capability")) for item in capabilities_list}
    required_capabilities = {
        ("A_Share_Monitor", "a10_hitl_ticket"),
        ("A_Share_Monitor", "manual_fill"),
        ("A_Share_Monitor", "broker_order_paper_live_auto"),
        ("US_Stock_Monitor", "recommendation_manual_fill_broker_order_paper_live_auto_runtime"),
        ("us_stock_30w", "archived_paper_or_live_style_scripts"),
        ("quant_research_lab", "llm_factor_mining"),
        ("market_data", "metadata_and_schema_export"),
        ("quant-proj", "automated_gate_manifest_validation"),
    }
    if not required_capabilities.issubset(keys):
        raise ValueError("capability matrix omits a load-bearing capability")
    _require_false(capabilities, "strategy_candidate_available", "capabilities")

    required_adr_text = (
        "Status: `ACCEPTED_FOR_REMEDIATION_R1`",
        "default research entry points are pure research",
        "write capability is hard-disabled",
        "Broker integration, order routing or submission",
        "strategy_candidate_available` remains `false`",
    )
    if any(fragment not in adr for fragment in required_adr_text):
        raise ValueError("capability ADR is missing a required decision")


def validate_online_blob_bindings(root: Path) -> None:
    matrix = _read_json(root.resolve() / "reports" / "remediation" / "FINDING_CLOSURE_MATRIX.json")
    for item in matrix["findings"]:
        if item.get("finding_id") not in {"F-008", "F-009"}:
            continue
        repository = item["repository"]
        checks = (
            (item["audited_ref"], item["audited_path"], item["audited_blob_sha"]),
            (item["fix_commit"], item["fixed_path"], item["fixed_blob_sha"]),
            (item["fix_commit"], item["test_file_path"], item["test_file_blob_sha"]),
        )
        for commit, path, expected_blob in checks:
            output = subprocess.check_output(
                [
                    "gh",
                    "api",
                    f"repos/2604714984-prog/{repository}/contents/{path}?ref={commit}",
                ],
                text=True,
            )
            actual_blob = json.loads(output).get("sha")
            if actual_blob != expected_blob:
                raise ValueError(
                    f"{item['finding_id']} remote blob differs for {commit}:{path}"
                )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--online", action="store_true")
    args = parser.parse_args()
    validate_root(args.root)
    if args.online:
        validate_online_blob_bindings(args.root)
    policy = _read_json(args.root / "reports" / "remediation" / "REMEDIATION_STAGE_POLICY.json")
    complete = policy["gate0"]["gate0_complete"]
    print(f"remediation Gate 0 control artifacts: VALID; gate0_complete={str(complete).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
