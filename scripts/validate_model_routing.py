#!/usr/bin/env python3
"""Validate the durable Sol/Luna collaboration routing contract."""

from __future__ import annotations

import argparse
from pathlib import Path
import tomllib

import yaml


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_ROLE_CONFIGS = {
    "coordinator": ("agents/sol-coordinator.toml", "gpt-5.6-sol", "high"),
    "dispatcher": ("agents/luna-dispatcher.toml", "gpt-5.6-luna", "medium"),
    "executor": ("agents/luna-executor.toml", "gpt-5.6-luna", "medium"),
    "strategy_research_executor": (
        "agents/sol-strategy-research-executor.toml",
        "gpt-5.6-sol",
        "high",
    ),
    "acceptance": ("agents/luna-acceptance.toml", "gpt-5.6-luna", "high"),
    "audit": ("agents/luna-audit.toml", "gpt-5.6-luna", "high"),
}
EXPECTED_DEFAULT_PATH = (
    "SOL_MANAGER",
    "LUNA_DISPATCHER",
    "LUNA_EXECUTOR",
    "AUTOMATED_GATE",
    "LUNA_ACCEPTANCE",
)
EXPECTED_STRATEGY_PATH = (
    "SOL_MANAGER",
    "SOL_STRATEGY_RESEARCH_EXECUTOR",
    "AUTOMATED_GATE",
    "LUNA_ACCEPTANCE",
)
EXPECTED_STRATEGY_THREAD_BINDING = {
    "thread_id": "019f3881-5293-74a1-8535-814bd83c8681",
    "title": "Strategy Work — Sol Research",
    "target_project": "strategy_work",
    "model_role": "strategy_research_executor",
    "model": "gpt-5.6-sol",
    "reasoning_effort": "high",
    "manager_callback_target": "019f4c70-cac3-7211-8e04-47b8b51c819e",
    "dispatcher_thread_id": "019f4ca0-2054-77e3-9559-7005c0f9b565",
    "acceptance_role": "codex_acceptance",
    "acceptance_model": "gpt-5.6-luna",
    "acceptance_reasoning_effort": "high",
    "acceptance_write_policy": "read-only",
}
EXPECTED_STRATEGY_MUST_NOT = (
    "act as Quant-Dispatcher or maintain the controller queue",
    "replace automated gates or Luna final acceptance",
)
EXPECTED_STRATEGY_RESULT_STATUSES = ("SOL_STRATEGY_RESEARCH_COMPLETE", "BLOCKED")
EXPECTED_STRATEGY_CONTEXT_RULE = (
    "preserve prior research, reuse the task packet, and send only the changed delta"
)
EXPECTED_STRATEGY_DETERMINISTIC_FAILURE = (
    "return to the Sol strategy research executor or BLOCKED"
)
EXPECTED_ESCALATIONS = {
    "EVIDENCE_INSUFFICIENT_AFTER_ONE_BOUNDED_LUNA_REWORK",
    "EVIDENCE_CONFLICT_UNRESOLVED_BY_DETERMINISTIC_CHECKS",
}


def _load_toml(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def validate(root: Path = ROOT) -> None:
    config_path = root / ".codex" / "config.toml"
    config = _load_toml(config_path)
    if config.get("model") != "gpt-5.6-sol":
        raise ValueError("controller default model must be gpt-5.6-sol")
    if config.get("model_reasoning_effort") != "high":
        raise ValueError("controller Sol reasoning effort must be high")

    agent_configs = config.get("agents", {})
    expected_agent_keys = {"max_threads", "max_depth", *EXPECTED_ROLE_CONFIGS}
    if set(agent_configs) != expected_agent_keys:
        raise ValueError("agent config keys must be exact; extra aliases are forbidden")
    if agent_configs.get("max_threads") != 4 or agent_configs.get("max_depth") != 1:
        raise ValueError("agent concurrency settings must remain max_threads=4 and max_depth=1")
    for role, (relative_path, model, effort) in EXPECTED_ROLE_CONFIGS.items():
        declared = agent_configs.get(role, {})
        if declared.get("config_file") != relative_path:
            raise ValueError(f"{role} must use {relative_path}")
        layer = _load_toml(config_path.parent / relative_path)
        if layer.get("model") != model or layer.get("model_reasoning_effort") != effort:
            raise ValueError(f"{role} model layer must be {model}/{effort}")
        if role in {"acceptance", "audit"}:
            if layer.get("sandbox_mode") != "read-only" or layer.get("approval_policy") != "never":
                raise ValueError(f"{role} role must be enforced read-only with no approval escalation")

    routing_path = root / "registry" / "model_routing.yaml"
    routing = yaml.safe_load(routing_path.read_text(encoding="utf-8"))
    if routing.get("policy_id") != "SOL_MANAGER_LUNA_DELIVERY_V2":
        raise ValueError("routing policy id must be SOL_MANAGER_LUNA_DELIVERY_V2")
    models = routing.get("codex_models", {})
    if set(models) != set(EXPECTED_ROLE_CONFIGS):
        raise ValueError("codex model roles must be exact; extra roles or aliases are forbidden")
    for role, (_, model, effort) in EXPECTED_ROLE_CONFIGS.items():
        facts = models.get(role, {})
        if facts.get("model") != model or facts.get("reasoning_effort") != effort:
            raise ValueError(f"registry {role} routing must be {model}/{effort}")
    audit = models.get("audit", {})
    if (
        audit.get("write_policy") != "read-only"
        or audit.get("sandbox_mode") != "read-only"
        or audit.get("approval_policy") != "never"
        or audit.get("context_policy") != "sha256-bound context delta required"
    ):
        raise ValueError("registry audit role must enforce read-only sandbox, no approvals, and hash-bound context")
    strategy = models.get("strategy_research_executor", {})
    if strategy.get("model_role") != "strategy_research_executor" or strategy.get("target_project") != "strategy_work":
        raise ValueError("strategy research executor must be bound to MODEL_ROLE strategy_research_executor and strategy_work")
    if tuple(strategy.get("must_not", ())) != EXPECTED_STRATEGY_MUST_NOT:
        raise ValueError("strategy research executor must_not rules must be exact")
    if tuple(strategy.get("result_statuses", ())) != EXPECTED_STRATEGY_RESULT_STATUSES:
        raise ValueError("strategy research executor result statuses must be exact")
    sol_high_roles = {
        role
        for role, facts in models.items()
        if facts.get("model") == "gpt-5.6-sol" and facts.get("reasoning_effort") == "high"
    }
    if sol_high_roles != {"coordinator", "strategy_research_executor"}:
        raise ValueError("only coordinator and strategy_research_executor may use gpt-5.6-sol/high")

    agents_registry = yaml.safe_load((root / "registry" / "agents.yaml").read_text(encoding="utf-8"))
    audit_agent = agents_registry.get("agents", {}).get("codex_audit", {})
    if (
        audit_agent.get("sandbox_mode") != "read-only"
        or audit_agent.get("approval_policy") != "never"
        or audit_agent.get("context_policy") != "task-local CONTEXT_DELTA with exact SHA-256"
        or audit_agent.get("write_policy")
        != "read-only; return findings in the task callback without filesystem writes"
    ):
        raise ValueError("Codex-Audit registry entry must be machine-enforced read-only and context-bound")

    workflow = routing.get("workflow", {})
    if tuple(workflow.get("path", ())) != EXPECTED_DEFAULT_PATH:
        raise ValueError("default workflow path must preserve Luna dispatcher and Luna executor")
    strategy_workflow = routing.get("strategy_workflow", {})
    if tuple(strategy_workflow.get("path", ())) != EXPECTED_STRATEGY_PATH:
        raise ValueError("strategy workflow path must bypass Luna dispatcher and use the Sol strategy research executor")
    if (
        strategy_workflow.get("target_project") != "strategy_work"
        or strategy_workflow.get("model_role") != "strategy_research_executor"
    ):
        raise ValueError("strategy workflow must be scoped to strategy_work and strategy_research_executor")
    if strategy_workflow.get("context_rule") != EXPECTED_STRATEGY_CONTEXT_RULE:
        raise ValueError("strategy workflow must preserve prior research with the exact context rule")
    if strategy_workflow.get("deterministic_failure") != EXPECTED_STRATEGY_DETERMINISTIC_FAILURE:
        raise ValueError("strategy deterministic failures must return to the bound research executor or BLOCKED")

    thread_bindings = routing.get("thread_bindings", {})
    if thread_bindings != {"strategy_work_research": EXPECTED_STRATEGY_THREAD_BINDING}:
        raise ValueError("active strategy_work thread binding does not match the operational contract")

    escalation = routing.get("sol_escalation", {})
    allowed = set(escalation.get("allowed_reasons", []))
    if allowed != EXPECTED_ESCALATIONS:
        raise ValueError(f"Sol escalation reasons must be exact: {sorted(EXPECTED_ESCALATIONS)}")
    if workflow.get("deterministic_failure") != "return to Luna; never use Sol":
        raise ValueError("deterministic failures must not route to Sol")
    if "Luna issues the final acceptance" not in escalation.get("return_path", ""):
        raise ValueError("final acceptance must return to Luna after Sol evidence review")

    packet_rule = (root / "runbooks" / "task_packet_validation.md").read_text(encoding="utf-8")
    if "do not pass model or thinking overrides" in packet_rule:
        raise ValueError("legacy no-model-override dispatch rule is still active")
    for required in (
        "gpt-5.6-sol",
        "gpt-5.6-luna",
        "strategy_research_executor",
        "AUTOMATED_GATE",
        "TARGET_REPO",
    ):
        if required not in packet_rule:
            raise ValueError(f"task packet validation is missing {required}")

    runbook = (root / "runbooks" / "model_routing.md").read_text(encoding="utf-8")
    for required in (
        *EXPECTED_ESCALATIONS,
        "SOL_STRATEGY_RESEARCH_EXECUTOR",
        EXPECTED_STRATEGY_THREAD_BINDING["thread_id"],
        EXPECTED_STRATEGY_THREAD_BINDING["title"],
        EXPECTED_STRATEGY_THREAD_BINDING["manager_callback_target"],
        EXPECTED_STRATEGY_THREAD_BINDING["dispatcher_thread_id"],
    ):
        if required not in runbook:
            raise ValueError(f"model routing runbook is missing {required}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    validate()
    print("model routing validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
