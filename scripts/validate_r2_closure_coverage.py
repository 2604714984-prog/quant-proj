#!/usr/bin/env python3
"""Fail closed when any R2 high-risk surface is absent from the closure matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


EXPECTED = {
    "RW-001": {"csv_importer", "controller_authorization", "config_identity", "sidecar_identity"},
    "RW-002": {"phase_us2_gate_config", "immutable_manifest", "evidence_gate"},
    "RW-003": {"panel_subset", "subset_manifest", "pre_execution_assertion"},
    "RW-004": {"reports_inventory", "content_classifier", "history_policy"},
    "RW-005": {"cli", "factory", "qualification", "phase_us2_loader", "evidence_gate"},
    "RW-006": {"branch_head_ci", "merge_ref_ci", "base_sha"},
    "EA-001": {"release_assets", "publisher_source", "parquet_reproduction", "external_receipt"},
}
ROOT = Path(__file__).resolve().parents[1]


class ClosureCoverageError(ValueError):
    pass


def _validate_runtime_result(
    runtime: dict,
    *,
    contract: dict,
    contract_sha256: str,
) -> None:
    if set(runtime) != {
        "schema_version", "source_commit", "contract_sha256", "derived",
        "strategy_candidate_available",
    }:
        raise ClosureCoverageError("runtime binding result shape differs")
    if (
        runtime["schema_version"] != "runtime-binding-result-v1"
        or runtime["contract_sha256"] != contract_sha256
        or runtime["source_commit"] != contract.get("commit")
        or runtime["strategy_candidate_available"] is not False
    ):
        raise ClosureCoverageError("runtime binding result identity differs")
    derived = runtime["derived"]
    if not isinstance(derived, dict) or set(derived) != {
        "cli_sensitive_functions",
        "sensitive_module_edges",
        "definitions",
        "function_calls",
        "return_calls",
        "conditional_return_calls",
    }:
        raise ClosureCoverageError("runtime derived result shape differs")
    cli = derived.get("cli_sensitive_functions", [])
    if cli != sorted({
        "cmd_data_import_csv", "cmd_data_provider_qualification",
        "cmd_data_readiness", "cmd_research_phase_us2",
    }):
        raise ClosureCoverageError("runtime CLI coverage differs")
    if derived.get("sensitive_module_edges") != sorted(contract["required_module_edges"]):
        raise ClosureCoverageError("runtime sensitive edge coverage differs")
    expected_definitions: dict[str, list[str]] = {}
    for module, name in contract["required_definitions"]:
        expected_definitions.setdefault(module, []).append(name)
    expected_definitions = {
        module: sorted(names) for module, names in sorted(expected_definitions.items())
    }
    if derived.get("definitions") != expected_definitions:
        raise ClosureCoverageError("runtime definition coverage differs")
    expected_projection_calls: dict[str, list[str]] = {}
    for module, function, call in contract["required_function_calls"]:
        expected_projection_calls.setdefault(f"{module}.{function}", []).append(call)
    expected_projection_calls = {
        function: sorted(calls)
        for function, calls in sorted(expected_projection_calls.items())
    }
    if derived.get("function_calls") != expected_projection_calls:
        raise ClosureCoverageError("runtime projected function calls differ")
    expected_returns = {
        f"{module}.{function}": [call]
        for module, function, call in contract["required_return_calls"]
    }
    if derived.get("return_calls") != expected_returns:
        raise ClosureCoverageError("runtime return calls differ")
    expected_conditional = {
        f"{module}.{function}": [[variable, value, call]]
        for module, function, variable, value, call
        in contract["required_conditional_return_calls"]
    }
    if derived.get("conditional_return_calls") != expected_conditional:
        raise ClosureCoverageError("runtime conditional return calls differ")
    calls = derived.get("function_calls", {})
    conditional = derived.get("conditional_return_calls", {})
    required_calls = {
        "usq.data.provider_qualification._qualify": {"get_provider", "validate_runtime"},
        "usq.research.phase_us2_candidate_gate._load_panel": {"get_provider", "subset_panel", "validate_runtime"},
        "usq.research.phase_us2_candidate_gate.run_phase_us2_evidence": {"_load_panel", "apply_evidence_gate"},
        "usq.research.phase_us2_evidence_gate.apply_evidence_gate": {"validate"},
    }
    for function, expected in required_calls.items():
        if not expected.issubset(set(calls.get(function, []))):
            raise ClosureCoverageError(f"runtime semantic call coverage differs: {function}")
    if ["name", "csv", "_csv_runtime"] not in conditional.get(
        "usq.data.factory.get_provider", []
    ):
        raise ClosureCoverageError("factory CSV conditional binding differs")


def validate(
    payload: dict,
    *,
    runtime_result: dict,
    runtime_contract: dict,
    runtime_contract_sha256: str,
) -> None:
    findings = payload.get("findings")
    if not isinstance(findings, list):
        raise ClosureCoverageError("findings missing")
    by_id = {item.get("id"): item for item in findings if isinstance(item, dict)}
    if set(by_id) != set(EXPECTED):
        raise ClosureCoverageError("finding IDs differ from the frozen R2 set")
    for finding_id, expected in EXPECTED.items():
        actual = by_id[finding_id].get("active_surfaces")
        if not isinstance(actual, list) or set(actual) != expected or len(actual) != len(expected):
            raise ClosureCoverageError(f"active surface coverage differs: {finding_id}")
        if by_id[finding_id].get("acceptance") not in {
            "independent_read_only_acceptance_required", "external_reviewer_receipt_required"
        }:
            raise ClosureCoverageError(f"acceptance route differs: {finding_id}")
    for finding_id in {"RW-001", "RW-002", "RW-003", "RW-004", "RW-005", "RW-006"}:
        if by_id[finding_id].get("status") != "VERIFIED_IMPLEMENTATION_ACCEPTED":
            raise ClosureCoverageError(f"accepted source finding status differs: {finding_id}")
    ea = by_id["EA-001"]
    if ea.get("status") != "VERIFIED_EXTERNAL_RECEIPT":
        raise ClosureCoverageError("EA-001 external receipt is not linked")
    receipt_path = ROOT / str(ea.get("receipt_path", ""))
    if not receipt_path.is_file() or hashlib.sha256(receipt_path.read_bytes()).hexdigest() != ea.get(
        "receipt_sha256"
    ):
        raise ClosureCoverageError("EA-001 receipt bytes differ")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if (
        receipt.get("finding_id") != "EA-001"
        or receipt.get("status") != "EA001_EXTERNAL_BYTE_VERIFICATION_PASS"
        or receipt.get("parquet_recomputation", {}).get("mismatch_rows") != 0
        or receipt.get("boundary", {}).get("strategy_candidate_available") is not False
    ):
        raise ClosureCoverageError("EA-001 receipt content differs")
    if payload.get("strategy_candidate_available") is not False:
        raise ClosureCoverageError("candidate boundary differs")
    _validate_runtime_result(
        runtime_result,
        contract=runtime_contract,
        contract_sha256=runtime_contract_sha256,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--runtime-result", type=Path, required=True)
    parser.add_argument("--runtime-contract", type=Path, required=True)
    args = parser.parse_args()
    contract = json.loads(args.runtime_contract.read_text(encoding="utf-8"))
    validate(
        json.loads(args.matrix.read_text(encoding="utf-8")),
        runtime_result=json.loads(args.runtime_result.read_text(encoding="utf-8")),
        runtime_contract=contract,
        runtime_contract_sha256=hashlib.sha256(args.runtime_contract.read_bytes()).hexdigest(),
    )
    print("R2 closure coverage: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
