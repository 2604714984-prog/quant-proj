"""One-use PIT low-asset-growth research adapter."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date, datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
from typing import Any

import duckdb


RESEARCH_ID = "US_QQQ_TOP50_PIT_LOW_ASSET_GROWTH_V1"
HOLDINGS = "qqq_nport_pit_20260723_a10cf2fcdafa4dd8"
MAPPING = "qqq_identity_complete_20260723_767fbc6dbfa92cb9"
FUNDAMENTALS = "US_SEC_COMPANYFACTS_PIT_V1_20260724_832d40ee1fc1"
STOCKS = "US_QQQ_DISCLOSED_TOP50_EQUAL_WEIGHT_V1_YAHOO_SINA_CACHE_20260723"
BENCHMARK = "QQQ_TTR_TIINGO_YAHOO_COMPLETION_20260723"
STOCK_QUALITY = "RESEARCH_PRIMARY_YAHOO_NO_REQUIRED_CROSSCHECK"
DISCOVERY_END = date(2024, 12, 31)
EVALUATION_END = date(2026, 7, 22)
SELECT = 15
RETAIN = 25
MINIMUM_ELIGIBLE = 35
MINIMUM_DISCOVERY = 18
BOOTSTRAP_REPS = 10_000
BOOTSTRAP_BLOCK = 3
BOOTSTRAP_SEED = 20_260_724


class ResearchError(RuntimeError):
    """Frozen input or one-use boundary failed."""


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
            default=str,
        )
        + "\n"
    ).encode()


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _hash_rows(rows: list[tuple[Any, ...]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(_canonical(row))
    return digest.hexdigest()


def _atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(_canonical(value))
    temporary.replace(path)


def _load(database: Path) -> dict[str, Any]:
    connection = duckdb.connect(str(database), read_only=True)
    try:
        holdings = connection.execute(
            """
            SELECT h.report_date,h.accepted_at,h.security_rank,h.cusip,m.symbol
            FROM us_equity_research.qqq_holdings_pit_research h
            JOIN us_equity_research.qqq_security_mapping_research m
              ON h.cusip=m.cusip
            WHERE h.snapshot_id=? AND m.snapshot_id=? AND h.is_top50
              AND NOT h.synthetic_data AND NOT m.synthetic_data
            ORDER BY 1,2,3,4,5
            """,
            [HOLDINGS, MAPPING],
        ).fetchall()
        fundamentals = connection.execute(
            """
            SELECT symbol,taxonomy,concept,unit,value,end_date,filed_date,
                   available_at,accession_number,row_sha256
            FROM us_equity_research.us_sec_companyfacts_pit_research
            WHERE snapshot_id=? AND concept='Assets' AND NOT synthetic_data
            ORDER BY 1,2,3,4,6,7,9,10
            """,
            [FUNDAMENTALS],
        ).fetchall()
        stocks = connection.execute(
            """
            SELECT symbol,trade_date,adj_close,row_sha256
            FROM us_equity_research.us_daily_total_return_research
            WHERE snapshot_id=? AND quality_status=? AND NOT synthetic_data
              AND trade_date<=? AND adj_close>0
            ORDER BY 1,2,4
            """,
            [STOCKS, STOCK_QUALITY, EVALUATION_END],
        ).fetchall()
        benchmark = connection.execute(
            """
            SELECT symbol,trade_date,adj_close,source_sha256
            FROM us_equity_research.us_benchmark_total_return_research
            WHERE snapshot_id=? AND symbol='QQQ' AND NOT synthetic_data
              AND trade_date<=? AND adj_close>0
            ORDER BY 1,2,4
            """,
            [BENCHMARK, EVALUATION_END],
        ).fetchall()
    finally:
        connection.close()
    if not holdings or not fundamentals or not stocks or not benchmark:
        raise ResearchError("one or more frozen inputs are empty")
    return {
        "holdings": holdings,
        "fundamentals": fundamentals,
        "stocks": stocks,
        "benchmark": benchmark,
        "hashes": {
            "holdings": _hash_rows(holdings),
            "fundamentals": _hash_rows(fundamentals),
            "stocks": _hash_rows(stocks),
            "benchmark": _hash_rows(benchmark),
        },
    }


def _asset_growth(rows: list[tuple[Any, ...]], execution: date) -> float | None:
    latest: dict[tuple[str, str, str, date], tuple[Any, ...]] = {}
    for row in rows:
        _, taxonomy, concept, unit, value, end, filed, available, accession, _ = row
        if available >= execution or not math.isfinite(value) or value <= 0:
            continue
        key = (taxonomy, concept, unit, end)
        if key not in latest or (filed, accession) > (latest[key][6], latest[key][8]):
            latest[key] = row
    groups: defaultdict[tuple[str, str, str], list[tuple[Any, ...]]] = defaultdict(list)
    for (taxonomy, concept, unit, _), row in latest.items():
        groups[(taxonomy, concept, unit)].append(row)
    candidates: list[tuple[date, str, str, str, float]] = []
    for (taxonomy, concept, unit), observations in groups.items():
        ordered = sorted(observations, key=lambda row: row[5], reverse=True)
        for current in ordered:
            prior = next(
                (row for row in ordered if 300 <= (current[5] - row[5]).days <= 430),
                None,
            )
            if prior is not None:
                candidates.append((current[5], taxonomy, concept, unit, current[4] / prior[4] - 1))
                break
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: (-item[0].toordinal(), *item[1:4]))[0][4]


def _unique_prices(rows: list[tuple[Any, ...]]) -> dict[str, dict[date, float]]:
    result: defaultdict[str, dict[date, float]] = defaultdict(dict)
    for symbol, day, value, _identity in rows:
        prior = result[symbol].get(day)
        if prior is not None and prior != value:
            raise ResearchError(f"conflicting frozen prices for {symbol} {day}")
        result[symbol][day] = value
    return dict(result)


def _formations(inputs: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    qqq = {row[1]: row[2] for row in inputs["benchmark"]}
    calendar = sorted(qqq)
    prices = _unique_prices(inputs["stocks"])
    facts: defaultdict[str, list[tuple[Any, ...]]] = defaultdict(list)
    for row in inputs["fundamentals"]:
        facts[row[0]].append(row)
    events: defaultdict[tuple[date, datetime], set[str]] = defaultdict(set)
    for report_date, accepted_at, _rank, _cusip, symbol in inputs["holdings"]:
        events[(report_date, accepted_at)].add(symbol)
    result: list[dict[str, Any]] = []
    held: set[str] = set()
    for (report_date, accepted_at), symbols in sorted(events.items()):
        execution = next((day for day in calendar if day > accepted_at.date()), None)
        if execution is None or execution > EVALUATION_END:
            continue
        signals = {
            symbol: growth
            for symbol in sorted(symbols)
            if execution in prices.get(symbol, {})
            and (growth := _asset_growth(facts[symbol], execution)) is not None
        }
        ranked = sorted(signals, key=lambda symbol: (signals[symbol], symbol))
        ranks = {symbol: index + 1 for index, symbol in enumerate(ranked)}
        retained = [symbol for symbol in sorted(held) if ranks.get(symbol, RETAIN + 1) <= RETAIN]
        selected = (
            retained
            + [symbol for symbol in ranked if symbol not in retained][: SELECT - len(retained)]
        )
        if len(signals) < MINIMUM_ELIGIBLE or len(selected) != SELECT:
            raise ResearchError(
                f"formation {execution} has {len(signals)} eligible and {len(selected)} selected"
            )
        held = set(selected)
        result.append(
            {
                "report_date": report_date,
                "accepted_at": accepted_at,
                "execution_date": execution,
                "eligible_count": len(signals),
                "signals": signals,
                "selected": selected,
                "selection_sha256": _sha(_canonical(selected)),
            }
        )
    discovery = [row for row in result if row["execution_date"] <= DISCOVERY_END]
    if len(discovery) < MINIMUM_DISCOVERY:
        raise ResearchError(f"only {len(discovery)} discovery formations")
    identity = [
        (
            row["report_date"],
            row["accepted_at"],
            row["execution_date"],
            row["eligible_count"],
            _sha(_canonical(sorted(row["signals"].items()))),
            row["selection_sha256"],
        )
        for row in result
    ]
    return result, {
        "formation_count": len(result),
        "discovery_formation_count": len(discovery),
        "holdout_formation_count": len(result) - len(discovery),
        "minimum_eligible": min(row["eligible_count"] for row in result),
        "maximum_eligible": max(row["eligible_count"] for row in result),
        "formation_input_sha256": _hash_rows(identity),
    }


def qualify(database: Path, definition: Path, script: Path, receipt_path: Path) -> dict[str, Any]:
    inputs = _load(database)
    _formations_list, formation_identity = _formations(inputs)
    receipt = {
        "research_id": RESEARCH_ID,
        "phase": "INPUT_QUALIFICATION",
        "status": "INPUT_QUALIFIED",
        "created_at": datetime.now(timezone.utc),
        "definition_sha256": _sha(definition.read_bytes()),
        "script_sha256": _sha(script.read_bytes()),
        "input_hashes": inputs["hashes"],
        "input_counts": {
            key: len(inputs[key]) for key in ("holdings", "fundamentals", "stocks", "benchmark")
        },
        **formation_identity,
        "strategy_outcomes_accessed": False,
        "strategy_candidate_available": False,
    }
    receipt["receipt_sha256"] = _sha(_canonical(receipt))
    _atomic_json(receipt_path, receipt)
    return receipt


def _returns(nav: list[float]) -> list[float]:
    return [nav[0] - 1, *[nav[index] / nav[index - 1] - 1 for index in range(1, len(nav))]]


def _metrics(nav: list[float], calendar: list[date]) -> dict[str, float]:
    returns = _returns(nav)
    deviation = statistics.stdev(returns)
    years = ((calendar[-1] - calendar[0]).days + 1) / 365.25
    peak = nav[0]
    drawdown = 0.0
    for value in nav:
        peak = max(peak, value)
        drawdown = min(drawdown, value / peak - 1)
    return {
        "total_return": nav[-1] - 1,
        "cagr": nav[-1] ** (1 / years) - 1,
        "daily_sharpe": statistics.mean(returns) / deviation * math.sqrt(252),
        "maximum_drawdown": drawdown,
        "annualized_volatility": deviation * math.sqrt(252),
        "years": years,
    }


def _simulate(
    prices: dict[str, dict[date, float]],
    qqq: dict[date, float],
    formations: list[dict[str, Any]],
    end: date,
    stock_bps: float,
) -> tuple[list[date], list[float], list[float], list[float]]:
    start = formations[0]["execution_date"]
    calendar = [day for day in sorted(qqq) if start <= day <= end]
    events = {row["execution_date"]: row for row in formations}
    shares: dict[str, float] = {}
    last: dict[str, float] = {}
    cash = 1.0
    nav: list[float] = []
    satellite_turnover: list[float] = []
    for day in calendar:
        for symbol in shares:
            if day in (prices.get(symbol, {}) if symbol != "QQQ" else qqq):
                last[symbol] = prices[symbol][day] if symbol != "QQQ" else qqq[day]
        values = {symbol: quantity * last[symbol] for symbol, quantity in shares.items()}
        pretrade = cash + sum(values.values())
        if day in events:
            selected = events[day]["selected"]
            target = {"QQQ": 0.8, **{symbol: 0.2 / SELECT for symbol in selected}}
            current = {symbol: value / pretrade for symbol, value in values.items()}
            qqq_trade = abs(target["QQQ"] - current.get("QQQ", 0.0))
            stock_names = (set(current) | set(target)) - {"QQQ"}
            stock_trade = sum(
                abs(target.get(symbol, 0.0) - current.get(symbol, 0.0)) for symbol in stock_names
            )
            if shares:
                old_stock = {symbol: value for symbol, value in values.items() if symbol != "QQQ"}
                sleeve = sum(old_stock.values())
                satellite_turnover.append(
                    0.5
                    * sum(
                        abs(
                            (1 / SELECT if symbol in selected else 0.0)
                            - old_stock.get(symbol, 0.0) / sleeve
                        )
                        for symbol in set(old_stock) | set(selected)
                    )
                )
            cost = pretrade * (qqq_trade * 0.0002 + stock_trade * stock_bps / 10_000)
            post_cost = pretrade - cost
            shares = {
                symbol: post_cost * weight / (qqq[day] if symbol == "QQQ" else prices[symbol][day])
                for symbol, weight in target.items()
            }
            last = {
                symbol: qqq[day] if symbol == "QQQ" else prices[symbol][day] for symbol in target
            }
            cash = 0.0
            pretrade = post_cost
        nav.append(pretrade)
    qqq_nav = [(1 - 0.0002) * qqq[day] / qqq[start] for day in calendar]
    years = ((calendar[-1] - calendar[0]).days + 1) / 365.25
    annual_turnover = sum(satellite_turnover) / years
    return calendar, nav, qqq_nav, [annual_turnover, *satellite_turnover]


def _subperiods(
    strategy: list[float], qqq: list[float], calendar: list[date]
) -> list[dict[str, Any]]:
    quotient, remainder = divmod(len(calendar), 3)
    result = []
    start = 0
    for number in range(3):
        stop = start + quotient + (1 if number < remainder else 0)
        left = 1.0 if start == 0 else strategy[start - 1]
        right = 1.0 if start == 0 else qqq[start - 1]
        result.append(
            {
                "number": number + 1,
                "start": calendar[start],
                "end": calendar[stop - 1],
                "excess_return": strategy[stop - 1] / left - qqq[stop - 1] / right,
            }
        )
        start = stop
    return result


def _rank(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    result = [0.0] * len(values)
    index = 0
    while index < len(order):
        stop = index + 1
        while stop < len(order) and values[order[stop]] == values[order[index]]:
            stop += 1
        rank = (index + 1 + stop) / 2
        for location in order[index:stop]:
            result[location] = rank
        index = stop
    return result


def _diagnostics(
    formations: list[dict[str, Any]], prices: dict[str, dict[date, float]]
) -> dict[str, Any]:
    ics: list[float] = []
    spreads: list[float] = []
    monotonic = 0
    usable = 0
    for current, following in zip(formations, formations[1:]):
        pairs = [
            (
                growth,
                prices[symbol][following["execution_date"]]
                / prices[symbol][current["execution_date"]]
                - 1,
            )
            for symbol, growth in current["signals"].items()
            if current["execution_date"] in prices.get(symbol, {})
            and following["execution_date"] in prices.get(symbol, {})
        ]
        if len(pairs) < MINIMUM_ELIGIBLE:
            continue
        signal_rank = _rank([-growth for growth, _return in pairs])
        return_rank = _rank([value for _growth, value in pairs])
        ics.append(statistics.correlation(signal_rank, return_rank))
        ordered = sorted(pairs)
        size = len(ordered) // 3
        groups = [
            statistics.mean(value for _growth, value in group)
            for group in (ordered[:size], ordered[size : 2 * size], ordered[2 * size :])
        ]
        monotonic += int(groups[0] > groups[1] > groups[2])
        spreads.append(groups[0] - groups[2])
        usable += 1
    deviation = statistics.stdev(ics) if len(ics) > 1 else 0.0
    return {
        "formation_pairs": usable,
        "mean_rank_ic": statistics.mean(ics) if ics else None,
        "icir": statistics.mean(ics) / deviation if deviation else None,
        "tercile_monotonic_fraction": monotonic / usable if usable else None,
        "mean_low_minus_high_return": statistics.mean(spreads) if spreads else None,
    }


def _monthly(nav: list[float], calendar: list[date]) -> list[float]:
    ends: list[float] = []
    months: list[tuple[int, int]] = []
    for day, value in zip(calendar, nav, strict=True):
        month = (day.year, day.month)
        if not months or month != months[-1]:
            months.append(month)
            ends.append(value)
        else:
            ends[-1] = value
    return [ends[index] / ends[index - 1] - 1 for index in range(1, len(ends))]


def _bootstrap(strategy: list[float], qqq: list[float], calendar: list[date]) -> dict[str, Any]:
    excess = [
        left - right
        for left, right in zip(_monthly(strategy, calendar), _monthly(qqq, calendar), strict=True)
    ]
    rng = random.Random(BOOTSTRAP_SEED)
    samples: list[float] = []
    blocks = math.ceil(len(excess) / BOOTSTRAP_BLOCK)
    for _ in range(BOOTSTRAP_REPS):
        draw: list[float] = []
        for _block in range(blocks):
            start = rng.randrange(len(excess))
            draw.extend(excess[(start + offset) % len(excess)] for offset in range(BOOTSTRAP_BLOCK))
        samples.append(statistics.mean(draw[: len(excess)]))
    samples.sort()
    return {
        "months": len(excess),
        "mean_monthly_excess": statistics.mean(excess),
        "lower_95": samples[int(0.025 * BOOTSTRAP_REPS)],
        "upper_95": samples[int(0.975 * BOOTSTRAP_REPS) - 1],
        "block_length": BOOTSTRAP_BLOCK,
        "replications": BOOTSTRAP_REPS,
        "seed": BOOTSTRAP_SEED,
    }


def execute(
    phase: str,
    database: Path,
    definition: Path,
    script: Path,
    receipt_path: Path,
    marker_path: Path,
    result_path: Path,
) -> dict[str, Any]:
    receipt = json.loads(receipt_path.read_bytes())
    inputs = _load(database)
    formations, identity = _formations(inputs)
    checks = {
        "definition": _sha(definition.read_bytes()) == receipt["definition_sha256"],
        "script": _sha(script.read_bytes()) == receipt["script_sha256"],
        "inputs": inputs["hashes"] == receipt["input_hashes"],
        "formations": identity["formation_input_sha256"] == receipt["formation_input_sha256"],
    }
    if not all(checks.values()):
        raise ResearchError(f"qualified input identity changed: {checks}")
    prior = json.loads(result_path.read_bytes()) if result_path.exists() else None
    if phase == "discovery":
        if marker_path.exists() or prior is not None:
            raise ResearchError("formal discovery was already attempted")
        selected_formations = [row for row in formations if row["execution_date"] <= DISCOVERY_END]
        end = DISCOVERY_END
    else:
        if prior is None or prior.get("status") != "DISCOVERY_PASS":
            raise ResearchError("holdout cannot open without a discovery pass")
        holdout_marker = marker_path.with_name("holdout_run_marker.json")
        if holdout_marker.exists() or prior.get("holdout") is not None:
            raise ResearchError("formal holdout was already attempted")
        marker_path = holdout_marker
        selected_formations = [row for row in formations if row["execution_date"] > DISCOVERY_END]
        end = EVALUATION_END
    _atomic_json(
        marker_path,
        {
            "research_id": RESEARCH_ID,
            "phase": phase.upper(),
            "started_at": datetime.now(timezone.utc),
            "receipt_sha256": receipt["receipt_sha256"],
        },
    )
    prices = _unique_prices(inputs["stocks"])
    qqq = {row[1]: row[2] for row in inputs["benchmark"]}
    calendar, base, qqq_nav, turnover = _simulate(prices, qqq, selected_formations, end, 15)
    _calendar, stress, _qqq, _stress_turnover = _simulate(prices, qqq, selected_formations, end, 30)
    base_metrics = _metrics(base, calendar)
    stress_metrics = _metrics(stress, calendar)
    qqq_metrics = _metrics(qqq_nav, calendar)
    drawdown_shortfall = max(
        0.0,
        abs(base_metrics["maximum_drawdown"]) - abs(qqq_metrics["maximum_drawdown"]),
    )
    if phase == "discovery":
        subperiods = _subperiods(base, qqq_nav, calendar)
        gates = {
            "base_net_cagr_excess_gt_0": base_metrics["cagr"] - qqq_metrics["cagr"] > 0,
            "stress_net_cagr_excess_gt_0": stress_metrics["cagr"] - qqq_metrics["cagr"] > 0,
            "daily_sharpe_margin_gte_0_03": base_metrics["daily_sharpe"]
            - qqq_metrics["daily_sharpe"]
            >= 0.03,
            "drawdown_shortfall_lte_0_02": drawdown_shortfall <= 0.02,
            "satellite_annual_turnover_lte_0_50": turnover[0] <= 0.50,
            "positive_subperiods_gte_2": sum(row["excess_return"] > 0 for row in subperiods) >= 2,
            "recent_subperiod_nonnegative": subperiods[-1]["excess_return"] >= 0,
        }
        result = {
            "research_id": RESEARCH_ID,
            "phase": "DISCOVERY",
            "status": "DISCOVERY_PASS" if all(gates.values()) else "REJECTED",
            "current_status": "current" if all(gates.values()) else "rejected",
            "input_identity": {**receipt, "qualification_checks": checks},
            "formation_count": len(selected_formations),
            "evaluation": {"start": calendar[0], "end": calendar[-1]},
            "base": base_metrics,
            "stress": stress_metrics,
            "qqq": qqq_metrics,
            "base_cagr_excess": base_metrics["cagr"] - qqq_metrics["cagr"],
            "stress_cagr_excess": stress_metrics["cagr"] - qqq_metrics["cagr"],
            "daily_sharpe_margin": base_metrics["daily_sharpe"] - qqq_metrics["daily_sharpe"],
            "drawdown_shortfall": drawdown_shortfall,
            "satellite_annual_one_way_turnover": turnover[0],
            "subperiods": subperiods,
            "diagnostics": _diagnostics(selected_formations, prices),
            "bootstrap": _bootstrap(base, qqq_nav, calendar),
            "gates": gates,
            "gate_pass_count": sum(gates.values()),
            "gate_total": len(gates),
            "holdout_opened": False,
            "strategy_candidate_available": False,
            "boundaries": {
                "recommendation": False,
                "paper": False,
                "broker": False,
                "live": False,
                "auto": False,
            },
        }
    else:
        gates = {
            "cumulative_net_excess_gt_0": base_metrics["total_return"] - qqq_metrics["total_return"]
            > 0,
            "daily_sharpe_margin_gte_0": base_metrics["daily_sharpe"] - qqq_metrics["daily_sharpe"]
            >= 0,
            "drawdown_shortfall_lte_0_02": drawdown_shortfall <= 0.02,
            "satellite_annual_turnover_lte_0_50": turnover[0] <= 0.50,
        }
        result = prior
        result["holdout_opened"] = True
        result["holdout"] = {
            "status": "HISTORICAL_RESEARCH_PASS_EXTERNAL_REVIEW_REQUIRED"
            if all(gates.values())
            else "REJECTED",
            "formation_count": len(selected_formations),
            "evaluation": {"start": calendar[0], "end": calendar[-1]},
            "base": base_metrics,
            "stress": stress_metrics,
            "qqq": qqq_metrics,
            "cumulative_net_excess": base_metrics["total_return"] - qqq_metrics["total_return"],
            "daily_sharpe_margin": base_metrics["daily_sharpe"] - qqq_metrics["daily_sharpe"],
            "drawdown_shortfall": drawdown_shortfall,
            "satellite_annual_one_way_turnover": turnover[0],
            "diagnostics": _diagnostics(selected_formations, prices),
            "bootstrap": _bootstrap(base, qqq_nav, calendar),
            "gates": gates,
            "gate_pass_count": sum(gates.values()),
            "gate_total": len(gates),
        }
        result["status"] = result["holdout"]["status"]
        result["current_status"] = "current" if all(gates.values()) else "rejected"
    _atomic_json(result_path, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("qualify", "discovery", "holdout"))
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--definition", type=Path, required=True)
    parser.add_argument("--staging-root", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    script = Path(__file__).resolve()
    staging = args.staging_root.resolve()
    receipt = staging / "input_receipt.json"
    marker = staging / "formal_run_marker.json"
    try:
        if args.phase == "qualify":
            result = qualify(args.database.resolve(), args.definition.resolve(), script, receipt)
        else:
            result = execute(
                args.phase,
                args.database.resolve(),
                args.definition.resolve(),
                script,
                receipt,
                marker,
                args.result.resolve(),
            )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, default=str))
        return 0
    except ResearchError as error:
        print(
            json.dumps(
                {
                    "research_id": RESEARCH_ID,
                    "status": "INPUT_BLOCKED",
                    "error": str(error),
                    "strategy_candidate_available": False,
                },
                sort_keys=True,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
