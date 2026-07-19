"""Pure calculations for the frozen SPY/GLD stress safe-haven sprint."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
import math
from numbers import Real

import numpy as np

from quant_system.research import us_spy_qqq_gld_dual_momentum as dm


SYMBOLS = ("SPY", "GLD")
CASH = "CASH"
COMPARATORS = (
    "B0_CASH",
    "B1_SPY_BUY_HOLD",
    "B2_SPY_STRESS_SLEEVE",
    "B3_GLD_BUY_HOLD",
    "B4_GLD_STRESS_SAFE_HAVEN",
)


class SafeHavenError(ValueError): ...


@dataclass(frozen=True)
class Bar:
    session_date: date
    symbol: str
    raw_open: float
    adj_open: float
    adj_close: float

    def __post_init__(self) -> None:
        if type(self.session_date) is not date or self.symbol not in SYMBOLS:
            raise SafeHavenError("bar date or symbol is invalid")
        values = (self.raw_open, self.adj_open, self.adj_close)
        if any(
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not math.isfinite(value)
            or value <= 0.0
            for value in values
        ):
            raise SafeHavenError("all prices must be positive and finite")


@dataclass(frozen=True)
class Panel:
    dates: tuple[date, ...]
    rows: tuple[Bar, ...]

    @property
    def lookup(self) -> dict[tuple[date, str], Bar]:
        return {(row.session_date, row.symbol): row for row in self.rows}


@dataclass(frozen=True)
class Interval:
    decision_date: date
    entry_date: date
    endpoint_date: date
    stress: bool
    stress_score: float


@dataclass(frozen=True)
class SplitView:
    panel: Panel
    intervals: tuple[Interval, ...]


def prepare_panel(rows: Sequence[Bar], cutoff: date) -> Panel:
    """Validate the SPY/GLD union before exposing exact common sessions."""
    if type(cutoff) is not date:
        raise SafeHavenError("cutoff must be a date")
    frozen = tuple(rows)
    if not frozen or any(not isinstance(row, Bar) for row in frozen):
        raise SafeHavenError("rows must contain Bar values")
    if any(row.session_date > cutoff for row in frozen):
        raise SafeHavenError("post-cutoff row is forbidden")
    keys = tuple((row.session_date, row.symbol) for row in frozen)
    if len(keys) != len(set(keys)):
        raise SafeHavenError("duplicate symbol-date key")
    per_symbol = {
        symbol: sorted(row.session_date for row in frozen if row.symbol == symbol)
        for symbol in SYMBOLS
    }
    if any(not days for days in per_symbol.values()):
        raise SafeHavenError("a frozen symbol is absent")
    start = max(days[0] for days in per_symbol.values())
    end = min(days[-1] for days in per_symbol.values())
    union = sorted({row.session_date for row in frozen if start <= row.session_date <= end})
    members: dict[date, set[str]] = defaultdict(set)
    for row in frozen:
        if start <= row.session_date <= end:
            members[row.session_date].add(row.symbol)
    if any(members[day] != set(SYMBOLS) for day in union):
        raise SafeHavenError("union date is missing a frozen symbol")
    usable = tuple(
        sorted(
            (row for row in frozen if start <= row.session_date <= end),
            key=lambda row: (row.session_date, SYMBOLS.index(row.symbol)),
        )
    )
    if len(union) < 254 or len(usable) != len(union) * len(SYMBOLS):
        raise SafeHavenError("common-session panel is too short or incomplete")
    return Panel(tuple(union), usable)


def build_intervals(panel: Panel) -> tuple[Interval, ...]:
    if not isinstance(panel, Panel):
        raise SafeHavenError("panel identity is invalid")
    dates, lookup = panel.dates, panel.lookup
    output = []
    for index in range(251, len(dates) - 2):
        decision = dates[index]
        current = lookup[(decision, "SPY")].adj_close
        peak = max(lookup[(day, "SPY")].adj_close for day in dates[index - 251 : index + 1])
        score = current / peak - 1.0
        output.append(
            Interval(decision, dates[index + 1], dates[index + 2], current <= peak * 0.90, score)
        )
    if not output:
        raise SafeHavenError("no complete stress interval")
    return tuple(output)


def select_split(
    panel: Panel, intervals: Sequence[Interval], start: date, end: date
) -> SplitView:
    if type(start) is not date or type(end) is not date or start > end:
        raise SafeHavenError("split bounds are invalid")
    kept = tuple(
        item
        for item in intervals
        if start <= item.decision_date < item.entry_date < item.endpoint_date <= end
    )
    if not kept:
        raise SafeHavenError("split has no complete intervals")
    first, last = kept[0].entry_date, kept[-1].endpoint_date
    dates = tuple(day for day in panel.dates if first <= day <= last)
    rows = tuple(row for row in panel.rows if first <= row.session_date <= last)
    if len(dates) != len(kept) + 1:
        raise SafeHavenError("daily split intervals are not contiguous")
    return SplitView(Panel(dates, rows), kept)


def _position_value(position: tuple[str, int, float, float] | None, bar: Bar) -> float:
    if position is None:
        return 0.0
    _, shares, raw_entry, adj_entry = position
    return shares * raw_entry * bar.adj_open / adj_entry


def _monthly_returns(dates: Sequence[date], returns: Sequence[float]) -> tuple[float, ...]:
    groups: dict[tuple[int, int], list[float]] = defaultdict(list)
    for day, value in zip(dates, returns, strict=True):
        groups[(day.year, day.month)].append(value)
    return tuple(math.prod(1.0 + value for value in values) - 1.0 for values in groups.values())


def _summarize(
    dates: tuple[date, ...],
    returns: tuple[float, ...],
    exposure: tuple[bool, ...],
    intervals: tuple[Interval, ...],
    active_returns: tuple[float, ...],
    turnover: float,
    cost: float,
    utilizations: tuple[float, ...],
) -> dict[str, object]:
    months = _monthly_returns(dates, returns)
    active = tuple(item for item in intervals if item.stress)
    result = dm._summarize(
        dates,
        returns,
        exposure,
        months,
        len(intervals),
        turnover,
        cost,
        utilizations,
        {
            "active_stress_interval_count": len(active),
            "distinct_active_calendar_year_count": len({item.decision_date.year for item in active}),
            "positive_active_interval_fraction": (
                sum(value > 0.0 for value in active_returns) / len(active_returns)
                if active_returns
                else None
            ),
            "state_transition_count": sum(
                left.stress != right.stress for left, right in zip(intervals, intervals[1:])
            ),
            "worst_monthly_interval_return": min(months) if months else None,
        },
    )
    result.update(
        {
            "_intervals": intervals,
            "_active_interval_returns": active_returns,
        }
    )
    return result


def evaluate(view: SplitView, comparator: str, cost_bps: float) -> dict[str, object]:
    if comparator not in COMPARATORS:
        raise SafeHavenError("unknown comparator")
    if (
        isinstance(cost_bps, bool)
        or not isinstance(cost_bps, Real)
        or not math.isfinite(cost_bps)
        or cost_bps < 0.0
    ):
        raise SafeHavenError("cost must be finite and nonnegative")
    dates, lookup = view.panel.dates, view.panel.lookup
    rate = float(cost_bps) / 10_000.0
    targets: dict[date, str] = {}
    for item in view.intervals:
        if comparator == "B0_CASH":
            target = CASH
        elif comparator == "B1_SPY_BUY_HOLD":
            target = "SPY"
        elif comparator == "B3_GLD_BUY_HOLD":
            target = "GLD"
        elif comparator == "B2_SPY_STRESS_SLEEVE":
            target = "SPY" if item.stress else CASH
        else:
            target = "GLD" if item.stress else CASH
        targets[item.entry_date] = target

    cash, position = 40_000.0, None
    turnover = cost = 0.0
    navs: list[float] = []
    exposure: list[bool] = []
    utilizations: list[float] = []
    for index, day in enumerate(dates):
        current_symbol = position[0] if position else CASH
        marked = _position_value(position, lookup[(day, current_symbol)]) if position else 0.0
        before = cash + marked
        target = CASH if index == len(dates) - 1 else targets[day]
        if target != current_symbol:
            if position is not None:
                sale_cost = marked * rate
                turnover += marked / before
                cost += sale_cost
                cash = before - sale_cost
                position = None
                before = cash
            if target != CASH:
                bar = lookup[(day, target)]
                shares = math.floor(cash / (bar.raw_open * (1.0 + rate)))
                if shares <= 0:
                    raise SafeHavenError("whole-share target cannot afford one share")
                notional = shares * bar.raw_open
                available = cash
                purchase_cost = notional * rate
                turnover += notional / available
                cost += purchase_cost
                cash -= notional + purchase_cost
                utilizations.append(notional / available)
                position = (target, shares, bar.raw_open, bar.adj_open)
        current_symbol = position[0] if position else CASH
        nav = cash + (_position_value(position, lookup[(day, current_symbol)]) if position else 0.0)
        if not math.isfinite(nav) or nav <= 0.0:
            raise SafeHavenError("account NAV became invalid")
        navs.append(nav)
        exposure.append(position is not None)

    returns = tuple(
        nav / (40_000.0 if index == 0 else navs[index - 1]) - 1.0
        for index, nav in enumerate(navs)
    )
    positions = {day: index for index, day in enumerate(dates)}
    active_returns = tuple(
        navs[positions[item.endpoint_date]] / navs[positions[item.entry_date]] - 1.0
        for item in view.intervals
        if item.stress
    )
    result = _summarize(
        dates,
        returns,
        tuple(exposure),
        view.intervals,
        active_returns,
        turnover,
        cost,
        tuple(utilizations),
    )
    return result


def combine_outcomes(outcomes: Sequence[dict[str, object]]) -> dict[str, object]:
    frozen = tuple(outcomes)
    if len(frozen) != 2:
        raise SafeHavenError("combined outcome requires validation and holdout")
    dates = tuple(day for item in frozen for day in item["_dates"])  # type: ignore[index]
    if any(left >= right for left, right in zip(dates, dates[1:])):
        raise SafeHavenError("combined dates must be strictly increasing")
    intervals = tuple(item for outcome in frozen for item in outcome["_intervals"])  # type: ignore[index]
    result = _summarize(
        dates,
        tuple(value for item in frozen for value in item["_daily_returns"]),  # type: ignore[index]
        tuple(value for item in frozen for value in item["_exposure"]),  # type: ignore[index]
        intervals,
        tuple(value for item in frozen for value in item["_active_interval_returns"]),  # type: ignore[index]
        math.fsum(float(item["_turnover"]) for item in frozen),
        math.fsum(float(item["_cost_usd"]) for item in frozen),
        tuple(value for item in frozen for value in item["_utilizations"]),  # type: ignore[index]
    )
    result["state_transition_count"] = sum(int(item["state_transition_count"]) for item in frozen)
    return result


def mean_inference(
    series: Sequence[Sequence[float]],
    *,
    draws: int = 20_000,
    block: int = 20,
    seed: int = 2_026_071_903,
    alpha: float = 0.025,
) -> tuple[dict[str, object], ...]:
    values = tuple(np.asarray(item, dtype=float) for item in series)
    if len(values) != 4 or draws < 1 or block < 1 or not 0.0 < alpha < 1.0:
        raise SafeHavenError("inference identity is invalid")
    if any(item.ndim != 1 or len(item) < block or not np.isfinite(item).all() for item in values):
        raise SafeHavenError("inference series is incomplete")
    rng = np.random.Generator(np.random.PCG64(seed))
    internal: list[dict[str, object]] = []
    for item in values:
        observed = float(np.mean(item))
        centered = item - observed
        null = np.empty(draws)
        blocks = math.ceil(len(item) / block)
        offsets = np.arange(block)
        for draw in range(draws):
            starts = rng.integers(0, len(item), size=blocks)
            indices = ((starts[:, None] + offsets) % len(item)).reshape(-1)[: len(item)]
            null[draw] = float(np.mean(centered[indices]))
        raw_p = (1 + int(np.count_nonzero(null >= observed))) / (draws + 1)
        internal.append({"observed_mean": observed, "raw_p": raw_p, "_null": null})
    order = sorted(range(4), key=lambda index: (float(internal[index]["raw_p"]), index))
    running, published = 0.0, {}
    for rank, index in enumerate(order, 1):
        multiplier = 5 - rank
        running = max(running, min(1.0, multiplier * float(internal[index]["raw_p"])))
        threshold = alpha / multiplier
        observed = float(internal[index]["observed_mean"])
        lower = observed - float(
            np.quantile(internal[index]["_null"], 1.0 - threshold, method="linear")
        )
        published[index] = {
            "observed_mean": observed,
            "raw_p": float(internal[index]["raw_p"]),
            "holm_adjusted_p": running,
            "holm_rank_threshold": threshold,
            "simultaneous_lower_bound": lower,
            "passed": running <= alpha and lower > 0.0,
        }
    return tuple(published[index] for index in range(4))


def _number(value: object) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value)


def adjudicate(
    results: dict[str, object],
    inference: Sequence[dict[str, object]],
    operational_failures: int = 0,
) -> dict[str, object]:
    if operational_failures:
        return {"status": "INPUT_BLOCKED", "gates_passed": None, "gates_total": 10}
    try:
        val = results["validation"]["15"]  # type: ignore[index]
        hold = results["holdout"]["15"]  # type: ignore[index]
        combined = results["combined"]["15"]  # type: ignore[index]
        stress = results["combined"]["30"]  # type: ignore[index]
        b4v, b4h, b4c, b4s = (val[COMPARATORS[4]], hold[COMPARATORS[4]], combined[COMPARATORS[4]], stress[COMPARATORS[4]])
        b2h, b2s = hold[COMPARATORS[2]], stress[COMPARATORS[2]]
        gates = (
            int(b4v["active_stress_interval_count"]) >= 60
            and int(b4v["distinct_active_calendar_year_count"]) >= 3
            and int(b4h["active_stress_interval_count"]) >= 60
            and int(b4h["distinct_active_calendar_year_count"]) >= 3,
            _number(b4v["cagr"]) and b4v["cagr"] > 0.0,
            _number(b4h["cagr"]) and b4h["cagr"] > 0.0,
            _number(b4h["daily_maximum_drawdown"]) and _number(b2h["daily_maximum_drawdown"]) and b4h["daily_maximum_drawdown"] > b2h["daily_maximum_drawdown"],
            _number(b4h["calmar"]) and _number(b2h["calmar"]) and b4h["calmar"] > b2h["calmar"],
            _number(b4c["cagr"]) and b4c["cagr"] > 0.0,
            _number(b4c["positive_active_interval_fraction"]) and b4c["positive_active_interval_fraction"] > 0.5,
            _number(b4s["cagr"]) and b4s["cagr"] > 0.0
            and _number(b4s["daily_maximum_drawdown"]) and _number(b2s["daily_maximum_drawdown"])
            and b4s["daily_maximum_drawdown"] > b2s["daily_maximum_drawdown"]
            and _number(b4s["largest_calendar_year_profit_contribution"])
            and b4s["largest_calendar_year_profit_contribution"] < 0.4,
            len(inference) == 4
            and all(type(item.get("passed")) is bool and item["passed"] is True for item in inference),
            operational_failures == 0,
        )
    except (KeyError, TypeError, ValueError):
        return {"status": "INPUT_BLOCKED", "gates_passed": None, "gates_total": 10}
    return {
        "status": (
            "RETROSPECTIVE_STRESS_SAFE_HAVEN_PASS_TO_EXTERNAL_REVIEW"
            if all(gates)
            else "RETROSPECTIVE_STRESS_SAFE_HAVEN_FAIL"
        ),
        "gates_passed": sum(gates),
        "gates_total": 10,
        "gates": gates,
    }
