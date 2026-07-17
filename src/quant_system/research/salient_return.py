"""Frozen, outcome-blind salient-return target formation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import math
from numbers import Real
from pathlib import Path
from statistics import median

from quant_system.backtest.capacity import CapacityPolicy
from quant_system.backtest.event_loop import (
    ExecutionInput,
    StaticRebalanceResult,
    run_static_rebalance,
)
from quant_system.backtest.portfolio import Portfolio
from quant_system.data import AcceptedSessionCalendar

RESEARCH_ID = "A_SHARE_SALIENT_RETURN_MISPRICING_V1_20260718"
VARIANT_ID = "LOW_ST_MONTHLY"
DEFINITION_PATH = Path("research/definitions/a_share_salient_return_mispricing_v1.json")
DEFINITION_SHA256 = "54f5a59823bf55c08a4f756cf902f3f1d5930ee0cea4347d22940989e7eb5a55"
SNAPSHOT_ID = "a_share_qfq_personal_research_20260716_v5"
SNAPSHOT_DIGEST = "da6160ddad3f5fcb21151dd0d3128ea7786be2a2014872a14f85635e783dba6b"
DATABASE_SHA256 = "e636bb80e300f89e46831e91275c6f2167e370e81a00b21b300e253f6107bee0"
SNAPSHOT_RECEIPT_FILENAME = "a_share_volume_unit_shares_v5_20260717.json"
SNAPSHOT_RECEIPT_SHA256 = "241be32158b9ab5cebbe92dfceeec2a889f3b56e681a1f764d7b6d257f21f17f"
COVERAGE_START, HISTORICAL_CUTOFF = date(2018, 1, 2), date(2026, 6, 30)
BENCHMARK_SYMBOL = "510300.SH"
INITIAL_CASH_CNY, MAX_POSITIONS, MIN_ELIGIBLE = 400_000.0, 15, 500
MIN_LISTED_SESSIONS, MIN_MEDIAN_AMOUNT_CNY = 252, 20_000_000.0
MIN_DAILY_RETURNS, DELTA, SLIPPAGE_BPS = 15, 0.7, 50.0
COMMON_PREFIXES = {
    "SH": ("600", "601", "603", "605", "688"),
    "SZ": ("000", "001", "002", "003", "300", "301"),
}


class SalientReturnContractError(ValueError): ...


def _finite(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise SalientReturnContractError(f"{name} must be finite numeric")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise SalientReturnContractError(f"{name} must be finite numeric")
    return parsed


def common_a_symbol(symbol: str) -> bool:
    if not isinstance(symbol, str) or symbol.count(".") != 1:
        return False
    code, suffix = symbol.split(".")
    return (
        len(code) == 6
        and code.isdigit()
        and suffix in COMMON_PREFIXES
        and code.startswith(COMMON_PREFIXES[suffix])
    )


@dataclass(frozen=True)
class MonthlySignal:
    """One security's exact complete-month return vector and D-state inputs."""

    symbol: str
    returns: tuple[float, ...]
    trailing_amounts_cny: tuple[float, ...]
    accepted_sessions_since_listing: int
    listed: bool
    delisted: bool
    is_st: bool
    is_suspended: bool
    is_limit_up: bool
    is_limit_down: bool

    def __post_init__(self) -> None:
        if not common_a_symbol(self.symbol):
            raise SalientReturnContractError("symbol must be a common A-share")
        if not isinstance(self.returns, tuple) or len(self.returns) < MIN_DAILY_RETURNS:
            raise SalientReturnContractError("returns must contain a complete month")
        parsed_returns = tuple(_finite(value, "return") for value in self.returns)
        if any(value <= -1.0 for value in parsed_returns):
            raise SalientReturnContractError("daily returns must exceed -1")
        if not isinstance(self.trailing_amounts_cny, tuple) or len(self.trailing_amounts_cny) < 20:
            raise SalientReturnContractError("twenty amount observations are required")
        if any(_finite(value, "amount") < 0.0 for value in self.trailing_amounts_cny):
            raise SalientReturnContractError("amount must be nonnegative CNY")
        if (
            type(self.accepted_sessions_since_listing) is not int
            or self.accepted_sessions_since_listing < 0
        ):
            raise SalientReturnContractError("listed-session count must be nonnegative int")
        flags = (
            self.listed,
            self.delisted,
            self.is_st,
            self.is_suspended,
            self.is_limit_up,
            self.is_limit_down,
        )
        if any(type(value) is not bool for value in flags):
            raise SalientReturnContractError("status fields must be boolean")


@dataclass(frozen=True)
class SalienceFeature:
    score: float
    sigmas: tuple[float, ...]
    competition_ranks: tuple[int, ...]
    normalized_weights: tuple[float, ...]


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


def salience_feature(
    returns: Sequence[float], reference_returns: Sequence[float]
) -> SalienceFeature:
    """Compute the exact binary64 competition-rank salience tendency."""
    values = tuple(_finite(value, "return") for value in returns)
    references = tuple(_finite(value, "reference return") for value in reference_returns)
    if len(values) < MIN_DAILY_RETURNS or len(values) != len(references):
        raise SalientReturnContractError("return and reference vectors must align")
    if any(value <= -1.0 for value in values):
        raise SalientReturnContractError("daily returns must exceed -1")
    sigmas = tuple(
        abs(value - reference) / (abs(value) + abs(reference) + 0.1)
        for value, reference in zip(values, references, strict=True)
    )
    ranks = tuple(1 + sum(other > sigma for other in sigmas) for sigma in sigmas)
    raw_weights = tuple(DELTA ** (rank - 1) for rank in ranks)
    raw_mean = math.fsum(raw_weights) / len(raw_weights)
    weights = tuple(weight / raw_mean for weight in raw_weights)
    weighted = math.fsum(
        weight * value for weight, value in zip(weights, values, strict=True)
    ) / len(values)
    ordinary = math.fsum(values) / len(values)
    score = weighted - ordinary
    if not all(math.isfinite(value) for value in (*sigmas, *weights, score)):
        raise SalientReturnContractError("salience feature is nonfinite")
    return SalienceFeature(score, sigmas, ranks, weights)


def _eligible(signal: MonthlySignal, expected_returns: int) -> bool:
    return (
        len(signal.returns) == expected_returns
        and signal.accepted_sessions_since_listing >= MIN_LISTED_SESSIONS
        and signal.listed
        and not signal.delisted
        and not signal.is_st
        and not signal.is_suspended
        and not signal.is_limit_up
        and not signal.is_limit_down
        and median(signal.trailing_amounts_cny[-20:]) >= MIN_MEDIAN_AMOUNT_CNY
    )


def build_monthly_target(
    signals: Sequence[MonthlySignal],
    calendar: AcceptedSessionCalendar,
    *,
    decision_date: date,
    decision_at: datetime,
    execution_inputs: tuple[ExecutionInput, ...],
) -> tuple[Target | None, DecisionAudit]:
    """Build the sole low-ST target without calculating any post-entry return."""
    if not isinstance(calendar, AcceptedSessionCalendar):
        raise TypeError("calendar must be an AcceptedSessionCalendar")
    if type(decision_date) is not date or not isinstance(decision_at, datetime):
        raise SalientReturnContractError("decision identity is invalid")
    try:
        position = calendar.session_dates.index(decision_date)
    except ValueError as exc:
        raise SalientReturnContractError("decision is not an accepted session") from exc
    signal_session = calendar.session_on(decision_date, as_of=decision_at)
    if decision_at != signal_session.close_at + timedelta(minutes=30):
        raise SalientReturnContractError("decision_at must equal D close plus 30 minutes")
    execution_session = calendar.next_session(decision_date, as_of=decision_at)
    if (execution_session.session_date.year, execution_session.session_date.month) == (
        decision_date.year,
        decision_date.month,
    ):
        raise SalientReturnContractError("decision must be the last accepted session of month")
    month_dates = tuple(
        day
        for day in calendar.session_dates[: position + 1]
        if (day.year, day.month) == (decision_date.year, decision_date.month)
    )
    if len(month_dates) < MIN_DAILY_RETURNS:
        raise SalientReturnContractError("complete month has too few daily returns")
    by_symbol: dict[str, MonthlySignal] = {}
    for item in signals:
        if not isinstance(item, MonthlySignal) or item.symbol in by_symbol:
            raise SalientReturnContractError("signals must have unique MonthlySignal symbols")
        by_symbol[item.symbol] = item
    eligible = tuple(
        by_symbol[symbol]
        for symbol in sorted(by_symbol)
        if _eligible(by_symbol[symbol], len(month_dates))
    )
    references = (
        tuple(
            math.fsum(item.returns[index] for item in eligible) / len(eligible)
            for index in range(len(month_dates))
        )
        if eligible
        else ()
    )
    ranked = tuple(
        sorted(
            ((item.symbol, salience_feature(item.returns, references).score) for item in eligible),
            key=lambda row: (row[1], row[0]),
        )
    )
    selected = ranked[:MAX_POSITIONS]
    panels: dict[str, ExecutionInput] = {}
    for item in execution_inputs:
        if not isinstance(item, ExecutionInput) or item.symbol in panels:
            raise SalientReturnContractError("execution inputs must have unique symbols")
        panels[item.symbol] = item
    panel_complete = len(selected) == MAX_POSITIONS and all(
        symbol in panels for symbol, _ in selected
    )
    valid = len(eligible) >= MIN_ELIGIBLE and len(ranked) >= MAX_POSITIONS and panel_complete
    audit = DecisionAudit(
        VARIANT_ID,
        decision_date,
        len(eligible),
        len(ranked),
        panel_complete,
        valid,
    )
    if not valid:
        return None, audit
    symbols = tuple(symbol for symbol, _ in selected)
    return (
        Target(
            VARIANT_ID,
            decision_date,
            execution_session.session_date,
            len(eligible),
            len(ranked),
            symbols,
            selected,
            tuple((symbol, 1 / MAX_POSITIONS) for symbol in symbols),
        ),
        audit,
    )


def qfq_execution_limits(
    qfq_open: float,
    raw_open: float,
    up_limit: float | None,
    down_limit: float | None,
) -> tuple[float | None, float | None]:
    adjusted, raw = _finite(qfq_open, "qfq open"), _finite(raw_open, "raw open")
    if adjusted <= 0.0 or raw <= 0.0:
        raise SalientReturnContractError("execution opens must be positive")
    limits = tuple(
        None if value is None else _finite(value, "execution limit")
        for value in (up_limit, down_limit)
    )
    if any(value is not None and value <= 0.0 for value in limits):
        raise SalientReturnContractError("execution limits must be positive")
    ratio = adjusted / raw
    return (
        None if limits[0] is None else limits[0] * ratio,
        None if limits[1] is None else limits[1] * ratio,
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
    prior_stage_hash: str = "0" * 64,
) -> StaticRebalanceResult:
    if (
        not isinstance(portfolio, Portfolio)
        or portfolio.lot_size != 100
        or portfolio.share_t_plus_one is not True
        or portfolio.a_share_stamp_tax_schedule is not True
    ):
        raise SalientReturnContractError("portfolio does not match frozen A-share semantics")
    return run_static_rebalance(
        portfolio,
        calendar,
        signal_session=signal_session,
        decision_at=decision_at,
        execution_inputs=execution_inputs,
        target_weights=lambda _: dict(target_weights),
        capacity_policy=CapacityPolicy(0.01, 0.01, "CNY"),
        max_positions=MAX_POSITIONS,
        slippage_bps=SLIPPAGE_BPS,
        prior_stage_hash=prior_stage_hash,
    )
