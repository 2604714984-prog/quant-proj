"""Frozen pure calculations for the Cycle 3 last-FOMC-move policy state.

The module contains no data access or execution code.  A future one-use runner
must prove official range-CSV/FOMC identities and the XNYS decision calendar.
"""

from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

RESEARCH_ID = "C3_POLICY_LAST_FOMC_MOVE_DIRECTION_V1"
PROGRAM_FAMILY_ID = "ISSUE119_US_NEAR_TERM_MECHANISMS_CYCLE3"
SERIES_ID = "DFEDTARU"
INITIAL_CAPITAL = 40_000.0
PROGRAM_ALPHA = 0.00625
VALIDATION_INTERVALS = 29
HOLDOUT_INTERVALS = 35
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 1_193_101
BOOTSTRAP_BLOCK_LENGTH = 3
MIN_DIRECTION_COUNT = 4
MIN_ADJACENT_STATE_CHANGES = 1
EXCHANGE_TIMEZONE = "America/New_York"

_NEW_YORK = ZoneInfo(EXCHANGE_TIMEZONE)
_SPLIT_STATE_COUNTS = {
    "development": 34,
    "validation": 30,
    "holdout": 36,
}
_SUPPORT_GATE_NAMES = (
    "easing_count_at_least_4",
    "tightening_count_at_least_4",
    "adjacent_state_changes_at_least_1",
)
_VALIDATION_GATE_NAMES = (
    "strategy_terminal_net_wealth_strictly_above_spy",
    "arithmetic_mean_paired_active_returns_strictly_positive",
    "strategy_maximum_drawdown_no_worse_than_spy",
)
_HOLDOUT_GATE_NAMES = (
    "strategy_terminal_net_wealth_strictly_above_spy",
    "strategy_maximum_drawdown_no_worse_than_spy",
    "interval_count_exactly_35",
    "centered_null_one_sided_p_at_most_0_00625",
    "uncentered_type7_0_00625_lower_bound_strictly_positive",
)


class InputContractError(ValueError):
    """Raised when frozen policy-state or inference inputs are invalid."""


def _finite(value: object, field: str) -> float:
    if type(value) not in {int, float}:
        raise InputContractError(f"{field} must be an int or float")
    number = float(value)
    if not math.isfinite(number):
        raise InputContractError(f"{field} must be finite")
    return number


def _aware(value: object, field: str) -> datetime:
    if (
        type(value) is not datetime
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise InputContractError(f"{field} must be timezone-aware")
    return value


def _sha256(value: object, field: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise InputContractError(f"{field} must be a lowercase SHA-256")
    return value


def _decision_time(value: object) -> datetime:
    decision_at = _aware(value, "decision_at")
    local = decision_at.astimezone(_NEW_YORK)
    if (local.hour, local.minute, local.second, local.microsecond) != (9, 0, 0, 0):
        raise InputContractError(
            "decision_at must equal 09:00 America/New_York on the entry session"
        )
    return local


@dataclass(frozen=True)
class PolicyEvent:
    """One target-upper-bound event tied to official range and FOMC evidence."""

    event_id: str
    series_id: str
    effective_date: date
    target_upper_bound_percent: float
    available_at: datetime
    official_range_row_sha256: str
    fomc_statement_sha256: str

    def __post_init__(self) -> None:
        if (
            type(self.event_id) is not str
            or not self.event_id.strip()
            or any(ord(character) < 32 for character in self.event_id)
        ):
            raise InputContractError("event_id must be nonempty and contain no C0 controls")
        if self.series_id != SERIES_ID:
            raise InputContractError("only DFEDTARU is allowed")
        if type(self.effective_date) is not date:
            raise InputContractError("effective_date must be a date")
        _finite(self.target_upper_bound_percent, "target_upper_bound_percent")
        _aware(self.available_at, "available_at")
        _sha256(
            self.official_range_row_sha256,
            "official_range_row_sha256",
        )
        _sha256(self.fomc_statement_sha256, "fomc_statement_sha256")


@dataclass(frozen=True)
class PolicyState:
    decision_at: datetime
    direction: str
    last_move_effective_date: date
    last_move_delta_percent: float
    spy_target_weight: float

    def __post_init__(self) -> None:
        local = _decision_time(self.decision_at)
        if self.direction not in {"easing", "tightening"}:
            raise InputContractError("direction must be easing or tightening")
        if type(self.last_move_effective_date) is not date:
            raise InputContractError("last_move_effective_date must be a date")
        if self.last_move_effective_date > local.date():
            raise InputContractError("last policy move cannot be after decision_at")
        delta = _finite(self.last_move_delta_percent, "last_move_delta_percent")
        if delta == 0.0:
            raise InputContractError("last policy move must be nonzero")
        if self.direction == "easing" and delta >= 0.0:
            raise InputContractError("easing requires a negative target change")
        if self.direction == "tightening" and delta <= 0.0:
            raise InputContractError("tightening requires a positive target change")
        weight = _finite(self.spy_target_weight, "spy_target_weight")
        expected = 1.0 if self.direction == "easing" else 0.0
        if weight != expected:
            raise InputContractError("easing maps to SPY and tightening maps to cash")


@dataclass(frozen=True)
class SupportDecision:
    split_id: str
    observed_states: int
    easing_count: int
    tightening_count: int
    adjacent_state_changes: int
    gates: tuple[tuple[str, bool], ...]

    @property
    def all_gates_pass(self) -> bool:
        return (
            self.observed_states == _SPLIT_STATE_COUNTS[self.split_id]
            and tuple(name for name, _ in self.gates) == _SUPPORT_GATE_NAMES
            and all(passed is True for _, passed in self.gates)
        )


@dataclass(frozen=True)
class PerformanceMetrics:
    terminal_net_wealth: float
    arithmetic_mean_return: float
    maximum_drawdown: float


@dataclass(frozen=True)
class ValidationDecision:
    observed_intervals: int
    strategy: PerformanceMetrics
    spy: PerformanceMetrics
    arithmetic_mean_active_return: float
    gates: tuple[tuple[str, bool], ...]

    @property
    def all_gates_pass(self) -> bool:
        return (
            self.observed_intervals == VALIDATION_INTERVALS
            and tuple(name for name, _ in self.gates) == _VALIDATION_GATE_NAMES
            and all(passed is True for _, passed in self.gates)
        )


@dataclass(frozen=True)
class BootstrapInference:
    observed_mean_active_return: float
    centered_null_one_sided_p: float
    uncentered_type7_lower_bound: float


@dataclass(frozen=True)
class HoldoutDecision:
    observed_intervals: int
    strategy: PerformanceMetrics
    spy: PerformanceMetrics
    inference: BootstrapInference
    gates: tuple[tuple[str, bool], ...]

    @property
    def all_gates_pass(self) -> bool:
        return (
            self.observed_intervals == HOLDOUT_INTERVALS
            and tuple(name for name, _ in self.gates) == _HOLDOUT_GATE_NAMES
            and all(passed is True for _, passed in self.gates)
        )


def derive_policy_state(
    events: tuple[PolicyEvent, ...],
    *,
    decision_at: datetime,
) -> PolicyState:
    """Map the most recent known nonzero target change to SPY or cash."""

    local_decision = _decision_time(decision_at)
    if (
        type(events) is not tuple
        or len(events) < 2
        or any(not isinstance(event, PolicyEvent) for event in events)
    ):
        raise InputContractError("at least two PolicyEvent values are required")
    dates = tuple(event.effective_date for event in events)
    if dates != tuple(sorted(dates)) or len(dates) != len(set(dates)):
        raise InputContractError("policy events must have unique increasing effective dates")
    event_ids = tuple(event.event_id for event in events)
    if len(event_ids) != len(set(event_ids)):
        raise InputContractError("policy event IDs must be unique")
    for event in events:
        if event.available_at > decision_at:
            raise InputContractError("every supplied policy event must be available by decision_at")
        if event.effective_date > local_decision.date():
            raise InputContractError("future-effective policy events are forbidden")

    last_move: tuple[date, float] | None = None
    for previous, current in zip(events, events[1:]):
        delta = _finite(
            current.target_upper_bound_percent - previous.target_upper_bound_percent,
            "policy target change",
        )
        if delta != 0.0:
            last_move = (current.effective_date, delta)
    if last_move is None:
        raise InputContractError("no nonzero policy move is known by decision_at")
    move_date, delta = last_move
    direction = "easing" if delta < 0.0 else "tightening"
    return PolicyState(
        decision_at=decision_at,
        direction=direction,
        last_move_effective_date=move_date,
        last_move_delta_percent=delta,
        spy_target_weight=1.0 if direction == "easing" else 0.0,
    )


def split_support(
    states: tuple[PolicyState, ...],
    *,
    split_id: str,
) -> SupportDecision:
    """Apply the frozen pre-outcome support contract to one named split."""

    if split_id not in _SPLIT_STATE_COUNTS:
        raise InputContractError("split_id must be development, validation, or holdout")
    expected = _SPLIT_STATE_COUNTS[split_id]
    if (
        type(states) is not tuple
        or len(states) != expected
        or any(not isinstance(state, PolicyState) for state in states)
    ):
        raise InputContractError(f"{split_id} requires exactly {expected} policy states")
    decisions = tuple(state.decision_at for state in states)
    if any(right <= left for left, right in zip(decisions, decisions[1:])):
        raise InputContractError("policy states must be strictly chronological")
    easing_count = sum(state.direction == "easing" for state in states)
    tightening_count = sum(state.direction == "tightening" for state in states)
    changes = sum(
        left.direction != right.direction for left, right in zip(states, states[1:])
    )
    gates = (
        ("easing_count_at_least_4", easing_count >= MIN_DIRECTION_COUNT),
        ("tightening_count_at_least_4", tightening_count >= MIN_DIRECTION_COUNT),
        (
            "adjacent_state_changes_at_least_1",
            changes >= MIN_ADJACENT_STATE_CHANGES,
        ),
    )
    return SupportDecision(
        split_id,
        len(states),
        easing_count,
        tightening_count,
        changes,
        gates,
    )


def _paired_returns(
    strategy_returns: tuple[float, ...],
    spy_returns: tuple[float, ...],
    *,
    expected: int,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    if (
        type(strategy_returns) is not tuple
        or type(spy_returns) is not tuple
        or len(strategy_returns) != expected
        or len(spy_returns) != expected
    ):
        raise InputContractError(f"exactly {expected} paired return intervals are required")
    strategy = tuple(_finite(value, "strategy return") for value in strategy_returns)
    spy = tuple(_finite(value, "SPY return") for value in spy_returns)
    if any(value <= -1.0 for value in strategy + spy):
        raise InputContractError("monthly returns must preserve strictly positive wealth")
    return strategy, spy


def _performance(returns: tuple[float, ...]) -> PerformanceMetrics:
    wealth = INITIAL_CAPITAL
    peak = wealth
    maximum_drawdown = 0.0
    for monthly_return in returns:
        wealth *= 1.0 + monthly_return
        peak = max(peak, wealth)
        maximum_drawdown = min(maximum_drawdown, wealth / peak - 1.0)
    outputs = PerformanceMetrics(
        terminal_net_wealth=_finite(wealth, "terminal net wealth"),
        arithmetic_mean_return=_finite(
            statistics.fmean(returns), "arithmetic mean return"
        ),
        maximum_drawdown=_finite(maximum_drawdown, "maximum drawdown"),
    )
    return outputs


def validation_decision(
    strategy_returns: tuple[float, ...],
    spy_returns: tuple[float, ...],
) -> ValidationDecision:
    strategy, spy = _paired_returns(
        strategy_returns, spy_returns, expected=VALIDATION_INTERVALS
    )
    strategy_metrics = _performance(strategy)
    spy_metrics = _performance(spy)
    mean_active = _finite(
        statistics.fmean(left - right for left, right in zip(strategy, spy)),
        "arithmetic mean active return",
    )
    gates = (
        (
            "strategy_terminal_net_wealth_strictly_above_spy",
            strategy_metrics.terminal_net_wealth > spy_metrics.terminal_net_wealth,
        ),
        (
            "arithmetic_mean_paired_active_returns_strictly_positive",
            mean_active > 0.0,
        ),
        (
            "strategy_maximum_drawdown_no_worse_than_spy",
            strategy_metrics.maximum_drawdown >= spy_metrics.maximum_drawdown,
        ),
    )
    return ValidationDecision(
        VALIDATION_INTERVALS,
        strategy_metrics,
        spy_metrics,
        mean_active,
        gates,
    )


def circular_block_bootstrap_indices(
    sample_size: int = HOLDOUT_INTERVALS,
) -> tuple[tuple[int, ...], ...]:
    """Return frozen length-3 circular-block paths using random.Random."""

    if type(sample_size) is not int or sample_size < 2:
        raise InputContractError("sample_size must be an integer of at least two")
    generator = random.Random(BOOTSTRAP_SEED)
    block_count = math.ceil(sample_size / BOOTSTRAP_BLOCK_LENGTH)
    paths: list[tuple[int, ...]] = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        path: list[int] = []
        for _ in range(block_count):
            start = math.floor(generator.random() * sample_size)
            path.extend(
                (start + offset) % sample_size
                for offset in range(BOOTSTRAP_BLOCK_LENGTH)
            )
        paths.append(tuple(path[:sample_size]))
    return tuple(paths)


def _type7_quantile(values: list[float], probability: float) -> float:
    if not values:
        raise InputContractError("bootstrap statistics cannot be empty")
    q = _finite(probability, "quantile probability")
    if not 0.0 < q < 1.0:
        raise InputContractError("quantile probability must be inside (0, 1)")
    ordered = sorted(_finite(value, "bootstrap statistic") for value in values)
    rank = (len(ordered) - 1) * q
    lower = math.floor(rank)
    upper = math.ceil(rank)
    return _finite(
        ordered[lower] + (rank - lower) * (ordered[upper] - ordered[lower]),
        "type-7 quantile",
    )


def bootstrap_inference(active_returns: tuple[float, ...]) -> BootstrapInference:
    if type(active_returns) is not tuple or len(active_returns) != HOLDOUT_INTERVALS:
        raise InputContractError("bootstrap requires exactly 35 active-return intervals")
    active = tuple(_finite(value, "active return") for value in active_returns)
    observed = _finite(statistics.fmean(active), "observed mean active return")
    centered = tuple(value - observed for value in active)
    uncentered_means: list[float] = []
    null_at_least_observed = 0
    paths = circular_block_bootstrap_indices()
    if len(paths) != BOOTSTRAP_RESAMPLES:
        raise InputContractError("bootstrap path count differs from the frozen contract")
    for path in paths:
        if len(path) != HOLDOUT_INTERVALS:
            raise InputContractError("bootstrap path length differs from the frozen contract")
        uncentered = _finite(
            statistics.fmean(active[index] for index in path),
            "uncentered bootstrap mean",
        )
        null_mean = _finite(
            statistics.fmean(centered[index] for index in path),
            "centered-null bootstrap mean",
        )
        uncentered_means.append(uncentered)
        if null_mean >= observed:
            null_at_least_observed += 1
    p_value = _finite(
        (1 + null_at_least_observed) / (BOOTSTRAP_RESAMPLES + 1),
        "centered-null one-sided p-value",
    )
    lower_bound = _type7_quantile(uncentered_means, PROGRAM_ALPHA)
    return BootstrapInference(observed, p_value, lower_bound)


def holdout_decision(
    strategy_returns: tuple[float, ...],
    spy_returns: tuple[float, ...],
) -> HoldoutDecision:
    strategy, spy = _paired_returns(
        strategy_returns, spy_returns, expected=HOLDOUT_INTERVALS
    )
    strategy_metrics = _performance(strategy)
    spy_metrics = _performance(spy)
    inference = bootstrap_inference(
        tuple(left - right for left, right in zip(strategy, spy))
    )
    gates = (
        (
            "strategy_terminal_net_wealth_strictly_above_spy",
            strategy_metrics.terminal_net_wealth > spy_metrics.terminal_net_wealth,
        ),
        (
            "strategy_maximum_drawdown_no_worse_than_spy",
            strategy_metrics.maximum_drawdown >= spy_metrics.maximum_drawdown,
        ),
        ("interval_count_exactly_35", len(strategy) == HOLDOUT_INTERVALS),
        (
            "centered_null_one_sided_p_at_most_0_00625",
            inference.centered_null_one_sided_p <= PROGRAM_ALPHA,
        ),
        (
            "uncentered_type7_0_00625_lower_bound_strictly_positive",
            inference.uncentered_type7_lower_bound > 0.0,
        ),
    )
    return HoldoutDecision(
        HOLDOUT_INTERVALS,
        strategy_metrics,
        spy_metrics,
        inference,
        gates,
    )
