#!/usr/bin/env python3
"""Run the text-only clean-room replay for rejected US31/36/41/46 lineages."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any

from quant_system.backtest.fixed_weight import GrossFactorRow, run_fixed_weight_backtest
from quant_system.data.reader import DataReadError, query
from quant_system.research.strict_bootstrap import apply_holm, bootstrap_one_sided


ROOT = Path(__file__).resolve().parents[1]
DEFINITION = ROOT / "research/definitions/us_four_cleanroom_replication_v1.json"
DATABASE = Path("/home/rongyu/workspace/quant-data/quant_research.duckdb")
OUTPUT = ROOT / "reports/validation/us_four_cleanroom_replication_v1.json"
DEFINITION_SHA256 = "0e235072fc3d440cd4e5c457d74b0f73741856dbcc46b39f60fafcadba0f08ce"
EXPECTED_COLUMNS = (
    "snapshot_id",
    "symbol",
    "trade_date",
    "gross_return_factor",
    "row_sha256",
    "source_document_sha256",
    "available_at",
    "availability_basis",
    "quality_status",
    "conflict_flags_json",
    "synthetic_data",
)
HEX = frozenset("0123456789abcdef")


class CleanroomReplayError(RuntimeError):
    """Raised when frozen replay inputs or execution conditions do not match."""


def _reject_constant(value: str) -> None:
    raise CleanroomReplayError(f"nonfinite JSON constant is not allowed: {value}")


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CleanroomReplayError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_definition(path: Path = DEFINITION) -> tuple[dict[str, Any], str]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise CleanroomReplayError(f"cannot read definition: {path}") from exc
    digest = hashlib.sha256(raw).hexdigest()
    if digest != DEFINITION_SHA256:
        raise CleanroomReplayError("definition SHA-256 does not match the frozen clean-room spec")
    try:
        parsed = json.loads(
            raw,
            object_pairs_hook=_unique_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CleanroomReplayError("definition is not strict JSON") from exc
    if not isinstance(parsed, dict):
        raise CleanroomReplayError("definition root must be an object")
    if parsed.get("status") != "OUTCOME_BLIND_DEFINITION_NOT_EXECUTED":
        raise CleanroomReplayError("definition is not outcome-blind and unexecuted")
    if parsed.get("classification") != "CLEAN_ROOM_MIGRATION_REPLAY_OF_REJECTED_LINEAGE":
        raise CleanroomReplayError("definition classification changed")
    lineage = parsed.get("lineage_controls")
    if not isinstance(lineage, dict) or any(
        lineage.get(key) is not expected
        for key, expected in (
            ("eligible_for_new_evidence", False),
            ("status_mutation_allowed", False),
            ("strategy_candidate_available", False),
            ("legacy_result_values_permitted_as_test_oracle", False),
            ("legacy_python_permitted_as_implementation_input", False),
        )
    ):
        raise CleanroomReplayError("clean-room lineage boundary changed")
    return parsed, digest


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= HEX


def _is_git_object_id(value: object) -> bool:
    return isinstance(value, str) and len(value) in {40, 64} and set(value) <= HEX


def _consumed_row_bytes(
    *,
    snapshot_id: str,
    symbol: str,
    trade_date: date,
    gross_return_factor: float,
    row_sha256: str,
    source_document_sha256: str,
    available_at: Any,
    availability_basis: str,
    quality_status: str,
    conflict_flags_json: str,
    synthetic_data: bool,
) -> bytes:
    available = None if available_at is None else available_at.isoformat()
    values = (
        snapshot_id,
        symbol,
        trade_date.isoformat(),
        gross_return_factor.hex(),
        row_sha256,
        source_document_sha256,
        available,
        availability_basis,
        quality_status,
        conflict_flags_json,
        synthetic_data,
    )
    return (
        json.dumps(values, ensure_ascii=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("utf-8")


def _load_panel(
    database: Path,
    definition: Mapping[str, Any],
) -> tuple[tuple[date, tuple[tuple[str, float], ...]], ...]:
    identity = definition["data_identity"]
    interval = definition["historical_external_replication"]
    expected_rows = int(identity["row_count"])
    sql = """
        SELECT snapshot_id, symbol, trade_date, gross_return_factor, row_sha256,
               source_document_sha256, available_at, availability_basis,
               quality_status, conflict_flags_json, synthetic_data
        FROM us_equity_research.us_daily_total_return_research
        WHERE snapshot_id = ?
          AND symbol IN (?, ?, ?)
          AND trade_date BETWEEN ? AND ?
        ORDER BY trade_date, symbol
    """
    try:
        result = query(
            database,
            sql,
            (
                identity["snapshot_id"],
                *identity["symbols"],
                interval["start_date"],
                interval["end_date"],
            ),
            max_rows=expected_rows + 1,
        )
    except DataReadError as exc:
        raise CleanroomReplayError("frozen source slice could not be read safely") from exc
    if result.truncated or result.columns != EXPECTED_COLUMNS:
        raise CleanroomReplayError("source query shape or row ceiling changed")
    if len(result.rows) != expected_rows:
        raise CleanroomReplayError("source row count changed")

    expected_symbols = tuple(identity["symbols"])
    grouped: list[tuple[date, tuple[tuple[str, float], ...]]] = []
    digest = hashlib.sha256()
    consumed_digest = hashlib.sha256()
    current_date: date | None = None
    current_factors: list[tuple[str, float]] = []
    per_symbol = {symbol: 0 for symbol in expected_symbols}
    previous_key: tuple[date, str] | None = None

    for raw_row in result.rows:
        (
            snapshot_id,
            symbol,
            trade_date,
            factor,
            row_sha,
            source_sha,
            available_at,
            availability_basis,
            quality_status,
            conflicts,
            synthetic_data,
        ) = raw_row
        if snapshot_id != identity["snapshot_id"]:
            raise CleanroomReplayError("snapshot identity changed")
        if symbol not in per_symbol or type(trade_date) is not date:
            raise CleanroomReplayError("symbol or trade-date type changed")
        key = (trade_date, symbol)
        if previous_key is not None and key <= previous_key:
            raise CleanroomReplayError("source rows are duplicate or out of canonical order")
        previous_key = key
        if isinstance(factor, bool):
            raise CleanroomReplayError("gross return factor must be numeric")
        try:
            normalized_factor = float(factor)
        except (TypeError, ValueError, OverflowError) as exc:
            raise CleanroomReplayError("gross return factor must be numeric") from exc
        if not math.isfinite(normalized_factor) or normalized_factor <= 0.0:
            raise CleanroomReplayError("gross return factor must be finite and positive")
        if not _is_sha256(row_sha) or not _is_sha256(source_sha):
            raise CleanroomReplayError("source or row content hash is invalid")
        if (
            available_at is not None
            or availability_basis != identity["availability_basis"]
            or quality_status != identity["quality_status"]
            or conflicts != identity["conflict_flags_json"]
            or synthetic_data is not identity["synthetic_data"]
        ):
            raise CleanroomReplayError("retrospective-only quality boundary changed")
        digest.update(row_sha.encode("ascii"))
        consumed_digest.update(
            _consumed_row_bytes(
                snapshot_id=snapshot_id,
                symbol=symbol,
                trade_date=trade_date,
                gross_return_factor=normalized_factor,
                row_sha256=row_sha,
                source_document_sha256=source_sha,
                available_at=available_at,
                availability_basis=availability_basis,
                quality_status=quality_status,
                conflict_flags_json=conflicts,
                synthetic_data=synthetic_data,
            )
        )
        per_symbol[symbol] += 1

        if current_date is None:
            current_date = trade_date
        elif trade_date != current_date:
            if tuple(symbol for symbol, _ in current_factors) != expected_symbols:
                raise CleanroomReplayError("a globally required session is incomplete")
            grouped.append((current_date, tuple(current_factors)))
            current_date = trade_date
            current_factors = []
        current_factors.append((symbol, normalized_factor))

    if current_date is None:
        raise CleanroomReplayError("source slice is empty")
    if tuple(symbol for symbol, _ in current_factors) != expected_symbols:
        raise CleanroomReplayError("the final globally required session is incomplete")
    grouped.append((current_date, tuple(current_factors)))

    if digest.hexdigest() != identity["concat_row_sha256"]:
        raise CleanroomReplayError("canonical source-slice row hash changed")
    if consumed_digest.hexdigest() != identity["consumed_slice_sha256"]:
        raise CleanroomReplayError("actual consumed source-slice hash changed")
    if any(count != identity["rows_per_symbol"] for count in per_symbol.values()):
        raise CleanroomReplayError("per-symbol coverage changed")
    if len(grouped) != identity["distinct_trade_dates"]:
        raise CleanroomReplayError("common-session count changed")
    if grouped[0][0].isoformat() != interval["start_date"]:
        raise CleanroomReplayError("first common close changed")
    if grouped[-1][0].isoformat() != interval["end_date"]:
        raise CleanroomReplayError("last common close changed")
    return tuple(grouped)


def _rows_for_symbols(
    panel: Sequence[tuple[date, tuple[tuple[str, float], ...]]],
    symbols: Sequence[str],
) -> tuple[GrossFactorRow, ...]:
    selected = tuple(sorted(symbols))
    rows: list[GrossFactorRow] = []
    for session_date, factors in panel[1:]:
        by_symbol = dict(factors)
        rows.extend(
            GrossFactorRow(session_date, symbol, by_symbol[symbol]) for symbol in selected
        )
    return tuple(rows)


def _metrics(sessions: Sequence[Any]) -> dict[str, float | int | None]:
    returns = tuple(float(session.net_factor) - 1.0 for session in sessions)
    if len(returns) < 2:
        raise CleanroomReplayError("at least two return observations are required")
    terminal = float(sessions[-1].wealth)
    mean = math.fsum(returns) / len(returns)
    variance = math.fsum((value - mean) ** 2 for value in returns) / (len(returns) - 1)
    sharpe = None if variance <= 0.0 else math.sqrt(252.0) * mean / math.sqrt(variance)
    peak = 1.0
    max_drawdown = 0.0
    for session in sessions:
        wealth = float(session.wealth)
        peak = max(peak, wealth)
        max_drawdown = min(max_drawdown, wealth / peak - 1.0)
    return {
        "observation_count": len(returns),
        "terminal_wealth": terminal,
        "total_return": terminal - 1.0,
        "cagr_252": terminal ** (252.0 / len(returns)) - 1.0,
        "sharpe_252_ddof1": sharpe,
        "max_drawdown": max_drawdown,
        "arithmetic_mean_daily_return": mean,
    }


def _session_returns(result: Any) -> tuple[float, ...]:
    return tuple(float(session.net_factor) - 1.0 for session in result.sessions)


def build_report(
    definition: Mapping[str, Any],
    definition_sha256: str,
    panel: Sequence[tuple[date, tuple[tuple[str, float], ...]]],
    *,
    source_commit: str,
) -> dict[str, Any]:
    portfolio = definition["portfolio_contract"]
    inference = definition["inference"]
    strategies: dict[str, Any] = {}
    tests: list[dict[str, Any]] = []
    bootstrap_inputs = []

    spy_rows = _rows_for_symbols(panel, ("SPY",))
    spy_result = run_fixed_weight_backtest(
        spy_rows,
        {"SPY": 1.0},
        rebalance_interval=None,
        cost_bps=0.0,
    )
    spy_returns = _session_returns(spy_result)

    for strategy in sorted(definition["strategies"], key=lambda item: item["order_index"]):
        strategy_id = strategy["strategy_id"]
        weights = strategy["target_weights"]
        rows = _rows_for_symbols(panel, weights)
        buy_hold = run_fixed_weight_backtest(
            rows,
            weights,
            rebalance_interval=None,
            cost_bps=0.0,
        )
        buy_hold_returns = _session_returns(buy_hold)
        cost_runs: dict[str, Any] = {}
        strict_result = None
        for cost_bps in portfolio["cost_bps"]:
            result = run_fixed_weight_backtest(
                rows,
                weights,
                rebalance_interval=portfolio["rebalance_interval_sessions"],
                cost_bps=float(cost_bps),
            )
            cost_runs[str(cost_bps)] = {
                "metrics": _metrics(result.sessions),
                "rebalance_count": sum(session.rebalanced for session in result.sessions),
                "total_turnover": math.fsum(session.turnover for session in result.sessions),
                "total_cost_fraction": math.fsum(
                    session.cost_fraction for session in result.sessions
                ),
            }
            if cost_bps == portfolio["strict_gate_cost_bps"]:
                strict_result = result
        if strict_result is None:
            raise CleanroomReplayError("strict gate cost run is missing")
        strict_returns = _session_returns(strict_result)
        comparator_returns = (spy_returns, buy_hold_returns)
        comparator_ids = ("SPY", "same_constituent_buy_and_hold")
        for comparator_index, (comparator_id, comparison) in enumerate(
            zip(comparator_ids, comparator_returns, strict=True)
        ):
            excess = tuple(
                strategy_return - comparator_return
                for strategy_return, comparator_return in zip(
                    strict_returns, comparison, strict=True
                )
            )
            seed = (
                inference["historical_seed_base"]
                + 10 * strategy["order_index"]
                + comparator_index
            )
            bootstrap = bootstrap_one_sided(
                excess,
                block_length=inference["moving_block_sessions"],
                draws=inference["bootstrap_draws"],
                seed=seed,
                null_mean=0.0,
            )
            bootstrap_inputs.append(bootstrap)
            tests.append(
                {
                    "strategy_id": strategy_id,
                    "comparator_id": comparator_id,
                    "seed": seed,
                    "observed_mean": bootstrap.observed_mean,
                    "raw_p": bootstrap.raw_p,
                }
            )
        strategies[strategy_id] = {
            "target_weights": weights,
            "cost_runs": cost_runs,
            "comparators": {
                "SPY": _metrics(spy_result.sessions),
                "same_constituent_buy_and_hold": _metrics(buy_hold.sessions),
            },
        }

    adjusted = apply_holm(bootstrap_inputs, alpha=inference["look_alpha"])
    for test, result in zip(tests, adjusted, strict=True):
        test.update(
            {
                "holm_rank": result.rank,
                "holm_threshold": result.threshold,
                "adjusted_p": result.adjusted_p,
                "holm_lower_bound": result.lower_bound,
                "test_pass": bool(
                    result.observed_mean > 0.0
                    and result.rejected
                    and result.lower_bound > 0.0
                ),
            }
        )

    strategy_passes = 0
    for strategy_id, payload in strategies.items():
        own_tests = [test for test in tests if test["strategy_id"] == strategy_id]
        passed = len(own_tests) == 2 and all(test["test_pass"] for test in own_tests)
        payload["historical_interval_pass"] = passed
        strategy_passes += int(passed)

    return {
        "schema_version": "us-four-cleanroom-replication-result-v1",
        "definition_id": definition["definition_id"],
        "definition_sha256": definition_sha256,
        "source_commit": source_commit,
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "classification": definition["classification"],
        "source_snapshot_id": definition["data_identity"]["snapshot_id"],
        "source_slice_concat_row_sha256": definition["data_identity"]["concat_row_sha256"],
        "source_slice_consumed_sha256": definition["data_identity"][
            "consumed_slice_sha256"
        ],
        "price_session_count": len(panel),
        "return_observation_count": len(panel) - 1,
        "strict_pit_eligible": False,
        "strategies": strategies,
        "holm_family": tests,
        "historical_strategy_pass_count": strategy_passes,
        "historical_strategy_count": len(strategies),
        "original_status_preserved": "rejected",
        "eligible_for_new_evidence": False,
        "strategy_candidate_available": False,
        "broker_order_paper_live_auto": False,
    }


def _git_identity() -> str:
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain=v1"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise CleanroomReplayError("cannot verify committed source identity") from exc
    if status.stdout:
        raise CleanroomReplayError("--execute requires a clean committed worktree")
    commit = head.stdout.strip()
    if not _is_git_object_id(commit):
        raise CleanroomReplayError("source commit identity is invalid")
    return commit


def _publish(report: Mapping[str, Any], output: Path) -> tuple[str, Path]:
    sidecar = output.with_suffix(output.suffix + ".sha256")
    if output.exists() or sidecar.exists():
        raise CleanroomReplayError("result or sidecar already exists")
    try:
        raw = (
            json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CleanroomReplayError("result is not strict finite JSON") from exc
    digest = hashlib.sha256(raw).hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    payloads = (
        (output, raw),
        (sidecar, f"{digest}  {output.name}\n".encode("ascii")),
    )
    temporary_paths: list[Path] = []
    try:
        for target, payload in payloads:
            with tempfile.NamedTemporaryFile(
                dir=output.parent,
                prefix=f".{target.name}.",
                delete=False,
            ) as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
                temporary_paths.append(Path(handle.name))
        for temporary, (target, _) in zip(temporary_paths, payloads, strict=True):
            os.replace(temporary, target)
        directory = os.open(output.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        for path in temporary_paths:
            path.unlink(missing_ok=True)
    return digest, sidecar


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--definition", type=Path, default=DEFINITION)
    parser.add_argument("--database", type=Path, default=DATABASE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)

    definition, definition_sha256 = _load_definition(args.definition.resolve())
    if not args.execute:
        print(
            json.dumps(
                {
                    "status": "VALIDATE_DEFINITION_ONLY",
                    "definition_sha256": definition_sha256,
                    "database_opened": False,
                    "output_written": False,
                    "network_used": False,
                },
                sort_keys=True,
            )
        )
        return 0

    if (
        args.definition.resolve() != DEFINITION.resolve()
        or args.database.resolve() != DATABASE.resolve()
        or args.output.resolve() != OUTPUT.resolve()
    ):
        raise CleanroomReplayError("--execute requires the exact frozen paths")
    source_commit = _git_identity()
    panel = _load_panel(args.database.resolve(), definition)
    report = build_report(
        definition,
        definition_sha256,
        panel,
        source_commit=source_commit,
    )
    digest, sidecar = _publish(report, args.output.resolve())
    print(
        json.dumps(
            {
                "status": "COMPLETED_CLEANROOM_MIGRATION_REPLAY",
                "result": str(args.output.resolve()),
                "result_sha256": digest,
                "sidecar": str(sidecar),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
