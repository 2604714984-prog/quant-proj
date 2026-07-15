"""Strict clean-room bootstrap and Holm inference primitives.

The functions are deterministic, preserve caller input order, perform no I/O,
and fail closed if the frozen 20-session block length is changed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Integral, Real
from typing import Sequence

import numpy as np


BLOCK_LENGTH = 20
_DRAW_CHUNK_SIZE = 256
_MAX_START_CELLS = 10_000_000
_MAX_UINT64 = (1 << 64) - 1


def _integer(value: int, *, name: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError(f"{name} must be an integer >= {minimum}")
    parsed = int(value)
    if parsed < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return parsed


def _probability(value: float, *, name: str, allow_endpoints: bool) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite probability")
    parsed = float(value)
    valid = 0.0 <= parsed <= 1.0 if allow_endpoints else 0.0 < parsed < 1.0
    if not math.isfinite(parsed) or not valid:
        raise ValueError(f"{name} must be a finite probability")
    return parsed


def _zero_null_mean(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError("null_mean must equal the frozen value 0.0")
    parsed = float(value)
    if not math.isfinite(parsed) or parsed != 0.0:
        raise ValueError("null_mean must equal the frozen value 0.0")
    return parsed


def _finite_values(
    values: Sequence[float],
    *,
    name: str,
    minimum: int,
) -> np.ndarray:
    try:
        frozen = tuple(values)
    except TypeError as exc:
        raise ValueError(f"{name} must be a one-dimensional numeric sequence") from exc
    if len(frozen) < minimum:
        raise ValueError(f"{name} must contain at least {minimum} observations")
    if any(isinstance(value, bool) or not isinstance(value, Real) for value in frozen):
        raise ValueError(f"{name} must contain only finite numeric values")
    try:
        array = np.asarray(frozen, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must contain only finite numeric values") from exc
    if array.ndim != 1 or not bool(np.isfinite(array).all()):
        raise ValueError(f"{name} must contain only finite numeric values")
    return array


def _frozen_block_length(value: int) -> int:
    parsed = _integer(value, name="block_length", minimum=1)
    if parsed != BLOCK_LENGTH:
        raise ValueError(f"block_length must equal the frozen value {BLOCK_LENGTH}")
    return parsed


def _seed(value: int) -> int:
    parsed = _integer(value, name="seed", minimum=0)
    if parsed > _MAX_UINT64:
        raise ValueError("seed must be an unsigned 64-bit integer")
    return parsed


def _start_matrix(
    sample_size: int,
    *,
    block_length: int,
    draws: int,
    seed: int,
) -> np.ndarray:
    sample_size = _integer(sample_size, name="sample_size", minimum=BLOCK_LENGTH)
    block_length = _frozen_block_length(block_length)
    draws = _integer(draws, name="draws", minimum=1)
    seed = _seed(seed)
    block_count = math.ceil(sample_size / block_length)
    cells = draws * block_count
    if cells > _MAX_START_CELLS:
        raise ValueError(
            f"bootstrap requires {cells} block starts; maximum is {_MAX_START_CELLS}"
        )
    generator = np.random.Generator(np.random.PCG64(seed))
    return generator.integers(
        0,
        sample_size,
        size=(draws, block_count),
        dtype=np.int64,
        endpoint=False,
    )


def circular_block_start_indices(
    sample_size: int,
    *,
    block_length: int = BLOCK_LENGTH,
    draws: int,
    seed: int,
) -> tuple[tuple[int, ...], ...]:
    """Return the exact PCG64 block starts used by the bootstrap."""

    starts = _start_matrix(
        sample_size,
        block_length=block_length,
        draws=draws,
        seed=seed,
    )
    return tuple(tuple(int(value) for value in row) for row in starts)


def _mean(values: np.ndarray) -> float:
    result = math.fsum(float(value) for value in values) / len(values)
    if not math.isfinite(result):
        raise ValueError("derived mean must be finite")
    return result


def _bootstrap_means_from_starts(
    values: np.ndarray,
    starts: np.ndarray,
    *,
    block_length: int,
) -> tuple[float, ...]:
    sample_size = len(values)
    offsets = np.arange(block_length, dtype=np.int64)
    means: list[float] = []
    for first in range(0, len(starts), _DRAW_CHUNK_SIZE):
        chunk = starts[first : first + _DRAW_CHUNK_SIZE]
        indices = (
            (chunk[:, :, None] + offsets[None, None, :]) % sample_size
        ).reshape(len(chunk), -1)[:, :sample_size]
        chunk_means = np.mean(
            values[indices],
            axis=1,
            dtype=np.float64,
        )
        means.extend(float(value) for value in chunk_means)
    return tuple(means)


def circular_moving_block_bootstrap_means(
    values: Sequence[float],
    *,
    block_length: int = BLOCK_LENGTH,
    draws: int,
    seed: int,
) -> tuple[float, ...]:
    """Return uncentered circular moving-block sample means."""

    frozen = _finite_values(values, name="values", minimum=BLOCK_LENGTH)
    block_length = _frozen_block_length(block_length)
    starts = _start_matrix(
        len(frozen),
        block_length=block_length,
        draws=draws,
        seed=seed,
    )
    return _bootstrap_means_from_starts(
        frozen,
        starts,
        block_length=block_length,
    )


def _linear_quantile(values: Sequence[float], probability: float) -> float:
    probability = _probability(probability, name="probability", allow_endpoints=True)
    ordered = sorted(float(value) for value in values)
    if not ordered or any(not math.isfinite(value) for value in ordered):
        raise ValueError("quantile values must be a nonempty finite sequence")
    position = (len(ordered) - 1) * probability
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    weight = position - lower_index
    return ordered[lower_index] + weight * (ordered[upper_index] - ordered[lower_index])


@dataclass(frozen=True)
class BootstrapOneSidedResult:
    observed_mean: float
    raw_p: float
    centered_means: tuple[float, ...]
    null_mean: float
    draws: int
    block_length: int
    seed: int


def bootstrap_one_sided(
    values: Sequence[float],
    *,
    block_length: int = BLOCK_LENGTH,
    draws: int,
    seed: int,
    null_mean: float = 0.0,
) -> BootstrapOneSidedResult:
    """Return null-centered means and the frozen one-sided p-value.

    The p-value is exactly ``(1 + count(centered_mean >= observed_mean)) /
    (draws + 1)``.
    """

    frozen = _finite_values(values, name="values", minimum=BLOCK_LENGTH)
    block_length = _frozen_block_length(block_length)
    draws = _integer(draws, name="draws", minimum=1)
    seed = _seed(seed)
    null_mean = _zero_null_mean(null_mean)
    observed_mean = _mean(frozen)
    starts = _start_matrix(
        len(frozen),
        block_length=block_length,
        draws=draws,
        seed=seed,
    )
    centered_means = _bootstrap_means_from_starts(
        frozen - observed_mean,
        starts,
        block_length=block_length,
    )
    exceedances = sum(mean >= observed_mean for mean in centered_means)
    return BootstrapOneSidedResult(
        observed_mean=observed_mean,
        raw_p=(1.0 + exceedances) / (draws + 1.0),
        centered_means=centered_means,
        null_mean=null_mean,
        draws=draws,
        block_length=block_length,
        seed=seed,
    )


@dataclass(frozen=True)
class HolmAdjustedResult:
    input_index: int
    rank: int
    observed_mean: float
    raw_p: float
    adjusted_p: float
    threshold: float
    lower_bound: float
    rejected: bool


def _validated_bootstrap_result(result: BootstrapOneSidedResult) -> None:
    if not isinstance(result, BootstrapOneSidedResult):
        raise ValueError("results must contain BootstrapOneSidedResult values")
    if not math.isfinite(result.observed_mean):
        raise ValueError("observed_mean must be finite")
    _probability(result.raw_p, name="raw_p", allow_endpoints=True)
    _zero_null_mean(result.null_mean)
    _frozen_block_length(result.block_length)
    draws = _integer(result.draws, name="draws", minimum=1)
    _seed(result.seed)
    centered = _finite_values(
        result.centered_means,
        name="centered_means",
        minimum=1,
    )
    if len(centered) != draws:
        raise ValueError("centered_means length must equal draws")


def apply_holm(
    results: Sequence[BootstrapOneSidedResult],
    *,
    alpha: float = 0.05,
) -> tuple[HolmAdjustedResult, ...]:
    """Apply deterministic Holm step-down and simultaneous lower bounds.

    Equal p-values retain input order. Results are returned in input order. For
    rank ``r`` in a family of size ``m``, ``threshold = alpha / (m-r+1)`` and
    ``lower_bound = observed_mean - Q(centered_means, 1-threshold)`` using the
    linearly interpolated quantile.
    """

    try:
        frozen = tuple(results)
    except TypeError as exc:
        raise ValueError("results must be a nonempty sequence") from exc
    if not frozen:
        raise ValueError("results must be a nonempty sequence")
    for result in frozen:
        _validated_bootstrap_result(result)
    draw_counts = {result.draws for result in frozen}
    if len(draw_counts) != 1:
        raise ValueError("all results must use the same draw count")
    alpha = _probability(alpha, name="alpha", allow_endpoints=False)

    family_size = len(frozen)
    ordered = tuple(sorted(range(family_size), key=lambda index: (frozen[index].raw_p, index)))
    rank_by_index: dict[int, int] = {}
    adjusted_by_index: dict[int, float] = {}
    threshold_by_index: dict[int, float] = {}
    rejected_by_index: dict[int, bool] = {}
    running_adjusted = 0.0
    rejection_open = True
    for offset, index in enumerate(ordered):
        remaining = family_size - offset
        rank = offset + 1
        threshold = alpha / remaining
        raw_p = frozen[index].raw_p
        running_adjusted = max(running_adjusted, min(1.0, remaining * raw_p))
        rejected = rejection_open and raw_p <= threshold
        if not rejected:
            rejection_open = False
        rank_by_index[index] = rank
        adjusted_by_index[index] = running_adjusted
        threshold_by_index[index] = threshold
        rejected_by_index[index] = rejected

    return tuple(
        HolmAdjustedResult(
            input_index=index,
            rank=rank_by_index[index],
            observed_mean=frozen[index].observed_mean,
            raw_p=frozen[index].raw_p,
            adjusted_p=adjusted_by_index[index],
            threshold=threshold_by_index[index],
            lower_bound=frozen[index].observed_mean
            - _linear_quantile(
                frozen[index].centered_means,
                1.0 - threshold_by_index[index],
            ),
            rejected=rejected_by_index[index],
        )
        for index in range(family_size)
    )


__all__ = [
    "BLOCK_LENGTH",
    "BootstrapOneSidedResult",
    "HolmAdjustedResult",
    "apply_holm",
    "bootstrap_one_sided",
    "circular_block_start_indices",
    "circular_moving_block_bootstrap_means",
]
