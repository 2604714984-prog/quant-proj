"""Frozen current-universe 12-1 momentum discovery; research-only and not PIT."""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, date, datetime, timedelta
import hashlib
from html.parser import HTMLParser
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
from statistics import median
from typing import Any, Iterable
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

import duckdb

from quant_system.data.writer import DataWriteError, append_rows


RID = "US_CURRENT_TOP50_MOMENTUM_DISCOVERY_V0"
CONTRACT_SHA = "a4b1126132fd8492cd1d2560a9e76b8c8485ce3282d0b109727db6dc8475f663"
OFFICIAL = "https://dng-api.invesco.com/cache/v1/accounts/en_US/shareclasses/46137V233/holdings/fund?idType=cusip"
FALLBACK = "https://stockanalysis.com/etf/xlg/holdings/"
UA = "quant-proj-research/2.0 (+https://github.com/2604714984-prog/quant-proj)"
OLD = {
    "us_stock_top50_input_blocked_20260722.json": "36d0581465ea37d26d695bfaa4e1ca1efbc190880b44148058cd30ba712d0877",
    "us_sp500_top50_xlg_disclosed_universe_v1_input_blocked_20260722.json": "f7da25e80b6f9aefaab59b74086fcd98f9f8d16265bdfa1b26f7461cf93d58a6",
    "sec_nport_bulk_zip_v1_smoke_2025q1_input_blocked_20260722.json": "fd401efa9ddcc404fd3e919eae0f83eb24cf4e2a2f8c2a90915f038e419823dd",
}
SMOKE = ("AAPL", "MSFT", "NVDA", "AMZN", "GOOGL")
SNAPSHOT = "US_CURRENT_TOP50_MOMENTUM_DISCOVERY_V0_20260722"


class Blocked(RuntimeError):
    pass


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while b := f.read(8 << 20):
            h.update(b)
    return h.hexdigest()


def dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_text(json.dumps(value, sort_keys=True, indent=2, default=str) + "\n")
    os.replace(tmp, path)


def guards(repo: Path) -> None:
    if sha(repo / "research/definitions/us_current_top50_momentum_discovery_v0.json") != CONTRACT_SHA:
        raise Blocked("contract_sha_changed")
    for name, expected in OLD.items():
        if sha(repo / "research/results" / name) != expected:
            raise Blocked(f"old_result_changed:{name}")


def fetch(url: str, path: Path, limit: int = 20 << 20) -> dict[str, Any]:
    meta_path = path.with_suffix(path.suffix + ".metadata.json")
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        if meta["url"] != url or (path.exists() and sha(path) != meta["sha256"]):
            raise Blocked(f"staging_identity_conflict:{path}")
        return meta
    request = Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    retrieved = datetime.now(UTC).isoformat()
    try:
        response = urlopen(request, timeout=90)  # noqa: S310
    except HTTPError as exc:
        response = exc
    with response:
        status = int(getattr(response, "status", 0) or getattr(response, "code", 0))
        final_url = response.geturl()
        headers = {k.lower(): v for k, v in response.headers.items()}
        raw = response.read(limit + 1)
    if len(raw) > limit:
        raise Blocked(f"response_too_large:{url}")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_bytes(raw)
    os.replace(tmp, path)
    meta = {
        "url": url,
        "final_url": final_url,
        "retrieved_at": retrieved,
        "status": status,
        "content_type": headers.get("content-type"),
        "bytes": len(raw),
        "sha256": sha(path),
        "retry_count": 0,
    }
    dump(meta_path, meta)
    return meta


def _key(row: dict[str, Any], names: Iterable[str]) -> Any:
    normalized = {re.sub(r"[^a-z0-9]", "", str(k).lower()): v for k, v in row.items()}
    for name in names:
        if name in normalized and normalized[name] not in (None, ""):
            return normalized[name]
    return None


def _weight(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).replace("%", "").replace(",", "").strip()
    try:
        result = float(text)
    except ValueError:
        return None
    return result / 100 if "%" in str(value) or result > 1 else result


def parse_holdings_json(raw: bytes) -> list[dict[str, Any]]:
    root = json.loads(raw)
    lists: list[list[dict[str, Any]]] = []

    def walk(value: Any) -> None:
        if isinstance(value, list) and value and all(isinstance(x, dict) for x in value):
            lists.append(value)
        if isinstance(value, dict):
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(root)
    best: list[dict[str, Any]] = []
    for items in lists:
        parsed = []
        for item in items:
            symbol = _key(item, ("ticker", "symbol", "securityticker", "holdingticker"))
            name = _key(item, ("name", "securityname", "holdingname", "issuername"))
            weight = _weight(_key(item, ("weight", "marketvalueweight", "percentage")))
            if symbol and name and re.fullmatch(r"[A-Za-z][A-Za-z0-9. -]{0,9}", str(symbol)):
                parsed.append({"symbol": str(symbol).upper().replace(".", "-"), "name": str(name), "weight": weight})
        if len(parsed) > len(best):
            best = parsed
    return best


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self.table: list[list[str]] | None = None
        self.row: list[str] | None = None
        self.cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self.table = []
        elif tag == "tr" and self.table is not None:
            self.row = []
        elif tag in {"th", "td"} and self.row is not None:
            self.cell = []

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"th", "td"} and self.cell is not None and self.row is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None and self.table is not None:
            self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def parse_holdings_html(raw: bytes) -> list[dict[str, Any]]:
    parser = TableParser()
    parser.feed(raw.decode("utf-8", errors="strict"))
    for table in parser.tables:
        if not table:
            continue
        header = [x.lower() for x in table[0]]
        if "symbol" not in header or "weight" not in " ".join(header):
            continue
        si = header.index("symbol")
        ni = next((i for i, x in enumerate(header) if x in {"company", "name", "holding"}), -1)
        wi = next(i for i, x in enumerate(header) if "weight" in x)
        rows = []
        for cells in table[1:]:
            if max(si, ni, wi) < len(cells) and ni >= 0:
                rows.append({"symbol": cells[si].upper().replace(".", "-"), "name": cells[ni], "weight": _weight(cells[wi])})
        if len(rows) >= 45:
            return rows
    return []


def company(name: str) -> str:
    value = re.sub(r"\bCLASS\s+[ABC]\b$", "", name.upper()).strip()
    return re.sub(r"[^A-Z0-9]", "", value)


def yahoo_url(symbol: str) -> str:
    p1 = int(datetime(2015, 1, 1, tzinfo=UTC).timestamp())
    p2 = int(datetime.combine(date.today() + timedelta(days=1), datetime.min.time(), UTC).timestamp())
    return f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}?period1={p1}&period2={p2}&interval=1d&events=div%2Csplits&includeAdjustedClose=true"


def stooq_url(symbol: str) -> str:
    return f"https://stooq.com/q/d/l/?s={quote(symbol.lower())}.us&d1=20150101&d2={date.today():%Y%m%d}&i=d"


def yahoo_rows(raw: bytes) -> list[dict[str, Any]]:
    result = json.loads(raw)["chart"]["result"][0]
    quote_data = result["indicators"]["quote"][0]
    adjusted = result["indicators"]["adjclose"][0]["adjclose"]
    rows = []
    for i, timestamp in enumerate(result["timestamp"]):
        values = {k: quote_data[k][i] for k in ("open", "high", "low", "close", "volume")}
        if adjusted[i] is None or any(values[k] is None for k in ("close", "volume")):
            continue
        rows.append({"date": datetime.fromtimestamp(timestamp, UTC).date(), **values, "adj_close": adjusted[i]})
    if len(rows) < 60 or any(float(row["close"]) <= 0 for row in rows):
        raise Blocked("invalid_yahoo_history")
    return rows


def stooq_rows(raw: bytes) -> dict[date, float]:
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    rows = {date.fromisoformat(row["Date"]): float(row["Close"]) for row in reader if row.get("Close") not in (None, "", "N/D")}
    if len(rows) < 60:
        raise Blocked("invalid_stooq_history")
    return rows


def crosscheck(primary: list[dict[str, Any]], other: dict[date, float]) -> dict[str, Any]:
    overlap = [(row["date"], abs(float(row["close"]) / other[row["date"]] - 1)) for row in primary if row["date"] in other]
    if not overlap:
        raise Blocked("no_price_overlap")
    passed = sum(diff <= 0.005 for _, diff in overlap) / len(overlap)
    worst = sorted(overlap, key=lambda item: item[1], reverse=True)[:3]
    return {"overlap": len(overlap), "pass_ratio": passed, "passed": passed >= 0.98, "worst": [(str(d), x) for d, x in worst]}


def acquire_symbol(symbol: str, root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    ypath = root / "prices/yahoo" / f"{symbol}.json"
    spath = root / "prices/stooq" / f"{symbol}.csv"
    ym = fetch(yahoo_url(symbol), ypath)
    sm = fetch(stooq_url(symbol), spath)
    if ym["status"] != 200 or sm["status"] != 200:
        raise Blocked(f"price_http_failure:{symbol}")
    rows = yahoo_rows(ypath.read_bytes())
    check = crosscheck(rows, stooq_rows(spath.read_bytes()))
    return rows, {"symbol": symbol, "yahoo": ym, "stooq": sm, "crosscheck": check}


def universe(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    opath = root / "universe/invesco_xlg_holdings.json"
    om = fetch(OFFICIAL, opath)
    rows = parse_holdings_json(opath.read_bytes()) if om["status"] == 200 else []
    used = "INVESCO_OFFICIAL"
    fallback_meta = None
    if not 50 <= len(rows) <= 51:
        if om["status"] != 200 or len(rows) < 5:
            raise Blocked("official_universe_not_crosscheckable")
        fpath = root / "universe/stockanalysis_xlg_holdings.html"
        fallback_meta = fetch(FALLBACK, fpath)
        fallback_rows = parse_holdings_html(fpath.read_bytes()) if fallback_meta["status"] == 200 else []
        if not 50 <= len(fallback_rows) <= 51:
            raise Blocked("fallback_universe_not_machine_readable")
        if [x["symbol"] for x in rows[:5]] != [x["symbol"] for x in fallback_rows[:5]]:
            raise Blocked("fallback_top_five_identity_conflict")
        if any(x["weight"] is None or y["weight"] is None or abs(x["weight"] - y["weight"]) > 0.001 for x, y in zip(rows[:5], fallback_rows[:5])):
            raise Blocked("fallback_top_five_weight_conflict")
        rows, used = fallback_rows, "STOCKANALYSIS_FALLBACK"
    rows = [row for row in rows if re.fullmatch(r"[A-Z][A-Z0-9-]{0,9}", row["symbol"])]
    if len({company(row["name"]) for row in rows}) != 50 or len(rows) not in {50, 51}:
        raise Blocked("universe_50_company_identity_failed")
    dump(root / "universe/frozen_rows.json", rows)
    return rows, {"source": used, "official": om, "fallback": fallback_meta, "security_lines": len(rows), "companies": 50}


def smoke(repo: Path, root: Path) -> dict[str, Any]:
    guards(repo)
    rows, identity = universe(root)
    checks = []
    for symbol in SMOKE:
        _, check = acquire_symbol(symbol, root)
        checks.append(check)
        if not check["crosscheck"]["passed"]:
            raise Blocked(f"smoke_crosscheck_failed:{symbol}")
    result = {"status": "SMOKE_PASS", "universe": identity, "symbols": len(checks), "checks": checks}
    dump(root / "smoke_result.json", result)
    return result


def choose_lines(rows: list[dict[str, Any]], histories: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(company(row["name"]), []).append(row)
    selected = []
    for members in groups.values():
        if len(members) == 1:
            selected.append(members[0])
            continue
        if len(members) != 2:
            raise Blocked("ambiguous_multi_class_company")
        common = sorted(set(x["date"] for x in histories[members[0]["symbol"]]) & set(x["date"] for x in histories[members[1]["symbol"]]))[-60:]
        if len(common) != 60:
            raise Blocked("multi_class_60_sessions_missing")
        scores = []
        for member in members:
            by_date = {x["date"]: x for x in histories[member["symbol"]]}
            scores.append((median(float(by_date[d]["close"]) * float(by_date[d]["volume"]) for d in common), member))
        if scores[0][0] == scores[1][0]:
            raise Blocked("multi_class_liquidity_tie")
        selected.append(max(scores, key=lambda x: x[0])[1])
    if len(selected) != 50:
        raise Blocked("selected_stock_line_count_not_50")
    return selected


def row_hash(row: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(row, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def writer_rows(symbol: str, rows: list[dict[str, Any]], meta: dict[str, Any]) -> list[dict[str, Any]]:
    result, previous = [], None
    observed = datetime.fromisoformat(meta["yahoo"]["retrieved_at"])
    for item in rows:
        close, adj = float(item["close"]), float(item["adj_close"])
        factor = adj / close
        gross = None if previous is None else adj / previous
        row = {"snapshot_id": SNAPSHOT, "symbol": symbol, "trade_date": item["date"], "source_timestamp": None, "open": item["open"], "high": item["high"], "low": item["low"], "close": close, "volume": int(item["volume"]), "adj_open": None if item["open"] is None else float(item["open"]) * factor, "adj_high": None if item["high"] is None else float(item["high"]) * factor, "adj_low": None if item["low"] is None else float(item["low"]) * factor, "adj_close": adj, "adj_volume": round(int(item["volume"]) / factor), "div_cash": None, "split_factor": None, "gross_return_factor": gross, "adjusted_reference_factor": factor, "adjusted_reference_relative_error": None, "source_url": meta["yahoo"]["url"], "source_document_sha256": meta["yahoo"]["sha256"], "observed_at": observed, "available_at": observed, "availability_basis": "CURRENT_RETRIEVAL_RETROSPECTIVE_ADJUSTED_DISCOVERY_NOT_PIT", "price_adjustment_status": "YAHOO_ADJ_CLOSE_CURRENT_RETRIEVAL_NOT_PIT", "row_sha256": "", "quality_status": "DISCOVERY_V0_PRIMARY_QUALIFIED", "conflict_flags_json": json.dumps({"stooq_pass_ratio": meta["crosscheck"]["pass_ratio"]}, sort_keys=True), "synthetic_data": False}
        row["row_sha256"] = row_hash({k: v for k, v in row.items() if k != "row_sha256"})
        result.append(row)
        previous = adj
    return result


def materialize(repo: Path, root: Path, db: Path) -> dict[str, Any]:
    guards(repo)
    if json.loads((root / "smoke_result.json").read_text())["status"] != "SMOKE_PASS":
        raise Blocked("smoke_not_passed")
    universe_rows = json.loads((root / "universe/frozen_rows.json").read_text())
    histories, evidence, unresolved = {}, {}, []
    for item in universe_rows + [{"symbol": "SPY"}, {"symbol": "XLG"}]:
        symbol = item["symbol"]
        rows, check = acquire_symbol(symbol, root)
        histories[symbol], evidence[symbol] = rows, check
        if not check["crosscheck"]["passed"]:
            unresolved.append(symbol)
    if len(unresolved) > 5:
        raise Blocked(f"unresolved_price_conflicts:{len(unresolved)}")
    selected = choose_lines(universe_rows, histories)
    qualified = [row for row in selected if row["symbol"] not in unresolved]
    if len(qualified) < 30:
        raise Blocked("fewer_than_30_qualified_current_lines")
    symbols = [row["symbol"] for row in qualified] + ["SPY", "XLG"]
    all_bars = [bar for symbol in symbols for bar in writer_rows(symbol, histories[symbol], evidence[symbol])]
    observed = datetime.now(UTC)
    universe_sha = sha(root / "universe/frozen_rows.json")
    metadata = []
    for item in qualified:
        row = {"snapshot_id": SNAPSHOT, "symbol": item["symbol"], "name": item["name"], "exchange_code": None, "description": "CURRENT_XLG_TOP50_FIXED_HISTORY_DISCOVERY_V0", "start_date": None, "end_date": None, "source_url": OFFICIAL, "source_document_sha256": universe_sha, "observed_at": observed, "available_at": observed, "availability_basis": "CURRENT_SNAPSHOT_SURVIVORSHIP_BIASED_NOT_PIT", "row_sha256": "", "quality_status": "DISCOVERY_V0_CURRENT_UNIVERSE", "synthetic_data": False}
        row["row_sha256"] = row_hash({k: v for k, v in row.items() if k != "row_sha256"})
        metadata.append(row)
    dump(root / "qualified_identity.json", {"snapshot_id": SNAPSHOT, "stock_count": len(qualified), "symbols": [x["symbol"] for x in qualified], "unresolved_symbols": unresolved})
    dump(root / "writer/security_rows.json", metadata)
    dump(root / "writer/bar_rows.json", all_bars)
    isolated = root / "writer/isolated.duckdb"
    shutil.copy2(db, isolated)
    security_sha, bars_sha = sha(root / "writer/security_rows.json"), sha(root / "writer/bar_rows.json")
    for target, rows, keys, source_sha in (("security", metadata, ("snapshot_id", "symbol"), security_sha), ("bars", all_bars, ("snapshot_id", "symbol", "trade_date"), bars_sha)):
        table = "us_security_metadata_research" if target == "security" else "us_daily_total_return_research"
        batch = f"{SNAPSHOT}:{target}"
        first = append_rows(isolated, schema="us_equity_research", table=table, natural_keys=keys, rows=rows, batch_id=batch, source_sha256=source_sha, max_rows=1_000_000)
        replay = append_rows(isolated, schema="us_equity_research", table=table, natural_keys=keys, rows=rows, batch_id=batch, source_sha256=source_sha, max_rows=1_000_000)
        if first.inserted_rows != len(rows) or replay.existing_rows != len(rows):
            raise Blocked(f"isolated_idempotency_failed:{target}")
    backup = root / "writer/quant_research.preappend.duckdb"
    shutil.copy2(db, backup)
    if sha(backup) != sha(db):
        raise Blocked("backup_hash_mismatch")
    receipts = []
    try:
        receipts.append(append_rows(db, schema="us_equity_research", table="us_security_metadata_research", natural_keys=("snapshot_id", "symbol"), rows=metadata, batch_id=f"{SNAPSHOT}:security", source_sha256=security_sha, max_rows=1_000_000).to_dict())
        receipts.append(append_rows(db, schema="us_equity_research", table="us_daily_total_return_research", natural_keys=("snapshot_id", "symbol", "trade_date"), rows=all_bars, batch_id=f"{SNAPSHOT}:bars", source_sha256=bars_sha, max_rows=1_000_000).to_dict())
    except Exception:
        shutil.copy2(backup, db)
        raise
    with duckdb.connect(str(db), read_only=True) as con:
        count = con.execute("SELECT count(*) FROM us_equity_research.us_daily_total_return_research WHERE snapshot_id=?", [SNAPSHOT]).fetchone()[0]
        duplicates = con.execute("SELECT count(*) FROM (SELECT symbol,trade_date,count(*) n FROM us_equity_research.us_daily_total_return_research WHERE snapshot_id=? GROUP BY 1,2 HAVING n>1)", [SNAPSHOT]).fetchone()[0]
        nonfinite = con.execute("SELECT count(*) FROM us_equity_research.us_daily_total_return_research WHERE snapshot_id=? AND (NOT isfinite(close) OR NOT isfinite(adj_close))", [SNAPSHOT]).fetchone()[0]
    if count != len(all_bars) or duplicates or nonfinite:
        shutil.copy2(backup, db)
        raise Blocked("central_postwrite_validation_failed")
    result = {"status": "CENTRAL_DATA_READY", "stock_count": len(qualified), "price_symbol_count": len(symbols), "bar_rows": len(all_bars), "unresolved_count": len(unresolved), "receipts": receipts, "backup_sha256": sha(backup), "db_sha256": sha(db)}
    dump(root / "central_data_receipt.json", result)
    return result


def metric(dates: list[date], equity: list[float], returns: list[float]) -> dict[str, float]:
    years = (dates[-1] - dates[0]).days / 365.25
    cagr = (equity[-1] / equity[0]) ** (1 / years) - 1
    mean = sum(returns) / len(returns)
    variance = sum((x - mean) ** 2 for x in returns) / (len(returns) - 1)
    vol = math.sqrt(variance) * math.sqrt(252)
    peak, drawdown = equity[0], 0.0
    for value in equity:
        peak = max(peak, value)
        drawdown = min(drawdown, value / peak - 1)
    return {"cagr": cagr, "volatility": vol, "sharpe": mean / math.sqrt(variance) * math.sqrt(252), "max_drawdown": drawdown}


def simulate(calendar: list[date], prices: dict[str, dict[date, float]], schedule: dict[date, dict[str, float]], cost: float) -> tuple[list[date], list[float], list[float], float]:
    weights, output_dates, equity, returns, value, turnover = {}, [], [], [], 1.0, 0.0
    started = False
    for prior, current in zip(calendar, calendar[1:]):
        daily = 0.0
        if started:
            for symbol, weight in weights.items():
                if prior not in prices[symbol] or current not in prices[symbol]:
                    raise Blocked(f"held_price_gap:{symbol}:{current}")
                daily += weight * (prices[symbol][current] / prices[symbol][prior] - 1)
            value *= 1 + daily
            gross = {symbol: weight * prices[symbol][current] / prices[symbol][prior] for symbol, weight in weights.items()}
            total = sum(gross.values())
            weights = {symbol: amount / total for symbol, amount in gross.items()}
        trade_cost = 0.0
        if current in schedule:
            target = schedule[current]
            traded = sum(abs(target.get(s, 0) - weights.get(s, 0)) for s in set(target) | set(weights))
            if started:
                turnover += traded / 2
            trade_cost = cost * traded
            value *= 1 - trade_cost
            weights, started = target, True
        if started:
            output_dates.append(current)
            equity.append(value)
            returns.append(daily - trade_cost)
    years = (output_dates[-1] - output_dates[0]).days / 365.25
    return output_dates, equity, returns, turnover / years


def svg_chart(path: Path, dates: list[date], strategy: list[float], benchmark: list[float]) -> None:
    width, height, margin = 1000, 560, 55
    peak_s = peak_b = 0.0
    dd_s, dd_b = [], []
    for s, b in zip(strategy, benchmark):
        peak_s, peak_b = max(peak_s, s), max(peak_b, b)
        dd_s.append(s / peak_s - 1)
        dd_b.append(b / peak_b - 1)
    def points(values: list[float], y0: float, h: float, low: float, high: float) -> str:
        return " ".join(f"{margin+i*(width-2*margin)/(len(values)-1):.1f},{y0+h-(v-low)/(high-low)*h:.1f}" for i, v in enumerate(values))
    high, low = max(strategy + benchmark), min(strategy + benchmark)
    dlow = min(dd_s + dd_b)
    content = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"><rect width="100%" height="100%" fill="white"/><text x="55" y="28" font-family="sans-serif" font-size="18">Discovery equity and drawdown (no holdings shown)</text><polyline fill="none" stroke="#1f77b4" stroke-width="2" points="{points(strategy,50,300,low,high)}"/><polyline fill="none" stroke="#ff7f0e" stroke-width="2" points="{points(benchmark,50,300,low,high)}"/><polyline fill="none" stroke="#1f77b4" stroke-width="2" points="{points(dd_s,390,120,dlow,0)}"/><polyline fill="none" stroke="#ff7f0e" stroke-width="2" points="{points(dd_b,390,120,dlow,0)}"/><text x="55" y="545" font-family="sans-serif" font-size="12">Blue: momentum; orange: equal-weight benchmark. Current-universe survivorship-biased discovery.</text></svg>'
    path.write_text(content)


def run(repo: Path, root: Path, db: Path) -> dict[str, Any]:
    guards(repo)
    marker = root / "formal_run_started.json"
    if marker.exists():
        raise Blocked("formal_run_already_started")
    dump(marker, {"started_at": datetime.now(UTC).isoformat(), "script_sha256": sha(Path(__file__)), "contract_sha256": CONTRACT_SHA, "db_sha256": sha(db)})
    identity = json.loads((root / "qualified_identity.json").read_text())
    symbols = identity["symbols"]
    with duckdb.connect(str(db), read_only=True) as con:
        rows = con.execute("SELECT symbol,trade_date,adj_close FROM us_equity_research.us_daily_total_return_research WHERE snapshot_id=? ORDER BY trade_date,symbol", [SNAPSHOT]).fetchall()
    prices: dict[str, dict[date, float]] = {}
    for symbol, day, price in rows:
        prices.setdefault(symbol, {})[day] = float(price)
    calendar = sorted(prices["SPY"])
    month_ends = [d for i, d in enumerate(calendar[:-1]) if calendar[i + 1].month != d.month and d >= date(2016, 1, 1)]
    strategy_schedule, benchmark_schedule, held = {}, {}, []
    for formation in month_ends:
        i = calendar.index(formation)
        if i < 252:
            continue
        execution = calendar[i + 1]
        ranked = []
        for symbol in symbols:
            p = prices.get(symbol, {})
            if all(calendar[j] in p for j in (i, i - 21, i - 252)) and execution in p:
                ranked.append((p[calendar[i - 21]] / p[calendar[i - 252]] - 1, symbol))
        ranked.sort(key=lambda x: (-x[0], x[1]))
        if len(ranked) < 30:
            raise Blocked(f"monthly_qualified_below_30:{formation}")
        ranks = {symbol: rank for rank, (_, symbol) in enumerate(ranked, 1)}
        retained = [symbol for symbol in held if ranks.get(symbol, 999) <= 15]
        held = (retained + [symbol for _, symbol in ranked if symbol not in retained])[:10]
        strategy_schedule[execution] = {symbol: 0.1 for symbol in held}
        benchmark_schedule[execution] = {symbol: 1 / len(ranked) for _, symbol in ranked}
    outputs = {}
    for label, schedule in (("strategy", strategy_schedule), ("benchmark", benchmark_schedule)):
        for cost_label, cost in (("base", 0.0015), ("stress", 0.0030)):
            d, e, r, t = simulate(calendar, prices, schedule, cost)
            outputs[f"{label}_{cost_label}"] = {"dates": d, "equity": e, "returns": r, "turnover": t, "metrics": metric(d, e, r)}
    s, b = outputs["strategy_base"], outputs["benchmark_base"]
    signs = {}
    for label, start, end in (("2016-2019", date(2016,1,1), date(2019,12,31)), ("2020-2022", date(2020,1,1), date(2022,12,31)), ("2023-latest", date(2023,1,1), date.max)):
        idx = [i for i, d in enumerate(s["dates"]) if start <= d <= end]
        signs[label] = (s["equity"][idx[-1]] / s["equity"][idx[0]] - b["equity"][idx[-1]] / b["equity"][idx[0]]) > 0
    sm, bm = s["metrics"], b["metrics"]
    stress_excess = outputs["strategy_stress"]["metrics"]["cagr"] - outputs["benchmark_stress"]["metrics"]["cagr"]
    gates = {"cagr_excess": sm["cagr"] > bm["cagr"] + 0.01, "sharpe": sm["sharpe"] >= bm["sharpe"], "drawdown": sm["max_drawdown"] >= bm["max_drawdown"] - 0.05, "stress_excess": stress_excess > 0, "turnover": s["turnover"] <= 2.0, "subperiods": sum(signs.values()) >= 2}
    chart = root / "discovery_equity_drawdown.svg"
    svg_chart(chart, s["dates"], s["equity"], b["equity"])
    result = {"result": "DISCOVERY_PASS" if all(gates.values()) else "DISCOVERY_FAIL", "strategy_candidate_available": False, "survivorship_bias": True, "evaluation": [str(s["dates"][0]), str(s["dates"][-1])], "strategy_base": sm, "benchmark_base": bm, "strategy_stress": outputs["strategy_stress"]["metrics"], "benchmark_stress": outputs["benchmark_stress"]["metrics"], "stress_annualized_excess": stress_excess, "annual_turnover": s["turnover"], "subperiod_relative_positive": signs, "gates": gates, "chart_path": str(chart), "chart_sha256": sha(chart), "current_holdings_output": False, "formal_run_count": 1}
    dump(root / "discovery_result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("smoke", "materialize", "run"))
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--staging", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = {"smoke": smoke, "materialize": materialize, "run": run}[args.phase](args.repo.resolve(), args.staging.resolve(), args.db.resolve()) if args.phase != "smoke" else smoke(args.repo.resolve(), args.staging.resolve())
    except (Blocked, DataWriteError, duckdb.Error, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        result = {"status": "INPUT_BLOCKED", "phase": args.phase, "failure": f"{type(exc).__name__}:{exc}", "strategy_candidate_available": False}
        dump(args.staging / f"{args.phase}_blocked.json", result)
        print(json.dumps(result, sort_keys=True))
        return 2
    print(json.dumps({k: v for k, v in result.items() if k not in {"checks", "receipts"}}, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
