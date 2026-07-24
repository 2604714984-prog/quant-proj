"""One-use adapter for US_TOP50_GROSS_PROFITABILITY_V2_APPROX90D."""

from __future__ import annotations

import argparse
import calendar
import datetime as dt
import hashlib
import json
import math
import os
import statistics
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import duckdb

IDENTITY = "US_TOP50_GROSS_PROFITABILITY_V2_APPROX90D"
FUND_SNAPSHOT = f"{IDENTITY}_EASTMONEY_20260723"
PRICE_SNAPSHOT = "US_CURRENT_TOP50_DATA_MATERIALIZATION_V0_9_GSD_20260723"
PRICE_TABLE = "us_equity_research.us_daily_total_return_research"
FUND_TABLE = "us_equity_research.us_quarterly_fundamentals_approx_research"
SOURCE_COMMIT = "d52a8a0013363577bceb28ca876c88fe6c1a5aeb"
SEARCH_URL = "https://searchapi.eastmoney.com/api/suggest/get"
DATA_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
TOKEN = "D43BF722C8E33BDC906FB84D85E326E8"
UA = "Mozilla/5.0 (compatible; lightweight-personal-quant-research/1.0)"


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def object_sha(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def parse_date(value: str | None) -> dt.date | None:
    return dt.date.fromisoformat(value[:10]) if value else None


def fetch(url: str, params: dict, raw_path: Path) -> tuple[dict, str]:
    request = urllib.request.Request(
        url + "?" + urllib.parse.urlencode(params), headers={"User-Agent": UA}
    )
    error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                raw = response.read()
            value = json.loads(raw)
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = raw_path.with_suffix(".json.part")
            temporary.write_bytes(raw)
            os.replace(temporary, raw_path)
            return value, hashlib.sha256(raw).hexdigest()
        except Exception as caught:  # pragma: no cover
            error = caught
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"request failed: {request.full_url}") from error


def resolve(symbol: str, raw_dir: Path) -> str:
    value, _ = fetch(
        SEARCH_URL,
        {"input": symbol, "type": 14, "token": TOKEN, "count": 10},
        raw_dir / f"{symbol}_search.json",
    )
    rows = value.get("QuotationCodeTable", {}).get("Data", [])
    exact = [
        row
        for row in rows
        if str(row.get("Code", "")).upper() == symbol
        and str(row.get("MktNum", "")) in {"105", "106"}
    ]
    if not exact:
        raise ValueError(f"no exact NASDAQ/NYSE mapping for {symbol}")
    suffix = {"105": "O", "106": "N"}[str(exact[0]["MktNum"])]
    return f"{symbol}.{suffix}"


def datacenter(report: str, filter_string: str, raw_path: Path) -> tuple[list[dict], str]:
    value, source_sha = fetch(
        DATA_URL,
        {
            "reportName": report,
            "columns": "ALL",
            "filter": filter_string,
            "pageNumber": 1,
            "pageSize": 500,
            "sortColumns": "REPORT_DATE",
            "sortTypes": -1,
            "source": "WEB",
            "client": "WEB",
        },
        raw_path,
    )
    if not value.get("success") or not value.get("result"):
        raise ValueError(f"provider rejected {report}: {value.get('message')}")
    return value["result"].get("data") or [], source_sha


def quarter_key(value: str | None) -> tuple[int, int] | None:
    if not value or "/Q" not in value:
        return None
    try:
        year_text, quarter_text = value.split("/Q", 1)
        result = (int(year_text), int(quarter_text))
    except ValueError:
        return None
    return result if result[1] in {1, 2, 3, 4} else None


def is_next_quarter(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return right == ((left[0] + 1, 1) if left[1] == 4 else (left[0], left[1] + 1))


def second_session_after(notice: dt.date, sessions: list[dt.date]) -> dt.date | None:
    after = [session for session in sessions if session > notice]
    return after[1] if len(after) >= 2 else None


def normalize(
    symbol: str,
    secucode: str,
    gross: list[dict],
    assets: list[dict],
    sessions: list[dt.date],
    gross_sha: str,
    assets_sha: str,
    retrieved_at: str,
) -> list[dict]:
    asset_by_date = {
        parse_date(row.get("REPORT_DATE")): row
        for row in assets
        if row.get("STD_ITEM_CODE") == "004005999"
        and row.get("AMOUNT") is not None
        and float(row["AMOUNT"]) > 0
    }
    revisions: dict[tuple[int, int, dt.date], dict] = {}
    for row in gross:
        fiscal = quarter_key(row.get("REPORT_TYPE"))
        period = parse_date(row.get("REPORT_DATE"))
        notice = parse_date(row.get("NOTICE_DATE"))
        asset = asset_by_date.get(period)
        approximate_date = period + dt.timedelta(days=90) if period else None
        available = (
            next((session for session in sessions if session >= approximate_date), None)
            if approximate_date
            else None
        )
        if (
            row.get("DATE_TYPE") != "单季报"
            or not fiscal
            or not period
            or not notice
            or not available
            or not asset
            or row.get("GROSS_PROFIT") is None
            or float(row["GROSS_PROFIT"]) <= 0
            or row.get("CURRENCY_ABBR") != asset.get("CURRENCY_ABBR")
        ):
            continue
        candidate = {
            "snapshot_id": FUND_SNAPSHOT,
            "symbol": symbol,
            "source_symbol": secucode,
            "fiscal_period_end": period.isoformat(),
            "fiscal_year": fiscal[0],
            "fiscal_quarter": fiscal[1],
            "notice_date": notice.isoformat(),
            "available_at": available.isoformat(),
            "gross_profit": float(row["GROSS_PROFIT"]),
            "total_assets": float(asset["AMOUNT"]),
            "currency": row["CURRENCY_ABBR"],
            "gross_source_sha256": gross_sha,
            "assets_source_sha256": assets_sha,
            "retrieved_at": retrieved_at,
        }
        revisions[(fiscal[0], fiscal[1], notice)] = candidate
    return sorted(
        revisions.values(),
        key=lambda row: (row["fiscal_year"], row["fiscal_quarter"], row["notice_date"]),
    )


def symbols_from(path: Path) -> list[str]:
    value = json.loads(path.read_text(encoding="utf-8"))
    symbols = [str(item).upper() for item in value.get("symbols", [])]
    if len(symbols) != 46 or len(set(symbols)) != 46:
        raise ValueError("identity must contain 46 unique symbols")
    return symbols


def sessions_from(database: Path) -> list[dt.date]:
    connection = duckdb.connect(str(database), read_only=True)
    try:
        rows = connection.execute(
            f"""SELECT trade_date FROM {PRICE_TABLE}
                WHERE snapshot_id=? AND symbol='SPY' AND adj_close>0 ORDER BY trade_date""",
            [PRICE_SNAPSHOT],
        ).fetchall()
    finally:
        connection.close()
    result = [row[0] for row in rows]
    if len(result) < 2000:
        raise ValueError("SPY calendar is unexpectedly short")
    return result


def central_insert(database: Path, rows: list[dict]) -> tuple[int, bool]:
    keys = [
        (row["snapshot_id"], row["symbol"], row["fiscal_period_end"], row["notice_date"])
        for row in rows
    ]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate normalized keys")
    connection = duckdb.connect(str(database))
    try:
        connection.execute("BEGIN")
        connection.execute("CREATE SCHEMA IF NOT EXISTS us_equity_research")
        connection.execute(
            f"""CREATE TABLE IF NOT EXISTS {FUND_TABLE} (
                snapshot_id VARCHAR NOT NULL, symbol VARCHAR NOT NULL,
                source_symbol VARCHAR NOT NULL, fiscal_period_end DATE NOT NULL,
                fiscal_year INTEGER NOT NULL, fiscal_quarter INTEGER NOT NULL,
                notice_date DATE NOT NULL, available_at DATE NOT NULL,
                gross_profit DOUBLE NOT NULL, total_assets DOUBLE NOT NULL,
                currency VARCHAR NOT NULL, gross_source_sha256 VARCHAR NOT NULL,
                assets_source_sha256 VARCHAR NOT NULL, retrieved_at TIMESTAMPTZ NOT NULL,
                PRIMARY KEY(snapshot_id,symbol,fiscal_period_end,notice_date))"""
        )
        existing = connection.execute(
            f"SELECT COUNT(*) FROM {FUND_TABLE} WHERE snapshot_id=?", [FUND_SNAPSHOT]
        ).fetchone()[0]
        if existing and existing != len(rows):
            raise ValueError(f"existing row count {existing} != normalized count {len(rows)}")
        if not existing:
            connection.executemany(
                f"INSERT INTO {FUND_TABLE} VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [
                    [
                        row[key]
                        for key in (
                            "snapshot_id",
                            "symbol",
                            "source_symbol",
                            "fiscal_period_end",
                            "fiscal_year",
                            "fiscal_quarter",
                            "notice_date",
                            "available_at",
                            "gross_profit",
                            "total_assets",
                            "currency",
                            "gross_source_sha256",
                            "assets_source_sha256",
                            "retrieved_at",
                        )
                    ]
                    for row in rows
                ],
            )
        duplicates = connection.execute(
            f"""SELECT COUNT(*) FROM (
                SELECT snapshot_id,symbol,fiscal_period_end,notice_date,COUNT(*) n
                FROM {FUND_TABLE} WHERE snapshot_id=? GROUP BY 1,2,3,4 HAVING n>1)""",
            [FUND_SNAPSHOT],
        ).fetchone()[0]
        if duplicates:
            raise ValueError("central snapshot uniqueness failed")
        connection.execute("COMMIT")
        return existing or len(rows), not bool(existing)
    except Exception:
        connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()


def acquire(args: argparse.Namespace) -> int:
    symbols = symbols_from(args.identity_file)
    sessions = sessions_from(args.price_database)
    raw_dir = args.staging_dir / "raw"
    retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
    all_rows: list[dict] = []
    counts: dict[str, int] = {}
    mappings: dict[str, str] = {}
    failures: dict[str, str] = {}
    for index, symbol in enumerate(symbols, 1):
        try:
            secucode = resolve(symbol, raw_dir)
            gross, gross_sha = datacenter(
                "RPT_USF10_FN_GMAININDICATOR",
                f'(SECUCODE="{secucode}")',
                raw_dir / f"{symbol}_gmain.json",
            )
            assets, assets_sha = datacenter(
                "RPT_USF10_FN_BALANCE",
                f'(SECUCODE="{secucode}")(STD_ITEM_CODE="004005999")',
                raw_dir / f"{symbol}_assets.json",
            )
            rows = normalize(
                symbol,
                secucode,
                gross,
                assets,
                sessions,
                gross_sha,
                assets_sha,
                retrieved_at,
            )
            mappings[symbol], counts[symbol] = secucode, len(rows)
            all_rows.extend(rows)
            print(f"[{index:02d}/46] {symbol} -> {secucode}: {len(rows)}")
        except Exception as error:
            counts[symbol], failures[symbol] = 0, str(error)
            print(f"[{index:02d}/46] {symbol}: FAILED {error}", file=sys.stderr)
    qualified = sum(count >= 16 for count in counts.values())
    passed = qualified >= 30
    central_rows, inserted = central_insert(args.database, all_rows) if passed else (0, False)
    receipt = {
        "research_identity": IDENTITY,
        "status": "INPUT_QUALIFIED" if passed else "INPUT_BLOCKED",
        "source_repository_commit": SOURCE_COMMIT,
        "fundamental_snapshot_id": FUND_SNAPSHOT,
        "retrieved_at": retrieved_at,
        "companies_requested": 46,
        "companies_with_minimum_16_rows": qualified,
        "normalized_rows": len(all_rows),
        "company_row_counts": counts,
        "mappings": mappings,
        "failures": failures,
        "central_database_write": inserted,
        "central_database_rows": central_rows,
        "normalized_rows_sha256": object_sha(all_rows),
        "strategy_outcomes_accessed": False,
        "strategy_candidate_available": False,
        "approximate_pit_not_validation_grade": True,
    }
    atomic_json(args.receipt, receipt)
    return 0 if passed else 2


def load_fundamentals(database: Path) -> dict[str, list[dict]]:
    connection = duckdb.connect(str(database), read_only=True)
    try:
        rows = connection.execute(
            f"""SELECT symbol,fiscal_year,fiscal_quarter,notice_date,available_at,gross_profit,
                       total_assets,currency FROM {FUND_TABLE}
                WHERE snapshot_id=? ORDER BY symbol,fiscal_year,fiscal_quarter,notice_date""",
            [FUND_SNAPSHOT],
        ).fetchall()
    finally:
        connection.close()
    result: dict[str, list[dict]] = {}
    for symbol, year, quarter, notice, available, gross, assets, currency in rows:
        result.setdefault(symbol, []).append(
            {
                "fiscal": (year, quarter),
                "notice_date": notice,
                "available_at": available,
                "gross_profit": gross,
                "total_assets": assets,
                "currency": currency,
            }
        )
    return result


def factor_at(rows: list[dict], date: dt.date) -> float | None:
    by_quarter: dict[tuple[int, int], dict] = {}
    for row in rows:
        if row["available_at"] <= date:
            previous = by_quarter.get(row["fiscal"])
            if previous is None or row["notice_date"] > previous["notice_date"]:
                by_quarter[row["fiscal"]] = row
    latest = [by_quarter[key] for key in sorted(by_quarter)][-4:]
    if len(latest) < 4:
        return None
    if any(not is_next_quarter(latest[i]["fiscal"], latest[i + 1]["fiscal"]) for i in range(3)):
        return None
    if len({row["currency"] for row in latest}) != 1:
        return None
    value = sum(row["gross_profit"] for row in latest) / latest[-1]["total_assets"]
    return value if math.isfinite(value) and value > 0 else None


def formation_dates(sessions: list[dt.date]) -> list[dt.date]:
    last: dict[tuple[int, int], dt.date] = {}
    for date in sessions:
        if date.year >= 2018 and date.month in {3, 6, 9, 12}:
            last[(date.year, date.month)] = date
    return [last[key] for key in sorted(last)]


def next_session(date: dt.date, sessions: list[dt.date]) -> dt.date | None:
    return next((item for item in sessions if item > date), None)


def load_prices(database: Path, symbols: list[str]) -> dict[str, dict[dt.date, float]]:
    connection = duckdb.connect(str(database), read_only=True)
    marks = ",".join("?" for _ in symbols)
    try:
        rows = connection.execute(
            f"""SELECT symbol,trade_date,adj_close FROM {PRICE_TABLE}
                WHERE snapshot_id=? AND symbol IN ({marks})
                AND trade_date BETWEEN DATE '2017-12-01' AND DATE '2026-07-22'
                AND adj_close>0 ORDER BY symbol,trade_date""",
            [PRICE_SNAPSHOT, *symbols],
        ).fetchall()
    finally:
        connection.close()
    result: dict[str, dict[dt.date, float]] = {}
    for symbol, date, price in rows:
        result.setdefault(symbol, {})[date] = price
    return result


def rankdata(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        for index in order[start:end]:
            ranks[index] = (start + 1 + end) / 2
        start = end
    return ranks


def correlation(left: list[float], right: list[float]) -> float | None:
    if len(left) < 3 or len(left) != len(right):
        return None
    x_mean, y_mean = statistics.mean(left), statistics.mean(right)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(left, right))
    denominator = math.sqrt(
        sum((x - x_mean) ** 2 for x in left) * sum((y - y_mean) ** 2 for y in right)
    )
    return numerator / denominator if denominator else None


def rank_ic(pairs: list[tuple[float, float]]) -> float | None:
    return (
        correlation(rankdata([x for x, _ in pairs]), rankdata([y for _, y in pairs]))
        if len(pairs) >= 10
        else None
    )


def add_months(date: dt.date, months: int) -> dt.date:
    index = date.month - 1 + months
    year, month = date.year + index // 12, index % 12 + 1
    return dt.date(year, month, min(date.day, calendar.monthrange(year, month)[1]))


def session_on_or_after(date: dt.date, sessions: list[dt.date]) -> dt.date | None:
    return next((item for item in sessions if item >= date), None)


def choose(scores: dict[str, float], retained: set[str]) -> dict[str, float]:
    ranked = sorted(scores, key=lambda symbol: (-scores[symbol], symbol))
    ranks = {symbol: index + 1 for index, symbol in enumerate(ranked)}
    selected = sorted(
        [symbol for symbol in retained if symbol in ranks and ranks[symbol] <= 20],
        key=lambda symbol: (ranks[symbol], symbol),
    )
    for symbol in ranked:
        if symbol not in selected and len(selected) < 15:
            selected.append(symbol)
    return {symbol: 1 / len(selected) for symbol in selected}


def one_way_turnover(previous: dict[str, float], current: dict[str, float]) -> float:
    names = set(previous) | set(current)
    securities = sum(abs(current.get(name, 0) - previous.get(name, 0)) for name in names)
    cash = abs((1 - sum(current.values())) - (1 - sum(previous.values())))
    return 0.5 * (securities + cash)


def weighted_return(
    weights: dict[str, float],
    start: dt.date,
    end: dt.date,
    prices: dict[str, dict[dt.date, float]],
) -> float:
    try:
        return sum(
            weight * (prices[symbol][end] / prices[symbol][start] - 1)
            for symbol, weight in weights.items()
        )
    except KeyError as error:
        raise ValueError(f"missing execution price {error}: {start} -> {end}") from error


def metrics(returns: list[float], dates: list[dt.date]) -> dict[str, float]:
    years = (dates[-1] - dates[0]).days / 365.25
    wealth = peak = 1.0
    drawdown = 0.0
    for value in returns:
        wealth *= 1 + value
        peak = max(peak, wealth)
        drawdown = min(drawdown, wealth / peak - 1)
    deviation = statistics.stdev(returns)
    return {
        "cagr": wealth ** (1 / years) - 1,
        "sharpe": statistics.mean(returns) / deviation * 2 if deviation else 0,
        "max_drawdown": drawdown,
        "total_return": wealth - 1,
        "years": years,
    }


def diagnostics(
    decisions: list[dict], sessions: list[dt.date], prices: dict[str, dict[dt.date, float]]
) -> dict:
    ics: dict[int, list[float]] = {1: [], 3: [], 6: []}
    monotonicity: list[float] = []
    spreads: list[float] = []
    for decision in decisions:
        start = decision["execution"]
        for horizon in (1, 3, 6):
            end = session_on_or_after(add_months(start, horizon), sessions)
            pairs = []
            if end:
                for symbol, score in decision["scores"].items():
                    if start in prices.get(symbol, {}) and end in prices.get(symbol, {}):
                        pairs.append((score, prices[symbol][end] / prices[symbol][start] - 1))
            value = rank_ic(pairs)
            if value is not None:
                ics[horizon].append(value)
        end = session_on_or_after(add_months(start, 3), sessions)
        ordered = sorted(decision["scores"], key=lambda item: (decision["scores"][item], item))
        if end and len(ordered) >= 30:
            cut1, cut2 = len(ordered) // 3, 2 * len(ordered) // 3
            buckets = (ordered[:cut1], ordered[cut1:cut2], ordered[cut2:])
            bucket_returns = []
            for bucket in buckets:
                values = [
                    prices[symbol][end] / prices[symbol][start] - 1
                    for symbol in bucket
                    if start in prices.get(symbol, {}) and end in prices.get(symbol, {})
                ]
                bucket_returns.append(statistics.mean(values) if values else math.nan)
            if all(math.isfinite(value) for value in bucket_returns):
                monotonicity.append(correlation([1, 2, 3], rankdata(bucket_returns)) or 0)
                spreads.append(bucket_returns[2] - statistics.mean(bucket_returns))
    return {
        "rank_ic_mean": {
            f"{horizon}m": statistics.mean(values) if values else None
            for horizon, values in ics.items()
        },
        "rank_ic_observations": {f"{horizon}m": len(values) for horizon, values in ics.items()},
        "tercile_monotonicity_mean_3m": statistics.mean(monotonicity)
        if monotonicity
        else None,
        "top_tercile_minus_tercile_mean_3m": statistics.mean(spreads) if spreads else None,
        "diagnostic_promotion_gate": False,
    }


def subperiods(strategy: list[float], benchmark: list[float], dates: list[dt.date]) -> dict:
    ranges = {"2018-2019": (2018, 2019), "2020-2022": (2020, 2022), "2023-latest": (2023, 9999)}
    result = {}
    for label, (first, last) in ranges.items():
        indices = [index for index, date in enumerate(dates) if first <= date.year <= last]
        result[label] = (
            math.prod(1 + strategy[index] for index in indices)
            - math.prod(1 + benchmark[index] for index in indices)
            if indices
            else None
        )
    return result


def run(args: argparse.Namespace) -> int:
    if args.result.exists() or args.marker.exists():
        raise FileExistsError("formal run marker/result already exists")
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    if contract.get("research_identity") != IDENTITY:
        raise ValueError("contract identity mismatch")
    symbols = symbols_from(args.identity_file)
    fundamentals = load_fundamentals(args.database)
    sessions = [
        date
        for date in sessions_from(args.price_database)
        if dt.date(2017, 12, 1) <= date <= dt.date(2026, 7, 22)
    ]
    retained: set[str] = set()
    decisions = []
    coverage = {}
    for formation in formation_dates(sessions):
        scores = {
            symbol: value
            for symbol in symbols
            if (value := factor_at(fundamentals.get(symbol, []), formation)) is not None
        }
        coverage[formation.isoformat()] = len(scores)
        execution = next_session(formation, sessions)
        if len(scores) >= 30 and execution:
            weights = choose(scores, retained)
            decisions.append(
                {
                    "formation": formation,
                    "execution": execution,
                    "scores": scores,
                    "weights": weights,
                    "benchmark": {symbol: 1 / len(scores) for symbol in scores},
                }
            )
            retained = set(weights)
    coverage_fraction = sum(value >= 30 for value in coverage.values()) / len(coverage)
    if len(decisions) < 30 or coverage_fraction < 0.70:
        atomic_json(
            args.result,
            {
                "research_identity": IDENTITY,
                "overall_result": "INPUT_BLOCKED",
                "qualified_formations": len(decisions),
                "coverage_fraction": coverage_fraction,
                "coverage": coverage,
                "formal_run_count": 0,
                "strategy_outcomes_accessed": False,
                "strategy_candidate_available": False,
            },
        )
        return 2

    marker = {
        "research_identity": IDENTITY,
        "formal_run_number": 1,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "contract_sha256": file_sha(args.contract),
        "adapter_sha256": file_sha(Path(__file__)),
        "identity_file_sha256": file_sha(args.identity_file),
        "price_database_sha256": file_sha(args.price_database),
        "fundamental_snapshot_id": FUND_SNAPSHOT,
        "fundamental_rows_sha256": object_sha(fundamentals),
    }
    atomic_json(args.marker, marker)
    prices = load_prices(args.price_database, [*symbols, "SPY"])
    factor_diagnostic = diagnostics(decisions, sessions, prices)
    dates = [decision["execution"] for decision in decisions]
    if dates[-1] < sessions[-1]:
        dates.append(sessions[-1])
    else:
        decisions = decisions[:-1]
    base_returns, stress_returns, benchmark_returns, spy_returns, turns = [], [], [], [], []
    previous: dict[str, float] = {}
    for index, decision in enumerate(decisions):
        start, end = dates[index], dates[index + 1]
        gross = weighted_return(decision["weights"], start, end, prices)
        benchmark = weighted_return(decision["benchmark"], start, end, prices)
        turnover = one_way_turnover(previous, decision["weights"])
        base_returns.append(gross - 0.0015 * turnover)
        stress_returns.append(gross - 0.0030 * turnover)
        benchmark_returns.append(benchmark)
        spy_returns.append(prices["SPY"][end] / prices["SPY"][start] - 1)
        turns.append(turnover)
        previous = decision["weights"]
    base, stress = metrics(base_returns, dates), metrics(stress_returns, dates)
    benchmark, spy = metrics(benchmark_returns, dates), metrics(spy_returns, dates)
    annual_turnover = sum(turns) / base["years"]
    periods = subperiods(base_returns, benchmark_returns, dates[:-1])
    values = {
        "base_cagr_excess_vs_primary": base["cagr"] - benchmark["cagr"],
        "base_sharpe_margin_vs_primary": base["sharpe"] - benchmark["sharpe"],
        "drawdown_shortfall_vs_primary": benchmark["max_drawdown"] - base["max_drawdown"],
        "stress_cagr_excess_vs_primary": stress["cagr"] - benchmark["cagr"],
        "annual_one_way_turnover": annual_turnover,
        "positive_primary_excess_subperiods": sum(
            value is not None and value > 0 for value in periods.values()
        ),
    }
    gates = {
        "base_cagr_excess_vs_primary": values["base_cagr_excess_vs_primary"] > 0.01,
        "base_sharpe_margin_vs_primary": values["base_sharpe_margin_vs_primary"] >= 0.05,
        "drawdown_shortfall_vs_primary": values["drawdown_shortfall_vs_primary"] <= 0.05,
        "stress_cagr_excess_vs_primary": values["stress_cagr_excess_vs_primary"] > 0,
        "annual_one_way_turnover": annual_turnover <= 2.0,
        "positive_primary_excess_subperiods": values["positive_primary_excess_subperiods"] >= 2,
    }
    passed = all(gates.values())
    result = {
        "research_identity": IDENTITY,
        "date": "2026-07-23",
        "phase": "SINGLE_HISTORICAL_DISCOVERY",
        "overall_result": "DISCOVERY_PASS_REVIEW_REQUIRED" if passed else "DISCOVERY_FAIL",
        "formal_run_count": 1,
        "strategy_outcomes_accessed": True,
        "input": {
            "price_snapshot_id": PRICE_SNAPSHOT,
            "fundamental_snapshot_id": FUND_SNAPSHOT,
            "qualified_formations": len(decisions),
            "formation_coverage_fraction": coverage_fraction,
            "minimum_eligible": min(
                coverage[decision["formation"].isoformat()] for decision in decisions
            ),
            "survivorship_bias": True,
            "approximate_pit_not_validation_grade": True,
        },
        "factor_diagnostics": factor_diagnostic,
        "portfolio": {
            "base_15bps": base,
            "stress_30bps": stress,
            "eligible_equal_weight": benchmark,
            "spy": spy,
            "annual_one_way_turnover": annual_turnover,
            "subperiod_primary_excess": periods,
        },
        "gates": {"values": values, "passed": gates},
        "artifacts": {
            "contract_sha256": marker["contract_sha256"],
            "adapter_sha256": marker["adapter_sha256"],
            "marker_sha256": file_sha(args.marker),
            "price_database_sha256": marker["price_database_sha256"],
            "fundamental_rows_sha256": marker["fundamental_rows_sha256"],
        },
        "boundaries": {
            "strategy_candidate_available": False,
            "approximate_pit_not_validation_grade": True,
            "recommendation": False,
            "current_holdings_output": False,
            "paper": False,
            "broker": False,
            "live": False,
            "auto": False,
            "next_if_pass": "independent external review before any validation identity",
            "next_if_fail": "permanent closure; no parameter repair",
        },
    }
    atomic_json(args.result, result)
    return 0 if passed else 1


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    acquisition = commands.add_parser("acquire")
    acquisition.add_argument("--database", type=Path, required=True)
    acquisition.add_argument("--price-database", type=Path, required=True)
    acquisition.add_argument("--identity-file", type=Path, required=True)
    acquisition.add_argument("--staging-dir", type=Path, required=True)
    acquisition.add_argument("--receipt", type=Path, required=True)
    execution = commands.add_parser("run")
    execution.add_argument("--database", type=Path, required=True)
    execution.add_argument("--price-database", type=Path, required=True)
    execution.add_argument("--identity-file", type=Path, required=True)
    execution.add_argument("--contract", type=Path, required=True)
    execution.add_argument("--marker", type=Path, required=True)
    execution.add_argument("--result", type=Path, required=True)
    return parser


def main() -> int:
    arguments = make_parser().parse_args()
    return acquire(arguments) if arguments.command == "acquire" else run(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
