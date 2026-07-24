from datetime import date
import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "research" / "us_qqq_top50_pit_low_asset_growth_v1.py"
SPEC = importlib.util.spec_from_file_location("low_asset_growth", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _fact(end: str, filed: str, value: float, accession: str) -> tuple:
    day = date.fromisoformat(filed)
    return (
        "A",
        "us-gaap",
        "Assets",
        "USD",
        value,
        date.fromisoformat(end),
        day,
        day,
        accession,
        accession,
    )


def test_asset_growth_is_strictly_point_in_time_and_revision_aware() -> None:
    rows = [
        _fact("2022-12-31", "2023-02-01", 100, "a"),
        _fact("2023-12-31", "2024-02-01", 120, "b"),
        _fact("2023-12-31", "2024-03-01", 110, "c"),
    ]
    assert MODULE._asset_growth(rows, date(2024, 2, 1)) is None
    assert MODULE._asset_growth(rows, date(2024, 2, 2)) == pytest.approx(0.2)
    assert MODULE._asset_growth(rows, date(2024, 3, 2)) == pytest.approx(0.1)


def test_rank_uses_average_tie_ranks() -> None:
    assert MODULE._rank([3.0, 1.0, 1.0, 2.0]) == [4.0, 1.5, 1.5, 3.0]


def test_simulation_charges_entry_and_excludes_entry_from_turnover_gate() -> None:
    start = date(2024, 1, 2)
    end = date(2024, 1, 3)
    selected = [f"S{index:02d}" for index in range(15)]
    prices = {symbol: {start: 10.0, end: 10.0} for symbol in selected}
    qqq = {start: 100.0, end: 100.0}
    formations = [{"execution_date": start, "selected": selected}]
    calendar, nav, benchmark, turnover = MODULE._simulate(prices, qqq, formations, end, 15)
    assert calendar == [start, end]
    assert nav[0] < 1.0
    assert benchmark[0] == 0.9998
    assert turnover == [0.0]


def test_subperiods_cover_calendar_without_overlap() -> None:
    calendar = [date(2024, 1, day) for day in range(1, 7)]
    strategy = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5]
    benchmark = [1.0] * 6
    rows = MODULE._subperiods(strategy, benchmark, calendar)
    assert [(row["start"], row["end"]) for row in rows] == [
        (calendar[0], calendar[1]),
        (calendar[2], calendar[3]),
        (calendar[4], calendar[5]),
    ]
