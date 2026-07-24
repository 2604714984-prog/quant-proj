import datetime as dt

from research.us_top50_gp_vs_qqq_audit import (
    circular_block_bootstrap,
    daily_metrics,
    overlap_return_error,
    simulate_qqq,
)


def test_overlap_uses_returns_not_price_level():
    dates = [dt.date(2026, 1, day) for day in range(1, 23)]
    left = {date: 100 + index for index, date in enumerate(dates)}
    right = {date: 200 + 2 * index for index, date in enumerate(dates)}
    error, count = overlap_return_error(left, right)
    assert count == 20
    assert error == 0


def test_qqq_path_charges_entry_and_exit():
    dates = [dt.date(2026, 1, 2), dt.date(2026, 1, 5)]
    path = simulate_qqq({dates[0]: 100, dates[1]: 110}, dates, 0.001)
    assert path[0] == (dates[0], 1.0)
    assert abs(path[1][1] - 0.999) < 1e-12
    assert abs(path[-1][1] - 0.999 * 1.1 * 0.999) < 1e-12


def test_daily_metrics_include_same_day_cost_events():
    date = dt.date(2025, 1, 2)
    path = [
        (date, 1.0),
        (date, 0.99),
        (dt.date(2026, 1, 2), 1.089),
    ]
    result = daily_metrics(path)
    assert abs(result["total_return"] - 0.089) < 1e-12


def test_block_bootstrap_is_deterministic():
    values = [0.01, -0.01, 0.02, 0.0, 0.03, -0.02]
    first = circular_block_bootstrap(values, 3, 1000, 7)
    second = circular_block_bootstrap(values, 3, 1000, 7)
    assert first == second
