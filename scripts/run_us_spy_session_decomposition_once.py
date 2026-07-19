#!/usr/bin/env python3
"""Run the frozen SPY overnight/intraday retrospective decomposition once."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import json
import math
from numbers import Real
import os
from pathlib import Path
import stat
import subprocess
from typing import Any, Sequence

import duckdb


ROOT = Path(__file__).resolve().parents[1]
RESEARCH_ID = "US_SPY_SESSION_DECOMPOSITION_V1_20260720"
CLASSIFICATION = "RETROSPECTIVE_PROGRAM_PERIOD_CONSUMED_DIAGNOSTIC_ONLY"
TABLE = "us_equity_research.us_daily_total_return_research"
SNAPSHOT_ID = "tiingo_raw_20260711T142010Z_5c24877d23cfc4a0"
SYMBOL = "SPY"
CUTOFF = date(2026, 6, 30)
EXPECTED_SNAPSHOT_ROWS = 8418
EXPECTED_CONSUMED_ROWS = 8411
DEFINITION_SHA256 = "73813f296e7e4824aded64e8456b4aba7a4b6a9dc4e10dcbb1d769085d5ab35c"
SPLITS = {
    "development": (date(1994, 1, 1), date(2009, 12, 31)),
    "validation": (date(2010, 1, 1), date(2017, 12, 31)),
    "retrospective_holdout": (date(2018, 1, 1), CUTOFF),
    "combined_validation_holdout": (date(2010, 1, 1), CUTOFF),
}
ACCOUNTS = ("B1_SPY_BUY_HOLD", "B2_SPY_OVERNIGHT", "B3_SPY_INTRADAY")
COSTS = (0, 5, 15)
EXPECTED_SPLIT_ROWS = {
    "development": 4030,
    "validation": 2013,
    "retrospective_holdout": 2134,
    "combined_validation_holdout": 4147,
}
TERMINAL_OUTCOME_STATUSES = (
    "RETROSPECTIVE_SESSION_DECOMPOSITION_OVERNIGHT_PASS_EXTERNAL_REVIEW",
    "RETROSPECTIVE_SESSION_DECOMPOSITION_INTRADAY_PASS_EXTERNAL_REVIEW",
    "RETROSPECTIVE_SESSION_DECOMPOSITION_BOTH_PASS_EXTERNAL_REVIEW",
    "RETROSPECTIVE_SESSION_DECOMPOSITION_FAIL",
    "INPUT_BLOCKED",
)
GATE_LABELS = (
    "validation 5 bps CAGR > 0",
    "retrospective holdout 5 bps CAGR > 0",
    "validation 15 bps CAGR > 0",
    "retrospective holdout 15 bps CAGR > 0",
    "combined validation plus holdout 15 bps CAGR > 0",
    "combined validation plus holdout 15 bps maximum positive year contribution <= 0.50",
    "zero duplicate missing nonfinite identity or execution failures",
)
DEFINITION = ROOT / "research/definitions/us_spy_session_decomposition_v1.json"
RUNNER = ROOT / "scripts/run_us_spy_session_decomposition_once.py"
TEST = ROOT / "tests/test_run_us_spy_session_decomposition_once.py"
RESULT = ROOT / "reports/validation/us_spy_session_decomposition_v1_result.json"
RECEIPT = ROOT / "reports/validation/us_spy_session_decomposition_v1_run.json"


class SessionDecompositionError(RuntimeError):
    """Frozen input or execution semantics cannot be satisfied."""


@dataclass(frozen=True)
class Bar:
    session_date: date
    raw_open: float
    raw_close: float
    adj_open: float
    adj_close: float

    def __post_init__(self) -> None:
        if type(self.session_date) is not date:
            raise SessionDecompositionError("session_date must be a date")
        for name, value in (
            ("raw_open", self.raw_open),
            ("raw_close", self.raw_close),
            ("adj_open", self.adj_open),
            ("adj_close", self.adj_close),
        ):
            if isinstance(value, bool) or not math.isfinite(value) or value <= 0.0:
                raise SessionDecompositionError(f"{name} must be positive and finite")


def _canonical(payload: Any) -> bytes:
    return (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        + b"\n"
    )


def _file_identity(value: os.stat_result) -> tuple[int, int, int, int]:
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns


def _capture_regular_file_with_identity(
    path: Path,
) -> tuple[bytes, tuple[int, int, int, int]]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise SessionDecompositionError(f"cannot capture regular file: {path.name}") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise SessionDecompositionError(f"captured path is not a regular file: {path.name}")
        blocks: list[bytes] = []
        while block := os.read(descriptor, 1024 * 1024):
            blocks.append(block)
        after = os.fstat(descriptor)
        if _file_identity(after) != _file_identity(before):
            raise SessionDecompositionError(f"captured file changed while reading: {path.name}")
    finally:
        os.close(descriptor)
    try:
        current = os.stat(path, follow_symlinks=False)
    except OSError as exc:
        raise SessionDecompositionError(f"captured path disappeared: {path.name}") from exc
    if not stat.S_ISREG(current.st_mode) or _file_identity(current) != _file_identity(before):
        raise SessionDecompositionError(f"captured path was replaced: {path.name}")
    return b"".join(blocks), _file_identity(before)


def _capture_regular_file(path: Path) -> bytes:
    return _capture_regular_file_with_identity(path)[0]


def _sha256(path: Path) -> str:
    return hashlib.sha256(_capture_regular_file(path)).hexdigest()


def _descriptor_sha256(descriptor: int) -> str:
    digest = hashlib.sha256()
    os.lseek(descriptor, 0, os.SEEK_SET)
    while block := os.read(descriptor, 1024 * 1024):
        digest.update(block)
    os.lseek(descriptor, 0, os.SEEK_SET)
    return digest.hexdigest()


def _strict_json_bytes(raw: bytes) -> dict[str, Any]:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, value in values:
            if key in output:
                raise SessionDecompositionError(f"duplicate JSON key: {key}")
            output[key] = value
        return output

    def invalid_constant(value: str) -> None:
        raise SessionDecompositionError(f"nonfinite JSON constant: {value}")

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SessionDecompositionError("JSON is not UTF-8") from exc
    parsed = json.loads(text, object_pairs_hook=pairs, parse_constant=invalid_constant)
    if not isinstance(parsed, dict):
        raise SessionDecompositionError("definition must be a JSON object")
    return parsed


def _capture_json(path: Path, *, require_canonical: bool = False) -> tuple[dict[str, Any], bytes]:
    raw = _capture_regular_file(path)
    parsed = _strict_json_bytes(raw)
    if require_canonical and raw != _canonical(parsed):
        raise SessionDecompositionError(f"output JSON is not canonical: {path.name}")
    return parsed, raw


def _strict_json(path: Path) -> dict[str, Any]:
    return _capture_json(path)[0]


def _git_bytes(*arguments: str) -> bytes:
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT), *arguments],
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SessionDecompositionError("cannot bind Git identity") from exc


def _git(*arguments: str) -> str:
    return _git_bytes(*arguments).decode("utf-8").strip()


def _locked_code_identity(allowed_outputs: Sequence[Path] = ()) -> tuple[str, str]:
    allowed = {
        f"?? {path.relative_to(ROOT).as_posix()}" for path in allowed_outputs
    }
    status = set(filter(None, _git("status", "--porcelain=v1", "--untracked-files=all").splitlines()))
    if status - allowed:
        raise SessionDecompositionError("worktree must be clean")
    commit = _git("rev-parse", "HEAD")
    tree = _git("rev-parse", "HEAD^{tree}")
    if _git("rev-parse", "@{upstream}") != commit:
        raise SessionDecompositionError("local commit must equal its pushed upstream")
    return commit, tree


def _head_bound_file_hashes() -> dict[str, str]:
    files = {
        "definition": (DEFINITION, "research/definitions/us_spy_session_decomposition_v1.json"),
        "runner": (RUNNER, "scripts/run_us_spy_session_decomposition_once.py"),
        "tests": (TEST, "tests/test_run_us_spy_session_decomposition_once.py"),
    }
    hashes: dict[str, str] = {}
    for name, (path, relative) in files.items():
        working = _capture_regular_file(path)
        committed = _git_bytes("show", f"HEAD:{relative}")
        if working != committed:
            raise SessionDecompositionError(f"{name} bytes differ from HEAD blob")
        hashes[name] = hashlib.sha256(working).hexdigest()
    return hashes


def _exclusive_write(path: Path, payload: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise SessionDecompositionError(f"immutable output already exists: {path.name}")
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
    directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _replace_captured_file(
    path: Path, payload: bytes, captured_identity: tuple[int, int, int, int]
) -> None:
    temporary = path.with_name(f".{path.name}.replace-{os.getpid()}")
    try:
        _exclusive_write(temporary, payload)
        current = os.stat(path, follow_symlinks=False)
        if not stat.S_ISREG(current.st_mode) or _file_identity(current) != captured_identity:
            raise SessionDecompositionError(f"captured output was replaced: {path.name}")
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if _exists_or_symlink(temporary):
            temporary.unlink()


def _finalize_claim(
    path: Path,
    payload: bytes,
    expected_claim: dict[str, Any],
    expected_result_bytes: bytes,
) -> None:
    raw, captured_identity = _capture_regular_file_with_identity(path)
    claim = _strict_json_bytes(raw)
    if raw != _canonical(claim) or claim != expected_claim:
        raise SessionDecompositionError("one-use receipt identity changed")
    if claim.get("status") != "CLAIMED_RETROSPECTIVE_DIAGNOSTIC_RUN":
        raise SessionDecompositionError("one-use receipt is not active")
    temporary = path.with_name(f".{path.name}.final-{os.getpid()}")
    try:
        _exclusive_write(temporary, payload)
        current = os.stat(path, follow_symlinks=False)
        if not stat.S_ISREG(current.st_mode) or _file_identity(current) != captured_identity:
            raise SessionDecompositionError("one-use receipt was replaced before finalization")
        actual_result, _result_identity = _capture_regular_file_with_identity(RESULT)
        if actual_result != expected_result_bytes:
            raise SessionDecompositionError("published result changed before receipt finalization")
        os.replace(temporary, path)
    finally:
        if _exists_or_symlink(temporary):
            temporary.unlink()
    directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _exists_or_symlink(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _validated_bars(rows: Sequence[Bar]) -> tuple[Bar, ...]:
    bars = tuple(rows)
    if len(bars) < 2 or any(not isinstance(row, Bar) for row in bars):
        raise SessionDecompositionError("at least two Bar rows are required")
    if any(left.session_date >= right.session_date for left, right in zip(bars, bars[1:])):
        raise SessionDecompositionError("bars must have strictly increasing unique dates")
    return bars


def _trade(cash: float, raw_entry: float, adjusted_ratio: float, rate: float) -> float:
    shares = math.floor(cash / (raw_entry * (1.0 + rate)))
    if shares < 1:
        raise SessionDecompositionError("whole-share trade is unaffordable")
    residual = cash - shares * raw_entry * (1.0 + rate)
    gross_exit = shares * raw_entry * adjusted_ratio
    return residual + gross_exit * (1.0 - rate)


def _annual_contribution(
    returns: Sequence[float], dates: Sequence[date], initial: float
) -> tuple[float | None, dict[str, float], dict[str, float]]:
    annual_returns: dict[str, float] = {}
    annual_pnl: dict[str, float] = {}
    wealth = initial
    current_year = dates[0].year
    year_start = wealth
    for value, event_date in zip(returns, dates):
        if event_date.year != current_year:
            annual_pnl[str(current_year)] = wealth - year_start
            annual_returns[str(current_year)] = wealth / year_start - 1.0
            current_year = event_date.year
            year_start = wealth
        wealth *= 1.0 + value
    annual_pnl[str(current_year)] = wealth - year_start
    annual_returns[str(current_year)] = wealth / year_start - 1.0
    positive = [value for value in annual_pnl.values() if value > 0.0]
    share = max(positive) / math.fsum(positive) if positive else None
    return share, annual_returns, annual_pnl


def _metrics(
    initial: float,
    navs: Sequence[float],
    dates: Sequence[date],
    trades: int,
) -> dict[str, Any]:
    if not navs or len(navs) != len(dates):
        raise SessionDecompositionError("metric inputs are empty or misaligned")
    returns: list[float] = []
    prior = initial
    for nav in navs:
        if not math.isfinite(nav) or nav <= 0.0:
            raise SessionDecompositionError("NAV must stay positive and finite")
        returns.append(nav / prior - 1.0)
        prior = nav
    cumulative = navs[-1] / initial - 1.0
    elapsed = max((dates[-1] - dates[0]).days / 365.2425, len(dates) / 252.0)
    cagr = (navs[-1] / initial) ** (1.0 / elapsed) - 1.0
    mean = math.fsum(returns) / len(returns)
    volatility = (
        math.sqrt(math.fsum((value - mean) ** 2 for value in returns) / (len(returns) - 1))
        * math.sqrt(252.0)
        if len(returns) > 1
        else 0.0
    )
    peak = initial
    drawdown = 0.0
    for nav in navs:
        peak = max(peak, nav)
        drawdown = min(drawdown, nav / peak - 1.0)
    year_share, annual, annual_pnl = _annual_contribution(returns, dates, initial)
    positive = [value for value in returns if value > 0.0]
    observation_share = max(positive) / math.fsum(positive) if positive else None
    return {
        "observation_count": len(returns),
        "cumulative_net_return": cumulative,
        "cagr": cagr,
        "annualized_volatility": volatility,
        "maximum_drawdown": drawdown,
        "calmar": cagr / abs(drawdown) if drawdown < 0.0 else None,
        "positive_observation_fraction": sum(value > 0.0 for value in returns) / len(returns),
        "maximum_positive_year_contribution": year_share,
        "maximum_positive_observation_contribution": observation_share,
        "whole_share_trade_count": trades,
        "annual_returns": annual,
        "annual_pnl_usd": annual_pnl,
    }


def _account_path(
    rows: Sequence[Bar], account: str, round_trip_bps: int, initial: float
) -> tuple[list[float], list[date], int]:
    bars = _validated_bars(rows)
    if account not in ACCOUNTS:
        raise SessionDecompositionError("unknown account")
    if round_trip_bps not in COSTS:
        raise SessionDecompositionError("unknown round-trip cost")
    if isinstance(initial, bool) or not isinstance(initial, Real) or not math.isfinite(initial):
        raise SessionDecompositionError("initial capital must be a positive finite real")
    if initial <= 0.0:
        raise SessionDecompositionError("initial capital must be a positive finite real")
    rate = round_trip_bps / 2.0 / 10_000.0
    navs: list[float] = []
    dates: list[date] = []
    if account == "B1_SPY_BUY_HOLD":
        first = bars[0]
        shares = math.floor(initial / (first.raw_open * (1.0 + rate)))
        if shares < 1:
            raise SessionDecompositionError("whole-share trade is unaffordable")
        residual = initial - shares * first.raw_open * (1.0 + rate)
        for bar in bars:
            gross = shares * first.raw_open * (bar.adj_close / first.adj_open)
            navs.append(residual + gross * (1.0 - rate))
            dates.append(bar.session_date)
        trades = 2
    else:
        cash = initial
        if account == "B2_SPY_OVERNIGHT":
            for entry, exit_ in zip(bars, bars[1:]):
                cash = _trade(cash, entry.raw_close, exit_.adj_open / entry.adj_close, rate)
                navs.append(cash)
                dates.append(exit_.session_date)
        else:
            for bar in bars:
                cash = _trade(cash, bar.raw_open, bar.adj_close / bar.adj_open, rate)
                navs.append(cash)
                dates.append(bar.session_date)
        trades = 2 * len(navs)
    return navs, dates, trades


def simulate(
    rows: Sequence[Bar], account: str, round_trip_bps: int, initial: float = 40_000.0
) -> dict[str, Any]:
    navs, dates, trades = _account_path(rows, account, round_trip_bps, initial)
    return _metrics(initial, navs, dates, trades)


def simulate_segmented(
    segments: Sequence[Sequence[Bar]],
    account: str,
    round_trip_bps: int,
    initial: float = 40_000.0,
) -> dict[str, Any]:
    if len(segments) < 2:
        raise SessionDecompositionError("segmented simulation requires at least two segments")
    capital = initial
    all_navs: list[float] = []
    all_dates: list[date] = []
    trades = 0
    for segment in segments:
        navs, dates, segment_trades = _account_path(
            segment, account, round_trip_bps, capital
        )
        if all_dates and dates[0] <= all_dates[-1]:
            raise SessionDecompositionError("segments must be strictly ordered and disjoint")
        all_navs.extend(navs)
        all_dates.extend(dates)
        trades += segment_trades
        capital = navs[-1]
    return _metrics(initial, all_navs, all_dates, trades)


def _select(rows: Sequence[Bar], start: date, end: date) -> tuple[Bar, ...]:
    return tuple(row for row in _validated_bars(rows) if start <= row.session_date <= end)


def adjudicate(periods: dict[str, Any], data_failures: int) -> dict[str, Any]:
    if type(data_failures) is not int or data_failures < 0:
        return {"status": "INPUT_BLOCKED", "specialists": {}}
    specialists: dict[str, Any] = {}
    for account in ("B2_SPY_OVERNIGHT", "B3_SPY_INTRADAY"):
        try:
            values = (
                periods["validation"]["5"][account]["cagr"],
                periods["retrospective_holdout"]["5"][account]["cagr"],
                periods["validation"]["15"][account]["cagr"],
                periods["retrospective_holdout"]["15"][account]["cagr"],
                periods["combined_validation_holdout"]["15"][account]["cagr"],
                periods["combined_validation_holdout"]["15"][account][
                    "maximum_positive_year_contribution"
                ],
            )
            if any(
                value is not None
                and (isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value))
                for value in values
            ):
                raise TypeError("metrics must be finite real numbers or null concentration")
            concentration = values[5]
            gates = (
                values[0] > 0.0,
                values[1] > 0.0,
                values[2] > 0.0,
                values[3] > 0.0,
                values[4] > 0.0,
                concentration is not None and concentration <= 0.50,
                data_failures == 0,
            )
        except (KeyError, TypeError):
            return {"status": "INPUT_BLOCKED", "specialists": {}}
        specialists[account] = {
            "passed": all(gates),
            "gates_passed": sum(gates),
            "gates_total": len(gates),
            "gates": [
                {"order": index, "name": name, "passed": value}
                for index, (name, value) in enumerate(zip(GATE_LABELS, gates), 1)
            ],
        }
    overnight = specialists["B2_SPY_OVERNIGHT"]["passed"]
    intraday = specialists["B3_SPY_INTRADAY"]["passed"]
    if overnight and intraday:
        status = "RETROSPECTIVE_SESSION_DECOMPOSITION_BOTH_PASS_EXTERNAL_REVIEW"
    elif overnight:
        status = "RETROSPECTIVE_SESSION_DECOMPOSITION_OVERNIGHT_PASS_EXTERNAL_REVIEW"
    elif intraday:
        status = "RETROSPECTIVE_SESSION_DECOMPOSITION_INTRADAY_PASS_EXTERNAL_REVIEW"
    else:
        status = "RETROSPECTIVE_SESSION_DECOMPOSITION_FAIL"
    return {"status": status, "specialists": specialists}


def _definition(expected_database_sha256: str) -> dict[str, Any]:
    raw = _capture_regular_file(DEFINITION)
    if hashlib.sha256(raw).hexdigest() != DEFINITION_SHA256:
        raise SessionDecompositionError("definition bytes differ")
    definition = _strict_json_bytes(raw)
    expected = {
        "research_id": RESEARCH_ID,
        "status": "DEFINITION_FROZEN_NOT_EXECUTED",
        "classification": "RETROSPECTIVE_PROGRAM_PERIOD_CONSUMED_DIAGNOSTIC_ONLY",
    }
    if any(definition.get(key) != value for key, value in expected.items()):
        raise SessionDecompositionError("definition identity differs")
    identity = definition.get("input_identity")
    if not isinstance(identity, dict) or identity.get("database_sha256") != expected_database_sha256:
        raise SessionDecompositionError("definition database identity differs")
    if tuple(definition["specialist_gates"]["items"]) != GATE_LABELS:
        raise SessionDecompositionError("definition gate identity differs")
    return definition


def _database_metadata(descriptor: int) -> dict[str, Any]:
    connection = duckdb.connect(f"/proc/self/fd/{descriptor}", read_only=True)
    try:
        schema_rows = connection.execute(
            f"DESCRIBE SELECT trade_date, open, close, adj_open, adj_close FROM {TABLE}"
        ).fetchall()
        aggregate = connection.execute(
            f"""
            SELECT count(*), min(trade_date), max(trade_date),
                   count(*) - count(DISTINCT trade_date),
                   sum(CASE WHEN trade_date <= ? THEN 1 ELSE 0 END),
                   sum(CASE WHEN trade_date BETWEEN ? AND ? THEN 1 ELSE 0 END),
                   sum(CASE WHEN trade_date BETWEEN ? AND ? THEN 1 ELSE 0 END),
                   sum(CASE WHEN trade_date BETWEEN ? AND ? THEN 1 ELSE 0 END),
                   sum(CASE WHEN trade_date BETWEEN ? AND ? THEN 1 ELSE 0 END)
            FROM {TABLE} WHERE snapshot_id = ? AND symbol = ?
            """,
            [
                CUTOFF,
                *SPLITS["development"],
                *SPLITS["validation"],
                *SPLITS["retrospective_holdout"],
                *SPLITS["combined_validation_holdout"],
                SNAPSHOT_ID,
                SYMBOL,
            ],
        ).fetchone()
    finally:
        connection.close()
    expected = (
        EXPECTED_SNAPSHOT_ROWS,
        date(1993, 1, 29),
        date(2026, 7, 10),
        0,
        EXPECTED_CONSUMED_ROWS,
        *EXPECTED_SPLIT_ROWS.values(),
    )
    if aggregate != expected:
        raise SessionDecompositionError("SPY date-key metadata differs")
    schema = [[row[0], row[1]] for row in schema_rows]
    if [row[0] for row in schema] != ["trade_date", "open", "close", "adj_open", "adj_close"]:
        raise SessionDecompositionError("SPY price schema differs")
    return {
        "schema": schema,
        "snapshot_row_count": aggregate[0],
        "consumed_row_count": aggregate[4],
        "observed_date_start": aggregate[1].isoformat(),
        "observed_date_end": aggregate[2].isoformat(),
        "duplicate_date_count": aggregate[3],
        "split_row_counts": dict(EXPECTED_SPLIT_ROWS),
    }


def _database_price_rows(descriptor: int) -> tuple[tuple[Bar, ...], dict[str, Any]]:
    connection = duckdb.connect(f"/proc/self/fd/{descriptor}", read_only=True)
    try:
        rows = connection.execute(
            f"""
            SELECT trade_date, open, close, adj_open, adj_close
            FROM {TABLE}
            WHERE snapshot_id = ? AND symbol = ? AND trade_date <= ?
            ORDER BY trade_date
            """,
            [SNAPSHOT_ID, SYMBOL, CUTOFF],
        ).fetchall()
    finally:
        connection.close()
    if len(rows) != EXPECTED_CONSUMED_ROWS:
        raise SessionDecompositionError("consumed SPY row count differs")
    digest = hashlib.sha256()
    bars: list[Bar] = []
    for session_date, raw_open, raw_close, adj_open, adj_close in rows:
        digest.update(
            f"{session_date.isoformat()}|{raw_open}|{raw_close}|{adj_open}|{adj_close}\n".encode()
        )
        try:
            bars.append(Bar(session_date, raw_open, raw_close, adj_open, adj_close))
        except (TypeError, ValueError) as exc:
            raise SessionDecompositionError("SPY price rows are invalid") from exc
    validated = _validated_bars(bars)
    return validated, {"missing_or_nonfinite_count": 0, "consumed_rows_sha256": digest.hexdigest()}


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


def _wal_exists_or_symlink(database: Path) -> bool:
    wal = database.with_name(database.name + ".wal")
    return wal.exists() or wal.is_symlink()


def _verify_database_capture(
    database: Path,
    descriptor: int,
    expected_sha256: str,
    expected_identity: tuple[int, int, int, int],
) -> None:
    captured = os.fstat(descriptor)
    if _file_identity(captured) != expected_identity:
        raise SessionDecompositionError("captured database identity changed")
    if _descriptor_sha256(descriptor) != expected_sha256:
        raise SessionDecompositionError("captured database bytes changed")
    try:
        current = os.stat(database, follow_symlinks=False)
    except OSError as exc:
        raise SessionDecompositionError("database path disappeared") from exc
    if not stat.S_ISREG(current.st_mode) or _file_identity(current) != expected_identity:
        raise SessionDecompositionError("database path was replaced")
    if _wal_exists_or_symlink(database):
        raise SessionDecompositionError("database WAL exists or is a symlink")


def _preflight_input(database: Path, expected_database_sha256: str) -> tuple[int, dict[str, Any]]:
    if _wal_exists_or_symlink(database):
        raise SessionDecompositionError("database WAL exists before qualification")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(database, flags)
    except OSError as exc:
        raise SessionDecompositionError("cannot open database without following links") from exc
    try:
        captured = os.fstat(descriptor)
        if not stat.S_ISREG(captured.st_mode):
            raise SessionDecompositionError("database must be a regular file")
        before_hash = _descriptor_sha256(descriptor)
        if before_hash != expected_database_sha256:
            raise SessionDecompositionError("database pre-execution identity differs")
        metadata = _database_metadata(descriptor)
        identity = _file_identity(captured)
        current = os.stat(database, follow_symlinks=False)
        if not stat.S_ISREG(current.st_mode) or _file_identity(current) != identity:
            raise SessionDecompositionError("database path was replaced during preflight")
        if _wal_exists_or_symlink(database):
            raise SessionDecompositionError("database WAL appeared during preflight")
    except BaseException:
        os.close(descriptor)
        raise
    metadata.update({
        "database_filename": database.name,
        "database_sha256": before_hash,
        "table": TABLE,
        "snapshot_id": SNAPSHOT_ID,
        "symbol": SYMBOL,
        "cutoff_inclusive": CUTOFF.isoformat(),
        "database_descriptor_identity": {
        "device": captured.st_dev,
        "inode": captured.st_ino,
        "size": captured.st_size,
        "mtime_ns": captured.st_mtime_ns,
        },
    })
    return descriptor, metadata


def _qualify_claimed_input(
    database: Path, descriptor: int, metadata: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, tuple[Bar, ...]]]:
    bars, row_identity = _database_price_rows(descriptor)
    selected = {split: _select(bars, *bounds) for split, bounds in SPLITS.items()}
    split_counts = {split: len(rows) for split, rows in selected.items()}
    if split_counts != EXPECTED_SPLIT_ROWS:
        raise SessionDecompositionError("split row counts differ")
    if any(len(rows) < 2 for rows in selected.values()):
        raise SessionDecompositionError("a split has insufficient rows")
    metadata.update(row_identity)
    return metadata, selected


def _execution_identity(
    expected_database_sha256: str, allowed_outputs: Sequence[Path] = ()
) -> tuple[str, str, dict[str, str]]:
    commit, tree = _locked_code_identity(allowed_outputs)
    _definition(expected_database_sha256)
    file_hashes = _head_bound_file_hashes()
    if file_hashes["definition"] != DEFINITION_SHA256:
        raise SessionDecompositionError("definition hash differs from its locked constant")
    return commit, tree, file_hashes


def _claim_payload(
    database: Path,
    expected_database_sha256: str,
    commit: str,
    tree: str,
    file_hashes: dict[str, str],
) -> dict[str, Any]:
    return {
        "schema_version": "us-spy-session-decomposition-run-v1",
        "research_id": RESEARCH_ID,
        "status": "CLAIMED_RETROSPECTIVE_DIAGNOSTIC_RUN",
        "definition_commit": commit,
        "definition_tree": tree,
        "files_sha256": file_hashes,
        "database_filename": database.name,
        "expected_database_sha256": expected_database_sha256,
        "claimed_at_utc": datetime.now(timezone.utc).isoformat(),
        "strategy_candidate_available": False,
    }


def _validate_claim(
    claim: dict[str, Any],
    database: Path,
    expected_database_sha256: str,
    commit: str,
    tree: str,
    file_hashes: dict[str, str],
) -> None:
    if set(claim) != {
        "schema_version",
        "research_id",
        "status",
        "definition_commit",
        "definition_tree",
        "files_sha256",
        "database_filename",
        "expected_database_sha256",
        "claimed_at_utc",
        "strategy_candidate_available",
    }:
        raise SessionDecompositionError("one-use claim schema differs")
    expected = {
        "schema_version": "us-spy-session-decomposition-run-v1",
        "research_id": RESEARCH_ID,
        "status": "CLAIMED_RETROSPECTIVE_DIAGNOSTIC_RUN",
        "definition_commit": commit,
        "definition_tree": tree,
        "files_sha256": file_hashes,
        "database_filename": database.name,
        "expected_database_sha256": expected_database_sha256,
        "strategy_candidate_available": False,
    }
    if any(claim.get(key) != value for key, value in expected.items()):
        raise SessionDecompositionError("one-use claim identity differs")
    try:
        claimed_at = datetime.fromisoformat(claim["claimed_at_utc"])
    except (TypeError, ValueError) as exc:
        raise SessionDecompositionError("one-use claim timestamp is invalid") from exc
    if claimed_at.tzinfo is None:
        raise SessionDecompositionError("one-use claim timestamp lacks timezone")


def _base_error_input(database: Path, expected_database_sha256: str) -> dict[str, Any]:
    return {
        "database_filename": database.name,
        "expected_database_sha256": expected_database_sha256,
        "table": TABLE,
        "snapshot_id": SNAPSHOT_ID,
        "symbol": SYMBOL,
        "cutoff_inclusive": CUTOFF.isoformat(),
    }


def _execution_error_result(
    reason_class: str,
    claim_sha256: str,
    database: Path,
    expected_database_sha256: str,
    commit: str,
    tree: str,
    file_hashes: dict[str, str],
) -> dict[str, Any]:
    return {
        "schema_version": "us-spy-session-decomposition-result-v1",
        "research_id": RESEARCH_ID,
        "status": "EXECUTION_ERROR_CONSUMED",
        "classification": CLASSIFICATION,
        "claim_sha256": claim_sha256,
        "reason_class": reason_class,
        "repository_identity": {"commit": commit, "tree": tree, "files_sha256": file_hashes},
        "input_identity": _base_error_input(database, expected_database_sha256),
        "periods": None,
        "adjudication": None,
        "boundaries": _boundaries(),
    }


def _validate_periods(periods: Any) -> None:
    if not isinstance(periods, dict) or set(periods) != set(SPLITS):
        raise SessionDecompositionError("result period scope differs")
    metric_keys = {
        "observation_count",
        "cumulative_net_return",
        "cagr",
        "annualized_volatility",
        "maximum_drawdown",
        "calmar",
        "positive_observation_fraction",
        "maximum_positive_year_contribution",
        "maximum_positive_observation_contribution",
        "whole_share_trade_count",
        "annual_returns",
        "annual_pnl_usd",
    }
    nullable = {
        "calmar",
        "maximum_positive_year_contribution",
        "maximum_positive_observation_contribution",
    }
    for split, costs in periods.items():
        if not isinstance(costs, dict) or set(costs) != {str(value) for value in COSTS}:
            raise SessionDecompositionError("result cost scope differs")
        rows = EXPECTED_SPLIT_ROWS[split]
        observations = {
            "B1_SPY_BUY_HOLD": rows,
            "B2_SPY_OVERNIGHT": rows - 1,
            "B3_SPY_INTRADAY": rows,
        }
        if split == "combined_validation_holdout":
            observations["B2_SPY_OVERNIGHT"] = (
                EXPECTED_SPLIT_ROWS["validation"]
                + EXPECTED_SPLIT_ROWS["retrospective_holdout"]
                - 2
            )
        for accounts in costs.values():
            if not isinstance(accounts, dict) or set(accounts) != set(ACCOUNTS):
                raise SessionDecompositionError("result account scope differs")
            for account, metrics in accounts.items():
                if not isinstance(metrics, dict) or set(metrics) != metric_keys:
                    raise SessionDecompositionError("result metric schema differs")
                if type(metrics["observation_count"]) is not int or (
                    metrics["observation_count"] != observations[account]
                ):
                    raise SessionDecompositionError("result observation count differs")
                expected_trades = (
                    4
                    if account == "B1_SPY_BUY_HOLD" and split == "combined_validation_holdout"
                    else 2
                    if account == "B1_SPY_BUY_HOLD"
                    else 2 * observations[account]
                )
                if type(metrics["whole_share_trade_count"]) is not int or (
                    metrics["whole_share_trade_count"] != expected_trades
                ):
                    raise SessionDecompositionError("result trade count differs")
                for key in metric_keys - {
                    "observation_count",
                    "whole_share_trade_count",
                    "annual_returns",
                    "annual_pnl_usd",
                }:
                    value = metrics[key]
                    if value is None and key in nullable:
                        continue
                    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
                        raise SessionDecompositionError("result metric is not finite")
                fraction = metrics["positive_observation_fraction"]
                if not 0.0 <= fraction <= 1.0:
                    raise SessionDecompositionError("positive fraction is outside [0,1]")
                if not -1.0 <= metrics["maximum_drawdown"] <= 0.0:
                    raise SessionDecompositionError("maximum drawdown is outside [-1,0]")
                if metrics["annualized_volatility"] < 0.0:
                    raise SessionDecompositionError("annualized volatility is negative")
                for key in (
                    "maximum_positive_year_contribution",
                    "maximum_positive_observation_contribution",
                ):
                    value = metrics[key]
                    if value is not None and not 0.0 <= value <= 1.0:
                        raise SessionDecompositionError("positive contribution is outside [0,1]")
                for key in ("annual_returns", "annual_pnl_usd"):
                    values = metrics[key]
                    if not isinstance(values, dict) or not values:
                        raise SessionDecompositionError("annual metric ledger is missing")
                    if any(
                        not isinstance(year, str)
                        or isinstance(value, bool)
                        or not isinstance(value, Real)
                        or not math.isfinite(value)
                        for year, value in values.items()
                    ):
                        raise SessionDecompositionError("annual metric ledger is invalid")
                if set(metrics["annual_returns"]) != set(metrics["annual_pnl_usd"]):
                    raise SessionDecompositionError("annual metric ledgers differ")


def _validate_success_input(
    identity: Any, database: Path, expected_database_sha256: str
) -> None:
    if not isinstance(identity, dict):
        raise SessionDecompositionError("result input identity is missing")
    expected = {
        "database_filename": database.name,
        "database_sha256": expected_database_sha256,
        "database_sha256_before": expected_database_sha256,
        "database_sha256_after": expected_database_sha256,
        "database_unchanged": True,
        "table": TABLE,
        "snapshot_id": SNAPSHOT_ID,
        "symbol": SYMBOL,
        "cutoff_inclusive": CUTOFF.isoformat(),
        "snapshot_row_count": EXPECTED_SNAPSHOT_ROWS,
        "consumed_row_count": EXPECTED_CONSUMED_ROWS,
        "observed_date_start": "1993-01-29",
        "observed_date_end": "2026-07-10",
        "duplicate_date_count": 0,
        "missing_or_nonfinite_count": 0,
        "split_row_counts": EXPECTED_SPLIT_ROWS,
    }
    if any(identity.get(key) != value for key, value in expected.items()):
        raise SessionDecompositionError("result input identity differs")
    if set(identity) != set(expected) | {
        "schema",
        "database_descriptor_identity",
        "consumed_rows_sha256",
    }:
        raise SessionDecompositionError("result input identity schema differs")
    if identity["schema"] != [
        ["trade_date", "DATE"],
        ["open", "DOUBLE"],
        ["close", "DOUBLE"],
        ["adj_open", "DOUBLE"],
        ["adj_close", "DOUBLE"],
    ]:
        raise SessionDecompositionError("result input schema differs")
    descriptor = identity["database_descriptor_identity"]
    if not isinstance(descriptor, dict) or set(descriptor) != {
        "device",
        "inode",
        "size",
        "mtime_ns",
    } or any(type(value) is not int or value < 0 for value in descriptor.values()):
        raise SessionDecompositionError("database descriptor identity differs")
    row_hash = identity["consumed_rows_sha256"]
    if not isinstance(row_hash, str) or len(row_hash) != 64:
        raise SessionDecompositionError("consumed row identity differs")


def _validate_result(
    result: dict[str, Any],
    claim: dict[str, Any],
    database: Path,
    expected_database_sha256: str,
) -> None:
    common = {
        "schema_version": "us-spy-session-decomposition-result-v1",
        "research_id": RESEARCH_ID,
        "classification": CLASSIFICATION,
        "claim_sha256": hashlib.sha256(_canonical(claim)).hexdigest(),
        "repository_identity": {
            "commit": claim["definition_commit"],
            "tree": claim["definition_tree"],
            "files_sha256": claim["files_sha256"],
        },
        "boundaries": _boundaries(),
    }
    if any(result.get(key) != value for key, value in common.items()):
        raise SessionDecompositionError("partial result identity differs")
    if result.get("status") == "EXECUTION_ERROR_CONSUMED":
        if set(result) != set(common) | {
            "status",
            "reason_class",
            "input_identity",
            "periods",
            "adjudication",
        }:
            raise SessionDecompositionError("execution-error result schema differs")
        if not isinstance(result.get("reason_class"), str) or not result["reason_class"]:
            raise SessionDecompositionError("execution-error reason is missing")
        if result.get("input_identity") != _base_error_input(
            database, expected_database_sha256
        ) or result.get("periods") is not None or result.get("adjudication") is not None:
            raise SessionDecompositionError("execution-error result payload differs")
        return
    if result.get("status") not in TERMINAL_OUTCOME_STATUSES:
        raise SessionDecompositionError("result status is not allowed")
    if set(result) != set(common) | {
        "status",
        "input_identity",
        "dominant_session_zero_cost_combined",
        "periods",
        "adjudication",
    }:
        raise SessionDecompositionError("outcome result schema differs")
    _validate_success_input(result.get("input_identity"), database, expected_database_sha256)
    _validate_periods(result.get("periods"))
    adjudication = adjudicate(result["periods"], 0)
    if result.get("adjudication") != adjudication or result["status"] != adjudication["status"]:
        raise SessionDecompositionError("result adjudication differs")
    zero = result["periods"]["combined_validation_holdout"]["0"]
    overnight_log = math.log1p(zero["B2_SPY_OVERNIGHT"]["cumulative_net_return"])
    intraday_log = math.log1p(zero["B3_SPY_INTRADAY"]["cumulative_net_return"])
    dominant = (
        "OVERNIGHT"
        if overnight_log > intraday_log
        else "INTRADAY" if intraday_log > overnight_log else "TIE"
    )
    if result.get("dominant_session_zero_cost_combined") != {
        "status": dominant,
        "overnight_log_return": overnight_log,
        "intraday_log_return": intraday_log,
    }:
        raise SessionDecompositionError("dominant-session result differs")


def _final_receipt(
    result: dict[str, Any],
    result_bytes: bytes,
    claim: dict[str, Any],
    *,
    recovered: bool,
    discarded_partial_result_sha256: str | None,
) -> dict[str, Any]:
    return {
        "schema_version": "us-spy-session-decomposition-run-v1",
        "research_id": RESEARCH_ID,
        "status": "CONSUMED_RETROSPECTIVE_DIAGNOSTIC_RUN",
        "result_status": result["status"],
        "result_sha256": hashlib.sha256(result_bytes).hexdigest(),
        "definition_commit": claim["definition_commit"],
        "definition_tree": claim["definition_tree"],
        "files_sha256": claim["files_sha256"],
        "database_filename": claim["database_filename"],
        "expected_database_sha256": claim["expected_database_sha256"],
        "claim_sha256": hashlib.sha256(_canonical(claim)).hexdigest(),
        "claimed_at_utc": claim["claimed_at_utc"],
        "provider_or_network_used": False,
        "database_write_performed": False,
        "strategy_candidate_available": False,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "recovered_partial_publication": recovered,
        "discarded_partial_result_sha256": discarded_partial_result_sha256,
    }


def _run(
    database: Path, expected_database_sha256: str
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if _exists_or_symlink(RESULT) or _exists_or_symlink(RECEIPT):
        raise SessionDecompositionError("one-use output already exists")
    commit, tree, file_hashes = _execution_identity(expected_database_sha256)
    descriptor, metadata = _preflight_input(database, expected_database_sha256)
    claim = _claim_payload(database, expected_database_sha256, commit, tree, file_hashes)
    claim_bytes = _canonical(claim)
    claim_sha256 = hashlib.sha256(claim_bytes).hexdigest()
    try:
        _exclusive_write(RECEIPT, claim_bytes)
    except BaseException:
        os.close(descriptor)
        raise
    try:
        data_identity, selected_splits = _qualify_claimed_input(database, descriptor, metadata)
        periods: dict[str, Any] = {}
        for split in ("development", "validation", "retrospective_holdout"):
            selected = selected_splits[split]
            periods[split] = {
                str(cost): {account: simulate(selected, account, cost) for account in ACCOUNTS}
                for cost in COSTS
            }
        combined_segments = (
            selected_splits["validation"],
            selected_splits["retrospective_holdout"],
        )
        periods["combined_validation_holdout"] = {
            str(cost): {
                account: simulate_segmented(combined_segments, account, cost)
                for account in ACCOUNTS
            }
            for cost in COSTS
        }
        adjudication = adjudicate(periods, 0)
        zero = periods["combined_validation_holdout"]["0"]
        overnight_log = math.log1p(zero["B2_SPY_OVERNIGHT"]["cumulative_net_return"])
        intraday_log = math.log1p(zero["B3_SPY_INTRADAY"]["cumulative_net_return"])
        dominant = (
            "OVERNIGHT"
            if overnight_log > intraday_log
            else "INTRADAY" if intraday_log > overnight_log else "TIE"
        )
        descriptor_identity = data_identity["database_descriptor_identity"]
        captured_identity = (
            descriptor_identity["device"],
            descriptor_identity["inode"],
            descriptor_identity["size"],
            descriptor_identity["mtime_ns"],
        )
        _verify_database_capture(
            database, descriptor, expected_database_sha256, captured_identity
        )
        result_input = {
            **data_identity,
            "database_sha256_before": expected_database_sha256,
            "database_sha256_after": expected_database_sha256,
            "database_unchanged": True,
        }
        result = {
            "schema_version": "us-spy-session-decomposition-result-v1",
            "research_id": RESEARCH_ID,
            "status": adjudication["status"],
            "classification": CLASSIFICATION,
            "claim_sha256": claim_sha256,
            "repository_identity": {
                "commit": commit,
                "tree": tree,
                "files_sha256": file_hashes,
            },
            "input_identity": result_input,
            "dominant_session_zero_cost_combined": {
                "status": dominant,
                "overnight_log_return": overnight_log,
                "intraday_log_return": intraday_log,
            },
            "periods": periods,
            "adjudication": adjudication,
            "boundaries": _boundaries(),
        }
    except (OSError, ArithmeticError, ValueError, duckdb.Error, SessionDecompositionError) as error:
        result = _execution_error_result(
            type(error).__name__,
            claim_sha256,
            database,
            expected_database_sha256,
            commit,
            tree,
            file_hashes,
        )
    finally:
        os.close(descriptor)
    result_bytes = _canonical(result)
    _validate_result(result, claim, database, expected_database_sha256)
    receipt = _final_receipt(
        result,
        result_bytes,
        claim,
        recovered=False,
        discarded_partial_result_sha256=None,
    )
    return result, receipt, claim


def _recover_partial_publication(
    database: Path, expected_database_sha256: str
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    result_exists = _exists_or_symlink(RESULT)
    receipt_exists = _exists_or_symlink(RECEIPT)
    if not result_exists and not receipt_exists:
        return None
    if not receipt_exists:
        raise SessionDecompositionError("result exists without its one-use receipt")
    allowed = tuple(path for path in (RESULT, RECEIPT) if _exists_or_symlink(path))
    commit, tree, file_hashes = _execution_identity(expected_database_sha256, allowed)
    descriptor, metadata = _preflight_input(database, expected_database_sha256)
    try:
        claim, claim_raw = _capture_json(RECEIPT, require_canonical=True)
        if claim.get("status") != "CLAIMED_RETROSPECTIVE_DIAGNOSTIC_RUN":
            raise SessionDecompositionError("one-use outcome was already consumed")
        _validate_claim(
            claim, database, expected_database_sha256, commit, tree, file_hashes
        )
        claim_sha256 = hashlib.sha256(claim_raw).hexdigest()
        discarded_partial_result_sha256 = None
        captured_result_identity = None
        if result_exists:
            partial_bytes, captured_result_identity = _capture_regular_file_with_identity(RESULT)
            discarded_partial_result_sha256 = hashlib.sha256(partial_bytes).hexdigest()
        result = _execution_error_result(
            "InterruptedAfterClaim",
            claim_sha256,
            database,
            expected_database_sha256,
            commit,
            tree,
            file_hashes,
        )
        result_bytes = _canonical(result)
        if captured_result_identity is None:
            _exclusive_write(RESULT, result_bytes)
        else:
            _replace_captured_file(RESULT, result_bytes, captured_result_identity)
        _validate_result(result, claim, database, expected_database_sha256)
        descriptor_identity = metadata["database_descriptor_identity"]
        captured_identity = (
            descriptor_identity["device"],
            descriptor_identity["inode"],
            descriptor_identity["size"],
            descriptor_identity["mtime_ns"],
        )
        _verify_database_capture(
            database, descriptor, expected_database_sha256, captured_identity
        )
        finalized = _final_receipt(
            result,
            result_bytes,
            claim,
            recovered=True,
            discarded_partial_result_sha256=discarded_partial_result_sha256,
        )
        _finalize_claim(RECEIPT, _canonical(finalized), claim, result_bytes)
    finally:
        os.close(descriptor)
    return result, finalized


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--database", type=Path)
    parser.add_argument("--expected-database-sha256")
    arguments = parser.parse_args(argv)
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
        raise SessionDecompositionError("--execute requires database and expected SHA-256")
    if len(arguments.expected_database_sha256) != 64:
        raise SessionDecompositionError("expected database SHA-256 must have 64 characters")
    expected_database_sha256 = arguments.expected_database_sha256.lower()
    database = Path(os.path.abspath(arguments.database))
    recovered = _recover_partial_publication(database, expected_database_sha256)
    if recovered is None:
        result, receipt, claim = _run(database, expected_database_sha256)
    else:
        result, receipt = recovered
    result_bytes = _canonical(result)
    receipt["result_sha256"] = hashlib.sha256(result_bytes).hexdigest()
    if recovered is None:
        _exclusive_write(RESULT, result_bytes)
        _finalize_claim(RECEIPT, _canonical(receipt), claim, result_bytes)
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
