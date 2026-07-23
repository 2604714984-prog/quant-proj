"""Minimal A-share daily execution rules.

Signals are assumed to be formed after close and executed at the next accepted
session open. Share settlement and cash accounting live in the portfolio module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from typing import Literal

from quant_system.data import SourceIdentity, capture_source_bytes, require_trusted_source

from .common import (
    FillDecision,
    MarketDataError,
    apply_slippage,
    is_finite_number,
    is_positive_price,
    normalize_side,
    require_nonempty_text,
)

AdjustmentBasis = Literal["raw", "qfq", "hfq", "total_return"]
_ADJUSTMENT_BASES = frozenset(AdjustmentBasis.__args__)
_A_SHARE_ACTION_TYPES = frozenset(
    {
        "cash_dividend",
        "special_dividend",
        "split",
        "reverse_split",
        "symbol_change",
        "delisting",
    }
)
_ADJUSTMENT_TOKEN = object()


@dataclass(frozen=True)
class AShareAdjustmentReceipt:
    """Parsed adjustment basis and complete action-day observation."""

    subject_id: str
    effective_session: date
    price_basis: AdjustmentBasis
    adjustment_factor: Decimal
    action_types: tuple[str, ...]
    factor_source: SourceIdentity
    action_completeness_source: SourceIdentity
    receipt_sha256: str
    _token: object | None = field(default=None, repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        require_nonempty_text(self.subject_id, "subject_id")
        if type(self.effective_session) is not date:
            raise MarketDataError("effective_session must be a date")
        if self.price_basis not in _ADJUSTMENT_BASES:
            raise MarketDataError("unsupported A-share adjustment basis")
        if (
            type(self.action_types) is not tuple
            or self.action_types != tuple(sorted(set(self.action_types)))
            or set(self.action_types) - _A_SHARE_ACTION_TYPES
        ):
            raise MarketDataError("action_types must be sorted, unique, and supported")
        if self.adjustment_factor <= 0 or not self.adjustment_factor.is_finite():
            raise MarketDataError("adjustment_factor must be positive and finite")
        if self.price_basis == "raw" and self.adjustment_factor != Decimal("1"):
            raise MarketDataError("raw basis requires adjustment_factor=1")
        try:
            require_trusted_source(self.factor_source)
            require_trusted_source(self.action_completeness_source)
        except ValueError as exc:
            raise MarketDataError("adjustment receipt requires trusted source captures") from exc
        expected = hashlib.sha256(_adjustment_payload(self)).hexdigest()
        if self._token is not _ADJUSTMENT_TOKEN or self.receipt_sha256 != expected:
            raise MarketDataError(
                "AShareAdjustmentReceipt must come from capture_a_share_adjustment_receipt"
            )


def _adjustment_payload(receipt: AShareAdjustmentReceipt) -> bytes:
    payload = {
        "action_completeness_source": receipt.action_completeness_source.content_sha256,
        "action_types": receipt.action_types,
        "adjustment_factor": str(receipt.adjustment_factor),
        "effective_session": receipt.effective_session.isoformat(),
        "factor_source": receipt.factor_source.content_sha256,
        "price_basis": receipt.price_basis,
        "subject_id": receipt.subject_id,
        "version": 1,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def capture_a_share_adjustment_receipt(
    *,
    factor_bytes: bytes,
    action_completeness_bytes: bytes,
    publication_evidence: bytes,
    factor_source_url: str,
    action_completeness_source_url: str,
    available_at: datetime,
    retrieved_at: datetime,
    provider_id: str,
) -> AShareAdjustmentReceipt:
    """Parse immutable provider bytes and bind their adjustment/action semantics."""

    try:
        factor_row = json.loads(factor_bytes)
        completeness_row = json.loads(action_completeness_bytes)
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MarketDataError("adjustment inputs must be UTF-8 JSON bytes") from exc
    if not isinstance(factor_row, dict) or not isinstance(completeness_row, dict):
        raise MarketDataError("adjustment inputs must each contain one JSON object")
    required_factor = {"symbol", "session", "price_basis", "adjustment_factor"}
    required_actions = {"symbol", "session", "action_types"}
    if set(factor_row) != required_factor or set(completeness_row) != required_actions:
        raise MarketDataError("adjustment JSON schema mismatch")
    subject = require_nonempty_text(factor_row["symbol"], "symbol")
    if completeness_row["symbol"] != subject or completeness_row["session"] != factor_row["session"]:
        raise MarketDataError("factor and action-completeness identities must match")
    try:
        effective_session = date.fromisoformat(factor_row["session"])
        factor = Decimal(str(factor_row["adjustment_factor"]))
    except (TypeError, ValueError, InvalidOperation) as exc:
        raise MarketDataError("invalid adjustment session or factor") from exc
    actions = completeness_row["action_types"]
    if not isinstance(actions, list) or any(not isinstance(item, str) for item in actions):
        raise MarketDataError("action_types must be a JSON string array")
    action_types = tuple(actions)
    factor_source = capture_source_bytes(
        factor_bytes,
        publication_evidence=publication_evidence,
        source_url=factor_source_url,
        available_at=available_at,
        retrieved_at=retrieved_at,
        revision_id=f"{subject}:{effective_session}:factor",
        source_family_id="a-share-adjustment-factor",
        provider_id=provider_id,
        subject_id=subject,
    ).source
    completeness_source = capture_source_bytes(
        action_completeness_bytes,
        publication_evidence=publication_evidence,
        source_url=action_completeness_source_url,
        available_at=available_at,
        retrieved_at=retrieved_at,
        revision_id=f"{subject}:{effective_session}:action-completeness",
        source_family_id="a-share-action-completeness",
        provider_id=provider_id,
        subject_id=subject,
    ).source
    provisional = object.__new__(AShareAdjustmentReceipt)
    values = {
        "subject_id": subject,
        "effective_session": effective_session,
        "price_basis": factor_row["price_basis"],
        "adjustment_factor": factor,
        "action_types": action_types,
        "factor_source": factor_source,
        "action_completeness_source": completeness_source,
    }
    for name, value in values.items():
        object.__setattr__(provisional, name, value)
    receipt_sha = hashlib.sha256(_adjustment_payload(provisional)).hexdigest()
    return AShareAdjustmentReceipt(
        **values,
        receipt_sha256=receipt_sha,
        _token=_ADJUSTMENT_TOKEN,
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
