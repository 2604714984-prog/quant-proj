"""Immutable blocked-exit lifecycle over one accepted-session calendar."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
import math
from typing import Literal

from quant_system.data import (
    AcceptedSession,
    AcceptedSessionCalendar,
    SourceIdentity,
    require_trusted_source,
)
from quant_system.markets.common import (
    MarketDataError,
    require_aware_datetime,
    require_date,
    require_nonempty_text,
)
from quant_system.markets.us import cash_settlement_lag_sessions

from .portfolio import Portfolio, Trade

BLOCKED_EXIT_REASONS = frozenset(
    {"suspended", "limit_down_sell_rejected", "confirmed_halt"}
)
FillBasis = Literal["timestamped_session_open", "retrospective_daily_bar_open_fill"]
EvidenceGrade = Literal["TIMESTAMPED_MARKET_EVENT", "RETROSPECTIVE_DAILY_BAR"]


def _normalized_float(value: object, *, label: str) -> float:
    if value is None or isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    try:
        normalized = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not math.isfinite(normalized):
        raise ValueError(f"{label} must be finite")
    return normalized


@dataclass(frozen=True)
class RetryDecision:
    """A pre-open decision to retry an exit, which can never carry a price."""

    decision_at: datetime
    requested_session: date
    reason: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "decision_at",
            require_aware_datetime(self.decision_at, "decision_at"),
        )
        require_date(self.requested_session, "requested_session")
        reason = require_nonempty_text(self.reason, "reason")
        if reason not in BLOCKED_EXIT_REASONS:
            raise MarketDataError("retry decision requires a recognized blocked-exit reason")
        object.__setattr__(self, "reason", reason)


@dataclass(frozen=True)
class FillEvent:
    """A post-event fill observation bound to exact captured source bytes."""

    execution_at: datetime
    price: float
    source: SourceIdentity
    effective_at: datetime
    basis: FillBasis

    def __post_init__(self) -> None:
        execution_at = require_aware_datetime(self.execution_at, "execution_at")
        effective_at = require_aware_datetime(self.effective_at, "effective_at")
        try:
            price = _normalized_float(self.price, label="fill price")
        except ValueError as exc:
            raise MarketDataError("fill event requires a positive finite price") from exc
        if price <= 0:
            raise MarketDataError("fill event requires a positive finite price")
        try:
            require_trusted_source(self.source)
        except ValueError as exc:
            raise MarketDataError("fill event requires a trusted source capture") from exc
        if self.basis not in {
            "timestamped_session_open",
            "retrospective_daily_bar_open_fill",
        }:
            raise MarketDataError("fill event basis is unsupported")
        if execution_at < effective_at:
            raise MarketDataError("execution_at cannot precede the effective market event")
        if self.source.available_at > execution_at:
            raise MarketDataError("fill source was unavailable at execution_at")
        if self.basis == "timestamped_session_open":
            if execution_at != effective_at or self.source.available_at != effective_at:
                raise MarketDataError(
                    "timestamped fill requires execution and source availability at effective_at"
                )
        elif self.source.available_at <= effective_at:
            raise MarketDataError(
                "retrospective fill source must become available after effective_at"
            )
        object.__setattr__(self, "execution_at", execution_at)
        object.__setattr__(self, "effective_at", effective_at)
        object.__setattr__(self, "price", price)

    @property
    def evidence_grade(self) -> EvidenceGrade:
        if self.basis == "timestamped_session_open":
            return "TIMESTAMPED_MARKET_EVENT"
        return "RETROSPECTIVE_DAILY_BAR"


@dataclass(frozen=True)
class BlockedExitOrder:
    symbol: str
    shares: float
    requested_session: date
    calendar: AcceptedSessionCalendar
    retry_decisions: tuple[RetryDecision, ...] = ()
    fill_event: FillEvent | None = None
    executed_session: date | None = None
    execution_price: float | None = None
    delay_sessions: int | None = None
    evidence_grade: EvidenceGrade | None = None

    def __post_init__(self) -> None:
        require_nonempty_text(self.symbol, "symbol")
        try:
            shares = _normalized_float(self.shares, label="shares")
        except ValueError as exc:
            raise ValueError("shares must be positive whole shares") from exc
        if shares <= 0.0 or not shares.is_integer():
            raise ValueError("shares must be positive whole shares")
        object.__setattr__(self, "shares", shares)
        require_date(self.requested_session, "requested_session")
        if not isinstance(self.calendar, AcceptedSessionCalendar):
            raise MarketDataError("calendar must be an AcceptedSessionCalendar")
        if self.requested_session not in self.calendar.session_dates:
            raise MarketDataError("requested_session must be present in the accepted calendar")
        if type(self.retry_decisions) is not tuple:
            raise MarketDataError("retry_decisions must be an immutable tuple")
        if any(not isinstance(item, RetryDecision) for item in self.retry_decisions):
            raise MarketDataError("retry_decisions must contain only RetryDecision values")

        previous_session: date | None = None
        for decision in self.retry_decisions:
            accepted = _accepted_retry_session(self, decision)
            if previous_session is None:
                if accepted.session_date != self.requested_session:
                    raise ValueError("the first retry must use the requested session")
            else:
                expected = self.calendar.next_session(
                    previous_session,
                    as_of=decision.decision_at,
                )
                if accepted != expected:
                    raise ValueError("retry decisions must use consecutive accepted sessions")
            previous_session = accepted.session_date

        if self.fill_event is None:
            if any(
                value is not None
                for value in (
                    self.executed_session,
                    self.execution_price,
                    self.delay_sessions,
                    self.evidence_grade,
                )
            ):
                raise ValueError("pending exit cannot contain execution fields")
        else:
            if self.executed_session is None:
                raise ValueError("completed exit requires executed_session")
            accepted_fill = self.calendar.session_on(
                self.executed_session,
                as_of=self.fill_event.execution_at,
            )
            expected_date = (
                self.calendar.next_session(
                    self.retry_decisions[-1].requested_session,
                    as_of=self.fill_event.execution_at,
                ).session_date
                if self.retry_decisions
                else self.requested_session
            )
            if self.executed_session != expected_date:
                raise ValueError("fill must use the next consecutive accepted session")
            if self.fill_event.effective_at != accepted_fill.open_at:
                raise ValueError("fill event must match executed-session open")
            if self.fill_event.source.subject_id != self.symbol:
                raise ValueError("fill source subject must match order symbol")
            if self.execution_price != self.fill_event.price:
                raise ValueError("execution price must match fill event")
            if self.delay_sessions != len(self.retry_decisions):
                raise ValueError("delay_sessions must equal preceding retry decisions")
            if self.evidence_grade != self.fill_event.evidence_grade:
                raise ValueError("evidence grade must match fill event basis")

    @property
    def pending(self) -> bool:
        return self.fill_event is None


def _accepted_retry_session(
    order: BlockedExitOrder,
    decision: RetryDecision,
) -> AcceptedSession:
    accepted = order.calendar.session_on(
        decision.requested_session,
        as_of=decision.decision_at,
    )
    if decision.decision_at >= accepted.open_at:
        raise MarketDataError("retry decision must be strictly before requested-session open")
    if accepted.source.available_at > decision.decision_at:
        raise MarketDataError("requested-session source was unavailable at decision_at")
    return accepted


def _expected_fill_session(order: BlockedExitOrder, fill_event: FillEvent) -> AcceptedSession:
    if not order.pending:
        raise ValueError("completed exit cannot be advanced")
    if order.retry_decisions:
        expected = order.calendar.next_session(
            order.retry_decisions[-1].requested_session,
            as_of=fill_event.execution_at,
        )
    else:
        expected = order.calendar.session_on(
            order.requested_session,
            as_of=fill_event.execution_at,
        )
    if fill_event.effective_at != expected.open_at:
        raise MarketDataError("fill effective_at must equal the accepted-session open")
    if fill_event.execution_at < expected.open_at:
        raise MarketDataError("fill event cannot be submitted before session open")
    if fill_event.source.subject_id != order.symbol:
        raise MarketDataError("fill source subject must match order symbol")
    return expected


def advance_blocked_exit(
    order: BlockedExitOrder,
    *,
    decision: RetryDecision,
) -> BlockedExitOrder:
    """Record one price-free pre-open retry on the next accepted session."""

    if not isinstance(decision, RetryDecision):
        raise TypeError("decision must be a RetryDecision")
    if not order.pending:
        raise ValueError("completed exit cannot be advanced")
    accepted = _accepted_retry_session(order, decision)
    if order.retry_decisions:
        expected = order.calendar.next_session(
            order.retry_decisions[-1].requested_session,
            as_of=decision.decision_at,
        )
        if accepted != expected:
            raise ValueError("retry decisions must use consecutive accepted sessions")
    elif accepted.session_date != order.requested_session:
        raise ValueError("the first retry must use the requested session")
    return replace(
        order,
        retry_decisions=order.retry_decisions + (decision,),
    )


def execute_ready_blocked_exit(
    order: BlockedExitOrder,
    *,
    portfolio: Portfolio,
    fill_event: FillEvent,
) -> tuple[BlockedExitOrder, Trade]:
    """Validate a post-open fill, sell, then return immutable completion evidence."""

    if not isinstance(portfolio, Portfolio):
        raise TypeError("portfolio must be a Portfolio")
    if not isinstance(fill_event, FillEvent):
        raise TypeError("fill_event must be a FillEvent")
    accepted = _expected_fill_session(order, fill_event)
    settlement_date: date | None = None
    settlement_sessions: tuple[date, ...] | None = None
    if portfolio.us_cash_settlement:
        accepted_settlements: list[date] = []
        after = accepted.session_date
        for _ in range(cash_settlement_lag_sessions(after)):
            row = order.calendar.next_session(after, as_of=fill_event.execution_at)
            accepted_settlements.append(row.session_date)
            after = row.session_date
        settlement_sessions = tuple(accepted_settlements)
        settlement_date = settlement_sessions[-1]
    completed = replace(
        order,
        fill_event=fill_event,
        executed_session=accepted.session_date,
        execution_price=fill_event.price,
        delay_sessions=len(order.retry_decisions),
        evidence_grade=fill_event.evidence_grade,
    )
    trade = portfolio.sell(
        order.symbol,
        order.shares,
        fill_event.price,
        accepted.session_date,
        settlement_date=settlement_date,
        accepted_settlement_sessions=settlement_sessions,
    )
    return completed, trade
