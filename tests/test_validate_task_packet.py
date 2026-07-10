import hashlib
import json
from pathlib import Path

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


def test_valid_luna_executor_packet_passes(tmp_path):
    validate(_packet(tmp_path))


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
