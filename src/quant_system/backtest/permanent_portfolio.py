"""Outcome-blind clean-room mechanics for preregistered A-share Family42.

This module is deliberately data-source agnostic except for the immutable CSV
identity frozen by the accepted mechanical supplement.  It performs no network,
database, publication, recommendation, or trading action.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import csv
from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import io
import json
import math
from numbers import Integral, Real
import os
from pathlib import Path
import stat
from statistics import median
from typing import Any

import numpy as np


FAMILY_NUMBER = 42
RESEARCH_ID = "A_SHARE_PERMANENT_PORTFOLIO_V1_20260710"
SUPPLEMENT_SHA256 = "45cc2dec9e98940274a336dc5643b693b0542c1e8ed33dea32e3aa3a6e608aa5"
PRICE_CSV_SHA256 = "c5f37bc0ad3a086ab24c50e84ebc1333ef716effd397bd46972f36d9d8b7c1b6"
LIQUIDITY_EVIDENCE_SHA256 = (
    "43f50efb7b41c161e825d8452097a9a59754e195bc525d44331d76bf10d1b80e"
)
PROVIDER_SOURCE = "tencent_ifzq_qfq_kline_public_open_endpoint_via_simonlin1212_policy"
ADJUSTMENT = "qfq"
EVALUATION_START = date(2018, 1, 2)
EVALUATION_END = date(2026, 6, 30)
SYMBOLS = ("510300.SH", "511010.SH", "518880.SH", "511880.SH")
TARGET_WEIGHTS = tuple((symbol, 0.25) for symbol in SYMBOLS)
REPORTED_COST_BPS = (20, 50)
STRICT_COST_BPS = 50
BOOTSTRAP_DRAWS = 50_000
BOOTSTRAP_BLOCK_MONTHS = 3
BOOTSTRAP_SEED = 20_260_710
BOOTSTRAP_Q = 0.05 / (42 * 2)
CSV_HEADER = (
    "snapshot_id",
    "ts_code",
    "trade_date",
    "open",
    "close",
    "high",
    "low",
    "volume",
    "amount",
    "provider_source",
    "adjustment",
    "nav_available",
)
LIQUIDITY_HEADER = (
    "ts_code",
    "name",
    "rows",
    "data_start",
    "data_end",
    "amount_materialized",
    "turnover_materialized",
    "nav_materialized",
    "premium_discount_materialized",
    "median_amount",
    "median_turnover_rate",
    "amount_missing_rate",
    "turnover_missing_rate",
    "field_status",
)
SPLITS = {
    "development_2018_2021": (date(2018, 1, 2), date(2021, 12, 31)),
    "validation_2022_2023": (date(2022, 1, 1), date(2023, 12, 31)),
    "holdout_2024_2025": (date(2024, 1, 1), date(2025, 12, 31)),
    "forward_2026h1": (date(2026, 1, 1), date(2026, 6, 30)),
}
CORE_SPLITS = (
    "development_2018_2021",
    "validation_2022_2023",
    "holdout_2024_2025",
)
HOLDOUT_MONTHS = tuple(
    f"{year:04d}-{month:02d}" for year in (2024, 2025) for month in range(1, 13)
)
DEFENSIVE_SYMBOLS = ("511010.SH", "518880.SH", "511880.SH")


class Family42Error(ValueError):
    """Raised when the frozen Family42 contract cannot be applied exactly."""


@dataclass(frozen=True)
class PriceVolumeRow:
    session_date: date
    symbol: str
    close: float
    volume: float | None


@dataclass(frozen=True)
class MarketSession:
    session_date: date
    closes: tuple[tuple[str, float], ...]
    equity_volume: float


@dataclass(frozen=True)
class Family42Dataset:
    sessions: tuple[MarketSession, ...]
    source_sha256: str
    snapshot_id: str


@dataclass(frozen=True)
class LedgerRow:
    session_date: date
    start_weights: tuple[tuple[str, float], ...]
    portfolio_gross_factor: float
    drifted_weights: tuple[tuple[str, float], ...]
    initial_turnover: float
    rebalance_turnover: float
    initial_cost_fraction: float
    rebalance_cost_fraction: float
    net_factor: float
    net_return: float
    end_weights: tuple[tuple[str, float], ...]
    wealth: float
    running_peak: float
    rebalanced: bool


@dataclass(frozen=True)
class SimulationResult:
    offset_month: int | None
    cost_bps: int
    target_weights: tuple[tuple[str, float], ...]
    ledger: tuple[LedgerRow, ...]


@dataclass(frozen=True)
class SplitMetrics:
    observation_count: int
    total_return: float
    annualized_return: float
    annualized_volatility: float
    annualized_sharpe: float
    maximum_drawdown: float


@dataclass(frozen=True)
class BootstrapResult:
    observed_mean: float
    lower_bound: float
    diagnostic_p_value: float
    uncentered_means: tuple[float, ...]
    centered_means: tuple[float, ...]
    draws: int
    seed: int


@dataclass(frozen=True)
class GateCheck:
    gate_id: str
    passed: bool


@dataclass(frozen=True)
class Family42Runs:
    strategies: tuple[tuple[int, int, SimulationResult], ...]
    csi300: tuple[tuple[int, SimulationResult], ...]
    cash: tuple[tuple[int, SimulationResult], ...]

    def strategy(self, cost_bps: int, offset_month: int) -> SimulationResult:
        return next(
            run
            for cost, offset, run in self.strategies
            if cost == cost_bps and offset == offset_month
        )

    def comparator(self, name: str, cost_bps: int) -> SimulationResult:
        items = self.csi300 if name == "csi300" else self.cash if name == "cash" else ()
        if not items:
            raise Family42Error("comparator name must be csi300 or cash")
        return next(run for cost, run in items if cost == cost_bps)


@dataclass(frozen=True)
class Family42Evaluation:
    runs: Family42Runs
    checks: tuple[GateCheck, ...]
    price_source_sha256: str
    liquidity_source_sha256: str
    snapshot_id: str
    classification: str = "RETROSPECTIVE_CLEAN_ROOM_MIGRATION_MECHANICS_ONLY"
    strategy_candidate_available: bool = False
    broker_or_order_path_available: bool = False


@dataclass(frozen=True)
class SyntheticFamily42Diagnostics:
    """Test-only mechanics diagnostics; never a formal Family42 adjudication."""

    runs: Family42Runs
    diagnostic_checks: tuple[GateCheck, ...]
    classification: str = "SYNTHETIC_MECHANICS_TEST_ONLY_NOT_FORMAL_ADJUDICATION"
    formal_adjudication_available: bool = False
    strategy_candidate_available: bool = False


def _number(value: object, name: str, *, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise Family42Error(f"{name} must be a finite number")
    parsed = float(value)
    if not math.isfinite(parsed) or (nonnegative and parsed < 0.0):
        qualifier = "finite and nonnegative" if nonnegative else "finite"
        raise Family42Error(f"{name} must be {qualifier}")
    return parsed


def _positive(value: object, name: str) -> float:
    parsed = _number(value, name)
    if parsed <= 0.0:
        raise Family42Error(f"{name} must be finite and positive")
    return parsed


def _sha256(value: str, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise Family42Error(f"{name} must be a lowercase SHA-256")
    return value


def _cost_bps(value: int) -> int:
    if type(value) is not int or value not in REPORTED_COST_BPS:
        raise Family42Error("cost_bps must be exactly 20 or 50")
    return value


def _offset(value: int) -> int:
    if type(value) is not int or not 1 <= value <= 12:
        raise Family42Error("offset_month must be an integer from 1 through 12")
    return value


def _capture_regular_file(path: Path) -> tuple[bytes, str]:
    candidate = Path(path)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(candidate, flags)
    except OSError as exc:
        raise Family42Error(f"cannot safely open regular file: {candidate}") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise Family42Error("captured path is not a regular file")
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        after = os.fstat(descriptor)
        identity = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        final_identity = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        )
        raw = b"".join(chunks)
        if identity != final_identity or len(raw) != after.st_size:
            raise Family42Error("file changed during descriptor capture")
        try:
            path_state = candidate.stat(follow_symlinks=False)
        except OSError as exc:
            raise Family42Error("file path disappeared during descriptor capture") from exc
        path_identity = (
            path_state.st_dev,
            path_state.st_ino,
            path_state.st_size,
            path_state.st_mtime_ns,
            path_state.st_ctime_ns,
        )
        if stat.S_ISLNK(path_state.st_mode) or path_identity != final_identity:
            raise Family42Error("file path was replaced during descriptor capture")
    finally:
        os.close(descriptor)
    return raw, hashlib.sha256(raw).hexdigest()


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise Family42Error(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise Family42Error(f"nonfinite JSON constant is not allowed: {value}")


def load_mechanical_supplement(path: Path) -> dict[str, Any]:
    """Capture and validate the exact independently accepted supplement."""

    raw, digest = _capture_regular_file(path)
    if digest != SUPPLEMENT_SHA256:
        raise Family42Error("mechanical supplement SHA-256 changed")
    try:
        parsed = json.loads(
            raw,
            object_pairs_hook=_unique_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Family42Error("mechanical supplement is not strict JSON") from exc
    if not isinstance(parsed, dict):
        raise Family42Error("mechanical supplement root must be an object")
    if (
        parsed.get("family_number") != FAMILY_NUMBER
        or parsed.get("research_id") != RESEARCH_ID
        or parsed.get("status") != "OUTCOME_BLIND_MECHANICAL_SUPPLEMENT_READY"
        or parsed.get("implementation_ready") is not True
        or parsed.get("remaining_blocker") is not None
    ):
        raise Family42Error("mechanical supplement readiness identity changed")
    if parsed.get("gates", {}).get("ids") != list(family42_gate_ids()):
        raise Family42Error("mechanical supplement 183-gate identity changed")
    boundary = parsed.get("boundary", {})
    if any(
        boundary.get(key) is not False
        for key in (
            "real_data_or_outcome_access_authorized",
            "backtest_execution_authorized",
            "strategy_candidate_available",
            "promotion_allowed",
            "recommendation_or_trading_allowed",
        )
    ):
        raise Family42Error("mechanical supplement research-only boundary changed")
    return parsed


def _parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y%m%d").date()
    except (TypeError, ValueError) as exc:
        raise Family42Error("trade_date must use YYYYMMDD") from exc


def _parse_csv_number(value: str, name: str, *, positive: bool) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise Family42Error(f"{name} must be numeric") from exc
    return _positive(parsed, name) if positive else _number(parsed, name, nonnegative=True)


def _dataset_from_rows(
    rows: Sequence[PriceVolumeRow],
    *,
    source_sha256: str,
    snapshot_id: str,
) -> Family42Dataset:
    """Validate rows and retain only the common complete evaluation calendar."""

    digest = _sha256(source_sha256, "source_sha256")
    if not isinstance(snapshot_id, str) or not snapshot_id.strip() or snapshot_id != snapshot_id.strip():
        raise Family42Error("snapshot_id must be nonempty trimmed text")
    frozen = tuple(rows)
    if not frozen:
        raise Family42Error("price rows must not be empty")
    by_symbol: dict[str, dict[date, PriceVolumeRow]] = {symbol: {} for symbol in SYMBOLS}
    for row in frozen:
        if not isinstance(row, PriceVolumeRow):
            raise Family42Error("rows must contain PriceVolumeRow values")
        if type(row.session_date) is not date:
            raise Family42Error("session_date must be a date, not a datetime")
        if row.symbol not in by_symbol:
            raise Family42Error("unexpected Family42 symbol")
        if not EVALUATION_START <= row.session_date <= EVALUATION_END:
            raise Family42Error("row date lies outside the frozen evaluation interval")
        close = _positive(row.close, "close")
        volume = (
            _number(row.volume, "510300.SH volume", nonnegative=True)
            if row.symbol == "510300.SH"
            else None
        )
        if row.session_date in by_symbol[row.symbol]:
            raise Family42Error("duplicate symbol-date row")
        by_symbol[row.symbol][row.session_date] = PriceVolumeRow(
            row.session_date,
            row.symbol,
            close,
            volume,
        )
    if any(not values for values in by_symbol.values()):
        raise Family42Error("one or more frozen symbols are absent")
    common_dates = set.intersection(*(set(values) for values in by_symbol.values()))
    if len(common_dates) < 2:
        raise Family42Error("at least two common complete sessions are required")
    sessions = tuple(
        MarketSession(
            session_date=session_date,
            closes=tuple(
                (symbol, by_symbol[symbol][session_date].close) for symbol in SYMBOLS
            ),
            equity_volume=_number(
                by_symbol["510300.SH"][session_date].volume,
                "510300.SH volume",
                nonnegative=True,
            ),
        )
        for session_date in sorted(common_dates)
    )
    return Family42Dataset(sessions, digest, snapshot_id)


def dataset_from_rows(
    rows: Sequence[PriceVolumeRow],
    *,
    source_sha256: str,
    snapshot_id: str,
) -> Family42Dataset:
    """Build an explicitly unqualified synthetic dataset for mechanics tests."""

    return _dataset_from_rows(
        rows,
        source_sha256=source_sha256,
        snapshot_id=snapshot_id,
    )


def _load_family42_csv_with_expected_identity(
    path: Path,
    *,
    expected_source_sha256: str,
) -> Family42Dataset:
    expected = _sha256(expected_source_sha256, "expected_source_sha256")
    raw, digest = _capture_regular_file(path)
    if digest != expected:
        raise Family42Error("source CSV SHA-256 changed")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Family42Error("source CSV must be UTF-8") from exc
    rows: list[PriceVolumeRow] = []
    snapshot_ids: set[str] = set()
    with io.StringIO(text, newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != CSV_HEADER:
            raise Family42Error("source CSV header or column order changed")
        for item in reader:
            symbol = item["ts_code"]
            if symbol not in SYMBOLS:
                continue
            session_date = _parse_date(item["trade_date"])
            if not EVALUATION_START <= session_date <= EVALUATION_END:
                continue
            if item["provider_source"] != PROVIDER_SOURCE or item["adjustment"] != ADJUSTMENT:
                raise Family42Error("selected source provenance changed")
            snapshot_id = item["snapshot_id"]
            if not snapshot_id or snapshot_id != snapshot_id.strip():
                raise Family42Error("selected snapshot_id is invalid")
            snapshot_ids.add(snapshot_id)
            rows.append(
                PriceVolumeRow(
                    session_date,
                    symbol,
                    _parse_csv_number(item["close"], "close", positive=True),
                    (
                        _parse_csv_number(item["volume"], "510300.SH volume", positive=False)
                        if symbol == "510300.SH"
                        else None
                    ),
                )
            )
    if len(snapshot_ids) != 1:
        raise Family42Error("selected rows must have exactly one snapshot_id")
    return _dataset_from_rows(
        rows,
        source_sha256=digest,
        snapshot_id=next(iter(snapshot_ids)),
    )


def load_family42_csv(path: Path) -> Family42Dataset:
    """Capture the one frozen source identity and parse only the Family42 slice."""

    return _load_family42_csv_with_expected_identity(
        path,
        expected_source_sha256=PRICE_CSV_SHA256,
    )


def _evidence_date(value: str, name: str) -> date:
    for date_format in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(value, date_format).date()
        except (TypeError, ValueError):
            continue
    raise Family42Error(f"{name} must be an ISO or compact calendar date")


def _load_defensive_median_amounts_with_expected_identity(
    path: Path,
    *,
    expected_source_sha256: str,
) -> dict[str, float]:
    expected = _sha256(expected_source_sha256, "expected_liquidity_sha256")
    raw, digest = _capture_regular_file(path)
    if digest != expected:
        raise Family42Error("liquidity evidence SHA-256 changed")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Family42Error("liquidity evidence must be UTF-8") from exc
    selected: dict[str, float] = {}
    seen_symbols: set[str] = set()
    with io.StringIO(text, newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != LIQUIDITY_HEADER:
            raise Family42Error("liquidity evidence header or column order changed")
        for item in reader:
            if None in item or any(value is None for value in item.values()):
                raise Family42Error("liquidity evidence row width changed")
            symbol = item["ts_code"]
            if symbol not in SYMBOLS:
                raise Family42Error("liquidity evidence contains an unexpected symbol")
            if symbol in seen_symbols:
                raise Family42Error("duplicate liquidity evidence symbol")
            seen_symbols.add(symbol)
            if symbol not in DEFENSIVE_SYMBOLS:
                continue
            if not item["name"].strip() or item["name"] != item["name"].strip():
                raise Family42Error("liquidity evidence name is invalid")
            try:
                row_count = int(item["rows"])
            except (TypeError, ValueError, OverflowError) as exc:
                raise Family42Error("liquidity evidence rows must be an integer") from exc
            if row_count <= 0 or str(row_count) != item["rows"]:
                raise Family42Error("liquidity evidence rows must be positive canonical text")
            if (
                _evidence_date(item["data_start"], "liquidity data_start")
                != date(2018, 1, 2)
                or _evidence_date(item["data_end"], "liquidity data_end")
                != date(2026, 7, 7)
            ):
                raise Family42Error("liquidity evidence window changed")
            if item["amount_materialized"] != "True":
                raise Family42Error("defensive amount evidence is not materialized")
            missing_rate = _number(
                _parse_csv_number(
                    item["amount_missing_rate"],
                    "amount_missing_rate",
                    positive=False,
                ),
                "amount_missing_rate",
                nonnegative=True,
            )
            if missing_rate != 0.0:
                raise Family42Error("defensive amount evidence must have zero missingness")
            if not item["field_status"].strip():
                raise Family42Error("liquidity evidence field_status is empty")
            selected[symbol] = _parse_csv_number(
                item["median_amount"],
                "median_amount",
                positive=False,
            )
    if set(selected) != set(DEFENSIVE_SYMBOLS):
        raise Family42Error("liquidity evidence is missing a defensive symbol")
    return selected


def load_defensive_median_amounts(path: Path) -> dict[str, float]:
    """Capture and parse the exact frozen defensive-liquidity evidence."""

    return _load_defensive_median_amounts_with_expected_identity(
        path,
        expected_source_sha256=LIQUIDITY_EVIDENCE_SHA256,
    )


def annual_rebalance_dates(dataset: Family42Dataset, offset_month: int) -> tuple[date, ...]:
    month = _offset(offset_month)
    first_date = dataset.sessions[0].session_date
    earliest: dict[int, date] = {}
    for session in dataset.sessions:
        current = session.session_date
        if current.month == month:
            earliest.setdefault(current.year, current)
    return tuple(current for current in earliest.values() if current > first_date)


def _validated_targets(
    target_weights: Mapping[str, float],
) -> tuple[tuple[str, float], ...]:
    if not isinstance(target_weights, Mapping) or not target_weights:
        raise Family42Error("target weights must be a nonempty mapping")
    normalized: list[tuple[str, float]] = []
    for symbol, weight in target_weights.items():
        if symbol not in SYMBOLS:
            raise Family42Error("target contains an unexpected Family42 symbol")
        normalized.append((symbol, _positive(weight, "target weight")))
    normalized.sort(key=lambda item: SYMBOLS.index(item[0]))
    if not math.isclose(
        math.fsum(weight for _, weight in normalized),
        1.0,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise Family42Error("target weights must sum to one")
    return tuple(normalized)


def _simulate(
    dataset: Family42Dataset,
    target_weights: Mapping[str, float],
    *,
    offset_month: int | None,
    cost_bps: int,
) -> SimulationResult:
    cost = _cost_bps(cost_bps)
    targets = _validated_targets(target_weights)
    target_symbols = tuple(symbol for symbol, _ in targets)
    schedule = (
        frozenset(annual_rebalance_dates(dataset, _offset(offset_month)))
        if offset_month is not None
        else frozenset()
    )
    weights = targets
    wealth = 1.0
    running_peak = 1.0
    ledger: list[LedgerRow] = []
    for index in range(1, len(dataset.sessions)):
        previous = dict(dataset.sessions[index - 1].closes)
        current_session = dataset.sessions[index]
        current = dict(current_session.closes)
        factors = {
            symbol: _positive(current[symbol] / previous[symbol], "gross factor")
            for symbol in target_symbols
        }
        start_weights = weights
        notionals = tuple(
            (symbol, weight * factors[symbol]) for symbol, weight in start_weights
        )
        gross_factor = _positive(
            math.fsum(value for _, value in notionals),
            "portfolio gross factor",
        )
        drifted = tuple((symbol, value / gross_factor) for symbol, value in notionals)
        initial_turnover = 1.0 if index == 1 else 0.0
        rebalanced = current_session.session_date in schedule
        rebalance_turnover = 0.0
        if rebalanced:
            target_map = dict(targets)
            rebalance_turnover = 0.5 * math.fsum(
                abs(target_map[symbol] - weight) for symbol, weight in drifted
            )
        initial_cost = cost / 10_000.0 * initial_turnover
        rebalance_cost = cost / 10_000.0 * rebalance_turnover
        if not 0.0 <= initial_cost < 1.0 or not 0.0 <= rebalance_cost < 1.0:
            raise Family42Error("cost fraction must lie in [0,1)")
        net_factor = _positive(
            gross_factor * (1.0 - initial_cost) * (1.0 - rebalance_cost),
            "net factor",
        )
        wealth = _positive(wealth * net_factor, "wealth")
        running_peak = max(running_peak, wealth)
        end_weights = targets if rebalanced else drifted
        ledger.append(
            LedgerRow(
                session_date=current_session.session_date,
                start_weights=start_weights,
                portfolio_gross_factor=gross_factor,
                drifted_weights=drifted,
                initial_turnover=initial_turnover,
                rebalance_turnover=rebalance_turnover,
                initial_cost_fraction=initial_cost,
                rebalance_cost_fraction=rebalance_cost,
                net_factor=net_factor,
                net_return=net_factor - 1.0,
                end_weights=end_weights,
                wealth=wealth,
                running_peak=running_peak,
                rebalanced=rebalanced,
            )
        )
        weights = end_weights
    return SimulationResult(offset_month, cost, targets, tuple(ledger))


def run_strategy(
    dataset: Family42Dataset,
    *,
    offset_month: int,
    cost_bps: int,
) -> SimulationResult:
    return _simulate(
        dataset,
        dict(TARGET_WEIGHTS),
        offset_month=_offset(offset_month),
        cost_bps=cost_bps,
    )


def run_comparator(
    dataset: Family42Dataset,
    symbol: str,
    *,
    cost_bps: int,
) -> SimulationResult:
    if symbol not in ("510300.SH", "511880.SH"):
        raise Family42Error("comparator must be 510300.SH or 511880.SH")
    return _simulate(dataset, {symbol: 1.0}, offset_month=None, cost_bps=cost_bps)


def run_reported_costs(dataset: Family42Dataset) -> Family42Runs:
    strategies = tuple(
        (cost, offset, run_strategy(dataset, offset_month=offset, cost_bps=cost))
        for cost in REPORTED_COST_BPS
        for offset in range(1, 13)
    )
    csi300 = tuple(
        (cost, run_comparator(dataset, "510300.SH", cost_bps=cost))
        for cost in REPORTED_COST_BPS
    )
    cash = tuple(
        (cost, run_comparator(dataset, "511880.SH", cost_bps=cost))
        for cost in REPORTED_COST_BPS
    )
    return Family42Runs(strategies, csi300, cash)


def split_metrics(result: SimulationResult, split_name: str) -> SplitMetrics:
    if split_name not in SPLITS:
        raise Family42Error("unknown Family42 split")
    start, end = SPLITS[split_name]
    selected = tuple(row for row in result.ledger if start <= row.session_date <= end)
    if len(selected) < 2:
        raise Family42Error("split must contain at least two return observations")
    returns = tuple(_number(row.net_return, "net return") for row in selected)
    factor = _positive(math.prod(1.0 + value for value in returns), "split wealth factor")
    count = len(returns)
    average = math.fsum(returns) / count
    variance = math.fsum((value - average) ** 2 for value in returns) / (count - 1)
    if not math.isfinite(variance) or variance <= 0.0:
        raise Family42Error("split sample variance must be finite and positive")
    standard_deviation = math.sqrt(variance)
    annualized_return = factor ** (252.0 / count) - 1.0
    annualized_volatility = math.sqrt(252.0) * standard_deviation
    annualized_sharpe = math.sqrt(252.0) * average / standard_deviation
    drawdown = min(row.wealth / row.running_peak - 1.0 for row in selected)
    values = (
        factor - 1.0,
        annualized_return,
        annualized_volatility,
        annualized_sharpe,
        drawdown,
    )
    if any(not math.isfinite(value) for value in values):
        raise Family42Error("split metric is nonfinite")
    return SplitMetrics(count, *values)


def monthly_returns(
    result: SimulationResult,
    *,
    split_name: str = "holdout_2024_2025",
) -> tuple[float, ...]:
    if split_name != "holdout_2024_2025":
        raise Family42Error("bootstrap monthly returns require holdout_2024_2025")
    start, end = SPLITS[split_name]
    grouped: dict[str, list[float]] = {}
    for row in result.ledger:
        if start <= row.session_date <= end:
            key = f"{row.session_date.year:04d}-{row.session_date.month:02d}"
            grouped.setdefault(key, []).append(row.net_return)
    if tuple(sorted(grouped)) != HOLDOUT_MONTHS or any(not grouped[key] for key in HOLDOUT_MONTHS):
        raise Family42Error("holdout must contain all 24 complete calendar months")
    output = tuple(
        _number(math.prod(1.0 + value for value in grouped[key]) - 1.0, "monthly return")
        for key in HOLDOUT_MONTHS
    )
    return output


def _integer(value: int, name: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < minimum:
        raise Family42Error(f"{name} must be an integer >= {minimum}")
    return int(value)


def circular_block_start_indices(
    sample_size: int,
    *,
    draws: int,
    seed: int = BOOTSTRAP_SEED,
) -> tuple[tuple[int, ...], ...]:
    size = _integer(sample_size, "sample_size", BOOTSTRAP_BLOCK_MONTHS)
    count = _integer(draws, "draws", 1)
    random_seed = _integer(seed, "seed", 0)
    blocks = math.ceil(size / BOOTSTRAP_BLOCK_MONTHS)
    generator = np.random.Generator(np.random.PCG64(random_seed))
    starts = generator.integers(0, size, size=(count, blocks), endpoint=False)
    return tuple(tuple(int(value) for value in row) for row in starts)


def _means_from_starts(
    values: np.ndarray,
    starts: tuple[tuple[int, ...], ...],
) -> tuple[float, ...]:
    sample_size = len(values)
    output: list[float] = []
    for row in starts:
        indices = tuple(
            (start + offset) % sample_size
            for start in row
            for offset in range(BOOTSTRAP_BLOCK_MONTHS)
        )[:sample_size]
        output.append(math.fsum(float(values[index]) for index in indices) / sample_size)
    return tuple(output)


def _linear_quantile(values: Sequence[float], q: float) -> float:
    ordered = sorted(_number(value, "bootstrap mean") for value in values)
    if not ordered or not 0.0 <= q <= 1.0:
        raise Family42Error("quantile requires values and q in [0,1]")
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    weight = position - lower
    return ordered[lower] + weight * (ordered[upper] - ordered[lower])


def family42_bootstrap(
    values: Sequence[float],
    *,
    draws: int = BOOTSTRAP_DRAWS,
    seed: int = BOOTSTRAP_SEED,
) -> BootstrapResult:
    frozen = tuple(_number(value, "monthly return") for value in values)
    if len(frozen) != 24:
        raise Family42Error("Family42 bootstrap requires exactly 24 monthly returns")
    starts = circular_block_start_indices(len(frozen), draws=draws, seed=seed)
    array = np.asarray(frozen, dtype=np.float64)
    observed = math.fsum(frozen) / len(frozen)
    raw_means = _means_from_starts(array, starts)
    centered_means = _means_from_starts(array - observed, starts)
    lower_bound = _linear_quantile(raw_means, BOOTSTRAP_Q)
    p_value = (1 + sum(value >= observed for value in centered_means)) / (
        len(centered_means) + 1
    )
    return BootstrapResult(
        observed,
        lower_bound,
        p_value,
        raw_means,
        centered_means,
        len(centered_means),
        seed,
    )


def pearson_sample(left: Sequence[float], right: Sequence[float]) -> float:
    x = tuple(_number(value, "left correlation value") for value in left)
    y = tuple(_number(value, "right correlation value") for value in right)
    if len(x) != len(y) or len(x) < 2:
        raise Family42Error("correlation inputs must have the same length >= 2")
    x_mean = math.fsum(x) / len(x)
    y_mean = math.fsum(y) / len(y)
    x_ss = math.fsum((value - x_mean) ** 2 for value in x)
    y_ss = math.fsum((value - y_mean) ** 2 for value in y)
    if x_ss <= 0.0 or y_ss <= 0.0:
        raise Family42Error("correlation variance must be positive")
    covariance = math.fsum(
        (x_value - x_mean) * (y_value - y_mean)
        for x_value, y_value in zip(x, y, strict=True)
    )
    result = covariance / math.sqrt(x_ss * y_ss)
    return _number(result, "Pearson correlation")


def development_correlations(dataset: Family42Dataset) -> tuple[float, float, float]:
    start, end = SPLITS["development_2018_2021"]
    by_symbol: dict[str, list[float]] = {symbol: [] for symbol in SYMBOLS}
    for index in range(1, len(dataset.sessions)):
        current_session = dataset.sessions[index]
        if not start <= current_session.session_date <= end:
            continue
        previous = dict(dataset.sessions[index - 1].closes)
        current = dict(current_session.closes)
        for symbol in SYMBOLS:
            by_symbol[symbol].append(current[symbol] / previous[symbol] - 1.0)
    equity = by_symbol["510300.SH"]
    return (
        pearson_sample(equity, by_symbol["518880.SH"]),
        pearson_sample(equity, by_symbol["511010.SH"]),
        pearson_sample(equity, by_symbol["511880.SH"]),
    )


def family42_gate_ids() -> tuple[str, ...]:
    ids: list[str] = []
    for split_name in CORE_SPLITS:
        for offset in range(1, 13):
            prefix = f"core.{split_name}.offset_{offset:02d}"
            ids.extend(
                (
                    f"{prefix}.total_return_positive",
                    f"{prefix}.annualized_sharpe_positive",
                    f"{prefix}.maximum_drawdown_ge_neg_0_20",
                    f"{prefix}.annualized_volatility_lt_csi300",
                )
            )
    for split_name in CORE_SPLITS:
        ids.extend(
            (
                f"cross_offset.{split_name}.median_annualized_sharpe_ge_0_30",
                f"cross_offset.{split_name}.fraction_total_return_gt_cash_ge_0_75",
            )
        )
    for offset in range(1, 13):
        prefix = f"forward.forward_2026h1.offset_{offset:02d}"
        ids.extend(
            (
                f"{prefix}.total_return_positive",
                f"{prefix}.maximum_drawdown_ge_neg_0_15",
            )
        )
    ids.extend(
        (
            "bootstrap.holdout_2024_2025.offset_01.monthly_portfolio_return."
            "lower_bound_gt_zero",
            "bootstrap.holdout_2024_2025.offset_01.monthly_excess_vs_cash."
            "lower_bound_gt_zero",
            "diversification.development_2018_2021.equity_gold_pearson_le_0_60",
            "diversification.development_2018_2021.equity_bond_pearson_le_0_60",
            "diversification.development_2018_2021.equity_cash_pearson_le_0_60",
            "capacity.510300_SH.median_volume_proxy_ge_1000000",
            "capacity.511010_SH.median_amount_cny_ge_100000000",
            "capacity.518880_SH.median_amount_cny_ge_100000000",
            "capacity.511880_SH.median_amount_cny_ge_100000000",
        )
    )
    frozen = tuple(ids)
    if len(frozen) != 183 or len(set(frozen)) != 183:
        raise RuntimeError("Family42 gate identity construction failed")
    return frozen


def _check(checks: list[GateCheck], gate_id: str, passed: bool) -> None:
    checks.append(GateCheck(gate_id, bool(passed)))


def _defensive_amounts(values: Mapping[str, float]) -> dict[str, float]:
    if not isinstance(values, Mapping) or set(values) != set(DEFENSIVE_SYMBOLS):
        raise Family42Error("defensive median amounts must contain exactly three symbols")
    return {
        symbol: _number(values[symbol], "defensive median amount", nonnegative=True)
        for symbol in DEFENSIVE_SYMBOLS
    }


def _compute_family42_mechanics(
    dataset: Family42Dataset,
    *,
    defensive_median_amounts_cny: Mapping[str, float],
) -> tuple[Family42Runs, tuple[GateCheck, ...]]:
    """Compute frozen mechanics without assigning formal evidence status."""

    defensive = _defensive_amounts(defensive_median_amounts_cny)
    runs = run_reported_costs(dataset)
    checks: list[GateCheck] = []
    csi = runs.comparator("csi300", STRICT_COST_BPS)
    cash = runs.comparator("cash", STRICT_COST_BPS)
    for split_name in CORE_SPLITS:
        csi_metrics = split_metrics(csi, split_name)
        for offset in range(1, 13):
            metrics = split_metrics(runs.strategy(STRICT_COST_BPS, offset), split_name)
            prefix = f"core.{split_name}.offset_{offset:02d}"
            _check(checks, f"{prefix}.total_return_positive", metrics.total_return > 0.0)
            _check(
                checks,
                f"{prefix}.annualized_sharpe_positive",
                metrics.annualized_sharpe > 0.0,
            )
            _check(
                checks,
                f"{prefix}.maximum_drawdown_ge_neg_0_20",
                metrics.maximum_drawdown >= -0.20,
            )
            _check(
                checks,
                f"{prefix}.annualized_volatility_lt_csi300",
                metrics.annualized_volatility < csi_metrics.annualized_volatility,
            )
    for split_name in CORE_SPLITS:
        metrics = tuple(
            split_metrics(runs.strategy(STRICT_COST_BPS, offset), split_name)
            for offset in range(1, 13)
        )
        cash_return = split_metrics(cash, split_name).total_return
        prefix = f"cross_offset.{split_name}"
        _check(
            checks,
            f"{prefix}.median_annualized_sharpe_ge_0_30",
            median(item.annualized_sharpe for item in metrics) >= 0.30,
        )
        _check(
            checks,
            f"{prefix}.fraction_total_return_gt_cash_ge_0_75",
            sum(item.total_return > cash_return for item in metrics) / 12.0 >= 0.75,
        )
    for offset in range(1, 13):
        metrics = split_metrics(
            runs.strategy(STRICT_COST_BPS, offset),
            "forward_2026h1",
        )
        prefix = f"forward.forward_2026h1.offset_{offset:02d}"
        _check(checks, f"{prefix}.total_return_positive", metrics.total_return > 0.0)
        _check(
            checks,
            f"{prefix}.maximum_drawdown_ge_neg_0_15",
            metrics.maximum_drawdown >= -0.15,
        )
    portfolio_monthly = monthly_returns(runs.strategy(STRICT_COST_BPS, 1))
    cash_monthly = monthly_returns(cash)
    excess_monthly = tuple(
        portfolio - comparator
        for portfolio, comparator in zip(portfolio_monthly, cash_monthly, strict=True)
    )
    portfolio_bootstrap = family42_bootstrap(
        portfolio_monthly,
        draws=BOOTSTRAP_DRAWS,
    )
    excess_bootstrap = family42_bootstrap(excess_monthly, draws=BOOTSTRAP_DRAWS)
    _check(
        checks,
        "bootstrap.holdout_2024_2025.offset_01.monthly_portfolio_return."
        "lower_bound_gt_zero",
        portfolio_bootstrap.lower_bound > 0.0,
    )
    _check(
        checks,
        "bootstrap.holdout_2024_2025.offset_01.monthly_excess_vs_cash."
        "lower_bound_gt_zero",
        excess_bootstrap.lower_bound > 0.0,
    )
    for gate_id, value in zip(
        family42_gate_ids()[176:179],
        development_correlations(dataset),
        strict=True,
    ):
        _check(checks, gate_id, value <= 0.60)
    equity_volume = median(session.equity_volume for session in dataset.sessions)
    _check(
        checks,
        "capacity.510300_SH.median_volume_proxy_ge_1000000",
        equity_volume >= 1_000_000,
    )
    for symbol, gate_id in zip(
        DEFENSIVE_SYMBOLS,
        family42_gate_ids()[180:183],
        strict=True,
    ):
        _check(checks, gate_id, defensive[symbol] >= 100_000_000)
    frozen = tuple(checks)
    if tuple(item.gate_id for item in frozen) != family42_gate_ids():
        raise RuntimeError("Family42 evaluation gate order drifted")
    return runs, frozen


def _evaluate_family42(
    dataset: Family42Dataset,
    *,
    defensive_median_amounts_cny: Mapping[str, float],
) -> SyntheticFamily42Diagnostics:
    """Return synthetic diagnostics that cannot masquerade as formal output."""

    runs, checks = _compute_family42_mechanics(
        dataset,
        defensive_median_amounts_cny=defensive_median_amounts_cny,
    )
    return SyntheticFamily42Diagnostics(runs, checks)


def evaluate_family42(
    *,
    price_evidence_path: Path,
    liquidity_evidence_path: Path,
) -> Family42Evaluation:
    """Descriptor-capture both locked evidence files and formally evaluate them."""

    dataset = load_family42_csv(price_evidence_path)
    if dataset.source_sha256 != PRICE_CSV_SHA256:
        raise Family42Error("formal evaluation price CSV identity changed")
    if not dataset.snapshot_id.strip() or dataset.snapshot_id != dataset.snapshot_id.strip():
        raise Family42Error("formal evaluation snapshot identity is invalid")
    if (
        not dataset.sessions
        or dataset.sessions[0].session_date != EVALUATION_START
        or dataset.sessions[-1].session_date != EVALUATION_END
    ):
        raise Family42Error("formal evaluation does not span the frozen endpoints")
    defensive = load_defensive_median_amounts(liquidity_evidence_path)
    runs, checks = _compute_family42_mechanics(
        dataset,
        defensive_median_amounts_cny=defensive,
    )
    return Family42Evaluation(
        runs,
        checks,
        dataset.source_sha256,
        LIQUIDITY_EVIDENCE_SHA256,
        dataset.snapshot_id,
    )


__all__ = [
    "BOOTSTRAP_BLOCK_MONTHS",
    "BOOTSTRAP_DRAWS",
    "BOOTSTRAP_Q",
    "BOOTSTRAP_SEED",
    "CSV_HEADER",
    "LIQUIDITY_HEADER",
    "Family42Dataset",
    "Family42Error",
    "Family42Evaluation",
    "Family42Runs",
    "GateCheck",
    "LedgerRow",
    "MarketSession",
    "PriceVolumeRow",
    "SimulationResult",
    "SplitMetrics",
    "annual_rebalance_dates",
    "circular_block_start_indices",
    "dataset_from_rows",
    "development_correlations",
    "evaluate_family42",
    "family42_bootstrap",
    "family42_gate_ids",
    "load_defensive_median_amounts",
    "load_family42_csv",
    "load_mechanical_supplement",
    "monthly_returns",
    "pearson_sample",
    "run_comparator",
    "run_reported_costs",
    "run_strategy",
    "split_metrics",
]
