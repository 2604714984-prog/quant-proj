from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
import math
import sys
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from quant_system.backtest import ExecutionInput, Portfolio, run_static_rebalance
from quant_system.data import (
    AcceptedSession,
    AcceptedSessionCalendar,
    CalendarIdentity,
    CorporateActionIdentity,
    SourceIdentity,
    calendar_identity_sha256,
    session_dates_sha256,
    session_rows_sha256,
)
from quant_system.markets.universe import (
    StatusEvidence,
    UniverseSnapshotIdentity,
    lifecycle_coverage_sha256,
    ordered_members_sha256,
)

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.adapters import us_spy_volatility_managed as MODULE  # noqa: E402
from scripts import run_us_spy_volatility_managed_validation as SCRIPT  # noqa: E402

ADAPTER_PATH = ROOT / "research" / "adapters" / "us_spy_volatility_managed.py"
REPORT_PATH = ROOT / "research" / "reports" / "us_spy_volatility_managed_exposure_v1.json"
SCRIPT_PATH = ROOT / "scripts" / "run_us_spy_volatility_managed_validation.py"
UTC = timezone.utc
NY = ZoneInfo("America/New_York")
DEFINITION_SHA = hashlib.sha256(b"spy-definition").hexdigest()
ADAPTER_SHA = hashlib.sha256(b"spy-adapter").hexdigest()
INCLUSION_SHA = SCRIPT.EXPECTED_INCLUSION_RULE_SHA256


def _source(
    label: str,
    available_at: datetime,
    *,
    content_sha256: str | None = None,
) -> SourceIdentity:
    return SourceIdentity(
        f"https://example.test/{label}",
        content_sha256 or hashlib.sha256(label.encode()).hexdigest(),
        available_at,
        available_at + timedelta(minutes=1),
        label,
    )


def _business_days(start: date, end: date) -> tuple[date, ...]:
    days: list[date] = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return tuple(days)


def _calendar(days: tuple[date, ...]) -> AcceptedSessionCalendar:
    sessions = tuple(
        AcceptedSession(
            day,
            datetime.combine(day, time(9, 30), NY),
            datetime.combine(day, time(16), NY),
            _source(f"calendar-{index}", datetime(2000, 1, 1, tzinfo=UTC)),
            "America/New_York",
            exchange_id="XNYS",
        )
        for index, day in enumerate(days)
    )
    identity = CalendarIdentity(
        "XNYS",
        "America/New_York",
        days[0],
        days[-1],
        len(days),
        session_dates_sha256(days),
        session_rows_sha256(sessions),
        _source(
            "calendar-identity",
            datetime(2000, 1, 1, tzinfo=UTC),
            content_sha256=SCRIPT.VALIDATION_CALENDAR_PROJECTION_SHA256,
        ),
    )
    return AcceptedSessionCalendar(sessions, identity=identity)


def _calendar_revision(
    calendar: AcceptedSessionCalendar,
    *,
    available_at: datetime,
    revision_id: str,
) -> AcceptedSessionCalendar:
    sessions = tuple(
        calendar.session_on(day, as_of=datetime(2030, 1, 1, tzinfo=UTC))
        for day in calendar.session_dates
    )
    source = SourceIdentity(
        f"https://example.test/{revision_id}",
        hashlib.sha256(revision_id.encode()).hexdigest(),
        available_at,
        available_at + timedelta(minutes=1),
        revision_id,
        calendar.identity.source_identity.revision_id,
    )
    return AcceptedSessionCalendar(
        sessions,
        identity=dataclasses.replace(calendar.identity, source_identity=source),
    )


def _close(calendar: AcceptedSessionCalendar, day: date, index: int) -> MODULE.CloseObservation:
    calendar.session_on(day, as_of=datetime(2030, 1, 1, tzinfo=UTC))
    return MODULE.CloseObservation(
        day,
        100.0 + index * 0.3 + (index % 4) * 0.11,
        _source(f"close-{day}", datetime.combine(day, time(20), NY)),
    )


def _signal_fixture() -> tuple[
    AcceptedSessionCalendar,
    tuple[MODULE.CloseObservation, ...],
    datetime,
    date,
]:
    calendar = _calendar(_business_days(date(2023, 12, 1), date(2024, 3, 8)))
    final = date(2024, 1, 31)
    position = calendar.session_dates.index(final)
    dates = calendar.session_dates[position - 21 : position + 1]
    closes = tuple(_close(calendar, day, index) for index, day in enumerate(dates))
    decision_at = datetime(2024, 1, 31, 20, 5, tzinfo=NY)
    return calendar, closes, decision_at, date(2024, 2, 1)


def _cash_action(
    day: date,
    action_id: str,
    *,
    amount: str = "1.25",
) -> CorporateActionIdentity:
    effective_at = datetime.combine(day, time(9, 30), NY)
    return CorporateActionIdentity(
        "SPY",
        action_id,
        "cash_dividend",
        effective_at,
        _source(f"action-{action_id}", effective_at - timedelta(days=1)),
        "America/New_York",
        ex_date=day,
        record_date=day + timedelta(days=1),
        pay_date=day + timedelta(days=7),
        cash_amount=Decimal(amount),
        currency="USD",
        unit="per_share",
    )


def _statuses() -> tuple[StatusEvidence, ...]:
    values = {"listed": True, "delisted": False}
    return tuple(
        StatusEvidence(
            f"SPY-{kind}",
            "SPY",
            kind,
            value,
            date(1990, 1, 1),
            None,
            "America/New_York",
            _source(f"status-{kind}", datetime(2000, 1, 1, tzinfo=UTC)),
        )
        for kind, value in values.items()
    )


def _execution_input(
    calendar: AcceptedSessionCalendar,
    signal_day: date,
    execution_day: date,
    *,
    open_price: float,
    decision_price: float,
) -> ExecutionInput:
    execution = calendar.session_on(execution_day, as_of=datetime(2030, 1, 1, tzinfo=UTC))
    calendar.session_on(signal_day, as_of=datetime(2030, 1, 1, tzinfo=UTC))
    return ExecutionInput(
        "SPY",
        "us",
        open_price,
        "USD",
        _source(f"open-{execution_day}", datetime.combine(execution_day, time(20), NY)),
        _statuses(),
        decision_price=decision_price,
        decision_price_source=_source(f"close-{signal_day}", datetime.combine(signal_day, time(20), NY)),
        decision_price_basis="raw_execution_units",
        execution_price_effective_at=execution.open_at,
        execution_price_basis="retrospective_daily_bar_open_fill",
    )


def _snapshot(
    calendar: AcceptedSessionCalendar,
    execution_day: date,
    decision_at: datetime,
    row: ExecutionInput,
) -> UniverseSnapshotIdentity:
    execution = calendar.session_on(execution_day, as_of=decision_at)
    members = ("SPY",)
    return UniverseSnapshotIdentity(
        "us",
        "XNYS",
        execution_day,
        1,
        ordered_members_sha256(members),
        lifecycle_coverage_sha256(
            members,
            execution,
            decision_at,
            {"SPY": row.status_records},
            market="us",
        ),
        INCLUSION_SHA,
        calendar_identity_sha256(calendar.identity),
        _source("snapshot", datetime(2000, 1, 1, tzinfo=UTC)),
    )


def _projection_bytes(days: tuple[date, ...]) -> bytes:
    selected = tuple(day for day in days if day.day >= 8)[:34]
    assert len(selected) == 34
    rows = []
    for index, day in enumerate(selected):
        rows.append(
            {
                "available_at_basis": SCRIPT.OFFICIAL_ACTION_AVAILABLE_AT_BASIS,
                "distribution": f"{1 + index / 100:.6f}",
                "event_type": "CASH_DISTRIBUTION",
                "ex_date": day.isoformat(),
                "payment_date": (day + timedelta(days=8)).isoformat(),
                "record_date": (day + timedelta(days=1)).isoformat(),
                "source_document_sha256": hashlib.sha256(b"official-doc").hexdigest(),
                "source_url": "https://example.test/official.xlsx",
                "symbol": "SPY",
            }
        )
    return ("\n".join(json.dumps(row, separators=(",", ":")) for row in rows) + "\n").encode()


def _navs(returns: tuple[float, ...]) -> tuple[float, ...]:
    values = [100.0]
    for value in returns:
        values.append(values[-1] * (1.0 + value))
    return tuple(values)


def _authorization(
    calendar: AcceptedSessionCalendar,
    points: tuple[SCRIPT.ExecutionPoint, ...] = (),
    projection_bytes: bytes = b"",
) -> SCRIPT.RuntimeAuthorization:
    return SCRIPT.RuntimeAuthorization(
        preregistration_status="PREREGISTERED_NOT_EXECUTED",
        preregistration_json_sha256=hashlib.sha256(REPORT_PATH.read_bytes()).hexdigest(),
        strategy_adapter_sha256=hashlib.sha256(ADAPTER_PATH.read_bytes()).hexdigest(),
        causal_core_reviewed_head=SCRIPT.PR117_REVIEWED_HEAD,
        causal_core_merged_main_head=SCRIPT.PR117_MERGED_MAIN_HEAD,
        status_core_reviewed_head=SCRIPT.STATUS_CORE_REVIEWED_HEAD,
        execution_core_reviewed_head=SCRIPT.EXECUTION_CORE_REVIEWED_HEAD,
        strategy_runner_sha256=hashlib.sha256(SCRIPT_PATH.read_bytes()).hexdigest(),
        reconstruction_calendar_identity_sha256=calendar_identity_sha256(calendar.identity),
        calendar_epoch_mapping_sha256=(
            SCRIPT.calendar_epoch_mapping_sha256(points) if points else "0" * 64
        ),
        qualified_market_rows_sha256=SCRIPT.QUALIFIED_MARKET_ROWS_SHA256,
        input_bundle_sha256=SCRIPT.runtime_input_bundle_sha256(calendar, points, projection_bytes)
        if points
        else "0" * 64,
    )


def _point(
    calendar: AcceptedSessionCalendar,
    signal_day: date,
    execution_day: date,
    *,
    open_price: float,
    decision_price: float,
    official_actions: tuple[CorporateActionIdentity, ...],
) -> SCRIPT.ExecutionPoint:
    decision_at = datetime.combine(signal_day, time(20, 5), NY)
    position = calendar.session_dates.index(signal_day)
    close_days = calendar.session_dates[position - 21 : position + 1]
    base_closes = tuple(_close(calendar, day, index) for index, day in enumerate(close_days))
    scale = decision_price / base_closes[-1].raw_close
    closes = tuple(
        dataclasses.replace(close, raw_close=close.raw_close * scale)
        for close in base_closes
    )
    row = _execution_input(
        calendar,
        signal_day,
        execution_day,
        open_price=open_price,
        decision_price=decision_price,
    )
    relevant = tuple(
        action for action in official_actions if action.effective_date in set(close_days[1:])
    )
    return SCRIPT.ExecutionPoint(
        closes,
        relevant,
        calendar,
        decision_at,
        execution_day,
        row,
        _snapshot(calendar, execution_day, decision_at, row),
    )


def test_preregistration_freezes_complete_terminal_contract_without_outcome() -> None:
    record = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    frozen = record["outcome_blind_frozen_specification"]

    assert record["status"] == "PREREGISTERED_NOT_EXECUTED"
    assert record["strategy_candidate_available"] is False
    assert record["adjudication"]["outcome_accessed"] is False
    assert record["repository_identity"]["causal_core_reviewed_head"] == (
        SCRIPT.PR117_REVIEWED_HEAD
    )
    assert record["repository_identity"]["causal_core_merged_main_head"] == (
        SCRIPT.PR117_MERGED_MAIN_HEAD
    )
    assert frozen["expected_inclusion_rule"] == "fixed-spy-universe"
    assert frozen["expected_inclusion_rule_sha256"] == INCLUSION_SHA
    assert INCLUSION_SHA == hashlib.sha256(b"fixed-spy-universe").hexdigest()
    assert frozen["calendar_and_signal"]["required_raw_closes"] == 22
    assert frozen["splits"]["validation_entry_cohorts"]["required_count"] == 45
    assert frozen["splits"]["retrospective_holdout_entry_cohorts"]["required_count"] == 53
    execution_gate = frozen["real_execution_gate"]
    assert execution_gate["validation_calendar_exact_session_count"] == 987
    assert execution_gate["validation_official_action_exact_count"] == 15
    assert execution_gate["validation_bundle_file_sha256"] == SCRIPT.VALIDATION_BUNDLE_FILE_SHA256
    assert execution_gate["validation_runtime_input_bundle_sha256"] == (
        SCRIPT.VALIDATION_RUNTIME_INPUT_BUNDLE_SHA256
    )
    assert execution_gate["validation_calendar_mapping_semantic_sha256"] == (
        SCRIPT.VALIDATION_CALENDAR_MAPPING_SHA256
    )
    assert execution_gate["holdout_calendar_projection_sha256"] is None
    assert execution_gate["holdout_runtime_input_bundle_sha256"] is None
    actions = frozen["corporate_actions"]
    assert actions["official_projection_sha256"] == SCRIPT.OFFICIAL_ACTION_PROJECTION_SHA256
    assert actions["required_event_count"] == 34
    assert actions["distribution_ex_date_first_session_execution_overlap_count"] == 0
    assert frozen["holdout_primary_inference"]["resamples"] == 10_000
    assert frozen["holdout_primary_inference"]["seed"] == 4601
    terminal = frozen["terminal_rules"]
    assert terminal["completed_validation_gate_failure"].startswith("HISTORICAL_VALIDATION_FAIL")
    assert terminal["completed_holdout_failure"] == "HISTORICAL_HOLDOUT_FAIL"
    assert terminal["validation_and_holdout_pass"] == ("HISTORICAL_PASS_PENDING_EXTERNAL_REVIEW")
    serialized = REPORT_PATH.read_text(encoding="utf-8")
    assert "shared P0" not in serialized
    assert '"strategy_result": null' in serialized


def test_signal_requires_exact_consecutive_month_end_window_and_next_session() -> None:
    calendar, closes, decision_at, execution = _signal_fixture()
    feature = MODULE.build_signal_feature(
        calendar,
        closes,
        decision_at=decision_at,
        execution_session=execution,
    )
    assert len(feature.log_total_returns) == 21
    assert feature.execution_session == execution

    prior = calendar.session_dates[calendar.session_dates.index(closes[0].session_date) - 1]
    omitted = (_close(calendar, prior, 99),) + closes[1:]
    with pytest.raises(MODULE.InputContractError, match="consecutive"):
        MODULE.build_signal_feature(
            calendar,
            omitted,
            decision_at=decision_at,
            execution_session=execution,
        )

    weekend = MODULE.CloseObservation(
        date(2024, 1, 6),
        100.0,
        _source("weekend", datetime(2024, 1, 6, 21, tzinfo=UTC)),
    )
    with pytest.raises(MODULE.InputContractError, match="consecutive"):
        MODULE.build_signal_feature(
            calendar,
            closes[:5] + (weekend,) + closes[6:],
            decision_at=decision_at,
            execution_session=execution,
        )

    penultimate_dates = calendar.session_dates[
        calendar.session_dates.index(date(2024, 1, 30)) - 21 : calendar.session_dates.index(
            date(2024, 1, 30)
        )
        + 1
    ]
    penultimate = tuple(_close(calendar, day, index) for index, day in enumerate(penultimate_dates))
    with pytest.raises(MODULE.InputContractError, match="final accepted"):
        MODULE.build_signal_feature(
            calendar,
            penultimate,
            decision_at=datetime(2024, 1, 30, 20, 5, tzinfo=NY),
            execution_session=date(2024, 1, 31),
        )

    with pytest.raises(MODULE.InputContractError, match="immediately following"):
        MODULE.build_signal_feature(
            calendar,
            closes,
            decision_at=decision_at,
            execution_session=date(2024, 2, 2),
        )


def test_signal_requires_exact_same_session_twenty_hundred_close_availability() -> None:
    calendar, closes, decision_at, execution = _signal_fixture()
    first = closes[0]
    for available_at in (
        datetime.combine(first.session_date, time(19, 59), NY),
        datetime.combine(first.session_date, time(20, 1), NY),
        datetime.combine(first.session_date + timedelta(days=1), time(20), NY),
    ):
        bad_source = SourceIdentity(
            first.source.source_url,
            first.source.content_sha256,
            available_at,
            available_at + timedelta(minutes=1),
            first.source.revision_id,
        )
        bad_closes = (dataclasses.replace(first, source=bad_source),) + closes[1:]
        with pytest.raises(MODULE.InputContractError, match="same-session 20:00"):
            MODULE.build_signal_feature(
                calendar,
                bad_closes,
                decision_at=decision_at,
                execution_session=execution,
            )


def test_zoneinfo_open_is_dst_correct() -> None:
    winter = _calendar((date(2024, 1, 2),)).session_on(
        date(2024, 1, 2),
        as_of=datetime(2030, 1, 1, tzinfo=UTC),
    )
    summer = _calendar((date(2024, 7, 1),)).session_on(
        date(2024, 7, 1),
        as_of=datetime(2030, 1, 1, tzinfo=UTC),
    )
    assert winter.open_at.astimezone(UTC).time() == time(14, 30)
    assert summer.open_at.astimezone(UTC).time() == time(13, 30)
    assert datetime.combine(date(2024, 1, 2), time(20), NY).astimezone(UTC).time() == time(1)
    assert datetime.combine(date(2024, 7, 1), time(20), NY).astimezone(UTC).time() == time(0)


def test_signal_action_ids_are_exact_and_official_amount_controls() -> None:
    calendar, closes, decision_at, execution = _signal_fixture()
    action_index = 10
    action = _cash_action(closes[action_index].session_date, "window-action", amount="1.636431")
    feature = MODULE.build_signal_feature(
        calendar,
        closes,
        actions=(action,),
        expected_action_ids=(action.action_id,),
        decision_at=decision_at,
        execution_session=execution,
    )
    expected = math.log(
        (closes[action_index].raw_close + 1.636431) / closes[action_index - 1].raw_close
    )
    assert feature.log_total_returns[action_index - 1] == pytest.approx(expected)

    with pytest.raises(MODULE.InputContractError, match="exactly match"):
        MODULE.build_signal_feature(
            calendar,
            closes,
            actions=(),
            expected_action_ids=(action.action_id,),
            decision_at=decision_at,
            execution_session=execution,
        )
    with pytest.raises(MODULE.InputContractError, match="exactly match"):
        MODULE.build_signal_feature(
            calendar,
            closes,
            actions=(action,),
            expected_action_ids=(action.action_id, "extra"),
            decision_at=decision_at,
            execution_session=execution,
        )
    outside = _cash_action(date(2023, 12, 29), "outside")
    with pytest.raises(MODULE.InputContractError, match="window-outside"):
        MODULE.build_signal_feature(
            calendar,
            closes,
            actions=(outside,),
            expected_action_ids=(outside.action_id,),
            decision_at=decision_at,
            execution_session=execution,
        )


def test_retrospective_action_basis_preserves_actual_retrieval_time() -> None:
    calendar, closes, decision_at, execution = _signal_fixture()
    action = _cash_action(closes[10].session_date, "retrospective-action")
    retrieved_at = datetime(2026, 7, 21, 8, 13, 17, tzinfo=UTC)
    source = SourceIdentity(
        action.source.source_url,
        action.source.content_sha256,
        retrieved_at,
        retrieved_at,
        action.source.revision_id,
    )
    action = dataclasses.replace(action, source=source)
    feature = MODULE.build_signal_feature(
        calendar,
        closes,
        actions=(action,),
        expected_action_ids=(action.action_id,),
        action_evidence_basis=MODULE.RETROSPECTIVE_ACTION_BASIS,
        decision_at=decision_at,
        execution_session=execution,
    )
    assert len(feature.log_total_returns) == 21

    with pytest.raises(MODULE.InputContractError, match="not available by ex-date open"):
        MODULE.build_signal_feature(
            calendar,
            closes,
            actions=(action,),
            expected_action_ids=(action.action_id,),
            decision_at=decision_at,
            execution_session=execution,
        )
    with pytest.raises(MODULE.InputContractError, match="unsupported"):
        MODULE.build_signal_feature(
            calendar,
            closes,
            actions=(action,),
            expected_action_ids=(action.action_id,),
            action_evidence_basis=None,  # type: ignore[arg-type]
            decision_at=decision_at,
            execution_session=execution,
        )
    backdated_source = SourceIdentity(
        action.source.source_url,
        action.source.content_sha256,
        action.effective_at,
        action.effective_at,
        action.source.revision_id,
    )
    with pytest.raises(MODULE.InputContractError, match="actual post-event"):
        MODULE.build_signal_feature(
            calendar,
            closes,
            actions=(dataclasses.replace(action, source=backdated_source),),
            expected_action_ids=(action.action_id,),
            action_evidence_basis=MODULE.RETROSPECTIVE_ACTION_BASIS,
            decision_at=decision_at,
            execution_session=execution,
        )
    mismatched_retrieval = SourceIdentity(
        action.source.source_url,
        action.source.content_sha256,
        retrieved_at,
        retrieved_at + timedelta(minutes=1),
        action.source.revision_id,
    )
    with pytest.raises(MODULE.InputContractError, match="actual post-event"):
        MODULE.build_signal_feature(
            calendar,
            closes,
            actions=(dataclasses.replace(action, source=mismatched_retrieval),),
            expected_action_ids=(action.action_id,),
            action_evidence_basis=MODULE.RETROSPECTIVE_ACTION_BASIS,
            decision_at=decision_at,
            execution_session=execution,
        )


def test_monthly_metric_formulas_drawdown_and_zero_variance() -> None:
    returns = (0.01, 0.02, 0.03)
    navs = (100.0, 101.0, 103.02, 106.1106)
    metrics = MODULE.performance_metrics(returns, navs)
    assert metrics.monthly_arithmetic_mean == pytest.approx(0.02)
    assert metrics.monthly_sample_stdev == pytest.approx(0.01)
    assert metrics.sharpe == pytest.approx(6.928203230275509)
    assert metrics.annualized_volatility == pytest.approx(0.034641016151377546)
    assert metrics.compounded_net_return == pytest.approx(0.061106000000000105)

    drawdown = MODULE.performance_metrics((0.1, -0.1), (100.0, 110.0, 99.0))
    assert drawdown.maximum_drawdown == pytest.approx(-0.1)
    with pytest.raises(MODULE.InputContractError, match="standard deviation"):
        MODULE.performance_metrics((0.01, 0.01), (100.0, 101.0, 102.01))
    with pytest.raises(MODULE.InputContractError, match="no cohort"):
        MODULE.cohort_returns((100.0, 101.0), expected_cohorts=2)


def test_bootstrap_literal_golden_vector_and_lower_bound_are_deterministic() -> None:
    paths = MODULE.stationary_bootstrap_indices(8)
    assert paths[:5] == (
        (1, 2, 3, 4, 5, 6, 6, 7),
        (2, 4, 5, 6, 7, 3, 4, 5),
        (7, 0, 1, 2, 3, 4, 5, 0),
        (7, 5, 6, 7, 0, 5, 6, 3),
        (2, 3, 4, 5, 4, 5, 6, 4),
    )
    assert MODULE.stationary_bootstrap_indices(8)[:5] == paths[:5]

    strategy = tuple(0.010 + 0.001 * ((index % 7) - 3) for index in range(53))
    benchmark = tuple(0.006 + 0.004 * ((index % 11) - 5) for index in range(53))
    first = MODULE.paired_bootstrap_lower_bound(strategy, benchmark)
    second = MODULE.paired_bootstrap_lower_bound(strategy, benchmark)
    assert first == pytest.approx(14.248971607495543, rel=0.0, abs=1e-12)
    assert second == first

    invalid = list(0.01 for _ in range(53))
    invalid[1] = 0.02
    with pytest.raises(MODULE.InputContractError, match="invalid bootstrap replicate"):
        MODULE.paired_bootstrap_lower_bound(tuple(invalid), benchmark)


def test_holdout_lock_and_terminal_exception_mapping() -> None:
    metric = MODULE.PerformanceMetrics(0.01, 0.02, 1.0, 0.05, 0.2, -0.1)
    failed = MODULE.ValidationDecision(
        45,
        metric,
        metric,
        0.0,
        (("gate", False),),
    )
    with pytest.raises(MODULE.InputContractError, match="locked"):
        MODULE.holdout_gate_decision(failed, (), (), (), ())
    with pytest.raises(SCRIPT.InputBlockedError, match="immutable validation receipt"):
        SCRIPT.require_holdout_unlocked(failed)

    assert SCRIPT.classify_terminal(stage="validation", complete=False, passed=False).status == (
        "INPUT_BLOCKED"
    )
    assert SCRIPT.classify_terminal(stage="validation", complete=True, passed=False).status == (
        "HISTORICAL_VALIDATION_FAIL"
    )
    assert SCRIPT.classify_terminal(stage="holdout", complete=True, passed=False).status == (
        "HISTORICAL_HOLDOUT_FAIL"
    )
    passed = SCRIPT.classify_terminal(stage="holdout", complete=True, passed=True)
    assert passed.status == "HISTORICAL_PASS_PENDING_EXTERNAL_REVIEW"
    assert passed.strategy_candidate_available is False


def test_holdout_unlock_recomputes_validation_navs_and_digest(monkeypatch) -> None:
    strategy_returns = tuple(0.01 + 0.001 * ((index % 5) - 2) for index in range(45))
    benchmark_returns = tuple(0.04 if index % 2 == 0 else -0.05 for index in range(45))
    simulation = SCRIPT.CohortSimulation(
        _navs(strategy_returns),
        _navs(benchmark_returns),
        strategy_returns,
        benchmark_returns,
        (),
        (),
    )
    receipt = SCRIPT.validation_receipt(simulation)
    SCRIPT.require_holdout_unlocked(receipt)

    holdout_calls: list[object] = []
    with monkeypatch.context() as guard:
        guard.setattr(
            SCRIPT,
            "_simulate_cohorts",
            lambda *args, **kwargs: holdout_calls.append((args, kwargs)),
        )
        with pytest.raises(SCRIPT.InputBlockedError, match="holdout calendar identity"):
            SCRIPT.simulate_holdout(
                receipt,
                _calendar((date(2021, 12, 1), date(2026, 6, 1))),
                (),
                None,  # type: ignore[arg-type]
                daily_sessions=(),
                action_projection_bytes=b"",
                authorization=None,  # type: ignore[arg-type]
                query_start=date(2021, 12, 1),
                query_end=date(2026, 6, 1),
            )
    assert holdout_calls == []

    forged_digest = dataclasses.replace(receipt, result_sha256="0" * 64)
    with pytest.raises(SCRIPT.InputBlockedError, match="content identity"):
        SCRIPT.require_holdout_unlocked(forged_digest)
    forged_navs = dataclasses.replace(
        receipt,
        strategy_boundary_navs=receipt.strategy_boundary_navs[:-1] + (1.0,),
    )
    with pytest.raises(SCRIPT.InputBlockedError):
        SCRIPT.require_holdout_unlocked(forged_navs)


def test_full_action_projection_bytes_bind_every_runtime_field(monkeypatch) -> None:
    days = _business_days(date(2018, 1, 1), date(2018, 4, 30))
    calendar = _calendar(days)
    projection = _projection_bytes(days)
    monkeypatch.setattr(
        SCRIPT,
        "OFFICIAL_ACTION_PROJECTION_SHA256",
        hashlib.sha256(projection).hexdigest(),
    )
    actions = SCRIPT.official_actions_from_projection(projection, calendar)
    assert len(actions) == 34
    assert actions[0].cash_amount == Decimal("1.000000")
    assert actions[0].pay_date == actions[0].effective_date + timedelta(days=8)
    assert actions[0].source.content_sha256 == hashlib.sha256(b"official-doc").hexdigest()
    assert actions[0].source.available_at == SCRIPT.OFFICIAL_ACTION_RETRIEVED_AT
    assert actions[0].source.retrieved_at == SCRIPT.OFFICIAL_ACTION_RETRIEVED_AT
    SCRIPT.assert_zero_distribution_execution_overlap(actions, (date(2018, 5, 1),))
    limited_calendar = _calendar(
        tuple(day for day in days if day <= date(2018, 2, 28))
    )
    stage_actions = SCRIPT.official_actions_from_projection(projection, limited_calendar)
    assert 0 < len(stage_actions) < SCRIPT.OFFICIAL_ACTION_COUNT
    assert all(
        action.effective_date <= limited_calendar.identity.coverage_end
        for action in stage_actions
    )

    changed = projection.replace(b'"distribution":"1.000000"', b'"distribution":"999.99"')
    with pytest.raises(SCRIPT.InputBlockedError, match="full hash mismatch"):
        SCRIPT.official_actions_from_projection(changed, calendar)
    with pytest.raises(SCRIPT.InputBlockedError, match="overlap"):
        SCRIPT.assert_zero_distribution_execution_overlap(
            actions,
            (actions[0].effective_date,),
        )


def test_authorization_binds_every_current_code_and_core_identity(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calendar = _calendar(_business_days(date(2023, 12, 1), date(2024, 2, 2)))
    point = _point(
        calendar,
        date(2024, 1, 31),
        date(2024, 2, 1),
        open_price=120.0,
        decision_price=106.41,
        official_actions=(),
    )
    authorization = dataclasses.replace(
        _authorization(calendar),
        calendar_epoch_mapping_sha256=SCRIPT.calendar_epoch_mapping_sha256((point,)),
    )

    class OneReadDefinition:
        calls = 0

        def read_bytes(self) -> bytes:
            self.calls += 1
            if self.calls != 1:
                raise AssertionError("definition bytes were reopened")
            return REPORT_PATH.read_bytes()

    one_read = OneReadDefinition()
    monkeypatch.setattr(SCRIPT, "_REPORT_PATH", one_read)
    SCRIPT.validate_runtime_authorization(authorization, calendar, (point,))
    assert one_read.calls == 1
    monkeypatch.setattr(SCRIPT, "_REPORT_PATH", REPORT_PATH)
    forged = dataclasses.replace(authorization, preregistration_json_sha256="0" * 64)
    with pytest.raises(SCRIPT.InputBlockedError, match="current bytes"):
        SCRIPT.validate_runtime_authorization(forged, calendar, (point,))
    wrong_adapter = dataclasses.replace(authorization, strategy_adapter_sha256="a" * 64)
    with pytest.raises(SCRIPT.InputBlockedError, match="strategy adapter"):
        SCRIPT.validate_runtime_authorization(wrong_adapter, calendar, (point,))
    wrong_runner = dataclasses.replace(authorization, strategy_runner_sha256="b" * 64)
    with pytest.raises(SCRIPT.InputBlockedError, match="strategy runner"):
        SCRIPT.validate_runtime_authorization(wrong_runner, calendar, (point,))
    wrong_core = dataclasses.replace(authorization, causal_core_reviewed_head="c" * 40)
    with pytest.raises(SCRIPT.InputBlockedError, match="reviewed PR117"):
        SCRIPT.validate_runtime_authorization(wrong_core, calendar, (point,))
    wrong_merged_core = dataclasses.replace(
        authorization,
        causal_core_merged_main_head="d" * 40,
    )
    with pytest.raises(SCRIPT.InputBlockedError, match="merged PR117"):
        SCRIPT.validate_runtime_authorization(wrong_merged_core, calendar, (point,))
    wrong_status_core = dataclasses.replace(
        authorization,
        status_core_reviewed_head="e" * 40,
    )
    with pytest.raises(SCRIPT.InputBlockedError, match="status core"):
        SCRIPT.validate_runtime_authorization(wrong_status_core, calendar, (point,))
    wrong_execution_core = dataclasses.replace(
        authorization,
        execution_core_reviewed_head="f" * 40,
    )
    with pytest.raises(SCRIPT.InputBlockedError, match="execution core"):
        SCRIPT.validate_runtime_authorization(wrong_execution_core, calendar, (point,))
    wrong_calendar = dataclasses.replace(
        authorization,
        reconstruction_calendar_identity_sha256="1" * 64,
    )
    with pytest.raises(SCRIPT.InputBlockedError, match="reconstruction calendar"):
        SCRIPT.validate_runtime_authorization(wrong_calendar, calendar, (point,))
    wrong_mapping = dataclasses.replace(
        authorization,
        calendar_epoch_mapping_sha256="2" * 64,
    )
    with pytest.raises(SCRIPT.InputBlockedError, match="epoch mapping"):
        SCRIPT.validate_runtime_authorization(wrong_mapping, calendar, (point,))

    forged_definition = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    forged_definition["outcome_blind_frozen_specification"][
        "expected_inclusion_rule_sha256"
    ] = "3" * 64
    forged_path = tmp_path / "forged-definition.json"
    forged_path.write_text(json.dumps(forged_definition), encoding="utf-8")
    monkeypatch.setattr(SCRIPT, "_REPORT_PATH", forged_path)
    forged_authorization = dataclasses.replace(
        authorization,
        preregistration_json_sha256=hashlib.sha256(forged_path.read_bytes()).hexdigest(),
    )
    with pytest.raises(SCRIPT.InputBlockedError, match="definition inclusion rule"):
        SCRIPT.validate_runtime_authorization(forged_authorization, calendar, (point,))

    forged_definition["outcome_blind_frozen_specification"][
        "expected_inclusion_rule_sha256"
    ] = SCRIPT.EXPECTED_INCLUSION_RULE_SHA256
    forged_definition["status"] = "HISTORICAL_VALIDATION_FAIL"
    forged_path.write_text(json.dumps(forged_definition), encoding="utf-8")
    forged_status_authorization = dataclasses.replace(
        authorization,
        preregistration_json_sha256=hashlib.sha256(forged_path.read_bytes()).hexdigest(),
    )
    with pytest.raises(SCRIPT.InputBlockedError, match="current JSON status"):
        SCRIPT.validate_runtime_authorization(
            forged_status_authorization,
            calendar,
            (point,),
        )


def test_shared_core_partial_cash_preserves_requested_shares_and_residual_cash() -> None:
    days = (date(2024, 1, 31), date(2024, 2, 1), date(2024, 2, 2))
    calendar = _calendar(days)
    signal_day, execution_day = days[:2]
    decision_at = datetime.combine(signal_day, time(20, 5), NY)
    row = _execution_input(
        calendar,
        signal_day,
        execution_day,
        open_price=11.0,
        decision_price=10.0,
    )
    result = run_static_rebalance(
        Portfolio.us(100.0),
        calendar,
        signal_session=signal_day,
        decision_at=decision_at,
        execution_inputs=(row,),
        universe_members=("SPY",),
        universe_snapshot=_snapshot(calendar, execution_day, decision_at, row),
        target_weights=lambda _: {"SPY": 1.0},
        strategy_definition_sha256=DEFINITION_SHA,
        strategy_adapter_sha256=ADAPTER_SHA,
        slippage_bps=10.0,
    )
    receipt = result.receipts[0]
    assert receipt.requested_shares == 10
    assert receipt.filled_shares == 9
    assert receipt.price == pytest.approx(11.011)
    assert receipt.reason == "partial_cash"
    assert result.portfolio.available_cash == pytest.approx(0.9010000000000105)


def test_spy_rebalance_rejects_non_eod_open_and_decision_price_drift(monkeypatch) -> None:
    days = _business_days(date(2023, 12, 1), date(2024, 2, 2))
    calendar = _calendar(days)
    point = _point(
        calendar,
        date(2024, 1, 31),
        date(2024, 2, 1),
        open_price=120.0,
        decision_price=106.41,
        official_actions=(),
    )
    signal = SCRIPT._point_signal(point, ())
    authorization = _authorization(calendar)
    baseline = SCRIPT._rebalance(
        Portfolio.us(40_000.0),
        point,
        authorization,
        signal.signal_session,
        signal.target_weight,
        "0" * 64,
    )
    assert baseline.receipts

    calls: list[object] = []

    def forbidden_rebalance(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("shared callback path must not run")

    monkeypatch.setattr(SCRIPT, "run_static_rebalance", forbidden_rebalance)

    execution = point.calendar.session_on(
        point.execution_session,
        as_of=point.decision_at,
    )
    backdated_source = _source("backdated-open", execution.open_at)
    bad_rows = (
        dataclasses.replace(
            point.execution_input,
            source=backdated_source,
        ),
        dataclasses.replace(
            point.execution_input,
            source=_source(
                "early-eod-open",
                datetime.combine(point.execution_session, time(19, 59), NY),
            ),
        ),
        dataclasses.replace(
            point.execution_input,
            source=_source(
                "late-eod-open",
                datetime.combine(point.execution_session, time(20, 1), NY),
            ),
        ),
        dataclasses.replace(
            point.execution_input,
            source=_source(
                "wrong-day-eod-open",
                datetime.combine(
                    point.execution_session + timedelta(days=1),
                    time(20),
                    NY,
                ),
            ),
        ),
        dataclasses.replace(
            point.execution_input,
            execution_price_basis="timestamped_session_open",
        ),
        dataclasses.replace(
            point.execution_input,
            execution_price_effective_at=execution.open_at + timedelta(microseconds=1),
        ),
        dataclasses.replace(
            point.execution_input,
            decision_price=point.execution_input.decision_price + 1.0,
        ),
        dataclasses.replace(
            point.execution_input,
            decision_price_source=_source(
                "wrong-close-source",
                datetime.combine(date(2024, 1, 31), time(20), NY),
            ),
        ),
    )
    expected_messages = (
        "same-session 20:00",
        "same-session 20:00",
        "same-session 20:00",
        "same-session 20:00",
        "retrospective daily-bar basis",
        "accepted-session open",
        "final causal raw close",
        "final causal raw close",
    )
    for row, message in zip(bad_rows, expected_messages, strict=True):
        bad_point = dataclasses.replace(point, execution_input=row)
        portfolio = Portfolio.us(40_000.0)
        before = dict(portfolio.__dict__)
        with pytest.raises(SCRIPT.InputBlockedError, match=message):
            SCRIPT._rebalance(
                portfolio,
                bad_point,
                authorization,
                signal.signal_session,
                signal.target_weight,
                "0" * 64,
            )
        assert calls == []
        assert portfolio.__dict__ == before


def test_execution_observation_fields_change_runtime_bundle_identity(monkeypatch) -> None:
    days = _business_days(date(2018, 1, 1), date(2018, 4, 30))
    calendar = _calendar(days)
    projection = _projection_bytes(days)
    monkeypatch.setattr(
        SCRIPT,
        "OFFICIAL_ACTION_PROJECTION_SHA256",
        hashlib.sha256(projection).hexdigest(),
    )
    official_actions = SCRIPT.official_actions_from_projection(projection, calendar)
    point = _point(
        calendar,
        date(2018, 3, 30),
        date(2018, 4, 2),
        open_price=120.0,
        decision_price=106.41,
        official_actions=official_actions,
    )
    baseline_rows = SCRIPT.runtime_market_rows_sha256((point,))
    baseline_bundle = SCRIPT.runtime_input_bundle_sha256(calendar, (point,), projection)
    changed_rows = (
        dataclasses.replace(
            point.execution_input,
            execution_price_basis="timestamped_session_open",
        ),
        dataclasses.replace(
            point.execution_input,
            execution_price_effective_at=(
                point.execution_input.execution_price_effective_at
                + timedelta(microseconds=1)
            ),
        ),
        dataclasses.replace(
            point.execution_input,
            source=_source(
                "changed-open-source",
                datetime.combine(point.execution_session, time(20), NY),
            ),
        ),
    )
    for row in changed_rows:
        changed = dataclasses.replace(point, execution_input=row)
        assert SCRIPT.runtime_market_rows_sha256((changed,)) != baseline_rows
        assert (
            SCRIPT.runtime_input_bundle_sha256(calendar, (changed,), projection)
            != baseline_bundle
        )


def test_execution_calendar_revision_is_stage_bound_and_passed_to_shared_core() -> None:
    days = _business_days(date(2023, 12, 1), date(2024, 2, 6))
    calendar = _calendar(days)
    point = _point(
        calendar,
        date(2024, 1, 31),
        date(2024, 2, 1),
        open_price=120.0,
        decision_price=106.41,
        official_actions=(),
    )
    execution = calendar.session_on(point.execution_session, as_of=point.decision_at)
    revision = _calendar_revision(
        calendar,
        available_at=execution.open_at,
        revision_id="post-decision-settlement-revision",
    )
    revised = dataclasses.replace(point, execution_calendar_revision=revision)
    assert SCRIPT.calendar_epoch_mapping_sha256((revised,)) != (
        SCRIPT.calendar_epoch_mapping_sha256((point,))
    )

    authorization = _authorization(calendar)
    signal = SCRIPT._point_signal(point, ())
    baseline = SCRIPT._rebalance(
        Portfolio.us(40_000.0),
        point,
        authorization,
        signal.signal_session,
        None,
        "0" * 64,
    )
    changed = SCRIPT._rebalance(
        Portfolio.us(40_000.0),
        revised,
        authorization,
        signal.signal_session,
        None,
        "0" * 64,
    )
    assert baseline.receipts == changed.receipts == ()
    assert baseline.input_identity_hash != changed.input_identity_hash
    assert baseline.stage_hash != changed.stage_hash


def test_cohort_simulation_resets_state_and_records_exact_boundaries(monkeypatch) -> None:
    days = _business_days(date(2023, 12, 1), date(2024, 4, 3))
    calendar = _calendar(days)
    projection = _projection_bytes(days)
    monkeypatch.setattr(
        SCRIPT,
        "OFFICIAL_ACTION_PROJECTION_SHA256",
        hashlib.sha256(projection).hexdigest(),
    )
    official_actions = SCRIPT.official_actions_from_projection(projection, calendar)
    first = _point(
        calendar,
        date(2024, 1, 31),
        date(2024, 2, 1),
        open_price=120.0,
        decision_price=106.41,
        official_actions=official_actions,
    )
    second = _point(
        calendar,
        date(2024, 2, 29),
        date(2024, 3, 1),
        open_price=121.0,
        decision_price=106.41,
        official_actions=official_actions,
    )
    final = _point(
        calendar,
        date(2024, 3, 29),
        date(2024, 4, 1),
        open_price=122.0,
        decision_price=106.41,
        official_actions=official_actions,
    )
    daily = tuple(day for day in days if date(2024, 2, 1) <= day <= date(2024, 4, 1))
    bundle_sha = SCRIPT.runtime_input_bundle_sha256(
        calendar,
        (first, second, final),
        projection,
    )
    authorization = _authorization(calendar, (first, second, final), projection)
    stage_contract = {
        "expected_months": ((2024, 2), (2024, 3)),
        "expected_calendar_bounds": (
            calendar.identity.coverage_start,
            calendar.identity.coverage_end,
        ),
        "expected_calendar_session_count": calendar.identity.session_count,
        "expected_official_action_count": len(official_actions),
        "expected_calendar_projection_sha256": (
            calendar.identity.source_identity.content_sha256
        ),
    }
    with pytest.raises(SCRIPT.InputBlockedError, match="official action count"):
        SCRIPT._simulate_cohorts(
            calendar,
            (first, second),
            final,
            daily_sessions=daily,
            action_projection_bytes=projection,
            authorization=authorization,
            expected_input_bundle_sha256=None,
            **{
                **stage_contract,
                "expected_official_action_count": len(official_actions) + 1,
            },
        )
    signal_calls: list[object] = []
    rebalance_calls: list[object] = []
    with monkeypatch.context() as guard:
        guard.setattr(
            SCRIPT,
            "_point_signal",
            lambda *args, **kwargs: signal_calls.append((args, kwargs)),
        )
        guard.setattr(
            SCRIPT,
            "run_static_rebalance",
            lambda *args, **kwargs: rebalance_calls.append((args, kwargs)),
        )
        with pytest.raises(SCRIPT.InputBlockedError, match="has not been frozen"):
            SCRIPT._simulate_cohorts(
                calendar,
                (first, second),
                final,
                daily_sessions=daily,
                action_projection_bytes=projection,
                authorization=authorization,
                expected_input_bundle_sha256=None,
                **stage_contract,
            )
    assert signal_calls == []
    assert rebalance_calls == []

    first_run = SCRIPT._simulate_cohorts(
        calendar,
        (first, second),
        final,
        daily_sessions=daily,
        action_projection_bytes=projection,
        authorization=authorization,
        expected_input_bundle_sha256=bundle_sha,
        **stage_contract,
    )
    second_run = SCRIPT._simulate_cohorts(
        calendar,
        (first, second),
        final,
        daily_sessions=daily,
        action_projection_bytes=projection,
        authorization=authorization,
        expected_input_bundle_sha256=bundle_sha,
        **stage_contract,
    )
    assert first_run == second_run
    assert first_run.strategy_boundary_navs[0] == 40_000.0
    assert first_run.benchmark_boundary_navs[0] == 40_000.0
    assert len(first_run.strategy_boundary_navs) == 3
    assert len(first_run.strategy_returns) == 2
    assert first_run.strategy_receipts[0].reason == "partial_cash"
    assert first_run.benchmark_receipts[0].reason == "partial_cash"
    assert first_run.strategy_receipts[-1].side == "sell"
    assert first_run.benchmark_receipts[-1].side == "sell"

    assert "signal" not in {field.name for field in dataclasses.fields(SCRIPT.ExecutionPoint)}
    rebuilt = SCRIPT._point_signal(first, official_actions)
    assert rebuilt.target_weight == MODULE.target_weight(rebuilt.annualized_volatility)
    wrong_inclusion = dataclasses.replace(
        first,
        universe_snapshot=dataclasses.replace(
            first.universe_snapshot,
            inclusion_rule_sha256="0" * 64,
        ),
    )
    with pytest.raises(SCRIPT.InputBlockedError, match="inclusion rule"):
        SCRIPT._point_signal(wrong_inclusion, official_actions)

    wrong_basis = dataclasses.replace(
        first,
        execution_input=dataclasses.replace(
            first.execution_input,
            decision_price_basis="raw_pre_action_per_old_share",
        ),
    )
    assert SCRIPT.runtime_market_rows_sha256((wrong_basis,)) != (
        SCRIPT.runtime_market_rows_sha256((first,))
    )
    with pytest.raises(SCRIPT.InputBlockedError, match="raw_execution_units"):
        SCRIPT._rebalance(
            Portfolio.us(40_000.0),
            wrong_basis,
            authorization,
            rebuilt.signal_session,
            rebuilt.target_weight,
            "0" * 64,
        )
    missing_basis = dataclasses.replace(
        first,
        execution_input=dataclasses.replace(
            first.execution_input,
            decision_price_basis=None,
        ),
    )
    with pytest.raises(SCRIPT.InputBlockedError, match="raw_execution_units"):
        SCRIPT._rebalance(
            Portfolio.us(40_000.0),
            missing_basis,
            authorization,
            rebuilt.signal_session,
            rebuilt.target_weight,
            "0" * 64,
        )
    forged_date = dataclasses.replace(second, execution_session=date(2024, 4, 1))
    forged_authorization = _authorization(calendar, (first, forged_date, final), projection)
    with pytest.raises(SCRIPT.InputBlockedError):
        SCRIPT._simulate_cohorts(
            calendar,
            (first, forged_date),
            final,
            daily_sessions=daily,
            action_projection_bytes=projection,
            authorization=forged_authorization,
            expected_input_bundle_sha256=bundle_sha,
            **stage_contract,
        )


def test_validation_bounds_real_gate_and_no_duplicate_adapter_surface() -> None:
    SCRIPT._require_query_bounds(
        date(2018, 1, 2),
        date(2021, 12, 1),
        SCRIPT.VALIDATION_QUERY_BOUNDS,
        "validation",
    )
    with pytest.raises(SCRIPT.InputBlockedError, match="exact frozen"):
        SCRIPT._require_query_bounds(
            date(2018, 1, 2),
            date(2021, 12, 31),
            SCRIPT.VALIDATION_QUERY_BOUNDS,
            "validation",
        )
    with pytest.raises(SCRIPT.InputBlockedError, match="calendar session count"):
        SCRIPT.simulate_validation(
            _calendar((date(2018, 1, 2), date(2021, 12, 1))),
            (),
            None,  # type: ignore[arg-type]
            daily_sessions=(),
            action_projection_bytes=b"",
            authorization=None,  # type: ignore[arg-type]
            query_start=date(2018, 1, 2),
            query_end=date(2021, 12, 1),
        )
    with pytest.raises(SCRIPT.InputBlockedError, match="current JSON"):
        SCRIPT.validate_runtime_authorization(None, _calendar((date(2024, 1, 2),)))

    tree = ast.parse(ADAPTER_PATH.read_text(encoding="utf-8"))
    public_names = {
        node.name for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef))
    }
    forbidden = {
        "RebalanceRequest",
        "ExecutionFillObservation",
        "DistributionEntitlement",
        "form_monthly_rebalance",
        "observe_execution_fill",
        "distribution_entitlement",
        "cash_credit_on",
    }
    assert public_names.isdisjoint(forbidden)
    assert "run_static_rebalance" in SCRIPT_PATH.read_text(encoding="utf-8")
    assert "apply_cash_distribution" in SCRIPT_PATH.read_text(encoding="utf-8")
    assert "apply_split" in SCRIPT_PATH.read_text(encoding="utf-8")

    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert not ({"open", "exec", "eval", "compile"} & called_names)


def test_exact_bundle_capture_rejects_permissions_symlink_and_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tmp_path.chmod(0o700)
    payload = b'{"fixed":"bundle"}'
    monkeypatch.setattr(SCRIPT, "VALIDATION_BUNDLE_FILE_SHA256", hashlib.sha256(payload).hexdigest())
    bundle = tmp_path / "bundle.json"
    bundle.write_bytes(payload)
    bundle.chmod(0o600)
    assert SCRIPT._capture_bundle(bundle) == payload

    bundle.chmod(0o644)
    with pytest.raises(SCRIPT.InputBlockedError, match="mode or size"):
        SCRIPT._capture_bundle(bundle)
    bundle.chmod(0o600)
    link = tmp_path / "link.json"
    link.symlink_to(bundle)
    with pytest.raises(OSError):
        SCRIPT._capture_bundle(link)

    original_read = SCRIPT.os.read
    replaced = False

    def replace_after_first_read(fd: int, size: int) -> bytes:
        nonlocal replaced
        chunk = original_read(fd, size)
        if chunk and not replaced:
            replacement = tmp_path / "replacement.json"
            replacement.write_bytes(payload)
            replacement.chmod(0o600)
            SCRIPT.os.replace(replacement, bundle)
            replaced = True
        return chunk

    monkeypatch.setattr(SCRIPT.os, "read", replace_after_first_read)
    with pytest.raises(SCRIPT.InputBlockedError, match="changed during"):
        SCRIPT._capture_bundle(bundle)


def test_strict_bundle_parser_rejects_duplicate_and_nonfinite_json() -> None:
    with pytest.raises(SCRIPT.InputBlockedError, match="duplicate JSON key"):
        SCRIPT._load_validation_bundle(b'{"stage":"validation","stage":"holdout"}')
    with pytest.raises(SCRIPT.InputBlockedError):
        SCRIPT._load_validation_bundle(b'{"value":NaN}')


def test_one_use_bridge_claims_before_read_and_writes_aggregate_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tmp_path.chmod(0o700)
    definition = b"{}"
    definition_sha = hashlib.sha256(definition).hexdigest()
    code_sha = hashlib.sha256(b"code").hexdigest()
    claim = tmp_path / "claim.json"
    result = tmp_path / "result.json"
    calls: list[str] = []

    monkeypatch.setattr(
        SCRIPT, "_read_definition",
        lambda: (definition, {"status": "PREREGISTERED_NOT_EXECUTED"}),
    )
    monkeypatch.setattr(SCRIPT, "_file_sha256", lambda path: code_sha)

    def capture(path: Path) -> bytes:
        assert claim.exists()
        calls.append("capture")
        return b"captured"

    monkeypatch.setattr(SCRIPT, "_capture_bundle", capture)
    monkeypatch.setattr(
        SCRIPT, "_load_validation_bundle", lambda payload: (object(), (), object(), (), b"projection")
    )
    navs = tuple(40_000.0 + index for index in range(46))
    simulation = SCRIPT.CohortSimulation(navs, navs, (0.0,) * 45, (0.0,) * 45, (), ())
    monkeypatch.setattr(SCRIPT, "simulate_validation", lambda *args, **kwargs: simulation)
    metrics = MODULE.PerformanceMetrics(0.1, 0.2, 0.3, 0.4, 0.5, -0.1)
    gates = tuple((name, True) for name in (
        "sharpe_difference_positive", "strategy_compounded_net_return_positive",
        "strategy_annualized_volatility_lower", "strategy_maximum_drawdown_better",
    ))
    monkeypatch.setattr(
        SCRIPT, "validation_gate_decision",
        lambda *args: MODULE.ValidationDecision(45, metrics, metrics, 0.1, gates),
    )
    receipt_sha = hashlib.sha256(b"receipt").hexdigest()
    monkeypatch.setattr(
        SCRIPT, "validation_receipt", lambda value: SCRIPT.ValidationReceipt(navs, navs, receipt_sha)
    )

    assert SCRIPT._run_once(tmp_path / "bundle.json", claim, result, (definition_sha, code_sha, code_sha)) == 0
    published = json.loads(result.read_text())
    assert calls == ["capture"]
    assert published["classification"] == "VALIDATION_PASS_HOLDOUT_LOCKED"
    assert published["strategy_candidate_available"] is False
    assert published["holdout_opened"] is False
    assert published["code_and_core_sha256"]["definition"] == definition_sha
    assert len(published["strategy_boundary_navs_hex"]) == 46
    assert "raw_open" not in result.read_text() and "raw_close" not in result.read_text()
    with pytest.raises(SCRIPT.InputBlockedError, match="must be absent"):
        SCRIPT._run_once(tmp_path / "bundle.json", claim, tmp_path / "second.json", (definition_sha, code_sha, code_sha))
    assert calls == ["capture"]
