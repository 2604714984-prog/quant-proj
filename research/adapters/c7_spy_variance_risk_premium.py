"""Frozen pure inference for Cycle 7 monthly variance-risk-premium timing.

This removable research adapter has no filesystem, network, database, or
execution access.  It only evaluates already produced paired monthly returns
against the outcome-blind gates frozen in the Cycle 7 definition.
"""

from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass

RESEARCH_ID = "C7_SPY_VARIANCE_RISK_PREMIUM_V1"
PROGRAM_FAMILY_ID = "ISSUE119_US_NEAR_TERM_MECHANISMS_CYCLE7"
INITIAL_CAPITAL = 40_000.0
PROGRAM_ALPHA = 0.00078125
VALIDATION_INTERVALS = 28
HOLDOUT_INTERVALS = 36
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 119_702
BOOTSTRAP_BLOCK_LENGTH = 3

_VALIDATION_GATE_NAMES = (
    "strategy_terminal_net_wealth_strictly_above_spy",
    "arithmetic_mean_paired_monthly_active_return_strictly_positive",
    "strategy_maximum_drawdown_no_worse_than_spy",
)
_HOLDOUT_GATE_NAMES = (
    "strategy_terminal_net_wealth_strictly_above_spy",
    "strategy_maximum_drawdown_no_worse_than_spy",
    "interval_count_exactly_36",
    "centered_null_one_sided_p_at_most_0_00078125",
    "uncentered_type7_0_00078125_lower_bound_strictly_positive",
)


class InputContractError(ValueError):
    """Raised when frozen inference input is incomplete or ambiguous."""


def _finite(value: object, field: str) -> float:
    if type(value) not in {int, float}:
        raise InputContractError(f"{field} must be an int or float")
    number = float(value)
    if not math.isfinite(number):
        raise InputContractError(f"{field} must be finite")
    return number


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
        raise InputContractError(
            f"exactly {expected} paired monthly returns are required"
        )
    strategy = tuple(_finite(value, "strategy return") for value in strategy_returns)
    spy = tuple(_finite(value, "SPY return") for value in spy_returns)
    if any(value <= -1.0 for value in strategy + spy):
        raise InputContractError("monthly returns must preserve positive wealth")
    return strategy, spy


def _performance(returns: tuple[float, ...]) -> PerformanceMetrics:
    wealth = INITIAL_CAPITAL
    peak = wealth
    maximum_drawdown = 0.0
    for monthly_return in returns:
        wealth *= 1.0 + monthly_return
        if not math.isfinite(wealth) or wealth <= 0.0:
            raise InputContractError("wealth path must remain finite and positive")
        peak = max(peak, wealth)
        maximum_drawdown = min(maximum_drawdown, wealth / peak - 1.0)
    return PerformanceMetrics(
        wealth,
        _finite(statistics.fmean(returns), "arithmetic mean return"),
        _finite(maximum_drawdown, "maximum drawdown"),
    )


def validation_decision(
    strategy_returns: tuple[float, ...],
    spy_returns: tuple[float, ...],
) -> ValidationDecision:
    """Apply all three frozen validation gates without discretion."""

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
            "arithmetic_mean_paired_monthly_active_return_strictly_positive",
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
    """Return the frozen length-three circular moving-block paths."""

    if type(sample_size) is not int or sample_size < 2:
        raise InputContractError("sample_size must be an integer of at least two")
    generator = random.Random(BOOTSTRAP_SEED)
    blocks = math.ceil(sample_size / BOOTSTRAP_BLOCK_LENGTH)
    paths: list[tuple[int, ...]] = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        path: list[int] = []
        for _ in range(blocks):
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
            f"bootstrap requires exactly {HOLDOUT_INTERVALS} active returns"
        )
    active = tuple(_finite(value, "active return") for value in active_returns)
    observed = _finite(statistics.fmean(active), "observed mean active return")
    centered = tuple(value - observed for value in active)
    uncentered_means: list[float] = []
    null_at_least_observed = 0
    for path in circular_block_bootstrap_indices():
        uncentered_means.append(
            _finite(
                statistics.fmean(active[index] for index in path),
                "uncentered bootstrap mean",
            )
        )
        null_mean = _finite(
            statistics.fmean(centered[index] for index in path),
            "centered-null bootstrap mean",
        )
        if null_mean >= observed:
            null_at_least_observed += 1
    return BootstrapInference(
        observed,
        (1 + null_at_least_observed) / (BOOTSTRAP_RESAMPLES + 1),
        _type7_quantile(uncentered_means, PROGRAM_ALPHA),
    )


def holdout_decision(
    strategy_returns: tuple[float, ...],
    spy_returns: tuple[float, ...],
) -> HoldoutDecision:
    """Apply all five frozen holdout gates without discretion."""

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
        ("interval_count_exactly_36", len(strategy) == HOLDOUT_INTERVALS),
        (
            "centered_null_one_sided_p_at_most_0_00078125",
            inference.centered_null_one_sided_p <= PROGRAM_ALPHA,
        ),
        (
            "uncentered_type7_0_00078125_lower_bound_strictly_positive",
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
