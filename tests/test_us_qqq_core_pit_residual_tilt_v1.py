from __future__ import annotations

from datetime import date
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(
    0,
    str(ROOT / "research/archive/us_qqq_core_pit_residual_tilt_v1/scripts"),
)

import us_qqq_core_pit_residual_tilt_v1 as research  # noqa: E402


def test_residual_score_prefers_positive_residual_mean() -> None:
    market = [(-1) ** index * 0.01 for index in range(500)]
    estimate = [0.001 + 1.2 * value for value in market]
    signal_market = market[:230]
    positive = [0.002 + 1.2 * value + (index % 3) * 0.0001 for index, value in enumerate(signal_market)]
    negative = [-0.002 + 1.2 * value + (index % 3) * 0.0001 for index, value in enumerate(signal_market)]

    assert research.residual_score(estimate, market, positive, signal_market) > 0
    assert research.residual_score(estimate, market, negative, signal_market) < 0


def test_rank_15_buffer_is_retained() -> None:
    scores = {f"S{index:02d}": float(30 - index) for index in range(30)}
    prior = ["S14", "S20"]

    selected = research.select_holdings(scores, prior)

    assert "S14" in selected
    assert "S20" not in selected
    assert len(selected) == 10


def test_initial_portfolio_is_90_10_and_turnover_one() -> None:
    day1, day2 = date(2024, 1, 2), date(2024, 1, 3)
    symbols = ["QQQ", *[f"S{index}" for index in range(10)]]
    prices = {
        symbol: {day1: 10.0, day2: 11.0} for symbol in symbols
    }
    target = {"QQQ": 0.9, **{symbol: 0.01 for symbol in symbols[1:]}}

    dates, nav, turnover = research.simulate(
        [day1, day2], prices, {day1: target}, 0.0015
    )

    assert dates == [day1, day2]
    assert turnover[0]["one_way_turnover"] == pytest.approx(1.0)
    assert nav[0] == pytest.approx(0.9985)
    assert nav[1] == pytest.approx(0.9985 * 1.1)


def test_split_indices_cover_all_rows_once() -> None:
    assert research.split_indices(10) == [(0, 4), (4, 7), (7, 10)]
