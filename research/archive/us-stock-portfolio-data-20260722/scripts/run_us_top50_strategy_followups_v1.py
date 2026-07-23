"""Read-only V0 diagnostic and two frozen sequential Top50 strategy discoveries."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import math
from pathlib import Path
from statistics import median
from typing import Any

import duckdb
import numpy as np

import run_us_current_top50_momentum_discovery_v0 as base


SNAPSHOT = "US_CURRENT_TOP50_DATA_MATERIALIZATION_V0_9_GSD_20260723"
DB_SHA = "6b29e56e8ccc79e2632e322c7671e7158408279c8411587f2c559eac9ec98d84"
CONTRACT_SHA = "77c5834dd3ce353d258cb700b9c881ea556a06545b2ba8608c5a207b50dc3281"
QUALIFIED_SHA = "39f10fd2e4eadc3bef920e9b8a87ae6b07e14048f2c6f57227371a380dfe31cb"
V0_SHA = "844e6e603f0dc380b6f0f4c5d92cc4ca0c35a8cd210beed63c39bd3f134bcacd"


class Blocked(RuntimeError):
    pass


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 << 20):
            h.update(chunk)
    return h.hexdigest()


def dump(path: Path, value: Any) -> None:
    base.dump(path, value)


def guards(repo: Path, db: Path, root: Path) -> list[str]:
    if sha(repo / "research/definitions/us_top50_strategy_followups_v1.json") != CONTRACT_SHA:
        raise Blocked("contract_sha_changed")
    if sha(repo / "research/results/us_current_top50_data_materialization_v0_9_gsd_discovery_fail_20260723.json") != V0_SHA:
        raise Blocked("v0_result_changed")
    identity = Path("/home/rongyu/workspace/quant-data/staging/us_current_top50_data_materialization_v0_9_gsd/qualified_identity.json")
    if sha(identity) != QUALIFIED_SHA or sha(db) != DB_SHA:
        raise Blocked("frozen_input_changed")
    symbols = json.loads(identity.read_text())["symbols"]
    if len(symbols) != 46 or len(set(symbols)) != 46:
        raise Blocked("qualified_identity_not_46")
    root.mkdir(parents=True, exist_ok=True)
    return symbols


def load(db: Path, symbols: list[str]) -> tuple[list[date], dict[str, dict[date, float]]]:
    wanted = symbols + ["SPY"]
    with duckdb.connect(str(db), read_only=True) as connection:
        rows = connection.execute(
            "SELECT symbol,trade_date,adj_close FROM us_equity_research.us_daily_total_return_research WHERE snapshot_id=? AND symbol IN (SELECT unnest(?)) ORDER BY trade_date,symbol",
            [SNAPSHOT, wanted],
        ).fetchall()
    prices: dict[str, dict[date, float]] = {}
    for symbol, day, value in rows:
        prices.setdefault(symbol, {})[day] = float(value)
    if set(prices) != set(wanted):
        raise Blocked("missing_price_symbol")
    return sorted(prices["SPY"]), prices


def matrix_returns(names: list[str], window: list[date], prices: dict[str, dict[date, float]]) -> np.ndarray:
    if len(window) < 2 or any(any(day not in prices[name] for day in window) for name in names):
        raise Blocked("incomplete_covariance_window")
    values = np.array([[prices[name][day] for name in names] for day in window], dtype=float)
    return values[1:] / values[:-1] - 1


def portfolio_vol(names: list[str], window: list[date], prices: dict[str, dict[date, float]]) -> tuple[float, np.ndarray]:
    returns = matrix_returns(names, window, prices)
    covariance = np.cov(returns, rowvar=False, ddof=1)
    covariance = np.atleast_2d(covariance)
    weights = np.full(len(names), 1 / len(names))
    variance = float(weights @ covariance @ weights)
    return math.sqrt(max(variance, 0) * 252), covariance


def percentile(values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(values, key=lambda symbol: (values[symbol], symbol))
    denominator = max(len(ordered) - 1, 1)
    return {symbol: index / denominator for index, symbol in enumerate(ordered)}


def schedules(kind: str, calendar: list[date], prices: dict[str, dict[date, float]], symbols: list[str]) -> tuple[dict[date, dict[str, float]], dict[date, dict[str, float]], list[float], list[dict[str, float]]]:
    month_ends = [day for i, day in enumerate(calendar[:-1]) if calendar[i + 1].month != day.month and day >= date(2016, 1, 1)]
    strategy, benchmark, held, gross, risk = {}, {}, [], [], []
    for formation in month_ends:
        i = calendar.index(formation)
        if i < 252:
            continue
        execution = calendar[i + 1]
        momentum = {}
        for symbol in symbols:
            series = prices[symbol]
            if all(calendar[j] in series for j in (i, i - 21, i - 252)) and execution in series:
                momentum[symbol] = series[calendar[i - 21]] / series[calendar[i - 252]] - 1
        if len(momentum) < 30:
            raise Blocked(f"monthly_qualified_below_30:{formation}")
        if kind in {"v0", "v1"}:
            ranked = sorted(momentum, key=lambda symbol: (-momentum[symbol], symbol))
            ranks = {symbol: rank for rank, symbol in enumerate(ranked, 1)}
            retained = [symbol for symbol in held if ranks.get(symbol, 999) <= 15]
            held = (retained + [symbol for symbol in ranked if symbol not in retained])[:10]
        else:
            window126 = calendar[i - 126 : i + 1]
            vol = {symbol: float(np.std(matrix_returns([symbol], window126, prices)[:, 0], ddof=1) * math.sqrt(252)) for symbol in momentum}
            mr, vr = percentile(momentum), percentile({symbol: -value for symbol, value in vol.items()})
            score = {symbol: 0.5 * mr[symbol] + 0.5 * vr[symbol] for symbol in momentum}
            ranked = sorted(score, key=lambda symbol: (-score[symbol], symbol))
            ranks = {symbol: rank for rank, symbol in enumerate(ranked, 1)}
            retained = [symbol for symbol in held if ranks.get(symbol, 999) <= 20]
            held = (retained + [symbol for symbol in ranked if symbol not in retained])[:15]
        g = 1.0
        if kind in {"v0", "v1"}:
            window63 = calendar[i - 63 : i + 1]
            selected_vol, covariance = portfolio_vol(held, window63, prices)
            if selected_vol <= 0:
                raise Blocked("nonpositive_selected_vol")
            if kind == "v1":
                benchmark_vol, _ = portfolio_vol(ranked, window63, prices)
                g = min(1.0, benchmark_vol / selected_vol)
            weights = np.full(len(held), 1 / len(held))
            variance = float(weights @ covariance @ weights)
            components = weights * (covariance @ weights) / variance
            risk.append({"max_component": float(max(components)), "top3_components": float(sum(sorted(components, reverse=True)[:3]))})
        strategy[execution] = {symbol: g / len(held) for symbol in held}
        benchmark[execution] = {symbol: 1 / len(ranked) for symbol in ranked}
        gross.append(g)
    return strategy, benchmark, gross, risk


def simulate(calendar: list[date], prices: dict[str, dict[date, float]], schedule: dict[date, dict[str, float]], cost: float) -> dict[str, Any]:
    weights: dict[str, float] = {}
    dates: list[date] = []
    equity: list[float] = []
    returns: list[float] = []
    value, turnover, total_cost, started = 1.0, 0.0, 0.0, False
    for prior, current in zip(calendar, calendar[1:]):
        daily = 0.0
        if started:
            daily = sum(weight * (prices[symbol][current] / prices[symbol][prior] - 1) for symbol, weight in weights.items())
            value *= 1 + daily
            stock = {symbol: weight * prices[symbol][current] / prices[symbol][prior] for symbol, weight in weights.items()}
            cash = 1 - sum(weights.values())
            total = cash + sum(stock.values())
            weights = {symbol: amount / total for symbol, amount in stock.items()}
        trade_cost = 0.0
        if current in schedule:
            target = schedule[current]
            traded = sum(abs(target.get(symbol, 0) - weights.get(symbol, 0)) for symbol in set(target) | set(weights))
            if started:
                turnover += traded / 2
            trade_cost = cost * traded
            value *= 1 - trade_cost
            total_cost += trade_cost
            weights, started = target, True
        if started:
            dates.append(current)
            equity.append(value)
            returns.append(daily - trade_cost)
    years = (dates[-1] - dates[0]).days / 365.25
    return {"dates": dates, "equity": equity, "returns": returns, "turnover": turnover / years, "total_cost_fraction": total_cost}


def metric(output: dict[str, Any]) -> dict[str, float]:
    return base.metric(output["dates"], output["equity"], output["returns"])


def monthly(output: dict[str, Any]) -> list[dict[str, Any]]:
    endings: dict[str, float] = {}
    for day, value in zip(output["dates"], output["equity"]):
        endings[f"{day:%Y-%m}"] = value
    prior, rows = 1.0, []
    for month, value in endings.items():
        rows.append({"month": month, "return": value / prior - 1})
        prior = value
    return rows


def series_sha(rows: list[dict[str, Any]]) -> str:
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def run_outputs(kind: str, calendar: list[date], prices: dict[str, dict[date, float]], symbols: list[str]) -> tuple[dict[str, Any], list[float], list[dict[str, float]]]:
    strategy, benchmark, gross, risk = schedules(kind, calendar, prices, symbols)
    outputs = {}
    for label, schedule in (("strategy", strategy), ("benchmark", benchmark)):
        for cost_name, cost in (("base", 0.0015), ("stress", 0.0030), ("gross", 0.0)):
            output = simulate(calendar, prices, schedule, cost)
            outputs[f"{label}_{cost_name}"] = {**output, "metrics": metric(output)}
    return outputs, gross, risk


def subperiods(strategy: dict[str, Any], benchmark: dict[str, Any]) -> dict[str, bool]:
    result = {}
    for label, start, end in (("2016-2019", date(2016, 1, 1), date(2019, 12, 31)), ("2020-2022", date(2020, 1, 1), date(2022, 12, 31)), ("2023-latest", date(2023, 1, 1), date.max)):
        indices = [i for i, day in enumerate(strategy["dates"]) if start <= day <= end]
        result[label] = strategy["equity"][indices[-1]] / strategy["equity"][indices[0]] > benchmark["equity"][indices[-1]] / benchmark["equity"][indices[0]]
    return result


def diagnostic(root: Path, calendar: list[date], prices: dict[str, dict[date, float]], symbols: list[str]) -> dict[str, Any]:
    outputs, _, risk = run_outputs("v0", calendar, prices, symbols)
    strategy, benchmark = outputs["strategy_base"], outputs["benchmark_base"]
    sm, bm = monthly(strategy), monthly(benchmark)
    sr, br = np.array([row["return"] for row in sm]), np.array([row["return"] for row in bm])
    covariance = float(np.cov(sr, br, ddof=1)[0, 1])
    vols = {row["month"]: float(np.std([value for day, value in zip(benchmark["dates"], benchmark["returns"]) if f"{day:%Y-%m}" == row["month"]], ddof=1) * math.sqrt(252)) for row in bm}
    vol_median = median(vols.values())
    frozen = {
        "strategy": {"cagr": 0.3744662083561068, "volatility": 0.28472249335552124, "sharpe": 1.2621528517050105, "max_drawdown": -0.32426289898908756},
        "benchmark": {"cagr": 0.2890136515539843, "volatility": 0.19701377568831055, "sharpe": 1.3899190249996958, "max_drawdown": -0.31601905666122587},
    }
    reconstructed = {"strategy": strategy["metrics"], "benchmark": benchmark["metrics"]}
    differences = {
        label: {key: reconstructed[label][key] - expected for key, expected in values.items()}
        for label, values in frozen.items()
    }
    if max(abs(value) for group in differences.values() for value in group.values()) > 1e-12:
        raise Blocked("v0_reconstruction_mismatch")
    regimes = {}
    for label, months in (("high", {month for month, value in vols.items() if value > vol_median}), ("low", {month for month, value in vols.items() if value <= vol_median})):
        pairs = [(s["return"], b["return"]) for s, b in zip(sm, bm) if s["month"] in months]
        regimes[label] = {"months": len(pairs), "strategy_mean_annualized": float(np.mean([x for x, _ in pairs]) * 12), "benchmark_mean_annualized": float(np.mean([y for _, y in pairs]) * 12), "excess_mean_annualized": float(np.mean([x - y for x, y in pairs]) * 12)}
    result = {
        "identity": "US_TOP50_V0_RISK_ATTRIBUTION_DIAGNOSTIC_V1",
        "outcome_diagnostic_only": True,
        "monthly_series": {"strategy_sha256": series_sha(sm), "benchmark_sha256": series_sha(bm), "count": len(sm)},
        "v0_reconciliation": {"passed": True, "differences": differences},
        "risk": {"annualized_vol": float(np.std(sr, ddof=1) * math.sqrt(12)), "downside_vol": float(np.std(np.minimum(sr, 0), ddof=1) * math.sqrt(12)), "beta_to_benchmark": covariance / float(np.var(br, ddof=1)), "correlation": float(np.corrcoef(sr, br)[0, 1])},
        "worst_10_months": sorted(sm, key=lambda row: row["return"])[:10],
        "concentration": {"equal_weight_hhi": 0.1, "mean_max_component_risk": float(np.mean([row["max_component"] for row in risk])) if risk else None, "mean_top3_component_risk": float(np.mean([row["top3_components"] for row in risk])) if risk else None},
        "turnover_cost": {"annual_turnover": strategy["turnover"], "base_total_cost_fraction": strategy["total_cost_fraction"], "gross_minus_base_cagr": outputs["strategy_gross"]["metrics"]["cagr"] - strategy["metrics"]["cagr"]},
        "regimes": regimes,
        "diagnosis": {"concentration": "material" if (risk and np.mean([row["top3_components"] for row in risk]) > 0.45) else "limited", "market_beta": "material" if covariance / float(np.var(br, ddof=1)) > 0.9 else "moderate", "volatility_clustering": "material" if regimes["high"]["excess_mean_annualized"] < regimes["low"]["excess_mean_annualized"] else "not_dominant"},
        "strategy_formula_changed": False,
    }
    dump(root / "v0_risk_diagnostic.json", result)
    return result


def formal(kind: str, root: Path, calendar: list[date], prices: dict[str, dict[date, float]], symbols: list[str], script: Path, db: Path) -> dict[str, Any]:
    identity = "US_TOP50_VOL_MANAGED_MOMENTUM_V1" if kind == "v1" else "US_TOP50_MOMENTUM_LOWVOL_COMPOSITE_V1"
    marker = root / f"{kind}_formal_run_started.json"
    if marker.exists():
        raise Blocked(f"{kind}_formal_run_already_started")
    dump(marker, {"identity": identity, "script_sha256": sha(script), "contract_sha256": CONTRACT_SHA, "db_path": str(db), "db_sha256": DB_SHA})
    outputs, gross, _ = run_outputs(kind, calendar, prices, symbols)
    strategy, benchmark = outputs["strategy_base"], outputs["benchmark_base"]
    sm, bm = strategy["metrics"], benchmark["metrics"]
    signs = subperiods(strategy, benchmark)
    median_gross = median(gross) if gross else 0
    gates = {"sharpe": sm["sharpe"] >= bm["sharpe"] + 0.05, "cagr_excess": sm["cagr"] > bm["cagr"] + 0.01, "drawdown": sm["max_drawdown"] >= bm["max_drawdown"] - 0.02, "stress_excess": outputs["strategy_stress"]["metrics"]["cagr"] > outputs["benchmark_stress"]["metrics"]["cagr"], "turnover": strategy["turnover"] <= 2.0, "subperiods": sum(signs.values()) >= 2, "median_gross": median_gross >= 0.5}
    chart = root / f"{kind}_equity_drawdown.svg"
    base.svg_chart(chart, strategy["dates"], strategy["equity"], benchmark["equity"])
    result = {"identity": identity, "result": "DISCOVERY_PASS" if all(gates.values()) else "DISCOVERY_FAIL", "formal_run_count": 1, "strategy_candidate_available": False, "input_db_path": str(db), "input_db_sha256": DB_SHA, "evaluation": [str(strategy["dates"][0]), str(strategy["dates"][-1])], "strategy_base": sm, "benchmark_base": bm, "strategy_stress": outputs["strategy_stress"]["metrics"], "benchmark_stress": outputs["benchmark_stress"]["metrics"], "stress_annualized_excess": outputs["strategy_stress"]["metrics"]["cagr"] - outputs["benchmark_stress"]["metrics"]["cagr"], "annual_turnover": strategy["turnover"], "median_gross_exposure": median_gross, "subperiod_relative_positive": signs, "gates": gates, "chart_path": str(chart), "chart_sha256": sha(chart), "current_holdings_output": False}
    dump(root / f"{kind}_result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("diagnostic", "v1", "backup"))
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--staging", type=Path, required=True)
    args = parser.parse_args()
    try:
        symbols = guards(args.repo, args.db, args.staging)
        calendar, prices = load(args.db, symbols)
        if args.phase == "diagnostic":
            result = diagnostic(args.staging, calendar, prices, symbols)
        else:
            if args.phase == "backup":
                prior = json.loads((args.staging / "v1_result.json").read_text())
                if prior["result"] != "DISCOVERY_FAIL":
                    raise Blocked("backup_not_authorized")
            result = formal(args.phase, args.staging, calendar, prices, symbols, Path(__file__), args.db)
    except (Blocked, OSError, ValueError, KeyError, duckdb.Error) as exc:
        result = {"status": "INPUT_BLOCKED", "phase": args.phase, "failure": f"{type(exc).__name__}:{exc}", "strategy_candidate_available": False}
        dump(args.staging / f"{args.phase}_blocked.json", result)
        print(json.dumps(result, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
