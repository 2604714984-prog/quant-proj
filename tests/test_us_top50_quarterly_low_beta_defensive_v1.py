from __future__ import annotations

from datetime import date, timedelta
import hashlib
import math
from pathlib import Path
import sys


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import us_top50_quarterly_low_beta_defensive_v1 as research  # noqa: E402


def test_market_beta_recovers_frozen_ols_slope() -> None:
    market = [-0.02 + index * 0.04 / 251 for index in range(252)]
    stock = [0.0004 + 0.65 * value for value in market]
    observed = research.market_beta(stock, market)
    assert observed is not None
    assert math.isclose(observed, 0.65, rel_tol=1e-12)


def test_market_beta_fails_closed_on_short_or_degenerate_window() -> None:
    assert research.market_beta([1.0] * 219, [1.0] * 219) is None
    assert research.market_beta([1.0] * 252, [1.0] * 252) is None
    assert research.market_beta([1.0] * 252, [1.0] * 251) is None


def test_frozen_return_window_has_252_observations() -> None:
    days = [date(2020, 1, 1) + timedelta(days=index) for index in range(300)]
    prices = {
        name: {day: float(index + offset) for index, day in enumerate(days, 100)}
        for name, offset in (("A", 0), ("SPY", 10))
    }
    stock, market = research.paired_returns("A", 47, 299, days, prices)
    assert len(stock) == len(market) == 252


def test_only_calendar_quarter_month_ends_form_signals() -> None:
    calendar = [
        date(2026, 2, 27),
        date(2026, 3, 30),
        date(2026, 3, 31),
        date(2026, 4, 1),
        date(2026, 5, 29),
        date(2026, 6, 30),
        date(2026, 7, 1),
    ]
    assert research.is_quarter_end(2, calendar) is True
    assert research.is_quarter_end(5, calendar) is True
    assert research.is_quarter_end(0, calendar) is False
    assert research.is_quarter_end(4, calendar) is False


def test_low_beta_rank_buffer_and_contract_are_frozen() -> None:
    betas = {f"S{index:02d}": float(index) for index in range(25)}
    selected = research.select_holdings(betas, ["S19", "S10", "S21"])
    assert selected[:2] == ["S19", "S10"]
    assert "S21" not in selected
    assert len(selected) == 15
    contract = ROOT / "research/definitions/us_top50_quarterly_low_beta_defensive_v1.json"
    assert hashlib.sha256(contract.read_bytes()).hexdigest() == research.CONTRACT_SHA256
