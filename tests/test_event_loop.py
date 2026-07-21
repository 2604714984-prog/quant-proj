from copy import deepcopy
from dataclasses import replace
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import hashlib
from zoneinfo import ZoneInfo

import pytest

from quant_system.backtest import (
    CapacityObservation,
    CapacityPolicy,
    ExecutionInput,
    Portfolio,
    TerminalAction,
    TransactionCostModel,
    blocked_exit_from_receipt,
    run_static_rebalance,
)
from quant_system.data import (
    AcceptedSession,
    AcceptedSessionCalendar,
    CalendarIdentity,
    CorporateActionIdentity,
    SourceIdentity,
    calendar_identity_sha256,
    session_dates_sha256,
    session_rows_sha256,
)
from quant_system.markets.common import MarketDataError
from quant_system.markets.universe import (
    StatusEvidence,
    UniverseSnapshotIdentity,
    lifecycle_coverage_sha256,
    ordered_members_sha256,
)
from quant_system.markets.us import CorporateActionValuationError

UTC = timezone.utc
DEFINITION_SHA = hashlib.sha256(b"fixture-strategy-definition-v1").hexdigest()
ADAPTER_SHA = hashlib.sha256(b"fixture-strategy-adapter-v1").hexdigest()
INCLUSION_RULE_SHA = hashlib.sha256(b"fixture-universe-inclusion-rule-v1").hexdigest()


def _source(
    label: str,
    available_at: datetime,
    *,
    content_sha256: str | None = None,
) -> SourceIdentity:
    return SourceIdentity(
        f"https://example.test/{label}",
        content_sha256 or hashlib.sha256(label.encode()).hexdigest(),
        available_at,
        available_at + timedelta(minutes=1),
        label,
    )


def _session(day: date, timezone_name: str, label: str) -> AcceptedSession:
    zone = ZoneInfo(timezone_name)
    exchange_id = "XNYS" if timezone_name == "America/New_York" else "XSHG"
    return AcceptedSession(
        day,
        datetime.combine(day, time(9, 30), zone),
        datetime.combine(day, time(16 if timezone_name == "America/New_York" else 15), zone),
        _source(f"calendar-{label}", datetime(2000, 1, 1, tzinfo=UTC)),
        timezone_name,
        exchange_id=exchange_id,
    )


def _calendar(days: tuple[date, ...], timezone_name: str) -> AcceptedSessionCalendar:
    rows = tuple(_session(day, timezone_name, str(index)) for index, day in enumerate(days))
    dates = tuple(row.session_date for row in rows)
    rows_sha = session_rows_sha256(rows)
    identity = CalendarIdentity(
        "XNYS" if timezone_name == "America/New_York" else "XSHG",
        timezone_name,
        dates[0],
        dates[-1],
        len(dates),
        session_dates_sha256(dates),
        rows_sha,
        _source("calendar-aggregate", datetime(2000, 1, 1, tzinfo=UTC)),
    )
    return AcceptedSessionCalendar(rows, identity=identity)


def _statuses(
    symbol: str,
    timezone_name: str,
    *,
    suspended: bool = False,
    delisted: bool = False,
    include_st: bool = True,
    include_suspended: bool = True,
    available_at: datetime = datetime(2000, 1, 1, tzinfo=UTC),
) -> tuple[StatusEvidence, ...]:
    values = {"listed": True, "delisted": delisted}
    if include_st:
        values["st"] = False
    if include_suspended:
        values["suspended"] = suspended
    return tuple(
        StatusEvidence(
            f"{symbol}-{kind}",
            symbol,
            kind,
            value,
            date(1990, 1, 1),
            None,
            timezone_name,
            _source(f"status-{symbol}-{kind}", available_at),
        )
        for kind, value in values.items()
    )


def _input(
    symbol: str,
    market: str,
    execution: AcceptedSession,
    *,
    price: float | None = 10.0,
    suspended: bool = False,
    delisted: bool = False,
    action_types: tuple[str, ...] = (),
    corporate_actions: tuple[CorporateActionIdentity, ...] = (),
    capacity: CapacityObservation | None = None,
    terminal: TerminalAction | None = None,
    source_label: str | None = None,
    decision_price: float | None = None,
    decision_price_available_at: datetime = datetime(2000, 1, 1, tzinfo=UTC),
    decision_price_basis: str | None = "raw_pre_action_per_old_share",
) -> ExecutionInput:
    timezone_name = execution.exchange_timezone
    decision_reference = (
        (10.0 if price is None else float(price))
        if decision_price is None
        else decision_price
    )
    return ExecutionInput(
        symbol,
        market,  # type: ignore[arg-type]
        price,
        "USD" if market == "us" else "CNY",
        _source(source_label or f"bar-{symbol}", execution.open_at),
        _statuses(
            symbol,
            timezone_name,
            suspended=suspended,
            delisted=delisted,
            include_st=market == "a_share",
            include_suspended=market == "a_share",
        ),
        action_types,
        corporate_actions,
        suspended,
        None,
        None,
        capacity,
        terminal,
        decision_reference,
        _source(f"decision-price-{symbol}", decision_price_available_at),
        decision_price_basis,  # type: ignore[arg-type]
    )


def _snapshot(
    calendar: AcceptedSessionCalendar,
    execution: AcceptedSession,
    decision_at: datetime,
    inputs: tuple[ExecutionInput, ...],
    members: tuple[str, ...],
    *,
    source_label: str = "universe-snapshot",
) -> UniverseSnapshotIdentity:
    cutoff = min(decision_at, execution.open_at - timedelta(microseconds=1))
    records = {
        row.symbol: row.status_records
        for row in inputs
        if row.symbol in members
    }
    member_hash = ordered_members_sha256(members)
    lifecycle_hash = lifecycle_coverage_sha256(
        members,
        execution,
        cutoff,
        records,
        market=inputs[0].market,
    )
    calendar_hash = calendar_identity_sha256(calendar.identity)
    return UniverseSnapshotIdentity(
        market=inputs[0].market,
        exchange_id=calendar.identity.exchange_id,
        effective_session=execution.session_date,
        member_count=len(members),
        ordered_members_sha256=member_hash,
        lifecycle_coverage_sha256=lifecycle_hash,
        inclusion_rule_sha256=INCLUSION_RULE_SHA,
        calendar_identity_sha256=calendar_hash,
        source_identity=_source(source_label, datetime(2000, 1, 1, tzinfo=UTC)),
    )


def _run_static_rebalance(
    portfolio: Portfolio,
    calendar: AcceptedSessionCalendar,
    **kwargs,
):
    inputs = kwargs["execution_inputs"]
    members = kwargs.setdefault(
        "universe_members",
        tuple(sorted(row.symbol for row in inputs)),
    )
    execution = calendar.next_session(
        kwargs["signal_session"],
        as_of=kwargs["decision_at"],
    )
    kwargs.setdefault(
        "universe_snapshot",
        _snapshot(calendar, execution, kwargs["decision_at"], inputs, members),
    )
    kwargs.setdefault("strategy_definition_sha256", DEFINITION_SHA)
    kwargs.setdefault("strategy_adapter_sha256", ADAPTER_SHA)
    return run_static_rebalance(portfolio, calendar, **kwargs)


def test_static_rebalance_uses_frozen_callback_and_is_deterministic() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal, execution = (
        calendar.session_on(day, as_of=datetime(2026, 7, 13, 12, tzinfo=UTC)) for day in days
    )
    portfolio = Portfolio.a_share(100_000, costs=TransactionCostModel())
    inputs = (
        _input("AAA", "a_share", execution, price=10),
        _input("BBB", "a_share", execution, price=20),
    )
    seen = []

    def strategy(context):
        seen.append(context)
        assert context.signal_session == signal
        assert context.execution_session == execution
        assert context.eligible_symbols == ("AAA", "BBB")
        assert not hasattr(context, "open_price")
        return {"AAA": 0.5, "BBB": 0.5}

    before = deepcopy(portfolio.__dict__)
    first = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=inputs,
        target_weights=strategy,
    )
    second = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=inputs,
        target_weights=lambda _: {"BBB": 0.5, "AAA": 0.5},
    )

    assert [receipt.symbol for receipt in first.receipts] == ["AAA", "BBB"]
    assert first.portfolio.positions["AAA"].shares == 5_000
    assert first.portfolio.positions["BBB"].shares == 2_500
    assert first.stage_hash == second.stage_hash
    assert first.input_identity_hash == second.input_identity_hash
    assert portfolio.__dict__ == before
    assert len(seen) == 1


def test_timing_pit_and_target_weight_boundaries_fail_closed() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(10_000, costs=TransactionCostModel())
    input_row = _input("AAA", "a_share", execution)

    with pytest.raises(MarketDataError, match="between signal close"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at - timedelta(microseconds=1),
            execution_inputs=(input_row,),
            target_weights=lambda _: {},
        )
    accepted_at_close = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(input_row,),
        target_weights=lambda _: {},
    )
    assert accepted_at_close.context.decision_at == signal.close_at
    accepted = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=execution.open_at - timedelta(microseconds=1),
        execution_inputs=(input_row,),
        target_weights=lambda _: {},
    )
    assert accepted.context.decision_at == execution.open_at - timedelta(microseconds=1)

    for decision_at in (
        execution.open_at,
        execution.open_at + timedelta(microseconds=1),
    ):
        with pytest.raises(MarketDataError, match="strictly before next-session open"):
            _run_static_rebalance(
                portfolio,
                calendar,
                signal_session=days[0],
                decision_at=decision_at,
                execution_inputs=(input_row,),
                target_weights=lambda _: {},
            )
    late = ExecutionInput(
        **{**input_row.__dict__, "source": _source("late", execution.open_at + timedelta(seconds=1))}
    )
    with pytest.raises(MarketDataError, match="unavailable at open"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(late,),
            target_weights=lambda _: {},
        )
    with pytest.raises(ValueError, match=r"in \[0, 1\]"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(input_row,),
            target_weights=lambda _: {"AAA": 1.1},
        )


def test_us_sells_before_buys_without_spending_unsettled_t_plus_three_cash() -> None:
    days = tuple(date(2016, 8, day) for day in range(1, 6))
    calendar = _calendar(days, "America/New_York")
    signal = calendar.session_on(days[0], as_of=datetime(2016, 8, 1, 22, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.us(100, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("OLD", 10, 10, days[0])

    result = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(
            _input("OLD", "us", execution),
            _input("NEW", "us", execution),
        ),
        target_weights=lambda _: {"NEW": 1.0},
    )

    assert [(item.side, item.symbol, item.reason) for item in result.receipts] == [
        ("sell", "OLD", "filled"),
        ("buy", "NEW", "insufficient_cash"),
    ]
    assert result.portfolio.positions == {}
    assert result.portfolio.available_cash == 0
    assert result.portfolio.pending_cash[0].settlement_date == days[4]
    assert result.receipts[0].cash_change == 100


def test_capacity_and_suspension_leave_blocked_exit_held_and_convertible() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14), date(2026, 7, 15))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(1_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("AAA", 100, 10, days[0])
    suspended = _input("AAA", "a_share", execution, price=None, suspended=True)

    result = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(suspended,),
        target_weights=lambda _: {},
    )
    assert result.receipts[0].reason == "suspended"
    assert result.portfolio.positions["AAA"].shares == 100
    blocked = blocked_exit_from_receipt(result.receipts[0], result.context, calendar)
    assert blocked.pending and len(blocked.attempts) == 1

    observation = CapacityObservation(
        "AAA",
        signal,
        500,
        5_000,
        "CNY",
        _source("capacity-AAA", signal.close_at),
    )
    capped = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(_input("AAA", "a_share", execution, capacity=observation),),
        target_weights=lambda _: {},
        capacity_policy=CapacityPolicy(0.1, 0.1, "CNY"),
    )
    assert capped.receipts[0].reason.startswith("capacity:")
    assert capped.portfolio.positions["AAA"].shares == 100


def test_max_positions_counts_a_blocked_exit_before_replacement_buy() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(100_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("AAA", 100, 10, days[0])

    result = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(
            _input("AAA", "a_share", execution, price=None, suspended=True),
            _input("BBB", "a_share", execution),
        ),
        target_weights=lambda _: {"BBB": 0.5},
        max_positions=1,
    )

    assert [(item.side, item.symbol, item.reason) for item in result.receipts] == [
        ("sell", "AAA", "suspended"),
        ("buy", "BBB", "max_positions_after_blocked_exit"),
    ]
    assert set(result.portfolio.positions) == {"AAA"}
    assert result.receipts[1].filled_shares == 0
    assert result.receipts[1].cash_change == 0
    assert result.receipts[1].cash_after == result.receipts[0].cash_after


def test_max_positions_allows_replacement_after_successful_exit() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(100_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("AAA", 100, 10, days[0])

    result = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(
            _input("AAA", "a_share", execution),
            _input("BBB", "a_share", execution),
        ),
        target_weights=lambda _: {"BBB": 0.5},
        max_positions=1,
    )

    assert [(item.side, item.symbol, item.reason) for item in result.receipts] == [
        ("sell", "AAA", "filled"),
        ("buy", "BBB", "filled"),
    ]
    assert set(result.portfolio.positions) == {"BBB"}


def test_max_positions_allows_existing_symbol_adjustment_at_the_cap() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(100_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("AAA", 100, 10, days[0])

    result = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(
            _input("AAA", "a_share", execution),
            _input("BBB", "a_share", execution),
        ),
        target_weights=lambda _: {"AAA": 0.5, "BBB": 0.5},
        max_positions=1,
    )

    assert [(item.side, item.symbol, item.reason) for item in result.receipts] == [
        ("buy", "AAA", "filled"),
        ("buy", "BBB", "max_positions_after_blocked_exit"),
    ]
    assert result.portfolio.positions["AAA"].shares > 100
    assert "BBB" not in result.portfolio.positions


def test_max_positions_uses_sorted_new_symbol_order_deterministically() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(100_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("AAA", 100, 10, days[0])

    result = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(
            _input("CCC", "a_share", execution),
            _input("AAA", "a_share", execution, price=None, suspended=True),
            _input("BBB", "a_share", execution),
        ),
        target_weights=lambda _: {"CCC": 0.25, "BBB": 0.25},
        max_positions=2,
    )

    assert [(item.side, item.symbol, item.reason) for item in result.receipts] == [
        ("sell", "AAA", "suspended"),
        ("buy", "BBB", "filled"),
        ("buy", "CCC", "max_positions_after_blocked_exit"),
    ]
    assert set(result.portfolio.positions) == {"AAA", "BBB"}


@pytest.mark.parametrize("value", [True, 0, -1, 1.5])
def test_max_positions_validation_and_default_identity_compatibility(value) -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(100_000, costs=TransactionCostModel())
    inputs = (_input("AAA", "a_share", execution),)
    arguments = {
        "signal_session": days[0],
        "decision_at": signal.close_at,
        "execution_inputs": inputs,
        "target_weights": lambda _: {"AAA": 0.5},
    }

    default = _run_static_rebalance(portfolio, calendar, **arguments)
    explicit_none = _run_static_rebalance(portfolio, calendar, max_positions=None, **arguments)
    nonbinding_cap = _run_static_rebalance(portfolio, calendar, max_positions=10, **arguments)
    assert default.input_identity_hash == explicit_none.input_identity_hash
    assert default.stage_hash == explicit_none.stage_hash
    assert default.portfolio.__dict__ == nonbinding_cap.portfolio.__dict__
    assert default.input_identity_hash != nonbinding_cap.input_identity_hash
    with pytest.raises(ValueError, match="positive integer or None"):
        _run_static_rebalance(portfolio, calendar, max_positions=value, **arguments)


def test_distribution_identity_credits_prior_holder_and_raw_label_is_rejected() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14), date(2026, 7, 15))
    calendar = _calendar(days, "America/New_York")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 22, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.us(1_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("ABC", 10, 10, days[0])
    action = CorporateActionIdentity(
        "ABC",
        "abc-dividend-v1",
        "cash_dividend",
        execution.open_at,
        _source("abc-dividend-source", signal.close_at),
        "America/New_York",
        ex_date=days[1],
        record_date=days[1],
        pay_date=days[2],
        cash_amount=Decimal("0.5"),
        currency="USD",
        unit="per_share",
    )
    result = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(
            _input(
                "ABC",
                "us",
                execution,
                corporate_actions=(action,),
                decision_price=10,
            ),
        ),
        target_weights=lambda _: {"ABC": 0.1},
    )
    assert result.receipts[0].side == "distribution"
    assert result.portfolio.pending_cash_total == pytest.approx(5)
    assert result.receipts[0].reason == "entitlement:5"

    with pytest.raises(CorporateActionValuationError, match="rich identity"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(_input("ABC", "us", execution, action_types=("dividend",)),),
            target_weights=lambda _: {},
        )


def test_terminal_action_is_timed_ineligible_and_cannot_be_repurchased() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "America/New_York")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 22, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.us(1_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("DEAD", 10, 10, days[0])
    terminal = TerminalAction(
        "dead-delisting-v1",
        "delisting",
        execution.open_at,
        2.5,
        _source("dead-delisting-source", signal.close_at),
    )
    row = _input(
        "DEAD",
        "us",
        execution,
        price=None,
        delisted=True,
        action_types=("delisting",),
        terminal=terminal,
    )
    result = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(row,),
        target_weights=lambda _: {},
    )
    assert result.portfolio.positions == {}
    assert result.receipts[0].cash_change == pytest.approx(25)
    assert result.receipts[0].reason == "terminal_delisting"

    eligible_row = ExecutionInput(
        **{
            **row.__dict__,
            "status_records": _statuses(
                "DEAD",
                "America/New_York",
                include_st=False,
                include_suspended=False,
            ),
        }
    )
    with pytest.raises(MarketDataError, match="PIT ineligible"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(eligible_row,),
            target_weights=lambda _: {"DEAD": 1.0},
        )

    empty = _run_static_rebalance(
        Portfolio.us(1_000, costs=TransactionCostModel()),
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(row,),
        target_weights=lambda _: {},
    )
    assert empty.receipts == () and empty.portfolio.positions == {}

    mistimed = TerminalAction(
        terminal.event_id,
        terminal.action_type,
        signal.open_at,
        terminal.recovery_per_share,
        terminal.source,
    )
    with pytest.raises(MarketDataError, match="effective date"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(ExecutionInput(**{**row.__dict__, "terminal_action": mistimed}),),
            target_weights=lambda _: {},
        )

    intraday_future = TerminalAction(
        "dead-delisting-close-v1",
        terminal.action_type,
        execution.close_at,
        terminal.recovery_per_share,
        terminal.source,
    )
    before = deepcopy(portfolio.__dict__)
    with pytest.raises(MarketDataError, match="follows execution open"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(
                ExecutionInput(**{**row.__dict__, "terminal_action": intraday_future}),
            ),
            target_weights=lambda _: {},
        )
    assert portfolio.__dict__ == before


def test_missing_halt_mark_fails_and_identity_or_prior_stage_changes_hash() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "America/New_York")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 22, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.us(1_000, costs=TransactionCostModel())
    base = _input("ABC", "us", execution)
    first = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(base,),
        target_weights=lambda _: {},
    )
    changed = _input("ABC", "us", execution, source_label="different-partition")
    second = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(changed,),
        target_weights=lambda _: {},
        prior_stage_hash="1" * 64,
    )
    assert first.receipts == () and second.receipts == ()
    assert first.input_identity_hash != second.input_identity_hash
    assert first.stage_hash != second.stage_hash

    numeric_change = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(_input("ABC", "us", execution, price=11),),
        target_weights=lambda _: {},
    )
    assert numeric_change.input_identity_hash != first.input_identity_hash
    with pytest.raises(ValueError, match="slippage_bps"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(base,),
            target_weights=lambda _: {},
            slippage_bps=-1,
        )

    portfolio.start_session(days[0])
    portfolio.buy("ABC", 10, 10, days[0])
    portfolio.positions["ABC"].last_accepted_mark = None
    halted = _input(
        "ABC",
        "us",
        execution,
        price=None,
        action_types=("trading_halt",),
        decision_price=10,
    )
    halted_result = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(halted,),
        target_weights=lambda _: {},
    )
    assert halted_result.final_nav == pytest.approx(1_000)
    assert halted_result.receipts[0].reason == "confirmed_halt"


def test_same_day_distribution_receipt_reconciles_immediate_cash() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "America/New_York")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 22, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.us(1_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("ABC", 10, 10, days[0])
    action = CorporateActionIdentity(
        "ABC", "same-day-dividend", "cash_dividend", execution.open_at,
        _source("same-day-source", signal.close_at), "America/New_York",
        ex_date=days[1], record_date=days[1], pay_date=days[1],
        cash_amount=Decimal("0.5"), currency="USD", unit="per_share",
    )
    result = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(
            _input(
                "ABC",
                "us",
                execution,
                corporate_actions=(action,),
                decision_price=10,
            ),
        ),
        target_weights=lambda _: {"ABC": 0.1},
    )
    assert result.receipts[0].cash_change == pytest.approx(5)
    assert result.receipts[0].cash_after == pytest.approx(905)


def test_engine_adjusts_pre_action_decision_price_for_split_and_distribution() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14), date(2026, 7, 15))
    calendar = _calendar(days, "America/New_York")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 22, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)

    split_portfolio = Portfolio.us(10_000, costs=TransactionCostModel())
    split_portfolio.start_session(days[0])
    split_portfolio.buy("ABC", 10, 100, days[0])
    split = CorporateActionIdentity(
        "ABC",
        "abc-split-2-for-1",
        "split",
        execution.open_at,
        _source("abc-split-source", signal.close_at),
        "America/New_York",
        ex_date=days[1],
        split_ratio=Decimal("2"),
    )
    split_result = _run_static_rebalance(
        split_portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(
            _input(
                "ABC",
                "us",
                execution,
                price=50,
                corporate_actions=(split,),
                decision_price=100,
                decision_price_basis="raw_pre_action_per_old_share",
            ),
        ),
        target_weights=lambda _: {"ABC": 1.0},
    )
    split_buy = next(item for item in split_result.receipts if item.side == "buy")
    assert split_buy.requested_shares == 180
    assert split_result.portfolio.positions["ABC"].shares == 200

    distribution_portfolio = Portfolio.us(10_000, costs=TransactionCostModel())
    distribution_portfolio.start_session(days[0])
    distribution_portfolio.buy("ABC", 10, 100, days[0])
    distribution = CorporateActionIdentity(
        "ABC",
        "abc-cash-10",
        "cash_dividend",
        execution.open_at,
        _source("abc-cash-source", signal.close_at),
        "America/New_York",
        ex_date=days[1],
        record_date=days[1],
        pay_date=days[2],
        cash_amount=Decimal("10"),
        currency="USD",
        unit="per_share",
    )
    distribution_input = _input(
        "ABC",
        "us",
        execution,
        price=90,
        corporate_actions=(distribution,),
        decision_price=100,
        decision_price_basis="raw_pre_action_per_old_share",
    )
    distribution_result = _run_static_rebalance(
        distribution_portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(distribution_input,),
        target_weights=lambda _: {"ABC": 1.0},
    )
    distribution_buy = next(
        item for item in distribution_result.receipts if item.side == "buy"
    )
    assert distribution_buy.requested_shares == 101
    assert distribution_result.portfolio.positions["ABC"].shares == 110
    assert distribution_result.portfolio.pending_cash_total == pytest.approx(100)

    for action, execution_price in ((split, 50), (distribution, 90)):
        caller = Portfolio.us(10_000, costs=TransactionCostModel())
        before = deepcopy(caller.__dict__)
        callback_calls = []
        with pytest.raises(
            CorporateActionValuationError,
            match="raw_pre_action_per_old_share",
        ):
            _run_static_rebalance(
                caller,
                calendar,
                signal_session=days[0],
                decision_at=signal.close_at,
                execution_inputs=(
                    _input(
                        "ABC",
                        "us",
                        execution,
                        price=execution_price,
                        corporate_actions=(action,),
                        decision_price=execution_price,
                        decision_price_basis="raw_execution_units",
                    ),
                ),
                target_weights=lambda context: callback_calls.append(context)
                or {"ABC": 1.0},
            )
        assert callback_calls == []
    assert caller.__dict__ == before

    with pytest.raises(CorporateActionValuationError, match="explicit order and unit basis"):
        _run_static_rebalance(
            Portfolio.us(10_000, costs=TransactionCostModel()),
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(
                _input(
                    "ABC",
                    "us",
                    execution,
                    corporate_actions=(split, distribution),
                    decision_price=100,
                ),
            ),
            target_weights=lambda _: {"ABC": 1.0},
        )


def test_invalid_weights_and_late_or_duplicate_actions_leave_caller_unchanged() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14), date(2026, 7, 15))
    calendar = _calendar(days, "America/New_York")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 22, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.us(1_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("ABC", 10, 10, days[0])
    before = deepcopy(portfolio.__dict__)
    late = CorporateActionIdentity(
        "ABC", "late-dividend", "cash_dividend", execution.open_at,
        _source("late-action-source", execution.open_at), "America/New_York",
        ex_date=days[1], record_date=days[1], pay_date=days[2],
        cash_amount=Decimal("0.5"), currency="USD", unit="per_share",
    )
    late_row = _input("ABC", "us", execution, corporate_actions=(late,))

    with pytest.raises(MarketDataError, match="late"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(late_row,),
            target_weights=lambda _: {},
        )
    with pytest.raises(MarketDataError, match="globally unique"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(
                ExecutionInput(**{**late_row.__dict__, "corporate_actions": (late, late)}),
            ),
            target_weights=lambda _: {},
        )
    with pytest.raises(ValueError, match="numeric"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(_input("ABC", "us", execution),),
            target_weights=lambda _: {"ABC": True},
        )
    future_action = CorporateActionIdentity(
        "ABC", "future-intraday-dividend", "cash_dividend", execution.close_at,
        _source("future-intraday-source", signal.close_at), "America/New_York",
        ex_date=days[1], record_date=days[1], pay_date=days[2],
        cash_amount=Decimal("0.5"), currency="USD", unit="per_share",
    )
    with pytest.raises(MarketDataError, match="after execution open"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(
                _input("ABC", "us", execution, corporate_actions=(future_action,)),
            ),
            target_weights=lambda _: {},
        )
    with pytest.raises(MarketDataError, match="unknown US action"):
        _run_static_rebalance(
            Portfolio.us(1_000, costs=TransactionCostModel()),
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(_input("ABC", "us", execution, action_types=("mystery",)),),
            target_weights=lambda _: {},
        )
    assert portfolio.__dict__ == before


def test_requested_shares_use_decision_prices_not_next_open_prices() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(100_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("HOLD", 100, 10, days[0])

    low_open = (
        _input("HOLD", "a_share", execution, price=10, decision_price=10),
        _input("NEW", "a_share", execution, price=10, decision_price=10),
    )
    high_open = (
        _input("HOLD", "a_share", execution, price=25, decision_price=10),
        _input("NEW", "a_share", execution, price=25, decision_price=10),
    )
    arguments = {
        "signal_session": days[0],
        "decision_at": signal.close_at,
        "target_weights": lambda _: {"HOLD": 0.5, "NEW": 0.5},
    }
    low = _run_static_rebalance(
        portfolio,
        calendar,
        execution_inputs=low_open,
        **arguments,
    )
    high = _run_static_rebalance(
        portfolio,
        calendar,
        execution_inputs=high_open,
        **arguments,
    )

    def requested(result):
        return tuple(
            (item.symbol, item.side, item.requested_shares) for item in result.receipts
        )

    assert requested(low) == requested(high)
    assert {item.price for item in low.receipts if item.filled_shares} == {10.0}
    assert {item.price for item in high.receipts if item.filled_shares} == {25.0}
    assert low.portfolio.__dict__ != high.portfolio.__dict__


@pytest.mark.parametrize("bad_price", [0.0, -1.0, float("nan"), float("inf")])
def test_decision_price_must_be_present_finite_positive_and_timely(bad_price) -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(10_000, costs=TransactionCostModel())
    before = deepcopy(portfolio.__dict__)
    base = _input("AAA", "a_share", execution)
    bad = ExecutionInput(**{**base.__dict__, "decision_price": bad_price})

    with pytest.raises(MarketDataError, match="decision price must be finite and positive"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(bad,),
            target_weights=lambda _: {"AAA": 1.0},
        )
    missing = ExecutionInput(
        **{
            **base.__dict__,
            "decision_price": None,
            "decision_price_source": None,
            "decision_price_basis": None,
        }
    )
    callback_calls = []
    with pytest.raises(MarketDataError, match="lacks a qualified decision-time sizing price"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(missing,),
            target_weights=lambda context: callback_calls.append(context) or {"AAA": 1.0},
        )
    assert callback_calls == []
    missing_basis = replace(base, decision_price_basis=None)
    with pytest.raises(MarketDataError, match="price, source, and basis"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(missing_basis,),
            target_weights=lambda context: callback_calls.append(context) or {"AAA": 1.0},
        )
    unknown_basis = replace(base, decision_price_basis="qfq")
    with pytest.raises(MarketDataError, match="basis is unsupported"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(unknown_basis,),
            target_weights=lambda context: callback_calls.append(context) or {"AAA": 1.0},
        )
    assert callback_calls == []
    late = _input(
        "AAA",
        "a_share",
        execution,
        decision_price_available_at=execution.open_at,
    )
    with pytest.raises(MarketDataError, match="unavailable at decision_at"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(late,),
            target_weights=lambda _: {"AAA": 1.0},
        )
    assert portfolio.__dict__ == before


def test_strategy_hashes_are_required_and_bound_to_stage_identity() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(10_000, costs=TransactionCostModel())
    inputs = (_input("AAA", "a_share", execution),)
    arguments = {
        "signal_session": days[0],
        "decision_at": signal.close_at,
        "execution_inputs": inputs,
        "target_weights": lambda _: {"AAA": 0.5},
    }
    baseline = _run_static_rebalance(portfolio, calendar, **arguments)
    definition_changed = _run_static_rebalance(
        portfolio,
        calendar,
        strategy_definition_sha256="1" * 64,
        **arguments,
    )
    adapter_changed = _run_static_rebalance(
        portfolio,
        calendar,
        strategy_adapter_sha256="2" * 64,
        **arguments,
    )

    assert baseline.receipts == definition_changed.receipts == adapter_changed.receipts
    assert len(
        {
            baseline.input_identity_hash,
            definition_changed.input_identity_hash,
            adapter_changed.input_identity_hash,
        }
    ) == 3
    assert len({baseline.stage_hash, definition_changed.stage_hash, adapter_changed.stage_hash}) == 3
    assert baseline.strategy_definition_sha256 == DEFINITION_SHA
    assert baseline.strategy_adapter_sha256 == ADAPTER_SHA

    execution_basis = _run_static_rebalance(
        portfolio,
        calendar,
        **{
            **arguments,
            "execution_inputs": (
                replace(inputs[0], decision_price_basis="raw_execution_units"),
            ),
        },
    )
    assert execution_basis.receipts == baseline.receipts
    assert execution_basis.input_identity_hash != baseline.input_identity_hash
    assert execution_basis.stage_hash != baseline.stage_hash

    called = False

    def callback(_):
        nonlocal called
        called = True
        return {}

    with pytest.raises(ValueError, match="strategy_definition_sha256"):
        _run_static_rebalance(
            portfolio,
            calendar,
            **{**arguments, "target_weights": callback},
            strategy_definition_sha256="A" * 64,
        )
    assert called is False


def test_universe_snapshot_rejects_missing_member_and_lifecycle_drift() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(10_000, costs=TransactionCostModel())
    alive = _input("ALIVE", "a_share", execution)
    delisted = _input("DEAD", "a_share", execution, delisted=True)
    full_inputs = (alive, delisted)
    full_members = ("ALIVE", "DEAD")
    frozen = _snapshot(calendar, execution, signal.close_at, full_inputs, full_members)

    with pytest.raises(MarketDataError, match="member_count mismatch"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(alive,),
            universe_members=("ALIVE",),
            universe_snapshot=frozen,
            target_weights=lambda _: {},
        )

    listed = alive.status_records[0]
    drifted_statuses = (
        replace(listed, value=False),
        *alive.status_records[1:],
    )
    drifted = ExecutionInput(**{**alive.__dict__, "status_records": drifted_statuses})
    alive_snapshot = _snapshot(
        calendar,
        execution,
        signal.close_at,
        (alive,),
        ("ALIVE",),
    )
    with pytest.raises(MarketDataError, match="lifecycle_coverage_sha256 mismatch"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(drifted,),
            universe_members=("ALIVE",),
            universe_snapshot=alive_snapshot,
            target_weights=lambda _: {},
        )
    future_statuses = (
        replace(
            alive.status_records[0],
            source=_source("future-listing-revision", execution.open_at),
        ),
        *alive.status_records[1:],
    )
    future = replace(alive, status_records=future_statuses)
    with pytest.raises(MarketDataError, match="future evidence"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(future,),
            universe_members=("ALIVE",),
            universe_snapshot=alive_snapshot,
            target_weights=lambda _: {},
        )


@pytest.mark.parametrize("members", [("A", "B\nC"), ("A\nB", "C"), ("A\tB",)])
def test_universe_member_identifiers_reject_c0_control_characters(members) -> None:
    with pytest.raises(MarketDataError, match="C0 control characters"):
        ordered_members_sha256(members)


def test_control_character_universe_fails_before_lifecycle_or_callback() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(10_000, costs=TransactionCostModel())
    before = deepcopy(portfolio.__dict__)
    inputs = (
        _input("A\nB", "a_share", execution),
        _input("C", "a_share", execution),
    )
    snapshot = UniverseSnapshotIdentity(
        market="a_share",
        exchange_id=calendar.identity.exchange_id,
        effective_session=execution.session_date,
        member_count=2,
        ordered_members_sha256="0" * 64,
        lifecycle_coverage_sha256="0" * 64,
        inclusion_rule_sha256=INCLUSION_RULE_SHA,
        calendar_identity_sha256=calendar_identity_sha256(calendar.identity),
        source_identity=_source("invalid-universe", signal.close_at),
    )
    callback_calls = []

    with pytest.raises(MarketDataError, match="C0 control characters"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=inputs,
            universe_members=("A\nB", "C"),
            universe_snapshot=snapshot,
            target_weights=lambda context: callback_calls.append(context) or {},
        )
    assert callback_calls == []
    assert portfolio.__dict__ == before


def test_universe_candidates_are_separate_from_held_maintenance_rows() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(10_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("OLD", 100, 10, days[0])
    old = _input("OLD", "a_share", execution)
    new = _input("NEW", "a_share", execution)
    snapshot = _snapshot(
        calendar,
        execution,
        signal.close_at,
        (old, new),
        ("NEW",),
    )
    seen = []

    result = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(old, new),
        universe_members=("NEW",),
        universe_snapshot=snapshot,
        target_weights=lambda context: seen.append(context.eligible_symbols) or {"NEW": 0.5},
    )

    assert seen == [("NEW",)]
    assert result.receipts[0].symbol == "OLD" and result.receipts[0].side == "sell"
    with pytest.raises(MarketDataError, match="not PIT eligible"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(old, new),
            universe_members=("NEW",),
            universe_snapshot=snapshot,
            target_weights=lambda _: {"OLD": 0.5},
        )
    changed_old = replace(
        old,
        status_records=(replace(old.status_records[0], value=False), *old.status_records[1:]),
    )
    changed_result = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(changed_old, new),
        universe_members=("NEW",),
        universe_snapshot=snapshot,
        target_weights=lambda _: {"NEW": 0.5},
    )
    assert changed_result.input_identity_hash != result.input_identity_hash


def test_universe_snapshot_source_is_causal_and_changes_input_identity() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(10_000, costs=TransactionCostModel())
    inputs = (_input("AAA", "a_share", execution),)
    first_snapshot = _snapshot(
        calendar,
        execution,
        signal.close_at,
        inputs,
        ("AAA",),
        source_label="universe-v1",
    )
    second_snapshot = _snapshot(
        calendar,
        execution,
        signal.close_at,
        inputs,
        ("AAA",),
        source_label="universe-v2",
    )
    arguments = {
        "signal_session": days[0],
        "decision_at": signal.close_at,
        "execution_inputs": inputs,
        "universe_members": ("AAA",),
        "target_weights": lambda _: {},
    }
    first = _run_static_rebalance(
        portfolio,
        calendar,
        universe_snapshot=first_snapshot,
        **arguments,
    )
    second = _run_static_rebalance(
        portfolio,
        calendar,
        universe_snapshot=second_snapshot,
        **arguments,
    )
    assert first.receipts == second.receipts == ()
    assert first.input_identity_hash != second.input_identity_hash
    late_snapshot = replace(
        first_snapshot,
        source_identity=_source(
            "universe-late",
            execution.open_at,
            content_sha256=first_snapshot.source_identity.content_sha256,
        ),
    )
    with pytest.raises(MarketDataError, match="unavailable at decision_at"):
        _run_static_rebalance(
            portfolio,
            calendar,
            universe_snapshot=late_snapshot,
            **arguments,
        )

    rows = tuple(
        calendar.session_on(day, as_of=signal.close_at) for day in calendar.session_dates
    )
    other_calendar_identity = replace(
        calendar.identity,
        source_identity=_source(
            "other-calendar-snapshot",
            datetime(2000, 1, 1, tzinfo=UTC),
        ),
    )
    other_calendar = AcceptedSessionCalendar(rows, identity=other_calendar_identity)
    with pytest.raises(MarketDataError, match="calendar identity mismatch"):
        _run_static_rebalance(
            portfolio,
            other_calendar,
            universe_snapshot=first_snapshot,
            **arguments,
        )
