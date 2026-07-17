"""Immutable blocked-exit lifecycle over one accepted-session calendar."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
import math

from quant_system.data import AcceptedSession, AcceptedSessionCalendar
from quant_system.markets.common import (
    FillDecision,
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
class ExitAttempt:
    session: AcceptedSession
    decision_at: datetime
    filled: bool
    price: float | None
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.session, AcceptedSession):
            raise MarketDataError("session must be an AcceptedSession")
        cutoff = require_aware_datetime(self.decision_at, "decision_at")
        if cutoff >= self.session.open_at:
            raise MarketDataError("decision_at cannot follow or equal the attempted-session open")
        if self.session.source.available_at > cutoff:
            raise MarketDataError("attempted-session source was unavailable at decision_at")
        require_nonempty_text(self.reason, "reason")
        if type(self.filled) is not bool:
            raise MarketDataError("filled must be boolean")
        if self.filled:
            try:
                price = _normalized_float(self.price, label="filled exit price")
            except ValueError as exc:
                raise MarketDataError(
                    "filled exit requires a positive finite price"
                ) from exc
            if price <= 0.0:
                raise MarketDataError("filled exit requires a positive finite price")
            if self.reason != "filled":
                raise MarketDataError("filled exit reason must be 'filled'")
            object.__setattr__(self, "price", price)
        elif self.price is not None or self.reason not in BLOCKED_EXIT_REASONS:
            raise MarketDataError("blocked exit requires a recognized reason and no price")


@dataclass(frozen=True)
class BlockedExitOrder:
    symbol: str
    shares: float
    requested_session: date
    calendar: AcceptedSessionCalendar
    attempts: tuple[ExitAttempt, ...] = ()
    executed_session: date | None = None
    execution_price: float | None = None
    delay_sessions: int | None = None

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
        if type(self.attempts) is not tuple:
            raise MarketDataError("attempts must be an immutable tuple")
        if any(not isinstance(attempt, ExitAttempt) for attempt in self.attempts):
            raise MarketDataError("attempts must contain only ExitAttempt values")

        previous: AcceptedSession | None = None
        for attempt in self.attempts:
            accepted = self.calendar.session_on(
                attempt.session.session_date,
                as_of=attempt.decision_at,
            )
            if accepted != attempt.session:
                raise MarketDataError("exit attempt does not match the accepted calendar identity")
            if previous is None:
                if attempt.session.session_date != self.requested_session:
                    raise ValueError("the first exit attempt must use the requested session")
            else:
                expected = self.calendar.next_session(
                    previous.session_date,
                    as_of=attempt.decision_at,
                )
                if attempt.session != expected:
                    raise ValueError("exit attempts must use consecutive accepted sessions")
            previous = attempt.session

        filled_attempts = tuple(attempt for attempt in self.attempts if attempt.filled)
        if self.executed_session is None:
            if filled_attempts or self.execution_price is not None or self.delay_sessions is not None:
                raise ValueError("pending exit cannot contain execution fields")
        else:
            if len(filled_attempts) != 1 or not self.attempts[-1].filled:
                raise ValueError("completed exit must end in exactly one filled attempt")
            last = self.attempts[-1]
            if self.executed_session != last.session.session_date or self.execution_price != last.price:
                raise ValueError("execution fields must match the final attempt")
            if self.delay_sessions != len(self.attempts) - 1:
                raise ValueError("delay_sessions must equal preceding blocked sessions")

    @property
    def pending(self) -> bool:
        return self.executed_session is None


def _validated_attempt(
    order: BlockedExitOrder,
    *,
    session: date,
    decision_at: datetime,
    decision: FillDecision,
    expected_filled: bool,
) -> ExitAttempt:
    if not order.pending:
        raise ValueError("completed exit cannot be advanced")
    require_date(session, "session")
    cutoff = require_aware_datetime(decision_at, "decision_at")
    if not isinstance(decision, FillDecision) or type(decision.filled) is not bool:
        raise MarketDataError("decision must be a FillDecision with boolean filled state")
    if decision.filled is not expected_filled:
        if expected_filled:
            raise MarketDataError("ready-exit execution requires a filled decision")
        raise MarketDataError("fillable decisions must execute through execute_ready_blocked_exit")

    accepted = order.calendar.session_on(session, as_of=cutoff)
    if order.attempts:
        expected = order.calendar.next_session(
            order.attempts[-1].session.session_date,
            as_of=cutoff,
        )
        if accepted != expected:
            raise ValueError("exit attempts must use consecutive accepted sessions")
    elif accepted.session_date != order.requested_session:
        raise ValueError("the first exit attempt must use the requested session")
    return ExitAttempt(
        session=accepted,
        decision_at=cutoff,
        filled=decision.filled,
        price=decision.price,
        reason=decision.reason,
    )


def advance_blocked_exit(
    order: BlockedExitOrder,
    *,
    session: date,
    decision_at: datetime,
    decision: FillDecision,
) -> BlockedExitOrder:
    """Record one non-fill on the next consecutive accepted session."""

    attempt = _validated_attempt(
        order,
        session=session,
        decision_at=decision_at,
        decision=decision,
        expected_filled=False,
    )
    return replace(order, attempts=order.attempts + (attempt,))


def execute_ready_blocked_exit(
    order: BlockedExitOrder,
    *,
    portfolio: Portfolio,
    session: date,
    decision_at: datetime,
    decision: FillDecision,
) -> tuple[BlockedExitOrder, Trade]:
    """Validate completion, sell through ``Portfolio``, then return both results."""

    if not isinstance(portfolio, Portfolio):
        raise TypeError("portfolio must be a Portfolio")
    attempt = _validated_attempt(
        order,
        session=session,
        decision_at=decision_at,
        decision=decision,
        expected_filled=True,
    )
    price = attempt.price
    assert type(price) is float
    settlement_date: date | None = None
    settlement_sessions: tuple[date, ...] | None = None
    if portfolio.us_cash_settlement:
        accepted: list[date] = []
        after = attempt.session.session_date
        for _ in range(cash_settlement_lag_sessions(after)):
            row = order.calendar.next_session(after, as_of=attempt.decision_at)
            accepted.append(row.session_date)
            after = row.session_date
        settlement_sessions = tuple(accepted)
        settlement_date = settlement_sessions[-1]
    completed = replace(
        order,
        attempts=order.attempts + (attempt,),
        executed_session=attempt.session.session_date,
        execution_price=price,
        delay_sessions=len(order.attempts),
    )
    trade = portfolio.sell(
        order.symbol,
        order.shares,
        price,
        attempt.session.session_date,
        settlement_date=settlement_date,
        accepted_settlement_sessions=settlement_sessions,
    )
    return completed, trade
