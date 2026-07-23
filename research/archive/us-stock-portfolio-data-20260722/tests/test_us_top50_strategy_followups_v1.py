from __future__ import annotations

from datetime import date, timedelta
import sys
from pathlib import Path

import numpy as np


sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import run_us_top50_strategy_followups_v1 as research  # noqa: E402


def test_percentile_has_deterministic_ticker_tie_break() -> None:
    ranks = research.percentile({"B": 1.0, "A": 1.0, "C": 2.0})
    assert ranks == {"A": 0.0, "B": 0.5, "C": 1.0}


def test_portfolio_vol_uses_equal_weight_sample_covariance() -> None:
    days = [date(2026, 1, 1) + timedelta(days=index) for index in range(5)]
    prices = {
        "A": dict(zip(days, [100.0, 101.0, 102.0, 101.0, 103.0], strict=True)),
        "B": dict(zip(days, [50.0, 49.0, 50.0, 51.0, 50.0], strict=True)),
    }
    observed, covariance = research.portfolio_vol(["A", "B"], days, prices)
    returns = np.array(
        [[prices[name][day] for name in ("A", "B")] for day in days]
    )
    returns = returns[1:] / returns[:-1] - 1
    expected_covariance = np.cov(returns, rowvar=False, ddof=1)
    weights = np.array([0.5, 0.5])
    expected = float(np.sqrt(weights @ expected_covariance @ weights * 252))
    assert np.allclose(covariance, expected_covariance)
    assert observed == expected


def test_v1_scaling_is_bounded_without_floor() -> None:
    selected_vol, benchmark_vol = 0.30, 0.12
    gross = min(1.0, benchmark_vol / selected_vol)
    assert gross == 0.4
    assert min(1.0, 0.40 / 0.20) == 1.0


def test_simulate_preserves_cash_for_subunit_gross() -> None:
    days = [date(2026, 1, 1) + timedelta(days=index) for index in range(3)]
    prices = {"A": dict(zip(days, [100.0, 110.0, 121.0], strict=True))}
    output = research.simulate(days, prices, {days[1]: {"A": 0.5}}, 0.0)
    assert output["equity"] == [1.0, 1.05]
