"""V0.7 preserves genuine short post-listing histories under a frozen quality branch."""

from __future__ import annotations

from datetime import UTC, date, datetime
import json
import os
from pathlib import Path
from typing import Any

import run_us_current_top50_momentum_discovery_v0 as engine
import run_us_current_top50_momentum_discovery_v0_3_gsd as prior
import run_us_current_top50_data_materialization_v0_4_gsd as v04
import run_us_current_top50_data_materialization_v0_6_gsd as v06


RID = "US_CURRENT_TOP50_DATA_MATERIALIZATION_V0_7_GSD"
CONTRACT_SHA = "9ea0395dc4528a2ec0bc30b1e5230893c6b228cd316ebfbb56ab9403c33176a3"
SNAPSHOT = "US_CURRENT_TOP50_DATA_MATERIALIZATION_V0_7_GSD_20260723"
V06_ROOT = Path("/home/rongyu/workspace/quant-data/staging/us_current_top50_data_materialization_v0_6_gsd")
V06_MANIFEST_SHA = "d0e8c619559842ce1167b7fb6fa9d014dd9c42060024878c26aa3e2e21e6bb55"
BASE_WRITER_ROWS = v06.BASE_WRITER_ROWS
PRESERVED = {
    "research/definitions/us_current_top50_data_materialization_v0_6_gsd.json": "44ae57d4a7c76d7f55317ba8baf564178787dae94def14cb144cbf4c18e2e84c",
    "scripts/run_us_current_top50_data_materialization_v0_6_gsd.py": "e885d684fbb72a41b3140ed8ac9de8adce5e5e38be1bae3bbb9f393718c0dff2",
    "tests/test_us_current_top50_data_materialization_v0_6_gsd.py": "3f1c458ad4ebbdb7c35dfc164621a29c85489b56d1ca597d4cdc4cadbacc6756",
    "research/results/us_current_top50_data_materialization_v0_6_gsd_input_blocked_20260723.json": "311ff145a313292c8a203d29c4ea4a55c643cc3040147c59aae3ac06d59f45b4",
}


def guards(repo: Path) -> None:
    contract = repo / "research/definitions/us_current_top50_data_materialization_v0_7_gsd.json"
    if engine.sha(contract) != CONTRACT_SHA:
        raise engine.Blocked("v0_7_contract_sha_changed")
    for relative, expected in PRESERVED.items():
        if engine.sha(repo / relative) != expected:
            raise engine.Blocked(f"preserved_v0_6_byte_changed:{relative}")
    manifest_path = V06_ROOT / "evidence_manifest.json"
    if engine.sha(manifest_path) != V06_MANIFEST_SHA:
        raise engine.Blocked("preserved_v0_6_manifest_changed")
    manifest = json.loads(manifest_path.read_text())
    for relative, identity in manifest["files"].items():
        path = V06_ROOT / relative
        if path.stat().st_size != identity["bytes"] or engine.sha(path) != identity["sha256"]:
            raise engine.Blocked(f"preserved_v0_6_staging_changed:{relative}")
    for relative, expected in prior.SOURCE_HASHES.items():
        if engine.sha(prior.GSD_REPO / relative) != expected:
            raise engine.Blocked(f"pinned_source_changed:{relative}")


def _copy_frozen(source: Path, target: Path) -> None:
    raw = source.read_bytes()
    if target.exists():
        if target.read_bytes() != raw:
            raise engine.Blocked(f"frozen_identity_conflict:{target}")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".part")
    temporary.write_bytes(raw)
    os.replace(temporary, target)


def universe(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    for name in ("raw_52_identity.json", "class_selection.json", "frozen_rows.json"):
        _copy_frozen(V06_ROOT / "universe" / name, root / "universe" / name)
    final = json.loads((root / "universe/frozen_rows.json").read_text())
    if len(final) != 50 or len({prior.company_id(str(row["name"])) for row in final}) != 50:
        raise engine.Blocked("v0_7_frozen_50_identity")
    return final, {
        "source": "V0_6_FROZEN_50_IDENTITY",
        "raw_security_lines": 52,
        "companies": 50,
        "selected_security_lines": 50,
        "identity_sha256": engine.sha(root / "universe/frozen_rows.json"),
    }


def yahoo_rows_short_ok(raw: bytes) -> list[dict[str, Any]]:
    payload = json.loads(raw)
    results = payload.get("chart", {}).get("result") or []
    if not results or results[0].get("meta", {}).get("dataGranularity") != "1d":
        raise engine.Blocked("v0_7_yahoo_not_daily")
    result = results[0]
    quote = result.get("indicators", {}).get("quote", [{}])[0]
    adjusted = result.get("indicators", {}).get("adjclose", [{}])[0].get("adjclose", [])
    rows = []
    for i, timestamp in enumerate(result.get("timestamp", [])):
        values = {key: quote.get(key, [None] * len(result["timestamp"]))[i] for key in ("open", "high", "low", "close", "volume")}
        if i >= len(adjusted) or adjusted[i] is None or values["close"] is None or values["volume"] is None:
            continue
        day = datetime.fromtimestamp(timestamp, UTC).date()
        if date(2015, 1, 1) <= day <= date(2026, 7, 22):
            rows.append({"date": day, **values, "adj_close": adjusted[i]})
    if len(rows) < 20 or any(float(row["close"]) <= 0 or float(row["adj_close"]) <= 0 for row in rows):
        raise engine.Blocked(f"v0_7_invalid_yahoo_history:{len(rows)}")
    return rows


def yahoo_history(symbol: str, root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    path = root / "prices/yahoo" / f"{symbol}.json"
    url = f"{prior.YAHOO_CHART}/{symbol}"
    params = {"period1": 1420070400, "period2": 1784764800, "interval": "1d", "events": "div,splits", "includeAdjustedClose": "true"}
    identity = {"url": url, "params": params, "source_function": "stock_kline_yahoo_explicit_period_v0_7"}
    meta = prior._cached(path, identity)
    if meta is None:
        response = v06.requests.get(url, params=params, headers={"User-Agent": prior.GSD_UA}, timeout=30)
        meta = prior._write_response(path, response, identity)
    if meta["status"] != 200:
        raise engine.Blocked(f"v0_7_yahoo_http_failure:{symbol}:{meta['status']}")
    return yahoo_rows_short_ok(path.read_bytes()), meta


def sina_rows_short_ok(raw: bytes) -> dict[date, float]:
    match = v06.re.search(r"\((\[.+\])\)", v06._decode_sina(raw))
    if not match:
        raise engine.Blocked("invalid_sina_jsonp")
    return {date.fromisoformat(item["d"]): float(item["c"]) for item in json.loads(match.group(1)) if item.get("d") and item.get("c") not in (None, "")}


def sina_history(symbol: str, root: Path) -> tuple[dict[date, float], dict[str, Any]]:
    path = root / "prices/sina" / f"{symbol}.jsonp"
    params = {"symbol": symbol.upper(), "num": 120}
    identity = {"url": v06.SINA_URL, "params": params, "source_function": "us_stock_kline_sina"}
    meta = prior._cached(path, identity)
    if meta is None:
        response = v06.requests.get(v06.SINA_URL, params=params, headers={"Referer": "https://finance.sina.com.cn/"}, timeout=15)
        meta = prior._write_response(path, response, identity)
    if meta["status"] != 200:
        raise engine.Blocked(f"sina_http_failure:{symbol}:{meta['status']}")
    return sina_rows_short_ok(path.read_bytes()), meta


def crosscheck_branched(primary: list[dict[str, Any]], other: dict[date, float]) -> dict[str, Any]:
    overlap = [(row["date"], abs(float(row["close"]) / other[row["date"]] - 1)) for row in primary if row["date"] in other]
    short = 20 <= len(primary) < 60
    if len(primary) >= 60:
        overlap, minimum = overlap[-120:], 60
    elif short:
        minimum = 20
    else:
        raise engine.Blocked(f"v0_7_yahoo_sessions_below_20:{len(primary)}")
    if len(overlap) < minimum:
        raise engine.Blocked(f"v0_7_common_sessions_below_{minimum}:{len(overlap)}")
    pass_ratio = sum(diff <= 0.005 for _, diff in overlap) / len(overlap)
    worst = sorted(overlap, key=lambda item: item[1], reverse=True)[:3]
    return {
        "overlap": len(overlap),
        "pass_ratio": pass_ratio,
        "passed": pass_ratio > 0.98,
        "worst": [(str(day), diff) for day, diff in worst],
        "short_history": short,
        "history_first_date": str(primary[0]["date"]),
        "history_row_count": len(primary),
    }


def acquire_symbol(symbol: str, root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows, yahoo_meta = yahoo_history(symbol, root)
    sina, sina_meta = sina_history(symbol, root)
    check = crosscheck_branched(rows, sina)
    return rows, {"symbol": symbol, "yahoo": yahoo_meta, "sina": sina_meta, "crosscheck": check}


def writer_rows(symbol: str, rows: list[dict[str, Any]], meta: dict[str, Any]) -> list[dict[str, Any]]:
    result = BASE_WRITER_ROWS(symbol, rows, meta)
    flags = {key: meta["crosscheck"][key] for key in ("pass_ratio", "overlap", "short_history", "history_first_date", "history_row_count")}
    for row in result:
        row["conflict_flags_json"] = json.dumps({"sina_crosscheck": flags}, sort_keys=True)
        row["row_sha256"] = engine.row_hash({key: value for key, value in row.items() if key != "row_sha256"})
    return result


def materialize(repo: Path, root: Path, db: Path) -> dict[str, Any]:
    guards(repo)
    final = json.loads((root / "universe/frozen_rows.json").read_text())
    symbols = [str(row["symbol"]) for row in final] + ["SPY", "XLG"]
    if len(symbols) != 52 or len(set(symbols)) != 52:
        raise engine.Blocked("v0_7_canonical_symbol_identity")
    checks = {}
    for symbol in symbols:
        _, check = acquire_symbol(symbol, root)
        checks[symbol] = check["crosscheck"]
        if not check["crosscheck"]["passed"]:
            raise engine.Blocked(f"v0_7_canonical_crosscheck_failed:{symbol}")
    engine.dump(root / "full_staging_validation.json", {"status": "PASS", "symbol_count": 52, "checks": checks})
    return v04.BASE_MATERIALIZE(repo, root, db)


def configure() -> None:
    prior.configure()
    engine.RID = RID
    engine.SNAPSHOT = SNAPSHOT
    engine.CONTRACT_SHA = CONTRACT_SHA
    engine.guards = guards
    engine.universe = universe
    engine.acquire_symbol = acquire_symbol
    engine.writer_rows = writer_rows
    engine.materialize = materialize
    engine.company = prior.company_id
    engine.__file__ = __file__


def main() -> int:
    configure()
    return engine.main()


if __name__ == "__main__":
    raise SystemExit(main())
