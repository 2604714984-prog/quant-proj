from pathlib import Path
import shutil

import pytest

from scripts import validate_model_routing as validator


ROOT = Path(__file__).resolve().parents[1]


def _copy_policy(tmp_path: Path) -> Path:
    for relative in (
        ".codex/config.toml",
        ".codex/agents/sol-coordinator.toml",
        ".codex/agents/luna-dispatcher.toml",
        ".codex/agents/luna-executor.toml",
        ".codex/agents/luna-acceptance.toml",
        "registry/model_routing.yaml",
        "runbooks/model_routing.md",
        "runbooks/task_packet_validation.md",
    ):
        source = ROOT / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return tmp_path


def test_live_model_routing_policy_passes():
    validator.validate(ROOT)


def test_executor_cannot_drift_to_sol(tmp_path):
    root = _copy_policy(tmp_path)
    executor = root / ".codex/agents/luna-executor.toml"
    executor.write_text('model = "gpt-5.6-sol"\nmodel_reasoning_effort = "medium"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="executor model layer"):
        validator.validate(root)


def test_deterministic_failure_cannot_escalate_to_sol(tmp_path):
    root = _copy_policy(tmp_path)
    policy = root / "registry/model_routing.yaml"
    payload = policy.read_text(encoding="utf-8").replace(
        'deterministic_failure: "return to Luna; never use Sol"',
        'deterministic_failure: "send to Sol"',
    )
    policy.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError, match="deterministic failures"):
        validator.validate(root)


def test_acceptance_role_cannot_enable_writes(tmp_path):
    root = _copy_policy(tmp_path)
    acceptance = root / ".codex/agents/luna-acceptance.toml"
    acceptance.write_text(
        'model = "gpt-5.6-luna"\nmodel_reasoning_effort = "high"\n'
        'sandbox_mode = "workspace-write"\napproval_policy = "never"\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="enforced read-only"):
        validator.validate(root)


def test_legacy_no_override_rule_is_rejected(tmp_path):
    root = _copy_policy(tmp_path)
    packet_rule = root / "runbooks/task_packet_validation.md"
    packet_rule.write_text(
        packet_rule.read_text(encoding="utf-8") + "\n- do not pass model or thinking overrides\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="legacy no-model-override"):
        validator.validate(root)
