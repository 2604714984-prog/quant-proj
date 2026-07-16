from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb
import pytest

from quant_system.backtest import CapacityObservation, ExecutionInput
from quant_system.data import AcceptedSession, AcceptedSessionCalendar, SourceIdentity
from quant_system.markets.universe import StatusEvidence
from quant_system.research import liquidity_shock_reversal as reversal


ROOT = Path(__file__).resolve().parents[1]
DEFINITION = ROOT / reversal.DEFINITION_PATH
UTC = timezone.utc


def _source(label: str, available_at: datetime | None = None) -> SourceIdentity:
    available = available_at or datetime(2000, 1, 1, tzinfo=UTC)
    return SourceIdentity(
        f"https://example.test/{label}",
        hashlib.sha256(label.encode()).hexdigest(),
        available,
        max(available, datetime(2026, 7, 1, tzinfo=UTC)),
        label,
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


def _fixture() -> tuple[
    tuple[reversal.SignalBar, ...],
    AcceptedSessionCalendar,
    date,
    datetime,
    tuple[ExecutionInput, ...],
]:
    days = tuple(date(2025, 1, 1) + timedelta(days=index) for index in range(22))
    calendar = _calendar(days)
    decision_date = days[-2]
    decision_at = calendar.session_on(
        decision_date, as_of=datetime(2000, 1, 1, tzinfo=UTC)
    ).close_at + timedelta(minutes=30)
    rows: list[reversal.SignalBar] = []
    source = _source("signals")
    for index in range(500):
        symbol = f"{index:06d}.SZ"
        for offset, day in enumerate(days[:-1]):
            rows.append(
                reversal.SignalBar(
                    day,
                    symbol,
                    100.0 if offset < 20 else 80.0 + index * 0.01,
                    50_000_000.0 if offset == 20 and index < 20 else 25_000_000.0,
                    300 + offset,
                    True,
                    False,
                    False,
                    False,
                    False,
                    False,
                    "COMMON_A",
                    "SZSE_MAIN",
                    source,
                )
            )
    for day in days[:-1]:
        rows.append(
            reversal.SignalBar(
                day,
                reversal.BENCHMARK_SYMBOL,
                100.0,
                1_000_000_000.0,
                1000,
                True,
                False,
                False,
                False,
                False,
                False,
                "ETF",
                "SSE_ETF",
                source,
            )
        )
    signal_session = calendar.session_on(decision_date, as_of=decision_at)
    execution_session = calendar.next_session(decision_date, as_of=decision_at)
    inputs = []
    for index in range(500):
        symbol = f"{index:06d}.SZ"
        capacity_source = _source(f"capacity-{index}", signal_session.close_at)
        inputs.append(
            ExecutionInput(
                symbol,
                "a_share",
                10.0,
                "CNY",
                _source(f"open-{index}", execution_session.open_at),
                _statuses(symbol),
                is_suspended=False,
                up_limit=11.0,
                down_limit=9.0,
                capacity=CapacityObservation(
                    symbol,
                    signal_session,
                    10_000_000.0,
                    1_000_000_000.0,
                    "CNY",
                    capacity_source,
                ),
            )
        )
    return tuple(rows), calendar, decision_date, decision_at, tuple(inputs)


def _preflight_db(path: Path, *, quality: str = "RETROSPECTIVE_PERSONAL_RESEARCH_GRADE_SECONDARY_NOT_STRICT_PIT") -> tuple[date, ...]:
    decision, execution = date(2024, 12, 31), date(2025, 1, 2)
    days = tuple(decision - timedelta(days=offset) for offset in range(252, -1, -1)) + (execution,)
    connection = duckdb.connect(str(path))
    connection.execute("CREATE SCHEMA a_share")
    connection.execute("CREATE TABLE a_share.a_share_trade_calendar(trade_date VARCHAR,is_open INTEGER)")
    connection.execute("CREATE TABLE a_share.a_share_symbol_master(ts_code VARCHAR,list_date VARCHAR,delist_date VARCHAR,ingested_at VARCHAR,snapshot_id VARCHAR)")
    connection.execute("CREATE TABLE a_share.a_share_canonical_daily_bars(snapshot_id VARCHAR,ts_code VARCHAR,trade_date VARCHAR,open DOUBLE,qfq_open DOUBLE,qfq_close DOUBLE,vol DOUBLE,amount DOUBLE,is_st BOOLEAN,is_suspended BOOLEAN,is_limit_up BOOLEAN,is_limit_down BOOLEAN,up_limit DOUBLE,down_limit DOUBLE,list_status VARCHAR,row_hash VARCHAR,quality_status VARCHAR,synthetic_data BOOLEAN)")
    connection.executemany("INSERT INTO a_share.a_share_trade_calendar VALUES (?,1)", [(day.strftime("%Y%m%d"),) for day in days])
    connection.execute("INSERT INTO a_share.a_share_symbol_master SELECT lpad(i::VARCHAR,6,'0')||'.SZ',?,NULL,'2026-07-16T00:00:00Z','test-master' FROM range(500) t(i)", [days[0].strftime("%Y%m%d")])
    connection.execute("CREATE TEMP TABLE bar_dates(trade_date VARCHAR,at_decision BOOLEAN)")
    connection.executemany("INSERT INTO bar_dates VALUES (?,?)", [(day.strftime("%Y%m%d"), day == decision) for day in (*days[-22:-1], execution)])
    connection.execute("INSERT INTO a_share.a_share_canonical_daily_bars SELECT ?,symbol,trade_date,10.0,10.0,CASE WHEN at_decision THEN 80.0+i*.01 ELSE 100.0 END,1000000.0,CASE WHEN at_decision AND i<20 THEN 50000000.0 ELSE 25000000.0 END,false,false,false,false,11.0,9.0,'L',sha256(symbol||'|'||trade_date),?,false FROM (SELECT i,lpad(i::VARCHAR,6,'0')||'.SZ' symbol FROM range(500) t(i)) CROSS JOIN bar_dates", [reversal.SNAPSHOT_ID, quality])
    connection.execute("INSERT INTO a_share.a_share_canonical_daily_bars SELECT ?,'510300.SH',trade_date,10.0,10.0,100.0,100000000.0,10000000000.0,false,false,false,false,11.0,9.0,'L',sha256('510300.SH|'||trade_date),?,false FROM bar_dates", [reversal.SNAPSHOT_ID, quality])
    connection.close()
    return days


def test_definition_freezes_exact_four_variants_shock_splits_gates_and_boundaries() -> None:
    definition = json.loads(DEFINITION.read_text())
    assert hashlib.sha256(DEFINITION.read_bytes()).hexdigest() == reversal.DEFINITION_SHA256
    assert definition["status"] == "PREREGISTERED_NOT_EXECUTED"
    assert definition["input_identity"]["database_sha256"] == reversal.DATABASE_SHA256
    assert definition["feature_contract"]["activity_shock"] == (
        "amount(D) / lagged_20_session_median_amount"
    )
    assert definition["feature_contract"]["shock_direction_and_threshold"] == (
        "greater than or equal to 2.0"
    )
    assert tuple(item["variant_id"] for item in definition["variants_in_exact_order"]) == (
        "REV10_NO_SHOCK",
        "REV10_AMOUNT_SHOCK2",
        "REV20_NO_SHOCK",
        "REV20_AMOUNT_SHOCK2",
    )
    assert definition["historical_test_family"]["family_size"] == 8
    assert len(definition["gates_per_primary_variant_and_historical_split"]) == 7
    assert definition["execution"] == {
        "real_data_preflight_authorized": True,
        "historical_outcome_authorized": False,
        "network_authorized": False,
        "database_write_authorized": False,
        "broker_order_paper_live_auto_authorized": False,
        "prospective_outcomes_opened": False,
        "gate_counts": None,
        "strategy_candidate_available": False,
    }


def test_targets_freeze_relative_decline_shock_order_ties_and_equal_weights() -> None:
    rows, calendar, decision, decision_at, execution = _fixture()
    targets, audits = reversal.build_decision_targets(
        rows,
        calendar,
        decision_date=decision,
        decision_at=decision_at,
        execution_inputs=execution,
    )
    assert tuple(target.variant_id for target in targets) == tuple(
        variant.variant_id for variant in reversal.VARIANTS
    )
    assert all(audit.eligible_count == 500 and audit.valid for audit in audits)
    assert tuple(audit.candidate_count for audit in audits) == (500, 20, 500, 20)
    selected = tuple(f"{index:06d}.SZ" for index in range(15))
    assert all(target.selected_symbols == selected for target in targets)
    assert all(
        target.selected_scores == tuple(sorted(target.selected_scores, key=lambda item: (item[1], item[0])))
        for target in targets
    )
    assert all(
        target.target_weights == tuple((symbol, 1 / 15) for symbol in selected)
        for target in targets
    )


def test_shock_is_lagged_fixed_high_direction_and_never_changes_comparator() -> None:
    rows, calendar, decision, decision_at, execution = _fixture()
    changed = tuple(
        replace(row, amount_cny=49_999_999.0)
        if row.session_date == decision and row.symbol < "000020.SZ"
        else row
        for row in rows
    )
    targets, audits = reversal.build_decision_targets(
        changed,
        calendar,
        decision_date=decision,
        decision_at=decision_at,
        execution_inputs=execution,
    )
    assert tuple(target.variant_id for target in targets) == (
        "REV10_NO_SHOCK",
        "REV20_NO_SHOCK",
    )
    assert tuple(audit.candidate_count for audit in audits) == (500, 0, 500, 0)
    assert sum(not audit.valid for audit in audits) == 2


def test_real_read_only_preflight_is_repeatable_aggregate_only_and_bound_to_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database = tmp_path / "preflight.duckdb"
    days = _preflight_db(database)
    digest = hashlib.sha256(database.read_bytes()).hexdigest()
    monkeypatch.setattr(reversal, "DATABASE_SHA256", digest)
    monkeypatch.setattr(reversal, "HISTORICAL_CUTOFF", days[-1])
    before = database.read_bytes()
    observed_volume = []
    rebalance = reversal.run_frozen_static_rebalance
    def capture_volume(*args: object, **kwargs: object) -> object:
        observed_volume.append(kwargs["execution_inputs"][0].capacity.session_volume_shares)  # type: ignore[index,union-attr]
        return rebalance(*args, **kwargs)  # type: ignore[arg-type]
    monkeypatch.setattr(reversal, "run_frozen_static_rebalance", capture_volume)
    first = reversal.run_read_only_preflight(database)
    second = reversal.run_read_only_preflight(database)
    assert first == second and database.read_bytes() == before
    assert first["status"] == "PREFLIGHT_PASS" and first["decision_count"] == 1
    assert first["minimum_eligible_count"] == 500 and first["minimum_candidate_count"] == 20
    assert first["invalid_decision_count"] == 0 and first["execution_panels_complete"] is True
    assert first["benchmark_initial_entry_filled"] is True
    assert observed_volume == [100_000_000.0] * 4
    assert 0.0 < first["benchmark_invested_ratio"] <= 1.0
    assert first["strategy_candidate_available"] is False
    definition = json.loads(DEFINITION.read_text())
    assert set(first) == set(definition["preflight"]["allowed_fields"])
    forbidden = ("symbol", "ranking", "return", "nav", "sharpe", "gate")
    assert not any(token in key.lower() for key in first for token in forbidden)


def test_input_failure_blocks_without_outcome_consumption_or_replacement() -> None:
    rows, calendar, decision, decision_at, execution = _fixture()
    missing = tuple(row for row in execution if row.symbol != "000000.SZ")
    targets, audits = reversal.build_decision_targets(
        rows,
        calendar,
        decision_date=decision,
        decision_at=decision_at,
        execution_inputs=missing,
    )
    assert targets == ()
    assert sum(not audit.valid for audit in audits) == 4

    incomplete = tuple(
        replace(row, status_records=row.status_records[:-1])
        if row.symbol == "000000.SZ"
        else row
        for row in execution
    )
    targets, audits = reversal.build_decision_targets(
        rows,
        calendar,
        decision_date=decision,
        decision_at=decision_at,
        execution_inputs=incomplete,
    )
    assert targets == ()
    assert sum(not audit.valid for audit in audits) == 4


def test_duplicates_timing_and_forged_preflight_health_fail_closed(tmp_path: Path) -> None:
    rows, calendar, decision, decision_at, execution = _fixture()
    with pytest.raises(reversal.LiquidityShockContractError, match="duplicate signal"):
        reversal.build_decision_targets(
            (*rows, rows[0]),
            calendar,
            decision_date=decision,
            decision_at=decision_at,
            execution_inputs=execution,
        )
    with pytest.raises(reversal.LiquidityShockContractError, match="close plus 30"):
        reversal.build_decision_targets(
            rows,
            calendar,
            decision_date=decision,
            decision_at=decision_at - timedelta(minutes=1),
            execution_inputs=execution,
        )
    assert not hasattr(reversal, "PreflightHealth")
    assert not hasattr(reversal, "build_preflight_report")
    forged = tmp_path / "forged.duckdb"
    forged.write_bytes(b"not the pinned database")
    with pytest.raises(reversal.LiquidityShockContractError, match="SHA-256"):
        reversal.run_read_only_preflight(forged)
    with pytest.raises(TypeError):
        reversal.run_read_only_preflight(forged, health={"status": "PREFLIGHT_PASS"})  # type: ignore[call-arg]


def test_preflight_rejects_wrong_snapshot_classification_without_mutation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database = tmp_path / "wrong.duckdb"
    days = _preflight_db(database, quality="FORGED_PASS")
    digest = hashlib.sha256(database.read_bytes()).hexdigest()
    monkeypatch.setattr(reversal, "DATABASE_SHA256", digest)
    monkeypatch.setattr(reversal, "HISTORICAL_CUTOFF", days[-1])
    before = database.read_bytes()
    with pytest.raises(reversal.LiquidityShockContractError, match="classification"):
        reversal.run_read_only_preflight(database)
    assert database.read_bytes() == before


def test_frozen_target_runs_through_existing_event_loop_cost_capacity_and_lot_semantics() -> None:
    rows, calendar, decision, decision_at, execution = _fixture()
    targets, _ = reversal.build_decision_targets(
        rows,
        calendar,
        decision_date=decision,
        decision_at=decision_at,
        execution_inputs=execution,
    )
    target = next(item for item in targets if item.variant_id == "REV10_AMOUNT_SHOCK2")
    inputs = tuple(row for row in execution if row.symbol in target.selected_symbols)
    result = reversal.run_frozen_static_rebalance(
        reversal.new_strategy_portfolio(),
        calendar,
        signal_session=decision,
        decision_at=decision_at,
        execution_inputs=inputs,
        target_weights=dict(target.target_weights),
        slippage_bps=50.0,
    )
    buys = tuple(receipt for receipt in result.receipts if receipt.side == "buy")
    assert len(result.portfolio.positions) == 15
    assert len(buys) == 15
    assert all(receipt.filled_shares % 100 == 0 for receipt in buys)
    assert all(receipt.price == pytest.approx(10.05) for receipt in buys)
    assert all(receipt.commission >= 5.0 for receipt in buys)
    with pytest.raises(reversal.LiquidityShockContractError, match="20 or 50"):
        reversal.run_frozen_static_rebalance(
            reversal.new_strategy_portfolio(),
            calendar,
            signal_session=decision,
            decision_at=decision_at,
            execution_inputs=inputs,
            target_weights=dict(target.target_weights),
            slippage_bps=30.0,
        )
