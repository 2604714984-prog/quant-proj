"""Pure, outcome-blind contract for the frozen SPY volatility-managed strategy."""

from __future__ import annotations

import math
import re
import statistics
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

INSTRUMENT = "SPY"
REQUIRED_RAW_CLOSES = 22
REQUIRED_LOG_RETURNS = 21
TARGET_ANNUALIZED_VOLATILITY = 0.10
ANNUALIZATION_DAYS = 252
ONE_WAY_SLIPPAGE_BPS = 10
DECISION_HOUR = 20
DECISION_MINUTE = 5

_NEW_YORK = ZoneInfo("America/New_York")
_SHA256 = re.compile(r"[0-9a-f]{64}")


class InputContractError(ValueError):
    """Raised before calculation when a frozen input invariant is not satisfied."""


def _require_date(value: date, field: str) -> None:
    if not isinstance(value, date) or isinstance(value, datetime):
        raise InputContractError(f"{field} must be a date")


def _require_aware(value: datetime, field: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise InputContractError(f"{field} must be timezone-aware")
    if value.utcoffset() is None:
        raise InputContractError(f"{field} must have a valid UTC offset")


def _require_finite(value: float, field: str, *, positive: bool = False) -> float:
    if isinstance(value, bool):
        raise InputContractError(f"{field} must be numeric, not boolean")
    number = float(value)
    if not math.isfinite(number):
        raise InputContractError(f"{field} must be finite")
    if positive and number <= 0.0:
        raise InputContractError(f"{field} must be positive")
    return number


def _require_sha256(value: str, field: str = "source_sha256") -> None:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise InputContractError(f"{field} must be a lowercase SHA-256 hex digest")


def _require_ex_date_open(value: datetime, ex_date: date) -> None:
    _require_aware(value, "information_available_at")
    local = value.astimezone(_NEW_YORK)
    if local.date() != ex_date:
        raise InputContractError("information_available_at must fall on ex_date")
    if (local.hour, local.minute, local.second, local.microsecond) != (9, 30, 0, 0):
        raise InputContractError("information_available_at must equal ex-date XNYS open")


def _require_decision_time(value: datetime) -> datetime:
    _require_aware(value, "decision_at")
    local = value.astimezone(_NEW_YORK)
    if (local.hour, local.minute, local.second, local.microsecond) != (
        DECISION_HOUR,
        DECISION_MINUTE,
        0,
        0,
    ):
        raise InputContractError("decision_at must equal 20:05 America/New_York")
    return local


@dataclass(frozen=True)
class CloseObservation:
    """One accepted raw close and its immutable source identity."""

    session_date: date
    close_at: datetime
    available_at: datetime
    raw_close: float
    source_sha256: str

    def __post_init__(self) -> None:
        _require_date(self.session_date, "session_date")
        _require_aware(self.close_at, "close_at")
        _require_aware(self.available_at, "available_at")
        if self.close_at.astimezone(_NEW_YORK).date() != self.session_date:
            raise InputContractError("close_at must belong to session_date")
        if self.available_at < self.close_at:
            raise InputContractError("raw close cannot be available before the close")
        _require_finite(self.raw_close, "raw_close", positive=True)
        _require_sha256(self.source_sha256)


@dataclass(frozen=True)
class CashDistribution:
    """Official cash distribution; comparison amounts never control calculations."""

    ex_date: date
    record_date: date
    payment_date: date
    information_available_at: datetime
    official_amount: float
    currency: str
    amount_unit: str
    source_sha256: str
    tiingo_comparison_amount: float | None = None

    def __post_init__(self) -> None:
        _require_date(self.ex_date, "ex_date")
        _require_date(self.record_date, "record_date")
        _require_date(self.payment_date, "payment_date")
        if not self.ex_date <= self.record_date <= self.payment_date:
            raise InputContractError("distribution dates must satisfy ex <= record <= payment")
        _require_ex_date_open(self.information_available_at, self.ex_date)
        _require_finite(self.official_amount, "official_amount", positive=True)
        if self.currency != "USD":
            raise InputContractError("distribution currency must equal USD")
        if self.amount_unit != "PER_SHARE":
            raise InputContractError("distribution amount_unit must equal PER_SHARE")
        _require_sha256(self.source_sha256)
        if self.tiingo_comparison_amount is not None:
            comparison = _require_finite(
                self.tiingo_comparison_amount,
                "tiingo_comparison_amount",
            )
            if comparison < 0.0:
                raise InputContractError("tiingo_comparison_amount must be nonnegative")


@dataclass(frozen=True)
class SplitEvent:
    """Official split event applied exactly once on its ex-date."""

    ex_date: date
    information_available_at: datetime
    factor: float
    source_sha256: str

    def __post_init__(self) -> None:
        _require_date(self.ex_date, "ex_date")
        _require_ex_date_open(self.information_available_at, self.ex_date)
        factor = _require_finite(self.factor, "factor", positive=True)
        if factor == 1.0:
            raise InputContractError("a split event must have a non-unit factor")
        _require_sha256(self.source_sha256)


@dataclass(frozen=True)
class RebalanceRequest:
    """Decision-time shares frozen before the next execution open is observed."""

    decision_at: datetime
    target_weight: float
    requested_shares: int
    sizing_price: float
    annualized_volatility: float

    def __post_init__(self) -> None:
        _require_decision_time(self.decision_at)
        weight = _require_finite(self.target_weight, "target_weight", positive=True)
        if weight > 1.0:
            raise InputContractError("target_weight cannot exceed one")
        volatility = _require_finite(
            self.annualized_volatility,
            "annualized_volatility",
            positive=True,
        )
        if not math.isclose(weight, target_weight(volatility), rel_tol=0.0, abs_tol=1e-15):
            raise InputContractError("target_weight must match the frozen volatility formula")
        if not isinstance(self.requested_shares, int) or isinstance(self.requested_shares, bool):
            raise InputContractError("requested_shares must be an integer")
        if self.requested_shares < 0:
            raise InputContractError("requested_shares must be nonnegative")
        _require_finite(self.sizing_price, "sizing_price", positive=True)


@dataclass(frozen=True)
class ExecutionFillObservation:
    """Next-session raw open observed only after requested shares are frozen."""

    execution_session_date: date
    raw_open: float
    requested_shares: int
    source_sha256: str

    def __post_init__(self) -> None:
        _require_date(self.execution_session_date, "execution_session_date")
        _require_finite(self.raw_open, "raw_open", positive=True)
        if not isinstance(self.requested_shares, int) or isinstance(self.requested_shares, bool):
            raise InputContractError("requested_shares must be an integer")
        if self.requested_shares < 0:
            raise InputContractError("requested_shares must be nonnegative")
        _require_sha256(self.source_sha256)


@dataclass(frozen=True)
class DistributionEntitlement:
    """Cash receivable fixed at ex-date and credited only on payment date."""

    ex_date: date
    payment_date: date
    entitled_shares: int
    amount_per_share: float
    total_cash: float
    source_sha256: str

    def __post_init__(self) -> None:
        _require_date(self.ex_date, "ex_date")
        _require_date(self.payment_date, "payment_date")
        if self.payment_date < self.ex_date:
            raise InputContractError("payment_date cannot precede ex_date")
        if not isinstance(self.entitled_shares, int) or isinstance(self.entitled_shares, bool):
            raise InputContractError("entitled_shares must be an integer")
        if self.entitled_shares < 0:
            raise InputContractError("entitled_shares must be nonnegative")
        amount = _require_finite(self.amount_per_share, "amount_per_share", positive=True)
        total = _require_finite(self.total_cash, "total_cash")
        expected = self.entitled_shares * amount
        if total < 0.0 or not math.isclose(total, expected, rel_tol=0.0, abs_tol=1e-12):
            raise InputContractError("total_cash must match shares times amount_per_share")
        _require_sha256(self.source_sha256)


def _action_by_date(
    closes: tuple[CloseObservation, ...],
    distributions: tuple[CashDistribution, ...],
    splits: tuple[SplitEvent, ...],
    decision_at: datetime,
) -> dict[date, CashDistribution | SplitEvent]:
    usable_dates = {observation.session_date for observation in closes[1:]}
    actions: dict[date, CashDistribution | SplitEvent] = {}
    for action in (*distributions, *splits):
        if action.ex_date not in usable_dates:
            raise InputContractError("every action must map to a return-period session")
        if action.ex_date in actions:
            raise InputContractError("multiple ordinary actions on one session fail closed")
        if action.information_available_at > decision_at:
            raise InputContractError("action information was not available by decision_at")
        actions[action.ex_date] = action
    return actions


def total_return_log_returns(
    closes: tuple[CloseObservation, ...],
    *,
    distributions: tuple[CashDistribution, ...] = (),
    splits: tuple[SplitEvent, ...] = (),
    decision_at: datetime,
) -> tuple[float, ...]:
    """Build the exact 21 causal total-return log returns from 22 raw closes."""

    observations = tuple(closes)
    if len(observations) != REQUIRED_RAW_CLOSES:
        raise InputContractError(f"exactly {REQUIRED_RAW_CLOSES} raw closes are required")
    decision_local = _require_decision_time(decision_at)
    dates = tuple(observation.session_date for observation in observations)
    if any(current <= previous for previous, current in zip(dates, dates[1:])):
        raise InputContractError("close session dates must be strictly increasing")
    if dates[-1] != decision_local.date():
        raise InputContractError("latest raw close must be from the decision session")
    if any(observation.available_at > decision_at for observation in observations):
        raise InputContractError("every raw close must be available by decision_at")

    actions = _action_by_date(observations, distributions, splits, decision_at)
    returns: list[float] = []
    for previous, current in zip(observations, observations[1:]):
        action = actions.get(current.session_date)
        split_factor = action.factor if isinstance(action, SplitEvent) else 1.0
        distribution = action.official_amount if isinstance(action, CashDistribution) else 0.0
        gross_return = (split_factor * current.raw_close + distribution) / previous.raw_close
        if not math.isfinite(gross_return) or gross_return <= 0.0:
            raise InputContractError("total-return gross relative must be finite and positive")
        returns.append(math.log(gross_return))
    if len(returns) != REQUIRED_LOG_RETURNS:
        raise InputContractError("return window length drifted from the frozen contract")
    return tuple(returns)


def annualized_realized_volatility(log_returns: tuple[float, ...]) -> float:
    """Frozen ddof=1 sample volatility annualized by sqrt(252)."""

    values = tuple(float(value) for value in log_returns)
    if len(values) != REQUIRED_LOG_RETURNS:
        raise InputContractError(f"exactly {REQUIRED_LOG_RETURNS} log returns are required")
    if not all(math.isfinite(value) for value in values):
        raise InputContractError("log returns must be finite")
    volatility = statistics.stdev(values) * math.sqrt(ANNUALIZATION_DAYS)
    if not math.isfinite(volatility) or volatility <= 0.0:
        raise InputContractError("annualized volatility must be finite and positive")
    return volatility


def target_weight(annualized_volatility: float) -> float:
    """Return the unlevered 10-percent volatility target weight."""

    volatility = _require_finite(
        annualized_volatility,
        "annualized_volatility",
        positive=True,
    )
    return min(1.0, TARGET_ANNUALIZED_VOLATILITY / volatility)


def form_monthly_rebalance(
    nav: float,
    closes: tuple[CloseObservation, ...],
    *,
    distributions: tuple[CashDistribution, ...] = (),
    splits: tuple[SplitEvent, ...] = (),
    decision_at: datetime,
) -> RebalanceRequest:
    """Freeze whole-share demand using only the latest causal decision-time close."""

    account_value = _require_finite(nav, "nav")
    if account_value <= 0.0:
        raise InputContractError("nav must be positive")
    returns = total_return_log_returns(
        closes,
        distributions=distributions,
        splits=splits,
        decision_at=decision_at,
    )
    volatility = annualized_realized_volatility(returns)
    weight = target_weight(volatility)
    sizing_price = float(closes[-1].raw_close)
    requested_shares = math.floor(account_value * weight / sizing_price)
    return RebalanceRequest(
        decision_at=decision_at,
        target_weight=weight,
        requested_shares=requested_shares,
        sizing_price=sizing_price,
        annualized_volatility=volatility,
    )


def observe_execution_fill(
    request: RebalanceRequest,
    *,
    execution_session_date: date,
    raw_open: float,
    source_sha256: str,
) -> ExecutionFillObservation:
    """Record a next-session open without allowing it to resize the request."""

    _require_date(execution_session_date, "execution_session_date")
    if execution_session_date <= request.decision_at.astimezone(_NEW_YORK).date():
        raise InputContractError("execution session must follow the decision session")
    opening_price = _require_finite(raw_open, "raw_open", positive=True)
    _require_sha256(source_sha256)
    return ExecutionFillObservation(
        execution_session_date=execution_session_date,
        raw_open=opening_price,
        requested_shares=request.requested_shares,
        source_sha256=source_sha256,
    )


def distribution_entitlement(
    action: CashDistribution,
    shares_held_before_ex_date_open: int,
) -> DistributionEntitlement:
    """Freeze the receivable using shares held before the ex-date open."""

    if not isinstance(shares_held_before_ex_date_open, int) or isinstance(
        shares_held_before_ex_date_open,
        bool,
    ):
        raise InputContractError("entitled shares must be an integer")
    if shares_held_before_ex_date_open < 0:
        raise InputContractError("entitled shares must be nonnegative")
    total = shares_held_before_ex_date_open * action.official_amount
    return DistributionEntitlement(
        ex_date=action.ex_date,
        payment_date=action.payment_date,
        entitled_shares=shares_held_before_ex_date_open,
        amount_per_share=action.official_amount,
        total_cash=total,
        source_sha256=action.source_sha256,
    )


def cash_credit_on(entitlement: DistributionEntitlement, session_date: date) -> float:
    """Credit the frozen receivable on pay-date only; all other sessions get zero."""

    _require_date(session_date, "session_date")
    if session_date < entitlement.ex_date:
        raise InputContractError("entitlement does not exist before ex-date")
    return entitlement.total_cash if session_date == entitlement.payment_date else 0.0
