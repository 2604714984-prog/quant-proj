from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from quant_system.backtest.blocked_orders import (
    BlockedExitOrder,
    FillEvent,
    NoFillEvent,
    RetryInstruction,
    advance_blocked_exit,
    execute_ready_blocked_exit,
)
from quant_system.backtest.capacity import (
    CapacityObservation,
    CapacityPolicy,
    assess_capacity,
)
from quant_system.backtest.portfolio import Portfolio
from quant_system.data import (
    AcceptedSession,
    AcceptedSessionCalendar,
    CalendarIdentity,
    SourceIdentity,
    capture_source_bytes,
    session_dates_sha256,
    session_rows_sha256,
)
from quant_system.markets.common import FillDecision, MarketDataError
from quant_system.markets.universe import (
    StatusEvidence,
    evaluate_universe,
    lifecycle_coverage_sha256,
)

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
UTC = timezone.utc
SHANGHAI = "Asia/Shanghai"


class _StatefulFloat(float):
    def __new__(
        cls,
        value: float,
        *,
        fail_on_call: int,
    ) -> "_StatefulFloat":
        instance = super().__new__(cls, value)
        instance.fail_on_call = fail_on_call
        instance.calls = 0
        return instance

    def __float__(self) -> float:
        self.calls += 1
        if self.calls == self.fail_on_call:
            raise ValueError("stateful float conversion failure")
        return super().__float__()


def _source(
    revision_id: str,
    sha256: str,
    *,
    available_at: datetime = datetime(2026, 7, 1, tzinfo=UTC),
    supersedes: str | None = None,
) -> SourceIdentity:
    return SourceIdentity(
        source_url="https://example.test/source",
        content_sha256=sha256,
        available_at=available_at,
        retrieved_at=available_at + timedelta(minutes=1),
        revision_id=revision_id,
        source_family_id="fixture-source",
        provider_id="fixture-provider",
        subject_id="fixture-subject",
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
        exchange_id="XSHG" if exchange_timezone == SHANGHAI else "XNYS",
    )


def _calendar(exchange_timezone: str = SHANGHAI) -> AcceptedSessionCalendar:
    rows = (
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
    dates = tuple(row.session_date for row in rows)
    rows_sha = session_rows_sha256(rows)
    identity = CalendarIdentity(
        "XSHG" if exchange_timezone == SHANGHAI else "XNYS",
        exchange_timezone,
        dates[0],
        dates[-1],
        len(dates),
        session_dates_sha256(dates),
        rows_sha,
        _source("calendar-aggregate", SHA_A),
    )
    return AcceptedSessionCalendar(rows, identity=identity)


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
        decision_at=execution.open_at - timedelta(microseconds=1),
        execution_session=execution,
    )

    assert decision.allowed is False
    assert decision.max_shares == 5_000
    assert decision.reason == "exceeds_volume_cap"


def test_capacity_requires_decision_strictly_before_execution_open() -> None:
    calendar = _calendar()
    observed = calendar.session_on(
        date(2026, 7, 13),
        as_of=datetime(2026, 7, 14, tzinfo=UTC),
    )
    execution = calendar.session_on(
        date(2026, 7, 14),
        as_of=datetime(2026, 7, 14, tzinfo=UTC),
    )
    arguments = {
        "subject_id": "000001.SZ",
        "order_shares": 100,
        "execution_price_per_share": 10,
        "execution_price_currency": "CNY",
        "observation": _capacity_observation(observed),
        "policy": CapacityPolicy(0.1, 0.1, "CNY"),
        "execution_session": execution,
    }

    accepted = assess_capacity(
        **arguments,
        decision_at=execution.open_at - timedelta(microseconds=1),
    )
    assert accepted.allowed is True

    for decision_at in (
        execution.open_at,
        execution.open_at + timedelta(microseconds=1),
    ):
        with pytest.raises(MarketDataError, match="cannot follow"):
            assess_capacity(**arguments, decision_at=decision_at)


def test_capacity_fails_closed_on_identity_time_currency_and_unit_mismatch() -> None:
    calendar = _calendar()
    observed = calendar.session_on(date(2026, 7, 13), as_of=datetime(2026, 7, 14, tzinfo=UTC))
    execution = calendar.session_on(date(2026, 7, 14), as_of=datetime(2026, 7, 14, tzinfo=UTC))
    cutoff = execution.open_at - timedelta(microseconds=1)
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
            decision_at=execution.open_at - timedelta(microseconds=1),
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
        decision_at=execution.open_at - timedelta(microseconds=1),
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
            order.retry_instructions,
            order.no_fill_events,
            order.fill_event,
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
    accepted = order.calendar.session_on(
        session,
        as_of=datetime(2026, 7, 15, tzinfo=UTC),
    )
    return accepted.open_at - timedelta(microseconds=1)


def _fill_event(
    order: BlockedExitOrder,
    session: date,
    price: object,
    *,
    basis: str = "timestamped_session_open",
) -> FillEvent:
    accepted = order.calendar.session_on(
        session,
        as_of=datetime(2026, 7, 16, tzinfo=UTC),
    )
    available_at = (
        accepted.open_at
        if basis == "timestamped_session_open"
        else accepted.close_at + timedelta(hours=1)
    )
    source = capture_source_bytes(
        f"{session}:{price}:{basis}".encode(),
        publication_evidence=b"fixture publication receipt",
        source_url="https://example.test/fill-event",
        available_at=available_at,
        retrieved_at=available_at + timedelta(microseconds=1),
        revision_id=f"fill-{session}-{basis}",
        source_family_id="fill-event",
        provider_id="fixture-provider",
        subject_id=order.symbol,
    ).source
    return FillEvent(
        execution_at=available_at,
        price=price,  # type: ignore[arg-type]
        source=source,
        effective_at=accepted.open_at,
        basis=basis,  # type: ignore[arg-type]
    )


def _no_fill_event(
    order: BlockedExitOrder,
    session: date,
    reason: str,
) -> NoFillEvent:
    accepted = order.calendar.session_on(
        session,
        as_of=datetime(2026, 7, 16, tzinfo=UTC),
    )
    source = capture_source_bytes(
        f"{session}:{reason}".encode(),
        publication_evidence=b"fixture publication receipt",
        source_url="https://example.test/no-fill-event",
        available_at=accepted.open_at,
        retrieved_at=accepted.open_at + timedelta(microseconds=1),
        revision_id=f"no-fill-{session}-{reason}",
        source_family_id="no-fill-event",
        provider_id="fixture-provider",
        subject_id=order.symbol,
    ).source
    return NoFillEvent(
        observed_at=accepted.open_at,
        effective_at=accepted.open_at,
        reason=reason,
        source=source,
    )


def test_blocked_exit_retries_require_an_immutable_typed_tuple() -> None:
    with pytest.raises(MarketDataError, match="immutable tuple"):
        BlockedExitOrder(
            "000001.SZ",
            100,
            date(2026, 7, 13),
            _calendar(),
            retry_instructions=[],  # type: ignore[arg-type]
        )

    with pytest.raises(MarketDataError, match="only RetryInstruction"):
        BlockedExitOrder(
            "000001.SZ",
            100,
            date(2026, 7, 13),
            _calendar(),
            retry_instructions=(object(),),  # type: ignore[arg-type]
        )

    calendar = _calendar()
    session = calendar.session_on(
        date(2026, 7, 13),
        as_of=datetime(2026, 7, 13, tzinfo=UTC),
    )
    valid = RetryInstruction(
        session.open_at - timedelta(microseconds=1),
        session.session_date,
    )
    order = BlockedExitOrder("000001.SZ", 100, date(2026, 7, 13), calendar)
    advanced = advance_blocked_exit(
        order,
        instruction=valid,
        no_fill_event=_no_fill_event(order, session.session_date, "suspended"),
    )
    assert advanced.retry_instructions == (valid,)
    assert advanced.no_fill_events[0].reason == "suspended"


def test_retry_decision_requires_decision_strictly_before_session_open() -> None:
    calendar = _calendar()
    session = calendar.session_on(
        date(2026, 7, 13),
        as_of=datetime(2026, 7, 13, tzinfo=UTC),
    )
    accepted = RetryInstruction(
        session.open_at - timedelta(microseconds=1),
        session.session_date,
    )
    assert accepted.decision_at == session.open_at - timedelta(microseconds=1)

    for decision_at in (
        session.open_at,
        session.open_at + timedelta(microseconds=1),
    ):
        with pytest.raises(MarketDataError, match="strictly before"):
            advance_blocked_exit(
                _blocked_order(),
                instruction=RetryInstruction(decision_at, session.session_date),
                no_fill_event=_no_fill_event(
                    _blocked_order(),
                    session.session_date,
                    "suspended",
                ),
            )


def test_no_fill_outcome_is_post_open_and_never_carried_by_instruction() -> None:
    order = _blocked_order()
    session = order.calendar.session_on(
        order.requested_session,
        as_of=datetime(2026, 7, 15, tzinfo=UTC),
    )
    instruction = RetryInstruction(
        session.open_at - timedelta(microseconds=1),
        session.session_date,
    )
    event = _no_fill_event(order, session.session_date, "suspended")

    assert not hasattr(instruction, "reason")
    assert event.observed_at == session.open_at
    with pytest.raises(MarketDataError, match="cannot be observed before"):
        NoFillEvent(
            observed_at=session.open_at - timedelta(microseconds=1),
            effective_at=session.open_at,
            reason="suspended",
            source=event.source,
        )


def test_next_retry_instruction_must_follow_prior_no_fill_observation() -> None:
    order = _blocked_order()
    first = order.calendar.session_on(
        order.requested_session,
        as_of=datetime(2026, 7, 15, tzinfo=UTC),
    )
    second = order.calendar.next_session(
        first.session_date,
        as_of=first.open_at + timedelta(microseconds=1),
    )
    first_event = _no_fill_event(order, first.session_date, "suspended")
    second_event = _no_fill_event(order, second.session_date, "limit_down_sell_rejected")
    first_instruction = RetryInstruction(
        first.open_at - timedelta(microseconds=1),
        first.session_date,
    )
    stale_second_instruction = RetryInstruction(
        first.open_at - timedelta(microseconds=1),
        second.session_date,
    )

    with pytest.raises(MarketDataError, match="follow the prior no-fill"):
        BlockedExitOrder(
            order.symbol,
            order.shares,
            order.requested_session,
            order.calendar,
            retry_instructions=(first_instruction, stale_second_instruction),
            no_fill_events=(first_event, second_event),
        )

    valid_second_instruction = RetryInstruction(
        first_event.observed_at + timedelta(microseconds=1),
        second.session_date,
    )
    advanced = BlockedExitOrder(
        order.symbol,
        order.shares,
        order.requested_session,
        order.calendar,
        retry_instructions=(first_instruction, valid_second_instruction),
        no_fill_events=(first_event, second_event),
    )
    assert advanced.retry_instructions[-1].decision_at > first_event.observed_at


def test_blocked_exit_normalizes_stateful_numbers_once_before_sale() -> None:
    shares = _StatefulFloat(100, fail_on_call=2)
    order = BlockedExitOrder(
        "000001.SZ",
        shares,  # type: ignore[arg-type]
        date(2026, 7, 13),
        _calendar(),
    )
    assert type(order.shares) is float
    assert shares.calls == 1

    portfolio = Portfolio.a_share(10_000)
    portfolio.start_session(date(2026, 7, 10))
    portfolio.buy("000001.SZ", 100, 10, date(2026, 7, 10))
    portfolio.start_session(date(2026, 7, 13))
    price = _StatefulFloat(10, fail_on_call=6)

    completed, trade = execute_ready_blocked_exit(
        order,
        portfolio=portfolio,
        fill_event=_fill_event(order, date(2026, 7, 13), price),
    )

    assert price.calls == 1
    assert type(completed.execution_price) is float
    assert type(trade.price) is float
    assert "000001.SZ" not in portfolio.positions


def test_price_normalization_failure_leaves_deep_state_unchanged() -> None:
    order = _blocked_order()
    portfolio = Portfolio.a_share(10_000)
    portfolio.start_session(date(2026, 7, 10))
    portfolio.buy("000001.SZ", 100, 10, date(2026, 7, 10))
    portfolio.start_session(date(2026, 7, 13))
    order_before = _order_snapshot(order)
    portfolio_before = _portfolio_snapshot(portfolio)

    with pytest.raises(MarketDataError, match="positive finite price"):
        execute_ready_blocked_exit(
            order,
            portfolio=portfolio,
            fill_event=_fill_event(
                order,
                date(2026, 7, 13),
                _StatefulFloat(10, fail_on_call=1),
            ),
        )

    assert _order_snapshot(order) == order_before
    assert _portfolio_snapshot(portfolio) == portfolio_before


def test_portfolio_buy_and_sell_normalize_before_mutation() -> None:
    portfolio = Portfolio.a_share(10_000)
    portfolio.start_session(date(2026, 7, 10))
    portfolio_before = _portfolio_snapshot(portfolio)
    with pytest.raises(ValueError, match="price must be finite"):
        portfolio.buy(
            "000001.SZ",
            100,
            _StatefulFloat(10, fail_on_call=1),
            date(2026, 7, 10),
        )
    assert _portfolio_snapshot(portfolio) == portfolio_before

    buy_price = _StatefulFloat(10, fail_on_call=3)
    buy = portfolio.buy("000001.SZ", 100, buy_price, date(2026, 7, 10))
    assert buy_price.calls == 1
    assert type(buy.price) is float

    portfolio.start_session(date(2026, 7, 13))
    portfolio_before = _portfolio_snapshot(portfolio)
    with pytest.raises(ValueError, match="price must be finite"):
        portfolio.sell(
            "000001.SZ",
            100,
            _StatefulFloat(11, fail_on_call=1),
            date(2026, 7, 13),
        )
    assert _portfolio_snapshot(portfolio) == portfolio_before

    sell_price = _StatefulFloat(11, fail_on_call=3)
    sell = portfolio.sell("000001.SZ", 100, sell_price, date(2026, 7, 13))
    assert sell_price.calls == 1
    assert type(sell.price) is float
    assert "000001.SZ" not in portfolio.positions


def test_blocked_exit_records_consecutive_sessions_and_sells_before_completion() -> None:
    order = _blocked_order()
    order = advance_blocked_exit(
        order,
        instruction=RetryInstruction(
            _decision_time(order, date(2026, 7, 13)),
            date(2026, 7, 13),
        ),
        no_fill_event=_no_fill_event(order, date(2026, 7, 13), "suspended"),
    )
    order = advance_blocked_exit(
        order,
        instruction=RetryInstruction(
            _decision_time(order, date(2026, 7, 14)),
            date(2026, 7, 14),
        ),
        no_fill_event=_no_fill_event(
            order,
            date(2026, 7, 14),
            "limit_down_sell_rejected",
        ),
    )
    portfolio = Portfolio.a_share(100_000)
    portfolio.start_session(date(2026, 7, 10))
    portfolio.buy("000001.SZ", 100, 10, date(2026, 7, 10))
    portfolio.start_session(date(2026, 7, 15))

    order, trade = execute_ready_blocked_exit(
        order,
        portfolio=portfolio,
        fill_event=_fill_event(order, date(2026, 7, 15), 9.8),
    )

    assert order.pending is False
    assert order.delay_sessions == 2
    assert order.executed_session == date(2026, 7, 15)
    assert tuple(item.requested_session for item in order.retry_instructions) == (
        date(2026, 7, 13),
        date(2026, 7, 14),
    )
    assert tuple(item.reason for item in order.no_fill_events) == (
        "suspended",
        "limit_down_sell_rejected",
    )
    assert order.fill_event is not None
    assert order.fill_event.effective_at.date() == date(2026, 7, 15)
    assert order.evidence_grade == "TIMESTAMPED_MARKET_EVENT"
    assert trade.side == "sell"
    assert "000001.SZ" not in portfolio.positions


def test_blocked_exit_rejects_skipped_sessions_and_completion_without_sale() -> None:
    terminal = _blocked_order()
    with pytest.raises(MarketDataError, match="recognized.*reason"):
        advance_blocked_exit(
            terminal,
            instruction=RetryInstruction(
                _decision_time(terminal, date(2026, 7, 13)),
                date(2026, 7, 13),
            ),
            no_fill_event=_no_fill_event(
                terminal,
                date(2026, 7, 13),
                "confirmed_terminal_action",
            ),
        )

    order = _blocked_order()
    order = advance_blocked_exit(
        order,
        instruction=RetryInstruction(
            _decision_time(order, date(2026, 7, 13)),
            date(2026, 7, 13),
        ),
        no_fill_event=_no_fill_event(order, date(2026, 7, 13), "suspended"),
    )
    with pytest.raises(ValueError, match="consecutive"):
        advance_blocked_exit(
            order,
            instruction=RetryInstruction(
                _decision_time(order, date(2026, 7, 15)),
                date(2026, 7, 15),
            ),
            no_fill_event=_no_fill_event(order, date(2026, 7, 15), "confirmed_halt"),
        )
    with pytest.raises(TypeError, match="RetryInstruction"):
        advance_blocked_exit(
            order,
            instruction=FillDecision(True, 9.9, "filled"),  # type: ignore[arg-type]
            no_fill_event=_no_fill_event(order, date(2026, 7, 14), "suspended"),
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
            fill_event=_fill_event(order, date(2026, 7, 13), 10),
        )

    assert _order_snapshot(order) == order_before
    assert _portfolio_snapshot(portfolio) == portfolio_before


def test_ready_exit_source_timing_failure_leaves_deep_state_unchanged() -> None:
    order = _blocked_order()
    portfolio = Portfolio.a_share(10_000)
    portfolio.start_session(date(2026, 7, 10))
    portfolio.buy("000001.SZ", 100, 10, date(2026, 7, 10))
    portfolio.start_session(date(2026, 7, 13))
    order_before = _order_snapshot(order)
    portfolio_before = _portfolio_snapshot(portfolio)

    session = order.calendar.session_on(
        date(2026, 7, 13),
        as_of=datetime(2026, 7, 15, tzinfo=UTC),
    )
    late_source = capture_source_bytes(
        b"late fill",
        publication_evidence=b"fixture publication receipt",
        source_url="https://example.test/fill-event",
        available_at=session.open_at + timedelta(hours=1),
        retrieved_at=session.open_at + timedelta(hours=1, microseconds=1),
        revision_id="late-fill",
        source_family_id="fill-event",
        provider_id="fixture-provider",
        subject_id="000001.SZ",
    ).source
    with pytest.raises(MarketDataError, match="unavailable at execution_at"):
        FillEvent(
            execution_at=session.open_at,
            price=10,
            source=late_source,
            effective_at=session.open_at,
            basis="timestamped_session_open",
        )

    assert _order_snapshot(order) == order_before
    assert _portfolio_snapshot(portfolio) == portfolio_before


def test_fill_event_cannot_be_submitted_before_open() -> None:
    order = _blocked_order()
    session = order.calendar.session_on(
        date(2026, 7, 13),
        as_of=datetime(2026, 7, 15, tzinfo=UTC),
    )
    available_at = session.open_at - timedelta(microseconds=1)
    source = capture_source_bytes(
        b"impossible pre-open fill",
        publication_evidence=b"fixture publication receipt",
        source_url="https://example.test/fill-event",
        available_at=available_at,
        retrieved_at=available_at,
        revision_id="pre-open-fill",
        source_family_id="fill-event",
        provider_id="fixture-provider",
        subject_id=order.symbol,
    ).source

    with pytest.raises(MarketDataError, match="cannot precede"):
        FillEvent(
            execution_at=available_at,
            price=10,
            source=source,
            effective_at=session.open_at,
            basis="timestamped_session_open",
        )


def test_fill_event_basis_produces_explicit_evidence_grade() -> None:
    order = _blocked_order()
    timestamped = _fill_event(order, date(2026, 7, 13), 10)
    retrospective = _fill_event(
        order,
        date(2026, 7, 13),
        10,
        basis="retrospective_daily_bar_open_fill",
    )

    assert timestamped.evidence_grade == "TIMESTAMPED_MARKET_EVENT"
    assert retrospective.evidence_grade == "RETROSPECTIVE_DAILY_BAR"
    assert retrospective.execution_at > retrospective.effective_at


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
        fill_event=_fill_event(order, date(2026, 7, 13), 101),
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
    decision_at = session.open_at - timedelta(microseconds=1)
    eligible = evaluate_universe(
        "000001.SZ",
        session,
        decision_at,
        _status_records(),
        market="a_share",
    )
    excluded = evaluate_universe(
        "000001.SZ",
        session,
        decision_at,
        _status_records(st=True),
        market="a_share",
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

    decision = evaluate_universe(
        "000001.SZ",
        session,
        session.open_at - timedelta(microseconds=1),
        records,
        market="a_share",
    )

    assert decision.eligible is False
    assert decision.reasons == ("st",)
    assert dict((kind, source.revision_id) for kind, _, source in decision.evidence)["st"] == "st-v2"


def test_universe_rejects_missing_overlapping_branched_and_late_statuses() -> None:
    session = _calendar().session_on(
        date(2026, 7, 13),
        as_of=datetime(2026, 7, 13, tzinfo=UTC),
    )
    cutoff = session.open_at - timedelta(microseconds=1)
    with pytest.raises(MarketDataError, match="missing effective suspended"):
        evaluate_universe(
            "000001.SZ",
            session,
            cutoff,
            _status_records()[:-1],
            market="a_share",
        )

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
        evaluate_universe("000001.SZ", session, cutoff, records, market="a_share")

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
        evaluate_universe("000001.SZ", session, cutoff, records, market="a_share")

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
    with pytest.raises(MarketDataError, match="unavailable at decision_at"):
        evaluate_universe("000001.SZ", session, cutoff, records, market="a_share")

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
        evaluate_universe("000001.SZ", session, cutoff, records, market="a_share")


def test_universe_rejects_future_cutoff_calendar_unavailability_and_timezone_reuse() -> None:
    session = _calendar().session_on(
        date(2026, 7, 13),
        as_of=datetime(2026, 7, 13, tzinfo=UTC),
    )
    accepted = evaluate_universe(
        "000001.SZ",
        session,
        session.open_at - timedelta(microseconds=1),
        _status_records(),
        market="a_share",
    )
    assert accepted.eligible is True

    for decision_at in (
        session.open_at,
        session.open_at + timedelta(microseconds=1),
    ):
        with pytest.raises(MarketDataError, match="cannot follow"):
            evaluate_universe(
                "000001.SZ",
                session,
                decision_at,
                _status_records(),
                market="a_share",
            )

    late_session = _session(
        date(2026, 7, 13),
        revision_id="late-calendar",
        sha256="7" * 64,
        source_available_at=session.open_at + timedelta(minutes=1),
    )
    with pytest.raises(MarketDataError, match="session source was unavailable"):
        evaluate_universe(
            "000001.SZ",
            late_session,
            session.open_at - timedelta(microseconds=1),
            _status_records(),
            market="a_share",
        )

    with pytest.raises(MarketDataError, match="different exchange timezone"):
        evaluate_universe(
            "000001.SZ",
            session,
            session.open_at - timedelta(microseconds=1),
            _status_records(exchange_timezone="America/New_York"),
            market="a_share",
        )


def test_us_universe_requires_only_us_lifecycle_kinds() -> None:
    session = _calendar("America/New_York").session_on(
        date(2026, 7, 13),
        as_of=datetime(2026, 7, 13, tzinfo=UTC),
    )
    cutoff = session.open_at - timedelta(microseconds=1)
    records = tuple(
        record
        for record in _status_records(exchange_timezone="America/New_York")
        if record.kind not in {"st", "suspended"}
    )

    decision = evaluate_universe(
        "000001.SZ",
        session,
        cutoff,
        records,
        market="us",
    )

    assert decision.eligible is True
    assert tuple(kind for kind, _, _ in decision.evidence) == (
        "listed",
        "delisted",
    )
    for missing_kind in ("listed", "delisted"):
        incomplete = tuple(record for record in records if record.kind != missing_kind)
        with pytest.raises(MarketDataError, match=f"missing effective {missing_kind}"):
            evaluate_universe(
                "000001.SZ",
                session,
                cutoff,
                incomplete,
                market="us",
            )

    all_records = _status_records(exchange_timezone="America/New_York")
    for extra_kind in ("st", "suspended"):
        extra = next(record for record in all_records if record.kind == extra_kind)
        with pytest.raises(MarketDataError, match="exactly the market-required kinds"):
            evaluate_universe(
                "000001.SZ",
                session,
                cutoff,
                (*records, extra),
                market="us",
            )

def test_a_share_st_remains_required_and_market_binds_lifecycle_hash() -> None:
    session = _calendar().session_on(
        date(2026, 7, 13),
        as_of=datetime(2026, 7, 13, tzinfo=UTC),
    )
    cutoff = session.open_at - timedelta(microseconds=1)
    records = tuple(_status_records())
    without_st = tuple(record for record in records if record.kind != "st")

    with pytest.raises(MarketDataError, match="missing effective st"):
        evaluate_universe(
            "000001.SZ",
            session,
            cutoff,
            without_st,
            market="a_share",
        )

    records_by_symbol = {"000001.SZ": records}
    a_share_hash = lifecycle_coverage_sha256(
        ("000001.SZ",),
        session,
        cutoff,
        records_by_symbol,
        market="a_share",
    )
    us_records_by_symbol = {
        "000001.SZ": tuple(
            record for record in records if record.kind in {"listed", "delisted"}
        )
    }
    us_hash = lifecycle_coverage_sha256(
        ("000001.SZ",),
        session,
        cutoff,
        us_records_by_symbol,
        market="us",
    )

    assert a_share_hash != us_hash
