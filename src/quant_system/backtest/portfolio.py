"""Small long-only portfolio with explicit A-share and US settlement behavior."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from quant_system.markets.a_share import require_board_lot, stamp_tax_rate
from quant_system.markets.common import is_finite_number, is_positive_price
from quant_system.markets.us import require_accepted_settlement_sessions, split_adjustment

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
    corporate_action_odd_lot: bool = False


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
        us_cash_settlement: bool = False,
        a_share_stamp_tax_schedule: bool = False,
    ) -> None:
        if not is_finite_number(initial_cash) or initial_cash < 0.0:
            raise ValueError("initial_cash must be finite and nonnegative")
        if lot_size <= 0:
            raise ValueError("lot_size must be positive")
        self.settled_cash = float(initial_cash)
        self.costs = costs
        self.lot_size = lot_size
        self.share_t_plus_one = share_t_plus_one
        self.us_cash_settlement = us_cash_settlement
        self.a_share_stamp_tax_schedule = a_share_stamp_tax_schedule
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
            ),
            lot_size=100,
            share_t_plus_one=True,
            us_cash_settlement=False,
            a_share_stamp_tax_schedule=True,
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
            us_cash_settlement=True,
        )

    @property
    def available_cash(self) -> float:
        return self.settled_cash

    @property
    def pending_cash_total(self) -> float:
        total = 0.0
        for item in self.pending_cash:
            if not is_finite_number(item.amount) or item.amount < 0.0:
                raise ValueError("pending cash must be finite and nonnegative")
            total = self._finite_result(total + item.amount, "pending cash total")
        return total

    def start_session(self, as_of: date) -> None:
        if self.current_session is not None and as_of < self.current_session:
            raise ValueError("sessions must be processed chronologically")
        new_session = self.current_session is None or as_of > self.current_session
        if new_session and self.share_t_plus_one:
            for position in self.positions.values():
                self._validate_position(position)
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
        gross = self._finite_result(shares * price, "buy gross amount")
        costs = self._calculate_costs("buy", gross, trade_date)
        cost_total = self._cost_total(costs)
        total_cash = self._finite_result(gross + cost_total, "buy total cash")
        if total_cash > self.settled_cash + 1e-9:
            raise InsufficientCashError("buy requires more settled cash than is available")

        new_cash = self._finite_result(self.settled_cash - total_cash, "settled cash")
        if new_cash < -1e-9:
            raise InsufficientCashError("buy requires more settled cash than is available")
        new_cash = max(new_cash, 0.0)
        position = self.positions.get(symbol) or Position()
        self._validate_position(position)
        old_cost_basis = self._finite_result(
            position.average_cost * position.shares,
            "existing position cost basis",
        )
        new_shares = self._finite_result(position.shares + shares, "position shares")
        new_average_cost = self._finite_result(
            (old_cost_basis + total_cash) / new_shares,
            "position average cost",
        )
        new_sellable = position.sellable_shares
        if not self.share_t_plus_one:
            new_sellable = self._finite_result(
                new_sellable + shares,
                "sellable shares",
            )

        self.settled_cash = new_cash
        position.shares = new_shares
        position.average_cost = new_average_cost
        position.sellable_shares = new_sellable
        position.last_accepted_mark = float(price)
        self.positions[symbol] = position
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
        accepted_settlement_sessions: tuple[date, ...] | None = None,
    ) -> Trade:
        self._require_current_session(trade_date)
        self._require_integer_quantity(shares)
        self._require_price(price)
        position = self.positions.get(symbol)
        if position is None or shares > position.sellable_shares + 1e-9:
            raise InsufficientSharesError("sell quantity exceeds currently sellable shares")
        self._validate_position(position)
        self._require_sell_lot(shares, position)
        if self.us_cash_settlement:
            if settlement_date is None or settlement_date <= trade_date:
                raise ValueError("US sale requires an explicit later settlement_date")
            if accepted_settlement_sessions is None:
                raise ValueError("US sale requires accepted_settlement_sessions")
            require_accepted_settlement_sessions(
                trade_date,
                settlement_date,
                accepted_settlement_sessions,
            )

        gross = self._finite_result(shares * price, "sell gross amount")
        costs = self._calculate_costs("sell", gross, trade_date)
        cost_total = self._cost_total(costs)
        proceeds = self._finite_result(gross - cost_total, "sale proceeds")
        if proceeds < 0.0:
            raise ValueError("transaction costs exceed sale proceeds")
        realized_pnl = self._finite_result(
            proceeds - position.average_cost * shares,
            "realized PnL",
        )
        new_shares = self._finite_result(position.shares - shares, "position shares")
        new_sellable = self._finite_result(
            position.sellable_shares - shares,
            "sellable shares",
        )
        if new_shares < -1e-9 or new_sellable < -1e-9:
            raise InsufficientSharesError("sell quantity exceeds currently sellable shares")
        new_shares = max(new_shares, 0.0)
        new_sellable = max(new_sellable, 0.0)
        new_settled_cash = self.settled_cash
        if self.us_cash_settlement:
            self._finite_result(
                self.pending_cash_total + proceeds,
                "pending cash total after sale",
            )
        else:
            new_settled_cash = self._finite_result(
                self.settled_cash + proceeds,
                "settled cash",
            )

        position.shares = new_shares
        position.sellable_shares = new_sellable
        position.last_accepted_mark = float(price)
        if new_shares <= 1e-9:
            del self.positions[symbol]

        if self.us_cash_settlement:
            assert settlement_date is not None
            self.pending_cash.append(PendingCash(settlement_date, proceeds))
        else:
            self.settled_cash = new_settled_cash
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
        self._validate_position(position)
        adjusted_shares, adjusted_average_cost = split_adjustment(
            position.shares,
            position.average_cost,
            ratio,
        )
        adjusted_sellable = self._finite_result(
            position.sellable_shares * ratio,
            "split-adjusted sellable shares",
        )
        adjusted_mark = position.last_accepted_mark
        if position.last_accepted_mark is not None:
            adjusted_mark = self._finite_result(
                position.last_accepted_mark / ratio,
                "split-adjusted mark",
            )
        adjusted_odd_lot = position.corporate_action_odd_lot
        if self.lot_size == 100:
            if not adjusted_shares.is_integer() or not adjusted_sellable.is_integer():
                raise ValueError("A-share split must resolve to whole-share quantities")
            adjusted_odd_lot = int(adjusted_shares) % self.lot_size != 0

        position.shares = adjusted_shares
        position.average_cost = adjusted_average_cost
        position.sellable_shares = adjusted_sellable
        position.last_accepted_mark = adjusted_mark
        position.corporate_action_odd_lot = adjusted_odd_lot

    def credit_cash(self, amount: float) -> None:
        if not is_finite_number(amount) or amount < 0.0:
            raise ValueError("cash credit must be finite and nonnegative")
        new_cash = self._finite_result(self.settled_cash + amount, "settled cash")
        self.settled_cash = new_cash

    def nav(self, marks: dict[str, float]) -> float:
        market_value = 0.0
        accepted_marks: dict[str, float] = {}
        for symbol, position in self.positions.items():
            self._validate_position(position)
            mark = marks.get(symbol)
            if not is_positive_price(mark):
                raise ValueError(f"missing or invalid accepted mark for {symbol}")
            accepted_mark = float(mark)
            position_value = self._finite_result(
                position.shares * accepted_mark,
                f"market value for {symbol}",
            )
            market_value = self._finite_result(
                market_value + position_value,
                "portfolio market value",
            )
            accepted_marks[symbol] = accepted_mark
        total = self._finite_result(
            self.settled_cash + self.pending_cash_total,
            "portfolio cash value",
        )
        total = self._finite_result(total + market_value, "portfolio NAV")
        for symbol, mark in accepted_marks.items():
            self.positions[symbol].last_accepted_mark = mark
        return total

    def _settle_cash(self, as_of: date) -> None:
        remaining: list[PendingCash] = []
        settled_amount = 0.0
        for item in self.pending_cash:
            if not is_finite_number(item.amount) or item.amount < 0.0:
                raise ValueError("pending cash must be finite and nonnegative")
            if item.settlement_date <= as_of:
                settled_amount = self._finite_result(
                    settled_amount + item.amount,
                    "cash settling this session",
                )
            else:
                remaining.append(item)
        new_cash = self._finite_result(
            self.settled_cash + settled_amount,
            "settled cash",
        )
        self.settled_cash = new_cash
        self.pending_cash = remaining

    def _calculate_costs(
        self,
        side: str,
        gross: float,
        trade_date: date,
    ) -> CostBreakdown:
        model = self.costs
        if self.a_share_stamp_tax_schedule:
            model = TransactionCostModel(
                commission_rate=self.costs.commission_rate,
                minimum_commission=self.costs.minimum_commission,
                sell_tax_rate=stamp_tax_rate(trade_date),
            )
        costs = model.calculate(side, gross)
        self._cost_total(costs)
        return costs

    @staticmethod
    def _cost_total(costs: CostBreakdown) -> float:
        if not is_finite_number(costs.commission) or costs.commission < 0.0:
            raise ValueError("commission must be finite and nonnegative")
        if not is_finite_number(costs.sell_tax) or costs.sell_tax < 0.0:
            raise ValueError("sell tax must be finite and nonnegative")
        return Portfolio._finite_result(costs.total, "transaction costs")

    @staticmethod
    def _validate_position(position: Position) -> None:
        for label, value in (
            ("position shares", position.shares),
            ("sellable shares", position.sellable_shares),
            ("position average cost", position.average_cost),
        ):
            if not is_finite_number(value) or value < 0.0:
                raise ValueError(f"{label} must be finite and nonnegative")
        if position.sellable_shares > position.shares + 1e-9:
            raise ValueError("sellable shares cannot exceed position shares")
        if position.last_accepted_mark is not None and not is_positive_price(
            position.last_accepted_mark
        ):
            raise ValueError("last accepted mark must be positive and finite")
        if type(position.corporate_action_odd_lot) is not bool:
            raise ValueError("corporate_action_odd_lot must be boolean")

    @staticmethod
    def _finite_result(value: float, label: str) -> float:
        if not is_finite_number(value):
            raise ValueError(f"{label} must be finite")
        return float(value)

    def _require_current_session(self, trade_date: date) -> None:
        if self.current_session != trade_date:
            raise ValueError("start_session must be called for the trade date")

    def _require_quantity(self, shares: float) -> None:
        self._require_integer_quantity(shares)
        if self.lot_size == 100:
            require_board_lot(shares, lot_size=self.lot_size)
        elif int(shares) % self.lot_size:
            raise ValueError(f"shares must be an integer multiple of {self.lot_size}")

    @staticmethod
    def _require_integer_quantity(shares: float) -> None:
        if not is_finite_number(shares) or shares <= 0.0:
            raise ValueError("shares must be positive and finite")
        if not float(shares).is_integer():
            raise ValueError("shares must be a whole-share quantity")

    def _require_sell_lot(self, shares: float, position: Position) -> None:
        if int(shares) % self.lot_size == 0:
            return
        full_odd_lot_liquidation = (
            self.lot_size == 100
            and position.corporate_action_odd_lot
            and shares == position.shares
            and shares == position.sellable_shares
        )
        if not full_odd_lot_liquidation:
            raise ValueError(
                "A-share odd-lot sale must fully liquidate a corporate-action remainder"
            )

    @staticmethod
    def _require_price(price: float) -> None:
        if not is_positive_price(price):
            raise ValueError("price must be positive and finite")
