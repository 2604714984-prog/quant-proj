"""Outcome-free defensive low-volatility target formation and preflight."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
import math
from numbers import Real
from pathlib import Path
from statistics import median
from typing import Any, Literal

from quant_system.data import AcceptedSessionCalendar, SourceIdentity

RESEARCH_ID = "A_SHARE_DEFENSIVE_LOW_VOLATILITY_V1_20260717"
DEFINITION_PATH = Path("research/definitions/a_share_defensive_low_volatility_v1.json")
DEFINITION_SHA256 = "319c278d08897324abce66d7b7c2b5dda1001428637d7ade90cdaced998746ed"
BENCHMARK_SYMBOL = "510300.SH"
MAX_POSITIONS = 15
MIN_LISTED_SESSIONS = 252
MIN_MEDIAN_AMOUNT_CNY = 20_000_000.0
COMMON_A_BOARDS = frozenset({"SSE_MAIN", "SSE_STAR", "SZSE_MAIN", "SZSE_CHINEXT"})
BOARD_PREFIXES = {
    "SSE_MAIN": ("600", "601", "603", "605"), "SSE_STAR": ("688",),
    "SZSE_MAIN": ("000", "001", "002", "003"), "SZSE_CHINEXT": ("300", "301"),
}
class LowVolatilityContractError(ValueError): ...
@dataclass(frozen=True)
class Variant:
    order: int
    variant_id: str
    lookback_sessions: int
    method: Literal["sample_std", "downside_semideviation"]
VARIANTS = (Variant(1, "LV60", 60, "sample_std"), Variant(2, "LV120", 120, "sample_std"),
            Variant(3, "DSV60", 60, "downside_semideviation"), Variant(4, "DSV120", 120, "downside_semideviation"))
def _finite(value: object, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise LowVolatilityContractError(f"{name} must be finite numeric")
    parsed = float(value)
    if not math.isfinite(parsed) or (positive and parsed <= 0.0):
        word = "positive finite" if positive else "finite"
        raise LowVolatilityContractError(f"{name} must be {word}")
    return parsed
def _common_a_symbol(symbol: str, board: str) -> bool:
    if not isinstance(symbol, str) or symbol.count(".") != 1:
        return False
    code, suffix = symbol.split(".")
    expected = "SH" if board.startswith("SSE_") else "SZ"
    return (len(code) == 6 and code.isdigit() and suffix == expected
            and code.startswith(BOARD_PREFIXES.get(board, ())))
@dataclass(frozen=True)
class SignalBar:
    session_date: date
    symbol: str
    total_return_index: float
    amount_cny: float
    amount_unit: str
    accepted_sessions_since_listing: int
    listed: bool
    delisted: bool
    is_st: bool
    is_suspended: bool
    security_type: str
    board: str
    source: SourceIdentity

    def __post_init__(self) -> None:
        if type(self.session_date) is not date or not _common_a_symbol(self.symbol, self.board):
            raise LowVolatilityContractError("signal date and symbol must be exact")
        _finite(self.total_return_index, "total_return_index", positive=True)
        if _finite(self.amount_cny, "amount_cny") < 0 or self.amount_unit != "CNY":
            raise LowVolatilityContractError("amount must be nonnegative CNY")
        if type(self.accepted_sessions_since_listing) is not int or self.accepted_sessions_since_listing < 0:
            raise LowVolatilityContractError("listed-session count must be nonnegative int")
        flags = (self.listed, self.delisted, self.is_st, self.is_suspended)
        if any(type(value) is not bool for value in flags):
            raise LowVolatilityContractError("status fields must be boolean")
        if self.security_type != "COMMON_A" or self.board not in COMMON_A_BOARDS:
            raise LowVolatilityContractError("row must be an ordinary common A share")
        if not isinstance(self.source, SourceIdentity):
            raise LowVolatilityContractError("source must be a SourceIdentity")
        self.source.__post_init__()
@dataclass(frozen=True)
class ExecutionRow:
    execution_date: date
    symbol: str
    open_price_cny: float
    currency_unit: str
    position_unit: str
    source: SourceIdentity

    def __post_init__(self) -> None:
        if type(self.execution_date) is not date or not isinstance(self.symbol, str) or not self.symbol.strip() or self.symbol != self.symbol.strip():
            raise LowVolatilityContractError("execution date and symbol must be exact")
        _finite(self.open_price_cny, "open_price_cny", positive=True)
        if (self.currency_unit, self.position_unit) != ("CNY", "SHARES"):
            raise LowVolatilityContractError("execution units must be CNY and SHARES")
        if not isinstance(self.source, SourceIdentity):
            raise LowVolatilityContractError("execution source must be SourceIdentity")
        self.source.__post_init__()
@dataclass(frozen=True)
class Target:
    variant_id: str
    variant_order: int
    decision_date: date
    execution_date: date
    eligible_count: int
    candidate_count: int
    selected_symbols: tuple[str, ...]
    selected_scores: tuple[tuple[str, float], ...]
    target_weights: tuple[tuple[str, float], ...]
@dataclass(frozen=True)
class PreflightHealth:
    benchmark_symbol: str
    benchmark_initial_entry_filled: bool
    benchmark_invested_ratio: float
    capacity_rejection_ratio: float
    unexpected_exception_count: int
    currency_unit: str = "CNY"
    position_unit: str = "SHARES"

    def __post_init__(self) -> None:
        if self.benchmark_symbol != BENCHMARK_SYMBOL:
            raise LowVolatilityContractError("benchmark identity must be 510300.SH")
        if type(self.benchmark_initial_entry_filled) is not bool:
            raise LowVolatilityContractError("benchmark fill flag must be boolean")
        for name in ("benchmark_invested_ratio", "capacity_rejection_ratio"):
            if not 0 <= _finite(getattr(self, name), name) <= 1:
                raise LowVolatilityContractError(f"{name} must be in [0, 1]")
        if type(self.unexpected_exception_count) is not int or self.unexpected_exception_count < 0:
            raise LowVolatilityContractError("exception count must be nonnegative int")
        if (self.currency_unit, self.position_unit) != ("CNY", "SHARES"):
            raise LowVolatilityContractError("preflight units must be CNY and SHARES")
def _score(returns: tuple[float, ...], variant: Variant) -> float:
    values = returns[-variant.lookback_sessions :]
    if len(values) != variant.lookback_sessions:
        raise LowVolatilityContractError("return history is incomplete")
    if variant.method == "sample_std":
        mean = math.fsum(values) / len(values)
        raw = math.sqrt(
            math.fsum((value - mean) ** 2 for value in values) / (len(values) - 1)
        )
    else:
        raw = math.sqrt(math.fsum(min(value, 0) ** 2 for value in values) / len(values))
    return _finite(raw * math.sqrt(252), "annualized score")
def _eligible_score(
    by_key: Mapping[tuple[date, str], SignalBar], symbol: str, history_dates: tuple[date, ...],
    decision_at: datetime, variant: Variant,
) -> float | None:
    possible = tuple(by_key.get((day, symbol)) for day in history_dates)
    if any(row is None or row.source.available_at > decision_at for row in possible):
        return None
    history = tuple(row for row in possible if row is not None)
    current = history[-1]
    if not (
        current.listed and not current.delisted and not current.is_st and not current.is_suspended
        and current.accepted_sessions_since_listing >= MIN_LISTED_SESSIONS
        and median(row.amount_cny for row in history[-20:]) >= MIN_MEDIAN_AMOUNT_CNY
    ):
        return None
    returns = tuple(history[i].total_return_index / history[i - 1].total_return_index - 1
                    for i in range(1, len(history)))
    return _score(returns, variant)
def _build(
    rows: Sequence[SignalBar], calendar: AcceptedSessionCalendar,
    decision_at_by_session: Mapping[date, datetime], execution_rows: Sequence[ExecutionRow],
) -> tuple[tuple[Target, ...], tuple[tuple[int, int, bool], ...], tuple[date, ...]]:
    if not isinstance(calendar, AcceptedSessionCalendar):
        raise TypeError("calendar must be AcceptedSessionCalendar")
    frozen = tuple(rows)
    if not frozen or any(not isinstance(row, SignalBar) for row in frozen):
        raise LowVolatilityContractError("rows must contain SignalBar values")
    by_key: dict[tuple[date, str], SignalBar] = {}
    for row in frozen:
        row.__post_init__()
        key = (row.session_date, row.symbol)
        if key in by_key:
            raise LowVolatilityContractError("duplicate signal symbol-session key")
        by_key[key] = row
    execution_by_key: dict[tuple[date, str], ExecutionRow] = {}
    for row in execution_rows:
        if not isinstance(row, ExecutionRow):
            raise LowVolatilityContractError("invalid execution row")
        row.__post_init__()
        key = (row.execution_date, row.symbol)
        if key in execution_by_key:
            raise LowVolatilityContractError("duplicate execution symbol-session key")
        execution_by_key[key] = row

    dates = calendar.session_dates
    decisions = tuple(index for index in range(120, len(dates) - 1)
                      if (dates[index].year, dates[index].month)
                      != (dates[index + 1].year, dates[index + 1].month))
    if not decisions:
        raise LowVolatilityContractError("no complete month-end decision")
    symbols = tuple(sorted({row.symbol for row in frozen}))
    targets: list[Target] = []
    audits: list[tuple[int, int, bool]] = []
    for index in decisions:
        decision_date = dates[index]
        decision_at = decision_at_by_session.get(decision_date)
        if not isinstance(decision_at, datetime) or decision_at.tzinfo is None:
            raise LowVolatilityContractError("decision_at must be aware")
        decision_session = calendar.session_on(decision_date, as_of=decision_at)
        execution_session = calendar.next_session(decision_date, as_of=decision_at)
        for session in (decision_session, execution_session):
            session.__post_init__()
            session.source.__post_init__()
        if not decision_session.close_at < decision_at < execution_session.open_at:
            raise LowVolatilityContractError("decision must be after D close, before D+1 open")
        for variant in VARIANTS:
            history_dates = dates[index - variant.lookback_sessions : index + 1]
            for session_date in history_dates:
                session = calendar.session_on(session_date, as_of=decision_at)
                session.__post_init__()
                session.source.__post_init__()
            ranked = tuple(sorted(
                ((symbol, score) for symbol in symbols
                 if (score := _eligible_score(
                     by_key, symbol, history_dates, decision_at, variant)) is not None),
                key=lambda item: (item[1], item[0]),
            ))
            selected = ranked[:MAX_POSITIONS]
            valid = len(selected) == MAX_POSITIONS and all(
                (entry := execution_by_key.get((execution_session.session_date, symbol)))
                is not None
                and entry.source.available_at <= execution_session.open_at
                for symbol, _ in selected
            )
            audits.append((len(ranked), len(ranked), valid))
            if valid:
                targets.append(Target(
                        variant.variant_id,
                        variant.order,
                        decision_date,
                        execution_session.session_date,
                        len(ranked),
                        len(ranked),
                        tuple(symbol for symbol, _ in selected),
                        selected,
                        tuple((symbol, 1 / MAX_POSITIONS) for symbol, _ in selected),
                    ))
    return tuple(targets), tuple(audits), tuple(dates[index] for index in decisions)
def build_monthly_targets(
    rows: Sequence[SignalBar], calendar: AcceptedSessionCalendar,
    *,
    decision_at_by_session: Mapping[date, datetime],
    execution_rows: Sequence[ExecutionRow],
) -> tuple[Target, ...]:
    return _build(rows, calendar, decision_at_by_session, execution_rows)[0]
def build_preflight_report(
    rows: Sequence[SignalBar], calendar: AcceptedSessionCalendar,
    *,
    decision_at_by_session: Mapping[date, datetime],
    execution_rows: Sequence[ExecutionRow],
    health: PreflightHealth,
) -> dict[str, Any]:
    if not isinstance(health, PreflightHealth):
        raise LowVolatilityContractError("health must be PreflightHealth")
    health.__post_init__()
    if not health.benchmark_initial_entry_filled:
        raise LowVolatilityContractError("benchmark initial entry must be filled")
    if health.unexpected_exception_count:
        raise LowVolatilityContractError("unexpected_exception_count must be zero")
    _, audits, decisions = _build(rows, calendar, decision_at_by_session, execution_rows)
    eligible = tuple(row[0] for row in audits)
    candidates = tuple(row[1] for row in audits)
    return {
        "schema_version": "defensive-low-volatility-preflight-v1",
        "research_id": RESEARCH_ID,
        "phase": "OUTCOME_FREE_PREFLIGHT",
        "status": "PREFLIGHT_PASS" if all(row[2] for row in audits) else "PREFLIGHT_BLOCKED",
        "coverage_start": min(row.session_date for row in rows).isoformat(),
        "coverage_end": max(row.session_date for row in rows).isoformat(),
        "decision_date_count": len(decisions),
        "min_eligible_count": min(eligible),
        "max_eligible_count": max(eligible),
        "min_candidate_count": min(candidates),
        "max_candidate_count": max(candidates),
        "decision_invalid_count": sum(not row[2] for row in audits),
        "benchmark_initial_entry_filled": True,
        "benchmark_invested_ratio": health.benchmark_invested_ratio,
        "capacity_rejection_ratio": health.capacity_rejection_ratio,
        "unexpected_exception_count": 0,
        "currency_unit": "CNY",
        "position_unit": "SHARES",
        "strategy_candidate_available": False,
    }
