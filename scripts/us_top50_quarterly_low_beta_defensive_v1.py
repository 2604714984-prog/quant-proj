"""One-use discovery adapter for quarterly US Top-50 low beta."""

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


RESEARCH_ID = "US_TOP50_QUARTERLY_LOW_BETA_DEFENSIVE_V1"
SNAPSHOT_ID = "US_CURRENT_TOP50_DATA_MATERIALIZATION_V0_9_GSD_20260723"
DATABASE_SHA256 = "6b29e56e8ccc79e2632e322c7671e7158408279c8411587f2c559eac9ec98d84"
IDENTITY_SHA256 = "39f10fd2e4eadc3bef920e9b8a87ae6b07e14048f2c6f57227371a380dfe31cb"
CONTRACT_SHA256 = "9990eb19f9e958f8d6e2b7bacaf9cff695c7302036278f3470efd9c728adfd76"
FORMATION_MONTHS = frozenset((3, 6, 9, 12))
EVALUATION_START = date(2018, 1, 1)


class Blocked(RuntimeError):
    """Raised when a frozen identity, run-control, or data gate fails."""


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
    contract = repo / "research/definitions/us_top50_quarterly_low_beta_defensive_v1.json"
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
        if value is None or float(value) <= 0:
            raise Blocked(f"invalid_adjusted_close:{symbol}:{day}")
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


def market_beta(stock_returns: list[float], market_returns: list[float]) -> float | None:
    if len(stock_returns) < 220 or len(stock_returns) != len(market_returns):
        return None
    count = len(market_returns)
    market_mean = sum(market_returns) / count
    stock_mean = sum(stock_returns) / count
    denominator = sum((value - market_mean) ** 2 for value in market_returns)
    if denominator <= 0:
        return None
    beta = sum(
        (market - market_mean) * (stock - stock_mean)
        for market, stock in zip(market_returns, stock_returns)
    ) / denominator
    return beta if math.isfinite(beta) else None


def is_quarter_end(index: int, calendar: list[date]) -> bool:
    day = calendar[index]
    return (
        day.month in FORMATION_MONTHS
        and index + 1 < len(calendar)
        and calendar[index + 1].month != day.month
    )


def select_holdings(betas: dict[str, float], prior_holdings: list[str]) -> list[str]:
    ranked = sorted(betas, key=lambda symbol: (betas[symbol], symbol))
    ranks = {symbol: rank for rank, symbol in enumerate(ranked, 1)}
    retained = [symbol for symbol in prior_holdings if ranks.get(symbol, 999) <= 20]
    return (retained + [symbol for symbol in ranked if symbol not in retained])[:15]


def build_schedules(
    calendar: list[date],
    prices: dict[str, dict[date, float]],
    symbols: list[str],
) -> tuple[
    dict[date, dict[str, float]],
    dict[date, dict[str, float]],
    dict[date, dict[str, float]],
    list[dict[str, Any]],
]:
    strategy: dict[date, dict[str, float]] = {}
    eligible_equal_weight: dict[date, dict[str, float]] = {}
    spy: dict[date, dict[str, float]] = {}
    held: list[str] = []
    coverage: list[dict[str, Any]] = []
    for index, formation in enumerate(calendar[:-1]):
        if formation < EVALUATION_START or not is_quarter_end(index, calendar):
            continue
        if index < 252:
            continue
        execution = calendar[index + 1]
        betas: dict[str, float] = {}
        for symbol in symbols:
            stock_returns, market_returns = paired_returns(
                symbol,
                index - 251,
                index + 1,
                calendar,
                prices,
            )
            beta = market_beta(stock_returns, market_returns)
            if beta is not None and execution in prices[symbol]:
                betas[symbol] = beta
        if len(betas) < 30:
            raise Blocked(f"eligible_below_30:{formation}:{len(betas)}")
        ranked = sorted(betas, key=lambda symbol: (betas[symbol], symbol))
        held = select_holdings(betas, held)
        strategy[execution] = {symbol: 1 / 15 for symbol in held}
        eligible_equal_weight[execution] = {
            symbol: 1 / len(ranked) for symbol in ranked
        }
        if not spy:
            spy[execution] = {"SPY": 1.0}
        coverage.append(
            {
                "formation": str(formation),
                "execution": str(execution),
                "eligible": len(ranked),
            }
        )
    if len(coverage) < 30:
        raise Blocked(f"complete_formations_below_30:{len(coverage)}")
    return strategy, eligible_equal_weight, spy, coverage


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
    first_execution = min(schedule)
    for prior, current in zip(calendar, calendar[1:]):
        if current < first_execution:
            continue
        gross_return = 0.0
        if started:
            missing = [
                symbol
                for symbol in weights
                if prior not in prices[symbol] or current not in prices[symbol]
            ]
            if missing:
                raise Blocked(f"held_price_missing:{current}:{','.join(sorted(missing))}")
            gross_return = sum(
                weight * (prices[symbol][current] / prices[symbol][prior] - 1)
                for symbol, weight in weights.items()
            )
            value *= 1 + gross_return
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
            returns.append((1 + gross_return) * (1 - trade_cost) - 1)
    years = (dates[-1] - dates[0]).days / 365.25
    return {
        "dates": dates,
        "equity": equity,
        "returns": returns,
        "annual_turnover": turnover / years,
    }


def period_metrics(
    dates: list[date],
    equity: list[float],
    returns: list[float],
) -> dict[str, float]:
    if len(dates) < 2 or len(returns) < 2:
        raise Blocked("insufficient_metric_observations")
    years = (dates[-1] - dates[0]).days / 365.25
    mean = sum(returns) / len(returns)
    variance = sum((value - mean) ** 2 for value in returns) / (len(returns) - 1)
    if variance <= 0 or years <= 0:
        raise Blocked("degenerate_metric_window")
    peak, max_drawdown = equity[0], 0.0
    for value in equity:
        peak = max(peak, value)
        max_drawdown = min(max_drawdown, value / peak - 1)
    return {
        "cagr": (equity[-1] / equity[0]) ** (1 / years) - 1,
        "volatility": math.sqrt(variance) * math.sqrt(252),
        "sharpe": mean / math.sqrt(variance) * math.sqrt(252),
        "max_drawdown": max_drawdown,
    }


def metrics(output: dict[str, Any]) -> dict[str, float]:
    return period_metrics(output["dates"], output["equity"], output["returns"])


def subperiod_sharpe_gates(
    strategy: dict[str, Any],
    spy: dict[str, Any],
) -> dict[str, bool]:
    periods = (
        ("2018-2019", date(2018, 1, 1), date(2019, 12, 31)),
        ("2020-2022", date(2020, 1, 1), date(2022, 12, 31)),
        ("2023-latest", date(2023, 1, 1), date.max),
    )
    results: dict[str, bool] = {}
    for label, start, end in periods:
        strategy_indices = [
            index for index, day in enumerate(strategy["dates"]) if start <= day <= end
        ]
        spy_indices = [index for index, day in enumerate(spy["dates"]) if start <= day <= end]
        if len(strategy_indices) < 2 or len(spy_indices) < 2:
            raise Blocked(f"empty_subperiod:{label}")
        strategy_metrics = period_metrics(
            [strategy["dates"][index] for index in strategy_indices],
            [strategy["equity"][index] for index in strategy_indices],
            [strategy["returns"][index] for index in strategy_indices],
        )
        spy_metrics = period_metrics(
            [spy["dates"][index] for index in spy_indices],
            [spy["equity"][index] for index in spy_indices],
            [spy["returns"][index] for index in spy_indices],
        )
        results[label] = strategy_metrics["sharpe"] >= spy_metrics["sharpe"]
    return results


def formal_run(repo: Path, database: Path, identity: Path, staging: Path) -> dict[str, Any]:
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
            "contract_sha256": CONTRACT_SHA256,
            "database_sha256": DATABASE_SHA256,
            "qualified_identity_sha256": IDENTITY_SHA256,
            "formal_run_number": 1,
        },
    )
    calendar, prices = load_prices(database, symbols)
    strategy_schedule, eligible_schedule, spy_schedule, coverage = build_schedules(
        calendar, prices, symbols
    )
    outputs: dict[str, Any] = {}
    for label, schedule in (
        ("strategy", strategy_schedule),
        ("eligible_equal_weight", eligible_schedule),
        ("spy", spy_schedule),
    ):
        for cost_label, cost in (("base", 0.0015), ("stress", 0.0030)):
            output = simulate(calendar, prices, schedule, cost)
            outputs[f"{label}_{cost_label}"] = {**output, "metrics": metrics(output)}
    strategy = outputs["strategy_base"]
    eligible = outputs["eligible_equal_weight_base"]
    spy = outputs["spy_base"]
    strategy_metrics = strategy["metrics"]
    eligible_metrics = eligible["metrics"]
    spy_metrics = spy["metrics"]
    subperiods = subperiod_sharpe_gates(strategy, spy)
    gates = {
        "base_sharpe_vs_spy": strategy_metrics["sharpe"] >= spy_metrics["sharpe"] + 0.05,
        "base_sharpe_vs_eligible_equal_weight": strategy_metrics["sharpe"] >= eligible_metrics["sharpe"],
        "base_drawdown_vs_spy": strategy_metrics["max_drawdown"] >= spy_metrics["max_drawdown"] + 0.03,
        "base_cagr_vs_spy": strategy_metrics["cagr"] >= spy_metrics["cagr"] - 0.02,
        "stress_cagr_vs_spy": outputs["strategy_stress"]["metrics"]["cagr"] >= outputs["spy_stress"]["metrics"]["cagr"] - 0.02,
        "annual_turnover": strategy["annual_turnover"] <= 1.0,
        "subperiod_sharpe": sum(subperiods.values()) >= 2,
        "eligible_stocks": min(row["eligible"] for row in coverage) >= 30,
        "complete_formations": len(coverage) >= 30,
    }
    passed = all(gates.values())
    result = {
        "research_id": RESEARCH_ID,
        "market": "US_EQUITIES",
        "phase": "DISCOVERY_EXECUTION_AND_ADJUDICATION",
        "status": "current" if passed else "rejected",
        "result": "DISCOVERY_PASS" if passed else "DISCOVERY_FAIL",
        "formal_run_count": 1,
        "strategy_candidate_available": False,
        "survivorship_bias": True,
        "input": {
            "database_sha256": DATABASE_SHA256,
            "qualified_identity_sha256": IDENTITY_SHA256,
            "stock_count": len(symbols),
        },
        "evaluation": [str(strategy["dates"][0]), str(strategy["dates"][-1])],
        "formation_count": len(coverage),
        "eligible_min": min(row["eligible"] for row in coverage),
        "eligible_max": max(row["eligible"] for row in coverage),
        "strategy_base": strategy_metrics,
        "eligible_equal_weight_base": eligible_metrics,
        "spy_base": spy_metrics,
        "strategy_stress": outputs["strategy_stress"]["metrics"],
        "spy_stress": outputs["spy_stress"]["metrics"],
        "annual_turnover": strategy["annual_turnover"],
        "subperiod_sharpe_at_least_spy": subperiods,
        "gates": gates,
        "gate_pass_count": sum(gates.values()),
        "gate_total_count": len(gates),
        "failed_gates": [name for name, gate_passed in gates.items() if not gate_passed],
        "current_holdings_output": False,
        "pit_validation_status": "AUTHORIZED_TO_PREREGISTER_NOT_STARTED" if passed else "NOT_STARTED_DISCOVERY_FAIL",
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
