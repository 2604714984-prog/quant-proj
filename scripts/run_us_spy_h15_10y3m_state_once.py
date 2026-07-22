"""One-use Screen-A runner for the frozen M119-03 term-spread state."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import stat
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from quant_system.backtest import ExecutionInput, Portfolio, run_static_rebalance  # noqa: E402
from quant_system.data import (  # noqa: E402
    AcceptedSession,
    AcceptedSessionCalendar,
    CalendarIdentity,
    CorporateActionIdentity,
    SourceIdentity,
)
from quant_system.markets.universe import (  # noqa: E402
    StatusEvidence,
    UniverseSnapshotIdentity,
)
from research.adapters.us_spy_h15_10y3m_state import (  # noqa: E402
    INITIAL_CAPITAL,
    MECHANISM_ID,
    ONE_WAY_SLIPPAGE_BPS,
    PROGRAM_ALPHA,
    PROGRAM_FAMILY_ID,
    RateObservation,
    screen_decision,
    target_weight,
)

BASE_BUNDLE_SHA256 = "fcf4b487b1b798c6afcfc774339d2066a45238431253e27b14ed5d1a4cc369c9"
H15_INPUT_SHA256 = "998e25841870582b56592ba03fb61ca278b51a9f8141e06e4601c6fde886d1c2"
H15_SELECTION_QUERY_SHA256 = (
    "a80b052fd13e688e90937d5fedac9b70d363e01cd6a3a057e42807bf522b65ab"
)
ACTION_PROJECTION_SHA256 = "caf871c657e8c1ff258e8733c8ef49409da1c66c911b5a48f2148cdf9cc3f12a"
EXPECTED_INCLUSION_RULE_SHA256 = (
    "89483ee34a4b87fcdb728889dc31c7dc7222f85b3071ff7a97c65148e1b6402e"
)
CORE_COMMIT = "35b3246e40f8315e2bbef847d995a3b6d3a3b4fc"
CORE_TREE = "06a78207779775abd165768b10b9b343749752d4"
ACTION_RETRIEVED_AT = datetime.fromisoformat("2026-07-21T08:13:17.580138+00:00")
DEFINITION = ROOT / "research" / "definitions" / "us_spy_h15_10y3m_state_v1.json"
ADAPTER = ROOT / "research" / "adapters" / "us_spy_h15_10y3m_state.py"
RUNNER = Path(__file__).resolve()
ENTRY_MONTHS = tuple(
    (year, month)
    for year in range(2018, 2022)
    for month in range(1, 13)
    if (2018, 3) <= (year, month) <= (2021, 11)
)


class InputBlockedError(ValueError):
    """Fail-closed input, identity, chronology or coverage error."""


@dataclass(frozen=True)
class Point:
    signal_session: date
    decision_at: datetime
    execution_session: date
    calendar: AcceptedSessionCalendar
    execution_calendar_revision: AcceptedSessionCalendar | None
    execution_input: ExecutionInput
    universe_snapshot: UniverseSnapshotIdentity
    terminal_exit: bool


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _file_sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _git(*args: str) -> str:
    completed = subprocess.run(
        ("git", "-C", str(ROOT), *args),
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if completed.returncode != 0:
        raise InputBlockedError("shared-core Git identity check failed")
    return completed.stdout.strip()


def _require_core_identity() -> None:
    if _git("rev-parse", f"{CORE_COMMIT}^{{tree}}") != CORE_TREE:
        raise InputBlockedError("frozen shared-core commit/tree identity mismatch")
    if _git("diff", "--name-only", CORE_COMMIT, "--", "src/quant_system"):
        raise InputBlockedError("tracked shared-core bytes differ from the frozen commit")
    if _git("ls-files", "--others", "--exclude-standard", "--", "src/quant_system"):
        raise InputBlockedError("untracked shared-core bytes are forbidden")


def _sha256(value: object, field: str) -> str:
    text = str(value)
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise InputBlockedError(f"{field} must be a lowercase SHA-256")
    return text


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    record: dict[str, Any] = {}
    for key, value in pairs:
        if key in record:
            raise InputBlockedError(f"duplicate JSON key: {key}")
        record[key] = value
    return record


def _json(payload: bytes, field: str) -> dict[str, Any]:
    try:
        record = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=_strict_object,
            parse_constant=lambda value: (_ for _ in ()).throw(
                InputBlockedError(f"nonfinite JSON constant: {value}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputBlockedError(f"{field} is not strict UTF-8 JSON") from exc
    if type(record) is not dict:
        raise InputBlockedError(f"{field} must be a JSON object")
    return record


def _capture(path: Path, expected_sha256: str, *, max_bytes: int) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid():
            raise InputBlockedError("input must be an owner-controlled regular file")
        if stat.S_IMODE(before.st_mode) & ~0o600 or not 0 < before.st_size <= max_bytes:
            raise InputBlockedError("input mode or size is outside the frozen bound")
        chunks: list[bytes] = []
        size = 0
        while chunk := os.read(fd, min(1024 * 1024, max_bytes + 1 - size)):
            chunks.append(chunk)
            size += len(chunk)
            if size > max_bytes:
                raise InputBlockedError("input exceeds the frozen size bound")
        after = os.fstat(fd)
    finally:
        os.close(fd)
    current = os.stat(path, follow_symlinks=False)
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(
        getattr(before, field) != getattr(after, field)
        or getattr(after, field) != getattr(current, field)
        for field in fields
    ):
        raise InputBlockedError("input changed during descriptor-bound capture")
    payload = b"".join(chunks)
    if _sha256_bytes(payload) != _sha256(expected_sha256, "expected input SHA-256"):
        raise InputBlockedError("input SHA-256 mismatch")
    return payload


def _iso_date(value: object, field: str) -> date:
    if type(value) is not str:
        raise InputBlockedError(f"{field} must be an ISO date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise InputBlockedError(f"{field} must be an ISO date") from exc
    if parsed.isoformat() != value:
        raise InputBlockedError(f"{field} must use canonical ISO format")
    return parsed


def _datetime(value: object, field: str) -> datetime:
    if type(value) is not str:
        raise InputBlockedError(f"{field} must be an ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise InputBlockedError(f"{field} must be an ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise InputBlockedError(f"{field} must be timezone-aware")
    return parsed


def _source(row: dict[str, Any]) -> SourceIdentity:
    return SourceIdentity(
        row["source_url"],
        row["content_sha256"],
        _datetime(row["available_at"], "available_at"),
        _datetime(row["retrieved_at"], "retrieved_at"),
        row["revision_id"],
        row.get("supersedes_revision_id"),
    )


def _calendar(row: dict[str, Any]) -> AcceptedSessionCalendar:
    sessions = tuple(
        AcceptedSession(
            _iso_date(item["session_date"], "session_date"),
            _datetime(item["open_at"], "open_at"),
            _datetime(item["close_at"], "close_at"),
            SourceIdentity(
                item["source_url"],
                item["source_document_set_sha256"],
                _datetime(item["source_available_at"], "source_available_at"),
                ACTION_RETRIEVED_AT,
                item["snapshot_id"],
            ),
            item["timezone"],
            item["early_close"],
            item["exchange"],
        )
        for item in row["session_rows"]
    )
    identity = row["calendar_identity"]
    return AcceptedSessionCalendar(
        sessions,
        identity=CalendarIdentity(
            identity["exchange_id"],
            identity["exchange_timezone"],
            _iso_date(identity["coverage_start"], "coverage_start"),
            _iso_date(identity["coverage_end"], "coverage_end"),
            identity["session_count"],
            identity["session_dates_sha256"],
            identity["session_rows_sha256"],
            _source(identity["source_identity"]),
        ),
    )


def _status(row: dict[str, Any]) -> StatusEvidence:
    return StatusEvidence(
        row["status_id"],
        row["symbol"],
        row["kind"],
        row["value"],
        _iso_date(row["effective_from"], "effective_from"),
        None if row["effective_to"] is None else _iso_date(row["effective_to"], "effective_to"),
        row["exchange_timezone"],
        _source(row["source"]),
    )


def _snapshot(row: dict[str, Any]) -> UniverseSnapshotIdentity:
    return UniverseSnapshotIdentity(
        row["market"],
        row["exchange_id"],
        _iso_date(row["effective_session"], "effective_session"),
        row["member_count"],
        row["ordered_members_sha256"],
        row["lifecycle_coverage_sha256"],
        row["inclusion_rule_sha256"],
        row["calendar_identity_sha256"],
        _source(row["source_identity"]),
    )


def _execution(row: dict[str, Any], statuses: tuple[StatusEvidence, ...]) -> ExecutionInput:
    return ExecutionInput(
        row["symbol"],
        row["market"],
        row["raw_open"],
        row["currency"],
        _source(row["source"]),
        statuses,
        decision_price=row["decision_price"],
        decision_price_source=_source(row["decision_price_source"]),
        decision_price_basis=row["decision_price_basis"],
        execution_price_effective_at=_datetime(
            row["execution_price_effective_at"], "execution_price_effective_at"
        ),
        execution_price_basis=row["execution_price_basis"],
    )


def _load_bundle(payload: bytes) -> tuple[
    AcceptedSessionCalendar,
    tuple[Point, ...],
    tuple[date, ...],
    tuple[CorporateActionIdentity, ...],
]:
    record = _json(payload, "SPY bundle")
    if (
        record.get("schema_version"),
        record.get("stage"),
        record.get("symbol"),
        record.get("query_start"),
        record.get("query_end"),
    ) != (
        "us-spy-vol-managed-validation-runtime-input-v1",
        "validation",
        "SPY",
        "2018-01-02",
        "2021-12-01",
    ):
        raise InputBlockedError("SPY bundle fixed identity mismatch")
    reconstruction = _calendar(record["reconstruction_calendar"])
    if len(reconstruction.session_dates) != 987:
        raise InputBlockedError("reconstruction calendar must contain exactly 987 sessions")
    epoch_rows = record["calendar_epochs"]
    epochs = tuple(_calendar(epoch_rows[key]) for key in ("a0", "a1", "b"))
    by_revision = {item.identity.source_identity.revision_id: item for item in epochs}
    if len(by_revision) != 3:
        raise InputBlockedError("calendar epochs are incomplete")

    points: list[Point] = []
    for item in record["execution_points"]:
        statuses = tuple(_status(row) for row in item["status_evidence"])
        execution = _execution(item["execution"], statuses)
        snapshot = _snapshot(item["universe_snapshot"])
        if snapshot.inclusion_rule_sha256 != EXPECTED_INCLUSION_RULE_SHA256:
            raise InputBlockedError("universe inclusion rule does not match the definition")
        revision_id = item["execution_calendar_revision_id"]
        points.append(
            Point(
                _iso_date(item["signal_session"], "signal_session"),
                _datetime(item["decision_at"], "decision_at"),
                _iso_date(item["execution"]["session_date"], "execution_session"),
                by_revision[item["decision_calendar_epoch_id"]],
                None if revision_id is None else by_revision[revision_id],
                execution,
                snapshot,
                item["terminal_exit"],
            )
        )
    frozen = tuple(points)
    if len(frozen) != 46 or sum(point.terminal_exit for point in frozen) != 1:
        raise InputBlockedError("SPY bundle must contain 45 entries and one terminal exit")
    if tuple((point.execution_session.year, point.execution_session.month) for point in frozen[:-1]) != ENTRY_MONTHS:
        raise InputBlockedError("Screen-A entry months are incomplete or reordered")
    if (frozen[-1].execution_session.year, frozen[-1].execution_session.month) != (2021, 12):
        raise InputBlockedError("terminal exit must be in 2021-12")
    if frozen[-1].terminal_exit is not True or any(point.terminal_exit for point in frozen[:-1]):
        raise InputBlockedError("terminal-exit flags are invalid")

    daily = tuple(_iso_date(row["session_date"], "daily session") for row in record["daily_sessions"])
    expected_daily = tuple(
        session
        for session in reconstruction.session_dates
        if frozen[0].execution_session <= session <= frozen[-1].execution_session
    )
    if daily != expected_daily:
        raise InputBlockedError("daily sessions are incomplete or reordered")
    projection = record["action_projection_jsonl"].encode()
    if _sha256_bytes(projection) != ACTION_PROJECTION_SHA256:
        raise InputBlockedError("corporate-action projection SHA-256 mismatch")
    actions = _actions(projection, reconstruction)
    if len(actions) != 15:
        raise InputBlockedError("Screen-A must contain exactly 15 cash distributions")
    if set(action.effective_date for action in actions) & set(
        point.execution_session for point in frozen
    ):
        raise InputBlockedError("distribution/execution overlap drifted from zero")
    return reconstruction, frozen, daily, actions


def _actions(
    projection: bytes,
    calendar: AcceptedSessionCalendar,
) -> tuple[CorporateActionIdentity, ...]:
    try:
        text = projection.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise InputBlockedError("action projection must be UTF-8") from exc
    lines = text.splitlines()
    if len(lines) != 34 or not text.endswith("\n"):
        raise InputBlockedError("action projection must contain 34 JSONL rows")
    actions: list[CorporateActionIdentity] = []
    for line in lines:
        row = _json(line.encode(), "action row")
        ex_date = _iso_date(row["ex_date"], "ex_date")
        if not calendar.identity.coverage_start <= ex_date <= calendar.identity.coverage_end:
            continue
        session = calendar.session_on(ex_date, as_of=ACTION_RETRIEVED_AT)
        event_payload = f"{ACTION_PROJECTION_SHA256}|SPY|{ex_date.isoformat()}".encode()
        source = SourceIdentity(
            row["source_url"],
            row["source_document_sha256"],
            ACTION_RETRIEVED_AT,
            ACTION_RETRIEVED_AT,
            f"ssga-distribution-{ex_date.isoformat()}",
        )
        actions.append(
            CorporateActionIdentity(
                "SPY",
                "spy-state-street-" + _sha256_bytes(event_payload),
                "cash_dividend",
                session.open_at,
                source,
                "America/New_York",
                ex_date=ex_date,
                record_date=_iso_date(row["record_date"], "record_date"),
                pay_date=_iso_date(row["payment_date"], "payment_date"),
                cash_amount=Decimal(row["distribution"]),
                currency="USD",
                unit="per_share",
            )
        )
    return tuple(actions)


def _load_h15(payload: bytes, points: tuple[Point, ...]) -> tuple[float, ...]:
    record = _json(payload, "H.15 input")
    expected_top = {
        "schema_version": "us-spy-h15-10y3m-state-v1",
        "stage": "validation_input",
        "source_table": "us_macro_research.alfred_h15_yield_observations_research",
        "source_class": "OFFICIAL_ALFRED_H15",
        "spy_bundle_sha256": BASE_BUNDLE_SHA256,
        "row_count": 45,
        "response_set_sha256": "338a8da0720f16045cd3325a5dc07241292c149e836bce1149af3de8bb97cc14",
        "db_postwrite_sha256": "4e7bd0792241087c7c4da05de32b75a7450baa1dda0342a326ef4c02aa42a92e",
    }
    if any(record.get(key) != value for key, value in expected_top.items()):
        raise InputBlockedError("H.15 top-level identity mismatch")
    if record.get("raw_response_sha256") != {
        "DGS10": "b59608fa97f00d945292ea77472079d419eee582b0a5ee5af4a2dfa3f5a2f55c",
        "DGS3MO": "6ec27c0460be9365e3648d3f1ed10e4af685aaf232065c1ae19d67cd70766fcf",
    }:
        raise InputBlockedError("H.15 raw response identity mismatch")
    if record.get("selection_proof") != {
        "algorithm_id": "ALFRED_H15_LATEST_COMMON_ELIGIBLE_OBSERVATION_V1",
        "query_sha256": H15_SELECTION_QUERY_SHA256,
        "replayed_db_sha256": expected_top["db_postwrite_sha256"],
        "decisions_verified": 45,
        "mismatch_count": 0,
        "later_eligible_common_count": 0,
    }:
        raise InputBlockedError("H.15 latest-common selection proof mismatch")
    rows = record.get("rows")
    if type(rows) is not list or len(rows) != 45:
        raise InputBlockedError("H.15 input must contain exactly 45 rows")
    weights: list[float] = []
    for point, row in zip(points[:-1], rows, strict=True):
        if type(row) is not dict or set(row) != {
            "decision_at",
            "signal_month",
            "selected_observation_date",
            "staleness_days",
            "DGS10",
            "DGS3MO",
        }:
            raise InputBlockedError("H.15 row schema mismatch")
        if row["decision_at"] != point.decision_at.isoformat():
            raise InputBlockedError("H.15 decision mapping mismatch")
        if row["signal_month"] != point.signal_session.isoformat()[:7]:
            raise InputBlockedError("H.15 signal month mismatch")
        observation_date = _iso_date(row["selected_observation_date"], "observation date")
        staleness = (point.decision_at.date() - observation_date).days
        if row["staleness_days"] != staleness:
            raise InputBlockedError("H.15 staleness field mismatch")
        observations: list[RateObservation] = []
        for series in ("DGS10", "DGS3MO"):
            value = row[series]
            if type(value) is not dict or set(value) != {
                "value_percent",
                "available_at",
                "row_sha",
            }:
                raise InputBlockedError("H.15 tenor schema mismatch")
            observations.append(
                RateObservation(
                    series,
                    observation_date,
                    value["value_percent"],
                    _datetime(value["available_at"], "H.15 available_at"),
                    value["row_sha"],
                )
            )
        weights.append(target_weight(*observations, decision_at=point.decision_at))
    return tuple(weights)


def _apply_actions(
    portfolios: tuple[Portfolio, Portfolio],
    session_date: date,
    actions: tuple[CorporateActionIdentity, ...],
) -> None:
    for portfolio in portfolios:
        portfolio.start_session(session_date)
        for action in actions:
            if action.effective_date != session_date:
                continue
            assert action.cash_amount is not None
            assert action.ex_date is not None and action.pay_date is not None
            portfolio.apply_cash_distribution(
                "SPY",
                event_id=action.action_id,
                amount_per_share=float(action.cash_amount),
                ex_date=action.ex_date,
                pay_date=action.pay_date,
            )


def _rebalance(
    portfolio: Portfolio,
    point: Point,
    target: float | None,
    prior_stage_hash: str,
    definition_sha256: str,
    adapter_sha256: str,
):
    row = point.execution_input
    if (
        row.symbol != "SPY"
        or row.market != "us"
        or row.decision_price_basis != "raw_execution_units"
        or row.execution_price_basis != "retrospective_daily_bar_open_fill"
    ):
        raise InputBlockedError("SPY execution basis mismatch")
    weights = {} if target is None else {"SPY": target}
    return run_static_rebalance(
        portfolio,
        point.calendar,
        signal_session=point.signal_session,
        decision_at=point.decision_at,
        execution_inputs=(row,),
        execution_calendar_revision=point.execution_calendar_revision,
        universe_members=("SPY",),
        universe_snapshot=point.universe_snapshot,
        target_weights=lambda context: weights,
        strategy_definition_sha256=definition_sha256,
        strategy_adapter_sha256=adapter_sha256,
        slippage_bps=ONE_WAY_SLIPPAGE_BPS,
        prior_stage_hash=prior_stage_hash,
    )


def _simulate(
    points: tuple[Point, ...],
    daily_sessions: tuple[date, ...],
    actions: tuple[CorporateActionIdentity, ...],
    weights: tuple[float, ...],
    definition_sha256: str,
    adapter_sha256: str,
) -> tuple[tuple[float, ...], tuple[float, ...], tuple[str, ...], tuple[str, ...]]:
    if len(weights) != 45:
        raise InputBlockedError("Screen-A requires exactly 45 target weights")
    point_by_date = {point.execution_session: point for point in points}
    if len(point_by_date) != 46:
        raise InputBlockedError("execution sessions must be unique")
    strategy = Portfolio.us(INITIAL_CAPITAL)
    benchmark = Portfolio.us(INITIAL_CAPITAL)
    strategy_navs = [INITIAL_CAPITAL]
    benchmark_navs = [INITIAL_CAPITAL]
    strategy_stage = "0" * 64
    benchmark_stage = "0" * 64
    strategy_hashes: list[str] = []
    benchmark_hashes: list[str] = []
    weight_by_date = {
        point.execution_session: weight for point, weight in zip(points[:-1], weights, strict=True)
    }

    for session_date in daily_sessions:
        _apply_actions((strategy, benchmark), session_date, actions)
        point = point_by_date.get(session_date)
        if point is None:
            continue
        if point.terminal_exit:
            strategy_result = _rebalance(
                strategy,
                point,
                None,
                strategy_stage,
                definition_sha256,
                adapter_sha256,
            )
            benchmark_result = _rebalance(
                benchmark,
                point,
                None,
                benchmark_stage,
                definition_sha256,
                adapter_sha256,
            )
            strategy = strategy_result.portfolio
            benchmark = benchmark_result.portfolio
            strategy_navs.append(strategy_result.final_nav)
            benchmark_navs.append(benchmark_result.final_nav)
            strategy_hashes.append(strategy_result.stage_hash)
            benchmark_hashes.append(benchmark_result.stage_hash)
            continue

        strategy_result = _rebalance(
            strategy,
            point,
            weight_by_date[session_date],
            strategy_stage,
            definition_sha256,
            adapter_sha256,
        )
        strategy = strategy_result.portfolio
        strategy_stage = strategy_result.stage_hash
        strategy_hashes.append(strategy_stage)
        if point is points[0]:
            benchmark_result = _rebalance(
                benchmark,
                point,
                1.0,
                benchmark_stage,
                definition_sha256,
                adapter_sha256,
            )
            benchmark = benchmark_result.portfolio
            benchmark_stage = benchmark_result.stage_hash
            benchmark_hashes.append(benchmark_stage)
            continue
        raw_open = point.execution_input.open_price
        if (
            isinstance(raw_open, bool)
            or raw_open is None
            or not math.isfinite(raw_open)
            or raw_open <= 0.0
        ):
            raise InputBlockedError("benchmark boundary requires a positive raw open")
        strategy_navs.append(strategy_result.final_nav)
        benchmark_navs.append(benchmark.nav({"SPY": float(raw_open)}))
    if len(strategy_navs) != 46 or len(benchmark_navs) != 46:
        raise InputBlockedError("Screen-A boundary path is incomplete")
    return tuple(strategy_navs), tuple(benchmark_navs), tuple(strategy_hashes), tuple(benchmark_hashes)


def _target(path: Path) -> None:
    parent = path.parent.lstat()
    if (
        not stat.S_ISDIR(parent.st_mode)
        or parent.st_uid != os.getuid()
        or stat.S_IMODE(parent.st_mode) & ~0o700
        or path.exists()
        or path.is_symlink()
    ):
        raise InputBlockedError("claim/result must be absent beneath an owner-private directory")


def _publish(path: Path, record: dict[str, Any]) -> str:
    _target(path)
    payload = json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        if os.write(fd, payload) != len(payload):
            raise InputBlockedError("private publication was incomplete")
        os.fsync(fd)
        os.link(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        os.close(fd)
        temporary.unlink(missing_ok=True)
    return _sha256_bytes(payload)


def _run_once(
    bundle_path: Path,
    h15_path: Path,
    claim_path: Path,
    result_path: Path,
    expected_hashes: tuple[str, str, str],
) -> None:
    definition_bytes = DEFINITION.read_bytes()
    definition = _json(definition_bytes, "definition")
    actual_hashes = (_sha256_bytes(definition_bytes), _file_sha256(ADAPTER), _file_sha256(RUNNER))
    if tuple(_sha256(value, "expected code identity") for value in expected_hashes) != actual_hashes:
        raise InputBlockedError("definition/adapter/runner identity mismatch")
    if definition.get("status") != "PREREGISTERED_NOT_EXECUTED":
        raise InputBlockedError("definition is not preregistered-not-executed")
    _require_core_identity()
    if claim_path == result_path:
        raise InputBlockedError("claim and result paths must differ")
    _target(result_path)
    identity = {
        "definition_sha256": actual_hashes[0],
        "adapter_sha256": actual_hashes[1],
        "runner_sha256": actual_hashes[2],
        "base_bundle_sha256": BASE_BUNDLE_SHA256,
        "h15_input_sha256": H15_INPUT_SHA256,
        "core_commit": CORE_COMMIT,
        "core_tree": CORE_TREE,
    }
    claim_sha256 = _publish(
        claim_path,
        {
            "research_id": "US_SPY_H15_10Y3M_STATE_V1",
            "mechanism_id": MECHANISM_ID,
            "program_family_id": PROGRAM_FAMILY_ID,
            "program_alpha": PROGRAM_ALPHA,
            "stage": "RETROSPECTIVE_SECONDARY_SCREEN_A",
            "claimed_at": datetime.now(timezone.utc).isoformat(),
            **identity,
        },
    )
    identity["claim_sha256"] = claim_sha256
    try:
        bundle = _capture(bundle_path, BASE_BUNDLE_SHA256, max_bytes=8 * 1024 * 1024)
        h15 = _capture(h15_path, H15_INPUT_SHA256, max_bytes=1024 * 1024)
        _, points, daily_sessions, actions = _load_bundle(bundle)
        weights = _load_h15(h15, points)
        strategy_navs, benchmark_navs, strategy_hashes, benchmark_hashes = _simulate(
            points,
            daily_sessions,
            actions,
            weights,
            actual_hashes[0],
            actual_hashes[1],
        )
        decision = screen_decision(strategy_navs, benchmark_navs)
    except Exception as exc:
        _publish(
            result_path,
            {
                "schema_version": "us-spy-h15-10y3m-state-screen-a-private-result-v1",
                "research_id": "US_SPY_H15_10Y3M_STATE_V1",
                "mechanism_id": MECHANISM_ID,
                "program_family_id": PROGRAM_FAMILY_ID,
                "program_alpha": PROGRAM_ALPHA,
                "stage": "RETROSPECTIVE_SECONDARY_SCREEN_A",
                "classification": "INPUT_BLOCKED",
                "error_type": type(exc).__name__,
                "identity": identity,
                "one_use_execution_consumed": True,
                "rerun_authorized": False,
                "inference_b_opened": False,
                "strategy_candidate_available": False,
                "shadow": False,
                "paper": False,
                "broker": False,
                "live": False,
            },
        )
        raise
    classification = (
        "RETROSPECTIVE_SECONDARY_SCREEN_A_PASS_INFERENCE_B_UNLOCKED"
        if decision.all_gates_pass
        else "RETROSPECTIVE_SECONDARY_SCREEN_A_FAIL"
    )
    result = {
        "schema_version": "us-spy-h15-10y3m-state-screen-a-private-result-v1",
        "research_id": "US_SPY_H15_10Y3M_STATE_V1",
        "mechanism_id": MECHANISM_ID,
        "program_family_id": PROGRAM_FAMILY_ID,
        "program_alpha": PROGRAM_ALPHA,
        "stage": "RETROSPECTIVE_SECONDARY_SCREEN_A",
        "classification": classification,
        "observed_cohorts": decision.observed_cohorts,
        "gates": dict(decision.gates),
        "strategy_metrics_hex": {
            key: float(value).hex() for key, value in vars(decision.strategy).items()
        },
        "benchmark_metrics_hex": {
            key: float(value).hex() for key, value in vars(decision.benchmark).items()
        },
        "sharpe_difference_hex": float(decision.sharpe_difference).hex(),
        "strategy_boundary_navs_hex": [float(value).hex() for value in strategy_navs],
        "benchmark_boundary_navs_hex": [float(value).hex() for value in benchmark_navs],
        "strategy_stage_hashes": strategy_hashes,
        "benchmark_stage_hashes": benchmark_hashes,
        "identity": identity,
        "one_use_execution_consumed": True,
        "rerun_authorized": False,
        "inference_b_opened": False,
        "strategy_candidate_available": False,
        "shadow": False,
        "paper": False,
        "broker": False,
        "live": False,
    }
    _publish(result_path, result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--h15", required=True, type=Path)
    parser.add_argument("--claim", required=True, type=Path)
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--expected-definition-sha256", required=True)
    parser.add_argument("--expected-adapter-sha256", required=True)
    parser.add_argument("--expected-runner-sha256", required=True)
    args = parser.parse_args(argv)
    _run_once(
        args.bundle,
        args.h15,
        args.claim,
        args.result,
        (
            args.expected_definition_sha256,
            args.expected_adapter_sha256,
            args.expected_runner_sha256,
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
