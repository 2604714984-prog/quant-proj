"""Qualify and run one QQQ-core PIT residual-momentum tilt discovery."""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from datetime import UTC, date, datetime, time
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any
from zoneinfo import ZoneInfo

import duckdb
import numpy as np


RESEARCH_ID = "US_QQQ_CORE_PIT_RESIDUAL_TILT_V1"
HOLDINGS_SNAPSHOT = "qqq_nport_pit_20260723_a10cf2fcdafa4dd8"
MAPPING_SNAPSHOT = "qqq_identity_complete_20260723_767fbc6dbfa92cb9"
PRICE_SNAPSHOT = (
    "US_QQQ_DISCLOSED_TOP50_EQUAL_WEIGHT_V1_YAHOO_SINA_CACHE_20260723"
)
BASE_COST = 0.0015
STRESS_COST = 0.0030
QQQ_ENTRY_COST = 0.0002
MINIMUM_ELIGIBLE = 30
MINIMUM_FORMATIONS = 12
BOOTSTRAP_SEED = 20260724
BOOTSTRAP_REPLICATIONS = 10_000
BOOTSTRAP_BLOCK = 3


class Blocked(RuntimeError):
    """A frozen input or execution boundary failed."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def load_inputs(
    database: Path,
) -> tuple[
    list[dict[str, Any]],
    list[date],
    dict[str, dict[date, float]],
    dict[str, Any],
]:
    digest = hashlib.sha256()
    with duckdb.connect(str(database), read_only=True) as connection:
        holding_rows = connection.execute(
            """
            SELECT h.report_date,h.accepted_at,h.cusip,m.symbol,h.security_rank,
                   h.row_sha256,m.row_sha256
            FROM us_equity_research.qqq_holdings_pit_research h
            JOIN us_equity_research.qqq_security_mapping_research m USING(cusip)
            WHERE h.snapshot_id=? AND h.is_top50 AND m.snapshot_id=?
            ORDER BY h.report_date,h.security_rank,h.cusip
            """,
            [HOLDINGS_SNAPSHOT, MAPPING_SNAPSHOT],
        ).fetchall()
        price_rows = connection.execute(
            """
            SELECT symbol,trade_date,adj_close,row_sha256
            FROM us_equity_research.us_daily_total_return_research
            WHERE snapshot_id=?
            ORDER BY symbol,trade_date
            """,
            [PRICE_SNAPSHOT],
        ).fetchall()
    holdings: list[dict[str, Any]] = []
    for report, accepted, cusip, symbol, rank, holding_hash, mapping_hash in holding_rows:
        row = {
            "report_date": report,
            "accepted_at": accepted,
            "cusip": cusip,
            "symbol": symbol,
            "security_rank": rank,
        }
        holdings.append(row)
        digest.update(
            f"H|{report}|{accepted.isoformat()}|{cusip}|{symbol}|{rank}|"
            f"{holding_hash}|{mapping_hash}\n".encode()
        )
    exact_prices: defaultdict[str, dict[date, float]] = defaultdict(dict)
    for symbol, day, adjusted_close, row_hash in price_rows:
        if day in exact_prices[symbol]:
            raise Blocked("duplicate_symbol_date")
        exact_prices[symbol][day] = float(adjusted_close)
        digest.update(
            f"P|{symbol}|{day}|{float(adjusted_close):.12g}|{row_hash}\n".encode()
        )
    if len(holdings) != 1350:
        raise Blocked(f"holding_rows_not_1350:{len(holdings)}")
    reports = {row["report_date"] for row in holdings}
    if len(reports) != 27:
        raise Blocked(f"reports_not_27:{len(reports)}")
    if "QQQ" not in exact_prices:
        raise Blocked("qqq_price_missing")
    calendar = sorted(exact_prices["QQQ"])
    identity = {
        "input_identity_sha256": digest.hexdigest(),
        "holding_rows": len(holdings),
        "report_count": len(reports),
        "mapped_symbol_count": len({row["symbol"] for row in holdings}),
        "price_row_count": len(price_rows),
        "price_symbol_count_including_qqq": len(exact_prices),
        "price_start": calendar[0].isoformat(),
        "price_end": calendar[-1].isoformat(),
    }
    return holdings, calendar, dict(exact_prices), identity


def formation_close(accepted_at: datetime, calendar: list[date]) -> date:
    eastern = ZoneInfo("America/New_York")
    accepted_utc = accepted_at.astimezone(UTC)
    for day in calendar:
        close = datetime.combine(day, time(16), eastern).astimezone(UTC)
        if close > accepted_utc:
            return day
    raise Blocked(f"no_close_after_acceptance:{accepted_at.isoformat()}")


def paired_returns(
    symbol: str,
    start: int,
    stop: int,
    calendar: list[date],
    exact_prices: dict[str, dict[date, float]],
) -> tuple[list[float], list[float]]:
    stock: list[float] = []
    market: list[float] = []
    for index in range(start, stop):
        prior, current = calendar[index - 1], calendar[index]
        if (
            prior not in exact_prices.get(symbol, {})
            or current not in exact_prices.get(symbol, {})
        ):
            continue
        stock.append(exact_prices[symbol][current] / exact_prices[symbol][prior] - 1)
        market.append(exact_prices["QQQ"][current] / exact_prices["QQQ"][prior] - 1)
    return stock, market


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
    market_mean = statistics.mean(estimate_market)
    stock_mean = statistics.mean(estimate_stock)
    denominator = sum((value - market_mean) ** 2 for value in estimate_market)
    if denominator <= 0:
        return None
    beta = sum(
        (market - market_mean) * (stock - stock_mean)
        for market, stock in zip(estimate_market, estimate_stock, strict=True)
    ) / denominator
    alpha = stock_mean - beta * market_mean
    residuals = [
        stock - alpha - beta * market
        for stock, market in zip(signal_stock, signal_market, strict=True)
    ]
    scale = statistics.stdev(residuals)
    if not math.isfinite(scale) or scale <= 0:
        return None
    score = statistics.mean(residuals) / scale * math.sqrt(252)
    return score if math.isfinite(score) else None


def build_contexts(
    holdings: list[dict[str, Any]],
    calendar: list[date],
    exact_prices: dict[str, dict[date, float]],
    *,
    calculate_scores: bool,
) -> list[dict[str, Any]]:
    grouped: defaultdict[date, list[dict[str, Any]]] = defaultdict(list)
    for row in holdings:
        grouped[row["report_date"]].append(row)
    contexts: list[dict[str, Any]] = []
    for report in sorted(grouped):
        group = grouped[report]
        formation = formation_close(group[0]["accepted_at"], calendar)
        index = calendar.index(formation)
        execution = calendar[index + 1] if index + 1 < len(calendar) else None
        scores: dict[str, float] = {}
        eligible = 0
        if index >= 756 and execution is not None:
            for row in group:
                estimate = paired_returns(
                    row["symbol"], index - 756, index - 252, calendar, exact_prices
                )
                signal = paired_returns(
                    row["symbol"], index - 252, index - 20, calendar, exact_prices
                )
                qualifies = (
                    len(estimate[0]) >= 450
                    and len(signal[0]) >= 220
                    and execution in exact_prices.get(row["symbol"], {})
                )
                if qualifies:
                    eligible += 1
                    if calculate_scores:
                        score = residual_score(*estimate, *signal)
                        if score is not None:
                            scores[row["symbol"]] = score
        contexts.append(
            {
                "report_date": report,
                "accepted_at": group[0]["accepted_at"],
                "formation": formation,
                "execution": execution,
                "eligible": eligible,
                "scores": scores,
            }
        )
    return contexts


def qualification(
    repo: Path,
    database: Path,
    result_path: Path,
) -> dict[str, Any]:
    holdings, calendar, exact_prices, identity = load_inputs(database)
    contexts = build_contexts(
        holdings, calendar, exact_prices, calculate_scores=False
    )
    qualified_contexts = [
        context for context in contexts if context["eligible"] >= MINIMUM_ELIGIBLE
    ]
    minimum = min(
        (context["eligible"] for context in qualified_contexts), default=0
    )
    passed = (
        identity["holding_rows"] == 1350
        and identity["report_count"] == 27
        and len(qualified_contexts) >= MINIMUM_FORMATIONS
        and minimum >= MINIMUM_ELIGIBLE
    )
    script_path = Path(__file__).resolve()
    result = {
        "research_id": RESEARCH_ID,
        "phase": "INPUT_QUALIFICATION",
        "current_status": "preregistered-not-executed" if passed else "blocked-on-data",
        "result": "INPUT_QUALIFIED" if passed else "INPUT_BLOCKED",
        "repository": {
            "path": str(repo),
            "script_path": str(script_path),
            "script_sha256": sha256(script_path),
        },
        "snapshots": {
            "holdings": HOLDINGS_SNAPSHOT,
            "mapping": MAPPING_SNAPSHOT,
            "prices": PRICE_SNAPSHOT,
        },
        "identity": identity,
        "coverage": {
            "qualified_formation_count": len(qualified_contexts),
            "minimum_eligible": minimum,
            "first_execution": (
                qualified_contexts[0]["execution"].isoformat()
                if qualified_contexts
                else None
            ),
            "last_execution": (
                qualified_contexts[-1]["execution"].isoformat()
                if qualified_contexts
                else None
            ),
            "per_formation": [
                {
                    "report_date": context["report_date"].isoformat(),
                    "formation": context["formation"].isoformat(),
                    "execution": (
                        context["execution"].isoformat()
                        if context["execution"]
                        else None
                    ),
                    "eligible": context["eligible"],
                }
                for context in contexts
            ],
        },
        "quality_gates": {
            "exactly_1350_pit_positions": identity["holding_rows"] == 1350,
            "exactly_27_reports": identity["report_count"] == 27,
            "at_least_12_qualified_formations": (
                len(qualified_contexts) >= MINIMUM_FORMATIONS
            ),
            "at_least_30_eligible_each": minimum >= MINIMUM_ELIGIBLE,
            "strategy_scores_accessed": False,
            "strategy_returns_accessed": False,
        },
        "research_boundaries": {
            "strategy_candidate_available": False,
            "current_rankings_output": False,
            "paper_broker_live_auto": False,
        },
        "next_action": (
            "Freeze the one-use historical feasibility contract."
            if passed
            else "Stop this research identity."
        ),
    }
    write_json(result_path, result)
    return result


def select_holdings(scores: dict[str, float], prior: list[str]) -> list[str]:
    ranked = sorted(scores, key=lambda symbol: (-scores[symbol], symbol))
    ranks = {symbol: index for index, symbol in enumerate(ranked, 1)}
    retained = [symbol for symbol in prior if ranks.get(symbol, 999) <= 15]
    return (retained + [symbol for symbol in ranked if symbol not in retained])[:10]


def build_schedule(
    contexts: list[dict[str, Any]],
) -> tuple[dict[date, dict[str, float]], list[dict[str, Any]]]:
    schedule: dict[date, dict[str, float]] = {}
    metadata: list[dict[str, Any]] = []
    held: list[str] = []
    for context in contexts:
        scores = context["scores"]
        if len(scores) < MINIMUM_ELIGIBLE:
            continue
        held = select_holdings(scores, held)
        if len(held) != 10 or context["execution"] is None:
            raise Blocked("selection_not_exactly_10")
        schedule[context["execution"]] = {
            "QQQ": 0.90,
            **{symbol: 0.01 for symbol in held},
        }
        metadata.append(
            {
                "formation": context["formation"],
                "execution": context["execution"],
                "eligible": len(scores),
                "scores": scores,
            }
        )
    if len(schedule) < MINIMUM_FORMATIONS:
        raise Blocked(f"qualified_formations_below_12:{len(schedule)}")
    return schedule, metadata


def simulate(
    calendar: list[date],
    exact_prices: dict[str, dict[date, float]],
    schedule: dict[date, dict[str, float]],
    one_way_cost: float,
) -> tuple[list[date], list[float], list[dict[str, Any]]]:
    first = min(schedule)
    dates = [day for day in calendar if day >= first]
    shares: dict[str, float] = {}
    last_prices: dict[str, float] = {}
    cash = 1.0
    nav: list[float] = []
    turnover_rows: list[dict[str, Any]] = []
    for day in dates:
        for symbol in shares:
            observed = exact_prices.get(symbol, {}).get(day)
            if observed is not None:
                last_prices[symbol] = observed
        values = {
            symbol: quantity * last_prices[symbol]
            for symbol, quantity in shares.items()
        }
        pretrade = cash + sum(values.values())
        if day in schedule:
            target = schedule[day]
            current = {
                symbol: value / pretrade for symbol, value in values.items()
            }
            cash_weight = cash / pretrade
            turnover = 0.5 * (
                sum(
                    abs(target.get(symbol, 0.0) - current.get(symbol, 0.0))
                    for symbol in set(target) | set(current)
                )
                + abs(cash_weight)
            )
            post_cost = pretrade * (1.0 - turnover * one_way_cost)
            missing = [
                symbol
                for symbol in target
                if day not in exact_prices.get(symbol, {})
            ]
            if missing:
                raise Blocked(f"missing_execution_prices:{day}:{len(missing)}")
            shares = {
                symbol: post_cost * weight / exact_prices[symbol][day]
                for symbol, weight in target.items()
            }
            last_prices = {
                symbol: exact_prices[symbol][day] for symbol in target
            }
            cash = 0.0
            pretrade = post_cost
            turnover_rows.append(
                {
                    "execution": day,
                    "one_way_turnover": turnover,
                    "cost_fraction": turnover * one_way_cost,
                }
            )
        nav.append(pretrade)
    return dates, nav, turnover_rows


def nav_returns(nav: list[float]) -> list[float]:
    return [nav[0] - 1.0, *[nav[i] / nav[i - 1] - 1.0 for i in range(1, len(nav))]]


def metrics(dates: list[date], nav: list[float]) -> dict[str, float]:
    returns = nav_returns(nav)
    years = ((dates[-1] - dates[0]).days + 1) / 365.25
    volatility = statistics.stdev(returns)
    peak = nav[0]
    maximum_drawdown = 0.0
    for value in nav:
        peak = max(peak, value)
        maximum_drawdown = min(maximum_drawdown, value / peak - 1.0)
    return {
        "total_return": nav[-1] - 1.0,
        "cagr": nav[-1] ** (1.0 / years) - 1.0,
        "daily_sharpe": statistics.mean(returns) / volatility * math.sqrt(252),
        "maximum_drawdown": maximum_drawdown,
        "annualized_volatility": volatility * math.sqrt(252),
        "years": years,
    }


def split_indices(length: int) -> list[tuple[int, int]]:
    quotient, remainder = divmod(length, 3)
    result: list[tuple[int, int]] = []
    start = 0
    for index in range(3):
        size = quotient + (1 if index < remainder else 0)
        result.append((start, start + size))
        start += size
    return result


def subperiods(
    dates: list[date], strategy: list[float], benchmark: list[float]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, (start, stop) in enumerate(split_indices(len(dates)), 1):
        strategy_base = 1.0 if start == 0 else strategy[start - 1]
        benchmark_base = 1.0 if start == 0 else benchmark[start - 1]
        strategy_return = strategy[stop - 1] / strategy_base - 1.0
        benchmark_return = benchmark[stop - 1] / benchmark_base - 1.0
        rows.append(
            {
                "subperiod": number,
                "start": dates[start],
                "end": dates[stop - 1],
                "strategy_return": strategy_return,
                "qqq_return": benchmark_return,
                "excess_return": strategy_return - benchmark_return,
            }
        )
    return rows


def monthly_returns(dates: list[date], nav: list[float]) -> list[float]:
    month_ends: list[float] = []
    current_month: tuple[int, int] | None = None
    for day, value in zip(dates, nav, strict=True):
        month = day.year, day.month
        if current_month != month:
            month_ends.append(value)
            current_month = month
        else:
            month_ends[-1] = value
    return [
        month_ends[index] / month_ends[index - 1] - 1.0
        for index in range(1, len(month_ends))
    ]


def bootstrap(
    dates: list[date], strategy: list[float], benchmark: list[float]
) -> dict[str, float | int]:
    left = monthly_returns(dates, strategy)
    right = monthly_returns(dates, benchmark)
    excess = np.asarray([a - b for a, b in zip(left, right, strict=True)])
    if len(excess) < BOOTSTRAP_BLOCK:
        raise Blocked("insufficient_months_for_bootstrap")
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    starts = np.arange(len(excess))
    samples = np.empty(BOOTSTRAP_REPLICATIONS)
    blocks = math.ceil(len(excess) / BOOTSTRAP_BLOCK)
    offsets = np.arange(BOOTSTRAP_BLOCK)
    for index in range(BOOTSTRAP_REPLICATIONS):
        selected = rng.choice(starts, size=blocks, replace=True)
        draw = excess[(selected[:, None] + offsets) % len(excess)].ravel()[
            : len(excess)
        ]
        samples[index] = draw.mean()
    return {
        "months": len(excess),
        "mean_monthly_excess": float(excess.mean()),
        "lower_95": float(np.quantile(samples, 0.025)),
        "upper_95": float(np.quantile(samples, 0.975)),
        "block_length_months": BOOTSTRAP_BLOCK,
        "replications": BOOTSTRAP_REPLICATIONS,
        "seed": BOOTSTRAP_SEED,
    }


def rank_correlation(scores: dict[str, float], outcomes: dict[str, float]) -> float:
    symbols = sorted(set(scores) & set(outcomes))
    if len(symbols) < 3:
        return float("nan")
    score_order = sorted(symbols, key=lambda symbol: (scores[symbol], symbol))
    outcome_order = sorted(symbols, key=lambda symbol: (outcomes[symbol], symbol))
    score_rank = {symbol: index for index, symbol in enumerate(score_order)}
    outcome_rank = {symbol: index for index, symbol in enumerate(outcome_order)}
    left = [score_rank[symbol] for symbol in symbols]
    right = [outcome_rank[symbol] for symbol in symbols]
    left_mean = statistics.mean(left)
    right_mean = statistics.mean(right)
    numerator = sum(
        (a - left_mean) * (b - right_mean)
        for a, b in zip(left, right, strict=True)
    )
    denominator = math.sqrt(
        sum((a - left_mean) ** 2 for a in left)
        * sum((b - right_mean) ** 2 for b in right)
    )
    return numerator / denominator if denominator else float("nan")


def signal_diagnostics(
    metadata: list[dict[str, Any]],
    calendar: list[date],
    exact_prices: dict[str, dict[date, float]],
) -> dict[str, Any]:
    horizon_ics: dict[str, list[float]] = {"21": [], "63": [], "holding": []}
    quintile_returns: defaultdict[int, list[float]] = defaultdict(list)
    for index, item in enumerate(metadata):
        execution = item["execution"]
        execution_index = calendar.index(execution)
        holding_end = (
            metadata[index + 1]["execution"]
            if index + 1 < len(metadata)
            else calendar[-1]
        )
        endpoints = {
            "21": calendar[min(execution_index + 21, len(calendar) - 1)],
            "63": calendar[min(execution_index + 63, len(calendar) - 1)],
            "holding": holding_end,
        }
        for label, endpoint in endpoints.items():
            outcomes = {
                symbol: exact_prices[symbol][endpoint]
                / exact_prices[symbol][execution]
                - 1.0
                for symbol in item["scores"]
                if execution in exact_prices.get(symbol, {})
                and endpoint in exact_prices.get(symbol, {})
            }
            value = rank_correlation(item["scores"], outcomes)
            if math.isfinite(value):
                horizon_ics[label].append(value)
            if label == "holding" and outcomes:
                ranked = sorted(item["scores"], key=item["scores"].get)
                for position, symbol in enumerate(ranked):
                    if symbol in outcomes:
                        quintile = min(4, position * 5 // len(ranked)) + 1
                        quintile_returns[quintile].append(outcomes[symbol])
    return {
        "rank_ic": {
            label: {
                "observations": len(values),
                "mean": statistics.mean(values) if values else None,
                "median": statistics.median(values) if values else None,
            }
            for label, values in horizon_ics.items()
        },
        "holding_period_quintile_mean_returns": {
            str(quintile): statistics.mean(values)
            for quintile, values in sorted(quintile_returns.items())
        },
        "diagnostic_only_not_strategy_evidence": True,
    }


def write_comparison(
    path: Path,
    dates: list[date],
    base: list[float],
    stress: list[float],
    benchmark: list[float],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["trade_date", "base_nav", "stress_nav", "qqq_nav"])
        writer.writerows(zip(dates, base, stress, benchmark, strict=True))
    temporary.replace(path)


def execute(
    repo: Path,
    database: Path,
    contract_path: Path,
    qualification_path: Path,
    staging: Path,
    result_path: Path,
) -> dict[str, Any]:
    marker = staging / "formal_run_marker.json"
    if marker.exists():
        raise Blocked("formal_run_already_attempted")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract["inputs"]["input_qualification_sha256"] != sha256(
        qualification_path
    ):
        raise Blocked("qualification_hash_changed")
    if contract["inputs"]["script_sha256"] != sha256(Path(__file__).resolve()):
        raise Blocked("script_hash_changed")
    qualification_result = json.loads(qualification_path.read_text(encoding="utf-8"))
    if qualification_result["result"] != "INPUT_QUALIFIED":
        raise Blocked("input_not_qualified")
    holdings, calendar, exact_prices, identity = load_inputs(database)
    if (
        identity["input_identity_sha256"]
        != contract["inputs"]["input_identity_sha256"]
    ):
        raise Blocked("central_input_identity_changed")
    write_json(
        marker,
        {
            "research_id": RESEARCH_ID,
            "started_at": datetime.now(UTC).isoformat(),
            "contract_sha256": sha256(contract_path),
            "maximum_formal_runs": 1,
        },
    )
    contexts = build_contexts(
        holdings, calendar, exact_prices, calculate_scores=True
    )
    schedule, metadata = build_schedule(contexts)
    dates, base_nav, turnover = simulate(
        calendar, exact_prices, schedule, BASE_COST
    )
    _, stress_nav, _ = simulate(calendar, exact_prices, schedule, STRESS_COST)
    qqq_start = exact_prices["QQQ"][dates[0]]
    qqq_nav = [
        exact_prices["QQQ"][day] / qqq_start * (1.0 - QQQ_ENTRY_COST)
        for day in dates
    ]
    base_metrics = metrics(dates, base_nav)
    stress_metrics = metrics(dates, stress_nav)
    qqq_metrics = metrics(dates, qqq_nav)
    period_rows = subperiods(dates, base_nav, qqq_nav)
    bootstrap_result = bootstrap(dates, base_nav, qqq_nav)
    annual_turnover = sum(row["one_way_turnover"] for row in turnover) / float(
        base_metrics["years"]
    )
    gates = {
        "base_cagr_excess_positive": base_metrics["cagr"] > qqq_metrics["cagr"],
        "stress_cagr_excess_positive": (
            stress_metrics["cagr"] > qqq_metrics["cagr"]
        ),
        "daily_sharpe_margin_at_least_0_02": (
            base_metrics["daily_sharpe"] - qqq_metrics["daily_sharpe"] >= 0.02
        ),
        "drawdown_shortfall_at_most_0_02": (
            abs(base_metrics["maximum_drawdown"])
            - abs(qqq_metrics["maximum_drawdown"])
            <= 0.02
        ),
        "annualized_one_way_turnover_at_most_0_50": annual_turnover <= 0.50,
        "at_least_2_of_3_positive_subperiods": (
            sum(row["excess_return"] > 0 for row in period_rows) >= 2
        ),
        "recent_subperiod_nonnegative": period_rows[-1]["excess_return"] >= 0,
    }
    passed = all(gates.values())
    comparison_path = staging / "daily_comparison.csv"
    write_comparison(comparison_path, dates, base_nav, stress_nav, qqq_nav)
    result = {
        "research_id": RESEARCH_ID,
        "phase": "ONE_USE_HISTORICAL_FEASIBILITY",
        "current_status": "closed",
        "result": (
            "HISTORICAL_FEASIBILITY_PASS_FORWARD_REQUIRED"
            if passed
            else "DISCOVERY_FAIL_PERMANENTLY_CLOSED"
        ),
        "formal_run_count": 1,
        "repository": {
            "path": str(repo),
            "contract_path": str(contract_path),
            "contract_sha256": sha256(contract_path),
            "script_path": str(Path(__file__).resolve()),
            "script_sha256": sha256(Path(__file__).resolve()),
        },
        "input_identity_sha256": identity["input_identity_sha256"],
        "period": {
            "start": dates[0],
            "end": dates[-1],
            "formation_count": len(schedule),
            "minimum_eligible": min(item["eligible"] for item in metadata),
        },
        "metrics": {
            "strategy_base_15bps": base_metrics,
            "strategy_stress_30bps": stress_metrics,
            "qqq_2bps_entry": qqq_metrics,
            "base_cagr_excess": base_metrics["cagr"] - qqq_metrics["cagr"],
            "stress_cagr_excess": stress_metrics["cagr"] - qqq_metrics["cagr"],
            "daily_sharpe_margin": (
                base_metrics["daily_sharpe"] - qqq_metrics["daily_sharpe"]
            ),
            "drawdown_shortfall": (
                abs(base_metrics["maximum_drawdown"])
                - abs(qqq_metrics["maximum_drawdown"])
            ),
            "annualized_one_way_turnover": annual_turnover,
        },
        "subperiods": period_rows,
        "monthly_excess_bootstrap": bootstrap_result,
        "signal_diagnostics": signal_diagnostics(
            metadata, calendar, exact_prices
        ),
        "acceptance_gates": gates,
        "gate_pass_count": sum(gates.values()),
        "gate_total_count": len(gates),
        "all_gates_passed": passed,
        "artifacts": {
            "formal_run_marker": str(marker),
            "daily_comparison": {
                "path": str(comparison_path),
                "sha256": sha256(comparison_path),
            },
        },
        "limitations": [
            "Historical feasibility is not prospective strategy evidence.",
            "The signal family was previously studied on a different survivorship-biased universe; no prior alpha is recycled.",
            "ATVI and WBA local cache closes lack inferred dividend adjustment.",
        ],
        "research_boundaries": {
            "strategy_candidate_available": False,
            "current_rankings_output": False,
            "paper": False,
            "broker": False,
            "live": False,
            "auto": False,
        },
        "next_action": (
            "Freeze a separate twelve-month forward research protocol."
            if passed
            else "Close this identity without variants or repairs."
        ),
    }
    write_json(result_path, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "phase", choices=("qualify", "execute"), help="One phase per invocation."
    )
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("/home/rongyu/workspace/quant-data/quant_research.duckdb"),
    )
    parser.add_argument(
        "--qualification",
        type=Path,
        default=Path(
            "research/results/"
            "us_qqq_core_pit_residual_tilt_v1_input_qualification_20260723.json"
        ),
    )
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path(
            "research/archive/us_qqq_core_pit_residual_tilt_v1/definitions/"
            "us_qqq_core_pit_residual_tilt_v1.json"
        ),
    )
    parser.add_argument(
        "--staging",
        type=Path,
        default=Path(
            "/home/rongyu/workspace/quant-data/staging/"
            "us_qqq_core_pit_residual_tilt_v1/formal"
        ),
    )
    parser.add_argument(
        "--result",
        type=Path,
        default=Path(
            "research/results/"
            "us_qqq_core_pit_residual_tilt_v1_validation_20260723.json"
        ),
    )
    args = parser.parse_args()
    repo = args.repo.resolve()

    def resolved(path: Path) -> Path:
        return path.resolve() if path.is_absolute() else (repo / path).resolve()

    if args.phase == "qualify":
        result = qualification(repo, args.database.resolve(), resolved(args.qualification))
    else:
        result = execute(
            repo,
            args.database.resolve(),
            resolved(args.contract),
            resolved(args.qualification),
            args.staging.resolve(),
            resolved(args.result),
        )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result["result"] not in {"INPUT_BLOCKED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
