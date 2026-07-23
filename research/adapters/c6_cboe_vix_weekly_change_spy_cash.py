"""Frozen pure calculations for Cycle 6 weekly VIX-change SPY/cash.

This branch-only module has no filesystem, provider, database, or execution
access.  It translates one exact weekly VIX change into a target weight and
implements the preregistered support and terminal decision rules.
"""

from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

RESEARCH_ID = "C6_VIX_WEEKLY_CHANGE_IMPULSE_SPY_CASH_V1"
PROGRAM_FAMILY_ID = "ISSUE119_US_NEAR_TERM_MECHANISMS_CYCLE6"
INITIAL_CAPITAL = 40_000.0
PROGRAM_ALPHA = 0.0015625
VALIDATION_INTERVALS = 129
HOLDOUT_INTERVALS = 156
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 1_196_101
BOOTSTRAP_BLOCK_LENGTH = 13
MIN_INTERVALS = 104
MIN_STATE_COUNT = 13
MIN_DIRECTIONAL_TRANSITIONS = 4
EXCHANGE_TIMEZONE = "America/New_York"

_NEW_YORK = ZoneInfo(EXCHANGE_TIMEZONE)
_SPLIT_INTERVAL_COUNTS = {
    "development": 147,
    "validation": VALIDATION_INTERVALS,
    "holdout": HOLDOUT_INTERVALS,
}
_SUPPORT_GATE_NAMES = (
    "complete_intervals_at_least_104",
    "spy_state_intervals_at_least_13",
    "cash_state_intervals_at_least_13",
    "spy_to_cash_transitions_at_least_4",
    "cash_to_spy_transitions_at_least_4",
)
_VALIDATION_GATE_NAMES = (
    "strategy_terminal_net_wealth_strictly_above_spy",
    "arithmetic_mean_paired_weekly_active_return_strictly_positive",
    "strategy_maximum_drawdown_no_worse_than_spy",
)
_HOLDOUT_GATE_NAMES = (
    "strategy_terminal_net_wealth_strictly_above_spy",
    "strategy_maximum_drawdown_no_worse_than_spy",
    "interval_count_exactly_156",
    "centered_null_one_sided_p_at_most_0_0015625",
    "uncentered_type7_0_0015625_lower_bound_strictly_positive",
)


class InputContractError(ValueError):
    """Raised when a frozen signal, support, or inference input is invalid."""


def _finite(value: object, field: str) -> float:
    if type(value) not in {int, float}:
        raise InputContractError(f"{field} must be an int or float")
    number = float(value)
    if not math.isfinite(number):
        raise InputContractError(f"{field} must be finite")
    return number


def _positive(value: object, field: str) -> float:
    number = _finite(value, field)
    if number <= 0.0:
        raise InputContractError(f"{field} must be positive")
    return number


def _aware(value: object, field: str) -> datetime:
    if (
        type(value) is not datetime
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise InputContractError(f"{field} must be timezone-aware")
    return value


def _sha256(value: object, field: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise InputContractError(f"{field} must be a lowercase SHA-256")
    return value


def _week_start(value: date) -> date:
    return value - timedelta(days=value.weekday())


@dataclass(frozen=True)
class WeeklyState:
    """One outcome-free weekly VIX change and its frozen SPY/cash mapping."""

    prior_observation_date: date
    observation_date: date
    execution_date: date
    prior_close: float
    current_close: float
    available_at: datetime
    state: str
    spy_target_weight: float
    row_sha256: str

    def __post_init__(self) -> None:
        if any(
            type(value) is not date
            for value in (
                self.prior_observation_date,
                self.observation_date,
                self.execution_date,
            )
        ):
            raise InputContractError("weekly state dates must be date values")
        if _week_start(self.observation_date) - _week_start(
            self.prior_observation_date
        ) != timedelta(days=7):
            raise InputContractError("weekly observations must be consecutive buckets")
        if not self.prior_observation_date < self.observation_date < self.execution_date:
            raise InputContractError("weekly state chronology is invalid")
        _positive(self.prior_close, "prior_close")
        _positive(self.current_close, "current_close")
        available = _aware(self.available_at, "available_at").astimezone(_NEW_YORK)
        if available.date() != self.observation_date or available.time().isoformat() != (
            "16:15:00"
        ):
            raise InputContractError(
                "available_at must equal 16:15 America/New_York on observation_date"
            )
        decision_at = datetime.combine(
            self.execution_date,
            datetime.min.time().replace(hour=9),
            tzinfo=_NEW_YORK,
        )
        if self.available_at > decision_at:
            raise InputContractError("weekly VIX state was unavailable by decision_at")
        expected_state = "cash" if self.current_close > self.prior_close else "spy"
        if self.state != expected_state:
            raise InputContractError("state differs from the frozen VIX-change sign rule")
        expected_weight = 0.0 if expected_state == "cash" else 1.0
        if _finite(self.spy_target_weight, "spy_target_weight") != expected_weight:
            raise InputContractError("SPY target weight differs from the frozen mapping")
        _sha256(self.row_sha256, "row_sha256")


@dataclass(frozen=True)
class SupportDecision:
    split_id: str
    observed_intervals: int
    spy_state_intervals: int
    cash_state_intervals: int
    spy_to_cash: int
    cash_to_spy: int
    gates: tuple[tuple[str, bool], ...]

    @property
    def all_gates_pass(self) -> bool:
        return (
            self.observed_intervals == _SPLIT_INTERVAL_COUNTS[self.split_id]
            and tuple(name for name, _ in self.gates) == _SUPPORT_GATE_NAMES
            and all(passed is True for _, passed in self.gates)
        )


@dataclass(frozen=True)
class PerformanceMetrics:
    terminal_net_wealth: float
    arithmetic_mean_return: float
    maximum_drawdown: float


@dataclass(frozen=True)
class ValidationDecision:
    observed_intervals: int
    strategy: PerformanceMetrics
    spy: PerformanceMetrics
    arithmetic_mean_active_return: float
    gates: tuple[tuple[str, bool], ...]

    @property
    def all_gates_pass(self) -> bool:
        return (
            self.observed_intervals == VALIDATION_INTERVALS
            and tuple(name for name, _ in self.gates) == _VALIDATION_GATE_NAMES
            and all(passed is True for _, passed in self.gates)
        )


@dataclass(frozen=True)
class BootstrapInference:
    observed_mean_active_return: float
    centered_null_one_sided_p: float
    uncentered_type7_lower_bound: float


@dataclass(frozen=True)
class HoldoutDecision:
    observed_intervals: int
    strategy: PerformanceMetrics
    spy: PerformanceMetrics
    inference: BootstrapInference
    gates: tuple[tuple[str, bool], ...]

    @property
    def all_gates_pass(self) -> bool:
        return (
            self.observed_intervals == HOLDOUT_INTERVALS
            and tuple(name for name, _ in self.gates) == _HOLDOUT_GATE_NAMES
            and all(passed is True for _, passed in self.gates)
        )


def derive_weekly_state(
    *,
    prior_observation_date: date,
    observation_date: date,
    execution_date: date,
    prior_close: float,
    current_close: float,
    available_at: datetime,
    row_sha256: str,
) -> WeeklyState:
    """Apply the single sign rule; exact equality maps to SPY."""

    prior = _positive(prior_close, "prior_close")
    current = _positive(current_close, "current_close")
    state = "cash" if current > prior else "spy"
    return WeeklyState(
        prior_observation_date,
        observation_date,
        execution_date,
        prior,
        current,
        available_at,
        state,
        0.0 if state == "cash" else 1.0,
        row_sha256,
    )


def split_support(
    states: tuple[WeeklyState, ...],
    *,
    split_id: str,
) -> SupportDecision:
    """Apply the exact pre-outcome state-support contract."""

    if split_id not in _SPLIT_INTERVAL_COUNTS:
        raise InputContractError("split_id must be development, validation, or holdout")
    expected = _SPLIT_INTERVAL_COUNTS[split_id]
    if (
        type(states) is not tuple
        or len(states) != expected
        or any(not isinstance(state, WeeklyState) for state in states)
    ):
        raise InputContractError(f"{split_id} requires exactly {expected} weekly states")
    buckets = tuple(_week_start(state.observation_date) for state in states)
    if any(right - left != timedelta(days=7) for left, right in zip(buckets, buckets[1:])):
        raise InputContractError("weekly states must use consecutive ordered buckets")
    row_hashes = tuple(state.row_sha256 for state in states)
    if len(row_hashes) != len(set(row_hashes)):
        raise InputContractError("weekly state row identities must be unique")
    spy_count = sum(state.state == "spy" for state in states)
    cash_count = sum(state.state == "cash" for state in states)
    spy_to_cash = sum(
        left.state == "spy" and right.state == "cash"
        for left, right in zip(states, states[1:])
    )
    cash_to_spy = sum(
        left.state == "cash" and right.state == "spy"
        for left, right in zip(states, states[1:])
    )
    gates = (
        ("complete_intervals_at_least_104", len(states) >= MIN_INTERVALS),
        ("spy_state_intervals_at_least_13", spy_count >= MIN_STATE_COUNT),
        ("cash_state_intervals_at_least_13", cash_count >= MIN_STATE_COUNT),
        (
            "spy_to_cash_transitions_at_least_4",
            spy_to_cash >= MIN_DIRECTIONAL_TRANSITIONS,
        ),
        (
            "cash_to_spy_transitions_at_least_4",
            cash_to_spy >= MIN_DIRECTIONAL_TRANSITIONS,
        ),
    )
    return SupportDecision(
        split_id,
        len(states),
        spy_count,
        cash_count,
        spy_to_cash,
        cash_to_spy,
        gates,
    )


def _paired_returns(
    strategy_returns: tuple[float, ...],
    spy_returns: tuple[float, ...],
    *,
    expected: int,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    if (
        type(strategy_returns) is not tuple
        or type(spy_returns) is not tuple
        or len(strategy_returns) != expected
        or len(spy_returns) != expected
    ):
        raise InputContractError(f"exactly {expected} paired weekly returns are required")
    strategy = tuple(_finite(value, "strategy return") for value in strategy_returns)
    spy = tuple(_finite(value, "SPY return") for value in spy_returns)
    if any(value <= -1.0 for value in strategy + spy):
        raise InputContractError("weekly returns must preserve strictly positive wealth")
    return strategy, spy


def _performance(returns: tuple[float, ...]) -> PerformanceMetrics:
    wealth = INITIAL_CAPITAL
    peak = wealth
    maximum_drawdown = 0.0
    for weekly_return in returns:
        wealth *= 1.0 + weekly_return
        peak = max(peak, wealth)
        maximum_drawdown = min(maximum_drawdown, wealth / peak - 1.0)
    return PerformanceMetrics(
        _finite(wealth, "terminal net wealth"),
        _finite(statistics.fmean(returns), "arithmetic mean return"),
        _finite(maximum_drawdown, "maximum drawdown"),
    )


def validation_decision(
    strategy_returns: tuple[float, ...],
    spy_returns: tuple[float, ...],
) -> ValidationDecision:
    strategy, spy = _paired_returns(
        strategy_returns,
        spy_returns,
        expected=VALIDATION_INTERVALS,
    )
    strategy_metrics = _performance(strategy)
    spy_metrics = _performance(spy)
    mean_active = _finite(
        statistics.fmean(left - right for left, right in zip(strategy, spy)),
        "arithmetic mean active return",
    )
    gates = (
        (
            "strategy_terminal_net_wealth_strictly_above_spy",
            strategy_metrics.terminal_net_wealth > spy_metrics.terminal_net_wealth,
        ),
        (
            "arithmetic_mean_paired_weekly_active_return_strictly_positive",
            mean_active > 0.0,
        ),
        (
            "strategy_maximum_drawdown_no_worse_than_spy",
            strategy_metrics.maximum_drawdown >= spy_metrics.maximum_drawdown,
        ),
    )
    return ValidationDecision(
        VALIDATION_INTERVALS,
        strategy_metrics,
        spy_metrics,
        mean_active,
        gates,
    )


def circular_block_bootstrap_indices(
    sample_size: int = HOLDOUT_INTERVALS,
) -> tuple[tuple[int, ...], ...]:
    """Return the frozen length-13 circular moving-block paths."""

    if type(sample_size) is not int or sample_size < 2:
        raise InputContractError("sample_size must be an integer of at least two")
    generator = random.Random(BOOTSTRAP_SEED)
    block_count = math.ceil(sample_size / BOOTSTRAP_BLOCK_LENGTH)
    paths: list[tuple[int, ...]] = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        path: list[int] = []
        for _ in range(block_count):
            start = math.floor(generator.random() * sample_size)
            path.extend(
                (start + offset) % sample_size
                for offset in range(BOOTSTRAP_BLOCK_LENGTH)
            )
        paths.append(tuple(path[:sample_size]))
    return tuple(paths)


def _type7_quantile(values: list[float], probability: float) -> float:
    if not values:
        raise InputContractError("bootstrap statistics cannot be empty")
    q = _finite(probability, "quantile probability")
    if not 0.0 < q < 1.0:
        raise InputContractError("quantile probability must be inside (0, 1)")
    ordered = sorted(_finite(value, "bootstrap statistic") for value in values)
    rank = (len(ordered) - 1) * q
    lower = math.floor(rank)
    upper = math.ceil(rank)
    return _finite(
        ordered[lower] + (rank - lower) * (ordered[upper] - ordered[lower]),
        "type-7 quantile",
    )


def bootstrap_inference(active_returns: tuple[float, ...]) -> BootstrapInference:
    if type(active_returns) is not tuple or len(active_returns) != HOLDOUT_INTERVALS:
        raise InputContractError(
            f"bootstrap requires exactly {HOLDOUT_INTERVALS} active-return intervals"
        )
    active = tuple(_finite(value, "active return") for value in active_returns)
    observed = _finite(statistics.fmean(active), "observed mean active return")
    centered = tuple(value - observed for value in active)
    uncentered_means: list[float] = []
    null_at_least_observed = 0
    paths = circular_block_bootstrap_indices()
    if len(paths) != BOOTSTRAP_RESAMPLES:
        raise InputContractError("bootstrap path count differs from the frozen contract")
    for path in paths:
        if len(path) != HOLDOUT_INTERVALS:
            raise InputContractError(
                "bootstrap path length differs from the frozen contract"
            )
        uncentered = _finite(
            statistics.fmean(active[index] for index in path),
            "uncentered bootstrap mean",
        )
        null_mean = _finite(
            statistics.fmean(centered[index] for index in path),
            "centered-null bootstrap mean",
        )
        uncentered_means.append(uncentered)
        if null_mean >= observed:
            null_at_least_observed += 1
    return BootstrapInference(
        observed,
        _finite(
            (1 + null_at_least_observed) / (BOOTSTRAP_RESAMPLES + 1),
            "centered-null one-sided p-value",
        ),
        _type7_quantile(uncentered_means, PROGRAM_ALPHA),
    )


def holdout_decision(
    strategy_returns: tuple[float, ...],
    spy_returns: tuple[float, ...],
) -> HoldoutDecision:
    strategy, spy = _paired_returns(
        strategy_returns,
        spy_returns,
        expected=HOLDOUT_INTERVALS,
    )
    strategy_metrics = _performance(strategy)
    spy_metrics = _performance(spy)
    inference = bootstrap_inference(
        tuple(left - right for left, right in zip(strategy, spy))
    )
    gates = (
        (
            "strategy_terminal_net_wealth_strictly_above_spy",
            strategy_metrics.terminal_net_wealth > spy_metrics.terminal_net_wealth,
        ),
        (
            "strategy_maximum_drawdown_no_worse_than_spy",
            strategy_metrics.maximum_drawdown >= spy_metrics.maximum_drawdown,
        ),
        ("interval_count_exactly_156", len(strategy) == HOLDOUT_INTERVALS),
        (
            "centered_null_one_sided_p_at_most_0_0015625",
            inference.centered_null_one_sided_p <= PROGRAM_ALPHA,
        ),
        (
            "uncentered_type7_0_0015625_lower_bound_strictly_positive",
            inference.uncentered_type7_lower_bound > 0.0,
        ),
    )
    return HoldoutDecision(
        HOLDOUT_INTERVALS,
        strategy_metrics,
        spy_metrics,
        inference,
        gates,
    )
