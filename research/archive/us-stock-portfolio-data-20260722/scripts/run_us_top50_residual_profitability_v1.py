"""Frozen residual-momentum discovery with a conditional profitability lane."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import duckdb
import numpy as np

import run_us_top50_strategy_followups_v1 as core


DB_SHA = "6b29e56e8ccc79e2632e322c7671e7158408279c8411587f2c559eac9ec98d84"
IDENTITY_SHA = "39f10fd2e4eadc3bef920e9b8a87ae6b07e14048f2c6f57227371a380dfe31cb"
CONTRACT_SHA = "137a489a4722a9fac6ec7fbf9eeb2bd0918f14c1c2032c37fe6d9661d9a42982"
PRIOR_RESULT_SHA = "3c71670dcc5f9dbc074763ab16e90d700d27c9704fea083fdf88ebab25f05a7a"
IDENTITY_PATH = Path("/home/rongyu/workspace/quant-data/staging/us_current_top50_data_materialization_v0_9_gsd/qualified_identity.json")


class Blocked(RuntimeError):
    pass


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def dump(path: Path, value: Any) -> None:
    core.dump(path, value)


def guard(repo: Path, db: Path) -> list[str]:
    checks = {
        repo / "research/definitions/us_top50_residual_profitability_v1.json": CONTRACT_SHA,
        repo / "research/results/us_top50_strategy_followups_v1_discovery_fail_20260723.json": PRIOR_RESULT_SHA,
        IDENTITY_PATH: IDENTITY_SHA,
        db: DB_SHA,
    }
    for path, expected in checks.items():
        if sha(path) != expected:
            raise Blocked(f"frozen_hash_changed:{path}")
    symbols = json.loads(IDENTITY_PATH.read_text())["symbols"]
    if len(symbols) != 46 or len(set(symbols)) != 46:
        raise Blocked("qualified_identity_not_46")
    return symbols


def paired_returns(
    symbol: str,
    start: int,
    stop: int,
    calendar: list[date],
    prices: dict[str, dict[date, float]],
) -> tuple[np.ndarray, np.ndarray]:
    stock, market = [], []
    for index in range(start, stop):
        prior, current = calendar[index - 1], calendar[index]
        if prior not in prices[symbol] or current not in prices[symbol]:
            continue
        stock.append(prices[symbol][current] / prices[symbol][prior] - 1)
        market.append(prices["SPY"][current] / prices["SPY"][prior] - 1)
    return np.asarray(stock), np.asarray(market)


def residual_score(
    estimate_stock: np.ndarray,
    estimate_market: np.ndarray,
    signal_stock: np.ndarray,
    signal_market: np.ndarray,
) -> float | None:
    if len(estimate_stock) < 450 or len(signal_stock) < 220:
        return None
    design = np.column_stack((np.ones(len(estimate_market)), estimate_market))
    alpha, beta = np.linalg.lstsq(design, estimate_stock, rcond=None)[0]
    residuals = signal_stock - alpha - beta * signal_market
    scale = float(np.std(residuals, ddof=1))
    if not math.isfinite(scale) or scale <= 0:
        return None
    score = float(np.mean(residuals) / scale * math.sqrt(252))
    return score if math.isfinite(score) else None


def schedules(
    calendar: list[date],
    prices: dict[str, dict[date, float]],
    symbols: list[str],
) -> tuple[dict[date, dict[str, float]], dict[date, dict[str, float]], list[dict[str, Any]]]:
    month_ends = [
        day
        for index, day in enumerate(calendar[:-1])
        if calendar[index + 1].month != day.month
    ]
    strategy, benchmark, held, coverage = {}, {}, [], []
    for formation in month_ends:
        index = calendar.index(formation)
        if index < 757:
            continue
        execution = calendar[index + 1]
        scores = {}
        for symbol in symbols:
            estimate = paired_returns(symbol, index - 756, index - 252, calendar, prices)
            signal = paired_returns(symbol, index - 252, index - 20, calendar, prices)
            score = residual_score(*estimate, *signal)
            if score is not None and execution in prices[symbol]:
                scores[symbol] = score
        if len(scores) < 30:
            raise Blocked(f"eligible_below_30:{formation}:{len(scores)}")
        ranked = sorted(scores, key=lambda symbol: (-scores[symbol], symbol))
        ranks = {symbol: rank for rank, symbol in enumerate(ranked, 1)}
        retained = [symbol for symbol in held if ranks.get(symbol, 999) <= 15]
        held = (retained + [symbol for symbol in ranked if symbol not in retained])[:10]
        strategy[execution] = {symbol: 0.1 for symbol in held}
        benchmark[execution] = {symbol: 1 / len(ranked) for symbol in ranked}
        coverage.append({"formation": str(formation), "execution": str(execution), "eligible": len(ranked)})
    if not strategy:
        raise Blocked("no_eligible_formations")
    return strategy, benchmark, coverage


def subperiods(strategy: dict[str, Any], benchmark: dict[str, Any]) -> dict[str, bool]:
    periods = (
        ("2018-2019", date(2018, 1, 1), date(2019, 12, 31)),
        ("2020-2022", date(2020, 1, 1), date(2022, 12, 31)),
        ("2023-latest", date(2023, 1, 1), date.max),
    )
    result = {}
    for label, start, end in periods:
        indices = [i for i, day in enumerate(strategy["dates"]) if start <= day <= end]
        if len(indices) < 2:
            raise Blocked(f"empty_subperiod:{label}")
        first, last = indices[0], indices[-1]
        strategy_return = strategy["equity"][last] / strategy["equity"][first] - 1
        benchmark_return = benchmark["equity"][last] / benchmark["equity"][first] - 1
        result[label] = strategy_return > benchmark_return
    return result


def formal(repo: Path, db: Path, root: Path) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    marker = root / "residual_formal_run_started.json"
    if marker.exists():
        raise Blocked("residual_formal_run_already_started")
    symbols = guard(repo, db)
    calendar, prices = core.load(db, symbols)
    script = Path(__file__)
    dump(marker, {"identity": "US_TOP50_MARKET_RESIDUAL_MOMENTUM_V1", "contract_sha256": CONTRACT_SHA, "script_sha256": sha(script), "database_sha256": DB_SHA})
    strategy_schedule, benchmark_schedule, coverage = schedules(calendar, prices, symbols)
    outputs = {}
    for label, schedule in (("strategy", strategy_schedule), ("benchmark", benchmark_schedule)):
        for cost_label, cost in (("base", 0.0015), ("stress", 0.0030)):
            output = core.simulate(calendar, prices, schedule, cost)
            outputs[f"{label}_{cost_label}"] = {**output, "metrics": core.metric(output)}
    strategy, benchmark = outputs["strategy_base"], outputs["benchmark_base"]
    sm, bm = strategy["metrics"], benchmark["metrics"]
    signs = subperiods(strategy, benchmark)
    gates = {
        "cagr_excess": sm["cagr"] > bm["cagr"] + 0.01,
        "sharpe": sm["sharpe"] >= bm["sharpe"] + 0.05,
        "drawdown": sm["max_drawdown"] >= bm["max_drawdown"] - 0.05,
        "stress_excess": outputs["strategy_stress"]["metrics"]["cagr"] > outputs["benchmark_stress"]["metrics"]["cagr"],
        "turnover": strategy["turnover"] <= 2.0,
        "subperiods": sum(signs.values()) >= 2,
    }
    chart = root / "residual_equity_drawdown.svg"
    core.base.svg_chart(chart, strategy["dates"], strategy["equity"], benchmark["equity"])
    result = {
        "identity": "US_TOP50_MARKET_RESIDUAL_MOMENTUM_V1",
        "result": "DISCOVERY_PASS" if all(gates.values()) else "DISCOVERY_FAIL",
        "formal_run_count": 1,
        "strategy_candidate_available": False,
        "survivorship_bias": True,
        "input_db_sha256": DB_SHA,
        "evaluation": [str(strategy["dates"][0]), str(strategy["dates"][-1])],
        "formation_count": len(coverage),
        "eligible_min": min(row["eligible"] for row in coverage),
        "eligible_max": max(row["eligible"] for row in coverage),
        "strategy_base": sm,
        "benchmark_base": bm,
        "strategy_stress": outputs["strategy_stress"]["metrics"],
        "benchmark_stress": outputs["benchmark_stress"]["metrics"],
        "stress_annualized_excess": outputs["strategy_stress"]["metrics"]["cagr"] - outputs["benchmark_stress"]["metrics"]["cagr"],
        "annual_turnover": strategy["turnover"],
        "subperiod_relative_positive": signs,
        "gates": gates,
        "chart_path": str(chart),
        "chart_sha256": sha(chart),
        "current_holdings_output": False,
    }
    dump(root / "residual_result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--staging", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = formal(args.repo, args.db, args.staging)
    except (Blocked, OSError, ValueError, KeyError, duckdb.Error) as exc:
        result = {"status": "INPUT_BLOCKED", "failure": f"{type(exc).__name__}:{exc}", "strategy_candidate_available": False}
        dump(args.staging / "residual_input_blocked.json", result)
        print(json.dumps(result, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
