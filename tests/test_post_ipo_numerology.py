from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb
import pytest

from quant_system.backtest.permanent_portfolio import circular_block_start_indices
from quant_system.data import AcceptedSession, AcceptedSessionCalendar, SourceIdentity
from quant_system.research import post_ipo_numerology as numerology
from scripts import run_a_share_post_ipo_numerology_preflight as preflight

ROOT = Path(__file__).resolve().parents[1]
DEFINITION = (
    ROOT / "research/definitions/a_share_post_ipo_numerological_overvaluation_avoidance_v1.json"
)


def _source(name: str) -> SourceIdentity:
    available = datetime(2000, 1, 1, tzinfo=timezone.utc)
    return SourceIdentity(
        f"https://example.test/{name}",
        hashlib.sha256(name.encode()).hexdigest(),
        available,
        available,
        name,
    )


def _calendar(start: date, end: date) -> AcceptedSessionCalendar:
    zone = ZoneInfo("Asia/Shanghai")
    days: list[date] = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return AcceptedSessionCalendar(
        AcceptedSession(
            day,
            datetime.combine(day, time(9, 30), zone),
            datetime.combine(day, time(15), zone),
            _source("calendar"),
            "Asia/Shanghai",
        )
        for day in days
    )


def _row(symbol: str, amount: float, *, age: int = 100, listed: date = date(2019, 9, 2)):
    return numerology.CohortRow(symbol, listed, age, (amount,) * 20)


def _side_symbols(lucky: bool, count: int) -> tuple[str, ...]:
    output: list[str] = []
    for number in range(600000, 601000):
        symbol = f"{number:06d}.SH"
        if numerology.lucky_code(symbol) is lucky:
            output.append(symbol)
        if len(output) == count:
            return tuple(output)
    raise AssertionError("test symbol generator exhausted")


def test_definition_hash_one_variant_secondary_cohort_and_sequential_access() -> None:
    raw = DEFINITION.read_bytes()
    frozen = json.loads(raw)
    assert hashlib.sha256(raw).hexdigest() == numerology.DEFINITION_SHA256
    assert frozen["research_id"] == numerology.RESEARCH_ID
    assert frozen["feature_contract"]["variant_count"] == 1
    assert frozen["input_identity"]["strict_pit_eligible"] is False
    assert frozen["input_identity"]["observed_snapshot_cohort_only"] is True
    assert frozen["cohort_coverage_disclosure"] == {
        "frozen_aggregate_audit_only": True,
        "master_ordinary_count_expected": 5208,
        "observed_snapshot_ordinary_count_expected": 2909,
        "unobserved_master_ordinary_count_expected": 2299,
        "runtime_rule": (
            "recompute all three counts from independently validated master and snapshot sets; "
            "unobserved equals exact master set difference and is never inferred"
        ),
        "interpretation": (
            "the screen describes only the observed snapshot cohort and is neither PIT-complete "
            "nor full-universe evidence"
        ),
    }
    assert frozen["universe"]["historical_st"] == "unknown and deliberately not a filter"
    assert frozen["historical_sequential_access"].startswith("Compute and adjudicate validation")
    assert frozen["execution_state"]["strategy_candidate_available"] is False


@pytest.mark.parametrize(
    ("symbol", "board"),
    (
        ("600001.SH", "SH_MAIN"),
        ("601001.SH", "SH_MAIN"),
        ("603001.SH", "SH_MAIN"),
        ("605001.SH", "SH_MAIN"),
        ("688001.SH", "STAR"),
        ("000001.SZ", "SZ_MAIN"),
        ("001001.SZ", "SZ_MAIN"),
        ("002001.SZ", "SZ_MAIN"),
        ("003001.SZ", "SZ_MAIN"),
        ("300001.SZ", "CHINEXT"),
        ("301001.SZ", "CHINEXT"),
    ),
)
def test_board_boundaries_are_exchange_aware(symbol: str, board: str) -> None:
    assert numerology.board_id(symbol) == board


@pytest.mark.parametrize(
    "symbol",
    (
        "600001.SZ",
        "000001.SH",
        "510300.SH",
        "900901.SH",
        "200001.SZ",
        "60001.SH",
        "A00001.SZ",
    ),
)
def test_nonordinary_cross_exchange_and_malformed_codes_are_excluded(symbol: str) -> None:
    assert numerology.board_id(symbol) is None
    with pytest.raises(numerology.PostIpoNumerologyContractError):
        numerology.lucky_code(symbol)


@pytest.mark.parametrize(
    ("symbol", "expected"),
    (
        ("600689.SH", True),
        ("600684.SH", False),
        ("600123.SH", False),
        ("000689.SZ", True),
        ("000604.SZ", False),
        ("000123.SZ", False),
        ("300111.SZ", False),
    ),
)
def test_lucky_code_uses_exact_exchange_suffix_and_forbidden_four(
    symbol: str, expected: bool
) -> None:
    assert numerology.lucky_code(symbol) is expected


def test_absolute_list_quarter_and_inclusive_accepted_session_age() -> None:
    assert numerology.list_quarter(date(2020, 1, 1)) == "2020Q1"
    assert numerology.list_quarter(date(2020, 12, 31)) == "2020Q4"
    calendar = _calendar(date(2022, 1, 3), date(2022, 1, 10))
    cutoff = datetime(2030, 1, 1, tzinfo=timezone.utc)
    assert (
        numerology.accepted_session_age(
            calendar,
            list_date=date(2022, 1, 1),
            decision_date=date(2022, 1, 10),
            as_of=cutoff,
        )
        == 6
    )
    with pytest.raises(numerology.PostIpoNumerologyContractError, match="unavailable"):
        numerology.accepted_session_age(
            calendar,
            list_date=date(2021, 12, 20),
            decision_date=date(2022, 1, 10),
            as_of=cutoff,
        )


def test_cohort_row_requires_exact_twenty_finite_amounts_and_frozen_age_range() -> None:
    assert _row("600001.SH", 10.0, age=60).eligible
    assert _row("600001.SH", 10.0, age=756).eligible
    assert not _row("600001.SH", 10.0, age=59).eligible
    assert not _row("600001.SH", 10.0, age=757).eligible
    with pytest.raises(numerology.PostIpoNumerologyContractError, match="twenty"):
        numerology.CohortRow("600001.SH", date(2020, 1, 1), 100, (1.0,) * 19)
    with pytest.raises(numerology.PostIpoNumerologyContractError, match="finite"):
        _row("600001.SH", float("nan"))


def test_pairing_is_ordinal_within_board_quarter_then_pool_liquidity_ranked() -> None:
    unlucky = _side_symbols(False, 3)
    lucky = _side_symbols(True, 3)
    rows = (
        _row(unlucky[0], 30.0),
        _row(unlucky[1], 10.0),
        _row(unlucky[2], 20.0),
        _row(lucky[0], 15.0),
        _row(lucky[1], 35.0),
        _row(lucky[2], 25.0),
    )
    pairs = numerology.build_pairs(rows)
    expected_unlucky = sorted(
        unlucky,
        key=lambda code: (-next(r.median_amount_cny for r in rows if r.symbol == code), code),
    )
    expected_lucky = sorted(
        lucky, key=lambda code: (-next(r.median_amount_cny for r in rows if r.symbol == code), code)
    )
    ordinal = dict(zip(expected_unlucky, expected_lucky, strict=True))
    assert {pair.not_lucky_symbol: pair.lucky_symbol for pair in pairs} == ordinal
    assert tuple(
        min(pair.not_lucky_median_amount, pair.lucky_median_amount) for pair in pairs
    ) == tuple(
        sorted(
            (min(pair.not_lucky_median_amount, pair.lucky_median_amount) for pair in pairs),
            reverse=True,
        )
    )


def test_pair_pool_caps_at_fifteen_without_tie_expansion_or_replacement() -> None:
    unlucky, lucky = _side_symbols(False, 16), _side_symbols(True, 16)
    pairs = numerology.build_pairs(tuple(_row(symbol, 10.0) for symbol in (*unlucky, *lucky)))
    assert len(pairs) == 15
    assert tuple(pair.not_lucky_symbol for pair in pairs) == tuple(sorted(unlucky)[:15])
    assert tuple(pair.lucky_symbol for pair in pairs) == tuple(sorted(lucky)[:15])
    assert len(numerology.build_pairs((_row(unlucky[0], 10.0),))) == 0


def test_monthly_interval_uses_next_open_and_first_open_after_next_month_end() -> None:
    calendar = _calendar(date(2021, 12, 1), date(2022, 4, 4))
    cutoff = datetime(2030, 1, 1, tzinfo=timezone.utc)
    assert numerology.interval_dates(calendar, decision_date=date(2022, 1, 31), as_of=cutoff) == (
        date(2022, 2, 1),
        date(2022, 3, 1),
        "validation_2022_2023",
    )
    with pytest.raises(numerology.PostIpoNumerologyContractError, match="last accepted"):
        numerology.interval_dates(calendar, decision_date=date(2022, 1, 28), as_of=cutoff)


def test_interval_purges_entry_exit_crossing_split() -> None:
    calendar = _calendar(date(2023, 10, 1), date(2024, 2, 5))
    with pytest.raises(numerology.PostIpoNumerologyContractError, match="one split"):
        numerology.interval_dates(
            calendar,
            decision_date=date(2023, 11, 30),
            as_of=datetime(2030, 1, 1, tzinfo=timezone.utc),
        )


def _fifteen_pairs() -> tuple[numerology.MatchedPair, ...]:
    unlucky, lucky = _side_symbols(False, 15), _side_symbols(True, 15)
    return tuple(
        numerology.MatchedPair(left, right, "SH_MAIN", "2019Q3", 1.0, 1.0)
        for left, right in zip(unlucky, lucky, strict=True)
    )


def test_synthetic_interval_is_arithmetic_paired_and_subtracts_friction_both_sides() -> None:
    pairs = _fifteen_pairs()
    prices = {pair.not_lucky_symbol: (10.0, 11.0) for pair in pairs} | {
        pair.lucky_symbol: (20.0, 21.0) for pair in pairs
    }
    result = numerology.synthetic_interval_return(pairs, prices)
    assert result.strategy_gross == pytest.approx(0.1)
    assert result.benchmark_gross == pytest.approx(0.05)
    assert result.strategy_net == pytest.approx(0.09)
    assert result.benchmark_net == pytest.approx(0.04)
    assert result.active == pytest.approx(0.05)
    with pytest.raises(numerology.PostIpoNumerologyContractError, match="fifteen"):
        numerology.synthetic_interval_return(pairs[:-1], prices)


def test_bootstrap_uses_literal_pcg64_block_starts_wrap_and_truncation() -> None:
    assert circular_block_start_indices(5, draws=3, seed=123) == (
        (0, 3),
        (2, 0),
        (4, 1),
    )
    result = numerology.bootstrap_mean((1.0, 2.0, 4.0, 8.0, 16.0), draws=3, seed=123)
    assert result.observed_mean == pytest.approx(6.2)
    assert result.p_value == pytest.approx(0.25)
    assert result.lower_bound == pytest.approx(6.2)
    assert (result.draws, result.seed) == (3, 123)


def test_geometric_annualization_and_failure_boundaries() -> None:
    assert numerology.annualized_net_return((0.01,) * 12) == pytest.approx(1.01**12 - 1)
    with pytest.raises(numerology.PostIpoNumerologyContractError, match="above -1"):
        numerology.annualized_net_return((0.01, -1.0))
    with pytest.raises(numerology.PostIpoNumerologyContractError, match="finite"):
        numerology.annualized_net_return((0.01, math.inf))


def _audits() -> tuple[preflight.IntervalAudit, ...]:
    output: list[preflight.IntervalAudit] = []
    for split, start, count in (
        ("development_2020_2021", date(2020, 1, 1), 2),
        ("validation_2022_2023", date(2022, 1, 1), 20),
        ("retrospective_holdout_2024_2026h1", date(2024, 1, 1), 24),
    ):
        output.extend(
            preflight.IntervalAudit(start + timedelta(days=index), split, 15, panel_count=30)
            for index in range(count)
        )
    return tuple(output)


def test_report_is_aggregate_only_allowlisted_and_discloses_cohort_gap() -> None:
    report = preflight._report(
        _audits(),
        (5208, 2909, 2299, 0),
        (numerology.COVERAGE_START, numerology.HISTORICAL_CUTOFF),
    )
    assert report["status"] == "PREFLIGHT_PASS"
    assert report["master_ordinary_count"] == 5208
    assert report["observed_ordinary_count"] == 2909
    assert report["unobserved_ordinary_count"] == 2299
    assert report["security_identifiers_in_report"] is False
    assert report["post_entry_outcomes_opened"] is False
    assert report["strategy_candidate_available"] is False
    prohibited = {"returns", "nav", "symbols", "pairs", "rankings", "p_value", "lower_bound"}
    assert set(report).isdisjoint(prohibited)


def test_report_status_precedence_is_input_blocked_then_structural() -> None:
    rows = list(_audits())
    rows[0] = preflight.IntervalAudit(rows[0].decision_date, rows[0].split_id, 14, panel_count=28)
    structural = preflight._report(
        rows,
        (5208, 2909, 2299, 0),
        (numerology.COVERAGE_START, numerology.HISTORICAL_CUTOFF),
    )
    assert structural["status"] == "STRUCTURAL_FAIL"
    rows[0] = preflight.IntervalAudit(
        rows[0].decision_date,
        rows[0].split_id,
        14,
        window_missing=1,
        panel_count=28,
    )
    blocked = preflight._report(
        rows,
        (5208, 2909, 2299, 0),
        (numerology.COVERAGE_START, numerology.HISTORICAL_CUTOFF),
    )
    assert blocked["status"] == "INPUT_BLOCKED"


def test_report_never_marks_qfq_complete_when_selected_panel_identity_fails() -> None:
    rows = list(_audits())
    row = rows[0]
    rows[0] = preflight.IntervalAudit(
        row.decision_date, row.split_id, 15, panel_count=30, panel_identity=1
    )
    report = preflight._report(
        rows,
        (5208, 2909, 2299, 0),
        (numerology.COVERAGE_START, numerology.HISTORICAL_CUTOFF),
    )
    assert report["status"] == "INPUT_BLOCKED"
    assert report["qfq_panel_identity_failure_count"] == 1
    assert report["qfq_panels_complete"] is False


def test_report_never_marks_adj_factor_complete_when_selected_panel_is_missing() -> None:
    rows = list(_audits())
    row = rows[0]
    rows[0] = preflight.IntervalAudit(
        row.decision_date, row.split_id, 15, panel_count=30, qfq_missing=1
    )
    report = preflight._report(
        rows,
        (5208, 2909, 2299, 0),
        (numerology.COVERAGE_START, numerology.HISTORICAL_CUTOFF),
    )
    assert report["status"] == "INPUT_BLOCKED"
    assert report["qfq_panel_missing_count"] == 1
    assert report["adj_factor_panels_complete"] is False


def test_definition_capture_rejects_changed_hash_symlink_duplicate_and_nonfinite(
    tmp_path: Path,
) -> None:
    copy = tmp_path / "definition.json"
    copy.write_bytes(DEFINITION.read_bytes())
    assert preflight._definition(copy)["research_id"] == numerology.RESEARCH_ID
    copy.write_text("{}", encoding="utf-8")
    with pytest.raises(numerology.PostIpoNumerologyContractError, match="SHA-256"):
        preflight._definition(copy)
    link = tmp_path / "link.json"
    link.symlink_to(DEFINITION)
    with pytest.raises(numerology.PostIpoNumerologyContractError, match="regular file"):
        preflight._capture(link, "link")
    with pytest.raises(numerology.PostIpoNumerologyContractError, match="duplicate"):
        preflight._strict_json(b'{"a":1,"a":2}', "fixture")
    with pytest.raises(numerology.PostIpoNumerologyContractError, match="nonfinite"):
        preflight._strict_json(b'{"a":NaN}', "fixture")


def _sql_fixture() -> duckdb.DuckDBPyConnection:
    connection = duckdb.connect(":memory:")
    connection.execute("CREATE SCHEMA a_share")
    connection.execute(
        "CREATE TABLE a_share.a_share_trade_calendar(snapshot_id VARCHAR,exchange VARCHAR,"
        "trade_date VARCHAR,is_open INTEGER,source VARCHAR,synthetic_data BOOLEAN)"
    )
    connection.execute(
        "CREATE TABLE a_share.a_share_symbol_master(snapshot_id VARCHAR,ts_code VARCHAR,"
        "list_date VARCHAR,source VARCHAR,ingested_at VARCHAR,row_hash VARCHAR,"
        "synthetic_data BOOLEAN)"
    )
    connection.execute(
        "CREATE TABLE a_share.a_share_canonical_daily_bars(snapshot_id VARCHAR,ts_code VARCHAR,"
        "trade_date VARCHAR,amount DOUBLE,adj_factor DOUBLE,qfq_open DOUBLE,"
        "quality_status VARCHAR,synthetic_data BOOLEAN,row_hash VARCHAR)"
    )
    calendar = _calendar(date(2019, 9, 2), date(2020, 5, 4)).session_dates
    connection.executemany(
        "INSERT INTO a_share.a_share_trade_calendar VALUES (?,?,?,?,?,?)",
        [
            (
                numerology.CALENDAR_SNAPSHOT_ID,
                numerology.CALENDAR_EXCHANGE,
                day.strftime("%Y%m%d"),
                1,
                numerology.CALENDAR_SOURCE,
                False,
            )
            for day in calendar
        ],
    )
    symbols = (*_side_symbols(False, 15), *_side_symbols(True, 15))
    connection.executemany(
        "INSERT INTO a_share.a_share_symbol_master VALUES (?,?,?,?,?,?,?)",
        [
            ("master", symbol, "20190902", "fixture", "2020-01-01", "legacy", False)
            for symbol in symbols
        ],
    )
    connection.executemany(
        "INSERT INTO a_share.a_share_canonical_daily_bars VALUES (?,?,?,?,?,?,?,?,?)",
        [
            (
                numerology.SNAPSHOT_ID,
                symbol,
                day.strftime("%Y%m%d"),
                30_000_000.0,
                1.0,
                10.0,
                preflight.CLASSIFICATION,
                False,
                "a" * 64,
            )
            for symbol in symbols
            for day in calendar
        ],
    )
    return connection


def test_scan_sql_accepts_complete_synthetic_panel_without_opening_returns() -> None:
    connection = _sql_fixture()
    try:
        audits = preflight._database_audits(connection)
    finally:
        connection.close()
    assert audits
    assert all(row.pair_count == 15 and row.panel_count == 30 for row in audits)
    assert all(
        row.window_missing
        + row.window_nonfinite
        + row.window_identity
        + row.qfq_missing
        + row.qfq_nonfinite
        + row.panel_identity
        == 0
        for row in audits
    )


@pytest.mark.parametrize(
    ("mutation", "field"),
    (
        (
            "UPDATE a_share.a_share_canonical_daily_bars SET qfq_open=NULL "
            "WHERE ts_code='600001.SH' AND trade_date='20200101'",
            "qfq_missing",
        ),
        (
            "UPDATE a_share.a_share_canonical_daily_bars SET adj_factor=-1 "
            "WHERE ts_code='600001.SH' AND trade_date='20200101'",
            "qfq_nonfinite",
        ),
        (
            "UPDATE a_share.a_share_canonical_daily_bars SET row_hash='bad' "
            "WHERE ts_code='600001.SH' AND trade_date='20191231'",
            "window_identity",
        ),
        (
            "DELETE FROM a_share.a_share_canonical_daily_bars WHERE ts_code='600001.SH' "
            "AND trade_date='20191231'",
            "window_missing",
        ),
        (
            "UPDATE a_share.a_share_canonical_daily_bars SET quality_status=NULL "
            "WHERE ts_code='600001.SH' AND trade_date='20200101'",
            "panel_identity",
        ),
    ),
)
def test_scan_sql_fails_closed_on_null_missing_nonfinite_and_identity_panel(
    mutation: str, field: str
) -> None:
    connection = _sql_fixture()
    try:
        connection.execute(mutation)
        audits = preflight._database_audits(connection)
    finally:
        connection.close()
    assert sum(getattr(row, field) for row in audits) > 0


def test_duplicate_key_audit_and_unique_panel_fail_closed() -> None:
    connection = _sql_fixture()
    try:
        duplicate = connection.execute(
            "SELECT * FROM a_share.a_share_canonical_daily_bars "
            "WHERE ts_code='600001.SH' AND trade_date='20191231'"
        ).fetchone()
        assert duplicate is not None
        connection.execute(
            "INSERT INTO a_share.a_share_canonical_daily_bars VALUES (?,?,?,?,?,?,?,?,?)",
            duplicate,
        )
        assert preflight._duplicate_keys(connection) == 1
        assert any(row.window_missing > 0 for row in preflight._database_audits(connection))
    finally:
        connection.close()
