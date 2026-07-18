"""Pure, deterministic calculations for the frozen SPY trend/cash baseline."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
import math
from numbers import Real


class SPYTrendCashError(ValueError): ...


MetricValue = float | int | None | tuple[float, ...]


@dataclass(frozen=True)
class DailyBar:
    session_date: date
    adj_open: float
    adj_close: float

    def __post_init__(self) -> None:
        if type(self.session_date) is not date:
            raise SPYTrendCashError("session_date must be a date")
        for name, value in (("adj_open", self.adj_open), ("adj_close", self.adj_close)):
            if (
                isinstance(value, bool)
                or not isinstance(value, Real)
                or not math.isfinite(value)
                or value <= 0
            ):
                raise SPYTrendCashError(f"{name} must be positive and finite")


@dataclass(frozen=True)
class MonthlyInterval:
    decision_date: date
    entry_date: date
    exit_date: date
    spy_return: float
    trend_on: bool


def _validated_bars(rows: Sequence[DailyBar], cutoff: date) -> tuple[DailyBar, ...]:
    if type(cutoff) is not date:
        raise SPYTrendCashError("cutoff must be a date")
    bars = tuple(rows)
    if any(not isinstance(bar, DailyBar) for bar in bars):
        raise SPYTrendCashError("rows must contain DailyBar values")
    usable = tuple(bar for bar in bars if bar.session_date <= cutoff)
    if any(left.session_date >= right.session_date for left, right in zip(usable, usable[1:])):
        raise SPYTrendCashError("bars must have strictly increasing unique dates")
    return usable


def build_monthly_intervals(rows: Sequence[DailyBar], cutoff: date) -> tuple[MonthlyInterval, ...]:
    """Form full next-execution-open intervals; the final incomplete interval is absent."""
    bars = _validated_bars(rows, cutoff)
    month_ends = tuple(
        index
        for index, bar in enumerate(bars)
        if index + 1 == len(bars)
        or (bar.session_date.year, bar.session_date.month)
        != (bars[index + 1].session_date.year, bars[index + 1].session_date.month)
    )
    decisions = tuple(index for index in month_ends if index >= 199 and index + 1 < len(bars))
    intervals: list[MonthlyInterval] = []
    for current, following in zip(decisions, decisions[1:]):
        entry, exit_ = bars[current + 1], bars[following + 1]
        mean = math.fsum(bar.adj_close for bar in bars[current - 199 : current + 1]) / 200
        intervals.append(
            MonthlyInterval(
                bars[current].session_date,
                entry.session_date,
                exit_.session_date,
                exit_.adj_open / entry.adj_open - 1.0,
                bars[current].adj_close > mean,
            )
        )
    return tuple(intervals)


def select_split(
    intervals: Sequence[MonthlyInterval], start: date, end: date
) -> tuple[MonthlyInterval, ...]:
    """Keep only complete intervals whose execution dates both fall in the split."""
    if type(start) is not date or type(end) is not date or start > end:
        raise SPYTrendCashError("split bounds are invalid")
    frozen = tuple(intervals)
    if any(not isinstance(item, MonthlyInterval) for item in frozen):
        raise SPYTrendCashError("intervals must contain MonthlyInterval values")
    return tuple(item for item in frozen if start <= item.entry_date <= item.exit_date <= end)


def _metrics(
    returns: tuple[float, ...], exposure: tuple[float, ...], turnover: float,
    transitions: int, cost_drag: float,
) -> dict[str, float | int | None]:
    count = len(returns)
    value = math.prod(1.0 + result for result in returns)
    cumulative = value - 1.0
    cagr = value ** (12.0 / count) - 1.0 if count and value > 0.0 else -1.0
    mean = math.fsum(returns) / count if count else 0.0
    volatility = (
        math.sqrt(math.fsum((result - mean) ** 2 for result in returns) / (count - 1))
        * math.sqrt(12.0)
        if count > 1
        else 0.0
    )
    wealth, peak, drawdown = 1.0, 1.0, 0.0
    for result in returns:
        wealth *= 1.0 + result
        peak = max(peak, wealth)
        drawdown = min(drawdown, wealth / peak - 1.0)
    return {
        "complete_month_count": count, "cumulative_net_return": cumulative, "cagr": cagr,
        "annualized_volatility": volatility, "maximum_drawdown": drawdown,
        "calmar": cagr / abs(drawdown) if drawdown < 0.0 else None,
        "positive_month_fraction": (
            sum(result > 0.0 for result in returns) / count if count else 0.0
        ),
        "time_in_market": math.fsum(exposure) / count if count else 0.0,
        "state_transition_count": transitions, "one_way_turnover": turnover, "cost_drag": cost_drag,
    }


def evaluate(
    intervals: Sequence[MonthlyInterval], comparator: str, cost_bps: float
) -> dict[str, MetricValue]:
    """Evaluate cash, buy/hold, or frozen trend/cash without external state."""
    if comparator not in {"B0_CASH", "B1_SPY_BUY_HOLD", "B2_SPY_200D_TREND_CASH"}:
        raise SPYTrendCashError("unknown comparator")
    if (
        isinstance(cost_bps, bool)
        or not isinstance(cost_bps, Real)
        or not math.isfinite(cost_bps)
        or cost_bps < 0
    ):
        raise SPYTrendCashError("cost_bps must be finite and nonnegative")
    frozen = tuple(intervals)
    if any(not isinstance(item, MonthlyInterval) for item in frozen):
        raise SPYTrendCashError("intervals must contain MonthlyInterval values")
    exposure = tuple(
        0.0
        if comparator == "B0_CASH"
        else 1.0 if comparator == "B1_SPY_BUY_HOLD" else float(item.trend_on)
        for item in frozen
    )
    rate = float(cost_bps) / 10_000.0
    turnover = (
        exposure[0]
        + exposure[-1]
        + math.fsum(abs(right - left) for left, right in zip(exposure, exposure[1:]))
        if exposure
        else 0.0
    )
    transitions = sum(left != right for left, right in zip(exposure, exposure[1:]))
    gross_returns = tuple(level * item.spy_return for level, item in zip(exposure, frozen))
    net_returns = list(gross_returns)
    if net_returns:
        net_returns[0] = (1.0 - exposure[0] * rate) * (1.0 + net_returns[0]) - 1.0
        for index, (left, right) in enumerate(zip(exposure, exposure[1:]), 1):
            net_returns[index] = (1.0 - abs(right - left) * rate) * (1.0 + net_returns[index]) - 1.0
        net_returns[-1] = (1.0 + net_returns[-1]) * (1.0 - exposure[-1] * rate) - 1.0
    gross_value = math.prod(1.0 + result for result in gross_returns)
    net_value = math.prod(1.0 + result for result in net_returns)
    return {
        **_metrics(tuple(net_returns), exposure, turnover, transitions, gross_value - net_value),
        "_net_returns": tuple(net_returns),
        "_gross_returns": gross_returns,
        "_exposure": exposure,
    }


def combine_outcomes(
    outcomes: Sequence[dict[str, MetricValue]]
) -> dict[str, float | int | None]:
    """Combine already evaluated contiguous outcomes only when raw returns are unavailable."""
    frozen = tuple(outcomes)
    if not frozen:
        return _metrics((), (), 0.0, 0, 0.0)
    try:
        returns = tuple(value for item in frozen for value in item["_net_returns"])
        gross_returns = tuple(value for item in frozen for value in item["_gross_returns"])
        exposure = tuple(value for item in frozen for value in item["_exposure"])
    except KeyError as exc:
        raise SPYTrendCashError("outcomes must originate from evaluate") from exc
    return _metrics(
        returns,
        exposure,
        sum(float(item["one_way_turnover"]) for item in frozen),
        sum(int(item["state_transition_count"]) for item in frozen),
        math.prod(1.0 + value for value in gross_returns)
        - math.prod(1.0 + value for value in returns),
    )


def adjudicate(
    results: dict[str, dict[str, dict[str, MetricValue]]], data_failures: int
) -> dict[str, object]:
    """Apply the eight frozen gates. Results are keyed split then cost then comparator."""
    if data_failures:
        return {"status": "RETROSPECTIVE_BASELINE_FAIL", "gates_passed": 0, "gates_total": 8}
    primary, stress = "15", "30"
    try:
        v, h, c = (results[name][primary] for name in ("validation", "holdout", "combined"))
        cs = results["combined"][stress]
        gates = (
            v["B2"]["cagr"] > 0,
            h["B2"]["cagr"] > 0,
            h["B2"]["maximum_drawdown"] > h["B1"]["maximum_drawdown"],
            h["B2"]["calmar"] > h["B1"]["calmar"],
            c["B2"]["cagr"] >= 0.5 * c["B1"]["cagr"],
            0.2 <= c["B2"]["time_in_market"] <= 0.9,
            cs["B2"]["cagr"] > 0,
            data_failures == 0,
        )
    except (KeyError, TypeError):
        return {"status": "INPUT_BLOCKED", "gates_passed": 0, "gates_total": 8}
    return {
        "status": (
            "RETROSPECTIVE_BASELINE_PASS_TO_SHADOW_REVIEW"
            if all(gates)
            else "RETROSPECTIVE_BASELINE_FAIL"
        ),
        "gates_passed": sum(gates),
        "gates_total": 8,
        "gates": gates,
    }
