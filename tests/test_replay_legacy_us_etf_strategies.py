from __future__ import annotations

from datetime import date, timedelta
import hashlib
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


def _frozen_market() -> object:
    middle = tuple(
        legacy.FROZEN_EXPECTED_FIRST_SESSION + timedelta(days=index)
        for index in range(1, legacy.FROZEN_EXPECTED_SESSION_COUNT - 1)
    )
    sessions = (
        legacy.FROZEN_EXPECTED_FIRST_SESSION,
        *middle,
        legacy.FROZEN_EXPECTED_LAST_SESSION,
    )
    return legacy.MarketSlice(
        sessions,
        _closes(legacy.FROZEN_EXPECTED_SESSION_COUNT),
        legacy.FROZEN_EXPECTED_SNAPSHOT_ID,
        legacy.FROZEN_EXPECTED_ROW_COUNT,
        legacy.FROZEN_EXPECTED_SLICE_SHA256,
        legacy.FROZEN_EXPECTED_ROW_COUNT,
    )


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
    report = legacy.build_report(_frozen_market())
    assert set(report["results"]) == set(legacy.STRATEGIES)
    assert report["classification"] == "RETROSPECTIVE_MIGRATION_CONSISTENCY_ONLY"
    assert report["evidence_state"] == "FROZEN_ONE_OFF_EVIDENCE"
    assert report["generalization_allowed"] is False
    assert report["generalization_policy"] == "NO_GENERALIZATION"
    assert report["boundary_counts_exact"] is True
    assert "coverage_exact" not in report
    assert report["input_slice_hash_exact"] is True
    assert report["snapshot_id_exact"] is True
    assert report["mismatch_reasons"] == []
    assert report["strict_pit_eligible"] is False
    assert report["strategy_evidence_eligible"] is False
    assert report["strategy_candidate_available"] is False
    assert report["headline_metrics_reproduced"] is False
    assert report["status"] == "REPLAY_COMPLETE_HEADLINES_NOT_REPRODUCED"
    assert "remain rejected" in " ".join(report["limitations"])


@pytest.mark.parametrize(
    ("mismatch", "expected_reason"),
    [
        ("boundary", "boundary_counts_mismatch"),
        ("slice_hash", "input_slice_hash_mismatch"),
        ("snapshot", "snapshot_id_mismatch"),
    ],
)
def test_each_identity_mismatch_blocks_replay_and_headline_comparison(
    monkeypatch, mismatch: str, expected_reason: str
) -> None:
    exact = _frozen_market()
    assert isinstance(exact, legacy.MarketSlice)
    market = legacy.MarketSlice(
        exact.sessions,
        exact.closes,
        "different-snapshot" if mismatch == "snapshot" else exact.snapshot_id,
        exact.row_count + 1 if mismatch == "boundary" else exact.row_count,
        "b" * 64 if mismatch == "slice_hash" else exact.slice_sha256,
        exact.available_at_missing,
    )
    def forbidden_replay(*_args, **_kwargs):
        raise AssertionError("replay must not run for an identity mismatch")

    monkeypatch.setattr(legacy, "replay", forbidden_replay)
    report = legacy.build_report(market)
    assert report["mismatch_reasons"] == [expected_reason]
    assert report["status"] == "INPUT_SLICE_MISMATCH"
    assert report["results"] is None
    assert report["headline_metrics_reproduced"] is None
    assert report["legacy_headline_drift"] is None


def test_mismatch_reasons_have_a_deterministic_order(monkeypatch) -> None:
    exact = _frozen_market()
    assert isinstance(exact, legacy.MarketSlice)
    market = legacy.MarketSlice(
        exact.sessions,
        exact.closes,
        "different-snapshot",
        exact.row_count + 1,
        "b" * 64,
        exact.available_at_missing,
    )
    monkeypatch.setattr(
        legacy,
        "replay",
        lambda *_args, **_kwargs: pytest.fail("mismatched input must not be replayed"),
    )
    report = legacy.build_report(market)
    assert report["mismatch_reasons"] == [
        "boundary_counts_mismatch",
        "input_slice_hash_mismatch",
        "snapshot_id_mismatch",
    ]
    assert report["status"] == "INPUT_SLICE_MISMATCH"


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
            row_hash = hashlib.sha256(f"{session}|{symbol}".encode()).hexdigest()
            rows.append((symbol, session, 100 + index, "snapshot", row_hash, None))
    connection.executemany("INSERT INTO us_equity_research.sina_daily_bars VALUES (?,?,?,?,?,?)", rows)
    connection.close()
    before = database.stat().st_mtime_ns
    market = legacy.load_market_slice(database)
    assert market.row_count == 6
    assert market.available_at_missing == 6
    assert database.stat().st_mtime_ns == before


@pytest.mark.parametrize("row_hash", ["a" * 63, "A" * 64, None])
def test_market_loader_rejects_noncanonical_row_sha256(
    tmp_path: Path, row_hash: str | None
) -> None:
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
            rows.append((symbol, session, 100 + index, "snapshot", row_hash, None))
    connection.executemany(
        "INSERT INTO us_equity_research.sina_daily_bars VALUES (?,?,?,?,?,?)", rows
    )
    connection.close()
    with pytest.raises(legacy.ReplayError, match="lowercase 64-hex"):
        legacy.load_market_slice(database)


def test_main_refuses_overwrite(monkeypatch, tmp_path: Path) -> None:
    market = _frozen_market()
    monkeypatch.setattr(legacy, "load_market_slice", lambda _: market)
    output = tmp_path / "result.json"
    assert legacy.main(["--database", str(tmp_path / "unused"), "--output", str(output)]) == 0
    with pytest.raises(legacy.ReplayError, match="already exists"):
        legacy.main(["--database", str(tmp_path / "unused"), "--output", str(output)])
