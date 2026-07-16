#!/usr/bin/env python3
"""One-use retrospective qfq screen for the frozen A-share RS strategy.

This deliberately narrow adapter is not a PIT data adapter.  It consumes one
hash-bound provider-hindsight qfq snapshot, opens DuckDB read-only, and emits an
aggregate-only historical screening report.  It cannot promote the parent
preregistration or open its prospective-forward outcomes.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import date
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import sys
from typing import Any, Iterator

import duckdb


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from quant_system.backtest.portfolio import Portfolio  # noqa: E402
from quant_system.markets.a_share import AShareBar, decide_fill  # noqa: E402
from quant_system.research import relative_strength as rs  # noqa: E402


AMENDMENT_RUN_ID = "A_SHARE_RELATIVE_STRENGTH_HISTORICAL_SECONDARY_SCREEN_V1_20260716"
CONSUMED_EXECUTION_RUN_IDS = frozenset(
    {
        AMENDMENT_RUN_ID,
        "A_SHARE_RELATIVE_STRENGTH_HISTORICAL_SECONDARY_SCREEN_V2_20260716",
    }
)
CLASSIFICATION = "RETROSPECTIVE_PERSONAL_RESEARCH_GRADE_SECONDARY_NOT_STRICT_PIT"
AMENDMENT = ROOT / (
    "research/definitions/a_share_relative_strength_historical_secondary_screen_v1.json"
)
AMENDMENT_SHA256 = "72621319dcc24c67bb02f56eda2f972320026dd89c3d5bbb96de0962d7038a1e"
PREREGISTRATION = ROOT / rs.DEFINITION_PATH
TABLE = "a_share.a_share_canonical_daily_bars"
START = date(2018, 1, 2)
END = date(2026, 6, 30)
HEX = frozenset("0123456789abcdef")
COMMON_PREFIXES = (
    ("SH", ("600", "601", "603", "605", "688")),
    ("SZ", ("000", "001", "002", "003", "300", "301")),
)
REQUIRED_COLUMNS = (
    "snapshot_id", "ts_code", "trade_date", "open", "close", "vol", "amount",
    "adj_factor", "qfq_open", "qfq_close", "is_st", "is_suspended", "up_limit",
    "down_limit", "list_status", "quality_status", "source", "row_hash",
    "synthetic_data",
)
VOLUME_UNIT = "SHARES"
AMOUNT_UNIT = "CNY"


class SecondaryScreenError(ValueError):
    """The secondary snapshot or frozen screen contract is unusable."""


class PrecheckBlockedError(SecondaryScreenError):
    """The benchmark cannot enter before strategy outcomes are opened."""

    def __init__(self, preflight: "BenchmarkPreflight") -> None:
        super().__init__("benchmark initial-entry preflight blocked")
        self.preflight = preflight


@dataclass(frozen=True)
class SecondaryFeature:
    session_date: date
    symbol: str
    relative_60: float
    relative_120: float
    volatility_20: float


@dataclass(frozen=True)
class SecondaryTarget:
    variant_id: str
    signal_date: date
    execution_date: date
    base_eligible_count: int
    ranked_candidate_count: int
    selected_symbols: tuple[str, ...]


@dataclass(frozen=True)
class SecondaryExecutionBar:
    symbol: str
    session_date: date
    qfq_open: float
    prior_qfq_close: float
    is_suspended: bool
    qfq_up_limit: float
    qfq_down_limit: float
    prior_volume_shares: float
    prior_amount_cny: float


@dataclass(frozen=True)
class SecondaryBenchmarkBar:
    session_date: date
    qfq_open: float
    prior_qfq_close: float
    is_suspended: bool
    prior_volume_shares: float
    prior_amount_cny: float


@dataclass(frozen=True)
class AdapterReceipt:
    side: str
    requested_shares: float
    filled_shares: float
    price: float | None
    reason: str


@dataclass(frozen=True)
class BenchmarkPreflight:
    benchmark_initial_entry_filled: bool
    benchmark_invested_ratio: float
    capacity_rejection_ratio: float
    unexpected_exception_count: int
    benchmark_preflight_attempt_count: int

    def __post_init__(self) -> None:
        if type(self.benchmark_initial_entry_filled) is not bool:
            raise SecondaryScreenError("benchmark fill flag must be boolean")
        for name in ("benchmark_invested_ratio", "capacity_rejection_ratio"):
            value = getattr(self, name)
            if not isinstance(value, float) or not math.isfinite(value) or not 0 <= value <= 1:
                raise SecondaryScreenError(f"{name} must be a finite ratio")
        if type(self.unexpected_exception_count) is not int or self.unexpected_exception_count < 0:
            raise SecondaryScreenError("unexpected exception count must be nonnegative integer")
        if type(self.benchmark_preflight_attempt_count) is not int or self.benchmark_preflight_attempt_count <= 0:
            raise SecondaryScreenError("benchmark preflight attempt count must be positive integer")

    @property
    def passed(self) -> bool:
        return self.benchmark_initial_entry_filled and self.unexpected_exception_count == 0


def _digest(value: object, label: str) -> str:
    text = str(value)
    if len(text) != 64 or any(char not in HEX for char in text):
        raise SecondaryScreenError(f"{label} must be lowercase SHA-256")
    return text


def _execution_run_id(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > 128
        or not value.isascii()
        or any(not (char.isalnum() or char in "_-") for char in value)
    ):
        raise SecondaryScreenError("execution run_id must be nonempty canonical ASCII")
    if value in CONSUMED_EXECUTION_RUN_IDS:
        raise SecondaryScreenError("execution run_id has already been consumed")
    return value


def _finite(value: object, label: str, *, positive: bool = False) -> float:
    if isinstance(value, bool):
        raise SecondaryScreenError(f"{label} must be finite numeric")
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise SecondaryScreenError(f"{label} must be finite numeric") from exc
    if not math.isfinite(parsed) or (positive and parsed <= 0):
        raise SecondaryScreenError(f"{label} must be {'positive ' if positive else ''}finite")
    return parsed


def _yyyymmdd(value: object, label: str = "trade_date") -> date:
    if not isinstance(value, str) or len(value) != 8 or not value.isascii() or not value.isdigit():
        raise SecondaryScreenError(f"{label} must be strict YYYYMMDD text")
    try:
        parsed = date(int(value[:4]), int(value[4:6]), int(value[6:8]))
    except ValueError as exc:
        raise SecondaryScreenError(f"{label} must be a real YYYYMMDD date") from exc
    if parsed.strftime("%Y%m%d") != value:
        raise SecondaryScreenError(f"{label} must use canonical YYYYMMDD text")
    return parsed


def _date_text(value: date) -> str:
    if type(value) is not date:
        raise SecondaryScreenError("date value is invalid")
    return value.strftime("%Y%m%d")


def _strict_json(raw: bytes, label: str) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise SecondaryScreenError(f"{label} contains duplicate JSON keys")
            result[key] = value
        return result

    try:
        value = json.loads(
            raw,
            object_pairs_hook=pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                SecondaryScreenError(f"{label} contains nonfinite {token}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SecondaryScreenError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise SecondaryScreenError(f"{label} must be a JSON object")
    return value


def _capture(path: Path) -> tuple[bytes, os.stat_result]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise SecondaryScreenError(f"cannot open immutable input: {path.name}") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise SecondaryScreenError("immutable input must be a regular file")
        blocks: list[bytes] = []
        while block := os.read(descriptor, 1024 * 1024):
            blocks.append(block)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    try:
        current = os.stat(path, follow_symlinks=False)
    except OSError as exc:
        raise SecondaryScreenError("immutable input path changed") from exc
    def signatures(item: os.stat_result) -> tuple[int, int, int, int]:
        return item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns
    if signatures(before) != signatures(after) or (after.st_dev, after.st_ino) != (
        current.st_dev,
        current.st_ino,
    ):
        raise SecondaryScreenError("immutable input changed during capture")
    return b"".join(blocks), after


def _bound_json(path: Path, expected_sha256: str, label: str) -> dict[str, Any]:
    raw, _ = _capture(path)
    if hashlib.sha256(raw).hexdigest() != _digest(expected_sha256, f"{label} SHA-256"):
        raise SecondaryScreenError(f"{label} SHA-256 mismatch")
    return _strict_json(raw, label)


def load_amendment() -> dict[str, Any]:
    amendment = _bound_json(AMENDMENT, AMENDMENT_SHA256, "amendment")
    prereg_raw, _ = _capture(PREREGISTRATION)
    if hashlib.sha256(prereg_raw).hexdigest() != rs.DEFINITION_SHA256:
        raise SecondaryScreenError("parent preregistration bytes changed")
    if (
        amendment.get("run_id") != AMENDMENT_RUN_ID
        or amendment.get("classification") != CLASSIFICATION
    ):
        raise SecondaryScreenError("amendment identity mismatch")
    return amendment


def load_data_manifest(
    path: Path,
    expected_sha256: str,
    execution_run_id: str,
) -> dict[str, Any]:
    run_id = _execution_run_id(execution_run_id)
    value = _bound_json(path, expected_sha256, "data manifest")
    expected = {
        "schema_version": "a-share-rs-secondary-data-manifest-v1",
        "research_id": rs.RESEARCH_ID,
        "run_id": run_id,
        "status": "ACCEPTED_RETROSPECTIVE_SECONDARY_SNAPSHOT",
        "classification": CLASSIFICATION,
        "table": TABLE,
        "strict_pit_eligible": False,
        "strategy_outcomes_opened": False,
        "synthetic_data": False,
        "volume_unit": VOLUME_UNIT,
        "amount_unit": AMOUNT_UNIT,
    }
    if any(value.get(key) != item for key, item in expected.items()):
        raise SecondaryScreenError("data manifest is not accepted for this secondary run")
    if not isinstance(value.get("snapshot_id"), str) or not value["snapshot_id"].strip():
        raise SecondaryScreenError("data manifest snapshot_id is required")
    database = value.get("database")
    coverage = value.get("coverage")
    identity = value.get("identity")
    if not all(isinstance(item, dict) for item in (database, coverage, identity)):
        raise SecondaryScreenError("data manifest identity sections are required")
    _digest(database.get("sha256"), "database SHA-256")
    if type(database.get("size_bytes")) is not int or database["size_bytes"] <= 0:
        raise SecondaryScreenError("database size_bytes must be positive integer")
    if database.get("mode") != "0600":
        raise SecondaryScreenError("database mode must be 0600")
    if coverage.get("start_date") != _date_text(START) or coverage.get("end_date") != _date_text(END):
        raise SecondaryScreenError("manifest coverage must equal the frozen date window")
    for name in ("row_count", "symbol_count", "benchmark_row_count"):
        if type(coverage.get(name)) is not int or coverage[name] <= 0:
            raise SecondaryScreenError(f"coverage {name} must be positive integer")
    _digest(identity.get("ordered_row_hash_sha256"), "ordered row hash")
    partitions = identity.get("partitions")
    if not isinstance(partitions, list) or not partitions:
        raise SecondaryScreenError("manifest partitions are required")
    months = []
    for item in partitions:
        if not isinstance(item, dict) or set(item) != {"month", "row_count", "sha256"}:
            raise SecondaryScreenError("partition identity has invalid shape")
        if not isinstance(item["month"], str) or len(item["month"]) != 6:
            raise SecondaryScreenError("partition month must be YYYYMM")
        if type(item["row_count"]) is not int or item["row_count"] <= 0:
            raise SecondaryScreenError("partition row_count must be positive")
        _digest(item["sha256"], "partition SHA-256")
        months.append(item["month"])
    if months != sorted(set(months)):
        raise SecondaryScreenError("partitions must be unique and ordered")
    return value


def _common_a(symbol: str) -> bool:
    if not isinstance(symbol, str) or "." not in symbol:
        return False
    code, exchange = symbol.split(".", 1)
    return len(code) == 6 and code.isdigit() and any(
        exchange == suffix and code.startswith(prefixes)
        for suffix, prefixes in COMMON_PREFIXES
    )


def select_secondary_targets(
    features: Sequence[SecondaryFeature],
    *,
    signal_date: date,
    execution_date: date,
) -> tuple[SecondaryTarget, ...]:
    frozen = tuple(features)
    if any(not isinstance(item, SecondaryFeature) or item.session_date != signal_date for item in frozen):
        raise SecondaryScreenError("features must be one typed signal-date slice")
    if len({item.symbol for item in frozen}) != len(frozen):
        raise SecondaryScreenError("duplicate feature symbol")
    if len(frozen) < rs.MINIMUM_BASE_ELIGIBLE:
        raise SecondaryScreenError("fewer than 500 base-eligible names")
    values = sorted(_finite(item.volatility_20, "volatility") for item in frozen)
    middle = len(values) // 2
    median = values[middle] if len(values) % 2 else math.fsum(values[middle - 1 : middle + 1]) / 2
    results = []
    for variant in rs.VARIANTS:
        field = "relative_60" if variant.lookback_sessions == 60 else "relative_120"
        candidates = sorted(
            (
                (item.symbol, _finite(getattr(item, field), "relative strength"))
                for item in frozen
                if _finite(getattr(item, field), "relative strength") > 0
                and (not variant.volatility_filter_enabled or item.volatility_20 <= median)
            ),
            key=lambda item: (-item[1], item[0]),
        )
        if len(candidates) < rs.MAX_POSITIONS:
            raise SecondaryScreenError("fewer than 15 ranked candidates")
        results.append(
            SecondaryTarget(
                variant.variant_id,
                signal_date,
                execution_date,
                len(frozen),
                len(candidates),
                tuple(symbol for symbol, _ in candidates[: rs.MAX_POSITIONS]),
            )
        )
    return tuple(results)


def _lot(value: float) -> float:
    return float(max(0, math.floor(value / rs.BOARD_LOT)) * rs.BOARD_LOT)


def _marks(portfolio: Portfolio, bars: Mapping[str, SecondaryExecutionBar]) -> dict[str, float]:
    marks = {}
    for symbol, position in portfolio.positions.items():
        try:
            bar = bars[symbol]
        except KeyError as exc:
            raise SecondaryScreenError("held symbol lacks an execution bar") from exc
        marks[symbol] = (
            bar.prior_qfq_close
            if bar.is_suspended
            else bar.qfq_open
        )
        if not math.isfinite(marks[symbol]) or marks[symbol] <= 0:
            raise SecondaryScreenError("held symbol lacks a positive secondary mark")
        if position.shares <= 0:
            raise SecondaryScreenError("portfolio contains an invalid holding")
    return marks


def _trade(
    portfolio: Portfolio,
    bar: SecondaryExecutionBar,
    side: str,
    requested: float,
    slippage_bps: float,
) -> AdapterReceipt:
    requested = _lot(requested) if side == "buy" else float(requested)
    if requested <= 0:
        return AdapterReceipt(side, 0.0, 0.0, None, "zero_request")
    decision = decide_fill(
        side,
        AShareBar(
            bar.qfq_open,
            bar.is_suspended,
            bar.qfq_up_limit,
            bar.qfq_down_limit,
            True,
        ),
        slippage_bps=slippage_bps,
    )
    if not decision.filled:
        return AdapterReceipt(side, requested, 0.0, None, decision.reason)
    assert decision.price is not None
    if requested > bar.prior_volume_shares * 0.01 or requested * decision.price > bar.prior_amount_cny * 0.01:
        return AdapterReceipt(side, requested, 0.0, None, "capacity")
    filled = requested
    if side == "buy":
        affordable = _lot(
            max(0.0, portfolio.available_cash - portfolio.costs.minimum_commission)
            / (1.0 + portfolio.costs.commission_rate)
            / decision.price
        )
        filled = min(requested, affordable)
    if filled <= 0:
        return AdapterReceipt(side, requested, 0.0, None, "insufficient_cash")
    if side == "buy":
        portfolio.buy(bar.symbol, filled, decision.price, bar.session_date)
    else:
        portfolio.sell(bar.symbol, filled, decision.price, bar.session_date)
    return AdapterReceipt(side, requested, filled, decision.price, "filled")


def secondary_rebalance(
    portfolio: Portfolio,
    ranked_symbols: Sequence[str],
    bars: Mapping[str, SecondaryExecutionBar],
    *,
    slippage_bps: float,
) -> tuple[AdapterReceipt, ...]:
    ranked = tuple(ranked_symbols)
    if len(ranked) != rs.MAX_POSITIONS or len(set(ranked)) != len(ranked):
        raise SecondaryScreenError("ranked target must contain exactly 15 unique symbols")
    portfolio.start_session(next(iter(bars.values())).session_date)
    receipts: list[AdapterReceipt] = []
    target = set(ranked)
    for symbol in sorted(set(portfolio.positions) - target):
        receipts.append(
            _trade(portfolio, bars[symbol], "sell", portfolio.positions[symbol].shares, slippage_bps)
        )
    trapped = {
        symbol: portfolio.positions[symbol].shares * _marks(portfolio, bars)[symbol]
        for symbol in sorted(set(portfolio.positions) - target)
    }
    nav = portfolio.nav(_marks(portfolio, bars))
    allocation = rs.residual_target_weights(ranked, trapped, nav=nav)
    weights = dict(allocation.target_weights)
    desired = {
        symbol: _lot(nav * weights.get(symbol, 0.0) / bars[symbol].qfq_open)
        for symbol in allocation.admitted_symbols
    }
    desired.update({symbol: 0.0 for symbol in portfolio.positions if symbol not in desired})
    for side in ("sell", "buy"):
        for symbol in sorted(desired):
            current = portfolio.positions.get(symbol)
            shares = 0.0 if current is None else current.shares
            delta = desired[symbol] - shares
            if side == "sell" and delta < -1e-9:
                receipts.append(_trade(portfolio, bars[symbol], side, -delta, slippage_bps))
            elif side == "buy" and delta > 1e-9:
                if symbol not in portfolio.positions and len(portfolio.positions) >= rs.MAX_POSITIONS:
                    receipts.append(AdapterReceipt(side, delta, 0.0, None, "max_positions"))
                else:
                    receipts.append(_trade(portfolio, bars[symbol], side, delta, slippage_bps))
    return tuple(receipts)


@contextmanager
def _read_only_connection(path: Path) -> Iterator[duckdb.DuckDBPyConnection]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    before = os.fstat(descriptor)
    connection: duckdb.DuckDBPyConnection | None = None
    try:
        connection = duckdb.connect(f"/proc/self/fd/{descriptor}", read_only=True)
        connection.execute("SET enable_external_access = false")
        yield connection
    finally:
        try:
            if connection is not None:
                connection.close()
            after = os.fstat(descriptor)
            current = os.stat(path, follow_symlinks=False)
        finally:
            os.close(descriptor)

        def signature(item: os.stat_result) -> tuple[int, int, int, int]:
            return item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns

        if signature(before) != signature(after) or (after.st_dev, after.st_ino) != (
            current.st_dev,
            current.st_ino,
        ):
            raise SecondaryScreenError("database changed during read-only run")


def _database_identity(path: Path) -> tuple[str, int, str]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise SecondaryScreenError("database must be a regular file")
        digest = hashlib.sha256()
        while block := os.read(descriptor, 1024 * 1024):
            digest.update(block)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    current = os.stat(path, follow_symlinks=False)
    def signature(item: os.stat_result) -> tuple[int, int, int, int]:
        return item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns

    if signature(before) != signature(after) or (after.st_dev, after.st_ino) != (
        current.st_dev,
        current.st_ino,
    ):
        raise SecondaryScreenError("database changed during hashing")
    return digest.hexdigest(), after.st_size, f"{stat.S_IMODE(after.st_mode):04o}"


def _verify_snapshot(
    connection: duckdb.DuckDBPyConnection,
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    column_rows = tuple(
        (row[0], str(row[1]).upper())
        for row in connection.execute(
            "SELECT column_name, data_type FROM duckdb_columns() "
            "WHERE schema_name='a_share' AND table_name='a_share_canonical_daily_bars' "
            "ORDER BY column_index"
        ).fetchall()
    )
    columns = tuple(row[0] for row in column_rows)
    if any(name not in columns for name in REQUIRED_COLUMNS):
        raise SecondaryScreenError("canonical table lacks a required column")
    if dict(column_rows).get("trade_date") != "VARCHAR":
        raise SecondaryScreenError("canonical trade_date must be VARCHAR YYYYMMDD")
    snapshot = manifest["snapshot_id"]
    malformed_dates = connection.execute(
        f"""
        SELECT count(*) FROM {TABLE} WHERE snapshot_id=? AND (
          trade_date IS NULL OR NOT regexp_full_match(trade_date, '[0-9]{{8}}')
          OR try_strptime(trade_date, '%Y%m%d') IS NULL
          OR strftime(try_strptime(trade_date, '%Y%m%d'), '%Y%m%d')<>trade_date
        )
        """,
        [snapshot],
    ).fetchone()[0]
    if malformed_dates:
        raise SecondaryScreenError("snapshot contains malformed or mixed trade_date values")
    aggregate = connection.execute(
        f"""
        SELECT count(*), count(DISTINCT ts_code), min(trade_date), max(trade_date),
               sum(CASE WHEN ts_code=? THEN 1 ELSE 0 END),
               sum(CASE WHEN synthetic_data THEN 1 ELSE 0 END),
               sum(CASE WHEN qfq_open IS NULL OR qfq_open<=0 OR qfq_close IS NULL
                             OR qfq_close<=0 OR adj_factor IS NULL OR adj_factor<=0
                             OR vol IS NULL OR vol<0 OR amount IS NULL OR amount<0
                             OR is_st IS NULL OR is_suspended IS NULL
                             OR (regexp_full_match(
                                  ts_code,
                                  '(600|601|603|605|688)[0-9]{{3}}[.]SH|(000|001|002|003|300|301)[0-9]{{3}}[.]SZ'
                                ) AND (
                                  up_limit IS NULL OR up_limit<=0
                                  OR down_limit IS NULL OR down_limit<=0))
                             OR row_hash IS NULL OR length(row_hash)<>64
                        THEN 1 ELSE 0 END)
        FROM {TABLE} WHERE snapshot_id=?
        """,
        [rs.BENCHMARK_SYMBOL, snapshot],
    ).fetchone()
    assert aggregate is not None
    coverage = manifest["coverage"]
    observed = {
        "row_count": int(aggregate[0]),
        "symbol_count": int(aggregate[1]),
        "start_date": str(aggregate[2]),
        "end_date": str(aggregate[3]),
        "benchmark_row_count": int(aggregate[4]),
    }
    if observed != {
        "row_count": coverage["row_count"],
        "symbol_count": coverage["symbol_count"],
        "start_date": coverage["start_date"],
        "end_date": coverage["end_date"],
        "benchmark_row_count": coverage["benchmark_row_count"],
    }:
        raise SecondaryScreenError("snapshot coverage differs from manifest")
    if aggregate[5] or aggregate[6]:
        raise SecondaryScreenError("snapshot contains synthetic or incomplete qfq rows")
    duplicates = connection.execute(
        f"""
        SELECT count(*) FROM (
          SELECT ts_code, trade_date FROM {TABLE} WHERE snapshot_id=?
          GROUP BY ts_code, trade_date HAVING count(*)<>1
        )
        """,
        [snapshot],
    ).fetchone()[0]
    missing_benchmark = connection.execute(
        f"""
        SELECT count(*) FROM (
          SELECT DISTINCT trade_date FROM {TABLE} WHERE snapshot_id=?
          EXCEPT
          SELECT trade_date FROM {TABLE} WHERE snapshot_id=? AND ts_code=?
        )
        """,
        [snapshot, snapshot, rs.BENCHMARK_SYMBOL],
    ).fetchone()[0]
    if duplicates or missing_benchmark:
        raise SecondaryScreenError("snapshot keys or benchmark coverage are incomplete")
    overall = hashlib.sha256()
    current_month = None
    partition = hashlib.sha256()
    partition_rows = 0
    actual_partitions: list[dict[str, Any]] = []
    cursor = connection.execute(
        f"SELECT trade_date, row_hash FROM {TABLE} "
        "WHERE snapshot_id=? ORDER BY trade_date, ts_code",
        [snapshot],
    )
    while rows := cursor.fetchmany(100_000):
        for trade_date, row_hash in rows:
            row_hash = _digest(row_hash, "row_hash")
            _yyyymmdd(trade_date)
            month = trade_date[:6]
            if current_month is not None and month != current_month:
                actual_partitions.append(
                    {"month": current_month, "row_count": partition_rows, "sha256": partition.hexdigest()}
                )
                partition, partition_rows = hashlib.sha256(), 0
            current_month = month
            encoded = row_hash.encode("ascii")
            overall.update(encoded)
            partition.update(encoded)
            partition_rows += 1
    if current_month is not None:
        actual_partitions.append(
            {"month": current_month, "row_count": partition_rows, "sha256": partition.hexdigest()}
        )
    identity = manifest["identity"]
    if overall.hexdigest() != identity["ordered_row_hash_sha256"]:
        raise SecondaryScreenError("ordered row identity changed")
    if actual_partitions != identity["partitions"]:
        raise SecondaryScreenError("partition identities changed")
    return observed | {
        "partition_count": len(actual_partitions),
        "ordered_row_hash_sha256": overall.hexdigest(),
    }


def _sessions(connection: duckdb.DuckDBPyConnection, snapshot: str) -> tuple[date, ...]:
    rows = connection.execute(
        f"SELECT DISTINCT trade_date FROM {TABLE} "
        "WHERE snapshot_id=? ORDER BY 1",
        [snapshot],
    ).fetchall()
    dates = tuple(_yyyymmdd(row[0]) for row in rows)
    if not dates or dates[0] != START or dates[-1] != END:
        raise SecondaryScreenError("session window is not exact")
    return dates


def _decision_pairs(sessions: tuple[date, ...]) -> tuple[tuple[date, date], ...]:
    first_by_month: dict[tuple[int, int], date] = {}
    index = {day: offset for offset, day in enumerate(sessions)}
    for day in sessions:
        first_by_month.setdefault((day.year, day.month), day)
    pairs = []
    for entry in first_by_month.values():
        if date(2022, 1, 1) <= entry <= date(2026, 5, 31):
            position = index[entry]
            if position == 0:
                raise SecondaryScreenError("first execution lacks a prior signal session")
            pairs.append((sessions[position - 1], entry))
    return tuple(pairs)


def _load_targets(
    connection: duckdb.DuckDBPyConnection,
    snapshot: str,
    sessions: tuple[date, ...],
) -> dict[tuple[date, str], SecondaryTarget]:
    pairs = _decision_pairs(sessions)
    signal_dates = tuple(item[0] for item in pairs)
    placeholders = ",".join("?" for _ in signal_dates)
    sql = f"""
    WITH base AS (
      SELECT ts_code, trade_date, qfq_close, amount,
             is_st, is_suspended, list_status,
             dense_rank() OVER (ORDER BY trade_date) AS market_seq
      FROM {TABLE} WHERE snapshot_id=?
    ), lagged AS (
      SELECT *, row_number() OVER (PARTITION BY ts_code ORDER BY trade_date) AS listed_sessions,
             lag(qfq_close,1) OVER w AS close_1,
             lag(qfq_close,60) OVER w AS close_60,
             lag(qfq_close,120) OVER w AS close_120,
             lag(market_seq,20) OVER w AS seq_20,
             lag(market_seq,60) OVER w AS seq_60,
             lag(market_seq,120) OVER w AS seq_120
      FROM base WINDOW w AS (PARTITION BY ts_code ORDER BY trade_date)
    ), metrics AS (
      SELECT *, median(amount) OVER (PARTITION BY ts_code ORDER BY trade_date
                  ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS amount20,
             stddev_samp(qfq_close/close_1-1) OVER (PARTITION BY ts_code ORDER BY trade_date
                  ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS vol20
      FROM lagged
    ), benchmark AS (
      SELECT trade_date, qfq_close/close_60 AS factor60, qfq_close/close_120 AS factor120
      FROM metrics WHERE ts_code=?
    )
    SELECT m.trade_date, m.ts_code,
           (m.qfq_close/m.close_60)/b.factor60-1 AS relative60,
           (m.qfq_close/m.close_120)/b.factor120-1 AS relative120,
           m.vol20
    FROM metrics m JOIN benchmark b USING(trade_date)
    WHERE m.trade_date IN ({placeholders}) AND m.ts_code<>?
      AND m.listed_sessions>=252 AND m.market_seq-m.seq_20=20
      AND m.market_seq-m.seq_60=60 AND m.market_seq-m.seq_120=120
      AND m.amount20>=? AND m.list_status='L' AND NOT m.is_st AND NOT m.is_suspended
    ORDER BY m.trade_date,m.ts_code
    """
    rows = connection.execute(
        sql,
        [
            snapshot,
            rs.BENCHMARK_SYMBOL,
            *(_date_text(day) for day in signal_dates),
            rs.BENCHMARK_SYMBOL,
            rs.MINIMUM_AMOUNT_CNY,
        ],
    ).fetchall()
    grouped: dict[date, list[SecondaryFeature]] = {day: [] for day in signal_dates}
    for session_text, symbol, relative60, relative120, volatility in rows:
        session_date = _yyyymmdd(session_text)
        if not _common_a(symbol):
            continue
        grouped[session_date].append(
            SecondaryFeature(
                session_date,
                symbol,
                _finite(relative60, "relative60"),
                _finite(relative120, "relative120"),
                _finite(volatility, "volatility20"),
            )
        )
    targets: dict[tuple[date, str], SecondaryTarget] = {}
    for signal_date, execution_date in pairs:
        for target in select_secondary_targets(
            grouped[signal_date], signal_date=signal_date, execution_date=execution_date
        ):
            targets[(signal_date, target.variant_id)] = target
    return targets


def _execution_bars(
    connection: duckdb.DuckDBPyConnection,
    snapshot: str,
    session_date: date,
    prior_date: date,
    symbols: Sequence[str],
) -> dict[str, SecondaryExecutionBar]:
    frozen = tuple(sorted(set(symbols)))
    if not frozen:
        raise SecondaryScreenError("execution requires symbols")
    placeholders = ",".join("?" for _ in frozen)
    rows = connection.execute(
        f"""
        SELECT c.ts_code,c.qfq_open,p.qfq_close,c.is_suspended,
               c.up_limit/c.adj_factor,c.down_limit/c.adj_factor,p.vol,p.amount
        FROM {TABLE} c JOIN {TABLE} p ON p.snapshot_id=c.snapshot_id
          AND p.ts_code=c.ts_code AND p.trade_date=?
        WHERE c.snapshot_id=? AND c.trade_date=?
          AND c.ts_code IN ({placeholders})
        ORDER BY c.ts_code
        """,
        [_date_text(prior_date), snapshot, _date_text(session_date), *frozen],
    ).fetchall()
    if len(rows) != len(frozen):
        raise SecondaryScreenError("execution panel has missing symbols")
    result = {}
    for symbol, opened, prior_close, suspended, upper, lower, volume, amount in rows:
        result[symbol] = SecondaryExecutionBar(
            symbol,
            session_date,
            _finite(opened, "qfq_open", positive=True),
            _finite(prior_close, "prior_qfq_close", positive=True),
            suspended if type(suspended) is bool else bool(suspended),
            _finite(upper, "qfq_up_limit", positive=True),
            _finite(lower, "qfq_down_limit", positive=True),
            _finite(volume, "prior volume"),
            _finite(amount, "prior amount"),
        )
    return result


def _benchmark_bar(
    connection: duckdb.DuckDBPyConnection,
    snapshot: str,
    session_date: date,
    prior_date: date,
) -> SecondaryBenchmarkBar:
    row = connection.execute(
        f"""
        SELECT c.qfq_open,p.qfq_close,c.is_suspended,p.vol,p.amount
        FROM {TABLE} c JOIN {TABLE} p ON p.snapshot_id=c.snapshot_id
          AND p.ts_code=c.ts_code AND p.trade_date=?
        WHERE c.snapshot_id=? AND c.trade_date=? AND c.ts_code=?
        """,
        [
            _date_text(prior_date),
            snapshot,
            _date_text(session_date),
            rs.BENCHMARK_SYMBOL,
        ],
    ).fetchall()
    if len(row) != 1:
        raise SecondaryScreenError("benchmark execution row is missing or duplicated")
    opened, prior_close, suspended, volume, amount = row[0]
    if type(suspended) is not bool:
        raise SecondaryScreenError("benchmark suspension flag must be boolean")
    return SecondaryBenchmarkBar(
        session_date,
        _finite(opened, "benchmark qfq_open", positive=True),
        _finite(prior_close, "benchmark prior qfq_close", positive=True),
        suspended,
        _finite(volume, "benchmark prior volume"),
        _finite(amount, "benchmark prior amount"),
    )


def _benchmark_mark(portfolio: Portfolio, bar: SecondaryBenchmarkBar) -> float:
    if not portfolio.positions:
        return portfolio.available_cash
    mark = bar.prior_qfq_close if bar.is_suspended else bar.qfq_open
    return portfolio.nav({rs.BENCHMARK_SYMBOL: mark})


def _benchmark_buy(
    portfolio: Portfolio,
    bar: SecondaryBenchmarkBar,
    slippage_bps: float,
) -> AdapterReceipt:
    portfolio.start_session(bar.session_date)
    if bar.is_suspended:
        return AdapterReceipt("buy", 0.0, 0.0, None, "suspended")
    fill_price = bar.qfq_open * (1.0 + slippage_bps / 10_000.0)
    requested = _lot(rs.INITIAL_CASH_CNY / bar.qfq_open)
    if requested > bar.prior_volume_shares * 0.01 or requested * fill_price > bar.prior_amount_cny * 0.01:
        return AdapterReceipt("buy", requested, 0.0, None, "capacity")
    affordable = _lot(
        max(0.0, portfolio.available_cash - portfolio.costs.minimum_commission)
        / (1.0 + portfolio.costs.commission_rate)
        / fill_price
    )
    filled = min(requested, affordable)
    if filled <= 0:
        return AdapterReceipt("buy", requested, 0.0, None, "insufficient_cash")
    portfolio.buy(rs.BENCHMARK_SYMBOL, filled, fill_price, bar.session_date)
    return AdapterReceipt("buy", requested, filled, fill_price, "filled")


def _benchmark_preflight(
    connection: duckdb.DuckDBPyConnection,
    snapshot: str,
    sessions: tuple[date, ...],
) -> BenchmarkPreflight:
    positions = {day: offset for offset, day in enumerate(sessions)}
    scenarios: list[tuple[date, float]] = []
    for split_id in rs.HISTORICAL_GATED_SPLITS:
        intervals = _split_intervals(sessions, split_id)
        if not intervals:
            raise SecondaryScreenError("benchmark preflight split has no complete interval")
        entry_date = intervals[0][1]
        scenarios.extend((entry_date, slippage) for slippage in rs.SLIPPAGE_SCENARIOS_BPS)
    filled_flags: list[bool] = []
    invested_ratios: list[float] = []
    capacity_rejections = 0
    unexpected_exceptions = 0
    for entry_date, slippage_bps in scenarios:
        try:
            bar = _benchmark_bar(
                connection,
                snapshot,
                entry_date,
                sessions[positions[entry_date] - 1],
            )
            portfolio = rs.new_strategy_portfolio()
            receipt = _benchmark_buy(portfolio, bar, slippage_bps)
            filled = (
                receipt.reason == "filled"
                and receipt.filled_shares > 0
                and receipt.price is not None
                and rs.BENCHMARK_SYMBOL in portfolio.positions
            )
            filled_flags.append(filled)
            invested_ratios.append(
                receipt.filled_shares * receipt.price / rs.INITIAL_CASH_CNY
                if filled and receipt.price is not None
                else 0.0
            )
            capacity_rejections += int(receipt.reason == "capacity")
        except Exception:
            filled_flags.append(False)
            invested_ratios.append(0.0)
            unexpected_exceptions += 1
    attempts = len(scenarios)
    return BenchmarkPreflight(
        benchmark_initial_entry_filled=all(filled_flags),
        benchmark_invested_ratio=float(min(invested_ratios)),
        capacity_rejection_ratio=float(capacity_rejections / attempts),
        unexpected_exception_count=unexpected_exceptions,
        benchmark_preflight_attempt_count=attempts,
    )


def _preflight_payload(preflight: BenchmarkPreflight) -> dict[str, Any]:
    return asdict(preflight)


def _split_intervals(
    sessions: tuple[date, ...], split_id: str
) -> tuple[tuple[date, date, date], ...]:
    split = next(item for item in rs.SPLITS if item.split_id == split_id)
    positions = {day: offset for offset, day in enumerate(sessions)}
    first_by_month: dict[tuple[int, int], date] = {}
    for day in sessions:
        first_by_month.setdefault((day.year, day.month), day)
    entries = tuple(day for day in first_by_month.values() if split.contains(day))
    result = []
    for entry, exit_date in zip(entries, entries[1:]):
        if split.contains(exit_date):
            result.append((sessions[positions[entry] - 1], entry, exit_date))
    return tuple(result)


def _retry_blocked_exits(
    connection: duckdb.DuckDBPyConnection,
    snapshot: str,
    sessions: tuple[date, ...],
    portfolio: Portfolio,
    blocked: set[str],
    start: date,
    end: date,
    slippage_bps: float,
    receipts: list[AdapterReceipt],
) -> None:
    positions = {day: offset for offset, day in enumerate(sessions)}
    for session_date in sessions[positions[start] + 1 : positions[end]]:
        if not blocked:
            return
        prior = sessions[positions[session_date] - 1]
        bars = _execution_bars(connection, snapshot, session_date, prior, tuple(blocked))
        portfolio.start_session(session_date)
        for symbol in tuple(sorted(blocked)):
            if symbol not in portfolio.positions:
                blocked.remove(symbol)
                continue
            receipt = _trade(
                portfolio,
                bars[symbol],
                "sell",
                portfolio.positions[symbol].shares,
                slippage_bps,
            )
            receipts.append(receipt)
            if receipt.filled_shares:
                blocked.remove(symbol)


def _simulate_one(
    connection: duckdb.DuckDBPyConnection,
    snapshot: str,
    sessions: tuple[date, ...],
    targets: Mapping[tuple[date, str], SecondaryTarget],
    *,
    variant_id: str,
    split_id: str,
    slippage_bps: float,
) -> tuple[tuple[rs.AssignedObservation, ...], rs.GatedDecisionLedger, dict[str, int]]:
    intervals = _split_intervals(sessions, split_id)
    if not intervals:
        raise SecondaryScreenError("split has no complete holding intervals")
    positions = {day: offset for offset, day in enumerate(sessions)}
    strategy = rs.new_strategy_portfolio()
    benchmark = rs.new_strategy_portfolio()
    blocked: set[str] = set()
    observations = []
    audits = []
    receipt_counts: Counter[str] = Counter()
    for interval_index, (signal_date, entry_date, exit_date) in enumerate(intervals):
        target = targets[(signal_date, variant_id)]
        blocked &= set(strategy.positions)
        blocked -= set(target.selected_symbols)
        symbols = set(target.selected_symbols) | set(strategy.positions)
        prior_entry = sessions[positions[entry_date] - 1]
        entry_bars = _execution_bars(
            connection,
            snapshot,
            entry_date,
            prior_entry,
            tuple(symbols),
        )
        benchmark_bar = _benchmark_bar(
            connection,
            snapshot,
            entry_date,
            prior_entry,
        )
        start_nav = strategy.nav(_marks(strategy, entry_bars)) if strategy.positions else strategy.available_cash
        receipts = list(
            secondary_rebalance(
                strategy,
                target.selected_symbols,
                entry_bars,
                slippage_bps=slippage_bps,
            )
        )
        blocked.update(
            symbol
            for symbol in set(strategy.positions) - set(target.selected_symbols)
        )
        benchmark_start = (
            _benchmark_mark(benchmark, benchmark_bar)
            if benchmark.positions
            else benchmark.available_cash
        )
        if interval_index == 0:
            receipt = _benchmark_buy(benchmark, benchmark_bar, slippage_bps)
            receipt_counts[f"benchmark:{receipt.reason}"] += 1
            if receipt.reason != "filled" or receipt.filled_shares <= 0:
                raise SecondaryScreenError("benchmark initial entry diverged from preflight")
        _retry_blocked_exits(
            connection,
            snapshot,
            sessions,
            strategy,
            blocked,
            entry_date,
            exit_date,
            slippage_bps,
            receipts,
        )
        for receipt in receipts:
            receipt_counts[f"{receipt.side}:{receipt.reason}"] += 1
        exit_symbols = set(strategy.positions)
        prior_exit = sessions[positions[exit_date] - 1]
        exit_bars = (
            _execution_bars(
                connection,
                snapshot,
                exit_date,
                prior_exit,
                tuple(exit_symbols),
            )
            if exit_symbols
            else {}
        )
        benchmark_exit_bar = _benchmark_bar(
            connection,
            snapshot,
            exit_date,
            prior_exit,
        )
        end_nav = strategy.nav(_marks(strategy, exit_bars)) if strategy.positions else strategy.available_cash
        benchmark_end = (
            _benchmark_mark(benchmark, benchmark_exit_bar)
            if benchmark.positions
            else benchmark.available_cash
        )
        observations.append(
            rs.AssignedObservation(
                variant_id,
                split_id,
                signal_date,
                entry_date,
                exit_date,
                end_nav / start_nav - 1.0,
                benchmark_end / benchmark_start - 1.0,
            )
        )
        audits.append(rs.DecisionAudit(signal_date, entry_date, exit_date, True))
    split = next(item for item in rs.SPLITS if item.split_id == split_id)
    ledger = rs.GatedDecisionLedger(
        variant_id,
        split_id,
        split.start,
        split.end,
        tuple(audits),
    )
    return tuple(observations), ledger, dict(receipt_counts)


def execute_screen(
    database: Path,
    manifest: Mapping[str, Any],
    execution_run_id: str,
) -> dict[str, Any]:
    run_id = _execution_run_id(execution_run_id)
    if manifest.get("run_id") != run_id:
        raise SecondaryScreenError("execution run_id differs from data manifest")
    with _read_only_connection(database) as connection:
        source_identity = _verify_snapshot(connection, manifest)
        sessions = _sessions(connection, manifest["snapshot_id"])
        preflight = _benchmark_preflight(connection, manifest["snapshot_id"], sessions)
        if not preflight.passed:
            raise PrecheckBlockedError(preflight)
        targets = _load_targets(connection, manifest["snapshot_id"], sessions)
        gated_observations: list[rs.AssignedObservation] = []
        gated_ledgers: list[rs.GatedDecisionLedger] = []
        execution_counts: Counter[str] = Counter()
        twenty_bps_interval_counts = 0
        for variant in rs.VARIANTS:
            for split_id in rs.HISTORICAL_GATED_SPLITS:
                for slippage in rs.SLIPPAGE_SCENARIOS_BPS:
                    observations, ledger, counts = _simulate_one(
                        connection,
                        manifest["snapshot_id"],
                        sessions,
                        targets,
                        variant_id=variant.variant_id,
                        split_id=split_id,
                        slippage_bps=slippage,
                    )
                    execution_counts.update(
                        {f"{int(slippage)}bps:{key}": value for key, value in counts.items()}
                    )
                    if slippage == 20.0:
                        twenty_bps_interval_counts += len(observations)
                    else:
                        gated_observations.extend(observations)
                        gated_ledgers.append(ledger)
        tests = rs.evaluate_historical_eight_tests(
            tuple(gated_observations), decision_ledgers=tuple(gated_ledgers)
        )
        gates_total = sum(len(item.gates) for item in tests)
        gates_passed = sum(passed for item in tests for _, passed in item.gates)
        status = (
            "HISTORICAL_SCREENING_PASS"
            if gates_passed == gates_total
            else "HISTORICAL_SCREENING_FAIL"
        )
        return {
            "schema_version": "a-share-rs-historical-secondary-result-v1",
            "run_id": run_id,
            "research_id": rs.RESEARCH_ID,
            "status": status,
            "classification": CLASSIFICATION,
            "amendment_sha256": AMENDMENT_SHA256,
            "preregistration_sha256": rs.DEFINITION_SHA256,
            "data_manifest_sha256": manifest["_sha256"],
            "database_sha256": manifest["database"]["sha256"],
            "source_identity": source_identity,
            **_preflight_payload(preflight),
            "historical_test_count": len(tests),
            "twenty_bps_interval_count": twenty_bps_interval_counts,
            "gate_counts": {"passed": gates_passed, "total": gates_total},
            "tests": [asdict(item) for item in tests],
            "execution_counts": dict(sorted(execution_counts.items())),
            "prospective_forward_outcomes_opened": False,
            "security_identifiers_in_result": False,
            "strict_strategy_evidence": False,
            "strategy_candidate_available": False,
            "provider_or_network_used": False,
            "database_write_performed": False,
        }


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"


def _publish(path: Path, report: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise SecondaryScreenError("output must not preexist")
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        raw = _canonical_bytes(report)
        os.write(descriptor, raw)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--db", type=Path)
    parser.add_argument("--data-manifest", type=Path)
    parser.add_argument("--expected-data-manifest-sha256")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--execute", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    execution_run_id = _execution_run_id(args.run_id)
    load_amendment()
    if not args.execute:
        print(
            json.dumps(
                {
                    "status": "DRY_RUN_PLAN",
                    "run_id": execution_run_id,
                    "classification": CLASSIFICATION,
                    "amendment_sha256": AMENDMENT_SHA256,
                    "database_opened": False,
                    "output_written": False,
                    "prospective_forward_outcomes_opened": False,
                    "strategy_candidate_available": False,
                },
                sort_keys=True,
            )
        )
        return 0
    if any(value is None for value in (args.db, args.data_manifest, args.output)) or not args.expected_data_manifest_sha256:
        raise SecondaryScreenError("--execute requires db, manifest hash, manifest, and output")
    assert args.db is not None and args.data_manifest is not None and args.output is not None
    if args.output.exists() or args.output.is_symlink():
        raise SecondaryScreenError("output must not preexist")
    manifest_sha = _digest(args.expected_data_manifest_sha256, "data manifest SHA-256")
    manifest = load_data_manifest(args.data_manifest, manifest_sha, execution_run_id)
    manifest["_sha256"] = manifest_sha
    before = _database_identity(args.db)
    expected_database = manifest["database"]
    if before != (
        expected_database["sha256"],
        expected_database["size_bytes"],
        expected_database["mode"],
    ):
        raise SecondaryScreenError("database identity differs from manifest")
    try:
        report = execute_screen(args.db, manifest, execution_run_id)
    except PrecheckBlockedError as exc:
        report = {
            "schema_version": "a-share-rs-historical-secondary-result-v1",
            "run_id": execution_run_id,
            "research_id": rs.RESEARCH_ID,
            "status": "PRECHECK_BLOCKED",
            "classification": CLASSIFICATION,
            "reason_class": type(exc).__name__,
            "amendment_sha256": AMENDMENT_SHA256,
            "preregistration_sha256": rs.DEFINITION_SHA256,
            "data_manifest_sha256": manifest_sha,
            **_preflight_payload(exc.preflight),
            "prospective_forward_outcomes_opened": False,
            "security_identifiers_in_result": False,
            "strict_strategy_evidence": False,
            "strategy_candidate_available": False,
            "provider_or_network_used": False,
            "database_write_performed": False,
        }
    except (SecondaryScreenError, rs.RelativeStrengthContractError, duckdb.Error, ValueError) as exc:
        report = {
            "schema_version": "a-share-rs-historical-secondary-result-v1",
            "run_id": execution_run_id,
            "research_id": rs.RESEARCH_ID,
            "status": "INPUT_BLOCKED",
            "classification": CLASSIFICATION,
            "reason_class": type(exc).__name__,
            "amendment_sha256": AMENDMENT_SHA256,
            "preregistration_sha256": rs.DEFINITION_SHA256,
            "data_manifest_sha256": manifest_sha,
            "prospective_forward_outcomes_opened": False,
            "security_identifiers_in_result": False,
            "strict_strategy_evidence": False,
            "strategy_candidate_available": False,
            "provider_or_network_used": False,
            "database_write_performed": False,
        }
    after = _database_identity(args.db)
    if after != before:
        raise SecondaryScreenError("database bytes changed; result not published")
    _publish(args.output, report)
    print(json.dumps({"status": report["status"], "output_written": True}, sort_keys=True))
    return 0 if report["status"] not in {"INPUT_BLOCKED", "PRECHECK_BLOCKED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
