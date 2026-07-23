"""V0.9 canonicalizes every real post-listing Yahoo row; tiny histories are unresolved."""

from __future__ import annotations

from datetime import UTC, date, datetime
import json
from pathlib import Path
import shutil
from typing import Any

import run_us_current_top50_momentum_discovery_v0 as engine
import run_us_current_top50_momentum_discovery_v0_3_gsd as prior
import run_us_current_top50_data_materialization_v0_7_gsd as v07
import run_us_current_top50_data_materialization_v0_8_gsd as v08


RID = "US_CURRENT_TOP50_DATA_MATERIALIZATION_V0_9_GSD"
CONTRACT_SHA = "70acce4fbefe84703f1ce0f5af447e720365f0fc2384ca43803c642247294dcd"
SNAPSHOT = "US_CURRENT_TOP50_DATA_MATERIALIZATION_V0_9_GSD_20260723"
V08_ROOT = Path("/home/rongyu/workspace/quant-data/staging/us_current_top50_data_materialization_v0_8_gsd")
V08_MANIFEST_SHA = "b67a2920ca849bbfc9789d96afb7498217d29508f601aaf658b8e9a8425bbfe7"
BASE_WRITER_ROWS = v08.BASE_WRITER_ROWS
PRESERVED = {
    "research/definitions/us_current_top50_data_materialization_v0_8_gsd.json": "0d00eea614d345b2d350a34e3be5236c506dbaf17730c0c26b431a355b4e8aee",
    "scripts/run_us_current_top50_data_materialization_v0_8_gsd.py": "77e6b56d7ef44571cf01662d6b69db8a42386f45117aa144a3d838362a54bd82",
    "tests/test_us_current_top50_data_materialization_v0_8_gsd.py": "7fa66103eddc83ef5cd26b22cad4c285cd27bcb26046cee8acec462116b7fa58",
    "research/results/us_current_top50_data_materialization_v0_8_gsd_input_blocked_20260723.json": "43014d497c91e58e642960eeeebadd6b7d489dd501f86715e92e7c510994203b",
}


def guards(repo: Path) -> None:
    contract = repo / "research/definitions/us_current_top50_data_materialization_v0_9_gsd.json"
    if engine.sha(contract) != CONTRACT_SHA:
        raise engine.Blocked("v0_9_contract_sha_changed")
    for relative, expected in PRESERVED.items():
        if engine.sha(repo / relative) != expected:
            raise engine.Blocked(f"preserved_v0_8_byte_changed:{relative}")
    manifest_path = V08_ROOT / "evidence_manifest.json"
    if engine.sha(manifest_path) != V08_MANIFEST_SHA:
        raise engine.Blocked("preserved_v0_8_manifest_changed")
    manifest = json.loads(manifest_path.read_text())
    for relative, identity in manifest["files"].items():
        path = V08_ROOT / relative
        if path.stat().st_size != identity["bytes"] or engine.sha(path) != identity["sha256"]:
            raise engine.Blocked(f"preserved_v0_8_staging_changed:{relative}")
    for relative, expected in prior.SOURCE_HASHES.items():
        if engine.sha(prior.GSD_REPO / relative) != expected:
            raise engine.Blocked(f"pinned_source_changed:{relative}")


def _reuse(relative: str, root: Path) -> None:
    source, target = V08_ROOT / relative, root / relative
    if not source.exists() or target.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def universe(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    for name in ("raw_52_identity.json", "class_selection.json", "frozen_rows.json"):
        _reuse(f"universe/{name}", root)
    final = json.loads((root / "universe/frozen_rows.json").read_text())
    if len(final) != 50:
        raise engine.Blocked("v0_9_frozen_50_identity")
    return final, {"source": "V0_8_FROZEN_50_IDENTITY", "raw_security_lines": 52, "companies": 50, "selected_security_lines": 50, "identity_sha256": engine.sha(root / "universe/frozen_rows.json")}


def _reuse_symbol(symbol: str, root: Path) -> None:
    for relative in (f"prices/yahoo/{symbol}.json", f"prices/yahoo/{symbol}.json.metadata.json", f"prices/sina/{symbol}.jsonp", f"prices/sina/{symbol}.jsonp.metadata.json"):
        _reuse(relative, root)


def yahoo_rows_any(raw: bytes) -> list[dict[str, Any]]:
    payload = json.loads(raw)
    results = payload.get("chart", {}).get("result") or []
    if not results or results[0].get("meta", {}).get("dataGranularity") != "1d":
        raise engine.Blocked("v0_9_yahoo_not_daily")
    result = results[0]
    timestamps = result.get("timestamp", [])
    quote = result.get("indicators", {}).get("quote", [{}])[0]
    adjusted = result.get("indicators", {}).get("adjclose", [{}])[0].get("adjclose", [])
    rows = []
    for i, timestamp in enumerate(timestamps):
        values = {key: quote.get(key, [None] * len(timestamps))[i] for key in ("open", "high", "low", "close", "volume")}
        if i >= len(adjusted) or adjusted[i] is None or values["close"] is None or values["volume"] is None:
            continue
        day = datetime.fromtimestamp(timestamp, UTC).date()
        if date(2015, 1, 1) <= day <= date(2026, 7, 22):
            rows.append({"date": day, **values, "adj_close": adjusted[i]})
    if not rows or any(float(row["close"]) <= 0 or float(row["adj_close"]) <= 0 for row in rows):
        raise engine.Blocked(f"v0_9_no_valid_yahoo_history:{len(rows)}")
    return rows


def yahoo_history(symbol: str, root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _reuse_symbol(symbol, root)
    path = root / "prices/yahoo" / f"{symbol}.json"
    url = f"{prior.YAHOO_CHART}/{symbol}"
    params = {"period1": 1420070400, "period2": 1784764800, "interval": "1d", "events": "div,splits", "includeAdjustedClose": "true"}
    identity = {"url": url, "params": params, "source_function": "stock_kline_yahoo_explicit_period_v0_7"}
    meta = prior._cached(path, identity)
    if meta is None:
        response = v07.v06.requests.get(url, params=params, headers={"User-Agent": prior.GSD_UA}, timeout=30)
        meta = prior._write_response(path, response, identity)
    if meta["status"] != 200:
        raise engine.Blocked(f"v0_9_yahoo_http_failure:{symbol}:{meta['status']}")
    return yahoo_rows_any(path.read_bytes()), meta


def crosscheck_any(primary: list[dict[str, Any]], other: dict[date, float]) -> dict[str, Any]:
    common = [(row, other[row["date"]]) for row in primary if row["date"] in other]
    tiny = len(primary) < 20
    short = 20 <= len(primary) < 60
    if len(primary) >= 60:
        common, minimum = common[-120:], 60
    elif short:
        minimum = 20
    else:
        minimum = 0
    observations = []
    for row, sina_close in common:
        yahoo_close = float(row["close"])
        observations.append((row["date"], yahoo_close, sina_close, abs(yahoo_close / sina_close - 1)))
    pass_ratio = sum(item[3] <= 0.005 for item in observations) / len(observations) if observations else 0.0
    sufficient = not tiny and len(observations) >= minimum
    qualified = sufficient and pass_ratio > 0.98
    conflicts = [{"date": str(day), "yahoo_close": yahoo, "sina_close": sina, "relative_difference": difference} for day, yahoo, sina, difference in observations if difference > 0.005]
    return {
        "overlap": len(observations),
        "pass_ratio": pass_ratio,
        "passed": qualified,
        "crosscheck_status": "QUALIFIED" if qualified else "UNRESOLVED",
        "qualification_reason": "INSUFFICIENT_LT20_HISTORY" if tiny else ("CROSSCHECK_PASS" if qualified else "CROSSCHECK_CONFLICT_OR_INSUFFICIENT_COMMON"),
        "conflicts": conflicts,
        "short_history": len(primary) < 60,
        "history_first_date": str(primary[0]["date"]),
        "history_row_count": len(primary),
    }


def sina_history_any(symbol: str, root: Path) -> tuple[dict[date, float], dict[str, Any]]:
    _reuse_symbol(symbol, root)
    path = root / "prices/sina" / f"{symbol}.jsonp"
    params = {"symbol": symbol.upper(), "num": 120}
    identity = {"url": v07.v06.SINA_URL, "params": params, "source_function": "us_stock_kline_sina"}
    meta = prior._cached(path, identity)
    if meta is None:
        response = v07.v06.requests.get(v07.v06.SINA_URL, params=params, headers={"Referer": "https://finance.sina.com.cn/"}, timeout=15)
        meta = prior._write_response(path, response, identity)
    if meta["status"] != 200:
        return {}, {**meta, "parse_status": "HTTP_FAILURE"}
    try:
        return v07.sina_rows_short_ok(path.read_bytes()), {**meta, "parse_status": "PARSED"}
    except engine.Blocked:
        return {}, {**meta, "parse_status": "INVALID_JSONP_UNRESOLVED"}


def acquire_symbol(symbol: str, root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows, yahoo_meta = yahoo_history(symbol, root)
    sina, sina_meta = sina_history_any(symbol, root)
    check = crosscheck_any(rows, sina)
    return rows, {"symbol": symbol, "yahoo": yahoo_meta, "sina": sina_meta, "crosscheck": check}


def writer_rows(symbol: str, rows: list[dict[str, Any]], meta: dict[str, Any]) -> list[dict[str, Any]]:
    result = BASE_WRITER_ROWS(symbol, rows, meta)
    check = meta["crosscheck"]
    flags = {key: check[key] for key in ("crosscheck_status", "qualification_reason", "overlap", "pass_ratio", "short_history", "history_first_date", "history_row_count", "conflicts")}
    quality = "RESEARCH_CANONICAL_CROSSCHECK_QUALIFIED" if check["passed"] else "RESEARCH_CANONICAL_CROSSCHECK_UNRESOLVED"
    for row in result:
        row["quality_status"] = quality
        row["conflict_flags_json"] = json.dumps({"sina_crosscheck": flags}, sort_keys=True)
        row["row_sha256"] = engine.row_hash({key: value for key, value in row.items() if key != "row_sha256"})
    return result


def materialize(repo: Path, root: Path, db: Path) -> dict[str, Any]:
    return v08.materialize(repo, root, db)


def configure() -> None:
    prior.configure()
    v08.SNAPSHOT = SNAPSHOT
    v08.guards = guards
    v08.acquire_symbol = acquire_symbol
    v08.writer_rows = writer_rows
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
