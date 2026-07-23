from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import random

import pytest

from research.adapters import (
    c144_nyfed_primary_dealer_corporate_position_impulse as adapter,
)
from research.adapters.c144_nyfed_primary_dealer_corporate_position_impulse import (
    HOLDOUT_INTERVALS,
    InputContractError,
    VALIDATION_INTERVALS,
    bootstrap_inference,
    circular_block_indices,
    holdout_decision,
    validation_decision,
)
from scripts import (
    run_c144_nyfed_primary_dealer_corporate_position_impulse_once as runner,
)


EXPECTED_VALIDATION_GATES = (
    "strategy_terminal_net_wealth_strictly_above_50_50_comparator",
    "strategy_terminal_net_wealth_strictly_above_spy_only",
    "arithmetic_mean_paired_active_return_strictly_positive",
    "strategy_maximum_drawdown_no_worse_than_50_50_comparator",
)
EXPECTED_HOLDOUT_GATES = EXPECTED_VALIDATION_GATES + (
    "exactly_156_paired_intervals",
    "centered_null_one_sided_p_at_most_0_05",
    "uncentered_type7_0_05_lower_bound_strictly_positive",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_exact_definition_adapter_data_and_shared_core_identities() -> None:
    definition = json.loads(runner.DEFINITION.read_bytes())
    assert sha(runner.DEFINITION) == runner.DEFINITION_SHA256
    assert sha(runner.ADAPTER) == runner.ADAPTER_SHA256
    assert sha(runner.SIGNAL_INPUT) == runner.SIGNAL_SHA256
    assert sha(runner.SIGNAL_RECEIPT) == runner.SIGNAL_RECEIPT_SHA256
    assert sha(runner.RUNTIME_RECEIPT) == runner.RUNTIME_RECEIPT_SHA256
    assert sha(runner.VALIDATION_BUNDLE) == runner.VALIDATION_BUNDLE_SHA256
    assert sha(runner.HOLDOUT_BUNDLE) == runner.HOLDOUT_BUNDLE_SHA256
    assert runner._core_identity() == (
        runner.CORE_SOURCE_FILE_COUNT,
        runner.CORE_SOURCE_SHA256,
    )
    assert definition["research_id"] == adapter.RESEARCH_ID
    assert definition["program_multiplicity"]["sole_primary_alpha"] == 0.05
    assert (
        definition["universe"]["expected_inclusion_rule_sha256"]
        == runner.INCLUSION_RULE_SHA256
    )
    assert definition["source_identities"]["adapter_sha256"] == runner.ADAPTER_SHA256
    assert definition["boundaries"] == {
        "broker": False,
        "live": False,
        "paper": False,
        "rerun_authorized": False,
        "shadow": False,
        "strategy_candidate_available": False,
    }


def test_real_signal_packet_is_exact_and_state_supported() -> None:
    groups = runner._signals(runner.SIGNAL_INPUT.read_bytes())
    validation = groups["validation"]
    holdout = groups["retrospective_holdout"]
    assert len(validation) == VALIDATION_INTERVALS
    assert len(holdout) == HOLDOUT_INTERVALS
    assert sum(row.target_symbol == "QQQ" for row in validation) == 65
    assert sum(row.target_symbol == "SPY" for row in validation) == 64
    assert sum(row.target_symbol == "QQQ" for row in holdout) == 83
    assert sum(row.target_symbol == "SPY" for row in holdout) == 73
    assert all(left.end == right.start for left, right in zip(validation, validation[1:]))
    assert all(left.end == right.start for left, right in zip(holdout, holdout[1:]))
    assert validation[-1].end.isoformat() == "2023-06-26"
    assert holdout[-1].end.isoformat() == "2026-06-29"


def test_signal_packet_rejects_target_and_identity_tampering() -> None:
    record = json.loads(runner.SIGNAL_INPUT.read_bytes())
    record["signals"][0]["target_symbol"] = (
        "QQQ" if record["signals"][0]["target_symbol"] == "SPY" else "SPY"
    )
    with pytest.raises(runner.InputBlockedError, match="target mismatch"):
        runner._signals(json.dumps(record).encode())

    record = json.loads(runner.SIGNAL_INPUT.read_bytes())
    record["signals"][0]["signal_identity_sha256"] = "0" * 64
    with pytest.raises(runner.InputBlockedError, match="identity mismatch"):
        runner._signals(json.dumps(record).encode())

    record = json.loads(runner.SIGNAL_INPUT.read_bytes())
    record["signals"][0]["current_as_of_date"] = record["signals"][0][
        "decision_session"
    ]
    with pytest.raises(runner.InputBlockedError, match="chronology mismatch"):
        runner._signals(json.dumps(record).encode())

    record = json.loads(runner.SIGNAL_INPUT.read_bytes())
    record["signals"][0]["position_impulse_usd_millions"] += 0.01
    with pytest.raises(runner.InputBlockedError, match="position impulse is invalid"):
        runner._signals(json.dumps(record).encode())


@pytest.mark.parametrize(
    ("stage", "bundle_path", "expected_points"),
    (
        ("validation", runner.VALIDATION_BUNDLE, 130),
        ("holdout", runner.HOLDOUT_BUNDLE, 157),
    ),
)
def test_real_runtime_bundle_preflight_without_outcome_access(
    stage: str,
    bundle_path: Path,
    expected_points: int,
) -> None:
    groups = runner._signals(runner.SIGNAL_INPUT.read_bytes())
    signal_stage = "validation" if stage == "validation" else "retrospective_holdout"
    bundle = runner._load_bundle(
        bundle_path.read_bytes(),
        runner.SIGNAL_INPUT.read_bytes(),
        runner.SIGNAL_RECEIPT.read_bytes(),
        runner.RUNTIME_RECEIPT.read_bytes(),
        stage=stage,
        signals=groups[signal_stage],
    )
    assert bundle.stage == stage
    assert len(bundle.points) == expected_points
    assert all(point.target_symbol is not None for point in bundle.points[:-1])
    assert bundle.points[-1].target_symbol is None
    assert all(
        left.execution_session < right.execution_session
        for left, right in zip(bundle.points, bundle.points[1:])
    )
    assert {execution.symbol for execution in bundle.points[0].executions} == {
        "SPY",
        "QQQ",
    }


def test_runtime_bundle_rejects_changed_signal_identity() -> None:
    groups = runner._signals(runner.SIGNAL_INPUT.read_bytes())
    record = json.loads(runner.VALIDATION_BUNDLE.read_bytes())
    record["signal_input_sha256"] = "0" * 64
    with pytest.raises(runner.InputBlockedError, match="runtime bundle identity"):
        runner._load_bundle(
            json.dumps(record).encode(),
            runner.SIGNAL_INPUT.read_bytes(),
            runner.SIGNAL_RECEIPT.read_bytes(),
            runner.RUNTIME_RECEIPT.read_bytes(),
            stage="validation",
            signals=groups["validation"],
        )


def test_validation_decision_has_exact_four_frozen_gates() -> None:
    strategy = (0.01,) * VALIDATION_INTERVALS
    comparator = (0.0,) * VALIDATION_INTERVALS
    spy = (0.005,) * VALIDATION_INTERVALS
    decision = validation_decision(strategy, comparator, spy)
    assert tuple(name for name, _ in decision.gates) == EXPECTED_VALIDATION_GATES
    assert decision.all_gates_pass is True
    assert decision.observed_intervals == VALIDATION_INTERVALS
    assert decision.strategy.terminal_wealth > decision.spy_only.terminal_wealth
    assert decision.spy_only.terminal_wealth > decision.comparator.terminal_wealth


def test_validation_failure_is_mechanical_and_not_repaired() -> None:
    strategy = (-0.001,) * VALIDATION_INTERVALS
    comparator = (0.0,) * VALIDATION_INTERVALS
    spy = (0.001,) * VALIDATION_INTERVALS
    decision = validation_decision(strategy, comparator, spy)
    assert decision.all_gates_pass is False
    assert any(not passed for _, passed in decision.gates)


@pytest.mark.parametrize(
    "values",
    (
        (0.0,) * (VALIDATION_INTERVALS - 1),
        (0.0,) * (VALIDATION_INTERVALS - 1) + (math.nan,),
        (0.0,) * (VALIDATION_INTERVALS - 1) + (-1.0,),
    ),
)
def test_validation_rejects_wrong_length_nonfinite_and_total_loss(
    values: tuple[float, ...],
) -> None:
    with pytest.raises(InputContractError):
        validation_decision(
            values,
            (0.0,) * VALIDATION_INTERVALS,
            (0.0,) * VALIDATION_INTERVALS,
        )


def test_circular_block_indices_are_frozen_and_wrap() -> None:
    observed = circular_block_indices(
        7,
        block_length=4,
        rng=random.Random(14400101),
    )
    assert observed == (4, 5, 6, 0, 6, 0, 1)

    class FixedRng:
        @staticmethod
        def random() -> float:
            return 0.99

    assert circular_block_indices(
        7,
        block_length=4,
        rng=FixedRng(),  # type: ignore[arg-type]
    ) == (6, 0, 1, 2, 6, 0, 1)


def test_holdout_bootstrap_and_seven_gates_are_deterministic() -> None:
    strategy = (0.01,) * HOLDOUT_INTERVALS
    comparator = (0.0,) * HOLDOUT_INTERVALS
    spy = (0.005,) * HOLDOUT_INTERVALS
    decision = holdout_decision(strategy, comparator, spy)
    assert tuple(name for name, _ in decision.gates) == EXPECTED_HOLDOUT_GATES
    assert decision.all_gates_pass is True
    assert decision.inference == bootstrap_inference(
        tuple(left - right for left, right in zip(strategy, comparator, strict=True))
    )
    assert decision.inference.block_length_weeks == 4
    assert decision.inference.resamples == 100_000
    assert decision.inference.seed == 14_400_101
    assert decision.inference.centered_null_one_sided_p <= 0.05
    assert decision.inference.uncentered_lower_bound > 0.0


def test_claim_and_result_keep_all_execution_boundaries_closed() -> None:
    claim = runner._claim(
        "validation",
        "a" * 64,
        runner.VALIDATION_BUNDLE_SHA256,
        None,
    )
    assert claim["one_use_execution_consumed"] is True
    assert claim["rerun_authorized"] is False
    assert claim["signal_materialization_receipt_sha256"] == (
        runner.SIGNAL_RECEIPT_SHA256
    )
    assert claim["runtime_materialization_receipt_sha256"] == (
        runner.RUNTIME_RECEIPT_SHA256
    )
    result = runner._result(
        "validation",
        "RETROSPECTIVE_SECONDARY_VALIDATION_FAIL",
        claim_sha="b" * 64,
        runner_sha="a" * 64,
        bundle_sha=runner.VALIDATION_BUNDLE_SHA256,
        decision=None,
    )
    assert result["strategy_candidate_available"] is False
    assert result["rerun_authorized"] is False
    assert result["shadow"] is False
    assert result["paper"] is False
    assert result["broker"] is False
    assert result["live"] is False


def test_decision_serialization_contains_spy_comparator() -> None:
    decision = validation_decision(
        (0.01,) * VALIDATION_INTERVALS,
        (0.0,) * VALIDATION_INTERVALS,
        (0.005,) * VALIDATION_INTERVALS,
    )
    record = {
        "strategy": asdict(decision.strategy),
        "comparator": asdict(decision.comparator),
        "spy_only": asdict(decision.spy_only),
    }
    assert set(record) == {"strategy", "comparator", "spy_only"}
