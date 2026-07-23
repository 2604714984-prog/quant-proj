"""Frozen statistics for the removable Cycle 15 broad-dollar SPY/QQQ research lane."""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
import statistics


RESEARCH_ID = "C15_BROAD_DOLLAR_DIRECTION_SPY_QQQ_ROTATION_V1"
INITIAL_CAPITAL = 40_000.0
VALIDATION_INTERVALS = 28
HOLDOUT_INTERVALS = 34
PROGRAM_ALPHA = 0.0000030517578125
BOOTSTRAP_RESAMPLES = 1_000_000
BOOTSTRAP_BLOCK_MONTHS = 3
BOOTSTRAP_SEED = 1_500_301


class InputContractError(ValueError):
    """Raised when a frozen inference or return contract is violated."""


@dataclass(frozen=True)
class Performance:
    terminal_wealth: float
    arithmetic_mean_return: float
    maximum_drawdown: float


@dataclass(frozen=True)
class ValidationDecision:
    observed_intervals: int
    strategy: Performance
    comparator: Performance
    arithmetic_mean_active_return: float
    gates: tuple[tuple[str, bool], ...]
    all_gates_pass: bool


@dataclass(frozen=True)
class BootstrapInference:
    observed_mean: float
    centered_null_one_sided_p: float
    uncentered_lower_bound: float
    resamples: int
    block_length_months: int
    seed: int


@dataclass(frozen=True)
class HoldoutDecision:
    observed_intervals: int
    strategy: Performance
    comparator: Performance
    inference: BootstrapInference
    gates: tuple[tuple[str, bool], ...]
    all_gates_pass: bool


def _returns(values: tuple[float, ...], field: str, expected: int) -> tuple[float, ...]:
    if type(values) is not tuple or len(values) != expected:
        raise InputContractError(f"{field} must contain exactly {expected} returns")
    normalized: list[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise InputContractError(f"{field} values must be real numbers")
        number = float(value)
        if not math.isfinite(number) or number <= -1.0:
            raise InputContractError(f"{field} values must be finite and greater than -1")
        normalized.append(number)
    return tuple(normalized)


def _performance(values: tuple[float, ...]) -> Performance:
    wealth = 1.0
    peak = 1.0
    drawdown = 0.0
    for value in values:
        wealth *= 1.0 + value
        if not math.isfinite(wealth) or wealth <= 0.0:
            raise InputContractError("wealth path must remain finite and positive")
        peak = max(peak, wealth)
        drawdown = min(drawdown, wealth / peak - 1.0)
    return Performance(wealth, statistics.fmean(values), drawdown)


def _paired(
    strategy_returns: tuple[float, ...],
    comparator_returns: tuple[float, ...],
    expected: int,
) -> tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]]:
    strategy = _returns(strategy_returns, "strategy_returns", expected)
    comparator = _returns(
        comparator_returns, "comparator_returns", expected
    )
    active = tuple(
        left - right for left, right in zip(strategy, comparator, strict=True)
    )
    if not all(math.isfinite(value) for value in active):
        raise InputContractError("active returns must be finite")
    return strategy, comparator, active


def validation_decision(
    strategy_returns: tuple[float, ...],
    comparator_returns: tuple[float, ...],
) -> ValidationDecision:
    strategy, comparator, active = _paired(
        strategy_returns, comparator_returns, VALIDATION_INTERVALS
    )
    strategy_performance = _performance(strategy)
    comparator_performance = _performance(comparator)
    mean_active = statistics.fmean(active)
    gates = (
        (
            "strategy_terminal_net_wealth_strictly_above_50_50_comparator",
            strategy_performance.terminal_wealth
            > comparator_performance.terminal_wealth,
        ),
        ("arithmetic_mean_paired_active_return_strictly_positive", mean_active > 0.0),
        (
            "strategy_maximum_drawdown_no_worse_than_50_50_comparator",
            strategy_performance.maximum_drawdown
            >= comparator_performance.maximum_drawdown,
        ),
    )
    return ValidationDecision(
        VALIDATION_INTERVALS,
        strategy_performance,
        comparator_performance,
        mean_active,
        gates,
        all(passed for _, passed in gates),
    )


def circular_block_indices(
    sample_size: int,
    *,
    block_length: int,
    rng: random.Random,
) -> tuple[int, ...]:
    if type(sample_size) is not int or sample_size < 1:
        raise InputContractError("sample_size must be positive")
    if type(block_length) is not int or not 1 <= block_length <= sample_size:
        raise InputContractError("block_length must be in [1, sample_size]")
    indices: list[int] = []
    while len(indices) < sample_size:
        start = int(rng.random() * sample_size)
        indices.extend((start + offset) % sample_size for offset in range(block_length))
    return tuple(indices[:sample_size])


def _type7(values: list[float], probability: float) -> float:
    if not values or not 0.0 <= probability <= 1.0:
        raise InputContractError("invalid quantile input")
    ordered = sorted(values)
    rank = (len(ordered) - 1) * probability
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    weight = rank - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def bootstrap_inference(active_returns: tuple[float, ...]) -> BootstrapInference:
    active = _returns(active_returns, "active_returns", HOLDOUT_INTERVALS)
    observed = statistics.fmean(active)
    centered = tuple(value - observed for value in active)
    rng = random.Random(BOOTSTRAP_SEED)
    null_means: list[float] = []
    uncentered_means: list[float] = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        indices = circular_block_indices(
            HOLDOUT_INTERVALS,
            block_length=BOOTSTRAP_BLOCK_MONTHS,
            rng=rng,
        )
        null_mean = statistics.fmean(centered[index] for index in indices)
        sample_mean = statistics.fmean(active[index] for index in indices)
        if not math.isfinite(null_mean) or not math.isfinite(sample_mean):
            raise InputContractError("bootstrap replicate must be finite")
        null_means.append(null_mean)
        uncentered_means.append(sample_mean)
    p_value = (1 + sum(value >= observed for value in null_means)) / (
        BOOTSTRAP_RESAMPLES + 1
    )
    lower_bound = _type7(uncentered_means, PROGRAM_ALPHA)
    return BootstrapInference(
        observed,
        p_value,
        lower_bound,
        BOOTSTRAP_RESAMPLES,
        BOOTSTRAP_BLOCK_MONTHS,
        BOOTSTRAP_SEED,
    )


def holdout_decision(
    strategy_returns: tuple[float, ...],
    comparator_returns: tuple[float, ...],
) -> HoldoutDecision:
    strategy, comparator, active = _paired(
        strategy_returns, comparator_returns, HOLDOUT_INTERVALS
    )
    strategy_performance = _performance(strategy)
    comparator_performance = _performance(comparator)
    inference = bootstrap_inference(active)
    gates = (
        (
            "strategy_terminal_net_wealth_strictly_above_50_50_comparator",
            strategy_performance.terminal_wealth
            > comparator_performance.terminal_wealth,
        ),
        (
            "strategy_maximum_drawdown_no_worse_than_50_50_comparator",
            strategy_performance.maximum_drawdown
            >= comparator_performance.maximum_drawdown,
        ),
        ("exactly_34_paired_intervals", len(active) == HOLDOUT_INTERVALS),
        (
            "centered_null_one_sided_p_at_most_0_0000030517578125",
            inference.centered_null_one_sided_p <= PROGRAM_ALPHA,
        ),
        (
            "uncentered_type7_0_0000030517578125_lower_bound_strictly_positive",
            inference.uncentered_lower_bound > 0.0,
        ),
    )
    return HoldoutDecision(
        HOLDOUT_INTERVALS,
        strategy_performance,
        comparator_performance,
        inference,
        gates,
        all(passed for _, passed in gates),
    )


__all__ = [
    "BOOTSTRAP_BLOCK_MONTHS",
    "BOOTSTRAP_RESAMPLES",
    "BOOTSTRAP_SEED",
    "HOLDOUT_INTERVALS",
    "INITIAL_CAPITAL",
    "InputContractError",
    "PROGRAM_ALPHA",
    "RESEARCH_ID",
    "VALIDATION_INTERVALS",
    "bootstrap_inference",
    "circular_block_indices",
    "holdout_decision",
    "validation_decision",
]
