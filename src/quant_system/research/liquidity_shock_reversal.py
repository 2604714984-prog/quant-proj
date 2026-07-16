"""Outcome-blind Cycle 3 reversal targets and aggregate preflight."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from bisect import bisect_left
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import hashlib
import math
from numbers import Real
import os
from pathlib import Path
from statistics import median
from typing import Any
from zoneinfo import ZoneInfo

from quant_system.backtest.capacity import CapacityObservation, CapacityPolicy
from quant_system.backtest.event_loop import ExecutionInput, StaticRebalanceResult, run_static_rebalance
from quant_system.backtest.portfolio import Portfolio
from quant_system.data import AcceptedSession, AcceptedSessionCalendar, SourceIdentity
from quant_system.markets.universe import StatusEvidence, evaluate_universe

RESEARCH_ID = "A_SHARE_LIQUIDITY_SHOCK_CONDITIONAL_SHORT_TERM_REVERSAL_V1_20260717"
DEFINITION_PATH = Path("research/definitions/a_share_liquidity_shock_conditional_short_term_reversal_v1.json")
DEFINITION_SHA256 = "ffc3ecdf9c3af3ec76e2e4912ce5629f6ac072a2c52007e58ad19173c52057fe"
SNAPSHOT_ID = "a_share_qfq_personal_research_20260716_v5"
DATABASE_SHA256 = "e636bb80e300f89e46831e91275c6f2167e370e81a00b21b300e253f6107bee0"
BENCHMARK_SYMBOL = "510300.SH"
HISTORICAL_CUTOFF = date(2026, 6, 30)
INITIAL_CASH_CNY, MAX_POSITIONS, MIN_ELIGIBLE = 400_000.0, 15, 500
MIN_LISTED_SESSIONS, MIN_MEDIAN_AMOUNT_CNY, SHOCK_THRESHOLD = 252, 20_000_000.0, 2.0
SLIPPAGE_SCENARIOS_BPS = (20.0, 50.0)
BOARD_PREFIXES = {
    "SSE_MAIN": ("600", "601", "603", "605"), "SSE_STAR": ("688",), "SZSE_MAIN": ("000", "001", "002", "003"),
    "SZSE_CHINEXT": ("300", "301"),
}


class LiquidityShockContractError(ValueError): ...


@dataclass(frozen=True)
class Variant:
    order: int; variant_id: str; lookback_sessions: int; shock_required: bool  # noqa: E702


VARIANTS = (
    Variant(1, "REV10_NO_SHOCK", 10, False), Variant(2, "REV10_AMOUNT_SHOCK2", 10, True),
    Variant(3, "REV20_NO_SHOCK", 20, False), Variant(4, "REV20_AMOUNT_SHOCK2", 20, True),
)


def _finite(value: object, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise LiquidityShockContractError(f"{name} must be finite numeric")
    parsed = float(value)
    if not math.isfinite(parsed) or (positive and parsed <= 0.0):
        raise LiquidityShockContractError(f"{name} must be positive finite" if positive else f"{name} must be finite")
    return parsed


def _common_symbol(symbol: str, board: str) -> bool:
    if not isinstance(symbol, str) or symbol.count(".") != 1:
        return False
    code, suffix = symbol.split(".")
    expected = "SH" if board.startswith("SSE_") else "SZ"
    return len(code) == 6 and code.isdigit() and suffix == expected and code.startswith(BOARD_PREFIXES.get(board, ()))


@dataclass(frozen=True)
class SignalBar:
    session_date: date; symbol: str; qfq_close_cny: float; amount_cny: float  # noqa: E702
    accepted_sessions_since_listing: int; listed: bool; delisted: bool; is_st: bool  # noqa: E702
    is_suspended: bool; is_limit_up: bool; is_limit_down: bool; security_type: str  # noqa: E702
    board: str; source: SourceIdentity  # noqa: E702

    def __post_init__(self) -> None:
        benchmark = self.symbol == BENCHMARK_SYMBOL
        if type(self.session_date) is not date or (benchmark and (self.security_type, self.board) != ("ETF", "SSE_ETF")) or (not benchmark and (self.security_type != "COMMON_A" or not _common_symbol(self.symbol, self.board))):
            raise LiquidityShockContractError("signal identity is invalid")
        _finite(self.qfq_close_cny, "qfq_close_cny", positive=True)
        if _finite(self.amount_cny, "amount_cny") < 0.0:
            raise LiquidityShockContractError("amount_cny must be nonnegative")
        if type(self.accepted_sessions_since_listing) is not int or self.accepted_sessions_since_listing < 0:
            raise LiquidityShockContractError("listing sessions must be a nonnegative int")
        flags = (self.listed, self.delisted, self.is_st, self.is_suspended, self.is_limit_up, self.is_limit_down)
        if any(type(value) is not bool for value in flags):
            raise LiquidityShockContractError("status fields must be boolean")
        if not isinstance(self.source, SourceIdentity):
            raise LiquidityShockContractError("source must be a SourceIdentity")
        self.source.__post_init__()


@dataclass(frozen=True)
class Target:
    variant_id: str; decision_date: date; execution_date: date  # noqa: E702
    eligible_count: int; candidate_count: int; selected_symbols: tuple[str, ...]  # noqa: E702
    selected_scores: tuple[tuple[str, float], ...]; target_weights: tuple[tuple[str, float], ...]  # noqa: E702


@dataclass(frozen=True)
class DecisionAudit:
    variant_id: str; decision_date: date; eligible_count: int; candidate_count: int  # noqa: E702
    execution_panel_complete: bool; valid: bool  # noqa: E702


def _history(by_key: Mapping[tuple[date, str], SignalBar], symbol: str,
             dates: tuple[date, ...], cutoff: datetime) -> tuple[SignalBar, ...] | None:
    rows = tuple(by_key.get((day, symbol)) for day in dates)
    if any(row is None or row.source.available_at > cutoff for row in rows):
        return None
    return tuple(row for row in rows if row is not None)


def _execution_complete(row: ExecutionInput | None, execution: AcceptedSession, cutoff: datetime) -> bool:
    if row is None or row.market != "a_share" or row.currency != "CNY" or row.is_suspended:
        return False
    if row.source.available_at > execution.open_at or row.capacity is None or row.capacity.source.available_at > cutoff or row.up_limit is None or row.down_limit is None:
        return False
    try:
        eligible = evaluate_universe(row.symbol, execution, cutoff, row.status_records).eligible
        price, upper, lower = _finite(row.open_price, "execution open", positive=True), _finite(row.up_limit, "up_limit", positive=True), _finite(row.down_limit, "down_limit", positive=True)
    except ValueError:
        return False
    return eligible and lower <= price <= upper


def build_decision_targets(
    rows: Sequence[SignalBar], calendar: AcceptedSessionCalendar, *, decision_date: date,
    decision_at: datetime, execution_inputs: tuple[ExecutionInput, ...],
) -> tuple[tuple[Target, ...], tuple[DecisionAudit, ...]]:
    if not isinstance(calendar, AcceptedSessionCalendar):
        raise TypeError("calendar must be an AcceptedSessionCalendar")
    frozen = tuple(rows)
    if not frozen or any(not isinstance(row, SignalBar) for row in frozen):
        raise LiquidityShockContractError("rows must contain SignalBar values")
    by_key: dict[tuple[date, str], SignalBar] = {}
    for row in frozen:
        row.__post_init__()
        key = (row.session_date, row.symbol)
        if key in by_key:
            raise LiquidityShockContractError("duplicate signal symbol-session key")
        by_key[key] = row
    inputs = {row.symbol: row for row in execution_inputs}
    if len(inputs) != len(execution_inputs):
        raise LiquidityShockContractError("duplicate execution symbol")
    try:
        index = calendar.session_dates.index(decision_date)
    except ValueError as exc:
        raise LiquidityShockContractError("decision is not an accepted session") from exc
    if index < 20:
        raise LiquidityShockContractError("required 20-session history is missing")
    signal, execution = calendar.session_on(decision_date, as_of=decision_at), calendar.next_session(decision_date, as_of=decision_at)
    if decision_at != signal.close_at + timedelta(minutes=30):
        raise LiquidityShockContractError("decision_at must equal D close plus 30 minutes")
    dates = calendar.session_dates[index - 20 : index + 1]
    for day in dates:
        calendar.session_on(day, as_of=decision_at)
    benchmark = _history(by_key, BENCHMARK_SYMBOL, dates, decision_at)
    if benchmark is None:
        raise LiquidityShockContractError("benchmark history is incomplete")
    features: dict[str, tuple[float, float, float]] = {}
    for symbol in sorted({row.symbol for row in frozen} - {BENCHMARK_SYMBOL}):
        history = _history(by_key, symbol, dates, decision_at)
        if history is None or any(row.amount_cny <= 0.0 for row in history[:-1]):
            continue
        current, baseline = history[-1], median(row.amount_cny for row in history[:-1])
        if not (current.listed and not current.delisted and not current.is_st and not current.is_suspended and not current.is_limit_up and not current.is_limit_down and current.accepted_sessions_since_listing >= MIN_LISTED_SESSIONS and baseline >= MIN_MEDIAN_AMOUNT_CNY and current.amount_cny > 0.0):
            continue
        rel10 = (current.qfq_close_cny / history[-11].qfq_close_cny) / (benchmark[-1].qfq_close_cny / benchmark[-11].qfq_close_cny) - 1.0
        rel20 = (current.qfq_close_cny / history[0].qfq_close_cny) / (benchmark[-1].qfq_close_cny / benchmark[0].qfq_close_cny) - 1.0
        features[symbol] = (_finite(rel10, "relative_10"), _finite(rel20, "relative_20"), _finite(current.amount_cny / baseline, "activity_shock"))
    targets, audits = [], []
    for variant in VARIANTS:
        offset = 0 if variant.lookback_sessions == 10 else 1
        candidates = tuple(sorted(((symbol, values[offset]) for symbol, values in features.items() if values[offset] < 0.0 and (not variant.shock_required or values[2] >= SHOCK_THRESHOLD)), key=lambda item: (item[1], item[0])))
        selected = candidates[:MAX_POSITIONS]
        complete = len(selected) == MAX_POSITIONS and all(_execution_complete(inputs.get(symbol), execution, decision_at) for symbol, _ in selected)
        valid = len(features) >= MIN_ELIGIBLE and len(candidates) >= MAX_POSITIONS and complete
        audits.append(DecisionAudit(variant.variant_id, decision_date, len(features), len(candidates), complete, valid))
        if valid:
            symbols = tuple(symbol for symbol, _ in selected)
            targets.append(Target(variant.variant_id, decision_date, execution.session_date, len(features), len(candidates), symbols, selected, tuple((symbol, 1 / MAX_POSITIONS) for symbol in symbols)))
    return tuple(targets), tuple(audits)


def _preflight_report(audits: Sequence[DecisionAudit], coverage: tuple[date, date],
                      benchmark: tuple[bool, float, float, int]) -> dict[str, Any]:
    frozen = tuple(audits)
    if not frozen or any(not isinstance(row, DecisionAudit) for row in frozen):
        raise LiquidityShockContractError("audits must contain DecisionAudit values")
    by_date: dict[date, dict[str, DecisionAudit]] = {}
    expected = {variant.variant_id for variant in VARIANTS}
    for row in frozen:
        if row.variant_id not in expected or any(
            type(value) is not int or value < 0 for value in (row.eligible_count, row.candidate_count)
        ) or type(row.execution_panel_complete) is not bool or type(row.valid) is not bool:
            raise LiquidityShockContractError("audit values are invalid")
        if row.variant_id in by_date.setdefault(row.decision_date, {}):
            raise LiquidityShockContractError("duplicate decision-variant audit")
        by_date[row.decision_date][row.variant_id] = row
    if any(set(group) != expected for group in by_date.values()):
        raise LiquidityShockContractError("every decision requires exactly four variant audits")
    invalid = {day for day, group in by_date.items() if not all(row.valid for row in group.values())}
    panels, (filled, invested, rejected, exceptions) = all(row.execution_panel_complete for row in frozen), benchmark
    passed = not invalid and panels and filled and exceptions == 0
    return {
        "schema_version": "a-share-liquidity-shock-reversal-preflight-v1", "research_id": RESEARCH_ID, "phase": "OUTCOME_FREE_PREFLIGHT",
        "status": "PREFLIGHT_PASS" if passed else "INPUT_BLOCKED", "snapshot_id": SNAPSHOT_ID, "database_sha256": DATABASE_SHA256,
        "coverage_start": coverage[0].isoformat(), "coverage_end": coverage[1].isoformat(), "required_history_exists": True,
        "decision_count": len(by_date), "minimum_eligible_count": min(row.eligible_count for row in frozen), "minimum_candidate_count": min(row.candidate_count for row in frozen),
        "invalid_decision_count": len(invalid), "execution_panels_complete": panels, "benchmark_initial_entry_filled": filled,
        "benchmark_invested_ratio": invested, "capacity_rejection_ratio": rejected, "unexpected_exception_count": exceptions,
        "currency_unit": "CNY", "position_unit": "SHARES", "post_entry_outcomes_opened": False, "embargo_or_prospective_data_accessed": False,
        "strategy_candidate_available": False,
    }


def _digest(path: Path) -> tuple[str, tuple[int, int, int]]:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise LiquidityShockContractError("database path must be a readable regular file") from exc
    with os.fdopen(descriptor, "rb") as stream:
        stat = os.fstat(stream.fileno()); digest = hashlib.sha256()  # noqa: E702
        for chunk in iter(lambda: stream.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest(), (stat.st_dev, stat.st_ino, stat.st_size)


def _parse_day(value: object) -> date:
    try:
        return datetime.strptime(str(value), "%Y%m%d").date()
    except ValueError as exc:
        raise LiquidityShockContractError("database contains an invalid trade date") from exc


def _accepted_calendar(days: tuple[date, ...]) -> AcceptedSessionCalendar:
    zone = ZoneInfo("Asia/Shanghai"); available = datetime(2000, 1, 1, tzinfo=zone)  # noqa: E702
    source = SourceIdentity("https://local.invalid/cycle3/calendar", hashlib.sha256(b"cycle3-calendar").hexdigest(), available, available, "cycle3-calendar")
    return AcceptedSessionCalendar(tuple(AcceptedSession(day, datetime.combine(day, datetime.min.time().replace(hour=9, minute=30), zone), datetime.combine(day, datetime.min.time().replace(hour=15), zone), source, "Asia/Shanghai") for day in days))


def _database_audits(connection: Any, days: tuple[date, ...]) -> tuple[tuple[DecisionAudit, ...], tuple[date, ...]]:
    masters = {row[0]: (_parse_day(row[1]), _parse_day(row[2]) if row[2] else None) for row in connection.execute("SELECT ts_code,nullif(list_date,''),nullif(delist_date,'') FROM a_share.a_share_symbol_master QUALIFY row_number() OVER (PARTITION BY ts_code ORDER BY ingested_at DESC,snapshot_id DESC)=1").fetchall() if row[1]}
    decisions = tuple(day for index, day in enumerate(days[:-1]) if index >= 252 and day.month != days[index + 1].month)
    audits: list[DecisionAudit] = []
    for decision in decisions:
        position = bisect_left(days, decision); window = days[position - 20 : position + 1]  # noqa: E702
        rows = connection.execute("SELECT ts_code,count(*),arg_min(qfq_close,trade_date),max(CASE WHEN trade_date=? THEN qfq_close END),arg_max(qfq_close,trade_date),median(amount) FILTER (WHERE trade_date<>?),min(amount) FILTER (WHERE trade_date<>?),arg_max(amount,trade_date),arg_max(is_st,trade_date),arg_max(is_suspended,trade_date),arg_max(is_limit_up,trade_date),arg_max(is_limit_down,trade_date),arg_max(list_status,trade_date) FROM a_share.a_share_canonical_daily_bars WHERE snapshot_id=? AND trade_date BETWEEN ? AND ? GROUP BY ts_code HAVING count(*)=21 AND count(qfq_close)=21 AND count(amount)=21", [window[-11].strftime("%Y%m%d"), decision.strftime("%Y%m%d"), decision.strftime("%Y%m%d"), SNAPSHOT_ID, window[0].strftime("%Y%m%d"), decision.strftime("%Y%m%d")]).fetchall()
        benchmark = next((row for row in rows if row[0] == BENCHMARK_SYMBOL), None)
        if benchmark is None or min(benchmark[2:5]) <= 0:
            raise LiquidityShockContractError("benchmark history is incomplete")
        features: dict[str, tuple[float, float, float]] = {}
        for row in rows:
            symbol, identity = row[0], masters.get(row[0])
            if symbol == BENCHMARK_SYMBOL or identity is None or row[5] is None or row[5] < MIN_MEDIAN_AMOUNT_CNY or row[6] is None or row[6] <= 0:
                continue
            board = next((name for name, prefixes in BOARD_PREFIXES.items() if symbol.endswith(".SH" if name.startswith("SSE_") else ".SZ") and symbol.startswith(prefixes)), ""); listed = position - bisect_left(days, identity[0]) + 1  # noqa: E702
            if not _common_symbol(symbol, board) or listed < MIN_LISTED_SESSIONS or (identity[1] and identity[1] <= decision) or any(bool(value) for value in row[8:12]) or row[12] != "L" or row[7] <= 0:
                continue
            features[symbol] = ((row[4] / row[3]) / (benchmark[4] / benchmark[3]) - 1, (row[4] / row[2]) / (benchmark[4] / benchmark[2]) - 1, row[7] / row[5])
        candidates = {variant.variant_id: tuple(sorted(((symbol, values[0 if variant.lookback_sessions == 10 else 1]) for symbol, values in features.items() if values[0 if variant.lookback_sessions == 10 else 1] < 0 and (not variant.shock_required or values[2] >= SHOCK_THRESHOLD)), key=lambda item: (item[1], item[0]))) for variant in VARIANTS}; selected = {symbol for values in candidates.values() for symbol, _ in values[:MAX_POSITIONS]}  # noqa: E702
        executions = {row[0]: row for row in connection.execute("SELECT ts_code,open,is_suspended,is_st,up_limit,down_limit,list_status FROM a_share.a_share_canonical_daily_bars WHERE snapshot_id=? AND trade_date=? AND ts_code IN (SELECT unnest(?))", [SNAPSHOT_ID, days[position + 1].strftime("%Y%m%d"), tuple(selected)]).fetchall()} if selected else {}
        for variant in VARIANTS:
            chosen = candidates[variant.variant_id][:MAX_POSITIONS]
            complete = len(chosen) == MAX_POSITIONS and all((row := executions.get(symbol)) is not None and row[1] is not None and row[1] > 0 and row[2] is False and row[3] is False and row[4] is not None and row[5] is not None and row[5] <= row[1] <= row[4] and row[6] == "L" for symbol, _ in chosen)
            valid = len(features) >= MIN_ELIGIBLE and len(candidates[variant.variant_id]) >= MAX_POSITIONS and complete; audits.append(DecisionAudit(variant.variant_id, decision, len(features), len(candidates[variant.variant_id]), complete, valid))  # noqa: E702
    return tuple(audits), decisions


def _benchmark_probe(connection: Any, calendar: AcceptedSessionCalendar, decisions: tuple[date, ...]) -> tuple[bool, float, float, int]:
    probes = tuple(dict.fromkeys(next((day for day in decisions if day >= start), decisions[-1]) for start in (date(2022, 1, 1), date(2024, 1, 1))))
    fills: list[bool] = []; invested: list[float] = []; rejected = exceptions = 0  # noqa: E702
    for decision in probes:
        signal = calendar.session_on(decision, as_of=datetime(2030, 1, 1, tzinfo=ZoneInfo("Asia/Shanghai"))); execution = calendar.next_session(decision, as_of=signal.close_at + timedelta(minutes=30))  # noqa: E702
        rows = connection.execute("SELECT trade_date,qfq_open,vol,amount,is_suspended,up_limit,down_limit,row_hash FROM a_share.a_share_canonical_daily_bars WHERE snapshot_id=? AND ts_code=? AND trade_date IN (?,?) ORDER BY trade_date", [SNAPSHOT_ID, BENCHMARK_SYMBOL, decision.strftime("%Y%m%d"), execution.session_date.strftime("%Y%m%d")]).fetchall()
        if len(rows) != 2:
            exceptions += len(SLIPPAGE_SCENARIOS_BPS)
            continue
        shares = round(float(rows[0][2]))
        if abs(float(rows[0][2]) - shares) > 1e-6:
            raise LiquidityShockContractError("volume cannot be normalized to whole shares")
        source = SourceIdentity("https://local.invalid/cycle3/benchmark", rows[1][7], execution.open_at, execution.open_at, "benchmark-open"); status_source = SourceIdentity("https://local.invalid/cycle3/status", hashlib.sha256(b"cycle3-status").hexdigest(), signal.close_at, signal.close_at, "benchmark-status")  # noqa: E702
        statuses = tuple(StatusEvidence(f"benchmark-{kind}", BENCHMARK_SYMBOL, kind, value, date(2000, 1, 1), None, "Asia/Shanghai", status_source) for kind, value in (("listed", True), ("delisted", False), ("st", False), ("suspended", False)))
        capacity_source = SourceIdentity("https://local.invalid/cycle3/capacity", rows[0][7], signal.close_at, signal.close_at, "benchmark-capacity"); item = ExecutionInput(BENCHMARK_SYMBOL, "a_share", rows[1][1], "CNY", source, statuses, is_suspended=bool(rows[1][4]), up_limit=rows[1][5], down_limit=rows[1][6], capacity=CapacityObservation(BENCHMARK_SYMBOL, signal, shares, rows[0][3], "CNY", capacity_source))  # noqa: E702
        for slippage in SLIPPAGE_SCENARIOS_BPS:
            try:
                result = run_frozen_static_rebalance(new_strategy_portfolio(), calendar, signal_session=decision, decision_at=signal.close_at + timedelta(minutes=30), execution_inputs=(item,), target_weights={BENCHMARK_SYMBOL: 1.0}, slippage_bps=slippage)
                buy = next((receipt for receipt in result.receipts if receipt.side == "buy"), None)
                filled = buy is not None and buy.filled_shares > 0 and buy.price is not None
                fills.append(filled)
                invested.append((buy.filled_shares * buy.price / INITIAL_CASH_CNY) if filled else 0.0)
                rejected += int(not filled and buy is not None and "capacity" in buy.reason)
            except (ValueError, TypeError):
                exceptions += 1
    attempts = max(1, len(fills) + exceptions)
    return bool(fills) and all(fills), sum(invested) / max(1, len(invested)), rejected / attempts, exceptions


def run_read_only_preflight(database_path: str | Path) -> dict[str, Any]:
    """Reproduce the aggregate preflight from the pinned local snapshot only."""
    path = Path(database_path); before, identity = _digest(path)  # noqa: E702
    if before != DATABASE_SHA256:
        raise LiquidityShockContractError("database SHA-256 does not match the frozen identity")
    import duckdb
    connection = duckdb.connect(str(path), read_only=True)
    try:
        connection.execute("SET enable_external_access=false")
        snapshot = connection.execute("SELECT count(*),min(trade_date),max(trade_date),count(DISTINCT quality_status),min(quality_status),bool_and(not synthetic_data) FROM a_share.a_share_canonical_daily_bars WHERE snapshot_id=? AND trade_date<=?", [SNAPSHOT_ID, HISTORICAL_CUTOFF.strftime("%Y%m%d")]).fetchone()
        if snapshot is None or snapshot[0] <= 0 or snapshot[3:] != (1, "RETROSPECTIVE_PERSONAL_RESEARCH_GRADE_SECONDARY_NOT_STRICT_PIT", True):
            raise LiquidityShockContractError("snapshot identity or classification is invalid")
        coverage = (_parse_day(snapshot[1]), _parse_day(snapshot[2])); days = tuple(_parse_day(row[0]) for row in connection.execute("SELECT DISTINCT trade_date FROM a_share.a_share_trade_calendar WHERE is_open=1 AND trade_date<=? ORDER BY trade_date", [HISTORICAL_CUTOFF.strftime("%Y%m%d")]).fetchall())  # noqa: E702
        if len(days) < 254 or days[-1] != HISTORICAL_CUTOFF:
            raise LiquidityShockContractError("accepted calendar history is incomplete")
        calendar = _accepted_calendar(days); audits, decisions = _database_audits(connection, days)  # noqa: E702
        if not audits or not decisions:
            raise LiquidityShockContractError("no reproducible month-end decisions")
        report = _preflight_report(audits, coverage, _benchmark_probe(connection, calendar, decisions))
    finally:
        connection.close()
    if _digest(path) != (before, identity):
        raise LiquidityShockContractError("database changed during read-only preflight")
    return report


def new_strategy_portfolio() -> Portfolio:
    return Portfolio.a_share(INITIAL_CASH_CNY)


def run_frozen_static_rebalance(
    portfolio: Portfolio, calendar: AcceptedSessionCalendar, *, signal_session: date,
    decision_at: datetime, execution_inputs: tuple[ExecutionInput, ...],
    target_weights: Mapping[str, float], slippage_bps: float,
    prior_stage_hash: str = "0" * 64,
) -> StaticRebalanceResult:
    if not isinstance(portfolio, Portfolio) or portfolio.lot_size != 100 or portfolio.share_t_plus_one is not True or portfolio.a_share_stamp_tax_schedule is not True:
        raise LiquidityShockContractError("portfolio does not match frozen A-share semantics")
    slippage = _finite(slippage_bps, "slippage_bps")
    if slippage not in SLIPPAGE_SCENARIOS_BPS:
        raise LiquidityShockContractError("slippage_bps must be exactly 20 or 50")
    weights = dict(target_weights)
    return run_static_rebalance(portfolio, calendar, signal_session=signal_session, decision_at=decision_at, execution_inputs=execution_inputs, target_weights=lambda _: weights, capacity_policy=CapacityPolicy(0.01, 0.01, "CNY"), max_positions=MAX_POSITIONS, slippage_bps=slippage, prior_stage_hash=prior_stage_hash)
