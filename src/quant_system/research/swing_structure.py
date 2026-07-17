"""Frozen Swing Count targets and shared-engine entry point."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import math
from pathlib import Path

from quant_system.backtest.capacity import CapacityPolicy
from quant_system.backtest.event_loop import (
    ExecutionInput,
    StaticRebalanceResult,
    run_static_rebalance,
)
from quant_system.backtest.portfolio import Portfolio
from quant_system.data import AcceptedSessionCalendar

RESEARCH_ID = "A_SHARE_SWING_STRUCTURE_PARTICIPATION_CONFIRMED_TREND_V1_20260718"
DEFINITION_PATH = Path(
    "research/definitions/a_share_swing_structure_participation_confirmed_trend_v1.json"
)
DEFINITION_SHA256 = "bfcd74a735196c0501cb15394775a77607537a4bf8ae029362d19a68e5c76a63"
SNAPSHOT_ID = "a_share_qfq_personal_research_20260716_v5"
SNAPSHOT_DIGEST = "da6160ddad3f5fcb21151dd0d3128ea7786be2a2014872a14f85635e783dba6b"
DATABASE_SHA256 = "e636bb80e300f89e46831e91275c6f2167e370e81a00b21b300e253f6107bee0"
SNAPSHOT_RECEIPT_FILENAME = "a_share_volume_unit_shares_v5_20260717.json"
SNAPSHOT_RECEIPT_SHA256 = "241be32158b9ab5cebbe92dfceeec2a889f3b56e681a1f764d7b6d257f21f17f"
COVERAGE_START, HISTORICAL_CUTOFF = date(2018, 1, 2), date(2026, 6, 30)
BENCHMARK_SYMBOL = "510300.SH"
INITIAL_CASH_CNY, MAX_POSITIONS, MIN_ELIGIBLE = 400_000.0, 15, 500
MIN_LISTED_SESSIONS, MIN_MEDIAN_AMOUNT_CNY = 252, 20_000_000.0
SLIPPAGE_SCENARIOS_BPS = (20.0, 50.0)
COMMON_PREFIXES = {
    "SH": ("600", "601", "603", "605", "688"),
    "SZ": ("000", "001", "002", "003", "300", "301"),
}


class SwingStructureContractError(ValueError): ...


@dataclass(frozen=True)
class Variant:
    order: int
    variant_id: str
    window_sessions: int


VARIANTS = (Variant(1, "SWING20", 20), Variant(2, "SWING60", 60))


@dataclass(frozen=True)
class SignalBar:
    session_date: date
    symbol: str
    close_cny: float
    amount_cny: float
    eligible: bool = True

    def __post_init__(self) -> None:
        if (
            type(self.session_date) is not date
            or not isinstance(self.symbol, str)
            or not self.symbol
        ):
            raise SwingStructureContractError("signal identity is invalid")
        values = (self.close_cny, self.amount_cny)
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in values
        ):
            raise SwingStructureContractError("signal values must be finite")
        if (
            self.close_cny <= 0
            or self.amount_cny < 0
            or type(self.eligible) is not bool
        ):
            raise SwingStructureContractError("signal values are invalid")


@dataclass(frozen=True)
class Target:
    variant_id: str
    decision_date: date
    execution_date: date
    eligible_count: int
    candidate_count: int
    selected_symbols: tuple[str, ...]
    selected_scores: tuple[tuple[str, float, float], ...]
    target_weights: tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class DecisionAudit:
    variant_id: str
    decision_date: date
    eligible_count: int
    candidate_count: int
    execution_panel_complete: bool
    valid: bool


def _feature_values(
    closes: Sequence[float], amounts: Sequence[float]
) -> tuple[float, float] | None:
    if len(closes) < 3 or len(closes) != len(amounts):
        return None
    if any(not math.isfinite(value) or value <= 0 for value in closes):
        return None
    if any(not math.isfinite(value) or value < 0 for value in amounts):
        return None
    highs = [
        i
        for i in range(1, len(closes) - 1)
        if closes[i] > closes[i - 1] and closes[i] >= closes[i + 1]
    ]
    lows = [
        i
        for i in range(1, len(closes) - 1)
        if closes[i] < closes[i - 1] and closes[i] <= closes[i + 1]
    ]
    if len(highs) < 2 or len(lows) < 2 or closes[-1] <= closes[0]:
        return None
    higher = sum(closes[b] > closes[a] for a, b in zip(highs, highs[1:]))
    higher += sum(closes[b] > closes[a] for a, b in zip(lows, lows[1:]))
    persistence = higher / ((len(highs) - 1) + (len(lows) - 1))
    total = math.fsum(amounts[1:])
    if total <= 0:
        return None
    participation = math.fsum(
        amounts[i] for i in range(1, len(closes)) if closes[i] > closes[i - 1]
    ) / total
    if persistence <= 0.5 or participation <= 0.5:
        return None
    return persistence, participation


def _feature(history: Sequence[SignalBar]) -> tuple[float, float] | None:
    if any(not row.eligible for row in history):
        return None
    return _feature_values(
        tuple(row.close_cny for row in history),
        tuple(row.amount_cny for row in history),
    )


def build_decision_targets(
    rows: Sequence[SignalBar],
    calendar: AcceptedSessionCalendar,
    *,
    decision_date: date,
    decision_at: datetime,
    execution_inputs: tuple[ExecutionInput, ...],
) -> tuple[tuple[Target, ...], tuple[DecisionAudit, ...]]:
    """Form the exact close-pivot targets; caller supplies next-open panels."""
    if not isinstance(calendar, AcceptedSessionCalendar):
        raise TypeError("calendar must be an AcceptedSessionCalendar")
    by_key: dict[tuple[date, str], SignalBar] = {}
    for row in rows:
        if not isinstance(row, SignalBar) or (row.session_date, row.symbol) in by_key:
            raise SwingStructureContractError("rows must be unique SignalBar values")
        by_key[row.session_date, row.symbol] = row
    try:
        position = calendar.session_dates.index(decision_date)
    except ValueError as exc:
        raise SwingStructureContractError("decision is not an accepted session") from exc
    signal = calendar.session_on(decision_date, as_of=decision_at)
    if decision_at != signal.close_at + timedelta(minutes=30):
        raise SwingStructureContractError("decision_at must equal D close plus 30 minutes")
    execution = calendar.next_session(decision_date, as_of=decision_at)
    panels = {item.symbol: item for item in execution_inputs}
    if len(panels) != len(execution_inputs):
        raise SwingStructureContractError("duplicate execution symbol")
    symbols = sorted({symbol for _, symbol in by_key if symbol != BENCHMARK_SYMBOL})
    targets: list[Target] = []
    audits: list[DecisionAudit] = []
    for variant in VARIANTS:
        if position + 1 < variant.window_sessions:
            raise SwingStructureContractError("required accepted-session history is missing")
        days = calendar.session_dates[
            position - variant.window_sessions + 1 : position + 1
        ]
        scores: list[tuple[str, float, float]] = []
        eligible = 0
        for symbol in symbols:
            history = [by_key.get((day, symbol)) for day in days]
            if any(row is None or not row.eligible for row in history):
                continue
            eligible += 1
            feature = _feature(tuple(row for row in history if row is not None))
            if feature is not None:
                scores.append((symbol, *feature))
        ranked = tuple(sorted(scores, key=lambda item: (-item[1], -item[2], item[0])))
        selected = ranked[:MAX_POSITIONS]
        complete = len(selected) == MAX_POSITIONS and all(
            item[0] in panels for item in selected
        )
        valid = eligible >= MIN_ELIGIBLE and len(ranked) >= MAX_POSITIONS and complete
        audits.append(
            DecisionAudit(
                variant.variant_id,
                decision_date,
                eligible,
                len(ranked),
                complete,
                valid,
            )
        )
        if valid:
            selected_symbols = tuple(item[0] for item in selected)
            targets.append(
                Target(
                    variant.variant_id,
                    decision_date,
                    execution.session_date,
                    eligible,
                    len(ranked),
                    selected_symbols,
                    selected,
                    tuple((symbol, 1 / MAX_POSITIONS) for symbol in selected_symbols),
                )
            )
    return tuple(targets), tuple(audits)


def qfq_execution_limits(
    qfq_open: float,
    raw_open: float,
    up_limit: float | None,
    down_limit: float | None,
) -> tuple[float | None, float | None]:
    """Put raw statutory limits on the same scale as a qfq execution price."""
    values = (qfq_open, raw_open)
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
        for value in values
    ):
        raise SwingStructureContractError("execution opens must be positive and finite")
    for value in (up_limit, down_limit):
        if value is not None and (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0
        ):
            raise SwingStructureContractError("execution limits must be positive and finite")
    ratio = qfq_open / raw_open
    return (
        None if up_limit is None else up_limit * ratio,
        None if down_limit is None else down_limit * ratio,
    )


def new_strategy_portfolio() -> Portfolio:
    return Portfolio.a_share(INITIAL_CASH_CNY)


def run_frozen_static_rebalance(
    portfolio: Portfolio,
    calendar: AcceptedSessionCalendar,
    *,
    signal_session: date,
    decision_at: datetime,
    execution_inputs: tuple[ExecutionInput, ...],
    target_weights: Mapping[str, float],
    slippage_bps: float,
    prior_stage_hash: str = "0" * 64,
) -> StaticRebalanceResult:
    if (
        not isinstance(portfolio, Portfolio)
        or portfolio.lot_size != 100
        or portfolio.share_t_plus_one is not True
        or portfolio.a_share_stamp_tax_schedule is not True
    ):
        raise SwingStructureContractError("portfolio does not match frozen A-share semantics")
    if slippage_bps not in SLIPPAGE_SCENARIOS_BPS:
        raise SwingStructureContractError("slippage_bps must be exactly 20 or 50")
    return run_static_rebalance(
        portfolio,
        calendar,
        signal_session=signal_session,
        decision_at=decision_at,
        execution_inputs=execution_inputs,
        target_weights=lambda _: dict(target_weights),
        capacity_policy=CapacityPolicy(0.01, 0.01, "CNY"),
        max_positions=MAX_POSITIONS,
        slippage_bps=slippage_bps,
        prior_stage_hash=prior_stage_hash,
    )
