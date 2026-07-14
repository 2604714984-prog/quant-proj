import math

import pytest

import quant_system.research.stats as stats_module
from quant_system.research.stats import (
    circular_block_bootstrap_greater_mean_test,
    circular_block_bootstrap_indices,
    circular_block_bootstrap_means,
    deflated_sharpe_ratio,
    expected_maximum_sharpe,
    newey_west_mean_test,
    overlapping_ic_hac_test,
    probabilistic_sharpe_ratio,
    probability_of_backtest_overfitting,
)


def test_probabilistic_and_deflated_sharpe_have_fixed_reference_values() -> None:
    assert probabilistic_sharpe_ratio(
        0.5,
        benchmark_sharpe=0.0,
        sample_size=60,
    ) == pytest.approx(0.9998532252336905)

    result = deflated_sharpe_ratio(
        0.5,
        trial_sharpes=(-0.1, 0.0, 0.1, 0.2),
        effective_independent_trial_count=4,
        sample_size=60,
    )
    assert result.attempted_trial_count == 4
    assert result.effective_independent_trial_count == 4.0
    assert result.expected_maximum_sharpe == pytest.approx(0.18582847247946879)
    assert result.probability == pytest.approx(0.9885525596595458)


def test_expected_maximum_includes_cross_trial_mean_and_effective_count() -> None:
    centered = expected_maximum_sharpe(
        (-0.2, -0.1, 0.0, 0.1),
        effective_independent_trial_count=2.5,
    )
    shifted = expected_maximum_sharpe(
        (0.8, 0.9, 1.0, 1.1),
        effective_independent_trial_count=2.5,
    )

    assert centered.attempted_trial_count == 4
    assert centered.effective_independent_trial_count == 2.5
    assert centered.cross_trial_mean == pytest.approx(-0.05)
    assert shifted.value - centered.value == pytest.approx(1.0)
    assert shifted.cross_trial_standard_deviation == pytest.approx(
        centered.cross_trial_standard_deviation
    )
    single_effective = expected_maximum_sharpe(
        (-0.2, -0.1, 0.0, 0.1),
        effective_independent_trial_count=1,
    )
    assert single_effective.value == pytest.approx(single_effective.cross_trial_mean)
    fractional_effective = expected_maximum_sharpe(
        (-0.2, -0.1, 0.0, 0.1),
        effective_independent_trial_count=1.5,
    )
    assert fractional_effective.effective_independent_trial_count == 1.5
    assert math.isfinite(fractional_effective.value)


@pytest.mark.parametrize("effective_count", [0, float("nan"), 4.1, True])
def test_expected_maximum_rejects_invalid_effective_trial_counts(
    effective_count: object,
) -> None:
    with pytest.raises(ValueError, match="effective_independent_trial_count"):
        expected_maximum_sharpe(
            (-0.1, 0.0, 0.1, 0.2),
            effective_independent_trial_count=effective_count,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (
            lambda: probabilistic_sharpe_ratio(
                float("nan"), benchmark_sharpe=0.0, sample_size=10
            ),
            "finite",
        ),
        (
            lambda: probabilistic_sharpe_ratio(0.1, benchmark_sharpe=0.0, sample_size=2),
            "sample_size",
        ),
        (
            lambda: expected_maximum_sharpe(
                (0.1, 0.1), effective_independent_trial_count=2
            ),
            "variance",
        ),
        (
            lambda: expected_maximum_sharpe(
                (1e308, -1e308), effective_independent_trial_count=2
            ),
            "finite",
        ),
    ],
)
def test_sharpe_statistics_fail_closed(call: object, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        call()  # type: ignore[operator]


def _pbo_matrix() -> tuple[tuple[float, ...], ...]:
    return tuple(
        (
            ((index % 5) - 2) * 0.01 + index * 0.0002,
            (((index * 2) % 7) - 3) * 0.008 - index * 0.0001,
            (((index * 3) % 11) - 5) * 0.005 + 0.001,
        )
        for index in range(12)
    )


def test_pbo_uses_every_observation_and_has_a_deterministic_ranking() -> None:
    result = probability_of_backtest_overfitting(_pbo_matrix(), slice_count=4)

    assert result.probability == 1.0
    assert result.logits == pytest.approx((-math.log(3),) * 6)
    assert result.selected_strategy_indices == (1, 2, 1, 0, 1, 2)
    assert result.combinations_evaluated == 6
    assert result.observations_used == 12
    assert result.observations_dropped == 0
    assert result.relative_ranks == pytest.approx((0.25,) * 6)
    assert result.selection_tie_policy == "fail_closed"
    assert result.rank_tie_policy == "average"
    assert result.overfit_rule == "relative_rank < 0.5"


def test_pbo_uses_average_ranks_and_strictly_below_median_overfit_rule() -> None:
    relative_rank = stats_module._average_relative_rank((0.2, 0.2), selected_index=0)

    assert relative_rank == pytest.approx(0.5)
    assert not relative_rank < 0.5


def test_pbo_fails_closed_on_an_in_sample_selection_tie() -> None:
    identical_strategies = tuple((float(index), float(index)) for index in range(1, 9))

    with pytest.raises(ValueError, match="in-sample maximum is tied"):
        probability_of_backtest_overfitting(identical_strategies, slice_count=4)


def test_pbo_is_invariant_to_strategy_column_permutation() -> None:
    matrix = _pbo_matrix()
    permutation = (2, 0, 1)
    permuted_matrix = tuple(
        tuple(row[index] for index in permutation)
        for row in matrix
    )

    original = probability_of_backtest_overfitting(matrix, slice_count=4)
    permuted = probability_of_backtest_overfitting(permuted_matrix, slice_count=4)

    assert permuted.probability == original.probability
    assert permuted.logits == pytest.approx(original.logits)
    assert permuted.relative_ranks == pytest.approx(original.relative_ranks)
    assert tuple(
        permutation[index] for index in permuted.selected_strategy_indices
    ) == original.selected_strategy_indices


def test_pbo_rejects_a_nondivisible_tail_and_degenerate_split() -> None:
    with pytest.raises(ValueError, match="exactly divisible"):
        probability_of_backtest_overfitting(_pbo_matrix()[:10], slice_count=4)
    with pytest.raises(ValueError, match="variance"):
        probability_of_backtest_overfitting(((1.0, 2.0),) * 8, slice_count=4)
    large = tuple((float(index), float(-index)) for index in range(20))
    with pytest.raises(ValueError, match="maximum is 50000"):
        probability_of_backtest_overfitting(large, slice_count=20)


def test_newey_west_lag_zero_matches_the_direct_population_autocovariance() -> None:
    values = (1.0, -0.5, 0.25, 0.75, -0.25, 0.5)
    result = newey_west_mean_test(values, max_lag=0)
    centered = tuple(value - sum(values) / len(values) for value in values)
    expected_se = math.sqrt(sum(value * value for value in centered) / len(values) ** 2)

    assert result.mean == pytest.approx(7 / 24)
    assert result.standard_error == pytest.approx(expected_se)
    assert result.statistic == pytest.approx(result.mean / expected_se)
    assert result.sample_size == 6
    assert result.max_lag == 0


def test_overlapping_ic_maps_overlap_to_the_frozen_hac_lag() -> None:
    values = (0.02, -0.01, 0.03, 0.01, -0.02, 0.04, 0.01, 0.02)
    result = overlapping_ic_hac_test(values, overlap=3)
    assert result.max_lag == 2
    assert result.sample_size == len(values)
    assert 0.0 <= result.two_sided_p_value <= 1.0


@pytest.mark.parametrize(
    "call",
    [
        lambda: newey_west_mean_test((1.0, 1.0, 1.0), max_lag=0),
        lambda: newey_west_mean_test((1.0, 2.0, float("inf")), max_lag=0),
        lambda: newey_west_mean_test((1.0, 2.0, 3.0), max_lag=3),
        lambda: overlapping_ic_hac_test((0.1, 0.2, 0.3), overlap=0),
    ],
)
def test_hac_statistics_fail_closed(call: object) -> None:
    with pytest.raises(ValueError):
        call()  # type: ignore[operator]


def test_circular_block_bootstrap_has_an_independent_golden_index_vector() -> None:
    indices = circular_block_bootstrap_indices(
        7,
        block_length=3,
        replications=4,
        seed=6801,
    )
    assert indices == (
        (1, 2, 3, 0, 1, 2, 5),
        (0, 1, 2, 0, 1, 2, 4),
        (2, 3, 4, 0, 1, 2, 2),
        (1, 2, 3, 4, 5, 6, 4),
    )


def test_circular_block_bootstrap_wraps_concatenates_and_truncates() -> None:
    values = (0.01, -0.02, 0.03, 0.04, -0.01, 0.05, 0.02)
    means = circular_block_bootstrap_means(
        values,
        block_length=3,
        replications=4,
        seed=6801,
    )
    assert means == pytest.approx(
        (0.017142857142857144, 0.004285714285714286, 0.015714285714285715, 0.014285714285714287)
    )


def test_bootstrap_means_stream_indices_instead_of_using_public_matrix_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        stats_module,
        "circular_block_bootstrap_indices",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("matrix helper called")),
    )
    means = circular_block_bootstrap_means(
        (0.01, -0.02, 0.03, 0.04, -0.01, 0.05, 0.02),
        block_length=3,
        replications=4,
        seed=6801,
    )
    assert len(means) == 4


def test_null_centered_bootstrap_is_one_sided_and_reproducible() -> None:
    values = (0.01, -0.02, 0.03, 0.04, -0.01, 0.05, 0.02)
    first = circular_block_bootstrap_greater_mean_test(
        values,
        null_mean=0.0,
        block_length=3,
        replications=99,
        seed=6801,
    )
    second = circular_block_bootstrap_greater_mean_test(
        values,
        null_mean=0.0,
        block_length=3,
        replications=99,
        seed=6801,
    )
    assert first == second
    assert first.observed_mean_difference == pytest.approx(0.017142857142857144)
    assert first.greater_p_value == 0.01
    assert first.null_mean == 0.0


def test_bootstrap_rejects_zero_variance_and_invalid_rng_parameters() -> None:
    with pytest.raises(ValueError, match="variance"):
        circular_block_bootstrap_means((1.0, 1.0, 1.0), block_length=2, replications=2, seed=1)
    with pytest.raises(ValueError, match="block_length"):
        circular_block_bootstrap_indices(3, block_length=4, replications=2, seed=1)
    with pytest.raises(ValueError, match="seed"):
        circular_block_bootstrap_indices(3, block_length=2, replications=2, seed=-1)
    with pytest.raises(ValueError, match="maximum is 100000"):
        circular_block_bootstrap_indices(2, block_length=1, replications=50_001, seed=1)
    with pytest.raises(ValueError, match="maximum is 10000000"):
        circular_block_bootstrap_means(
            (0.0, 1.0),
            block_length=1,
            replications=5_000_001,
            seed=1,
        )
