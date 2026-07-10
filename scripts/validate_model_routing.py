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
    "acceptance": ("agents/luna-acceptance.toml", "gpt-5.6-luna", "high"),
}
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
    for role, (relative_path, model, effort) in EXPECTED_ROLE_CONFIGS.items():
        declared = agent_configs.get(role, {})
        if declared.get("config_file") != relative_path:
            raise ValueError(f"{role} must use {relative_path}")
        layer = _load_toml(config_path.parent / relative_path)
        if layer.get("model") != model or layer.get("model_reasoning_effort") != effort:
            raise ValueError(f"{role} model layer must be {model}/{effort}")
        if role == "acceptance":
            if layer.get("sandbox_mode") != "read-only" or layer.get("approval_policy") != "never":
                raise ValueError("acceptance role must be enforced read-only with no approval escalation")

    routing_path = root / "registry" / "model_routing.yaml"
    routing = yaml.safe_load(routing_path.read_text(encoding="utf-8"))
    models = routing.get("codex_models", {})
    for role, (_, model, effort) in EXPECTED_ROLE_CONFIGS.items():
        facts = models.get(role, {})
        if facts.get("model") != model or facts.get("reasoning_effort") != effort:
            raise ValueError(f"registry {role} routing must be {model}/{effort}")

    escalation = routing.get("sol_escalation", {})
    allowed = set(escalation.get("allowed_reasons", []))
    if allowed != EXPECTED_ESCALATIONS:
        raise ValueError(f"Sol escalation reasons must be exact: {sorted(EXPECTED_ESCALATIONS)}")
    if routing.get("workflow", {}).get("deterministic_failure") != "return to Luna; never use Sol":
        raise ValueError("deterministic failures must not route to Sol")
    if "Luna issues the final acceptance" not in escalation.get("return_path", ""):
        raise ValueError("final acceptance must return to Luna after Sol evidence review")

    packet_rule = (root / "runbooks" / "task_packet_validation.md").read_text(encoding="utf-8")
    if "do not pass model or thinking overrides" in packet_rule:
        raise ValueError("legacy no-model-override dispatch rule is still active")
    for required in ("gpt-5.6-sol", "gpt-5.6-luna", "AUTOMATED_GATE"):
        if required not in packet_rule:
            raise ValueError(f"task packet validation is missing {required}")

    runbook = (root / "runbooks" / "model_routing.md").read_text(encoding="utf-8")
    for required in EXPECTED_ESCALATIONS:
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
