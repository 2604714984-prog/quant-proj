"""Frozen calculations for the M119-03 SPY yield-curve-state screen."""

from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

MECHANISM_ID = "M119-03_US_SPY_YIELD_CURVE_STATE"
PROGRAM_FAMILY_ID = "ISSUE119_US_NEAR_TERM_MECHANISMS_CYCLE1"
PROGRAM_ALPHA = 0.015
INITIAL_CAPITAL = 40_000.0
SCREEN_COHORTS = 45
INFERENCE_COHORTS = 53
ONE_WAY_SLIPPAGE_BPS = 10.0
MAX_STALENESS_DAYS = 7
TEN_YEAR_SERIES = "DGS10"
THREE_MONTH_SERIES = "DGS3MO"
EXCHANGE_TIMEZONE = "America/New_York"
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 11_903
BOOTSTRAP_EXPECTED_BLOCK_MONTHS = 6
BOOTSTRAP_RESTART_PROBABILITY = 1.0 / BOOTSTRAP_EXPECTED_BLOCK_MONTHS
LOCAL_INFERENCE_ALPHA = 0.05
CONSTANT_RETURN_TOLERANCE = 1e-12

_NEW_YORK = ZoneInfo(EXCHANGE_TIMEZONE)
_GATE_NAMES = (
    "sharpe_difference_positive",
    "strategy_compounded_net_return_positive",
    "strategy_annualized_volatility_lower",
    "strategy_maximum_drawdown_better",
)
_INFERENCE_GATE_NAMES = (
    "local_lower_bound_positive",
    "program_lower_bound_positive",
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


@dataclass(frozen=True)
class RateObservation:
    """One official ALFRED observation as known by its conservative cutoff."""

    series_id: str
    observation_date: date
    value_percent: float
    available_at: datetime
    row_sha256: str

    def __post_init__(self) -> None:
        if self.series_id not in {TEN_YEAR_SERIES, THREE_MONTH_SERIES}:
            raise InputContractError("unsupported H.15 series")
        if type(self.observation_date) is not date:
            raise InputContractError("observation_date must be a date")
        _finite(self.value_percent, "value_percent")
        if (
            type(self.available_at) is not datetime
            or self.available_at.tzinfo is None
            or self.available_at.utcoffset() is None
        ):
            raise InputContractError("available_at must be timezone-aware")
        if (
            type(self.row_sha256) is not str
            or len(self.row_sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.row_sha256)
        ):
            raise InputContractError("row_sha256 must be a lowercase SHA-256")


@dataclass(frozen=True)
class PerformanceMetrics:
    monthly_arithmetic_mean: float
    monthly_sample_stdev: float
    sharpe: float
    annualized_volatility: float
    compounded_net_return: float
    maximum_drawdown: float


@dataclass(frozen=True)
class ScreenDecision:
    observed_cohorts: int
    strategy: PerformanceMetrics
    benchmark: PerformanceMetrics
    sharpe_difference: float
    gates: tuple[tuple[str, bool], ...]

    @property
    def all_gates_pass(self) -> bool:
        return (
            self.observed_cohorts == SCREEN_COHORTS
            and tuple(name for name, _ in self.gates) == _GATE_NAMES
            and all(passed is True for _, passed in self.gates)
        )


@dataclass(frozen=True)
class InferenceDecision:
    observed_cohorts: int
    strategy: PerformanceMetrics
    benchmark: PerformanceMetrics
    observed_sharpe_difference: float
    local_lower_bound: float
    program_lower_bound: float
    gates: tuple[tuple[str, bool], ...]

    @property
    def all_gates_pass(self) -> bool:
        return (
            self.observed_cohorts == INFERENCE_COHORTS
            and tuple(name for name, _ in self.gates) == _INFERENCE_GATE_NAMES
            and all(passed is True for _, passed in self.gates)
        )


def target_weight(
    ten_year: RateObservation,
    three_month: RateObservation,
    *,
    decision_at: datetime,
) -> float:
    """Return the preregistered binary SPY weight without smoothing or repair."""

    if not isinstance(ten_year, RateObservation) or not isinstance(
        three_month, RateObservation
    ):
        raise InputContractError("two H.15 observations are required")
    if (ten_year.series_id, three_month.series_id) != (
        TEN_YEAR_SERIES,
        THREE_MONTH_SERIES,
    ):
        raise InputContractError("H.15 series order is fixed")
    if ten_year.observation_date != three_month.observation_date:
        raise InputContractError("both tenors must use the same observation date")
    if (
        type(decision_at) is not datetime
        or decision_at.tzinfo is None
        or decision_at.utcoffset() is None
    ):
        raise InputContractError("decision_at must be timezone-aware")
    if ten_year.available_at > decision_at or three_month.available_at > decision_at:
        raise InputContractError("both H.15 observations must be available by decision_at")
    local_date = decision_at.astimezone(_NEW_YORK).date()
    staleness = (local_date - ten_year.observation_date).days
    if staleness < 0 or staleness > MAX_STALENESS_DAYS:
        raise InputContractError("common H.15 observation is outside the frozen staleness bound")
    spread = _finite(ten_year.value_percent, "DGS10") - _finite(
        three_month.value_percent, "DGS3MO"
    )
    return 1.0 if spread > 0.0 else 0.0


def cohort_returns(
    boundary_navs: tuple[float, ...],
    *,
    expected_cohorts: int = SCREEN_COHORTS,
) -> tuple[float, ...]:
    if type(boundary_navs) is not tuple or len(boundary_navs) != expected_cohorts + 1:
        raise InputContractError("no monthly cohort may be skipped")
    navs = tuple(_finite(value, "boundary NAV", positive=True) for value in boundary_navs)
    returns = tuple(current / previous - 1.0 for previous, current in zip(navs, navs[1:]))
    if not all(math.isfinite(value) for value in returns):
        raise InputContractError("cohort returns must be finite")
    return returns


def performance_metrics(
    monthly_returns: tuple[float, ...],
    boundary_navs: tuple[float, ...],
) -> PerformanceMetrics:
    returns = tuple(_finite(value, "monthly return") for value in monthly_returns)
    navs = tuple(_finite(value, "boundary NAV", positive=True) for value in boundary_navs)
    if len(returns) < 2 or len(navs) != len(returns) + 1:
        raise InputContractError("metrics require a complete return and NAV path")
    expected = cohort_returns(navs, expected_cohorts=len(returns))
    if any(
        not math.isclose(actual, implied, rel_tol=0.0, abs_tol=1e-12)
        for actual, implied in zip(returns, expected)
    ):
        raise InputContractError("monthly returns must match boundary NAVs")
    mean = statistics.fmean(returns)
    stdev = statistics.stdev(returns)
    if not math.isfinite(stdev) or stdev < 0.0:
        raise InputContractError("monthly sample standard deviation must be nonnegative")
    return_range = max(returns) - min(returns)
    if return_range <= CONSTANT_RETURN_TOLERANCE and any(value != 0.0 for value in returns):
        raise InputContractError("nonzero constant returns have undefined finite Sharpe")
    sharpe = 0.0 if stdev == 0.0 else math.sqrt(12.0) * mean / stdev
    running_max = navs[0]
    drawdowns: list[float] = []
    for nav in navs:
        running_max = max(running_max, nav)
        drawdowns.append(nav / running_max - 1.0)
    outputs = PerformanceMetrics(
        mean,
        stdev,
        sharpe,
        math.sqrt(12.0) * stdev,
        math.prod(1.0 + value for value in returns) - 1.0,
        min(drawdowns),
    )
    if not all(math.isfinite(value) for value in vars(outputs).values()):
        raise InputContractError("performance metrics must be finite")
    return outputs


def screen_decision(
    strategy_boundary_navs: tuple[float, ...],
    benchmark_boundary_navs: tuple[float, ...],
) -> ScreenDecision:
    strategy_returns = cohort_returns(strategy_boundary_navs)
    benchmark_returns = cohort_returns(benchmark_boundary_navs)
    strategy = performance_metrics(strategy_returns, strategy_boundary_navs)
    benchmark = performance_metrics(benchmark_returns, benchmark_boundary_navs)
    sharpe_difference = _finite(strategy.sharpe - benchmark.sharpe, "Sharpe difference")
    gates = (
        ("sharpe_difference_positive", sharpe_difference > 0.0),
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
    return ScreenDecision(SCREEN_COHORTS, strategy, benchmark, sharpe_difference, gates)


def stationary_bootstrap_indices(
    sample_size: int = INFERENCE_COHORTS,
) -> tuple[tuple[int, ...], ...]:
    """Return the exact frozen paired stationary-bootstrap index paths."""

    if type(sample_size) is not int or sample_size < 2:
        raise InputContractError("sample_size must be an integer of at least two")
    generator = random.Random(BOOTSTRAP_SEED)
    paths: list[tuple[int, ...]] = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        path = [math.floor(generator.random() * sample_size)]
        for _ in range(1, sample_size):
            if generator.random() < BOOTSTRAP_RESTART_PROBABILITY:
                path.append(math.floor(generator.random() * sample_size))
            else:
                path.append((path[-1] + 1) % sample_size)
        paths.append(tuple(path))
    return tuple(paths)


def _linear_quantile(ordered: list[float], probability: float) -> float:
    if not ordered:
        raise InputContractError("bootstrap statistics cannot be empty")
    probability = _finite(probability, "quantile probability")
    if not 0.0 < probability < 1.0:
        raise InputContractError("quantile probability must be inside (0, 1)")
    rank = (len(ordered) - 1) * probability
    lower = math.floor(rank)
    upper = math.ceil(rank)
    return _finite(
        ordered[lower] + (rank - lower) * (ordered[upper] - ordered[lower]),
        "bootstrap lower bound",
    )


def paired_stationary_bootstrap_lower_bounds(
    strategy_returns: tuple[float, ...],
    benchmark_returns: tuple[float, ...],
) -> tuple[float, float]:
    """Compute the frozen local and program one-sided lower bounds."""

    if (
        type(strategy_returns) is not tuple
        or type(benchmark_returns) is not tuple
        or len(strategy_returns) != INFERENCE_COHORTS
        or len(benchmark_returns) != INFERENCE_COHORTS
    ):
        raise InputContractError("inference bootstrap requires exactly 53 paired rows")
    strategy = tuple(_finite(value, "strategy return") for value in strategy_returns)
    benchmark = tuple(_finite(value, "benchmark return") for value in benchmark_returns)
    if statistics.stdev(strategy) <= 0.0 or statistics.stdev(benchmark) <= 0.0:
        raise InputContractError("zero standard deviation fails inference closed")

    statistics_: list[float] = []
    for path in stationary_bootstrap_indices():
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
            raise InputContractError("invalid bootstrap replicate fails inference closed")
        statistic = math.sqrt(12.0) * (
            statistics.fmean(strategy_sample) / strategy_stdev
            - statistics.fmean(benchmark_sample) / benchmark_stdev
        )
        statistics_.append(_finite(statistic, "bootstrap Sharpe difference"))

    ordered = sorted(statistics_)
    return (
        _linear_quantile(ordered, LOCAL_INFERENCE_ALPHA),
        _linear_quantile(ordered, PROGRAM_ALPHA),
    )


def inference_decision(
    strategy_boundary_navs: tuple[float, ...],
    benchmark_boundary_navs: tuple[float, ...],
    *,
    screen_a_unlocked: bool,
) -> InferenceDecision:
    if screen_a_unlocked is not True:
        raise InputContractError("inference B is locked until Screen A passes")
    strategy_returns = cohort_returns(
        strategy_boundary_navs, expected_cohorts=INFERENCE_COHORTS
    )
    benchmark_returns = cohort_returns(
        benchmark_boundary_navs, expected_cohorts=INFERENCE_COHORTS
    )
    strategy = performance_metrics(strategy_returns, strategy_boundary_navs)
    benchmark = performance_metrics(benchmark_returns, benchmark_boundary_navs)
    observed = _finite(
        strategy.sharpe - benchmark.sharpe, "observed Sharpe difference"
    )
    local_lower, program_lower = paired_stationary_bootstrap_lower_bounds(
        strategy_returns, benchmark_returns
    )
    gates = (
        ("local_lower_bound_positive", local_lower > 0.0),
        ("program_lower_bound_positive", program_lower > 0.0),
    )
    return InferenceDecision(
        INFERENCE_COHORTS,
        strategy,
        benchmark,
        observed,
        local_lower,
        program_lower,
        gates,
    )
