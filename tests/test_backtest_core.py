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


def test_terminal_delisting_recovery_is_settled_once_and_position_is_removed() -> None:
    portfolio = Portfolio.us(1_000.0, costs=TransactionCostModel())
    trade_date = date(2026, 7, 13)
    portfolio.start_session(trade_date)
    portfolio.buy("DELISTED", 10, 10.0, trade_date)

    recovery = portfolio.apply_terminal_action(
        "DELISTED",
        event_id="delisting-DELISTED-20260713-v1",
        action_type="delisting",
        recovery_per_share=2.5,
    )

    assert recovery == pytest.approx(25.0)
    assert portfolio.available_cash == pytest.approx(925.0)
    assert portfolio.positions == {}
    assert portfolio.nav({}) == pytest.approx(925.0)
    with pytest.raises(ValueError, match="already been applied"):
        portfolio.apply_terminal_action(
            "DELISTED",
            event_id="delisting-DELISTED-20260713-v1",
            action_type="delisting",
            recovery_per_share=2.5,
        )
    assert portfolio.available_cash == pytest.approx(925.0)


def test_zero_terminal_recovery_closes_position_without_a_zero_nav_mark() -> None:
    portfolio = Portfolio.us(100.0, costs=TransactionCostModel())
    trade_date = date(2026, 7, 13)
    portfolio.start_session(trade_date)
    portfolio.buy("ZERO", 1, 10.0, trade_date)

    assert portfolio.apply_terminal_action(
        "ZERO",
        event_id="delisting-ZERO-20260713-v1",
        action_type="delisting",
        recovery_per_share=0.0,
    ) == 0.0
    assert portfolio.positions == {}
    assert portfolio.nav({}) == pytest.approx(90.0)


@pytest.mark.parametrize("bad_recovery", [float("nan"), float("inf"), -1.0])
def test_invalid_terminal_recovery_fails_before_mutation(bad_recovery: float) -> None:
    portfolio = Portfolio.us(100.0, costs=TransactionCostModel())
    trade_date = date(2026, 7, 13)
    portfolio.start_session(trade_date)
    portfolio.buy("ABC", 1, 10.0, trade_date)

    with pytest.raises(ValueError, match="recovery_per_share"):
        portfolio.apply_terminal_action(
            "ABC",
            event_id="terminal-ABC-20260713-v1",
            action_type="delisting",
            recovery_per_share=bad_recovery,
        )

    assert portfolio.available_cash == pytest.approx(90.0)
    assert portfolio.positions["ABC"].shares == 1.0


@pytest.mark.parametrize("action_type", ["merger", "symbol_change"])
def test_stock_terminal_action_without_successor_mapping_fails_closed(
    action_type: str,
) -> None:
    portfolio = Portfolio.us(100.0, costs=TransactionCostModel())
    trade_date = date(2026, 7, 13)
    portfolio.start_session(trade_date)
    portfolio.buy("OLD", 2, 10.0, trade_date)

    with pytest.raises(ValueError, match="explicit successor mapping"):
        portfolio.apply_terminal_action(
            "OLD",
            event_id=f"{action_type}-OLD-20260713-v1",
            action_type=action_type,
            recovery_per_share=0.0,
        )

    assert portfolio.available_cash == pytest.approx(80.0)
    assert portfolio.positions["OLD"].shares == 2.0


def test_symbol_change_mapping_replaces_position_and_requires_a_fresh_mark() -> None:
    portfolio = Portfolio.us(1_000.0, costs=TransactionCostModel())
    trade_date = date(2026, 7, 13)
    portfolio.start_session(trade_date)
    portfolio.buy("OLD", 10, 10.0, trade_date)

    recovery = portfolio.apply_terminal_action(
        "OLD",
        event_id="symbol-change-OLD-NEW-20260713-v1",
        action_type="symbol_change",
        recovery_per_share=1.0,
        successor_symbol="NEW",
        successor_shares_per_share=0.5,
    )

    assert recovery == pytest.approx(10.0)
    assert "OLD" not in portfolio.positions
    successor = portfolio.positions["NEW"]
    assert successor.shares == pytest.approx(5.0)
    assert successor.sellable_shares == pytest.approx(5.0)
    assert successor.average_cost == pytest.approx(20.0)
    assert successor.last_accepted_mark is None
    assert portfolio.available_cash == pytest.approx(910.0)
    with pytest.raises(ValueError, match="accepted mark"):
        portfolio.nav({})
    assert portfolio.nav({"NEW": 20.0}) == pytest.approx(1_010.0)


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


def test_cash_distribution_freezes_ex_date_entitlement_and_settles_once() -> None:
    portfolio = Portfolio.us(1_000.0, costs=TransactionCostModel())
    prior_date = date(2026, 7, 10)
    ex_date = date(2026, 7, 13)
    pay_date = date(2026, 7, 15)
    portfolio.start_session(prior_date)
    portfolio.buy("ABC", 10, 10.0, prior_date)
    portfolio.start_session(ex_date)

    entitlement = portfolio.apply_cash_distribution(
        "ABC",
        event_id="abc-dividend-20260713-v1",
        amount_per_share=0.5,
        ex_date=ex_date,
        pay_date=pay_date,
    )

    assert entitlement == pytest.approx(5.0)
    assert portfolio.available_cash == pytest.approx(900.0)
    assert portfolio.pending_cash_total == pytest.approx(5.0)
    with pytest.raises(ValueError, match="already been applied"):
        portfolio.apply_cash_distribution(
            "ABC",
            event_id="abc-dividend-20260713-v1",
            amount_per_share=0.5,
            ex_date=ex_date,
            pay_date=pay_date,
        )
    portfolio.start_session(date(2026, 7, 14))
    assert portfolio.available_cash == pytest.approx(900.0)
    portfolio.start_session(pay_date)
    assert portfolio.available_cash == pytest.approx(905.0)
    assert portfolio.pending_cash_total == 0.0


def test_distribution_uses_session_open_shares_not_ex_date_trading() -> None:
    buyer = Portfolio.us(1_000.0, costs=TransactionCostModel())
    ex_date = date(2026, 7, 13)
    pay_date = date(2026, 7, 15)
    buyer.start_session(ex_date)
    buyer.buy("ABC", 10, 10.0, ex_date)
    assert buyer.apply_cash_distribution(
        "ABC",
        event_id="buyer-dividend",
        amount_per_share=0.5,
        ex_date=ex_date,
        pay_date=pay_date,
    ) == 0.0
    assert buyer.pending_cash_total == 0.0

    seller = Portfolio.us(1_000.0, costs=TransactionCostModel())
    prior_date = date(2026, 7, 10)
    seller.start_session(prior_date)
    seller.buy("ABC", 10, 10.0, prior_date)
    seller.start_session(ex_date)
    seller.sell(
        "ABC",
        10,
        10.0,
        ex_date,
        settlement_date=date(2026, 7, 14),
        accepted_settlement_sessions=(date(2026, 7, 14),),
    )
    assert seller.apply_cash_distribution(
        "ABC",
        event_id="seller-dividend",
        amount_per_share=0.5,
        ex_date=ex_date,
        pay_date=pay_date,
    ) == pytest.approx(5.0)
    assert seller.pending_cash_total == pytest.approx(105.0)


def test_cash_distribution_and_split_validation_fail_before_mutation() -> None:
    portfolio = Portfolio.us(1_000.0, costs=TransactionCostModel())
    prior_date = date(2026, 7, 10)
    ex_date = date(2026, 7, 13)
    portfolio.start_session(prior_date)
    portfolio.buy("ABC", 10, 10.0, prior_date)
    portfolio.start_session(ex_date)

    with pytest.raises(ValueError, match="pay_date"):
        portfolio.apply_cash_distribution(
            "ABC",
            event_id="bad-pay-date",
            amount_per_share=1.0,
            ex_date=ex_date,
            pay_date=date(2026, 7, 12),
        )
    assert portfolio.pending_cash_total == 0.0
    assert portfolio.apply_cash_distribution(
        "ABC",
        event_id="bad-pay-date",
        amount_per_share=1.0,
        ex_date=ex_date,
        pay_date=ex_date,
    ) == pytest.approx(10.0)

    portfolio.apply_split("ABC", 2.0, event_id="abc-split-v1")
    assert portfolio.positions["ABC"].shares == 20.0
    with pytest.raises(ValueError, match="already been applied"):
        portfolio.apply_split("ABC", 2.0, event_id="abc-split-v1")
    assert portfolio.positions["ABC"].shares == 20.0

    portfolio.apply_split("MISSING", 2.0, event_id="missing-split-v1")
    portfolio.buy("MISSING", 1, 10.0, ex_date)
    with pytest.raises(ValueError, match="already been applied"):
        portfolio.apply_split("MISSING", 2.0, event_id="missing-split-v1")
    assert portfolio.positions["MISSING"].shares == 1.0


def test_zero_tax_a_share_listed_fund_distribution_freezes_and_settles_once() -> None:
    portfolio = Portfolio(
        10_000.0,
        TransactionCostModel(sell_tax_rate=0.0),
        lot_size=100,
        share_t_plus_one=True,
        us_cash_settlement=False,
        a_share_stamp_tax_schedule=False,
    )
    prior_date = date(2026, 7, 10)
    ex_date = date(2026, 7, 13)
    pay_date = date(2026, 7, 15)
    portfolio.start_session(prior_date)
    portfolio.buy("510300.SH", 100, 10.0, prior_date)
    portfolio.start_session(ex_date)

    assert portfolio.supports_a_share_listed_fund_distributions is True
    assert portfolio.apply_cash_distribution(
        "510300.SH",
        event_id="510300-20260713-cash-v1",
        amount_per_share=0.5,
        ex_date=ex_date,
        pay_date=pay_date,
    ) == pytest.approx(50.0)
    sale = portfolio.sell("510300.SH", 100, 10.0, ex_date)
    assert sale.costs.sell_tax == 0.0
    assert portfolio.pending_cash_total == pytest.approx(50.0)
    with pytest.raises(ValueError, match="already been applied"):
        portfolio.apply_cash_distribution(
            "510300.SH",
            event_id="510300-20260713-cash-v1",
            amount_per_share=0.5,
            ex_date=ex_date,
            pay_date=pay_date,
        )

    portfolio.start_session(pay_date)
    settled_once = portfolio.available_cash
    assert settled_once == pytest.approx(10_050.0)
    portfolio.start_session(pay_date)
    assert portfolio.available_cash == settled_once


def test_a_share_listed_fund_ex_date_buy_has_no_prior_entitlement() -> None:
    portfolio = Portfolio(
        10_000.0,
        TransactionCostModel(),
        lot_size=100,
        share_t_plus_one=True,
        a_share_stamp_tax_schedule=False,
    )
    ex_date = date(2026, 7, 13)
    portfolio.start_session(ex_date)
    portfolio.buy("510300.SH", 100, 10.0, ex_date)

    assert portfolio.apply_cash_distribution(
        "510300.SH",
        event_id="510300-20260713-buyer-cash-v1",
        amount_per_share=0.5,
        ex_date=ex_date,
        pay_date=date(2026, 7, 15),
    ) == 0.0
    assert portfolio.pending_cash_total == 0.0


def test_a_share_stock_portfolio_still_rejects_cash_distribution() -> None:
    portfolio = Portfolio.a_share(10_000.0, costs=TransactionCostModel())
    prior_date = date(2026, 7, 10)
    ex_date = date(2026, 7, 13)
    portfolio.start_session(prior_date)
    portfolio.buy("600000.SH", 100, 10.0, prior_date)
    portfolio.start_session(ex_date)
    before_cash = portfolio.available_cash
    before_position = portfolio.positions["600000.SH"].shares

    assert portfolio.supports_a_share_listed_fund_distributions is False
    with pytest.raises(ValueError, match="zero-tax A-share listed-fund"):
        portfolio.apply_cash_distribution(
            "600000.SH",
            event_id="600000-20260713-cash-v1",
            amount_per_share=0.5,
            ex_date=ex_date,
            pay_date=date(2026, 7, 15),
        )
    assert portfolio.available_cash == before_cash
    assert portfolio.positions["600000.SH"].shares == before_position
    assert portfolio.pending_cash == []
