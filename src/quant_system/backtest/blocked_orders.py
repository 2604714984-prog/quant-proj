"""Immutable lifecycle for exits blocked on accepted market sessions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date

from quant_system.markets.common import (
    FillDecision,
    MarketDataError,
    is_finite_number,
    is_positive_price,
    require_date,
    require_nonempty_text,
    require_sha256,
)

BLOCKED_EXIT_REASONS = frozenset(
    {"suspended", "limit_down_sell_rejected", "confirmed_halt"}
)


@dataclass(frozen=True)
class ExitAttempt:
    session: date
    accepted_session_ordinal: int
    session_identity_sha256: str
    filled: bool
    price: float | None
    reason: str

    def __post_init__(self) -> None:
        require_date(self.session, "session")
        if type(self.accepted_session_ordinal) is not int or self.accepted_session_ordinal < 0:
            raise ValueError("accepted_session_ordinal must be a nonnegative integer")
        require_sha256(self.session_identity_sha256, "session_identity_sha256")
        require_nonempty_text(self.reason, "reason")
        if type(self.filled) is not bool:
            raise MarketDataError("filled must be boolean")
        if self.filled:
            if not is_positive_price(self.price):
                raise MarketDataError("filled exit requires a positive finite price")
            if self.reason != "filled":
                raise MarketDataError("filled exit reason must be 'filled'")
        elif self.price is not None or self.reason not in BLOCKED_EXIT_REASONS:
            raise MarketDataError("blocked exit requires a recognized reason and no price")


@dataclass(frozen=True)
class BlockedExitOrder:
    symbol: str
    quantity: float
    requested_session: date
    attempts: tuple[ExitAttempt, ...] = ()
    executed_session: date | None = None
    execution_price: float | None = None
    delay_sessions: int | None = None

    def __post_init__(self) -> None:
        require_nonempty_text(self.symbol, "symbol")
        if not is_finite_number(self.quantity) or self.quantity <= 0.0:
            raise ValueError("quantity must be finite and positive")
        require_date(self.requested_session, "requested_session")
        previous_session: date | None = None
        for ordinal, attempt in enumerate(self.attempts):
            if attempt.accepted_session_ordinal != ordinal:
                raise ValueError("exit attempts must use contiguous accepted-session ordinals")
            if ordinal == 0 and attempt.session != self.requested_session:
                raise ValueError("the first exit attempt must use the requested session")
            if previous_session is not None and attempt.session <= previous_session:
                raise ValueError("exit attempt sessions must be strictly increasing")
            previous_session = attempt.session

        filled_attempts = tuple(attempt for attempt in self.attempts if attempt.filled)
        if self.executed_session is None:
            if filled_attempts or self.execution_price is not None or self.delay_sessions is not None:
                raise ValueError("pending exit cannot contain execution fields")
        else:
            if len(filled_attempts) != 1 or not self.attempts[-1].filled:
                raise ValueError("completed exit must end in exactly one filled attempt")
            last = self.attempts[-1]
            if self.executed_session != last.session or self.execution_price != last.price:
                raise ValueError("execution fields must match the final attempt")
            if self.delay_sessions != len(self.attempts) - 1:
                raise ValueError("delay_sessions must equal preceding blocked sessions")

    @property
    def pending(self) -> bool:
        return self.executed_session is None


def advance_blocked_exit(
    order: BlockedExitOrder,
    *,
    session: date,
    accepted_session_ordinal: int,
    session_identity_sha256: str,
    decision: FillDecision,
) -> BlockedExitOrder:
    """Record every accepted session until the first executable exit."""

    if not order.pending:
        raise ValueError("completed exit cannot be advanced")
    require_date(session, "session")
    expected_ordinal = len(order.attempts)
    if accepted_session_ordinal != expected_ordinal:
        raise ValueError("accepted sessions cannot be skipped or replayed")
    if expected_ordinal == 0 and session != order.requested_session:
        raise ValueError("the first exit attempt must use the requested session")
    if order.attempts and session <= order.attempts[-1].session:
        raise ValueError("exit attempt sessions must be strictly increasing")
    require_sha256(session_identity_sha256, "session_identity_sha256")
    if type(decision.filled) is not bool:
        raise MarketDataError("fill decision must contain a boolean filled state")

    attempt = ExitAttempt(
        session=session,
        accepted_session_ordinal=accepted_session_ordinal,
        session_identity_sha256=session_identity_sha256,
        filled=decision.filled,
        price=decision.price,
        reason=decision.reason,
    )
    attempts = order.attempts + (attempt,)
    if not decision.filled:
        return replace(order, attempts=attempts)
    assert decision.price is not None
    return replace(
        order,
        attempts=attempts,
        executed_session=session,
        execution_price=float(decision.price),
        delay_sessions=len(order.attempts),
    )
