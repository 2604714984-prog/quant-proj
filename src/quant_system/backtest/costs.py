"""Deterministic transaction-cost arithmetic."""

from __future__ import annotations

from dataclasses import dataclass

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
