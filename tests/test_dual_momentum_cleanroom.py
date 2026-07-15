from datetime import date, timedelta
import math

import pytest

from quant_system.backtest.dual_momentum import (
    MonthlyTarget,
    OpenCloseBar,
    build_dual_momentum_targets,
    build_static_targets,
    run_monthly_open_close_backtest,
)


def _trend_rows(
    risky: tuple[str, ...] = ("AAA", "BBB", "CCC"),
    cash: str = "CASH",
    days: int = 330,
) -> tuple[OpenCloseBar, ...]:
    symbols = tuple(sorted((*risky, cash)))
    drifts = {"AAA": 0.0030, "BBB": 0.0024, "CCC": 0.0008, cash: 0.0001}
    rows: list[OpenCloseBar] = []
    start = date(2024, 1, 1)
    for offset in range(days):
        session = start + timedelta(days=offset)
        for index, symbol in enumerate(symbols):
            close = 100.0 * math.exp(
                drifts[symbol] * offset + 0.004 * math.sin(offset * (index + 1) / 3.0)
            )
            rows.append(OpenCloseBar(session, symbol, close * 0.999, close))
    return tuple(rows)


def test_month_end_signal_uses_exact_252_21_formula_and_frozen_order() -> None:
    rows = _trend_rows()
    targets = build_dual_momentum_targets(rows, ("AAA", "BBB", "CCC"), "CASH")

    first = targets[0]
    assert first.execution_date == first.decision_date + timedelta(days=1)
    assert first.selected_symbols == ("AAA", "BBB")
    momenta = dict(first.momentum_by_symbol)
    by_key = {(row.session_date, row.symbol): row for row in rows}
    decision_index = (first.decision_date - date(2024, 1, 1)).days
    expected = (
        by_key[(date(2024, 1, 1) + timedelta(days=decision_index - 21), "AAA")].close_price
        / by_key[(date(2024, 1, 1) + timedelta(days=decision_index - 252), "AAA")].close_price
        - 1.0
    )
    assert momenta["AAA"] == pytest.approx(expected)


def test_exact_sixty_return_ddof1_inverse_volatility_weight() -> None:
    rows = _trend_rows()
    first = build_dual_momentum_targets(rows, ("AAA", "BBB", "CCC"), "CASH")[0]
    by_key = {(row.session_date, row.symbol): row for row in rows}
    decision_index = (first.decision_date - date(2024, 1, 1)).days
    expected_volatility = {}
    for symbol in first.selected_symbols:
        returns = []
        for offset in range(decision_index - 59, decision_index + 1):
            current = by_key[(date(2024, 1, 1) + timedelta(days=offset), symbol)].close_price
            prior = by_key[(date(2024, 1, 1) + timedelta(days=offset - 1), symbol)].close_price
            returns.append(current / prior - 1.0)
        mean = math.fsum(returns) / 60
        expected_volatility[symbol] = math.sqrt(
            math.fsum((value - mean) ** 2 for value in returns) / 59
        )
    assert dict(first.volatility_by_symbol) == pytest.approx(expected_volatility)
    inverse = {symbol: 1.0 / value for symbol, value in expected_volatility.items()}
    inverse_total = math.fsum(inverse.values())
    expected_weights = {
        symbol: min(inverse[symbol] / inverse_total, 0.6) for symbol in first.selected_symbols
    }
    for symbol, expected_weight in expected_weights.items():
        assert dict(first.weights)[symbol] == pytest.approx(expected_weight)


def test_selected_zero_volatility_fails_closed() -> None:
    rows = []
    start = date(2024, 1, 1)
    for offset in range(330):
        session = start + timedelta(days=offset)
        for symbol in ("AAA", "BBB", "CASH"):
            if symbol == "AAA":
                close = 100.0 + min(offset, 200)
            elif symbol == "BBB":
                close = 200.0 - 0.1 * offset
            else:
                close = 100.0
            rows.append(OpenCloseBar(session, symbol, close, close))
    with pytest.raises(ValueError, match="strictly positive"):
        build_dual_momentum_targets(tuple(rows), ("AAA", "BBB"), "CASH")


def test_exact_momentum_tie_uses_caller_risky_order() -> None:
    rows = list(_trend_rows(risky=("AAA", "BBB")))
    for index, row in enumerate(rows):
        if row.symbol == "BBB":
            matching = next(
                item for item in rows if item.session_date == row.session_date and item.symbol == "AAA"
            )
            rows[index] = OpenCloseBar(
                row.session_date,
                row.symbol,
                matching.open_price,
                matching.close_price,
            )
    targets = build_dual_momentum_targets(tuple(rows), ("BBB", "AAA"), "CASH", top_count=1)
    assert targets[0].selected_symbols == ("BBB",)


def test_cash_filter_can_produce_all_cash_target() -> None:
    rows = list(_trend_rows(risky=("AAA", "BBB")))
    start = date(2024, 1, 1)
    for index, row in enumerate(rows):
        if row.symbol == "CASH":
            close = 100.0 * math.exp(0.01 * (row.session_date - start).days)
            rows[index] = OpenCloseBar(row.session_date, row.symbol, close, close)
    targets = build_dual_momentum_targets(tuple(rows), ("AAA", "BBB"), "CASH")
    assert targets[0].selected_symbols == ()
    assert dict(targets[0].weights) == {"AAA": 0.0, "BBB": 0.0, "CASH": 1.0}


def test_cap_is_direct_clip_without_redistribution() -> None:
    targets = build_dual_momentum_targets(
        _trend_rows(),
        ("AAA", "BBB", "CCC"),
        "CASH",
        single_risky_cap=0.51,
    )
    weights = dict(targets[0].weights)
    assert max(weights["AAA"], weights["BBB"]) <= 0.51
    assert weights["CASH"] == pytest.approx(1.0 - weights["AAA"] - weights["BBB"])


def _golden_rows() -> tuple[OpenCloseBar, ...]:
    rows = []
    for session, values in (
        (date(2026, 1, 1), {"AAA": (100.0, 100.0), "CASH": (100.0, 100.0)}),
        (date(2026, 1, 2), {"AAA": (110.0, 121.0), "CASH": (100.0, 100.0)}),
        (date(2026, 1, 3), {"AAA": (121.0, 121.0), "CASH": (100.0, 100.0)}),
    ):
        for symbol in ("AAA", "CASH"):
            open_price, close_price = values[symbol]
            rows.append(OpenCloseBar(session, symbol, open_price, close_price))
    return tuple(rows)


def _golden_target() -> MonthlyTarget:
    return MonthlyTarget(
        decision_date=date(2026, 1, 1),
        execution_date=date(2026, 1, 2),
        weights=(("AAA", 0.5), ("CASH", 0.5)),
        selected_symbols=("AAA",),
        momentum_by_symbol=(),
        volatility_by_symbol=(),
    )


def test_open_rebalance_golden_charges_full_l1_and_then_intraday() -> None:
    result = run_monthly_open_close_backtest(
        _golden_rows(),
        (_golden_target(),),
        cash_like_symbol="CASH",
        cost_bps_per_turnover_side=100.0,
    )

    first = result.sessions[0]
    assert first.overnight_factor == pytest.approx(1.0)
    assert first.turnover == pytest.approx(1.0)
    assert first.cost_fraction == pytest.approx(0.01)
    assert first.intraday_factor == pytest.approx(1.05)
    assert first.net_factor == pytest.approx(0.99 * 1.05)
    assert first.wealth == pytest.approx(1.0395)
    assert result.sessions[1].rebalanced is False
    assert result.sessions[1].turnover == 0.0
    assert result.final_wealth == pytest.approx(1.0395)


def test_second_rebalance_golden_charges_drifted_overnight_full_l1() -> None:
    rows = []
    for session, values in (
        (date(2026, 1, 1), {"AAA": (100.0, 100.0), "CASH": (100.0, 100.0)}),
        (date(2026, 1, 2), {"AAA": (100.0, 100.0), "CASH": (100.0, 100.0)}),
        (date(2026, 1, 3), {"AAA": (200.0, 200.0), "CASH": (100.0, 100.0)}),
    ):
        for symbol in ("AAA", "CASH"):
            rows.append(OpenCloseBar(session, symbol, *values[symbol]))
    first = MonthlyTarget(
        decision_date=date(2026, 1, 1),
        execution_date=date(2026, 1, 2),
        weights=(("AAA", 0.5), ("CASH", 0.5)),
        selected_symbols=("AAA",),
        momentum_by_symbol=(),
        volatility_by_symbol=(),
    )
    second = MonthlyTarget(
        decision_date=date(2026, 1, 2),
        execution_date=date(2026, 1, 3),
        weights=(("AAA", 0.5), ("CASH", 0.5)),
        selected_symbols=("AAA",),
        momentum_by_symbol=(),
        volatility_by_symbol=(),
    )
    result = run_monthly_open_close_backtest(
        tuple(rows),
        (first, second),
        cash_like_symbol="CASH",
        cost_bps_per_turnover_side=50.0,
    )
    second_session = result.sessions[1]
    assert second_session.overnight_factor == pytest.approx(1.5)
    assert second_session.turnover == pytest.approx(1.0 / 3.0)
    assert second_session.cost_fraction == pytest.approx(0.0016666666666666668)


def test_pre_first_target_period_carries_cash_like_from_frozen_initial_close() -> None:
    rows = []
    for session, values in (
        (date(2026, 1, 1), {"AAA": (100.0, 100.0), "CASH": (100.0, 100.0)}),
        (date(2026, 1, 2), {"AAA": (100.0, 100.0), "CASH": (101.0, 102.0)}),
        (date(2026, 1, 3), {"AAA": (100.0, 100.0), "CASH": (102.0, 102.0)}),
    ):
        for symbol in ("AAA", "CASH"):
            rows.append(OpenCloseBar(session, symbol, *values[symbol]))
    target = MonthlyTarget(
        decision_date=date(2026, 1, 2),
        execution_date=date(2026, 1, 3),
        weights=(("AAA", 0.5), ("CASH", 0.5)),
        selected_symbols=("AAA",),
        momentum_by_symbol=(),
        volatility_by_symbol=(),
    )
    result = run_monthly_open_close_backtest(
        tuple(rows),
        (target,),
        cash_like_symbol="CASH",
        cost_bps_per_turnover_side=0.0,
        initial_close_date=date(2026, 1, 1),
    )
    assert [item.session_date for item in result.sessions] == [
        date(2026, 1, 2),
        date(2026, 1, 3),
    ]
    assert result.sessions[0].rebalanced is False
    assert result.sessions[0].net_factor == pytest.approx(1.02)
    assert result.sessions[1].rebalanced is True


def test_static_targets_preserve_schedule_and_require_full_symbol_mapping() -> None:
    target = _golden_target()
    static = build_static_targets((target,), {"AAA": 0.2, "CASH": 0.8})
    assert static[0].decision_date == target.decision_date
    assert static[0].execution_date == target.execution_date
    assert dict(static[0].weights) == {"AAA": 0.2, "CASH": 0.8}
    with pytest.raises(ValueError, match="exactly"):
        build_static_targets((target,), {"AAA": 1.0})


@pytest.mark.parametrize("bad", [0.0, -1.0, float("nan"), float("inf"), True])
def test_bad_open_or_close_fails_closed(bad: object) -> None:
    rows = list(_golden_rows())
    first = rows[0]
    rows[0] = OpenCloseBar(first.session_date, first.symbol, bad, first.close_price)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="open_price"):
        run_monthly_open_close_backtest(
            tuple(rows),
            (_golden_target(),),
            cash_like_symbol="CASH",
            cost_bps_per_turnover_side=0.0,
        )


def test_missing_duplicate_or_out_of_order_common_rows_fail_closed() -> None:
    rows = _golden_rows()
    with pytest.raises(ValueError, match="missing"):
        run_monthly_open_close_backtest(
            rows[:-1],
            (_golden_target(),),
            cash_like_symbol="CASH",
            cost_bps_per_turnover_side=0.0,
        )
    with pytest.raises(ValueError, match="duplicate"):
        run_monthly_open_close_backtest(
            (rows[0], rows[0], *rows[1:]),
            (_golden_target(),),
            cash_like_symbol="CASH",
            cost_bps_per_turnover_side=0.0,
        )
    with pytest.raises(ValueError, match="strictly increasing"):
        run_monthly_open_close_backtest(
            (*rows[2:4], *rows[:2], *rows[4:]),
            (_golden_target(),),
            cash_like_symbol="CASH",
            cost_bps_per_turnover_side=0.0,
        )


def test_target_must_execute_on_immediate_following_common_session() -> None:
    target = MonthlyTarget(
        decision_date=date(2026, 1, 1),
        execution_date=date(2026, 1, 3),
        weights=(("AAA", 0.5), ("CASH", 0.5)),
        selected_symbols=("AAA",),
        momentum_by_symbol=(),
        volatility_by_symbol=(),
    )
    with pytest.raises(ValueError, match="immediately after decision"):
        run_monthly_open_close_backtest(
            _golden_rows(),
            (target,),
            cash_like_symbol="CASH",
            cost_bps_per_turnover_side=0.0,
        )
