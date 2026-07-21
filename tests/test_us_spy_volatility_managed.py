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
INCLUSION_SHA = hashlib.sha256(b"fixed-spy-universe").hexdigest()


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
            content_sha256=SCRIPT.QUALIFIED_CALENDAR_PROJECTION_SHA256,
        ),
    )
    return AcceptedSessionCalendar(sessions, identity=identity)


def _close(calendar: AcceptedSessionCalendar, day: date, index: int) -> MODULE.CloseObservation:
    session = calendar.session_on(day, as_of=datetime(2030, 1, 1, tzinfo=UTC))
    return MODULE.CloseObservation(
        day,
        100.0 + index * 0.3 + (index % 4) * 0.11,
        _source(f"close-{day}", session.close_at + timedelta(minutes=1)),
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
    values = {"listed": True, "delisted": False, "st": False, "suspended": False}
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
    signal = calendar.session_on(signal_day, as_of=datetime(2030, 1, 1, tzinfo=UTC))
    return ExecutionInput(
        "SPY",
        "us",
        open_price,
        "USD",
        _source(f"open-{execution_day}", execution.open_at),
        _statuses(),
        decision_price=decision_price,
        decision_price_source=_source(f"decision-{signal_day}", signal.close_at),
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
        "PREREGISTERED_NOT_EXECUTED",
        hashlib.sha256(REPORT_PATH.read_bytes()).hexdigest(),
        hashlib.sha256(ADAPTER_PATH.read_bytes()).hexdigest(),
        SCRIPT.PR117_REVIEWED_HEAD,
        calendar_identity_sha256(calendar.identity),
        SCRIPT.QUALIFIED_MARKET_ROWS_SHA256,
        SCRIPT.runtime_input_bundle_sha256(calendar, points, projection_bytes)
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
    row = _execution_input(
        calendar,
        signal_day,
        execution_day,
        open_price=open_price,
        decision_price=decision_price,
    )
    position = calendar.session_dates.index(signal_day)
    close_days = calendar.session_dates[position - 21 : position + 1]
    closes = tuple(_close(calendar, day, index) for index, day in enumerate(close_days))
    relevant = tuple(
        action for action in official_actions if action.effective_date in set(close_days[1:])
    )
    return SCRIPT.ExecutionPoint(
        closes,
        relevant,
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
    assert frozen["calendar_and_signal"]["required_raw_closes"] == 22
    assert frozen["splits"]["validation_entry_cohorts"]["required_count"] == 45
    assert frozen["splits"]["retrospective_holdout_entry_cohorts"]["required_count"] == 53
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


def test_holdout_unlock_recomputes_validation_navs_and_digest() -> None:
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
    assert (
        actions[0].source.available_at
        == calendar.session_on(
            actions[0].effective_date,
            as_of=SCRIPT.OFFICIAL_ACTION_RETRIEVED_AT,
        ).open_at
    )
    SCRIPT.assert_zero_distribution_execution_overlap(actions, (date(2018, 5, 1),))

    changed = projection.replace(b'"distribution":"1.000000"', b'"distribution":"999.99"')
    with pytest.raises(SCRIPT.InputBlockedError, match="full hash mismatch"):
        SCRIPT.official_actions_from_projection(changed, calendar)
    with pytest.raises(SCRIPT.InputBlockedError, match="overlap"):
        SCRIPT.assert_zero_distribution_execution_overlap(
            actions,
            (actions[0].effective_date,),
        )


def test_authorization_binds_actual_files_and_reviewed_core_head() -> None:
    calendar = _calendar(_business_days(date(2024, 1, 1), date(2024, 2, 2)))
    authorization = _authorization(calendar)
    SCRIPT.validate_runtime_authorization(authorization, calendar)
    forged = SCRIPT.RuntimeAuthorization(
        authorization.preregistration_status,
        "0" * 64,
        authorization.strategy_adapter_sha256,
        authorization.causal_core_reviewed_head,
        authorization.calendar_identity_sha256,
        authorization.qualified_market_rows_sha256,
        authorization.input_bundle_sha256,
    )
    with pytest.raises(SCRIPT.InputBlockedError, match="current bytes"):
        SCRIPT.validate_runtime_authorization(forged, calendar)
    wrong_core = SCRIPT.RuntimeAuthorization(
        authorization.preregistration_status,
        authorization.preregistration_json_sha256,
        authorization.strategy_adapter_sha256,
        "c" * 40,
        authorization.calendar_identity_sha256,
        authorization.qualified_market_rows_sha256,
        authorization.input_bundle_sha256,
    )
    with pytest.raises(SCRIPT.InputBlockedError, match="reviewed PR117"):
        SCRIPT.validate_runtime_authorization(wrong_core, calendar)


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
        open_price=10.0,
        decision_price=10.0,
        official_actions=official_actions,
    )
    second = _point(
        calendar,
        date(2024, 2, 29),
        date(2024, 3, 1),
        open_price=11.0,
        decision_price=10.5,
        official_actions=official_actions,
    )
    final = _point(
        calendar,
        date(2024, 3, 29),
        date(2024, 4, 1),
        open_price=12.0,
        decision_price=11.5,
        official_actions=official_actions,
    )
    daily = tuple(day for day in days if date(2024, 2, 1) <= day <= date(2024, 4, 1))
    bundle_sha = SCRIPT.runtime_input_bundle_sha256(
        calendar,
        (first, second, final),
        projection,
    )
    monkeypatch.setattr(SCRIPT, "RUNTIME_INPUT_BUNDLE_SHA256", bundle_sha)
    authorization = _authorization(calendar, (first, second, final), projection)

    first_run = SCRIPT._simulate_cohorts(
        calendar,
        (first, second),
        final,
        daily_sessions=daily,
        action_projection_bytes=projection,
        authorization=authorization,
        expected_months=((2024, 2), (2024, 3)),
    )
    second_run = SCRIPT._simulate_cohorts(
        calendar,
        (first, second),
        final,
        daily_sessions=daily,
        action_projection_bytes=projection,
        authorization=authorization,
        expected_months=((2024, 2), (2024, 3)),
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
    rebuilt = SCRIPT._point_signal(calendar, first, official_actions)
    assert rebuilt.target_weight == MODULE.target_weight(rebuilt.annualized_volatility)
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
            expected_months=((2024, 2), (2024, 3)),
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
