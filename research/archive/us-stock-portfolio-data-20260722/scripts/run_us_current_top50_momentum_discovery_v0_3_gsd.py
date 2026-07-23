"""Pinned global-stock-data acquisition adapter over the frozen V0 engine."""

from __future__ import annotations

import csv
from datetime import UTC, date, datetime
import io
import json
import os
from pathlib import Path
from typing import Any

import requests

import run_us_current_top50_momentum_discovery_v0 as engine


RID = "US_CURRENT_TOP50_MOMENTUM_DISCOVERY_V0_3_GSD"
CONTRACT_SHA = "6ff104e67479cdcee23eec6116b35b55468320d7ca1e8d10264f5f7a830a86b7"
SNAPSHOT = "US_CURRENT_TOP50_MOMENTUM_DISCOVERY_V0_3_GSD_20260723"
GSD_REPO = Path("/home/rongyu/workspace/quant-data/staging/us_current_top50_momentum_discovery_v0_3_gsd/source/global-stock-data")
GSD_COMMIT = "d52a8a0013363577bceb28ca876c88fe6c1a5aeb"
GSD_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
XLG_SUMMARY = "https://query2.finance.yahoo.com/v10/finance/quoteSummary/XLG"
YAHOO_CHART = "https://query2.finance.yahoo.com/v8/finance/chart"
PRESERVED = {
    "research/definitions/us_current_top50_momentum_discovery_v0_2.json": "f8bd96c27638b99a83a67fb520f427d2902c4fb88eac3fe1ab8e3108fd40cf2e",
    "scripts/run_us_current_top50_momentum_discovery_v0_2.py": "798ee7bc329f96d0608d36bbcc2570fdbc9ca97fe93cf724c511d192dc2e8a2d",
    "tests/test_us_current_top50_momentum_discovery_v0_2.py": "ed96dd3d35f456575bada81d6ff2d9785efa429b48d0d906cc286176d49b237e",
    "research/results/us_current_top50_momentum_discovery_v0_1_input_blocked_20260723.json": "28473d5e9bce69f8e230dc529bf03489bb380dfd6eba0b99b19857fc647f24e1",
    "research/results/us_current_top50_momentum_discovery_v0_input_blocked_20260722.json": "d1995e946caabd9542309da636807a43166b74b44a2adcae7375cdcf55fc244e",
    "research/results/us_stock_top50_input_blocked_20260722.json": "36d0581465ea37d26d695bfaa4e1ca1efbc190880b44148058cd30ba712d0877",
    "research/results/us_sp500_top50_xlg_disclosed_universe_v1_input_blocked_20260722.json": "f7da25e80b6f9aefaab59b74086fcd98f9f8d16265bdfa1b26f7461cf93d58a6",
    "research/results/sec_nport_bulk_zip_v1_smoke_2025q1_input_blocked_20260722.json": "fd401efa9ddcc404fd3e919eae0f83eb24cf4e2a2f8c2a90915f038e419823dd",
}
SOURCE_HASHES = {
    "SKILL.md": "39005851f179f74d970caccfb775bcffb9dd64d2ccedacca5c611fc4ebf101a8",
    "README.md": "1b648cbf70d80be0bb07357b50435a461ca99a8462fe5b29da79559157fd7499",
    "LICENSE": "199bab40163ad21135c2c4d5db43bffdadb14ed80762b048f04931cc48700bbf",
}


def guards(repo: Path) -> None:
    contract = repo / "research/definitions/us_current_top50_momentum_discovery_v0_3_gsd.json"
    if engine.sha(contract) != CONTRACT_SHA:
        raise engine.Blocked("v0_3_contract_sha_changed")
    for relative, expected in PRESERVED.items():
        if engine.sha(repo / relative) != expected:
            raise engine.Blocked(f"preserved_byte_changed:{relative}")
    for relative, expected in SOURCE_HASHES.items():
        if engine.sha(GSD_REPO / relative) != expected:
            raise engine.Blocked(f"pinned_source_changed:{relative}")


def _write_response(path: Path, response: requests.Response, identity: dict[str, Any]) -> dict[str, Any]:
    raw = response.content
    if len(raw) > 20 << 20:
        raise engine.Blocked("gsd_response_too_large")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_bytes(raw)
    os.replace(tmp, path)
    meta = {
        **identity,
        "status": response.status_code,
        "content_type": response.headers.get("content-type"),
        "bytes": len(raw),
        "sha256": engine.sha(path),
        "retrieved_at": datetime.now(UTC).isoformat(),
        "retry_count": 0,
    }
    engine.dump(path.with_suffix(path.suffix + ".metadata.json"), meta)
    return meta


def _cached(path: Path, identity: dict[str, Any]) -> dict[str, Any] | None:
    meta_path = path.with_suffix(path.suffix + ".metadata.json")
    if not meta_path.exists():
        return None
    meta = json.loads(meta_path.read_text())
    if any(meta.get(key) != value for key, value in identity.items()) or engine.sha(path) != meta.get("sha256"):
        raise engine.Blocked(f"staging_identity_conflict:{path}")
    return meta


def _top_holdings(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    path = root / "universe/yahoo_xlg_top_holdings.json"
    identity = {"url": XLG_SUMMARY, "module": "topHoldings", "source_function": "yahoo_quote_summary"}
    meta = _cached(path, identity)
    if meta is None:
        session = requests.Session()
        session.headers["User-Agent"] = GSD_UA
        session.get("https://fc.yahoo.com", timeout=10)
        crumb_response = session.get("https://query2.finance.yahoo.com/v1/test/getcrumb", timeout=10)
        crumb_response.raise_for_status()
        response = session.get(XLG_SUMMARY, params={"modules": "topHoldings", "crumb": crumb_response.text}, timeout=15)
        meta = _write_response(path, response, identity)
    rows: list[dict[str, Any]] = []
    if meta["status"] == 200:
        result = json.loads(path.read_bytes()).get("quoteSummary", {}).get("result") or []
        holdings = result[0].get("topHoldings", {}).get("holdings", []) if result else []
        for item in holdings:
            percent = item.get("holdingPercent")
            weight = percent.get("raw") if isinstance(percent, dict) else percent
            symbol, name = item.get("symbol"), item.get("holdingName")
            if symbol and name:
                rows.append({"symbol": str(symbol).upper().replace(".", "-").replace("_", "-"), "name": str(name), "weight": weight})
    return rows, meta


def _eastmoney_market(root: Path, market: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    path = root / f"universe/eastmoney_{market.replace(':', '_')}_market_cap.json"
    url = "https://push2.eastmoney.com/api/qt/clist/get"
    params = {"fs": market, "fields": "f12,f14,f20", "pn": 1, "pz": 100, "fid": "f20", "po": 1}
    identity = {"url": url, "params": params, "source_function": "market_stock_list"}
    meta = _cached(path, identity)
    if meta is None:
        response = requests.get(url, params=params, timeout=15)
        meta = _write_response(path, response, identity)
    if meta["status"] != 200:
        return [], meta
    data = json.loads(path.read_bytes()).get("data") or {}
    diff = data.get("diff") or []
    if isinstance(diff, dict):
        diff = list(diff.values())
    rows = []
    for item in diff:
        if item.get("f12") and item.get("f14") and isinstance(item.get("f20"), (int, float)) and item["f20"] > 0:
            rows.append({"symbol": str(item["f12"]).upper().replace(".", "-").replace("_", "-"), "name": str(item["f14"]), "weight": None, "market_cap": item["f20"], "market": market})
    return rows, meta


def _valid_identity(rows: list[dict[str, Any]]) -> bool:
    return len(rows) in {50, 51} and len({company_id(str(row["name"])) for row in rows}) == 50


def company_id(name: str) -> str:
    value = engine.re.sub(r"[-_\s]+[ABC]$", "", name.upper()).strip()
    return "".join(character for character in value if character.isalnum())


def universe(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows, primary_meta = _top_holdings(root)
    source, fallback_meta = "YAHOO_QUOTE_SUMMARY_TOP_HOLDINGS", None
    if not _valid_identity(rows):
        nasdaq, nasdaq_meta = _eastmoney_market(root, "m:105")
        nyse, nyse_meta = _eastmoney_market(root, "m:106")
        merged = sorted(nasdaq + nyse, key=lambda row: (-float(row["market_cap"]), str(row["symbol"])))
        companies: list[str] = []
        selected: list[dict[str, Any]] = []
        for row in merged:
            company = company_id(str(row["name"]))
            if company in companies or len(companies) < 50:
                selected.append(row)
                if company not in companies:
                    companies.append(company)
            if len(companies) == 50 and len(selected) >= 51:
                break
        rows, source = selected, "EASTMONEY_PUSH2_TOTAL_MARKET_CAP"
        fallback_meta = {"nasdaq": nasdaq_meta, "nyse": nyse_meta}
    rows = [row for row in rows if engine.re.fullmatch(r"[A-Z][A-Z0-9-]{0,9}", str(row["symbol"]))]
    if not _valid_identity(rows):
        raise engine.Blocked(f"gsd_universe_identity:lines={len(rows)}:companies={len({company_id(str(x['name'])) for x in rows})}")
    engine.dump(root / "universe/frozen_rows.json", rows)
    return rows, {"source": source, "primary": primary_meta, "fallback": fallback_meta, "security_lines": len(rows), "companies": 50, "pinned_commit": GSD_COMMIT}


def _yahoo_chart(symbol: str, root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    path = root / "prices/yahoo" / f"{symbol}.json"
    url = f"{YAHOO_CHART}/{symbol}"
    params = {"interval": "1d", "range": "max"}
    identity = {"url": url, "params": params, "source_function": "stock_kline_yahoo"}
    meta = _cached(path, identity)
    if meta is None:
        response = requests.get(url, params=params, headers={"User-Agent": GSD_UA}, timeout=15)
        meta = _write_response(path, response, identity)
    if meta["status"] != 200:
        raise engine.Blocked(f"yahoo_chart_http_failure:{symbol}:{meta['status']}")
    rows = [row for row in engine.yahoo_rows(path.read_bytes()) if row["date"] >= date(2015, 1, 1)]
    return rows, meta


def stooq_rows(raw: bytes) -> dict[date, float]:
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    rows = {date.fromisoformat(row["Date"]): float(row["Close"]) for row in reader if row.get("Close") not in (None, "", "N/D")}
    if len(rows) < 60:
        raise engine.Blocked("invalid_stooq_history")
    return rows


def acquire_symbol(symbol: str, root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows, yahoo_meta = _yahoo_chart(symbol, root)
    stooq_path = root / "prices/stooq" / f"{symbol}.csv"
    stooq_meta = engine.fetch(engine.stooq_url(symbol), stooq_path)
    if stooq_meta["status"] != 200:
        raise engine.Blocked(f"stooq_http_failure:{symbol}:{stooq_meta['status']}")
    check = engine.crosscheck(rows, stooq_rows(stooq_path.read_bytes()))
    return rows, {"symbol": symbol, "yahoo": yahoo_meta, "stooq": stooq_meta, "crosscheck": check}


def configure() -> None:
    engine.RID = RID
    engine.SNAPSHOT = SNAPSHOT
    engine.OFFICIAL = "https://github.com/simonlin1212/global-stock-data/tree/" + GSD_COMMIT
    engine.CONTRACT_SHA = CONTRACT_SHA
    engine.UA = GSD_UA
    engine.guards = guards
    engine.universe = universe
    engine.acquire_symbol = acquire_symbol
    engine.stooq_rows = stooq_rows
    engine.company = company_id
    engine.__file__ = __file__


def main() -> int:
    configure()
    return engine.main()


if __name__ == "__main__":
    raise SystemExit(main())
