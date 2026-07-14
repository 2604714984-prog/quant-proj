"""Minimal US-equity halt, lifecycle, and corporate-action semantics."""

from __future__ import annotations

from enum import Enum
from typing import Iterable

from .common import FillDecision, apply_slippage, is_finite_number, is_positive_price
from .common import normalize_side


class GapClass(str, Enum):
    AVAILABLE = "available"
    CONFIRMED_HALT = "confirmed_halt"
    CONFIRMED_CORPORATE_ACTION = "confirmed_corporate_action"
    UNEXPLAINED_PROVIDER_GAP = "unexplained_provider_gap"


class GapPolicyError(RuntimeError):
    """A missing bar or valuation that invalidates a backtest."""


class UnexplainedProviderGapError(GapPolicyError):
    pass


class CorporateActionValuationError(GapPolicyError):
    pass


PRICE_IDENTITY_ACTION_TYPES = frozenset(
    {
        "split",
        "reverse_split",
        "dividend",
        "special_dividend",
        "symbol_change",
        "merger",
        "delisting",
    }
)
TERMINAL_ACTION_TYPES = frozenset({"symbol_change", "merger", "delisting"})
KNOWN_ACTION_TYPES = PRICE_IDENTITY_ACTION_TYPES | {"trading_halt", "earnings_date"}


def classify_bar(price: float | None, action_types: Iterable[str] = ()) -> GapClass:
    types = _normalize_action_types(action_types)
    if is_positive_price(price):
        return GapClass.AVAILABLE
    if types & PRICE_IDENTITY_ACTION_TYPES:
        return GapClass.CONFIRMED_CORPORATE_ACTION
    if "trading_halt" in types:
        return GapClass.CONFIRMED_HALT
    return GapClass.UNEXPLAINED_PROVIDER_GAP


def decide_fill(
    side: str,
    open_price: float | None,
    *,
    action_types: Iterable[str] = (),
    slippage_bps: float = 0.0,
) -> FillDecision:
    """Fail closed on unknown gaps and suppress fills on accepted lifecycle events."""

    normalized_side = normalize_side(side)
    types = _normalize_action_types(action_types)
    if types & TERMINAL_ACTION_TYPES:
        return FillDecision(False, None, "confirmed_terminal_action")
    if "trading_halt" in types:
        return FillDecision(False, None, "confirmed_halt")

    classification = classify_bar(open_price, types)
    if classification is GapClass.CONFIRMED_CORPORATE_ACTION:
        return FillDecision(False, None, "confirmed_corporate_action_gap")
    if classification is GapClass.UNEXPLAINED_PROVIDER_GAP:
        raise UnexplainedProviderGapError(
            "missing US execution bar has no accepted event identity"
        )

    return FillDecision(
        True,
        apply_slippage(float(open_price), normalized_side, slippage_bps),
        "filled",
    )


def resolve_mark(
    *,
    symbol: str,
    current_price: float | None,
    previous_accepted_price: float | None,
    action_types: Iterable[str] = (),
    terminal_value: float | None = None,
) -> float:
    """Resolve a held-position mark without treating missing data as zero return."""

    types = _normalize_action_types(action_types)
    if types & TERMINAL_ACTION_TYPES:
        if is_finite_number(terminal_value) and float(terminal_value) >= 0.0:
            return float(terminal_value)
        raise CorporateActionValuationError(
            f"{symbol} terminal action lacks an action-complete terminal value"
        )
    if "trading_halt" in types:
        if is_positive_price(previous_accepted_price):
            return float(previous_accepted_price)
        raise UnexplainedProviderGapError(
            f"{symbol} confirmed halt has no prior accepted valuation"
        )
    if is_positive_price(current_price):
        return float(current_price)
    if types & PRICE_IDENTITY_ACTION_TYPES:
        raise CorporateActionValuationError(
            f"{symbol} corporate-action gap lacks an adjusted total-return value"
        )
    raise UnexplainedProviderGapError(
        f"{symbol} missing valuation has no accepted halt or corporate-action identity"
    )


def split_adjustment(shares: float, average_cost: float, ratio: float) -> tuple[float, float]:
    if not is_finite_number(shares) or shares < 0.0:
        raise ValueError("shares must be finite and nonnegative")
    if not is_finite_number(average_cost) or average_cost < 0.0:
        raise ValueError("average_cost must be finite and nonnegative")
    if not is_finite_number(ratio) or ratio <= 0.0:
        raise ValueError("split ratio must be positive and finite")
    return shares * ratio, average_cost / ratio


def cash_distribution(shares: float, amount_per_share: float) -> float:
    if not is_finite_number(shares) or shares < 0.0:
        raise ValueError("shares must be finite and nonnegative")
    if not is_finite_number(amount_per_share) or amount_per_share < 0.0:
        raise ValueError("amount_per_share must be finite and nonnegative")
    return shares * amount_per_share


def _normalize_action_types(action_types: Iterable[str]) -> frozenset[str]:
    types = frozenset(str(item) for item in action_types)
    unknown = types - KNOWN_ACTION_TYPES
    if unknown:
        raise ValueError(f"unknown US corporate-action types: {sorted(unknown)}")
    return types
