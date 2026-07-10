#!/usr/bin/env python3
"""Validate one Luna acceptance record, including narrow Sol escalation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
THREAD_ID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
INSUFFICIENT = "EVIDENCE_INSUFFICIENT_AFTER_ONE_BOUNDED_LUNA_REWORK"
CONFLICT = "EVIDENCE_CONFLICT_UNRESOLVED_BY_DETERMINISTIC_CHECKS"
DECISIONS = {"LUNA_ACCEPTANCE", "REWORK_REQUIRED", "SOL_ESCALATION_REQUEST"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(value: object, field: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value) or len(set(value)) == 1:
        raise ValueError(f"{field} must be a non-placeholder SHA-256")
    return value


def _rooted(root: Path, value: object, field: str) -> Path:
    if not isinstance(value, str) or not value or any(token in value for token in ("<", ">", "path/to")):
        raise ValueError(f"{field} must be a concrete path")
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"{field} escapes workspace_root")
    if not resolved.is_file():
        raise ValueError(f"{field} file does not exist")
    return resolved


def validate_payload(payload: dict) -> None:
    if payload.get("template_only") is True:
        raise ValueError("template-only acceptance record is not a decision")
    if payload.get("superseded") is True:
        raise ValueError("superseded acceptance record is not final")
    if payload.get("schema_version") != 1:
        raise ValueError("schema_version must be 1")
    for field in ("acceptance_id", "task_id", "workspace_root"):
        if not isinstance(payload.get(field), str) or not payload[field].strip():
            raise ValueError(f"{field} is required")
    if not THREAD_ID_RE.fullmatch(str(payload.get("acceptance_task_id", ""))):
        raise ValueError("acceptance_task_id must be a concrete Codex task UUID")
    identity = (
        payload.get("model_role"),
        payload.get("model"),
        payload.get("reasoning_effort"),
        payload.get("sandbox_mode"),
        payload.get("approval_policy"),
        payload.get("final_owner"),
    )
    if identity != ("acceptance", "gpt-5.6-luna", "high", "read-only", "never", "LUNA"):
        raise ValueError("acceptance identity must be read-only Luna/high with Luna final ownership")
    if payload.get("decision") not in DECISIONS:
        raise ValueError("invalid Luna decision")
    if payload.get("stage") not in {"ROUTINE", "FINAL_AFTER_SOL"}:
        raise ValueError("stage must be ROUTINE or FINAL_AFTER_SOL")
    _digest(payload.get("gate_manifest_sha256"), "gate_manifest_sha256")
    if not isinstance(payload.get("gate_manifest_path"), str) or not payload["gate_manifest_path"].strip():
        raise ValueError("gate_manifest_path is required")
    count = payload.get("evidence_rework_count")
    if count not in {0, 1}:
        raise ValueError("evidence_rework_count must be 0 or 1")
    missing = payload.get("missing_evidence")
    conflicts = payload.get("evidence_conflicts")
    if not isinstance(missing, list) or not isinstance(conflicts, list):
        raise ValueError("missing_evidence and evidence_conflicts must be lists")

    decision = payload["decision"]
    reason = payload.get("escalation_reason")
    refs = payload.get("disputed_evidence_refs", [])
    if decision == "LUNA_ACCEPTANCE":
        if missing or conflicts or reason or refs:
            raise ValueError("accepted evidence must be complete and coherent")
    elif decision == "REWORK_REQUIRED":
        if not missing and not conflicts:
            raise ValueError("rework requires an exact evidence issue")
        if reason or refs:
            raise ValueError("rework must not use a Sol escalation payload")
    else:
        if payload.get("stage") != "ROUTINE":
            raise ValueError("Sol escalation begins from routine Luna acceptance")
        if reason == INSUFFICIENT:
            if count != 1 or not missing or conflicts:
                raise ValueError("insufficient evidence requires exactly one Luna evidence rework")
            prior = payload.get("prior_luna_rework")
            if not isinstance(prior, dict) or not prior.get("path"):
                raise ValueError("insufficient evidence escalation requires a prior Luna rework record")
            _digest(prior.get("sha256"), "prior_luna_rework.sha256")
        elif reason == CONFLICT:
            if not conflicts:
                raise ValueError("conflict escalation requires unresolved evidence conflicts")
            check = payload.get("deterministic_check")
            if not isinstance(check, dict) or not check.get("path"):
                raise ValueError("conflict escalation requires a deterministic conflict record")
            _digest(check.get("sha256"), "deterministic_check.sha256")
        else:
            raise ValueError("Sol escalation reason is not allowed")
        if not isinstance(refs, list) or not refs:
            raise ValueError("Sol escalation requires disputed evidence refs")
        digests: set[str] = set()
        for ref in refs:
            if not isinstance(ref, dict) or not ref.get("path"):
                raise ValueError("each disputed evidence ref requires a path")
            digests.add(_digest(ref.get("sha256"), "disputed evidence sha256"))
        if reason == CONFLICT and len(digests) < 2:
            raise ValueError("conflict escalation requires two distinct evidence hashes")
        if payload.get("return_to") != "LUNA_FINAL_ACCEPTANCE":
            raise ValueError("Sol escalation must return to Luna final acceptance")

    ruling = payload.get("sol_ruling")
    if payload["stage"] == "FINAL_AFTER_SOL":
        if decision != "LUNA_ACCEPTANCE" or not isinstance(ruling, dict):
            raise ValueError("final-after-Sol stage requires a Luna acceptance and Sol ruling")
        _digest(ruling.get("sha256"), "sol_ruling.sha256")
        if not isinstance(ruling.get("path"), str) or not ruling["path"].strip():
            raise ValueError("sol_ruling.path is required")
    elif ruling not in (None, {}):
        raise ValueError("routine acceptance must not include a Sol ruling")


def validate_file(path: Path, *, require_current: bool = True) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("acceptance record must be a JSON object")
    validate_payload(payload)
    workspace = Path(payload["workspace_root"]).resolve()
    if not workspace.is_dir():
        raise ValueError("workspace_root does not exist")
    record_root = path.resolve().parent
    if require_current:
        if path.name != "luna_acceptance.json":
            raise ValueError("current acceptance must use canonical luna_acceptance.json")
        acceptance_files = list(record_root.glob("luna_acceptance*.json"))
        if [item.resolve() for item in acceptance_files] != [path.resolve()]:
            raise ValueError("task packet must contain exactly one current Luna acceptance record")
        spec = record_root / "spec.md"
        if not spec.is_file():
            raise ValueError("current acceptance requires task packet spec.md")
        status_match = re.search(r"^STATUS:\s*(\S+)", spec.read_text(encoding="utf-8"), re.MULTILINE)
        expected_status = {
            "LUNA_ACCEPTANCE": "LUNA_ACCEPTED_CODE_ONLY",
            "REWORK_REQUIRED": "LUNA_REWORK_REQUIRED",
            "SOL_ESCALATION_REQUEST": "SOL_ESCALATION_REQUEST",
        }[payload["decision"]]
        if not status_match or status_match.group(1) != expected_status:
            raise ValueError("task packet status does not point to the current Luna decision")
    gate_path = _rooted(record_root, payload["gate_manifest_path"], "gate_manifest_path")
    if _sha256(gate_path) != payload["gate_manifest_sha256"]:
        raise ValueError("gate manifest hash does not match")
    try:
        from scripts.validate_automated_gate_manifest import validate_file as validate_gate
    except ModuleNotFoundError:
        from validate_automated_gate_manifest import validate_file as validate_gate
    validate_gate(gate_path, execute_commands=False)
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    if gate.get("task_id") != payload["task_id"]:
        raise ValueError("acceptance task differs from gate task")

    for ref in payload.get("disputed_evidence_refs", []):
        evidence = _rooted(record_root, ref["path"], "disputed evidence path")
        if _sha256(evidence) != ref["sha256"]:
            raise ValueError("disputed evidence hash does not match")
    if payload.get("decision") == "SOL_ESCALATION_REQUEST":
        if payload["escalation_reason"] == INSUFFICIENT:
            prior_info = payload["prior_luna_rework"]
            prior_path = _rooted(record_root, prior_info["path"], "prior_luna_rework.path")
            if _sha256(prior_path) != prior_info["sha256"]:
                raise ValueError("prior Luna rework hash does not match")
            prior = json.loads(prior_path.read_text(encoding="utf-8"))
            if (
                prior.get("task_id") != payload["task_id"]
                or prior.get("decision") != "REWORK_REQUIRED"
                or prior.get("model_role") != "acceptance"
                or prior.get("model") != "gpt-5.6-luna"
                or prior.get("gate_manifest_sha256") == payload["gate_manifest_sha256"]
            ):
                raise ValueError("prior Luna rework does not prove one bounded evidence rework")
            validate_file(prior_path, require_current=False)
        else:
            check_info = payload["deterministic_check"]
            check_path = _rooted(record_root, check_info["path"], "deterministic_check.path")
            if _sha256(check_path) != check_info["sha256"]:
                raise ValueError("deterministic conflict record hash does not match")
            check = json.loads(check_path.read_text(encoding="utf-8"))
            expected_hashes = {ref["sha256"] for ref in payload["disputed_evidence_refs"]}
            if (
                check.get("task_id") != payload["task_id"]
                or check.get("result") != "CONFLICT"
                or check.get("resolved") is not False
                or set(check.get("evidence_sha256s", [])) != expected_hashes
            ):
                raise ValueError("deterministic check does not prove an unresolved evidence conflict")
    if payload["stage"] == "FINAL_AFTER_SOL":
        ruling_info = payload["sol_ruling"]
        ruling_path = _rooted(record_root, ruling_info["path"], "sol_ruling.path")
        if _sha256(ruling_path) != ruling_info["sha256"]:
            raise ValueError("Sol ruling hash does not match")
        ruling = json.loads(ruling_path.read_text(encoding="utf-8"))
        if (
            ruling.get("task_id") != payload["task_id"]
            or ruling.get("reviewer_model") != "gpt-5.6-sol"
            or ruling.get("scope") != "DISPUTED_EVIDENCE_SLICE_ONLY"
            or ruling.get("return_to") != "LUNA_FINAL_ACCEPTANCE"
        ):
            raise ValueError("Sol ruling is not a narrow return-to-Luna record")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("record", type=Path)
    args = parser.parse_args()
    validate_file(args.record)
    print("Luna acceptance record: VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
