"""Run the single frozen historical validation of disclosed QQQ top-50 equal weight."""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from datetime import UTC, date, datetime
import hashlib
import json
from pathlib import Path
import statistics
from typing import Any

import duckdb
import numpy as np

import acquire_us_qqq_top50_prices_v1 as prices
import smoke_us_qqq_disclosed_top50_v1 as smoke


RESEARCH_ID = smoke.RESEARCH_ID
EXECUTION_ID = f"{RESEARCH_ID}_ONE_USE_VALIDATION"
HOLDINGS_SNAPSHOT = prices.HOLDINGS_SNAPSHOT
MAPPING_SNAPSHOT = prices.MAPPING_SNAPSHOT
PRICE_SNAPSHOT = (
    "US_QQQ_DISCLOSED_TOP50_EQUAL_WEIGHT_V1_YAHOO_SINA_CACHE_20260723"
)
STRATEGY_COST = 0.0015
STRESS_COST = 0.0030
QQQ_ENTRY_COST = 0.0002
MINIMUM_POSITIONS = 49
BOOTSTRAP_SEED = 20260723
BOOTSTRAP_REPLICATIONS = 10_000
BOOTSTRAP_BLOCK = 3


class ValidationInputError(RuntimeError):
    """A frozen input or one-use execution boundary failed."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _load_inputs(
    database_path: Path,
) -> tuple[list[dict[str, Any]], dict[str, dict[date, float]]]:
    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        holding_rows = connection.execute(
            """
            SELECT h.report_date,h.accepted_at,h.cusip,m.symbol,h.security_rank
            FROM us_equity_research.qqq_holdings_pit_research h
            JOIN us_equity_research.qqq_security_mapping_research m USING(cusip)
            WHERE h.snapshot_id=? AND h.is_top50 AND m.snapshot_id=?
            ORDER BY h.report_date,h.security_rank
            """,
            [HOLDINGS_SNAPSHOT, MAPPING_SNAPSHOT],
        ).fetchall()
        daily_rows = connection.execute(
            """
            SELECT symbol,trade_date,adj_close
            FROM us_equity_research.us_daily_total_return_research
            WHERE snapshot_id=?
            ORDER BY trade_date,symbol
            """,
            [PRICE_SNAPSHOT],
        ).fetchall()
    finally:
        connection.close()
    holdings = [
        {
            "report_date": row[0],
            "accepted_at": row[1],
            "cusip": row[2],
            "symbol": row[3],
            "security_rank": row[4],
        }
        for row in holding_rows
    ]
    if len(holdings) != 1350 or len({row["report_date"] for row in holdings}) != 27:
        raise ValidationInputError("holdings input is not exactly 27 x 50")
    exact_prices: defaultdict[str, dict[date, float]] = defaultdict(dict)
    for symbol, trade_date, adjusted_close in daily_rows:
        if trade_date in exact_prices[symbol]:
            raise ValidationInputError("duplicate central symbol-date rows")
        exact_prices[symbol][trade_date] = float(adjusted_close)
    if len(exact_prices) != 92 or "QQQ" not in exact_prices:
        raise ValidationInputError("central price snapshot shape changed")
    return holdings, dict(exact_prices)


def _build_formations(
    holdings: list[dict[str, Any]],
    exact_prices: dict[str, dict[date, float]],
    qqq_dates: list[date],
) -> list[dict[str, Any]]:
    grouped: defaultdict[date, list[dict[str, Any]]] = defaultdict(list)
    for row in holdings:
        grouped[row["report_date"]].append(row)
    formations: list[dict[str, Any]] = []
    for report_date in sorted(grouped):
        group = grouped[report_date]
        accepted_at = group[0]["accepted_at"]
        execution_date = prices._formation_close(accepted_at, qqq_dates)
        counts: defaultdict[str, int] = defaultdict(int)
        for row in group:
            if execution_date in exact_prices.get(row["symbol"], {}):
                counts[row["symbol"]] += 1
        priced_positions = sum(counts.values())
        if priced_positions < MINIMUM_POSITIONS:
            raise ValidationInputError(
                f"formation {execution_date} has only {priced_positions} prices"
            )
        formations.append(
            {
                "report_date": report_date.isoformat(),
                "accepted_at": accepted_at.isoformat(),
                "execution_date": execution_date.isoformat(),
                "priced_position_count": priced_positions,
                "target_weights": {
                    symbol: count / priced_positions
                    for symbol, count in sorted(counts.items())
                },
            }
        )
    if len(formations) != 27:
        raise ValidationInputError("formation count changed")
    return formations


def _simulate(
    exact_prices: dict[str, dict[date, float]],
    calendar: list[date],
    formations: list[dict[str, Any]],
    one_way_cost: float,
) -> tuple[list[float], list[dict[str, Any]]]:
    first = date.fromisoformat(formations[0]["execution_date"])
    calendar = [day for day in calendar if day >= first]
    formation_by_day = {
        date.fromisoformat(item["execution_date"]): item for item in formations
    }
    shares: dict[str, float] = {}
    last_prices: dict[str, float] = {}
    cash = 1.0
    nav: list[float] = []
    turnover_rows: list[dict[str, Any]] = []
    for day in calendar:
        for symbol in shares:
            observed = exact_prices[symbol].get(day)
            if observed is not None:
                last_prices[symbol] = observed
        current_values = {
            symbol: quantity * last_prices[symbol]
            for symbol, quantity in shares.items()
        }
        pretrade_nav = cash + sum(current_values.values())
        if day in formation_by_day:
            formation = formation_by_day[day]
            target = formation["target_weights"]
            current_weights = {
                symbol: value / pretrade_nav
                for symbol, value in current_values.items()
            }
            cash_weight = cash / pretrade_nav
            all_symbols = set(current_weights) | set(target)
            turnover = 0.5 * (
                sum(
                    abs(target.get(symbol, 0.0) - current_weights.get(symbol, 0.0))
                    for symbol in all_symbols
                )
                + abs(cash_weight)
            )
            cost = pretrade_nav * turnover * one_way_cost
            post_cost_nav = pretrade_nav - cost
            shares = {
                symbol: post_cost_nav
                * weight
                / exact_prices[symbol][day]
                for symbol, weight in target.items()
            }
            last_prices = {
                symbol: exact_prices[symbol][day] for symbol in target
            }
            cash = 0.0
            pretrade_nav = post_cost_nav
            turnover_rows.append(
                {
                    "execution_date": day.isoformat(),
                    "one_way_turnover": turnover,
                    "cost_fraction_of_pretrade_nav": turnover * one_way_cost,
                    "priced_position_count": formation["priced_position_count"],
                }
            )
        nav.append(pretrade_nav)
    return nav, turnover_rows


def _returns(nav: list[float]) -> list[float]:
    return [nav[0] - 1.0, *[nav[i] / nav[i - 1] - 1.0 for i in range(1, len(nav))]]


def _metrics(nav: list[float], calendar: list[date]) -> dict[str, float]:
    returns = _returns(nav)
    elapsed_days = (calendar[-1] - calendar[0]).days + 1
    years = elapsed_days / 365.25
    volatility = statistics.stdev(returns)
    sharpe = (
        statistics.mean(returns) / volatility * (252**0.5)
        if volatility > 0
        else 0.0
    )
    peak = nav[0]
    maximum_drawdown = 0.0
    for value in nav:
        peak = max(peak, value)
        maximum_drawdown = min(maximum_drawdown, value / peak - 1.0)
    return {
        "total_return": nav[-1] - 1.0,
        "cagr": nav[-1] ** (1.0 / years) - 1.0,
        "daily_sharpe": sharpe,
        "maximum_drawdown": maximum_drawdown,
        "annualized_volatility": volatility * (252**0.5),
        "years": years,
    }


def _split_indices(length: int, parts: int) -> list[tuple[int, int]]:
    quotient, remainder = divmod(length, parts)
    result: list[tuple[int, int]] = []
    start = 0
    for index in range(parts):
        size = quotient + (1 if index < remainder else 0)
        result.append((start, start + size))
        start += size
    return result


def _subperiod_excess(
    strategy_nav: list[float], qqq_nav: list[float], calendar: list[date]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, (start, stop) in enumerate(_split_indices(len(calendar), 3), 1):
        strategy_base = 1.0 if start == 0 else strategy_nav[start - 1]
        qqq_base = 1.0 if start == 0 else qqq_nav[start - 1]
        strategy_return = strategy_nav[stop - 1] / strategy_base - 1.0
        qqq_return = qqq_nav[stop - 1] / qqq_base - 1.0
        rows.append(
            {
                "subperiod": number,
                "start": calendar[start].isoformat(),
                "end": calendar[stop - 1].isoformat(),
                "strategy_return": strategy_return,
                "qqq_return": qqq_return,
                "excess_return": strategy_return - qqq_return,
            }
        )
    return rows


def _monthly_returns(nav: list[float], calendar: list[date]) -> list[float]:
    month_ends: list[float] = []
    current_month: tuple[int, int] | None = None
    for day, value in zip(calendar, nav, strict=True):
        month = (day.year, day.month)
        if current_month is None or month != current_month:
            month_ends.append(value)
            current_month = month
        else:
            month_ends[-1] = value
    return [
        month_ends[index] / month_ends[index - 1] - 1.0
        for index in range(1, len(month_ends))
    ]


def _bootstrap_monthly_excess(
    strategy_nav: list[float], qqq_nav: list[float], calendar: list[date]
) -> dict[str, float | int]:
    strategy = _monthly_returns(strategy_nav, calendar)
    qqq = _monthly_returns(qqq_nav, calendar)
    excess = np.asarray(
        [left - right for left, right in zip(strategy, qqq, strict=True)]
    )
    if len(excess) < BOOTSTRAP_BLOCK:
        raise ValidationInputError("insufficient monthly excess observations")
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    starts = np.arange(len(excess))
    samples = np.empty(BOOTSTRAP_REPLICATIONS)
    blocks_needed = int(np.ceil(len(excess) / BOOTSTRAP_BLOCK))
    offsets = np.arange(BOOTSTRAP_BLOCK)
    for index in range(BOOTSTRAP_REPLICATIONS):
        chosen = rng.choice(starts, size=blocks_needed, replace=True)
        draw = excess[(chosen[:, None] + offsets) % len(excess)].ravel()[
            : len(excess)
        ]
        samples[index] = draw.mean()
    return {
        "month_count": len(excess),
        "mean_monthly_excess": float(excess.mean()),
        "lower_95": float(np.quantile(samples, 0.025)),
        "upper_95": float(np.quantile(samples, 0.975)),
        "block_length_months": BOOTSTRAP_BLOCK,
        "replications": BOOTSTRAP_REPLICATIONS,
        "seed": BOOTSTRAP_SEED,
    }


def _write_comparison(
    path: Path,
    calendar: list[date],
    strategy: list[float],
    stress: list[float],
    qqq: list[float],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["trade_date", "strategy_nav", "strategy_stress_nav", "qqq_nav"]
        )
        writer.writerows(zip(calendar, strategy, stress, qqq, strict=True))
    temporary.replace(path)


def run(
    repo_root: Path,
    database_path: Path,
    staging_root: Path,
    result_path: Path,
) -> dict[str, Any]:
    contract_path = (
        repo_root
        / "research/definitions/"
        "us_qqq_disclosed_top50_equal_weight_v1_validation.json"
    )
    marker_path = staging_root / "formal_validation_run_marker.json"
    if marker_path.exists():
        raise ValidationInputError("formal validation was already attempted")
    holdings, exact_prices = _load_inputs(database_path)
    qqq_dates = sorted(exact_prices["QQQ"])
    formations = _build_formations(holdings, exact_prices, qqq_dates)
    _atomic_json(
        marker_path,
        {
            "execution_id": EXECUTION_ID,
            "started_at": datetime.now(UTC).isoformat(),
            "contract_sha256": _sha256(contract_path),
            "maximum_formal_runs": 1,
        },
    )
    first = date.fromisoformat(formations[0]["execution_date"])
    calendar = [day for day in qqq_dates if day >= first]
    strategy_nav, turnover = _simulate(
        exact_prices, calendar, formations, STRATEGY_COST
    )
    stress_nav, _ = _simulate(
        exact_prices, calendar, formations, STRESS_COST
    )
    qqq_start = exact_prices["QQQ"][calendar[0]]
    qqq_nav = [
        exact_prices["QQQ"][day] / qqq_start * (1.0 - QQQ_ENTRY_COST)
        for day in calendar
    ]
    strategy_metrics = _metrics(strategy_nav, calendar)
    stress_metrics = _metrics(stress_nav, calendar)
    qqq_metrics = _metrics(qqq_nav, calendar)
    subperiods = _subperiod_excess(strategy_nav, qqq_nav, calendar)
    bootstrap = _bootstrap_monthly_excess(strategy_nav, qqq_nav, calendar)
    annualized_turnover = sum(row["one_way_turnover"] for row in turnover) / float(
        strategy_metrics["years"]
    )
    gate_values = {
        "net_cagr_excess_gt_2pp": (
            strategy_metrics["cagr"] - qqq_metrics["cagr"] > 0.02
        ),
        "daily_sharpe_margin_gte_0_10": (
            strategy_metrics["daily_sharpe"] - qqq_metrics["daily_sharpe"] >= 0.10
        ),
        "maximum_drawdown_shortfall_lte_5pp": (
            abs(strategy_metrics["maximum_drawdown"])
            - abs(qqq_metrics["maximum_drawdown"])
            <= 0.05
        ),
        "at_least_2_of_3_positive_subperiods": (
            sum(row["excess_return"] > 0 for row in subperiods) >= 2
        ),
        "recent_subperiod_positive": subperiods[-1]["excess_return"] > 0,
        "annualized_one_way_turnover_lte_50pct": annualized_turnover <= 0.50,
        "monthly_excess_bootstrap_lower_95_gt_0": bootstrap["lower_95"] > 0.0,
    }
    passed = all(gate_values.values())
    comparison_path = staging_root / "daily_comparison.csv"
    _write_comparison(
        comparison_path, calendar, strategy_nav, stress_nav, qqq_nav
    )
    result = {
        "research_id": RESEARCH_ID,
        "execution_id": EXECUTION_ID,
        "phase": "ONE_USE_HISTORICAL_VALIDATION",
        "current_status": "closed",
        "result": (
            "HISTORICAL_GATED_PASS_EXTERNAL_REVIEW_REQUIRED"
            if passed
            else "REJECTED_NOT_WORTH_COMPLEXITY_VS_QQQ"
        ),
        "formal_run_count": 1,
        "contract": {
            "path": str(contract_path),
            "sha256": _sha256(contract_path),
        },
        "input_snapshots": {
            "holdings": HOLDINGS_SNAPSHOT,
            "mapping": MAPPING_SNAPSHOT,
            "prices": PRICE_SNAPSHOT,
        },
        "period": {
            "start": calendar[0].isoformat(),
            "end": calendar[-1].isoformat(),
            "formation_count": len(formations),
            "minimum_priced_positions": min(
                item["priced_position_count"] for item in formations
            ),
        },
        "metrics": {
            "strategy_net_15bps": strategy_metrics,
            "strategy_stress_30bps": stress_metrics,
            "qqq_2bps_entry": qqq_metrics,
            "net_cagr_excess": strategy_metrics["cagr"] - qqq_metrics["cagr"],
            "daily_sharpe_margin": (
                strategy_metrics["daily_sharpe"] - qqq_metrics["daily_sharpe"]
            ),
            "maximum_drawdown_shortfall": (
                abs(strategy_metrics["maximum_drawdown"])
                - abs(qqq_metrics["maximum_drawdown"])
            ),
            "annualized_one_way_turnover": annualized_turnover,
        },
        "subperiods": subperiods,
        "monthly_excess_bootstrap": bootstrap,
        "acceptance_gates": gate_values,
        "all_gates_passed": passed,
        "artifacts": {
            "run_marker": str(marker_path),
            "daily_comparison": {
                "path": str(comparison_path),
                "sha256": _sha256(comparison_path),
            },
        },
        "limitations": [
            "This is one retrospective historical comparison, not a live result.",
            "ATVI and WBA local Sina cache closes lack inferred dividend adjustment.",
            "CELG was excluded at the first formation because no valid price existed.",
        ],
        "research_boundaries": {
            "strategy_candidate_available": False,
            "current_stock_rankings_output": False,
            "paper_trading": False,
            "broker": False,
            "live": False,
            "automatic_execution": False,
        },
        "next_action": (
            "Independent read-only review; do not activate."
            if passed
            else "Close this identity; prefer QQQ over added strategy complexity."
        ),
    }
    _atomic_json(result_path, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("/home/rongyu/workspace/quant-data/quant_research.duckdb"),
    )
    parser.add_argument(
        "--staging-root",
        type=Path,
        default=Path(
            "/home/rongyu/workspace/quant-data/staging/"
            "us_qqq_disclosed_top50_equal_weight_v1/formal_validation"
        ),
    )
    parser.add_argument(
        "--result",
        type=Path,
        default=Path(
            "research/results/"
            "us_qqq_disclosed_top50_equal_weight_v1_validation_20260723.json"
        ),
    )
    args = parser.parse_args()
    result_path = (
        (args.repo_root.resolve() / args.result).resolve()
        if not args.result.is_absolute()
        else args.result.resolve()
    )
    result = run(
        args.repo_root.resolve(),
        args.database.resolve(),
        args.staging_root.resolve(),
        result_path,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["result"] != "INPUT_BLOCKED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
