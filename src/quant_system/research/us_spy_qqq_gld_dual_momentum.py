"""Pure calculations for the frozen SPY/QQQ/GLD dual-momentum replication."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
import math
from numbers import Real


SYMBOLS = ("SPY", "QQQ", "GLD")
CASH = "CASH"


class DualMomentumError(ValueError): ...


@dataclass(frozen=True)
class Bar:
    session_date: date
    symbol: str
    raw_open: float
    adj_open: float
    adj_close: float

    def __post_init__(self) -> None:
        if type(self.session_date) is not date or self.symbol not in SYMBOLS:
            raise DualMomentumError("bar date or symbol is invalid")
        for value in (self.raw_open, self.adj_open, self.adj_close):
            if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value) or value <= 0:
                raise DualMomentumError("all prices must be positive and finite")


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
    exit_date: date
    target: str
    momentum: tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class SplitView:
    panel: Panel
    intervals: tuple[Interval, ...]


def prepare_panel(rows: Sequence[Bar], cutoff: date) -> Panel:
    """Validate the union first, then expose the exact common-session panel."""
    if type(cutoff) is not date:
        raise DualMomentumError("cutoff must be a date")
    frozen = tuple(rows)
    if not frozen or any(not isinstance(row, Bar) for row in frozen):
        raise DualMomentumError("rows must contain Bar values")
    if any(row.session_date > cutoff for row in frozen):
        raise DualMomentumError("post-cutoff row is forbidden")
    keys = [(row.session_date, row.symbol) for row in frozen]
    if len(keys) != len(set(keys)):
        raise DualMomentumError("duplicate symbol-date key")
    per_symbol = {symbol: sorted(row.session_date for row in frozen if row.symbol == symbol) for symbol in SYMBOLS}
    if any(not dates for dates in per_symbol.values()):
        raise DualMomentumError("a frozen symbol is absent")
    start, end = max(dates[0] for dates in per_symbol.values()), min(dates[-1] for dates in per_symbol.values())
    union = sorted({row.session_date for row in frozen if start <= row.session_date <= end})
    by_date: dict[date, set[str]] = defaultdict(set)
    for row in frozen:
        if start <= row.session_date <= end:
            by_date[row.session_date].add(row.symbol)
    if any(by_date[day] != set(SYMBOLS) for day in union):
        raise DualMomentumError("union date is missing a frozen symbol before intersection")
    usable = tuple(sorted((row for row in frozen if row.session_date in by_date), key=lambda x: (x.session_date, SYMBOLS.index(x.symbol))))
    if len(union) < 254 or len(usable) != len(union) * len(SYMBOLS):
        raise DualMomentumError("common-session panel is too short or incomplete")
    return Panel(tuple(union), usable)


def build_intervals(panel: Panel) -> tuple[Interval, ...]:
    if not isinstance(panel, Panel):
        raise DualMomentumError("panel identity is invalid")
    lookup, dates = panel.lookup, panel.dates
    ends = [i for i, day in enumerate(dates[:-1]) if (day.year, day.month) != (dates[i + 1].year, dates[i + 1].month)]
    decisions = [i for i in ends if i >= 252 and i + 1 < len(dates)]
    signals: list[tuple[int, str, tuple[tuple[str, float], ...]]] = []
    for index in decisions:
        values = tuple((symbol, lookup[(dates[index], symbol)].adj_close / lookup[(dates[index - 252], symbol)].adj_close - 1.0) for symbol in SYMBOLS)
        best = max(value for _, value in values)
        selected = next(symbol for symbol, value in values if value == best)
        signals.append((index, selected if best > 0.0 else CASH, values))
    return tuple(
        Interval(dates[left], dates[left + 1], dates[right + 1], target, values)
        for (left, target, values), (right, _, _) in zip(signals, signals[1:])
    )


def select_split(panel: Panel, intervals: Sequence[Interval], start: date, end: date) -> SplitView:
    if type(start) is not date or type(end) is not date or start > end:
        raise DualMomentumError("split bounds are invalid")
    kept = tuple(item for item in intervals if start <= item.decision_date < item.entry_date < item.exit_date <= end)
    if not kept:
        raise DualMomentumError("split has no complete intervals")
    first, last = kept[0].entry_date, kept[-1].exit_date
    dates = tuple(day for day in panel.dates if first <= day <= last)
    rows = tuple(row for row in panel.rows if first <= row.session_date <= last)
    return SplitView(Panel(dates, rows), kept)


def _position_value(position: tuple[str, int, float, float] | None, day: date, lookup: dict[tuple[date, str], Bar]) -> float:
    if position is None:
        return 0.0
    symbol, shares, raw_entry, adj_entry = position
    return shares * raw_entry * lookup[(day, symbol)].adj_open / adj_entry


def _summarize(
    dates: tuple[date, ...], returns: tuple[float, ...], exposure: tuple[bool, ...],
    month_returns: tuple[float, ...], interval_count: int, turnover: float,
    cost_usd: float, utilizations: tuple[float, ...], extras: dict[str, object] | None = None,
) -> dict[str, object]:
    if len(dates) != len(returns) or len(returns) != len(exposure) or len(dates) < 2:
        raise DualMomentumError("daily metric inputs differ")
    wealth, peak, drawdown = 40_000.0, 40_000.0, 0.0
    annual: dict[int, float] = defaultdict(float)
    navs: list[float] = []
    for day, result in zip(dates, returns):
        prior = wealth
        wealth *= 1.0 + result
        if not math.isfinite(wealth) or wealth <= 0.0:
            raise DualMomentumError("account wealth became invalid")
        annual[day.year] += wealth - prior
        navs.append(wealth)
        peak = max(peak, wealth)
        drawdown = min(drawdown, wealth / peak - 1.0)
    actual_days = (dates[-1] - dates[0]).days
    cagr = (wealth / 40_000.0) ** (365.25 / actual_days) - 1.0 if actual_days > 0 else None
    mean = math.fsum(returns) / len(returns)
    volatility = math.sqrt(math.fsum((value - mean) ** 2 for value in returns) / (len(returns) - 1)) * math.sqrt(252.0)
    positives = tuple(max(value, 0.0) for value in annual.values())
    pool = math.fsum(positives)
    public: dict[str, object] = {
        "complete_day_count": len(dates), "complete_interval_count": interval_count,
        "actual_calendar_days": actual_days, "cumulative_net_return": wealth / 40_000.0 - 1.0,
        "cagr": cagr, "annualized_volatility": volatility, "daily_maximum_drawdown": drawdown,
        "calmar": cagr / abs(drawdown) if cagr is not None and drawdown < 0.0 else None,
        "positive_month_fraction": sum(value > 0.0 for value in month_returns) / len(month_returns) if month_returns else None,
        "time_in_market": sum(exposure) / len(exposure), "one_way_turnover": turnover,
        "cost_drag": cost_usd / 40_000.0,
        "whole_share_cash_utilization": math.fsum(utilizations) / len(utilizations) if utilizations else None,
        "largest_calendar_year_profit_contribution": max(positives) / pool if pool > 0.0 else None,
        "_dates": dates, "_daily_returns": returns, "_exposure": exposure,
        "_month_returns": month_returns, "_turnover": turnover, "_cost_usd": cost_usd,
        "_utilizations": utilizations, "_navs": tuple(navs),
    }
    public.update(extras or {})
    return public


def _from_navs(view: SplitView, navs: list[float], exposure: list[bool], turnover: float, cost: float, utils: list[float], extras: dict[str, object] | None = None) -> dict[str, object]:
    returns = tuple(value / (40_000.0 if index == 0 else navs[index - 1]) - 1.0 for index, value in enumerate(navs))
    positions = {day: index for index, day in enumerate(view.panel.dates)}
    months = tuple(
        navs[positions[item.exit_date]]
        / (40_000.0 if index == 0 else navs[positions[item.entry_date]])
        - 1.0
        for index, item in enumerate(view.intervals)
    )
    return _summarize(view.panel.dates, returns, tuple(exposure), months, len(view.intervals), turnover, cost, tuple(utils), extras)


def _buy_hold_leg(
    view: SplitView, symbol: str, budget: float, rate: float
) -> tuple[list[float], float, float, float, float]:
    dates, lookup = view.panel.dates, view.panel.lookup
    first = lookup[(dates[0], symbol)]
    shares = math.floor(budget / (first.raw_open * (1.0 + rate)))
    if shares <= 0:
        raise DualMomentumError("whole-share leg cannot afford one share")
    notional, cost = shares * first.raw_open, shares * first.raw_open * rate
    cash = budget - notional - cost
    navs: list[float] = []
    terminal_notional = 0.0
    for index, day in enumerate(dates):
        marked = shares * first.raw_open * lookup[(day, symbol)].adj_open / first.adj_open
        if index == len(dates) - 1:
            exit_cost = marked * rate
            terminal_notional = marked
            cost += exit_cost
            navs.append(cash + marked - exit_cost)
        else:
            navs.append(cash + marked)
    return navs, cost, notional / budget, notional, terminal_notional


def evaluate(view: SplitView, comparator: str, cost_bps: float) -> dict[str, object]:
    if comparator not in {"B0_CASH", "B1_SPY_BUY_HOLD", "B2_STATIC_EQUAL_WEIGHT_SPY_QQQ_GLD", "B3_DUAL_MOMENTUM_CASH"}:
        raise DualMomentumError("unknown comparator")
    if isinstance(cost_bps, bool) or not isinstance(cost_bps, Real) or not math.isfinite(cost_bps) or cost_bps < 0:
        raise DualMomentumError("cost must be finite and nonnegative")
    dates, lookup, rate = view.panel.dates, view.panel.lookup, float(cost_bps) / 10_000.0
    if comparator == "B0_CASH":
        return _from_navs(view, [40_000.0] * len(dates), [False] * len(dates), 0.0, 0.0, [])
    if comparator in {"B1_SPY_BUY_HOLD", "B2_STATIC_EQUAL_WEIGHT_SPY_QQQ_GLD"}:
        symbols = ("SPY",) if comparator.startswith("B1") else SYMBOLS
        budget = 40_000.0 / len(symbols)
        legs = [_buy_hold_leg(view, symbol, budget, rate) for symbol in symbols]
        navs = [math.fsum(leg[0][index] for leg in legs) for index in range(len(dates))]
        exposure = [index < len(dates) - 1 for index in range(len(dates))]
        buy_notional = math.fsum(leg[3] for leg in legs)
        sale_notional = math.fsum(leg[4] for leg in legs)
        terminal_cash = math.fsum(
            budget - leg[3] * (1.0 + rate) + leg[4] for leg in legs
        )
        turnover = buy_notional / 40_000.0 + sale_notional / terminal_cash
        return _from_navs(
            view,
            navs,
            exposure,
            turnover,
            math.fsum(leg[1] for leg in legs),
            [leg[2] for leg in legs],
        )
    targets = {item.entry_date: item.target for item in view.intervals}
    cash, position, turnover, cost = 40_000.0, None, 0.0, 0.0
    navs: list[float] = []
    exposure: list[bool] = []
    utils: list[float] = []
    for index, day in enumerate(dates):
        before = cash + _position_value(position, day, lookup)
        target = targets.get(day)
        current = position[0] if position else CASH
        if target is not None and target != current:
            if position is not None:
                sale = _position_value(position, day, lookup)
                turnover += sale / before
                cost += sale * rate
                cash += sale * (1.0 - rate)
                position = None
            if target != CASH:
                bar = lookup[(day, target)]
                available = cash
                shares = math.floor(cash / (bar.raw_open * (1.0 + rate)))
                if shares <= 0:
                    raise DualMomentumError("whole-share account cannot afford selected asset")
                notional = shares * bar.raw_open
                turnover += notional / available
                cost += notional * rate
                cash -= notional * (1.0 + rate)
                utils.append(notional / available)
                position = (target, shares, bar.raw_open, bar.adj_open)
        if index == len(dates) - 1 and position is not None:
            sale = _position_value(position, day, lookup)
            before = cash + sale
            turnover += sale / before
            cost += sale * rate
            cash += sale * (1.0 - rate)
            position = None
        navs.append(cash + _position_value(position, day, lookup))
        exposure.append(position is not None)
    selections = tuple(item.target for item in view.intervals)
    counts = {target: selections.count(target) for target in (*SYMBOLS, CASH)}
    extras = {
        "selection_counts": counts,
        "selection_share": {target: counts[target] / len(selections) for target in counts},
        "state_transition_count": sum(left != right for left, right in zip(selections, selections[1:])),
        "worst_monthly_interval_return": None,
    }
    result = _from_navs(view, navs, exposure, turnover, cost, utils, extras)
    result["worst_monthly_interval_return"] = min(result["_month_returns"])
    return result


def combine_outcomes(outcomes: Sequence[dict[str, object]]) -> dict[str, object]:
    frozen = tuple(outcomes)
    if not frozen:
        raise DualMomentumError("combined outcomes are absent")
    try:
        dates = tuple(day for item in frozen for day in item["_dates"])
        returns = tuple(value for item in frozen for value in item["_daily_returns"])
        exposure = tuple(value for item in frozen for value in item["_exposure"])
        months = tuple(value for item in frozen for value in item["_month_returns"])
        utils = tuple(value for item in frozen for value in item["_utilizations"])
    except (KeyError, TypeError) as exc:
        raise DualMomentumError("outcomes must originate from evaluate") from exc
    if any(left >= right for left, right in zip(dates, dates[1:])):
        raise DualMomentumError("combined split dates must be strictly ordered")
    extras: dict[str, object] = {}
    if all("selection_counts" in item for item in frozen):
        counts = {target: sum(int(item["selection_counts"][target]) for item in frozen) for target in (*SYMBOLS, CASH)}
        total = sum(counts.values())
        extras = {"selection_counts": counts, "selection_share": {target: counts[target] / total for target in counts},
                  "state_transition_count": sum(int(item["state_transition_count"]) for item in frozen),
                  "worst_monthly_interval_return": min(months)}
    return _summarize(dates, returns, exposure, months, sum(int(item["complete_interval_count"]) for item in frozen),
                      math.fsum(float(item["_turnover"]) for item in frozen), math.fsum(float(item["_cost_usd"]) for item in frozen), utils, extras)


def adjudicate(results: dict[str, dict[str, dict[str, dict[str, object]]]], input_failures: int = 0) -> dict[str, object]:
    if input_failures:
        return {"status": "INPUT_BLOCKED", "gates_passed": None, "gates_total": 8}
    try:
        v, h, c, s = results["validation"]["15"], results["holdout"]["15"], results["combined"]["15"], results["combined"]["30"]
        b3, b1, b2 = h["B3_DUAL_MOMENTUM_CASH"], h["B1_SPY_BUY_HOLD"], h["B2_STATIC_EQUAL_WEIGHT_SPY_QQQ_GLD"]
        gates = (v["B3_DUAL_MOMENTUM_CASH"]["cagr"] > 0, b3["cagr"] > 0,
                 b3["daily_maximum_drawdown"] > b1["daily_maximum_drawdown"],
                 b3["calmar"] is not None and b1["calmar"] is not None and b2["calmar"] is not None and b3["calmar"] > b1["calmar"] and b3["calmar"] > b2["calmar"],
                 c["B3_DUAL_MOMENTUM_CASH"]["cagr"] > 0 and c["B3_DUAL_MOMENTUM_CASH"]["cagr"] >= 0.5 * c["B1_SPY_BUY_HOLD"]["cagr"],
                 c["B3_DUAL_MOMENTUM_CASH"]["calmar"] is not None and c["B2_STATIC_EQUAL_WEIGHT_SPY_QQQ_GLD"]["calmar"] is not None and c["B3_DUAL_MOMENTUM_CASH"]["calmar"] > c["B2_STATIC_EQUAL_WEIGHT_SPY_QQQ_GLD"]["calmar"],
                 s["B3_DUAL_MOMENTUM_CASH"]["cagr"] > 0 and s["B3_DUAL_MOMENTUM_CASH"]["largest_calendar_year_profit_contribution"] is not None and s["B3_DUAL_MOMENTUM_CASH"]["largest_calendar_year_profit_contribution"] < 0.4,
                 input_failures == 0)
    except (KeyError, TypeError):
        return {"status": "INPUT_BLOCKED", "gates_passed": None, "gates_total": 8}
    return {"status": "RETROSPECTIVE_DUAL_MOMENTUM_PASS_TO_EXTERNAL_REVIEW" if all(gates) else "RETROSPECTIVE_DUAL_MOMENTUM_FAIL",
            "gates_passed": sum(gates), "gates_total": 8, "gates": gates}
