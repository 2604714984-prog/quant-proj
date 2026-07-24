from copy import deepcopy
import base64
from dataclasses import replace
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo

import pytest

import quant_system.backtest.event_loop as event_loop_module
from quant_system.backtest import (
    CapacityObservation,
    CapacityPolicy,
    DecisionArtifact,
    CostStressCase,
    ExecutionInput,
    ExecutionCostAssumptions,
    NoFillEvent,
    Portfolio,
    StageContext,
    TerminalAction,
    TransactionCostModel,
    blocked_exit_from_receipt,
    capture_candidate_run_config,
    capture_controlled_stage_receipt,
    capture_decision_artifact,
    create_stage_plan,
    genesis_stage,
    load_candidate_run_bundle,
    load_controlled_stage_receipt,
    next_stage,
    replay_candidate_run_bundle,
    run_candidate_rebalance,
    run_controlled_stage,
    run_static_rebalance,
    serialize_candidate_run_bundle,
    serialize_controlled_stage_receipt,
)
from quant_system.data import (
    AcceptedSession,
    AcceptedSessionCalendar,
    CalendarIdentity,
    CorporateActionIdentity,
    SourceIdentity,
    capture_source_bytes,
    parse_provider_observation,
    calendar_identity_sha256,
    session_dates_sha256,
    session_rows_sha256,
)
from quant_system.markets.common import MarketDataError
from quant_system.markets.a_share import (
    AShareAdjustmentReceipt,
    capture_a_share_adjustment_receipt,
)
from quant_system.markets.universe import (
    StatusEvidence,
    UniverseMaterialization,
    UniverseSnapshotIdentity,
    lifecycle_coverage_sha256,
    materialize_universe_partition,
    ordered_members_sha256,
)
from quant_system.markets.us import CorporateActionValuationError
from quant_system.research.identity import build_dataset_manifest
from quant_system.research.experiments import (
    capture_family_anchor,
    capture_family_contract,
    capture_final_run_receipt,
    capture_holdout_result,
    capture_trial_config,
    evaluate_frozen_historical_run,
    freeze_experiment_manifest,
    persist_experiment_ledger,
    preregister_trial,
    record_holdout_result,
    replay_trial_run,
)
from quant_system.research.splits import (
    build_split_evaluation_plan,
    build_split_manifest,
    capture_return_artifact,
    evaluate_split,
)

UTC = timezone.utc
DEFINITION_SHA = hashlib.sha256(b"fixture-strategy-definition-v1").hexdigest()
ADAPTER_SHA = hashlib.sha256(b"fixture-strategy-adapter-v1").hexdigest()
INCLUSION_RULE_SHA = hashlib.sha256(b"fixture-universe-inclusion-rule-v1").hexdigest()


def _adjustment_receipt(
    symbol: str,
    session: date,
    *,
    price_basis: str = "raw",
    adjustment_factor: str = "1",
    action_types: tuple[str, ...] = (),
) -> AShareAdjustmentReceipt:
    factor_bytes = json.dumps(
        {
            "adjustment_factor": adjustment_factor,
            "price_basis": price_basis,
            "session": session.isoformat(),
            "symbol": symbol,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    action_bytes = json.dumps(
        {
            "action_types": action_types,
            "session": session.isoformat(),
            "symbol": symbol,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return capture_a_share_adjustment_receipt(
        factor_bytes=factor_bytes,
        action_completeness_bytes=action_bytes,
        publication_evidence=b"fixture publication receipt",
        factor_source_url="https://example.test/a-share-adjustment-factor",
        action_completeness_source_url="https://example.test/a-share-actions",
        available_at=datetime(2000, 1, 1, tzinfo=UTC),
        retrieved_at=datetime(2000, 1, 1, 0, 1, tzinfo=UTC),
        provider_id="fixture-provider",
    )


def _source(
    label: str,
    available_at: datetime,
    *,
    content_sha256: str | None = None,
) -> SourceIdentity:
    revision_id = "".join(character if ord(character) >= 32 else "-" for character in label)
    return SourceIdentity(
        source_url="https://example.test/source",
        content_sha256=content_sha256 or hashlib.sha256(label.encode()).hexdigest(),
        available_at=available_at,
        retrieved_at=available_at + timedelta(minutes=1),
        revision_id=revision_id,
        source_family_id="fixture-source",
        provider_id="fixture-provider",
        subject_id="fixture-subject",
    )


def _session(day: date, timezone_name: str, label: str) -> AcceptedSession:
    zone = ZoneInfo(timezone_name)
    exchange_id = "XNYS" if timezone_name == "America/New_York" else "XSHG"
    return AcceptedSession(
        day,
        datetime.combine(day, time(9, 30), zone),
        datetime.combine(day, time(16 if timezone_name == "America/New_York" else 15), zone),
        _source(f"calendar-{label}", datetime(2000, 1, 1, tzinfo=UTC)),
        timezone_name,
        exchange_id=exchange_id,
    )


def _calendar(days: tuple[date, ...], timezone_name: str) -> AcceptedSessionCalendar:
    rows = tuple(_session(day, timezone_name, str(index)) for index, day in enumerate(days))
    dates = tuple(row.session_date for row in rows)
    rows_sha = session_rows_sha256(rows)
    identity = CalendarIdentity(
        "XNYS" if timezone_name == "America/New_York" else "XSHG",
        timezone_name,
        dates[0],
        dates[-1],
        len(dates),
        session_dates_sha256(dates),
        rows_sha,
        _source("calendar-aggregate", datetime(2000, 1, 1, tzinfo=UTC)),
    )
    return AcceptedSessionCalendar(rows, identity=identity)


def _calendar_revision(
    days: tuple[date, ...],
    timezone_name: str,
    *,
    available_at: datetime,
    revision_id: str,
    supersedes_revision_id: str = "calendar-aggregate",
    changed_session: date | None = None,
    semantic_change: str | None = None,
    late_source_session: date | None = None,
    late_source_available_at: datetime | None = None,
) -> AcceptedSessionCalendar:
    if (late_source_session is None) != (late_source_available_at is None):
        raise AssertionError("late source session and available_at must be paired")
    rows_list: list[AcceptedSession] = []
    for index, day in enumerate(days):
        row = _session(day, timezone_name, f"{revision_id}-{index}")
        if day == changed_session:
            if semantic_change == "open":
                row = replace(row, open_at=row.open_at + timedelta(minutes=1))
            elif semantic_change == "close":
                row = replace(row, close_at=row.close_at - timedelta(hours=1))
            elif semantic_change == "early_close":
                row = replace(row, is_early_close=not row.is_early_close)
            else:
                raise AssertionError("semantic_change must identify a changed field")
        if day == late_source_session:
            assert late_source_available_at is not None
            row = replace(
                row,
                source=_source(
                    f"{revision_id}-{index}-late",
                    late_source_available_at,
                ),
            )
        rows_list.append(row)
    rows = tuple(rows_list)
    dates = tuple(row.session_date for row in rows)
    identity = CalendarIdentity(
        "XNYS" if timezone_name == "America/New_York" else "XSHG",
        timezone_name,
        dates[0],
        dates[-1],
        len(dates),
        session_dates_sha256(dates),
        session_rows_sha256(rows),
        SourceIdentity(
            source_url="https://example.test/source",
            content_sha256=hashlib.sha256(revision_id.encode()).hexdigest(),
            available_at=available_at,
            retrieved_at=available_at + timedelta(minutes=1),
            revision_id=revision_id,
            source_family_id="fixture-source",
            provider_id="fixture-provider",
            subject_id="fixture-subject",
            supersedes_revision_id=supersedes_revision_id,
        ),
    )
    return AcceptedSessionCalendar(rows, identity=identity)


def _statuses(
    symbol: str,
    timezone_name: str,
    *,
    suspended: bool = False,
    delisted: bool = False,
    include_st: bool = True,
    include_suspended: bool = True,
    available_at: datetime = datetime(2000, 1, 1, tzinfo=UTC),
) -> tuple[StatusEvidence, ...]:
    values = {"listed": True, "delisted": delisted}
    if include_st:
        values["st"] = False
    if include_suspended:
        values["suspended"] = suspended
    return tuple(
        StatusEvidence(
            f"{symbol}-{kind}",
            symbol,
            kind,
            value,
            date(1990, 1, 1),
            None,
            timezone_name,
            _source(f"status-{symbol}-{kind}", available_at),
        )
        for kind, value in values.items()
    )


def _input(
    symbol: str,
    market: str,
    execution: AcceptedSession,
    *,
    price: float | None = 10.0,
    suspended: bool = False,
    delisted: bool = False,
    action_types: tuple[str, ...] = (),
    corporate_actions: tuple[CorporateActionIdentity, ...] = (),
    capacity: CapacityObservation | None = None,
    terminal: TerminalAction | None = None,
    source_label: str | None = None,
    decision_price: float | None = None,
    decision_price_available_at: datetime = datetime(2000, 1, 1, tzinfo=UTC),
    decision_price_basis: str | None = "raw_pre_action_per_old_share",
    execution_price_source_available_at: datetime | None = None,
    execution_price_effective_at: datetime | None = None,
    execution_price_basis: str | None = "timestamped_session_open",
    limit_regime: str = "no_limit",
    adjustment_basis: str = "raw",
    adjustment_factor: str = "1",
    a_share_action_types: tuple[str, ...] = (),
) -> ExecutionInput:
    timezone_name = execution.exchange_timezone
    source_available_at = (
        execution.open_at
        if execution_price_source_available_at is None
        else execution_price_source_available_at
    )
    decision_reference = (
        (10.0 if price is None else float(price))
        if decision_price is None
        else decision_price
    )
    return ExecutionInput(
        symbol,
        market,  # type: ignore[arg-type]
        price,
        "USD" if market == "us" else "CNY",
        _source(
            source_label or f"bar-{symbol}",
            source_available_at,
        ),
        _statuses(
            symbol,
            timezone_name,
            suspended=suspended,
            delisted=delisted,
            include_st=market == "a_share",
            include_suspended=market == "a_share",
        ),
        action_types,
        corporate_actions,
        suspended,
        None,
        None,
        capacity,
        terminal,
        decision_reference,
        _source(f"decision-price-{symbol}", decision_price_available_at),
        decision_price_basis,  # type: ignore[arg-type]
        execution.open_at
        if execution_price_effective_at is None
        else execution_price_effective_at,
        execution_price_basis,  # type: ignore[arg-type]
        limit_regime if market == "a_share" else None,  # type: ignore[arg-type]
        _adjustment_receipt(
            symbol,
            execution.session_date,
            price_basis=adjustment_basis,
            adjustment_factor=adjustment_factor,
            action_types=a_share_action_types,
        )
        if market == "a_share"
        else None,
        no_open_observed_at=(
            source_available_at
            if execution_price_basis == "confirmed_no_open_event"
            else None
        ),
    )


def _snapshot(
    calendar: AcceptedSessionCalendar,
    execution: AcceptedSession,
    decision_at: datetime,
    inputs: tuple[ExecutionInput, ...],
    members: tuple[str, ...],
    *,
    source_label: str = "universe-snapshot",
) -> UniverseSnapshotIdentity:
    cutoff = min(decision_at, execution.open_at - timedelta(microseconds=1))
    records = {
        row.symbol: row.status_records
        for row in inputs
        if row.symbol in members
    }
    member_hash = ordered_members_sha256(members)
    lifecycle_hash = lifecycle_coverage_sha256(
        members,
        execution,
        cutoff,
        records,
        market=inputs[0].market,
    )
    calendar_hash = calendar_identity_sha256(calendar.identity)
    return UniverseSnapshotIdentity(
        market=inputs[0].market,
        exchange_id=calendar.identity.exchange_id,
        effective_session=execution.session_date,
        member_count=len(members),
        ordered_members_sha256=member_hash,
        lifecycle_coverage_sha256=lifecycle_hash,
        inclusion_rule_sha256=INCLUSION_RULE_SHA,
        calendar_identity_sha256=calendar_hash,
        source_identity=_source(source_label, datetime(2000, 1, 1, tzinfo=UTC)),
    )


def _run_static_rebalance(
    portfolio: Portfolio,
    calendar: AcceptedSessionCalendar,
    **kwargs,
):
    inputs = kwargs["execution_inputs"]
    members = kwargs.setdefault(
        "universe_members",
        tuple(sorted(row.symbol for row in inputs)),
    )
    execution = calendar.next_session(
        kwargs["signal_session"],
        as_of=kwargs["decision_at"],
    )
    kwargs.setdefault(
        "universe_snapshot",
        _snapshot(calendar, execution, kwargs["decision_at"], inputs, members),
    )
    kwargs.setdefault("strategy_definition_sha256", DEFINITION_SHA)
    kwargs.setdefault("strategy_adapter_sha256", ADAPTER_SHA)
    kwargs.setdefault(
        "stage_context",
        genesis_stage(create_stage_plan((kwargs["signal_session"],))),
    )
    return run_static_rebalance(portfolio, calendar, **kwargs)


def test_static_rebalance_uses_frozen_callback_and_is_deterministic() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal, execution = (
        calendar.session_on(day, as_of=datetime(2026, 7, 13, 12, tzinfo=UTC)) for day in days
    )
    portfolio = Portfolio.a_share(100_000, costs=TransactionCostModel())
    inputs = (
        _input("AAA", "a_share", execution, price=10),
        _input("BBB", "a_share", execution, price=20),
    )
    seen = []

    def strategy(context):
        seen.append(context)
        assert context.signal_session == signal
        assert context.execution_session == execution
        assert context.eligible_symbols == ("AAA", "BBB")
        assert not hasattr(context, "open_price")
        return {"AAA": 0.5, "BBB": 0.5}

    before = deepcopy(portfolio.__dict__)
    first = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=inputs,
        target_weights=strategy,
    )
    second = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=inputs,
        target_weights=lambda _: {"BBB": 0.5, "AAA": 0.5},
    )

    assert [receipt.symbol for receipt in first.receipts] == ["AAA", "BBB"]
    assert first.portfolio.positions["AAA"].shares == 5_000
    assert first.portfolio.positions["BBB"].shares == 2_500
    assert first.stage_hash == second.stage_hash
    assert first.input_identity_hash == second.input_identity_hash
    assert portfolio.__dict__ == before
    assert len(seen) == 1


def test_stage_plan_requires_genesis_then_exact_previous_result() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14), date(2026, 7, 15))
    calendar = _calendar(days, "Asia/Shanghai")
    plan = create_stage_plan(days[:2])
    first_execution = calendar.session_on(
        days[1],
        as_of=datetime(2026, 7, 13, 12, tzinfo=UTC),
    )
    first = _run_static_rebalance(
        Portfolio.a_share(100_000, costs=TransactionCostModel()),
        calendar,
        signal_session=days[0],
        decision_at=first_execution.open_at - timedelta(minutes=1),
        execution_inputs=(_input("AAA", "a_share", first_execution),),
        target_weights=lambda _: {},
        stage_context=genesis_stage(plan),
    )
    second_execution = calendar.session_on(days[2], as_of=first.context.execution_session.close_at)
    second = _run_static_rebalance(
        first.portfolio,
        calendar,
        signal_session=days[1],
        decision_at=second_execution.open_at - timedelta(minutes=1),
        execution_inputs=(_input("AAA", "a_share", second_execution),),
        target_weights=lambda _: {},
        stage_context=next_stage(plan, first),
    )

    assert second.stage_index == 1
    assert second.stage_session == days[1]
    assert second.prior_stage_hash == first.stage_hash
    assert second.initial_portfolio_sha256 == first.final_portfolio_sha256
    with pytest.raises(ValueError, match="StageContext must be created"):
        StageContext(plan.plan_sha256, 1, days[1], "0" * 64)
    with pytest.raises(ValueError, match="session must match"):
        _run_static_rebalance(
            first.portfolio,
            calendar,
            signal_session=days[0],
            decision_at=first_execution.open_at - timedelta(minutes=1),
            execution_inputs=(_input("AAA", "a_share", first_execution),),
            target_weights=lambda _: {},
            stage_context=next_stage(plan, first),
        )
    with pytest.raises(ValueError, match="chronological"):
        create_stage_plan((days[1], days[0]))


def test_timing_pit_and_target_weight_boundaries_fail_closed() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(10_000, costs=TransactionCostModel())
    input_row = _input("AAA", "a_share", execution)

    with pytest.raises(MarketDataError, match="between signal close"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at - timedelta(microseconds=1),
            execution_inputs=(input_row,),
            target_weights=lambda _: {},
        )
    accepted_at_close = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(input_row,),
        target_weights=lambda _: {},
    )
    assert accepted_at_close.context.decision_at == signal.close_at
    accepted = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=execution.open_at - timedelta(microseconds=1),
        execution_inputs=(input_row,),
        target_weights=lambda _: {},
    )
    assert accepted.context.decision_at == execution.open_at - timedelta(microseconds=1)

    for decision_at in (
        execution.open_at,
        execution.open_at + timedelta(microseconds=1),
    ):
        with pytest.raises(MarketDataError, match="strictly before next-session open"):
            _run_static_rebalance(
                portfolio,
                calendar,
                signal_session=days[0],
                decision_at=decision_at,
                execution_inputs=(input_row,),
                target_weights=lambda _: {},
            )
    late = replace(
        input_row,
        source=_source("late", execution.open_at + timedelta(seconds=1)),
    )
    with pytest.raises(MarketDataError, match="timestamped session-open source"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(late,),
            target_weights=lambda _: {},
        )
    retrospective = replace(
        late,
        execution_price_basis="retrospective_daily_bar_open_fill",
    )
    accepted_retrospective = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(retrospective,),
        target_weights=lambda _: {},
    )
    assert accepted_retrospective.context.execution_session == execution
    with pytest.raises(ValueError, match=r"in \[0, 1\]"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(input_row,),
            target_weights=lambda _: {"AAA": 1.1},
        )


def test_execution_price_event_and_late_source_are_explicit_and_fail_closed() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "America/New_York")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 22, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.us(10_000, costs=TransactionCostModel())
    before = deepcopy(portfolio.__dict__)
    callback_calls = []
    base = _input("SPY", "us", execution)
    arguments = {
        "signal_session": days[0],
        "decision_at": signal.close_at,
        "target_weights": lambda context: callback_calls.append(context) or {"SPY": 1.0},
    }

    for bad in (
        replace(base, execution_price_effective_at=None),
        replace(base, execution_price_basis=None),
    ):
        with pytest.raises(MarketDataError, match="effective_at and basis are required"):
            _run_static_rebalance(
                portfolio,
                calendar,
                execution_inputs=(bad,),
                **arguments,
            )
    unknown = replace(base, execution_price_basis="official_auction_q")
    with pytest.raises(MarketDataError, match="execution price basis is unsupported"):
        _run_static_rebalance(
            portfolio,
            calendar,
            execution_inputs=(unknown,),
            **arguments,
        )
    for offset in (-1, 1):
        mistimed = replace(
            base,
            execution_price_effective_at=(
                execution.open_at + timedelta(microseconds=offset)
            ),
        )
        with pytest.raises(MarketDataError, match="must equal the accepted-session open"):
            _run_static_rebalance(
                portfolio,
                calendar,
                execution_inputs=(mistimed,),
                **arguments,
            )
    too_early = replace(
        base,
        source=_source("pre-event-open", execution.open_at - timedelta(microseconds=1)),
        execution_price_basis="retrospective_daily_bar_open_fill",
    )
    with pytest.raises(MarketDataError, match="cannot be available before its market event"):
        _run_static_rebalance(
            portfolio,
            calendar,
            execution_inputs=(too_early,),
            **arguments,
        )
    assert callback_calls == []
    assert portfolio.__dict__ == before

    late = replace(
        base,
        source=_source("eod-open", execution.close_at + timedelta(hours=2)),
        execution_price_basis="retrospective_daily_bar_open_fill",
    )
    retrospective = _run_static_rebalance(
        portfolio,
        calendar,
        execution_inputs=(late,),
        **arguments,
    )
    assert callback_calls == [retrospective.context]
    assert retrospective.receipts[0].requested_shares == 1_000
    assert retrospective.receipts[0].price == 10.0
    assert portfolio.__dict__ == before


def test_execution_price_basis_changes_bound_identity_without_changing_receipts() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "America/New_York")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 22, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.us(10_000, costs=TransactionCostModel())
    timestamped = _input("SPY", "us", execution)
    retrospective = replace(
        timestamped,
        execution_price_basis="retrospective_daily_bar_open_fill",
    )
    arguments = {
        "signal_session": days[0],
        "decision_at": signal.close_at,
        "target_weights": lambda _: {"SPY": 1.0},
    }

    first = _run_static_rebalance(
        portfolio,
        calendar,
        execution_inputs=(timestamped,),
        **arguments,
    )
    second = _run_static_rebalance(
        portfolio,
        calendar,
        execution_inputs=(retrospective,),
        **arguments,
    )

    assert first.receipts == second.receipts
    assert first.input_identity_hash != second.input_identity_hash
    assert first.stage_hash != second.stage_hash


def test_confirmed_no_open_halt_requires_post_open_source_and_binds_identity() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "America/New_York")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 22, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    halt_notice_at = execution.open_at - timedelta(hours=1, minutes=30)
    portfolio = Portfolio.us(1_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("ABC", 10, 10, days[0])
    before = deepcopy(portfolio.__dict__)
    preopen_row = _input(
        "ABC",
        "us",
        execution,
        price=None,
        action_types=("trading_halt",),
        decision_price=10,
        source_label="halt-notice-v1",
        execution_price_source_available_at=halt_notice_at,
        execution_price_basis="confirmed_no_open_event",
    )
    first_row = _input(
        "ABC",
        "us",
        execution,
        price=None,
        action_types=("trading_halt",),
        decision_price=10,
        source_label="halt-notice-v1",
        execution_price_source_available_at=execution.open_at,
        execution_price_basis="confirmed_no_open_event",
    )
    second_row = replace(
        first_row,
        source=_source("halt-notice-v2", execution.open_at),
    )
    arguments = {
        "signal_session": days[0],
        "decision_at": signal.close_at,
        "target_weights": lambda _: {},
    }

    with pytest.raises(MarketDataError, match="post-event observation time"):
        _run_static_rebalance(
            portfolio,
            calendar,
            execution_inputs=(preopen_row,),
            **arguments,
        )
    first = _run_static_rebalance(
        portfolio,
        calendar,
        execution_inputs=(first_row,),
        **arguments,
    )
    second = _run_static_rebalance(
        portfolio,
        calendar,
        execution_inputs=(second_row,),
        **arguments,
    )

    assert first.receipts[0].reason == "confirmed_halt"
    assert first.receipts == second.receipts
    assert first.input_identity_hash != second.input_identity_hash
    assert first.stage_hash != second.stage_hash
    assert portfolio.__dict__ == before


def test_confirmed_no_open_event_contract_fails_before_callback() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14), date(2026, 7, 15))
    calendar = _calendar(days, "America/New_York")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 22, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    notice_at = execution.open_at
    portfolio = Portfolio.us(1_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("ABC", 10, 10, days[0])
    before = deepcopy(portfolio.__dict__)
    callback_calls: list[object] = []
    arguments = {
        "signal_session": days[0],
        "decision_at": signal.close_at,
        "target_weights": lambda context: callback_calls.append(context) or {},
    }
    unexplained = _input(
        "ABC",
        "us",
        execution,
        price=None,
        execution_price_source_available_at=notice_at,
        execution_price_basis="confirmed_no_open_event",
    )
    positive_price = _input(
        "ABC",
        "us",
        execution,
        price=10,
        action_types=("trading_halt",),
        execution_price_source_available_at=notice_at,
        execution_price_basis="confirmed_no_open_event",
    )
    distribution = CorporateActionIdentity(
        "ABC",
        "abc-dividend-no-open-v1",
        "cash_dividend",
        execution.open_at,
        _source("abc-dividend-no-open-source", signal.close_at),
        "America/New_York",
        ex_date=days[1],
        record_date=days[1],
        pay_date=days[2],
        cash_amount=Decimal("0.5"),
        currency="USD",
        unit="per_share",
    )
    unsupported_rich_action = _input(
        "ABC",
        "us",
        execution,
        price=None,
        corporate_actions=(distribution,),
        decision_price=10,
        execution_price_source_available_at=notice_at,
        execution_price_basis="confirmed_no_open_event",
    )

    with pytest.raises(MarketDataError, match="requires a halt or terminal action identity"):
        _run_static_rebalance(
            portfolio,
            calendar,
            execution_inputs=(unexplained,),
            **arguments,
        )
    with pytest.raises(MarketDataError, match="requires open_price=None"):
        _run_static_rebalance(
            portfolio,
            calendar,
            execution_inputs=(positive_price,),
            **arguments,
        )
    with pytest.raises(MarketDataError, match="requires a halt or terminal action identity"):
        _run_static_rebalance(
            portfolio,
            calendar,
            execution_inputs=(unsupported_rich_action,),
            **arguments,
        )

    assert callback_calls == []
    assert portfolio.__dict__ == before


def test_execution_calendar_revision_skips_announced_closure_for_t_plus_two() -> None:
    days = (
        date(2018, 11, 30),
        date(2018, 12, 3),
        date(2018, 12, 4),
        date(2018, 12, 5),
        date(2018, 12, 6),
        date(2018, 12, 7),
    )
    revised_days = tuple(day for day in days if day != date(2018, 12, 5))
    calendar = _calendar(days, "America/New_York")
    signal = calendar.session_on(days[0], as_of=datetime(2018, 11, 30, 22, tzinfo=UTC))
    execution = calendar.next_session(days[0], as_of=signal.close_at)
    decision_at = datetime(2018, 11, 30, 20, 5, tzinfo=ZoneInfo("America/New_York"))
    revision = _calendar_revision(
        revised_days,
        "America/New_York",
        available_at=datetime(2018, 12, 1, 12, tzinfo=ZoneInfo("America/New_York")),
        revision_id="bush-closure-revision",
    )
    assert revision.session_on(days[0], as_of=execution.open_at).source != (
        calendar.session_on(days[0], as_of=decision_at).source
    )

    def portfolio() -> Portfolio:
        value = Portfolio.us(1_000.0, costs=TransactionCostModel())
        value.start_session(days[0])
        value.buy("SPY", 10, 10, days[0])
        return value

    row = _input("SPY", "us", execution)
    first = _run_static_rebalance(
        portfolio(),
        calendar,
        signal_session=days[0],
        decision_at=decision_at,
        execution_inputs=(row,),
        execution_calendar_revision=revision,
        target_weights=lambda _: {},
    )
    assert first.receipts[-1].side == "sell"
    assert first.portfolio.pending_cash[0].settlement_date == date(2018, 12, 6)

    other_revision = _calendar_revision(
        revised_days,
        "America/New_York",
        available_at=datetime(2018, 12, 1, 12, tzinfo=ZoneInfo("America/New_York")),
        revision_id="bush-closure-revision-copy",
    )
    second = _run_static_rebalance(
        portfolio(),
        calendar,
        signal_session=days[0],
        decision_at=decision_at,
        execution_inputs=(row,),
        execution_calendar_revision=other_revision,
        target_weights=lambda _: {},
    )
    assert first.receipts == second.receipts
    assert first.input_identity_hash != second.input_identity_hash
    assert first.stage_hash != second.stage_hash


def test_execution_calendar_revision_fails_closed_before_callback() -> None:
    days = (
        date(2018, 11, 30),
        date(2018, 12, 3),
        date(2018, 12, 4),
        date(2018, 12, 5),
        date(2018, 12, 6),
        date(2018, 12, 7),
    )
    revised_days = tuple(day for day in days if day != date(2018, 12, 5))
    calendar = _calendar(days, "America/New_York")
    execution = calendar.next_session(
        days[0],
        as_of=datetime(2018, 11, 30, 20, 5, tzinfo=ZoneInfo("America/New_York")),
    )
    decision_at = datetime(2018, 11, 30, 20, 5, tzinfo=ZoneInfo("America/New_York"))
    row = _input("SPY", "us", execution)
    invalid = (
        (
            _calendar_revision(
                revised_days,
                "America/New_York",
                available_at=decision_at - timedelta(microseconds=1),
                revision_id="already-known",
            ),
            "after decision",
        ),
        (
            _calendar_revision(
                revised_days,
                "America/New_York",
                available_at=execution.open_at + timedelta(microseconds=1),
                revision_id="too-late",
            ),
            "by execution open",
        ),
        (
            _calendar_revision(
                revised_days,
                "America/New_York",
                available_at=execution.open_at,
                revision_id="wrong-parent",
                supersedes_revision_id="other-calendar",
            ),
            "must supersede",
        ),
        (
            _calendar_revision(
                revised_days[:-1],
                "America/New_York",
                available_at=execution.open_at,
                revision_id="short-coverage",
            ),
            "preserve exchange, timezone, and coverage",
        ),
        (
            _calendar_revision(
                (days[0],) + days[2:],
                "America/New_York",
                available_at=execution.open_at,
                revision_id="changed-execution",
            ),
            "cannot change the execution session",
        ),
        (
            _calendar_revision(
                revised_days,
                "America/New_York",
                available_at=execution.open_at,
                revision_id="changed-open",
                changed_session=execution.session_date,
                semantic_change="open",
            ),
            "cannot change the execution session",
        ),
        (
            _calendar_revision(
                revised_days,
                "America/New_York",
                available_at=execution.open_at,
                revision_id="changed-close",
                changed_session=execution.session_date,
                semantic_change="close",
            ),
            "cannot change the execution session",
        ),
        (
            _calendar_revision(
                revised_days,
                "America/New_York",
                available_at=execution.open_at,
                revision_id="changed-early-close",
                changed_session=execution.session_date,
                semantic_change="early_close",
            ),
            "cannot change the execution session",
        ),
        (
            _calendar_revision(
                revised_days,
                "Asia/Shanghai",
                available_at=execution.open_at,
                revision_id="wrong-market-calendar",
            ),
            "preserve exchange, timezone, and coverage",
        ),
    )
    for revision, message in invalid:
        callback_calls: list[object] = []
        original = Portfolio.us(1_000.0, costs=TransactionCostModel())
        before = deepcopy(original.__dict__)
        with pytest.raises(MarketDataError, match=message):
            _run_static_rebalance(
                original,
                calendar,
                signal_session=days[0],
                decision_at=decision_at,
                execution_inputs=(row,),
                execution_calendar_revision=revision,
                target_weights=lambda context: callback_calls.append(context) or {},
            )
        assert callback_calls == []
        assert original.__dict__ == before

    a_days = (date(2018, 11, 30), date(2018, 12, 3), date(2018, 12, 4))
    a_calendar = _calendar(a_days, "Asia/Shanghai")
    a_execution = a_calendar.next_session(
        a_days[0],
        as_of=datetime(2018, 11, 30, 16, tzinfo=ZoneInfo("Asia/Shanghai")),
    )
    a_revision = _calendar_revision(
        a_days,
        "Asia/Shanghai",
        available_at=a_execution.open_at,
        revision_id="a-share-revision",
    )
    with pytest.raises(MarketDataError, match="US-settlement-only"):
        _run_static_rebalance(
            Portfolio.a_share(1_000.0, costs=TransactionCostModel()),
            a_calendar,
            signal_session=a_days[0],
            decision_at=datetime(2018, 11, 30, 16, tzinfo=ZoneInfo("Asia/Shanghai")),
            execution_inputs=(_input("AAA", "a_share", a_execution),),
            execution_calendar_revision=a_revision,
            target_weights=lambda _: {},
        )


def test_execution_calendar_revision_rejects_late_unrelated_row_before_callback() -> None:
    days = (
        date(2018, 11, 30),
        date(2018, 12, 3),
        date(2018, 12, 4),
        date(2018, 12, 5),
        date(2018, 12, 6),
        date(2018, 12, 7),
    )
    revised_days = tuple(day for day in days if day != date(2018, 12, 5))
    calendar = _calendar(days, "America/New_York")
    decision_at = datetime(2018, 11, 30, 20, 5, tzinfo=ZoneInfo("America/New_York"))
    execution = calendar.next_session(days[0], as_of=decision_at)
    revision = _calendar_revision(
        revised_days,
        "America/New_York",
        available_at=datetime(2018, 12, 1, 12, tzinfo=ZoneInfo("America/New_York")),
        revision_id="late-unrelated-row",
        late_source_session=date(2018, 12, 7),
        late_source_available_at=execution.open_at + timedelta(microseconds=1),
    )
    portfolio = Portfolio.us(1_000.0, costs=TransactionCostModel())
    before = deepcopy(portfolio.__dict__)
    callback_calls: list[object] = []

    with pytest.raises(MarketDataError, match="every execution calendar revision row"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=decision_at,
            execution_inputs=(_input("SPY", "us", execution),),
            execution_calendar_revision=revision,
            target_weights=lambda context: callback_calls.append(context) or {},
        )

    assert callback_calls == []
    assert portfolio.__dict__ == before


def test_us_sells_before_buys_without_spending_unsettled_t_plus_three_cash() -> None:
    days = tuple(date(2016, 8, day) for day in range(1, 6))
    calendar = _calendar(days, "America/New_York")
    signal = calendar.session_on(days[0], as_of=datetime(2016, 8, 1, 22, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.us(100, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("OLD", 10, 10, days[0])

    result = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(
            _input("OLD", "us", execution),
            _input("NEW", "us", execution),
        ),
        target_weights=lambda _: {"NEW": 1.0},
    )

    assert [(item.side, item.symbol, item.reason) for item in result.receipts] == [
        ("sell", "OLD", "filled"),
        ("buy", "NEW", "insufficient_cash"),
    ]
    assert result.portfolio.positions == {}
    assert result.portfolio.available_cash == 0
    assert result.portfolio.pending_cash[0].settlement_date == days[4]
    assert result.receipts[0].cash_change == 100


def test_capacity_and_suspension_leave_blocked_exit_held_and_convertible() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14), date(2026, 7, 15))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(1_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("AAA", 100, 10, days[0])
    suspended = _input("AAA", "a_share", execution, price=None, suspended=True)

    result = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(suspended,),
        target_weights=lambda _: {},
    )
    assert result.receipts[0].reason == "suspended"
    assert result.portfolio.positions["AAA"].shares == 100
    blocked = blocked_exit_from_receipt(
        result.receipts[0],
        result.context,
        calendar,
        no_fill_event=NoFillEvent(
            observed_at=execution.open_at,
            effective_at=execution.open_at,
            reason="suspended",
            source=_captured_source(
                "blocked-AAA",
                execution.open_at,
                subject_id="AAA",
            ),
        ),
    )
    assert blocked.pending and len(blocked.retry_instructions) == 1
    assert blocked.no_fill_events[0].observed_at == execution.open_at

    observation = CapacityObservation(
        "AAA",
        signal,
        500,
        5_000,
        "CNY",
        _source("capacity-AAA", signal.close_at),
    )
    capped = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(_input("AAA", "a_share", execution, capacity=observation),),
        target_weights=lambda _: {},
        capacity_policy=CapacityPolicy(0.1, 0.1, "CNY"),
    )
    assert capped.receipts[0].reason.startswith("capacity:")
    assert capped.portfolio.positions["AAA"].shares == 100


def test_max_positions_counts_a_blocked_exit_before_replacement_buy() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(100_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("AAA", 100, 10, days[0])

    result = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(
            _input("AAA", "a_share", execution, price=None, suspended=True),
            _input("BBB", "a_share", execution),
        ),
        target_weights=lambda _: {"BBB": 0.5},
        max_positions=1,
    )

    assert [(item.side, item.symbol, item.reason) for item in result.receipts] == [
        ("sell", "AAA", "suspended"),
        ("buy", "BBB", "max_positions_after_blocked_exit"),
    ]
    assert set(result.portfolio.positions) == {"AAA"}
    assert result.receipts[1].filled_shares == 0
    assert result.receipts[1].cash_change == 0
    assert result.receipts[1].cash_after == result.receipts[0].cash_after


def test_max_positions_allows_replacement_after_successful_exit() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(100_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("AAA", 100, 10, days[0])

    result = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(
            _input("AAA", "a_share", execution),
            _input("BBB", "a_share", execution),
        ),
        target_weights=lambda _: {"BBB": 0.5},
        max_positions=1,
    )

    assert [(item.side, item.symbol, item.reason) for item in result.receipts] == [
        ("sell", "AAA", "filled"),
        ("buy", "BBB", "filled"),
    ]
    assert set(result.portfolio.positions) == {"BBB"}


def test_max_positions_allows_existing_symbol_adjustment_at_the_cap() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(100_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("AAA", 100, 10, days[0])

    result = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(
            _input("AAA", "a_share", execution),
            _input("BBB", "a_share", execution),
        ),
        target_weights=lambda _: {"AAA": 0.5, "BBB": 0.5},
        max_positions=1,
    )

    assert [(item.side, item.symbol, item.reason) for item in result.receipts] == [
        ("buy", "AAA", "filled"),
        ("buy", "BBB", "max_positions_after_blocked_exit"),
    ]
    assert result.portfolio.positions["AAA"].shares > 100
    assert "BBB" not in result.portfolio.positions


def test_max_positions_uses_sorted_new_symbol_order_deterministically() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(100_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("AAA", 100, 10, days[0])

    result = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(
            _input("CCC", "a_share", execution),
            _input("AAA", "a_share", execution, price=None, suspended=True),
            _input("BBB", "a_share", execution),
        ),
        target_weights=lambda _: {"CCC": 0.25, "BBB": 0.25},
        max_positions=2,
    )

    assert [(item.side, item.symbol, item.reason) for item in result.receipts] == [
        ("sell", "AAA", "suspended"),
        ("buy", "BBB", "filled"),
        ("buy", "CCC", "max_positions_after_blocked_exit"),
    ]
    assert set(result.portfolio.positions) == {"AAA", "BBB"}


@pytest.mark.parametrize("value", [True, 0, -1, 1.5])
def test_max_positions_validation_and_default_identity_compatibility(value) -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(100_000, costs=TransactionCostModel())
    inputs = (_input("AAA", "a_share", execution),)
    arguments = {
        "signal_session": days[0],
        "decision_at": signal.close_at,
        "execution_inputs": inputs,
        "target_weights": lambda _: {"AAA": 0.5},
    }

    default = _run_static_rebalance(portfolio, calendar, **arguments)
    explicit_none = _run_static_rebalance(portfolio, calendar, max_positions=None, **arguments)
    nonbinding_cap = _run_static_rebalance(portfolio, calendar, max_positions=10, **arguments)
    assert default.input_identity_hash == explicit_none.input_identity_hash
    assert default.stage_hash == explicit_none.stage_hash
    assert default.portfolio.__dict__ == nonbinding_cap.portfolio.__dict__
    assert default.input_identity_hash != nonbinding_cap.input_identity_hash
    with pytest.raises(ValueError, match="positive integer or None"):
        _run_static_rebalance(portfolio, calendar, max_positions=value, **arguments)


def test_distribution_identity_credits_prior_holder_and_raw_label_is_rejected() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14), date(2026, 7, 15))
    calendar = _calendar(days, "America/New_York")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 22, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.us(1_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("ABC", 10, 10, days[0])
    action = CorporateActionIdentity(
        "ABC",
        "abc-dividend-v1",
        "cash_dividend",
        execution.open_at,
        _source("abc-dividend-source", signal.close_at),
        "America/New_York",
        ex_date=days[1],
        record_date=days[1],
        pay_date=days[2],
        cash_amount=Decimal("0.5"),
        currency="USD",
        unit="per_share",
    )
    result = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(
            _input(
                "ABC",
                "us",
                execution,
                corporate_actions=(action,),
                decision_price=10,
            ),
        ),
        target_weights=lambda _: {"ABC": 0.1},
    )
    assert result.receipts[0].side == "distribution"
    assert result.portfolio.pending_cash_total == pytest.approx(5)
    assert result.receipts[0].reason == "entitlement:5"

    with pytest.raises(CorporateActionValuationError, match="rich identity"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(_input("ABC", "us", execution, action_types=("dividend",)),),
            target_weights=lambda _: {},
        )


def test_terminal_action_is_timed_ineligible_and_cannot_be_repurchased() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "America/New_York")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 22, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.us(1_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("DEAD", 10, 10, days[0])
    terminal = TerminalAction(
        "dead-delisting-v1",
        "delisting",
        execution.open_at,
        2.5,
        _source("dead-delisting-source", signal.close_at),
        execution.session_date,
        (),
    )
    utc_boundary = TerminalAction(
        "utc-boundary-delisting",
        "delisting",
        datetime(2026, 7, 14, 0, 30, tzinfo=UTC),
        0,
        terminal.source,
        date(2026, 7, 13),
        (),
    )
    assert utc_boundary.effective_at.astimezone(
        ZoneInfo("America/New_York")
    ).date() == utc_boundary.payment_date
    row = _input(
        "DEAD",
        "us",
        execution,
        price=None,
        delisted=True,
        action_types=("delisting",),
        terminal=terminal,
        execution_price_basis="confirmed_no_open_event",
    )
    result = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(row,),
        target_weights=lambda _: {},
    )
    assert result.portfolio.positions == {}
    assert result.receipts[0].cash_change == pytest.approx(25)
    assert result.receipts[0].reason == "terminal_delisting"

    eligible_row = ExecutionInput(
        **{
            **row.__dict__,
            "status_records": _statuses(
                "DEAD",
                "America/New_York",
                include_st=False,
                include_suspended=False,
            ),
        }
    )
    with pytest.raises(MarketDataError, match="PIT ineligible"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(eligible_row,),
            target_weights=lambda _: {"DEAD": 1.0},
        )

    empty = _run_static_rebalance(
        Portfolio.us(1_000, costs=TransactionCostModel()),
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(row,),
        target_weights=lambda _: {},
    )
    assert empty.receipts == () and empty.portfolio.positions == {}

    mistimed = TerminalAction(
        terminal.event_id,
        terminal.action_type,
        signal.open_at,
        terminal.recovery_per_share,
        terminal.source,
        terminal.payment_date,
        terminal.accepted_settlement_sessions,
    )
    with pytest.raises(MarketDataError, match="effective date"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(ExecutionInput(**{**row.__dict__, "terminal_action": mistimed}),),
            target_weights=lambda _: {},
        )

    intraday_future = TerminalAction(
        "dead-delisting-close-v1",
        terminal.action_type,
        execution.close_at,
        terminal.recovery_per_share,
        terminal.source,
        terminal.payment_date,
        terminal.accepted_settlement_sessions,
    )
    before = deepcopy(portfolio.__dict__)
    with pytest.raises(MarketDataError, match="follows execution open"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(
                ExecutionInput(**{**row.__dict__, "terminal_action": intraday_future}),
            ),
            target_weights=lambda _: {},
        )
    assert portfolio.__dict__ == before


def test_terminal_recovery_payment_evidence_is_pending_and_identity_bound() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14), date(2026, 7, 15))
    calendar = _calendar(days, "America/New_York")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 22, tzinfo=UTC))
    execution = calendar.next_session(days[0], as_of=signal.close_at)
    payment_session = calendar.next_session(days[1], as_of=signal.close_at)
    portfolio = Portfolio.us(100.0, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("DEAD", 10, 10, days[0])
    source = _source("terminal-payment-source", signal.close_at)
    pending_action = TerminalAction(
        "dead-delisting-payment-v1",
        "delisting",
        execution.open_at,
        2.5,
        source,
        payment_session.session_date,
        (payment_session,),
    )
    pending_row = _input(
        "DEAD",
        "us",
        execution,
        price=None,
        delisted=True,
        action_types=("delisting",),
        terminal=pending_action,
        execution_price_basis="confirmed_no_open_event",
    )
    pending = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(pending_row,),
        target_weights=lambda _: {},
    )

    assert pending.portfolio.available_cash == 0.0
    assert pending.portfolio.pending_cash_total == pytest.approx(25.0)
    assert pending.receipts[0].cash_change == 0.0
    assert "pending_until_2026-07-15" in pending.receipts[0].reason
    pending.portfolio.start_session(payment_session.session_date)
    assert pending.portfolio.available_cash == pytest.approx(25.0)

    same_day_action = replace(
        pending_action,
        payment_date=execution.session_date,
        accepted_settlement_sessions=(),
    )
    same_day = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(replace(pending_row, terminal_action=same_day_action),),
        target_weights=lambda _: {},
    )
    changed_source = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(
            replace(
                pending_row,
                terminal_action=replace(
                    pending_action,
                    source=_source("terminal-payment-source-v2", signal.close_at),
                ),
            ),
        ),
        target_weights=lambda _: {},
    )
    assert pending.input_identity_hash != same_day.input_identity_hash
    assert pending.input_identity_hash != changed_source.input_identity_hash


def test_missing_halt_mark_fails_and_identity_or_prior_stage_changes_hash() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "America/New_York")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 22, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.us(1_000, costs=TransactionCostModel())
    base = _input("ABC", "us", execution)
    first = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(base,),
        target_weights=lambda _: {},
    )
    changed = _input("ABC", "us", execution, source_label="different-partition")
    second = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(changed,),
        target_weights=lambda _: {},
    )
    assert first.receipts == () and second.receipts == ()
    assert first.input_identity_hash != second.input_identity_hash
    assert first.stage_hash != second.stage_hash

    numeric_change = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(_input("ABC", "us", execution, price=11),),
        target_weights=lambda _: {},
    )
    assert numeric_change.input_identity_hash != first.input_identity_hash
    with pytest.raises(ValueError, match="slippage_bps"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(base,),
            target_weights=lambda _: {},
            slippage_bps=-1,
        )

    portfolio.start_session(days[0])
    portfolio.buy("ABC", 10, 10, days[0])
    portfolio.positions["ABC"].last_accepted_mark = None
    halted = _input(
        "ABC",
        "us",
        execution,
        price=None,
        action_types=("trading_halt",),
        decision_price=10,
        execution_price_basis="confirmed_no_open_event",
    )
    halted_result = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(halted,),
        target_weights=lambda _: {},
    )
    assert halted_result.final_nav == pytest.approx(1_000)
    assert halted_result.receipts[0].reason == "confirmed_halt"


def test_same_day_distribution_receipt_reconciles_immediate_cash() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "America/New_York")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 22, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.us(1_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("ABC", 10, 10, days[0])
    action = CorporateActionIdentity(
        "ABC", "same-day-dividend", "cash_dividend", execution.open_at,
        _source("same-day-source", signal.close_at), "America/New_York",
        ex_date=days[1], record_date=days[1], pay_date=days[1],
        cash_amount=Decimal("0.5"), currency="USD", unit="per_share",
    )
    result = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(
            _input(
                "ABC",
                "us",
                execution,
                corporate_actions=(action,),
                decision_price=10,
            ),
        ),
        target_weights=lambda _: {"ABC": 0.1},
    )
    assert result.receipts[0].cash_change == pytest.approx(5)
    assert result.receipts[0].cash_after == pytest.approx(905)


def test_engine_adjusts_pre_action_decision_price_for_split_and_distribution() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14), date(2026, 7, 15))
    calendar = _calendar(days, "America/New_York")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 22, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)

    split_portfolio = Portfolio.us(10_000, costs=TransactionCostModel())
    split_portfolio.start_session(days[0])
    split_portfolio.buy("ABC", 10, 100, days[0])
    split = CorporateActionIdentity(
        "ABC",
        "abc-split-2-for-1",
        "split",
        execution.open_at,
        _source("abc-split-source", signal.close_at),
        "America/New_York",
        ex_date=days[1],
        split_ratio=Decimal("2"),
    )
    split_result = _run_static_rebalance(
        split_portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(
            _input(
                "ABC",
                "us",
                execution,
                price=50,
                corporate_actions=(split,),
                decision_price=100,
                decision_price_basis="raw_pre_action_per_old_share",
            ),
        ),
        target_weights=lambda _: {"ABC": 1.0},
    )
    split_buy = next(item for item in split_result.receipts if item.side == "buy")
    assert split_buy.requested_shares == 180
    assert split_result.portfolio.positions["ABC"].shares == 200

    distribution_portfolio = Portfolio.us(10_000, costs=TransactionCostModel())
    distribution_portfolio.start_session(days[0])
    distribution_portfolio.buy("ABC", 10, 100, days[0])
    distribution = CorporateActionIdentity(
        "ABC",
        "abc-cash-10",
        "cash_dividend",
        execution.open_at,
        _source("abc-cash-source", signal.close_at),
        "America/New_York",
        ex_date=days[1],
        record_date=days[1],
        pay_date=days[2],
        cash_amount=Decimal("10"),
        currency="USD",
        unit="per_share",
    )
    distribution_input = _input(
        "ABC",
        "us",
        execution,
        price=90,
        corporate_actions=(distribution,),
        decision_price=100,
        decision_price_basis="raw_pre_action_per_old_share",
    )
    distribution_result = _run_static_rebalance(
        distribution_portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(distribution_input,),
        target_weights=lambda _: {"ABC": 1.0},
    )
    distribution_buy = next(
        item for item in distribution_result.receipts if item.side == "buy"
    )
    assert distribution_buy.requested_shares == 101
    assert distribution_result.portfolio.positions["ABC"].shares == 110
    assert distribution_result.portfolio.pending_cash_total == pytest.approx(100)

    for action, execution_price in ((split, 50), (distribution, 90)):
        caller = Portfolio.us(10_000, costs=TransactionCostModel())
        before = deepcopy(caller.__dict__)
        callback_calls = []
        with pytest.raises(
            CorporateActionValuationError,
            match="raw_pre_action_per_old_share",
        ):
            _run_static_rebalance(
                caller,
                calendar,
                signal_session=days[0],
                decision_at=signal.close_at,
                execution_inputs=(
                    _input(
                        "ABC",
                        "us",
                        execution,
                        price=execution_price,
                        corporate_actions=(action,),
                        decision_price=execution_price,
                        decision_price_basis="raw_execution_units",
                    ),
                ),
                target_weights=lambda context: callback_calls.append(context)
                or {"ABC": 1.0},
            )
        assert callback_calls == []
    assert caller.__dict__ == before

    with pytest.raises(CorporateActionValuationError, match="explicit order and unit basis"):
        _run_static_rebalance(
            Portfolio.us(10_000, costs=TransactionCostModel()),
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(
                _input(
                    "ABC",
                    "us",
                    execution,
                    corporate_actions=(split, distribution),
                    decision_price=100,
                ),
            ),
            target_weights=lambda _: {"ABC": 1.0},
        )


def test_a_share_split_changes_shares_cost_and_mark_economics() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(10_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("AAA", 100, 10, days[0])
    split = CorporateActionIdentity(
        "AAA",
        "aaa-split-2-for-1",
        "split",
        execution.open_at,
        _source("aaa-split-source", signal.close_at),
        "Asia/Shanghai",
        ex_date=days[1],
        split_ratio=Decimal("2"),
    )

    result = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(
            _input(
                "AAA",
                "a_share",
                execution,
                price=5,
                corporate_actions=(split,),
                decision_price=10,
                a_share_action_types=("split",),
            ),
        ),
        target_weights=lambda _: {"AAA": 0.1},
    )

    position = result.portfolio.positions["AAA"]
    assert position.shares == 200
    assert position.sellable_shares == 200
    assert position.average_cost == pytest.approx(5)
    assert result.portfolio.nav({"AAA": 5}) == pytest.approx(10_000)
    assert any(item.side == "split" for item in result.receipts)


def test_a_share_cash_dividend_enters_pending_cash_and_preserves_value() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14), date(2026, 7, 15))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(10_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("AAA", 100, 10, days[0])
    distribution = CorporateActionIdentity(
        "AAA",
        "aaa-cash-1",
        "cash_dividend",
        execution.open_at,
        _source("aaa-cash-source", signal.close_at),
        "Asia/Shanghai",
        ex_date=days[1],
        record_date=days[1],
        pay_date=days[2],
        cash_amount=Decimal("1"),
        currency="CNY",
        unit="per_share",
    )

    result = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(
            _input(
                "AAA",
                "a_share",
                execution,
                price=9,
                corporate_actions=(distribution,),
                decision_price=10,
                a_share_action_types=("cash_dividend",),
            ),
        ),
        target_weights=lambda _: {"AAA": 0.09},
    )

    assert result.portfolio.positions["AAA"].shares == 100
    assert result.portfolio.pending_cash_total == pytest.approx(100)
    assert result.portfolio.nav({"AAA": 9}) == pytest.approx(10_000)
    assert any(item.side == "distribution" for item in result.receipts)


def test_a_share_delisting_settles_explicit_recovery_and_removes_position() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(10_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("DEAD", 100, 10, days[0])
    terminal = TerminalAction(
        "dead-a-share-delisting-v1",
        "delisting",
        execution.open_at,
        2.5,
        _source("dead-a-share-delisting-source", signal.close_at),
        execution.session_date,
        (),
    )

    result = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(
            _input(
                "DEAD",
                "a_share",
                execution,
                price=None,
                delisted=True,
                action_types=("delisting",),
                terminal=terminal,
                execution_price_basis="confirmed_no_open_event",
                a_share_action_types=("delisting",),
            ),
        ),
        target_weights=lambda _: {},
    )

    assert "DEAD" not in result.portfolio.positions
    assert result.portfolio.available_cash == pytest.approx(9_250)
    assert result.receipts[0].reason == "terminal_delisting"


def test_invalid_weights_and_late_or_duplicate_actions_leave_caller_unchanged() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14), date(2026, 7, 15))
    calendar = _calendar(days, "America/New_York")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 22, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.us(1_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("ABC", 10, 10, days[0])
    before = deepcopy(portfolio.__dict__)
    late = CorporateActionIdentity(
        "ABC", "late-dividend", "cash_dividend", execution.open_at,
        _source("late-action-source", execution.open_at), "America/New_York",
        ex_date=days[1], record_date=days[1], pay_date=days[2],
        cash_amount=Decimal("0.5"), currency="USD", unit="per_share",
    )
    late_row = _input("ABC", "us", execution, corporate_actions=(late,))

    with pytest.raises(MarketDataError, match="late"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(late_row,),
            target_weights=lambda _: {},
        )
    with pytest.raises(MarketDataError, match="globally unique"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(
                ExecutionInput(**{**late_row.__dict__, "corporate_actions": (late, late)}),
            ),
            target_weights=lambda _: {},
        )
    with pytest.raises(ValueError, match="numeric"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(_input("ABC", "us", execution),),
            target_weights=lambda _: {"ABC": True},
        )
    future_action = CorporateActionIdentity(
        "ABC", "future-intraday-dividend", "cash_dividend", execution.close_at,
        _source("future-intraday-source", signal.close_at), "America/New_York",
        ex_date=days[1], record_date=days[1], pay_date=days[2],
        cash_amount=Decimal("0.5"), currency="USD", unit="per_share",
    )
    with pytest.raises(MarketDataError, match="after execution open"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(
                _input("ABC", "us", execution, corporate_actions=(future_action,)),
            ),
            target_weights=lambda _: {},
        )
    with pytest.raises(MarketDataError, match="unknown US action"):
        _run_static_rebalance(
            Portfolio.us(1_000, costs=TransactionCostModel()),
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(_input("ABC", "us", execution, action_types=("mystery",)),),
            target_weights=lambda _: {},
        )
    assert portfolio.__dict__ == before


def test_requested_shares_use_decision_prices_not_next_open_prices() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(100_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("HOLD", 100, 10, days[0])

    low_open = (
        _input("HOLD", "a_share", execution, price=10, decision_price=10),
        _input("NEW", "a_share", execution, price=10, decision_price=10),
    )
    high_open = (
        _input("HOLD", "a_share", execution, price=25, decision_price=10),
        _input("NEW", "a_share", execution, price=25, decision_price=10),
    )
    arguments = {
        "signal_session": days[0],
        "decision_at": signal.close_at,
        "target_weights": lambda _: {"HOLD": 0.5, "NEW": 0.5},
    }
    low = _run_static_rebalance(
        portfolio,
        calendar,
        execution_inputs=low_open,
        **arguments,
    )
    high = _run_static_rebalance(
        portfolio,
        calendar,
        execution_inputs=high_open,
        **arguments,
    )

    def requested(result):
        return tuple(
            (item.symbol, item.side, item.requested_shares) for item in result.receipts
        )

    assert requested(low) == requested(high)
    assert {item.price for item in low.receipts if item.filled_shares} == {10.0}
    assert {item.price for item in high.receipts if item.filled_shares} == {25.0}
    assert low.portfolio.__dict__ != high.portfolio.__dict__


@pytest.mark.parametrize("bad_price", [0.0, -1.0, float("nan"), float("inf")])
def test_decision_price_must_be_present_finite_positive_and_timely(bad_price) -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(10_000, costs=TransactionCostModel())
    before = deepcopy(portfolio.__dict__)
    base = _input("AAA", "a_share", execution)
    bad = ExecutionInput(**{**base.__dict__, "decision_price": bad_price})

    with pytest.raises(MarketDataError, match="decision price must be finite and positive"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(bad,),
            target_weights=lambda _: {"AAA": 1.0},
        )
    missing = ExecutionInput(
        **{
            **base.__dict__,
            "decision_price": None,
            "decision_price_source": None,
            "decision_price_basis": None,
        }
    )
    callback_calls = []
    with pytest.raises(MarketDataError, match="lacks a qualified decision-time sizing price"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(missing,),
            target_weights=lambda context: callback_calls.append(context) or {"AAA": 1.0},
        )
    assert callback_calls == []
    missing_basis = replace(base, decision_price_basis=None)
    with pytest.raises(MarketDataError, match="price, source, and basis"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(missing_basis,),
            target_weights=lambda context: callback_calls.append(context) or {"AAA": 1.0},
        )
    unknown_basis = replace(base, decision_price_basis="qfq")
    with pytest.raises(MarketDataError, match="basis is unsupported"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(unknown_basis,),
            target_weights=lambda context: callback_calls.append(context) or {"AAA": 1.0},
        )
    assert callback_calls == []
    late = _input(
        "AAA",
        "a_share",
        execution,
        decision_price_available_at=execution.open_at,
    )
    with pytest.raises(MarketDataError, match="unavailable at decision_at"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(late,),
            target_weights=lambda _: {"AAA": 1.0},
        )
    assert portfolio.__dict__ == before


def test_strategy_hashes_are_required_and_bound_to_stage_identity() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(10_000, costs=TransactionCostModel())
    inputs = (_input("AAA", "a_share", execution),)
    arguments = {
        "signal_session": days[0],
        "decision_at": signal.close_at,
        "execution_inputs": inputs,
        "target_weights": lambda _: {"AAA": 0.5},
    }
    baseline = _run_static_rebalance(portfolio, calendar, **arguments)
    definition_changed = _run_static_rebalance(
        portfolio,
        calendar,
        strategy_definition_sha256="1" * 64,
        **arguments,
    )
    adapter_changed = _run_static_rebalance(
        portfolio,
        calendar,
        strategy_adapter_sha256="2" * 64,
        **arguments,
    )

    assert baseline.receipts == definition_changed.receipts == adapter_changed.receipts
    assert len(
        {
            baseline.input_identity_hash,
            definition_changed.input_identity_hash,
            adapter_changed.input_identity_hash,
        }
    ) == 3
    assert len({baseline.stage_hash, definition_changed.stage_hash, adapter_changed.stage_hash}) == 3
    assert baseline.strategy_definition_sha256 == DEFINITION_SHA
    assert baseline.strategy_adapter_sha256 == ADAPTER_SHA

    execution_basis = _run_static_rebalance(
        portfolio,
        calendar,
        **{
            **arguments,
            "execution_inputs": (
                replace(inputs[0], decision_price_basis="raw_execution_units"),
            ),
        },
    )
    assert execution_basis.receipts == baseline.receipts
    assert execution_basis.input_identity_hash != baseline.input_identity_hash
    assert execution_basis.stage_hash != baseline.stage_hash

    called = False

    def callback(_):
        nonlocal called
        called = True
        return {}

    with pytest.raises(ValueError, match="strategy_definition_sha256"):
        _run_static_rebalance(
            portfolio,
            calendar,
            **{**arguments, "target_weights": callback},
            strategy_definition_sha256="A" * 64,
        )
    assert called is False


def test_universe_snapshot_rejects_missing_member_and_lifecycle_drift() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(10_000, costs=TransactionCostModel())
    alive = _input("ALIVE", "a_share", execution)
    delisted = _input("DEAD", "a_share", execution, delisted=True)
    full_inputs = (alive, delisted)
    full_members = ("ALIVE", "DEAD")
    frozen = _snapshot(calendar, execution, signal.close_at, full_inputs, full_members)

    with pytest.raises(MarketDataError, match="member_count mismatch"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(alive,),
            universe_members=("ALIVE",),
            universe_snapshot=frozen,
            target_weights=lambda _: {},
        )

    listed = alive.status_records[0]
    drifted_statuses = (
        replace(listed, value=False),
        *alive.status_records[1:],
    )
    drifted = ExecutionInput(**{**alive.__dict__, "status_records": drifted_statuses})
    alive_snapshot = _snapshot(
        calendar,
        execution,
        signal.close_at,
        (alive,),
        ("ALIVE",),
    )
    with pytest.raises(MarketDataError, match="lifecycle_coverage_sha256 mismatch"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(drifted,),
            universe_members=("ALIVE",),
            universe_snapshot=alive_snapshot,
            target_weights=lambda _: {},
        )
    future_statuses = (
        replace(
            alive.status_records[0],
            source=_source("future-listing-revision", execution.open_at),
        ),
        *alive.status_records[1:],
    )
    future = replace(alive, status_records=future_statuses)
    with pytest.raises(MarketDataError, match="future evidence"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(future,),
            universe_members=("ALIVE",),
            universe_snapshot=alive_snapshot,
            target_weights=lambda _: {},
        )


@pytest.mark.parametrize("members", [("A", "B\nC"), ("A\nB", "C"), ("A\tB",)])
def test_universe_member_identifiers_reject_c0_control_characters(members) -> None:
    with pytest.raises(MarketDataError, match="C0 control characters"):
        ordered_members_sha256(members)


def test_control_character_universe_fails_before_lifecycle_or_callback() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(10_000, costs=TransactionCostModel())
    before = deepcopy(portfolio.__dict__)
    invalid = _input("AB", "a_share", execution)
    inputs = (
        replace(
            invalid,
            symbol="A\nB",
            status_records=tuple(
                replace(record, symbol="A\nB") for record in invalid.status_records
            ),
        ),
        _input("C", "a_share", execution),
    )
    snapshot = UniverseSnapshotIdentity(
        market="a_share",
        exchange_id=calendar.identity.exchange_id,
        effective_session=execution.session_date,
        member_count=2,
        ordered_members_sha256="0" * 64,
        lifecycle_coverage_sha256="0" * 64,
        inclusion_rule_sha256=INCLUSION_RULE_SHA,
        calendar_identity_sha256=calendar_identity_sha256(calendar.identity),
        source_identity=_source("invalid-universe", signal.close_at),
    )
    callback_calls = []

    with pytest.raises(MarketDataError, match="C0 control characters"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=inputs,
            universe_members=("A\nB", "C"),
            universe_snapshot=snapshot,
            target_weights=lambda context: callback_calls.append(context) or {},
        )
    assert callback_calls == []
    assert portfolio.__dict__ == before


def test_universe_candidates_are_separate_from_held_maintenance_rows() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(10_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("OLD", 100, 10, days[0])
    old = _input("OLD", "a_share", execution)
    new = _input("NEW", "a_share", execution)
    snapshot = _snapshot(
        calendar,
        execution,
        signal.close_at,
        (old, new),
        ("NEW",),
    )
    seen = []

    result = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(old, new),
        universe_members=("NEW",),
        universe_snapshot=snapshot,
        target_weights=lambda context: seen.append(context.eligible_symbols) or {"NEW": 0.5},
    )

    assert seen == [("NEW",)]
    assert result.receipts[0].symbol == "OLD" and result.receipts[0].side == "sell"
    with pytest.raises(MarketDataError, match="not PIT eligible"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(old, new),
            universe_members=("NEW",),
            universe_snapshot=snapshot,
            target_weights=lambda _: {"OLD": 0.5},
        )
    changed_old = replace(
        old,
        status_records=(replace(old.status_records[0], value=False), *old.status_records[1:]),
    )
    changed_result = _run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(changed_old, new),
        universe_members=("NEW",),
        universe_snapshot=snapshot,
        target_weights=lambda _: {"NEW": 0.5},
    )
    assert changed_result.input_identity_hash != result.input_identity_hash


def test_universe_snapshot_source_is_causal_and_changes_input_identity() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(10_000, costs=TransactionCostModel())
    inputs = (_input("AAA", "a_share", execution),)
    first_snapshot = _snapshot(
        calendar,
        execution,
        signal.close_at,
        inputs,
        ("AAA",),
        source_label="universe-v1",
    )
    second_snapshot = _snapshot(
        calendar,
        execution,
        signal.close_at,
        inputs,
        ("AAA",),
        source_label="universe-v2",
    )
    arguments = {
        "signal_session": days[0],
        "decision_at": signal.close_at,
        "execution_inputs": inputs,
        "universe_members": ("AAA",),
        "target_weights": lambda _: {},
    }
    first = _run_static_rebalance(
        portfolio,
        calendar,
        universe_snapshot=first_snapshot,
        **arguments,
    )
    second = _run_static_rebalance(
        portfolio,
        calendar,
        universe_snapshot=second_snapshot,
        **arguments,
    )
    assert first.receipts == second.receipts == ()
    assert first.input_identity_hash != second.input_identity_hash
    late_snapshot = replace(
        first_snapshot,
        source_identity=_source(
            "universe-late",
            execution.open_at,
            content_sha256=first_snapshot.source_identity.content_sha256,
        ),
    )
    with pytest.raises(MarketDataError, match="unavailable at decision_at"):
        _run_static_rebalance(
            portfolio,
            calendar,
            universe_snapshot=late_snapshot,
            **arguments,
        )

    rows = tuple(
        calendar.session_on(day, as_of=signal.close_at) for day in calendar.session_dates
    )
    other_calendar_identity = replace(
        calendar.identity,
        source_identity=_source(
            "other-calendar-snapshot",
            datetime(2000, 1, 1, tzinfo=UTC),
        ),
    )
    other_calendar = AcceptedSessionCalendar(rows, identity=other_calendar_identity)
    with pytest.raises(MarketDataError, match="calendar identity mismatch"):
        _run_static_rebalance(
            portfolio,
            other_calendar,
            universe_snapshot=first_snapshot,
            **arguments,
        )


def _captured_source(
    label: str,
    available_at: datetime,
    *,
    subject_id: str = "fixture-subject",
) -> SourceIdentity:
    return capture_source_bytes(
        label.encode(),
        publication_evidence=f"published:{label}".encode(),
        source_url="https://example.test/captured-source",
        available_at=available_at,
        retrieved_at=available_at + timedelta(minutes=1),
        revision_id=label,
        source_family_id="captured-fixture-v1",
        provider_id="fixture-provider",
        subject_id=subject_id,
    ).source


def _controlled_calendar(days: tuple[date, ...]) -> AcceptedSessionCalendar:
    timezone_name = "Asia/Shanghai"
    zone = ZoneInfo(timezone_name)
    rows = tuple(
        AcceptedSession(
            day,
            datetime.combine(day, time(9, 30), zone),
            datetime.combine(day, time(15), zone),
            _captured_source(f"calendar-{index}", datetime(2000, 1, 1, tzinfo=UTC)),
            timezone_name,
            exchange_id="XSHG",
        )
        for index, day in enumerate(days)
    )
    dates = tuple(row.session_date for row in rows)
    identity = CalendarIdentity(
        "XSHG",
        timezone_name,
        dates[0],
        dates[-1],
        len(dates),
        session_dates_sha256(dates),
        session_rows_sha256(rows),
        _captured_source("calendar-identity", datetime(2000, 1, 1, tzinfo=UTC)),
    )
    return AcceptedSessionCalendar(rows, identity=identity)


def _controlled_input(
    symbol: str,
    execution: AcceptedSession,
    *,
    observed_session: AcceptedSession | None = None,
    price: float = 10.0,
) -> ExecutionInput:
    zone = ZoneInfo(execution.exchange_timezone)
    observed_day = execution.session_date - timedelta(days=1)
    observed = observed_session or AcceptedSession(
            observed_day,
            datetime.combine(observed_day, time(9, 30), zone),
            datetime.combine(observed_day, time(15), zone),
            _captured_source("capacity-calendar", datetime(2000, 1, 1, tzinfo=UTC)),
            execution.exchange_timezone,
            exchange_id=execution.exchange_id,
        )
    statuses = tuple(
        StatusEvidence(
            f"{symbol}:{kind}",
            symbol,
            kind,  # type: ignore[arg-type]
            value,
            date(1990, 1, 1),
            None,
            execution.exchange_timezone,
            _captured_source(f"status-{kind}", datetime(2000, 1, 1, tzinfo=UTC)),
        )
        for kind, value in (
            ("listed", True),
            ("delisted", False),
            ("st", False),
            ("suspended", False),
        )
    )
    return ExecutionInput(
        symbol=symbol,
        market="a_share",
        open_price=price,
        currency="CNY",
        source=_captured_source("execution-open", execution.open_at),
        status_records=statuses,
        decision_price=price,
        decision_price_source=_captured_source(
            "decision-close",
            datetime(2000, 1, 1, tzinfo=UTC),
        ),
        decision_price_basis="raw_execution_units",
        execution_price_effective_at=execution.open_at,
        execution_price_basis="timestamped_session_open",
        limit_regime="no_limit",
        adjustment_receipt=_adjustment_receipt(symbol, execution.session_date),
        capacity=CapacityObservation(
            symbol,
            observed,
            1_000_000,
            10_000_000,
            "CNY",
            _captured_source("capacity-observation", observed.close_at),
        ),
    )


def _cost_assumptions(
    *,
    spread_bps: float = 2.0,
    gross_only: bool = False,
    adverse_regulatory_fee: float | None = None,
) -> ExecutionCostAssumptions:
    policy = CapacityPolicy(0.1, 0.1, "CNY")
    regulatory_fee = 0.0 if gross_only else 0.0005
    base = CostStressCase(
        0.0,
        0.0,
        spread_bps,
        1.0 if spread_bps else 0.0,
        regulatory_fee,
        1.0,
    )
    adverse = CostStressCase(
        0.0,
        0.0,
        spread_bps * 2,
        3.0 if spread_bps else 0.0,
        (
            regulatory_fee
            if adverse_regulatory_fee is None
            else adverse_regulatory_fee
        ),
        1.0,
    )
    return ExecutionCostAssumptions(
        "fixture-costs-v1",
        "CNY",
        policy,
        base,
        adverse,
        gross_only=gross_only,
    )


def _captured_decision_artifact(
    tmp_path: Path,
    decision_at: datetime,
    *,
    dataset_identity_sha256: str = "d" * 64,
    split_identity_sha256: str = "e" * 64,
    scores: dict[str, float] | None = None,
    minimum_score: float = 0.0,
    name: str = "",
) -> DecisionArtifact:
    feature = tmp_path / f"feature{name}.json"
    definition = tmp_path / f"definition{name}.json"
    adapter = tmp_path / f"adapter{name}.json"
    feature_bytes = (
        json.dumps(
            {"scores": scores or {"AAA": 1.0}, "version": 1},
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode()
    definition_bytes = (
        json.dumps(
            {"minimum_score": minimum_score, "version": 1},
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode()
    adapter_bytes = (
        '{"feature_field":"scores","normalization":"positive_sum",'
        '"transform":"threshold","version":1}\n'
    ).encode()
    feature.write_bytes(feature_bytes)
    definition.write_bytes(definition_bytes)
    adapter.write_bytes(adapter_bytes)
    artifact_sources = tuple(
        capture_source_bytes(
            content,
            publication_evidence=f"published:{label}".encode(),
            source_url=f"https://example.test/{label}",
            available_at=datetime(2000, 1, 1, tzinfo=UTC),
            retrieved_at=datetime(2000, 1, 1, 0, 1, tzinfo=UTC),
            revision_id=f"{label}{name}",
            source_family_id=f"{label}-fixture",
            provider_id="fixture-provider",
            subject_id=f"{label}{name}",
        ).source
        for label, content in (
            ("feature", feature_bytes),
            ("definition", definition_bytes),
            ("adapter", adapter_bytes),
        )
    )
    return capture_decision_artifact(
        feature_snapshot_path=feature,
        strategy_definition_path=definition,
        strategy_adapter_path=adapter,
        feature_source=artifact_sources[0],
        strategy_definition_source=artifact_sources[1],
        strategy_adapter_source=artifact_sources[2],
        decision_at=decision_at,
        dataset_identity_sha256=dataset_identity_sha256,
        split_identity_sha256=split_identity_sha256,
    )


def _controlled_materialization(
    tmp_path: Path,
    calendar: AcceptedSessionCalendar,
    execution: AcceptedSession,
    decision_at: datetime,
    rows: tuple[ExecutionInput, ...],
) -> UniverseMaterialization:
    partition_path = tmp_path / "universe.json"
    partition_bytes = json.dumps(
        [{"symbol": row.symbol} for row in rows],
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    partition_path.write_bytes(partition_bytes)
    rule_path = tmp_path / "universe_rule.json"
    rule_path.write_text(
        '{"include":"lifecycle_eligible","version":1}\n',
        encoding="utf-8",
    )
    partition_source = capture_source_bytes(
        partition_bytes,
        publication_evidence=b"fixture publication receipt",
        source_url="https://example.test/complete-universe-partition",
        available_at=datetime(2000, 1, 1, tzinfo=UTC),
        retrieved_at=datetime(2000, 1, 1, 0, 1, tzinfo=UTC),
        revision_id="complete-universe-v1",
        source_family_id="complete-universe",
        provider_id="fixture-provider",
        subject_id="XSHG",
    ).source
    return materialize_universe_partition(
        partition_path,
        source_identity=partition_source,
        symbol_field="symbol",
        records_by_symbol={row.symbol: row.status_records for row in rows},
        inclusion_rule_path=rule_path,
        market="a_share",
        calendar_identity=calendar.identity,
        session=execution,
        decision_at=decision_at,
    )


def test_family_contract_accepts_two_real_distinct_decision_artifacts(
    tmp_path: Path,
) -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _controlled_calendar(days)
    execution = calendar.next_session(
        days[0],
        as_of=datetime(2026, 7, 20, tzinfo=UTC),
    )
    decision_at = execution.open_at - timedelta(microseconds=1)
    row = _controlled_input(
        "AAA",
        execution,
        observed_session=calendar.session_on(days[0], as_of=decision_at),
    )
    materialization = _controlled_materialization(
        tmp_path,
        calendar,
        execution,
        decision_at,
        (row,),
    )
    dataset = _dataset_manifest(materialization, days[1])
    artifacts = (
        _captured_decision_artifact(
            tmp_path,
            decision_at,
            name="-family-a",
            minimum_score=0.5,
            dataset_identity_sha256=dataset.identity_sha256,
            split_identity_sha256=dataset.split_manifest_sha256,
        ),
        _captured_decision_artifact(
            tmp_path,
            decision_at,
            name="-family-b",
            minimum_score=0.6,
            dataset_identity_sha256=dataset.identity_sha256,
            split_identity_sha256=dataset.split_manifest_sha256,
        ),
    )
    split_manifest = _candidate_split_manifest(days[1])
    split_plan = build_split_evaluation_plan(
        split_manifest,
        holdout_id="real-two-trial-family",
        selected_sample_ids=tuple(
            sample.sample_id for sample in split_manifest.samples
        ),
        method="non_overlapping",
        preregistered_at=decision_at - timedelta(days=1),
    )
    stage_plan = create_stage_plan((days[0],))
    costs = _cost_assumptions()
    family = capture_family_contract(
        multiplicity_family_id="real-family",
        holdout_id=split_plan.holdout_id,
        dataset_sha256=dataset.identity_sha256,
        split_sha256=dataset.split_manifest_sha256,
        stage_plan_sha256=stage_plan.plan_sha256,
        split_evaluation_plan_sha256=split_plan.plan_sha256,
        cost_assumptions_sha256=costs.identity_sha256,
        alpha=0.05,
        family_size=2,
    )
    events = ()
    for index, artifact in enumerate(artifacts):
        trial = capture_trial_config(
            trial_id=f"real-trial-{index}",
            definition_sha256=artifact.strategy_definition_sha256,
            dataset_sha256=dataset.identity_sha256,
            split_sha256=dataset.split_manifest_sha256,
            stage_plan_sha256=stage_plan.plan_sha256,
            split_evaluation_plan_sha256=split_plan.plan_sha256,
            ordered_decision_artifact_sha256s=(artifact.artifact_sha256,),
            ordered_universe_materialization_sha256s=(
                materialization.materialization_sha256,
            ),
            cost_assumptions_sha256=costs.identity_sha256,
            max_positions=None,
            parameters={"minimum_score": 0.5 + 0.1 * index},
        )
        events = preregister_trial(
            events,
            family_contract=family,
            trial_config=trial,
            split_evaluation_plan=split_plan,
            preregistered_at=decision_at - timedelta(days=1),
        )

    assert len({event.trial_config_sha256 for event in events}) == 2
    assert len({event.candidate_run_config_sha256 for event in events}) == 2


def test_real_controlled_multistage_chain_produces_return_artifact(
    tmp_path: Path,
) -> None:
    days = tuple(date(2026, 7, 6) + timedelta(days=index) for index in range(6))
    prices = (10.0, 11.0, 10.5, 12.0, 11.5)
    calendar = _controlled_calendar(days)
    stage_plan = create_stage_plan(days[:5])
    stage_context = genesis_stage(stage_plan)
    portfolio = Portfolio.a_share(100_000, costs=TransactionCostModel())
    results = []

    for index, (signal_session, price) in enumerate(
        zip(stage_plan.sessions, prices, strict=True)
    ):
        execution = calendar.next_session(
            signal_session,
            as_of=datetime(2026, 7, 20, tzinfo=UTC),
        )
        decision_at = execution.open_at - timedelta(microseconds=1)
        row = _controlled_input(
            "AAA",
            execution,
            observed_session=calendar.session_on(
                signal_session,
                as_of=decision_at,
            ),
            price=price,
        )
        stage_directory = tmp_path / f"real-stage-{index}"
        stage_directory.mkdir()
        materialization = _controlled_materialization(
            stage_directory,
            calendar,
            execution,
            decision_at,
            (row,),
        )
        artifact = _captured_decision_artifact(
            stage_directory,
            decision_at,
            name=f"-stage-{index}",
        )
        cost_assumptions = _cost_assumptions()
        result = run_controlled_stage(
            portfolio,
            calendar,
            signal_session=signal_session,
            decision_at=decision_at,
            execution_inputs=(row,),
            universe_materialization=materialization,
            decision_artifact=artifact,
            stage_context=stage_context,
            cost_assumptions=cost_assumptions,
            cost_case="base",
        )
        assert result.cost_assumptions_sha256 == cost_assumptions.identity_sha256
        assert result.cost_assumptions_json == cost_assumptions.canonical_payload_json
        assert result.cost_case == "base"
        assert result.portfolio.costs == cost_assumptions.base.transaction_cost_model()
        if index == 0:
            adverse = run_controlled_stage(
                portfolio,
                calendar,
                signal_session=signal_session,
                decision_at=decision_at,
                execution_inputs=(row,),
                universe_materialization=materialization,
                decision_artifact=artifact,
                stage_context=stage_context,
                cost_assumptions=cost_assumptions,
                cost_case="adverse",
            )
            assert adverse.cost_case == "adverse"
            assert adverse.portfolio.costs == (
                cost_assumptions.adverse.transaction_cost_model()
            )
            assert adverse.stage_hash != result.stage_hash
        results.append(result)
        portfolio = result.portfolio
        if index + 1 < len(stage_plan.sessions):
            stage_context = next_stage(stage_plan, result)

    frozen_results = tuple(results)
    stage_receipts = tuple(
        load_controlled_stage_receipt(
            serialize_controlled_stage_receipt(
                capture_controlled_stage_receipt(result)
            )
        )
        for result in frozen_results
    )
    final_run = capture_final_run_receipt(stage_plan, stage_receipts)
    return_artifact = capture_return_artifact(
        stage_plan,
        stage_receipts,
        final_run,
    )
    execution_sessions = days[1:]
    split_manifest = build_split_manifest(
        entity_ids=("AAA",) * len(execution_sessions),
        observed_at=execution_sessions,
        label_end_at=execution_sessions,
        fold_ids=("real-controlled-chain",) * len(execution_sessions),
    )
    evaluation_plan = build_split_evaluation_plan(
        split_manifest,
        holdout_id="real-controlled-chain",
        selected_sample_ids=tuple(
            sample.sample_id for sample in split_manifest.samples
        ),
        method="non_overlapping",
        preregistered_at=datetime(2026, 7, 1, tzinfo=UTC),
    )
    evaluation = evaluate_split(
        split_manifest,
        plan=evaluation_plan,
        return_artifact=return_artifact,
    )

    assert tuple(item.signal_session for item in return_artifact.observations) == (
        stage_plan.sessions
    )
    assert tuple(item.session for item in return_artifact.observations) == (
        execution_sessions
    )
    assert evaluation.nominal_n == 5
    tampered = json.loads(serialize_controlled_stage_receipt(stage_receipts[0]))
    tampered["final_nav"] += 1
    with pytest.raises(ValueError, match="differs from replay"):
        load_controlled_stage_receipt(
            json.dumps(tampered, sort_keys=True, separators=(",", ":")).encode()
        )
    with pytest.raises(ValueError, match="engine artifact changed"):
        replace(
            stage_receipts[0],
            engine_artifact_sha256="f" * 64,
        ).verify()


def test_candidate_weights_are_computed_from_frozen_strategy_artifacts(
    tmp_path: Path,
) -> None:
    decision_at = datetime(2026, 7, 13, 7, tzinfo=UTC)
    artifact = _captured_decision_artifact(
        tmp_path,
        decision_at,
        scores={"AAA": 3.0, "BBB": 1.0, "CCC": -5.0},
        name="-derived",
    )

    assert artifact.weights == (("AAA", 0.75), ("BBB", 0.25))
    late_feature_source = capture_source_bytes(
        artifact._feature_snapshot_path.read_bytes(),
        publication_evidence=b"late feature publication",
        source_url="https://example.test/late-feature",
        available_at=decision_at + timedelta(seconds=1),
        retrieved_at=decision_at + timedelta(seconds=2),
        revision_id="late-feature",
        source_family_id="feature-fixture",
        provider_id="fixture-provider",
        subject_id="late-feature",
    ).source
    with pytest.raises(MarketDataError, match="unavailable at decision_at"):
        capture_decision_artifact(
            feature_snapshot_path=artifact._feature_snapshot_path,
            strategy_definition_path=artifact._strategy_definition_path,
            strategy_adapter_path=artifact._strategy_adapter_path,
            feature_source=late_feature_source,
            strategy_definition_source=artifact.strategy_definition_source,
            strategy_adapter_source=artifact.strategy_adapter_source,
            decision_at=decision_at,
            dataset_identity_sha256="d" * 64,
            split_identity_sha256="e" * 64,
        )
    with pytest.raises(TypeError, match="unexpected keyword argument 'weights'"):
        capture_decision_artifact(
            weights={"CCC": 1.0},  # type: ignore[call-arg]
            feature_snapshot_path=tmp_path / "feature-derived.json",
            strategy_definition_path=tmp_path / "definition-derived.json",
            strategy_adapter_path=tmp_path / "adapter-derived.json",
            decision_at=decision_at,
            dataset_identity_sha256="d" * 64,
            split_identity_sha256="e" * 64,
        )


def _dataset_manifest(
    materialization: UniverseMaterialization,
    session: date,
    *,
    cost_assumptions: ExecutionCostAssumptions | None = None,
):
    split_manifest = _candidate_split_manifest(session)
    return build_dataset_manifest(
        dates=(session,),
        frequency="1d-open",
        schema=(("symbol", "VARCHAR"), ("open", "DOUBLE")),
        source_snapshot_sha256s=("1" * 64,),
        universe_snapshot_sha256=materialization.materialization_sha256,
        feature_code_sha256="2" * 64,
        label_code_sha256="3" * 64,
        split_manifest_sha256=split_manifest.manifest_sha256,
        calendar_policy_sha256="4" * 64,
        action_policy_sha256="5" * 64,
        cost_policy_sha256=(
            cost_assumptions or _cost_assumptions()
        ).identity_sha256,
        partition_sha256s=("7" * 64,),
    )


def _candidate_split_manifest(session: date):
    observed = tuple(session - timedelta(days=offset) for offset in range(6, 1, -1))
    return build_split_manifest(
        entity_ids=("AAA",) * len(observed),
        observed_at=observed,
        label_end_at=observed,
        fold_ids=("candidate",) * len(observed),
    )


def _real_controlled_return_fixture(
    tmp_path: Path,
    execution_dates: tuple[date, ...],
    *,
    dataset_identity_sha256: str,
    split_identity_sha256: str,
    cost_assumptions: ExecutionCostAssumptions,
):
    signal_dates = tuple(session - timedelta(days=1) for session in execution_dates)
    calendar_dates = tuple(sorted(set(signal_dates) | set(execution_dates)))
    calendar = _controlled_calendar(calendar_dates)
    stage_plan = create_stage_plan(signal_dates)
    stage_context = genesis_stage(stage_plan)
    portfolio = Portfolio.a_share(
        100_000,
        costs=cost_assumptions.base.transaction_cost_model(),
    )
    portfolio.a_share_stamp_tax_schedule = False
    results = []
    for index, (signal_session, execution_date) in enumerate(
        zip(signal_dates, execution_dates, strict=True)
    ):
        execution = calendar.session_on(
            execution_date,
            as_of=datetime(2026, 7, 20, tzinfo=UTC),
        )
        decision_at = execution.open_at - timedelta(microseconds=1)
        row = _controlled_input(
            "AAA",
            execution,
            observed_session=calendar.session_on(
                signal_session,
                as_of=decision_at,
            ),
            price=10.0 + index,
        )
        stage_directory = tmp_path / f"historical-stage-{index}"
        stage_directory.mkdir(exist_ok=True)
        materialization = _controlled_materialization(
            stage_directory,
            calendar,
            execution,
            decision_at,
            (row,),
        )
        artifact = _captured_decision_artifact(
            stage_directory,
            decision_at,
            name=f"-historical-{index}",
            dataset_identity_sha256=dataset_identity_sha256,
            split_identity_sha256=split_identity_sha256,
        )
        result = run_controlled_stage(
            portfolio,
            calendar,
            signal_session=signal_session,
            decision_at=decision_at,
            execution_inputs=(row,),
            universe_materialization=materialization,
            decision_artifact=artifact,
            stage_context=stage_context,
            cost_assumptions=cost_assumptions,
            cost_case="base",
        )
        results.append(result)
        portfolio = result.portfolio
        if index + 1 < len(signal_dates):
            stage_context = next_stage(stage_plan, result)
    frozen_results = tuple(results)
    stage_receipts = tuple(
        load_controlled_stage_receipt(
            serialize_controlled_stage_receipt(
                capture_controlled_stage_receipt(result)
            )
        )
        for result in frozen_results
    )
    return stage_plan, stage_receipts


def _run_candidate_rebalance(
    tmp_path: Path,
    portfolio: Portfolio,
    calendar: AcceptedSessionCalendar,
    **kwargs,
):
    artifact = kwargs["decision_artifact"]
    if (
        not isinstance(artifact, DecisionArtifact)
        or not isinstance(kwargs["cost_assumptions"], ExecutionCostAssumptions)
        or not isinstance(kwargs["universe_materialization"], UniverseMaterialization)
        or artifact.dataset_identity_sha256
        != kwargs["dataset_manifest"].identity_sha256
        or artifact.split_identity_sha256
        != kwargs["dataset_manifest"].split_manifest_sha256
    ):
        return run_candidate_rebalance(
            portfolio,
            calendar,
            experiment_events=(),
            experiment_manifest=None,  # type: ignore[arg-type]
            experiment_ledger=None,  # type: ignore[arg-type]
            experiment_anchor=None,  # type: ignore[arg-type]
            holdout_event=None,  # type: ignore[arg-type]
            holdout_result_receipt=None,  # type: ignore[arg-type]
            trial_config=None,  # type: ignore[arg-type]
            trial_run_receipt=None,  # type: ignore[arg-type]
            final_run_receipt=None,  # type: ignore[arg-type]
            split_evaluation=None,  # type: ignore[arg-type]
            candidate_run_config=None,  # type: ignore[arg-type]
            **kwargs,
        )
    decision_at = kwargs["decision_at"]
    split_manifest = _candidate_split_manifest(
        kwargs["dataset_manifest"].dates[0],
    )
    split_plan = build_split_evaluation_plan(
        split_manifest,
        holdout_id=f"holdout-{artifact.artifact_sha256[:12]}",
        selected_sample_ids=tuple(
            sample.sample_id for sample in split_manifest.samples
        ),
        method="non_overlapping",
        preregistered_at=decision_at - timedelta(days=1),
    )
    split_dates = tuple(
        sorted(
            {
                sample.observed_at
                for sample in split_manifest.samples
                if type(sample.observed_at) is date
            }
        )
    )
    historical_stage_plan, stage_receipts = _real_controlled_return_fixture(
        tmp_path,
        split_dates,
        dataset_identity_sha256=artifact.dataset_identity_sha256,
        split_identity_sha256=artifact.split_identity_sha256,
        cost_assumptions=kwargs["cost_assumptions"],
    )
    trial_id = f"trial-{artifact.artifact_sha256[:12]}"
    evidence_stage_plan_sha256 = kwargs.pop(
        "evidence_stage_plan_sha256",
        historical_stage_plan.plan_sha256,
    )
    trial_config = capture_trial_config(
        trial_id=trial_id,
        definition_sha256=artifact.strategy_definition_sha256,
        dataset_sha256=kwargs["dataset_manifest"].identity_sha256,
        split_sha256=kwargs["dataset_manifest"].split_manifest_sha256,
        stage_plan_sha256=evidence_stage_plan_sha256,
        split_evaluation_plan_sha256=split_plan.plan_sha256,
        ordered_decision_artifact_sha256s=tuple(
            item.decision_artifact_sha256 for item in stage_receipts
        ),
        ordered_universe_materialization_sha256s=tuple(
            item.universe_materialization_sha256 for item in stage_receipts
        ),
        cost_assumptions_sha256=kwargs["cost_assumptions"].identity_sha256,
        max_positions=kwargs.get("max_positions"),
        parameters={"historical_stages": len(stage_receipts)},
    )
    (
        trial_run_receipt,
        final_run_receipt,
        return_artifact,
        split_evaluation,
    ) = evaluate_frozen_historical_run(
        trial_config=trial_config,
        stage_plan=historical_stage_plan,
        stage_receipts=stage_receipts,
        split_manifest=split_manifest,
        split_evaluation_plan=split_plan,
    )
    replayed_final, replayed_returns, replayed_evaluation = replay_trial_run(
        trial_run_receipt
    )
    assert replayed_final.receipt_sha256 == final_run_receipt.receipt_sha256
    assert replayed_returns.artifact_sha256 == return_artifact.artifact_sha256
    assert replayed_evaluation.evaluation_sha256 == split_evaluation.evaluation_sha256
    prospective_stage_context = kwargs["stage_context"]
    candidate_run_config = capture_candidate_run_config(
        decision_artifact_sha256=artifact.artifact_sha256,
        dataset_identity_sha256=kwargs["dataset_manifest"].identity_sha256,
        split_identity_sha256=kwargs["dataset_manifest"].split_manifest_sha256,
        split_evaluation_plan_sha256=split_plan.plan_sha256,
        stage_plan_sha256=prospective_stage_context.plan_sha256,
        final_stage_index=prospective_stage_context.stage_index,
        cost_assumptions_sha256=kwargs["cost_assumptions"].identity_sha256,
        signal_session=kwargs["signal_session"],
        decision_at=decision_at,
        max_positions=kwargs.get("max_positions"),
    )
    events = preregister_trial(
        (),
        family_contract=capture_family_contract(
            multiplicity_family_id=f"family-{artifact.artifact_sha256[:12]}",
            holdout_id=split_plan.holdout_id,
            dataset_sha256=artifact.dataset_identity_sha256,
            split_sha256=artifact.split_identity_sha256,
            stage_plan_sha256=evidence_stage_plan_sha256,
            split_evaluation_plan_sha256=split_plan.plan_sha256,
            cost_assumptions_sha256=kwargs["cost_assumptions"].identity_sha256,
            alpha=0.05,
            family_size=1,
        ),
        trial_config=trial_config,
        split_evaluation_plan=split_plan,
        preregistered_at=decision_at - timedelta(days=1),
    )
    configured_root = tmp_path / "canonical-quant-data"
    previous_data_root = os.environ.get("QUANT_DATA_ROOT")
    previous_owner_root = os.environ.get("QUANT_EXPERIMENT_OWNER_ROOT")
    previous_project_id = os.environ.get("QUANT_PROJECT_ID")
    os.environ["QUANT_DATA_ROOT"] = str(configured_root)
    os.environ["QUANT_EXPERIMENT_OWNER_ROOT"] = str(
        tmp_path / "experiment-owner"
    )
    os.environ["QUANT_PROJECT_ID"] = "quant-proj-test"
    preregistration_ledger = persist_experiment_ledger(events)
    anchor_available_at = decision_at - timedelta(hours=12)
    anchor_values = {
        "created_at": anchor_available_at.isoformat(),
        "family_size": 1,
        "frozen_at": (decision_at - timedelta(days=1)).isoformat(),
        "holdout_id": split_plan.holdout_id,
        "ledger_event_count": 1,
        "ledger_head_sha256": events[-1].event_sha256,
        "multiplicity_family_id": f"family-{artifact.artifact_sha256[:12]}",
        "parameter_summary_sha256": hashlib.sha256(
            json.dumps(
                (
                    {
                        "definition_sha256": artifact.strategy_definition_sha256,
                        "parameters_json": trial_config.parameters_json,
                        "trial_id": trial_id,
                        "trial_config_sha256": trial_config.config_sha256,
                    },
                ),
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest(),
    }
    anchor_content = json.dumps(
        {
            "schema": "experiment-anchor-v1",
            "observations": [
                {
                    "kind": "experiment_anchor",
                    "subject_id": split_plan.holdout_id,
                    "values": anchor_values,
                }
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    anchor_source = capture_source_bytes(
        anchor_content,
        publication_evidence=b"fixture anchor publication",
        source_url="https://example.test/experiment-anchor",
        available_at=anchor_available_at,
        retrieved_at=anchor_available_at + timedelta(minutes=1),
        revision_id=f"anchor-{artifact.artifact_sha256[:12]}",
        source_family_id="fixture-experiment-anchor",
        provider_id="fixture-provider",
        subject_id=split_plan.holdout_id,
    )
    anchor = capture_family_anchor(
        events,
        holdout_id=split_plan.holdout_id,
        ledger_receipt=preregistration_ledger,
        observation_receipt=parse_provider_observation(
            anchor_source,
            anchor_content,
            observation_kind="experiment_anchor",
            subject_id=split_plan.holdout_id,
        ),
    )
    holdout_receipt = capture_holdout_result(
        trial_id=trial_id,
        holdout_id=split_plan.holdout_id,
        trial_run_receipt=trial_run_receipt,
        final_run_receipt=final_run_receipt,
        split_evaluation=split_evaluation,
        holdout_access_at=decision_at - timedelta(seconds=1),
    )
    events = record_holdout_result(
        events,
        receipt=holdout_receipt,
        multiplicity_method="holm",
        anchor=anchor,
    )
    manifest = freeze_experiment_manifest(events)
    ledger = persist_experiment_ledger(events)
    try:
        return run_candidate_rebalance(
            portfolio,
            calendar,
            experiment_events=events,
            experiment_manifest=manifest,
            experiment_ledger=ledger,
            experiment_anchor=anchor,
            holdout_event=events[-1],
            holdout_result_receipt=holdout_receipt,
            trial_config=trial_config,
            trial_run_receipt=trial_run_receipt,
            final_run_receipt=final_run_receipt,
            candidate_run_config=candidate_run_config,
            split_evaluation=split_evaluation,
            **kwargs,
        )
    finally:
        if previous_data_root is None:
            os.environ.pop("QUANT_DATA_ROOT", None)
        else:
            os.environ["QUANT_DATA_ROOT"] = previous_data_root
        if previous_owner_root is None:
            os.environ.pop("QUANT_EXPERIMENT_OWNER_ROOT", None)
        else:
            os.environ["QUANT_EXPERIMENT_OWNER_ROOT"] = previous_owner_root
        if previous_project_id is None:
            os.environ.pop("QUANT_PROJECT_ID", None)
        else:
            os.environ["QUANT_PROJECT_ID"] = previous_project_id


def test_callable_interface_is_permanently_experimental() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    execution = calendar.session_on(days[1], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    result = _run_static_rebalance(
        Portfolio.a_share(100_000, costs=TransactionCostModel()),
        calendar,
        signal_session=days[0],
        decision_at=execution.open_at - timedelta(minutes=1),
        execution_inputs=(_input("AAA", "a_share", execution),),
        target_weights=lambda _: {"AAA": 1.0},
    )
    assert result.interface_grade == "UNTRUSTED_EXPERIMENT"
    assert result.strategy_candidate_available is False


def test_execution_basis_produces_visible_evidence_grade() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.next_session(days[0], as_of=signal.close_at)
    timestamped_row = _input("AAA", "a_share", execution)
    retrospective_row = _input(
        "AAA",
        "a_share",
        execution,
        execution_price_source_available_at=execution.close_at,
        execution_price_basis="retrospective_daily_bar_open_fill",
    )
    arguments = {
        "signal_session": days[0],
        "decision_at": signal.close_at,
        "target_weights": lambda _: {"AAA": 0.5},
    }
    timestamped = _run_static_rebalance(
        Portfolio.a_share(100_000, costs=TransactionCostModel()),
        calendar,
        execution_inputs=(timestamped_row,),
        **arguments,
    )
    retrospective = _run_static_rebalance(
        Portfolio.a_share(100_000, costs=TransactionCostModel()),
        calendar,
        execution_inputs=(retrospective_row,),
        **arguments,
    )

    assert timestamped.receipts == retrospective.receipts
    assert timestamped.execution_evidence_grade == "TIMESTAMPED_EXECUTION"
    assert retrospective.execution_evidence_grade == "RETROSPECTIVE_EXECUTION"
    assert timestamped.input_identity_hash != retrospective.input_identity_hash
    assert retrospective.strategy_candidate_available is False


def test_suspension_evidence_conflict_fails_before_callback_or_trade() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.next_session(days[0], as_of=signal.close_at)
    portfolio = Portfolio.a_share(10_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("AAA", 100, 10.0, days[0])
    row = replace(
        _input("AAA", "a_share", execution, suspended=True),
        is_suspended=False,
    )
    before = deepcopy(portfolio.__dict__)
    callback_calls: list[object] = []

    with pytest.raises(MarketDataError, match="suspension status conflicts"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(row,),
            target_weights=lambda context: callback_calls.append(context) or {},
        )
    assert callback_calls == []
    assert portfolio.__dict__ == before


def test_applicable_limit_regime_missing_limits_fails_before_callback() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.next_session(days[0], as_of=signal.close_at)
    row = _input("AAA", "a_share", execution, limit_regime="applies")
    callback_calls: list[object] = []

    with pytest.raises(MarketDataError, match="requires both limit fields"):
        _run_static_rebalance(
            Portfolio.a_share(10_000, costs=TransactionCostModel()),
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(row,),
            target_weights=lambda context: callback_calls.append(context) or {},
        )
    assert callback_calls == []


def test_a_share_missing_adjustment_receipt_fails_before_callback() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.next_session(days[0], as_of=signal.close_at)
    row = replace(
        _input("AAA", "a_share", execution),
        adjustment_receipt=None,
    )
    portfolio = Portfolio.a_share(10_000, costs=TransactionCostModel())
    before = deepcopy(portfolio.__dict__)
    callback_calls: list[object] = []

    with pytest.raises(MarketDataError, match="captured adjustment receipt"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(row,),
            target_weights=lambda context: callback_calls.append(context) or {},
        )
    assert callback_calls == []
    assert portfolio.__dict__ == before


def test_a_share_adjusted_prices_cannot_enter_execution_or_portfolio_accounting() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.next_session(days[0], as_of=signal.close_at)
    mixed = _input(
        "AAA",
        "a_share",
        execution,
        adjustment_basis="qfq",
        adjustment_factor="0.9",
    )

    with pytest.raises(MarketDataError, match="require raw price units"):
        _run_static_rebalance(
            Portfolio.a_share(10_000, costs=TransactionCostModel()),
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(mixed,),
            target_weights=lambda _: {},
        )

    adjusted = replace(mixed, decision_price_basis="adjusted_qfq")
    portfolio = Portfolio.a_share(10_000, costs=TransactionCostModel())
    before = deepcopy(portfolio.__dict__)
    callback_calls: list[object] = []
    with pytest.raises(MarketDataError, match="require raw price units"):
        _run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(adjusted,),
            target_weights=lambda context: callback_calls.append(context) or {},
        )
    assert callback_calls == []
    assert portfolio.__dict__ == before


def test_a_share_action_receipt_accepts_raw_actions_but_rejects_duplicates() -> None:
    session = date(2026, 7, 14)
    portfolio = Portfolio.a_share(10_000, costs=TransactionCostModel())
    before = deepcopy(portfolio.__dict__)

    raw_action = _adjustment_receipt(
        "AAA",
        session,
        action_types=("cash_dividend",),
    )
    assert raw_action.action_types == ("cash_dividend",)
    with pytest.raises(MarketDataError, match="sorted, unique"):
        _adjustment_receipt(
            "AAA",
            session,
            price_basis="qfq",
            adjustment_factor="0.9",
            action_types=("split", "split"),
        )
    terminal_declaration = _adjustment_receipt(
        "AAA",
        session,
        action_types=("delisting",),
    )
    assert terminal_declaration.action_types == ("delisting",)
    assert portfolio.__dict__ == before


def test_candidate_interface_uses_frozen_artifact_without_callback(tmp_path: Path) -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _controlled_calendar(days)
    decision_at = calendar.session_on(
        days[1],
        as_of=datetime(2026, 7, 13, 12, tzinfo=UTC),
    ).open_at - timedelta(minutes=1)
    execution = calendar.next_session(days[0], as_of=decision_at)
    row = _controlled_input(
        "AAA",
        execution,
        observed_session=calendar.session_on(days[0], as_of=decision_at),
    )
    materialization = _controlled_materialization(
        tmp_path,
        calendar,
        execution,
        decision_at,
        (row,),
    )
    dataset_manifest = _dataset_manifest(materialization, days[1])
    artifact = _captured_decision_artifact(
        tmp_path,
        decision_at,
        dataset_identity_sha256=dataset_manifest.identity_sha256,
        split_identity_sha256=dataset_manifest.split_manifest_sha256,
    )

    result = _run_candidate_rebalance(
        tmp_path,
        Portfolio.a_share(100_000, costs=TransactionCostModel()),
        calendar,
        signal_session=days[0],
        decision_at=decision_at,
        execution_inputs=(row,),
        universe_materialization=materialization,
        dataset_manifest=dataset_manifest,
        decision_artifact=artifact,
        cost_assumptions=_cost_assumptions(),
        stage_context=genesis_stage(create_stage_plan((days[0],))),
    )

    assert result.interface_grade == "GENERIC_CAPTURE_EXPERIMENT"
    assert result.decision_artifact_sha256 == artifact.artifact_sha256
    assert result.cost_assumptions_sha256 == _cost_assumptions().identity_sha256
    assert result.adverse_final_nav is not None
    assert result.adverse_input_identity_hash is not None
    assert result.adverse_stage_hash is not None
    assert result.base_fx_adjusted_final_nav is not None
    assert result.adverse_fx_adjusted_final_nav is not None
    assert result.strategy_candidate_available is False
    assert result.run_bundle is not None
    payload = serialize_candidate_run_bundle(result.run_bundle)
    loaded_bundle = load_candidate_run_bundle(payload)
    assert loaded_bundle.base_stage_hash == result.stage_hash
    replayed_base, replayed_adverse = replay_candidate_run_bundle(loaded_bundle)
    assert replayed_base.final_nav == result.final_nav
    assert replayed_adverse.final_nav == result.adverse_final_nav
    with pytest.raises(ValueError, match="engine artifact changed"):
        replace(
            result.run_bundle,
            engine_artifact_sha256="f" * 64,
        ).verify()
    bundle_path = tmp_path / "candidate-run-bundle.json"
    bundle_path.write_bytes(payload)
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    replayed = subprocess.check_output(
        [
            sys.executable,
            "-c",
            (
                "from pathlib import Path;"
                "from quant_system.backtest import load_candidate_run_bundle;"
                "print(load_candidate_run_bundle(Path(__import__('sys').argv[1])"
                ".read_bytes()).base_stage_hash)"
            ),
            str(bundle_path),
        ],
        env=environment,
        text=True,
    ).strip()
    assert replayed == result.stage_hash
    final_state = json.loads(result.run_bundle.base_final_portfolio_json)
    final_state["settled_cash"] += 1
    with pytest.raises(ValueError, match="final NAV cannot be replayed"):
        replace(
            result.run_bundle,
            base_final_portfolio_json=json.dumps(
                final_state,
                sort_keys=True,
                separators=(",", ":"),
            ),
        ).verify()
    input_state = json.loads(result.run_bundle.base_input_artifact_json)
    input_state["portfolio"]["settled_cash"] += 1
    with pytest.raises(ValueError, match="input identity cannot be replayed"):
        replace(
            result.run_bundle,
            base_input_artifact_json=json.dumps(
                input_state,
                sort_keys=True,
                separators=(",", ":"),
            ),
        ).verify()
    replay_input = json.loads(result.run_bundle.base_replay_artifact_json)
    portfolio_mapping = replay_input["portfolio"]["state"]["__mapping__"]
    settled_cash = next(
        pair for pair in portfolio_mapping if pair[0] == "settled_cash"
    )
    settled_cash[1] += 1
    forged = replace(
        result.run_bundle,
        base_replay_artifact_json=json.dumps(
            replay_input,
            sort_keys=True,
            separators=(",", ":"),
        ),
    )
    forged = replace(
        forged,
        bundle_sha256=hashlib.sha256(
            event_loop_module._candidate_run_bundle_payload(forged)
        ).hexdigest(),
    )
    with pytest.raises(ValueError, match="execution, portfolio, or NAV replay differs"):
        forged.verify()
    artifact_payloads = list(result.run_bundle.artifact_payloads)
    feature_index = next(
        index
        for index, payload_item in enumerate(artifact_payloads)
        if json.loads(payload_item)["role"] == "decision.feature_snapshot"
    )
    feature_envelope = json.loads(artifact_payloads[feature_index])
    feature = json.loads(base64.b64decode(feature_envelope["content_base64"]))
    feature["scores"] = {"BBB": 1.0}
    feature_bytes = json.dumps(
        feature,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    feature_envelope["content_base64"] = base64.b64encode(feature_bytes).decode()
    feature_envelope["sha256"] = hashlib.sha256(feature_bytes).hexdigest()
    artifact_payloads[feature_index] = json.dumps(
        feature_envelope,
        sort_keys=True,
        separators=(",", ":"),
    )
    forged_qualification = replace(
        result.run_bundle,
        artifact_payloads=tuple(artifact_payloads),
    )
    forged_qualification = replace(
        forged_qualification,
        bundle_sha256=hashlib.sha256(
            event_loop_module._candidate_run_bundle_payload(
                forged_qualification
            )
        ).hexdigest(),
    )
    with pytest.raises(ValueError, match="decision artifact role mapping|decision weights"):
        forged_qualification.verify()

    same_weights_different_definition = _captured_decision_artifact(
        tmp_path,
        decision_at,
        dataset_identity_sha256=dataset_manifest.identity_sha256,
        split_identity_sha256=dataset_manifest.split_manifest_sha256,
        minimum_score=0.5,
        name="-different-definition",
    )
    assert same_weights_different_definition.weights == result.target_weights
    assert same_weights_different_definition.artifact_sha256 != (
        result.decision_artifact_sha256
    )
    with pytest.raises(ValueError, match="prefix is missing or changed"):
        _run_candidate_rebalance(
            tmp_path,
            Portfolio.a_share(100_000, costs=TransactionCostModel()),
            calendar,
            signal_session=days[0],
            decision_at=decision_at,
            execution_inputs=(row,),
            universe_materialization=materialization,
            dataset_manifest=dataset_manifest,
            cost_assumptions=_cost_assumptions(),
            stage_context=genesis_stage(create_stage_plan((days[0],))),
            decision_artifact=same_weights_different_definition,
        )
    os.environ.pop("QUANT_DATA_ROOT", None)


def test_candidate_retrospective_execution_is_research_only(tmp_path: Path) -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _controlled_calendar(days)
    decision_at = calendar.session_on(
        days[1],
        as_of=datetime(2026, 7, 13, 12, tzinfo=UTC),
    ).open_at - timedelta(minutes=1)
    execution = calendar.next_session(days[0], as_of=decision_at)
    row = replace(
        _controlled_input(
            "AAA",
            execution,
            observed_session=calendar.session_on(days[0], as_of=decision_at),
        ),
        source=_captured_source("retrospective-open", execution.close_at),
        execution_price_basis="retrospective_daily_bar_open_fill",
    )
    materialization = _controlled_materialization(
        tmp_path,
        calendar,
        execution,
        decision_at,
        (row,),
    )
    dataset_manifest = _dataset_manifest(materialization, days[1])
    artifact = _captured_decision_artifact(
        tmp_path,
        decision_at,
        dataset_identity_sha256=dataset_manifest.identity_sha256,
        split_identity_sha256=dataset_manifest.split_manifest_sha256,
    )
    result = _run_candidate_rebalance(
        tmp_path,
        Portfolio.a_share(100_000, costs=TransactionCostModel()),
        calendar,
        signal_session=days[0],
        decision_at=decision_at,
        execution_inputs=(row,),
        universe_materialization=materialization,
        dataset_manifest=dataset_manifest,
        decision_artifact=artifact,
        cost_assumptions=_cost_assumptions(),
        stage_context=genesis_stage(create_stage_plan((days[0],))),
    )

    assert result.execution_evidence_grade == "RETROSPECTIVE_EXECUTION"
    assert result.interface_grade == "RETROSPECTIVE_RESEARCH_ONLY"
    assert result.strategy_candidate_available is False


def test_candidate_cost_and_capacity_evidence_is_mandatory(tmp_path: Path) -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _controlled_calendar(days)
    decision_at = calendar.session_on(
        days[1],
        as_of=datetime(2026, 7, 13, 12, tzinfo=UTC),
    ).open_at - timedelta(minutes=1)
    execution = calendar.next_session(days[0], as_of=decision_at)
    row = _controlled_input(
        "AAA",
        execution,
        observed_session=calendar.session_on(days[0], as_of=decision_at),
    )
    materialization = _controlled_materialization(
        tmp_path,
        calendar,
        execution,
        decision_at,
        (row,),
    )
    dataset_manifest = _dataset_manifest(materialization, days[1])
    artifact = _captured_decision_artifact(
        tmp_path,
        decision_at,
        dataset_identity_sha256=dataset_manifest.identity_sha256,
        split_identity_sha256=dataset_manifest.split_manifest_sha256,
    )
    portfolio = Portfolio.a_share(100_000, costs=TransactionCostModel())
    before = deepcopy(portfolio.__dict__)

    with pytest.raises(TypeError, match="ExecutionCostAssumptions"):
        _run_candidate_rebalance(
            tmp_path,
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=decision_at,
            execution_inputs=(row,),
            universe_materialization=materialization,
            dataset_manifest=dataset_manifest,
            decision_artifact=artifact,
            cost_assumptions=None,  # type: ignore[arg-type]
            stage_context=genesis_stage(create_stage_plan((days[0],))),
        )
    with pytest.raises(MarketDataError, match="capacity (evidence|policy)"):
        _run_candidate_rebalance(
            tmp_path,
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=decision_at,
            execution_inputs=(replace(row, capacity=None),),
            universe_materialization=materialization,
            dataset_manifest=dataset_manifest,
            decision_artifact=artifact,
            cost_assumptions=_cost_assumptions(),
            stage_context=genesis_stage(create_stage_plan((days[0],))),
        )
    assert portfolio.__dict__ == before


def test_cost_assumptions_change_candidate_identity_and_gross_grade(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _controlled_calendar(days)
    decision_at = calendar.session_on(
        days[1],
        as_of=datetime(2026, 7, 13, 12, tzinfo=UTC),
    ).open_at - timedelta(minutes=1)
    execution = calendar.next_session(days[0], as_of=decision_at)
    row = _controlled_input(
        "AAA",
        execution,
        observed_session=calendar.session_on(days[0], as_of=decision_at),
    )
    materialization = _controlled_materialization(
        tmp_path,
        calendar,
        execution,
        decision_at,
        (row,),
    )
    observed_cost_models = []
    real_run_static = event_loop_module.run_static_rebalance

    def recording_run_static(portfolio, calendar, **kwargs):
        observed_cost_models.append(
            (portfolio.a_share_stamp_tax_schedule, portfolio.costs.sell_tax_rate)
        )
        return real_run_static(portfolio, calendar, **kwargs)

    monkeypatch.setattr(event_loop_module, "run_static_rebalance", recording_run_static)
    def run_for(costs: ExecutionCostAssumptions, name: str):
        manifest = _dataset_manifest(
            materialization,
            days[1],
            cost_assumptions=costs,
        )
        artifact = _captured_decision_artifact(
            tmp_path,
            decision_at,
            dataset_identity_sha256=manifest.identity_sha256,
            split_identity_sha256=manifest.split_manifest_sha256,
            name=name,
        )
        return _run_candidate_rebalance(
            tmp_path,
            Portfolio.a_share(100_000, costs=TransactionCostModel()),
            calendar,
            signal_session=days[0],
            decision_at=decision_at,
            execution_inputs=(row,),
            universe_materialization=materialization,
            dataset_manifest=manifest,
            decision_artifact=artifact,
            stage_context=genesis_stage(create_stage_plan((days[0],))),
            cost_assumptions=costs,
        )

    base = run_for(
        _cost_assumptions(spread_bps=2, adverse_regulatory_fee=0.001),
        "-base-cost",
    )
    stressed = _cost_assumptions(spread_bps=4, adverse_regulatory_fee=0.001)
    gross = _cost_assumptions(spread_bps=0, gross_only=True)

    assert base.cost_assumptions_sha256 != stressed.identity_sha256
    assert gross.gross_only is True
    assert base.interface_grade == "GENERIC_CAPTURE_EXPERIMENT"
    assert base.strategy_candidate_available is False
    candidate_cost_models = [
        item for item in observed_cost_models if item[0] is False
    ]
    assert candidate_cost_models.count((False, 0.0005)) >= 2
    assert candidate_cost_models.count((False, 0.001)) >= 2


def test_candidate_rejects_partition_manifest_drift_before_mutation(tmp_path: Path) -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _controlled_calendar(days)
    decision_at = calendar.session_on(
        days[1],
        as_of=datetime(2026, 7, 13, 12, tzinfo=UTC),
    ).open_at - timedelta(minutes=1)
    execution = calendar.next_session(days[0], as_of=decision_at)
    row = _controlled_input(
        "AAA",
        execution,
        observed_session=calendar.session_on(days[0], as_of=decision_at),
    )
    materialization = _controlled_materialization(
        tmp_path,
        calendar,
        execution,
        decision_at,
        (row,),
    )
    dataset_manifest = _dataset_manifest(materialization, days[1])
    artifact = _captured_decision_artifact(tmp_path, decision_at)
    portfolio = Portfolio.a_share(100_000, costs=TransactionCostModel())
    before = deepcopy(portfolio.__dict__)

    with pytest.raises(MarketDataError, match="dataset manifest"):
        _run_candidate_rebalance(
            tmp_path,
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=decision_at,
            execution_inputs=(row,),
            universe_materialization=materialization,
            dataset_manifest=dataset_manifest,
            decision_artifact=artifact,
            cost_assumptions=_cost_assumptions(),
            stage_context=genesis_stage(create_stage_plan((days[0],))),
        )
    assert portfolio.__dict__ == before


def test_candidate_interface_rejects_callable_before_mutation(tmp_path: Path) -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _controlled_calendar(days)
    decision_at = calendar.session_on(
        days[1],
        as_of=datetime(2026, 7, 13, 12, tzinfo=UTC),
    ).open_at - timedelta(minutes=1)
    execution = calendar.next_session(days[0], as_of=decision_at)
    row = _controlled_input(
        "AAA",
        execution,
        observed_session=calendar.session_on(days[0], as_of=decision_at),
    )
    portfolio = Portfolio.a_share(100_000, costs=TransactionCostModel())
    before = deepcopy(portfolio.__dict__)
    materialization = _controlled_materialization(
        tmp_path,
        calendar,
        execution,
        decision_at,
        (row,),
    )
    dataset_manifest = _dataset_manifest(materialization, days[1])

    with pytest.raises(TypeError, match="DecisionArtifact"):
        _run_candidate_rebalance(
            tmp_path,
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=decision_at,
            execution_inputs=(row,),
            universe_materialization=materialization,
            dataset_manifest=dataset_manifest,
            decision_artifact=lambda _: {"AAA": 1.0},  # type: ignore[arg-type]
            cost_assumptions=_cost_assumptions(),
            stage_context=genesis_stage(create_stage_plan((days[0],))),
        )
    assert portfolio.__dict__ == before


def test_candidate_interface_detects_adapter_byte_change(tmp_path: Path) -> None:
    decision_at = datetime(2026, 7, 13, 8, tzinfo=UTC)
    artifact = _captured_decision_artifact(tmp_path, decision_at)
    original_identity = artifact.artifact_sha256
    artifact._strategy_adapter_path.write_text("WEIGHT = 0.5\n", encoding="utf-8")

    with pytest.raises(MarketDataError, match="adapter_sha256"):
        artifact.verify_current_bytes()
    assert artifact.artifact_sha256 == original_identity


def test_candidate_interface_rejects_manual_universe_snapshot(tmp_path: Path) -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _controlled_calendar(days)
    decision_at = calendar.session_on(
        days[1],
        as_of=datetime(2026, 7, 13, 12, tzinfo=UTC),
    ).open_at - timedelta(minutes=1)
    execution = calendar.next_session(days[0], as_of=decision_at)
    row = _controlled_input(
        "AAA",
        execution,
        observed_session=calendar.session_on(days[0], as_of=decision_at),
    )
    artifact = _captured_decision_artifact(tmp_path, decision_at)
    portfolio = Portfolio.a_share(100_000, costs=TransactionCostModel())
    before = deepcopy(portfolio.__dict__)
    materialization = _controlled_materialization(
        tmp_path,
        calendar,
        execution,
        decision_at,
        (row,),
    )
    dataset_manifest = _dataset_manifest(materialization, days[1])

    with pytest.raises(TypeError, match="materialize_universe_partition"):
        _run_candidate_rebalance(
            tmp_path,
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=decision_at,
            execution_inputs=(row,),
            universe_materialization=_snapshot(  # type: ignore[arg-type]
                calendar,
                execution,
                decision_at,
                (row,),
                ("AAA",),
            ),
            dataset_manifest=dataset_manifest,
            decision_artifact=artifact,
            cost_assumptions=_cost_assumptions(),
            stage_context=genesis_stage(create_stage_plan((days[0],))),
        )
    assert portfolio.__dict__ == before


def test_universe_materialization_requires_complete_source_partition(tmp_path: Path) -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _controlled_calendar(days)
    decision_at = calendar.session_on(
        days[1],
        as_of=datetime(2026, 7, 13, 12, tzinfo=UTC),
    ).open_at - timedelta(minutes=1)
    execution = calendar.next_session(days[0], as_of=decision_at)
    observed = calendar.session_on(days[0], as_of=decision_at)
    active = _controlled_input("AAA", execution, observed_session=observed)
    delisted = _controlled_input("DEAD", execution, observed_session=observed)
    delisted = replace(
        delisted,
        status_records=tuple(
            replace(record, value=True) if record.kind == "delisted" else record
            for record in delisted.status_records
        ),
    )
    materialization = _controlled_materialization(
        tmp_path,
        calendar,
        execution,
        decision_at,
        (active, delisted),
    )

    assert materialization.members == ("AAA",)
    assert tuple((entry.symbol, entry.exclusion_reason) for entry in materialization.entries) == (
        ("AAA", None),
        ("DEAD", "delisted"),
    )
    with pytest.raises(MarketDataError, match="lifecycle records must cover"):
        materialize_universe_partition(
            materialization._source_partition_path,
            source_identity=materialization.snapshot.source_identity,
            symbol_field="symbol",
            records_by_symbol={
                active.symbol: active.status_records,
            },
            inclusion_rule_path=materialization._inclusion_rule_path,
            market="a_share",
            calendar_identity=calendar.identity,
            session=execution,
            decision_at=decision_at,
        )


def test_universe_materialization_detects_rule_byte_change(tmp_path: Path) -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _controlled_calendar(days)
    decision_at = calendar.session_on(
        days[1],
        as_of=datetime(2026, 7, 13, 12, tzinfo=UTC),
    ).open_at - timedelta(minutes=1)
    execution = calendar.next_session(days[0], as_of=decision_at)
    row = _controlled_input(
        "AAA",
        execution,
        observed_session=calendar.session_on(days[0], as_of=decision_at),
    )
    materialization = _controlled_materialization(
        tmp_path,
        calendar,
        execution,
        decision_at,
        (row,),
    )
    materialization._inclusion_rule_path.write_text("INCLUDE = 'all'\n", encoding="utf-8")

    with pytest.raises(MarketDataError, match="inclusion rule"):
        materialization.verify_current_bytes()
