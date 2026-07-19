#!/usr/bin/env python3
"""Run the frozen classic SPY turn-of-the-month replication exactly once."""

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
from quant_system.research import us_spy_turn_of_month as tom  # noqa: E402


RESEARCH_ID = "US_SPY_CLASSIC_TURN_OF_MONTH_V1_20260719"
DEFINITION_SHA256 = "33f34f88cddb53d3ca4d88fbd1df600f54041c4a3231cdfdd9c3d2283208b9fa"
TABLE = "us_equity_research.us_daily_total_return_research"
CALENDAR_TABLE = "us_equity_research.s2_us_expected_sessions_research"
SNAPSHOT_ID = "tiingo_raw_20260711T142010Z_5c24877d23cfc4a0"
CALENDAR_ID = "XNYS_OFFICIAL_US_EQUITY_20180102_20260706_V1"
CUTOFF = date(2026, 6, 30)
DEFINITION = ROOT / "research/definitions/us_spy_classic_turn_of_month_v1.json"
MODULE = ROOT / "src/quant_system/research/us_spy_turn_of_month.py"
TEST = ROOT / "tests/test_us_spy_turn_of_month.py"
RESULT = ROOT / "reports/validation/us_spy_classic_turn_of_month_v1_result.json"
RECEIPT = ROOT / "reports/validation/us_spy_classic_turn_of_month_v1_run.json"
COMPARATORS = ("B0_CASH", "B1_SPY_BUY_HOLD", "B2_SPY_CLASSIC_TURN_OF_MONTH")
COSTS = (5, 15)
SPLITS = {
    "development": (date(2000, 1, 1), date(2009, 12, 31)),
    "validation": (date(2010, 1, 1), date(2017, 12, 31)),
    "holdout": (date(2018, 1, 1), CUTOFF),
}
EXPECTED_EPISODES = {"development": 119, "validation": 95, "holdout": 101}
GATE_LABELS = (
    "validation B2 net CAGR > 0",
    "holdout B2 net CAGR > 0",
    "validation mean TOM daily return > mean non-TOM daily return",
    "holdout mean TOM daily return > mean non-TOM daily return",
    "combined calendar-month bootstrap 95 percent lower bound of TOM minus non-TOM mean daily return > 0",
    "holdout B2 daily maximum drawdown is less severe than B1 and B2 Calmar > B1",
    "15 bps combined B2 CAGR > 0 and largest year contribution < 40 percent and largest episode contribution < 20 percent",
    "zero session price identity snapshot database or result failures and whole-share validation and holdout CAGR > 0",
)


class TurnOfMonthRunError(RuntimeError):
    """The one-use result cannot be produced without violating the frozen contract."""


def _canonical(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"


def _strict_json(path: Path) -> dict[str, Any]:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise TurnOfMonthRunError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    parsed = json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(
            TurnOfMonthRunError(f"nonfinite JSON constant: {value}")
        ),
    )
    if not isinstance(parsed, dict):
        raise TurnOfMonthRunError("definition must be a JSON object")
    return parsed


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*arguments: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT), *arguments], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise TurnOfMonthRunError("cannot bind Git identity") from exc


def _locked_code_identity() -> tuple[str, str]:
    if _git("status", "--porcelain=v1", "--untracked-files=all"):
        raise TurnOfMonthRunError("worktree must be clean before the one-use result")
    commit, tree = _git("rev-parse", "HEAD"), _git("rev-parse", "HEAD^{tree}")
    if _git("rev-parse", "@{upstream}") != commit:
        raise TurnOfMonthRunError("local code commit is not the pushed upstream commit")
    return commit, tree


def _exclusive_write(path: Path, payload: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise TurnOfMonthRunError(f"immutable output already exists: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0), 0o600
    )
    try:
        written = 0
        while written < len(payload):
            written += os.write(descriptor, payload[written:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _finalize_claim(path: Path, payload: bytes) -> None:
    if _strict_json(path).get("status") != "CLAIMED_RETROSPECTIVE_OUTCOME_RUN":
        raise TurnOfMonthRunError("one-use receipt is not the active claim")
    temporary = path.with_name(f".{path.name}.final-{os.getpid()}")
    _exclusive_write(temporary, payload)
    os.replace(temporary, path)


def _validate_definition(definition: dict[str, Any], database_sha256: str) -> None:
    if _sha256(DEFINITION) != DEFINITION_SHA256:
        raise TurnOfMonthRunError("definition bytes differ from the accepted freeze")
    if (
        definition.get("research_id") != RESEARCH_ID
        or definition.get("status") != "DEFINITION_FROZEN_NOT_EXECUTED"
        or definition.get("input_identity", {}).get("database_sha256") != database_sha256
        or tuple(definition.get("primary_gates", ())) != GATE_LABELS
    ):
        raise TurnOfMonthRunError("definition identity, data hash or gates differ")
    identity = definition["input_identity"]
    expected = {
        "table": TABLE, "snapshot_id": SNAPSHOT_ID, "symbol": "SPY",
        "cutoff_inclusive": CUTOFF.isoformat(), "required_row_count_through_cutoff": 8411,
    }
    if any(identity.get(key) != value for key, value in expected.items()):
        raise TurnOfMonthRunError("definition input contract differs")


def _database_signature(database: Path) -> tuple[int, int, int, int, int]:
    try:
        value = database.lstat()
    except OSError as exc:
        raise TurnOfMonthRunError("database path cannot be inspected") from exc
    if not stat.S_ISREG(value.st_mode):
        raise TurnOfMonthRunError("database must be a regular non-symlink file")
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def _assert_database_signature(database: Path, expected: tuple[int, ...]) -> None:
    if _database_signature(database) != expected:
        raise TurnOfMonthRunError("database path identity changed during the run")


def _load_inputs(
    database: Path, signature: tuple[int, ...]
) -> tuple[tuple[tom.DailyBar, ...], dict[str, Any]]:
    _assert_database_signature(database, signature)
    rows = query(
        database,
        f"SELECT trade_date, close, adj_close FROM {TABLE} "
        "WHERE snapshot_id=? AND symbol='SPY' AND trade_date<=? ORDER BY trade_date",
        (SNAPSHOT_ID, CUTOFF), max_rows=10_000,
    )
    if rows.truncated or len(rows.rows) != 8411:
        raise TurnOfMonthRunError("SPY cutoff row count differs")
    _assert_database_signature(database, signature)
    if any(day is None or raw is None or adj is None for day, raw, adj in rows.rows):
        raise TurnOfMonthRunError("SPY cutoff rows contain missing required values")
    bars = tuple(tom.DailyBar(day, float(raw), float(adj)) for day, raw, adj in rows.rows)
    if bars[0].session_date != date(1993, 1, 29) or bars[-1].session_date != CUTOFF:
        raise TurnOfMonthRunError("SPY cutoff dates differ")
    calendar = query(
        database,
        f"SELECT session_date FROM {CALENDAR_TABLE} "
        "WHERE calendar_contract_id=? AND session_date BETWEEN ? AND ? ORDER BY session_date",
        (CALENDAR_ID, date(2018, 1, 2), CUTOFF), max_rows=3_000,
    )
    calendar_dates = tuple(row[0] for row in calendar.rows)
    _assert_database_signature(database, signature)
    spy_dates = tuple(bar.session_date for bar in bars if bar.session_date >= date(2018, 1, 2))
    if calendar.truncated or len(calendar_dates) != 2134 or calendar_dates != spy_dates:
        raise TurnOfMonthRunError("SPY and frozen XNYS session identities differ")
    digest = hashlib.sha256()
    for bar in bars:
        digest.update(
            f"{bar.session_date.isoformat()}|{bar.raw_close:.17g}|{bar.adj_close:.17g}\n".encode()
        )
    return bars, {
        "consumed_row_count": len(bars), "observed_date_start": bars[0].session_date.isoformat(),
        "observed_date_end": bars[-1].session_date.isoformat(),
        "duplicate_missing_nonfinite_nonpositive_count": 0,
        "consumed_rows_sha256": digest.hexdigest(), "calendar_session_count": len(calendar_dates),
        "calendar_missing_or_extra_session_count": 0,
    }


def _public(item: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in item.items() if not key.startswith("_")}


def _evaluate(views: dict[str, tom.SplitView]) -> tuple[dict[str, Any], dict[str, Any]]:
    internal: dict[str, Any] = {}
    public: dict[str, Any] = {}
    for split, view in views.items():
        internal[split], public[split] = {}, {"daily_return_concentration": _public(tom.label_metrics(tom.daily_labels(view)))}
        for cost in COSTS:
            key = str(cost)
            internal[split][key] = {
                comparator: tom.evaluate(view, comparator, cost) for comparator in COMPARATORS
            }
            public[split][key] = {
                comparator: _public(value) for comparator, value in internal[split][key].items()
            }
    internal["combined"], public["combined"] = {}, {}
    for cost in COSTS:
        key = str(cost)
        internal["combined"][key] = {
            comparator: tom.combine_outcomes(
                (internal["validation"][key][comparator], internal["holdout"][key][comparator])
            ) for comparator in COMPARATORS
        }
        public["combined"][key] = {
            comparator: _public(value) for comparator, value in internal["combined"][key].items()
        }
    return internal, public


def _boundaries() -> dict[str, bool]:
    return {
        "strict_pit_evidence": False, "provider_or_network_used": False,
        "database_write_performed": False, "prospective_forward_outcomes_opened": False,
        "strategy_candidate_available": False, "shadow_authorized": False,
        "paper_authorized": False, "broker_authorized": False,
        "live_authorized": False, "auto_trading_authorized": False,
    }


def _blocked(database: Path, expected_hash: str, commit: str, tree: str,
             files: dict[str, str], error: BaseException) -> tuple[dict[str, Any], dict[str, Any]]:
    result = {
        "schema_version": "us-spy-classic-turn-of-month-result-v1", "research_id": RESEARCH_ID,
        "status": "INPUT_BLOCKED", "classification": "RETROSPECTIVE_SECONDARY_NOT_STRICT_PIT",
        "reason_class": type(error).__name__,
        "repository_identity": {"definition_commit": commit, "definition_tree": tree, "files_sha256": files},
        "input_identity": {"database_filename": database.name, "expected_database_sha256": expected_hash,
                           "table": TABLE, "snapshot_id": SNAPSHOT_ID, "cutoff_inclusive": CUTOFF.isoformat()},
        "periods": None, "gates": {"passed": None, "total": 8, "items": []},
        "boundaries": _boundaries(),
    }
    result_bytes = _canonical(result)
    receipt = {
        "schema_version": "one-use-us-tom-run-receipt-v1", "research_id": RESEARCH_ID,
        "status": "CONSUMED_RETROSPECTIVE_INPUT_BLOCKED", "result_status": "INPUT_BLOCKED",
        "result_sha256": hashlib.sha256(result_bytes).hexdigest(), "definition_commit": commit,
        "definition_tree": tree, "files_sha256": files, "database_filename": database.name,
        "expected_database_sha256": expected_hash, "provider_or_network_used": False,
        "database_write_performed": False, "strategy_candidate_available": False,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    return result, receipt


def _run(database: Path, expected_hash: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if RESULT.exists() or RESULT.is_symlink() or RECEIPT.exists() or RECEIPT.is_symlink():
        raise TurnOfMonthRunError("one-use result or receipt already exists")
    commit, tree = _locked_code_identity()
    definition = _strict_json(DEFINITION)
    _validate_definition(definition, expected_hash)
    database_signature = _database_signature(database)
    files = {"definition": _sha256(DEFINITION), "module": _sha256(MODULE),
             "runner": _sha256(Path(__file__)), "tests": _sha256(TEST)}
    claim = {
        "schema_version": "one-use-us-tom-run-receipt-v1", "research_id": RESEARCH_ID,
        "status": "CLAIMED_RETROSPECTIVE_OUTCOME_RUN", "definition_commit": commit,
        "definition_tree": tree, "files_sha256": files, "database_filename": database.name,
        "expected_database_sha256": expected_hash,
        "claimed_at_utc": datetime.now(timezone.utc).isoformat(),
        "strategy_candidate_available": False,
    }
    _exclusive_write(RECEIPT, _canonical(claim))
    try:
        wal = database.with_name(database.name + ".wal")
        before_hash = sha256_file(database)
        _assert_database_signature(database, database_signature)
        if wal.exists() or before_hash != expected_hash:
            raise TurnOfMonthRunError("database pre-execution identity differs")
        bars, input_identity = _load_inputs(database, database_signature)
        episodes = tom.build_episodes(bars)
        views = {
            name: tom.split_view(
                bars, episodes, *bounds, terminal_censored_t=CUTOFF if name == "holdout" else None
            )
            for name, bounds in SPLITS.items()
        }
        observed_counts = {name: len(view.episodes) for name, view in views.items()}
        if observed_counts != EXPECTED_EPISODES:
            raise TurnOfMonthRunError("split episode counts differ")
        internal, public = _evaluate(views)
        labels = {name: tom.label_metrics(tom.daily_labels(view)) for name, view in views.items()}
        combined_labels = tom.daily_labels(views["validation"]) + tom.daily_labels(views["holdout"])
        lower_bound = tom.bootstrap_lower_bound(combined_labels)
        adjudication = tom.adjudicate(internal, labels, lower_bound)
        gates = tuple(bool(value) for value in adjudication.get("gates", ()))
        if len(gates) != 8:
            raise TurnOfMonthRunError("adjudication did not return eight gates")
        after_hash = sha256_file(database)
        _assert_database_signature(database, database_signature)
        if wal.exists() or after_hash != before_hash:
            raise TurnOfMonthRunError("read-only database identity changed")
    except (OSError, DataReadError, TurnOfMonthRunError, tom.TurnOfMonthError) as error:
        return _blocked(database, expected_hash, commit, tree, files, error)
    result = {
        "schema_version": "us-spy-classic-turn-of-month-result-v1", "research_id": RESEARCH_ID,
        "status": adjudication["status"], "classification": "RETROSPECTIVE_SECONDARY_NOT_STRICT_PIT",
        "repository_identity": {"definition_commit": commit, "definition_tree": tree, "files_sha256": files},
        "input_identity": {"database_filename": database.name, "database_sha256_before": before_hash,
                           "database_sha256_after": after_hash, "database_unchanged": before_hash == after_hash,
                           "wal_before_after_absent": not wal.exists(), "table": TABLE,
                           "snapshot_id": SNAPSHOT_ID, "cutoff_inclusive": CUTOFF.isoformat(),
                           "complete_episode_counts": observed_counts, **input_identity},
        "periods": public,
        "inference": {**_public(tom.label_metrics(combined_labels)),
                      "calendar_month_bootstrap_lower_95_percent": lower_bound,
                      "draws": 10_000, "seed": 20_260_719},
        "gates": {"passed": sum(gates), "total": 8,
                  "items": [{"order": index, "name": name, "passed": passed}
                            for index, (name, passed) in enumerate(zip(GATE_LABELS, gates), 1)]},
        "boundaries": _boundaries(),
    }
    result_bytes = _canonical(result)
    receipt = {
        "schema_version": "one-use-us-tom-run-receipt-v1", "research_id": RESEARCH_ID,
        "status": "CONSUMED_RETROSPECTIVE_OUTCOME_PUBLISHED", "result_status": result["status"],
        "result_sha256": hashlib.sha256(result_bytes).hexdigest(), "definition_commit": commit,
        "definition_tree": tree, "files_sha256": files, "database_filename": database.name,
        "database_sha256": before_hash, "database_unchanged": before_hash == after_hash,
        "provider_or_network_used": False, "database_write_performed": False,
        "strategy_candidate_available": False, "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    return result, receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--database", type=Path)
    parser.add_argument("--expected-database-sha256")
    arguments = parser.parse_args(argv)
    if not arguments.execute:
        print(json.dumps({"status": "DRY_RUN_NO_OUTCOME", "research_id": RESEARCH_ID,
                          "database_opened": False, "files_written": False,
                          "strategy_candidate_available": False}, sort_keys=True))
        return 0
    if arguments.database is None or arguments.expected_database_sha256 is None:
        raise TurnOfMonthRunError("--execute requires database path and expected SHA-256")
    expected_hash = arguments.expected_database_sha256.lower()
    if len(expected_hash) != 64 or any(character not in "0123456789abcdef" for character in expected_hash):
        raise TurnOfMonthRunError("expected database SHA-256 must be 64 lowercase hex characters")
    result, receipt = _run(arguments.database.resolve(), expected_hash)
    result_bytes = _canonical(result)
    receipt["result_sha256"] = hashlib.sha256(result_bytes).hexdigest()
    _exclusive_write(RESULT, result_bytes)
    _finalize_claim(RECEIPT, _canonical(receipt))
    print(json.dumps({"status": result["status"], "result_sha256": receipt["result_sha256"],
                      "strategy_candidate_available": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
