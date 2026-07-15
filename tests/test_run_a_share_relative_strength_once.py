from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import socket
import sys
from zoneinfo import ZoneInfo

import duckdb
import pytest

from quant_system.backtest import CapacityObservation, ExecutionInput
from quant_system.data import AcceptedSession, AcceptedSessionCalendar, SourceIdentity
from quant_system.markets.universe import StatusEvidence
from quant_system.research import relative_strength as rs


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_a_share_relative_strength_once.py"
CODE_MANIFEST = ROOT / (
    "research/definitions/a_share_relative_strength_historical_secondary_screen_code_v1.json"
)
SPEC = importlib.util.spec_from_file_location("rs_once", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)
UTC = timezone.utc


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _source(label: str, available: datetime | None = None) -> SourceIdentity:
    when = available or datetime(2000, 1, 1, tzinfo=UTC)
    return SourceIdentity(
        f"https://example.test/{label}", _sha(label), when, when + timedelta(minutes=1), label
    )


def _calendar(days: tuple[date, ...]) -> AcceptedSessionCalendar:
    zone = ZoneInfo("Asia/Shanghai")
    source = _source("calendar")
    return AcceptedSessionCalendar(
        tuple(
            AcceptedSession(
                day,
                datetime.combine(day, time(9, 30), zone),
                datetime.combine(day, time(15), zone),
                source,
                "Asia/Shanghai",
            )
            for day in days
        )
    )


def _statuses(symbol: str) -> tuple[StatusEvidence, ...]:
    return tuple(
        StatusEvidence(
            f"{symbol}-{kind}",
            symbol,
            kind,
            value,
            date(2000, 1, 1),
            None,
            "Asia/Shanghai",
            _source(f"status-{symbol}-{kind}"),
        )
        for kind, value in (
            ("listed", True),
            ("delisted", False),
            ("st", False),
            ("suspended", False),
        )
    )


def _bar(symbol: str, day: date, *, opened: float = 10.0, suspended: bool = False):
    return runner.SecondaryExecutionBar(
        symbol,
        day,
        opened,
        opened,
        suspended,
        12.0,
        8.0,
        10_000_000.0,
        1_000_000_000.0,
    )


def test_frozen_amendment_and_parent_preregistration_are_exact() -> None:
    amendment = runner.load_amendment()
    assert hashlib.sha256(runner.AMENDMENT.read_bytes()).hexdigest() == runner.AMENDMENT_SHA256
    assert hashlib.sha256(runner.PREREGISTRATION.read_bytes()).hexdigest() == rs.DEFINITION_SHA256
    assert amendment["classification"] == runner.CLASSIFICATION
    assert amendment["outcome_window"]["lifetime_family_size_remains"] == 12
    assert amendment["outcome_window"]["prospective_forward_2027_2029_outcomes_opened"] is False
    assert amendment["output_contract"]["strategy_candidate_available"] is False


def test_code_manifest_binds_exact_narrow_scope() -> None:
    manifest = json.loads(CODE_MANIFEST.read_text())
    actual = {
        item["path"]: hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest()
        for item in manifest["scope"]
    }
    assert actual == {item["path"]: item["sha256"] for item in manifest["scope"]}
    assert tuple(actual) == (
        "research/definitions/a_share_relative_strength_historical_secondary_screen_v1.json",
        "scripts/run_a_share_relative_strength_once.py",
        "tests/test_run_a_share_relative_strength_once.py",
    )
    assert manifest["mechanical_proof"]["prospective_forward_fixture_created"] is False
    assert manifest["boundary"]["strategy_candidate_available"] is False


def test_default_is_no_database_no_socket_no_output(monkeypatch, capsys) -> None:
    monkeypatch.setattr(duckdb, "connect", lambda *a, **k: pytest.fail("database opened"))
    monkeypatch.setattr(socket, "socket", lambda *a, **k: pytest.fail("socket opened"))
    monkeypatch.setattr(runner, "_publish", lambda *a, **k: pytest.fail("output written"))
    assert runner.main([]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "DRY_RUN_PLAN"
    assert report["database_opened"] is False
    assert report["output_written"] is False
    assert report["strategy_candidate_available"] is False


def test_secondary_selection_matches_strict_target_builder() -> None:
    start = date(2025, 1, 1)
    days = tuple(start + timedelta(days=offset) for offset in range(120)) + (
        date(2025, 5, 31),
        date(2025, 6, 1),
    )
    calendar = _calendar(days)
    source = _source("signals")
    strict_rows = []
    series: dict[str, list[float]] = {}
    benchmark = [math.exp(0.0001 * index) for index in range(len(days))]
    for index, day in enumerate(days):
        strict_rows.append(
            rs.SignalBar(
                day, rs.BENCHMARK_SYMBOL, benchmark[index], 1e9, 1000 + index,
                True, False, False, False, "ETF", "SSE_MAIN", source,
            )
        )
        for symbol_index in range(500):
            symbol = f"{600000 + symbol_index:06d}.SH"
            values = series.setdefault(symbol, [])
            value = math.exp(
                (0.0003 + symbol_index * 0.000001) * index
                + (0.00002 if symbol_index < 250 else 0.00020) * math.sin(index * 0.7)
            )
            values.append(value)
            strict_rows.append(
                rs.SignalBar(
                    day, symbol, value, 25e6, 300 + index, True, False, False,
                    False, "COMMON_A", "SSE_MAIN", source,
                )
            )
    decision = datetime(2025, 5, 31, 15, 30, tzinfo=ZoneInfo("Asia/Shanghai"))
    strict = rs.build_monthly_targets(
        tuple(strict_rows), calendar, decision_at_by_session={date(2025, 5, 31): decision}
    )
    features = []
    for symbol, values in series.items():
        returns = tuple(values[index] / values[index - 1] - 1 for index in range(101, 121))
        mean = math.fsum(returns) / 20
        volatility = math.sqrt(math.fsum((item - mean) ** 2 for item in returns) / 19)
        features.append(
            runner.SecondaryFeature(
                date(2025, 5, 31),
                symbol,
                (values[-2] / values[-62]) / (benchmark[-2] / benchmark[-62]) - 1,
                (values[-2] / values[0]) / (benchmark[-2] / benchmark[0]) - 1,
                volatility,
            )
        )
    secondary = runner.select_secondary_targets(
        features, signal_date=date(2025, 5, 31), execution_date=date(2025, 6, 1)
    )
    assert tuple(item.variant_id for item in secondary) == tuple(item.variant_id for item in strict)
    assert tuple(item.selected_symbols for item in secondary) == tuple(
        item.selected_symbols for item in strict
    )
    assert tuple(item.ranked_candidate_count for item in secondary) == tuple(
        item.ranked_candidate_count for item in strict
    )


def test_secondary_fill_adapter_matches_accepted_event_loop() -> None:
    days = (date(2026, 6, 29), date(2026, 6, 30))
    calendar = _calendar(days)
    signal = calendar.session_on(days[0], as_of=datetime(2026, 6, 29, 8, tzinfo=UTC))
    execution = calendar.next_session(days[0], as_of=signal.close_at + timedelta(minutes=30))
    symbols = tuple(f"{600000 + index:06d}.SH" for index in range(15))
    strict_inputs = []
    secondary_bars = {}
    for symbol in symbols:
        strict_inputs.append(
            ExecutionInput(
                symbol,
                "a_share",
                10.0,
                "CNY",
                _source(f"open-{symbol}", execution.open_at),
                _statuses(symbol),
                capacity=CapacityObservation(
                    symbol,
                    signal,
                    10_000_000.0,
                    1_000_000_000.0,
                    "CNY",
                    _source(f"capacity-{symbol}", signal.close_at),
                ),
                up_limit=12.0,
                down_limit=8.0,
            )
        )
        secondary_bars[symbol] = _bar(symbol, days[1])
    weights = {symbol: 1 / 15 for symbol in symbols}
    strict = rs.run_frozen_static_rebalance(
        rs.new_strategy_portfolio(),
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at + timedelta(minutes=30),
        execution_inputs=tuple(strict_inputs),
        target_weights=weights,
        slippage_bps=50.0,
    )
    secondary_portfolio = rs.new_strategy_portfolio()
    receipts = runner.secondary_rebalance(
        secondary_portfolio, symbols, secondary_bars, slippage_bps=50.0
    )
    assert {key: value.shares for key, value in secondary_portfolio.positions.items()} == {
        key: value.shares for key, value in strict.portfolio.positions.items()
    }
    assert secondary_portfolio.available_cash == pytest.approx(strict.portfolio.available_cash)
    assert tuple((r.filled_shares, r.price) for r in receipts if r.side == "buy") == tuple(
        (r.filled_shares, r.price) for r in strict.receipts if r.side == "buy"
    )


def test_blocked_exit_keeps_slot_and_ranked_membership_never_falls_back() -> None:
    first_day, second_day = date(2026, 5, 4), date(2026, 6, 1)
    old = tuple(f"{600000 + index:06d}.SH" for index in range(15))
    new = tuple(f"{601000 + index:06d}.SH" for index in range(15))
    portfolio = rs.new_strategy_portfolio()
    runner.secondary_rebalance(
        portfolio, old, {symbol: _bar(symbol, first_day) for symbol in old}, slippage_bps=20
    )
    bars = {symbol: _bar(symbol, second_day, suspended=(symbol == old[0])) for symbol in old}
    bars.update({symbol: _bar(symbol, second_day) for symbol in new})
    receipts = runner.secondary_rebalance(portfolio, new, bars, slippage_bps=20)
    assert old[0] in portfolio.positions
    assert tuple(symbol for symbol in new if symbol in portfolio.positions) == new[:14]
    assert new[14] not in portfolio.positions
    assert len(portfolio.positions) == 15
    assert any(item.side == "sell" and item.reason == "suspended" for item in receipts)


def _write_database(path: Path) -> tuple[list[tuple[str, str, str]], str]:
    connection = duckdb.connect(str(path))
    connection.execute("CREATE SCHEMA a_share")
    connection.execute(
        """
        CREATE TABLE a_share.a_share_canonical_daily_bars (
          snapshot_id VARCHAR, ts_code VARCHAR, trade_date VARCHAR, open DOUBLE,
          close DOUBLE, vol DOUBLE, amount DOUBLE, adj_factor DOUBLE,
          qfq_open DOUBLE, qfq_close DOUBLE, is_st BOOLEAN, is_suspended BOOLEAN,
          up_limit DOUBLE, down_limit DOUBLE, list_status VARCHAR,
          quality_status VARCHAR, source VARCHAR, row_hash VARCHAR,
          synthetic_data BOOLEAN
        )
        """
    )
    rows = []
    for day in (runner.START, runner.END):
        for symbol in (rs.BENCHMARK_SYMBOL, "600000.SH"):
            row_hash = _sha(f"{day}|{symbol}")
            upper, lower = ((None, None) if symbol == rs.BENCHMARK_SYMBOL else (12, 8))
            connection.execute(
                "INSERT INTO a_share.a_share_canonical_daily_bars VALUES "
                "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    "snapshot", symbol, runner._date_text(day), 10, 10, 1_000_000,
                    100_000_000, 1, 10, 10, False, False, upper, lower, "L",
                    "PASS_SECONDARY", "fixture",
                    row_hash, False,
                ),
            )
            rows.append((runner._date_text(day), symbol, row_hash))
    connection.close()
    ordered = sorted(rows)
    return ordered, runner._database_identity(path)[0]


def _manifest(path: Path, database: Path, rows: list[tuple[str, str, str]]) -> tuple[dict, str]:
    partitions = []
    for month in sorted({day[:6] for day, _, _ in rows}):
        values = [row_hash for day, _, row_hash in rows if day[:6] == month]
        partitions.append(
            {"month": month, "row_count": len(values), "sha256": hashlib.sha256("".join(values).encode()).hexdigest()}
        )
    db_sha, size, mode = runner._database_identity(database)
    value = {
        "schema_version": "a-share-rs-secondary-data-manifest-v1",
        "research_id": rs.RESEARCH_ID,
        "run_id": runner.RUN_ID,
        "status": "ACCEPTED_RETROSPECTIVE_SECONDARY_SNAPSHOT",
        "classification": runner.CLASSIFICATION,
        "table": runner.TABLE,
        "snapshot_id": "snapshot",
        "database": {"sha256": db_sha, "size_bytes": size, "mode": mode},
        "coverage": {
            "start_date": runner._date_text(runner.START),
            "end_date": runner._date_text(runner.END),
            "row_count": len(rows),
            "symbol_count": 2,
            "benchmark_row_count": 2,
        },
        "identity": {
            "ordered_row_hash_sha256": hashlib.sha256("".join(row[2] for row in rows).encode()).hexdigest(),
            "partitions": partitions,
        },
        "strict_pit_eligible": False,
        "strategy_outcomes_opened": False,
        "synthetic_data": False,
    }
    raw = runner._canonical_bytes(value)
    path.write_bytes(raw)
    return value, hashlib.sha256(raw).hexdigest()


def test_manifest_snapshot_identity_and_input_blocked_publication(tmp_path) -> None:
    database = tmp_path / "research.duckdb"
    rows, _ = _write_database(database)
    os.chmod(database, 0o600)
    manifest_path = tmp_path / "manifest.json"
    manifest, digest = _manifest(manifest_path, database, rows)
    loaded = runner.load_data_manifest(manifest_path, digest)
    with runner._read_only_connection(database) as connection:
        observed = runner._verify_snapshot(connection, loaded)
    assert observed["row_count"] == 4
    output = tmp_path / "result.json"
    result = runner.main(
        [
            "--db", str(database),
            "--data-manifest", str(manifest_path),
            "--expected-data-manifest-sha256", digest,
            "--output", str(output),
            "--execute",
        ]
    )
    assert result == 2
    report = json.loads(output.read_text())
    assert report["status"] == "INPUT_BLOCKED"
    assert report["security_identifiers_in_result"] is False
    assert report["strategy_candidate_available"] is False
    assert "600000.SH" not in output.read_text()
    assert runner._database_identity(database)[0] == manifest["database"]["sha256"]


def test_real_varchar_dates_reject_malformed_or_mixed_values(tmp_path) -> None:
    database = tmp_path / "research.duckdb"
    rows, _ = _write_database(database)
    os.chmod(database, 0o600)
    manifest_path = tmp_path / "manifest.json"
    manifest, _ = _manifest(manifest_path, database, rows)
    connection = duckdb.connect(str(database))
    connection.execute(
        "UPDATE a_share.a_share_canonical_daily_bars SET trade_date='2026-06-30' "
        "WHERE ts_code='600000.SH' AND trade_date='20260630'"
    )
    connection.close()
    with runner._read_only_connection(database) as read_only:
        with pytest.raises(runner.SecondaryScreenError, match="malformed or mixed"):
            runner._verify_snapshot(read_only, manifest)


def test_common_a_limits_are_required_but_benchmark_limits_are_not(tmp_path) -> None:
    database = tmp_path / "research.duckdb"
    rows, _ = _write_database(database)
    os.chmod(database, 0o600)
    manifest_path = tmp_path / "manifest.json"
    manifest, _ = _manifest(manifest_path, database, rows)
    with runner._read_only_connection(database) as read_only:
        assert runner._verify_snapshot(read_only, manifest)["benchmark_row_count"] == 2
    connection = duckdb.connect(str(database))
    connection.execute(
        "UPDATE a_share.a_share_canonical_daily_bars SET up_limit=NULL "
        "WHERE ts_code='600000.SH'"
    )
    connection.close()
    with runner._read_only_connection(database) as read_only:
        with pytest.raises(runner.SecondaryScreenError, match="incomplete"):
            runner._verify_snapshot(read_only, manifest)


def test_manifest_symlink_and_preexisting_output_fail_closed(tmp_path) -> None:
    target = tmp_path / "manifest.json"
    target.write_text("{}\n")
    link = tmp_path / "link.json"
    link.symlink_to(target)
    with pytest.raises(runner.SecondaryScreenError, match="cannot open"):
        runner.load_data_manifest(link, hashlib.sha256(target.read_bytes()).hexdigest())
    output = tmp_path / "result.json"
    output.write_text("existing")
    with pytest.raises(runner.SecondaryScreenError, match="preexist"):
        runner._publish(output, {"status": "INPUT_BLOCKED"})
