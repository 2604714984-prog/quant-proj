"""V0.5 explicit-period daily Yahoo transport over the pinned GSD adapter."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any

import requests

import run_us_current_top50_momentum_discovery_v0 as engine
import run_us_current_top50_momentum_discovery_v0_3_gsd as prior
import run_us_current_top50_data_materialization_v0_4_gsd as v04


RID = "US_CURRENT_TOP50_DATA_MATERIALIZATION_V0_5_GSD"
CONTRACT_SHA = "2f72bc5bf1ee20123795a75ddb61580e7c61ff4c267874d339bd3e28c33ccbaa"
SNAPSHOT = "US_CURRENT_TOP50_DATA_MATERIALIZATION_V0_5_GSD_20260723"
PERIOD1 = 1420070400
PERIOD2 = 1784764800
V04_ROOT = Path("/home/rongyu/workspace/quant-data/staging/us_current_top50_data_materialization_v0_4_gsd")
PRESERVED = {
    "research/definitions/us_current_top50_data_materialization_v0_4_gsd.json": "42d702a1551002f7cae3ae1eb1c6b63b8a2e8ac705c45960fa901f9426c9dbc2",
    "scripts/run_us_current_top50_data_materialization_v0_4_gsd.py": "1105baa8558a29c507395f671beabc8cabce94c9f77edc6d2aaa9adfe35d7094",
    "tests/test_us_current_top50_data_materialization_v0_4_gsd.py": "085f62ea2b879d7ba9362fd1be6c65a8008e47b26c99ab4ab76e354be54546d8",
    "research/results/us_current_top50_data_materialization_v0_4_gsd_input_blocked_20260723.json": "30aa1f9ab8ddf1cc16b2bdefa711b8ae9f936e0051c8e29b0ad22561f3945227",
}
V04_STAGING = {
    "prices/yahoo/BRK-A.json": "7b8e6f9d507925c7ad4c2f105af6fa2b4c56f3ee2c95a65fb3cd80a71de7eb2d",
    "prices/yahoo/BRK-A.json.metadata.json": "7ee225aca31335c8f71033c0b7a2381d0397f035dd5ba8ae4d68ad99d1495c02",
    "prices/yahoo/BRK-B.json": "5973fc77f4abec32b5f4474a8b764c9533b56eea7df16dd8cb33c3eadcabaa3a",
    "prices/yahoo/BRK-B.json.metadata.json": "dd2e427aedf66fa3d48c6e822d1f7674d48415ba111f4f166d719dcf50c90142",
    "smoke_blocked.json": "8925608ef68d0a1dc05c82ff04f371cb82d9e38d776056e9c0f53b23d2ce79ef",
    "universe/raw_52_identity.json": "4c8b8547daf43b744f7fbcc3633b9302d33740e4e34ffb70f12e67eb33a5ceb7",
}


def guards(repo: Path) -> None:
    contract = repo / "research/definitions/us_current_top50_data_materialization_v0_5_gsd.json"
    if engine.sha(contract) != CONTRACT_SHA:
        raise engine.Blocked("v0_5_contract_sha_changed")
    for relative, expected in PRESERVED.items():
        if engine.sha(repo / relative) != expected:
            raise engine.Blocked(f"preserved_v0_4_byte_changed:{relative}")
    for relative, expected in V04_STAGING.items():
        if engine.sha(V04_ROOT / relative) != expected:
            raise engine.Blocked(f"preserved_v0_4_staging_changed:{relative}")
    for relative, expected in prior.SOURCE_HASHES.items():
        if engine.sha(prior.GSD_REPO / relative) != expected:
            raise engine.Blocked(f"pinned_source_changed:{relative}")


def daily_chart(symbol: str, root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    path = root / "prices/yahoo" / f"{symbol}.json"
    url = f"{prior.YAHOO_CHART}/{symbol}"
    params = {
        "period1": PERIOD1,
        "period2": PERIOD2,
        "interval": "1d",
        "events": "div,splits",
        "includeAdjustedClose": "true",
    }
    identity = {"url": url, "params": params, "source_function": "stock_kline_yahoo_explicit_period_v0_5"}
    meta = prior._cached(path, identity)
    if meta is None:
        response = requests.get(url, params=params, headers={"User-Agent": prior.GSD_UA}, timeout=30)
        meta = prior._write_response(path, response, identity)
    if meta["status"] != 200:
        raise engine.Blocked(f"v0_5_yahoo_http_failure:{symbol}:{meta['status']}")
    payload = json.loads(path.read_bytes())
    results = payload.get("chart", {}).get("result") or []
    if not results or results[0].get("meta", {}).get("dataGranularity") != "1d":
        granularity = results[0].get("meta", {}).get("dataGranularity") if results else None
        raise engine.Blocked(f"v0_5_yahoo_not_daily:{symbol}:{granularity}")
    rows = engine.yahoo_rows(path.read_bytes())
    rows = [row for row in rows if date(2015, 1, 1) <= row["date"] <= date(2026, 7, 22)]
    if not rows or rows[-1]["date"] > date(2026, 7, 22):
        raise engine.Blocked(f"v0_5_yahoo_date_identity:{symbol}")
    return rows, meta


def acquire_symbol(symbol: str, root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows, yahoo_meta = daily_chart(symbol, root)
    stooq_path = root / "prices/stooq" / f"{symbol}.csv"
    stooq_meta = engine.fetch(engine.stooq_url(symbol), stooq_path)
    if stooq_meta["status"] != 200:
        raise engine.Blocked(f"stooq_http_failure:{symbol}:{stooq_meta['status']}")
    check = engine.crosscheck(rows, prior.stooq_rows(stooq_path.read_bytes()))
    return rows, {"symbol": symbol, "yahoo": yahoo_meta, "stooq": stooq_meta, "crosscheck": check}


def universe(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw, source = v04.raw_candidates()
    engine.dump(root / "universe/raw_52_identity.json", {"rows": raw, "source": source})
    final, class_evidence = v04.select_lines(raw, root)
    engine.dump(root / "universe/class_selection.json", class_evidence)
    engine.dump(root / "universe/frozen_rows.json", final)
    return final, {
        "source": "PINNED_GSD_EASTMONEY_MARKET_CAP_EXPLICIT_PERIOD_YAHOO_LIQUIDITY",
        "raw_security_lines": 52,
        "companies": 50,
        "selected_security_lines": 50,
        "multiclass_companies": 2,
        "source_identity": source,
    }


def materialize(repo: Path, root: Path, db: Path) -> dict[str, Any]:
    guards(repo)
    final = json.loads((root / "universe/frozen_rows.json").read_text())
    symbols = [str(row["symbol"]) for row in final] + ["SPY", "XLG"]
    if len(symbols) != 52 or len(set(symbols)) != 52:
        raise engine.Blocked("v0_5_canonical_symbol_identity")
    for symbol in symbols:
        _, check = acquire_symbol(symbol, root)
        if not check["crosscheck"]["passed"]:
            raise engine.Blocked(f"v0_5_canonical_crosscheck_failed:{symbol}")
    return v04.BASE_MATERIALIZE(repo, root, db)


def configure() -> None:
    prior.configure()
    prior._yahoo_chart = daily_chart
    engine.RID = RID
    engine.SNAPSHOT = SNAPSHOT
    engine.CONTRACT_SHA = CONTRACT_SHA
    engine.guards = guards
    engine.universe = universe
    engine.acquire_symbol = acquire_symbol
    engine.materialize = materialize
    engine.company = prior.company_id
    engine.__file__ = __file__


def main() -> int:
    configure()
    return engine.main()


if __name__ == "__main__":
    raise SystemExit(main())
