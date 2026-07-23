from __future__ import annotations

import hashlib
import inspect
import json
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

import research.adapters.c3_policy_last_fomc_move as ADAPTER
from research.adapters.c3_policy_last_fomc_move import (
    BOOTSTRAP_BLOCK_LENGTH,
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    HOLDOUT_INTERVALS,
    PROGRAM_ALPHA,
    RESEARCH_ID,
    VALIDATION_INTERVALS,
    BootstrapInference,
    InputContractError,
    PolicyEvent,
    PolicyState,
    bootstrap_inference,
    circular_block_bootstrap_indices,
    derive_policy_state,
    holdout_decision,
    split_support,
    validation_decision,
)


def _decision(month: int, *, hour_utc: int = 13) -> datetime:
    return datetime(2022, month, 1, hour_utc, tzinfo=timezone.utc)


def _event(
    event_id: str,
    effective_date: date,
    value: float,
    *,
    available_at: datetime | None = None,
) -> PolicyEvent:
    return PolicyEvent(
        event_id=event_id,
        series_id="DFEDTARU",
        effective_date=effective_date,
        target_upper_bound_percent=value,
        available_at=available_at or datetime(2021, 1, 1, tzinfo=timezone.utc),
        official_range_row_sha256="a" * 64,
        fomc_statement_sha256="b" * 64,
    )


def _state(index: int, direction: str) -> PolicyState:
    decision_at = datetime(
        2018 + index // 12,
        index % 12 + 1,
        1,
        9,
        tzinfo=ZoneInfo("America/New_York"),
    )
    local_date = decision_at.date()
    return PolicyState(
        decision_at=decision_at,
        direction=direction,
        last_move_effective_date=local_date - timedelta(days=1),
        last_move_delta_percent=-0.25 if direction == "easing" else 0.25,
        spy_target_weight=1.0 if direction == "easing" else 0.0,
    )


def test_frozen_constants_are_exact() -> None:
    assert RESEARCH_ID == "C3_POLICY_LAST_FOMC_MOVE_DIRECTION_V1"
    assert PROGRAM_ALPHA == 0.00625
    assert VALIDATION_INTERVALS == 29
    assert HOLDOUT_INTERVALS == 35
    assert (BOOTSTRAP_RESAMPLES, BOOTSTRAP_SEED, BOOTSTRAP_BLOCK_LENGTH) == (
        10_000,
        1_193_101,
        3,
    )
    assert "ALFRED" not in inspect.getsource(ADAPTER)


def test_latest_nonzero_move_controls_state_and_zero_changes_are_ignored() -> None:
    events = (
        _event("fomc-1", date(2021, 1, 1), 5.50),
        _event("fomc-2", date(2021, 2, 1), 5.50),
        _event("fomc-3", date(2021, 3, 1), 5.25),
        _event("fomc-4", date(2021, 4, 1), 5.25),
    )
    easing = derive_policy_state(events, decision_at=_decision(5))
    assert easing.direction == "easing"
    assert easing.last_move_effective_date == date(2021, 3, 1)
    assert easing.last_move_delta_percent == pytest.approx(-0.25)
    assert easing.spy_target_weight == 1.0

    tightening = derive_policy_state(
        events + (_event("fomc-5", date(2021, 5, 1), 5.50),),
        decision_at=_decision(6),
    )
    assert tightening.direction == "tightening"
    assert tightening.last_move_delta_percent == pytest.approx(0.25)
    assert tightening.spy_target_weight == 0.0


@pytest.mark.parametrize(
    "events",
    [
        (_event("a", date(2021, 2, 1), 5.0), _event("b", date(2021, 1, 1), 4.0)),
        (_event("a", date(2021, 1, 1), 5.0), _event("b", date(2021, 1, 1), 4.0)),
        (_event("a", date(2021, 1, 1), 5.0), _event("a", date(2021, 2, 1), 4.0)),
        (_event("a", date(2021, 1, 1), 5.0), _event("b", date(2021, 2, 1), 5.0)),
    ],
)
def test_state_derivation_fails_closed_on_ambiguous_or_absent_move(
    events: tuple[PolicyEvent, ...],
) -> None:
    with pytest.raises(InputContractError):
        derive_policy_state(events, decision_at=_decision(5))


def test_state_derivation_rejects_late_future_and_wrong_decision_time() -> None:
    late = _event(
        "late",
        date(2021, 2, 1),
        4.75,
        available_at=datetime(2022, 5, 1, 14, tzinfo=timezone.utc),
    )
    with pytest.raises(InputContractError, match="available"):
        derive_policy_state(
            (_event("base", date(2021, 1, 1), 5.0), late),
            decision_at=_decision(5),
        )
    with pytest.raises(InputContractError, match="future-effective"):
        derive_policy_state(
            (
                _event("base", date(2021, 1, 1), 5.0),
                _event("future", date(2023, 1, 1), 4.75),
            ),
            decision_at=_decision(5),
        )
    with pytest.raises(InputContractError, match="09:00"):
        derive_policy_state(
            (
                _event("base", date(2021, 1, 1), 5.0),
                _event("move", date(2021, 2, 1), 4.75),
            ),
            decision_at=datetime(2022, 5, 1, 13, 1, tzinfo=timezone.utc),
        )


def test_policy_event_and_state_reject_bad_identity_or_mapping() -> None:
    with pytest.raises(InputContractError, match="DFEDTARU"):
        PolicyEvent(
            "event",
            "DFF",
            date(2021, 1, 1),
            1.0,
            datetime(2021, 1, 1, tzinfo=timezone.utc),
            "a" * 64,
            "b" * 64,
        )
    with pytest.raises(InputContractError, match="finite"):
        _event("event", date(2021, 1, 1), float("nan"))
    with pytest.raises(InputContractError, match="SHA-256"):
        PolicyEvent(
            "event",
            "DFEDTARU",
            date(2021, 1, 1),
            1.0,
            datetime(2021, 1, 1, tzinfo=timezone.utc),
            "bad",
            "b" * 64,
        )
    with pytest.raises(InputContractError, match="maps to"):
        PolicyState(
            _decision(5),
            "easing",
            date(2021, 1, 1),
            -0.25,
            0.0,
        )


@pytest.mark.parametrize(
    ("split_id", "count"),
    [("development", 34), ("validation", 30), ("holdout", 36)],
)
def test_split_support_uses_exact_counts_and_one_total_change(
    split_id: str,
    count: int,
) -> None:
    states = tuple(
        _state(index, "easing" if index < 4 else "tightening")
        for index in range(count)
    )
    decision = split_support(states, split_id=split_id)
    assert decision.easing_count == 4
    assert decision.tightening_count == count - 4
    assert decision.adjacent_state_changes == 1
    assert decision.all_gates_pass is True
    assert tuple(name for name, _ in decision.gates) == (
        "easing_count_at_least_4",
        "tightening_count_at_least_4",
        "adjacent_state_changes_at_least_1",
    )


def test_split_support_rejects_wrong_size_and_fails_low_direction_count() -> None:
    with pytest.raises(InputContractError, match="exactly 30"):
        split_support(tuple(_state(index, "easing") for index in range(29)), split_id="validation")
    states = tuple(
        _state(index, "easing" if index < 3 else "tightening")
        for index in range(30)
    )
    decision = split_support(states, split_id="validation")
    assert decision.all_gates_pass is False
    assert dict(decision.gates)["easing_count_at_least_4"] is False


def test_validation_applies_exact_three_gates_and_equality_rules() -> None:
    strategy = tuple(0.01 if index % 2 else 0.0 for index in range(VALIDATION_INTERVALS))
    spy = tuple(0.005 if index % 2 else -0.005 for index in range(VALIDATION_INTERVALS))
    decision = validation_decision(strategy, spy)
    assert decision.all_gates_pass is True
    assert tuple(name for name, _ in decision.gates) == (
        "strategy_terminal_net_wealth_strictly_above_spy",
        "arithmetic_mean_paired_active_returns_strictly_positive",
        "strategy_maximum_drawdown_no_worse_than_spy",
    )

    equal = validation_decision(spy, spy)
    assert dict(equal.gates) == {
        "strategy_terminal_net_wealth_strictly_above_spy": False,
        "arithmetic_mean_paired_active_returns_strictly_positive": False,
        "strategy_maximum_drawdown_no_worse_than_spy": True,
    }
    assert equal.all_gates_pass is False


@pytest.mark.parametrize(
    ("strategy", "spy"),
    [
        ((0.0,) * 28, (0.0,) * 28),
        ((0.0,) * 28 + (float("nan"),), (0.0,) * 29),
        ((0.0,) * 28 + (-1.0,), (0.0,) * 29),
    ],
)
def test_validation_rejects_incomplete_nonfinite_or_bankrupt_paths(
    strategy: tuple[float, ...],
    spy: tuple[float, ...],
) -> None:
    with pytest.raises(InputContractError):
        validation_decision(strategy, spy)


def test_circular_bootstrap_has_literal_golden_paths_and_full_path_hash() -> None:
    paths = circular_block_bootstrap_indices(8)
    assert paths[:4] == (
        (6, 7, 0, 0, 1, 2, 1, 2),
        (5, 6, 7, 0, 1, 2, 0, 1),
        (2, 3, 4, 2, 3, 4, 3, 4),
        (3, 4, 5, 5, 6, 7, 3, 4),
    )
    assert len(paths) == 10_000
    assert all(len(path) == 8 and min(path) >= 0 and max(path) <= 7 for path in paths)
    payload = json.dumps(paths, separators=(",", ":")).encode()
    assert hashlib.sha256(payload).hexdigest() == (
        "4e9ebf220a06b2ee6477978ff1af35e88b2d412612adbd9f33c305756b62fce9"
    )
    production_paths = circular_block_bootstrap_indices()
    assert production_paths[:2] == (
        (
            26, 27, 28, 1, 2, 3, 8, 9, 10, 25, 26, 27, 4, 5, 6, 2, 3, 4, 9,
            10, 11, 12, 13, 14, 13, 14, 15, 15, 16, 17, 25, 26, 27, 14, 15,
        ),
        (
            0, 1, 2, 23, 24, 25, 31, 32, 33, 16, 17, 18, 10, 11, 12, 33, 34,
            0, 32, 33, 34, 15, 16, 17, 34, 0, 1, 5, 6, 7, 21, 22, 23, 15, 16,
        ),
    )
    production_payload = json.dumps(
        production_paths, separators=(",", ":")
    ).encode()
    assert hashlib.sha256(production_payload).hexdigest() == (
        "0e4ef34a2f12e02eb203153c561ada2e730a7f9309fc64fd04b4fae58dfa0c1b"
    )


def test_type7_quantile_is_linear_and_does_not_use_discrete_order_statistic() -> None:
    assert ADAPTER._type7_quantile([0.0, 1.0, 2.0, 3.0], 0.25) == pytest.approx(0.75)
    assert ADAPTER._type7_quantile([0.0, 1.0, 2.0, 3.0], 0.00625) == pytest.approx(0.01875)


def test_bootstrap_inference_matches_nonconstant_literal_golden_output() -> None:
    active = tuple(0.004 + ((index % 7) - 3) * 0.001 for index in range(35))
    result = bootstrap_inference(active)
    assert result.observed_mean_active_return == pytest.approx(0.004)
    assert result.centered_null_one_sided_p == pytest.approx(1 / 10_001)
    assert result.uncentered_type7_lower_bound == pytest.approx(
        0.0031142857142857144
    )


def test_bootstrap_rejects_wrong_length_and_nonfinite_values() -> None:
    with pytest.raises(InputContractError, match="exactly 35"):
        bootstrap_inference((0.01,) * 34)
    with pytest.raises(InputContractError, match="finite"):
        bootstrap_inference((0.01,) * 34 + (float("inf"),))


def test_centered_null_p_value_counts_equality_as_more_extreme() -> None:
    result = bootstrap_inference((0.0,) * HOLDOUT_INTERVALS)
    assert result.observed_mean_active_return == 0.0
    assert result.centered_null_one_sided_p == 1.0
    assert result.uncentered_type7_lower_bound == 0.0


def test_holdout_applies_exact_five_gates(monkeypatch: pytest.MonkeyPatch) -> None:
    strategy = tuple(0.01 if index % 2 else 0.0 for index in range(HOLDOUT_INTERVALS))
    spy = tuple(0.004 if index % 2 else -0.004 for index in range(HOLDOUT_INTERVALS))
    monkeypatch.setattr(
        ADAPTER,
        "bootstrap_inference",
        lambda active: BootstrapInference(0.005, PROGRAM_ALPHA, 0.001),
    )
    decision = holdout_decision(strategy, spy)
    assert decision.all_gates_pass is True
    assert tuple(name for name, _ in decision.gates) == (
        "strategy_terminal_net_wealth_strictly_above_spy",
        "strategy_maximum_drawdown_no_worse_than_spy",
        "interval_count_exactly_35",
        "centered_null_one_sided_p_at_most_0_00625",
        "uncentered_type7_0_00625_lower_bound_strictly_positive",
    )


@pytest.mark.parametrize(
    ("p_value", "lower_bound", "expected"),
    [
        (PROGRAM_ALPHA, 0.001, True),
        (PROGRAM_ALPHA + 1e-9, 0.001, False),
        (PROGRAM_ALPHA, 0.0, False),
    ],
)
def test_holdout_p_value_is_inclusive_and_lower_bound_is_strict(
    monkeypatch: pytest.MonkeyPatch,
    p_value: float,
    lower_bound: float,
    expected: bool,
) -> None:
    strategy = (0.01,) * HOLDOUT_INTERVALS
    spy = (0.0,) * HOLDOUT_INTERVALS
    monkeypatch.setattr(
        ADAPTER,
        "bootstrap_inference",
        lambda active: BootstrapInference(0.01, p_value, lower_bound),
    )
    assert holdout_decision(strategy, spy).all_gates_pass is expected
