from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from quant_system.backtest.blocked_orders import (
    BlockedExitOrder,
    ExitAttempt,
    advance_blocked_exit,
    execute_ready_blocked_exit,
)
from quant_system.backtest.capacity import (
    CapacityObservation,
    CapacityPolicy,
    assess_capacity,
)
from quant_system.backtest.portfolio import Portfolio
from quant_system.data import AcceptedSession, AcceptedSessionCalendar, SourceIdentity
from quant_system.markets.common import FillDecision, MarketDataError
from quant_system.markets.universe import StatusEvidence, evaluate_universe

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
UTC = timezone.utc
SHANGHAI = "Asia/Shanghai"


def _source(
    revision_id: str,
    sha256: str,
    *,
    available_at: datetime = datetime(2026, 7, 1, tzinfo=UTC),
    supersedes: str | None = None,
) -> SourceIdentity:
    return SourceIdentity(
        source_url=f"https://example.test/{revision_id}",
        content_sha256=sha256,
        available_at=available_at,
        retrieved_at=available_at + timedelta(minutes=1),
        revision_id=revision_id,
        supersedes_revision_id=supersedes,
    )


def _session(
    session_date: date,
    *,
    revision_id: str,
    sha256: str,
    exchange_timezone: str = SHANGHAI,
    source_available_at: datetime = datetime(2026, 7, 1, tzinfo=UTC),
) -> AcceptedSession:
    zone = ZoneInfo(exchange_timezone)
    opened = datetime.combine(session_date, time(9, 30), zone)
    closed = datetime.combine(session_date, time(15), zone)
    return AcceptedSession(
        session_date,
        opened,
        closed,
        _source(revision_id, sha256, available_at=source_available_at),
        exchange_timezone,
    )


def _calendar(exchange_timezone: str = SHANGHAI) -> AcceptedSessionCalendar:
    return AcceptedSessionCalendar(
        (
            _session(
                date(2026, 7, 10),
                revision_id="cal-10",
                sha256="1" * 64,
                exchange_timezone=exchange_timezone,
            ),
            _session(
                date(2026, 7, 13),
                revision_id="cal-13",
                sha256="2" * 64,
                exchange_timezone=exchange_timezone,
            ),
            _session(
                date(2026, 7, 14),
                revision_id="cal-14",
                sha256="3" * 64,
                exchange_timezone=exchange_timezone,
            ),
            _session(
                date(2026, 7, 15),
                revision_id="cal-15",
                sha256="4" * 64,
                exchange_timezone=exchange_timezone,
            ),
        )
    )


def _capacity_observation(
    observed_session: AcceptedSession,
    *,
    subject_id: str = "000001.SZ",
    volume_shares: float = 100_000,
    amount: float = 500_000,
    currency: str = "CNY",
    source: SourceIdentity | None = None,
) -> CapacityObservation:
    return CapacityObservation(
        subject_id=subject_id,
        observed_session=observed_session,
        session_volume_shares=volume_shares,
        session_amount=amount,
        currency=currency,
        source=source
        or _source(
            "bar-13",
            SHA_A,
            available_at=observed_session.close_at,
        ),
    )


def test_capacity_uses_prior_accepted_share_volume_and_amount_caps() -> None:
    calendar = _calendar()
    observed = calendar.session_on(date(2026, 7, 13), as_of=datetime(2026, 7, 14, tzinfo=UTC))
    execution = calendar.session_on(date(2026, 7, 14), as_of=datetime(2026, 7, 14, tzinfo=UTC))
    decision_at = execution.open_at - timedelta(minutes=30)
    observation = _capacity_observation(observed)
    policy = CapacityPolicy(0.10, 0.05, "CNY")

    accepted = assess_capacity(
        "000001.SZ",
        2_000,
        10.0,
        "CNY",
        observation,
        policy,
        decision_at=decision_at,
        execution_session=execution,
    )
    rejected = assess_capacity(
        "000001.SZ",
        3_000,
        10.0,
        "CNY",
        observation,
        policy,
        decision_at=decision_at,
        execution_session=execution,
    )

    assert accepted.allowed is True
    assert accepted.binding_cap == "amount"
    assert accepted.max_shares == pytest.approx(2_500)
    assert accepted.max_amount == pytest.approx(25_000)
    assert rejected.reason == "exceeds_amount_cap"


def test_capacity_cannot_treat_one_hundred_lots_as_one_hundred_shares() -> None:
    calendar = _calendar()
    observed = calendar.session_on(date(2026, 7, 13), as_of=datetime(2026, 7, 14, tzinfo=UTC))
    execution = calendar.session_on(date(2026, 7, 14), as_of=datetime(2026, 7, 14, tzinfo=UTC))
    observation = _capacity_observation(observed, volume_shares=50_000, amount=10_000_000)

    decision = assess_capacity(
        "000001.SZ",
        10_000,
        10,
        "CNY",
        observation,
        CapacityPolicy(0.10, 1.0, "CNY"),
        decision_at=execution.open_at,
        execution_session=execution,
    )

    assert decision.allowed is False
    assert decision.max_shares == 5_000
    assert decision.reason == "exceeds_volume_cap"


def test_capacity_fails_closed_on_identity_time_currency_and_unit_mismatch() -> None:
    calendar = _calendar()
    observed = calendar.session_on(date(2026, 7, 13), as_of=datetime(2026, 7, 14, tzinfo=UTC))
    execution = calendar.session_on(date(2026, 7, 14), as_of=datetime(2026, 7, 14, tzinfo=UTC))
    cutoff = execution.open_at
    observation = _capacity_observation(observed)
    policy = CapacityPolicy(0.1, 0.1, "CNY")

    with pytest.raises(MarketDataError, match="subject"):
        assess_capacity(
            "600000.SH",
            100,
            10,
            "CNY",
            observation,
            policy,
            decision_at=cutoff,
            execution_session=execution,
        )
    with pytest.raises(MarketDataError, match="earlier accepted session"):
        assess_capacity(
            "000001.SZ",
            100,
            10,
            "CNY",
            _capacity_observation(execution),
            policy,
            decision_at=cutoff,
            execution_session=execution,
        )
    late_source = _source(
        "late-bar",
        SHA_B,
        available_at=cutoff + timedelta(minutes=1),
    )
    with pytest.raises(MarketDataError, match="unavailable"):
        assess_capacity(
            "000001.SZ",
            100,
            10,
            "CNY",
            _capacity_observation(observed, source=late_source),
            policy,
            decision_at=cutoff,
            execution_session=execution,
        )
    premature_source = _source(
        "premature-bar",
        "8" * 64,
        available_at=observed.open_at,
    )
    with pytest.raises(MarketDataError, match="before the observed-session close"):
        assess_capacity(
            "000001.SZ",
            100,
            10,
            "CNY",
            _capacity_observation(observed, source=premature_source),
            policy,
            decision_at=cutoff,
            execution_session=execution,
        )
    with pytest.raises(MarketDataError, match="cannot follow"):
        assess_capacity(
            "000001.SZ",
            100,
            10,
            "CNY",
            observation,
            policy,
            decision_at=cutoff + timedelta(microseconds=1),
            execution_session=execution,
        )
    with pytest.raises(MarketDataError, match="currencies"):
        assess_capacity(
            "000001.SZ",
            100,
            10,
            "USD",
            observation,
            policy,
            decision_at=cutoff,
            execution_session=execution,
        )
    with pytest.raises(MarketDataError, match="whole shares"):
        assess_capacity(
            "000001.SZ",
            1.5,
            10,
            "CNY",
            observation,
            policy,
            decision_at=cutoff,
            execution_session=execution,
        )


def test_capacity_rejects_cross_timezone_session_reuse_and_nonfinite_values() -> None:
    calendar = _calendar()
    execution = calendar.session_on(date(2026, 7, 14), as_of=datetime(2026, 7, 14, tzinfo=UTC))
    ny_observed = _session(
        date(2026, 7, 13),
        revision_id="nyse-13",
        sha256=SHA_B,
        exchange_timezone="America/New_York",
    )
    with pytest.raises(MarketDataError, match="mix exchange timezones"):
        assess_capacity(
            "000001.SZ",
            100,
            10,
            "CNY",
            _capacity_observation(ny_observed),
            CapacityPolicy(0.1, 0.1, "CNY"),
            decision_at=execution.open_at,
            execution_session=execution,
        )
    for bad in (float("nan"), float("inf"), -1.0, 1.5):
        with pytest.raises(MarketDataError):
            _capacity_observation(
                calendar.session_on(
                    date(2026, 7, 13),
                    as_of=datetime(2026, 7, 14, tzinfo=UTC),
                ),
                volume_shares=bad,
            )


def test_zero_observed_liquidity_is_valid_evidence_but_zero_capacity() -> None:
    calendar = _calendar()
    observed = calendar.session_on(date(2026, 7, 13), as_of=datetime(2026, 7, 14, tzinfo=UTC))
    execution = calendar.session_on(date(2026, 7, 14), as_of=datetime(2026, 7, 14, tzinfo=UTC))
    decision = assess_capacity(
        "000001.SZ",
        1,
        10,
        "CNY",
        _capacity_observation(observed, volume_shares=0, amount=0),
        CapacityPolicy(0.1, 0.1, "CNY"),
        decision_at=execution.open_at,
        execution_session=execution,
    )
    assert decision.allowed is False
    assert decision.max_shares == 0.0
    assert decision.binding_cap == "both"


def _blocked_order() -> BlockedExitOrder:
    return BlockedExitOrder("000001.SZ", 100, date(2026, 7, 13), _calendar())


def _order_snapshot(order: BlockedExitOrder) -> object:
    return deepcopy(
        (
            order.symbol,
            order.shares,
            order.requested_session,
            order.calendar.session_dates,
            order.attempts,
            order.executed_session,
            order.execution_price,
            order.delay_sessions,
        )
    )


def _portfolio_snapshot(portfolio: Portfolio) -> object:
    return deepcopy(
        (
            portfolio.settled_cash,
            portfolio.costs,
            portfolio.lot_size,
            portfolio.share_t_plus_one,
            portfolio.us_cash_settlement,
            portfolio.a_share_stamp_tax_schedule,
            portfolio.positions,
            portfolio.pending_cash,
            portfolio.current_session,
        )
    )


def _decision_time(order: BlockedExitOrder, session: date) -> datetime:
    return order.calendar.session_on(session, as_of=datetime(2026, 7, 15, tzinfo=UTC)).open_at


def test_blocked_exit_attempts_require_an_immutable_typed_tuple() -> None:
    with pytest.raises(MarketDataError, match="immutable tuple"):
        BlockedExitOrder(
            "000001.SZ",
            100,
            date(2026, 7, 13),
            _calendar(),
            attempts=[],  # type: ignore[arg-type]
        )

    with pytest.raises(MarketDataError, match="only ExitAttempt"):
        BlockedExitOrder(
            "000001.SZ",
            100,
            date(2026, 7, 13),
            _calendar(),
            attempts=(object(),),  # type: ignore[arg-type]
        )

    calendar = _calendar()
    session = calendar.session_on(
        date(2026, 7, 13),
        as_of=datetime(2026, 7, 13, tzinfo=UTC),
    )
    valid = ExitAttempt(
        session,
        session.open_at,
        False,
        None,
        "suspended",
    )
    assert BlockedExitOrder(
        "000001.SZ",
        100,
        date(2026, 7, 13),
        calendar,
        attempts=(valid,),
    ).attempts == (valid,)


def test_blocked_exit_records_consecutive_sessions_and_sells_before_completion() -> None:
    order = _blocked_order()
    order = advance_blocked_exit(
        order,
        session=date(2026, 7, 13),
        decision_at=_decision_time(order, date(2026, 7, 13)),
        decision=FillDecision(False, None, "suspended"),
    )
    order = advance_blocked_exit(
        order,
        session=date(2026, 7, 14),
        decision_at=_decision_time(order, date(2026, 7, 14)),
        decision=FillDecision(False, None, "limit_down_sell_rejected"),
    )
    portfolio = Portfolio.a_share(100_000)
    portfolio.start_session(date(2026, 7, 10))
    portfolio.buy("000001.SZ", 100, 10, date(2026, 7, 10))
    portfolio.start_session(date(2026, 7, 15))

    order, trade = execute_ready_blocked_exit(
        order,
        portfolio=portfolio,
        session=date(2026, 7, 15),
        decision_at=_decision_time(order, date(2026, 7, 15)),
        decision=FillDecision(True, 9.8, "filled"),
    )

    assert order.pending is False
    assert order.delay_sessions == 2
    assert order.executed_session == date(2026, 7, 15)
    assert tuple(attempt.session.session_date for attempt in order.attempts) == (
        date(2026, 7, 13),
        date(2026, 7, 14),
        date(2026, 7, 15),
    )
    assert tuple(attempt.session.source.revision_id for attempt in order.attempts) == (
        "cal-13",
        "cal-14",
        "cal-15",
    )
    assert trade.side == "sell"
    assert "000001.SZ" not in portfolio.positions


def test_blocked_exit_rejects_skipped_sessions_and_completion_without_sale() -> None:
    terminal = _blocked_order()
    with pytest.raises(MarketDataError, match="recognized reason"):
        advance_blocked_exit(
            terminal,
            session=date(2026, 7, 13),
            decision_at=_decision_time(terminal, date(2026, 7, 13)),
            decision=FillDecision(False, None, "confirmed_terminal_action"),
        )

    order = _blocked_order()
    order = advance_blocked_exit(
        order,
        session=date(2026, 7, 13),
        decision_at=_decision_time(order, date(2026, 7, 13)),
        decision=FillDecision(False, None, "suspended"),
    )
    with pytest.raises(ValueError, match="consecutive"):
        advance_blocked_exit(
            order,
            session=date(2026, 7, 15),
            decision_at=_decision_time(order, date(2026, 7, 15)),
            decision=FillDecision(False, None, "confirmed_halt"),
        )
    with pytest.raises(MarketDataError, match="execute through"):
        advance_blocked_exit(
            order,
            session=date(2026, 7, 14),
            decision_at=_decision_time(order, date(2026, 7, 14)),
            decision=FillDecision(True, 9.9, "filled"),
        )


def test_failed_portfolio_sale_leaves_order_and_portfolio_unchanged() -> None:
    order = _blocked_order()
    portfolio = Portfolio.a_share(10_000)
    portfolio.start_session(date(2026, 7, 13))
    order_before = _order_snapshot(order)
    portfolio_before = _portfolio_snapshot(portfolio)

    with pytest.raises(ValueError, match="sell quantity"):
        execute_ready_blocked_exit(
            order,
            portfolio=portfolio,
            session=date(2026, 7, 13),
            decision_at=_decision_time(order, date(2026, 7, 13)),
            decision=FillDecision(True, 10, "filled"),
        )

    assert _order_snapshot(order) == order_before
    assert _portfolio_snapshot(portfolio) == portfolio_before


def test_ready_exit_precondition_failure_leaves_deep_state_unchanged() -> None:
    order = _blocked_order()
    portfolio = Portfolio.a_share(10_000)
    portfolio.start_session(date(2026, 7, 10))
    portfolio.buy("000001.SZ", 100, 10, date(2026, 7, 10))
    portfolio.start_session(date(2026, 7, 13))
    order_before = _order_snapshot(order)
    portfolio_before = _portfolio_snapshot(portfolio)

    with pytest.raises(MarketDataError, match="requires a filled decision"):
        execute_ready_blocked_exit(
            order,
            portfolio=portfolio,
            session=date(2026, 7, 13),
            decision_at=_decision_time(order, date(2026, 7, 13)),
            decision=FillDecision(False, None, "suspended"),
        )

    assert _order_snapshot(order) == order_before
    assert _portfolio_snapshot(portfolio) == portfolio_before


def test_us_ready_exit_derives_settlement_from_the_same_accepted_calendar() -> None:
    calendar = _calendar("America/New_York")
    order = BlockedExitOrder("SPY", 1, date(2026, 7, 13), calendar)
    portfolio = Portfolio.us(10_000)
    portfolio.start_session(date(2026, 7, 10))
    portfolio.buy("SPY", 1, 100, date(2026, 7, 10))
    portfolio.start_session(date(2026, 7, 13))

    order, trade = execute_ready_blocked_exit(
        order,
        portfolio=portfolio,
        session=date(2026, 7, 13),
        decision_at=_decision_time(order, date(2026, 7, 13)),
        decision=FillDecision(True, 101, "filled"),
    )

    assert order.executed_session == date(2026, 7, 13)
    assert trade.side == "sell"
    assert tuple(item.settlement_date for item in portfolio.pending_cash) == (
        date(2026, 7, 14),
    )


def _status_records(
    *,
    st: bool = False,
    suspended: bool = False,
    exchange_timezone: str = SHANGHAI,
) -> list[StatusEvidence]:
    return [
        StatusEvidence(
            "listing",
            "000001.SZ",
            "listed",
            True,
            date(1991, 4, 3),
            None,
            exchange_timezone,
            _source("listing-v1", SHA_A),
        ),
        StatusEvidence(
            "delisting",
            "000001.SZ",
            "delisted",
            False,
            date(1991, 4, 3),
            None,
            exchange_timezone,
            _source("delisting-v1", SHA_B),
        ),
        StatusEvidence(
            "st-2026",
            "000001.SZ",
            "st",
            st,
            date(2026, 1, 1),
            None,
            exchange_timezone,
            _source("st-v1", SHA_C),
        ),
        StatusEvidence(
            "suspension-20260713",
            "000001.SZ",
            "suspended",
            suspended,
            date(2026, 7, 13),
            date(2026, 7, 14),
            exchange_timezone,
            _source("suspension-v1", "d" * 64),
        ),
    ]


def test_universe_uses_accepted_session_and_complete_pit_statuses() -> None:
    session = _calendar().session_on(
        date(2026, 7, 13),
        as_of=datetime(2026, 7, 13, tzinfo=UTC),
    )
    decision_at = session.open_at
    eligible = evaluate_universe("000001.SZ", session, decision_at, _status_records())
    excluded = evaluate_universe(
        "000001.SZ",
        session,
        decision_at,
        _status_records(st=True),
    )

    assert eligible.eligible is True
    assert tuple(kind for kind, _, _ in eligible.evidence) == (
        "listed",
        "delisted",
        "st",
        "suspended",
    )
    assert all(isinstance(source, SourceIdentity) for _, _, source in eligible.evidence)
    assert excluded.reasons == ("st",)


def test_universe_selects_one_valid_linear_status_revision() -> None:
    session = _calendar().session_on(
        date(2026, 7, 13),
        as_of=datetime(2026, 7, 13, tzinfo=UTC),
    )
    records = _status_records()
    original = records[2]
    revised_source = _source(
        "st-v2",
        "e" * 64,
        available_at=datetime(2026, 7, 12, tzinfo=UTC),
        supersedes=original.source.revision_id,
    )
    records.append(
        StatusEvidence(
            original.status_id,
            original.symbol,
            original.kind,
            True,
            original.effective_from,
            original.effective_to,
            original.exchange_timezone,
            revised_source,
        )
    )

    decision = evaluate_universe("000001.SZ", session, session.open_at, records)

    assert decision.eligible is False
    assert decision.reasons == ("st",)
    assert dict((kind, source.revision_id) for kind, _, source in decision.evidence)["st"] == "st-v2"


def test_universe_rejects_missing_overlapping_branched_and_late_statuses() -> None:
    session = _calendar().session_on(
        date(2026, 7, 13),
        as_of=datetime(2026, 7, 13, tzinfo=UTC),
    )
    cutoff = session.open_at
    with pytest.raises(MarketDataError, match="missing effective suspended"):
        evaluate_universe("000001.SZ", session, cutoff, _status_records()[:-1])

    records = _status_records()
    records.append(
        StatusEvidence(
            "other-st",
            "000001.SZ",
            "st",
            False,
            date(2026, 1, 1),
            None,
            SHANGHAI,
            _source("other-st-v1", "f" * 64),
        )
    )
    with pytest.raises(MarketDataError, match="overlapping effective st"):
        evaluate_universe("000001.SZ", session, cutoff, records)

    records = _status_records()
    parent = records[2]
    for revision_id, digest in (("st-v2a", "5" * 64), ("st-v2b", "6" * 64)):
        records.append(
            StatusEvidence(
                parent.status_id,
                parent.symbol,
                parent.kind,
                False,
                parent.effective_from,
                parent.effective_to,
                parent.exchange_timezone,
                _source(
                    revision_id,
                    digest,
                    available_at=datetime(2026, 7, 12, tzinfo=UTC),
                    supersedes=parent.source.revision_id,
                ),
            )
        )
    with pytest.raises(ValueError, match="branched"):
        evaluate_universe("000001.SZ", session, cutoff, records)

    records = _status_records()
    late = records[2]
    records[2] = StatusEvidence(
        late.status_id,
        late.symbol,
        late.kind,
        late.value,
        late.effective_from,
        late.effective_to,
        late.exchange_timezone,
        _source("late-st", SHA_C, available_at=cutoff + timedelta(minutes=1)),
    )
    with pytest.raises(MarketDataError, match="missing effective st"):
        evaluate_universe("000001.SZ", session, cutoff, records)

    records = _status_records()
    drifted = records[2]
    records.append(
        StatusEvidence(
            drifted.status_id,
            "600000.SH",
            drifted.kind,
            drifted.value,
            drifted.effective_from,
            drifted.effective_to,
            drifted.exchange_timezone,
            _source(
                "st-drifted-symbol",
                "9" * 64,
                available_at=datetime(2026, 7, 12, tzinfo=UTC),
                supersedes=drifted.source.revision_id,
            ),
        )
    )
    with pytest.raises(MarketDataError, match="share symbol, kind"):
        evaluate_universe("000001.SZ", session, cutoff, records)


def test_universe_rejects_future_cutoff_calendar_unavailability_and_timezone_reuse() -> None:
    session = _calendar().session_on(
        date(2026, 7, 13),
        as_of=datetime(2026, 7, 13, tzinfo=UTC),
    )
    with pytest.raises(MarketDataError, match="cannot follow"):
        evaluate_universe(
            "000001.SZ",
            session,
            session.open_at + timedelta(microseconds=1),
            _status_records(),
        )

    late_session = _session(
        date(2026, 7, 13),
        revision_id="late-calendar",
        sha256="7" * 64,
        source_available_at=session.open_at + timedelta(minutes=1),
    )
    with pytest.raises(MarketDataError, match="session source was unavailable"):
        evaluate_universe("000001.SZ", late_session, session.open_at, _status_records())

    with pytest.raises(MarketDataError, match="different exchange timezone"):
        evaluate_universe(
            "000001.SZ",
            session,
            session.open_at,
            _status_records(exchange_timezone="America/New_York"),
        )
