from datetime import date

import pytest

from quant_system.backtest.costs import TransactionCostModel
from quant_system.backtest.portfolio import InsufficientCashError, Portfolio
from quant_system.markets.common import MarketDataError
from quant_system.markets.us import (
    CorporateActionValuationError,
    GapPolicyError,
    UnexplainedProviderGapError,
    cash_distribution,
    cash_settlement_lag_sessions,
    decide_fill,
    require_accepted_settlement_sessions,
    resolve_mark,
    split_adjustment,
)


def test_us_halt_and_terminal_actions_override_a_positive_provider_price() -> None:
    halt = decide_fill(
        "buy",
        10.0,
        action_types={"trading_halt"},
        data_qualified=True,
    )
    delisting = decide_fill(
        "sell",
        10.0,
        action_types={"delisting"},
        data_qualified=True,
    )

    assert (halt.filled, halt.reason) == (False, "confirmed_halt")
    assert (delisting.filled, delisting.reason) == (
        False,
        "confirmed_terminal_action",
    )


def test_us_unknown_gap_fails_and_confirmed_halt_carries_only_prior_mark() -> None:
    with pytest.raises(UnexplainedProviderGapError, match="no accepted event"):
        decide_fill("buy", None, data_qualified=True)

    with pytest.raises(GapPolicyError, match="explicitly complete"):
        decide_fill("buy", 10.0)
    with pytest.raises(GapPolicyError, match="explicitly complete"):
        resolve_mark(
            symbol="ABC",
            current_price=12.0,
            previous_accepted_price=10.0,
        )
    assert resolve_mark(
        symbol="ABC",
        current_price=12.0,
        previous_accepted_price=10.0,
        data_qualified=True,
    ) == pytest.approx(12.0)

    assert resolve_mark(
        symbol="ABC",
        current_price=12.0,
        previous_accepted_price=10.0,
        action_types={"trading_halt"},
        data_qualified=True,
    ) == pytest.approx(10.0)
    with pytest.raises(UnexplainedProviderGapError, match="no prior accepted"):
        resolve_mark(
            symbol="ABC",
            current_price=12.0,
            previous_accepted_price=None,
            action_types={"trading_halt"},
            data_qualified=True,
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
            data_qualified=True,
        )

    assert resolve_mark(
        symbol="DELISTED",
        current_price=None,
        previous_accepted_price=8.0,
        action_types={"delisting"},
        terminal_value=0.0,
        data_qualified=True,
    ) == 0.0


@pytest.mark.parametrize(
    "action_type",
    ["split", "reverse_split", "dividend", "special_dividend"],
)
def test_ordinary_corporate_action_cannot_explain_a_missing_execution_bar(
    action_type: str,
) -> None:
    with pytest.raises(UnexplainedProviderGapError, match="no accepted event"):
        decide_fill(
            "buy",
            None,
            action_types={action_type},
            data_qualified=True,
        )

    available = decide_fill(
        "buy",
        10.0,
        action_types={action_type},
        data_qualified=True,
    )
    assert (available.filled, available.reason) == (True, "filled")


def test_split_and_cash_distribution_arithmetic_is_value_preserving() -> None:
    shares, average_cost = split_adjustment(10.0, 100.0, 2.0)
    assert (shares, average_cost) == (20.0, 50.0)
    assert shares * average_cost == pytest.approx(1_000.0)
    assert cash_distribution(shares, 0.25) == pytest.approx(5.0)
    with pytest.raises(ValueError, match="finite"):
        split_adjustment(1e308, 1.0, 2.0)
    with pytest.raises(ValueError, match="finite"):
        cash_distribution(1e308, 2.0)


@pytest.mark.parametrize(
    "side, price",
    [("buy", 1e308), ("sell", 5e-324)],
)
def test_us_slippage_nonfinite_or_nonpositive_result_fails_closed(
    side: str,
    price: float,
) -> None:
    with pytest.raises(MarketDataError, match="slippage-adjusted price"):
        decide_fill(
            side,
            price,
            data_qualified=True,
            slippage_bps=9999.0,
        )


def test_us_sale_proceeds_are_pending_until_explicit_next_session() -> None:
    day_one = date(2026, 7, 13)
    day_two = date(2026, 7, 14)
    portfolio = Portfolio.us(1_000.0, costs=TransactionCostModel())
    portfolio.start_session(day_one)
    portfolio.buy("ABC", 10, 10.0, day_one)
    portfolio.sell(
        "ABC",
        10,
        10.0,
        day_one,
        settlement_date=day_two,
        accepted_settlement_sessions=(day_two,),
    )

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
    with pytest.raises(ValueError, match="accepted_settlement_sessions"):
        portfolio.sell(
            "ABC",
            10,
            10.0,
            trade_date,
            settlement_date=date(2026, 7, 14),
        )

    assert portfolio.positions["ABC"].shares == 10
    assert portfolio.pending_cash_total == 0.0


def test_us_settlement_lag_historical_transitions_are_explicit() -> None:
    t_plus_three = date(2017, 9, 4)
    t_plus_two = date(2017, 9, 5)
    old_date = date(2024, 5, 27)
    new_date = date(2024, 5, 28)
    assert cash_settlement_lag_sessions(t_plus_three) == 3
    assert cash_settlement_lag_sessions(t_plus_two) == 2
    assert cash_settlement_lag_sessions(old_date) == 2
    assert cash_settlement_lag_sessions(new_date) == 1

    with pytest.raises(ValueError, match="exactly 3 session"):
        require_accepted_settlement_sessions(
            t_plus_three,
            date(2017, 9, 7),
            (date(2017, 9, 5), date(2017, 9, 6)),
        )
    assert require_accepted_settlement_sessions(
        t_plus_three,
        date(2017, 9, 7),
        (date(2017, 9, 5), date(2017, 9, 6), date(2017, 9, 7)),
    ) == (date(2017, 9, 5), date(2017, 9, 6), date(2017, 9, 7))

    portfolio = Portfolio.us(1_000.0, costs=TransactionCostModel())
    portfolio.start_session(old_date)
    portfolio.buy("ABC", 10, 10.0, old_date)
    with pytest.raises(ValueError, match="exactly 2 session"):
        portfolio.sell(
            "ABC",
            10,
            10.0,
            old_date,
            settlement_date=date(2024, 5, 29),
            accepted_settlement_sessions=(date(2024, 5, 29),),
        )
    assert portfolio.positions["ABC"].shares == 10

    with pytest.raises(ValueError, match="strictly increasing"):
        require_accepted_settlement_sessions(
            old_date,
            date(2024, 5, 28),
            (date(2024, 5, 29), date(2024, 5, 28)),
        )
    with pytest.raises(ValueError, match="final accepted"):
        require_accepted_settlement_sessions(
            old_date,
            date(2024, 5, 30),
            (date(2024, 5, 28), date(2024, 5, 29)),
        )

    portfolio.sell(
        "ABC",
        10,
        10.0,
        old_date,
        settlement_date=date(2024, 5, 29),
        accepted_settlement_sessions=(date(2024, 5, 28), date(2024, 5, 29)),
    )
