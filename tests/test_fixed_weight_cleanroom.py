from datetime import date, datetime, timedelta

import pytest

from quant_system.backtest.fixed_weight import GrossFactorRow, run_fixed_weight_backtest


def _rows(
    factors: list[tuple[float, float]],
    *,
    start: date = date(2026, 1, 1),
) -> tuple[GrossFactorRow, ...]:
    rows: list[GrossFactorRow] = []
    for offset, (aaa, bbb) in enumerate(factors):
        session = start + timedelta(days=offset)
        rows.extend(
            (
                GrossFactorRow(session, "AAA", aaa),
                GrossFactorRow(session, "BBB", bbb),
            )
        )
    return tuple(rows)


def test_hand_worked_two_session_golden_applies_return_cost_then_reset() -> None:
    result = run_fixed_weight_backtest(
        _rows([(1.1, 0.9), (1.0, 1.2)]),
        {"AAA": 0.5, "BBB": 0.5},
        rebalance_interval=2,
        cost_bps=100.0,
    )

    first, second = result.sessions
    assert first.portfolio_gross_factor == pytest.approx(1.0)
    assert dict(first.drifted_weights) == pytest.approx({"AAA": 0.55, "BBB": 0.45})
    assert first.rebalanced is False
    assert first.wealth == pytest.approx(1.0)

    assert second.start_weights == first.drifted_weights
    assert second.portfolio_gross_factor == pytest.approx(1.09)
    assert dict(second.drifted_weights) == pytest.approx(
        {"AAA": 0.55 / 1.09, "BBB": 0.54 / 1.09}
    )
    assert second.turnover == pytest.approx(0.00917431192660545)
    assert second.cost_fraction == pytest.approx(0.0000917431192660545)
    assert second.net_factor == pytest.approx(1.0899)
    assert second.wealth == pytest.approx(1.0899)
    assert second.end_weights == (("AAA", 0.5), ("BBB", 0.5))
    assert result.final_wealth == pytest.approx(1.0899)


def test_sixty_third_session_resets_only_after_its_return() -> None:
    result = run_fixed_weight_backtest(
        _rows([(1.01, 1.0)] * 64),
        {"AAA": 0.5, "BBB": 0.5},
        rebalance_interval=63,
        cost_bps=0.0,
    )

    assert result.sessions[61].session_index == 62
    assert result.sessions[61].rebalanced is False
    boundary = result.sessions[62]
    assert boundary.session_index == 63
    assert boundary.rebalanced is True
    assert boundary.start_weights != (("AAA", 0.5), ("BBB", 0.5))
    assert boundary.end_weights == (("AAA", 0.5), ("BBB", 0.5))
    following = result.sessions[63]
    assert following.start_weights == (("AAA", 0.5), ("BBB", 0.5))
    assert following.portfolio_gross_factor == pytest.approx(1.005)


def test_none_interval_is_buy_and_hold_without_turnover_or_cost() -> None:
    result = run_fixed_weight_backtest(
        _rows([(1.1, 0.9), (1.0, 1.2)]),
        {"AAA": 0.5, "BBB": 0.5},
        rebalance_interval=None,
        cost_bps=500.0,
    )

    assert result.final_wealth == pytest.approx(0.5 * 1.1 + 0.5 * 0.9 * 1.2)
    assert all(not item.rebalanced for item in result.sessions)
    assert all(item.turnover == 0.0 for item in result.sessions)
    assert all(item.cost_fraction == 0.0 for item in result.sessions)


@pytest.mark.parametrize(
    "bad_factor",
    [0.0, -1.0, float("nan"), float("inf"), "1.0", True],
)
def test_nonpositive_nonfinite_or_nonnumeric_gross_factor_is_rejected(
    bad_factor: object,
) -> None:
    with pytest.raises(ValueError, match="gross_factor"):
        run_fixed_weight_backtest(
            (
                GrossFactorRow(date(2026, 1, 1), "AAA", bad_factor),  # type: ignore[arg-type]
                GrossFactorRow(date(2026, 1, 1), "BBB", 1.0),
            ),
            {"AAA": 0.5, "BBB": 0.5},
        )


def test_missing_symbol_is_rejected() -> None:
    with pytest.raises(ValueError, match="missing=\\['BBB'\\]"):
        run_fixed_weight_backtest(
            (GrossFactorRow(date(2026, 1, 1), "AAA", 1.0),),
            {"AAA": 0.5, "BBB": 0.5},
        )


def test_duplicate_symbol_within_session_is_rejected() -> None:
    session = date(2026, 1, 1)
    with pytest.raises(ValueError, match="duplicate symbol"):
        run_fixed_weight_backtest(
            (
                GrossFactorRow(session, "AAA", 1.0),
                GrossFactorRow(session, "AAA", 1.0),
                GrossFactorRow(session, "BBB", 1.0),
            ),
            {"AAA": 0.5, "BBB": 0.5},
        )


def test_symbol_order_is_strict_and_deterministic() -> None:
    session = date(2026, 1, 1)
    with pytest.raises(ValueError, match="strictly sorted"):
        run_fixed_weight_backtest(
            (
                GrossFactorRow(session, "BBB", 1.0),
                GrossFactorRow(session, "AAA", 1.0),
            ),
            {"AAA": 0.5, "BBB": 0.5},
        )


@pytest.mark.parametrize("dates", [(2, 1), (1, 2, 1)])
def test_session_dates_cannot_move_backwards_or_repeat_as_a_second_block(
    dates: tuple[int, ...],
) -> None:
    first = date(2026, 1, 1)
    rows: list[GrossFactorRow] = []
    for day in dates:
        session = first + timedelta(days=day - 1)
        rows.extend(
            (
                GrossFactorRow(session, "AAA", 1.0),
                GrossFactorRow(session, "BBB", 1.0),
            )
        )
    with pytest.raises(ValueError, match="strictly increasing"):
        run_fixed_weight_backtest(
            tuple(rows),
            {"AAA": 0.5, "BBB": 0.5},
        )


@pytest.mark.parametrize(
    "weights",
    [
        {},
        {"AAA": 0.5, "BBB": 0.4},
        {"AAA": 1.0, "BBB": 0.0},
        {"AAA": 1.1, "BBB": -0.1},
        {"AAA": float("nan"), "BBB": 0.5},
        {"AAA ": 0.5, "BBB": 0.5},
    ],
)
def test_illegal_target_weights_are_rejected(weights: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        run_fixed_weight_backtest(_rows([(1.0, 1.0)]), weights)


@pytest.mark.parametrize("bad_cost", [-1.0, 10_000.0, float("nan"), float("inf")])
def test_illegal_costs_are_rejected(bad_cost: float) -> None:
    with pytest.raises(ValueError, match="cost_bps"):
        run_fixed_weight_backtest(
            _rows([(1.0, 1.0)]),
            {"AAA": 0.5, "BBB": 0.5},
            cost_bps=bad_cost,
        )


@pytest.mark.parametrize("bad_interval", [0, -1, 1.5, True])
def test_illegal_rebalance_intervals_are_rejected(bad_interval: object) -> None:
    with pytest.raises(ValueError, match="rebalance_interval"):
        run_fixed_weight_backtest(
            _rows([(1.0, 1.0)]),
            {"AAA": 0.5, "BBB": 0.5},
            rebalance_interval=bad_interval,  # type: ignore[arg-type]
        )


def test_datetime_session_and_unexpected_symbol_are_rejected() -> None:
    with pytest.raises(ValueError, match="not a datetime"):
        run_fixed_weight_backtest(
            (
                GrossFactorRow(datetime(2026, 1, 1), "AAA", 1.0),
                GrossFactorRow(datetime(2026, 1, 1), "BBB", 1.0),
            ),
            {"AAA": 0.5, "BBB": 0.5},
        )

    session = date(2026, 1, 1)
    with pytest.raises(ValueError, match="unexpected=\\['CCC'\\]"):
        run_fixed_weight_backtest(
            (
                GrossFactorRow(session, "AAA", 1.0),
                GrossFactorRow(session, "CCC", 1.0),
            ),
            {"AAA": 0.5, "BBB": 0.5},
        )
