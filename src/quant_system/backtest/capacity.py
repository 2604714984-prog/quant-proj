"""Fail-closed participation capacity from explicitly identified market data."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal

from quant_system.markets.common import (
    MarketDataError,
    is_finite_number,
    is_positive_price,
    require_nonempty_text,
    require_sha256,
)

BindingCap = Literal["volume", "amount", "both"]


@dataclass(frozen=True)
class CapacityObservation:
    session_volume: float
    volume_unit: str
    session_amount: float
    amount_currency: str
    source_id: str
    source_sha256: str

    def __post_init__(self) -> None:
        if not is_finite_number(self.session_volume) or self.session_volume < 0.0:
            raise MarketDataError("session_volume must be finite and nonnegative")
        if not is_finite_number(self.session_amount) or self.session_amount < 0.0:
            raise MarketDataError("session_amount must be finite and nonnegative")
        require_nonempty_text(self.volume_unit, "volume_unit")
        require_nonempty_text(self.amount_currency, "amount_currency")
        require_nonempty_text(self.source_id, "source_id")
        require_sha256(self.source_sha256)


@dataclass(frozen=True)
class CapacityPolicy:
    max_volume_fraction: float
    max_amount_fraction: float
    volume_unit: str
    amount_currency: str

    def __post_init__(self) -> None:
        for name, value in (
            ("max_volume_fraction", self.max_volume_fraction),
            ("max_amount_fraction", self.max_amount_fraction),
        ):
            if not is_finite_number(value) or not 0.0 < value <= 1.0:
                raise ValueError(f"{name} must be finite and in (0, 1]")
        require_nonempty_text(self.volume_unit, "volume_unit")
        require_nonempty_text(self.amount_currency, "amount_currency")


@dataclass(frozen=True)
class CapacityDecision:
    allowed: bool
    order_volume: float
    order_amount: float
    max_volume: float
    max_amount: float
    binding_cap: BindingCap
    reason: str


def assess_capacity(
    order_volume: float,
    execution_price: float,
    observation: CapacityObservation,
    policy: CapacityPolicy,
) -> CapacityDecision:
    """Apply the minimum of volume- and amount-participation caps."""

    if not is_finite_number(order_volume) or order_volume <= 0.0:
        raise ValueError("order_volume must be finite and positive")
    if not is_positive_price(execution_price):
        raise ValueError("execution_price must be finite and positive")
    if observation.volume_unit != policy.volume_unit:
        raise MarketDataError("capacity volume units do not match")
    if observation.amount_currency != policy.amount_currency:
        raise MarketDataError("capacity amount currencies do not match")

    volume_cap = observation.session_volume * policy.max_volume_fraction
    amount_cap = observation.session_amount * policy.max_amount_fraction
    amount_cap_as_volume = amount_cap / execution_price
    order_amount = order_volume * execution_price
    values = (volume_cap, amount_cap, amount_cap_as_volume, order_amount)
    if not all(is_finite_number(value) and value >= 0.0 for value in values):
        raise ValueError("capacity arithmetic must remain finite and nonnegative")

    max_volume = min(volume_cap, amount_cap_as_volume)
    max_amount = max_volume * execution_price
    if not is_finite_number(max_amount):
        raise ValueError("capacity arithmetic must remain finite")
    if math.isclose(volume_cap, amount_cap_as_volume, rel_tol=1e-12, abs_tol=0.0):
        binding_cap: BindingCap = "both"
    elif volume_cap < amount_cap_as_volume:
        binding_cap = "volume"
    else:
        binding_cap = "amount"

    exceeds_volume = order_volume > volume_cap
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
        order_volume=float(order_volume),
        order_amount=float(order_amount),
        max_volume=float(max_volume),
        max_amount=float(max_amount),
        binding_cap=binding_cap,
        reason=reason,
    )
