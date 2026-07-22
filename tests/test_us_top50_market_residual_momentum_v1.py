from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import us_top50_market_residual_momentum_v1 as research  # noqa: E402


def test_residual_score_uses_frozen_out_of_sample_beta() -> None:
    market_estimate = np.linspace(-0.02, 0.02, 504)
    stock_estimate = 0.0003 + 1.25 * market_estimate
    market_signal = np.linspace(-0.015, 0.015, 232)
    residual = np.tile(np.array([-0.001, 0.003]), 116)
    stock_signal = 0.0003 + 1.25 * market_signal + residual
    observed = research.residual_score(
        stock_estimate,
        market_estimate,
        stock_signal,
        market_signal,
    )
    expected = float(np.mean(residual) / np.std(residual, ddof=1) * np.sqrt(252))
    assert observed is not None
    assert np.isclose(observed, expected)


def test_residual_score_fails_closed_on_short_windows() -> None:
    assert research.residual_score(
        np.ones(449),
        np.ones(449),
        np.ones(232),
        np.ones(232),
    ) is None
    assert research.residual_score(
        np.ones(504),
        np.ones(504),
        np.ones(219),
        np.ones(219),
    ) is None


def test_frozen_window_indexing_has_504_and_232_returns() -> None:
    days = [date(2020, 1, 1) + timedelta(days=index) for index in range(800)]
    prices = {
        name: {
            day: float(index + offset)
            for index, day in enumerate(days, 100)
        }
        for name, offset in (("A", 0), ("SPY", 10))
    }
    estimate = research.paired_returns("A", 43, 547, days, prices)
    signal = research.paired_returns("A", 547, 779, days, prices)
    assert len(estimate[0]) == len(estimate[1]) == 504
    assert len(signal[0]) == len(signal[1]) == 232


def test_rank_buffer_retains_existing_names_through_rank_15() -> None:
    scores = {f"S{index:02d}": float(20 - index) for index in range(20)}
    prior = ["S14", "S10", "S18"]
    selected = research.select_holdings(scores, prior)
    assert selected[:2] == ["S14", "S10"]
    assert "S18" not in selected
    assert len(selected) == 10


def test_preserved_contract_and_terminal_result_are_exact_and_closed() -> None:
    contract = ROOT / "research/definitions/us_top50_market_residual_momentum_v1.json"
    result = ROOT / "research/reports/us_top50_market_residual_momentum_v1_discovery_fail.json"
    assert hashlib.sha256(contract.read_bytes()).hexdigest() == research.CONTRACT_SHA256
    assert hashlib.sha256(result.read_bytes()).hexdigest() == (
        "76a3ba2c59c452da232f8eed6c7d1e6da17767999ae1c3771fc3bae2d05e5f04"
    )
    payload = json.loads(result.read_text(encoding="utf-8"))
    assert payload["result"] == "DISCOVERY_FAIL"
    assert payload["permanently_closed"] is True
    assert payload["gates"]["turnover"] is False
    assert payload["strategy_candidate_available"] is False
