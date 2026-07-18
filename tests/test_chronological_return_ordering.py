from __future__ import annotations

from dataclasses import replace
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
from quant_system.research import chronological_return_ordering as cro
from scripts import run_a_share_chronological_return_ordering_preflight as preflight

ROOT = Path(__file__).resolve().parents[1]
DEFINITION = ROOT / "research/definitions/a_share_chronological_return_ordering_monthly_v1.json"
GOLDEN_CLOSES = (
    100.0,
    103.0,
    101.97,
    104.0094,
    104.0094,
    108.169776,
    106.00638047999999,
    107.06644428479999,
    112.41976649904,
    109.0471735040688,
    111.22811697415017,
    112.34039814389168,
    116.83401406964735,
    115.66567392895088,
    119.13564414681942,
)


def _source() -> SourceIdentity:
    available = datetime(2000, 1, 1, tzinfo=timezone.utc)
    return SourceIdentity(
        "https://example.test/calendar",
        hashlib.sha256(b"calendar").hexdigest(),
        available,
        available,
        "calendar",
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
            _source(),
            "Asia/Shanghai",
        )
        for day in days
    )


def _formation_rows(count: int = 1000) -> tuple[cro.FormationRow, ...]:
    return tuple(
        cro.FormationRow(
            f"600{index:03d}.SH",
            GOLDEN_CLOSES,
            (60_000_000.0,) * 14,
        )
        for index in range(count)
    )


def test_definition_hash_and_frozen_non_pit_boundaries() -> None:
    raw = DEFINITION.read_bytes()
    frozen = json.loads(raw)
    assert hashlib.sha256(raw).hexdigest() == cro.DEFINITION_SHA256
    assert frozen["research_id"] == cro.RESEARCH_ID
    assert frozen["input_identity"]["observed_snapshot_cohort_only"] is True
    assert frozen["input_identity"]["strict_pit_eligible"] is False
    assert frozen["cohort_coverage_disclosure"] == {
        "master_ordinary_count_expected": 5208,
        "observed_snapshot_ordinary_count_expected": 2909,
        "unobserved_master_ordinary_count_expected": 2299,
        "runtime_rule": (
            "recompute the observed snapshot set and exact master set difference; never cross "
            "join the full master into the signal universe"
        ),
        "interpretation": (
            "retrospective evidence for the observed cohort only, not full-universe or PIT evidence"
        ),
    }
    assert frozen["historical_sequential_access"].startswith("Adjudicate validation first")
    assert frozen["execution_state"]["strategy_candidate_available"] is False


@pytest.mark.parametrize(
    ("symbol", "accepted"),
    (
        ("600001.SH", True),
        ("688001.SH", True),
        ("000001.SZ", True),
        ("301001.SZ", True),
        ("510300.SH", False),
        ("900001.SH", False),
        ("600001.BJ", False),
    ),
)
def test_frozen_common_a_boards(symbol: str, accepted: bool) -> None:
    assert cro.common_a_symbol(symbol) is accepted


def test_cro_has_literal_nonconstant_golden_and_fail_closed_variance() -> None:
    assert cro.chronological_return_ordering(GOLDEN_CLOSES) == pytest.approx(0.06050024991854076)
    constant_returns = (100.0,) * 15
    assert cro.chronological_return_ordering(constant_returns) is None
    assert cro.chronological_return_ordering(GOLDEN_CLOSES[:-1]) is None
    bad = list(GOLDEN_CLOSES)
    bad[3] = math.nan
    assert cro.chronological_return_ordering(bad) is None


def test_formation_exclusions_and_deterministic_low_decile() -> None:
    rows = _formation_rows()
    selection = cro.select_low_cro(rows)
    assert selection.valid
    assert selection.eligible_symbols == tuple(f"600{index:03d}.SH" for index in range(1000))
    assert selection.selected_symbols == tuple(f"600{index:03d}.SH" for index in range(100))
    excluded = (
        cro.FormationRow("601000.SH", GOLDEN_CLOSES, (49_999_999.0,) * 14),
        cro.FormationRow("601001.SH", (100.0,) * 15, (60e6,) * 14),
        cro.FormationRow("601002.SH", GOLDEN_CLOSES[:-1] + (None,), (60e6,) * 14),
    )
    screened = cro.select_low_cro((*rows, *excluded))
    assert screened == selection
    with pytest.raises(cro.ChronologicalReturnOrderingError, match="duplicate"):
        cro.select_low_cro((rows[0], rows[0]))


def test_timing_uses_month_end_next_open_and_following_month_end() -> None:
    calendar = _calendar(date(2021, 12, 1), date(2022, 3, 4))
    zone = ZoneInfo("Asia/Shanghai")
    entry, exit_day, identity = cro.interval_dates(
        calendar,
        decision_date=date(2022, 1, 31),
        as_of=datetime(2022, 1, 31, 16, tzinfo=zone),
    )
    assert (entry, exit_day, identity) == (
        date(2022, 2, 1),
        date(2022, 3, 1),
        "validation_2022_2023",
    )
    with pytest.raises(cro.ChronologicalReturnOrderingError, match="last accepted"):
        cro.interval_dates(
            calendar,
            decision_date=date(2022, 1, 28),
            as_of=datetime(2022, 1, 28, 16, tzinfo=zone),
        )


def _panels(selection: cro.Selection) -> tuple[cro.PricePanel, ...]:
    return tuple(
        cro.PricePanel(symbol, 10.0, 11.0, 1.0, 1.0) for symbol in selection.eligible_symbols
    )


def test_all_benchmark_panels_are_required_and_identity_checked() -> None:
    selection = cro.select_low_cro(_formation_rows())
    panels = _panels(selection)
    assert cro.validate_price_panels(selection, panels) == panels
    with pytest.raises(cro.ChronologicalReturnOrderingError, match="every benchmark"):
        cro.validate_price_panels(selection, panels[:-1])
    broken = (*panels[:-1], replace(panels[-1], entry_row_hash="bad"))
    with pytest.raises(cro.ChronologicalReturnOrderingError, match="identity"):
        cro.validate_price_panels(selection, broken)
    nonfinite = (*panels[:-1], replace(panels[-1], exit_qfq_open=math.inf))
    with pytest.raises(cro.ChronologicalReturnOrderingError, match="finite"):
        cro.validate_price_panels(selection, nonfinite)


def test_pcg64_block3_golden_and_bootstrap_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    assert circular_block_start_indices(5, draws=3, seed=20260725) == (
        (1, 3),
        (2, 1),
        (1, 4),
    )
    calls: list[tuple[int, int, int]] = []

    def starts(size: int, *, draws: int, seed: int) -> tuple[tuple[int, ...], ...]:
        calls.append((size, draws, seed))
        return ((0,),) * draws

    monkeypatch.setattr(cro, "circular_block_start_indices", starts)
    result = cro.bootstrap_mean((1.0, 2.0, 3.0), seed=20260725)
    assert calls == [(3, 10_000, 20260725)]
    assert result.observed_mean == 2.0
    assert result.p_value == pytest.approx(1 / 10001)
    assert result.lower_bound == 2.0


def _audits(validation: int = 23, holdout: int = 24) -> tuple[preflight.IntervalAudit, ...]:
    output: list[preflight.IntervalAudit] = []
    for split, start, count in (
        ("development_2020_2021", date(2020, 1, 1), 2),
        ("validation_2022_2023", date(2022, 1, 1), validation),
        ("retrospective_holdout_2024_2026m4", date(2024, 1, 1), holdout),
    ):
        output.extend(
            preflight.IntervalAudit(
                start + timedelta(days=index),
                split,
                20,
                1000,
                100,
                panel_count=1000,
            )
            for index in range(count)
        )
    return tuple(output)


def _report(rows: tuple[preflight.IntervalAudit, ...]) -> dict[str, object]:
    return preflight._report(
        rows,
        (5208, 2909, 2299, 0),
        (cro.COVERAGE_START, cro.HISTORICAL_CUTOFF),
    )


def test_aggregate_report_allowlist_split_bounds_and_no_outcomes() -> None:
    report = _report(_audits())
    assert report["status"] == "PREFLIGHT_PASS"
    assert report["split_interval_counts"]["validation_2022_2023"] == 23
    assert report["split_interval_counts"]["retrospective_holdout_2024_2026m4"] == 24
    assert (report["master_ordinary_count"], report["observed_ordinary_count"]) == (5208, 2909)
    assert report["unobserved_ordinary_count"] == 2299
    assert report["post_entry_outcomes_opened"] is False
    assert report["security_identifiers_in_report"] is False
    assert report["strategy_candidate_available"] is False
    prohibited = {"cro", "rank", "symbols", "returns", "p_value", "lower_bound", "nav"}
    assert set(report).isdisjoint(prohibited)
    assert _report(_audits(validation=19))["status"] == "STRUCTURAL_FAIL"
    assert _report(_audits(validation=24))["status"] == "STRUCTURAL_FAIL"
    assert _report(_audits(holdout=23))["status"] == "STRUCTURAL_FAIL"


def test_report_exclusions_are_counts_but_panel_defects_fail_closed() -> None:
    rows = list(_audits())
    rows[0] = replace(rows[0], formation_missing=7)
    report = _report(tuple(rows))
    assert report["status"] == "PREFLIGHT_PASS"
    assert report["formation_missing_count"] == 7
    rows[0] = replace(rows[0], panel_missing=1)
    blocked = _report(tuple(rows))
    assert blocked["status"] == "INPUT_BLOCKED"
    assert blocked["split_invalid_interval_counts"]["development_2020_2021"] == 1
    assert (
        preflight._report(
            _audits(),
            (5208, 2909, 2299, 1),
            (cro.COVERAGE_START, cro.HISTORICAL_CUTOFF),
        )["status"]
        == "INPUT_BLOCKED"
    )


def test_validation_boundary_interval_is_counted_as_purged_not_vanished() -> None:
    connection = duckdb.connect(":memory:")
    connection.execute("CREATE SCHEMA a_share")
    connection.execute(
        "CREATE TABLE a_share.a_share_trade_calendar(snapshot_id VARCHAR,exchange VARCHAR,"
        "trade_date VARCHAR,is_open INTEGER,source VARCHAR,synthetic_data BOOLEAN)"
    )
    connection.execute(
        "CREATE TABLE a_share.a_share_canonical_daily_bars(snapshot_id VARCHAR,ts_code VARCHAR,"
        "trade_date VARCHAR,qfq_close DOUBLE,amount DOUBLE,adj_factor DOUBLE,"
        "quality_status VARCHAR,row_hash VARCHAR,synthetic_data BOOLEAN,qfq_open DOUBLE)"
    )
    days = ("20211029", "20211130", "20211231", "20220131", "20220228")
    connection.executemany(
        "INSERT INTO a_share.a_share_trade_calendar VALUES (?,?,?,?,?,?)",
        [
            (
                cro.CALENDAR_SNAPSHOT_ID,
                cro.CALENDAR_EXCHANGE,
                day,
                1,
                cro.CALENDAR_SOURCE,
                False,
            )
            for day in days
        ],
    )
    try:
        audits = preflight._database_audits(connection)
    finally:
        connection.close()
    assert {row.decision_date for row in audits} == {date(2021, 10, 29), date(2021, 12, 31)}
    assert {row.cross_boundary_purged for row in audits} == {1}


def test_definition_capture_rejects_changed_symlink_duplicate_and_nonfinite(tmp_path: Path) -> None:
    copy = tmp_path / "definition.json"
    copy.write_bytes(DEFINITION.read_bytes())
    assert preflight._definition(copy)["research_id"] == cro.RESEARCH_ID
    copy.write_text("{}", encoding="utf-8")
    with pytest.raises(cro.ChronologicalReturnOrderingError, match="SHA-256"):
        preflight._definition(copy)
    link = tmp_path / "link.json"
    link.symlink_to(DEFINITION)
    with pytest.raises(cro.ChronologicalReturnOrderingError, match="regular file"):
        preflight._capture(link, "link")
    with pytest.raises(cro.ChronologicalReturnOrderingError, match="duplicate"):
        preflight._strict_json(b'{"a":1,"a":2}', "fixture")
    with pytest.raises(cro.ChronologicalReturnOrderingError, match="nonfinite"):
        preflight._strict_json(b'{"a":NaN}', "fixture")
