#!/usr/bin/env python3
"""Validate new task packets against the Sol/Luna routing contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


REQUIRED_FILES = ("spec.md", "handoff.md", "human_gate.md")
REQUIRED_FIELDS = (
    "TASK_ID",
    "STATUS",
    "TARGET_PROJECT",
    "RECOMMENDED_AGENT",
    "MODEL_ROLE",
    "MODEL",
    "REASONING_EFFORT",
    "SOURCE_COMMIT",
    "SOURCE_TREE",
    "AUTOMATED_GATE_COMMANDS",
    "AUTOMATED_GATE_COMMANDS_SHA256",
    "CALLBACK_TARGET",
    "ACCEPTANCE_ROLE",
    "CONTEXT_DELTA",
    "CONTEXT_DELTA_SHA256",
)
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
THREAD_ID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
RETIRED_CALLBACK_TARGETS = {"019f3830-4b44-7a83-944d-247a0d4dc169"}
ACCEPTANCE_FIELDS = (
    "AUTOMATED_GATE_MANIFEST",
    "AUTOMATED_GATE_MANIFEST_SHA256",
    "SANDBOX_MODE",
    "APPROVAL_POLICY",
)


def _metadata(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^([A-Z][A-Z0-9_]*):\s*(.+?)\s*$", line)
        if match:
            values[match.group(1)] = match.group(2).strip("` ")
    return values


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _packet_file(packet_dir: Path, value: str, field: str) -> Path:
    if any(token in value for token in ("<", ">", "N/A", "path/to")):
        raise ValueError(f"{field} contains a placeholder")
    candidate = (packet_dir / value).resolve()
    root = packet_dir.resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError(f"{field} escapes task packet")
    if not candidate.is_file():
        raise ValueError(f"{field} file does not exist: {value}")
    return candidate


def _verify_packet_file(packet_dir: Path, facts: dict[str, str], path_field: str, hash_field: str) -> Path:
    path = _packet_file(packet_dir, facts[path_field], path_field)
    expected = facts[hash_field]
    if not SHA256_RE.fullmatch(expected) or len(set(expected)) == 1:
        raise ValueError(f"{hash_field} must be a non-placeholder full SHA-256")
    if _sha256(path) != expected:
        raise ValueError(f"{hash_field} does not match {path_field}")
    return path


def validate(packet_dir: Path) -> None:
    for name in REQUIRED_FILES:
        if not (packet_dir / name).is_file():
            raise ValueError(f"missing task packet file: {name}")
    spec = (packet_dir / "spec.md").read_text(encoding="utf-8")
    facts = _metadata(spec)
    missing = [field for field in REQUIRED_FIELDS if not facts.get(field)]
    if missing:
        raise ValueError(f"missing task packet metadata: {missing}")
    for field in REQUIRED_FIELDS:
        if any(token in facts[field] for token in ("<", ">")):
            raise ValueError(f"task packet metadata contains placeholder: {field}")
    if not THREAD_ID_RE.fullmatch(facts["CALLBACK_TARGET"]):
        raise ValueError("CALLBACK_TARGET must be a concrete Codex task UUID")
    if facts["CALLBACK_TARGET"] in RETIRED_CALLBACK_TARGETS:
        raise ValueError("callback target is a retired legacy dispatcher")

    agent = facts["RECOMMENDED_AGENT"]
    if agent in {"codex_dev", "codex_acceptance"}:
        _verify_packet_file(packet_dir, facts, "CONTEXT_DELTA", "CONTEXT_DELTA_SHA256")

    if agent == "codex_dev":
        expected = ("executor", "gpt-5.6-luna", "medium", "codex_acceptance")
        actual = (
            facts["MODEL_ROLE"],
            facts["MODEL"],
            facts["REASONING_EFFORT"],
            facts["ACCEPTANCE_ROLE"],
        )
        if actual != expected:
            raise ValueError(f"Codex-Dev routing must be {expected}")
        if (
            not SHA1_RE.fullmatch(facts["SOURCE_COMMIT"])
            or not SHA1_RE.fullmatch(facts["SOURCE_TREE"])
            or len(set(facts["SOURCE_COMMIT"])) == 1
            or len(set(facts["SOURCE_TREE"])) == 1
        ):
            raise ValueError("Codex-Dev tasks require full source commit and tree")
        if facts["AUTOMATED_GATE_COMMANDS"] == "N/A":
            raise ValueError("Codex-Dev tasks require automated gate commands")
        _verify_packet_file(
            packet_dir,
            facts,
            "AUTOMATED_GATE_COMMANDS",
            "AUTOMATED_GATE_COMMANDS_SHA256",
        )
    elif agent == "codex_acceptance":
        missing_acceptance = [field for field in ACCEPTANCE_FIELDS if not facts.get(field)]
        if missing_acceptance:
            raise ValueError(f"missing acceptance packet metadata: {missing_acceptance}")
        expected = ("acceptance", "gpt-5.6-luna", "high", "codex_acceptance", "read-only", "never")
        actual = (
            facts["MODEL_ROLE"],
            facts["MODEL"],
            facts["REASONING_EFFORT"],
            facts["ACCEPTANCE_ROLE"],
            facts["SANDBOX_MODE"],
            facts["APPROVAL_POLICY"],
        )
        if actual != expected:
            raise ValueError(f"Codex-Acceptance routing must be {expected}")
        if (
            not SHA1_RE.fullmatch(facts["SOURCE_COMMIT"])
            or not SHA1_RE.fullmatch(facts["SOURCE_TREE"])
            or len(set(facts["SOURCE_COMMIT"])) == 1
            or len(set(facts["SOURCE_TREE"])) == 1
        ):
            raise ValueError("Codex-Acceptance tasks require full result commit and tree")
        manifest = _verify_packet_file(
            packet_dir,
            facts,
            "AUTOMATED_GATE_MANIFEST",
            "AUTOMATED_GATE_MANIFEST_SHA256",
        )
        try:
            from scripts.validate_automated_gate_manifest import validate_file as validate_gate
        except ModuleNotFoundError:  # Direct execution from scripts/.
            from validate_automated_gate_manifest import validate_file as validate_gate
        validate_gate(manifest)
        gate = json.loads(manifest.read_text(encoding="utf-8"))
        if gate.get("task_id") != facts["TASK_ID"]:
            raise ValueError("acceptance packet task id must match automated gate")
        result = gate.get("result", {})
        if result.get("commit") != facts["SOURCE_COMMIT"] or result.get("tree") != facts["SOURCE_TREE"]:
            raise ValueError("acceptance source refs must match automated gate result refs")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet_dir", type=Path)
    args = parser.parse_args()
    validate(args.packet_dir)
    print("task packet validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
