from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import hashlib
from statistics import fmean

import pytest

from quant_system.data import AcceptedSession, AcceptedSessionCalendar, SourceIdentity
from quant_system.research.young_chairman import (
    BENCHMARK_SYMBOL,
    COST_BPS_PER_SIDE,
    HORIZON_SESSIONS,
    REQUIRED_COVERAGE_DOMAINS,
    DailyBar,
    ManagementRecord,
    MarketCapPoint,
    PITDomainCoverage,
    SecurityState,
    SignalAssessment,
    YoungChairmanContractError,
    evaluate_signal,
    plan_fixed_horizon_events,
)


UTC = timezone.utc
SIGNAL_DATE = date(2024, 8, 6)
ENTRY_DATE = date(2024, 8, 7)


def _source(name: str, *, available_at: datetime | None = None) -> SourceIdentity:
    available = available_at or datetime(2020, 1, 1, tzinfo=UTC)
    retrieved = max(available, datetime(2024, 8, 8, tzinfo=UTC))
    return SourceIdentity(
        source_url=f"https://example.test/{name}",
        content_sha256=hashlib.sha256(name.encode()).hexdigest(),
        available_at=available,
        retrieved_at=retrieved,
        revision_id=name,
    )


def _business_dates(start: date, end: date) -> tuple[date, ...]:
    values = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            values.append(current)
        current += timedelta(days=1)
    return tuple(values)


def _session(value: date, *, source: SourceIdentity | None = None) -> AcceptedSession:
    return AcceptedSession(
        value,
        datetime(value.year, value.month, value.day, 1, 30, tzinfo=UTC),
        datetime(value.year, value.month, value.day, 7, 0, tzinfo=UTC),
        source or _source("calendar"),
        "Asia/Shanghai",
    )


def _fixture() -> dict[str, object]:
    dates = _business_dates(date(2023, 12, 1), ENTRY_DATE)
    calendar = AcceptedSessionCalendar(tuple(_session(value) for value in dates))
    bar_dates = tuple(value for value in dates if value <= SIGNAL_DATE)
    closes = [100.0] * len(bar_dates)
    closes[-11:-1] = [10.0] * 10
    closes[-1] = 20.0
    bars = tuple(
        DailyBar(
            "000001.SZ",
            session_date,
            close_value,
            close_value,
            close_value,
            close_value,
            _source("raw-bars"),
            _source("adjusted-bars"),
            _source("corporate-actions"),
        )
        for session_date, close_value in zip(bar_dates, closes, strict=True)
    )
    coverage = tuple(
        PITDomainCoverage(
            domain,
            bar_dates[0],
            ENTRY_DATE,
            True,
            _source(f"coverage-{domain}"),
        )
        for domain in sorted(REQUIRED_COVERAGE_DOMAINS)
    )
    manager = ManagementRecord(
        "000001.SZ",
        "person-1",
        "董事长兼总经理",
        date(2023, 6, 1),
        date(2023, 5, 31),
        None,
        date(1990, 2, 3),
        "day",
        _source("management"),
    )
    market_cap = MarketCapPoint(
        "000001.SZ", SIGNAL_DATE, 1_100_000_000.0, _source("market-cap")
    )
    state = SecurityState(
        "000001.SZ",
        ENTRY_DATE,
        date(2023, 1, 3),
        None,
        False,
        False,
        _source("listing"),
        _source("suspension"),
        _source("limit"),
    )
    return {
        "symbol": "000001.SZ",
        "signal_date": SIGNAL_DATE,
        "entry_session": _session(ENTRY_DATE),
        "calendar": calendar,
        "managers": (manager,),
        "market_cap": market_cap,
        "security_state": state,
        "bars": bars,
        "coverage": coverage,
    }


def _evaluate(**changes: object) -> SignalAssessment:
    values = _fixture()
    values.update(changes)
    return evaluate_signal(**values)  # type: ignore[arg-type]


def test_frozen_positive_signal_uses_prior_30_completed_weeks_only() -> None:
    values = _fixture()
    result = evaluate_signal(**values)  # type: ignore[arg-type]

    assert result.status == "ELIGIBLE"
    assert result.reasons == ()
    assert result.conservative_age_upper == 34
    bars = values["bars"]
    assert isinstance(bars, tuple)
    weekly_last: dict[tuple[int, int], DailyBar] = {}
    for row in bars:
        week = row.session_date.isocalendar()[:2]
        if week < SIGNAL_DATE.isocalendar()[:2]:
            weekly_last[week] = row
    expected = fmean(
        tuple(weekly_last[key].adjusted_close for key in sorted(weekly_last))[-30:]
    )
    assert result.weekly_close_mean_30 == expected
    assert result.weekly_close_mean_30 > bars[-1].adjusted_close


def test_missing_or_late_identity_blocks_before_economic_screen() -> None:
    fixture = _fixture()
    coverage = tuple(
        row for row in fixture["coverage"] if row.domain != "management"  # type: ignore[union-attr]
    )
    assert _evaluate(coverage=coverage).reasons == ("missing_coverage:management",)

    cap = fixture["market_cap"]
    assert isinstance(cap, MarketCapPoint)
    late_cap = replace(
        cap,
        source=_source(
            "late-cap", available_at=datetime(2024, 8, 7, 2, 0, tzinfo=UTC)
        ),
    )
    late_result = _evaluate(market_cap=late_cap)
    assert late_result.status == "BLOCKED"
    assert late_result.reasons == ("late_signal_date_market_cap",)


def test_late_adjusted_revision_and_future_bar_are_never_used() -> None:
    fixture = _fixture()
    bars = fixture["bars"]
    assert isinstance(bars, tuple)
    late = replace(
        bars[-1],
        adjusted_source=_source(
            "late-adjusted", available_at=datetime(2024, 8, 7, 2, 0, tzinfo=UTC)
        ),
    )
    result = _evaluate(bars=(*bars[:-1], late))
    assert result.status == "BLOCKED"
    assert f"late_adjusted_bar:{SIGNAL_DATE.isoformat()}" in result.reasons

    future = replace(bars[-1], session_date=ENTRY_DATE)
    assert _evaluate(bars=(*bars, future)).reasons == ("bar_window_not_cut_at_signal",)


def test_management_available_at_and_announcement_date_are_point_in_time() -> None:
    fixture = _fixture()
    manager = fixture["managers"][0]  # type: ignore[index]
    assert isinstance(manager, ManagementRecord)
    late = replace(
        manager,
        source=_source(
            "late-manager", available_at=datetime(2024, 8, 7, 2, 0, tzinfo=UTC)
        ),
    )
    assert _evaluate(managers=(late,)).reasons == ("no_active_qualifying_chairman",)
    future_announcement = replace(manager, ann_date=date(2024, 8, 7))
    assert _evaluate(managers=(future_announcement,)).reasons == (
        "no_active_qualifying_chairman",
    )


def test_role_begin_and_single_active_chairman_are_exact() -> None:
    fixture = _fixture()
    manager = fixture["managers"][0]  # type: ignore[index]
    assert isinstance(manager, ManagementRecord)
    vice = replace(manager, title="副董事长")
    honorary = replace(manager, title="名誉董事长")
    assert _evaluate(managers=(vice, honorary)).status == "INELIGIBLE"
    begins_on_signal = replace(manager, begin_date=SIGNAL_DATE)
    assert _evaluate(managers=(begins_on_signal,)).reasons == (
        "no_active_qualifying_chairman",
    )
    second = replace(manager, person_id="person-2")
    ambiguous = _evaluate(managers=(manager, second))
    assert ambiguous.status == "BLOCKED"
    assert ambiguous.reasons == ("ambiguous_active_chairmen",)


def test_conservative_birthday_precision_fails_closed_at_age_boundary() -> None:
    fixture = _fixture()
    manager = fixture["managers"][0]  # type: ignore[index]
    assert isinstance(manager, ManagementRecord)
    unknown = replace(manager, birthday=None, birthday_precision="unknown")
    assert _evaluate(managers=(unknown,)).reasons == ("birthday_precision_unknown",)

    year_only = replace(
        manager,
        birthday=date(1984, 1, 1),
        birthday_precision="year",
    )
    result = _evaluate(managers=(year_only,))
    assert result.status == "INELIGIBLE"
    assert result.conservative_age_upper == 40
    assert result.reasons == ("chairman_age_upper_not_below_40",)


def test_market_cap_and_three_calendar_year_boundaries_are_strict() -> None:
    fixture = _fixture()
    cap = fixture["market_cap"]
    state = fixture["security_state"]
    assert isinstance(cap, MarketCapPoint)
    assert isinstance(state, SecurityState)
    cap_result = _evaluate(market_cap=replace(cap, total_mv_cny=1_000_000_000.0))
    assert cap_result.reasons == ("market_cap_not_above_1bn",)
    listing_result = _evaluate(
        security_state=replace(state, list_date=date(2021, 8, 6))
    )
    assert listing_result.reasons == ("not_within_first_three_calendar_years",)


@pytest.mark.parametrize(
    ("change", "reason"),
    (
        ({"is_suspended": True}, "entry_session_suspended"),
        ({"is_limit_up": True}, "entry_session_limit_up_not_executable"),
    ),
)
def test_known_entry_execution_blocks_are_not_imputed(change, reason) -> None:
    state = _fixture()["security_state"]
    assert isinstance(state, SecurityState)
    result = _evaluate(security_state=replace(state, **change))
    assert result.status == "INELIGIBLE"
    assert result.reasons == (reason,)


def test_st_status_is_not_a_required_domain_or_strategy_filter() -> None:
    assert "st_status" not in REQUIRED_COVERAGE_DOMAINS
    assert _evaluate().status == "ELIGIBLE"


def test_technical_and_history_gaps_fail_without_parameter_repair() -> None:
    fixture = _fixture()
    bars = fixture["bars"]
    assert isinstance(bars, tuple)
    flat = tuple(replace(row, adjusted_close=100.0) for row in bars)
    result = _evaluate(bars=flat)
    assert result.status == "INELIGIBLE"
    assert "ma5_did_not_cross_above_ma10" in result.reasons
    assert "close_not_below_30week_mean" in result.reasons

    short = tuple(row for row in bars if row.session_date >= date(2024, 6, 1))
    short_coverage = tuple(
        replace(row, start=short[0].session_date) for row in fixture["coverage"]  # type: ignore[union-attr]
    )
    blocked = _evaluate(bars=short, coverage=short_coverage)
    assert blocked.status == "BLOCKED"
    assert blocked.reasons == ("fewer_than_30_completed_weeks",)


def _eligible(symbol: str, sessions: tuple[date, ...], position: int) -> SignalAssessment:
    entry = sessions[position]
    return SignalAssessment(
        symbol,
        entry - timedelta(days=1),
        entry,
        "ELIGIBLE",
        (),
        35,
        100.0,
    )


def _eligible_with_signal(
    symbol: str,
    sessions: tuple[date, ...],
    *,
    signal_position: int,
    entry_position: int,
) -> SignalAssessment:
    return SignalAssessment(
        symbol,
        sessions[signal_position],
        sessions[entry_position],
        "ELIGIBLE",
        (),
        35,
        100.0,
    )


def test_horizon_planning_is_fixed_nonoverlapping_and_outcome_free() -> None:
    sessions = _business_dates(date(2015, 1, 1), date(2023, 12, 31))
    assessments = (
        _eligible("000001.SZ", sessions, 0),
        _eligible("000001.SZ", sessions, 100),
        _eligible_with_signal(
            "000001.SZ", sessions, signal_position=252, entry_position=253
        ),
        _eligible_with_signal(
            "000001.SZ", sessions, signal_position=253, entry_position=254
        ),
        _eligible("000001.SZ", sessions, len(sessions) - 10),
    )

    plans = plan_fixed_horizon_events(assessments, sessions)

    assert tuple(plan.horizon_sessions for plan in plans) == HORIZON_SESSIONS
    assert tuple(event.entry_date for event in plans[0].events) == (
        sessions[0],
        sessions[254],
    )
    assert tuple(event.exit_date for event in plans[0].events) == (
        sessions[252],
        sessions[506],
    )
    assert plans[0].overlap_excluded_count == 2
    assert plans[0].incomplete_count == 1
    assert plans[1].overlap_excluded_count == 3
    assert plans[1].incomplete_count == 1
    assert all(event.horizon_sessions in HORIZON_SESSIONS for plan in plans for event in plan.events)
    assert BENCHMARK_SYMBOL == "510300.SH"
    assert COST_BPS_PER_SIDE == 50.0


def test_planner_rejects_noneligible_or_duplicate_inputs() -> None:
    sessions = _business_dates(date(2020, 1, 1), date(2022, 12, 31))
    eligible = _eligible("000001.SZ", sessions, 0)
    with pytest.raises(YoungChairmanContractError, match="only ELIGIBLE"):
        plan_fixed_horizon_events((replace(eligible, status="BLOCKED"),), sessions)
    with pytest.raises(YoungChairmanContractError, match="unique"):
        plan_fixed_horizon_events((eligible, eligible), sessions)
