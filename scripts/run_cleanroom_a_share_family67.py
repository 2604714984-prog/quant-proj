#!/usr/bin/env python3
"""Run the text-only clean-room migration replay for rejected Family67."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from quant_system.backtest.dual_momentum import (  # noqa: E402
    AllocationSession,
    MonthlyTarget,
    OpenCloseBar,
    build_dual_momentum_targets,
    build_static_targets,
    run_monthly_open_close_backtest,
)
from quant_system.research.strict_bootstrap import bootstrap_one_sided  # noqa: E402

DEFINITION = ROOT / "research/definitions/a_share_family67_cleanroom_replication_v1.json"
OUTPUT = ROOT / "reports/validation/a_share_family67_cleanroom_replication_v1.json"
DEFINITION_SHA256 = "8a1ee84c99088a1b71bddf4d10100d7dd9d135f968827b073a027cf67eafe556"
HEX = frozenset("0123456789abcdef")


class Family67ReplayError(RuntimeError):
    """Raised when frozen inputs or clean-room execution boundaries drift."""


@dataclass(frozen=True)
class LoadedSource:
    rows: tuple[OpenCloseBar, ...]
    source_sha256: str
    selected_slice_sha256: str
    common_slice_sha256: str
    selected_row_count: int
    common_session_count: int
    common_row_count: int
    excluded_non_common_rows: int
    per_symbol_row_counts: tuple[int, ...]
    first_common_date: date
    last_common_date: date


def _reject_constant(value: str) -> None:
    raise Family67ReplayError(f"nonfinite JSON constant is not allowed: {value}")


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise Family67ReplayError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_definition(path: Path = DEFINITION) -> tuple[dict[str, Any], str]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise Family67ReplayError(f"cannot read definition: {path}") from exc
    digest = hashlib.sha256(raw).hexdigest()
    if digest != DEFINITION_SHA256:
        raise Family67ReplayError("definition SHA-256 does not match the frozen spec")
    try:
        parsed = json.loads(
            raw,
            object_pairs_hook=_unique_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Family67ReplayError("definition is not strict JSON") from exc
    if not isinstance(parsed, dict):
        raise Family67ReplayError("definition root must be an object")
    if parsed.get("status") != "OUTCOME_BLIND_DEFINITION_NOT_EXECUTED":
        raise Family67ReplayError("definition is no longer outcome-blind and unexecuted")
    if parsed.get("classification") != "RETROSPECTIVE_CLEANROOM_MIGRATION_REPLAY":
        raise Family67ReplayError("definition classification changed")
    lineage = parsed.get("lineage_controls")
    if not isinstance(lineage, dict) or any(
        lineage.get(key) is not expected
        for key, expected in (
            ("legacy_python_permitted_as_implementation_input", False),
            ("legacy_result_values_permitted_as_test_oracle", False),
            ("status_mutation_allowed", False),
            ("eligible_for_new_strategy_evidence", False),
            ("strict_pit", False),
            ("strategy_candidate_available", False),
        )
    ):
        raise Family67ReplayError("clean-room lineage boundary changed")
    if parsed.get("family_number") != 67 or parsed.get("gates", {}).get("expected_count") != 23:
        raise Family67ReplayError("Family67 identity or 23-gate contract changed")
    return parsed, digest


def _capture_regular_file(path: Path) -> tuple[bytes, str]:
    """Capture one regular file descriptor and bind hash, bytes, and path identity."""

    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise Family67ReplayError(f"cannot safely open source file: {path}") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise Family67ReplayError("source path must identify a regular file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
        captured = b"".join(chunks)
        descriptor_identity = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        )
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        ) != descriptor_identity or len(captured) != after.st_size:
            raise Family67ReplayError("source file changed during descriptor capture")
        try:
            path_state = path.stat(follow_symlinks=False)
        except OSError as exc:
            raise Family67ReplayError("source path disappeared during descriptor capture") from exc
        path_identity = (
            path_state.st_dev,
            path_state.st_ino,
            path_state.st_size,
            path_state.st_mtime_ns,
        )
        if stat.S_ISLNK(path_state.st_mode) or path_identity != descriptor_identity:
            raise Family67ReplayError("source path was replaced during descriptor capture")
    finally:
        os.close(descriptor)
    return captured, hashlib.sha256(captured).hexdigest()


def _parse_date(value: str, fmt: str) -> date:
    try:
        parsed = datetime.strptime(value, fmt).date()
    except (TypeError, ValueError) as exc:
        raise Family67ReplayError("trade_date does not match the frozen format") from exc
    return parsed


def _positive_price(value: str, name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise Family67ReplayError(f"{name} must be numeric") from exc
    if not math.isfinite(parsed) or parsed <= 0.0:
        raise Family67ReplayError(f"{name} must be finite and positive")
    return parsed


def _canonical_csv_row(row: dict[str, str], columns: tuple[str, ...]) -> bytes:
    return (
        json.dumps(
            [row[column] for column in columns],
            ensure_ascii=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _load_source(path: Path, definition: dict[str, Any]) -> LoadedSource:
    source = definition["source_data"]
    raw_source, source_sha = _capture_regular_file(path)
    if source_sha != source["sha256"]:
        raise Family67ReplayError("source CSV SHA-256 changed")
    assets = tuple(sorted(item["symbol"] for item in definition["asset_classes"]))
    columns = tuple(source["expected_columns"])
    by_symbol: dict[str, dict[date, tuple[float, float, bytes]]] = {
        symbol: {} for symbol in assets
    }
    try:
        text_source = raw_source.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Family67ReplayError("source CSV is not valid UTF-8") from exc
    with io.StringIO(text_source, newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != columns:
            raise Family67ReplayError("source CSV columns or order changed")
        for row in reader:
            symbol = row["ts_code"]
            if symbol not in by_symbol:
                continue
            if (
                row["snapshot_id"] != source["snapshot_id"]
                or row["provider_source"] != source["provider_source"]
                or row["adjustment"] != source["adjustment"]
            ):
                raise Family67ReplayError("selected source provenance changed")
            trade_date = _parse_date(row["trade_date"], source["trade_date_format"])
            if trade_date in by_symbol[symbol]:
                raise Family67ReplayError("duplicate selected symbol-date row")
            by_symbol[symbol][trade_date] = (
                _positive_price(row["open"], "open"),
                _positive_price(row["close"], "close"),
                _canonical_csv_row(row, columns),
            )

    if any(not rows for rows in by_symbol.values()):
        raise Family67ReplayError("one or more frozen symbols are absent")
    common_dates = set.intersection(*(set(rows) for rows in by_symbol.values()))
    if not common_dates:
        raise Family67ReplayError("the frozen symbols have no common sessions")
    ordered_common = tuple(sorted(common_dates))
    selected_digest = hashlib.sha256()
    common_digest = hashlib.sha256()
    for trade_date, symbol in sorted(
        (trade_date, symbol)
        for symbol, rows in by_symbol.items()
        for trade_date in rows
    ):
        selected_digest.update(by_symbol[symbol][trade_date][2])
    bars: list[OpenCloseBar] = []
    for trade_date in ordered_common:
        for symbol in assets:
            open_price, close_price, raw = by_symbol[symbol][trade_date]
            common_digest.update(raw)
            bars.append(OpenCloseBar(trade_date, symbol, open_price, close_price))
    per_symbol_counts = tuple(len(by_symbol[symbol]) for symbol in assets)
    selected_count = sum(per_symbol_counts)
    common_count = len(ordered_common) * len(assets)
    return LoadedSource(
        rows=tuple(bars),
        source_sha256=source_sha,
        selected_slice_sha256=selected_digest.hexdigest(),
        common_slice_sha256=common_digest.hexdigest(),
        selected_row_count=selected_count,
        common_session_count=len(ordered_common),
        common_row_count=common_count,
        excluded_non_common_rows=selected_count - common_count,
        per_symbol_row_counts=per_symbol_counts,
        first_common_date=ordered_common[0],
        last_common_date=ordered_common[-1],
    )


def _returns_by_date(sessions: tuple[AllocationSession, ...]) -> dict[date, float]:
    return {item.session_date: item.net_factor - 1.0 for item in sessions}


def _split_metrics(returns: list[float]) -> dict[str, float | int | None]:
    if not returns:
        raise Family67ReplayError("split has no return observations")
    wealth = 1.0
    peak = 1.0
    drawdown = 0.0
    for value in returns:
        factor = 1.0 + value
        if not math.isfinite(factor) or factor <= 0.0:
            raise Family67ReplayError("split net factor must be finite and positive")
        wealth *= factor
        peak = max(peak, wealth)
        drawdown = min(drawdown, wealth / peak - 1.0)
    return {
        "observation_count": len(returns),
        "terminal_wealth": wealth,
        "net_annualized_return_252": wealth ** (252.0 / len(returns)) - 1.0,
        "maximum_drawdown": drawdown,
        "arithmetic_mean_daily_return": math.fsum(returns) / len(returns),
    }


def _complete_month_count(
    common_dates: tuple[date, ...],
    return_dates: set[date],
    start: date,
    end: date,
) -> int:
    by_month: dict[tuple[int, int], set[date]] = {}
    for session_date in common_dates:
        if start <= session_date <= end:
            by_month.setdefault((session_date.year, session_date.month), set()).add(session_date)
    return sum(bool(dates) and dates <= return_dates for dates in by_month.values())


def _linear_quantile(values: tuple[float, ...], probability: float) -> float:
    ordered = sorted(values)
    if not ordered or not 0.0 <= probability <= 1.0:
        raise Family67ReplayError("invalid quantile input")
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    weight = position - lower
    return ordered[lower] + weight * (ordered[upper] - ordered[lower])


def _bh_adjusted(raw_p_values: list[float]) -> list[float]:
    if len(raw_p_values) != 3 or any(
        not math.isfinite(value) or not 0.0 <= value <= 1.0 for value in raw_p_values
    ):
        raise Family67ReplayError("BH requires exactly three finite p-values")
    ordered = sorted(range(3), key=lambda index: (raw_p_values[index], index))
    ordered_adjusted = [0.0, 0.0, 0.0]
    running = 1.0
    for position in range(2, -1, -1):
        index = ordered[position]
        rank = position + 1
        running = min(running, min(1.0, raw_p_values[index] * 3.0 / rank))
        ordered_adjusted[position] = running
    adjusted = [0.0, 0.0, 0.0]
    for position, index in enumerate(ordered):
        adjusted[index] = ordered_adjusted[position]
    return adjusted


def _weights_from_classes(definition: dict[str, Any], weights: dict[str, float]) -> dict[str, float]:
    symbol_by_class = {
        item["asset_class"]: item["symbol"] for item in definition["asset_classes"]
    }
    return {symbol_by_class[asset_class]: weight for asset_class, weight in weights.items()}


def _targets_after_anchor(
    targets: tuple[MonthlyTarget, ...],
    initial_close_date: date,
) -> tuple[MonthlyTarget, ...]:
    """Discard pre-anchor executions only after full-history signal construction."""

    filtered = tuple(item for item in targets if item.execution_date > initial_close_date)
    if not filtered:
        raise Family67ReplayError("no monthly targets remain after the evaluation anchor")
    return filtered


def build_report(
    definition: dict[str, Any],
    definition_sha256: str,
    loaded: LoadedSource,
    *,
    source_commit: str,
) -> dict[str, Any]:
    assets = sorted(definition["asset_classes"], key=lambda item: item["order"])
    risky = tuple(item["symbol"] for item in assets if item["role"] == "risky")
    cash = next(item["symbol"] for item in assets if item["role"] == "defensive")
    signal = definition["signal"]
    common_dates = tuple(sorted({row.session_date for row in loaded.rows}))
    try:
        initial_close_date = next(item for item in common_dates if item >= date(2019, 1, 1))
    except StopIteration as exc:
        raise Family67ReplayError("source has no common-session initial close for 2019") from exc
    generated_targets = build_dual_momentum_targets(
        loaded.rows,
        risky,
        cash,
        lookback_sessions=signal["lookback_sessions"],
        skip_sessions=signal["skip_sessions"],
        volatility_sessions=signal["volatility_sessions"],
        top_count=signal["top_count"],
        single_risky_cap=signal["single_risky_cap"],
    )
    strategy_targets = _targets_after_anchor(generated_targets, initial_close_date)
    comparator_targets = {
        item["comparator_id"]: build_static_targets(
            strategy_targets,
            _weights_from_classes(definition, item["weights_by_class"]),
        )
        for item in sorted(definition["comparators"], key=lambda item: item["order"])
    }
    costs = definition["execution_accounting"]["cost_bps_per_turnover_side"]
    run_by_cost: dict[int, dict[str, Any]] = {}
    return_ledgers: dict[int, dict[str, dict[date, float]]] = {}
    for cost in costs:
        strategy_result = run_monthly_open_close_backtest(
            loaded.rows,
            strategy_targets,
            cash_like_symbol=cash,
            cost_bps_per_turnover_side=cost,
            initial_close_date=initial_close_date,
        )
        comparator_results = {
            name: run_monthly_open_close_backtest(
                loaded.rows,
                targets,
                cash_like_symbol=cash,
                cost_bps_per_turnover_side=cost,
                initial_close_date=initial_close_date,
            )
            for name, targets in comparator_targets.items()
        }
        ledgers = {"strategy": _returns_by_date(strategy_result.sessions)}
        ledgers.update(
            {name: _returns_by_date(result.sessions) for name, result in comparator_results.items()}
        )
        if len({tuple(ledger) for ledger in ledgers.values()}) != 1:
            raise Family67ReplayError("strategy and comparator return dates are not aligned")
        return_ledgers[int(cost)] = ledgers
        split_results: dict[str, Any] = {}
        for split in definition["splits_by_return_date"]:
            start = date.fromisoformat(split["start"])
            end = date.fromisoformat(split["end"])
            dates = [item for item in ledgers["strategy"] if start <= item <= end]
            split_results[split["split_id"]] = {
                "complete_month_count": _complete_month_count(
                    common_dates,
                    set(dates),
                    start,
                    end,
                ),
                "strategy": _split_metrics([ledgers["strategy"][item] for item in dates]),
                "comparators": {
                    name: _split_metrics([ledger[item] for item in dates])
                    for name, ledger in ledgers.items()
                    if name != "strategy"
                },
            }
        run_by_cost[int(cost)] = {"splits": split_results}

    gate_cost = int(definition["gates"]["at_cost_bps"])
    gated = run_by_cost[gate_cost]["splits"]
    ledgers = return_ledgers[gate_cost]
    inference = definition["inference"]
    tests: list[dict[str, Any]] = []
    inference_by_split: dict[str, Any] = {}
    comparator_names = [
        item["comparator_id"]
        for item in sorted(definition["comparators"], key=lambda item: item["order"])
    ]
    for split_id in ("validation_2022_2023", "holdout_2024_2025"):
        split = next(item for item in definition["splits_by_return_date"] if item["split_id"] == split_id)
        start = date.fromisoformat(split["start"])
        end = date.fromisoformat(split["end"])
        dates = [item for item in ledgers["strategy"] if start <= item <= end]
        bootstraps = []
        raw_p_values = []
        for comparator in comparator_names:
            excess = [
                ledgers["strategy"][item] - ledgers[comparator][item] for item in dates
            ]
            result = bootstrap_one_sided(
                excess,
                block_length=inference["moving_block_sessions"],
                draws=inference["bootstrap_draws"],
                seed=inference["seed"],
            )
            lower = result.observed_mean - _linear_quantile(
                result.centered_means,
                1.0 - inference["one_sided_alpha"],
            )
            bootstraps.append((comparator, result, lower))
            raw_p_values.append(result.raw_p)
        adjusted = _bh_adjusted(raw_p_values)
        entries = []
        for index, (comparator, result, lower) in enumerate(bootstraps):
            entries.append(
                {
                    "comparator_id": comparator,
                    "observed_mean_daily_excess": result.observed_mean,
                    "moving_block_lower_bound": lower,
                    "raw_p": result.raw_p,
                    "bh_adjusted_p": adjusted[index],
                }
            )
            tests.extend(
                (
                    {
                        "gate_id": f"{split_id}.lower_bound.{comparator}",
                        "passed": lower > 0.0,
                    },
                    {
                        "gate_id": f"{split_id}.bh_significant.{comparator}",
                        "passed": adjusted[index] <= inference["one_sided_alpha"],
                    },
                )
            )
        inference_by_split[split_id] = entries

    for split in definition["splits_by_return_date"]:
        if not split["gated"]:
            continue
        split_id = split["split_id"]
        metrics = gated[split_id]
        tests.extend(
            (
                {
                    "gate_id": f"{split_id}.minimum_complete_months",
                    "passed": metrics["complete_month_count"] >= split["minimum_complete_months"],
                },
                {
                    "gate_id": f"{split_id}.positive_net_annualized_return",
                    "passed": metrics["strategy"]["net_annualized_return_252"] > 0.0,
                },
                {
                    "gate_id": f"{split_id}.annualized_above_static",
                    "passed": metrics["strategy"]["net_annualized_return_252"]
                    > metrics["comparators"]["static_diversified"][
                        "net_annualized_return_252"
                    ],
                },
            )
        )
    for split_id in ("validation_2022_2023", "holdout_2024_2025"):
        tests.append(
            {
                "gate_id": f"{split_id}.drawdown_no_worse_than_static",
                "passed": gated[split_id]["strategy"]["maximum_drawdown"]
                >= gated[split_id]["comparators"]["static_diversified"]["maximum_drawdown"],
            }
        )
    tests.sort(key=lambda item: item["gate_id"])
    if len(tests) != definition["gates"]["expected_count"]:
        raise Family67ReplayError("derived gate count is not exactly 23")
    pass_count = sum(item["passed"] for item in tests)
    return {
        "definition_id": definition["definition_id"],
        "research_id": definition["research_id"],
        "family_number": 67,
        "status": "RETROSPECTIVE_CLEANROOM_MIGRATION_REPLAY_COMPLETED",
        "classification": "RETROSPECTIVE_CLEANROOM_MIGRATION_REPLAY",
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": source_commit,
        "definition_sha256": definition_sha256,
        "source_data": {
            "source_sha256": loaded.source_sha256,
            "selected_slice_sha256": loaded.selected_slice_sha256,
            "common_slice_sha256": loaded.common_slice_sha256,
            "selected_row_count": loaded.selected_row_count,
            "common_session_count": loaded.common_session_count,
            "common_row_count": loaded.common_row_count,
            "excluded_non_common_rows": loaded.excluded_non_common_rows,
            "per_symbol_row_counts_sorted": list(loaded.per_symbol_row_counts),
            "first_common_date": loaded.first_common_date.isoformat(),
            "last_common_date": loaded.last_common_date.isoformat(),
            "strict_pit": False,
        },
        "generated_target_count": len(generated_targets),
        "evaluation_target_count": len(strategy_targets),
        "excluded_pre_anchor_target_count": len(generated_targets) - len(strategy_targets),
        "evaluation_initial_close_date": initial_close_date.isoformat(),
        "results_by_cost_bps": run_by_cost,
        "inference_at_50bps": inference_by_split,
        "gate_results": {
            "pass_count": pass_count,
            "total_count": len(tests),
            "all_passed": pass_count == len(tests),
            "checks": tests,
        },
        "lineage": {
            "legacy_rejected_status_preserved": True,
            "eligible_for_new_strategy_evidence": False,
            "strict_pit": False,
            "strategy_candidate_available": False,
        },
        "boundary": definition["boundary"],
    }


def _is_git_oid(value: str) -> bool:
    return len(value) in {40, 64} and set(value) <= HEX


def _git_identity() -> str:
    status = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--porcelain=v1"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if status:
        raise Family67ReplayError("execution requires a clean committed worktree")
    head = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not _is_git_oid(head):
        raise Family67ReplayError("current HEAD is not a valid Git object ID")
    return head


def _publish(report: dict[str, Any], output: Path) -> tuple[str, Path]:
    sidecar = output.with_name(output.name + ".sha256")
    if output.exists() or sidecar.exists():
        raise Family67ReplayError("output or sidecar already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    temp_paths: list[Path] = []
    try:
        for target, content in (
            (output, payload),
            (sidecar, f"{digest}  {output.name}\n".encode("ascii")),
        ):
            descriptor, raw_temp = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
            temporary = Path(raw_temp)
            temp_paths.append(temporary)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
            temp_paths.remove(temporary)
    finally:
        for temporary in temp_paths:
            temporary.unlink(missing_ok=True)
    return digest, sidecar


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--source-commit")
    parser.add_argument("--data-file", type=Path)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    definition, definition_sha = _load_definition()
    if not args.execute:
        print(
            json.dumps(
                {
                    "definition_sha256": definition_sha,
                    "network_used": False,
                    "source_data_opened": False,
                    "output_written": False,
                    "status": "VALIDATE_DEFINITION_ONLY",
                },
                sort_keys=True,
            )
        )
        return 0
    if args.data_file is None or args.source_commit is None:
        raise Family67ReplayError("--execute requires --data-file and --source-commit")
    head = _git_identity()
    if args.source_commit != head:
        raise Family67ReplayError("--source-commit does not match clean HEAD")
    loaded = _load_source(args.data_file, definition)
    report = build_report(definition, definition_sha, loaded, source_commit=head)
    digest, sidecar = _publish(report, args.output)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "output_sha256": digest,
                "sidecar": str(sidecar),
                "status": report["status"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
