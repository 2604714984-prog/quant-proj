from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from quant_system.backtest import CapacityObservation, ExecutionInput
from quant_system.data import AcceptedSession, AcceptedSessionCalendar, SourceIdentity
from quant_system.research import swing_structure as swing
from scripts import run_a_share_swing_structure_preflight as preflight


def _source(name: str) -> SourceIdentity:
    now = datetime(2000, 1, 1, tzinfo=timezone.utc)
    return SourceIdentity(f"https://example.test/{name}", hashlib.sha256(name.encode()).hexdigest(), now, now, name)


def _calendar(days: tuple[date, ...]) -> AcceptedSessionCalendar:
    zone = ZoneInfo("Asia/Shanghai")
    return AcceptedSessionCalendar(tuple(AcceptedSession(day, datetime.combine(day, time(9, 30), zone), datetime.combine(day, time(15), zone), _source("calendar"), "Asia/Shanghai") for day in days))


def _rows(days: tuple[date, ...], count: int = 500) -> tuple[swing.SignalBar, ...]:
    # Alternating completed pivots with strictly increasing highs and lows.
    return tuple(swing.SignalBar(day, f"{number:06d}.SZ", 10.0 + index * .1 + (1.0 if index % 2 == 0 else -1.0), 30_000_000.0 if index % 2 == 0 else 10_000_000.0) for number in range(count) for index, day in enumerate(days))


def _inputs(days: tuple[date, ...], count: int = 500) -> tuple[ExecutionInput, ...]:
    session = _calendar(days).session_on(days[-1], as_of=datetime(2000, 1, 1, tzinfo=timezone.utc))
    return tuple(ExecutionInput(f"{i:06d}.SZ", "a_share", 10.0, "CNY", _source(f"open{i}"), (), is_suspended=False, up_limit=11.0, down_limit=9.0, capacity=CapacityObservation(f"{i:06d}.SZ", session, 1_000_000, 100_000_000, "CNY", _source(f"cap{i}"))) for i in range(count))


def _tiny_preflight_database(root: Path) -> tuple[Path, tuple[date, ...], int]:
    import duckdb

    database = root / "quant_research.duckdb"
    connection = duckdb.connect(str(database))
    connection.execute("CREATE SCHEMA a_share")
    connection.execute(
        "CREATE TABLE a_share.a_share_symbol_master("
        "snapshot_id VARCHAR,ts_code VARCHAR,list_date VARCHAR,delist_date VARCHAR,"
        "ingested_at VARCHAR,row_hash VARCHAR,synthetic_data BOOLEAN)"
    )
    connection.execute(
        "INSERT INTO a_share.a_share_symbol_master VALUES "
        "('test-snapshot','000001.SZ','20200101','',"
        "'2025-01-01T00:00:00Z','master:test',false)"
    )
    connection.execute(
        "CREATE TABLE a_share.a_share_trade_calendar("
        "trade_date VARCHAR,is_open INTEGER,exchange VARCHAR,row_hash VARCHAR,"
        "synthetic_data BOOLEAN)"
    )
    connection.execute(
        "CREATE TABLE a_share.a_share_canonical_daily_bars("
        "snapshot_id VARCHAR,ts_code VARCHAR,trade_date VARCHAR,qfq_open DOUBLE,"
        "open DOUBLE,qfq_close DOUBLE,vol DOUBLE,amount DOUBLE,is_st BOOLEAN,"
        "is_suspended BOOLEAN,is_limit_up BOOLEAN,is_limit_down BOOLEAN,"
        "up_limit DOUBLE,down_limit DOUBLE,list_status VARCHAR,quality_status VARCHAR,"
        "row_hash VARCHAR,synthetic_data BOOLEAN)"
    )
    days = (
        date(2025, 1, 22), date(2025, 1, 23), date(2025, 1, 24),
        date(2025, 1, 27), date(2025, 1, 28), date(2025, 1, 29),
        date(2025, 1, 30), date(2025, 1, 31), date(2025, 2, 3),
    )
    quality = "RETROSPECTIVE_PERSONAL_RESEARCH_GRADE_SECONDARY_NOT_STRICT_PIT"
    closes = (10.0, 12.0, 11.0, 13.0, 12.0, 14.0, 13.0, 15.0, 16.0)
    calendar_rows = []
    bar_rows = []
    for index, day in enumerate(days):
        day_text = day.strftime("%Y%m%d")
        calendar_rows.append(
            (day_text, 1, "SSE", hashlib.sha256(f"calendar:{day_text}".encode()).hexdigest(), False)
        )
        stock_hash = hashlib.sha256(f"stock:{day_text}".encode()).hexdigest()
        bar_rows.append(
            ("test-snapshot", "000001.SZ", day_text, closes[index], closes[index],
             closes[index], 20_000_000.0, 30_000_000.0 if index % 2 else 10_000_000.0,
             False, False, False, False, closes[index] * 1.1, closes[index] * .9,
             "L", quality, stock_hash, False)
        )
        benchmark_hash = hashlib.sha256(f"benchmark:{day_text}".encode()).hexdigest()
        bar_rows.append(
            ("test-snapshot", swing.BENCHMARK_SYMBOL, day_text, 4.0, 4.0, 4.0,
             20_000_000.0, 100_000_000.0, False, False, None, None, None, None,
             "L", quality, benchmark_hash, False)
        )
    connection.executemany(
        "INSERT INTO a_share.a_share_trade_calendar VALUES (?,?,?,?,?)",
        calendar_rows,
    )
    connection.executemany(
        "INSERT INTO a_share.a_share_canonical_daily_bars VALUES "
        "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        bar_rows,
    )
    connection.close()
    return database, days, len(bar_rows)


def test_exact_pivots_participation_ties_variant_order_and_timing() -> None:
    assert hashlib.sha256(swing.DEFINITION_PATH.read_bytes()).hexdigest() == swing.DEFINITION_SHA256
    assert swing._feature_values((10.0, 11.0, float("nan")), (1.0, 1.0, 1.0)) is None
    days = tuple(date(2025, 1, 1) + timedelta(days=i) for i in range(62))
    calendar, decision = _calendar(days), days[-2]
    at = calendar.session_on(decision, as_of=datetime(2000, 1, 1, tzinfo=timezone.utc)).close_at + timedelta(minutes=30)
    targets, audits = swing.build_decision_targets(_rows(days[:-1]), calendar, decision_date=decision, decision_at=at, execution_inputs=_inputs(days))
    assert tuple(item.variant_id for item in targets) == ("SWING20", "SWING60")
    assert all(item.selected_symbols == tuple(f"{i:06d}.SZ" for i in range(15)) for item in targets)
    assert all(item.execution_date == days[-1] and item.target_weights[0][1] == 1 / 15 for item in targets)
    assert all(item.valid and item.eligible_count == 500 and item.candidate_count == 500 for item in audits)
    with pytest.raises(swing.SwingStructureContractError, match="close plus 30"):
        swing.build_decision_targets(_rows(days[:-1]), calendar, decision_date=decision, decision_at=at - timedelta(minutes=1), execution_inputs=_inputs(days))


def test_participation_threshold_insufficient_candidates_and_shared_cny_shares() -> None:
    days = tuple(date(2025, 1, 1) + timedelta(days=i) for i in range(62))
    calendar, decision = _calendar(days), days[-2]
    at = calendar.session_on(decision, as_of=datetime(2000, 1, 1, tzinfo=timezone.utc)).close_at + timedelta(minutes=30)
    rows = tuple(swing.SignalBar(row.session_date, row.symbol, row.close_cny, 1.0 if (row.session_date - days[0]).days % 2 == 0 else 100.0, row.eligible) for row in _rows(days[:-1]))
    targets, audits = swing.build_decision_targets(rows, calendar, decision_date=decision, decision_at=at, execution_inputs=_inputs(days))
    assert targets == () and all(not item.valid and item.candidate_count == 0 for item in audits)
    portfolio = swing.new_strategy_portfolio()
    assert portfolio.lot_size == 100 and portfolio.share_t_plus_one and portfolio.a_share_stamp_tax_schedule


def test_pinned_hash_fails_closed_without_database_write(tmp_path: Path) -> None:
    database = tmp_path / "empty.duckdb"
    database.write_bytes(b"not a duckdb")
    before = database.read_bytes()
    with pytest.raises(swing.SwingStructureContractError, match="SHA-256"):
        preflight.run_read_only_preflight(database)
    assert database.read_bytes() == before


def test_execution_panel_distinguishes_complete_blocked_entries_from_bad_data() -> None:
    row_hash = "a" * 64
    assert not preflight._execution_panel_complete(
        ("000001.SZ", None, None, True, False, None, None, "L", row_hash)
    )
    assert preflight._execution_panel_complete(
        ("000001.SZ", 10.0, 10.0, True, False, 11.0, 9.0, "L", row_hash)
    )
    assert preflight._execution_panel_complete(
        ("000001.SZ", 10.0, 11.0, False, False, 11.0, 9.0, "L", row_hash)
    )
    assert not preflight._execution_panel_complete(
        ("000001.SZ", 10.0, 12.0, False, False, 11.0, 9.0, "L", row_hash)
    )
    assert not preflight._execution_panel_complete(
        ("000001.SZ", float("nan"), 10.0, False, False, 11.0, 9.0, "L", row_hash)
    )
    assert not preflight._execution_panel_complete(
        ("000001.SZ", 10.0, 10.0, False, False, 11.0, 9.0, "L", "bad")
    )
    assert swing.qfq_execution_limits(8.0, 10.0, 11.0, 9.0) == (8.8, 7.2)
    with pytest.raises(swing.SwingStructureContractError, match="opens"):
        swing.qfq_execution_limits(8.0, 0.0, 11.0, 9.0)


def test_preflight_report_requires_every_variant_and_exact_aggregate_allowlist() -> None:
    decision = date(2025, 1, 31)
    audits = tuple(
        swing.DecisionAudit(variant.variant_id, decision, 500, 15, True, True)
        for variant in swing.VARIANTS
    )
    report = preflight._preflight_report(
        audits,
        (date(2018, 1, 2), swing.HISTORICAL_CUTOFF),
        (True, 0.99, 0.0, 0),
    )
    definition = json.loads(swing.DEFINITION_PATH.read_text(encoding="utf-8"))
    assert report["status"] == "PREFLIGHT_PASS"
    assert set(report) == set(definition["outcome_free_preflight"]["allowed_fields"])
    assert report["security_identifiers_in_report"] is False
    assert report["post_entry_outcomes_opened"] is False
    assert report["strategy_candidate_available"] is False
    with pytest.raises(swing.SwingStructureContractError, match="both frozen variants"):
        preflight._preflight_report(
            audits[:1],
            (date(2018, 1, 2), swing.HISTORICAL_CUTOFF),
            (True, 0.99, 0.0, 0),
        )


def test_preflight_report_fails_closed_and_runner_requires_stamp_tax() -> None:
    decision = date(2025, 1, 31)
    audits = tuple(
        swing.DecisionAudit(
            variant.variant_id,
            decision,
            500,
            15,
            variant.variant_id != "SWING60",
            variant.variant_id != "SWING60",
        )
        for variant in swing.VARIANTS
    )
    report = preflight._preflight_report(
        audits,
        (date(2018, 1, 2), swing.HISTORICAL_CUTOFF),
        (True, 0.99, 0.0, 0),
    )
    assert report["status"] == "INPUT_BLOCKED"
    structural = tuple(
        swing.DecisionAudit(variant.variant_id, decision, 499, 15, True, False)
        for variant in swing.VARIANTS
    )
    assert (
        preflight._preflight_report(
            structural,
            (date(2018, 1, 2), swing.HISTORICAL_CUTOFF),
            (True, 0.99, 0.0, 0),
        )["status"]
        == "STRUCTURAL_FAIL"
    )
    portfolio = swing.new_strategy_portfolio()
    portfolio.a_share_stamp_tax_schedule = False
    with pytest.raises(swing.SwingStructureContractError, match="A-share semantics"):
        swing.run_frozen_static_rebalance(
            portfolio,
            _calendar((date(2025, 1, 2), date(2025, 1, 3))),
            signal_session=date(2025, 1, 2),
            decision_at=datetime(2025, 1, 2, 15, 30, tzinfo=ZoneInfo("Asia/Shanghai")),
            execution_inputs=(),
            target_weights={},
            slippage_bps=50.0,
        )


def test_tiny_duckdb_preflight_is_repeatable_aggregate_only_and_read_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database, days, row_count = _tiny_preflight_database(tmp_path)
    receipt_dir = tmp_path / "receipts"
    receipt_dir.mkdir()
    receipt = receipt_dir / "test-receipt.json"
    payload = {
        "post_db_sha256": hashlib.sha256(database.read_bytes()).hexdigest(),
        "target_snapshot": "test-snapshot",
        "v5_digest": "b" * 64,
        "date_start": days[0].strftime("%Y%m%d"),
        "date_end": days[-1].strftime("%Y%m%d"),
        "volume_unit": "SHARES",
        "amount_unit": "CNY",
        "status": "PUBLISHED_V5_VOLUME_UNIT_SHARES_VERIFIED",
        "strategy_candidate_available": False,
        "strategy_outcomes_opened": False,
        "target_rows": row_count,
    }
    receipt.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    monkeypatch.setattr(preflight, "DATABASE_SHA256", payload["post_db_sha256"])
    monkeypatch.setattr(preflight, "SNAPSHOT_ID", "test-snapshot")
    monkeypatch.setattr(preflight, "SNAPSHOT_DIGEST", "b" * 64)
    monkeypatch.setattr(preflight, "SNAPSHOT_RECEIPT_FILENAME", receipt.name)
    monkeypatch.setattr(
        preflight, "SNAPSHOT_RECEIPT_SHA256", hashlib.sha256(receipt.read_bytes()).hexdigest()
    )
    monkeypatch.setattr(preflight, "HISTORICAL_CUTOFF", days[-1])
    monkeypatch.setattr(preflight, "COVERAGE_START", days[0])
    monkeypatch.setattr(preflight, "MIN_LISTED_SESSIONS", 1)
    monkeypatch.setattr(preflight, "MIN_ELIGIBLE", 1)
    monkeypatch.setattr(preflight, "MIN_MEDIAN_AMOUNT_CNY", 1.0)
    monkeypatch.setattr(preflight, "MAX_POSITIONS", 1)
    monkeypatch.setattr(
        preflight,
        "VARIANTS",
        (swing.Variant(1, "SWING20", 8), swing.Variant(2, "SWING60", 8)),
    )
    before = database.read_bytes()
    first = preflight.run_read_only_preflight(database)
    second = preflight.run_read_only_preflight(database)
    assert first == second
    assert first["status"] == "PREFLIGHT_PASS"
    assert first["security_identifiers_in_report"] is False
    assert first["post_entry_outcomes_opened"] is False
    assert set(first) == set(
        json.loads(swing.DEFINITION_PATH.read_text(encoding="utf-8"))[
            "outcome_free_preflight"
        ]["allowed_fields"]
    )
    assert database.read_bytes() == before
