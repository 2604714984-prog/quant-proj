#!/usr/bin/env python3
"""Validate new task packets against the Sol/Luna routing contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


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
STRATEGY_EXECUTOR_AGENT = "strategy_research_executor"
STRATEGY_EXECUTOR_FIELDS = ("EXECUTION_THREAD_ID", "EXECUTION_THREAD_TITLE")
STRATEGY_THREAD_ID = "019f3881-5293-74a1-8535-814bd83c8681"
STRATEGY_THREAD_TITLE = "Strategy Work — Sol Research"
STRATEGY_MANAGER_CALLBACK_TARGET = "019f4c70-cac3-7211-8e04-47b8b51c819e"
CODEX_AGENT_ROLE_MODEL_BINDINGS = {
    "codex_dev": ("executor", "gpt-5.6-luna", "medium"),
    STRATEGY_EXECUTOR_AGENT: ("strategy_research_executor", "gpt-5.6-sol", "high"),
    "codex_acceptance": ("acceptance", "gpt-5.6-luna", "high"),
    "codex_audit": ("audit", "gpt-5.6-luna", "high"),
}
CODEX_MODELS = {"gpt-5.6-luna", "gpt-5.6-sol"}
ALLOWED_RECOMMENDED_AGENTS = {
    *CODEX_AGENT_ROLE_MODEL_BINDINGS,
    "reasonix_db_maintainer",
    "reasonix_strategy_researcher",
    "reasonix_advisory",
    "chatgpt_external_audit",
    "human_gate",
}
ACCEPTANCE_FIELDS = (
    "AUTOMATED_GATE_MANIFEST",
    "AUTOMATED_GATE_MANIFEST_SHA256",
    "SANDBOX_MODE",
    "APPROVAL_POLICY",
)
AUDIT_FIELDS = ("SANDBOX_MODE", "APPROVAL_POLICY", "TARGET_REPO")


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


def _validate_execution_refs_and_commands(packet_dir: Path, facts: dict[str, str], label: str) -> None:
    if (
        not SHA1_RE.fullmatch(facts["SOURCE_COMMIT"])
        or not SHA1_RE.fullmatch(facts["SOURCE_TREE"])
        or len(set(facts["SOURCE_COMMIT"])) == 1
        or len(set(facts["SOURCE_TREE"])) == 1
    ):
        raise ValueError(f"{label} tasks require full source commit and tree")
    if facts["AUTOMATED_GATE_COMMANDS"] == "N/A":
        raise ValueError(f"{label} tasks require automated gate commands")
    _verify_packet_file(
        packet_dir,
        facts,
        "AUTOMATED_GATE_COMMANDS",
        "AUTOMATED_GATE_COMMANDS_SHA256",
    )


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode:
        raise ValueError((completed.stderr or completed.stdout).strip() or "target Git lookup failed")
    return completed.stdout.strip()


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
    thread_metadata_declared = any(
        re.search(rf"^{field}:\s*", spec, re.MULTILINE) for field in STRATEGY_EXECUTOR_FIELDS
    )
    if thread_metadata_declared and agent != STRATEGY_EXECUTOR_AGENT:
        raise ValueError("strategy thread metadata is reserved for RECOMMENDED_AGENT strategy_research_executor")
    if agent not in ALLOWED_RECOMMENDED_AGENTS:
        raise ValueError(f"RECOMMENDED_AGENT must be one of {sorted(ALLOWED_RECOMMENDED_AGENTS)}")
    if facts["MODEL"] in CODEX_MODELS and agent not in CODEX_AGENT_ROLE_MODEL_BINDINGS:
        raise ValueError("gpt-5.6 Codex models require a whitelisted Codex agent-role-model binding")

    route = CODEX_AGENT_ROLE_MODEL_BINDINGS.get(agent)
    routed_roles = {binding[0] for binding in CODEX_AGENT_ROLE_MODEL_BINDINGS.values()}
    if route is not None:
        actual_route = (facts["MODEL_ROLE"], facts["MODEL"], facts["REASONING_EFFORT"])
        if actual_route != route:
            label = {
                "codex_dev": "Codex-Dev",
                STRATEGY_EXECUTOR_AGENT: "Strategy research executor",
                "codex_acceptance": "Codex-Acceptance",
                "codex_audit": "Codex-Audit",
            }[agent]
            raise ValueError(f"{label} routing must begin with {route}")
    elif facts["MODEL_ROLE"] in routed_roles:
        raise ValueError(f"Codex agent routing must be one of {CODEX_AGENT_ROLE_MODEL_BINDINGS}")

    if agent in {"codex_dev", STRATEGY_EXECUTOR_AGENT, "codex_acceptance", "codex_audit"}:
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
        _validate_execution_refs_and_commands(packet_dir, facts, "Codex-Dev")
    elif agent == STRATEGY_EXECUTOR_AGENT:
        missing_strategy = [field for field in STRATEGY_EXECUTOR_FIELDS if not facts.get(field)]
        if missing_strategy:
            raise ValueError(f"missing strategy executor metadata: {missing_strategy}")
        expected = (
            "strategy_work",
            "strategy_research_executor",
            "gpt-5.6-sol",
            "high",
            "codex_acceptance",
            STRATEGY_THREAD_ID,
            STRATEGY_THREAD_TITLE,
            STRATEGY_MANAGER_CALLBACK_TARGET,
        )
        actual = (
            facts["TARGET_PROJECT"],
            facts["MODEL_ROLE"],
            facts["MODEL"],
            facts["REASONING_EFFORT"],
            facts["ACCEPTANCE_ROLE"],
            facts["EXECUTION_THREAD_ID"],
            facts["EXECUTION_THREAD_TITLE"],
            facts["CALLBACK_TARGET"],
        )
        if actual != expected:
            raise ValueError(f"Strategy research executor routing must be {expected}")
        _validate_execution_refs_and_commands(packet_dir, facts, "Strategy research executor")
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
    elif agent == "codex_audit":
        missing_audit = [field for field in AUDIT_FIELDS if not facts.get(field)]
        if missing_audit:
            raise ValueError(f"missing audit packet metadata: {missing_audit}")
        expected = ("audit", "gpt-5.6-luna", "high", "N/A", "read-only", "never")
        actual = (
            facts["MODEL_ROLE"],
            facts["MODEL"],
            facts["REASONING_EFFORT"],
            facts["ACCEPTANCE_ROLE"],
            facts["SANDBOX_MODE"],
            facts["APPROVAL_POLICY"],
        )
        if actual != expected:
            raise ValueError(f"Codex-Audit routing must be {expected}")
        if facts["AUTOMATED_GATE_COMMANDS"] != "N/A" or facts["AUTOMATED_GATE_COMMANDS_SHA256"] != "N/A":
            raise ValueError("Codex-Audit must not carry executor gate commands")
        if (
            not SHA1_RE.fullmatch(facts["SOURCE_COMMIT"])
            or not SHA1_RE.fullmatch(facts["SOURCE_TREE"])
            or len(set(facts["SOURCE_COMMIT"])) == 1
            or len(set(facts["SOURCE_TREE"])) == 1
        ):
            raise ValueError("Codex-Audit tasks require immutable target commit and tree")
        target_repo_value = facts["TARGET_REPO"]
        if any(token in target_repo_value for token in ("<", ">", "N/A", "path/to")):
            raise ValueError("Codex-Audit TARGET_REPO contains a placeholder")
        target_repo = Path(target_repo_value)
        if not target_repo.is_absolute():
            raise ValueError("Codex-Audit TARGET_REPO must be an absolute Git repository")
        target_repo = target_repo.resolve()
        if not target_repo.is_dir() or _git(target_repo, "rev-parse", "--is-inside-work-tree") != "true":
            raise ValueError("Codex-Audit TARGET_REPO must be an existing Git worktree")
        try:
            object_type = _git(target_repo, "cat-file", "-t", facts["SOURCE_COMMIT"])
            actual_tree = _git(target_repo, "show", "-s", "--format=%T", facts["SOURCE_COMMIT"])
        except ValueError as exc:
            raise ValueError("Codex-Audit target commit is unavailable in TARGET_REPO") from exc
        if object_type != "commit" or actual_tree != facts["SOURCE_TREE"]:
            raise ValueError("Codex-Audit target commit/tree does not match TARGET_REPO")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet_dir", type=Path)
    args = parser.parse_args()
    validate(args.packet_dir)
    print("task packet validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
