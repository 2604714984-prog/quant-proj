from datetime import date, timedelta
import json
from pathlib import Path

import pytest

from quant_system.research.us_employment_release_intraday import (
    DailyBar,
    ResearchInputError,
    build_observations,
    circular_block_lower_bound,
    frozen_monthly_release_dates,
)


DEFINITION = (
    Path(__file__).parents[1]
    / "research"
    / "definitions"
    / "us_employment_release_day_spy_intraday_premium_v1.json"
)


def test_frozen_monthly_release_dates_selects_first_release_date() -> None:
    text = "\n".join(
        [
            "Release Dates:",
            "2024-01-05",
            "2024-01-10",
            "2024-02-02",
            "2024-03-08",
        ]
    )
    assert frozen_monthly_release_dates(
        text, start=date(2024, 1, 1), end=date(2024, 3, 31)
    ) == (date(2024, 1, 5), date(2024, 2, 2), date(2024, 3, 8))


def test_build_observations_uses_month_baseline_and_frozen_closure() -> None:
    start = date(2024, 1, 1)
    bars = []
    for offset in range(23):
        item = start + timedelta(days=offset)
        close = 101.0 if item == date(2024, 1, 10) else 100.2
        bars.append(DailyBar(item, 100.0, close))
    observations, missing = build_observations(
        bars,
        (date(2024, 1, 10), date(2024, 2, 10)),
        expected_closed_dates=(date(2024, 2, 10),),
        round_trip_cost=0.001,
        minimum_non_event_sessions=15,
    )
    assert missing == (date(2024, 2, 10),)
    assert len(observations) == 1
    assert observations[0].gross_return == pytest.approx(0.01)
    assert observations[0].non_event_month_mean == pytest.approx(0.002)
    assert observations[0].net_premium == pytest.approx(0.007)


def test_build_observations_rejects_unfrozen_missing_event() -> None:
    with pytest.raises(ResearchInputError, match="frozen market closures"):
        build_observations(
            [DailyBar(date(2024, 1, 2), 100.0, 101.0)],
            (date(2024, 1, 10),),
            expected_closed_dates=(),
            round_trip_cost=0.001,
            minimum_non_event_sessions=1,
        )


def test_circular_block_lower_bound_is_deterministic() -> None:
    kwargs = {
        "block_length": 2,
        "replications": 1000,
        "seed": 17,
        "quantile": 0.025,
    }
    first = circular_block_lower_bound((0.01, 0.02, -0.01, 0.03), **kwargs)
    second = circular_block_lower_bound((0.01, 0.02, -0.01, 0.03), **kwargs)
    assert first == second
    assert first == pytest.approx(0.005)
    assert circular_block_lower_bound((0.02,) * 5, **kwargs) == pytest.approx(0.02)


def test_definition_freezes_one_complete_event_list() -> None:
    definition = json.loads(DEFINITION.read_text())
    events = definition["data_contract"]["event_dates"]
    assert definition["lineage"]["variants"] == 1
    assert len(events) == len(set(events)) == 108
    assert events[0] == "2016-01-08"
    assert events[-1] == "2024-12-06"
    assert not {"2020-05-11", "2024-01-10", "2024-08-21"} & set(events)
    assert set(definition["event_identity"]["excluded_noninitial_alfred_dates"]) == {
        "2020-05-11",
        "2024-01-10",
        "2024-08-21",
    }
    assert definition["data_contract"]["expected_closed_release_dates"] == [
        "2021-04-02",
        "2023-04-07",
    ]
    assert definition["strategy_candidate_available"] is False
