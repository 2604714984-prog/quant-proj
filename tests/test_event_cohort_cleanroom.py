from __future__ import annotations

from datetime import date
import math

import pytest

from quant_system.research.event_cohort import (
    CohortObservation,
    EventCohortError,
    EventReturnInput,
    SplitWindow,
    aggregate_event_sleeve,
    assign_whole_label_split,
    benjamini_hochberg_adjusted,
    block_bootstrap_summary,
    fixed_two_side_cost_return,
    resolve_event_return,
)


def _event(
    symbol: str = "AAA",
    *,
    entry: float | None = 10.0,
    exit: float | None = 11.0,
    limit_up: bool | None = False,
) -> EventReturnInput:
    return EventReturnInput(
        symbol,
        date(2022, 1, 3),
        date(2022, 1, 4),
        date(2022, 1, 20),
        entry,
        exit,
        limit_up,
    )


def test_whole_label_purge_requires_signal_entry_and_exit_in_one_split() -> None:
    splits = (
        SplitWindow("first", date(2022, 1, 1), date(2022, 1, 31)),
        SplitWindow("second", date(2022, 2, 1), date(2022, 2, 28)),
    )

    assert assign_whole_label_split(
        date(2022, 1, 3), date(2022, 1, 4), date(2022, 1, 20), splits
    ) == "first"
    assert assign_whole_label_split(
        date(2022, 1, 20), date(2022, 1, 21), date(2022, 2, 8), splits
    ) is None
    assert assign_whole_label_split(
        date(2021, 12, 1), date(2021, 12, 2), date(2021, 12, 20), splits
    ) is None

    with pytest.raises(EventCohortError, match="chronological"):
        assign_whole_label_split(
            date(2022, 1, 3), date(2022, 1, 4), date(2022, 1, 20), splits[::-1]
        )


def test_event_return_cost_limit_up_and_incomplete_semantics_are_exact() -> None:
    assert fixed_two_side_cost_return(0.10, bps_per_side=100) == pytest.approx(0.08)
    assert resolve_event_return(
        _event(), cash_gross_return=0.02, bps_per_side=100
    ) == pytest.approx(0.08)
    assert resolve_event_return(
        _event(limit_up=True), cash_gross_return=0.02, bps_per_side=100
    ) == pytest.approx(0.0)
    assert resolve_event_return(
        _event(exit=None), cash_gross_return=0.02, bps_per_side=100
    ) is None
    assert resolve_event_return(
        _event(limit_up=None), cash_gross_return=0.02, bps_per_side=100
    ) is None


def test_sleeve_records_incomplete_events_instead_of_hiding_them() -> None:
    aggregate = aggregate_event_sleeve(
        (_event("AAA"), _event("BBB", exit=None), _event("CCC", limit_up=True)),
        cash_gross_return=0.02,
        bps_per_side=100,
    )

    assert aggregate.candidate_count == 3
    assert aggregate.retained_count == 2
    assert aggregate.incomplete_count == 1
    assert aggregate.mean_return == pytest.approx(0.04)


def test_cohort_series_are_arithmetic_return_differences() -> None:
    row = CohortObservation(
        "holdout",
        date(2024, 1, 2),
        date(2024, 1, 3),
        date(2024, 1, 24),
        0.08,
        0.03,
        0.01,
        0.02,
        0.005,
        4,
    )

    assert row.series_value("signal_return") == 0.08
    assert row.series_value("excess_vs_breakout_only") == pytest.approx(0.05)
    assert row.series_value("excess_vs_eligible") == pytest.approx(0.07)
    assert row.series_value("excess_vs_510300") == pytest.approx(0.06)
    assert row.series_value("excess_vs_511880") == pytest.approx(0.075)
    with pytest.raises(EventCohortError, match="unknown series"):
        row.series_value("unknown")


def test_bh_golden_vector_and_tie_order_are_independently_checkable() -> None:
    raw = (0.01, 0.04, 0.03, 0.002, 0.04)
    # Sorted values are .002, .01, .03, .04, .04.  Reverse monotonic
    # adjustment gives .01, .025, .04, .04, .04 and maps back to input order.
    assert benjamini_hochberg_adjusted(raw) == pytest.approx(
        (0.025, 0.04, 0.04, 0.01, 0.04)
    )


def test_block_bootstrap_uses_pcg64_wrapping_and_linear_lower_quantile() -> None:
    values = tuple(float(value) for value in range(1, 24))
    result = block_bootstrap_summary(
        values,
        block_length=20,
        draws=3,
        seed=20260715,
        alpha=0.25,
    )

    expected_means = (
        10.695652173913043,
        10.956521739130435,
        12.521739130434783,
    )
    assert result.observed_mean == 12.0
    assert result.lower_bound == pytest.approx((expected_means[0] + expected_means[1]) / 2)
    assert result.raw_p == 0.25


@pytest.mark.parametrize(
    "factory",
    (
        lambda: _event(entry=math.nan),
        lambda: _event(exit=-1.0),
        lambda: fixed_two_side_cost_return(math.inf, bps_per_side=100),
        lambda: fixed_two_side_cost_return(0.1, bps_per_side=-1),
        lambda: benjamini_hochberg_adjusted((0.1, math.nan)),
    ),
)
def test_nonfinite_or_invalid_inputs_fail_closed(factory) -> None:
    with pytest.raises(EventCohortError):
        factory()
