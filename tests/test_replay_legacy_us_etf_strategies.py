from __future__ import annotations

from datetime import date, timedelta
import importlib.util
from pathlib import Path
import sys

import duckdb
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/replay_legacy_us_etf_strategies.py"
SPEC = importlib.util.spec_from_file_location("legacy_replay", SCRIPT)
assert SPEC and SPEC.loader
legacy = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = legacy
SPEC.loader.exec_module(legacy)


def _closes(length: int = 64) -> dict[str, tuple[float, ...]]:
    return {
        "SPY": tuple(100 + index for index in range(length)),
        "QQQ": tuple(100 + 2 * index for index in range(length)),
        "GLD": tuple(100 + index / 2 for index in range(length)),
    }


def test_replay_is_deterministic_and_costs_apply_at_session_63() -> None:
    weights = {"SPY": 0.5, "QQQ": 0.0, "GLD": 0.5}
    first = legacy.replay(_closes(), weights)
    second = legacy.replay(_closes(), weights)
    assert first == second
    assert first["final_equity"] > legacy.INITIAL_CASH
    flat = {symbol: (100.0,) * 64 for symbol in legacy.SYMBOLS}
    expected_cost = legacy.INITIAL_CASH * legacy.COST_BPS / 10_000 * 2 * 2
    assert legacy.replay(flat, weights)["final_equity"] == pytest.approx(
        legacy.INITIAL_CASH - expected_cost
    )


def test_replay_rejects_bad_weights_and_misaligned_series() -> None:
    with pytest.raises(legacy.ReplayError, match="sum to one"):
        legacy.replay(_closes(), {"SPY": 0.4, "QQQ": 0.0, "GLD": 0.5})
    broken = _closes()
    broken["GLD"] = broken["GLD"][:-1]
    with pytest.raises(legacy.ReplayError, match="common length"):
        legacy.replay(broken, legacy.STRATEGIES["US46_QQQ_GLD_50_50"])


def test_build_report_keeps_rejected_lineage_and_non_pit_boundary() -> None:
    sessions = tuple(date(2025, 1, 1) + timedelta(days=i) for i in range(64))
    market = legacy.MarketSlice(sessions, _closes(), "snapshot", 192, "a" * 64, 192)
    report = legacy.build_report(market)
    assert set(report["results"]) == set(legacy.STRATEGIES)
    assert report["classification"] == "RETROSPECTIVE_MIGRATION_CONSISTENCY_ONLY"
    assert report["strict_pit_eligible"] is False
    assert report["strategy_evidence_eligible"] is False
    assert report["strategy_candidate_available"] is False
    assert report["headline_metrics_reproduced"] is False
    assert report["status"] == "REPLAY_COMPLETE_HEADLINES_NOT_REPRODUCED"
    assert "remain rejected" in " ".join(report["limitations"])


def test_market_loader_uses_read_only_central_shape(tmp_path: Path) -> None:
    database = tmp_path / "market.duckdb"
    connection = duckdb.connect(str(database))
    connection.execute("CREATE SCHEMA us_equity_research")
    connection.execute("""
        CREATE TABLE us_equity_research.sina_daily_bars (
            symbol VARCHAR, trade_date DATE, close DOUBLE, snapshot_id VARCHAR,
            row_sha256 VARCHAR, available_at TIMESTAMPTZ
        )
    """)
    rows = []
    for index in range(2):
        session = date(2025, 1, 2 + index)
        for symbol in legacy.SYMBOLS:
            rows.append((symbol, session, 100 + index, "snapshot", symbol * 16, None))
    connection.executemany("INSERT INTO us_equity_research.sina_daily_bars VALUES (?,?,?,?,?,?)", rows)
    connection.close()
    before = database.stat().st_mtime_ns
    market = legacy.load_market_slice(database)
    assert market.row_count == 6
    assert market.available_at_missing == 6
    assert database.stat().st_mtime_ns == before


def test_main_refuses_overwrite(monkeypatch, tmp_path: Path) -> None:
    market = legacy.MarketSlice(
        tuple(date(2025, 1, 1) + timedelta(days=i) for i in range(64)),
        _closes(), "snapshot", 192, "a" * 64, 192,
    )
    monkeypatch.setattr(legacy, "load_market_slice", lambda _: market)
    output = tmp_path / "result.json"
    assert legacy.main(["--database", str(tmp_path / "unused"), "--output", str(output)]) == 0
    with pytest.raises(legacy.ReplayError, match="already exists"):
        legacy.main(["--database", str(tmp_path / "unused"), "--output", str(output)])
