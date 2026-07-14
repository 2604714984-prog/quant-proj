"""Small, dependency-free market execution primitives."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import math
from typing import Literal, cast

Side = Literal["buy", "sell"]


class MarketDataError(ValueError):
    """Raised when a market input is missing or internally inconsistent."""


@dataclass(frozen=True)
class FillDecision:
    filled: bool
    price: float | None
    reason: str


def normalize_side(side: str) -> Side:
    normalized = side.lower()
    if normalized not in {"buy", "sell"}:
        raise ValueError(f"unsupported side: {side!r}")
    return cast(Side, normalized)


def is_finite_number(value: object) -> bool:
    if value is None or isinstance(value, bool):
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def is_positive_price(value: object) -> bool:
    return is_finite_number(value) and float(value) > 0.0


def require_nonempty_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise MarketDataError(f"{name} must be nonempty text without surrounding whitespace")
    return value


def require_sha256(value: object, name: str = "source_sha256") -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise MarketDataError(f"{name} must be a lowercase SHA-256 digest")
    return value


def require_aware_datetime(value: object, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise MarketDataError(f"{name} must be timezone-aware")
    return value


def require_date(value: object, name: str) -> date:
    if type(value) is not date:
        raise MarketDataError(f"{name} must be a date, not a datetime")
    return value


def apply_slippage(price: float, side: Side, slippage_bps: float) -> float:
    if not is_positive_price(price):
        raise MarketDataError("execution price must be positive and finite")
    if (
        not is_finite_number(slippage_bps)
        or slippage_bps < 0.0
        or slippage_bps >= 10_000.0
    ):
        raise ValueError("slippage_bps must be finite and in [0, 10000)")
    adjustment = float(slippage_bps) / 10_000.0
    adjusted_price = price * (
        1.0 + adjustment if side == "buy" else 1.0 - adjustment
    )
    if not is_positive_price(adjusted_price):
        raise MarketDataError("slippage-adjusted price must be positive and finite")
    return float(adjusted_price)
