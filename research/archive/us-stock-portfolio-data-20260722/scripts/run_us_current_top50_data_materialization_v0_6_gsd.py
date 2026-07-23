"""V0.6 Yahoo canonical data with pinned GSD Sina daily cross-check."""

from __future__ import annotations

from datetime import date
import json
import os
from pathlib import Path
import re
from typing import Any

import requests

import run_us_current_top50_momentum_discovery_v0 as engine
import run_us_current_top50_momentum_discovery_v0_3_gsd as prior
import run_us_current_top50_data_materialization_v0_4_gsd as v04
import run_us_current_top50_data_materialization_v0_5_gsd as v05


RID = "US_CURRENT_TOP50_DATA_MATERIALIZATION_V0_6_GSD"
CONTRACT_SHA = "44ae57d4a7c76d7f55317ba8baf564178787dae94def14cb144cbf4c18e2e84c"
SNAPSHOT = "US_CURRENT_TOP50_DATA_MATERIALIZATION_V0_6_GSD_20260723"
V05_ROOT = Path("/home/rongyu/workspace/quant-data/staging/us_current_top50_data_materialization_v0_5_gsd")
SINA_URL = "https://stock.finance.sina.com.cn/usstock/api/jsonp.php/var/US_MinKService.getDailyK"
BASE_WRITER_ROWS = engine.writer_rows
PRESERVED = {
    "research/definitions/us_current_top50_data_materialization_v0_5_gsd.json": "2f72bc5bf1ee20123795a75ddb61580e7c61ff4c267874d339bd3e28c33ccbaa",
    "scripts/run_us_current_top50_data_materialization_v0_5_gsd.py": "d1c1f949d08b3ef5f827fc757cbb78cebe4f8ba2b70fd8d2ab453c2cfe334f31",
    "tests/test_us_current_top50_data_materialization_v0_5_gsd.py": "f143aa53f352f65d43ff70cadf64b3b450b59ee41b9cd55f55aa4f3f3886e5a1",
    "research/results/us_current_top50_data_materialization_v0_5_gsd_input_blocked_20260723.json": "208c9c7144933cedf29131f148a195e7e82f046242475fffc56a701bb963f6fb",
}
V05_STAGING = {
    "prices/stooq/AAPL.csv": "39cb5819acc5a7da8ddda288ce3019c8027898309b85e3ec2397f72ce5cd74dc",
    "prices/stooq/AAPL.csv.metadata.json": "08f5706f25916f0f29acda86e6987e2779d5e617f04e8c9286bed60945b9f78f",
    "prices/yahoo/AAPL.json": "984f117783bcf327e3fba37950bdb63f17dcb674554c79f70ed1efa6e4ae767b",
    "prices/yahoo/AAPL.json.metadata.json": "11443c57e438b78801c4f3244449e505b0fb7909c04447e191eae68a303b4c67",
    "prices/yahoo/BRK-A.json": "77e73fc4fe1b8045d395c2560836e5cad6e828611479d5c8422b93af18a1b4df",
    "prices/yahoo/BRK-A.json.metadata.json": "14a4f605916b0d95556a37da04ba1f2e6ea3743e9b0e938cc3bff400d3fff2e8",
    "prices/yahoo/BRK-B.json": "c6b059334affc689efb9d5da0cf0564e993b2d20d56304af15a071e7277b397f",
    "prices/yahoo/BRK-B.json.metadata.json": "993c049fbc86d7a2bfb5653ae778e0c0b671c35c8fbf692c197c1d39983ee3ba",
    "prices/yahoo/GOOG.json": "f982d5c1c328e43cbb607e9bd2ac39c5ea9116e0408c582ada88f0e76a46a3d9",
    "prices/yahoo/GOOG.json.metadata.json": "9584eb72eb54b8d7ad61546eebe3eb366dad32d30e2436a22338f6ede0250e44",
    "prices/yahoo/GOOGL.json": "2a826475d61b8eeff1185831ae99e8164b5a15ea67772a946efcd90aa3861f92",
    "prices/yahoo/GOOGL.json.metadata.json": "1d934bdcbbb638d7c67ad845979fb8ccdd25c662110120f3c88475cceeccaed6",
    "smoke_blocked.json": "51e27c31a737e195e3d1cd73afa6d2479f6b184766fa76b865f16709c9acf61d",
    "universe/class_selection.json": "93935c1dad9b562810031193bc48ebab5f183ff4fe0d7bfa6300aeaa408068bf",
    "universe/frozen_rows.json": "b7d74d1d92fef41b2d685397d4f369be5379c6cf774bed7681fbe882cb5f036f",
    "universe/raw_52_identity.json": "4c8b8547daf43b744f7fbcc3633b9302d33740e4e34ffb70f12e67eb33a5ceb7",
}


def guards(repo: Path) -> None:
    contract = repo / "research/definitions/us_current_top50_data_materialization_v0_6_gsd.json"
    if engine.sha(contract) != CONTRACT_SHA:
        raise engine.Blocked("v0_6_contract_sha_changed")
    for relative, expected in PRESERVED.items():
        if engine.sha(repo / relative) != expected:
            raise engine.Blocked(f"preserved_v0_5_byte_changed:{relative}")
    for relative, expected in V05_STAGING.items():
        if engine.sha(V05_ROOT / relative) != expected:
            raise engine.Blocked(f"preserved_v0_5_staging_changed:{relative}")
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
        _copy_frozen(V05_ROOT / "universe" / name, root / "universe" / name)
    final = json.loads((root / "universe/frozen_rows.json").read_text())
    if len(final) != 50 or len({prior.company_id(str(row["name"])) for row in final}) != 50:
        raise engine.Blocked("v0_6_frozen_50_identity")
    return final, {
        "source": "V0_5_FROZEN_50_IDENTITY",
        "raw_security_lines": 52,
        "companies": 50,
        "selected_security_lines": 50,
        "identity_sha256": engine.sha(root / "universe/frozen_rows.json"),
    }


def _decode_sina(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("gbk")


def sina_rows(raw: bytes) -> dict[date, float]:
    match = re.search(r"\((\[.+\])\)", _decode_sina(raw))
    if not match:
        raise engine.Blocked("invalid_sina_jsonp")
    items = json.loads(match.group(1))
    rows = {}
    for item in items:
        if item.get("d") and item.get("c") not in (None, ""):
            rows[date.fromisoformat(item["d"])] = float(item["c"])
    if len(rows) < 60:
        raise engine.Blocked(f"invalid_sina_history:{len(rows)}")
    return rows


def sina_history(symbol: str, root: Path) -> tuple[dict[date, float], dict[str, Any]]:
    path = root / "prices/sina" / f"{symbol}.jsonp"
    params = {"symbol": symbol.upper(), "num": 120}
    identity = {"url": SINA_URL, "params": params, "source_function": "us_stock_kline_sina"}
    meta = prior._cached(path, identity)
    if meta is None:
        response = requests.get(SINA_URL, params=params, headers={"Referer": "https://finance.sina.com.cn/"}, timeout=15)
        meta = prior._write_response(path, response, identity)
    if meta["status"] != 200:
        raise engine.Blocked(f"sina_http_failure:{symbol}:{meta['status']}")
    return sina_rows(path.read_bytes()), meta


def crosscheck_latest(primary: list[dict[str, Any]], other: dict[date, float]) -> dict[str, Any]:
    overlap = [(row["date"], abs(float(row["close"]) / other[row["date"]] - 1)) for row in primary if row["date"] in other]
    overlap = overlap[-120:]
    if len(overlap) < 60:
        raise engine.Blocked(f"sina_common_sessions_below_60:{len(overlap)}")
    pass_ratio = sum(diff <= 0.005 for _, diff in overlap) / len(overlap)
    worst = sorted(overlap, key=lambda item: item[1], reverse=True)[:3]
    return {"overlap": len(overlap), "pass_ratio": pass_ratio, "passed": pass_ratio >= 0.98, "worst": [(str(day), diff) for day, diff in worst]}


def acquire_symbol(symbol: str, root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows, yahoo_meta = v05.daily_chart(symbol, root)
    sina, sina_meta = sina_history(symbol, root)
    check = crosscheck_latest(rows, sina)
    return rows, {"symbol": symbol, "yahoo": yahoo_meta, "sina": sina_meta, "crosscheck": check}


def writer_rows(symbol: str, rows: list[dict[str, Any]], meta: dict[str, Any]) -> list[dict[str, Any]]:
    result = BASE_WRITER_ROWS(symbol, rows, meta)
    for row in result:
        row["conflict_flags_json"] = json.dumps({"sina_pass_ratio": meta["crosscheck"]["pass_ratio"]}, sort_keys=True)
        row["row_sha256"] = engine.row_hash({key: value for key, value in row.items() if key != "row_sha256"})
    return result


def materialize(repo: Path, root: Path, db: Path) -> dict[str, Any]:
    guards(repo)
    final = json.loads((root / "universe/frozen_rows.json").read_text())
    symbols = [str(row["symbol"]) for row in final] + ["SPY", "XLG"]
    if len(symbols) != 52 or len(set(symbols)) != 52:
        raise engine.Blocked("v0_6_canonical_symbol_identity")
    for symbol in symbols:
        _, check = acquire_symbol(symbol, root)
        if not check["crosscheck"]["passed"]:
            raise engine.Blocked(f"v0_6_canonical_crosscheck_failed:{symbol}")
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
