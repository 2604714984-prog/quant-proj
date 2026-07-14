"""Minimal US-equity halt, lifecycle, and corporate-action semantics."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
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
T_PLUS_ONE_EFFECTIVE_DATE = date(2024, 5, 28)


def cash_settlement_lag_sessions(trade_date: date) -> int:
    """Return the US equity settlement lag effective on ``trade_date``."""

    if type(trade_date) is not date:
        raise TypeError("trade_date must be a date")
    return 1 if trade_date >= T_PLUS_ONE_EFFECTIVE_DATE else 2


def require_accepted_settlement_sessions(
    trade_date: date,
    settlement_date: date,
    accepted_sessions: Sequence[date],
) -> tuple[date, ...]:
    """Bind settlement to the accepted sessions following the trade date."""

    if type(trade_date) is not date or type(settlement_date) is not date:
        raise TypeError("trade_date and settlement_date must be dates")
    if isinstance(accepted_sessions, (str, bytes)) or not isinstance(
        accepted_sessions,
        Sequence,
    ):
        raise TypeError("accepted_settlement_sessions must be a date sequence")
    sessions = tuple(accepted_sessions)
    expected_lag = cash_settlement_lag_sessions(trade_date)
    if len(sessions) != expected_lag:
        raise ValueError(
            f"accepted_settlement_sessions must contain exactly {expected_lag} session(s)"
        )
    if any(type(session) is not date for session in sessions):
        raise TypeError("accepted_settlement_sessions must contain only dates")
    if sessions[0] <= trade_date or any(
        earlier >= later for earlier, later in zip(sessions, sessions[1:])
    ):
        raise ValueError(
            "accepted_settlement_sessions must be strictly increasing after trade_date"
        )
    if sessions[-1] != settlement_date:
        raise ValueError(
            "settlement_date must equal the final accepted settlement session"
        )
    return sessions


def classify_bar(
    price: float | None,
    action_types: Iterable[str] = (),
    *,
    data_qualified: bool = False,
) -> GapClass:
    types = _normalize_action_types(action_types)
    _require_data_qualified(data_qualified)
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
    data_qualified: bool = False,
    slippage_bps: float = 0.0,
) -> FillDecision:
    """Fail closed on unknown gaps and suppress fills on accepted lifecycle events."""

    normalized_side = normalize_side(side)
    types = _normalize_action_types(action_types)
    _require_data_qualified(data_qualified)
    if types & TERMINAL_ACTION_TYPES:
        return FillDecision(False, None, "confirmed_terminal_action")
    if "trading_halt" in types:
        return FillDecision(False, None, "confirmed_halt")

    classification = classify_bar(open_price, types, data_qualified=True)
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
    data_qualified: bool = False,
) -> float:
    """Resolve a held-position mark without treating missing data as zero return."""

    types = _normalize_action_types(action_types)
    _require_data_qualified(data_qualified)
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
    adjusted_shares = shares * ratio
    adjusted_average_cost = average_cost / ratio
    if not is_finite_number(adjusted_shares) or not is_finite_number(
        adjusted_average_cost
    ):
        raise ValueError("split adjustment must produce finite values")
    return adjusted_shares, adjusted_average_cost


def cash_distribution(shares: float, amount_per_share: float) -> float:
    if not is_finite_number(shares) or shares < 0.0:
        raise ValueError("shares must be finite and nonnegative")
    if not is_finite_number(amount_per_share) or amount_per_share < 0.0:
        raise ValueError("amount_per_share must be finite and nonnegative")
    distribution = shares * amount_per_share
    if not is_finite_number(distribution):
        raise ValueError("cash distribution must be finite")
    return distribution


def _normalize_action_types(action_types: Iterable[str]) -> frozenset[str]:
    types = frozenset(str(item) for item in action_types)
    unknown = types - KNOWN_ACTION_TYPES
    if unknown:
        raise ValueError(f"unknown US corporate-action types: {sorted(unknown)}")
    return types


def _require_data_qualified(data_qualified: bool) -> None:
    if data_qualified is not True:
        raise GapPolicyError(
            "US bar and action data must be explicitly complete and available"
        )
