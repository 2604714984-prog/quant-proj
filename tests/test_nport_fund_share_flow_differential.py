from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib

import pytest

from research.adapters import nport_fund_share_flow_differential as adapter
from research.adapters.nport_fund_share_flow_differential import (
    Distribution,
    FlowPair,
    InputContractError,
    MarketSession,
    SegmentDecision,
    Split,
    decision_session,
    require_secondary_unsealed,
    run_validation,
    select_symbol,
    settlement_sessions,
)
from quant_system.backtest import Portfolio, TransactionCostModel


UTC = timezone.utc
REPORT_DATES = (
    date(2020, 3, 31),
    date(2020, 6, 30),
    date(2020, 9, 30),
    date(2020, 12, 31),
    date(2021, 3, 31),
    date(2021, 6, 30),
    date(2021, 9, 30),
    date(2021, 12, 31),
    date(2022, 3, 31),
    date(2022, 6, 30),
    date(2022, 9, 30),
    date(2022, 12, 31),
    date(2023, 3, 31),
)
DEFAULT_STATES = ("SPY", "SPY", "SPY") + ("QQQ",) * 9 + ("SPY",)


def _hash(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def _pair(
    report_date: date,
    state: str,
    index: int,
    *,
    accepted_at: datetime | None = None,
) -> FlowPair:
    if state == "QQQ":
        spy_net, qqq_net = Decimal("0"), Decimal("0.5")
    else:
        spy_net, qqq_net = Decimal("0.5"), Decimal("0")
    return FlowPair(
        report_date,
        accepted_at
        or datetime.combine(report_date + timedelta(days=31), datetime.min.time(), UTC)
        + timedelta(hours=12),
        spy_net,
        Decimal("1"),
        qqq_net,
        Decimal("1"),
        _hash(f"pair-{index}"),
    )


def _pairs(states: tuple[str, ...] = DEFAULT_STATES) -> tuple[FlowPair, ...]:
    assert len(states) == len(REPORT_DATES)
    return tuple(
        _pair(report_date, state, index)
        for index, (report_date, state) in enumerate(zip(REPORT_DATES, states))
    )


def _sessions(
    *,
    start: date = date(2020, 4, 29),
    end: date = date(2023, 5, 31),
    price: float = 100.0,
) -> tuple[MarketSession, ...]:
    rows = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            rows.append(MarketSession(current, price, price, price, price))
        current += timedelta(days=1)
    return tuple(rows)


def _decision_dates(
    pairs: tuple[FlowPair, ...],
    sessions: tuple[MarketSession, ...],
) -> tuple[date, ...]:
    return tuple(decision_session(pair, sessions) for pair in pairs)


def test_decision_cutoff_is_strict_and_0850_moves_to_next_session() -> None:
    sessions = (
        MarketSession(date(2020, 11, 30), 100, 100, 100, 100),
        MarketSession(date(2020, 12, 1), 100, 100, 100, 100),
    )
    before = _pair(
        date(2020, 9, 30),
        "QQQ",
        1,
        accepted_at=datetime(2020, 11, 30, 8, 29, tzinfo=adapter.NY),
    )
    equal = replace(
        before,
        pair_initial_available_at=datetime(
            2020,
            11,
            30,
            8,
            30,
            tzinfo=adapter.NY,
        ),
        pair_sha256=_hash("equal"),
    )
    late = replace(
        before,
        pair_initial_available_at=datetime(
            2020,
            11,
            30,
            8,
            50,
            tzinfo=adapter.NY,
        ),
        pair_sha256=_hash("late"),
    )
    assert decision_session(before, sessions) == date(2020, 11, 30)
    assert decision_session(equal, sessions) == date(2020, 12, 1)
    assert decision_session(late, sessions) == date(2020, 12, 1)


def test_zero_external_gross_uses_exact_spy_fallback() -> None:
    pair = FlowPair(
        date(2020, 3, 31),
        datetime(2020, 5, 1, 12, tzinfo=UTC),
        Decimal("0"),
        Decimal("0"),
        Decimal("0.5"),
        Decimal("1"),
        _hash("zero-gross"),
    )
    assert pair.spy_imbalance is None
    assert select_symbol(pair) == "SPY"
    with pytest.raises(InputContractError, match="must be zero"):
        replace(
            pair,
            spy_external_net=Decimal("0.1"),
            pair_sha256=_hash("invalid-zero-gross"),
        )


def test_first_trade_uses_previous_raw_close_target_and_execution_raw_open() -> None:
    pairs = _pairs(("QQQ", "SPY", "SPY") + ("QQQ",) * 9 + ("SPY",))
    sessions = list(_sessions())
    first_decision = decision_session(pairs[0], tuple(sessions))
    first_index = next(
        index
        for index, session in enumerate(sessions)
        if session.session_date == first_decision
    )
    sessions[first_index - 1] = replace(sessions[first_index - 1], qqq_close=200.0)
    sessions[first_index] = replace(sessions[first_index], qqq_open=100.0)
    result = run_validation(pairs, tuple(sessions))
    first_trade = result.strategy.trades[0]
    assert (first_trade.symbol, first_trade.side, first_trade.phase) == (
        "QQQ",
        "buy",
        "A",
    )
    assert first_trade.shares == 200
    assert first_trade.price == 100.0
    assert first_trade.commission == pytest.approx(20.0)


def test_cash_settlement_switches_from_t_plus_two_to_t_plus_one() -> None:
    old_sessions = (
        date(2024, 5, 24),
        date(2024, 5, 28),
        date(2024, 5, 29),
        date(2024, 5, 30),
    )
    new_sessions = (
        date(2024, 5, 28),
        date(2024, 5, 29),
        date(2024, 5, 30),
    )
    assert settlement_sessions(date(2024, 5, 24), old_sessions) == (
        date(2024, 5, 28),
        date(2024, 5, 29),
    )
    assert settlement_sessions(date(2024, 5, 28), new_sessions) == (
        date(2024, 5, 29),
    )


def test_switch_sells_in_phase_a_and_buys_only_at_settlement() -> None:
    pairs = _pairs(("QQQ", "SPY", "SPY") + ("QQQ",) * 9 + ("SPY",))
    sessions = _sessions()
    result = run_validation(pairs, sessions)
    switch_date = _decision_dates(pairs, sessions)[1]
    switch_trades = tuple(
        trade for trade in result.strategy.trades if trade.trade_date >= switch_date
    )
    sale = next(
        trade
        for trade in switch_trades
        if trade.trade_date == switch_date and trade.side == "sell"
    )
    purchase = next(
        trade for trade in switch_trades if trade.side == "buy" and trade.symbol == "SPY"
    )
    expected_path = settlement_sessions(
        switch_date,
        tuple(session.session_date for session in sessions),
    )
    assert (sale.phase, sale.symbol) == ("A", "QQQ")
    assert (purchase.phase, purchase.trade_date) == ("B", expected_path[-1])
    assert not any(
        trade.side == "buy" and trade.trade_date == switch_date
        for trade in switch_trades
    )


def test_phase_b_buys_in_fixed_qqq_then_spy_order_without_selling() -> None:
    account = adapter._new_account("test")
    day = date(2024, 6, 3)
    account.portfolio.start_session(day)
    account.pending = adapter._PendingPhaseB(
        date(2024, 5, 31),
        day,
        (("SPY", 100), ("QQQ", 100)),
    )
    adapter._phase_b(account, MarketSession(day, 100, 100, 100, 100))
    assert tuple((trade.symbol, trade.side, trade.phase) for trade in account.trades) == (
        ("QQQ", "buy", "B"),
        ("SPY", "buy", "B"),
    )


def test_phase_b_rising_price_caps_affordable_shares_without_recomputing_targets() -> None:
    portfolio = Portfolio.us(
        1_000,
        costs=TransactionCostModel(commission_rate=adapter.COMMISSION_RATE),
    )
    account = adapter._Account("test", portfolio)
    day = date(2024, 6, 3)
    account.portfolio.start_session(day)
    account.pending = adapter._PendingPhaseB(
        date(2024, 5, 31),
        day,
        (("SPY", 10), ("QQQ", 10)),
    )
    adapter._phase_b(account, MarketSession(day, 90, 90, 90, 90))
    assert account.portfolio.positions["QQQ"].shares == 10
    assert account.portfolio.positions["SPY"].shares == 1
    assert tuple((trade.symbol, trade.side) for trade in account.trades) == (
        ("QQQ", "buy"),
        ("SPY", "buy"),
    )
    assert account.pending is None


def test_fifty_fifty_sells_at_decision_then_buys_at_settlement() -> None:
    pairs = _pairs()
    sessions = list(_sessions())
    second_decision = _decision_dates(pairs, tuple(sessions))[1]
    second_index = next(
        index
        for index, session in enumerate(sessions)
        if session.session_date == second_decision
    )
    sessions[second_index - 1] = replace(
        sessions[second_index - 1],
        spy_close=200.0,
        qqq_close=50.0,
    )
    result = run_validation(pairs, tuple(sessions))
    sales = tuple(
        trade
        for trade in result.fifty_fifty.trades
        if trade.trade_date == second_decision and trade.side == "sell"
    )
    buys = tuple(
        trade
        for trade in result.fifty_fifty.trades
        if trade.trade_date > second_decision and trade.phase == "B"
    )
    expected_settlement = settlement_sessions(
        second_decision,
        tuple(session.session_date for session in sessions),
    )[-1]
    assert tuple((trade.symbol, trade.phase) for trade in sales) == (("SPY", "A"),)
    assert tuple((trade.symbol, trade.side) for trade in buys[:1]) == (
        ("QQQ", "buy"),
    )
    assert buys[0].trade_date == expected_settlement


def test_distribution_freezes_ex_date_entitlement_and_settles_on_pay_date() -> None:
    account = adapter._new_account("test")
    purchase_date = date(2021, 1, 4)
    ex_date = date(2021, 1, 5)
    pay_date = date(2021, 1, 7)
    account.portfolio.start_session(purchase_date)
    account.portfolio.buy("SPY", 100, 100, purchase_date)
    account.portfolio.start_session(ex_date)
    event = Distribution("SPY", "spy-div-1", ex_date, pay_date, 1.25)
    adapter._apply_actions(account.portfolio, (event,), ())
    assert account.portfolio.pending_cash_total == pytest.approx(125.0)
    cash_before_pay = account.portfolio.available_cash
    account.portfolio.start_session(date(2021, 1, 6))
    assert account.portfolio.available_cash == cash_before_pay
    account.portfolio.start_session(pay_date)
    assert account.portfolio.pending_cash_total == 0.0
    assert account.portfolio.available_cash == pytest.approx(cash_before_pay + 125.0)


def test_split_between_phase_a_and_phase_b_fails_closed() -> None:
    pairs = _pairs(("QQQ", "SPY", "SPY") + ("QQQ",) * 9 + ("SPY",))
    sessions = _sessions()
    switch_date = _decision_dates(pairs, sessions)[1]
    session_dates = tuple(session.session_date for session in sessions)
    split_date = next(item for item in session_dates if item > switch_date)
    split = Split("QQQ", "qqq-split-gap", split_date, 2.0)
    with pytest.raises(InputContractError, match="Phase A and Phase B"):
        run_validation(pairs, sessions, splits=(split,))


def test_interval_boundaries_are_pretrade_and_include_prior_rebalance_cost() -> None:
    sessions = _sessions()
    result = run_validation(_pairs(), sessions)
    assert len(result.strategy.pretrade_boundaries) == 13
    assert len(result.strategy.interval_returns) == 12
    assert result.strategy.pretrade_boundaries[0] == 40_000.0
    assert result.strategy.pretrade_boundaries[1] < 40_000.0
    assert result.strategy.interval_returns[0] == pytest.approx(
        result.strategy.pretrade_boundaries[1] / 40_000.0 - 1.0
    )


def test_daily_open_drawdown_uses_intrainterval_open_path() -> None:
    pairs = _pairs()
    sessions = list(_sessions())
    decisions = _decision_dates(pairs, tuple(sessions))
    first_qqq_decision = decisions[3]
    session_dates = tuple(session.session_date for session in sessions)
    settlement_date = settlement_sessions(
        first_qqq_decision,
        session_dates,
    )[-1]
    shock_index = next(
        index
        for index, session in enumerate(sessions)
        if session.session_date > settlement_date
    )
    sessions[shock_index] = replace(sessions[shock_index], qqq_open=50.0)
    result = run_validation(pairs, tuple(sessions))
    assert result.strategy.maximum_drawdown < -0.45
    assert result.strategy.daily_open_nav[0][0] == decisions[0]


def test_validation_requires_exactly_twelve_intervals_and_terminal_is_mark_only() -> None:
    pairs = _pairs()
    sessions = _sessions()
    with pytest.raises(InputContractError, match="exactly 13"):
        run_validation(pairs[:-1], sessions)
    result = run_validation(pairs, sessions)
    terminal_date = _decision_dates(pairs, sessions)[-1]
    assert result.observed_intervals == 12
    assert len(result.strategy.pretrade_boundaries) == 13
    assert terminal_date not in {
        trade.trade_date for trade in result.strategy.trades
    }
    assert result.strategy.daily_open_nav[-1][0] < terminal_date


def test_secondary_remains_sealed_without_exact_passing_validation() -> None:
    pairs = _pairs()
    sessions = _sessions()
    failed = run_validation(pairs, sessions)
    assert not failed.all_gates_pass
    with pytest.raises(InputContractError, match="sealed"):
        require_secondary_unsealed(failed)
    with pytest.raises(InputContractError, match="summary is inconsistent"):
        require_secondary_unsealed(replace(failed, all_gates_pass=True))
    forged_all_true = replace(
        failed,
        gates=tuple((name, True) for name, _ in failed.gates),
        all_gates_pass=True,
    )
    with pytest.raises(InputContractError, match="exact validation gates"):
        require_secondary_unsealed(forged_all_true)
    forged = SegmentDecision(
        "validation",
        13,
        3,
        9,
        failed.strategy,
        failed.fifty_fifty,
        failed.spy_buyhold,
        tuple((name, True) for name, _ in failed.gates),
        True,
    )
    with pytest.raises(InputContractError, match="frozen validation"):
        require_secondary_unsealed(forged)
    self_unseal = replace(
        forged,
        segment="secondary",
        observed_intervals=12,
    )
    with pytest.raises(InputContractError, match="validation-segment"):
        require_secondary_unsealed(self_unseal)
    truthy_non_bools = replace(
        forged,
        observed_intervals=12,
        spy_intervals=3,
        qqq_intervals=9,
        gates=tuple((name, 1) for name, _ in forged.gates),
    )
    with pytest.raises(InputContractError, match="exact validation gates"):
        require_secondary_unsealed(truthy_non_bools)
