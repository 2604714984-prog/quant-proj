from __future__ import annotations

from datetime import date, datetime, time, timedelta
import hashlib
import json
from pathlib import Path
import random
import stat
from types import SimpleNamespace

import pytest

from research.adapters import c100_cboe_volatility_convexity_ratio as adapter
from research.adapters.c100_cboe_volatility_convexity_ratio import (
    BOOTSTRAP_BLOCK_MONTHS,
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    HOLDOUT_INTERVALS,
    PROGRAM_ALPHA,
    VALIDATION_INTERVALS,
    InputContractError,
    circular_block_indices,
    holdout_decision,
    validation_decision,
)
from scripts import run_c100_cboe_volatility_convexity_ratio_once as runner


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_frozen_definition_adapter_core_and_constants_are_exact() -> None:
    assert sha(runner.DEFINITION) == runner.DEFINITION_SHA256
    assert sha(runner.ADAPTER) == runner.ADAPTER_SHA256
    assert runner._core_identity() == (
        runner.CORE_SOURCE_FILE_COUNT,
        runner.CORE_SOURCE_SHA256,
    )
    assert VALIDATION_INTERVALS == 28
    assert HOLDOUT_INTERVALS == 34
    assert PROGRAM_ALPHA == 0.05
    assert BOOTSTRAP_RESAMPLES == 100_000
    assert BOOTSTRAP_BLOCK_MONTHS == 3
    assert BOOTSTRAP_SEED == 10_000_101


def test_definition_is_one_variant_outcome_blind_and_nontrading() -> None:
    record = json.loads(runner.DEFINITION.read_text(encoding="utf-8"))
    selection = record["selection_without_outcomes"]
    assert selection["price_return_nav_sharpe_or_drawdown_used_for_selection"] is False
    assert selection["parameter_grid"] is False
    assert selection["variant_count"] == 1
    multiplicity = record["program_multiplicity"]
    assert multiplicity["epoch53_mechanism_count"] == 1
    assert multiplicity["sole_primary_alpha"] == PROGRAM_ALPHA
    assert multiplicity["alpha_recycling"] is False
    assert multiplicity["lifetime_fwer_claim"] is False
    assert record["source_identities"]["adapter_sha256"] == runner.ADAPTER_SHA256
    assert record["expected_inclusion_rule_sha256"] == runner.INCLUSION_RULE_SHA256
    assert record["terminal_rules"]["rerun"] is False
    assert all(value is False for value in record["boundaries"].values())


def test_validation_requires_all_three_frozen_gates() -> None:
    passing = validation_decision(
        (0.01,) * VALIDATION_INTERVALS,
        (0.005,) * VALIDATION_INTERVALS,
    )
    assert passing.all_gates_pass is True
    assert all(value for _, value in passing.gates)

    failing = validation_decision(
        (0.0,) * VALIDATION_INTERVALS,
        (0.005,) * VALIDATION_INTERVALS,
    )
    assert failing.all_gates_pass is False


@pytest.mark.parametrize(
    "strategy,comparator",
    [
        ((0.0,) * (VALIDATION_INTERVALS - 1), (0.0,) * VALIDATION_INTERVALS),
        (
            (float("nan"),) + (0.0,) * (VALIDATION_INTERVALS - 1),
            (0.0,) * VALIDATION_INTERVALS,
        ),
        ((-1.0,) + (0.0,) * (VALIDATION_INTERVALS - 1), (0.0,) * VALIDATION_INTERVALS),
    ],
)
def test_validation_fails_closed_on_invalid_returns(
    strategy: tuple[float, ...], comparator: tuple[float, ...]
) -> None:
    with pytest.raises(InputContractError):
        validation_decision(strategy, comparator)


def test_bootstrap_index_sequence_has_literal_golden_vectors() -> None:
    rng = random.Random(BOOTSTRAP_SEED)
    assert circular_block_indices(8, block_length=3, rng=rng) == (
        7,
        0,
        1,
        4,
        5,
        6,
        0,
        1,
    )
    assert circular_block_indices(8, block_length=3, rng=rng) == (
        4,
        5,
        6,
        6,
        7,
        0,
        6,
        7,
    )


def test_constant_positive_active_holdout_passes_exact_inference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(adapter, "BOOTSTRAP_RESAMPLES", 20_000)
    monkeypatch.setattr(adapter, "PROGRAM_ALPHA", 0.001)
    decision = holdout_decision(
        (0.01,) * HOLDOUT_INTERVALS,
        (0.0,) * HOLDOUT_INTERVALS,
    )
    assert decision.all_gates_pass is True
    assert decision.inference.centered_null_one_sided_p == pytest.approx(1 / 20001)
    assert decision.inference.uncentered_lower_bound == pytest.approx(0.01)


def _month(value: date, offset: int) -> date:
    ordinal = value.year * 12 + value.month - 1 + offset
    return date(ordinal // 12, ordinal % 12 + 1, 1)


def _synthetic_signal_packet() -> bytes:
    rows: list[dict[str, object]] = []
    state_support: dict[str, dict[str, int]] = {}
    for stage, first, count in (
        ("validation", date(2021, 2, 1), VALIDATION_INTERVALS),
        ("retrospective_holdout", date(2023, 8, 1), HOLDOUT_INTERVALS),
    ):
        targets: list[str] = []
        for index in range(count):
            start = _month(first, index)
            end = _month(first, index + 1)
            signal_session = start - timedelta(days=1)
            current_ratio = 1.1 if index % 2 == 0 else 0.9
            prior_ratio = 1.0
            difference = current_ratio - prior_ratio
            target = "SPY" if difference > 0.0 else "QQQ"
            targets.append(target)
            row: dict[str, object] = {
                "decision_at": datetime.combine(
                    signal_session,
                    time(20, 5),
                    tzinfo=runner.NY,
                ).isoformat(),
                "current_observation_date": signal_session.isoformat(),
                "current_ratio": current_ratio,
                "current_vix": 20.0,
                "current_vvix": current_ratio * 20.0,
                "holding_end_execution_session": end.isoformat(),
                "holding_start_execution_session": start.isoformat(),
                "prior_observation_date": (
                    signal_session - timedelta(days=28)
                ).isoformat(),
                "prior_ratio": prior_ratio,
                "prior_vix": 20.0,
                "prior_vvix": 20.0,
                "ratio_change": difference,
                "signal_session": signal_session.isoformat(),
                "source_row_hash_set_sha256": hashlib.sha256(
                    f"{stage}-{index}-rows".encode()
                ).hexdigest(),
                "stage": stage,
                "target_symbol": target,
            }
            row["signal_identity_sha256"] = hashlib.sha256(
                json.dumps(row, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            rows.append(row)
        transitions = list(zip(targets, targets[1:], strict=False))
        state_support[stage] = {
            "complete_intervals": len(targets),
            "SPY_intervals": targets.count("SPY"),
            "QQQ_intervals": targets.count("QQQ"),
            "SPY_to_QQQ": transitions.count(("SPY", "QQQ")),
            "QQQ_to_SPY": transitions.count(("QQQ", "SPY")),
        }
    return json.dumps(
        {
            "schema_version": "c100-cboe-volatility-convexity-ratio-input-v1",
            "research_id": runner.RESEARCH_ID,
            "evidence_class": "RETROSPECTIVE_SECONDARY_NOT_STRICT_PIT",
            "strategy_outcomes_opened": False,
            "price_values_used_for_signal": False,
            "spy_price_values_used_for_materialization": False,
            "adjusted_prices_used_for_signal": False,
            "database_opened": False,
            "database_write": False,
            "source_selected_using_performance": False,
            "strategy_candidate_available": False,
            "signal_contract": {
                "current_rule": (
                    "newest common positive finite official VVIX and VIX "
                    "observation on or before signal date"
                ),
                "comparison_rule": (
                    "newest common observation on or before current "
                    "observation date minus 28 calendar days"
                ),
                "ratio_definition": "VVIX divided by VIX",
                "target_rule": (
                    "strict ratio increase selects SPY; "
                    "equality or decrease selects QQQ"
                ),
                "missing_rule": (
                    "fail closed; no alternate lookback, source or row blend"
                ),
            },
            "signals": rows,
            "state_support": state_support,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def test_synthetic_packet_reproduces_frozen_rule_without_outcomes() -> None:
    payload = _synthetic_signal_packet()
    groups = runner._signals(payload)
    assert len(groups["validation"]) == VALIDATION_INTERVALS
    assert len(groups["retrospective_holdout"]) == HOLDOUT_INTERVALS
    assert sum(row.target_symbol == "QQQ" for row in groups["validation"]) == 14
    assert sum(
        row.target_symbol == "QQQ" for row in groups["retrospective_holdout"]
    ) == 17
    lowered = payload.lower()
    for forbidden in (
        b'"terminal_wealth"',
        b'"nav"',
        b'"sharpe"',
        b'"strategy_returns"',
        b'"comparator_returns"',
    ):
        assert forbidden not in lowered


def test_signal_packet_rejects_arithmetic_and_target_tampering() -> None:
    record = json.loads(_synthetic_signal_packet())
    record["signals"][0]["ratio_change"] = 0.2
    payload = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    with pytest.raises(runner.InputBlockedError, match="arithmetic mismatch"):
        runner._signals(payload)

    record = json.loads(_synthetic_signal_packet())
    record["signals"][0]["target_symbol"] = "QQQ"
    payload = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    with pytest.raises(runner.InputBlockedError, match="target mismatch"):
        runner._signals(payload)


def test_real_input_bytes_are_bound_and_support_matches() -> None:
    assert sha(runner.SIGNAL_INPUT) == runner.SIGNAL_SHA256
    assert sha(runner.INPUT_RECEIPT) == runner.RECEIPT_SHA256
    groups = runner._signals(runner.SIGNAL_INPUT.read_bytes())
    validation = tuple(row.target_symbol for row in groups["validation"])
    holdout = tuple(row.target_symbol for row in groups["retrospective_holdout"])
    assert (validation.count("SPY"), validation.count("QQQ")) == (13, 15)
    assert (holdout.count("SPY"), holdout.count("QQQ")) == (17, 17)


def test_rebalance_binds_two_asset_universe_and_exact_weight(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake(portfolio, calendar, **kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(runner, "run_static_rebalance", fake)
    point = SimpleNamespace(
        calendar=object(),
        signal_session=date(2021, 1, 29),
        decision_at=datetime(2021, 2, 1, 14, 0, tzinfo=runner.NY),
        executions=("QQQ_INPUT", "SPY_INPUT"),
        revision=None,
        snapshot=object(),
    )
    runner._rebalance(object(), point, {"QQQ": 1.0}, "0" * 64)
    assert captured["execution_inputs"] == ("QQQ_INPUT", "SPY_INPUT")
    assert captured["universe_members"] == ("QQQ", "SPY")
    assert captured["target_weights"](None) == {"QQQ": 1.0}


def test_strict_json_capture_and_one_use_publication_fail_closed(
    tmp_path: Path,
) -> None:
    with pytest.raises(runner.InputBlockedError, match="duplicate JSON key"):
        runner._json(b'{"a":1,"a":2}', "test")
    with pytest.raises(runner.InputBlockedError, match="nonfinite JSON constant"):
        runner._json(b'{"a":NaN}', "test")

    target = tmp_path / "target.json"
    target.write_bytes(b"{}")
    link = tmp_path / "link.json"
    link.symlink_to(target)
    with pytest.raises(runner.InputBlockedError, match="cannot open protected input"):
        runner._capture(link, hashlib.sha256(b"{}").hexdigest(), max_bytes=10)

    destination = tmp_path / "private" / "result.json"
    value = {"classification": "TEST_ONLY"}
    runner._publish(destination, value)
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600
    with pytest.raises(runner.InputBlockedError):
        runner._publish(destination, value)


def test_real_one_use_state_is_pristine_or_mechanically_terminal() -> None:
    if not runner.VALIDATION_CLAIM.exists():
        assert not runner.VALIDATION_RESULT.exists()
        assert not runner.HOLDOUT_CLAIM.exists()
        assert not runner.HOLDOUT_RESULT.exists()
        return
    assert runner.VALIDATION_RESULT.exists()
    result = json.loads(runner.VALIDATION_RESULT.read_text(encoding="utf-8"))
    if (
        result["classification"]
        == "RETROSPECTIVE_SECONDARY_VALIDATION_PASS_HOLDOUT_UNLOCKED"
    ):
        assert result["decision"]["all_gates_pass"] is True
        assert runner.HOLDOUT_CLAIM.exists() is runner.HOLDOUT_RESULT.exists()
    else:
        assert not runner.HOLDOUT_CLAIM.exists()
        assert not runner.HOLDOUT_RESULT.exists()
