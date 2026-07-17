#!/usr/bin/env python3
"""One-use retrospective historical run for the frozen Swing Count screen."""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
from statistics import median
import subprocess
import sys
from typing import Any
from zoneinfo import ZoneInfo

import duckdb
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from quant_system.backtest.blocked_orders import (  # noqa: E402
    BLOCKED_EXIT_REASONS,
    BlockedExitOrder,
    advance_blocked_exit,
    execute_ready_blocked_exit,
)
from quant_system.backtest.capacity import CapacityObservation  # noqa: E402
from quant_system.backtest.event_loop import (  # noqa: E402
    ExecutionInput,
    blocked_exit_from_receipt,
)
from quant_system.data import AcceptedSessionCalendar, SourceIdentity  # noqa: E402
from quant_system.markets.a_share import AShareBar, decide_fill  # noqa: E402
from quant_system.markets.common import FillDecision  # noqa: E402
from quant_system.markets.universe import StatusEvidence  # noqa: E402
from quant_system.research import swing_structure as swing  # noqa: E402


PREFLIGHT_PATH = ROOT / "scripts/run_a_share_swing_structure_preflight.py"
PREFLIGHT_SPEC = importlib.util.spec_from_file_location("swing_preflight", PREFLIGHT_PATH)
if PREFLIGHT_SPEC is None or PREFLIGHT_SPEC.loader is None:  # pragma: no cover
    raise RuntimeError("cannot load the accepted Swing preflight")
preflight = importlib.util.module_from_spec(PREFLIGHT_SPEC)
sys.modules[PREFLIGHT_SPEC.name] = preflight
PREFLIGHT_SPEC.loader.exec_module(preflight)

RUN_ID = "A_SHARE_SWING_STRUCTURE_PARTICIPATION_CONFIRMED_TREND_V1_HISTORICAL_20260718_001"
BASE_COMMIT = "9377d193de3f41ded226628478af158e8644f463"
BASE_TREE = "417be837d975b50ad4e5540fdea6454a0c870eff"
CLASSIFICATION = "RETROSPECTIVE_PERSONAL_RESEARCH_GRADE_SECONDARY_NOT_STRICT_PIT"
QUALITY = CLASSIFICATION
TABLE = "a_share.a_share_canonical_daily_bars"
ZONE = ZoneInfo("Asia/Shanghai")
GATED_SPLITS = (
    ("validation_2022_2023", date(2022, 1, 1), date(2023, 12, 31), 20, 1),
    ("retrospective_holdout_2024_2026h1", date(2024, 1, 1), date(2026, 6, 30), 24, 2),
)
ALPHA = 1 / 120
BOOTSTRAP_DRAWS = 10_000
BLOCK_LENGTH = 3


class HistoricalRunError(ValueError):
    """The one-use historical contract or its frozen input is unusable."""


@dataclass(frozen=True)
class Target:
    signal_date: date
    entry_date: date
    variant_id: str
    symbols: tuple[str, ...]


@dataclass(frozen=True)
class PanelRow:
    symbol: str
    session_date: date
    qfq_open: float
    raw_open: float
    prior_qfq_close: float
    is_suspended: bool
    prior_is_st: bool
    prior_is_suspended: bool
    prior_list_status: str
    raw_up_limit: float | None
    raw_down_limit: float | None
    prior_volume: float
    prior_amount: float
    current_row_hash: str
    prior_row_hash: str


@dataclass(frozen=True)
class CellResult:
    variant_id: str
    split_id: str
    interval_count: int
    invalid_count: int
    mean_monthly_net_active_return: float
    one_sided_p_value: float
    bonferroni_lower_bound: float
    strategy_annualized_net_return: float
    benchmark_annualized_net_return: float
    gates: tuple[tuple[str, bool], ...]


@dataclass
class PreparedRun:
    database_path: Path
    database_identity: tuple[str, tuple[int, int, int]]
    connection: Any
    calendar: AcceptedSessionCalendar
    sessions: tuple[date, ...]
    intervals: dict[str, tuple[tuple[date, date, date], ...]]
    targets: dict[tuple[date, str], Target]
    code_commit: str
    code_tree: str


def _sha(path: Path) -> str:
    digest, _ = preflight._digest(path)
    return digest


def _git_identity() -> tuple[str, str]:
    try:
        commit = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
        ).strip()
        tree = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD^{tree}"], text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise HistoricalRunError("cannot bind the execution code commit") from exc
    return _row_hash(commit, "code commit"), _row_hash(tree, "code tree")


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode() + b"\n"


def _exclusive_write(path: Path, payload: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise HistoricalRunError(f"{path.name} already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0),
        0o600,
    )
    try:
        os.write(descriptor, _canonical(payload))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _finalize_marker(path: Path, payload: Mapping[str, Any]) -> None:
    if not path.is_file() or path.is_symlink():
        raise HistoricalRunError("one-use marker disappeared")
    temporary = path.with_name(f".{path.name}.final-{os.getpid()}")
    _exclusive_write(temporary, payload)
    os.replace(temporary, path)


def _finite(value: object, label: str, *, positive: bool = False) -> float:
    if isinstance(value, bool):
        raise HistoricalRunError(f"{label} must be finite numeric")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise HistoricalRunError(f"{label} must be finite numeric") from exc
    if not math.isfinite(result) or (positive and result <= 0):
        raise HistoricalRunError(f"{label} is invalid")
    return result


def _row_hash(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise HistoricalRunError(f"{label} must be lowercase SHA-256")
    return value


def _status_records(row: PanelRow, decision_at: datetime) -> tuple[StatusEvidence, ...]:
    source = SourceIdentity(
        "https://local.invalid/swing/status",
        row.prior_row_hash,
        decision_at,
        decision_at,
        "swing-prior-status",
    )
    values = (
        ("listed", row.prior_list_status == "L"),
        ("delisted", row.prior_list_status == "D"),
        ("st", row.prior_is_st),
        ("suspended", row.prior_is_suspended),
    )
    return tuple(
        StatusEvidence(
            f"{row.prior_row_hash}-{kind}",
            row.symbol,
            kind,
            value,
            date(2000, 1, 1),
            None,
            "Asia/Shanghai",
            source,
        )
        for kind, value in values
    )


def _execution_input(
    row: PanelRow,
    signal_session: Any,
    execution_session: Any,
    decision_at: datetime,
) -> ExecutionInput:
    upper, lower = swing.qfq_execution_limits(
        row.qfq_open, row.raw_open, row.raw_up_limit, row.raw_down_limit
    )
    source = SourceIdentity(
        "https://local.invalid/swing/open",
        row.current_row_hash,
        execution_session.open_at,
        execution_session.open_at,
        "swing-qfq-open",
    )
    capacity_source = SourceIdentity(
        "https://local.invalid/swing/capacity",
        row.prior_row_hash,
        decision_at,
        decision_at,
        "swing-prior-capacity",
    )
    return ExecutionInput(
        row.symbol,
        "a_share",
        row.qfq_open,
        "CNY",
        source,
        _status_records(row, decision_at),
        is_suspended=row.is_suspended,
        up_limit=upper,
        down_limit=lower,
        capacity=CapacityObservation(
            row.symbol,
            signal_session,
            row.prior_volume,
            row.prior_amount,
            "CNY",
            capacity_source,
        ),
    )


def _calendar_and_sessions(connection: Any) -> tuple[AcceptedSessionCalendar, tuple[date, ...]]:
    rows = connection.execute(
        "SELECT trade_date,row_hash,synthetic_data "
        "FROM a_share.a_share_trade_calendar WHERE is_open=1 AND trade_date<=? "
        "ORDER BY trade_date,exchange,row_hash",
        [swing.HISTORICAL_CUTOFF.strftime("%Y%m%d")],
    ).fetchall()
    if not rows or any(
        row[2] is not False or _row_hash(row[1], "calendar row_hash") != row[1]
        for row in rows
    ):
        raise HistoricalRunError("accepted calendar identity is incomplete")
    sessions = tuple(sorted({preflight._parse_day(row[0]) for row in rows}))
    if sessions[-1] != swing.HISTORICAL_CUTOFF:
        raise HistoricalRunError("calendar exceeds or misses the frozen cutoff")
    digest = hashlib.sha256(
        "|".join(f"{row[0]}:{row[1]}" for row in rows).encode()
    ).hexdigest()
    return preflight._accepted_calendar(sessions, digest), sessions


def _intervals(
    sessions: Sequence[date], start: date, end: date
) -> tuple[tuple[date, date, date], ...]:
    frozen = tuple(sessions)
    positions = {day: index for index, day in enumerate(frozen)}
    first_by_month: dict[tuple[int, int], date] = {}
    for day in frozen:
        first_by_month.setdefault((day.year, day.month), day)
    entries = tuple(day for day in first_by_month.values() if start <= day <= end)
    result: list[tuple[date, date, date]] = []
    for entry, exit_date in zip(entries, entries[1:]):
        if start <= exit_date <= end:
            position = positions[entry]
            if position == 0:
                raise HistoricalRunError("split entry lacks a prior signal session")
            result.append((frozen[position - 1], entry, exit_date))
    return tuple(result)


def _masters(connection: Any) -> dict[str, tuple[date, date | None]]:
    rows = connection.execute(
        "SELECT ts_code,nullif(list_date,''),nullif(delist_date,''),row_hash,synthetic_data "
        "FROM a_share.a_share_symbol_master QUALIFY row_number() OVER "
        "(PARTITION BY ts_code ORDER BY ingested_at DESC,snapshot_id DESC)=1"
    ).fetchall()
    result: dict[str, tuple[date, date | None]] = {}
    for symbol, listed, delisted, row_hash, synthetic in rows:
        if not preflight._common_symbol(symbol):
            continue
        if not listed or synthetic is not False:
            raise HistoricalRunError("symbol-master identity is incomplete")
        _row_hash(row_hash, "symbol-master row_hash")
        result[symbol] = (
            preflight._parse_day(listed),
            None if not delisted else preflight._parse_day(delisted),
        )
    return result


def _load_targets(
    connection: Any,
    sessions: tuple[date, ...],
    required_signals: Sequence[date],
) -> dict[tuple[date, str], Target]:
    positions = {day: index for index, day in enumerate(sessions)}
    masters = _masters(connection)
    targets: dict[tuple[date, str], Target] = {}
    for signal_date in tuple(sorted(set(required_signals))):
        position = positions[signal_date]
        if position < 59 or position + 1 >= len(sessions):
            raise HistoricalRunError("target signal lacks its frozen panel")
        history = sessions[position - 59 : position + 1]
        rows = connection.execute(
            "SELECT ts_code,list(trade_date ORDER BY trade_date),"
            "list(qfq_close ORDER BY trade_date),list(amount ORDER BY trade_date),"
            "arg_max(is_st,trade_date),arg_max(is_suspended,trade_date),"
            "arg_max(is_limit_up,trade_date),arg_max(is_limit_down,trade_date),"
            "arg_max(list_status,trade_date) "
            f"FROM {TABLE} WHERE snapshot_id=? AND trade_date BETWEEN ? AND ? "
            "GROUP BY ts_code",
            [
                swing.SNAPSHOT_ID,
                history[0].strftime("%Y%m%d"),
                history[-1].strftime("%Y%m%d"),
            ],
        ).fetchall()
        scores: dict[str, list[tuple[str, float, float]]] = {
            variant.variant_id: [] for variant in swing.VARIANTS
        }
        eligible = {variant.variant_id: 0 for variant in swing.VARIANTS}
        for row in rows:
            symbol = row[0]
            identity = masters.get(symbol)
            if identity is None:
                continue
            listed_sessions = position - _left_index(sessions, identity[0]) + 1
            if (
                listed_sessions < swing.MIN_LISTED_SESSIONS
                or (identity[1] is not None and identity[1] <= signal_date)
                or any(value is not False for value in row[4:8])
                or row[8] != "L"
            ):
                continue
            observations = dict(zip(row[1], zip(row[2], row[3])))
            for variant in swing.VARIANTS:
                required = tuple(
                    day.strftime("%Y%m%d")
                    for day in history[-variant.window_sessions :]
                )
                if any(day not in observations for day in required):
                    continue
                values = tuple(observations[day] for day in required)
                if any(value[0] is None or value[1] is None for value in values):
                    continue
                closes = tuple(_finite(value[0], "qfq_close", positive=True) for value in values)
                amounts = tuple(_finite(value[1], "amount") for value in values)
                if any(value < 0 for value in amounts) or median(amounts[-20:]) < swing.MIN_MEDIAN_AMOUNT_CNY:
                    continue
                eligible[variant.variant_id] += 1
                feature = swing._feature_values(closes, amounts)
                if feature is not None:
                    scores[variant.variant_id].append((symbol, *feature))
        for variant in swing.VARIANTS:
            ranked = tuple(
                sorted(
                    scores[variant.variant_id],
                    key=lambda item: (-item[1], -item[2], item[0]),
                )
            )
            if eligible[variant.variant_id] < swing.MIN_ELIGIBLE or len(ranked) < swing.MAX_POSITIONS:
                raise HistoricalRunError("preflight target minimum no longer passes")
            target = Target(
                signal_date,
                sessions[position + 1],
                variant.variant_id,
                tuple(item[0] for item in ranked[: swing.MAX_POSITIONS]),
            )
            targets[(signal_date, variant.variant_id)] = target
    return targets


def _left_index(values: Sequence[date], target: date) -> int:
    from bisect import bisect_left

    return bisect_left(values, target)


def _panel(
    connection: Any,
    session_date: date,
    prior_date: date,
    symbols: Sequence[str],
) -> dict[str, PanelRow]:
    frozen = tuple(sorted(set(symbols)))
    if not frozen:
        return {}
    rows = connection.execute(
        f"SELECT c.ts_code,c.qfq_open,c.open,p.qfq_close,c.is_suspended,"
        "p.is_st,p.is_suspended,p.list_status,c.up_limit,c.down_limit,"
        "p.vol,p.amount,c.row_hash,p.row_hash,c.quality_status,c.synthetic_data "
        f"FROM {TABLE} c JOIN {TABLE} p ON p.snapshot_id=c.snapshot_id "
        "AND p.ts_code=c.ts_code AND p.trade_date=? "
        "WHERE c.snapshot_id=? AND c.trade_date=? AND c.trade_date<=? "
        "AND c.ts_code IN (SELECT unnest(?)) ORDER BY c.ts_code",
        [
            prior_date.strftime("%Y%m%d"),
            swing.SNAPSHOT_ID,
            session_date.strftime("%Y%m%d"),
            swing.HISTORICAL_CUTOFF.strftime("%Y%m%d"),
            frozen,
        ],
    ).fetchall()
    if len(rows) != len(frozen):
        raise HistoricalRunError("execution or mark panel has missing symbols")
    result: dict[str, PanelRow] = {}
    for row in rows:
        symbol = row[0]
        if type(row[4]) is not bool or type(row[5]) is not bool or type(row[6]) is not bool:
            raise HistoricalRunError("execution status flags must be boolean")
        if row[7] not in {"L", "D"} or row[14] != QUALITY or row[15] is not False:
            raise HistoricalRunError("execution row classification is invalid")
        volume = _finite(row[10], "prior volume")
        amount = _finite(row[11], "prior amount")
        if volume < 0 or amount < 0 or not volume.is_integer():
            raise HistoricalRunError("capacity units are invalid")
        upper = None if row[8] is None else _finite(row[8], "raw up_limit", positive=True)
        lower = None if row[9] is None else _finite(row[9], "raw down_limit", positive=True)
        if symbol != swing.BENCHMARK_SYMBOL and (upper is None or lower is None):
            raise HistoricalRunError("common-share raw statutory limits are missing")
        result[symbol] = PanelRow(
            symbol,
            session_date,
            _finite(row[1], "qfq_open", positive=True),
            _finite(row[2], "raw open", positive=True),
            _finite(row[3], "prior qfq_close", positive=True),
            row[4],
            row[5],
            row[6],
            row[7],
            upper,
            lower,
            volume,
            amount,
            _row_hash(row[12], "current row_hash"),
            _row_hash(row[13], "prior row_hash"),
        )
    return result


def _marks(portfolio: Any, rows: Mapping[str, PanelRow]) -> dict[str, float]:
    marks: dict[str, float] = {}
    for symbol in portfolio.positions:
        row = rows.get(symbol)
        if row is None:
            raise HistoricalRunError("holding lacks a qualified mark row")
        marks[symbol] = row.prior_qfq_close if row.is_suspended else row.qfq_open
    return marks


def _decision_at(calendar: AcceptedSessionCalendar, signal_date: date) -> datetime:
    signal = calendar.session_on(
        signal_date, as_of=datetime(2030, 1, 1, tzinfo=ZONE)
    )
    return signal.close_at + timedelta(minutes=30)


def _new_blocked_orders(
    orders: dict[str, BlockedExitOrder],
    result: Any,
    calendar: AcceptedSessionCalendar,
) -> None:
    """Advance old orders and create new retry objects from one rebalance."""
    receipts = {
        receipt.symbol: receipt for receipt in result.receipts if receipt.side == "sell"
    }
    for symbol in tuple(orders):
        receipt = receipts.get(symbol)
        if receipt is None:
            continue
        if receipt.filled_shares > 0:
            del orders[symbol]
        elif receipt.reason in BLOCKED_EXIT_REASONS:
            orders[symbol] = advance_blocked_exit(
                orders[symbol],
                session=result.context.execution_session.session_date,
                decision_at=result.context.decision_at,
                decision=FillDecision(False, None, receipt.reason),
            )
        else:
            raise HistoricalRunError("pending blocked exit left the shared lifecycle")
    for receipt in result.receipts:
        if receipt.side != "sell" or receipt.symbol not in result.portfolio.positions:
            continue
        residual = receipt.requested_shares - receipt.filled_shares
        if residual <= 1e-9:
            continue
        if (
            receipt.filled_shares == 0
            and receipt.reason in BLOCKED_EXIT_REASONS
            and receipt.symbol not in orders
        ):
            orders[receipt.symbol] = blocked_exit_from_receipt(
                receipt, result.context, calendar
            )
        elif receipt.symbol not in orders:
            raise HistoricalRunError(
                "residual non-target sell cannot enter the shared retry lifecycle"
            )


def _retry_blocked(
    connection: Any,
    sessions: tuple[date, ...],
    calendar: AcceptedSessionCalendar,
    portfolio: Any,
    orders: dict[str, BlockedExitOrder],
    start: date,
    end: date,
    slippage_bps: float,
    counts: Counter[str],
) -> None:
    positions = {day: index for index, day in enumerate(sessions)}
    for session_date in sessions[positions[start] + 1 : positions[end]]:
        if not orders:
            return
        prior_date = sessions[positions[session_date] - 1]
        rows = _panel(connection, session_date, prior_date, tuple(orders))
        portfolio.start_session(session_date)
        decision_at = _decision_at(calendar, prior_date)
        for symbol in tuple(sorted(orders)):
            if symbol not in portfolio.positions:
                del orders[symbol]
                continue
            row = rows[symbol]
            upper, lower = swing.qfq_execution_limits(
                row.qfq_open, row.raw_open, row.raw_up_limit, row.raw_down_limit
            )
            decision = decide_fill(
                "sell",
                AShareBar(row.qfq_open, row.is_suspended, upper, lower, True),
                slippage_bps=slippage_bps,
            )
            if decision.filled:
                assert decision.price is not None
                shares = orders[symbol].shares
                if (
                    shares > row.prior_volume * 0.01
                    or shares * decision.price > row.prior_amount * 0.01
                ):
                    raise HistoricalRunError("blocked exit fails the frozen capacity cap")
                completed, _ = execute_ready_blocked_exit(
                    orders[symbol],
                    portfolio=portfolio,
                    session=session_date,
                    decision_at=decision_at,
                    decision=decision,
                )
                counts[f"blocked_exit:{decision.reason}:delay_{completed.delay_sessions}"] += 1
                del orders[symbol]
            elif decision.reason in BLOCKED_EXIT_REASONS:
                orders[symbol] = advance_blocked_exit(
                    orders[symbol],
                    session=session_date,
                    decision_at=decision_at,
                    decision=decision,
                )
                counts[f"blocked_exit:{decision.reason}"] += 1
            else:
                raise HistoricalRunError("blocked exit produced an unsupported retry state")


def _simulate_cell(
    connection: Any,
    calendar: AcceptedSessionCalendar,
    sessions: tuple[date, ...],
    targets: Mapping[tuple[date, str], Target],
    *,
    variant_id: str,
    split: tuple[str, date, date, int, int],
    slippage_bps: float,
) -> tuple[tuple[float, ...], tuple[float, ...], dict[str, int], int]:
    split_id, start, end, _, _ = split
    intervals = _intervals(sessions, start, end)
    strategy = swing.new_strategy_portfolio()
    benchmark = swing.new_strategy_portfolio()
    blocked: dict[str, BlockedExitOrder] = {}
    strategy_returns: list[float] = []
    benchmark_returns: list[float] = []
    counts: Counter[str] = Counter()
    invalid = 0
    strategy_stage_hash = "0" * 64
    benchmark_stage_hash = "0" * 64
    positions = {day: index for index, day in enumerate(sessions)}
    for index, (signal_date, entry_date, exit_date) in enumerate(intervals):
        target = targets[(signal_date, variant_id)]
        blocked = {symbol: order for symbol, order in blocked.items() if symbol not in target.symbols}
        entry_symbols = set(target.symbols) | set(strategy.positions) | {swing.BENCHMARK_SYMBOL}
        prior_entry = sessions[positions[entry_date] - 1]
        entry_rows = _panel(connection, entry_date, prior_entry, tuple(entry_symbols))
        start_nav = (
            strategy.nav(_marks(strategy, entry_rows))
            if strategy.positions
            else strategy.available_cash
        )
        benchmark_start = (
            benchmark.nav(_marks(benchmark, entry_rows))
            if benchmark.positions
            else benchmark.available_cash
        )
        decision_at = _decision_at(calendar, signal_date)
        signal = calendar.session_on(signal_date, as_of=decision_at)
        execution = calendar.next_session(signal_date, as_of=decision_at)
        inputs = tuple(
            _execution_input(entry_rows[symbol], signal, execution, decision_at)
            for symbol in sorted(set(target.symbols) | set(strategy.positions))
        )
        result = swing.run_frozen_static_rebalance(
            strategy,
            calendar,
            signal_session=signal_date,
            decision_at=decision_at,
            execution_inputs=inputs,
            target_weights={symbol: 1 / swing.MAX_POSITIONS for symbol in target.symbols},
            slippage_bps=slippage_bps,
            prior_stage_hash=strategy_stage_hash,
        )
        strategy = result.portfolio
        strategy_stage_hash = result.stage_hash
        for receipt in result.receipts:
            counts[f"strategy:{receipt.side}:{receipt.reason}"] += 1
        _new_blocked_orders(blocked, result, calendar)
        if index == 0:
            benchmark_input = _execution_input(
                entry_rows[swing.BENCHMARK_SYMBOL], signal, execution, decision_at
            )
            benchmark_result = swing.run_frozen_static_rebalance(
                benchmark,
                calendar,
                signal_session=signal_date,
                decision_at=decision_at,
                execution_inputs=(benchmark_input,),
                target_weights={swing.BENCHMARK_SYMBOL: 1.0},
                slippage_bps=slippage_bps,
                prior_stage_hash=benchmark_stage_hash,
            )
            benchmark = benchmark_result.portfolio
            benchmark_stage_hash = benchmark_result.stage_hash
            filled = sum(
                receipt.filled_shares
                for receipt in benchmark_result.receipts
                if receipt.side == "buy"
            )
            if filled <= 0:
                raise HistoricalRunError("benchmark initial entry did not fill")
            for receipt in benchmark_result.receipts:
                counts[f"benchmark:{receipt.side}:{receipt.reason}"] += 1
        _retry_blocked(
            connection,
            sessions,
            calendar,
            strategy,
            blocked,
            entry_date,
            exit_date,
            slippage_bps,
            counts,
        )
        prior_exit = sessions[positions[exit_date] - 1]
        exit_rows = _panel(
            connection,
            exit_date,
            prior_exit,
            tuple(set(strategy.positions) | {swing.BENCHMARK_SYMBOL}),
        )
        end_nav = (
            strategy.nav(_marks(strategy, exit_rows))
            if strategy.positions
            else strategy.available_cash
        )
        benchmark_end = benchmark.nav(_marks(benchmark, exit_rows))
        if min(start_nav, end_nav, benchmark_start, benchmark_end) <= 0:
            invalid += 1
            raise HistoricalRunError("nonpositive NAV invalidates the cell")
        strategy_return = end_nav / start_nav - 1
        benchmark_return = benchmark_end / benchmark_start - 1
        if any(
            not math.isfinite(value) or value <= -1
            for value in (strategy_return, benchmark_return)
        ):
            invalid += 1
            raise HistoricalRunError("invalid monthly return")
        strategy_returns.append(strategy_return)
        benchmark_returns.append(benchmark_return)
    if len(strategy_returns) != len(intervals):
        raise HistoricalRunError(f"{split_id} has a missing complete interval")
    return tuple(strategy_returns), tuple(benchmark_returns), dict(counts), invalid


def _annualized(values: Sequence[float]) -> float:
    frozen = tuple(float(value) for value in values)
    if not frozen or any(not math.isfinite(value) or value <= -1 for value in frozen):
        raise HistoricalRunError("annualized return requires finite complete returns")
    return math.prod(1 + value for value in frozen) ** (12 / len(frozen)) - 1


def _bootstrap(
    active_returns: Sequence[float], *, seed: int
) -> tuple[float, float, float]:
    values = np.asarray(tuple(active_returns), dtype=np.float64)
    if values.ndim != 1 or values.size == 0 or not np.isfinite(values).all():
        raise HistoricalRunError("bootstrap requires finite chronological returns")
    observed = float(values.mean())
    centered = values - observed
    rng = np.random.Generator(np.random.PCG64(seed))
    blocks = math.ceil(values.size / BLOCK_LENGTH)
    starts = rng.integers(0, values.size, size=(BOOTSTRAP_DRAWS, blocks))
    offsets = np.arange(BLOCK_LENGTH)
    indices = (starts[..., None] + offsets) % values.size
    samples = centered[indices].reshape(BOOTSTRAP_DRAWS, -1)[:, : values.size]
    bootstrap_means = samples.mean(axis=1)
    p_value = float((1 + np.count_nonzero(bootstrap_means >= observed)) / 10001)
    quantile = float(np.quantile(bootstrap_means, 1 - ALPHA, method="linear"))
    return observed, p_value, observed - quantile


def _evaluate(
    variant: swing.Variant,
    split: tuple[str, date, date, int, int],
    strategy_returns: Sequence[float],
    benchmark_returns: Sequence[float],
    invalid_count: int,
) -> CellResult:
    split_id, _, _, minimum, split_order = split
    strategy_values = tuple(strategy_returns)
    benchmark_values = tuple(benchmark_returns)
    if len(strategy_values) != len(benchmark_values):
        raise HistoricalRunError("strategy and benchmark intervals are misaligned")
    active = tuple(
        strategy_value - benchmark_value
        for strategy_value, benchmark_value in zip(strategy_values, benchmark_values)
    )
    mean_active, p_value, lower = _bootstrap(
        active, seed=20260718 + 100 * variant.order + split_order
    )
    strategy_annualized = _annualized(strategy_values)
    benchmark_annualized = _annualized(benchmark_values)
    gates = (
        ("minimum_complete_interval_count", len(active) >= minimum),
        ("zero_invalid_decisions_marks_and_accounting_failures", invalid_count == 0),
        ("mean_monthly_net_active_return_positive", mean_active > 0),
        ("one_sided_bonferroni_p_value", p_value <= ALPHA),
        ("bonferroni_lower_bound_positive", lower > 0),
        (
            "strategy_annualized_net_return_exceeds_benchmark",
            strategy_annualized > benchmark_annualized,
        ),
    )
    return CellResult(
        variant.variant_id,
        split_id,
        len(active),
        invalid_count,
        mean_active,
        p_value,
        lower,
        strategy_annualized,
        benchmark_annualized,
        gates,
    )


def _historical_status(cells: Sequence[CellResult]) -> tuple[str, tuple[str, ...]]:
    by_variant: dict[str, dict[str, bool]] = {}
    for cell in cells:
        passed = all(value for _, value in cell.gates)
        by_variant.setdefault(cell.variant_id, {})[cell.split_id] = passed
    passing = tuple(
        variant.variant_id
        for variant in swing.VARIANTS
        if all(
            by_variant.get(variant.variant_id, {}).get(split[0], False)
            for split in GATED_SPLITS
        )
    )
    return (
        "HISTORICAL_SCREENING_PASS" if passing else "HISTORICAL_SCREENING_FAIL",
        passing,
    )


def prepare_historical(
    database_path: Path, preflight_report: Mapping[str, Any]
) -> PreparedRun:
    """Finish all identity and target work before the Run ID is consumed."""
    if preflight_report.get("status") != "PREFLIGHT_PASS":
        raise HistoricalRunError("accepted aggregate preflight no longer passes")
    before = preflight._digest(database_path)
    if before[0] != swing.DATABASE_SHA256:
        raise HistoricalRunError("database SHA-256 differs from the frozen identity")
    code_commit, code_tree = _git_identity()
    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        connection.execute("SET enable_external_access=false")
        calendar, sessions = _calendar_and_sessions(connection)
        intervals = {
            split[0]: _intervals(sessions, split[1], split[2]) for split in GATED_SPLITS
        }
        if {key: len(value) for key, value in intervals.items()} != {
            "validation_2022_2023": 23,
            "retrospective_holdout_2024_2026h1": 29,
        }:
            raise HistoricalRunError("frozen split interval counts changed")
        signal_dates = tuple(
            signal for values in intervals.values() for signal, _, _ in values
        )
        targets = _load_targets(connection, sessions, signal_dates)
    except Exception:
        connection.close()
        raise
    return PreparedRun(
        database_path,
        before,
        connection,
        calendar,
        sessions,
        intervals,
        targets,
        code_commit,
        code_tree,
    )


def close_prepared(prepared: PreparedRun) -> None:
    prepared.connection.close()
    if preflight._digest(prepared.database_path) != prepared.database_identity:
        raise HistoricalRunError("database changed during the read-only historical run")


def execute_historical(
    prepared: PreparedRun, preflight_report: Mapping[str, Any]
) -> dict[str, Any]:
    """Open historical returns; caller must consume the Run ID immediately before this."""
    cells: list[CellResult] = []
    diagnostics: dict[str, int] = {}
    execution_counts: Counter[str] = Counter()
    for variant in swing.VARIANTS:
        for split in GATED_SPLITS:
            for slippage in swing.SLIPPAGE_SCENARIOS_BPS:
                strategy_returns, benchmark_returns, counts, invalid = _simulate_cell(
                    prepared.connection,
                    prepared.calendar,
                    prepared.sessions,
                    prepared.targets,
                    variant_id=variant.variant_id,
                    split=split,
                    slippage_bps=slippage,
                )
                execution_counts.update(
                    {
                        f"{variant.variant_id}:{split[0]}:{int(slippage)}bps:{key}": value
                        for key, value in counts.items()
                    }
                )
                if slippage == 20.0:
                    diagnostics[f"{variant.variant_id}:{split[0]}:interval_count"] = len(
                        strategy_returns
                    )
                else:
                    cells.append(
                        _evaluate(
                            variant,
                            split,
                            strategy_returns,
                            benchmark_returns,
                            invalid,
                        )
                    )
    status, passing_variants = _historical_status(cells)
    gate_total = sum(len(cell.gates) for cell in cells)
    gate_passed = sum(value for cell in cells for _, value in cell.gates)
    return {
            "schema_version": "a-share-swing-structure-historical-secondary-result-v1",
            "run_id": RUN_ID,
            "research_id": swing.RESEARCH_ID,
            "status": status,
            "classification": CLASSIFICATION,
            "base_commit": BASE_COMMIT,
            "base_tree": BASE_TREE,
            "code_commit": prepared.code_commit,
            "code_tree": prepared.code_tree,
            "definition_sha256": swing.DEFINITION_SHA256,
            "adapter_sha256": _sha(ROOT / "src/quant_system/research/swing_structure.py"),
            "preflight_sha256": _sha(PREFLIGHT_PATH),
            "runner_sha256": _sha(Path(__file__).resolve()),
            "tests_sha256": _sha(ROOT / "tests/test_run_a_share_swing_structure_once.py"),
            "database_sha256": swing.DATABASE_SHA256,
            "snapshot_id": swing.SNAPSHOT_ID,
            "snapshot_digest": swing.SNAPSHOT_DIGEST,
            "snapshot_receipt_sha256": swing.SNAPSHOT_RECEIPT_SHA256,
            "preflight_status": preflight_report["status"],
            "preflight_aggregates": {
                "split_decision_counts": preflight_report["split_decision_counts"],
                "variant_aggregates": preflight_report["variant_aggregates"],
                "execution_panels_complete": preflight_report[
                    "execution_panels_complete"
                ],
                "benchmark_initial_entry_filled": preflight_report[
                    "benchmark_initial_entry_filled"
                ],
                "benchmark_invested_ratio": preflight_report[
                    "benchmark_invested_ratio"
                ],
                "capacity_rejection_ratio": preflight_report[
                    "capacity_rejection_ratio"
                ],
                "unexpected_exception_count": preflight_report[
                    "unexpected_exception_count"
                ],
            },
            "historical_primary_cell_count": len(cells),
            "gate_counts": {"passed": gate_passed, "total": gate_total},
            "historically_passing_variant_count": len(passing_variants),
            "cells": [asdict(cell) for cell in cells],
            "diagnostic_20bps": diagnostics,
            "execution_counts": dict(sorted(execution_counts.items())),
            "security_identifiers_in_result": False,
            "prospective_forward_outcomes_opened": False,
            "strict_pit_evidence": False,
            "strategy_candidate_available": False,
            "provider_or_network_used": False,
            "database_write_performed": False,
        }


def _terminal_execution_failure(prepared: PreparedRun, error: Exception) -> dict[str, Any]:
    """Publish one aggregate terminal failure after outcome access has begun."""
    return {
        "schema_version": "a-share-swing-structure-historical-secondary-result-v1",
        "run_id": RUN_ID,
        "research_id": swing.RESEARCH_ID,
        "status": "HISTORICAL_SCREENING_FAIL_CLOSED_EXECUTION_ERROR",
        "classification": CLASSIFICATION,
        "base_commit": BASE_COMMIT,
        "base_tree": BASE_TREE,
        "code_commit": prepared.code_commit,
        "code_tree": prepared.code_tree,
        "definition_sha256": swing.DEFINITION_SHA256,
        "runner_sha256": _sha(Path(__file__).resolve()),
        "reason_class": type(error).__name__,
        "gate_counts": None,
        "security_identifiers_in_result": False,
        "prospective_forward_outcomes_opened": False,
        "strict_pit_evidence": False,
        "strategy_candidate_available": False,
        "provider_or_network_used": False,
        "database_write_performed": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--db", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--run-marker", type=Path)
    parser.add_argument("--execute", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.run_id != RUN_ID:
        raise HistoricalRunError("run_id is not the single authorized identity")
    if not args.execute:
        print(
            json.dumps(
                {
                    "status": "DRY_RUN_PLAN",
                    "run_id": RUN_ID,
                    "database_opened": False,
                    "output_written": False,
                    "historical_outcomes_opened": False,
                    "prospective_forward_outcomes_opened": False,
                    "strategy_candidate_available": False,
                },
                sort_keys=True,
            )
        )
        return 0
    if args.db is None or args.output is None or args.run_marker is None:
        raise HistoricalRunError("--execute requires db, output, and run-marker")
    if any(path.exists() or path.is_symlink() for path in (args.output, args.run_marker)):
        raise HistoricalRunError("result and run marker must not preexist")
    preflight_report = preflight.run_read_only_preflight(args.db)
    if preflight_report.get("status") != "PREFLIGHT_PASS":
        raise HistoricalRunError("outcome-free preflight did not pass")
    prepared = prepare_historical(args.db, preflight_report)
    claimed = {
        "schema_version": "one-use-historical-run-receipt-v1",
        "run_id": RUN_ID,
        "status": "CLAIMED_BEFORE_HISTORICAL_OUTCOME_ACCESS",
        "research_id": swing.RESEARCH_ID,
        "definition_sha256": swing.DEFINITION_SHA256,
        "database_sha256": swing.DATABASE_SHA256,
        "strategy_candidate_available": False,
    }
    try:
        _exclusive_write(args.run_marker, claimed)
    except Exception:
        close_prepared(prepared)
        raise
    try:
        report = execute_historical(prepared, preflight_report)
    except Exception as exc:
        report = _terminal_execution_failure(prepared, exc)
    finally:
        close_prepared(prepared)
    _exclusive_write(args.output, report)
    output_sha256 = _sha(args.output)
    _finalize_marker(
        args.run_marker,
        claimed
        | {
            "status": "CONSUMED_HISTORICAL_OUTCOME_PUBLISHED",
            "result_sha256": output_sha256,
            "result_status": report["status"],
        },
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "output_written": True,
                "run_consumed": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
