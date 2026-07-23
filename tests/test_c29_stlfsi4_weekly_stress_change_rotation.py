from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import random

import pytest

from quant_system.backtest import Portfolio
from quant_system.data import CorporateActionIdentity, SourceIdentity
from research.adapters import c29_stlfsi4_weekly_stress_change_rotation as adapter
from scripts import run_c29_stlfsi4_weekly_stress_change_rotation_once as runner


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_frozen_constants_and_source_hashes() -> None:
    assert adapter.RESEARCH_ID == "C29_STLFSI4_WEEKLY_STRESS_CHANGE_ROTATION_SPY_QQQ_V1"
    assert adapter.VALIDATION_INTERVALS == 77
    assert adapter.HOLDOUT_INTERVALS == 104
    assert adapter.PROGRAM_ALPHA == 0.000000000186264514923095703125
    assert adapter.BOOTSTRAP_RESAMPLES == 8_192_000_000
    assert adapter.BOOTSTRAP_BLOCK_WEEKS == 13
    assert adapter.BOOTSTRAP_SEED == 2_500_101
    assert sha(runner.DEFINITION) == runner.DEFINITION_SHA256
    assert sha(runner.ADAPTER) == runner.ADAPTER_SHA256
    assert runner._core_identity() == (
        runner.CORE_SOURCE_FILE_COUNT,
        runner.CORE_SOURCE_SHA256,
    )


def test_definition_freezes_single_outcome_blind_variant() -> None:
    record = json.loads(runner.DEFINITION.read_text())
    assert record["research_id"] == adapter.RESEARCH_ID
    assert record["selection_without_outcomes"]["parameter_grid"] is False
    assert record["selection_without_outcomes"]["variant_count"] == 1
    assert record["program_multiplicity"]["sole_primary_alpha"] == adapter.PROGRAM_ALPHA
    assert record["state_support_before_outcomes"]["strategy_outcomes_opened"] is False
    assert record["source_identities"]["runtime_packet_sha256"] == runner.RUNTIME_SHA256
    assert record["source_identities"]["adapter_sha256"] == runner.ADAPTER_SHA256
    assert record["expected_inclusion_rule_sha256"] == runner.INCLUSION_RULE_SHA256
    assert record["boundaries"] == {
        "provider_or_network_call": False,
        "database_open_or_write": False,
        "external_review_requested": False,
        "prospective_forward_access": False,
        "strategy_candidate_available": False,
        "shadow": False,
        "paper": False,
        "broker": False,
        "live": False,
    }


def test_validation_all_three_gates_can_pass() -> None:
    strategy = (0.01,) * adapter.VALIDATION_INTERVALS
    comparator = (0.0,) * adapter.VALIDATION_INTERVALS
    decision = adapter.validation_decision(strategy, comparator)
    assert decision.observed_intervals == 77
    assert decision.all_gates_pass is True
    assert all(passed for _, passed in decision.gates)


def test_validation_requires_exact_length_and_finite_returns() -> None:
    with pytest.raises(adapter.InputContractError, match="exactly 77"):
        adapter.validation_decision((0.0,) * 76, (0.0,) * 76)
    values = [0.0] * 77
    values[5] = float("nan")
    with pytest.raises(adapter.InputContractError, match="finite"):
        adapter.validation_decision(tuple(values), (0.0,) * 77)
    values[5] = -1.0
    with pytest.raises(adapter.InputContractError, match="greater than -1"):
        adapter.validation_decision(tuple(values), (0.0,) * 77)


def test_validation_is_all_gates_not_a_score() -> None:
    strategy = (0.01,) * 38 + (-0.009,) * 39
    comparator = (0.0,) * 77
    decision = adapter.validation_decision(strategy, comparator)
    assert len(decision.gates) == 3
    assert decision.all_gates_pass is all(passed for _, passed in decision.gates)


def test_circular_block_golden_indices() -> None:
    observed = adapter.circular_block_indices(
        8,
        block_length=3,
        rng=random.Random(2_500_101),
    )
    assert observed == (2, 3, 4, 1, 2, 3, 0, 1)


@pytest.mark.parametrize(
    ("sample_size", "block_length"),
    [(0, 1), (8, 0), (8, 9)],
)
def test_circular_block_rejects_invalid_contract(
    sample_size: int, block_length: int
) -> None:
    with pytest.raises(adapter.InputContractError):
        adapter.circular_block_indices(
            sample_size,
            block_length=block_length,
            rng=random.Random(1),
        )


def test_small_bootstrap_preserves_frozen_algorithm_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(adapter, "BOOTSTRAP_RESAMPLES", 31)
    active = tuple(((index % 7) - 3) / 10_000 for index in range(104))
    inference = adapter.bootstrap_inference(active)
    assert inference.resamples == 31
    assert inference.block_length_weeks == 13
    assert inference.seed == 2_500_101
    assert 0.0 < inference.centered_null_one_sided_p <= 1.0


def test_exact_signal_and_runtime_packets_parse_without_outcomes() -> None:
    signal = runner._capture(
        runner.SIGNAL_INPUT,
        runner.SIGNAL_SHA256,
        max_bytes=2 * 1024 * 1024,
    )
    signal_receipt = runner._capture(
        runner.SIGNAL_RECEIPT,
        runner.SIGNAL_RECEIPT_SHA256,
        max_bytes=256 * 1024,
    )
    signals = runner._signals(signal, signal_receipt)
    assert len(signals["validation"]) == 77
    assert len(signals["retrospective_holdout"]) == 104
    runtime = runner._capture(
        runner.RUNTIME_INPUT,
        runner.RUNTIME_SHA256,
        max_bytes=32 * 1024 * 1024,
    )
    runtime_receipt = runner._capture(
        runner.RUNTIME_RECEIPT,
        runner.RUNTIME_RECEIPT_SHA256,
        max_bytes=256 * 1024,
    )
    validation = runner._load_bundle(
        runtime,
        runtime_receipt,
        stage="validation",
        signals=signals["validation"],
    )
    holdout = runner._load_bundle(
        runtime,
        runtime_receipt,
        stage="holdout",
        signals=signals["retrospective_holdout"],
    )
    assert len(validation.points) == 78
    assert len(holdout.points) == 105
    assert validation.points[-1].target_symbol is None
    assert holdout.points[-1].target_symbol is None
    assert all(action.action_type in {"cash_dividend", "special_dividend"} for action in validation.actions + holdout.actions)


def test_runtime_packet_records_retrospective_action_limitation() -> None:
    record = json.loads(runner.RUNTIME_INPUT.read_text())
    assert record["strategy_outcomes_opened"] is False
    assert record["adjusted_prices_used"] is False
    assert record["source_selected_using_performance"] is False
    assert record["database_opened"] is False
    assert record["database_write"] is False
    assert record["corporate_action_mode"].startswith(
        "retrospective_accounting_only_not_signal_or_selection"
    )


def test_cash_distribution_is_accounted_before_execution_without_signal_use() -> None:
    source = SourceIdentity(
        "https://example.com/official-distribution",
        "1" * 64,
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        "distribution-1",
    )
    action = CorporateActionIdentity(
        "SPY",
        "SPY:test-distribution",
        "cash_dividend",
        datetime(2024, 3, 15, 13, 30, tzinfo=timezone.utc),
        source,
        "America/New_York",
        ex_date=date(2024, 3, 15),
        record_date=date(2024, 3, 18),
        pay_date=date(2024, 4, 30),
        cash_amount=Decimal("1.50"),
        currency="USD",
        unit="per_share",
    )
    portfolio = Portfolio.us(1000.0)
    portfolio.start_session(date(2024, 3, 14))
    portfolio.buy("SPY", 2, 100.0, date(2024, 3, 14))
    runner._apply_actions(portfolio, date(2024, 3, 15), (action,))
    assert portfolio.pending_cash_total == 3.0


def test_claim_and_result_boundaries_remain_nontrading() -> None:
    claim = runner._claim("validation", "2" * 64, None)
    assert claim["one_use_execution_consumed"] is True
    assert claim["rerun_authorized"] is False
    result = runner._result(
        "validation",
        "RETROSPECTIVE_SECONDARY_VALIDATION_FAIL",
        claim_sha="3" * 64,
        runner_sha="2" * 64,
        decision={"all_gates_pass": False},
    )
    assert result["strategy_candidate_available"] is False
    assert result["rerun_authorized"] is False
    assert result["shadow"] is False
    assert result["paper"] is False
    assert result["broker"] is False
    assert result["live"] is False


def test_one_use_paths_are_pristine_before_formal_execution() -> None:
    assert not runner.VALIDATION_CLAIM.exists()
    assert not runner.VALIDATION_RESULT.exists()
    assert not runner.HOLDOUT_CLAIM.exists()
    assert not runner.HOLDOUT_RESULT.exists()
