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
        ".codex/agents/sol-strategy-research-executor.toml",
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


def test_strategy_research_executor_is_exact_sol_high(tmp_path):
    root = _copy_policy(tmp_path)
    strategy = root / ".codex/agents/sol-strategy-research-executor.toml"
    strategy.write_text('model = "gpt-5.6-luna"\nmodel_reasoning_effort = "high"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="strategy_research_executor model layer"):
        validator.validate(root)


def test_strategy_workflow_cannot_become_luna_dispatch(tmp_path):
    root = _copy_policy(tmp_path)
    policy = root / "registry/model_routing.yaml"
    payload = policy.read_text(encoding="utf-8").replace(
        '    - "SOL_STRATEGY_RESEARCH_EXECUTOR"',
        '    - "LUNA_DISPATCHER"',
    )
    policy.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError, match="strategy workflow path"):
        validator.validate(root)


def test_active_strategy_thread_binding_cannot_drift(tmp_path):
    root = _copy_policy(tmp_path)
    policy = root / "registry/model_routing.yaml"
    payload = policy.read_text(encoding="utf-8").replace(
        'thread_id: "019f3881-5293-74a1-8535-814bd83c8681"',
        'thread_id: "019f3881-5293-74a1-8535-814bd83c8682"',
    )
    policy.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError, match="active strategy_work thread binding"):
        validator.validate(root)


def test_extra_agent_alias_is_rejected(tmp_path):
    root = _copy_policy(tmp_path)
    config = root / ".codex/config.toml"
    config.write_text(
        config.read_text(encoding="utf-8")
        + '\n[agents.strategy_alias]\nconfig_file = "agents/sol-strategy-research-executor.toml"\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="extra aliases"):
        validator.validate(root)


def test_extra_codex_model_role_is_rejected(tmp_path):
    root = _copy_policy(tmp_path)
    policy = root / "registry/model_routing.yaml"
    payload = policy.read_text(encoding="utf-8").replace(
        "\nworkflow:\n",
        '\n  strategy_alias:\n    model: "gpt-5.6-luna"\n    reasoning_effort: "medium"\n\nworkflow:\n',
    )
    policy.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError, match="extra roles or aliases"):
        validator.validate(root)


def test_extra_thread_binding_is_rejected(tmp_path):
    root = _copy_policy(tmp_path)
    policy = root / "registry/model_routing.yaml"
    payload = policy.read_text(encoding="utf-8").replace(
        "\nsol_escalation:\n",
        "\n  conflicting_alias: {}\n\nsol_escalation:\n",
    )
    policy.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError, match="active strategy_work thread binding"):
        validator.validate(root)


@pytest.mark.parametrize(
    ("old", "new", "error"),
    (
        (
            '      - "act as Quant-Dispatcher or maintain the controller queue"',
            '      - "may dispatch research"',
            "must_not rules",
        ),
        (
            'result_statuses: ["SOL_STRATEGY_RESEARCH_COMPLETE", "BLOCKED"]',
            'result_statuses: ["LUNA_EXECUTION_COMPLETE", "BLOCKED"]',
            "result statuses",
        ),
        (
            'context_rule: "preserve prior research, reuse the task packet, and send only the changed delta"',
            'context_rule: "send the changed delta"',
            "preserve prior research",
        ),
        (
            'deterministic_failure: "return to the Sol strategy research executor or BLOCKED"',
            'deterministic_failure: "send to Sol Manager"',
            "strategy deterministic failures",
        ),
    ),
)
def test_strategy_contract_fields_are_exact(tmp_path, old, new, error):
    root = _copy_policy(tmp_path)
    policy = root / "registry/model_routing.yaml"
    payload = policy.read_text(encoding="utf-8").replace(old, new)
    assert payload != policy.read_text(encoding="utf-8")
    policy.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError, match=error):
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
