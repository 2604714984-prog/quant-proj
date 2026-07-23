from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import sys

import numpy as np


sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import run_us_top50_residual_profitability_v1 as research  # noqa: E402


def test_residual_score_uses_frozen_out_of_sample_beta() -> None:
    market_estimate = np.linspace(-0.02, 0.02, 504)
    stock_estimate = 0.0003 + 1.25 * market_estimate
    market_signal = np.linspace(-0.015, 0.015, 232)
    residual = np.tile(np.array([-0.001, 0.003]), 116)
    stock_signal = 0.0003 + 1.25 * market_signal + residual
    observed = research.residual_score(
        stock_estimate, market_estimate, stock_signal, market_signal
    )
    expected = float(np.mean(residual) / np.std(residual, ddof=1) * np.sqrt(252))
    assert observed is not None
    assert np.isclose(observed, expected)


def test_residual_score_fails_closed_on_short_windows() -> None:
    assert research.residual_score(
        np.ones(449), np.ones(449), np.ones(232), np.ones(232)
    ) is None
    assert research.residual_score(
        np.ones(504), np.ones(504), np.ones(219), np.ones(219)
    ) is None


def test_frozen_window_indexing_has_504_and_232_returns() -> None:
    days = [date(2020, 1, 1) + timedelta(days=index) for index in range(800)]
    prices = {
        name: {day: float(index + offset) for index, day in enumerate(days, 100)}
        for name, offset in (("A", 0), ("SPY", 10))
    }
    estimate = research.paired_returns("A", 43, 547, days, prices)
    signal = research.paired_returns("A", 547, 779, days, prices)
    assert len(estimate[0]) == len(estimate[1]) == 504
    assert len(signal[0]) == len(signal[1]) == 232
