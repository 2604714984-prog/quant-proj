"""Aggregate-only read-only scanner for the frozen Swing Count definition."""
from __future__ import annotations

from bisect import bisect_left
from collections.abc import Sequence
from datetime import date, datetime, timedelta
import hashlib
import json
import math
import os
from pathlib import Path
from statistics import median
from typing import Any
from zoneinfo import ZoneInfo

from quant_system.backtest.capacity import CapacityObservation
from quant_system.backtest.event_loop import ExecutionInput
from quant_system.data import AcceptedSession, AcceptedSessionCalendar, SourceIdentity
from quant_system.markets.universe import StatusEvidence

from quant_system.research.swing_structure import (
    BENCHMARK_SYMBOL,
    COMMON_PREFIXES,
    COVERAGE_START,
    DATABASE_SHA256,
    HISTORICAL_CUTOFF,
    INITIAL_CASH_CNY,
    MAX_POSITIONS,
    MIN_ELIGIBLE,
    MIN_LISTED_SESSIONS,
    MIN_MEDIAN_AMOUNT_CNY,
    RESEARCH_ID,
    SLIPPAGE_SCENARIOS_BPS,
    SNAPSHOT_DIGEST,
    SNAPSHOT_ID,
    SNAPSHOT_RECEIPT_FILENAME,
    SNAPSHOT_RECEIPT_SHA256,
    VARIANTS,
    DecisionAudit,
    SwingStructureContractError,
    _feature_values,
    new_strategy_portfolio,
    qfq_execution_limits,
    run_frozen_static_rebalance,
)


def _digest(path: Path) -> tuple[str, tuple[int, int, int]]:
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError as exc:
        raise SwingStructureContractError(
            "database path must be a readable regular file"
        ) from exc
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
        raise SwingStructureContractError("snapshot receipt is unreadable") from exc
    with os.fdopen(descriptor, "rb") as stream:
        raw = stream.read()
    if hashlib.sha256(raw).hexdigest() != SNAPSHOT_RECEIPT_SHA256:
        raise SwingStructureContractError(
            "snapshot receipt SHA-256 does not match the frozen identity"
        )
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SwingStructureContractError("snapshot receipt is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise SwingStructureContractError("snapshot receipt must be an object")
    return payload


def _parse_day(value: object) -> date:
    try:
        return datetime.strptime(str(value), "%Y%m%d").date()
    except ValueError as exc:
        raise SwingStructureContractError(
            "database contains an invalid trade date"
        ) from exc


def _common_symbol(symbol: str) -> bool:
    if not isinstance(symbol, str) or symbol.count(".") != 1:
        return False
    code, suffix = symbol.split(".")
    return (
        len(code) == 6
        and code.isdigit()
        and suffix in COMMON_PREFIXES
        and code.startswith(COMMON_PREFIXES[suffix])
    )


def _accepted_calendar(
    days: tuple[date, ...], content_sha256: str
) -> AcceptedSessionCalendar:
    zone = ZoneInfo("Asia/Shanghai")
    available = datetime(2000, 1, 1, tzinfo=zone)
    source = SourceIdentity(
        "https://local.invalid/swing/calendar",
        content_sha256,
        available,
        available,
        "swing-calendar",
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


def _execution_panel_complete(row: tuple[Any, ...] | None) -> bool:
    """Check that the shared A-share fill path can classify one next-open row."""
    if row is None or len(row) != 9:
        return False
    _, qfq_open, raw_open, is_suspended, is_st, up_limit, down_limit, status, row_hash = row
    if type(is_suspended) is not bool or type(is_st) is not bool or status != "L":
        return False
    if (
        not isinstance(row_hash, str)
        or len(row_hash) != 64
        or any(character not in "0123456789abcdef" for character in row_hash)
    ):
        return False
    limits = (up_limit, down_limit)
    if any(
        value is not None
        and (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or float(value) <= 0
        )
        for value in limits
    ):
        return False
    if up_limit is None or down_limit is None or down_limit > up_limit:
        return False
    if any(
        value is None
        or isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) <= 0
        for value in (qfq_open, raw_open)
    ):
        return False
    return not (
        (up_limit is not None and float(raw_open) > float(up_limit) + 0.001)
        or (down_limit is not None and float(raw_open) < float(down_limit) - 0.001)
    )


def _database_audits(
    connection: Any, days: tuple[date, ...]
) -> tuple[tuple[DecisionAudit, ...], tuple[date, ...]]:
    master_rows = connection.execute(
        "SELECT ts_code,nullif(list_date,''),nullif(delist_date,''),row_hash,synthetic_data "
        "FROM a_share.a_share_symbol_master QUALIFY row_number() OVER "
        "(PARTITION BY ts_code ORDER BY ingested_at DESC,snapshot_id DESC)=1"
    ).fetchall()
    if any(
        _common_symbol(row[0])
        and (
            not row[1]
            or not isinstance(row[3], str)
            or not row[3]
            or row[4] is not False
        )
        for row in master_rows
    ):
        raise SwingStructureContractError("symbol-master identity is incomplete")
    masters = {
        row[0]: (_parse_day(row[1]), _parse_day(row[2]) if row[2] else None)
        for row in master_rows
        if row[1]
    }
    decisions = tuple(
        day
        for index, day in enumerate(days[:-1])
        if index >= MIN_LISTED_SESSIONS and day.month != days[index + 1].month
    )
    audits: list[DecisionAudit] = []
    for decision in decisions:
        position = bisect_left(days, decision)
        history = tuple(
            day.strftime("%Y%m%d") for day in days[position - 59 : position + 1]
        )
        rows = connection.execute(
            "SELECT ts_code,list(trade_date ORDER BY trade_date),"
            "list(qfq_close ORDER BY trade_date),list(amount ORDER BY trade_date),"
            "arg_max(is_st,trade_date),arg_max(is_suspended,trade_date),"
            "arg_max(is_limit_up,trade_date),arg_max(is_limit_down,trade_date),"
            "arg_max(list_status,trade_date),arg_max(vol,trade_date),"
            "arg_max(amount,trade_date),arg_max(row_hash,trade_date) "
            "FROM a_share.a_share_canonical_daily_bars "
            "WHERE snapshot_id=? AND trade_date BETWEEN ? AND ? GROUP BY ts_code",
            [SNAPSHOT_ID, history[0], history[-1]],
        ).fetchall()
        scores = {variant.variant_id: [] for variant in VARIANTS}
        eligible = {variant.variant_id: 0 for variant in VARIANTS}
        capacity_ready: set[str] = set()
        for row in rows:
            symbol, identity = row[0], masters.get(row[0])
            if not _common_symbol(symbol) or identity is None:
                continue
            listed_sessions = position - bisect_left(days, identity[0]) + 1
            if (
                listed_sessions < MIN_LISTED_SESSIONS
                or (identity[1] is not None and identity[1] <= decision)
                or any(value is not False for value in row[4:8])
                or row[8] != "L"
            ):
                continue
            volume, current_amount, row_hash = row[9:12]
            if (
                isinstance(volume, bool)
                or not isinstance(volume, (int, float))
                or not math.isfinite(float(volume))
                or float(volume) < 0
                or not float(volume).is_integer()
                or isinstance(current_amount, bool)
                or not isinstance(current_amount, (int, float))
                or not math.isfinite(float(current_amount))
                or float(current_amount) < 0
                or not isinstance(row_hash, str)
                or len(row_hash) != 64
                or any(character not in "0123456789abcdef" for character in row_hash)
            ):
                continue
            capacity_ready.add(symbol)
            observations = dict(zip(row[1], zip(row[2], row[3])))
            for variant in VARIANTS:
                required = history[-variant.window_sessions :]
                if any(day not in observations for day in required):
                    continue
                values = tuple(observations[day] for day in required)
                closes = tuple(float(value[0]) for value in values if value[0] is not None)
                amounts = tuple(float(value[1]) for value in values if value[1] is not None)
                if (
                    len(closes) != len(required)
                    or len(amounts) != len(required)
                    or any(not math.isfinite(value) or value <= 0 for value in closes)
                    or any(not math.isfinite(value) or value < 0 for value in amounts)
                ):
                    continue
                if median(amounts[-20:]) < MIN_MEDIAN_AMOUNT_CNY:
                    continue
                eligible[variant.variant_id] += 1
                feature = _feature_values(closes, amounts)
                if feature is not None:
                    scores[variant.variant_id].append((symbol, *feature))
        ranked = {
            key: tuple(sorted(value, key=lambda item: (-item[1], -item[2], item[0])))
            for key, value in scores.items()
        }
        selected = {
            symbol
            for value in ranked.values()
            for symbol, _, _ in value[:MAX_POSITIONS]
        }
        execution_date = days[position + 1].strftime("%Y%m%d")
        executions = (
            {
                row[0]: row
                for row in connection.execute(
                    "SELECT ts_code,qfq_open,open,is_suspended,is_st,up_limit,"
                    "down_limit,list_status,row_hash "
                    "FROM a_share.a_share_canonical_daily_bars "
                    "WHERE snapshot_id=? AND trade_date=? "
                    "AND ts_code IN (SELECT unnest(?))",
                    [SNAPSHOT_ID, execution_date, tuple(selected)],
                ).fetchall()
            }
            if selected
            else {}
        )
        for variant in VARIANTS:
            candidates = ranked[variant.variant_id]
            chosen = candidates[:MAX_POSITIONS]
            complete = len(chosen) == MAX_POSITIONS and all(
                symbol in capacity_ready
                and _execution_panel_complete(executions.get(symbol))
                for symbol, _, _ in chosen
            )
            count = eligible[variant.variant_id]
            audits.append(
                DecisionAudit(
                    variant.variant_id,
                    decision,
                    count,
                    len(candidates),
                    complete,
                    count >= MIN_ELIGIBLE
                    and len(candidates) >= MAX_POSITIONS
                    and complete,
                )
            )
    return tuple(audits), decisions


def _preflight_report(
    audits: Sequence[DecisionAudit],
    coverage: tuple[date, date],
    benchmark: tuple[bool, float, float, int],
) -> dict[str, object]:
    expected = {variant.variant_id for variant in VARIANTS}
    by_date: dict[date, dict[str, DecisionAudit]] = {}
    for row in audits:
        if not isinstance(row, DecisionAudit) or row.variant_id not in expected:
            raise SwingStructureContractError("preflight audit identity is invalid")
        if row.variant_id in by_date.setdefault(row.decision_date, {}):
            raise SwingStructureContractError("duplicate decision-variant audit")
        by_date[row.decision_date][row.variant_id] = row
    if not by_date or any(set(group) != expected for group in by_date.values()):
        raise SwingStructureContractError("every decision requires both frozen variants")
    filled, invested, rejected, exceptions = benchmark
    aggregates = {
        variant.variant_id: {
            "decision_count": len(by_date),
            "minimum_eligible_count": min(
                group[variant.variant_id].eligible_count for group in by_date.values()
            ),
            "maximum_eligible_count": max(
                group[variant.variant_id].eligible_count for group in by_date.values()
            ),
            "minimum_candidate_count": min(
                group[variant.variant_id].candidate_count for group in by_date.values()
            ),
            "maximum_candidate_count": max(
                group[variant.variant_id].candidate_count for group in by_date.values()
            ),
            "invalid_decision_count": sum(
                not group[variant.variant_id].valid for group in by_date.values()
            ),
        }
        for variant in VARIANTS
    }
    panels = all(row.execution_panel_complete for row in audits)
    structural = any(
        row.eligible_count < MIN_ELIGIBLE or row.candidate_count < MAX_POSITIONS
        for row in audits
    )
    passed = (
        not structural
        and all(row.valid for row in audits)
        and panels
        and filled
        and exceptions == 0
    )
    split_counts = {
        "development_2019_2021": sum(day <= date(2021, 12, 31) for day in by_date),
        "validation_2022_2023": sum(
            date(2022, 1, 1) <= day <= date(2023, 12, 31) for day in by_date
        ),
        "retrospective_holdout_2024_2026h1": sum(
            day >= date(2024, 1, 1) for day in by_date
        ),
    }
    return {
        "schema_version": "a-share-swing-structure-preflight-v1",
        "research_id": RESEARCH_ID,
        "phase": "OUTCOME_FREE_PREFLIGHT",
        "status": (
            "PREFLIGHT_PASS"
            if passed
            else "STRUCTURAL_FAIL"
            if structural
            else "INPUT_BLOCKED"
        ),
        "snapshot_id": SNAPSHOT_ID,
        "database_sha256": DATABASE_SHA256,
        "snapshot_digest": SNAPSHOT_DIGEST,
        "classification": "RETROSPECTIVE_PERSONAL_RESEARCH_GRADE_SECONDARY_NOT_STRICT_PIT",
        "coverage_start": coverage[0].isoformat(),
        "coverage_end": coverage[1].isoformat(),
        "split_decision_counts": split_counts,
        "variant_aggregates": aggregates,
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


def _benchmark_probe(
    connection: Any,
    calendar: AcceptedSessionCalendar,
    decisions: tuple[date, ...],
) -> tuple[bool, float, float, int]:
    probes = tuple(
        next(day for day in decisions if day >= start)
        for start in (date(2019, 1, 1), date(2022, 1, 1), date(2024, 1, 1))
    )
    fills: list[bool] = []
    invested: list[float] = []
    rejected = exceptions = 0
    zone = ZoneInfo("Asia/Shanghai")
    for decision in probes:
        signal = calendar.session_on(
            decision, as_of=datetime(2030, 1, 1, tzinfo=zone)
        )
        decision_at = signal.close_at + timedelta(minutes=30)
        execution = calendar.next_session(decision, as_of=decision_at)
        rows = connection.execute(
            "SELECT trade_date,qfq_open,open,vol,amount,is_suspended,is_st,"
            "is_limit_up,is_limit_down,up_limit,down_limit,list_status,quality_status,"
            "synthetic_data,row_hash FROM a_share.a_share_canonical_daily_bars WHERE snapshot_id=? "
            "AND ts_code=? AND trade_date IN (?,?) ORDER BY trade_date",
            [
                SNAPSHOT_ID,
                BENCHMARK_SYMBOL,
                decision.strftime("%Y%m%d"),
                execution.session_date.strftime("%Y%m%d"),
            ],
        ).fetchall()
        if len(rows) != 2:
            exceptions += len(SLIPPAGE_SCENARIOS_BPS)
            continue
        valid_rows = all(
            row[11] == "L"
            and row[6] is False
            and type(row[5]) is bool
            and (
                (row[7] is False and row[8] is False)
                or (
                    row[7] is None
                    and row[8] is None
                    and row[9] is None
                    and row[10] is None
                )
            )
            and row[12]
            == "RETROSPECTIVE_PERSONAL_RESEARCH_GRADE_SECONDARY_NOT_STRICT_PIT"
            and row[13] is False
            and isinstance(row[14], str)
            and len(row[14]) == 64
            and all(character in "0123456789abcdef" for character in row[14])
            for row in rows
        )
        volume, amount = rows[0][3], rows[0][4]
        if (
            not valid_rows
            or rows[0][5] is not False
            or isinstance(volume, bool)
            or not isinstance(volume, (int, float))
            or not math.isfinite(float(volume))
            or float(volume) < 0
            or not float(volume).is_integer()
            or isinstance(amount, bool)
            or not isinstance(amount, (int, float))
            or not math.isfinite(float(amount))
            or float(amount) < 0
        ):
            exceptions += len(SLIPPAGE_SCENARIOS_BPS)
            continue
        shares = float(volume)
        adjusted_up, adjusted_down = qfq_execution_limits(
            rows[1][1], rows[1][2], rows[1][9], rows[1][10]
        )
        source = SourceIdentity(
            "https://local.invalid/swing/benchmark",
            rows[1][14],
            execution.open_at,
            execution.open_at,
            "benchmark-open",
        )
        status_source = SourceIdentity(
            "https://local.invalid/swing/status",
            rows[0][14],
            decision_at,
            decision_at,
            "benchmark-status",
        )
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
        capacity_source = SourceIdentity(
            "https://local.invalid/swing/capacity",
            rows[0][14],
            decision_at,
            decision_at,
            "benchmark-capacity",
        )
        item = ExecutionInput(
            BENCHMARK_SYMBOL,
            "a_share",
            rows[1][1],
            "CNY",
            source,
            statuses,
            is_suspended=rows[1][5],
            up_limit=adjusted_up,
            down_limit=adjusted_down,
            capacity=CapacityObservation(
                BENCHMARK_SYMBOL,
                signal,
                shares,
                rows[0][4],
                "CNY",
                capacity_source,
            ),
        )
        for slippage in SLIPPAGE_SCENARIOS_BPS:
            try:
                result = run_frozen_static_rebalance(
                    new_strategy_portfolio(),
                    calendar,
                    signal_session=decision,
                    decision_at=decision_at,
                    execution_inputs=(item,),
                    target_weights={BENCHMARK_SYMBOL: 1.0},
                    slippage_bps=slippage,
                )
                buy = next(
                    (receipt for receipt in result.receipts if receipt.side == "buy"),
                    None,
                )
                filled = (
                    buy is not None
                    and buy.filled_shares > 0
                    and buy.price is not None
                )
                fills.append(filled)
                invested.append(
                    buy.filled_shares * buy.price / INITIAL_CASH_CNY if filled else 0.0
                )
                rejected += int(
                    not filled and buy is not None and "capacity" in buy.reason
                )
            except (TypeError, ValueError):
                exceptions += 1
    attempts = max(1, len(fills) + exceptions)
    return (
        bool(fills) and all(fills),
        sum(invested) / max(1, len(invested)),
        rejected / attempts,
        exceptions,
    )


def run_read_only_preflight(database_path: str | Path) -> dict[str, object]:
    path = Path(database_path)
    before = _digest(path)
    if before[0] != DATABASE_SHA256:
        raise SwingStructureContractError(
            "database SHA-256 does not match the frozen identity"
        )
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
        raise SwingStructureContractError(
            "snapshot receipt does not bind the frozen database and snapshot"
        )
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
            or snapshot[3:]
            != (
                1,
                "RETROSPECTIVE_PERSONAL_RESEARCH_GRADE_SECONDARY_NOT_STRICT_PIT",
                True,
            )
        ):
            raise SwingStructureContractError(
                "snapshot identity or classification is invalid"
            )
        coverage = (_parse_day(snapshot[1]), _parse_day(snapshot[2]))
        if coverage != (COVERAGE_START, HISTORICAL_CUTOFF):
            raise SwingStructureContractError("snapshot coverage is not frozen")
        calendar_rows = connection.execute(
            "SELECT trade_date,row_hash,synthetic_data "
            "FROM a_share.a_share_trade_calendar WHERE is_open=1 AND trade_date<=? "
            "ORDER BY trade_date,exchange,row_hash",
            [HISTORICAL_CUTOFF.strftime("%Y%m%d")],
        ).fetchall()
        if not calendar_rows or any(
            not isinstance(row[1], str)
            or len(row[1]) != 64
            or any(character not in "0123456789abcdef" for character in row[1])
            or row[2] is not False
            for row in calendar_rows
        ):
            raise SwingStructureContractError("accepted calendar identity is incomplete")
        days = tuple(sorted({_parse_day(row[0]) for row in calendar_rows}))
        if len(days) < MIN_LISTED_SESSIONS + 2 or days[-1] != HISTORICAL_CUTOFF:
            raise SwingStructureContractError("accepted calendar history is incomplete")
        calendar_digest = hashlib.sha256(
            "|".join(f"{row[0]}:{row[1]}" for row in calendar_rows).encode()
        ).hexdigest()
        calendar = _accepted_calendar(days, calendar_digest)
        audits, decisions = _database_audits(connection, days)
        if not audits or not decisions:
            raise SwingStructureContractError("no reproducible month-end decisions")
        report = _preflight_report(
            audits, coverage, _benchmark_probe(connection, calendar, decisions)
        )
    finally:
        connection.close()
    if _digest(path) != before:
        raise SwingStructureContractError("database changed during read-only preflight")
    return report
