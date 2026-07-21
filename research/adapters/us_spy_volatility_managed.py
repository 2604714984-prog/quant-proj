"""Pure frozen calculations for the SPY volatility-managed research lane.

Execution and portfolio accounting deliberately live in the shared backtest core.
"""

from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from quant_system.data import (
    AcceptedSessionCalendar,
    CorporateActionIdentity,
    SourceIdentity,
)

INSTRUMENT = "SPY"
EXCHANGE_ID = "XNYS"
EXCHANGE_TIMEZONE = "America/New_York"
REQUIRED_RAW_CLOSES = 22
REQUIRED_LOG_RETURNS = 21
TARGET_ANNUALIZED_VOLATILITY = 0.10
ANNUALIZATION_DAYS = 252
MONTHS_PER_YEAR = 12
INITIAL_CAPITAL = 40_000.0
VALIDATION_COHORTS = 45
HOLDOUT_COHORTS = 53
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 4601
BOOTSTRAP_RESTART_PROBABILITY = 1.0 / 6.0
PROGRAM_FAMILY_ID = "ISSUE119_US_NEAR_TERM_MECHANISMS_CYCLE1"
PROGRAM_MECHANISM_ORDER = (
    "M119-01_US_SPY_REALIZED_VOL_SCALING",
    "M119-03_US_SPY_YIELD_CURVE_STATE",
    "M119-09_US_SPY_CREDIT_STRESS_STATE",
)
PROGRAM_ALPHA_ALLOCATIONS = (0.025, 0.015, 0.010)
PROGRAM_ALPHA_NON_RECYCLING = True
LOCAL_INFERENCE_ALPHA = 0.05
M119_01_PROGRAM_ALPHA = 0.025
CONTEMPORANEOUS_ACTION_BASIS = "contemporaneous_point_in_time"
RETROSPECTIVE_ACTION_BASIS = "retrospective_realized_event_reconstruction"
_ACTION_EVIDENCE_BASES = {
    CONTEMPORANEOUS_ACTION_BASIS,
    RETROSPECTIVE_ACTION_BASIS,
}

_NEW_YORK = ZoneInfo(EXCHANGE_TIMEZONE)
_VALIDATION_GATE_NAMES = (
    "sharpe_difference_positive",
    "strategy_compounded_net_return_positive",
    "strategy_annualized_volatility_lower",
    "strategy_maximum_drawdown_better",
)
_HOLDOUT_GATE_NAMES = (
    "bootstrap_lower_bound_positive",
    "program_overlay_bootstrap_lower_bound_positive",
    "strategy_compounded_net_return_positive",
    "strategy_annualized_volatility_lower",
    "strategy_maximum_drawdown_better",
)


class InputContractError(ValueError):
    """Raised when a frozen input or calculation invariant is not satisfied."""


def _finite(value: object, field: str, *, positive: bool = False) -> float:
    if isinstance(value, bool):
        raise InputContractError(f"{field} must be numeric, not boolean")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise InputContractError(f"{field} must be numeric") from exc
    if not math.isfinite(number):
        raise InputContractError(f"{field} must be finite")
    if positive and number <= 0.0:
        raise InputContractError(f"{field} must be positive")
    return number


def _date(value: object, field: str) -> date:
    if type(value) is not date:
        raise InputContractError(f"{field} must be a date")
    return value


def _decision_at(value: datetime, expected_date: date) -> datetime:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise InputContractError("decision_at must be timezone-aware")
    local = value.astimezone(_NEW_YORK)
    if local.date() != expected_date or (
        local.hour,
        local.minute,
        local.second,
        local.microsecond,
    ) != (20, 5, 0, 0):
        raise InputContractError(
            "decision_at must equal 20:05 America/New_York on the signal session"
        )
    return local


@dataclass(frozen=True)
class CloseObservation:
    """One causal raw close with canonical source identity."""

    session_date: date
    raw_close: float
    source: SourceIdentity

    def __post_init__(self) -> None:
        _date(self.session_date, "session_date")
        _finite(self.raw_close, "raw_close", positive=True)
        if not isinstance(self.source, SourceIdentity):
            raise InputContractError("source must be a canonical SourceIdentity")


@dataclass(frozen=True)
class VolatilitySignal:
    signal_session: date
    execution_session: date
    log_total_returns: tuple[float, ...]
    annualized_volatility: float
    target_weight: float


@dataclass(frozen=True)
class PerformanceMetrics:
    monthly_arithmetic_mean: float
    monthly_sample_stdev: float
    sharpe: float
    annualized_volatility: float
    compounded_net_return: float
    maximum_drawdown: float


@dataclass(frozen=True)
class ValidationDecision:
    observed_cohorts: int
    strategy: PerformanceMetrics
    benchmark: PerformanceMetrics
    sharpe_difference: float
    gates: tuple[tuple[str, bool], ...]

    @property
    def all_gates_pass(self) -> bool:
        return (
            self.observed_cohorts == VALIDATION_COHORTS
            and tuple(name for name, _ in self.gates) == _VALIDATION_GATE_NAMES
            and all(passed is True for _, passed in self.gates)
        )


@dataclass(frozen=True)
class HoldoutDecision:
    observed_cohorts: int
    strategy: PerformanceMetrics
    benchmark: PerformanceMetrics
    bootstrap_lower_bound: float
    program_overlay_lower_bound: float
    gates: tuple[tuple[str, bool], ...]

    @property
    def all_gates_pass(self) -> bool:
        return (
            self.observed_cohorts == HOLDOUT_COHORTS
            and tuple(name for name, _ in self.gates) == _HOLDOUT_GATE_NAMES
            and all(passed is True for _, passed in self.gates)
        )


def _calendar_window(
    calendar: AcceptedSessionCalendar,
    closes: tuple[CloseObservation, ...],
    *,
    decision_at: datetime,
    execution_session: date,
) -> tuple[date, ...]:
    if not isinstance(calendar, AcceptedSessionCalendar):
        raise InputContractError("calendar must be an AcceptedSessionCalendar")
    if calendar.exchange_id != EXCHANGE_ID or calendar.exchange_timezone != EXCHANGE_TIMEZONE:
        raise InputContractError("signal calendar must be accepted XNYS/America-New_York")
    if len(closes) != REQUIRED_RAW_CLOSES:
        raise InputContractError(f"exactly {REQUIRED_RAW_CLOSES} raw closes are required")
    dates = tuple(item.session_date for item in closes)
    if len(set(dates)) != len(dates):
        raise InputContractError("close session dates must be unique")
    final_date = dates[-1]
    _decision_at(decision_at, final_date)
    _date(execution_session, "execution_session")
    try:
        final_position = calendar.session_dates.index(final_date)
    except ValueError as exc:
        raise InputContractError("signal session is not an accepted XNYS session") from exc
    if final_position < REQUIRED_RAW_CLOSES - 1:
        raise InputContractError("calendar lacks the complete 22-session signal window")
    expected = calendar.session_dates[final_position - REQUIRED_RAW_CLOSES + 1 : final_position + 1]
    if dates != expected:
        raise InputContractError("closes must cover 22 consecutive accepted XNYS sessions")
    try:
        following = calendar.next_session(final_date, as_of=decision_at)
    except (TypeError, ValueError) as exc:
        raise InputContractError("calendar cannot establish the next accepted session") from exc
    if (following.session_date.year, following.session_date.month) == (
        final_date.year,
        final_date.month,
    ):
        raise InputContractError("signal session must be the final accepted session of the month")
    if following.session_date != execution_session:
        raise InputContractError("execution must be the immediately following accepted session")
    for observation, session_date in zip(closes, expected, strict=True):
        try:
            calendar.session_on(session_date, as_of=decision_at)
        except (TypeError, ValueError) as exc:
            raise InputContractError("calendar session identity is unavailable") from exc
        source_local = observation.source.available_at.astimezone(_NEW_YORK)
        if source_local.date() != session_date or (
            source_local.hour,
            source_local.minute,
            source_local.second,
            source_local.microsecond,
        ) != (20, 0, 0, 0):
            raise InputContractError(
                "raw close source must use the same-session 20:00 America/New_York convention"
            )
        if observation.source.available_at > decision_at:
            raise InputContractError("raw close must be available by decision_at")
    return expected


def _actions_by_date(
    calendar: AcceptedSessionCalendar,
    actions: tuple[CorporateActionIdentity, ...],
    expected_action_ids: tuple[str, ...],
    return_dates: tuple[date, ...],
    decision_at: datetime,
    action_evidence_basis: str,
) -> dict[date, CorporateActionIdentity]:
    if type(actions) is not tuple or any(
        not isinstance(action, CorporateActionIdentity) for action in actions
    ):
        raise InputContractError("actions must be CorporateActionIdentity values")
    if type(expected_action_ids) is not tuple or any(
        not isinstance(action_id, str) or not action_id.strip() for action_id in expected_action_ids
    ):
        raise InputContractError("expected_action_ids must be a nonempty-ID tuple")
    actual_ids = tuple(action.action_id for action in actions)
    if len(actual_ids) != len(set(actual_ids)):
        raise InputContractError("duplicate action IDs fail closed")
    if actual_ids != expected_action_ids:
        raise InputContractError("runtime action IDs do not exactly match the expected window")
    if action_evidence_basis not in _ACTION_EVIDENCE_BASES:
        raise InputContractError("unsupported corporate-action evidence basis")
    usable = set(return_dates)
    indexed: dict[date, CorporateActionIdentity] = {}
    for action in actions:
        if action.subject_id != INSTRUMENT:
            raise InputContractError("corporate action subject must equal SPY")
        if action.effective_date not in usable:
            raise InputContractError("window-outside action fails closed")
        if action.effective_date in indexed:
            raise InputContractError("multiple ordinary actions on one session fail closed")
        try:
            session = calendar.session_on(action.effective_date, as_of=decision_at)
        except (TypeError, ValueError) as exc:
            raise InputContractError("corporate action is not on an accepted session") from exc
        if action.effective_at != session.open_at:
            raise InputContractError("corporate action effective_at must equal XNYS open")
        if action.effective_at > decision_at:
            raise InputContractError("corporate action cannot follow the decision time")
        if action_evidence_basis == CONTEMPORANEOUS_ACTION_BASIS:
            if action.source.available_at > action.effective_at:
                raise InputContractError(
                    "corporate action identity was not available by ex-date open"
                )
        elif (
            action.source.available_at <= action.effective_at
            or action.source.available_at != action.source.retrieved_at
        ):
            raise InputContractError(
                "retrospective action source must retain its actual post-event retrieval time"
            )
        if action.action_type in {"cash_dividend", "special_dividend"}:
            if action.currency != "USD" or action.unit != "per_share":
                raise InputContractError("cash action must use USD per_share")
        elif action.action_type not in {"split", "reverse_split"}:
            raise InputContractError("unsupported action type in signal window")
        indexed[action.effective_date] = action
    return indexed


def build_signal_feature(
    calendar: AcceptedSessionCalendar,
    closes: tuple[CloseObservation, ...],
    *,
    actions: tuple[CorporateActionIdentity, ...] = (),
    expected_action_ids: tuple[str, ...] = (),
    action_evidence_basis: str = CONTEMPORANEOUS_ACTION_BASIS,
    decision_at: datetime,
    execution_session: date,
) -> VolatilitySignal:
    """Build the exact causal 21-return feature for one monthly decision."""

    dates = _calendar_window(
        calendar,
        closes,
        decision_at=decision_at,
        execution_session=execution_session,
    )
    indexed = _actions_by_date(
        calendar,
        actions,
        expected_action_ids,
        dates[1:],
        decision_at,
        action_evidence_basis,
    )
    log_returns: list[float] = []
    for previous, current in zip(closes, closes[1:]):
        action = indexed.get(current.session_date)
        split_ratio = 1.0
        distribution = 0.0
        if action is not None and action.action_type in {"split", "reverse_split"}:
            assert action.split_ratio is not None
            split_ratio = _finite(action.split_ratio, "split_ratio", positive=True)
        elif action is not None:
            assert action.cash_amount is not None
            distribution = _finite(action.cash_amount, "cash_amount", positive=True)
        gross = (
            split_ratio * _finite(current.raw_close, "raw_close", positive=True) + distribution
        ) / _finite(previous.raw_close, "raw_close", positive=True)
        if not math.isfinite(gross) or gross <= 0.0:
            raise InputContractError("total-return gross relative must be finite and positive")
        log_returns.append(math.log(gross))
    frozen_returns = tuple(log_returns)
    volatility = annualized_realized_volatility(frozen_returns)
    return VolatilitySignal(
        dates[-1],
        execution_session,
        frozen_returns,
        volatility,
        target_weight(volatility),
    )


def annualized_realized_volatility(log_returns: tuple[float, ...]) -> float:
    values = tuple(_finite(value, "log return") for value in log_returns)
    if len(values) != REQUIRED_LOG_RETURNS:
        raise InputContractError(f"exactly {REQUIRED_LOG_RETURNS} log returns are required")
    volatility = statistics.stdev(values) * math.sqrt(ANNUALIZATION_DAYS)
    if not math.isfinite(volatility) or volatility <= 0.0:
        raise InputContractError("annualized volatility must be finite and positive")
    return volatility


def target_weight(annualized_volatility: float) -> float:
    volatility = _finite(
        annualized_volatility,
        "annualized_volatility",
        positive=True,
    )
    return min(1.0, TARGET_ANNUALIZED_VOLATILITY / volatility)


def cohort_returns(
    boundary_navs: tuple[float, ...],
    *,
    expected_cohorts: int | None = None,
) -> tuple[float, ...]:
    if type(boundary_navs) is not tuple or len(boundary_navs) < 2:
        raise InputContractError("boundary_navs must contain an initial and final boundary")
    if expected_cohorts is not None and (type(expected_cohorts) is not int or expected_cohorts < 1):
        raise InputContractError("expected_cohorts must be a positive integer")
    if expected_cohorts is not None and len(boundary_navs) != expected_cohorts + 1:
        raise InputContractError("no cohort may be skipped")
    values = tuple(_finite(value, "boundary NAV", positive=True) for value in boundary_navs)
    returns = tuple(current / previous - 1.0 for previous, current in zip(values, values[1:]))
    if not all(math.isfinite(value) for value in returns):
        raise InputContractError("cohort returns must be finite")
    return returns


def performance_metrics(
    monthly_returns: tuple[float, ...],
    boundary_navs: tuple[float, ...],
) -> PerformanceMetrics:
    values = tuple(_finite(value, "monthly return") for value in monthly_returns)
    navs = tuple(_finite(value, "boundary NAV", positive=True) for value in boundary_navs)
    if len(values) < 2 or len(navs) != len(values) + 1:
        raise InputContractError("metrics require every monthly return and boundary NAV")
    expected = cohort_returns(navs, expected_cohorts=len(values))
    if any(not math.isclose(a, b, rel_tol=0.0, abs_tol=1e-12) for a, b in zip(values, expected)):
        raise InputContractError("monthly returns must match the complete boundary NAV path")
    mean = statistics.fmean(values)
    stdev = statistics.stdev(values)
    if not math.isfinite(stdev) or stdev <= 0.0:
        raise InputContractError("monthly sample standard deviation must be finite and positive")
    sharpe = math.sqrt(MONTHS_PER_YEAR) * mean / stdev
    annualized_volatility = stdev * math.sqrt(MONTHS_PER_YEAR)
    compounded = math.prod(1.0 + value for value in values) - 1.0
    running_max = navs[0]
    drawdowns: list[float] = []
    for nav in navs:
        running_max = max(running_max, nav)
        drawdowns.append(nav / running_max - 1.0)
    maximum_drawdown = min(drawdowns)
    outputs = (mean, stdev, sharpe, annualized_volatility, compounded, maximum_drawdown)
    if not all(math.isfinite(value) for value in outputs):
        raise InputContractError("performance metrics must be finite")
    return PerformanceMetrics(*outputs)


def validation_gate_decision(
    strategy_returns: tuple[float, ...],
    benchmark_returns: tuple[float, ...],
    strategy_boundary_navs: tuple[float, ...],
    benchmark_boundary_navs: tuple[float, ...],
) -> ValidationDecision:
    if len(strategy_returns) != VALIDATION_COHORTS or len(benchmark_returns) != VALIDATION_COHORTS:
        raise InputContractError("validation requires exactly 45 complete cohorts")
    strategy = performance_metrics(strategy_returns, strategy_boundary_navs)
    benchmark = performance_metrics(benchmark_returns, benchmark_boundary_navs)
    difference = _finite(strategy.sharpe - benchmark.sharpe, "Sharpe difference")
    gates = (
        ("sharpe_difference_positive", difference > 0.0),
        ("strategy_compounded_net_return_positive", strategy.compounded_net_return > 0.0),
        (
            "strategy_annualized_volatility_lower",
            strategy.annualized_volatility < benchmark.annualized_volatility,
        ),
        (
            "strategy_maximum_drawdown_better",
            strategy.maximum_drawdown > benchmark.maximum_drawdown,
        ),
    )
    return ValidationDecision(VALIDATION_COHORTS, strategy, benchmark, difference, gates)


def stationary_bootstrap_indices(sample_size: int) -> tuple[tuple[int, ...], ...]:
    """Return the exact 10,000 frozen stationary-bootstrap index paths."""

    if type(sample_size) is not int or sample_size < 2:
        raise InputContractError("sample_size must be an integer of at least two")
    generator = random.Random(BOOTSTRAP_SEED)
    paths: list[tuple[int, ...]] = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        path = [math.floor(generator.random() * sample_size)]
        for _ in range(1, sample_size):
            restart_draw = generator.random()
            if restart_draw < BOOTSTRAP_RESTART_PROBABILITY:
                path.append(math.floor(generator.random() * sample_size))
            else:
                path.append((path[-1] + 1) % sample_size)
        paths.append(tuple(path))
    return tuple(paths)


def paired_bootstrap_lower_bounds(
    strategy_returns: tuple[float, ...],
    benchmark_returns: tuple[float, ...],
) -> tuple[float, float]:
    if len(strategy_returns) != HOLDOUT_COHORTS or len(benchmark_returns) != HOLDOUT_COHORTS:
        raise InputContractError("holdout bootstrap requires exactly 53 paired rows")
    strategy = tuple(_finite(value, "strategy return") for value in strategy_returns)
    benchmark = tuple(_finite(value, "benchmark return") for value in benchmark_returns)
    statistics_: list[float] = []
    for path in stationary_bootstrap_indices(HOLDOUT_COHORTS):
        strategy_sample = tuple(strategy[index] for index in path)
        benchmark_sample = tuple(benchmark[index] for index in path)
        strategy_stdev = statistics.stdev(strategy_sample)
        benchmark_stdev = statistics.stdev(benchmark_sample)
        if (
            not math.isfinite(strategy_stdev)
            or strategy_stdev <= 0.0
            or not math.isfinite(benchmark_stdev)
            or benchmark_stdev <= 0.0
        ):
            raise InputContractError("invalid bootstrap replicate fails closed")
        statistic = math.sqrt(MONTHS_PER_YEAR) * (
            statistics.fmean(strategy_sample) / strategy_stdev
            - statistics.fmean(benchmark_sample) / benchmark_stdev
        )
        statistics_.append(_finite(statistic, "bootstrap statistic"))
    ordered = sorted(statistics_)
    bounds = []
    for alpha in (LOCAL_INFERENCE_ALPHA, M119_01_PROGRAM_ALPHA):
        h = (len(ordered) - 1) * alpha
        lower = math.floor(h)
        upper = math.ceil(h)
        bounds.append(ordered[lower] + (h - lower) * (ordered[upper] - ordered[lower]))
    return (
        _finite(bounds[0], "local bootstrap lower bound"),
        _finite(bounds[1], "program-overlay bootstrap lower bound"),
    )


def paired_bootstrap_lower_bound(
    strategy_returns: tuple[float, ...],
    benchmark_returns: tuple[float, ...],
) -> float:
    """Preserve the original local-alpha lower bound API."""

    return paired_bootstrap_lower_bounds(strategy_returns, benchmark_returns)[0]


def holdout_gate_decision(
    validation: ValidationDecision,
    strategy_returns: tuple[float, ...],
    benchmark_returns: tuple[float, ...],
    strategy_boundary_navs: tuple[float, ...],
    benchmark_boundary_navs: tuple[float, ...],
) -> HoldoutDecision:
    if not isinstance(validation, ValidationDecision) or not validation.all_gates_pass:
        raise InputContractError("holdout is locked until a validation decision passes every gate")
    if len(strategy_returns) != HOLDOUT_COHORTS or len(benchmark_returns) != HOLDOUT_COHORTS:
        raise InputContractError("holdout requires exactly 53 complete cohorts")
    strategy = performance_metrics(strategy_returns, strategy_boundary_navs)
    benchmark = performance_metrics(benchmark_returns, benchmark_boundary_navs)
    lower_bound, program_lower_bound = paired_bootstrap_lower_bounds(
        strategy_returns, benchmark_returns
    )
    gates = (
        ("bootstrap_lower_bound_positive", lower_bound > 0.0),
        ("program_overlay_bootstrap_lower_bound_positive", program_lower_bound > 0.0),
        ("strategy_compounded_net_return_positive", strategy.compounded_net_return > 0.0),
        (
            "strategy_annualized_volatility_lower",
            strategy.annualized_volatility < benchmark.annualized_volatility,
        ),
        (
            "strategy_maximum_drawdown_better",
            strategy.maximum_drawdown > benchmark.maximum_drawdown,
        ),
    )
    return HoldoutDecision(
        HOLDOUT_COHORTS, strategy, benchmark, lower_bound, program_lower_bound, gates
    )


__all__ = [
    "BOOTSTRAP_RESAMPLES",
    "BOOTSTRAP_RESTART_PROBABILITY",
    "BOOTSTRAP_SEED",
    "CloseObservation",
    "HOLDOUT_COHORTS",
    "HoldoutDecision",
    "INITIAL_CAPITAL",
    "InputContractError",
    "LOCAL_INFERENCE_ALPHA",
    "M119_01_PROGRAM_ALPHA",
    "PerformanceMetrics",
    "PROGRAM_ALPHA_ALLOCATIONS",
    "PROGRAM_ALPHA_NON_RECYCLING",
    "PROGRAM_FAMILY_ID",
    "PROGRAM_MECHANISM_ORDER",
    "VALIDATION_COHORTS",
    "ValidationDecision",
    "VolatilitySignal",
    "annualized_realized_volatility",
    "build_signal_feature",
    "cohort_returns",
    "holdout_gate_decision",
    "paired_bootstrap_lower_bound",
    "paired_bootstrap_lower_bounds",
    "performance_metrics",
    "stationary_bootstrap_indices",
    "target_weight",
    "validation_gate_decision",
]
