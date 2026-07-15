"""Frozen relative-strength mechanics with no data-access path.

The module stops at deterministic target formation, one existing event-loop
rebalance, split assignment, and aggregate inference. Formal data execution
must first pass :func:`load_formal_evidence`; synthetic diagnostics use a
separate function and can never be labelled strategy evidence.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
import hashlib
import json
import math
from numbers import Real
import os
from pathlib import Path
import stat
from typing import Any

import numpy as np

from quant_system.backtest.capacity import CapacityPolicy
from quant_system.backtest.event_loop import (
    ExecutionInput,
    StaticRebalanceResult,
    run_static_rebalance,
)
from quant_system.backtest.portfolio import Portfolio
from quant_system.data import AcceptedSessionCalendar, SourceIdentity
from quant_system.research.event_cohort import SplitWindow, linear_quantile


RESEARCH_ID = "A_SHARE_RELATIVE_STRENGTH_MEDIUM_TERM_MOMENTUM_V1_20260715"
QUALIFICATION_RESEARCH_ID = (
    "A_SHARE_RELATIVE_STRENGTH_MEDIUM_TERM_MOMENTUM_DATA_QUALIFICATION_V1_20260715"
)
DEFINITION_PATH = Path(
    "research/definitions/a_share_relative_strength_medium_term_momentum_v1.json"
)
DEFINITION_SHA256 = "84a0d0c80e2e072caf13474873e92de0a2ce7edc4878bcdad2006dfdd46a02ac"
QUALIFICATION_PATH = Path(
    "research/reports/a_share_relative_strength_medium_term_momentum_data_qualification_v1.json"
)
QUALIFICATION_SHA256 = "92b44d66b0eeebdb3b37c63be9639085ba2e4d5e17d90ca3ed3a0ec3ec300ee0"
ACCEPTED_SOURCE_COMMIT = "7160d07459fa0514f48beca00f34278ffa13c98c"
ACCEPTED_SOURCE_TREE = "758fa2b2bb836a0c5cfbf9763d4973f202f117c6"
BENCHMARK_SYMBOL = "510300.SH"
INITIAL_CASH_CNY = 400_000.0
MAX_POSITIONS = 15
MINIMUM_BASE_ELIGIBLE = 500
MINIMUM_AMOUNT_CNY = 20_000_000.0
BOARD_LOT = 100
SLIPPAGE_SCENARIOS_BPS = (20.0, 50.0)
BONFERRONI_ALPHA = 0.05 / 12.0
BOOTSTRAP_BLOCK_MONTHS = 3
BOOTSTRAP_DRAWS = 10_000
_MAX_BOOTSTRAP_CELLS = 2_000_000
_SHA256 = frozenset("0123456789abcdef")
_COMMON_A_BOARDS = frozenset({"SSE_MAIN", "SSE_STAR", "SZSE_MAIN", "SZSE_CHINEXT"})


class RelativeStrengthContractError(ValueError):
    """One frozen strategy or evidence condition was violated."""


@dataclass(frozen=True)
class Variant:
    order: int
    variant_id: str
    lookback_sessions: int
    volatility_filter_enabled: bool


VARIANTS = (
    Variant(1, "RS60_BASE", 60, False),
    Variant(2, "RS60_VOL20_MEDIAN", 60, True),
    Variant(3, "RS120_BASE", 120, False),
    Variant(4, "RS120_VOL20_MEDIAN", 120, True),
)

SPLITS = (
    SplitWindow("development_2019_2021", date(2019, 1, 1), date(2021, 12, 31)),
    SplitWindow("validation_2022_2023", date(2022, 1, 1), date(2023, 12, 31)),
    SplitWindow(
        "retrospective_holdout_2024_2026h1", date(2024, 1, 1), date(2026, 6, 30)
    ),
    SplitWindow("embargo_2026h2", date(2026, 7, 1), date(2026, 12, 31)),
    SplitWindow("prospective_forward_2027_2029", date(2027, 1, 1), date(2029, 12, 31)),
)
GATED_SPLITS = (
    "validation_2022_2023",
    "retrospective_holdout_2024_2026h1",
    "prospective_forward_2027_2029",
)
HISTORICAL_GATED_SPLITS = GATED_SPLITS[:2]
ASSIGNABLE_SPLITS = ("development_2019_2021", *GATED_SPLITS)
MINIMUM_INTERVALS = {
    "validation_2022_2023": 20,
    "retrospective_holdout_2024_2026h1": 24,
    "prospective_forward_2027_2029": 30,
}
_SPLIT_BY_ID = {split.split_id: split for split in SPLITS}


def _month(value: date) -> tuple[int, int]:
    return value.year, value.month


def _month_ordinal(value: date) -> int:
    return value.year * 12 + value.month


def _entry_exit_split(entry_date: date, exit_date: date) -> str | None:
    matches = tuple(
        split.split_id
        for split in SPLITS
        if split.contains(entry_date) and split.contains(exit_date)
    )
    if len(matches) > 1:
        raise RelativeStrengthContractError("entry and exit match multiple splits")
    return matches[0] if matches else None


def _finite(value: object, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise RelativeStrengthContractError(f"{name} must be finite numeric")
    parsed = float(value)
    if not math.isfinite(parsed) or (positive and parsed <= 0.0):
        qualifier = "positive finite" if positive else "finite"
        raise RelativeStrengthContractError(f"{name} must be {qualifier}")
    return parsed


def _digest(value: object, name: str) -> str:
    digest = str(value)
    if len(digest) != 64 or any(character not in _SHA256 for character in digest):
        raise RelativeStrengthContractError(f"{name} must be a lowercase SHA-256 digest")
    return digest


@dataclass(frozen=True)
class SignalBar:
    session_date: date
    symbol: str
    total_return_index: float
    amount_cny: float
    accepted_sessions_since_listing: int
    listed: bool
    delisted: bool
    is_st: bool
    is_suspended: bool
    security_type: str
    board: str
    source: SourceIdentity

    def __post_init__(self) -> None:
        if type(self.session_date) is not date:
            raise RelativeStrengthContractError("session_date must be a date")
        if not isinstance(self.symbol, str) or not self.symbol or self.symbol != self.symbol.strip():
            raise RelativeStrengthContractError("symbol must be nonempty trimmed text")
        _finite(self.total_return_index, "total_return_index", positive=True)
        if _finite(self.amount_cny, "amount_cny") < 0.0:
            raise RelativeStrengthContractError("amount_cny must be nonnegative")
        if (
            type(self.accepted_sessions_since_listing) is not int
            or self.accepted_sessions_since_listing < 0
        ):
            raise RelativeStrengthContractError(
                "accepted_sessions_since_listing must be a nonnegative integer"
            )
        if any(
            type(value) is not bool
            for value in (self.listed, self.delisted, self.is_st, self.is_suspended)
        ):
            raise RelativeStrengthContractError("status fields must be boolean")
        if not isinstance(self.security_type, str) or not self.security_type:
            raise RelativeStrengthContractError("security_type must be nonempty")
        if not isinstance(self.board, str) or not self.board:
            raise RelativeStrengthContractError("board must be nonempty")
        if not isinstance(self.source, SourceIdentity):
            raise RelativeStrengthContractError("source must be a SourceIdentity")


@dataclass(frozen=True)
class RelativeStrengthTarget:
    variant_id: str
    variant_order: int
    decision_date: date
    execution_date: date
    decision_at: datetime
    base_eligible_count: int
    ranked_candidate_count: int
    volatility_median: float
    selected_symbols: tuple[str, ...]
    target_weights: tuple[tuple[str, float], ...]
    selected_relative_strength: tuple[tuple[str, float], ...]


def build_monthly_targets(
    rows: Sequence[SignalBar],
    calendar: AcceptedSessionCalendar,
    *,
    decision_at_by_session: Mapping[date, datetime],
) -> tuple[RelativeStrengthTarget, ...]:
    """Build all four frozen targets at each complete month-end decision."""

    if not isinstance(calendar, AcceptedSessionCalendar):
        raise TypeError("calendar must be an AcceptedSessionCalendar")
    frozen = tuple(rows)
    if not frozen or any(not isinstance(row, SignalBar) for row in frozen):
        raise RelativeStrengthContractError("rows must contain SignalBar values")
    by_key: dict[tuple[date, str], SignalBar] = {}
    for row in frozen:
        key = (row.session_date, row.symbol)
        if key in by_key:
            raise RelativeStrengthContractError("duplicate symbol-session key")
        by_key[key] = row

    dates = calendar.session_dates
    month_ends = tuple(
        index
        for index in range(len(dates) - 1)
        if (dates[index].year, dates[index].month)
        != (dates[index + 1].year, dates[index + 1].month)
        and index >= 120
    )
    results: list[RelativeStrengthTarget] = []
    symbols = tuple(sorted({row.symbol for row in frozen} - {BENCHMARK_SYMBOL}))
    for decision_index in month_ends:
        decision_date = dates[decision_index]
        try:
            decision_at = decision_at_by_session[decision_date]
        except (KeyError, TypeError) as exc:
            raise RelativeStrengthContractError("every month-end requires an explicit decision_at") from exc
        signal_session = calendar.session_on(decision_date, as_of=decision_at)
        if decision_at != signal_session.close_at + timedelta(minutes=30):
            raise RelativeStrengthContractError("decision_at must equal signal close plus 30 minutes")
        execution_session = calendar.next_session(decision_date, as_of=decision_at)
        if decision_at >= execution_session.open_at:
            raise RelativeStrengthContractError("decision_at must precede next-session open")
        history_dates = dates[decision_index - 120 : decision_index + 1]
        for session_date in history_dates:
            calendar.session_on(session_date, as_of=decision_at)
        benchmark = _history(
            by_key, BENCHMARK_SYMBOL, history_dates, decision_at, require_common_a=False
        )
        if benchmark is None:
            raise RelativeStrengthContractError("benchmark lacks complete point-in-time history")
        features: dict[str, tuple[float, float, float]] = {}
        for symbol in symbols:
            history = _history(
                by_key, symbol, history_dates, decision_at, require_common_a=True
            )
            if history is None or not _current_eligible(history[-1]):
                continue
            amount_median = _median(tuple(row.amount_cny for row in history[-20:]))
            if amount_median < MINIMUM_AMOUNT_CNY:
                continue
            volatility = _sample_std(
                tuple(
                    history[index].total_return_index
                    / history[index - 1].total_return_index
                    - 1.0
                    for index in range(len(history) - 20, len(history))
                )
            )
            features[symbol] = (
                _relative_strength(history, benchmark, 60),
                _relative_strength(history, benchmark, 120),
                volatility,
            )
        if len(features) < MINIMUM_BASE_ELIGIBLE:
            raise RelativeStrengthContractError(
                f"{decision_date} has fewer than {MINIMUM_BASE_ELIGIBLE} base-eligible names"
            )
        volatility_median = _median(tuple(value[2] for value in features.values()))
        for variant in VARIANTS:
            offset = 0 if variant.lookback_sessions == 60 else 1
            candidates = tuple(
                sorted(
                    (
                        (symbol, value[offset])
                        for symbol, value in features.items()
                        if value[offset] > 0.0
                        and (not variant.volatility_filter_enabled or value[2] <= volatility_median)
                    ),
                    key=lambda item: (-item[1], item[0]),
                )
            )
            if len(candidates) < MAX_POSITIONS:
                raise RelativeStrengthContractError(
                    f"{decision_date} {variant.variant_id} has fewer than 15 ranked candidates"
                )
            selected = candidates[:MAX_POSITIONS]
            symbols_selected = tuple(symbol for symbol, _ in selected)
            weight = 1.0 / MAX_POSITIONS
            results.append(
                RelativeStrengthTarget(
                    variant.variant_id,
                    variant.order,
                    decision_date,
                    execution_session.session_date,
                    decision_at,
                    len(features),
                    len(candidates),
                    volatility_median,
                    symbols_selected,
                    tuple((symbol, weight) for symbol in symbols_selected),
                    selected,
                )
            )
    return tuple(results)


def _history(
    by_key: Mapping[tuple[date, str], SignalBar],
    symbol: str,
    dates: tuple[date, ...],
    decision_at: datetime,
    *,
    require_common_a: bool,
) -> tuple[SignalBar, ...] | None:
    rows: list[SignalBar] = []
    for session_date in dates:
        row = by_key.get((session_date, symbol))
        if row is None or row.source.available_at > decision_at:
            return None
        rows.append(row)
    if require_common_a and (
        rows[-1].security_type != "COMMON_A" or rows[-1].board not in _COMMON_A_BOARDS
    ):
        return None
    return tuple(rows)


def _current_eligible(row: SignalBar) -> bool:
    return (
        row.listed
        and not row.delisted
        and not row.is_st
        and not row.is_suspended
        and row.accepted_sessions_since_listing >= 252
    )


def _relative_strength(
    stock: tuple[SignalBar, ...], benchmark: tuple[SignalBar, ...], lookback: int
) -> float:
    stock_factor = stock[-1].total_return_index / stock[-1 - lookback].total_return_index
    benchmark_factor = (
        benchmark[-1].total_return_index / benchmark[-1 - lookback].total_return_index
    )
    return _finite(stock_factor / benchmark_factor - 1.0, "relative_strength")


def _median(values: Sequence[float]) -> float:
    ordered = tuple(sorted(_finite(value, "median value") for value in values))
    if not ordered:
        raise RelativeStrengthContractError("median requires values")
    midpoint = len(ordered) // 2
    return (
        ordered[midpoint]
        if len(ordered) % 2
        else math.fsum((ordered[midpoint - 1], ordered[midpoint])) / 2.0
    )


def _sample_std(values: Sequence[float]) -> float:
    frozen = tuple(_finite(value, "return") for value in values)
    if len(frozen) < 2:
        raise RelativeStrengthContractError("sample volatility requires two observations")
    mean = math.fsum(frozen) / len(frozen)
    variance = math.fsum((value - mean) ** 2 for value in frozen) / (len(frozen) - 1)
    return _finite(math.sqrt(variance), "sample volatility")


@dataclass(frozen=True)
class ResidualAllocation:
    admitted_symbols: tuple[str, ...]
    trapped_symbols: tuple[str, ...]
    trapped_market_value: float
    residual_investable_nav: float
    target_weights: tuple[tuple[str, float], ...]


def residual_target_weights(
    ranked_symbols: Sequence[str],
    trapped_market_values: Mapping[str, float],
    *,
    nav: float,
) -> ResidualAllocation:
    """Reserve trapped slots and equal-weight only residual investable NAV."""

    ranked = tuple(ranked_symbols)
    if len(ranked) < MAX_POSITIONS or len(ranked) != len(set(ranked)):
        raise RelativeStrengthContractError("ranked_symbols must be unique with at least 15 names")
    if any(not isinstance(symbol, str) or not symbol for symbol in ranked):
        raise RelativeStrengthContractError("ranked symbols must be nonempty text")
    trapped = tuple(sorted(trapped_market_values))
    if len(trapped) > MAX_POSITIONS or set(trapped) & set(ranked):
        raise RelativeStrengthContractError("off-target trapped symbols must be disjoint and <= 15")
    trapped_values = tuple(
        _finite(trapped_market_values[symbol], f"trapped mark {symbol}") for symbol in trapped
    )
    if any(value < 0.0 for value in trapped_values):
        raise RelativeStrengthContractError("trapped market values must be nonnegative")
    trapped_total = math.fsum(trapped_values)
    total_nav = _finite(nav, "nav", positive=True)
    if trapped_total < 0.0 or trapped_total > total_nav + 1e-9:
        raise RelativeStrengthContractError("trapped market value must lie within NAV")
    residual = max(0.0, total_nav - trapped_total)
    admitted = ranked[: MAX_POSITIONS - len(trapped)]
    per_name = residual / len(admitted) / total_nav if admitted else 0.0
    return ResidualAllocation(
        admitted,
        trapped,
        trapped_total,
        residual,
        tuple((symbol, per_name) for symbol in admitted),
    )


def new_strategy_portfolio() -> Portfolio:
    """Return the frozen CNY 400,000 A-share portfolio implementation."""

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
    """Apply one frozen target through the existing V2 event loop and costs."""

    if not isinstance(portfolio, Portfolio) or (
        portfolio.lot_size != BOARD_LOT
        or portfolio.share_t_plus_one is not True
        or portfolio.a_share_stamp_tax_schedule is not True
        or portfolio.costs.commission_rate != 0.0003
        or portfolio.costs.minimum_commission != 5.0
        or portfolio.costs.sell_tax_rate != 0.0
    ):
        raise RelativeStrengthContractError("portfolio does not match frozen A-share costs")
    slippage = _finite(slippage_bps, "slippage_bps")
    if slippage not in SLIPPAGE_SCENARIOS_BPS:
        raise RelativeStrengthContractError("slippage_bps must be exactly 20 or 50")
    frozen_weights = dict(target_weights)
    return run_static_rebalance(
        portfolio,
        calendar,
        signal_session=signal_session,
        decision_at=decision_at,
        execution_inputs=execution_inputs,
        target_weights=lambda _: frozen_weights,
        capacity_policy=CapacityPolicy(0.01, 0.01, "CNY"),
        max_positions=MAX_POSITIONS,
        slippage_bps=slippage,
        prior_stage_hash=prior_stage_hash,
    )


@dataclass(frozen=True)
class MonthlyObservation:
    variant_id: str
    signal_date: date
    entry_date: date
    exit_date: date
    strategy_return: float
    benchmark_return: float

    def __post_init__(self) -> None:
        if self.variant_id not in {variant.variant_id for variant in VARIANTS}:
            raise RelativeStrengthContractError("unknown frozen variant")
        if any(
            type(value) is not date
            for value in (self.signal_date, self.entry_date, self.exit_date)
        ):
            raise RelativeStrengthContractError("observation dates must be date values")
        if not self.signal_date < self.entry_date < self.exit_date:
            raise RelativeStrengthContractError("observation dates must satisfy signal < entry < exit")
        _finite(self.strategy_return, "strategy_return")
        _finite(self.benchmark_return, "benchmark_return")
        if self.strategy_return <= -1.0 or self.benchmark_return <= -1.0:
            raise RelativeStrengthContractError("monthly returns must exceed -100%")


@dataclass(frozen=True)
class AssignedObservation:
    variant_id: str
    split_id: str
    signal_date: date
    entry_date: date
    exit_date: date
    strategy_return: float
    benchmark_return: float

    def __post_init__(self) -> None:
        if self.variant_id not in {variant.variant_id for variant in VARIANTS}:
            raise RelativeStrengthContractError("unknown frozen variant")
        if self.split_id not in ASSIGNABLE_SPLITS:
            raise RelativeStrengthContractError("assigned observation uses an unknown split")
        if any(
            type(value) is not date
            for value in (self.signal_date, self.entry_date, self.exit_date)
        ) or not self.signal_date < self.entry_date < self.exit_date:
            raise RelativeStrengthContractError("assigned observation dates are invalid")
        _finite(self.strategy_return, "strategy_return")
        _finite(self.benchmark_return, "benchmark_return")
        if self.strategy_return <= -1.0 or self.benchmark_return <= -1.0:
            raise RelativeStrengthContractError("monthly returns must exceed -100%")
        split = _SPLIT_BY_ID[self.split_id]
        if not split.contains(self.entry_date) or not split.contains(self.exit_date):
            raise RelativeStrengthContractError("entry and exit must lie inside the declared split")


@dataclass(frozen=True)
class DecisionAudit:
    signal_date: date
    entry_date: date
    exit_date: date
    valid: bool
    invalid_reason: str | None = None

    def __post_init__(self) -> None:
        if any(
            type(value) is not date
            for value in (self.signal_date, self.entry_date, self.exit_date)
        ) or not self.signal_date < self.entry_date < self.exit_date:
            raise RelativeStrengthContractError("audit dates must satisfy signal < entry < exit")
        if type(self.valid) is not bool:
            raise RelativeStrengthContractError("audit valid must be boolean")
        if self.valid and self.invalid_reason is not None:
            raise RelativeStrengthContractError("valid audit cannot have an invalid reason")
        if not self.valid and (
            not isinstance(self.invalid_reason, str) or not self.invalid_reason.strip()
        ):
            raise RelativeStrengthContractError("invalid audit requires a reason")

    @property
    def identity(self) -> tuple[date, date, date]:
        return self.signal_date, self.entry_date, self.exit_date


@dataclass(frozen=True)
class GatedDecisionLedger:
    variant_id: str
    split_id: str
    declared_start: date
    declared_end: date
    decisions: tuple[DecisionAudit, ...]

    def __post_init__(self) -> None:
        if self.variant_id not in {variant.variant_id for variant in VARIANTS}:
            raise RelativeStrengthContractError("ledger uses an unknown frozen variant")
        if self.split_id not in GATED_SPLITS:
            raise RelativeStrengthContractError("ledger must use a gated split")
        split = _SPLIT_BY_ID[self.split_id]
        if (self.declared_start, self.declared_end) != (split.start, split.end):
            raise RelativeStrengthContractError("declared split bounds do not match the contract")
        if type(self.decisions) is not tuple or not self.decisions or any(
            not isinstance(item, DecisionAudit) for item in self.decisions
        ):
            raise RelativeStrengthContractError("ledger decisions must be a nonempty tuple")
        if self.decisions != tuple(sorted(self.decisions, key=lambda item: item.entry_date)):
            raise RelativeStrengthContractError("ledger decisions must be ordered by entry date")
        if len({item.identity for item in self.decisions}) != len(self.decisions):
            raise RelativeStrengthContractError("ledger decision identities must be unique")
        signal_dates = tuple(item.signal_date for item in self.decisions)
        if signal_dates != tuple(sorted(signal_dates)) or len(signal_dates) != len(
            set(signal_dates)
        ):
            raise RelativeStrengthContractError(
                "ledger signal dates must be unique and chronologically ordered"
            )
        if _month(self.decisions[0].entry_date) != _month(split.start):
            raise RelativeStrengthContractError("ledger must begin in the declared start month")
        if _month(self.decisions[-1].exit_date) != _month(split.end):
            raise RelativeStrengthContractError("ledger must end in the declared end month")
        for decision in self.decisions:
            if not split.contains(decision.entry_date) or not split.contains(decision.exit_date):
                raise RelativeStrengthContractError("ledger entry and exit must lie inside split")
            if _month_ordinal(decision.exit_date) != _month_ordinal(decision.entry_date) + 1:
                raise RelativeStrengthContractError(
                    "each ledger holding interval must span exactly one calendar month"
                )
        for current, following in zip(self.decisions, self.decisions[1:]):
            if current.exit_date != following.entry_date:
                raise RelativeStrengthContractError(
                    "monthly decision ledger must be complete and non-overlapping"
                )
            if _month_ordinal(following.entry_date) != _month_ordinal(current.entry_date) + 1:
                raise RelativeStrengthContractError("ledger must advance exactly one calendar month")


def assign_and_purge_monthly_observations(
    observations: Sequence[MonthlyObservation],
) -> tuple[tuple[AssignedObservation, ...], int]:
    """Assign by whole entry-to-exit label; formation may precede split start."""

    frozen = tuple(observations)
    if any(not isinstance(item, MonthlyObservation) for item in frozen):
        raise RelativeStrengthContractError("observations must contain MonthlyObservation values")
    assigned: list[AssignedObservation] = []
    purged = 0
    seen: set[tuple[str, date]] = set()
    for item in sorted(frozen, key=lambda row: (row.variant_id, row.signal_date)):
        key = (item.variant_id, item.signal_date)
        if key in seen:
            raise RelativeStrengthContractError("duplicate variant signal date")
        seen.add(key)
        split_id = _entry_exit_split(item.entry_date, item.exit_date)
        if split_id == "embargo_2026h2":
            raise RelativeStrengthContractError("embargo outcomes must never be opened")
        if split_id is None:
            purged += 1
            continue
        assigned.append(
            AssignedObservation(
                item.variant_id,
                split_id,
                item.signal_date,
                item.entry_date,
                item.exit_date,
                item.strategy_return,
                item.benchmark_return,
            )
        )
    return tuple(assigned), purged


@dataclass(frozen=True)
class BonferroniTestResult:
    variant_id: str
    split_id: str
    sample_size: int
    seed: int
    observed_mean_active_return: float
    one_sided_p_value: float
    one_sided_lower_bound: float
    strategy_annualized_net_return: float
    benchmark_annualized_net_return: float
    gates: tuple[tuple[str, bool], ...]


def evaluate_twelve_tests(
    observations: Sequence[AssignedObservation],
    *,
    decision_ledgers: Sequence[GatedDecisionLedger],
) -> tuple[BonferroniTestResult, ...]:
    """Evaluate the exact four-by-three family against the complete audit ledger."""

    return _evaluate_tests(
        observations,
        decision_ledgers=decision_ledgers,
        split_ids=GATED_SPLITS,
        observation_split_error="inference accepts gated split observations only",
        ledger_order_error=(
            "decision ledgers must contain the exact ordered 12 gated "
            "variant-split tests"
        ),
    )


def evaluate_historical_eight_tests(
    observations: Sequence[AssignedObservation],
    *,
    decision_ledgers: Sequence[GatedDecisionLedger],
) -> tuple[BonferroniTestResult, ...]:
    """Evaluate only the four-by-two completed historical test family.

    The function deliberately excludes development and prospective-forward
    observations. Split orders remain the contract-wide orders one and two,
    so its seeds and Bonferroni gates are identical to the matching tests from
    :func:`evaluate_twelve_tests` without requiring fabricated forward data.
    """

    return _evaluate_tests(
        observations,
        decision_ledgers=decision_ledgers,
        split_ids=HISTORICAL_GATED_SPLITS,
        observation_split_error=(
            "historical inference accepts validation and retrospective "
            "holdout observations only"
        ),
        ledger_order_error=(
            "decision ledgers must contain the exact ordered 8 historical "
            "variant-split tests"
        ),
    )


def _evaluate_tests(
    observations: Sequence[AssignedObservation],
    *,
    decision_ledgers: Sequence[GatedDecisionLedger],
    split_ids: tuple[str, ...],
    observation_split_error: str,
    ledger_order_error: str,
) -> tuple[BonferroniTestResult, ...]:
    """Evaluate one exact ordered subset of the frozen 12-test family."""

    frozen = tuple(observations)
    if any(not isinstance(item, AssignedObservation) for item in frozen):
        raise RelativeStrengthContractError("assigned observations have invalid types")
    if any(item.split_id not in split_ids for item in frozen):
        raise RelativeStrengthContractError(observation_split_error)
    ledgers = tuple(decision_ledgers)
    if any(not isinstance(item, GatedDecisionLedger) for item in ledgers):
        raise RelativeStrengthContractError("decision_ledgers have invalid types")
    expected = tuple(
        (variant.variant_id, split_id)
        for variant in VARIANTS
        for split_id in split_ids
    )
    ledger_pairs = tuple((item.variant_id, item.split_id) for item in ledgers)
    if ledger_pairs != expected:
        raise RelativeStrengthContractError(ledger_order_error)
    expected_observation_identities = tuple(
        (ledger.variant_id, ledger.split_id, *decision.identity)
        for ledger in ledgers
        for decision in ledger.decisions
    )
    observed_identities = tuple(
        (
            item.variant_id,
            item.split_id,
            item.signal_date,
            item.entry_date,
            item.exit_date,
        )
        for item in frozen
    )
    if observed_identities != expected_observation_identities:
        raise RelativeStrengthContractError(
            "observations must exactly match the complete ordered decision ledger"
        )
    ledger_validity = {
        (ledger.variant_id, ledger.split_id): all(
            decision.valid for decision in ledger.decisions
        )
        for ledger in ledgers
    }
    if not all(ledger_validity.values()):
        raise RelativeStrengthContractError(
            "decision ledger contains missing or invalid audit decisions"
        )
    results: list[BonferroniTestResult] = []
    cursor = 0
    for variant in VARIANTS:
        for split_id in split_ids:
            split_order = GATED_SPLITS.index(split_id) + 1
            ledger = ledgers[len(results)]
            group = frozen[cursor : cursor + len(ledger.decisions)]
            cursor += len(group)
            strategy = tuple(_finite(item.strategy_return, "strategy return") for item in group)
            benchmark = tuple(_finite(item.benchmark_return, "benchmark return") for item in group)
            active = tuple(left - right for left, right in zip(strategy, benchmark, strict=True))
            seed = 20_260_715 + 100 * variant.order + split_order
            observed, p_value, lower = _pcg64_bootstrap(active, seed=seed)
            strategy_annual = _annualized(strategy)
            benchmark_annual = _annualized(benchmark)
            gates = (
                ("minimum_complete_holding_intervals", len(group) >= MINIMUM_INTERVALS[split_id]),
                ("mean_monthly_active_return_positive", observed > 0.0),
                ("bonferroni_one_sided_lower_bound_positive", lower > 0.0),
                ("bonferroni_one_sided_p_value", p_value <= BONFERRONI_ALPHA),
                ("strategy_annualized_net_exceeds_benchmark", strategy_annual > benchmark_annual),
                (
                    "no_invalid_decision_or_missing_mark",
                    ledger_validity[(variant.variant_id, split_id)],
                ),
            )
            results.append(
                BonferroniTestResult(
                    variant.variant_id,
                    split_id,
                    len(group),
                    seed,
                    observed,
                    p_value,
                    lower,
                    strategy_annual,
                    benchmark_annual,
                    gates,
                )
            )
    return tuple(results)


def _pcg64_bootstrap(values: Sequence[float], *, seed: int) -> tuple[float, float, float]:
    frozen = np.asarray(tuple(_finite(value, "active return") for value in values), dtype=np.float64)
    if frozen.ndim != 1 or len(frozen) < BOOTSTRAP_BLOCK_MONTHS:
        raise RelativeStrengthContractError("bootstrap requires at least three monthly returns")
    block_count = math.ceil(len(frozen) / BOOTSTRAP_BLOCK_MONTHS)
    if BOOTSTRAP_DRAWS * block_count > _MAX_BOOTSTRAP_CELLS:
        raise RelativeStrengthContractError("bootstrap work exceeds the frozen safety limit")
    observed = math.fsum(float(value) for value in frozen) / len(frozen)
    centered = frozen - observed
    generator = np.random.Generator(np.random.PCG64(seed))
    starts = generator.integers(
        0,
        len(frozen),
        size=(BOOTSTRAP_DRAWS, block_count),
        dtype=np.int64,
        endpoint=False,
    )
    offsets = np.arange(BOOTSTRAP_BLOCK_MONTHS, dtype=np.int64)
    centered_means: list[float] = []
    for first in range(0, BOOTSTRAP_DRAWS, 256):
        chunk = starts[first : first + 256]
        indices = ((chunk[:, :, None] + offsets) % len(frozen)).reshape(len(chunk), -1)
        centered_means.extend(
            float(value) for value in centered[indices[:, : len(frozen)]].mean(axis=1)
        )
    p_value = (
        1.0 + sum(value >= observed for value in centered_means)
    ) / (BOOTSTRAP_DRAWS + 1.0)
    lower = observed - linear_quantile(centered_means, 1.0 - BONFERRONI_ALPHA)
    return observed, p_value, lower


def _annualized(values: Sequence[float]) -> float:
    frozen = tuple(_finite(value, "monthly return") for value in values)
    if not frozen or any(value <= -1.0 for value in frozen):
        raise RelativeStrengthContractError("annualization requires returns above -100%")
    result = math.exp(
        math.fsum(math.log1p(value) for value in frozen) * 12.0 / len(frozen)
    ) - 1.0
    return _finite(result, "annualized return")


@dataclass(frozen=True)
class FormalEvidence:
    definition_sha256: str
    qualification_sha256: str
    data_manifest_sha256: str
    dataset_identity_sha256: str
    calendar_identity_sha256: str
    parser_identity_sha256: str
    corporate_action_identity_sha256: str


def load_formal_evidence(
    repo_root: Path,
    *,
    data_manifest_path: Path,
    expected_data_manifest_sha256: str,
) -> FormalEvidence:
    """Bind exact accepted bytes; missing, symlinked, or blocked input fails closed."""

    root = Path(repo_root)
    definition = _read_bound_json(root / DEFINITION_PATH, DEFINITION_SHA256)
    qualification = _read_bound_json(root / QUALIFICATION_PATH, QUALIFICATION_SHA256)
    manifest_hash = _digest(expected_data_manifest_sha256, "expected_data_manifest_sha256")
    manifest = _read_bound_json(Path(data_manifest_path), manifest_hash)
    if definition.get("research_id") != RESEARCH_ID:
        raise RelativeStrengthContractError("definition research_id mismatch")
    if qualification.get("research_id") != QUALIFICATION_RESEARCH_ID:
        raise RelativeStrengthContractError("qualification research_id mismatch")
    required = {
        "status": "ACCEPTED_STRICT_PIT_MANIFEST",
        "research_id": RESEARCH_ID,
        "preregistration_sha256": DEFINITION_SHA256,
        "data_qualification_sha256": QUALIFICATION_SHA256,
        "strict_pit_execution_eligible": True,
        "strategy_outcomes_opened": False,
    }
    if any(manifest.get(name) != value for name, value in required.items()):
        raise RelativeStrengthContractError("data manifest is not accepted for this contract")
    identity_names = (
        "dataset_identity_sha256",
        "calendar_identity_sha256",
        "parser_identity_sha256",
        "corporate_action_identity_sha256",
    )
    identities = tuple(_digest(manifest.get(name), name) for name in identity_names)
    return FormalEvidence(DEFINITION_SHA256, QUALIFICATION_SHA256, manifest_hash, *identities)


def _read_bound_json(path: Path, expected_sha256: str) -> dict[str, Any]:
    expected = _digest(expected_sha256, "expected_sha256")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise RelativeStrengthContractError(f"cannot open immutable evidence: {path}") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise RelativeStrengthContractError("evidence must be a regular file")
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        raw = b"".join(chunks)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    try:
        current = os.stat(path, follow_symlinks=False)
    except OSError as exc:
        raise RelativeStrengthContractError("evidence path changed during capture") from exc
    if (
        (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        or (after.st_dev, after.st_ino) != (current.st_dev, current.st_ino)
    ):
        raise RelativeStrengthContractError("evidence changed during capture")
    if hashlib.sha256(raw).hexdigest() != expected:
        raise RelativeStrengthContractError("evidence SHA-256 mismatch")

    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise RelativeStrengthContractError("JSON contains duplicate keys")
            result[key] = value
        return result

    try:
        value = json.loads(
            raw,
            object_pairs_hook=pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                RelativeStrengthContractError(f"nonfinite JSON token: {token}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RelativeStrengthContractError("evidence is not strict JSON") from exc
    if not isinstance(value, dict):
        raise RelativeStrengthContractError("evidence JSON must be an object")
    return value


def build_synthetic_diagnostic(
    observations: Sequence[AssignedObservation],
    *,
    decision_ledgers: Sequence[GatedDecisionLedger],
) -> dict[str, Any]:
    """Return a deterministic aggregate-only non-evidence diagnostic."""

    tests = evaluate_twelve_tests(observations, decision_ledgers=decision_ledgers)
    gate_total = sum(len(result.gates) for result in tests)
    gate_passed = sum(passed for result in tests for _, passed in result.gates)
    return {
        "schema_version": "relative-strength-synthetic-diagnostic-v1",
        "research_id": RESEARCH_ID,
        "phase": "SYNTHETIC_DIAGNOSTIC",
        "status": "SYNTHETIC_DIAGNOSTIC_NOT_STRATEGY_EVIDENCE",
        "definition_sha256": DEFINITION_SHA256,
        "qualification_sha256": QUALIFICATION_SHA256,
        "test_family_size": len(tests),
        "gate_counts": {"passed": gate_passed, "total": gate_total},
        "tests": [asdict(result) for result in tests],
        "stock_identifiers_in_result": False,
        "real_data_used": False,
        "strategy_candidate_available": False,
    }


def canonical_report_bytes(report: Mapping[str, Any]) -> bytes:
    if not isinstance(report, Mapping):
        raise TypeError("report must be a mapping")
    try:
        return json.dumps(
            report, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode() + b"\n"
    except (TypeError, ValueError) as exc:
        raise RelativeStrengthContractError("report is not canonical finite JSON") from exc


__all__ = [
    "ACCEPTED_SOURCE_COMMIT",
    "ACCEPTED_SOURCE_TREE",
    "AssignedObservation",
    "BENCHMARK_SYMBOL",
    "BONFERRONI_ALPHA",
    "BonferroniTestResult",
    "DEFINITION_SHA256",
    "DecisionAudit",
    "FormalEvidence",
    "GATED_SPLITS",
    "HISTORICAL_GATED_SPLITS",
    "GatedDecisionLedger",
    "MonthlyObservation",
    "QUALIFICATION_SHA256",
    "QUALIFICATION_RESEARCH_ID",
    "RESEARCH_ID",
    "RelativeStrengthContractError",
    "RelativeStrengthTarget",
    "ResidualAllocation",
    "SignalBar",
    "VARIANTS",
    "assign_and_purge_monthly_observations",
    "build_monthly_targets",
    "build_synthetic_diagnostic",
    "canonical_report_bytes",
    "evaluate_historical_eight_tests",
    "evaluate_twelve_tests",
    "load_formal_evidence",
    "new_strategy_portfolio",
    "residual_target_weights",
    "run_frozen_static_rebalance",
]
