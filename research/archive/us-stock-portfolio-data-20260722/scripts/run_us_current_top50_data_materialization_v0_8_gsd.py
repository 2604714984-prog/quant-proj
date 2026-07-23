"""V0.8 publishes Yahoo canonical rows while quarantining unresolved cross-checks."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import shutil
from typing import Any

import duckdb

import run_us_current_top50_momentum_discovery_v0 as engine
import run_us_current_top50_momentum_discovery_v0_3_gsd as prior
import run_us_current_top50_data_materialization_v0_7_gsd as v07


RID = "US_CURRENT_TOP50_DATA_MATERIALIZATION_V0_8_GSD"
CONTRACT_SHA = "0d00eea614d345b2d350a34e3be5236c506dbaf17730c0c26b431a355b4e8aee"
SNAPSHOT = "US_CURRENT_TOP50_DATA_MATERIALIZATION_V0_8_GSD_20260723"
BASE_DB_SHA = "513e5417650dbc4876537a9ad75e36695e28cb4f408a93201a72b970b2cd979c"
V07_ROOT = Path("/home/rongyu/workspace/quant-data/staging/us_current_top50_data_materialization_v0_7_gsd")
V07_MANIFEST_SHA = "5df3f6137a111a2a2200b1527c0cc005a2807ad9c62a1f1f05a45e91703dc295"
BASE_WRITER_ROWS = v07.BASE_WRITER_ROWS
PRESERVED = {
    "research/definitions/us_current_top50_data_materialization_v0_7_gsd.json": "9ea0395dc4528a2ec0bc30b1e5230893c6b228cd316ebfbb56ab9403c33176a3",
    "scripts/run_us_current_top50_data_materialization_v0_7_gsd.py": "5b777d293f7c74771cf644bf53f77534c09b406d2a468b01780c4a6a51419208",
    "tests/test_us_current_top50_data_materialization_v0_7_gsd.py": "639a458ccfecdfd8c1f50a5fbed3ca1d9d35a4947d67d33f14363bce15d955b8",
    "research/results/us_current_top50_data_materialization_v0_7_gsd_input_blocked_20260723.json": "9998d11b17070336e634e25721434a958f65bee032f50340d17aae6aa403e210",
}


def guards(repo: Path) -> None:
    contract = repo / "research/definitions/us_current_top50_data_materialization_v0_8_gsd.json"
    if engine.sha(contract) != CONTRACT_SHA:
        raise engine.Blocked("v0_8_contract_sha_changed")
    for relative, expected in PRESERVED.items():
        if engine.sha(repo / relative) != expected:
            raise engine.Blocked(f"preserved_v0_7_byte_changed:{relative}")
    manifest_path = V07_ROOT / "evidence_manifest.json"
    if engine.sha(manifest_path) != V07_MANIFEST_SHA:
        raise engine.Blocked("preserved_v0_7_manifest_changed")
    manifest = json.loads(manifest_path.read_text())
    for relative, identity in manifest["files"].items():
        path = V07_ROOT / relative
        if path.stat().st_size != identity["bytes"] or engine.sha(path) != identity["sha256"]:
            raise engine.Blocked(f"preserved_v0_7_staging_changed:{relative}")
    for relative, expected in prior.SOURCE_HASHES.items():
        if engine.sha(prior.GSD_REPO / relative) != expected:
            raise engine.Blocked(f"pinned_source_changed:{relative}")


def _reuse(relative: str, root: Path) -> None:
    source = V07_ROOT / relative
    target = root / relative
    if not source.exists() or target.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def universe(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    for name in ("raw_52_identity.json", "class_selection.json", "frozen_rows.json"):
        _reuse(f"universe/{name}", root)
    final = json.loads((root / "universe/frozen_rows.json").read_text())
    if len(final) != 50 or len({prior.company_id(str(row["name"])) for row in final}) != 50:
        raise engine.Blocked("v0_8_frozen_50_identity")
    return final, {
        "source": "V0_7_FROZEN_50_IDENTITY",
        "raw_security_lines": 52,
        "companies": 50,
        "selected_security_lines": 50,
        "identity_sha256": engine.sha(root / "universe/frozen_rows.json"),
    }


def _reuse_symbol(symbol: str, root: Path) -> None:
    for relative in (
        f"prices/yahoo/{symbol}.json",
        f"prices/yahoo/{symbol}.json.metadata.json",
        f"prices/sina/{symbol}.jsonp",
        f"prices/sina/{symbol}.jsonp.metadata.json",
    ):
        _reuse(relative, root)


def crosscheck_unresolved(primary: list[dict[str, Any]], other: dict[engine.date, float]) -> dict[str, Any]:
    common = [(row, other[row["date"]]) for row in primary if row["date"] in other]
    short = 20 <= len(primary) < 60
    if len(primary) >= 60:
        common, minimum = common[-120:], 60
    elif short:
        minimum = 20
    else:
        raise engine.Blocked(f"v0_8_yahoo_sessions_below_20:{len(primary)}")
    if len(common) < minimum:
        raise engine.Blocked(f"v0_8_common_sessions_below_{minimum}:{len(common)}")
    observations = []
    for row, other_close in common:
        yahoo_close = float(row["close"])
        difference = abs(yahoo_close / other_close - 1)
        observations.append((row["date"], yahoo_close, other_close, difference))
    pass_ratio = sum(item[3] <= 0.005 for item in observations) / len(observations)
    conflicts = [
        {"date": str(day), "yahoo_close": yahoo, "sina_close": sina, "relative_difference": difference}
        for day, yahoo, sina, difference in observations
        if difference > 0.005
    ]
    qualified = pass_ratio > 0.98
    return {
        "overlap": len(observations),
        "pass_ratio": pass_ratio,
        "passed": qualified,
        "crosscheck_status": "QUALIFIED" if qualified else "UNRESOLVED",
        "conflicts": conflicts,
        "short_history": short,
        "history_first_date": str(primary[0]["date"]),
        "history_row_count": len(primary),
    }


def acquire_symbol(symbol: str, root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _reuse_symbol(symbol, root)
    rows, yahoo_meta = v07.yahoo_history(symbol, root)
    sina, sina_meta = v07.sina_history(symbol, root)
    check = crosscheck_unresolved(rows, sina)
    return rows, {"symbol": symbol, "yahoo": yahoo_meta, "sina": sina_meta, "crosscheck": check}


def writer_rows(symbol: str, rows: list[dict[str, Any]], meta: dict[str, Any]) -> list[dict[str, Any]]:
    result = BASE_WRITER_ROWS(symbol, rows, meta)
    check = meta["crosscheck"]
    flags = {
        "crosscheck_status": check["crosscheck_status"],
        "provider": "SINA_US_DAILY_KLINE",
        "common_sessions": check["overlap"],
        "pass_ratio": check["pass_ratio"],
        "short_history": check["short_history"],
        "history_first_date": check["history_first_date"],
        "history_row_count": check["history_row_count"],
        "conflicts": check["conflicts"],
    }
    quality = "RESEARCH_CANONICAL_CROSSCHECK_QUALIFIED" if check["passed"] else "RESEARCH_CANONICAL_CROSSCHECK_UNRESOLVED"
    for row in result:
        row["quality_status"] = quality
        row["conflict_flags_json"] = json.dumps(flags, sort_keys=True)
        row["row_sha256"] = engine.row_hash({key: value for key, value in row.items() if key != "row_sha256"})
    return result


def _metadata_rows(final: list[dict[str, Any]], evidence: dict[str, dict[str, Any]], root: Path) -> list[dict[str, Any]]:
    observed = datetime.now(UTC)
    universe_sha = engine.sha(root / "universe/frozen_rows.json")
    rows = []
    for item in final:
        symbol = str(item["symbol"])
        unresolved = not evidence[symbol]["crosscheck"]["passed"]
        row = {
            "snapshot_id": SNAPSHOT,
            "symbol": symbol,
            "name": item["name"],
            "exchange_code": None,
            "description": "CURRENT_TOP50_FIXED_HISTORY;CROSSCHECK_" + ("UNRESOLVED" if unresolved else "QUALIFIED"),
            "start_date": None,
            "end_date": None,
            "source_url": engine.OFFICIAL,
            "source_document_sha256": universe_sha,
            "observed_at": observed,
            "available_at": observed,
            "availability_basis": "CURRENT_SNAPSHOT_SURVIVORSHIP_BIASED_NOT_PIT",
            "row_sha256": "",
            "quality_status": "RESEARCH_CANONICAL_CROSSCHECK_UNRESOLVED" if unresolved else "RESEARCH_CANONICAL_CROSSCHECK_QUALIFIED",
            "synthetic_data": False,
        }
        row["row_sha256"] = engine.row_hash({key: value for key, value in row.items() if key != "row_sha256"})
        rows.append(row)
    return rows


def _isolated_test(db: Path, isolated: Path, batches: list[tuple[str, list[dict[str, Any]], tuple[str, ...], str]]) -> None:
    shutil.copy2(db, isolated)
    for target, rows, keys, source_sha in batches:
        table = "us_security_metadata_research" if target == "security" else "us_daily_total_return_research"
        batch_id = f"{SNAPSHOT}:{target}"
        first = engine.append_rows(isolated, schema="us_equity_research", table=table, natural_keys=keys, rows=rows, batch_id=batch_id, source_sha256=source_sha, max_rows=1_000_000)
        replay = engine.append_rows(isolated, schema="us_equity_research", table=table, natural_keys=keys, rows=rows, batch_id=batch_id, source_sha256=source_sha, max_rows=1_000_000)
        if first.inserted_rows != len(rows) or replay.existing_rows != len(rows):
            raise engine.Blocked(f"v0_8_isolated_idempotency_failed:{target}")
        conflict = dict(rows[0])
        if target == "security":
            conflict["description"] = str(conflict["description"]) + ";CONFLICT_TEST"
        else:
            conflict["close"] = float(conflict["close"]) * 1.01
        conflict["row_sha256"] = engine.row_hash({key: value for key, value in conflict.items() if key != "row_sha256"})
        try:
            engine.append_rows(isolated, schema="us_equity_research", table=table, natural_keys=keys, rows=[conflict], batch_id=f"{batch_id}:conflict-test", source_sha256=engine.row_hash(conflict), max_rows=1_000_000)
        except engine.DataWriteError:
            pass
        else:
            raise engine.Blocked(f"v0_8_isolated_conflict_not_rejected:{target}")


def materialize(repo: Path, root: Path, db: Path) -> dict[str, Any]:
    guards(repo)
    if engine.sha(db) != BASE_DB_SHA:
        raise engine.Blocked("v0_8_central_db_baseline_changed")
    if json.loads((root / "smoke_result.json").read_text())["status"] != "SMOKE_PASS":
        raise engine.Blocked("v0_8_smoke_not_passed")
    final = json.loads((root / "universe/frozen_rows.json").read_text())
    symbols = [str(row["symbol"]) for row in final] + ["SPY", "XLG"]
    if len(symbols) != 52 or len(set(symbols)) != 52:
        raise engine.Blocked("v0_8_canonical_symbol_identity")
    histories, evidence, unresolved = {}, {}, []
    for symbol in symbols:
        histories[symbol], evidence[symbol] = acquire_symbol(symbol, root)
        if not evidence[symbol]["crosscheck"]["passed"]:
            unresolved.append(symbol)
    if len(unresolved) > 5:
        raise engine.Blocked(f"v0_8_unresolved_symbols:{len(unresolved)}")
    inspections = [
        {"symbol": symbol, "conflicts": evidence[symbol]["crosscheck"]["conflicts"]}
        for symbol in unresolved[:3]
    ]
    qualified_stocks = [str(row["symbol"]) for row in final if str(row["symbol"]) not in unresolved]
    if len(qualified_stocks) < 30:
        raise engine.Blocked("v0_8_fewer_than_30_qualified_stocks")
    metadata = _metadata_rows(final, evidence, root)
    all_bars = [bar for symbol in symbols for bar in writer_rows(symbol, histories[symbol], evidence[symbol])]
    engine.dump(root / "full_staging_validation.json", {"status": "PASS", "canonical_symbol_count": 52, "stock_metadata_count": 50, "unresolved_count": len(unresolved), "bounded_inspections": inspections, "checks": {symbol: evidence[symbol]["crosscheck"] for symbol in symbols}})
    engine.dump(root / "qualified_identity.json", {"snapshot_id": SNAPSHOT, "stock_count": len(qualified_stocks), "symbols": qualified_stocks, "unresolved_symbols": unresolved})
    engine.dump(root / "canonical_identity.json", {"snapshot_id": SNAPSHOT, "stock_count": 50, "price_symbol_count": 52, "symbols": symbols})
    engine.dump(root / "writer/security_rows.json", metadata)
    engine.dump(root / "writer/bar_rows.json", all_bars)
    security_sha = engine.sha(root / "writer/security_rows.json")
    bars_sha = engine.sha(root / "writer/bar_rows.json")
    batches = [
        ("security", metadata, ("snapshot_id", "symbol"), security_sha),
        ("bars", all_bars, ("snapshot_id", "symbol", "trade_date"), bars_sha),
    ]
    isolated = root / "writer/isolated.duckdb"
    _isolated_test(db, isolated, batches)
    backup = root / "writer/quant_research.preappend.duckdb"
    shutil.copy2(db, backup)
    if engine.sha(backup) != BASE_DB_SHA:
        raise engine.Blocked("v0_8_backup_hash_mismatch")
    receipts = []
    try:
        for target, rows, keys, source_sha in batches:
            table = "us_security_metadata_research" if target == "security" else "us_daily_total_return_research"
            receipt = engine.append_rows(db, schema="us_equity_research", table=table, natural_keys=keys, rows=rows, batch_id=f"{SNAPSHOT}:{target}", source_sha256=source_sha, max_rows=1_000_000)
            receipts.append(receipt.to_dict())
        with duckdb.connect(str(db), read_only=True) as connection:
            metadata_count = connection.execute("SELECT count(*) FROM us_equity_research.us_security_metadata_research WHERE snapshot_id=?", [SNAPSHOT]).fetchone()[0]
            bar_count = connection.execute("SELECT count(*) FROM us_equity_research.us_daily_total_return_research WHERE snapshot_id=?", [SNAPSHOT]).fetchone()[0]
            price_symbols = connection.execute("SELECT count(DISTINCT symbol) FROM us_equity_research.us_daily_total_return_research WHERE snapshot_id=?", [SNAPSHOT]).fetchone()[0]
            duplicates = connection.execute("SELECT count(*) FROM (SELECT symbol,trade_date,count(*) n FROM us_equity_research.us_daily_total_return_research WHERE snapshot_id=? GROUP BY 1,2 HAVING n>1)", [SNAPSHOT]).fetchone()[0]
            nonfinite = connection.execute("SELECT count(*) FROM us_equity_research.us_daily_total_return_research WHERE snapshot_id=? AND (NOT isfinite(close) OR NOT isfinite(adj_close))", [SNAPSHOT]).fetchone()[0]
            unresolved_rows = connection.execute("SELECT count(*) FROM us_equity_research.us_security_metadata_research WHERE snapshot_id=? AND quality_status='RESEARCH_CANONICAL_CROSSCHECK_UNRESOLVED'", [SNAPSHOT]).fetchone()[0]
        if (metadata_count, bar_count, price_symbols, duplicates, nonfinite, unresolved_rows) != (50, len(all_bars), 52, 0, 0, len([symbol for symbol in unresolved if symbol not in {"SPY", "XLG"}])):
            raise engine.Blocked("v0_8_central_postwrite_validation_failed")
    except Exception:
        shutil.copy2(backup, db)
        raise
    result = {
        "status": "CENTRAL_DATA_READY",
        "snapshot_id": SNAPSHOT,
        "stock_metadata_count": 50,
        "price_symbol_count": 52,
        "qualified_stock_count": len(qualified_stocks),
        "unresolved_count": len(unresolved),
        "bar_rows": len(all_bars),
        "receipts": receipts,
        "security_rows_sha256": security_sha,
        "bar_rows_sha256": bars_sha,
        "backup_sha256": engine.sha(backup),
        "db_sha256": engine.sha(db),
    }
    engine.dump(root / "central_data_receipt.json", result)
    return result


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
