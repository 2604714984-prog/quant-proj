"""Deterministic, source-agnostic fixed-horizon event-cohort helpers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
import math
from numbers import Real

from quant_system.research.strict_bootstrap import (
    bootstrap_one_sided,
    circular_moving_block_bootstrap_means,
)


class EventCohortError(ValueError):
    """An event-cohort input violates the frozen mechanics."""


def _finite(value: object, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise EventCohortError(f"{name} must be finite numeric")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise EventCohortError(f"{name} must be finite numeric")
    return parsed


@dataclass(frozen=True)
class SplitWindow:
    split_id: str
    start: date
    end: date

    def __post_init__(self) -> None:
        if not isinstance(self.split_id, str) or not self.split_id.strip():
            raise EventCohortError("split_id must be nonempty")
        if type(self.start) is not date or type(self.end) is not date or self.start > self.end:
            raise EventCohortError("split dates must form a closed ordered interval")

    def contains(self, value: date) -> bool:
        return self.start <= value <= self.end


def assign_whole_label_split(
    signal_date: date,
    entry_date: date,
    exit_date: date,
    splits: Sequence[SplitWindow],
) -> str | None:
    """Return the one split containing signal, entry, and exit, else ``None``."""

    if any(type(value) is not date for value in (signal_date, entry_date, exit_date)):
        raise EventCohortError("event dates must be date values")
    if not signal_date < entry_date < exit_date:
        raise EventCohortError("event dates must satisfy signal < entry < exit")
    frozen = tuple(splits)
    if not frozen or any(not isinstance(item, SplitWindow) for item in frozen):
        raise EventCohortError("splits must be a nonempty SplitWindow sequence")
    if frozen != tuple(sorted(frozen, key=lambda item: (item.start, item.end, item.split_id))):
        raise EventCohortError("splits must be supplied in chronological order")
    if any(current.start <= previous.end for previous, current in zip(frozen, frozen[1:])):
        raise EventCohortError("split intervals must not overlap")
    matches = tuple(
        item.split_id
        for item in frozen
        if item.contains(signal_date) and item.contains(entry_date) and item.contains(exit_date)
    )
    if len(matches) > 1:
        raise EventCohortError("whole label matched more than one split")
    return matches[0] if matches else None


@dataclass(frozen=True)
class EventReturnInput:
    symbol: str
    signal_date: date
    entry_date: date
    exit_date: date
    entry_open: float | None
    exit_open: float | None
    entry_is_limit_up: bool | None

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, str) or not self.symbol.strip():
            raise EventCohortError("symbol must be nonempty")
        if any(type(value) is not date for value in (
            self.signal_date, self.entry_date, self.exit_date
        )):
            raise EventCohortError("event dates must be date values")
        if not self.signal_date < self.entry_date < self.exit_date:
            raise EventCohortError("event dates must satisfy signal < entry < exit")
        if self.entry_is_limit_up is not None and type(self.entry_is_limit_up) is not bool:
            raise EventCohortError("entry_is_limit_up must be boolean or None")
        for name, value in (("entry_open", self.entry_open), ("exit_open", self.exit_open)):
            if value is not None and _finite(value, name=name) <= 0.0:
                raise EventCohortError(f"{name} must be positive when present")

    @property
    def complete(self) -> bool:
        return (
            self.entry_open is not None
            and self.exit_open is not None
            and self.entry_is_limit_up is not None
        )


def fixed_two_side_cost_return(gross_return: float, *, bps_per_side: float) -> float:
    gross = _finite(gross_return, name="gross_return")
    bps = _finite(bps_per_side, name="bps_per_side")
    if not 0.0 <= bps < 5_000.0:
        raise EventCohortError("bps_per_side must be in [0, 5000)")
    return gross - 2.0 * bps / 10_000.0


def resolve_event_return(
    event: EventReturnInput,
    *,
    cash_gross_return: float,
    bps_per_side: float,
) -> float | None:
    """Resolve one event; incomplete rows return ``None`` without imputation."""

    if not isinstance(event, EventReturnInput):
        raise EventCohortError("event must be EventReturnInput")
    cash_return = _finite(cash_gross_return, name="cash_gross_return")
    if not event.complete:
        return None
    assert event.entry_open is not None and event.exit_open is not None
    assert event.entry_is_limit_up is not None
    gross = cash_return if event.entry_is_limit_up else event.exit_open / event.entry_open - 1.0
    return fixed_two_side_cost_return(gross, bps_per_side=bps_per_side)


@dataclass(frozen=True)
class CohortAggregate:
    candidate_count: int
    retained_count: int
    incomplete_count: int
    mean_return: float | None


def aggregate_event_sleeve(
    events: Sequence[EventReturnInput],
    *,
    cash_gross_return: float,
    bps_per_side: float,
) -> CohortAggregate:
    """Equal-weight all complete events and account for omitted incomplete events."""

    frozen = tuple(events)
    if any(not isinstance(item, EventReturnInput) for item in frozen):
        raise EventCohortError("events must contain EventReturnInput values")
    ordered = tuple(
        sorted(
            frozen,
            key=lambda item: (
                item.signal_date,
                item.entry_date,
                item.exit_date,
                item.symbol,
            ),
        )
    )
    identities = tuple(
        (item.signal_date, item.entry_date, item.exit_date, item.symbol)
        for item in ordered
    )
    if len(identities) != len(set(identities)):
        raise EventCohortError("events must have unique stable identities")
    resolved = tuple(
        resolve_event_return(
            event, cash_gross_return=cash_gross_return, bps_per_side=bps_per_side
        )
        for event in ordered
    )
    retained = tuple(value for value in resolved if value is not None)
    return CohortAggregate(
        candidate_count=len(frozen),
        retained_count=len(retained),
        incomplete_count=len(frozen) - len(retained),
        mean_return=None if not retained else math.fsum(retained) / len(retained),
    )


@dataclass(frozen=True)
class CohortObservation:
    split_id: str
    signal_date: date
    entry_date: date
    exit_date: date
    signal_return: float
    breakout_return: float
    eligible_return: float
    equity_benchmark_return: float
    cash_benchmark_return: float
    signal_event_count: int
    incomplete_signal_event_count: int = 0
    incomplete_breakout_event_count: int = 0
    incomplete_eligible_event_count: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.split_id, str) or not self.split_id.strip():
            raise EventCohortError("split_id must be nonempty")
        if not self.signal_date < self.entry_date < self.exit_date:
            raise EventCohortError("cohort dates must satisfy signal < entry < exit")
        for name in (
            "signal_return", "breakout_return", "eligible_return",
            "equity_benchmark_return", "cash_benchmark_return",
        ):
            _finite(getattr(self, name), name=name)
        for name in (
            "signal_event_count", "incomplete_signal_event_count",
            "incomplete_breakout_event_count", "incomplete_eligible_event_count",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise EventCohortError(f"{name} must be a nonnegative integer")
        if self.signal_event_count < 1:
            raise EventCohortError("signal_event_count must be positive")

    def series_value(self, series_id: str) -> float:
        values = {
            "signal_return": self.signal_return,
            "excess_vs_breakout_only": self.signal_return - self.breakout_return,
            "excess_vs_eligible": self.signal_return - self.eligible_return,
            "excess_vs_510300": self.signal_return - self.equity_benchmark_return,
            "excess_vs_511880": self.signal_return - self.cash_benchmark_return,
        }
        try:
            return values[series_id]
        except KeyError as exc:
            raise EventCohortError(f"unknown series_id: {series_id}") from exc


@dataclass(frozen=True)
class EconomicSummary:
    count: int
    mean: float
    median: float
    positive_fraction: float


def economic_summary(values: Sequence[float]) -> EconomicSummary:
    ordered = tuple(sorted(_finite(value, name="return") for value in values))
    if not ordered:
        raise EventCohortError("economic summary requires at least one return")
    midpoint = len(ordered) // 2
    median_value = (
        ordered[midpoint]
        if len(ordered) % 2
        else math.fsum((ordered[midpoint - 1], ordered[midpoint])) / 2.0
    )
    return EconomicSummary(
        count=len(ordered),
        mean=math.fsum(ordered) / len(ordered),
        median=median_value,
        positive_fraction=sum(value > 0.0 for value in ordered) / len(ordered),
    )


def linear_quantile(values: Sequence[float], probability: float) -> float:
    frozen = sorted(_finite(value, name="quantile value") for value in values)
    p = _finite(probability, name="probability")
    if not frozen or not 0.0 <= p <= 1.0:
        raise EventCohortError("quantile requires values and probability in [0, 1]")
    position = (len(frozen) - 1) * p
    lower, upper = math.floor(position), math.ceil(position)
    weight = position - lower
    return frozen[lower] + weight * (frozen[upper] - frozen[lower])


@dataclass(frozen=True)
class BlockBootstrapSummary:
    observed_mean: float
    raw_p: float
    lower_bound: float
    draws: int
    block_length: int
    seed: int


def block_bootstrap_summary(
    values: Sequence[float],
    *,
    block_length: int,
    draws: int,
    seed: int,
    alpha: float,
) -> BlockBootstrapSummary:
    """Return an uncentered lower bound and centered-null one-sided p-value."""

    frozen = tuple(_finite(value, name="bootstrap value") for value in values)
    p = _finite(alpha, name="alpha")
    if not 0.0 < p < 1.0:
        raise EventCohortError("alpha must be in (0, 1)")
    one_sided = bootstrap_one_sided(
        frozen, block_length=block_length, draws=draws, seed=seed, null_mean=0.0
    )
    uncentered = circular_moving_block_bootstrap_means(
        frozen, block_length=block_length, draws=draws, seed=seed
    )
    return BlockBootstrapSummary(
        observed_mean=one_sided.observed_mean,
        raw_p=one_sided.raw_p,
        lower_bound=linear_quantile(uncentered, p),
        draws=draws,
        block_length=block_length,
        seed=seed,
    )


def benjamini_hochberg_adjusted(raw_p_values: Sequence[float]) -> tuple[float, ...]:
    """Return BH adjusted p-values; ties retain caller order."""

    frozen = tuple(_finite(value, name="raw_p") for value in raw_p_values)
    if not frozen or any(not 0.0 <= value <= 1.0 for value in frozen):
        raise EventCohortError("raw p-values must be a nonempty sequence in [0, 1]")
    size = len(frozen)
    ordered = tuple(sorted(range(size), key=lambda index: (frozen[index], index)))
    adjusted_sorted = [1.0] * size
    running = 1.0
    for reverse_offset in range(size - 1, -1, -1):
        index = ordered[reverse_offset]
        rank = reverse_offset + 1
        running = min(running, size * frozen[index] / rank, 1.0)
        adjusted_sorted[reverse_offset] = running
    adjusted = [1.0] * size
    for offset, index in enumerate(ordered):
        adjusted[index] = adjusted_sorted[offset]
    return tuple(adjusted)
