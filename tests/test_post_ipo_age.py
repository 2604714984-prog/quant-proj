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
from quant_system.research import post_ipo_age as age
from scripts import run_a_share_post_ipo_age_preflight as preflight

ROOT = Path(__file__).resolve().parents[1]
DEFINITION = ROOT / "research/definitions/a_share_post_ipo_age_underperformance_avoidance_v1.json"


def _source() -> SourceIdentity:
    available = datetime(2000, 1, 1, tzinfo=timezone.utc)
    return SourceIdentity("https://example.test/calendar", "a" * 64, available, available, "test")


def _calendar(start: date, end: date) -> AcceptedSessionCalendar:
    zone, sessions = ZoneInfo("Asia/Shanghai"), []
    day = start
    while day <= end:
        if day.weekday() < 5:
            sessions.append(
                AcceptedSession(
                    day,
                    datetime.combine(day, time(9, 30), zone),
                    datetime.combine(day, time(15), zone),
                    _source(),
                    "Asia/Shanghai",
                )
            )
        day += timedelta(days=1)
    return AcceptedSessionCalendar(sessions)


def _row(symbol: str, board: str, listed: date, amount: float) -> age.CohortRow:
    return age.CohortRow(symbol, board, listed, (amount,) * 20)


def _pair(index: int) -> age.MatchedPair:
    return age.MatchedPair(f"young-{index:03d}", f"seasoned-{index:03d}", "Main", 2.0, 1.0)


def _panel(symbol: str, entry: float = 10.0, exit_price: float = 11.0) -> age.SelectedPanel:
    return age.SelectedPanel(
        symbol,
        entry,
        exit_price,
        1.0,
        1.0,
        "a" * 64,
        "b" * 64,
        preflight.CLASSIFICATION,
        preflight.CLASSIFICATION,
        False,
        False,
    )


def test_definition_is_frozen_secondary_one_variant_and_split_seeded() -> None:
    raw = DEFINITION.read_bytes()
    frozen = json.loads(raw)
    assert hashlib.sha256(raw).hexdigest() == age.DEFINITION_SHA256
    assert frozen["research_id"] == age.RESEARCH_ID
    assert frozen["age_feature"]["variant_count"] == 1
    assert frozen["input_identity"]["strict_pit_eligible"] is False
    assert frozen["cohort_disclosure"] == {
        "master_ordinary_count": 5208,
        "observed_snapshot_ordinary_count": 2909,
        "unobserved_master_ordinary_count": 2299,
        "historical_st": "unknown_and_not_used_as_filter",
        "scope": "observed_snapshot_cohort_only_not_full_universe",
    }
    assert frozen["inference"]["seeds"] == {
        "validation": 20260728,
        "retrospective_holdout": 20260729,
        "prospective_forward_closed": 20260730,
    }
    assert frozen["execution_state"]["strategy_candidate_available"] is False


def test_anniversary_clamps_leap_day_and_age_gap_is_exact() -> None:
    listed = date(2020, 2, 29)
    assert age.anniversary(listed, 3) == date(2023, 2, 28)
    assert age.anniversary(listed, 5) == date(2025, 2, 28)
    assert age.age_side(listed, date(2023, 2, 27)) == "young"
    assert age.age_side(listed, date(2023, 2, 28)) is None
    assert age.age_side(listed, date(2025, 2, 27)) is None
    assert age.age_side(listed, date(2025, 2, 28)) == "seasoned"
    assert age.age_side(date(2025, 1, 1), date(2024, 1, 1)) is None
    sql_day = duckdb.sql("SELECT DATE '2020-02-29' + INTERVAL 3 YEAR").fetchone()[0]
    assert sql_day.date() == date(2023, 2, 28)


def test_candidate_requires_exact_complete_amount_window() -> None:
    assert _row("opaque-A", "Main", date(2022, 1, 1), 1.0).median_amount_cny == 1.0
    with pytest.raises(age.PostIpoAgeContractError, match="twenty"):
        age.CohortRow("opaque", "Main", date(2020, 1, 1), (1.0,) * 19)
    with pytest.raises(age.PostIpoAgeContractError, match="finite"):
        _row("opaque", "Main", date(2020, 1, 1), math.nan)
    with pytest.raises(age.PostIpoAgeContractError, match="board"):
        _row("opaque", "Other", date(2020, 1, 1), 1.0)


def test_pairing_uses_opaque_identity_ties_and_exact_top_fifty() -> None:
    decision = date(2024, 1, 31)
    rows = []
    for index in range(51):
        rows.extend(
            (
                _row(f"Y:{index:02d}", "Main", date(2022, 1, 1), 100 - index),
                _row(f"S:{index:02d}", "Main", date(2010, 1, 1), 100 - index),
            )
        )
    pairs = age.build_pairs(rows, decision_date=decision)
    assert len(pairs) == 50
    assert pairs[0].young_symbol == "Y:00"
    assert pairs[-1].seasoned_symbol == "S:49"
    assert all(pair.board == "Main" for pair in pairs)
    source = (ROOT / "src/quant_system/research/post_ipo_age.py").read_text()
    assert all(token not in source for token in ("split('.')", "startswith(", "[-3:]", "[-4:]"))


def test_selected_panel_fails_closed_and_synthetic_return_is_fixed_fifty() -> None:
    pairs = tuple(_pair(index) for index in range(50))
    panels = {pair.seasoned_symbol: _panel(pair.seasoned_symbol) for pair in pairs}
    panels.update({pair.young_symbol: _panel(pair.young_symbol, 20.0, 21.0) for pair in pairs})
    frozen_pairs, frozen_panels = tuple(pairs), dict(panels)
    result = age.synthetic_interval_return(pairs, panels)
    assert result.seasoned_net == pytest.approx(0.09)
    assert result.young_net == pytest.approx(0.04)
    assert result.active == pytest.approx(0.05)
    assert pairs == frozen_pairs and panels == frozen_panels
    with pytest.raises(age.PostIpoAgeContractError, match="selected panel"):
        age.synthetic_interval_return(pairs, panels | {pairs[0].young_symbol: None})  # type: ignore[dict-item]
    with pytest.raises(age.PostIpoAgeContractError, match="finite"):
        _panel("opaque", math.nan)
    with pytest.raises(age.PostIpoAgeContractError, match="hash"):
        age.SelectedPanel(
            "opaque",
            1.0,
            1.0,
            1.0,
            1.0,
            "bad",
            "b" * 64,
            preflight.CLASSIFICATION,
            preflight.CLASSIFICATION,
            False,
            False,
        )


@pytest.mark.parametrize(
    "defect", ("object", "duplicate", "cross_side", "board", "nan", "negative")
)
def test_interval_rejects_malformed_pairs_without_mutating_inputs(defect: str) -> None:
    pairs = list(_pair(index) for index in range(50))
    panels = {pair.seasoned_symbol: _panel(pair.seasoned_symbol) for pair in pairs}
    panels.update({pair.young_symbol: _panel(pair.young_symbol) for pair in pairs})
    if defect == "object":
        pairs[0] = object()  # type: ignore[list-item]
    elif defect == "duplicate":
        pairs[1] = pairs[0]
    elif defect == "cross_side":
        pairs[1] = pairs[1]._replace(young_symbol=pairs[0].seasoned_symbol)
    elif defect == "board":
        pairs[0] = pairs[0]._replace(board="Other")
    elif defect == "nan":
        pairs[0] = pairs[0]._replace(young_median_amount=math.nan)
    else:
        pairs[0] = pairs[0]._replace(seasoned_median_amount=-1.0)
    frozen_pairs, frozen_panels = tuple(pairs), dict(panels)
    with pytest.raises(age.PostIpoAgeContractError):
        age.synthetic_interval_return(pairs, panels)  # type: ignore[arg-type]
    assert tuple(pairs) == frozen_pairs and panels == frozen_panels


def test_interval_rejects_overflow_without_mutating_panels() -> None:
    pairs = tuple(_pair(index) for index in range(50))
    panels = {pair.seasoned_symbol: _panel(pair.seasoned_symbol) for pair in pairs}
    panels.update({pair.young_symbol: _panel(pair.young_symbol) for pair in pairs})
    panels[pairs[0].seasoned_symbol] = _panel(pairs[0].seasoned_symbol, 1e-308, 1e308)
    frozen = dict(panels)
    with pytest.raises(age.PostIpoAgeContractError, match="finite"):
        age.synthetic_interval_return(pairs, panels)
    assert panels == frozen


def test_interval_uses_month_end_next_sessions_purges_boundaries_and_forbids_may() -> None:
    calendar = _calendar(date(2021, 11, 1), date(2026, 8, 3))
    cutoff = datetime(2030, 1, 1, tzinfo=timezone.utc)
    assert age.interval_dates(calendar, decision_date=date(2022, 1, 31), as_of=cutoff) == (
        date(2022, 2, 1),
        date(2022, 3, 1),
        "validation_2022_2023",
    )
    with pytest.raises(age.PostIpoAgeContractError, match="one split"):
        age.interval_dates(calendar, decision_date=date(2021, 11, 30), as_of=cutoff)
    with pytest.raises(age.PostIpoAgeContractError, match="forbidden"):
        age.interval_dates(calendar, decision_date=date(2026, 5, 29), as_of=cutoff)


def _audits(validation: int = 23) -> tuple[preflight.IntervalAudit, ...]:
    rows = [preflight.IntervalAudit(date(2019, 11, 29), None, True, 0)]
    for split, start, count in (
        ("development_2020_2021", date(2020, 1, 1), 2),
        ("validation_2022_2023", date(2022, 1, 1), validation),
        ("retrospective_holdout_2024_2026h1", date(2024, 1, 1), 24),
    ):
        rows.extend(
            preflight.IntervalAudit(start + timedelta(days=i), split, False, 50, panel_count=100)
            for i in range(count)
        )
    return tuple(rows)


def test_report_allowlist_has_no_ids_outcomes_and_candidate_exclusions_do_not_block() -> None:
    rows = list(_audits())
    rows[1] = preflight.IntervalAudit(
        rows[1].decision_date, rows[1].split_id, False, 50, 7, 9, panel_count=100
    )
    report = preflight._report(
        rows, (5208, 2909, 2299, 0), (age.COVERAGE_START, age.HISTORICAL_CUTOFF)
    )
    assert report["status"] == "PREFLIGHT_PASS"
    assert report["cross_boundary_purge_count"] == 1
    assert report["young_candidate_excluded_counts"]["development_2020_2021"] == 7
    assert report["security_identifiers_in_report"] is False
    assert report["post_entry_outcomes_opened"] is False
    assert report["holdout_outcomes_opened"] is False
    assert set(report).isdisjoint({"symbols", "pairs", "returns", "rankings", "p_value", "nav"})


def test_report_status_precedence_and_validation_maximum() -> None:
    structural = preflight._report(
        _audits(24), (5208, 2909, 2299, 0), (age.COVERAGE_START, age.HISTORICAL_CUTOFF)
    )
    assert structural["status"] == "STRUCTURAL_FAIL"
    rows = list(_audits())
    row = rows[1]
    rows[1] = preflight.IntervalAudit(
        row.decision_date, row.split_id, False, 50, panel_count=100, panel_missing=1
    )
    blocked = preflight._report(
        rows, (5208, 2909, 2299, 0), (age.COVERAGE_START, age.HISTORICAL_CUTOFF)
    )
    assert blocked["status"] == "INPUT_BLOCKED"
    assert blocked["split_invalid_interval_counts"]["development_2020_2021"] == 1


def test_strict_json_rejects_duplicates_and_sql_is_parameter_bound() -> None:
    with pytest.raises(age.PostIpoAgeContractError, match="duplicate"):
        preflight._strict_json(b'{"a":1,"a":2}', "probe")
    assert preflight._SCAN_SQL.count("?") == 14
    assert preflight._ORDINARY not in preflight._SCAN_SQL
    assert age.SNAPSHOT_ID not in preflight._SCAN_SQL


def test_pcg64_block_three_dependency_has_literal_golden_starts() -> None:
    frozen = json.loads(DEFINITION.read_bytes())
    assert frozen["inference"]["dependency"].endswith("circular_block_start_indices")
    assert frozen["inference"]["block_length_months"] == 3
    assert circular_block_start_indices(5, draws=3, seed=123) == ((0, 3), (2, 0), (4, 1))
