"""Fail-closed share participation from point-in-time market observations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
from typing import Literal

from quant_system.data import AcceptedSession, SourceIdentity
from quant_system.markets.common import (
    MarketDataError,
    is_finite_number,
    is_positive_price,
    require_aware_datetime,
    require_nonempty_text,
)

BindingCap = Literal["volume", "amount", "both"]


def _require_currency(value: object, name: str) -> str:
    currency = require_nonempty_text(value, name)
    if len(currency) != 3 or not currency.isalpha() or not currency.isupper():
        raise MarketDataError(f"{name} must be a three-letter uppercase currency")
    return currency


def _require_whole_shares(value: object, name: str, *, allow_zero: bool) -> float:
    if not is_finite_number(value):
        raise MarketDataError(f"{name} must be finite whole shares")
    shares = float(value)
    lower_bound = 0.0 if allow_zero else 1.0
    if shares < lower_bound or not shares.is_integer():
        qualifier = "nonnegative" if allow_zero else "positive"
        raise MarketDataError(f"{name} must be {qualifier} whole shares")
    return shares


@dataclass(frozen=True)
class CapacityObservation:
    subject_id: str
    observed_session: AcceptedSession
    session_volume_shares: float
    session_amount: float
    currency: str
    source: SourceIdentity

    def __post_init__(self) -> None:
        require_nonempty_text(self.subject_id, "subject_id")
        if not isinstance(self.observed_session, AcceptedSession):
            raise MarketDataError("observed_session must be an AcceptedSession")
        _require_whole_shares(
            self.session_volume_shares,
            "session_volume_shares",
            allow_zero=True,
        )
        if not is_finite_number(self.session_amount) or self.session_amount < 0.0:
            raise MarketDataError("session_amount must be finite and nonnegative")
        _require_currency(self.currency, "currency")
        if not isinstance(self.source, SourceIdentity):
            raise MarketDataError("source must be a canonical SourceIdentity")


@dataclass(frozen=True)
class CapacityPolicy:
    max_volume_fraction: float
    max_amount_fraction: float
    currency: str

    def __post_init__(self) -> None:
        for name, value in (
            ("max_volume_fraction", self.max_volume_fraction),
            ("max_amount_fraction", self.max_amount_fraction),
        ):
            if not is_finite_number(value) or not 0.0 < value <= 1.0:
                raise ValueError(f"{name} must be finite and in (0, 1]")
        _require_currency(self.currency, "currency")


@dataclass(frozen=True)
class CapacityDecision:
    allowed: bool
    order_shares: float
    order_amount: float
    max_shares: float
    max_amount: float
    binding_cap: BindingCap
    reason: str


def assess_capacity(
    subject_id: str,
    order_shares: float,
    execution_price_per_share: float,
    execution_price_currency: str,
    observation: CapacityObservation,
    policy: CapacityPolicy,
    *,
    decision_at: datetime,
    execution_session: AcceptedSession,
) -> CapacityDecision:
    """Apply volume and amount caps using only prior-session share observations."""

    subject = require_nonempty_text(subject_id, "subject_id")
    shares = _require_whole_shares(order_shares, "order_shares", allow_zero=False)
    if not is_positive_price(execution_price_per_share):
        raise ValueError("execution_price_per_share must be finite and positive")
    price_currency = _require_currency(execution_price_currency, "execution_price_currency")
    if not isinstance(observation, CapacityObservation):
        raise MarketDataError("observation must be a CapacityObservation")
    if observation.subject_id != subject:
        raise MarketDataError("capacity observation subject does not match the order")
    if not isinstance(execution_session, AcceptedSession):
        raise MarketDataError("execution_session must be an AcceptedSession")
    cutoff = require_aware_datetime(decision_at, "decision_at")
    if cutoff >= execution_session.open_at:
        raise MarketDataError("decision_at cannot follow or equal the execution-session open")
    observed_session = observation.observed_session
    if observed_session.session_date >= execution_session.session_date:
        raise MarketDataError("capacity observation must use an earlier accepted session")
    if observed_session.exchange_timezone != execution_session.exchange_timezone:
        raise MarketDataError("capacity sessions cannot mix exchange timezones")
    if observation.source.available_at < observed_session.close_at:
        raise MarketDataError(
            "full-session capacity source cannot be available before the observed-session close"
        )
    for label, source in (
        ("capacity observation", observation.source),
        ("observed calendar session", observed_session.source),
        ("execution calendar session", execution_session.source),
    ):
        if source.available_at > cutoff:
            raise MarketDataError(f"{label} source was unavailable at decision_at")
    if not (observation.currency == policy.currency == price_currency):
        raise MarketDataError("capacity amount and execution-price currencies do not match")

    price = float(execution_price_per_share)
    volume_cap = float(observation.session_volume_shares) * policy.max_volume_fraction
    amount_cap = float(observation.session_amount) * policy.max_amount_fraction
    amount_cap_as_shares = amount_cap / price
    order_amount = shares * price
    values = (volume_cap, amount_cap, amount_cap_as_shares, order_amount)
    if not all(is_finite_number(value) and value >= 0.0 for value in values):
        raise ValueError("capacity arithmetic must remain finite and nonnegative")

    max_shares = min(volume_cap, amount_cap_as_shares)
    max_amount = max_shares * price
    if not is_finite_number(max_amount):
        raise ValueError("capacity arithmetic must remain finite")
    if math.isclose(volume_cap, amount_cap_as_shares, rel_tol=1e-12, abs_tol=0.0):
        binding_cap: BindingCap = "both"
    elif volume_cap < amount_cap_as_shares:
        binding_cap = "volume"
    else:
        binding_cap = "amount"

    exceeds_volume = shares > volume_cap
    exceeds_amount = order_amount > amount_cap
    allowed = not exceeds_volume and not exceeds_amount
    if allowed:
        reason = "within_capacity"
    elif exceeds_volume and exceeds_amount:
        reason = "exceeds_volume_and_amount_caps"
    elif exceeds_volume:
        reason = "exceeds_volume_cap"
    else:
        reason = "exceeds_amount_cap"
    return CapacityDecision(
        allowed=allowed,
        order_shares=shares,
        order_amount=float(order_amount),
        max_shares=float(max_shares),
        max_amount=float(max_amount),
        binding_cap=binding_cap,
        reason=reason,
    )
