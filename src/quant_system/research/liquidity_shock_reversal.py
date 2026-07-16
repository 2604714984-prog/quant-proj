"""Outcome-blind Cycle 3 reversal targets and aggregate preflight."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import math
from numbers import Real
from pathlib import Path
from statistics import median
from typing import Any

from quant_system.backtest.capacity import CapacityPolicy
from quant_system.backtest.event_loop import ExecutionInput, StaticRebalanceResult, run_static_rebalance
from quant_system.backtest.portfolio import Portfolio
from quant_system.data import AcceptedSession, AcceptedSessionCalendar, SourceIdentity
from quant_system.markets.universe import evaluate_universe

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
    order: int
    variant_id: str
    lookback_sessions: int
    shock_required: bool


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
    return len(code) == 6 and code.isdigit() and suffix == expected and code.startswith(
        BOARD_PREFIXES.get(board, ())
    )


@dataclass(frozen=True)
class SignalBar:
    session_date: date
    symbol: str
    qfq_close_cny: float
    amount_cny: float
    accepted_sessions_since_listing: int
    listed: bool
    delisted: bool
    is_st: bool
    is_suspended: bool
    is_limit_up: bool
    is_limit_down: bool
    security_type: str
    board: str
    source: SourceIdentity

    def __post_init__(self) -> None:
        benchmark = self.symbol == BENCHMARK_SYMBOL
        if type(self.session_date) is not date or (
            benchmark and (self.security_type, self.board) != ("ETF", "SSE_ETF")
        ) or (
            not benchmark and (self.security_type != "COMMON_A" or not _common_symbol(self.symbol, self.board))
        ):
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
    variant_id: str
    decision_date: date
    execution_date: date
    eligible_count: int
    candidate_count: int
    selected_symbols: tuple[str, ...]
    selected_scores: tuple[tuple[str, float], ...]
    target_weights: tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class DecisionAudit:
    variant_id: str
    decision_date: date
    eligible_count: int
    candidate_count: int
    execution_panel_complete: bool
    valid: bool


@dataclass(frozen=True)
class PreflightHealth:
    snapshot_id: str
    database_sha256: str
    coverage_start: date
    coverage_end: date
    required_history_exists: bool
    benchmark_initial_entry_filled: bool
    benchmark_invested_ratio: float
    capacity_rejection_ratio: float
    unexpected_exception_count: int
    post_entry_outcomes_opened: bool = False
    embargo_or_prospective_data_accessed: bool = False
    currency_unit: str = "CNY"
    position_unit: str = "SHARES"

    def __post_init__(self) -> None:
        if self.snapshot_id != SNAPSHOT_ID or self.database_sha256 != DATABASE_SHA256:
            raise LiquidityShockContractError("preflight input identity changed")
        if type(self.coverage_start) is not date or type(self.coverage_end) is not date \
                or self.coverage_start > self.coverage_end or self.coverage_end > HISTORICAL_CUTOFF:
            raise LiquidityShockContractError("preflight coverage is invalid")
        flags = (self.required_history_exists, self.benchmark_initial_entry_filled, self.post_entry_outcomes_opened,
                 self.embargo_or_prospective_data_accessed)
        if any(type(value) is not bool for value in flags):
            raise LiquidityShockContractError("preflight flags must be boolean")
        for name in ("benchmark_invested_ratio", "capacity_rejection_ratio"):
            if not 0.0 <= _finite(getattr(self, name), name) <= 1.0:
                raise LiquidityShockContractError(f"{name} must be in [0, 1]")
        if type(self.unexpected_exception_count) is not int or self.unexpected_exception_count < 0:
            raise LiquidityShockContractError("exception count must be a nonnegative int")
        if (self.currency_unit, self.position_unit) != ("CNY", "SHARES"):
            raise LiquidityShockContractError("preflight units must be CNY and SHARES")


def _history(by_key: Mapping[tuple[date, str], SignalBar], symbol: str,
             dates: tuple[date, ...], cutoff: datetime) -> tuple[SignalBar, ...] | None:
    rows = tuple(by_key.get((day, symbol)) for day in dates)
    if any(row is None or row.source.available_at > cutoff for row in rows):
        return None
    return tuple(row for row in rows if row is not None)


def _execution_complete(row: ExecutionInput | None, execution: AcceptedSession, cutoff: datetime) -> bool:
    if row is None or row.market != "a_share" or row.currency != "CNY" or row.is_suspended:
        return False
    if row.source.available_at > execution.open_at or row.capacity is None:
        return False
    if row.capacity.source.available_at > cutoff or row.up_limit is None or row.down_limit is None:
        return False
    try:
        eligible = evaluate_universe(row.symbol, execution, cutoff, row.status_records).eligible
        price = _finite(row.open_price, "execution open", positive=True)
        upper = _finite(row.up_limit, "up_limit", positive=True)
        lower = _finite(row.down_limit, "down_limit", positive=True)
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
    signal = calendar.session_on(decision_date, as_of=decision_at)
    execution = calendar.next_session(decision_date, as_of=decision_at)
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
        if not (current.listed and not current.delisted and not current.is_st
                and not current.is_suspended and not current.is_limit_up
                and not current.is_limit_down
                and current.accepted_sessions_since_listing >= MIN_LISTED_SESSIONS
                and baseline >= MIN_MEDIAN_AMOUNT_CNY and current.amount_cny > 0.0):
            continue
        rel10 = (current.qfq_close_cny / history[-11].qfq_close_cny) / (
            benchmark[-1].qfq_close_cny / benchmark[-11].qfq_close_cny
        ) - 1.0
        rel20 = (current.qfq_close_cny / history[0].qfq_close_cny) / (
            benchmark[-1].qfq_close_cny / benchmark[0].qfq_close_cny
        ) - 1.0
        features[symbol] = (_finite(rel10, "relative_10"), _finite(rel20, "relative_20"),
                            _finite(current.amount_cny / baseline, "activity_shock"))
    targets, audits = [], []
    for variant in VARIANTS:
        offset = 0 if variant.lookback_sessions == 10 else 1
        candidates = tuple(sorted(
            ((symbol, values[offset]) for symbol, values in features.items()
             if values[offset] < 0.0 and (not variant.shock_required or values[2] >= SHOCK_THRESHOLD)),
            key=lambda item: (item[1], item[0]),
        ))
        selected = candidates[:MAX_POSITIONS]
        complete = len(selected) == MAX_POSITIONS and all(
            _execution_complete(inputs.get(symbol), execution, decision_at)
            for symbol, _ in selected
        )
        valid = len(features) >= MIN_ELIGIBLE and len(candidates) >= MAX_POSITIONS and complete
        audits.append(DecisionAudit(variant.variant_id, decision_date, len(features), len(candidates), complete, valid))
        if valid:
            symbols = tuple(symbol for symbol, _ in selected)
            targets.append(Target(variant.variant_id, decision_date, execution.session_date,
                                  len(features), len(candidates), symbols, selected,
                                  tuple((symbol, 1 / MAX_POSITIONS) for symbol in symbols)))
    return tuple(targets), tuple(audits)


def build_preflight_report(audits: Sequence[DecisionAudit], health: PreflightHealth) -> dict[str, Any]:
    if not isinstance(health, PreflightHealth):
        raise LiquidityShockContractError("health must be PreflightHealth")
    health.__post_init__()
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
    panels = all(row.execution_panel_complete for row in frozen)
    passed = (health.required_history_exists and not invalid and panels
              and health.benchmark_initial_entry_filled and health.unexpected_exception_count == 0
              and not health.post_entry_outcomes_opened
              and not health.embargo_or_prospective_data_accessed)
    return {
        "schema_version": "a-share-liquidity-shock-reversal-preflight-v1", "research_id": RESEARCH_ID,
        "phase": "OUTCOME_FREE_PREFLIGHT",
        "status": "PREFLIGHT_PASS" if passed else "INPUT_BLOCKED", "snapshot_id": health.snapshot_id,
        "database_sha256": health.database_sha256, "coverage_start": health.coverage_start.isoformat(),
        "coverage_end": health.coverage_end.isoformat(), "required_history_exists": health.required_history_exists,
        "decision_count": len(by_date), "minimum_eligible_count": min(row.eligible_count for row in frozen),
        "minimum_candidate_count": min(row.candidate_count for row in frozen),
        "invalid_decision_count": len(invalid), "execution_panels_complete": panels,
        "benchmark_initial_entry_filled": health.benchmark_initial_entry_filled, "benchmark_invested_ratio": health.benchmark_invested_ratio,
        "capacity_rejection_ratio": health.capacity_rejection_ratio,
        "unexpected_exception_count": health.unexpected_exception_count,
        "currency_unit": health.currency_unit, "position_unit": health.position_unit,
        "post_entry_outcomes_opened": health.post_entry_outcomes_opened, "embargo_or_prospective_data_accessed": health.embargo_or_prospective_data_accessed,
        "strategy_candidate_available": False,
    }


def new_strategy_portfolio() -> Portfolio:
    return Portfolio.a_share(INITIAL_CASH_CNY)


def run_frozen_static_rebalance(
    portfolio: Portfolio, calendar: AcceptedSessionCalendar, *, signal_session: date,
    decision_at: datetime, execution_inputs: tuple[ExecutionInput, ...],
    target_weights: Mapping[str, float], slippage_bps: float,
    prior_stage_hash: str = "0" * 64,
) -> StaticRebalanceResult:
    if not isinstance(portfolio, Portfolio) or portfolio.lot_size != 100 \
            or portfolio.share_t_plus_one is not True \
            or portfolio.a_share_stamp_tax_schedule is not True:
        raise LiquidityShockContractError("portfolio does not match frozen A-share semantics")
    slippage = _finite(slippage_bps, "slippage_bps")
    if slippage not in SLIPPAGE_SCENARIOS_BPS:
        raise LiquidityShockContractError("slippage_bps must be exactly 20 or 50")
    weights = dict(target_weights)
    return run_static_rebalance(
        portfolio, calendar, signal_session=signal_session, decision_at=decision_at,
        execution_inputs=execution_inputs, target_weights=lambda _: weights,
        capacity_policy=CapacityPolicy(0.01, 0.01, "CNY"), max_positions=MAX_POSITIONS,
        slippage_bps=slippage, prior_stage_hash=prior_stage_hash,
    )
