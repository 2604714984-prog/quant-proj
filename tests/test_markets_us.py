from datetime import date

import pytest

from quant_system.backtest.costs import TransactionCostModel
from quant_system.backtest.portfolio import InsufficientCashError, Portfolio
from quant_system.backtest.schedule import next_session
from quant_system.markets.us import (
    CorporateActionValuationError,
    UnexplainedProviderGapError,
    cash_distribution,
    decide_fill,
    resolve_mark,
    split_adjustment,
)


def test_us_halt_and_terminal_actions_override_a_positive_provider_price() -> None:
    halt = decide_fill("buy", 10.0, action_types={"trading_halt"})
    delisting = decide_fill("sell", 10.0, action_types={"delisting"})

    assert (halt.filled, halt.reason) == (False, "confirmed_halt")
    assert (delisting.filled, delisting.reason) == (
        False,
        "confirmed_terminal_action",
    )


def test_us_unknown_gap_fails_and_confirmed_halt_carries_only_prior_mark() -> None:
    with pytest.raises(UnexplainedProviderGapError, match="no accepted event"):
        decide_fill("buy", None)

    assert resolve_mark(
        symbol="ABC",
        current_price=12.0,
        previous_accepted_price=10.0,
        action_types={"trading_halt"},
    ) == pytest.approx(10.0)
    with pytest.raises(UnexplainedProviderGapError, match="no prior accepted"):
        resolve_mark(
            symbol="ABC",
            current_price=12.0,
            previous_accepted_price=None,
            action_types={"trading_halt"},
        )

    with pytest.raises(ValueError, match="unknown US corporate-action"):
        decide_fill("buy", 10.0, action_types={"mystery_event"})


def test_terminal_valuation_requires_explicit_action_complete_value() -> None:
    with pytest.raises(CorporateActionValuationError, match="terminal value"):
        resolve_mark(
            symbol="DELISTED",
            current_price=None,
            previous_accepted_price=8.0,
            action_types={"delisting"},
        )

    assert resolve_mark(
        symbol="DELISTED",
        current_price=None,
        previous_accepted_price=8.0,
        action_types={"delisting"},
        terminal_value=0.0,
    ) == 0.0


def test_split_and_cash_distribution_arithmetic_is_value_preserving() -> None:
    shares, average_cost = split_adjustment(10.0, 100.0, 2.0)
    assert (shares, average_cost) == (20.0, 50.0)
    assert shares * average_cost == pytest.approx(1_000.0)
    assert cash_distribution(shares, 0.25) == pytest.approx(5.0)


def test_us_sale_proceeds_are_pending_until_explicit_next_session() -> None:
    day_one = date(2026, 7, 13)
    day_two = date(2026, 7, 14)
    portfolio = Portfolio.us(1_000.0, costs=TransactionCostModel())
    portfolio.start_session(day_one)
    portfolio.buy("ABC", 10, 10.0, day_one)
    portfolio.sell("ABC", 10, 10.0, day_one, settlement_date=day_two)

    assert portfolio.available_cash == pytest.approx(900.0)
    assert portfolio.pending_cash_total == pytest.approx(100.0)
    assert portfolio.nav({}) == pytest.approx(1_000.0)
    with pytest.raises(InsufficientCashError):
        portfolio.buy("XYZ", 91, 10.0, day_one)

    portfolio.start_session(day_two)
    assert portfolio.available_cash == pytest.approx(1_000.0)
    assert portfolio.pending_cash_total == 0.0


def test_invalid_us_settlement_date_does_not_mutate_position() -> None:
    trade_date = date(2026, 7, 13)
    portfolio = Portfolio.us(1_000.0, costs=TransactionCostModel())
    portfolio.start_session(trade_date)
    portfolio.buy("ABC", 10, 10.0, trade_date)

    with pytest.raises(ValueError, match="settlement_date"):
        portfolio.sell("ABC", 10, 10.0, trade_date, settlement_date=trade_date)

    assert portfolio.positions["ABC"].shares == 10
    assert portfolio.pending_cash_total == 0.0


def test_close_signal_is_scheduled_for_next_accepted_session_open() -> None:
    sessions = (
        date(2026, 7, 10),
        date(2026, 7, 13),
        date(2026, 7, 14),
    )
    assert next_session(sessions, sessions[0]) == sessions[1]
    with pytest.raises(ValueError, match="strictly increasing"):
        next_session((sessions[1], sessions[0]), sessions[0])
