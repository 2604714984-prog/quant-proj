from datetime import date

import pytest

from quant_system.backtest.costs import TransactionCostModel
from quant_system.backtest.portfolio import InsufficientSharesError, Portfolio
from quant_system.markets.a_share import AShareBar, decide_fill, require_board_lot
from quant_system.markets.common import MarketDataError


def test_suspension_and_locked_limits_reject_only_the_blocked_side() -> None:
    assert decide_fill("buy", AShareBar(10.0, is_suspended=True)).reason == "suspended"
    assert decide_fill("buy", AShareBar(10.0, up_limit=10.0)).reason == (
        "limit_up_buy_rejected"
    )
    assert decide_fill("sell", AShareBar(9.0, down_limit=9.0)).reason == (
        "limit_down_sell_rejected"
    )

    allowed_buy = decide_fill("buy", AShareBar(9.9, up_limit=10.0), slippage_bps=5.0)
    allowed_sell = decide_fill("sell", AShareBar(9.1, down_limit=9.0))
    assert allowed_buy.filled is True
    assert allowed_buy.price == pytest.approx(9.90495)
    assert allowed_sell.filled is True


def test_invalid_market_inputs_fail_closed() -> None:
    assert decide_fill("buy", AShareBar(None)).reason == "missing_or_invalid_price"
    assert decide_fill("sell", AShareBar(float("nan"))).filled is False
    with pytest.raises(MarketDataError, match="up_limit"):
        decide_fill("buy", AShareBar(10.0, up_limit=float("nan")))
    with pytest.raises(ValueError, match="multiple of 100"):
        require_board_lot(50)


def test_a_share_t_plus_one_blocks_same_day_sale_and_releases_next_session() -> None:
    zero_cost = TransactionCostModel()
    portfolio = Portfolio.a_share(10_000.0, costs=zero_cost)
    day_one = date(2026, 7, 13)
    day_two = date(2026, 7, 14)

    portfolio.start_session(day_one)
    portfolio.buy("000001.SZ", 100, 10.0, day_one)
    assert portfolio.positions["000001.SZ"].sellable_shares == 0

    portfolio.start_session(day_one)
    with pytest.raises(InsufficientSharesError):
        portfolio.sell("000001.SZ", 100, 10.0, day_one)

    portfolio.start_session(day_two)
    trade = portfolio.sell("000001.SZ", 100, 10.5, day_two)
    assert trade.realized_pnl == pytest.approx(50.0)
    assert portfolio.available_cash == pytest.approx(10_050.0)


def test_a_share_default_costs_are_included_in_cash_and_basis() -> None:
    portfolio = Portfolio.a_share(20_000.0)
    trade_date = date(2026, 7, 13)
    portfolio.start_session(trade_date)

    trade = portfolio.buy("000001.SZ", 1000, 10.0, trade_date)

    assert trade.costs.commission == pytest.approx(5.0)
    assert portfolio.available_cash == pytest.approx(9_995.0)
    assert portfolio.positions["000001.SZ"].average_cost == pytest.approx(10.005)
