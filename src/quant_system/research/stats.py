"""Dependency-light statistics for preregistered quantitative research.

The module deliberately contains no experiment registry, strategy selection, or
data-access code. Callers must supply already frozen inputs and multiplicity
counts.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import combinations
from typing import Sequence


_EULER_MASCHERONI = 0.5772156649015329
_MAX_BOOTSTRAP_DRAW_CELLS = 10_000_000
_MAX_EXPOSED_INDEX_CELLS = 100_000
_MAX_PBO_COMBINATIONS = 50_000
_UINT32_RANGE = 1 << 32
_UINT64_MASK = (1 << 64) - 1


def _require_int(value: int, *, name: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _finite_values(values: Sequence[float], *, name: str, minimum: int = 2) -> tuple[float, ...]:
    try:
        frozen = tuple(float(value) for value in values)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must contain only finite numeric values") from exc
    if len(frozen) < minimum:
        raise ValueError(f"{name} must contain at least {minimum} observations")
    if any(not math.isfinite(value) for value in frozen):
        raise ValueError(f"{name} must contain only finite values")
    return frozen


def _mean(values: Sequence[float]) -> float:
    try:
        result = math.fsum(values) / len(values)
    except OverflowError as exc:
        raise ValueError("derived mean is nonfinite") from exc
    if not math.isfinite(result):
        raise ValueError("derived mean is nonfinite")
    return result


def _sample_variance(values: Sequence[float]) -> float:
    mean = _mean(values)
    try:
        result = math.fsum((value - mean) ** 2 for value in values) / (len(values) - 1)
    except OverflowError as exc:
        raise ValueError("sample variance must be finite and positive") from exc
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError("sample variance must be finite and positive")
    return result


def _normal_cdf(value: float) -> float:
    return 0.5 * math.erfc(-value / math.sqrt(2.0))


def _inverse_normal_cdf(probability: float) -> float:
    """Acklam's rational approximation to the standard-normal quantile."""

    if not math.isfinite(probability) or not 0.0 < probability < 1.0:
        raise ValueError("probability must lie strictly between zero and one")
    a = (
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    )
    b = (
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    )
    c = (
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    )
    d = (
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    )
    lower = 0.02425
    upper = 1.0 - lower
    if probability < lower:
        q = math.sqrt(-2.0 * math.log(probability))
        return (
            ((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]
        ) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    if probability > upper:
        q = math.sqrt(-2.0 * math.log(1.0 - probability))
        return -(
            ((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]
        ) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    q = probability - 0.5
    r = q * q
    return (
        (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q
    ) / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)


def probabilistic_sharpe_ratio(
    observed_sharpe: float,
    *,
    benchmark_sharpe: float,
    sample_size: int,
    skewness: float = 0.0,
    kurtosis: float = 3.0,
) -> float:
    """Return the probability that a Sharpe ratio exceeds its benchmark.

    ``kurtosis`` is the ordinary (non-excess) kurtosis, so a Gaussian sample
    uses 3.0.
    """

    _require_int(sample_size, name="sample_size", minimum=3)
    inputs = (observed_sharpe, benchmark_sharpe, skewness, kurtosis)
    if any(not math.isfinite(value) for value in inputs):
        raise ValueError("Sharpe inputs and moments must be finite")
    if kurtosis < 1.0:
        raise ValueError("ordinary kurtosis must be at least one")
    denominator_variance = (
        1.0
        - skewness * observed_sharpe
        + ((kurtosis - 1.0) / 4.0) * observed_sharpe**2
    )
    if not math.isfinite(denominator_variance) or denominator_variance <= 0.0:
        raise ValueError("probabilistic Sharpe denominator must be finite and positive")
    statistic = (
        (observed_sharpe - benchmark_sharpe)
        * math.sqrt(sample_size - 1.0)
        / math.sqrt(denominator_variance)
    )
    if not math.isfinite(statistic):
        raise ValueError("probabilistic Sharpe statistic is nonfinite")
    return _normal_cdf(statistic)


@dataclass(frozen=True)
class ExpectedMaximumSharpeResult:
    value: float
    cross_trial_mean: float
    cross_trial_standard_deviation: float
    attempted_trial_count: int
    effective_independent_trial_count: float


def _effective_trial_count(value: float, *, attempted_trial_count: int) -> float:
    if isinstance(value, bool):
        raise ValueError("effective_independent_trial_count must be numeric")
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("effective_independent_trial_count must be numeric") from exc
    if not math.isfinite(parsed) or not 1.0 <= parsed <= attempted_trial_count:
        raise ValueError(
            "effective_independent_trial_count must be finite and lie between 1 and "
            "attempted_trial_count"
        )
    return parsed


def expected_maximum_sharpe(
    trial_sharpes: Sequence[float],
    *,
    effective_independent_trial_count: float,
) -> ExpectedMaximumSharpeResult:
    """Estimate the null maximum from all attempts and an explicit effective count."""

    trials = _finite_values(trial_sharpes, name="trial_sharpes", minimum=2)
    trial_variance = _sample_variance(trials)
    attempted_count = len(trials)
    effective_count = _effective_trial_count(
        effective_independent_trial_count,
        attempted_trial_count=attempted_count,
    )
    trial_mean = _mean(trials)
    trial_standard_deviation = math.sqrt(trial_variance)
    if effective_count == 1.0:
        expected_standard_maximum = 0.0
    else:
        expected_standard_maximum = (
            (1.0 - _EULER_MASCHERONI)
            * _inverse_normal_cdf(1.0 - 1.0 / effective_count)
            + _EULER_MASCHERONI
            * _inverse_normal_cdf(1.0 - 1.0 / (effective_count * math.e))
        )
    result = trial_mean + trial_standard_deviation * expected_standard_maximum
    if not math.isfinite(result):
        raise ValueError("expected maximum Sharpe is nonfinite")
    return ExpectedMaximumSharpeResult(
        value=result,
        cross_trial_mean=trial_mean,
        cross_trial_standard_deviation=trial_standard_deviation,
        attempted_trial_count=attempted_count,
        effective_independent_trial_count=effective_count,
    )


@dataclass(frozen=True)
class DeflatedSharpeResult:
    probability: float
    expected_maximum_sharpe: float
    attempted_trial_count: int
    effective_independent_trial_count: float


def deflated_sharpe_ratio(
    observed_sharpe: float,
    *,
    trial_sharpes: Sequence[float],
    effective_independent_trial_count: float,
    sample_size: int,
    skewness: float = 0.0,
    kurtosis: float = 3.0,
) -> DeflatedSharpeResult:
    """Apply PSR against a threshold derived from all attempted trials."""

    trials = _finite_values(trial_sharpes, name="trial_sharpes", minimum=2)
    threshold = expected_maximum_sharpe(
        trials,
        effective_independent_trial_count=effective_independent_trial_count,
    )
    probability = probabilistic_sharpe_ratio(
        observed_sharpe,
        benchmark_sharpe=threshold.value,
        sample_size=sample_size,
        skewness=skewness,
        kurtosis=kurtosis,
    )
    return DeflatedSharpeResult(
        probability,
        threshold.value,
        threshold.attempted_trial_count,
        threshold.effective_independent_trial_count,
    )


def _sharpe_score(values: Sequence[float]) -> float:
    frozen = _finite_values(values, name="split returns", minimum=2)
    score = _mean(frozen) / math.sqrt(_sample_variance(frozen))
    if not math.isfinite(score):
        raise ValueError("split Sharpe score is nonfinite")
    return score


@dataclass(frozen=True)
class PBOResult:
    probability: float
    logits: tuple[float, ...]
    selected_strategy_indices: tuple[int, ...]
    combinations_evaluated: int
    observations_used: int
    observations_dropped: int
    relative_ranks: tuple[float, ...]
    selection_tie_policy: str
    rank_tie_policy: str
    overfit_rule: str


def _average_relative_rank(scores: Sequence[float], *, selected_index: int) -> float:
    selected_score = scores[selected_index]
    lower_count = math.fsum(score < selected_score for score in scores)
    tie_count = math.fsum(score == selected_score for score in scores)
    average_rank = lower_count + (tie_count + 1.0) / 2.0
    return average_rank / (len(scores) + 1.0)


def probability_of_backtest_overfitting(
    returns_by_observation: Sequence[Sequence[float]],
    *,
    slice_count: int,
) -> PBOResult:
    """Estimate PBO using combinatorially symmetric cross-validation.

    Rows are observations and columns are strategy configurations. The number
    of rows must divide exactly into the requested even number of slices; no
    tail is silently discarded.
    """

    try:
        rows = tuple(tuple(float(value) for value in row) for row in returns_by_observation)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("returns matrix must contain only finite numeric values") from exc
    if len(rows) < 4:
        raise ValueError("returns matrix must contain at least four observations")
    strategy_count = len(rows[0]) if rows else 0
    if strategy_count < 2 or any(len(row) != strategy_count for row in rows):
        raise ValueError("returns matrix must be rectangular with at least two strategies")
    if any(not math.isfinite(value) for row in rows for value in row):
        raise ValueError("returns matrix must contain only finite values")
    _require_int(slice_count, name="slice_count", minimum=4)
    if slice_count % 2 != 0:
        raise ValueError("slice_count must be even")
    if slice_count > len(rows):
        raise ValueError("slice_count cannot exceed the observation count")
    if len(rows) % slice_count != 0:
        raise ValueError("observation count must be exactly divisible by slice_count")
    combination_count = math.comb(slice_count, slice_count // 2)
    if combination_count > _MAX_PBO_COMBINATIONS:
        raise ValueError(
            f"PBO requires {combination_count} combinations; maximum is "
            f"{_MAX_PBO_COMBINATIONS}"
        )

    slice_size = len(rows) // slice_count
    slices = tuple(
        tuple(range(index * slice_size, (index + 1) * slice_size))
        for index in range(slice_count)
    )
    all_slices = set(range(slice_count))
    logits: list[float] = []
    relative_ranks: list[float] = []
    selected: list[int] = []
    for train_slices in combinations(range(slice_count), slice_count // 2):
        train_set = set(train_slices)
        test_slices = tuple(sorted(all_slices - train_set))
        train_rows = tuple(row for group in train_slices for row in slices[group])
        test_rows = tuple(row for group in test_slices for row in slices[group])
        train_scores = tuple(
            _sharpe_score(tuple(rows[row][strategy] for row in train_rows))
            for strategy in range(strategy_count)
        )
        maximum_train_score = max(train_scores)
        train_winners = tuple(
            index for index, score in enumerate(train_scores) if score == maximum_train_score
        )
        if len(train_winners) != 1:
            raise ValueError("PBO in-sample maximum is tied")
        selected_strategy = train_winners[0]
        test_scores = tuple(
            _sharpe_score(tuple(rows[row][strategy] for row in test_rows))
            for strategy in range(strategy_count)
        )
        relative_rank = _average_relative_rank(
            test_scores,
            selected_index=selected_strategy,
        )
        logit = math.log(relative_rank / (1.0 - relative_rank))
        logits.append(logit)
        relative_ranks.append(relative_rank)
        selected.append(selected_strategy)

    probability = math.fsum(relative_rank < 0.5 for relative_rank in relative_ranks) / len(
        relative_ranks
    )
    return PBOResult(
        probability=probability,
        logits=tuple(logits),
        selected_strategy_indices=tuple(selected),
        combinations_evaluated=len(logits),
        observations_used=len(rows),
        observations_dropped=0,
        relative_ranks=tuple(relative_ranks),
        selection_tie_policy="fail_closed",
        rank_tie_policy="average",
        overfit_rule="relative_rank < 0.5",
    )


@dataclass(frozen=True)
class HACMeanResult:
    mean: float
    standard_error: float
    statistic: float
    two_sided_p_value: float
    sample_size: int
    max_lag: int


def newey_west_mean_test(values: Sequence[float], *, max_lag: int) -> HACMeanResult:
    """Test a mean with a Bartlett-kernel Newey-West long-run variance."""

    frozen = _finite_values(values, name="values", minimum=3)
    _require_int(max_lag, name="max_lag", minimum=0)
    if max_lag >= len(frozen):
        raise ValueError("max_lag must be smaller than the sample size")
    mean = _mean(frozen)
    centered = tuple(value - mean for value in frozen)
    sample_size = len(frozen)
    gamma_zero = math.fsum(value * value for value in centered) / sample_size
    long_run_variance = gamma_zero
    for lag in range(1, max_lag + 1):
        autocovariance = math.fsum(
            centered[index] * centered[index - lag] for index in range(lag, sample_size)
        ) / sample_size
        weight = 1.0 - lag / (max_lag + 1.0)
        long_run_variance += 2.0 * weight * autocovariance
    if not math.isfinite(long_run_variance) or long_run_variance <= 0.0:
        raise ValueError("Newey-West long-run variance must be finite and positive")
    standard_error = math.sqrt(long_run_variance / sample_size)
    statistic = mean / standard_error
    if not math.isfinite(standard_error) or not math.isfinite(statistic):
        raise ValueError("Newey-West result is nonfinite")
    p_value = math.erfc(abs(statistic) / math.sqrt(2.0))
    return HACMeanResult(mean, standard_error, statistic, p_value, sample_size, max_lag)


def overlapping_ic_hac_test(ic_values: Sequence[float], *, overlap: int) -> HACMeanResult:
    """Apply HAC inference to an ordered, overlapping information-coefficient series."""

    _require_int(overlap, name="overlap", minimum=1)
    return newey_west_mean_test(ic_values, max_lag=overlap - 1)


class _PCG32:
    """Minimal fixed PCG-XSH-RR generator used only for reproducible resampling."""

    def __init__(self, seed: int) -> None:
        if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= _UINT64_MASK:
            raise ValueError("seed must be an unsigned 64-bit integer")
        self._state = 0
        self._increment = 1442695040888963407
        self._next_uint32()
        self._state = (self._state + seed) & _UINT64_MASK
        self._next_uint32()

    def _next_uint32(self) -> int:
        old_state = self._state
        self._state = (
            old_state * 6364136223846793005 + self._increment
        ) & _UINT64_MASK
        xorshifted = (((old_state >> 18) ^ old_state) >> 27) & 0xFFFFFFFF
        rotation = (old_state >> 59) & 31
        return (
            (xorshifted >> rotation) | (xorshifted << ((-rotation) & 31))
        ) & 0xFFFFFFFF

    def randbelow(self, upper_bound: int) -> int:
        _require_int(upper_bound, name="upper_bound", minimum=1)
        if upper_bound > _UINT32_RANGE:
            raise ValueError("upper_bound exceeds the PCG32 output range")
        rejection_threshold = _UINT32_RANGE % upper_bound
        while True:
            candidate = self._next_uint32()
            if candidate >= rejection_threshold:
                return candidate % upper_bound


def _validate_bootstrap_dimensions(
    sample_size: int,
    *,
    block_length: int,
    replications: int,
    cell_limit: int,
) -> None:
    _require_int(sample_size, name="sample_size", minimum=2)
    _require_int(block_length, name="block_length", minimum=1)
    _require_int(replications, name="replications", minimum=1)
    if block_length > sample_size:
        raise ValueError("block_length cannot exceed sample_size")
    cells = sample_size * replications
    if cells > cell_limit:
        raise ValueError(f"bootstrap work requires {cells} cells; maximum is {cell_limit}")


def _iter_circular_block_bootstrap_indices(
    sample_size: int,
    *,
    block_length: int,
    replications: int,
    seed: int,
):
    generator = _PCG32(seed)
    for _ in range(replications):
        indices: list[int] = []
        while len(indices) < sample_size:
            start = generator.randbelow(sample_size)
            indices.extend((start + offset) % sample_size for offset in range(block_length))
        yield tuple(indices[:sample_size])


def circular_block_bootstrap_indices(
    sample_size: int,
    *,
    block_length: int,
    replications: int,
    seed: int,
) -> tuple[tuple[int, ...], ...]:
    """Expose a bounded fixed-PCG32 index matrix for small golden tests."""

    _validate_bootstrap_dimensions(
        sample_size,
        block_length=block_length,
        replications=replications,
        cell_limit=_MAX_EXPOSED_INDEX_CELLS,
    )
    return tuple(
        _iter_circular_block_bootstrap_indices(
            sample_size,
            block_length=block_length,
            replications=replications,
            seed=seed,
        )
    )


def _iter_circular_block_bootstrap_means(
    values: tuple[float, ...],
    *,
    block_length: int,
    replications: int,
    seed: int,
):
    for replication in _iter_circular_block_bootstrap_indices(
        len(values),
        block_length=block_length,
        replications=replications,
        seed=seed,
    ):
        yield _mean(tuple(values[index] for index in replication))


def circular_block_bootstrap_means(
    values: Sequence[float],
    *,
    block_length: int,
    replications: int,
    seed: int,
) -> tuple[float, ...]:
    """Return generic uncentered circular-block bootstrap sample means."""

    frozen = _finite_values(values, name="values", minimum=2)
    _sample_variance(frozen)
    _validate_bootstrap_dimensions(
        len(frozen),
        block_length=block_length,
        replications=replications,
        cell_limit=_MAX_BOOTSTRAP_DRAW_CELLS,
    )
    return tuple(
        _iter_circular_block_bootstrap_means(
            frozen,
            block_length=block_length,
            replications=replications,
            seed=seed,
        )
    )


@dataclass(frozen=True)
class NullCenteredBootstrapResult:
    observed_mean_difference: float
    greater_p_value: float
    null_mean: float
    replications: int
    block_length: int
    seed: int


def circular_block_bootstrap_greater_mean_test(
    values: Sequence[float],
    *,
    null_mean: float,
    block_length: int,
    replications: int,
    seed: int,
) -> NullCenteredBootstrapResult:
    """One-sided greater-than mean test using a null-centered bootstrap."""

    frozen = _finite_values(values, name="values", minimum=2)
    _sample_variance(frozen)
    if not math.isfinite(null_mean):
        raise ValueError("null_mean must be finite")
    observed_mean = _mean(frozen)
    observed_difference = observed_mean - null_mean
    null_centered = tuple(value - observed_mean + null_mean for value in frozen)
    _validate_bootstrap_dimensions(
        len(null_centered),
        block_length=block_length,
        replications=replications,
        cell_limit=_MAX_BOOTSTRAP_DRAW_CELLS,
    )
    exceedances = math.fsum(
        (bootstrap_mean - null_mean) >= observed_difference
        for bootstrap_mean in _iter_circular_block_bootstrap_means(
            null_centered,
            block_length=block_length,
            replications=replications,
            seed=seed,
        )
    )
    p_value = (exceedances + 1.0) / (replications + 1.0)
    return NullCenteredBootstrapResult(
        observed_mean_difference=observed_difference,
        greater_p_value=p_value,
        null_mean=null_mean,
        replications=replications,
        block_length=block_length,
        seed=seed,
    )
