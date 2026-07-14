from datetime import date

import pytest

from quant_system.backtest.costs import TransactionCostModel
from quant_system.backtest.portfolio import Portfolio


def test_cost_model_uses_commission_floor_and_sell_only_tax() -> None:
    model = TransactionCostModel(
        commission_rate=0.0003,
        minimum_commission=5.0,
        sell_tax_rate=0.001,
    )
    buy = model.calculate("buy", 10_000.0)
    sell = model.calculate("sell", 10_000.0)

    assert (buy.commission, buy.sell_tax, buy.total) == (5.0, 0.0, 5.0)
    assert (sell.commission, sell.sell_tax, sell.total) == (5.0, 10.0, 15.0)


def test_cost_model_derived_nonfinite_values_fail_closed() -> None:
    with pytest.raises(ValueError, match="commission"):
        TransactionCostModel(commission_rate=1e308).calculate("buy", 1e308)
    with pytest.raises(ValueError, match="sell tax"):
        TransactionCostModel(sell_tax_rate=1e308).calculate("sell", 1e308)
    with pytest.raises(ValueError, match="total"):
        TransactionCostModel(
            commission_rate=1.0,
            sell_tax_rate=1.0,
        ).calculate("sell", 1e308)


def test_nav_uses_settled_pending_and_accepted_marks_without_zero_fill() -> None:
    portfolio = Portfolio.us(1_000.0, costs=TransactionCostModel())
    day_one = date(2026, 7, 13)
    day_two = date(2026, 7, 14)
    portfolio.start_session(day_one)
    portfolio.buy("ABC", 10, 10.0, day_one)

    assert portfolio.nav({"ABC": 11.0}) == pytest.approx(1_010.0)
    with pytest.raises(ValueError, match="accepted mark"):
        portfolio.nav({})

    portfolio.sell(
        "ABC",
        10,
        11.0,
        day_one,
        settlement_date=day_two,
        accepted_settlement_sessions=(day_two,),
    )
    assert portfolio.nav({}) == pytest.approx(1_010.0)


def test_split_updates_portfolio_quantity_basis_and_last_mark() -> None:
    portfolio = Portfolio.us(1_000.0, costs=TransactionCostModel())
    trade_date = date(2026, 7, 13)
    portfolio.start_session(trade_date)
    portfolio.buy("ABC", 10, 10.0, trade_date)

    portfolio.apply_split("ABC", 2.0)

    position = portfolio.positions["ABC"]
    assert position.shares == 20.0
    assert position.sellable_shares == 20.0
    assert position.average_cost == pytest.approx(5.0)
    assert position.last_accepted_mark == pytest.approx(5.0)


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), -1.0])
def test_nonfinite_or_negative_inputs_fail_closed(bad_value: float) -> None:
    with pytest.raises(ValueError):
        TransactionCostModel(commission_rate=bad_value)

    portfolio = Portfolio.us(1_000.0, costs=TransactionCostModel())
    trade_date = date(2026, 7, 13)
    portfolio.start_session(trade_date)
    with pytest.raises(ValueError):
        portfolio.buy("ABC", 1, bad_value, trade_date)


def test_sessions_cannot_move_backwards() -> None:
    portfolio = Portfolio.us(1_000.0, costs=TransactionCostModel())
    portfolio.start_session(date(2026, 7, 14))
    with pytest.raises(ValueError, match="chronologically"):
        portfolio.start_session(date(2026, 7, 13))


def test_nonfinite_buy_arithmetic_fails_before_mutation() -> None:
    costs = TransactionCostModel(commission_rate=1e308)
    portfolio = Portfolio.us(1e308, costs=costs)
    trade_date = date(2026, 7, 13)
    portfolio.start_session(trade_date)

    with pytest.raises(ValueError, match="commission"):
        portfolio.buy("ABC", 1, 1e308, trade_date)

    assert portfolio.available_cash == 1e308
    assert portfolio.positions == {}


def test_failed_nav_does_not_partially_update_marks() -> None:
    portfolio = Portfolio.us(1_000.0, costs=TransactionCostModel())
    trade_date = date(2026, 7, 13)
    portfolio.start_session(trade_date)
    portfolio.buy("AAA", 10, 10.0, trade_date)
    portfolio.buy("BBB", 10, 10.0, trade_date)

    with pytest.raises(ValueError, match="accepted mark"):
        portfolio.nav({"AAA": 12.0, "BBB": float("nan")})

    assert portfolio.positions["AAA"].last_accepted_mark == 10.0
    assert portfolio.positions["BBB"].last_accepted_mark == 10.0


def test_cash_and_split_overflow_fail_before_mutation() -> None:
    portfolio = Portfolio.us(1e308, costs=TransactionCostModel())
    with pytest.raises(ValueError, match="settled cash"):
        portfolio.credit_cash(1e308)
    assert portfolio.available_cash == 1e308

    trade_date = date(2026, 7, 13)
    portfolio.start_session(trade_date)
    portfolio.buy("ABC", 1, 1.0, trade_date)
    before = portfolio.positions["ABC"]
    before_values = (
        before.shares,
        before.sellable_shares,
        before.average_cost,
        before.last_accepted_mark,
        before.corporate_action_odd_lot,
    )
    with pytest.raises(ValueError, match="split adjustment"):
        portfolio.apply_split("ABC", 1e-309)
    after = portfolio.positions["ABC"]
    assert (
        after.shares,
        after.sellable_shares,
        after.average_cost,
        after.last_accepted_mark,
        after.corporate_action_odd_lot,
    ) == before_values


def test_pending_cash_overflow_fails_before_sale_mutation() -> None:
    portfolio = Portfolio.us(2.0, costs=TransactionCostModel())
    trade_date = date(2026, 7, 13)
    settlement_date = date(2026, 7, 14)
    portfolio.start_session(trade_date)
    portfolio.buy("AAA", 1, 1.0, trade_date)
    portfolio.buy("BBB", 1, 1.0, trade_date)
    portfolio.sell(
        "AAA",
        1,
        1e308,
        trade_date,
        settlement_date=settlement_date,
        accepted_settlement_sessions=(settlement_date,),
    )
    before = portfolio.positions["BBB"]
    before_values = (
        before.shares,
        before.sellable_shares,
        before.average_cost,
        before.last_accepted_mark,
    )

    with pytest.raises(ValueError, match="pending cash total after sale"):
        portfolio.sell(
            "BBB",
            1,
            1e308,
            trade_date,
            settlement_date=settlement_date,
            accepted_settlement_sessions=(settlement_date,),
        )

    after = portfolio.positions["BBB"]
    assert (
        after.shares,
        after.sellable_shares,
        after.average_cost,
        after.last_accepted_mark,
    ) == before_values
    assert portfolio.pending_cash_total == 1e308
