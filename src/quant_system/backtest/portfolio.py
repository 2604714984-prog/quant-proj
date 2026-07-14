"""Small long-only portfolio with explicit A-share and US settlement behavior."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from quant_system.markets.a_share import require_board_lot
from quant_system.markets.common import is_finite_number, is_positive_price
from quant_system.markets.us import split_adjustment

from .costs import CostBreakdown, TransactionCostModel


class InsufficientCashError(ValueError):
    pass


class InsufficientSharesError(ValueError):
    pass


@dataclass
class Position:
    shares: float = 0.0
    sellable_shares: float = 0.0
    average_cost: float = 0.0
    last_accepted_mark: float | None = None


@dataclass(frozen=True)
class PendingCash:
    settlement_date: date
    amount: float


@dataclass(frozen=True)
class Trade:
    symbol: str
    side: str
    trade_date: date
    shares: float
    price: float
    gross_amount: float
    costs: CostBreakdown
    cash_change: float
    realized_pnl: float | None = None


class Portfolio:
    def __init__(
        self,
        initial_cash: float,
        costs: TransactionCostModel,
        *,
        lot_size: int = 1,
        share_t_plus_one: bool = False,
        cash_t_plus_one: bool = False,
    ) -> None:
        if not is_finite_number(initial_cash) or initial_cash < 0.0:
            raise ValueError("initial_cash must be finite and nonnegative")
        if lot_size <= 0:
            raise ValueError("lot_size must be positive")
        self.settled_cash = float(initial_cash)
        self.costs = costs
        self.lot_size = lot_size
        self.share_t_plus_one = share_t_plus_one
        self.cash_t_plus_one = cash_t_plus_one
        self.positions: dict[str, Position] = {}
        self.pending_cash: list[PendingCash] = []
        self.current_session: date | None = None

    @classmethod
    def a_share(
        cls,
        initial_cash: float,
        *,
        costs: TransactionCostModel | None = None,
    ) -> "Portfolio":
        return cls(
            initial_cash,
            costs
            or TransactionCostModel(
                commission_rate=0.0003,
                minimum_commission=5.0,
                sell_tax_rate=0.001,
            ),
            lot_size=100,
            share_t_plus_one=True,
            cash_t_plus_one=False,
        )

    @classmethod
    def us(
        cls,
        initial_cash: float,
        *,
        costs: TransactionCostModel | None = None,
    ) -> "Portfolio":
        return cls(
            initial_cash,
            costs or TransactionCostModel(),
            lot_size=1,
            share_t_plus_one=False,
            cash_t_plus_one=True,
        )

    @property
    def available_cash(self) -> float:
        return self.settled_cash

    @property
    def pending_cash_total(self) -> float:
        return sum(item.amount for item in self.pending_cash)

    def start_session(self, as_of: date) -> None:
        if self.current_session is not None and as_of < self.current_session:
            raise ValueError("sessions must be processed chronologically")
        new_session = self.current_session is None or as_of > self.current_session
        self._settle_cash(as_of)
        if new_session and self.share_t_plus_one:
            for position in self.positions.values():
                position.sellable_shares = position.shares
        self.current_session = as_of

    def buy(
        self,
        symbol: str,
        shares: float,
        price: float,
        trade_date: date,
    ) -> Trade:
        self._require_current_session(trade_date)
        self._require_quantity(shares)
        self._require_price(price)
        gross = shares * price
        costs = self.costs.calculate("buy", gross)
        total_cash = gross + costs.total
        if total_cash > self.settled_cash + 1e-9:
            raise InsufficientCashError("buy requires more settled cash than is available")

        self.settled_cash -= total_cash
        position = self.positions.setdefault(symbol, Position())
        old_cost_basis = position.average_cost * position.shares
        position.shares += shares
        position.average_cost = (old_cost_basis + total_cash) / position.shares
        if not self.share_t_plus_one:
            position.sellable_shares += shares
        position.last_accepted_mark = price
        return Trade(
            symbol,
            "buy",
            trade_date,
            shares,
            price,
            gross,
            costs,
            -total_cash,
        )

    def sell(
        self,
        symbol: str,
        shares: float,
        price: float,
        trade_date: date,
        *,
        settlement_date: date | None = None,
    ) -> Trade:
        self._require_current_session(trade_date)
        self._require_quantity(shares)
        self._require_price(price)
        position = self.positions.get(symbol)
        if position is None or shares > position.sellable_shares + 1e-9:
            raise InsufficientSharesError("sell quantity exceeds currently sellable shares")
        if self.cash_t_plus_one and (
            settlement_date is None or settlement_date <= trade_date
        ):
            raise ValueError("US sale requires an explicit later settlement_date")

        gross = shares * price
        costs = self.costs.calculate("sell", gross)
        proceeds = gross - costs.total
        if proceeds < 0.0:
            raise ValueError("transaction costs exceed sale proceeds")
        realized_pnl = proceeds - position.average_cost * shares
        position.shares -= shares
        position.sellable_shares -= shares
        position.last_accepted_mark = price
        if position.shares <= 1e-9:
            del self.positions[symbol]

        if self.cash_t_plus_one:
            assert settlement_date is not None
            self.pending_cash.append(PendingCash(settlement_date, proceeds))
        else:
            self.settled_cash += proceeds
        return Trade(
            symbol,
            "sell",
            trade_date,
            shares,
            price,
            gross,
            costs,
            proceeds,
            realized_pnl,
        )

    def apply_split(self, symbol: str, ratio: float) -> None:
        position = self.positions.get(symbol)
        if position is None:
            return
        position.shares, position.average_cost = split_adjustment(
            position.shares,
            position.average_cost,
            ratio,
        )
        position.sellable_shares *= ratio
        if position.last_accepted_mark is not None:
            position.last_accepted_mark /= ratio

    def credit_cash(self, amount: float) -> None:
        if not is_finite_number(amount) or amount < 0.0:
            raise ValueError("cash credit must be finite and nonnegative")
        self.settled_cash += amount

    def nav(self, marks: dict[str, float]) -> float:
        market_value = 0.0
        for symbol, position in self.positions.items():
            mark = marks.get(symbol)
            if not is_finite_number(mark) or float(mark) < 0.0:
                raise ValueError(f"missing or invalid accepted mark for {symbol}")
            position.last_accepted_mark = float(mark)
            market_value += position.shares * float(mark)
        return self.settled_cash + self.pending_cash_total + market_value

    def _settle_cash(self, as_of: date) -> None:
        remaining: list[PendingCash] = []
        for item in self.pending_cash:
            if item.settlement_date <= as_of:
                self.settled_cash += item.amount
            else:
                remaining.append(item)
        self.pending_cash = remaining

    def _require_current_session(self, trade_date: date) -> None:
        if self.current_session != trade_date:
            raise ValueError("start_session must be called for the trade date")

    def _require_quantity(self, shares: float) -> None:
        if not is_finite_number(shares) or shares <= 0.0:
            raise ValueError("shares must be positive and finite")
        if self.lot_size == 100:
            require_board_lot(shares, lot_size=self.lot_size)
        elif not float(shares).is_integer() or int(shares) % self.lot_size:
            raise ValueError(f"shares must be an integer multiple of {self.lot_size}")

    @staticmethod
    def _require_price(price: float) -> None:
        if not is_positive_price(price):
            raise ValueError("price must be positive and finite")
