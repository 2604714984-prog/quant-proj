import hashlib
import json
from pathlib import Path
import re
import subprocess

import pytest

from scripts.validate_task_packet import validate


SHA = "0123456789abcdef0123456789abcdef01234567"
CALLBACK = "019f4c70-cac3-7211-8e04-47b8b51c819e"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _packet(tmp_path: Path) -> Path:
    delta = tmp_path / "context_delta.md"
    gate = tmp_path / "gate_commands.txt"
    delta.write_text("new bounded delta", encoding="utf-8")
    gate.write_text("pytest\ngit diff --check\n", encoding="utf-8")
    spec = f"""# Task

TASK_ID: TASK-1
STATUS: BACKLOG
TARGET_PROJECT: a_share_monitor
RECOMMENDED_AGENT: codex_dev
MODEL_ROLE: executor
MODEL: gpt-5.6-luna
REASONING_EFFORT: medium
SOURCE_COMMIT: {SHA}
SOURCE_TREE: {SHA}
AUTOMATED_GATE_COMMANDS: gate_commands.txt
AUTOMATED_GATE_COMMANDS_SHA256: {_digest(gate)}
CALLBACK_TARGET: {CALLBACK}
ACCEPTANCE_ROLE: codex_acceptance
CONTEXT_DELTA: context_delta.md
CONTEXT_DELTA_SHA256: {_digest(delta)}
"""
    (tmp_path / "spec.md").write_text(spec, encoding="utf-8")
    (tmp_path / "handoff.md").write_text("handoff", encoding="utf-8")
    (tmp_path / "human_gate.md").write_text("not required", encoding="utf-8")
    return tmp_path


def _strategy_packet(tmp_path: Path) -> Path:
    packet = _packet(tmp_path)
    spec = packet / "spec.md"
    payload = spec.read_text(encoding="utf-8")
    payload = payload.replace("TARGET_PROJECT: a_share_monitor", "TARGET_PROJECT: strategy_work")
    payload = payload.replace("RECOMMENDED_AGENT: codex_dev", "RECOMMENDED_AGENT: strategy_research_executor")
    payload = payload.replace("MODEL_ROLE: executor", "MODEL_ROLE: strategy_research_executor")
    payload = payload.replace("MODEL: gpt-5.6-luna", "MODEL: gpt-5.6-sol")
    payload = payload.replace("REASONING_EFFORT: medium", "REASONING_EFFORT: high")
    payload = payload.replace(
        "CONTEXT_DELTA: context_delta.md",
        "EXECUTION_THREAD_ID: 019f3881-5293-74a1-8535-814bd83c8681\n"
        "EXECUTION_THREAD_TITLE: Strategy Work — Sol Research\n"
        "CONTEXT_DELTA: context_delta.md",
    )
    spec.write_text(payload, encoding="utf-8")
    return packet


def _audit_packet(tmp_path: Path) -> Path:
    packet = _packet(tmp_path)
    target = tmp_path / "audit-target"
    target.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=target, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=target, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=target, check=True)
    (target / "tracked.txt").write_text("target\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=target, check=True)
    subprocess.run(["git", "commit", "-qm", "target"], cwd=target, check=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=target, text=True).strip()
    tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=target, text=True).strip()
    spec = packet / "spec.md"
    payload = spec.read_text(encoding="utf-8")
    payload = payload.replace("RECOMMENDED_AGENT: codex_dev", "RECOMMENDED_AGENT: codex_audit")
    payload = payload.replace("MODEL_ROLE: executor", "MODEL_ROLE: audit")
    payload = payload.replace("REASONING_EFFORT: medium", "REASONING_EFFORT: high")
    payload = payload.replace("AUTOMATED_GATE_COMMANDS: gate_commands.txt", "AUTOMATED_GATE_COMMANDS: N/A")
    payload = payload.replace(
        f"AUTOMATED_GATE_COMMANDS_SHA256: {_digest(packet / 'gate_commands.txt')}",
        "AUTOMATED_GATE_COMMANDS_SHA256: N/A",
    )
    payload = payload.replace("ACCEPTANCE_ROLE: codex_acceptance", "ACCEPTANCE_ROLE: N/A")
    payload = payload.replace(f"SOURCE_COMMIT: {SHA}", f"SOURCE_COMMIT: {commit}")
    payload = payload.replace(f"SOURCE_TREE: {SHA}", f"SOURCE_TREE: {tree}")
    payload += f"SANDBOX_MODE: read-only\nAPPROVAL_POLICY: never\nTARGET_REPO: {target}\n"
    spec.write_text(payload, encoding="utf-8")
    return packet


def test_valid_luna_executor_packet_passes(tmp_path):
    validate(_packet(tmp_path))


def test_valid_sol_strategy_research_executor_packet_passes(tmp_path):
    validate(_strategy_packet(tmp_path))


def test_valid_codex_audit_packet_is_read_only_and_context_bound(tmp_path):
    validate(_audit_packet(tmp_path))


@pytest.mark.parametrize(
    ("old", "new"),
    (
        ("SANDBOX_MODE: read-only", "SANDBOX_MODE: workspace-write"),
        ("APPROVAL_POLICY: never", "APPROVAL_POLICY: on-request"),
    ),
)
def test_codex_audit_packet_rejects_write_or_approval_escalation(tmp_path, old, new):
    packet = _audit_packet(tmp_path)
    spec = packet / "spec.md"
    spec.write_text(spec.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
    with pytest.raises(ValueError, match="Codex-Audit routing"):
        validate(packet)


def test_codex_audit_packet_rejects_tampered_context_delta(tmp_path):
    packet = _audit_packet(tmp_path)
    (packet / "context_delta.md").write_text("unbound expanded scope", encoding="utf-8")
    with pytest.raises(ValueError, match="does not match"):
        validate(packet)


def test_codex_audit_packet_rejects_executor_gate_commands(tmp_path):
    packet = _audit_packet(tmp_path)
    spec = packet / "spec.md"
    payload = spec.read_text(encoding="utf-8")
    payload = payload.replace("AUTOMATED_GATE_COMMANDS: N/A", "AUTOMATED_GATE_COMMANDS: gate_commands.txt")
    payload = payload.replace(
        "AUTOMATED_GATE_COMMANDS_SHA256: N/A",
        f"AUTOMATED_GATE_COMMANDS_SHA256: {_digest(packet / 'gate_commands.txt')}",
    )
    spec.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError, match="must not carry executor gate commands"):
        validate(packet)


def test_codex_audit_packet_rejects_commit_absent_from_target_repo(tmp_path):
    packet = _audit_packet(tmp_path)
    spec = packet / "spec.md"
    payload = re.sub(
        r"SOURCE_COMMIT: [0-9a-f]{40}",
        "SOURCE_COMMIT: fedcba9876543210fedcba9876543210fedcba98",
        spec.read_text(encoding="utf-8"),
    )
    spec.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError, match="target commit is unavailable"):
        validate(packet)


def test_codex_audit_packet_rejects_tree_mismatch(tmp_path):
    packet = _audit_packet(tmp_path)
    spec = packet / "spec.md"
    payload = re.sub(
        r"SOURCE_TREE: [0-9a-f]{40}",
        "SOURCE_TREE: abcdef0123456789abcdef0123456789abcdef01",
        spec.read_text(encoding="utf-8"),
    )
    spec.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError, match="commit/tree does not match"):
        validate(packet)


def test_codex_audit_packet_requires_target_repo(tmp_path):
    packet = _audit_packet(tmp_path)
    spec = packet / "spec.md"
    payload = re.sub(
        r"^TARGET_REPO:.*\n",
        "",
        spec.read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
    spec.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError, match="missing audit packet metadata"):
        validate(packet)


def test_strategy_research_executor_requires_exact_role_model_and_thread(tmp_path):
    packet = _strategy_packet(tmp_path)
    spec = packet / "spec.md"
    spec.write_text(
        spec.read_text(encoding="utf-8").replace("MODEL: gpt-5.6-sol", "MODEL: gpt-5.6-luna"),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Strategy research executor routing"):
        validate(packet)

    packet = _strategy_packet(tmp_path)
    spec.write_text(
        spec.read_text(encoding="utf-8").replace(
            "EXECUTION_THREAD_ID: 019f3881-5293-74a1-8535-814bd83c8681",
            "EXECUTION_THREAD_ID: 019f3881-5293-74a1-8535-814bd83c8682",
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Strategy research executor routing"):
        validate(packet)


@pytest.mark.parametrize(
    ("agent", "role", "model", "effort"),
    (
        ("codex_dev", "executor", "gpt-5.6-luna", "medium"),
        ("luna_dispatcher", "dispatcher", "gpt-5.6-luna", "medium"),
    ),
)
def test_non_strategy_agent_cannot_claim_reserved_strategy_thread(
    tmp_path, agent, role, model, effort
):
    packet = _strategy_packet(tmp_path)
    spec = packet / "spec.md"
    payload = spec.read_text(encoding="utf-8")
    payload = payload.replace("RECOMMENDED_AGENT: strategy_research_executor", f"RECOMMENDED_AGENT: {agent}")
    payload = payload.replace("MODEL_ROLE: strategy_research_executor", f"MODEL_ROLE: {role}")
    payload = payload.replace("MODEL: gpt-5.6-sol", f"MODEL: {model}")
    payload = payload.replace("REASONING_EFFORT: high", f"REASONING_EFFORT: {effort}")
    spec.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError, match="strategy thread metadata is reserved"):
        validate(packet)


def test_non_strategy_agent_cannot_declare_any_execution_thread_metadata(tmp_path):
    packet = _packet(tmp_path)
    spec = packet / "spec.md"
    spec.write_text(
        spec.read_text(encoding="utf-8") + "EXECUTION_THREAD_ID: 11111111-1111-1111-1111-111111111111\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="strategy thread metadata is reserved"):
        validate(packet)


def test_unknown_codex_agent_alias_is_rejected(tmp_path):
    packet = _packet(tmp_path)
    spec = packet / "spec.md"
    spec.write_text(
        spec.read_text(encoding="utf-8").replace("RECOMMENDED_AGENT: codex_dev", "RECOMMENDED_AGENT: luna_executor"),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="RECOMMENDED_AGENT must be one of"):
        validate(packet)


def test_codex_agent_cannot_borrow_another_role_model_binding(tmp_path):
    packet = _packet(tmp_path)
    spec = packet / "spec.md"
    spec.write_text(
        spec.read_text(encoding="utf-8").replace("RECOMMENDED_AGENT: codex_dev", "RECOMMENDED_AGENT: codex_audit"),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Codex-Audit routing"):
        validate(packet)


def test_non_codex_agent_cannot_borrow_a_codex_model(tmp_path):
    packet = _packet(tmp_path)
    spec = packet / "spec.md"
    payload = spec.read_text(encoding="utf-8")
    payload = payload.replace("RECOMMENDED_AGENT: codex_dev", "RECOMMENDED_AGENT: human_gate")
    payload = payload.replace("MODEL_ROLE: executor", "MODEL_ROLE: coordinator")
    spec.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError, match="whitelisted Codex agent-role-model"):
        validate(packet)


def test_missing_model_field_fails(tmp_path):
    packet = _packet(tmp_path)
    spec = packet / "spec.md"
    spec.write_text(spec.read_text(encoding="utf-8").replace("MODEL: gpt-5.6-luna\n", ""), encoding="utf-8")
    with pytest.raises(ValueError, match="missing task packet metadata"):
        validate(packet)


def test_executor_cannot_use_sol(tmp_path):
    packet = _packet(tmp_path)
    spec = packet / "spec.md"
    spec.write_text(spec.read_text(encoding="utf-8").replace("MODEL: gpt-5.6-luna", "MODEL: gpt-5.6-sol"), encoding="utf-8")
    with pytest.raises(ValueError, match="Codex-Dev routing"):
        validate(packet)


def test_retired_dispatcher_callback_is_rejected(tmp_path):
    packet = _packet(tmp_path)
    spec = packet / "spec.md"
    spec.write_text(
        spec.read_text(encoding="utf-8").replace(
            f"CALLBACK_TARGET: {CALLBACK}",
            "CALLBACK_TARGET: 019f3830-4b44-7a83-944d-247a0d4dc169",
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="retired legacy dispatcher"):
        validate(packet)


def test_code_task_requires_immutable_source_ref(tmp_path):
    packet = _packet(tmp_path)
    spec = packet / "spec.md"
    spec.write_text(spec.read_text(encoding="utf-8").replace(f"SOURCE_TREE: {SHA}", "SOURCE_TREE: N/A"), encoding="utf-8")
    with pytest.raises(ValueError, match="full source commit and tree"):
        validate(packet)


def test_placeholder_and_tampered_context_delta_are_rejected(tmp_path):
    packet = _packet(tmp_path)
    spec = packet / "spec.md"
    spec.write_text(
        spec.read_text(encoding="utf-8").replace("AUTOMATED_GATE_COMMANDS: gate_commands.txt", "AUTOMATED_GATE_COMMANDS: <commands>"),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="placeholder"):
        validate(packet)

    packet = _packet(tmp_path)
    (packet / "context_delta.md").write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="does not match"):
        validate(packet)


def test_acceptance_packet_is_read_only_and_bound_to_gate(tmp_path, monkeypatch):
    delta = tmp_path / "context_delta.md"
    delta.write_text("review only the new gate", encoding="utf-8")
    gate = tmp_path / "gate.json"
    gate.write_text(json.dumps({"task_id": "TASK-1", "result": {"commit": SHA, "tree": SHA}}), encoding="utf-8")
    (tmp_path / "spec.md").write_text(
        f"""TASK_ID: TASK-1
STATUS: BACKLOG
TARGET_PROJECT: a_share_monitor
RECOMMENDED_AGENT: codex_acceptance
MODEL_ROLE: acceptance
MODEL: gpt-5.6-luna
REASONING_EFFORT: high
SOURCE_COMMIT: {SHA}
SOURCE_TREE: {SHA}
AUTOMATED_GATE_COMMANDS: N/A
AUTOMATED_GATE_COMMANDS_SHA256: N/A
CALLBACK_TARGET: {CALLBACK}
ACCEPTANCE_ROLE: codex_acceptance
CONTEXT_DELTA: context_delta.md
CONTEXT_DELTA_SHA256: {_digest(delta)}
AUTOMATED_GATE_MANIFEST: gate.json
AUTOMATED_GATE_MANIFEST_SHA256: {_digest(gate)}
SANDBOX_MODE: read-only
APPROVAL_POLICY: never
""",
        encoding="utf-8",
    )
    (tmp_path / "handoff.md").write_text("handoff", encoding="utf-8")
    (tmp_path / "human_gate.md").write_text("not required", encoding="utf-8")
    monkeypatch.setattr("scripts.validate_automated_gate_manifest.validate_file", lambda _: None)
    validate(tmp_path)

    spec = tmp_path / "spec.md"
    spec.write_text(spec.read_text(encoding="utf-8").replace("SANDBOX_MODE: read-only", "SANDBOX_MODE: workspace-write"), encoding="utf-8")
    with pytest.raises(ValueError, match="Codex-Acceptance routing"):
        validate(tmp_path)
