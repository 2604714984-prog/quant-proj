"""One-use QQQ complexity kill test for the frozen gross-profitability strategy."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import random
import statistics
import urllib.parse
import urllib.request
from pathlib import Path

import duckdb

from research import us_top50_gross_profitability as strategy

AUDIT_ID = "US_TOP50_GP_V2_VS_QQQ_AUDIT_V1"
BENCHMARK_SNAPSHOT = "QQQ_TTR_TIINGO_YAHOO_COMPLETION_20260723"
BENCHMARK_TABLE = "us_equity_research.us_benchmark_total_return_research"
TIINGO_SNAPSHOT = "tiingo_raw_20260711T142010Z_5c24877d23cfc4a0"
START = dt.date(2018, 4, 2)
END = dt.date(2026, 7, 22)
TIINGO_END = dt.date(2026, 7, 10)
UA = "Mozilla/5.0 (compatible; lightweight-personal-quant-research/1.0)"


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def fetch_yahoo(raw_path: Path) -> tuple[dict[dt.date, float], str, str]:
    params = {
        "period1": int(dt.datetime(2026, 6, 1, tzinfo=dt.timezone.utc).timestamp()),
        "period2": int(dt.datetime(2026, 7, 23, tzinfo=dt.timezone.utc).timestamp()),
        "interval": "1d",
        "events": "div,splits",
        "includeAdjustedClose": "true",
    }
    errors: list[str] = []
    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        url = f"https://{host}/v8/finance/chart/QQQ?" + urllib.parse.urlencode(params)
        try:
            request = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(request, timeout=20) as response:
                raw = response.read()
            document = json.loads(raw)
            result = document["chart"]["result"][0]
            timestamps = result["timestamp"]
            adjusted = result["indicators"]["adjclose"][0]["adjclose"]
            rows = {
                dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc).date(): float(price)
                for timestamp, price in zip(timestamps, adjusted)
                if price is not None
            }
            temporary = raw_path.with_suffix(".json.part")
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_bytes(raw)
            os.replace(temporary, raw_path)
            return rows, hashlib.sha256(raw).hexdigest(), url
        except Exception as error:  # pragma: no cover - provider dependent
            errors.append(f"{host}: {error}")
    raise RuntimeError("; ".join(errors))


def load_tiingo(database: Path) -> dict[dt.date, float]:
    connection = duckdb.connect(str(database), read_only=True)
    try:
        rows = connection.execute(
            f"""
            SELECT trade_date, adj_close
            FROM {strategy.PRICE_TABLE}
            WHERE snapshot_id=? AND symbol='QQQ'
              AND trade_date BETWEEN ? AND ? AND adj_close>0
            ORDER BY trade_date
            """,
            [TIINGO_SNAPSHOT, START, TIINGO_END],
        ).fetchall()
    finally:
        connection.close()
    return {date: price for date, price in rows}


def overlap_return_error(
    left: dict[dt.date, float], right: dict[dt.date, float], observations: int = 20
) -> tuple[float, int]:
    common = sorted(set(left) & set(right))
    pairs = list(zip(common[-(observations + 1) : -1], common[-observations:]))
    errors = [
        abs((left[end] / left[start] - 1) - (right[end] / right[start] - 1))
        for start, end in pairs
    ]
    return (max(errors) if errors else math.inf), len(errors)


def spy_sessions(price_database: Path) -> list[dt.date]:
    return [
        date
        for date in strategy.sessions_from(price_database)
        if START <= date <= END
    ]


def insert_benchmark(
    database: Path,
    rows: list[tuple],
) -> tuple[int, bool]:
    connection = duckdb.connect(str(database))
    try:
        connection.execute("BEGIN")
        connection.execute("CREATE SCHEMA IF NOT EXISTS us_equity_research")
        connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {BENCHMARK_TABLE} (
                snapshot_id VARCHAR NOT NULL,
                symbol VARCHAR NOT NULL,
                trade_date DATE NOT NULL,
                adj_close DOUBLE NOT NULL,
                provider VARCHAR NOT NULL,
                segment VARCHAR NOT NULL,
                source_sha256 VARCHAR NOT NULL,
                source_url VARCHAR NOT NULL,
                synthetic_data BOOLEAN NOT NULL,
                PRIMARY KEY(snapshot_id,symbol,trade_date)
            )
            """
        )
        existing = connection.execute(
            f"SELECT COUNT(*) FROM {BENCHMARK_TABLE} WHERE snapshot_id=?",
            [BENCHMARK_SNAPSHOT],
        ).fetchone()[0]
        if existing and existing != len(rows):
            raise ValueError(f"existing benchmark rows {existing} != expected {len(rows)}")
        if not existing:
            connection.executemany(
                f"INSERT INTO {BENCHMARK_TABLE} VALUES (?,?,?,?,?,?,?,?,?)", rows
            )
        connection.execute("COMMIT")
        return existing or len(rows), not bool(existing)
    except Exception:
        connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()


def materialize(args: argparse.Namespace) -> int:
    tiingo = load_tiingo(args.database)
    yahoo, yahoo_sha, yahoo_url = fetch_yahoo(args.raw)
    max_error, overlap_count = overlap_return_error(tiingo, yahoo)
    if overlap_count < 20 or max_error > 0.005:
        receipt = {
            "research_id": AUDIT_ID,
            "status": "INPUT_BLOCKED",
            "overlap_return_observations": overlap_count,
            "overlap_max_absolute_return_error": max_error,
            "benchmark_outcomes_accessed": True,
            "formal_run_count": 0,
            "strategy_candidate_available": False,
        }
        atomic_json(args.receipt, receipt)
        return 2
    combined = {**tiingo}
    combined.update({date: price for date, price in yahoo.items() if date > TIINGO_END})
    sessions = spy_sessions(args.price_database)
    missing = [date.isoformat() for date in sessions if date not in combined]
    if missing:
        receipt = {
            "research_id": AUDIT_ID,
            "status": "INPUT_BLOCKED",
            "missing_sessions": missing,
            "formal_run_count": 0,
            "strategy_candidate_available": False,
        }
        atomic_json(args.receipt, receipt)
        return 2
    tiingo_sha = strategy.object_sha(sorted(tiingo.items()))
    rows = [
        (
            BENCHMARK_SNAPSHOT,
            "QQQ",
            date.isoformat(),
            combined[date],
            "Tiingo" if date <= TIINGO_END else "Yahoo",
            "history" if date <= TIINGO_END else "completion",
            tiingo_sha if date <= TIINGO_END else yahoo_sha,
            "central://us_daily_total_return_research"
            if date <= TIINGO_END
            else yahoo_url,
            False,
        )
        for date in sessions
    ]
    count, inserted = insert_benchmark(args.database, rows)
    receipt = {
        "research_id": AUDIT_ID,
        "status": "INPUT_QUALIFIED",
        "snapshot_id": BENCHMARK_SNAPSHOT,
        "row_count": count,
        "start": sessions[0].isoformat(),
        "end": sessions[-1].isoformat(),
        "tiingo_rows": sum(date <= TIINGO_END for date in sessions),
        "yahoo_completion_rows": sum(date > TIINGO_END for date in sessions),
        "overlap_return_observations": overlap_count,
        "overlap_max_absolute_return_error": max_error,
        "yahoo_source_sha256": yahoo_sha,
        "central_database_write": inserted,
        "formal_run_count": 0,
        "strategy_candidate_available": False,
    }
    atomic_json(args.receipt, receipt)
    return 0


def load_benchmark(database: Path) -> dict[dt.date, float]:
    connection = duckdb.connect(str(database), read_only=True)
    try:
        rows = connection.execute(
            f"""
            SELECT trade_date,adj_close FROM {BENCHMARK_TABLE}
            WHERE snapshot_id=? ORDER BY trade_date
            """,
            [BENCHMARK_SNAPSHOT],
        ).fetchall()
    finally:
        connection.close()
    return {date: price for date, price in rows}


def build_decisions(
    fundamentals: dict[str, list[dict]],
    symbols: list[str],
    sessions: list[dt.date],
) -> list[dict]:
    retained: set[str] = set()
    decisions: list[dict] = []
    for formation in strategy.formation_dates(sessions):
        scores = {
            symbol: value
            for symbol in symbols
            if (value := strategy.factor_at(fundamentals.get(symbol, []), formation))
            is not None
        }
        execution = strategy.next_session(formation, sessions)
        if len(scores) >= 30 and execution:
            weights = strategy.choose(scores, retained)
            decisions.append({"formation": formation, "execution": execution, "weights": weights})
            retained = set(weights)
    return decisions


def simulate_strategy(
    decisions: list[dict],
    sessions: list[dt.date],
    prices: dict[str, dict[dt.date, float]],
    cost: float,
) -> tuple[list[tuple[dt.date, float]], float]:
    shares: dict[str, float] = {}
    nav_path: list[tuple[dt.date, float]] = []
    turnovers: list[float] = []
    for index, decision in enumerate(decisions):
        start = decision["execution"]
        end = decisions[index + 1]["execution"] if index + 1 < len(decisions) else sessions[-1]
        if shares:
            capital = sum(quantity * prices[symbol][start] for symbol, quantity in shares.items())
            drifted = {
                symbol: quantity * prices[symbol][start] / capital
                for symbol, quantity in shares.items()
            }
        else:
            capital, drifted = 1.0, {}
            nav_path.append((start, capital))
        target = decision["weights"]
        turnover = strategy.one_way_turnover(drifted, target)
        turnovers.append(turnover)
        capital *= 1 - cost * turnover
        shares = {
            symbol: capital * weight / prices[symbol][start]
            for symbol, weight in target.items()
        }
        nav_path.append((start, capital))
        for date in sessions:
            if start < date <= end:
                if any(date not in prices.get(symbol, {}) for symbol in shares):
                    raise ValueError(f"missing strategy price at {date}")
                nav_path.append(
                    (
                        date,
                        sum(
                            quantity * prices[symbol][date]
                            for symbol, quantity in shares.items()
                        ),
                    )
                )
    terminal_capital = nav_path[-1][1] * (1 - cost)
    turnovers.append(1.0)
    nav_path.append((sessions[-1], terminal_capital))
    years = (sessions[-1] - decisions[0]["execution"]).days / 365.25
    return nav_path, sum(turnovers) / years


def simulate_qqq(
    benchmark: dict[dt.date, float], sessions: list[dt.date], cost: float
) -> list[tuple[dt.date, float]]:
    initial = benchmark[sessions[0]]
    nav = [(sessions[0], 1.0)]
    nav.extend((date, (1 - cost) * benchmark[date] / initial) for date in sessions)
    nav.append((sessions[-1], nav[-1][1] * (1 - cost)))
    return nav


def daily_metrics(path: list[tuple[dt.date, float]]) -> dict[str, float]:
    returns = [path[index][1] / path[index - 1][1] - 1 for index in range(1, len(path))]
    years = (path[-1][0] - path[0][0]).days / 365.25
    peak = path[0][1]
    drawdown = 0.0
    for _, nav in path:
        peak = max(peak, nav)
        drawdown = min(drawdown, nav / peak - 1)
    deviation = statistics.stdev(returns)
    return {
        "cagr": (path[-1][1] / path[0][1]) ** (1 / years) - 1,
        "daily_sharpe": statistics.mean(returns) / deviation * math.sqrt(252),
        "max_drawdown": drawdown,
        "total_return": path[-1][1] / path[0][1] - 1,
        "years": years,
    }


def last_nav_by_date(path: list[tuple[dt.date, float]]) -> dict[dt.date, float]:
    result: dict[dt.date, float] = {}
    for date, nav in path:
        result[date] = nav
    return result


def subperiod_excess(
    strategy_path: list[tuple[dt.date, float]],
    benchmark_path: list[tuple[dt.date, float]],
) -> dict[str, float]:
    strategy_nav = last_nav_by_date(strategy_path)
    benchmark_nav = last_nav_by_date(benchmark_path)
    dates = sorted(set(strategy_nav) & set(benchmark_nav))
    ranges = {
        "2018-2019": (2018, 2019),
        "2020-2022": (2020, 2022),
        "2023-latest": (2023, 9999),
    }
    result = {}
    for label, (first_year, last_year) in ranges.items():
        selected = [date for date in dates if first_year <= date.year <= last_year]
        strategy_return = strategy_nav[selected[-1]] / strategy_nav[selected[0]] - 1
        benchmark_return = benchmark_nav[selected[-1]] / benchmark_nav[selected[0]] - 1
        result[label] = strategy_return - benchmark_return
    return result


def monthly_excess(
    strategy_path: list[tuple[dt.date, float]],
    benchmark_path: list[tuple[dt.date, float]],
) -> list[float]:
    strategy_nav = last_nav_by_date(strategy_path)
    benchmark_nav = last_nav_by_date(benchmark_path)
    common = sorted(set(strategy_nav) & set(benchmark_nav))
    month_ends: dict[tuple[int, int], dt.date] = {}
    for date in common:
        month_ends[(date.year, date.month)] = date
    dates = [month_ends[key] for key in sorted(month_ends)]
    return [
        (strategy_nav[end] / strategy_nav[start] - 1)
        - (benchmark_nav[end] / benchmark_nav[start] - 1)
        for start, end in zip(dates, dates[1:])
    ]


def circular_block_bootstrap(
    values: list[float],
    block_length: int,
    resamples: int,
    seed: int,
) -> dict[str, float]:
    generator = random.Random(seed)
    sample_means = []
    size = len(values)
    for _ in range(resamples):
        sample = []
        while len(sample) < size:
            start = generator.randrange(size)
            sample.extend(values[(start + offset) % size] for offset in range(block_length))
        sample_means.append(statistics.mean(sample[:size]))
    sample_means.sort()
    return {
        "observed_mean": statistics.mean(values),
        "lower_95": sample_means[int(0.025 * resamples)],
        "upper_95": sample_means[int(0.975 * resamples) - 1],
    }


def run(args: argparse.Namespace) -> int:
    if args.marker.exists() or args.result.exists():
        raise FileExistsError("formal audit marker/result already exists")
    expected = {
        args.strategy_result: "a5d4950d7d62ae64249d9f430ee289baa432a5904b954f57b87e9bce671614db",
        args.strategy_contract: "ff73032def532e4ad256a1e78ce85357ccc0fcbcdd0e1552d9e92c6f25184b64",
        args.strategy_adapter: "5b09494288916ff52e521a9a0171444557ae826e0a76e42e008ddc8680f07942",
        args.price_database: "6b29e56e8ccc79e2632e322c7671e7158408279c8411587f2c559eac9ec98d84",
    }
    for path, expected_sha in expected.items():
        actual = file_sha(path)
        if actual != expected_sha:
            raise ValueError(f"frozen input hash mismatch: {path}: {actual}")
    marker = {
        "research_id": AUDIT_ID,
        "formal_run_number": 1,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "audit_contract_sha256": file_sha(args.contract),
        "audit_adapter_sha256": file_sha(Path(__file__)),
        "benchmark_snapshot_id": BENCHMARK_SNAPSHOT,
        "frozen_input_hashes": {str(path): value for path, value in expected.items()},
    }
    atomic_json(args.marker, marker)
    symbols = strategy.symbols_from(args.identity_file)
    fundamentals = strategy.load_fundamentals(args.database)
    sessions = spy_sessions(args.price_database)
    decision_sessions = [
        date
        for date in strategy.sessions_from(args.price_database)
        if dt.date(2017, 12, 1) <= date <= END
    ]
    decisions = build_decisions(fundamentals, symbols, decision_sessions)
    prices = strategy.load_prices(args.price_database, symbols)
    benchmark = load_benchmark(args.database)
    base_path, turnover = simulate_strategy(decisions, sessions, prices, 0.0015)
    stress_path, _ = simulate_strategy(decisions, sessions, prices, 0.0030)
    qqq_path = simulate_qqq(benchmark, sessions, 0.0002)
    base = daily_metrics(base_path)
    stress = daily_metrics(stress_path)
    qqq = daily_metrics(qqq_path)
    periods = subperiod_excess(base_path, qqq_path)
    monthly = monthly_excess(base_path, qqq_path)
    bootstrap = circular_block_bootstrap(monthly, 3, 10000, 20260723)
    gate_values = {
        "base_cagr_excess_vs_qqq": base["cagr"] - qqq["cagr"],
        "daily_sharpe_margin_vs_qqq": base["daily_sharpe"] - qqq["daily_sharpe"],
        "drawdown_shortfall_vs_qqq": qqq["max_drawdown"] - base["max_drawdown"],
        "positive_subperiods": sum(value > 0 for value in periods.values()),
        "recent_subperiod_excess": periods["2023-latest"],
        "annual_one_way_turnover": turnover,
        "monthly_excess_bootstrap_lower": bootstrap["lower_95"],
    }
    gates = {
        "base_cagr_excess_vs_qqq": gate_values["base_cagr_excess_vs_qqq"] > 0.02,
        "daily_sharpe_margin_vs_qqq": gate_values["daily_sharpe_margin_vs_qqq"] >= 0.10,
        "drawdown_shortfall_vs_qqq": gate_values["drawdown_shortfall_vs_qqq"] <= 0.05,
        "subperiod_gate": gate_values["positive_subperiods"] >= 2
        and gate_values["recent_subperiod_excess"] > 0,
        "annual_one_way_turnover": turnover <= 0.50,
        "monthly_excess_bootstrap_lower": bootstrap["lower_95"] > 0,
    }
    passed = all(gates.values())
    result = {
        "research_id": AUDIT_ID,
        "date": "2026-07-23",
        "market": "US_EQUITIES",
        "phase": "RETROSPECTIVE_BENCHMARK_KILL_TEST",
        "current_status": "current" if passed else "rejected",
        "overall_result": "WORTH_TRUE_PIT_REPAIR_NOT_VALIDATED"
        if passed
        else "REJECTED_NOT_WORTH_COMPLEXITY_VS_QQQ",
        "formal_run_count": 1,
        "input": {
            "benchmark_snapshot_id": BENCHMARK_SNAPSHOT,
            "formation_count": len(decisions),
            "start": sessions[0].isoformat(),
            "end": sessions[-1].isoformat(),
            "strategy_approximate_pit": True,
            "strategy_survivorship_bias": True,
        },
        "metrics": {
            "strategy_base_15bps": base,
            "strategy_stress_30bps": stress,
            "qqq_2bps_entry_and_exit": qqq,
            "strategy_annual_one_way_turnover": turnover,
            "subperiod_excess_vs_qqq": periods,
            "monthly_excess_bootstrap": bootstrap,
        },
        "gates": {
            "passed_count": sum(gates.values()),
            "total_count": len(gates),
            "values": gate_values,
            "passed": gates,
            "failed": [name for name, value in gates.items() if not value],
        },
        "artifacts": {
            "audit_contract_sha256": marker["audit_contract_sha256"],
            "audit_adapter_sha256": marker["audit_adapter_sha256"],
            "marker_sha256": file_sha(args.marker),
            "strategy_result_sha256": expected[args.strategy_result],
            "price_database_sha256": expected[args.price_database],
        },
        "boundary": {
            "strategy_candidate_available": False,
            "this_is_validation": False,
            "recommendation": False,
            "paper": False,
            "broker": False,
            "live": False,
            "auto": False,
            "next_action": "true PIT repair only" if passed else "permanent strategy closure",
            "timing_or_factor_repair_allowed": False,
        },
    }
    atomic_json(args.result, result)
    return 0 if passed else 1


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    materialization = commands.add_parser("materialize")
    materialization.add_argument("--database", type=Path, required=True)
    materialization.add_argument("--price-database", type=Path, required=True)
    materialization.add_argument("--raw", type=Path, required=True)
    materialization.add_argument("--receipt", type=Path, required=True)
    execution = commands.add_parser("run")
    execution.add_argument("--database", type=Path, required=True)
    execution.add_argument("--price-database", type=Path, required=True)
    execution.add_argument("--identity-file", type=Path, required=True)
    execution.add_argument("--strategy-result", type=Path, required=True)
    execution.add_argument("--strategy-contract", type=Path, required=True)
    execution.add_argument("--strategy-adapter", type=Path, required=True)
    execution.add_argument("--contract", type=Path, required=True)
    execution.add_argument("--marker", type=Path, required=True)
    execution.add_argument("--result", type=Path, required=True)
    return parser


def main() -> int:
    arguments = make_parser().parse_args()
    return materialize(arguments) if arguments.command == "materialize" else run(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
