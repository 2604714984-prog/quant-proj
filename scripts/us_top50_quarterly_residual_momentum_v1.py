"""One-use discovery adapter for quarterly US Top-50 residual momentum."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

import duckdb


RESEARCH_ID = "US_TOP50_QUARTERLY_RESIDUAL_MOMENTUM_V1"
SNAPSHOT_ID = "US_CURRENT_TOP50_DATA_MATERIALIZATION_V0_9_GSD_20260723"
DATABASE_SHA256 = "6b29e56e8ccc79e2632e322c7671e7158408279c8411587f2c559eac9ec98d84"
IDENTITY_SHA256 = "39f10fd2e4eadc3bef920e9b8a87ae6b07e14048f2c6f57227371a380dfe31cb"
CONTRACT_SHA256 = "3e798e6d2ebfb120868ea79a5c76fa787d1aa695ef77f8aef43d2112f92458d9"
FORMATION_MONTHS = frozenset((3, 6, 9, 12))


class Blocked(RuntimeError):
    """Raised when a frozen identity or data gate is not satisfied."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(
        json.dumps(value, sort_keys=True, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def validate_inputs(repo: Path, database: Path, identity: Path) -> list[str]:
    contract = repo / "research/definitions/us_top50_quarterly_residual_momentum_v1.json"
    checks = {
        contract: CONTRACT_SHA256,
        database: DATABASE_SHA256,
        identity: IDENTITY_SHA256,
    }
    for path, expected in checks.items():
        if not path.is_file() or sha256(path) != expected:
            raise Blocked(f"frozen_hash_changed:{path.name}")
    symbols = json.loads(identity.read_text(encoding="utf-8"))["symbols"]
    if len(symbols) != 46 or len(set(symbols)) != 46:
        raise Blocked("qualified_identity_not_46_unique_symbols")
    return symbols


def load_prices(
    database: Path,
    symbols: list[str],
) -> tuple[list[date], dict[str, dict[date, float]]]:
    wanted = symbols + ["SPY"]
    with duckdb.connect(str(database), read_only=True) as connection:
        rows = connection.execute(
            """
            SELECT symbol, trade_date, adj_close
            FROM us_equity_research.us_daily_total_return_research
            WHERE snapshot_id = ?
              AND symbol IN (SELECT unnest(?))
            ORDER BY trade_date, symbol
            """,
            [SNAPSHOT_ID, wanted],
        ).fetchall()
    prices: dict[str, dict[date, float]] = {}
    for symbol, day, value in rows:
        prices.setdefault(symbol, {})[day] = float(value)
    if set(prices) != set(wanted):
        raise Blocked("missing_price_symbol")
    return sorted(prices["SPY"]), prices


def paired_returns(
    symbol: str,
    start: int,
    stop: int,
    calendar: list[date],
    prices: dict[str, dict[date, float]],
) -> tuple[list[float], list[float]]:
    stock_returns: list[float] = []
    market_returns: list[float] = []
    for index in range(start, stop):
        prior, current = calendar[index - 1], calendar[index]
        if prior not in prices[symbol] or current not in prices[symbol]:
            continue
        stock_returns.append(prices[symbol][current] / prices[symbol][prior] - 1)
        market_returns.append(prices["SPY"][current] / prices["SPY"][prior] - 1)
    return stock_returns, market_returns


def residual_score(
    estimate_stock: list[float],
    estimate_market: list[float],
    signal_stock: list[float],
    signal_market: list[float],
) -> float | None:
    if (
        len(estimate_stock) < 450
        or len(signal_stock) < 220
        or len(estimate_stock) != len(estimate_market)
        or len(signal_stock) != len(signal_market)
    ):
        return None
    count = len(estimate_market)
    market_mean = sum(estimate_market) / count
    stock_mean = sum(estimate_stock) / count
    denominator = sum((value - market_mean) ** 2 for value in estimate_market)
    if denominator <= 0:
        return None
    beta = sum(
        (market - market_mean) * (stock - stock_mean)
        for market, stock in zip(estimate_market, estimate_stock)
    ) / denominator
    alpha = stock_mean - beta * market_mean
    residuals = [
        stock - alpha - beta * market
        for stock, market in zip(signal_stock, signal_market)
    ]
    residual_mean = sum(residuals) / len(residuals)
    residual_variance = sum(
        (value - residual_mean) ** 2 for value in residuals
    ) / (len(residuals) - 1)
    scale = math.sqrt(residual_variance)
    if not math.isfinite(scale) or scale <= 0:
        return None
    score = residual_mean / scale * math.sqrt(252)
    return score if math.isfinite(score) else None


def is_quarter_end(index: int, calendar: list[date]) -> bool:
    day = calendar[index]
    return (
        day.month in FORMATION_MONTHS
        and index + 1 < len(calendar)
        and calendar[index + 1].month != day.month
    )


def select_holdings(scores: dict[str, float], prior_holdings: list[str]) -> list[str]:
    ranked = sorted(scores, key=lambda symbol: (-scores[symbol], symbol))
    ranks = {symbol: rank for rank, symbol in enumerate(ranked, 1)}
    retained = [symbol for symbol in prior_holdings if ranks.get(symbol, 999) <= 15]
    return (retained + [symbol for symbol in ranked if symbol not in retained])[:10]


def build_schedules(
    calendar: list[date],
    prices: dict[str, dict[date, float]],
    symbols: list[str],
) -> tuple[
    dict[date, dict[str, float]],
    dict[date, dict[str, float]],
    list[dict[str, Any]],
]:
    formations = [
        day
        for index, day in enumerate(calendar[:-1])
        if is_quarter_end(index, calendar)
    ]
    strategy: dict[date, dict[str, float]] = {}
    benchmark: dict[date, dict[str, float]] = {}
    held: list[str] = []
    coverage: list[dict[str, Any]] = []
    for formation in formations:
        index = calendar.index(formation)
        if index < 757:
            continue
        execution = calendar[index + 1]
        scores: dict[str, float] = {}
        for symbol in symbols:
            estimate = paired_returns(
                symbol,
                index - 756,
                index - 252,
                calendar,
                prices,
            )
            signal = paired_returns(
                symbol,
                index - 252,
                index - 20,
                calendar,
                prices,
            )
            score = residual_score(*estimate, *signal)
            if score is not None and execution in prices[symbol]:
                scores[symbol] = score
        if len(scores) < 30:
            raise Blocked(f"eligible_below_30:{formation}:{len(scores)}")
        ranked = sorted(scores, key=lambda symbol: (-scores[symbol], symbol))
        held = select_holdings(scores, held)
        strategy[execution] = {symbol: 0.1 for symbol in held}
        benchmark[execution] = {symbol: 1 / len(ranked) for symbol in ranked}
        coverage.append(
            {
                "formation": str(formation),
                "execution": str(execution),
                "eligible": len(ranked),
            }
        )
    if len(coverage) < 30:
        raise Blocked(f"complete_formations_below_30:{len(coverage)}")
    return strategy, benchmark, coverage


def simulate(
    calendar: list[date],
    prices: dict[str, dict[date, float]],
    schedule: dict[date, dict[str, float]],
    one_way_cost: float,
) -> dict[str, Any]:
    weights: dict[str, float] = {}
    dates: list[date] = []
    equity: list[float] = []
    returns: list[float] = []
    value, turnover, started = 1.0, 0.0, False
    for prior, current in zip(calendar, calendar[1:]):
        daily_return = 0.0
        if started:
            daily_return = sum(
                weight * (prices[symbol][current] / prices[symbol][prior] - 1)
                for symbol, weight in weights.items()
            )
            value *= 1 + daily_return
            stock_values = {
                symbol: weight * prices[symbol][current] / prices[symbol][prior]
                for symbol, weight in weights.items()
            }
            cash = 1 - sum(weights.values())
            total = cash + sum(stock_values.values())
            weights = {
                symbol: stock_value / total
                for symbol, stock_value in stock_values.items()
            }
        trade_cost = 0.0
        if current in schedule:
            target = schedule[current]
            traded = sum(
                abs(target.get(symbol, 0) - weights.get(symbol, 0))
                for symbol in set(target) | set(weights)
            )
            if started:
                turnover += traded / 2
            trade_cost = one_way_cost * traded
            value *= 1 - trade_cost
            weights, started = target, True
        if started:
            dates.append(current)
            equity.append(value)
            returns.append(daily_return - trade_cost)
    years = (dates[-1] - dates[0]).days / 365.25
    return {
        "dates": dates,
        "equity": equity,
        "returns": returns,
        "turnover": turnover / years,
    }


def metrics(output: dict[str, Any]) -> dict[str, float]:
    dates, equity, returns = output["dates"], output["equity"], output["returns"]
    years = (dates[-1] - dates[0]).days / 365.25
    cagr = (equity[-1] / equity[0]) ** (1 / years) - 1
    mean = sum(returns) / len(returns)
    variance = sum((value - mean) ** 2 for value in returns) / (len(returns) - 1)
    volatility = math.sqrt(variance) * math.sqrt(252)
    peak, max_drawdown = equity[0], 0.0
    for value in equity:
        peak = max(peak, value)
        max_drawdown = min(max_drawdown, value / peak - 1)
    return {
        "cagr": cagr,
        "volatility": volatility,
        "sharpe": mean / math.sqrt(variance) * math.sqrt(252),
        "max_drawdown": max_drawdown,
    }


def subperiod_results(
    strategy: dict[str, Any],
    benchmark: dict[str, Any],
) -> dict[str, bool]:
    periods = (
        ("2018-2019", date(2018, 1, 1), date(2019, 12, 31)),
        ("2020-2022", date(2020, 1, 1), date(2022, 12, 31)),
        ("2023-latest", date(2023, 1, 1), date.max),
    )
    results: dict[str, bool] = {}
    for label, start, end in periods:
        indices = [
            index
            for index, day in enumerate(strategy["dates"])
            if start <= day <= end
        ]
        if len(indices) < 2:
            raise Blocked(f"empty_subperiod:{label}")
        first, last = indices[0], indices[-1]
        strategy_return = strategy["equity"][last] / strategy["equity"][first] - 1
        benchmark_return = benchmark["equity"][last] / benchmark["equity"][first] - 1
        results[label] = strategy_return > benchmark_return
    return results


def formal_run(
    repo: Path,
    database: Path,
    identity: Path,
    staging: Path,
) -> dict[str, Any]:
    staging.mkdir(parents=True, exist_ok=True)
    marker = staging / "formal_run_started.json"
    if marker.exists():
        raise Blocked("formal_run_already_started")
    symbols = validate_inputs(repo, database, identity)
    write_json(
        marker,
        {
            "research_id": RESEARCH_ID,
            "adapter_path": str(Path(__file__)),
            "adapter_sha256": sha256(Path(__file__)),
            "contract_path": str(
                repo / "research/definitions/us_top50_quarterly_residual_momentum_v1.json"
            ),
            "contract_sha256": CONTRACT_SHA256,
            "database_path": str(database),
            "database_sha256": DATABASE_SHA256,
            "qualified_identity_path": str(identity),
            "qualified_identity_sha256": IDENTITY_SHA256,
            "formal_run_number": 1,
        },
    )
    calendar, prices = load_prices(database, symbols)
    strategy_schedule, benchmark_schedule, coverage = build_schedules(
        calendar,
        prices,
        symbols,
    )
    outputs: dict[str, Any] = {}
    for label, schedule in (
        ("strategy", strategy_schedule),
        ("benchmark", benchmark_schedule),
    ):
        for cost_label, cost in (("base", 0.0015), ("stress", 0.0030)):
            output = simulate(calendar, prices, schedule, cost)
            outputs[f"{label}_{cost_label}"] = {
                **output,
                "metrics": metrics(output),
            }
    strategy = outputs["strategy_base"]
    benchmark = outputs["benchmark_base"]
    strategy_metrics = strategy["metrics"]
    benchmark_metrics = benchmark["metrics"]
    signs = subperiod_results(strategy, benchmark)
    stress_excess = (
        outputs["strategy_stress"]["metrics"]["cagr"]
        - outputs["benchmark_stress"]["metrics"]["cagr"]
    )
    gates = {
        "cagr_excess": strategy_metrics["cagr"] > benchmark_metrics["cagr"] + 0.01,
        "sharpe": strategy_metrics["sharpe"] >= benchmark_metrics["sharpe"] + 0.05,
        "drawdown": (
            strategy_metrics["max_drawdown"]
            >= benchmark_metrics["max_drawdown"] - 0.05
        ),
        "stress_excess": stress_excess > 0,
        "turnover": strategy["turnover"] <= 1.25,
        "subperiods": sum(signs.values()) >= 2,
        "eligible_stocks": min(row["eligible"] for row in coverage) >= 30,
        "complete_formations": len(coverage) >= 30,
    }
    result = {
        "research_id": RESEARCH_ID,
        "market": "US_EQUITIES",
        "phase": "DISCOVERY_EXECUTION_AND_ADJUDICATION",
        "status": "current" if all(gates.values()) else "rejected",
        "result": "DISCOVERY_PASS" if all(gates.values()) else "DISCOVERY_FAIL",
        "formal_run_count": 1,
        "strategy_candidate_available": False,
        "survivorship_bias": True,
        "input": {
            "database_path": str(database),
            "database_sha256": DATABASE_SHA256,
            "qualified_identity_path": str(identity),
            "qualified_identity_sha256": IDENTITY_SHA256,
            "stock_count": len(symbols),
        },
        "evaluation": [str(strategy["dates"][0]), str(strategy["dates"][-1])],
        "formation_count": len(coverage),
        "eligible_min": min(row["eligible"] for row in coverage),
        "eligible_max": max(row["eligible"] for row in coverage),
        "strategy_base": strategy_metrics,
        "benchmark_base": benchmark_metrics,
        "strategy_stress": outputs["strategy_stress"]["metrics"],
        "benchmark_stress": outputs["benchmark_stress"]["metrics"],
        "stress_annualized_excess": stress_excess,
        "annual_turnover": strategy["turnover"],
        "subperiod_relative_positive": signs,
        "gates": gates,
        "gate_pass_count": sum(gates.values()),
        "gate_total_count": len(gates),
        "failed_gates": [name for name, passed in gates.items() if not passed],
        "current_holdings_output": False,
        "pit_validation_status": (
            "AUTHORIZED_TO_PREREGISTER_NOT_STARTED"
            if all(gates.values())
            else "NOT_STARTED_DISCOVERY_FAIL"
        ),
        "boundaries": {
            "recommendation": False,
            "paper": False,
            "broker": False,
            "live": False,
            "auto": False,
        },
    }
    write_json(staging / "discovery_result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--identity", type=Path, required=True)
    parser.add_argument("--staging", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = formal_run(args.repo, args.db, args.identity, args.staging)
    except (Blocked, OSError, ValueError, KeyError, duckdb.Error) as exc:
        result = {
            "research_id": RESEARCH_ID,
            "status": "blocked-on-data",
            "result": "INPUT_BLOCKED",
            "failure": f"{type(exc).__name__}:{exc}",
            "strategy_candidate_available": False,
        }
        write_json(args.staging / "input_blocked.json", result)
        print(json.dumps(result, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
