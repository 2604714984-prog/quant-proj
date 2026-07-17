"""Aggregate-only, outcome-free scanner for the frozen salient-return study."""

from __future__ import annotations

from bisect import bisect_left
from collections.abc import Sequence
from datetime import date, datetime, timedelta
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from quant_system.backtest.capacity import CapacityObservation
from quant_system.backtest.event_loop import ExecutionInput
from quant_system.data import AcceptedSession, AcceptedSessionCalendar, SourceIdentity
from quant_system.markets.universe import StatusEvidence
from quant_system.research.salient_return import (
    BENCHMARK_SYMBOL,
    COVERAGE_START,
    DATABASE_SHA256,
    HISTORICAL_CUTOFF,
    INITIAL_CASH_CNY,
    MAX_POSITIONS,
    MIN_DAILY_RETURNS,
    MIN_ELIGIBLE,
    MIN_LISTED_SESSIONS,
    RESEARCH_ID,
    SNAPSHOT_DIGEST,
    SNAPSHOT_ID,
    SNAPSHOT_RECEIPT_FILENAME,
    SNAPSHOT_RECEIPT_SHA256,
    VARIANT_ID,
    DecisionAudit,
    MonthlySignal,
    SalientReturnContractError,
    build_monthly_target,
    common_a_symbol,
    new_strategy_portfolio,
    qfq_execution_limits,
    run_frozen_static_rebalance,
)

CLASSIFICATION = "RETROSPECTIVE_PERSONAL_RESEARCH_GRADE_SECONDARY_NOT_STRICT_PIT"


def _digest(path: Path) -> tuple[str, tuple[int, int, int]]:
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError as exc:
        raise SalientReturnContractError("database path must be a readable regular file") from exc
    with os.fdopen(descriptor, "rb") as stream:
        stat = os.fstat(stream.fileno())
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest(), (stat.st_dev, stat.st_ino, stat.st_size)


def _receipt(path: Path) -> dict[str, object]:
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError as exc:
        raise SalientReturnContractError("snapshot receipt is unreadable") from exc
    with os.fdopen(descriptor, "rb") as stream:
        raw = stream.read()
    if hashlib.sha256(raw).hexdigest() != SNAPSHOT_RECEIPT_SHA256:
        raise SalientReturnContractError("snapshot receipt SHA-256 is not frozen")
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SalientReturnContractError("snapshot receipt is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise SalientReturnContractError("snapshot receipt must be an object")
    return payload


def _parse_day(value: object) -> date:
    try:
        return datetime.strptime(str(value), "%Y%m%d").date()
    except ValueError as exc:
        raise SalientReturnContractError("database contains an invalid date") from exc


def _accepted_calendar(days: tuple[date, ...], content_sha256: str) -> AcceptedSessionCalendar:
    zone = ZoneInfo("Asia/Shanghai")
    available = datetime(2000, 1, 1, tzinfo=zone)
    source = SourceIdentity(
        "https://local.invalid/salient/calendar",
        content_sha256,
        available,
        available,
        "salient-calendar",
    )
    return AcceptedSessionCalendar(
        tuple(
            AcceptedSession(
                day,
                datetime(day.year, day.month, day.day, 9, 30, tzinfo=zone),
                datetime(day.year, day.month, day.day, 15, 0, tzinfo=zone),
                source,
                "Asia/Shanghai",
            )
            for day in days
        )
    )


def _valid_hash(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _execution_panel_complete(row: tuple[Any, ...] | None) -> bool:
    if row is None or len(row) != 9:
        return False
    _, qfq_open, raw_open, is_suspended, is_st, up_limit, down_limit, status, row_hash = row
    if (
        type(is_suspended) is not bool
        or type(is_st) is not bool
        or status != "L"
        or not _valid_hash(row_hash)
    ):
        return False
    numeric = (qfq_open, raw_open, up_limit, down_limit)
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) <= 0.0
        for value in numeric
    ):
        return False
    return float(down_limit) <= float(up_limit)


def _source(kind: str, row_hash: str, available_at: datetime) -> SourceIdentity:
    return SourceIdentity(
        f"https://local.invalid/salient/{kind}",
        row_hash,
        available_at,
        available_at,
        kind,
    )


def _legacy_symbol_master_identity(
    value: object,
    *,
    source: object,
    snapshot_id: object,
    symbol: object,
) -> str:
    components = (source, snapshot_id, symbol)
    if any(
        not isinstance(component, str) or not component or "|" in component
        for component in components
    ):
        raise SalientReturnContractError("legacy symbol-master components are invalid")
    expected = f"{source}|{snapshot_id}|symbol_master|{symbol}|"
    if not isinstance(value, str) or value.count("|") != 4 or value != expected:
        raise SalientReturnContractError("legacy symbol-master row identity differs")
    return value


def _execution_input(
    symbol: str,
    panel: tuple[Any, ...] | None,
    *,
    signal_session: AcceptedSession,
    execution_session: AcceptedSession,
    decision_at: datetime,
    prior_volume: float,
    prior_amount: float,
    prior_hash: str,
) -> ExecutionInput | None:
    if not _execution_panel_complete(panel):
        return None
    assert panel is not None
    _, qfq_open, raw_open, is_suspended, _, up_limit, down_limit, _, row_hash = panel
    adjusted_up, adjusted_down = qfq_execution_limits(
        float(qfq_open), float(raw_open), float(up_limit), float(down_limit)
    )
    status_source = _source("status", prior_hash, decision_at)
    statuses = tuple(
        StatusEvidence(
            f"salient-{kind}",
            symbol,
            kind,
            value,
            date(2000, 1, 1),
            None,
            "Asia/Shanghai",
            status_source,
        )
        for kind, value in (
            ("listed", True),
            ("delisted", False),
            ("st", False),
            ("suspended", False),
        )
    )
    return ExecutionInput(
        symbol,
        "a_share",
        float(qfq_open),
        "CNY",
        _source("open", row_hash, execution_session.open_at),
        statuses,
        is_suspended=is_suspended,
        up_limit=adjusted_up,
        down_limit=adjusted_down,
        capacity=CapacityObservation(
            symbol,
            signal_session,
            prior_volume,
            prior_amount,
            "CNY",
            _source("capacity", prior_hash, decision_at),
        ),
    )


def _master(connection: Any) -> dict[str, tuple[date, date | None]]:
    rows = connection.execute(
        "SELECT ts_code,nullif(list_date,''),nullif(delist_date,''),"
        "source,snapshot_id,row_hash,synthetic_data "
        "FROM a_share.a_share_symbol_master QUALIFY row_number() OVER "
        "(PARTITION BY ts_code ORDER BY ingested_at DESC,snapshot_id DESC)=1"
    ).fetchall()
    result: dict[str, tuple[date, date | None]] = {}
    for symbol, listed, delisted, source, snapshot_id, row_hash, synthetic in rows:
        if not common_a_symbol(symbol):
            continue
        if not listed or synthetic is not False:
            raise SalientReturnContractError("symbol-master identity is incomplete")
        _legacy_symbol_master_identity(
            row_hash,
            source=source,
            snapshot_id=snapshot_id,
            symbol=symbol,
        )
        result[symbol] = (
            _parse_day(listed),
            None if not delisted else _parse_day(delisted),
        )
    return result


def _monthly_signals(
    connection: Any,
    days: tuple[date, ...],
    position: int,
    masters: dict[str, tuple[date, date | None]],
) -> tuple[tuple[MonthlySignal, ...], dict[str, tuple[float, float, str]]]:
    decision = days[position]
    month_start = next(
        index
        for index in range(position + 1)
        if (days[index].year, days[index].month) == (decision.year, decision.month)
    )
    month_days = days[month_start : position + 1]
    if month_start == 0 or len(month_days) < MIN_DAILY_RETURNS:
        raise SalientReturnContractError("complete month history is unavailable")
    start = min(month_start - 1, position - 19)
    required_returns = tuple(day.strftime("%Y%m%d") for day in days[month_start - 1 : position + 1])
    required_amounts = tuple(day.strftime("%Y%m%d") for day in days[position - 19 : position + 1])
    rows = connection.execute(
        "SELECT ts_code,list(trade_date ORDER BY trade_date),"
        "list(qfq_close ORDER BY trade_date),list(amount ORDER BY trade_date),"
        "arg_max(is_st,trade_date),arg_max(is_suspended,trade_date),"
        "arg_max(is_limit_up,trade_date),arg_max(is_limit_down,trade_date),"
        "arg_max(list_status,trade_date),arg_max(vol,trade_date),"
        "arg_max(amount,trade_date),arg_max(row_hash,trade_date),"
        "arg_max(quality_status,trade_date),bool_and(not synthetic_data) "
        "FROM a_share.a_share_canonical_daily_bars "
        "WHERE snapshot_id=? AND trade_date BETWEEN ? AND ? GROUP BY ts_code",
        [SNAPSHOT_ID, days[start].strftime("%Y%m%d"), decision.strftime("%Y%m%d")],
    ).fetchall()
    signals: list[MonthlySignal] = []
    capacity: dict[str, tuple[float, float, str]] = {}
    for row in rows:
        symbol, identity = row[0], masters.get(row[0])
        if not common_a_symbol(symbol) or identity is None:
            continue
        listed_sessions = position - bisect_left(days, identity[0]) + 1
        if (
            listed_sessions < MIN_LISTED_SESSIONS
            or (identity[1] is not None and identity[1] <= decision)
            or any(value is not False for value in row[4:8])
            or row[8] != "L"
            or row[12] != CLASSIFICATION
            or row[13] is not True
            or not _valid_hash(row[11])
        ):
            continue
        volume, amount = row[9], row[10]
        if (
            isinstance(volume, bool)
            or not isinstance(volume, (int, float))
            or not math.isfinite(float(volume))
            or float(volume) < 0.0
            or not float(volume).is_integer()
            or isinstance(amount, bool)
            or not isinstance(amount, (int, float))
            or not math.isfinite(float(amount))
            or float(amount) < 0.0
        ):
            continue
        if len(row[1]) != len(set(row[1])):
            raise SalientReturnContractError("duplicate symbol-date row in snapshot")
        observations = dict(zip(row[1], zip(row[2], row[3]), strict=True))
        if any(day not in observations for day in (*required_returns, *required_amounts)):
            continue
        closes = tuple(observations[day][0] for day in required_returns)
        amounts = tuple(observations[day][1] for day in required_amounts)
        if any(
            value is None
            or isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or float(value) <= 0.0
            for value in closes
        ) or any(
            value is None
            or isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or float(value) < 0.0
            for value in amounts
        ):
            continue
        parsed_closes = tuple(float(value) for value in closes)
        returns = tuple(
            parsed_closes[index] / parsed_closes[index - 1] - 1.0
            for index in range(1, len(parsed_closes))
        )
        signals.append(
            MonthlySignal(
                symbol,
                returns,
                tuple(float(value) for value in amounts),
                listed_sessions,
                True,
                False,
                False,
                False,
                False,
                False,
            )
        )
        capacity[symbol] = (float(volume), float(amount), row[11])
    return tuple(signals), capacity


def _database_audits(
    connection: Any, calendar: AcceptedSessionCalendar
) -> tuple[tuple[DecisionAudit, ...], tuple[date, ...]]:
    days, masters = calendar.session_dates, _master(connection)
    decisions = tuple(
        day
        for position, day in enumerate(days[:-1])
        if position >= MIN_LISTED_SESSIONS
        and day >= date(2020, 1, 1)
        and (day.year, day.month) != (days[position + 1].year, days[position + 1].month)
    )
    audits: list[DecisionAudit] = []
    zone = ZoneInfo("Asia/Shanghai")
    for decision in decisions:
        position = days.index(decision)
        return_count = sum(
            (day.year, day.month) == (decision.year, decision.month) for day in days[: position + 1]
        )
        if return_count < MIN_DAILY_RETURNS:
            audits.append(DecisionAudit(VARIANT_ID, decision, 0, 0, False, False))
            continue
        signal_session = calendar.session_on(decision, as_of=datetime(2030, 1, 1, tzinfo=zone))
        decision_at = signal_session.close_at + timedelta(minutes=30)
        execution_session = calendar.next_session(decision, as_of=decision_at)
        signals, capacity = _monthly_signals(connection, days, position, masters)
        execution_rows = (
            {
                row[0]: row
                for row in connection.execute(
                    "SELECT ts_code,qfq_open,open,is_suspended,is_st,up_limit,"
                    "down_limit,list_status,row_hash "
                    "FROM a_share.a_share_canonical_daily_bars "
                    "WHERE snapshot_id=? AND trade_date=? "
                    "AND ts_code IN (SELECT unnest(?))",
                    [
                        SNAPSHOT_ID,
                        execution_session.session_date.strftime("%Y%m%d"),
                        tuple(item.symbol for item in signals),
                    ],
                ).fetchall()
            }
            if signals
            else {}
        )
        inputs = tuple(
            item
            for signal in signals
            if (
                item := _execution_input(
                    signal.symbol,
                    execution_rows.get(signal.symbol),
                    signal_session=signal_session,
                    execution_session=execution_session,
                    decision_at=decision_at,
                    prior_volume=capacity[signal.symbol][0],
                    prior_amount=capacity[signal.symbol][1],
                    prior_hash=capacity[signal.symbol][2],
                )
            )
            is not None
        )
        _, audit = build_monthly_target(
            signals,
            calendar,
            decision_date=decision,
            decision_at=decision_at,
            execution_inputs=inputs,
        )
        audits.append(audit)
    return tuple(audits), decisions


def _benchmark_probe(
    connection: Any,
    calendar: AcceptedSessionCalendar,
    decisions: tuple[date, ...],
) -> tuple[bool, float, float, int]:
    probes = tuple(
        next(day for day in decisions if day >= start)
        for start in (date(2020, 1, 1), date(2022, 1, 1), date(2024, 1, 1))
    )
    fills: list[bool] = []
    invested: list[float] = []
    capacity_rejections = exceptions = 0
    zone = ZoneInfo("Asia/Shanghai")
    for decision in probes:
        signal = calendar.session_on(decision, as_of=datetime(2030, 1, 1, tzinfo=zone))
        decision_at = signal.close_at + timedelta(minutes=30)
        execution = calendar.next_session(decision, as_of=decision_at)
        rows = connection.execute(
            "SELECT trade_date,qfq_open,open,vol,amount,is_suspended,is_st,"
            "up_limit,down_limit,list_status,quality_status,synthetic_data,row_hash "
            "FROM a_share.a_share_canonical_daily_bars WHERE snapshot_id=? "
            "AND ts_code=? AND trade_date IN (?,?) ORDER BY trade_date",
            [
                SNAPSHOT_ID,
                BENCHMARK_SYMBOL,
                decision.strftime("%Y%m%d"),
                execution.session_date.strftime("%Y%m%d"),
            ],
        ).fetchall()
        if len(rows) != 2 or any(
            row[9] != "L"
            or type(row[5]) is not bool
            or row[6] is not False
            or row[10] != CLASSIFICATION
            or row[11] is not False
            or not _valid_hash(row[12])
            for row in rows
        ):
            exceptions += 1
            continue
        volume, amount = rows[0][3], rows[0][4]
        if (
            any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or float(value) < 0.0
                for value in (volume, amount)
            )
            or not float(volume).is_integer()
        ):
            exceptions += 1
            continue
        qfq_open, raw_open = rows[1][1], rows[1][2]
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or float(value) <= 0.0
            for value in (qfq_open, raw_open)
        ):
            exceptions += 1
            continue
        up_limit, down_limit = rows[1][7], rows[1][8]
        if (up_limit is None) != (down_limit is None):
            exceptions += 1
            continue
        try:
            adjusted_up, adjusted_down = qfq_execution_limits(
                float(qfq_open),
                float(raw_open),
                up_limit,
                down_limit,
            )
        except SalientReturnContractError:
            exceptions += 1
            continue
        status_source = _source("benchmark-status", rows[0][12], decision_at)
        statuses = tuple(
            StatusEvidence(
                f"benchmark-{kind}",
                BENCHMARK_SYMBOL,
                kind,
                value,
                date(2000, 1, 1),
                None,
                "Asia/Shanghai",
                status_source,
            )
            for kind, value in (
                ("listed", True),
                ("delisted", False),
                ("st", False),
                ("suspended", False),
            )
        )
        item = ExecutionInput(
            BENCHMARK_SYMBOL,
            "a_share",
            float(qfq_open),
            "CNY",
            _source("benchmark-open", rows[1][12], execution.open_at),
            statuses,
            is_suspended=rows[1][5],
            up_limit=adjusted_up,
            down_limit=adjusted_down,
            capacity=CapacityObservation(
                BENCHMARK_SYMBOL,
                signal,
                float(volume),
                float(amount),
                "CNY",
                _source("benchmark-capacity", rows[0][12], decision_at),
            ),
        )
        try:
            result = run_frozen_static_rebalance(
                new_strategy_portfolio(),
                calendar,
                signal_session=decision,
                decision_at=decision_at,
                execution_inputs=(item,),
                target_weights={BENCHMARK_SYMBOL: 1.0},
            )
        except (TypeError, ValueError):
            exceptions += 1
            continue
        buy = next((receipt for receipt in result.receipts if receipt.side == "buy"), None)
        filled = buy is not None and buy.filled_shares > 0 and buy.price is not None
        fills.append(filled)
        invested.append(buy.filled_shares * buy.price / INITIAL_CASH_CNY if filled else 0.0)
        capacity_rejections += int(not filled and buy is not None and "capacity" in buy.reason)
    attempts = max(1, len(fills) + exceptions)
    return (
        bool(fills) and all(fills),
        math.fsum(invested) / max(1, len(invested)),
        capacity_rejections / attempts,
        exceptions,
    )


def _preflight_report(
    audits: Sequence[DecisionAudit],
    coverage: tuple[date, date],
    benchmark: tuple[bool, float, float, int],
) -> dict[str, object]:
    frozen = tuple(audits)
    if not frozen or any(
        not isinstance(row, DecisionAudit) or row.variant_id != VARIANT_ID for row in frozen
    ):
        raise SalientReturnContractError("preflight audit identity is invalid")
    if len({row.decision_date for row in frozen}) != len(frozen):
        raise SalientReturnContractError("duplicate decision audit")
    filled, invested, rejected, exceptions = benchmark
    structural = any(
        row.eligible_count < MIN_ELIGIBLE or row.candidate_count < MAX_POSITIONS for row in frozen
    )
    panels = all(row.execution_panel_complete for row in frozen)
    passed = (
        not structural
        and all(row.valid for row in frozen)
        and panels
        and filled
        and exceptions == 0
    )
    return {
        "schema_version": "a-share-salient-return-preflight-v1",
        "research_id": RESEARCH_ID,
        "phase": "OUTCOME_FREE_PREFLIGHT",
        "status": (
            "PREFLIGHT_PASS" if passed else "STRUCTURAL_FAIL" if structural else "INPUT_BLOCKED"
        ),
        "snapshot_id": SNAPSHOT_ID,
        "database_sha256": DATABASE_SHA256,
        "snapshot_digest": SNAPSHOT_DIGEST,
        "classification": CLASSIFICATION,
        "coverage_start": coverage[0].isoformat(),
        "coverage_end": coverage[1].isoformat(),
        "split_decision_counts": {
            "development_2020_2021": sum(row.decision_date <= date(2021, 12, 31) for row in frozen),
            "validation_2022_2023": sum(
                date(2022, 1, 1) <= row.decision_date <= date(2023, 12, 31) for row in frozen
            ),
            "retrospective_holdout_2024_2026h1": sum(
                row.decision_date >= date(2024, 1, 1) for row in frozen
            ),
        },
        "variant_aggregates": {
            VARIANT_ID: {
                "decision_count": len(frozen),
                "minimum_eligible_count": min(row.eligible_count for row in frozen),
                "maximum_eligible_count": max(row.eligible_count for row in frozen),
                "minimum_candidate_count": min(row.candidate_count for row in frozen),
                "maximum_candidate_count": max(row.candidate_count for row in frozen),
                "invalid_decision_count": sum(not row.valid for row in frozen),
            }
        },
        "execution_panels_complete": panels,
        "benchmark_initial_entry_filled": filled,
        "benchmark_invested_ratio": invested,
        "capacity_rejection_ratio": rejected,
        "unexpected_exception_count": exceptions,
        "currency_unit": "CNY",
        "position_unit": "SHARES",
        "post_entry_outcomes_opened": False,
        "embargo_or_prospective_data_accessed": False,
        "security_identifiers_in_report": False,
        "strategy_candidate_available": False,
    }


def run_read_only_preflight(database_path: str | Path) -> dict[str, object]:
    path = Path(database_path)
    before = _digest(path)
    if before[0] != DATABASE_SHA256:
        raise SalientReturnContractError("database SHA-256 is not frozen")
    receipt = _receipt(path.parent / "receipts" / SNAPSHOT_RECEIPT_FILENAME)
    expected_receipt = {
        "post_db_sha256": DATABASE_SHA256,
        "target_snapshot": SNAPSHOT_ID,
        "v5_digest": SNAPSHOT_DIGEST,
        "date_start": COVERAGE_START.strftime("%Y%m%d"),
        "date_end": HISTORICAL_CUTOFF.strftime("%Y%m%d"),
        "volume_unit": "SHARES",
        "amount_unit": "CNY",
        "status": "PUBLISHED_V5_VOLUME_UNIT_SHARES_VERIFIED",
        "strategy_candidate_available": False,
        "strategy_outcomes_opened": False,
    }
    if any(receipt.get(key) != value for key, value in expected_receipt.items()):
        raise SalientReturnContractError("receipt does not bind the frozen snapshot")
    import duckdb

    connection = duckdb.connect(str(path), read_only=True)
    try:
        connection.execute("SET enable_external_access=false")
        snapshot = connection.execute(
            "SELECT count(*),min(trade_date),max(trade_date),"
            "count(DISTINCT quality_status),min(quality_status),"
            "bool_and(not synthetic_data) FROM a_share.a_share_canonical_daily_bars "
            "WHERE snapshot_id=? AND trade_date<=?",
            [SNAPSHOT_ID, HISTORICAL_CUTOFF.strftime("%Y%m%d")],
        ).fetchone()
        if (
            snapshot is None
            or snapshot[0] <= 0
            or receipt.get("target_rows") != snapshot[0]
            or snapshot[3:] != (1, CLASSIFICATION, True)
        ):
            raise SalientReturnContractError("snapshot identity is invalid")
        coverage = (_parse_day(snapshot[1]), _parse_day(snapshot[2]))
        if coverage != (COVERAGE_START, HISTORICAL_CUTOFF):
            raise SalientReturnContractError("snapshot coverage is not frozen")
        calendar_rows = connection.execute(
            "SELECT trade_date,row_hash,synthetic_data "
            "FROM a_share.a_share_trade_calendar WHERE is_open=1 AND trade_date<=? "
            "ORDER BY trade_date,exchange,row_hash",
            [HISTORICAL_CUTOFF.strftime("%Y%m%d")],
        ).fetchall()
        if not calendar_rows or any(
            not _valid_hash(row[1]) or row[2] is not False for row in calendar_rows
        ):
            raise SalientReturnContractError("calendar identity is incomplete")
        days = tuple(sorted({_parse_day(row[0]) for row in calendar_rows}))
        if len(days) < MIN_LISTED_SESSIONS + 2 or days[-1] != HISTORICAL_CUTOFF:
            raise SalientReturnContractError("calendar history is incomplete")
        calendar_digest = hashlib.sha256(
            "|".join(f"{row[0]}:{row[1]}" for row in calendar_rows).encode()
        ).hexdigest()
        calendar = _accepted_calendar(days, calendar_digest)
        audits, decisions = _database_audits(connection, calendar)
        if not audits or not decisions:
            raise SalientReturnContractError("no reproducible month-end decisions")
        report = _preflight_report(
            audits,
            coverage,
            _benchmark_probe(connection, calendar, decisions),
        )
    finally:
        connection.close()
    if _digest(path) != before:
        raise SalientReturnContractError("database changed during read-only preflight")
    return report
