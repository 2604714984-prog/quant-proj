#!/usr/bin/env python3
"""Run the frozen SPY/QQQ/GLD inverse-volatility sprint exactly once."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from typing import Any
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from quant_system.data.reader import DataReadError, query, sha256_file  # noqa: E402
from quant_system.research import us_spy_qqq_gld_dual_momentum as dm  # noqa: E402
from quant_system.research import us_spy_qqq_gld_inverse_volatility as iv  # noqa: E402
RESEARCH_ID = "US_SPY_QQQ_GLD_INVERSE_VOLATILITY_V1"
DATABASE = Path("/home/rongyu/workspace/quant-data/quant_research.duckdb")
DATABASE_SHA256 = "e636bb80e300f89e46831e91275c6f2167e370e81a00b21b300e253f6107bee0"
DEFINITION_SHA256 = "acf04eb0b2a75a61e9dec83db4b4c763b60402568ef68d74233e52095c95c9f6"
TABLE = "us_equity_research.us_daily_total_return_research"
SNAPSHOT_ID = "tiingo_raw_20260711T142010Z_5c24877d23cfc4a0"
CUTOFF = date(2026, 6, 30)
DEFINITION = ROOT / "research/definitions/us_spy_qqq_gld_inverse_volatility_v1.json"
MODULE = ROOT / "src/quant_system/research/us_spy_qqq_gld_inverse_volatility.py"
TEST = ROOT / "tests/test_us_spy_qqq_gld_inverse_volatility.py"
RESULT = ROOT / "reports/validation/us_spy_qqq_gld_inverse_volatility_v1_result.json"
RECEIPT = ROOT / "reports/validation/us_spy_qqq_gld_inverse_volatility_v1_run.json"
COSTS = (15, 30)
SPLITS = {"development": (date(2006, 1, 1), date(2009, 12, 31)),
          "validation": (date(2010, 1, 1), date(2017, 12, 31)),
          "holdout": (date(2018, 1, 1), CUTOFF)}
COMPARATORS = ("B0_CASH", "B1_SPY_BUY_HOLD", "B2_STATIC_EQUAL_WEIGHT_SPY_QQQ_GLD",
               "B3_DUAL_MOMENTUM_CASH", "B4_INVERSE_VOLATILITY")
GATES = (
    "validation B4 CAGR > 0", "holdout B4 CAGR > 0",
    "validation B4 annualized volatility < B2", "holdout B4 annualized volatility < B2",
    "holdout B4 daily maximum drawdown is less severe than both B1 and B2",
    "holdout B4 Calmar is strictly greater than both B1 and B2",
    "combined B4 CAGR is positive and at least 50 percent of B1 CAGR",
    "combined B4 Calmar is strictly greater than B2 Calmar",
    "at 30 bps combined B4 CAGR > 0, B4 Calmar > B2, and largest calendar-year contribution < 40 percent",
    "all four Holm-adjusted inference tests pass and zero input, cap, full-investment, whole-share, cost, database or output failures",
)


class InverseVolatilityRunError(RuntimeError): ...
def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
def _strict_json(path: Path) -> dict[str, Any]:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise InverseVolatilityRunError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs,
                       parse_constant=lambda item: (_ for _ in ()).throw(InverseVolatilityRunError(f"nonfinite JSON constant: {item}")))
    if not isinstance(value, dict):
        raise InverseVolatilityRunError("definition must be an object")
    return value


def _git(*arguments: str) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(ROOT), *arguments], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise InverseVolatilityRunError("cannot bind Git identity") from exc


def _code_identity() -> tuple[str, str]:
    if _git("status", "--porcelain=v1", "--untracked-files=all"):
        raise InverseVolatilityRunError("worktree must be clean before outcome access")
    commit, tree = _git("rev-parse", "HEAD"), _git("show", "-s", "--format=%T", "HEAD")
    if _git("rev-parse", "@{upstream}") != commit:
        raise InverseVolatilityRunError("local commit must equal configured upstream")
    return commit, tree


def _exclusive(path: Path, payload: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise InverseVolatilityRunError(f"immutable output exists: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0), 0o600)
    try:
        os.write(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _finalize(path: Path, payload: bytes) -> None:
    if _strict_json(path).get("status") != "CLAIMED_RETROSPECTIVE_OUTCOME_RUN":
        raise InverseVolatilityRunError("one-use claim is absent")
    temporary = path.with_name(f".{path.name}.final-{os.getpid()}")
    _exclusive(temporary, payload)
    os.replace(temporary, path)


def _signature(path: Path) -> tuple[int, int, int, int, int]:
    value = path.lstat()
    if not stat.S_ISREG(value.st_mode) or path.is_symlink():
        raise InverseVolatilityRunError("database must be a regular non-symlink file")
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns


def _validate_definition(value: dict[str, Any], expected: str) -> None:
    identity = value.get("input_identity", {})
    required = {"database_path": str(DATABASE), "database_sha256": expected, "table": TABLE,
                "snapshot_id": SNAPSHOT_ID, "symbols": list(iv.SYMBOLS), "cutoff_inclusive": CUTOFF.isoformat()}
    if _sha256(DEFINITION) != DEFINITION_SHA256 or value.get("research_id") != RESEARCH_ID:
        raise InverseVolatilityRunError("definition bytes or identity differ")
    if value.get("status") != "DEFINITION_FROZEN_NOT_EXECUTED" or any(identity.get(key) != item for key, item in required.items()):
        raise InverseVolatilityRunError("definition input identity differs")
    if tuple(value.get("primary_gates", ())) != GATES:
        raise InverseVolatilityRunError("definition gates differ")


def _load(database: Path, signature: tuple[int, ...]) -> tuple[dm.Panel, dict[str, Any]]:
    if _signature(database) != signature:
        raise InverseVolatilityRunError("database identity changed before query")
    result = query(database, f"SELECT trade_date,symbol,open,adj_open,adj_close FROM {TABLE} "
                   "WHERE snapshot_id=? AND symbol IN ('SPY','QQQ','GLD') AND trade_date<=? ORDER BY trade_date,symbol",
                   (SNAPSHOT_ID, CUTOFF), max_rows=30_000)
    if result.truncated or not result.rows or _signature(database) != signature:
        raise InverseVolatilityRunError("snapshot query is empty, truncated or unstable")
    bars = tuple(dm.Bar(day, symbol, float(raw), float(adj_open), float(adj_close))
                 for day, symbol, raw, adj_open, adj_close in result.rows)
    panel = dm.prepare_panel(bars, CUTOFF)
    if panel.dates[-1] != CUTOFF or len(panel.dates) < 62:
        raise InverseVolatilityRunError("common-session cutoff or warm-up is absent")
    digest = hashlib.sha256()
    for row in panel.rows:
        digest.update(f"{row.session_date.isoformat()}|{row.symbol}|{row.raw_open:.17g}|{row.adj_open:.17g}|{row.adj_close:.17g}\n".encode())
    details = {"queried_union_row_count": len(result.rows), "consumed_common_session_count": len(panel.dates),
               "consumed_common_row_count": len(panel.rows), "common_date_start": panel.dates[0].isoformat(),
               "common_date_end": panel.dates[-1].isoformat(), "symbol_date_duplicate_count": 0,
               "missing_nonfinite_nonpositive_count": 0, "consumed_common_sessions_sha256": digest.hexdigest()}
    return panel, details


def _public(value: dict[str, object]) -> dict[str, object]:
    return {key: item for key, item in value.items() if not key.startswith("_")}


def _evaluate(iv_views: dict[str, iv.SplitView], dm_views: dict[str, dm.SplitView]) -> tuple[dict[str, Any], dict[str, Any], tuple[dict[str, object], ...]]:
    internal: dict[str, Any] = {}
    for split in SPLITS:
        internal[split] = {}
        for cost in COSTS:
            key = str(cost)
            internal[split][key] = {name: dm.evaluate(dm_views[split], name, cost) for name in COMPARATORS[:4]}
            internal[split][key]["B4_INVERSE_VOLATILITY"] = iv.evaluate(iv_views[split], cost)
    internal["combined"] = {}
    for cost in COSTS:
        key = str(cost)
        internal["combined"][key] = {name: (iv.combine_outcomes if name == "B4_INVERSE_VOLATILITY" else dm.combine_outcomes)((internal["validation"][key][name], internal["holdout"][key][name])) for name in COMPARATORS}
    tests = []
    for split in ("validation", "holdout"):
        for comparator in ("B1_SPY_BUY_HOLD", "B2_STATIC_EQUAL_WEIGHT_SPY_QQQ_GLD"):
            tests.append(iv.paired_sharpe_test(internal[split]["15"]["B4_INVERSE_VOLATILITY"]["_daily_returns"],
                                               internal[split]["15"][comparator]["_daily_returns"]))
    inference = iv.holm(tests)
    public = {split: {cost: {name: _public(value) for name, value in outcomes.items()}
                      for cost, outcomes in costs.items()} for split, costs in internal.items()}
    return internal, public, inference


def _boundaries() -> dict[str, bool]:
    return {"strict_pit_evidence": False, "provider_or_network_used": False, "database_write_performed": False,
            "prospective_forward_outcomes_opened": False, "strategy_candidate_available": False,
            "shadow_authorized": False, "paper_authorized": False, "broker_authorized": False,
            "live_authorized": False, "auto_trading_authorized": False}


def _blocked(database: Path, expected: str, commit: str, tree: str, files: dict[str, str], error: BaseException, consumed: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    result = {"schema_version": "us-spy-qqq-gld-inverse-volatility-result-v1", "research_id": RESEARCH_ID,
              "status": "INPUT_BLOCKED", "classification": "RETROSPECTIVE_SECONDARY_NOT_STRICT_PIT",
              "reason_class": type(error).__name__, "repository_identity": {"definition_commit": commit, "definition_tree": tree, "files_sha256": files},
              "input_identity": {"database_path": str(database), "expected_database_sha256": expected, "table": TABLE,
                                 "snapshot_id": SNAPSHOT_ID, "cutoff_inclusive": CUTOFF.isoformat()},
              "periods": None, "inference": None, "gates": {"passed": None, "total": 10, "items": []}, "boundaries": _boundaries()}
    result_bytes = _canonical(result)
    receipt = {"schema_version": "one-use-us-inverse-volatility-run-receipt-v1", "research_id": RESEARCH_ID,
               "status": "CONSUMED_RETROSPECTIVE_INPUT_BLOCKED" if consumed else "INPUT_QUALIFICATION_FAILED_NO_OUTCOME_CONSUMED",
               "outcome_run_consumed": consumed, "result_status": "INPUT_BLOCKED",
               "result_sha256": hashlib.sha256(result_bytes).hexdigest(), "definition_commit": commit,
               "definition_tree": tree, "files_sha256": files, "database_path": str(database),
               "expected_database_sha256": expected, "provider_or_network_used": False,
               "database_write_performed": False, "strategy_candidate_available": False,
               "completed_at_utc": datetime.now(timezone.utc).isoformat()}
    return result, receipt


def _run(database: Path, expected: str) -> tuple[dict[str, Any], dict[str, Any], bool]:
    if RESULT.exists() or RESULT.is_symlink() or RECEIPT.exists() or RECEIPT.is_symlink():
        raise InverseVolatilityRunError("one-use result or receipt already exists")
    commit, tree = _code_identity()
    files = {"definition": _sha256(DEFINITION), "module": _sha256(MODULE),
             "runner": _sha256(Path(__file__)), "tests": _sha256(TEST)}
    try:
        _validate_definition(_strict_json(DEFINITION), expected)
        signature, wal = _signature(database), database.with_name(database.name + ".wal")
        before = sha256_file(database)
        if before != expected or wal.exists():
            raise InverseVolatilityRunError("database pre-execution identity differs")
        panel, input_identity = _load(database, signature)
        iv_intervals, dm_intervals = iv.build_intervals(panel), dm.build_intervals(panel)
        iv_views = {name: iv.select_split(panel, iv_intervals, *bounds) for name, bounds in SPLITS.items()}
        dm_views = {name: dm.select_split(panel, dm_intervals, *bounds) for name, bounds in SPLITS.items()}
        if sha256_file(database) != before or wal.exists() or _signature(database) != signature:
            raise InverseVolatilityRunError("database changed during input qualification")
    except (OSError, TypeError, ValueError, DataReadError, InverseVolatilityRunError, iv.InverseVolatilityError, dm.DualMomentumError) as error:
        result, receipt = _blocked(database, expected, commit, tree, files, error, False)
        return result, receipt, False
    claim = {"schema_version": "one-use-us-inverse-volatility-run-receipt-v1", "research_id": RESEARCH_ID,
             "status": "CLAIMED_RETROSPECTIVE_OUTCOME_RUN", "definition_commit": commit,
             "definition_tree": tree, "files_sha256": files, "database_path": str(database),
             "expected_database_sha256": expected, "claimed_at_utc": datetime.now(timezone.utc).isoformat(),
             "strategy_candidate_available": False}
    _exclusive(RECEIPT, _canonical(claim))
    try:
        internal, public, inference = _evaluate(iv_views, dm_views)
        adjudication = iv.adjudicate(internal, inference)
        gates = tuple(bool(value) for value in adjudication.get("gates", ()))
        after = sha256_file(database)
        if len(gates) != 10 or after != before or wal.exists() or _signature(database) != signature:
            raise InverseVolatilityRunError("adjudication or database identity differs")
    except (OSError, TypeError, ValueError, DataReadError, InverseVolatilityRunError, iv.InverseVolatilityError, dm.DualMomentumError) as error:
        result, receipt = _blocked(database, expected, commit, tree, files, error, True)
        return result, receipt, True
    result = {"schema_version": "us-spy-qqq-gld-inverse-volatility-result-v1", "research_id": RESEARCH_ID,
              "status": adjudication["status"], "classification": "RETROSPECTIVE_SECONDARY_NOT_STRICT_PIT",
              "repository_identity": {"definition_commit": commit, "definition_tree": tree, "files_sha256": files},
              "input_identity": {"database_path": str(database), "database_sha256_before": before,
                                 "database_sha256_after": after, "database_unchanged": before == after,
                                 "wal_before_after_absent": not wal.exists(), "table": TABLE, "snapshot_id": SNAPSHOT_ID,
                                 "cutoff_inclusive": CUTOFF.isoformat(), **input_identity},
              "periods": public, "inference": inference, "gates": {"passed": sum(gates), "total": 10,
              "items": [{"order": index, "name": name, "passed": passed} for index, (name, passed) in enumerate(zip(GATES, gates), 1)]},
              "boundaries": _boundaries()}
    result_bytes = _canonical(result)
    receipt = {"schema_version": "one-use-us-inverse-volatility-run-receipt-v1", "research_id": RESEARCH_ID,
               "status": "CONSUMED_RETROSPECTIVE_OUTCOME_PUBLISHED", "outcome_run_consumed": True,
               "result_status": result["status"], "result_sha256": hashlib.sha256(result_bytes).hexdigest(),
               "definition_commit": commit, "definition_tree": tree, "files_sha256": files,
               "database_path": str(database), "database_sha256": before, "database_unchanged": before == after,
               "provider_or_network_used": False, "database_write_performed": False,
               "strategy_candidate_available": False, "completed_at_utc": datetime.now(timezone.utc).isoformat()}
    return result, receipt, True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--database", type=Path)
    parser.add_argument("--expected-database-sha256")
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({"status": "DRY_RUN_NO_OUTCOME", "research_id": RESEARCH_ID,
                          "database_opened": False, "files_written": False,
                          "strategy_candidate_available": False}, sort_keys=True))
        return 0
    if args.database is None or args.expected_database_sha256 is None:
        raise InverseVolatilityRunError("--execute requires database and expected SHA-256")
    database, expected = args.database.resolve(), args.expected_database_sha256.lower()
    if database != DATABASE or expected != DATABASE_SHA256:
        raise InverseVolatilityRunError("database path or expected SHA-256 differs from freeze")
    result, receipt, claimed = _run(database, expected)
    result_bytes = _canonical(result)
    receipt["result_sha256"] = hashlib.sha256(result_bytes).hexdigest()
    _exclusive(RESULT, result_bytes)
    if claimed:
        _finalize(RECEIPT, _canonical(receipt))
    else:
        _exclusive(RECEIPT, _canonical(receipt))
    print(json.dumps({"status": result["status"], "result_sha256": receipt["result_sha256"],
                      "strategy_candidate_available": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
