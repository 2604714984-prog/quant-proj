"""Pure calculations for the frozen three-ETF inverse-volatility sprint."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
import math
from numbers import Real

import numpy as np
from quant_system.research import us_spy_qqq_gld_dual_momentum as dm


SYMBOLS = dm.SYMBOLS
Bar = dm.Bar
Panel = dm.Panel
prepare_panel = dm.prepare_panel
class InverseVolatilityError(ValueError): ...


@dataclass(frozen=True)
class Interval:
    decision_date: date
    entry_date: date
    exit_date: date
    weights: tuple[tuple[str, float], ...]
    volatilities: tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class SplitView:
    panel: Panel
    intervals: tuple[Interval, ...]
def capped_inverse_weights(
    volatilities: Sequence[tuple[str, float]], cap: float = 0.6
) -> tuple[tuple[str, float], ...]:
    values = tuple(volatilities)
    if tuple(name for name, _ in values) != SYMBOLS or not 0.0 < cap <= 1.0:
        raise InverseVolatilityError("volatility identity or cap is invalid")
    if cap * len(values) < 1.0 - 1e-12:
        raise InverseVolatilityError("cap cannot support full investment")
    scores: dict[str, float] = {}
    for symbol, value in values:
        if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value) or value <= 0.0:
            raise InverseVolatilityError("volatility must be positive and finite")
        scores[symbol] = 1.0 / float(value)
    weights, remaining = {}, set(SYMBOLS)
    while remaining:
        budget = 1.0 - math.fsum(weights.values())
        total = math.fsum(scores[symbol] for symbol in remaining)
        proposed = {symbol: budget * scores[symbol] / total for symbol in remaining}
        breached = tuple(symbol for symbol in SYMBOLS if symbol in remaining and proposed[symbol] > cap)
        if not breached:
            weights.update(proposed)
            break
        for symbol in breached:
            weights[symbol] = cap
            remaining.remove(symbol)
    ordered = tuple((symbol, weights[symbol]) for symbol in SYMBOLS)
    if abs(math.fsum(value for _, value in ordered) - 1.0) > 1e-12 or any(value > cap + 1e-12 for _, value in ordered):
        raise InverseVolatilityError("capped weights are not fully invested")
    return ordered
def build_intervals(panel: Panel) -> tuple[Interval, ...]:
    if not isinstance(panel, Panel):
        raise InverseVolatilityError("panel identity is invalid")
    dates, lookup = panel.dates, panel.lookup
    ends = [i for i, day in enumerate(dates[:-1]) if (day.year, day.month) != (dates[i + 1].year, dates[i + 1].month)]
    decisions = [index for index in ends if index >= 60 and index + 1 < len(dates)]
    signals: list[tuple[int, tuple[tuple[str, float], ...], tuple[tuple[str, float], ...]]] = []
    for index in decisions:
        volatilities = []
        for symbol in SYMBOLS:
            returns = tuple(
                lookup[(dates[offset], symbol)].adj_close / lookup[(dates[offset - 1], symbol)].adj_close - 1.0
                for offset in range(index - 59, index + 1)
            )
            mean = math.fsum(returns) / 60.0
            sigma = math.sqrt(math.fsum((value - mean) ** 2 for value in returns) / 59.0)
            volatilities.append((symbol, sigma))
        frozen = tuple(volatilities)
        signals.append((index, capped_inverse_weights(frozen), frozen))
    return tuple(
        Interval(dates[left], dates[left + 1], dates[right + 1], weights, volatilities)
        for (left, weights, volatilities), (right, _, _) in zip(signals, signals[1:])
    )
def select_split(panel: Panel, intervals: Sequence[Interval], start: date, end: date) -> SplitView:
    if type(start) is not date or type(end) is not date or start > end:
        raise InverseVolatilityError("split bounds are invalid")
    kept = tuple(item for item in intervals if start <= item.decision_date < item.entry_date < item.exit_date <= end)
    if not kept:
        raise InverseVolatilityError("split has no complete intervals")
    first, last = kept[0].entry_date, kept[-1].exit_date
    dates = tuple(day for day in panel.dates if first <= day <= last)
    rows = tuple(row for row in panel.rows if first <= row.session_date <= last)
    return SplitView(Panel(dates, rows), kept)


def _position_value(position: tuple[int, float, float], bar: Bar) -> float:
    shares, raw_entry, adj_entry = position
    return shares * raw_entry * bar.adj_open / adj_entry


def _number(value: object) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value)


def _greater(value: object, *others: object) -> bool:
    return _number(value) and all(_number(other) and value > other for other in others)  # type: ignore[operator]


def evaluate(view: SplitView, cost_bps: float) -> dict[str, object]:
    if isinstance(cost_bps, bool) or not isinstance(cost_bps, Real) or not math.isfinite(cost_bps) or cost_bps < 0:
        raise InverseVolatilityError("cost must be finite and nonnegative")
    dates, lookup, rate = view.panel.dates, view.panel.lookup, float(cost_bps) / 10_000.0
    targets = {item.entry_date: item.weights for item in view.intervals}
    cash, positions, turnover, cost = 40_000.0, {}, 0.0, 0.0
    navs, exposure, utilizations, residuals, monthly_turnovers = [], [], [], [], []
    target_sums = {symbol: 0.0 for symbol in SYMBOLS}
    cap_months = 0
    for index, day in enumerate(dates):
        before = cash + math.fsum(_position_value(position, lookup[(day, symbol)]) for symbol, position in positions.items())
        weights = targets.get(day)
        if weights is not None:
            sales = math.fsum(_position_value(position, lookup[(day, symbol)]) for symbol, position in positions.items())
            turnover += sales / before
            cost += sales * rate
            cash = before - sales * rate
            available, positions = cash, {}
            purchases = 0.0
            for symbol, weight in weights:
                bar = lookup[(day, symbol)]
                shares = math.floor(weight * available / (bar.raw_open * (1.0 + rate)))
                if shares <= 0:
                    raise InverseVolatilityError("whole-share target cannot afford one share")
                notional = shares * bar.raw_open
                purchases += notional
                cost += notional * rate
                cash -= notional * (1.0 + rate)
                positions[symbol] = (shares, bar.raw_open, bar.adj_open)
                target_sums[symbol] += weight
            monthly_turnovers.append(sales / before + purchases / available)
            turnover += purchases / available
            utilizations.append(purchases / available)
            residuals.append(cash / available)
            cap_months += int(any(abs(weight - 0.6) <= 1e-12 for _, weight in weights))
        if index == len(dates) - 1 and positions:
            sales = math.fsum(_position_value(position, lookup[(day, symbol)]) for symbol, position in positions.items())
            before = cash + sales
            turnover += sales / before
            cost += sales * rate
            cash += sales * (1.0 - rate)
            positions = {}
        navs.append(cash + math.fsum(_position_value(position, lookup[(day, symbol)]) for symbol, position in positions.items()))
        exposure.append(bool(positions))
    returns = tuple(value / (40_000.0 if index == 0 else navs[index - 1]) - 1.0 for index, value in enumerate(navs))
    positions_by_day = {day: index for index, day in enumerate(dates)}
    months = tuple(
        navs[positions_by_day[item.exit_date]] / (40_000.0 if index == 0 else navs[positions_by_day[item.entry_date]]) - 1.0
        for index, item in enumerate(view.intervals)
    )
    extras = {
        "mean_target_weights": {symbol: target_sums[symbol] / len(view.intervals) for symbol in SYMBOLS},
        "cap_binding_month_count": cap_months,
        "mean_residual_cash_fraction": math.fsum(residuals) / len(residuals),
        "maximum_residual_cash_fraction": max(residuals),
        "mean_monthly_one_way_turnover": math.fsum(monthly_turnovers) / len(monthly_turnovers),
    }
    return dm._summarize(dates, returns, tuple(exposure), months, len(view.intervals), turnover, cost, tuple(utilizations), extras)
def combine_outcomes(outcomes: Sequence[dict[str, object]]) -> dict[str, object]:
    frozen = tuple(outcomes)
    result = dm.combine_outcomes(frozen)
    counts = tuple(int(item["complete_interval_count"]) for item in frozen)
    total = sum(counts)
    if total <= 0 or any("mean_target_weights" not in item for item in frozen):
        raise InverseVolatilityError("inverse-volatility outcomes are incomplete")
    result.update({
        "mean_target_weights": {symbol: math.fsum(float(item["mean_target_weights"][symbol]) * count for item, count in zip(frozen, counts)) / total for symbol in SYMBOLS},  # type: ignore[index]
        "cap_binding_month_count": sum(int(item["cap_binding_month_count"]) for item in frozen),
        "mean_residual_cash_fraction": math.fsum(float(item["mean_residual_cash_fraction"]) * count for item, count in zip(frozen, counts)) / total,
        "maximum_residual_cash_fraction": max(float(item["maximum_residual_cash_fraction"]) for item in frozen),
        "mean_monthly_one_way_turnover": math.fsum(float(item["mean_monthly_one_way_turnover"]) * count for item, count in zip(frozen, counts)) / total,
    })
    return result
def _sharpe(values: np.ndarray) -> float:
    if values.ndim != 1 or len(values) < 2:
        raise InverseVolatilityError("Sharpe input is incomplete")
    deviation = float(np.std(values, ddof=1))
    if not math.isfinite(deviation) or deviation <= 0.0:
        raise InverseVolatilityError("Sharpe volatility must be positive")
    return math.sqrt(252.0) * float(np.mean(values)) / deviation


def paired_sharpe_test(
    strategy: Sequence[float], comparator: Sequence[float], *, draws: int = 20_000,
    block: int = 20, seed: int = 2_026_071_902,
) -> dict[str, object]:
    left, right = np.asarray(strategy, dtype=float), np.asarray(comparator, dtype=float)
    if left.shape != right.shape or left.ndim != 1 or len(left) < block or draws < 1:
        raise InverseVolatilityError("paired bootstrap inputs are invalid")
    if not np.isfinite(left).all() or not np.isfinite(right).all():
        raise InverseVolatilityError("paired bootstrap returns must be finite")
    observed, rng = _sharpe(left) - _sharpe(right), np.random.Generator(np.random.PCG64(seed))
    centered = np.empty(draws)
    blocks = math.ceil(len(left) / block)
    offsets = np.arange(block)
    for draw in range(draws):
        starts = rng.integers(0, len(left), size=blocks)
        indices = ((starts[:, None] + offsets) % len(left)).reshape(-1)[: len(left)]
        centered[draw] = _sharpe(left[indices]) - _sharpe(right[indices]) - observed
    raw_p = (1 + int(np.count_nonzero(centered >= observed))) / (draws + 1)
    return {"observed_difference": observed, "raw_p": raw_p, "_centered": centered}


def holm(tests: Sequence[dict[str, object]], alpha: float = 0.025) -> tuple[dict[str, object], ...]:
    frozen = tuple(tests)
    if not frozen or not 0.0 < alpha < 1.0:
        raise InverseVolatilityError("Holm inputs are invalid")
    order = sorted(range(len(frozen)), key=lambda index: (float(frozen[index]["raw_p"]), index))
    adjusted, running = {}, 0.0
    for rank, index in enumerate(order, 1):
        multiplier = len(frozen) - rank + 1
        running = max(running, min(1.0, multiplier * float(frozen[index]["raw_p"])))
        threshold = alpha / multiplier
        observed = float(frozen[index]["observed_difference"])
        lower = observed - float(np.quantile(frozen[index]["_centered"], 1.0 - threshold, method="linear"))
        adjusted[index] = {"observed_difference": observed, "raw_p": float(frozen[index]["raw_p"]),
                           "holm_adjusted_p": running, "holm_lower_bound": lower,
                           "passed": running <= alpha and lower > 0.0}
    return tuple(adjusted[index] for index in range(len(frozen)))


def adjudicate(results: dict[str, object], inference: Sequence[dict[str, object]], input_failures: int = 0) -> dict[str, object]:
    if input_failures:
        return {"status": "INPUT_BLOCKED", "gates_passed": None, "gates_total": 10}
    try:
        validation, holdout = results["validation"]["15"], results["holdout"]["15"]  # type: ignore[index]
        combined, stress = results["combined"]["15"], results["combined"]["30"]  # type: ignore[index]
        b4v, b4h, b4c, b4s = validation["B4_INVERSE_VOLATILITY"], holdout["B4_INVERSE_VOLATILITY"], combined["B4_INVERSE_VOLATILITY"], stress["B4_INVERSE_VOLATILITY"]
        b1h, b2v, b2h, b1c, b2c, b2s = holdout["B1_SPY_BUY_HOLD"], validation["B2_STATIC_EQUAL_WEIGHT_SPY_QQQ_GLD"], holdout["B2_STATIC_EQUAL_WEIGHT_SPY_QQQ_GLD"], combined["B1_SPY_BUY_HOLD"], combined["B2_STATIC_EQUAL_WEIGHT_SPY_QQQ_GLD"], stress["B2_STATIC_EQUAL_WEIGHT_SPY_QQQ_GLD"]
        gates = (_greater(b4v["cagr"], 0), _greater(b4h["cagr"], 0), _number(b4v["annualized_volatility"]) and _number(b2v["annualized_volatility"]) and b4v["annualized_volatility"] < b2v["annualized_volatility"],
                 _number(b4h["annualized_volatility"]) and _number(b2h["annualized_volatility"]) and b4h["annualized_volatility"] < b2h["annualized_volatility"], _greater(b4h["daily_maximum_drawdown"], b1h["daily_maximum_drawdown"], b2h["daily_maximum_drawdown"]),
                 _greater(b4h["calmar"], b1h["calmar"], b2h["calmar"]), _greater(b4c["cagr"], 0) and _number(b1c["cagr"]) and b4c["cagr"] >= 0.5 * b1c["cagr"],
                 _greater(b4c["calmar"], b2c["calmar"]), _greater(b4s["cagr"], 0) and _greater(b4s["calmar"], b2s["calmar"]) and _number(b4s["largest_calendar_year_profit_contribution"]) and b4s["largest_calendar_year_profit_contribution"] < 0.4,
                 len(inference) == 4 and all(bool(item["passed"]) for item in inference))
    except (KeyError, TypeError, ValueError):
        return {"status": "INPUT_BLOCKED", "gates_passed": None, "gates_total": 10}
    return {"status": "RETROSPECTIVE_INVERSE_VOLATILITY_PASS_TO_EXTERNAL_REVIEW" if all(gates) else "RETROSPECTIVE_INVERSE_VOLATILITY_FAIL",
            "gates_passed": sum(gates), "gates_total": 10, "gates": gates}
