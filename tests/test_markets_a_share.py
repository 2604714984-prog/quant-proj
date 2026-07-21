from datetime import date

import pytest

from quant_system.backtest.costs import TransactionCostModel
from quant_system.backtest.portfolio import InsufficientSharesError, Portfolio
from quant_system.markets.a_share import (
    AShareBar,
    decide_fill,
    require_board_lot,
    stamp_tax_rate,
)
from quant_system.markets.common import MarketDataError


def test_suspension_and_locked_limits_reject_only_the_blocked_side() -> None:
    assert decide_fill(
        "buy",
        AShareBar(10.0, data_qualified=True, is_suspended=True),
    ).reason == "suspended"
    assert decide_fill(
        "buy",
        AShareBar(10.0, data_qualified=True, up_limit=10.0),
    ).reason == (
        "limit_up_buy_rejected"
    )
    assert decide_fill(
        "sell",
        AShareBar(9.0, data_qualified=True, down_limit=9.0),
    ).reason == (
        "limit_down_sell_rejected"
    )

    allowed_buy = decide_fill(
        "buy",
        AShareBar(9.9, data_qualified=True, up_limit=10.0),
        slippage_bps=5.0,
    )
    allowed_sell = decide_fill(
        "sell",
        AShareBar(9.1, data_qualified=True, down_limit=9.0),
    )
    assert allowed_buy.filled is True
    assert allowed_buy.price == pytest.approx(9.90495)
    assert allowed_sell.filled is True


def test_invalid_market_inputs_fail_closed() -> None:
    with pytest.raises(MarketDataError, match="explicitly complete"):
        decide_fill("buy", AShareBar(10.0))
    with pytest.raises(MarketDataError, match="positive finite open"):
        decide_fill("buy", AShareBar(None, data_qualified=True))
    with pytest.raises(MarketDataError, match="positive finite open"):
        decide_fill("sell", AShareBar(float("nan"), data_qualified=True))
    with pytest.raises(MarketDataError, match="up_limit"):
        decide_fill(
            "buy",
            AShareBar(10.0, data_qualified=True, up_limit=float("nan")),
        )
    with pytest.raises(MarketDataError, match="exceeds"):
        decide_fill(
            "buy",
            AShareBar(10.1, data_qualified=True, up_limit=10.0),
        )
    with pytest.raises(MarketDataError, match="down_limit cannot exceed"):
        decide_fill(
            "buy",
            AShareBar(
                10.0,
                down_limit=11.0,
                up_limit=10.0,
                data_qualified=True,
            ),
        )
    with pytest.raises(ValueError, match="multiple of 100"):
        require_board_lot(50)


def test_suspended_bar_is_an_explicit_explanation_for_missing_open() -> None:
    decision = decide_fill(
        "sell",
        AShareBar(None, data_qualified=True, is_suspended=True),
    )
    assert (decision.filled, decision.reason) == (False, "suspended")


def test_slippage_crossing_qualified_daily_limits_is_an_unfilled_order() -> None:
    buy = decide_fill(
        "buy",
        AShareBar(9.99, up_limit=10.0, data_qualified=True),
        slippage_bps=20.0,
    )
    sell = decide_fill(
        "sell",
        AShareBar(9.01, down_limit=9.0, data_qualified=True),
        slippage_bps=20.0,
    )

    assert buy == type(buy)(False, None, "slippage_crosses_up_limit")
    assert sell == type(sell)(False, None, "slippage_crosses_down_limit")


def test_slippage_inside_limit_tolerance_remains_fillable_without_capping() -> None:
    buy = decide_fill(
        "buy",
        AShareBar(9.9989, up_limit=10.0, data_qualified=True),
        slippage_bps=1.2,
    )
    sell = decide_fill(
        "sell",
        AShareBar(9.0011, down_limit=9.0, data_qualified=True),
        slippage_bps=1.3,
    )

    assert buy.filled is True
    assert buy.price == pytest.approx(10.000099868)
    assert sell.filled is True
    assert sell.price == pytest.approx(8.999929857)


@pytest.mark.parametrize(
    "side, price",
    [("buy", 1e308), ("sell", 5e-324)],
)
def test_slippage_nonfinite_or_nonpositive_result_fails_closed(
    side: str,
    price: float,
) -> None:
    with pytest.raises(MarketDataError, match="slippage-adjusted price"):
        decide_fill(
            side,
            AShareBar(price, data_qualified=True),
            slippage_bps=9999.0,
        )


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
    assert trade.realized_pnl == pytest.approx(49.475)
    assert portfolio.available_cash == pytest.approx(10_049.475)


def test_a_share_default_costs_are_included_in_cash_and_basis() -> None:
    portfolio = Portfolio.a_share(20_000.0)
    trade_date = date(2026, 7, 13)
    portfolio.start_session(trade_date)

    trade = portfolio.buy("000001.SZ", 1000, 10.0, trade_date)

    assert trade.costs.commission == pytest.approx(5.0)
    assert portfolio.available_cash == pytest.approx(9_995.0)
    assert portfolio.positions["000001.SZ"].average_cost == pytest.approx(10.005)


def test_a_share_stamp_tax_schedule_uses_trade_date() -> None:
    assert stamp_tax_rate(date(2023, 8, 27)) == pytest.approx(0.001)
    assert stamp_tax_rate(date(2023, 8, 28)) == pytest.approx(0.0005)

    old = Portfolio.a_share(20_000.0)
    old.start_session(date(2023, 8, 24))
    old.buy("000001.SZ", 100, 10.0, date(2023, 8, 24))
    old.start_session(date(2023, 8, 25))
    old_sale = old.sell("000001.SZ", 100, 10.0, date(2023, 8, 25))

    new = Portfolio.a_share(20_000.0)
    new.start_session(date(2023, 8, 25))
    new.buy("000001.SZ", 100, 10.0, date(2023, 8, 25))
    new.start_session(date(2023, 8, 28))
    new_sale = new.sell("000001.SZ", 100, 10.0, date(2023, 8, 28))

    assert old_sale.costs.sell_tax == pytest.approx(1.0)
    assert new_sale.costs.sell_tax == pytest.approx(0.5)


def test_custom_commission_keeps_statutory_stamp_tax_schedule() -> None:
    custom = TransactionCostModel(
        commission_rate=0.001,
        minimum_commission=0.0,
        sell_tax_rate=0.0,
    )
    portfolio = Portfolio.a_share(20_000.0, costs=custom)
    portfolio.start_session(date(2023, 8, 25))
    portfolio.buy("000001.SZ", 100, 10.0, date(2023, 8, 25))
    portfolio.start_session(date(2023, 8, 28))
    sale = portfolio.sell("000001.SZ", 100, 10.0, date(2023, 8, 28))

    assert sale.costs.commission == pytest.approx(1.0)
    assert sale.costs.sell_tax == pytest.approx(0.5)


def test_a_share_odd_lot_requires_corporate_action_and_full_liquidation() -> None:
    portfolio = Portfolio.a_share(20_000.0, costs=TransactionCostModel())
    day_one = date(2026, 7, 13)
    day_two = date(2026, 7, 14)
    portfolio.start_session(day_one)
    with pytest.raises(ValueError, match="multiple of 100"):
        portfolio.buy("000001.SZ", 50, 10.0, day_one)
    portfolio.buy("000001.SZ", 100, 10.0, day_one)
    portfolio.apply_split("000001.SZ", 1.5)
    portfolio.start_session(day_two)

    with pytest.raises(ValueError, match="fully liquidate"):
        portfolio.sell("000001.SZ", 50, 10.0, day_two)
    portfolio.sell("000001.SZ", 100, 10.0, day_two)
    remainder = portfolio.positions["000001.SZ"]
    assert (remainder.shares, remainder.sellable_shares) == (50.0, 50.0)
    portfolio.sell("000001.SZ", 50, 10.0, day_two)
    assert "000001.SZ" not in portfolio.positions
