from __future__ import annotations

import math

import pytest

from quant_system.research.strict_bootstrap import (
    BLOCK_LENGTH,
    BootstrapOneSidedResult,
    apply_holm,
    bootstrap_one_sided,
    circular_block_start_indices,
    circular_moving_block_bootstrap_means,
)


def test_pcg64_nonconstant_golden_starts_and_means() -> None:
    values = tuple(float(value) for value in range(1, 24))

    starts = circular_block_start_indices(
        len(values),
        block_length=20,
        draws=3,
        seed=20260715,
    )
    means = circular_moving_block_bootstrap_means(
        values,
        block_length=20,
        draws=3,
        seed=20260715,
    )

    assert BLOCK_LENGTH == 20
    assert starts == ((16, 3), (11, 0), (11, 12))
    assert means == pytest.approx(
        (10.695652173913043, 10.956521739130435, 12.521739130434783)
    )


def test_centered_null_p_value_is_exact() -> None:
    values = tuple(float(value) / 100.0 for value in range(1, 24))
    result = bootstrap_one_sided(
        values,
        block_length=20,
        draws=9,
        seed=17,
        null_mean=0.0,
    )

    centered = tuple(value - result.observed_mean for value in values)
    expected_means = circular_moving_block_bootstrap_means(
        centered,
        block_length=20,
        draws=9,
        seed=17,
    )
    expected_p = (1 + sum(mean >= result.observed_mean for mean in expected_means)) / 10

    assert result.centered_means == expected_means
    assert result.raw_p == expected_p
    assert result.block_length == 20
    assert result.null_mean == 0.0


@pytest.mark.parametrize(
    ("values", "kwargs"),
    [
        (tuple(range(19)), {"block_length": 20, "draws": 10, "seed": 1}),
        (tuple(range(19)) + (math.nan,), {"block_length": 20, "draws": 10, "seed": 1}),
        (tuple(range(20)), {"block_length": 19, "draws": 10, "seed": 1}),
        (tuple(range(20)), {"block_length": 20, "draws": 0, "seed": 1}),
        (tuple(range(20)), {"block_length": 20, "draws": 10, "seed": -1}),
        (tuple(range(20)), {"block_length": 20, "draws": 10, "seed": True}),
        (
            tuple(range(20)),
            {"block_length": 20, "draws": 10, "seed": 1, "null_mean": 0.01},
        ),
    ],
)
def test_bootstrap_rejects_invalid_inputs(values: tuple[float, ...], kwargs: dict) -> None:
    with pytest.raises(ValueError):
        bootstrap_one_sided(values, **kwargs)


def _result(observed: float, raw_p: float) -> BootstrapOneSidedResult:
    return BootstrapOneSidedResult(
        observed_mean=observed,
        raw_p=raw_p,
        centered_means=(-2.0, -1.0, 0.0, 1.0, 2.0),
        null_mean=0.0,
        draws=5,
        block_length=20,
        seed=1,
    )


def test_holm_ties_keep_input_order_and_bounds_use_exact_upper_quantile() -> None:
    results = apply_holm(
        (_result(0.5, 0.01), _result(10.5, 0.01), _result(20.5, 0.04)),
        alpha=0.05,
    )

    assert tuple(result.input_index for result in results) == (0, 1, 2)
    assert tuple(result.rank for result in results) == (1, 2, 3)
    assert tuple(result.adjusted_p for result in results) == pytest.approx(
        (0.03, 0.03, 0.04)
    )
    assert tuple(result.threshold for result in results) == pytest.approx(
        (0.05 / 3.0, 0.025, 0.05)
    )
    assert tuple(result.lower_bound for result in results) == pytest.approx(
        (0.5 - 29.0 / 15.0, 10.5 - 1.9, 20.5 - 1.8)
    )
    assert all(result.rejected for result in results)


def test_holm_tie_ranks_follow_original_positions_after_a_different_p_value() -> None:
    results = apply_holm(
        (_result(0.0, 0.04), _result(0.0, 0.01), _result(0.0, 0.01)),
        alpha=0.05,
    )

    assert tuple(result.rank for result in results) == (3, 1, 2)


def test_eight_hypothesis_family_uses_frozen_rank_denominators() -> None:
    results = apply_holm(tuple(_result(float(index), 0.001) for index in range(8)))

    assert tuple(result.rank for result in results) == tuple(range(1, 9))
    assert tuple(result.threshold for result in results) == pytest.approx(
        tuple(0.05 / remaining for remaining in range(8, 0, -1))
    )


def test_holm_stops_after_first_failure_and_rejects_bad_inputs() -> None:
    results = apply_holm(
        (_result(0.0, 0.02), _result(0.0, 0.03), _result(0.0, 0.04)),
        alpha=0.05,
    )

    assert not any(result.rejected for result in results)
    assert tuple(result.adjusted_p for result in results) == pytest.approx((0.06, 0.06, 0.06))

    with pytest.raises(ValueError):
        apply_holm(())
    with pytest.raises(ValueError):
        apply_holm((_result(0.0, 1.01),))
    with pytest.raises(ValueError):
        apply_holm(
            (
                _result(0.0, 0.01),
                BootstrapOneSidedResult(0.0, 0.02, (0.0, 1.0), 0.0, 2, 20, 1),
            )
        )
