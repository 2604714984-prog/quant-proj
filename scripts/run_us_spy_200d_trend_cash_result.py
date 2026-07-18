#!/usr/bin/env python3
"""Run the frozen SPY 200-session trend/cash baseline exactly once."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import duckdb


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from quant_system.research import us_spy_200d_trend_cash as baseline  # noqa: E402


RESEARCH_ID = "US_SPY_200D_TREND_CASH_RETROSPECTIVE_BASELINE_V1_20260719"
SNAPSHOT_ID = "tiingo_raw_20260711T142010Z_5c24877d23cfc4a0"
TABLE = "us_equity_research.us_daily_total_return_research"
SYMBOL = "SPY"
CUTOFF = date(2026, 6, 30)
DEFINITION = ROOT / "research/definitions/us_spy_200d_trend_cash_retrospective_baseline_v1.json"
MODULE = ROOT / "src/quant_system/research/us_spy_200d_trend_cash.py"
TEST = ROOT / "tests/test_us_spy_200d_trend_cash.py"
RESULT = ROOT / "reports/validation/us_spy_200d_trend_cash_retrospective_baseline_v1_result.json"
RECEIPT = ROOT / "reports/validation/us_spy_200d_trend_cash_retrospective_baseline_v1_run.json"
COMPARATORS = ("B0_CASH", "B1_SPY_BUY_HOLD", "B2_SPY_200D_TREND_CASH")
COSTS = (15, 30)
SPLITS = {
    "development": (date(2000, 1, 1), date(2009, 12, 31)),
    "validation": (date(2010, 1, 1), date(2017, 12, 31)),
    "holdout": (date(2018, 1, 1), CUTOFF),
}
GATE_LABELS = (
    "validation B2 CAGR > 0",
    "holdout B2 CAGR > 0",
    "holdout B2 maximum drawdown is strictly less severe than B1",
    "holdout B2 Calmar is strictly greater than B1",
    "combined validation plus holdout B2 CAGR >= 50 percent of B1 CAGR",
    "combined validation plus holdout B2 time in market is between 20 and 90 percent inclusive",
    "at 30 bps combined validation plus holdout B2 CAGR > 0",
    "zero duplicate missing nonfinite or identity failures",
)


class BaselineRunError(RuntimeError):
    """The frozen result cannot be produced without violating its contract."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(payload: Any) -> bytes:
    return (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        + b"\n"
    )


def _strict_json(path: Path) -> dict[str, Any]:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise BaselineRunError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid_constant(value: str) -> None:
        raise BaselineRunError(f"nonfinite JSON constant: {value}")

    parsed = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=pairs,
        parse_constant=invalid_constant,
    )
    if not isinstance(parsed, dict):
        raise BaselineRunError("definition must be a JSON object")
    return parsed


def _git(*arguments: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT), *arguments], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise BaselineRunError("cannot bind the Git execution identity") from exc


def _locked_code_identity() -> tuple[str, str]:
    if _git("status", "--porcelain=v1", "--untracked-files=all"):
        raise BaselineRunError("worktree must be clean before the one-use result")
    commit = _git("rev-parse", "HEAD")
    tree = _git("rev-parse", "HEAD^{tree}")
    try:
        upstream = _git("rev-parse", "@{upstream}")
    except BaselineRunError as exc:
        raise BaselineRunError("branch must have a configured upstream") from exc
    if upstream != commit:
        raise BaselineRunError("local code commit is not the pushed upstream commit")
    return commit, tree


def _exclusive_write(path: Path, payload: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise BaselineRunError(f"immutable output already exists: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0),
        0o600,
    )
    try:
        written = 0
        while written < len(payload):
            written += os.write(descriptor, payload[written:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _finalize_claim(path: Path, payload: bytes) -> None:
    current = _strict_json(path)
    if current.get("status") != "CLAIMED_RETROSPECTIVE_OUTCOME_RUN":
        raise BaselineRunError("one-use receipt is not the active claim")
    temporary = path.with_name(f".{path.name}.final-{os.getpid()}")
    _exclusive_write(temporary, payload)
    os.replace(temporary, path)


def _validate_definition(definition: dict[str, Any], expected_database_sha256: str) -> None:
    expected = {
        "research_id": RESEARCH_ID,
        "status": "DEFINITION_FROZEN_NOT_EXECUTED",
        "classification": "RETROSPECTIVE_SECONDARY_NOT_STRICT_PIT",
    }
    if any(definition.get(key) != value for key, value in expected.items()):
        raise BaselineRunError("definition identity or frozen state differs")
    identity = definition.get("input_identity")
    if not isinstance(identity, dict):
        raise BaselineRunError("definition input identity is absent")
    required = {
        "database_sha256": expected_database_sha256,
        "table": TABLE,
        "snapshot_id": SNAPSHOT_ID,
        "symbol": SYMBOL,
        "open_field": "adj_open",
        "close_field": "adj_close",
        "required_row_count": 8418,
        "cutoff_inclusive": CUTOFF.isoformat(),
    }
    if any(identity.get(key) != value for key, value in required.items()):
        raise BaselineRunError("definition data identity differs")
    if tuple(definition.get("primary_gates", ())) != GATE_LABELS:
        raise BaselineRunError("definition gate order differs")


def _database_rows(database: Path) -> tuple[tuple[baseline.DailyBar, ...], dict[str, Any]]:
    if not database.is_file() or database.is_symlink():
        raise BaselineRunError("database must be a regular non-symlink file")
    connection = duckdb.connect(str(database), read_only=True)
    try:
        aggregate = connection.execute(
            f"""
            SELECT count(*), min(trade_date), max(trade_date),
                   count(*) - count(DISTINCT trade_date),
                   sum(CASE WHEN adj_open IS NULL OR adj_close IS NULL
                                  OR NOT isfinite(adj_open) OR NOT isfinite(adj_close)
                                  OR adj_open <= 0 OR adj_close <= 0
                            THEN 1 ELSE 0 END)
            FROM {TABLE}
            WHERE snapshot_id = ? AND symbol = ?
            """,
            [SNAPSHOT_ID, SYMBOL],
        ).fetchone()
        if aggregate is None:
            raise BaselineRunError("snapshot aggregate query returned no row")
        row_count, start, end, duplicate_count, invalid_count = aggregate
        if (
            row_count != 8418
            or start != date(1993, 1, 29)
            or end != date(2026, 7, 10)
            or duplicate_count != 0
            or invalid_count != 0
        ):
            raise BaselineRunError("SPY snapshot shape or adjusted fields differ")
        rows = connection.execute(
            f"""
            SELECT trade_date, adj_open, adj_close
            FROM {TABLE}
            WHERE snapshot_id = ? AND symbol = ? AND trade_date <= ?
            ORDER BY trade_date
            """,
            [SNAPSHOT_ID, SYMBOL, CUTOFF],
        ).fetchall()
    finally:
        connection.close()
    if not rows:
        raise BaselineRunError("no SPY rows remain before the frozen cutoff")
    digest = hashlib.sha256()
    bars: list[baseline.DailyBar] = []
    for session_date, adj_open, adj_close in rows:
        digest.update(f"{session_date.isoformat()}|{adj_open}|{adj_close}\n".encode())
        bars.append(baseline.DailyBar(session_date, float(adj_open), float(adj_close)))
    return tuple(bars), {
        "snapshot_row_count": row_count,
        "consumed_row_count": len(rows),
        "observed_date_start": start.isoformat(),
        "observed_date_end": end.isoformat(),
        "duplicate_date_count": duplicate_count,
        "missing_or_nonfinite_count": invalid_count,
        "consumed_rows_sha256": digest.hexdigest(),
    }


def _public_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in metrics.items() if not key.startswith("_")}


def _period_results(
    split_intervals: dict[str, tuple[baseline.MonthlyInterval, ...]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    evaluated: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
    public: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
    for split_name, intervals in split_intervals.items():
        evaluated[split_name] = {}
        public[split_name] = {}
        for cost in COSTS:
            cost_key = str(cost)
            evaluated[split_name][cost_key] = {}
            public[split_name][cost_key] = {}
            for comparator in COMPARATORS:
                outcome = baseline.evaluate(intervals, comparator, cost)
                evaluated[split_name][cost_key][comparator] = outcome
                public[split_name][cost_key][comparator] = _public_metrics(outcome)
    public["combined_validation_holdout"] = {}
    evaluated["combined_validation_holdout"] = {}
    for cost in COSTS:
        cost_key = str(cost)
        public["combined_validation_holdout"][cost_key] = {}
        evaluated["combined_validation_holdout"][cost_key] = {}
        for comparator in COMPARATORS:
            outcome = baseline.combine_outcomes(
                (
                    evaluated["validation"][cost_key][comparator],
                    evaluated["holdout"][cost_key][comparator],
                )
            )
            evaluated["combined_validation_holdout"][cost_key][comparator] = outcome
            public["combined_validation_holdout"][cost_key][comparator] = _public_metrics(outcome)
    return evaluated, public


def _adjudication_input(evaluated: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    mapping = {
        "validation": "validation",
        "holdout": "holdout",
        "combined": "combined_validation_holdout",
    }
    for target, source in mapping.items():
        output[target] = {}
        for cost in ("15", "30"):
            output[target][cost] = {
                "B1": evaluated[source][cost]["B1_SPY_BUY_HOLD"],
                "B2": evaluated[source][cost]["B2_SPY_200D_TREND_CASH"],
            }
    return output


def _boundaries() -> dict[str, bool]:
    return {
        "strict_pit_evidence": False,
        "provider_or_network_used": False,
        "database_write_performed": False,
        "prospective_forward_outcomes_opened": False,
        "strategy_candidate_available": False,
        "shadow_authorized": False,
        "paper_authorized": False,
        "broker_authorized": False,
        "live_authorized": False,
        "auto_trading_authorized": False,
    }


def _input_blocked(
    database: Path,
    expected_database_sha256: str,
    commit: str,
    tree: str,
    file_hashes: dict[str, str],
    error: BaseException,
) -> tuple[dict[str, Any], dict[str, Any]]:
    result: dict[str, Any] = {
        "schema_version": "us-spy-200d-trend-cash-retrospective-baseline-result-v1",
        "research_id": RESEARCH_ID,
        "status": "INPUT_BLOCKED",
        "classification": "RETROSPECTIVE_SECONDARY_NOT_STRICT_PIT",
        "reason_class": type(error).__name__,
        "repository_identity": {
            "definition_commit": commit,
            "definition_tree": tree,
            "files_sha256": file_hashes,
        },
        "input_identity": {
            "database_filename": database.name,
            "expected_database_sha256": expected_database_sha256,
            "table": TABLE,
            "snapshot_id": SNAPSHOT_ID,
            "symbol": SYMBOL,
            "cutoff_inclusive": CUTOFF.isoformat(),
        },
        "periods": None,
        "gates": {"passed": None, "total": 8, "items": []},
        "boundaries": _boundaries(),
    }
    result_bytes = _canonical(result)
    receipt = {
        "schema_version": "one-use-retrospective-baseline-run-receipt-v1",
        "research_id": RESEARCH_ID,
        "status": "CONSUMED_RETROSPECTIVE_INPUT_BLOCKED",
        "result_status": "INPUT_BLOCKED",
        "result_sha256": hashlib.sha256(result_bytes).hexdigest(),
        "definition_commit": commit,
        "definition_tree": tree,
        "files_sha256": file_hashes,
        "database_filename": database.name,
        "expected_database_sha256": expected_database_sha256,
        "provider_or_network_used": False,
        "database_write_performed": False,
        "strategy_candidate_available": False,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    return result, receipt


def _run(database: Path, expected_database_sha256: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if RESULT.exists() or RESULT.is_symlink() or RECEIPT.exists() or RECEIPT.is_symlink():
        raise BaselineRunError("one-use result or receipt already exists")
    commit, tree = _locked_code_identity()
    definition = _strict_json(DEFINITION)
    _validate_definition(definition, expected_database_sha256)
    file_hashes = {
        "definition": _sha256(DEFINITION),
        "module": _sha256(MODULE),
        "runner": _sha256(Path(__file__)),
        "tests": _sha256(TEST),
    }
    claim = {
        "schema_version": "one-use-retrospective-baseline-run-receipt-v1",
        "research_id": RESEARCH_ID,
        "status": "CLAIMED_RETROSPECTIVE_OUTCOME_RUN",
        "definition_commit": commit,
        "definition_tree": tree,
        "files_sha256": file_hashes,
        "database_filename": database.name,
        "expected_database_sha256": expected_database_sha256,
        "claimed_at_utc": datetime.now(timezone.utc).isoformat(),
        "strategy_candidate_available": False,
    }
    _exclusive_write(RECEIPT, _canonical(claim))
    try:
        before_wal = database.with_name(database.name + ".wal").exists()
        before_hash = _sha256(database)
        if before_wal or before_hash != expected_database_sha256:
            raise BaselineRunError("database pre-execution identity differs")
        bars, data_identity = _database_rows(database)
        intervals = baseline.build_monthly_intervals(bars, CUTOFF)
        split_intervals = {
            name: baseline.select_split(intervals, start, end)
            for name, (start, end) in SPLITS.items()
        }
        split_intervals["full_post_warmup"] = intervals
        if any(not split_intervals[name] for name in ("validation", "holdout")):
            raise BaselineRunError("a gated split has no complete monthly intervals")
        evaluated, public = _period_results(split_intervals)
        adjudication = baseline.adjudicate(_adjudication_input(evaluated), 0)
        gate_values = tuple(bool(value) for value in adjudication.get("gates", ()))
        if len(gate_values) != len(GATE_LABELS):
            raise BaselineRunError("adjudication did not return the eight frozen gates")
        after_hash = _sha256(database)
        after_wal = database.with_name(database.name + ".wal").exists()
        if after_wal or after_hash != before_hash:
            raise BaselineRunError("read-only database identity changed")
        purged = {
            name: sum(
                (start <= item.entry_date <= end) != (start <= item.exit_date <= end)
                for item in intervals
            )
            for name, (start, end) in SPLITS.items()
        }
    except (OSError, duckdb.Error, BaselineRunError, baseline.SPYTrendCashError) as error:
        return _input_blocked(
            database, expected_database_sha256, commit, tree, file_hashes, error
        )
    result: dict[str, Any] = {
        "schema_version": "us-spy-200d-trend-cash-retrospective-baseline-result-v1",
        "research_id": RESEARCH_ID,
        "status": adjudication["status"],
        "classification": "RETROSPECTIVE_SECONDARY_NOT_STRICT_PIT",
        "repository_identity": {
            "definition_commit": commit,
            "definition_tree": tree,
            "files_sha256": file_hashes,
        },
        "input_identity": {
            "database_filename": database.name,
            "database_sha256_before": before_hash,
            "database_sha256_after": after_hash,
            "database_sha256_before_after_equal": before_hash == after_hash,
            "wal_before": before_wal,
            "wal_after": after_wal,
            "table": TABLE,
            "snapshot_id": SNAPSHOT_ID,
            "symbol": SYMBOL,
            "cutoff_inclusive": CUTOFF.isoformat(),
            **data_identity,
            "purged_boundary_interval_count": purged,
        },
        "periods": public,
        "gates": {
            "passed": sum(gate_values),
            "total": len(gate_values),
            "items": [
                {"order": index, "name": label, "passed": passed}
                for index, (label, passed) in enumerate(zip(GATE_LABELS, gate_values), 1)
            ],
        },
        "boundaries": _boundaries(),
    }
    result_bytes = _canonical(result)
    receipt = {
        "schema_version": "one-use-retrospective-baseline-run-receipt-v1",
        "research_id": RESEARCH_ID,
        "status": "CONSUMED_RETROSPECTIVE_OUTCOME_PUBLISHED",
        "result_status": result["status"],
        "result_sha256": hashlib.sha256(result_bytes).hexdigest(),
        "definition_commit": commit,
        "definition_tree": tree,
        "files_sha256": file_hashes,
        "database_filename": database.name,
        "database_sha256": before_hash,
        "database_unchanged": before_hash == after_hash and not before_wal and not after_wal,
        "provider_or_network_used": False,
        "database_write_performed": False,
        "strategy_candidate_available": False,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    return result, receipt


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--database", type=Path)
    parser.add_argument("--expected-database-sha256")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    if not arguments.execute:
        print(
            json.dumps(
                {
                    "status": "DRY_RUN_NO_OUTCOME",
                    "research_id": RESEARCH_ID,
                    "database_opened": False,
                    "files_written": False,
                    "strategy_candidate_available": False,
                },
                sort_keys=True,
            )
        )
        return 0
    if arguments.database is None or arguments.expected_database_sha256 is None:
        raise BaselineRunError("--execute requires database path and expected SHA-256")
    if len(arguments.expected_database_sha256) != 64:
        raise BaselineRunError("expected database SHA-256 must have 64 hex characters")
    result, receipt = _run(
        arguments.database.resolve(), arguments.expected_database_sha256.lower()
    )
    result_bytes = _canonical(result)
    receipt["result_sha256"] = hashlib.sha256(result_bytes).hexdigest()
    _exclusive_write(RESULT, result_bytes)
    _finalize_claim(RECEIPT, _canonical(receipt))
    print(
        json.dumps(
            {
                "status": result["status"],
                "result_sha256": receipt["result_sha256"],
                "strategy_candidate_available": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
