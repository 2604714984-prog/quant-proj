from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from quant_system.backtest import CapacityObservation, ExecutionInput
from quant_system.data import AcceptedSession, AcceptedSessionCalendar, SourceIdentity
from quant_system.research import salient_return as salient
from scripts import run_a_share_salient_return_preflight as preflight


def _source(name: str) -> SourceIdentity:
    available = datetime(2000, 1, 1, tzinfo=timezone.utc)
    return SourceIdentity(
        f"https://example.test/{name}",
        hashlib.sha256(name.encode()).hexdigest(),
        available,
        available,
        name,
    )


def _legacy_master_hash(
    source: str = "wsl2_chain_repair_20260706",
    snapshot_id: str = "wsl2_chain_repair_20260706_195210",
    symbol: str = "600000.SH",
) -> str:
    return f"{source}|{snapshot_id}|symbol_master|{symbol}|"


def _calendar(days: tuple[date, ...]) -> AcceptedSessionCalendar:
    zone = ZoneInfo("Asia/Shanghai")
    return AcceptedSessionCalendar(
        tuple(
            AcceptedSession(
                day,
                datetime.combine(day, time(9, 30), zone),
                datetime.combine(day, time(15), zone),
                _source("calendar"),
                "Asia/Shanghai",
            )
            for day in days
        )
    )


def _signal(symbol: str, returns: tuple[float, ...]) -> salient.MonthlySignal:
    return salient.MonthlySignal(
        symbol,
        returns,
        (30_000_000.0,) * 20,
        252,
        True,
        False,
        False,
        False,
        False,
        False,
    )


def _input(
    symbol: str,
    calendar: AcceptedSessionCalendar,
    decision: date,
) -> ExecutionInput:
    at = calendar.session_on(
        decision, as_of=datetime(2000, 1, 1, tzinfo=timezone.utc)
    ).close_at + timedelta(minutes=30)
    signal = calendar.session_on(decision, as_of=at)
    return ExecutionInput(
        symbol,
        "a_share",
        10.0,
        "CNY",
        _source(f"open-{symbol}"),
        (),
        is_suspended=False,
        up_limit=11.0,
        down_limit=9.0,
        capacity=CapacityObservation(
            symbol,
            signal,
            1_000_000.0,
            100_000_000.0,
            "CNY",
            _source(f"capacity-{symbol}"),
        ),
    )


def _month_calendar() -> tuple[AcceptedSessionCalendar, date, datetime]:
    days = tuple(date(2025, 1, 17) + timedelta(days=index) for index in range(15))
    days += (date(2025, 2, 3),)
    calendar = _calendar(days)
    decision = days[-2]
    at = calendar.session_on(
        decision, as_of=datetime(2000, 1, 1, tzinfo=timezone.utc)
    ).close_at + timedelta(minutes=30)
    return calendar, decision, at


def test_definition_is_exact_one_variant_outcome_blind_and_hash_bound() -> None:
    raw = salient.DEFINITION_PATH.read_bytes()
    definition = json.loads(raw)
    assert hashlib.sha256(raw).hexdigest() == salient.DEFINITION_SHA256
    assert definition["research_id"] == salient.RESEARCH_ID
    assert definition["feature_contract"]["variant_id"] == "LOW_ST_MONTHLY"
    assert definition["feature_contract"]["variant_count"] == 1
    assert definition["feature_contract"]["delta"] == 0.7
    assert definition["feature_contract"]["direction"] == "LOWEST_ST_LONG_ONLY"
    assert definition["inference"]["lifetime_primary_test_count"] == 3
    assert definition["inference"]["bonferroni_one_sided_alpha"] == 1 / 60
    assert len(set(definition["inference"]["seeds"].values())) == 3
    assert len(definition["gates_per_gated_split"]) == 6
    assert definition["execution_state"] == {
        "preflight_authorized": True,
        "historical_outcome_authorized": False,
        "provider_or_network_authorized": False,
        "database_write_authorized": False,
        "gate_counts": None,
        "strategy_candidate_available": False,
    }


def test_binary64_salience_competition_rank_ties_gaps_and_normalization() -> None:
    returns = (0.1, -0.1, 0.05, -0.05) + (0.0,) * 11
    feature = salient.salience_feature(returns, (0.0,) * 15)
    assert feature.competition_ranks == (1, 1, 3, 3) + (5,) * 11
    assert feature.sigmas[:4] == pytest.approx((0.5, 0.5, 1 / 3, 1 / 3))
    assert math.fsum(feature.normalized_weights) / 15 == pytest.approx(1.0)
    expected = (
        math.fsum(
            weight * value
            for weight, value in zip(feature.normalized_weights, returns, strict=True)
        )
        / 15
        - math.fsum(returns) / 15
    )
    assert feature.score == expected


@pytest.mark.parametrize(
    ("returns", "references", "message"),
    [
        ((0.0,) * 14, (0.0,) * 14, "align"),
        ((float("nan"),) + (0.0,) * 14, (0.0,) * 15, "finite"),
        ((-1.0,) + (0.0,) * 14, (0.0,) * 15, "exceed"),
    ],
)
def test_salience_feature_rejects_incomplete_nonfinite_or_impossible_returns(
    returns: tuple[float, ...], references: tuple[float, ...], message: str
) -> None:
    with pytest.raises(salient.SalientReturnContractError, match=message):
        salient.salience_feature(returns, references)


def test_monthly_target_uses_cross_sectional_reference_lowest_score_and_symbol_tie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(salient, "MIN_ELIGIBLE", 3)
    monkeypatch.setattr(salient, "MAX_POSITIONS", 2)
    calendar, decision, at = _month_calendar()
    signals = (
        _signal("000001.SZ", (0.02, -0.01, 0.01) * 5),
        _signal("000002.SZ", (-0.02, 0.01, -0.01) * 5),
        _signal("000003.SZ", (0.005,) * 15),
    )
    references = tuple(math.fsum(row.returns[i] for row in signals) / 3 for i in range(15))
    expected = tuple(
        symbol
        for symbol, _ in sorted(
            (
                (row.symbol, salient.salience_feature(row.returns, references).score)
                for row in signals
            ),
            key=lambda item: (item[1], item[0]),
        )[:2]
    )
    target, audit = salient.build_monthly_target(
        signals,
        calendar,
        decision_date=decision,
        decision_at=at,
        execution_inputs=tuple(_input(row.symbol, calendar, decision) for row in signals),
    )
    assert target is not None
    assert target.variant_id == "LOW_ST_MONTHLY"
    assert target.selected_symbols == expected
    assert target.execution_date == date(2025, 2, 3)
    assert target.target_weights == tuple((symbol, 0.5) for symbol in expected)
    assert audit.valid and (audit.eligible_count, audit.candidate_count) == (3, 3)

    tied = tuple(_signal(f"00000{index}.SZ", (0.001,) * 15) for index in range(1, 4))
    tied_target, _ = salient.build_monthly_target(
        tied,
        calendar,
        decision_date=decision,
        decision_at=at,
        execution_inputs=tuple(_input(row.symbol, calendar, decision) for row in tied),
    )
    assert tied_target is not None
    assert tied_target.selected_symbols == ("000001.SZ", "000002.SZ")


def test_target_fails_closed_on_timing_month_end_liquidity_status_and_panel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(salient, "MIN_ELIGIBLE", 1)
    monkeypatch.setattr(salient, "MAX_POSITIONS", 1)
    calendar, decision, at = _month_calendar()
    signal = _signal("000001.SZ", (0.001,) * 15)
    with pytest.raises(salient.SalientReturnContractError, match="close plus 30"):
        salient.build_monthly_target(
            (signal,),
            calendar,
            decision_date=decision,
            decision_at=at - timedelta(minutes=1),
            execution_inputs=(_input(signal.symbol, calendar, decision),),
        )
    target, audit = salient.build_monthly_target(
        (signal,),
        calendar,
        decision_date=decision,
        decision_at=at,
        execution_inputs=(),
    )
    assert target is None and not audit.valid and not audit.execution_panel_complete
    illiquid = salient.MonthlySignal(
        signal.symbol,
        signal.returns,
        (19_999_999.0,) * 20,
        252,
        True,
        False,
        False,
        False,
        False,
        False,
    )
    _, illiquid_audit = salient.build_monthly_target(
        (illiquid,),
        calendar,
        decision_date=decision,
        decision_at=at,
        execution_inputs=(_input(signal.symbol, calendar, decision),),
    )
    assert illiquid_audit.eligible_count == 0


def test_qfq_limits_and_frozen_shared_a_share_portfolio_contract() -> None:
    assert salient.qfq_execution_limits(8.0, 10.0, 11.0, 9.0) == (8.8, 7.2)
    with pytest.raises(salient.SalientReturnContractError, match="positive"):
        salient.qfq_execution_limits(8.0, 0.0, 11.0, 9.0)
    portfolio = salient.new_strategy_portfolio()
    portfolio.a_share_stamp_tax_schedule = False
    calendar = _calendar((date(2025, 1, 2), date(2025, 1, 3)))
    with pytest.raises(salient.SalientReturnContractError, match="A-share semantics"):
        salient.run_frozen_static_rebalance(
            portfolio,
            calendar,
            signal_session=date(2025, 1, 2),
            decision_at=datetime(2025, 1, 2, 15, 30, tzinfo=ZoneInfo("Asia/Shanghai")),
            execution_inputs=(),
            target_weights={},
        )


def test_symbol_master_accepts_exact_legacy_identity_and_rejects_forged_composition() -> None:
    class Result:
        def __init__(self, row_hash: str) -> None:
            self.row_hash = row_hash

        def fetchall(self) -> list[tuple[object, ...]]:
            return [
                (
                    "600000.SH",
                    "20100101",
                    None,
                    "wsl2_chain_repair_20260706",
                    "wsl2_chain_repair_20260706_195210",
                    self.row_hash,
                    False,
                )
            ]

    class Connection:
        def __init__(self, row_hash: str) -> None:
            self.row_hash = row_hash
            self.sql = ""

        def execute(self, sql: str) -> Result:
            self.sql = sql
            return Result(self.row_hash)

    valid = Connection(_legacy_master_hash())
    assert preflight._master(valid) == {"600000.SH": (date(2010, 1, 1), None)}
    assert "source,snapshot_id,row_hash" in valid.sql
    forged = Connection(_legacy_master_hash(snapshot_id="forged-snapshot"))
    with pytest.raises(salient.SalientReturnContractError, match="row identity differs"):
        preflight._master(forged)


def test_benchmark_open_at_adjusted_limit_is_not_reported_as_filled() -> None:
    decisions = (date(2020, 1, 31), date(2022, 1, 31), date(2024, 1, 31))
    calendar = _calendar(
        (
            date(2020, 1, 31),
            date(2020, 2, 3),
            date(2022, 1, 31),
            date(2022, 2, 1),
            date(2024, 1, 31),
            date(2024, 2, 1),
        )
    )

    class Result:
        def fetchall(self) -> list[tuple[object, ...]]:
            return [
                (
                    "signal",
                    10.0,
                    10.0,
                    1_000_000.0,
                    100_000_000.0,
                    False,
                    False,
                    11.0,
                    9.0,
                    "L",
                    preflight.CLASSIFICATION,
                    False,
                    "a" * 64,
                ),
                (
                    "execution",
                    11.0,
                    11.0,
                    1_000_000.0,
                    100_000_000.0,
                    False,
                    False,
                    11.0,
                    9.0,
                    "L",
                    preflight.CLASSIFICATION,
                    False,
                    "b" * 64,
                ),
            ]

    class Connection:
        def execute(self, *_: object) -> Result:
            return Result()

    filled, invested, rejected, exceptions = preflight._benchmark_probe(
        Connection(), calendar, decisions
    )
    assert filled is False
    assert invested == 0.0
    assert rejected == 0.0
    assert exceptions == 0


def test_preflight_report_has_exact_allowlist_and_three_fail_closed_states() -> None:
    decision = date(2025, 1, 31)
    valid = salient.DecisionAudit(salient.VARIANT_ID, decision, 500, 500, True, True)
    report = preflight._preflight_report(
        (valid,),
        (salient.COVERAGE_START, salient.HISTORICAL_CUTOFF),
        (True, 0.95, 0.0, 0),
    )
    definition = json.loads(salient.DEFINITION_PATH.read_text(encoding="utf-8"))
    assert report["status"] == "PREFLIGHT_PASS"
    assert set(report) == set(definition["outcome_free_preflight"]["allowed_fields"])
    assert report["variant_aggregates"] == {
        "LOW_ST_MONTHLY": {
            "decision_count": 1,
            "minimum_eligible_count": 500,
            "maximum_eligible_count": 500,
            "minimum_candidate_count": 500,
            "maximum_candidate_count": 500,
            "invalid_decision_count": 0,
        }
    }
    assert report["post_entry_outcomes_opened"] is False
    assert report["embargo_or_prospective_data_accessed"] is False
    assert report["security_identifiers_in_report"] is False
    assert report["strategy_candidate_available"] is False
    structural = salient.DecisionAudit(salient.VARIANT_ID, decision, 499, 499, True, False)
    assert (
        preflight._preflight_report(
            (structural,),
            (salient.COVERAGE_START, salient.HISTORICAL_CUTOFF),
            (True, 0.95, 0.0, 0),
        )["status"]
        == "STRUCTURAL_FAIL"
    )
    blocked = salient.DecisionAudit(salient.VARIANT_ID, decision, 500, 500, False, False)
    assert (
        preflight._preflight_report(
            (blocked,),
            (salient.COVERAGE_START, salient.HISTORICAL_CUTOFF),
            (True, 0.95, 0.0, 0),
        )["status"]
        == "INPUT_BLOCKED"
    )
    with pytest.raises(salient.SalientReturnContractError, match="duplicate"):
        preflight._preflight_report(
            (valid, valid),
            (salient.COVERAGE_START, salient.HISTORICAL_CUTOFF),
            (True, 0.95, 0.0, 0),
        )


def test_monthly_scanner_rejects_duplicate_symbol_date_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DuplicateConnection:
        def execute(self, *_: object) -> "DuplicateConnection":
            return self

        def fetchall(self) -> list[tuple[object, ...]]:
            dates = [day.strftime("%Y%m%d") for day in days]
            dates[-1] = dates[-2]
            return [
                (
                    "000001.SZ",
                    dates,
                    [10.0] * len(dates),
                    [30_000_000.0] * len(dates),
                    False,
                    False,
                    False,
                    False,
                    "L",
                    1_000_000.0,
                    30_000_000.0,
                    "a" * 64,
                    preflight.CLASSIFICATION,
                    True,
                )
            ]

    days = (date(2024, 12, 31),) + tuple(
        date(2025, 1, 1) + timedelta(days=index) for index in range(20)
    )
    monkeypatch.setattr(preflight, "MIN_LISTED_SESSIONS", 1)
    with pytest.raises(salient.SalientReturnContractError, match="duplicate"):
        preflight._monthly_signals(
            DuplicateConnection(),
            days,
            len(days) - 1,
            {"000001.SZ": (date(2024, 1, 1), None)},
        )


def test_fourteen_session_month_is_structural_audit_and_fifteen_uses_ordinary_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    january = tuple(date(2025, 1, 2) + timedelta(days=index) for index in range(14))
    february = tuple(date(2025, 2, 1) + timedelta(days=index) for index in range(15))
    calendar = _calendar(january + february + (date(2025, 3, 1),))

    class Result:
        def fetchall(self) -> list[tuple[object, ...]]:
            return []

    class Connection:
        def execute(self, *_: object) -> Result:
            return Result()

    ordinary_calls: list[date] = []

    def monthly_signals(
        _connection: object,
        days: tuple[date, ...],
        position: int,
        _masters: object,
    ) -> tuple[tuple[salient.MonthlySignal, ...], dict[str, tuple[float, float, str]]]:
        ordinary_calls.append(days[position])
        return (), {}

    def ordinary_target(
        _signals: object,
        _calendar_value: object,
        *,
        decision_date: date,
        decision_at: datetime,
        execution_inputs: object,
    ) -> tuple[None, salient.DecisionAudit]:
        assert decision_at.tzinfo is not None
        assert execution_inputs == ()
        return None, salient.DecisionAudit(salient.VARIANT_ID, decision_date, 500, 500, True, True)

    monkeypatch.setattr(preflight, "MIN_LISTED_SESSIONS", 0)
    monkeypatch.setattr(preflight, "_monthly_signals", monthly_signals)
    monkeypatch.setattr(preflight, "build_monthly_target", ordinary_target)
    audits, decisions = preflight._database_audits(Connection(), calendar)
    assert decisions == (january[-1], february[-1])
    assert audits[0] == salient.DecisionAudit(salient.VARIANT_ID, january[-1], 0, 0, False, False)
    assert audits[1] == salient.DecisionAudit(
        salient.VARIANT_ID, february[-1], 500, 500, True, True
    )
    assert ordinary_calls == [february[-1]]
    report = preflight._preflight_report(
        audits,
        (january[0], february[-1]),
        (True, 0.9, 0.0, 0),
    )
    aggregate = report["variant_aggregates"][salient.VARIANT_ID]
    assert report["status"] == "STRUCTURAL_FAIL"
    assert aggregate["minimum_eligible_count"] == 0
    assert aggregate["minimum_candidate_count"] == 0
    assert aggregate["invalid_decision_count"] == 1


def _tiny_read_only_database(root: Path) -> tuple[Path, tuple[date, ...]]:
    import duckdb

    database = root / "quant_research.duckdb"
    connection = duckdb.connect(str(database))
    connection.execute("CREATE SCHEMA a_share")
    connection.execute(
        "CREATE TABLE a_share.a_share_canonical_daily_bars("
        "snapshot_id VARCHAR,trade_date VARCHAR,quality_status VARCHAR,"
        "synthetic_data BOOLEAN)"
    )
    days = (date(2025, 1, 2), date(2025, 1, 3), date(2025, 1, 6))
    connection.executemany(
        "INSERT INTO a_share.a_share_canonical_daily_bars VALUES (?,?,?,false)",
        [
            ("test-snapshot", days[0].strftime("%Y%m%d"), preflight.CLASSIFICATION),
            ("test-snapshot", days[-1].strftime("%Y%m%d"), preflight.CLASSIFICATION),
        ],
    )
    connection.execute(
        "CREATE TABLE a_share.a_share_trade_calendar("
        "trade_date VARCHAR,row_hash VARCHAR,synthetic_data BOOLEAN,"
        "is_open INTEGER,exchange VARCHAR)"
    )
    connection.executemany(
        "INSERT INTO a_share.a_share_trade_calendar VALUES (?,?,false,1,'SSE')",
        [(day.strftime("%Y%m%d"), hashlib.sha256(str(day).encode()).hexdigest()) for day in days],
    )
    connection.close()
    return database, days


def test_read_only_preflight_binds_receipt_is_repeatable_and_never_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database, days = _tiny_read_only_database(tmp_path)
    database_hash = hashlib.sha256(database.read_bytes()).hexdigest()
    receipt_dir = tmp_path / "receipts"
    receipt_dir.mkdir()
    receipt = receipt_dir / "receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "post_db_sha256": database_hash,
                "target_snapshot": "test-snapshot",
                "v5_digest": "b" * 64,
                "date_start": days[0].strftime("%Y%m%d"),
                "date_end": days[-1].strftime("%Y%m%d"),
                "volume_unit": "SHARES",
                "amount_unit": "CNY",
                "status": "PUBLISHED_V5_VOLUME_UNIT_SHARES_VERIFIED",
                "strategy_candidate_available": False,
                "strategy_outcomes_opened": False,
                "target_rows": 2,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(preflight, "DATABASE_SHA256", database_hash)
    monkeypatch.setattr(preflight, "SNAPSHOT_ID", "test-snapshot")
    monkeypatch.setattr(preflight, "SNAPSHOT_DIGEST", "b" * 64)
    monkeypatch.setattr(preflight, "SNAPSHOT_RECEIPT_FILENAME", receipt.name)
    monkeypatch.setattr(
        preflight,
        "SNAPSHOT_RECEIPT_SHA256",
        hashlib.sha256(receipt.read_bytes()).hexdigest(),
    )
    monkeypatch.setattr(preflight, "COVERAGE_START", days[0])
    monkeypatch.setattr(preflight, "HISTORICAL_CUTOFF", days[-1])
    monkeypatch.setattr(preflight, "MIN_LISTED_SESSIONS", 1)
    audit = salient.DecisionAudit(salient.VARIANT_ID, days[1], 500, 500, True, True)
    monkeypatch.setattr(preflight, "_database_audits", lambda *_: ((audit,), (days[1],)))
    monkeypatch.setattr(preflight, "_benchmark_probe", lambda *_: (True, 0.9, 0.0, 0))
    before = database.read_bytes()
    first = preflight.run_read_only_preflight(database)
    second = preflight.run_read_only_preflight(database)
    assert first == second
    assert first["status"] == "PREFLIGHT_PASS"
    assert first["post_entry_outcomes_opened"] is False
    assert database.read_bytes() == before


def test_database_hash_mismatch_fails_before_duckdb_and_preserves_bytes(
    tmp_path: Path,
) -> None:
    database = tmp_path / "not-the-frozen-database.duckdb"
    database.write_bytes(b"not a database")
    before = database.read_bytes()
    with pytest.raises(salient.SalientReturnContractError, match="SHA-256"):
        preflight.run_read_only_preflight(database)
    assert database.read_bytes() == before
