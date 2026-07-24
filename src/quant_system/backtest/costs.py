"""Deterministic transaction-cost arithmetic."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from .capacity import CapacityPolicy

from quant_system.markets.common import is_finite_number, normalize_side


@dataclass(frozen=True)
class CostBreakdown:
    commission: float
    sell_tax: float

    @property
    def total(self) -> float:
        return self.commission + self.sell_tax


@dataclass(frozen=True)
class TransactionCostModel:
    commission_rate: float = 0.0
    minimum_commission: float = 0.0
    sell_tax_rate: float = 0.0

    def __post_init__(self) -> None:
        for name, value in (
            ("commission_rate", self.commission_rate),
            ("minimum_commission", self.minimum_commission),
            ("sell_tax_rate", self.sell_tax_rate),
        ):
            if not is_finite_number(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and nonnegative")

    def calculate(self, side: str, gross_amount: float) -> CostBreakdown:
        normalized_side = normalize_side(side)
        if not is_finite_number(gross_amount) or gross_amount < 0.0:
            raise ValueError("gross_amount must be finite and nonnegative")
        if gross_amount == 0.0:
            return CostBreakdown(0.0, 0.0)
        commission = max(
            gross_amount * self.commission_rate,
            self.minimum_commission,
        )
        sell_tax = (
            gross_amount * self.sell_tax_rate if normalized_side == "sell" else 0.0
        )
        if not is_finite_number(commission) or commission < 0.0:
            raise ValueError("calculated commission must be finite and nonnegative")
        if not is_finite_number(sell_tax) or sell_tax < 0.0:
            raise ValueError("calculated sell tax must be finite and nonnegative")
        if not is_finite_number(commission + sell_tax):
            raise ValueError("calculated transaction cost total must be finite")
        return CostBreakdown(commission, sell_tax)


@dataclass(frozen=True)
class CostStressCase:
    commission_rate: float
    minimum_commission: float
    bid_ask_spread_bps: float
    market_impact_bps: float
    regulatory_fee_rate: float
    fx_to_base: float

    def __post_init__(self) -> None:
        for name in (
            "commission_rate",
            "minimum_commission",
            "bid_ask_spread_bps",
            "market_impact_bps",
            "regulatory_fee_rate",
        ):
            value = getattr(self, name)
            if not is_finite_number(value) or value < 0:
                raise ValueError(f"{name} must be finite and nonnegative")
        if not is_finite_number(self.fx_to_base) or self.fx_to_base <= 0:
            raise ValueError("fx_to_base must be finite and positive")

    @property
    def slippage_bps(self) -> float:
        return self.bid_ask_spread_bps / 2 + self.market_impact_bps

    def transaction_cost_model(self) -> TransactionCostModel:
        return TransactionCostModel(
            commission_rate=self.commission_rate,
            minimum_commission=self.minimum_commission,
            sell_tax_rate=self.regulatory_fee_rate,
        )

    @property
    def total_rate_proxy(self) -> float:
        return (
            self.commission_rate
            + self.regulatory_fee_rate
            + self.bid_ask_spread_bps / 10_000
            + self.market_impact_bps / 10_000
        )


@dataclass(frozen=True)
class ExecutionCostAssumptions:
    """Versioned base/adverse costs, capacity, currency, and FX assumptions."""

    version: str
    currency: str
    capacity_policy: CapacityPolicy
    base: CostStressCase
    adverse: CostStressCase
    gross_only: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.version, str) or not self.version.strip():
            raise ValueError("cost assumption version must be nonempty")
        if (
            not isinstance(self.currency, str)
            or len(self.currency) != 3
            or not self.currency.isalpha()
            or not self.currency.isupper()
        ):
            raise ValueError("currency must be a three-letter uppercase code")
        if not isinstance(self.capacity_policy, CapacityPolicy):
            raise TypeError("capacity_policy must be a CapacityPolicy")
        if self.capacity_policy.currency != self.currency:
            raise ValueError("capacity and cost assumption currencies must match")
        if not isinstance(self.base, CostStressCase) or not isinstance(
            self.adverse,
            CostStressCase,
        ):
            raise TypeError("base and adverse must be CostStressCase values")
        if type(self.gross_only) is not bool:
            raise TypeError("gross_only must be boolean")
        if self.gross_only:
            if self.base.total_rate_proxy or self.adverse.total_rate_proxy:
                raise ValueError("gross_only assumptions must contain zero transaction costs")
        elif self.base.total_rate_proxy <= 0:
            raise ValueError("zero costs require gross_only=true")
        if self.adverse.total_rate_proxy < self.base.total_rate_proxy:
            raise ValueError("adverse cost case cannot be cheaper than base")

    @property
    def canonical_payload_json(self) -> str:
        payload = {
            "adverse": self.adverse.__dict__,
            "base": self.base.__dict__,
            "capacity_policy": self.capacity_policy.__dict__,
            "currency": self.currency,
            "gross_only": self.gross_only,
            "version": self.version,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @property
    def identity_sha256(self) -> str:
        return hashlib.sha256(self.canonical_payload_json.encode()).hexdigest()

    @classmethod
    def from_canonical_payload_json(cls, payload_json: str) -> "ExecutionCostAssumptions":
        try:
            payload = json.loads(payload_json)
            if (
                type(payload) is not dict
                or set(payload)
                != {
                    "adverse",
                    "base",
                    "capacity_policy",
                    "currency",
                    "gross_only",
                    "version",
                }
            ):
                raise ValueError
            assumptions = cls(
                version=payload["version"],
                currency=payload["currency"],
                capacity_policy=CapacityPolicy(**payload["capacity_policy"]),
                base=CostStressCase(**payload["base"]),
                adverse=CostStressCase(**payload["adverse"]),
                gross_only=payload["gross_only"],
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("cost assumptions payload is invalid") from exc
        if assumptions.canonical_payload_json != payload_json:
            raise ValueError("cost assumptions payload is not canonical")
        return assumptions
