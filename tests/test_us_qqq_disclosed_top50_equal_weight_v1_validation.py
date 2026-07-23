from __future__ import annotations

from datetime import date
from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(
    0,
    str(
        REPO_ROOT
        / "research/archive/us_qqq_disclosed_top50_equal_weight_v1/scripts"
    ),
)

import validate_us_qqq_disclosed_top50_equal_weight_v1 as validation  # noqa: E402


def test_metrics_include_initial_cost() -> None:
    calendar = [date(2020, 1, 2), date(2021, 1, 4)]
    nav = [0.99, 1.10]

    metrics = validation._metrics(nav, calendar)

    assert validation._returns(nav)[0] == pytest.approx(-0.01)
    assert metrics["total_return"] == pytest.approx(0.10)


def test_turnover_includes_initial_cash() -> None:
    calendar = [date(2020, 1, 2), date(2020, 1, 3)]
    exact_prices = {
        "AAA": {
            date(2020, 1, 2): 10.0,
            date(2020, 1, 3): 11.0,
        }
    }
    formations = [
        {
            "execution_date": "2020-01-02",
            "priced_position_count": 50,
            "target_weights": {"AAA": 1.0},
        }
    ]

    nav, turnover = validation._simulate(
        exact_prices, calendar, formations, 0.0015
    )

    assert turnover[0]["one_way_turnover"] == pytest.approx(1.0)
    assert nav[0] == pytest.approx(0.9985)
    assert nav[1] == pytest.approx(0.9985 * 1.1)


def test_bootstrap_is_deterministic() -> None:
    calendar = [
        date(2020 + index // 12, index % 12 + 1, 28) for index in range(18)
    ]
    strategy = [1.01**index for index in range(18)]
    qqq = [1.005**index for index in range(18)]

    first = validation._bootstrap_monthly_excess(strategy, qqq, calendar)
    second = validation._bootstrap_monthly_excess(strategy, qqq, calendar)

    assert first == second
