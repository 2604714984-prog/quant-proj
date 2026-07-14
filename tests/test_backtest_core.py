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


def test_nav_uses_settled_pending_and_accepted_marks_without_zero_fill() -> None:
    portfolio = Portfolio.us(1_000.0, costs=TransactionCostModel())
    day_one = date(2026, 7, 13)
    day_two = date(2026, 7, 14)
    portfolio.start_session(day_one)
    portfolio.buy("ABC", 10, 10.0, day_one)

    assert portfolio.nav({"ABC": 11.0}) == pytest.approx(1_010.0)
    with pytest.raises(ValueError, match="accepted mark"):
        portfolio.nav({})

    portfolio.sell("ABC", 10, 11.0, day_one, settlement_date=day_two)
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
