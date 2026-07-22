"""Minimal A-share daily execution rules.

Signals are assumed to be formed after close and executed at the next accepted
session open. Share settlement and cash accounting live in the portfolio module.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math
from typing import Literal

from .common import (
    FillDecision,
    MarketDataError,
    apply_slippage,
    is_finite_number,
    is_positive_price,
    normalize_side,
)


@dataclass(frozen=True)
class AShareBar:
    open: float | None
    is_suspended: bool = False
    up_limit: float | None = None
    down_limit: float | None = None
    data_qualified: bool = False
    limit_regime: Literal["applies", "no_limit"] | None = None


STAMP_TAX_REDUCTION_DATE = date(2023, 8, 28)


def stamp_tax_rate(trade_date: date) -> float:
    """Return the sell-side stamp-tax rate effective on ``trade_date``."""

    if not isinstance(trade_date, date):
        raise TypeError("trade_date must be a date")
    return 0.0005 if trade_date >= STAMP_TAX_REDUCTION_DATE else 0.001


def decide_fill(
    side: str,
    bar: AShareBar,
    *,
    slippage_bps: float = 0.0,
) -> FillDecision:
    """Apply suspension and locked-limit rules to one accepted execution bar."""

    normalized_side = normalize_side(side)
    if bar.data_qualified is not True:
        raise MarketDataError(
            "A-share bar must be explicitly complete and available before execution"
        )
    if type(bar.is_suspended) is not bool:
        raise MarketDataError("is_suspended must be boolean")
    if bar.limit_regime not in {"applies", "no_limit"}:
        raise MarketDataError("A-share bar requires an explicit limit_regime")
    up_limit = _optional_limit(bar.up_limit, "up_limit")
    down_limit = _optional_limit(bar.down_limit, "down_limit")
    if bar.limit_regime == "applies" and (up_limit is None or down_limit is None):
        raise MarketDataError("applicable limit regime requires both limit fields")
    if bar.limit_regime == "no_limit" and (up_limit is not None or down_limit is not None):
        raise MarketDataError("no-limit regime cannot carry limit fields")
    if up_limit is not None and down_limit is not None and down_limit > up_limit:
        raise MarketDataError("down_limit cannot exceed up_limit")
    if bar.is_suspended:
        return FillDecision(False, None, "suspended")
    if not is_positive_price(bar.open):
        raise MarketDataError(
            "qualified non-suspended A-share bar requires a positive finite open"
        )

    execution_price = float(bar.open)
    if up_limit is not None and execution_price > up_limit and not math.isclose(
        execution_price,
        up_limit,
        rel_tol=1e-6,
        abs_tol=0.001,
    ):
        raise MarketDataError("open exceeds the qualified up_limit")
    if down_limit is not None and execution_price < down_limit and not math.isclose(
        execution_price,
        down_limit,
        rel_tol=1e-6,
        abs_tol=0.001,
    ):
        raise MarketDataError("open is below the qualified down_limit")

    if normalized_side == "buy" and up_limit is not None:
        if execution_price > up_limit or math.isclose(
            execution_price,
            up_limit,
            rel_tol=1e-6,
            abs_tol=0.001,
        ):
            return FillDecision(False, None, "limit_up_buy_rejected")
    if normalized_side == "sell" and down_limit is not None:
        if execution_price < down_limit or math.isclose(
            execution_price,
            down_limit,
            rel_tol=1e-6,
            abs_tol=0.001,
        ):
            return FillDecision(False, None, "limit_down_sell_rejected")

    fill_price = apply_slippage(execution_price, normalized_side, slippage_bps)
    if up_limit is not None and fill_price > up_limit and not math.isclose(
        fill_price,
        up_limit,
        rel_tol=1e-6,
        abs_tol=0.001,
    ):
        return FillDecision(False, None, "slippage_crosses_up_limit")
    if down_limit is not None and fill_price < down_limit and not math.isclose(
        fill_price,
        down_limit,
        rel_tol=1e-6,
        abs_tol=0.001,
    ):
        return FillDecision(False, None, "slippage_crosses_down_limit")
    return FillDecision(True, fill_price, "filled")


def require_board_lot(shares: float, *, lot_size: int = 100) -> None:
    if lot_size <= 0:
        raise ValueError("lot_size must be positive")
    if not is_finite_number(shares) or shares <= 0:
        raise ValueError("shares must be positive and finite")
    if not float(shares).is_integer() or int(shares) % lot_size:
        raise ValueError(f"A-share order quantity must be a multiple of {lot_size}")


def _optional_limit(value: float | None, name: str) -> float | None:
    if value is None:
        return None
    if not is_positive_price(value):
        raise MarketDataError(f"{name} must be positive and finite when supplied")
    return float(value)
