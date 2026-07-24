"""Small removable adapter for aggregate Form 4 purchase-breadth timing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
import math
import statistics
from zoneinfo import ZoneInfo

from quant_system.backtest import (
    ExecutionInput,
    Portfolio,
    StaticRebalanceResult,
    run_static_rebalance,
)
from quant_system.data import AcceptedSessionCalendar
from quant_system.markets.universe import UniverseSnapshotIdentity


RESEARCH_ID = "US_EQ_FORM4_AGGREGATE_PURCHASE_BREADTH_V1"
EXPECTED_INCLUSION_RULE_SHA256 = (
    "7e5f43b7d0dc6e5a18f19317e21d94bba456ffd87b1b91c87a7a7f1c70512af3"
)
INITIAL_CAPITAL = 40_000.0
ONE_WAY_COMMISSION_RATE = 0.001
VALIDATION_MONTHS = 46
SECONDARY_MONTHS = 53
MINIMUM_STATE_MONTHS = 12
NY = ZoneInfo("America/New_York")


class InputContractError(ValueError):
    """Raised when an input violates the frozen research contract."""


@dataclass(frozen=True)
class SignalRow:
    month: str
    purchases: int
    sales: int

    def __post_init__(self) -> None:
        _month_tuple(self.month)
        for name, value in (("purchases", self.purchases), ("sales", self.sales)):
            if type(value) is not int or value < 0:
                raise InputContractError(f"{name} must be a nonnegative integer")
        if self.purchases + self.sales == 0:
            raise InputContractError("purchases + sales must be positive")

    @property
    def breadth(self) -> float:
        return (self.purchases - self.sales) / (self.purchases + self.sales)


@dataclass(frozen=True)
class Distribution:
    event_id: str
    ex_date: date
    pay_date: date
    amount_per_share: float

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise InputContractError("distribution event_id is required")
        if type(self.ex_date) is not date or type(self.pay_date) is not date:
            raise InputContractError("distribution dates must be dates")
        if self.pay_date < self.ex_date:
            raise InputContractError("distribution pay_date cannot precede ex_date")
        if (
            isinstance(self.amount_per_share, bool)
            or not isinstance(self.amount_per_share, (int, float))
            or not math.isfinite(self.amount_per_share)
            or self.amount_per_share <= 0
        ):
            raise InputContractError("distribution amount must be finite and positive")


@dataclass(frozen=True)
class Performance:
    terminal_wealth: float
    arithmetic_mean_return: float
    maximum_drawdown: float


@dataclass(frozen=True)
class SegmentDecision:
    observed_months: int
    risk_on_months: int
    cash_months: int
    strategy: Performance
    fifty_fifty: Performance
    spy_buyhold: Performance
    gates: tuple[tuple[str, bool], ...]
    all_gates_pass: bool


def _month_tuple(value: str) -> tuple[int, int]:
    if type(value) is not str or len(value) != 7 or value[4] != "-":
        raise InputContractError("month must use YYYY-MM")
    try:
        year, month = int(value[:4]), int(value[5:])
    except ValueError as exc:
        raise InputContractError("month must use YYYY-MM") from exc
    if not 1 <= month <= 12 or value != f"{year:04d}-{month:02d}":
        raise InputContractError("month must use canonical YYYY-MM")
    return year, month


def _next_month(value: str) -> str:
    year, month = _month_tuple(value)
    if month == 12:
        return f"{year + 1:04d}-01"
    return f"{year:04d}-{month + 1:02d}"


def risk_states(rows: tuple[SignalRow, ...]) -> dict[str, bool]:
    """Return risk-on iff current breadth strictly exceeds the prior-12 median."""

    if type(rows) is not tuple or len(rows) < 13:
        raise InputContractError("at least 13 monthly signal rows are required")
    months = tuple(row.month for row in rows)
    if len(set(months)) != len(months):
        raise InputContractError("signal months must be unique")
    if any(_next_month(left) != right for left, right in zip(months, months[1:])):
        raise InputContractError("signal months must be consecutive")
    states: dict[str, bool] = {}
    for index in range(12, len(rows)):
        prior = tuple(row.breadth for row in rows[index - 12 : index])
        states[rows[index].month] = rows[index].breadth > statistics.median(prior)
    return states


def rebalance(
    portfolio: Portfolio,
    calendar: AcceptedSessionCalendar,
    *,
    signal_session: date,
    decision_at: datetime,
    execution_inputs: tuple[ExecutionInput, ...],
    universe_snapshot: UniverseSnapshotIdentity,
    risk_on: bool,
    strategy_definition_sha256: str,
    strategy_adapter_sha256: str,
    prior_stage_hash: str,
) -> StaticRebalanceResult:
    """Run one SPY/cash rebalance through the shared event loop."""

    if type(risk_on) is not bool:
        raise InputContractError("risk_on must be boolean")
    return rebalance_to_spy_weight(
        portfolio,
        calendar,
        signal_session=signal_session,
        decision_at=decision_at,
        execution_inputs=execution_inputs,
        universe_snapshot=universe_snapshot,
        spy_weight=1.0 if risk_on else 0.0,
        strategy_definition_sha256=strategy_definition_sha256,
        strategy_adapter_sha256=strategy_adapter_sha256,
        prior_stage_hash=prior_stage_hash,
    )


def rebalance_to_spy_weight(
    portfolio: Portfolio,
    calendar: AcceptedSessionCalendar,
    *,
    signal_session: date,
    decision_at: datetime,
    execution_inputs: tuple[ExecutionInput, ...],
    universe_snapshot: UniverseSnapshotIdentity,
    spy_weight: float,
    strategy_definition_sha256: str,
    strategy_adapter_sha256: str,
    prior_stage_hash: str,
) -> StaticRebalanceResult:
    """Rebalance SPY to the frozen strategy or comparator weight."""

    if type(spy_weight) is not float or spy_weight not in {0.0, 0.5, 1.0}:
        raise InputContractError("SPY weight must be exactly 0.0, 0.5, or 1.0")
    if (
        calendar.exchange_id != "XNYS"
        or calendar.exchange_timezone != "America/New_York"
    ):
        raise InputContractError("calendar must be the frozen XNYS identity")
    if type(signal_session) is not date:
        raise InputContractError("signal_session must be a date")
    if (
        type(decision_at) is not datetime
        or decision_at.tzinfo is None
        or decision_at.utcoffset() is None
    ):
        raise InputContractError("decision_at must be timezone-aware")
    execution = calendar.next_session(signal_session, as_of=decision_at)
    if execution.session_date.strftime("%Y-%m") != _next_month(
        signal_session.strftime("%Y-%m")
    ):
        raise InputContractError(
            "execution must be the first accepted XNYS session after month end"
        )
    expected_decision = datetime.combine(
        execution.session_date,
        time(8, 30),
        NY,
    )
    if decision_at.astimezone(NY) != expected_decision:
        raise InputContractError("decision_at must be exactly 08:30 America/New_York")
    if universe_snapshot.inclusion_rule_sha256 != EXPECTED_INCLUSION_RULE_SHA256:
        raise InputContractError("universe inclusion-rule identity mismatch")
    costs = portfolio.costs
    if (
        costs.commission_rate != ONE_WAY_COMMISSION_RATE
        or costs.minimum_commission != 0.0
        or costs.sell_tax_rate != 0.0
    ):
        raise InputContractError("portfolio must use exactly 10 bps one-way commission")
    return run_static_rebalance(
        portfolio,
        calendar,
        signal_session=signal_session,
        decision_at=decision_at,
        execution_inputs=execution_inputs,
        universe_members=("SPY",),
        universe_snapshot=universe_snapshot,
        target_weights=lambda _: {"SPY": spy_weight} if spy_weight else {},
        strategy_definition_sha256=strategy_definition_sha256,
        strategy_adapter_sha256=strategy_adapter_sha256,
        max_positions=1,
        slippage_bps=0.0,
        prior_stage_hash=prior_stage_hash,
    )


def apply_distribution(portfolio: Portfolio, event: Distribution) -> float:
    """Freeze entitlement on ex-date; Portfolio settles it on pay date."""

    if not isinstance(portfolio, Portfolio) or not isinstance(event, Distribution):
        raise TypeError("portfolio and event have invalid types")
    portfolio.start_session(event.ex_date)
    return portfolio.apply_cash_distribution(
        "SPY",
        event_id=event.event_id,
        amount_per_share=event.amount_per_share,
        ex_date=event.ex_date,
        pay_date=event.pay_date,
    )


def _performance(nav: tuple[float, ...], expected_months: int) -> Performance:
    if type(nav) is not tuple or len(nav) != expected_months + 1:
        raise InputContractError("NAV path length must equal observed months + 1")
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float))
        for value in nav
    ):
        raise InputContractError("NAV values must be real numbers")
    normalized = tuple(float(value) for value in nav)
    if any(not math.isfinite(value) or value <= 0 for value in normalized):
        raise InputContractError("NAV values must be finite and positive")
    returns = tuple(
        following / current - 1.0
        for current, following in zip(normalized, normalized[1:])
    )
    peak = normalized[0]
    drawdown = 0.0
    for value in normalized:
        peak = max(peak, value)
        drawdown = min(drawdown, value / peak - 1.0)
    return Performance(normalized[-1], statistics.fmean(returns), drawdown)


def adjudicate(
    *,
    strategy_nav: tuple[float, ...],
    fifty_fifty_nav: tuple[float, ...],
    spy_buyhold_nav: tuple[float, ...],
    states: tuple[bool, ...],
    expected_months: int,
) -> SegmentDecision:
    """Apply the five frozen mechanical gates to one completed segment."""

    if expected_months not in {VALIDATION_MONTHS, SECONDARY_MONTHS}:
        raise InputContractError("unexpected segment length")
    if type(states) is not tuple or len(states) != expected_months:
        raise InputContractError("state count must match the frozen segment")
    if any(type(value) is not bool for value in states):
        raise InputContractError("states must be booleans")
    risk_on = sum(states)
    cash = len(states) - risk_on
    strategy = _performance(strategy_nav, expected_months)
    fifty_fifty = _performance(fifty_fifty_nav, expected_months)
    spy = _performance(spy_buyhold_nav, expected_months)
    gates = (
        ("exact_month_count", len(states) == expected_months),
        ("minimum_12_risk_on_months", risk_on >= MINIMUM_STATE_MONTHS),
        ("minimum_12_cash_months", cash >= MINIMUM_STATE_MONTHS),
        (
            "terminal_wealth_above_monthly_50_50",
            strategy.terminal_wealth > fifty_fifty.terminal_wealth,
        ),
        (
            "mean_monthly_return_above_monthly_50_50",
            strategy.arithmetic_mean_return > fifty_fifty.arithmetic_mean_return,
        ),
        (
            "maximum_drawdown_no_worse_than_spy_buyhold",
            strategy.maximum_drawdown >= spy.maximum_drawdown,
        ),
    )
    return SegmentDecision(
        expected_months,
        risk_on,
        cash,
        strategy,
        fifty_fifty,
        spy,
        gates,
        all(passed for _, passed in gates),
    )


def require_secondary_unsealed(validation: SegmentDecision) -> None:
    if not isinstance(validation, SegmentDecision) or not validation.all_gates_pass:
        raise InputContractError("secondary remains sealed unless validation passes")


__all__ = [
    "Distribution",
    "EXPECTED_INCLUSION_RULE_SHA256",
    "INITIAL_CAPITAL",
    "InputContractError",
    "MINIMUM_STATE_MONTHS",
    "ONE_WAY_COMMISSION_RATE",
    "Performance",
    "RESEARCH_ID",
    "SECONDARY_MONTHS",
    "SegmentDecision",
    "SignalRow",
    "VALIDATION_MONTHS",
    "adjudicate",
    "apply_distribution",
    "rebalance",
    "rebalance_to_spy_weight",
    "require_secondary_unsealed",
    "risk_states",
]
