"""Deterministic calculations for the frozen classic SPY turn-of-the-month test."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
import math
from numbers import Real

import numpy as np


class TurnOfMonthError(ValueError):
    """The frozen calculation cannot be completed without changing its contract."""


@dataclass(frozen=True)
class DailyBar:
    session_date: date
    raw_close: float
    adj_close: float

    def __post_init__(self) -> None:
        if type(self.session_date) is not date:
            raise TurnOfMonthError("session_date must be a date")
        for name, value in (("raw_close", self.raw_close), ("adj_close", self.adj_close)):
            if (
                isinstance(value, bool)
                or not isinstance(value, Real)
                or not math.isfinite(value)
                or value <= 0
            ):
                raise TurnOfMonthError(f"{name} must be positive and finite")


@dataclass(frozen=True)
class Episode:
    episode_id: str
    entry_date: date
    t_date: date
    t1_date: date
    t2_date: date
    exit_date: date

    @property
    def dates(self) -> tuple[date, ...]:
        return (self.entry_date, self.t_date, self.t1_date, self.t2_date, self.exit_date)

    @property
    def return_dates(self) -> tuple[date, ...]:
        return (self.t_date, self.t1_date, self.t2_date, self.exit_date)


@dataclass(frozen=True)
class SplitView:
    bars: tuple[DailyBar, ...]
    episodes: tuple[Episode, ...]
    excluded_return_dates: frozenset[date]


def _month_after(left: tuple[int, int], right: tuple[int, int]) -> bool:
    year, month = left
    expected = (year + 1, 1) if month == 12 else (year, month + 1)
    return right == expected


def _validated_bars(rows: Sequence[DailyBar]) -> tuple[DailyBar, ...]:
    bars = tuple(rows)
    if not bars or any(not isinstance(bar, DailyBar) for bar in bars):
        raise TurnOfMonthError("bars must contain DailyBar values")
    if any(left.session_date >= right.session_date for left, right in zip(bars, bars[1:])):
        raise TurnOfMonthError("bars must have strictly increasing unique dates")
    return bars


def build_episodes(rows: Sequence[DailyBar]) -> tuple[Episode, ...]:
    """Build the sole T-1/T/T+1/T+2/T+3 role assignment."""
    bars = _validated_bars(rows)
    groups: list[tuple[tuple[int, int], list[DailyBar]]] = []
    for bar in bars:
        key = (bar.session_date.year, bar.session_date.month)
        if not groups or groups[-1][0] != key:
            groups.append((key, []))
        groups[-1][1].append(bar)
    episodes: list[Episode] = []
    for position, ((old_key, old), (new_key, new)) in enumerate(zip(groups, groups[1:])):
        if not _month_after(old_key, new_key):
            raise TurnOfMonthError("source session calendar has a missing calendar month")
        if len(old) < 2:
            if position == 0:
                continue
            raise TurnOfMonthError("an interior month lacks T-1 and T")
        if len(new) < 3:
            raise TurnOfMonthError("an interior month lacks T+1 through T+3")
        dates = (old[-2].session_date, old[-1].session_date, *(bar.session_date for bar in new[:3]))
        if any(left >= right for left, right in zip(dates, dates[1:])):
            raise TurnOfMonthError("episode roles are not strictly ordered")
        episodes.append(
            Episode(
                f"{new_key[0]:04d}-{new_key[1]:02d}",
                dates[0], dates[1], dates[2], dates[3], dates[4],
            )
        )
    return tuple(episodes)


def split_view(
    rows: Sequence[DailyBar], episodes: Sequence[Episode], start: date, end: date,
    terminal_censored_t: date | None = None,
) -> SplitView:
    if type(start) is not date or type(end) is not date or start > end:
        raise TurnOfMonthError("split bounds are invalid")
    bars = tuple(bar for bar in _validated_bars(rows) if start <= bar.session_date <= end)
    if not bars:
        raise TurnOfMonthError("split has no bars")
    frozen = tuple(episodes)
    if any(not isinstance(item, Episode) for item in frozen):
        raise TurnOfMonthError("episodes must contain Episode values")
    retained = tuple(item for item in frozen if all(start <= day <= end for day in item.dates))
    purged = tuple(
        item
        for item in frozen
        if any(start <= day <= end for day in item.dates)
        and not all(start <= day <= end for day in item.dates)
    )
    excluded = frozenset(
        day for item in purged for day in item.return_dates if start <= day <= end
    )
    if terminal_censored_t is not None:
        if type(terminal_censored_t) is not date or terminal_censored_t != bars[-1].session_date:
            raise TurnOfMonthError("terminal censored T must equal the final split session")
        if terminal_censored_t in {day for item in retained for day in item.return_dates}:
            raise TurnOfMonthError("terminal censored T conflicts with a retained episode")
        excluded = excluded | {terminal_censored_t}
    return SplitView(bars, retained, excluded)


def daily_labels(view: SplitView) -> tuple[tuple[date, float, bool], ...]:
    tom_dates = {day for item in view.episodes for day in item.return_dates}
    labelled: list[tuple[date, float, bool]] = []
    for previous, current in zip(view.bars, view.bars[1:]):
        if current.session_date in view.excluded_return_dates:
            continue
        labelled.append(
            (
                current.session_date,
                current.adj_close / previous.adj_close - 1.0,
                current.session_date in tom_dates,
            )
        )
    if not any(item[2] for item in labelled) or not any(not item[2] for item in labelled):
        raise TurnOfMonthError("split lacks a TOM or non-TOM daily-return label")
    return tuple(labelled)


def label_metrics(labelled: Sequence[tuple[date, float, bool]]) -> dict[str, float | int]:
    frozen = tuple(labelled)
    tom = tuple(value for _, value, flag in frozen if flag)
    other = tuple(value for _, value, flag in frozen if not flag)
    if not tom or not other:
        raise TurnOfMonthError("both daily-return labels are required")
    tom_mean, other_mean = math.fsum(tom) / len(tom), math.fsum(other) / len(other)
    return {
        "tom_day_count": len(tom),
        "non_tom_day_count": len(other),
        "mean_tom_daily_return": tom_mean,
        "mean_non_tom_daily_return": other_mean,
        "tom_minus_non_tom_mean_daily_return": tom_mean - other_mean,
    }


def _metrics(
    daily_returns: tuple[float, ...], exposure: tuple[bool, ...], turnover: float,
    cost_drag: float, episode_returns: tuple[float, ...], episode_profits: tuple[float, ...],
    exit_years: tuple[int, ...], utilizations: tuple[float, ...], initial: float,
) -> dict[str, object]:
    wealth, peak, drawdown = initial, initial, 0.0
    navs: list[float] = []
    for result in daily_returns:
        wealth *= 1.0 + result
        navs.append(wealth)
        peak = max(peak, wealth)
        drawdown = min(drawdown, wealth / peak - 1.0)
    count = len(daily_returns)
    cumulative = wealth / initial - 1.0
    cagr = (wealth / initial) ** (252.0 / count) - 1.0 if count else 0.0
    mean = math.fsum(daily_returns) / count if count else 0.0
    volatility = (
        math.sqrt(math.fsum((value - mean) ** 2 for value in daily_returns) / (count - 1))
        * math.sqrt(252.0)
        if count > 1 else 0.0
    )
    annual: dict[int, float] = defaultdict(float)
    for year, profit in zip(exit_years, episode_profits):
        annual[year] += profit
    terminal_profit = math.fsum(episode_profits)
    concentration = terminal_profit if terminal_profit > 0 else None
    return {
        "complete_day_count": count,
        "complete_episode_count": len(episode_returns),
        "cumulative_net_return": cumulative,
        "cagr": cagr,
        "annualized_volatility": volatility,
        "daily_maximum_drawdown": drawdown,
        "calmar": cagr / abs(drawdown) if drawdown < 0 else None,
        "time_in_market": sum(exposure) / count if count else 0.0,
        "one_way_turnover": turnover,
        "cost_drag": cost_drag,
        "mean_episode_return": math.fsum(episode_returns) / len(episode_returns)
        if episode_returns else None,
        "median_episode_return": float(np.median(episode_returns)) if episode_returns else None,
        "positive_episode_fraction": sum(value > 0 for value in episode_returns)
        / len(episode_returns) if episode_returns else None,
        "largest_episode_contribution": max((max(value, 0.0) for value in episode_profits), default=0.0)
        / concentration if concentration else None,
        "largest_calendar_year_contribution": max((max(value, 0.0) for value in annual.values()), default=0.0)
        / concentration if concentration else None,
        "whole_share_cash_utilization": math.fsum(utilizations) / len(utilizations)
        if utilizations else None,
        "_daily_returns": daily_returns,
        "_exposure": exposure,
        "_episode_returns": episode_returns,
        "_episode_profits": episode_profits,
        "_exit_years": exit_years,
        "_utilizations": utilizations,
        "_turnover": turnover,
        "_cost_usd": cost_drag * initial,
        "_initial": initial,
        "_navs": tuple(navs),
    }


def evaluate(
    view: SplitView, comparator: str, cost_bps: float, initial_capital: float = 40_000.0
) -> dict[str, object]:
    if comparator not in {"B0_CASH", "B1_SPY_BUY_HOLD", "B2_SPY_CLASSIC_TURN_OF_MONTH"}:
        raise TurnOfMonthError("unknown comparator")
    if any(
        isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value)
        for value in (cost_bps, initial_capital)
    ) or cost_bps < 0 or initial_capital <= 0:
        raise TurnOfMonthError("cost and capital must be finite and valid")
    bars, rate = view.bars, float(cost_bps) / 10_000.0
    cash, active = float(initial_capital), None
    navs: list[float] = []
    exposure: list[bool] = []
    turnover = total_cost = 0.0
    episode_returns: list[float] = []
    episode_profits: list[float] = []
    exit_years: list[int] = []
    utilizations: list[float] = []
    entries = {item.entry_date: item for item in view.episodes}
    if comparator == "B0_CASH":
        navs = [cash] * len(bars)
        exposure = [False] * len(bars)
    elif comparator == "B1_SPY_BUY_HOLD":
        first = bars[0]
        shares = math.floor(cash / (first.raw_close * (1.0 + rate)))
        if shares <= 0:
            raise TurnOfMonthError("whole-share account cannot afford one share")
        notional, before = shares * first.raw_close, cash
        entry_cost = notional * rate
        cash -= notional + entry_cost
        turnover += notional / before
        total_cost += entry_cost
        for index, bar in enumerate(bars):
            marked = shares * first.raw_close * bar.adj_close / first.adj_close
            if index == len(bars) - 1:
                exit_cost = marked * rate
                turnover += marked / (cash + marked)
                total_cost += exit_cost
                navs.append(cash + marked - exit_cost)
            else:
                navs.append(cash + marked)
            exposure.append(index > 0)
    else:
        for bar in bars:
            if bar.session_date in entries:
                if active is not None:
                    raise TurnOfMonthError("episodes overlap")
                episode = entries[bar.session_date]
                before = cash
                shares = math.floor(cash / (bar.raw_close * (1.0 + rate)))
                if shares <= 0:
                    raise TurnOfMonthError("whole-share account cannot afford one share")
                notional = shares * bar.raw_close
                entry_cost = notional * rate
                cash -= notional + entry_cost
                turnover += notional / before
                total_cost += entry_cost
                utilizations.append(notional / before)
                active = (episode, shares, bar.raw_close, bar.adj_close, before)
                navs.append(cash + notional)
                exposure.append(False)
            elif active is not None:
                episode, shares, raw_entry, adj_entry, before = active
                marked = shares * raw_entry * bar.adj_close / adj_entry
                if bar.session_date == episode.exit_date:
                    exit_cost = marked * rate
                    turnover += marked / (cash + marked)
                    total_cost += exit_cost
                    cash += marked - exit_cost
                    episode_returns.append(cash / before - 1.0)
                    episode_profits.append(cash - before)
                    exit_years.append(bar.session_date.year)
                    navs.append(cash)
                    active = None
                else:
                    navs.append(cash + marked)
                exposure.append(True)
            else:
                navs.append(cash)
                exposure.append(False)
        if active is not None or len(episode_returns) != len(view.episodes):
            raise TurnOfMonthError("not every retained episode was completed")
    daily_returns = tuple(
        value / (initial_capital if index == 0 else navs[index - 1]) - 1.0
        for index, value in enumerate(navs)
    )
    return _metrics(
        daily_returns, tuple(exposure), turnover, total_cost / initial_capital,
        tuple(episode_returns), tuple(episode_profits), tuple(exit_years),
        tuple(utilizations), float(initial_capital),
    )


def combine_outcomes(outcomes: Sequence[dict[str, object]]) -> dict[str, object]:
    frozen = tuple(outcomes)
    if not frozen:
        raise TurnOfMonthError("at least one outcome is required")
    try:
        returns = tuple(value for item in frozen for value in item["_daily_returns"])
        exposure = tuple(value for item in frozen for value in item["_exposure"])
        episode_returns = tuple(value for item in frozen for value in item["_episode_returns"])
        episode_profits = tuple(value for item in frozen for value in item["_episode_profits"])
        exit_years = tuple(value for item in frozen for value in item["_exit_years"])
        utilizations = tuple(value for item in frozen for value in item["_utilizations"])
        initial = float(frozen[0]["_initial"])
        total_initial = math.fsum(float(item["_initial"]) for item in frozen)
        total_cost = math.fsum(float(item["_cost_usd"]) for item in frozen)
    except (KeyError, TypeError) as exc:
        raise TurnOfMonthError("outcomes must originate from evaluate") from exc
    return _metrics(
        returns, exposure, math.fsum(float(item["_turnover"]) for item in frozen),
        total_cost / total_initial, episode_returns, episode_profits, exit_years,
        utilizations, initial,
    )


def bootstrap_lower_bound(
    labelled: Sequence[tuple[date, float, bool]], draws: int = 10_000,
    seed: int = 20_260_719,
) -> float:
    blocks: dict[tuple[int, int], list[tuple[float, bool]]] = defaultdict(list)
    for day, value, flag in labelled:
        blocks[(day.year, day.month)].append((value, flag))
    ordered = tuple(blocks[key] for key in sorted(blocks))
    if not ordered or draws <= 0:
        raise TurnOfMonthError("bootstrap inputs are invalid")
    summaries = np.array(
        [[sum(v for v, f in block if f), sum(f for _, f in block),
          sum(v for v, f in block if not f), sum(not f for _, f in block)]
         for block in ordered],
        dtype=float,
    )
    samples = np.random.Generator(np.random.PCG64(seed)).integers(
        0, len(ordered), size=(draws, len(ordered))
    )
    totals = summaries[samples].sum(axis=1)
    if np.any(totals[:, 1] == 0) or np.any(totals[:, 3] == 0):
        raise TurnOfMonthError("a bootstrap replicate lacks a label")
    statistics = totals[:, 0] / totals[:, 1] - totals[:, 2] / totals[:, 3]
    return float(np.percentile(statistics, 5, method="linear"))


def adjudicate(
    results: dict[str, dict[str, dict[str, dict[str, object]]]],
    labels: dict[str, dict[str, float | int]], bootstrap_bound: float,
    input_failures: int = 0,
) -> dict[str, object]:
    if input_failures:
        return {"status": "INPUT_BLOCKED", "gates_passed": None, "gates_total": 8}
    try:
        v, h = results["validation"]["5"], results["holdout"]["5"]
        stress = results["combined"]["15"]["B2_SPY_CLASSIC_TURN_OF_MONTH"]
        h_b1, h_b2 = h["B1_SPY_BUY_HOLD"], h["B2_SPY_CLASSIC_TURN_OF_MONTH"]
        episode_contribution = stress["largest_episode_contribution"]
        year_contribution = stress["largest_calendar_year_contribution"]
        gates = (
            v["B2_SPY_CLASSIC_TURN_OF_MONTH"]["cagr"] > 0,
            h_b2["cagr"] > 0,
            labels["validation"]["mean_tom_daily_return"]
            > labels["validation"]["mean_non_tom_daily_return"],
            labels["holdout"]["mean_tom_daily_return"]
            > labels["holdout"]["mean_non_tom_daily_return"],
            bootstrap_bound > 0,
            h_b2["daily_maximum_drawdown"] > h_b1["daily_maximum_drawdown"]
            and h_b2["calmar"] is not None and h_b1["calmar"] is not None
            and h_b2["calmar"] > h_b1["calmar"],
            stress["cagr"] > 0 and year_contribution is not None
            and episode_contribution is not None and year_contribution < 0.4
            and episode_contribution < 0.2,
            input_failures == 0 and v["B2_SPY_CLASSIC_TURN_OF_MONTH"]["cagr"] > 0
            and h_b2["cagr"] > 0,
        )
    except (KeyError, TypeError):
        return {"status": "INPUT_BLOCKED", "gates_passed": None, "gates_total": 8}
    return {
        "status": "RETROSPECTIVE_REPLICATION_PASS_TO_EXTERNAL_REVIEW"
        if all(gates) else "RETROSPECTIVE_REPLICATION_FAIL",
        "gates_passed": sum(gates), "gates_total": len(gates), "gates": gates,
    }
