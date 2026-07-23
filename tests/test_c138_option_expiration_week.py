from __future__ import annotations

import hashlib
import json
from pathlib import Path
import random
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from research.adapters.c138_option_expiration_week import (  # noqa: E402
    BOOTSTRAP_BLOCK_WEEKS,
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    HOLDOUT_INTERVALS,
    InputContractError,
    VALIDATION_INTERVALS,
    bootstrap_inference,
    circular_block_indices,
    holdout_decision,
    validation_decision,
)
from scripts import run_c138_option_expiration_week_once as runner  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_definition_freezes_one_outcome_blind_calendar_mechanism() -> None:
    record = json.loads(runner.DEFINITION.read_text(encoding="utf-8"))
    assert record["research_id"] == runner.RESEARCH_ID
    assert record["selection_without_outcomes"]["variant_count"] == 1
    assert record["selection_without_outcomes"]["parameter_grid"] is False
    assert (
        record["selection_without_outcomes"][
            "price_return_nav_sharpe_or_drawdown_used_for_selection"
        ]
        is False
    )
    assert record["signal"]["strategy_rule"].startswith("hold SPY only")
    assert record["signal"]["comparator_rule"].startswith("hold SPY only")
    assert record["splits"]["validation"]["complete_intervals"] == 125
    assert (
        record["splits"]["retrospective_holdout"]["complete_intervals"] == 152
    )
    assert record["terminal_rules"]["strategy_candidate_available"] is False
    assert record["source_identities"]["adapter_sha256"] == sha(runner.ADAPTER)


def test_validation_all_four_gates_can_pass() -> None:
    decision = validation_decision(
        (0.002,) * VALIDATION_INTERVALS,
        (0.0,) * VALIDATION_INTERVALS,
    )
    assert len(decision.gates) == 4
    assert decision.all_gates_pass is True
    assert all(passed for _, passed in decision.gates)


def test_validation_requires_positive_wealth_not_only_relative_outperformance() -> None:
    decision = validation_decision(
        (-0.0001,) * VALIDATION_INTERVALS,
        (-0.0002,) * VALIDATION_INTERVALS,
    )
    gates = dict(decision.gates)
    assert (
        gates[
            "strategy_terminal_net_wealth_strictly_above_fourth_friday_comparator"
        ]
        is True
    )
    assert (
        gates["strategy_terminal_net_wealth_strictly_above_initial_capital"]
        is False
    )
    assert decision.all_gates_pass is False


def test_validation_rejects_wrong_length_and_nonfinite() -> None:
    with pytest.raises(InputContractError):
        validation_decision((0.0,) * (VALIDATION_INTERVALS - 1), (0.0,) * VALIDATION_INTERVALS)
    values = [0.0] * VALIDATION_INTERVALS
    values[-1] = float("nan")
    with pytest.raises(InputContractError):
        validation_decision(tuple(values), (0.0,) * VALIDATION_INTERVALS)


def test_circular_block_indices_are_seeded_wrapped_and_truncated() -> None:
    observed = circular_block_indices(
        7, block_length=4, rng=random.Random(BOOTSTRAP_SEED)
    )
    assert observed == (3, 4, 5, 6, 3, 4, 5)


def test_holdout_all_six_gates_can_pass() -> None:
    decision = holdout_decision(
        (0.002,) * HOLDOUT_INTERVALS,
        (0.0,) * HOLDOUT_INTERVALS,
    )
    assert len(decision.gates) == 6
    assert decision.inference.resamples == BOOTSTRAP_RESAMPLES
    assert decision.inference.block_length_weeks == BOOTSTRAP_BLOCK_WEEKS
    assert decision.all_gates_pass is True


def test_bootstrap_is_repeatable_and_finite() -> None:
    values = tuple((index % 9 - 4) / 10_000 for index in range(HOLDOUT_INTERVALS))
    left = bootstrap_inference(values)
    right = bootstrap_inference(values)
    assert left == right
    assert 0.0 < left.centered_null_one_sided_p <= 1.0


def test_input_packet_receipt_and_bundle_hashes_are_exact() -> None:
    packet_payload = runner.INPUT_PACKET.read_bytes()
    receipt_payload = runner.INPUT_RECEIPT.read_bytes()
    assert hashlib.sha256(packet_payload).hexdigest() == runner.INPUT_PACKET_SHA256
    assert hashlib.sha256(receipt_payload).hexdigest() == runner.RECEIPT_SHA256
    packet, receipt = runner._validate_packet_receipt(
        packet_payload, receipt_payload
    )
    assert packet["strategy_outcomes_opened"] is False
    assert receipt["database_write"] is False
    assert sha(runner.VALIDATION_BUNDLE) == runner.VALIDATION_BUNDLE_SHA256
    assert sha(runner.HOLDOUT_BUNDLE) == runner.HOLDOUT_BUNDLE_SHA256


def test_runtime_bundles_parse_without_opening_outcomes() -> None:
    packet, receipt = runner._validate_packet_receipt(
        runner.INPUT_PACKET.read_bytes(),
        runner.INPUT_RECEIPT.read_bytes(),
    )
    validation = runner._load_bundle(
        runner.VALIDATION_BUNDLE.read_bytes(),
        packet,
        receipt,
        stage="validation",
    )
    holdout = runner._load_bundle(
        runner.HOLDOUT_BUNDLE.read_bytes(),
        packet,
        receipt,
        stage="holdout",
    )
    assert len(validation.points) == VALIDATION_INTERVALS + 1
    assert len(holdout.points) == HOLDOUT_INTERVALS + 1
    assert validation.points[-1].strategy_target_symbol is None
    assert holdout.points[-1].comparator_target_symbol is None


def test_third_and_fourth_friday_targets_never_overlap() -> None:
    for path in (runner.VALIDATION_BUNDLE, runner.HOLDOUT_BUNDLE):
        record = json.loads(path.read_text(encoding="utf-8"))
        for point in record["execution_points"][:-1]:
            ordinal = point["calendar_friday_ordinal"]
            assert point["strategy_target_symbol"] == (
                "SPY" if ordinal == 3 else None
            )
            assert point["comparator_target_symbol"] == (
                "SPY" if ordinal == 4 else None
            )
            assert not (
                point["strategy_target_symbol"]
                and point["comparator_target_symbol"]
            )


def test_wrong_input_hash_is_rejected() -> None:
    with pytest.raises(runner.InputBlockedError):
        runner._capture(
            runner.INPUT_PACKET,
            "0" * 64,
            max_bytes=2 * 1024 * 1024,
        )


def test_shared_core_identity_is_frozen() -> None:
    assert runner._core_identity() == (
        runner.CORE_SOURCE_FILE_COUNT,
        runner.CORE_SOURCE_SHA256,
    )


def test_runner_private_paths_are_pristine_before_first_use() -> None:
    for path in (
        runner.VALIDATION_CLAIM,
        runner.VALIDATION_RESULT,
        runner.HOLDOUT_CLAIM,
        runner.HOLDOUT_RESULT,
    ):
        assert not path.exists()
