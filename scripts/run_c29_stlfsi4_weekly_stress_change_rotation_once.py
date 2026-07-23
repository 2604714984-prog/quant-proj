"""One-use runner for frozen Cycle 29 STLFSI4 SPY/QQQ rotation."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "src", ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from quant_system.backtest import ExecutionInput, Portfolio, run_static_rebalance  # noqa: E402
from quant_system.data import (  # noqa: E402
    AcceptedSession,
    AcceptedSessionCalendar,
    CalendarIdentity,
    CorporateActionIdentity,
    SourceIdentity,
    calendar_identity_sha256,
)
from quant_system.markets.universe import (  # noqa: E402
    StatusEvidence,
    UniverseSnapshotIdentity,
    lifecycle_coverage_sha256,
    ordered_members_sha256,
)
from research.adapters.c29_stlfsi4_weekly_stress_change_rotation import (  # noqa: E402
    HOLDOUT_INTERVALS,
    INITIAL_CAPITAL,
    PROGRAM_ALPHA,
    RESEARCH_ID,
    VALIDATION_INTERVALS,
    holdout_decision,
    validation_decision,
)


DEFINITION = ROOT / "research/definitions/c29_stlfsi4_weekly_stress_change_rotation_v1.json"
ADAPTER = ROOT / "research/adapters/c29_stlfsi4_weekly_stress_change_rotation.py"
RUNNER = Path(__file__).resolve()
DEFINITION_SHA256 = "99dcf9f76c6e9b855af1df44f04a9551fcd26dd9189dd4e062fcd40bcf803092"
ADAPTER_SHA256 = "fbbd285306a480c2f3090f07f330197c0fdc07f4dc80b25bc7c2b50b98fd27f9"
SIGNAL_SHA256 = "b22195f8b097afb4b2a6690ee0ca13065b5844f7d5c29e4a55652e23a437b3bb"
SIGNAL_RECEIPT_SHA256 = "9214ce9de3218ca3f0d03f8913accc6fc8e1fa5a9ebbffbac6f856e2479277b9"
RUNTIME_SHA256 = "15a654f3002f5d83b5907fc23b4ec0e1e8d8022174d9a29479f80c0ca110cb84"
RUNTIME_RECEIPT_SHA256 = "5c5153ce963d370ddea20347dbec989670259ee5dfb5b986967464fd4f5c9645"
CORE_SOURCE_FILE_COUNT = 23
CORE_SOURCE_SHA256 = "46ae2fe342a40034b9caacb6cc48a182947a49da9d874de31a1fdb60be0b9a80"
INCLUSION_RULE_SHA256 = "89483ee34a4b87fcdb728889dc31c7dc7222f85b3071ff7a97c65148e1b6402e"
INPUT_ROOT = Path(
    "/home/rongyu/workspace/quant-data/staging/"
    "c29_stlfsi4_weekly_stress_change_rotation_spy_qqq_v1"
)
SIGNAL_INPUT = INPUT_ROOT / "stlfsi4_weekly_stress_change_signal_packet.json"
SIGNAL_RECEIPT = INPUT_ROOT / "materialization_receipt.json"
RUNTIME_INPUT = INPUT_ROOT / "c29_full_runtime_packet.json"
RUNTIME_RECEIPT = INPUT_ROOT / "c29_full_runtime_receipt.json"
PRIVATE_ROOT = Path("/home/rongyu/workspace/quant-data/private_results")
VALIDATION_CLAIM = PRIVATE_ROOT / f"{RESEARCH_ID.lower()}_validation/claim.json"
VALIDATION_RESULT = VALIDATION_CLAIM.with_name("result.json")
HOLDOUT_CLAIM = PRIVATE_ROOT / f"{RESEARCH_ID.lower()}_holdout/claim.json"
HOLDOUT_RESULT = HOLDOUT_CLAIM.with_name("result.json")
ONE_WAY_SLIPPAGE_BPS = 10.0


class InputBlockedError(ValueError):
    """Fail-closed identity, chronology, schema, or one-use error."""


@dataclass(frozen=True)
class Signal:
    stage: str
    start: date
    end: date
    available_at: datetime
    target_symbol: str
    identity_sha256: str


@dataclass(frozen=True)
class Point:
    signal_session: date
    decision_at: datetime
    execution_session: date
    calendar: AcceptedSessionCalendar
    executions: tuple[ExecutionInput, ExecutionInput]
    snapshot: UniverseSnapshotIdentity
    target_symbol: str | None


@dataclass(frozen=True)
class Bundle:
    stage: str
    points: tuple[Point, ...]
    daily_sessions: tuple[date, ...]
    actions: tuple[CorporateActionIdentity, ...]


def _hash_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _compact(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()


def _sha(value: object, field: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise InputBlockedError(f"{field} must be a lowercase SHA-256")
    return value


def _file_hash(path: Path) -> str:
    return _hash_bytes(path.read_bytes())


def _core_identity() -> tuple[int, str]:
    rows: list[dict[str, str]] = []
    for path in sorted((ROOT / "src/quant_system").rglob("*.py")):
        if path.is_symlink() or not path.is_file():
            raise InputBlockedError("shared-core source must contain regular files")
        rows.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": _file_hash(path),
            }
        )
    return len(rows), _hash_bytes(_compact(rows))


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise InputBlockedError(f"duplicate JSON key: {key}")
        output[key] = value
    return output


def _json(payload: bytes, field: str) -> dict[str, Any]:
    def nonfinite(value: str) -> None:
        raise InputBlockedError(f"nonfinite JSON constant: {value}")

    try:
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=_strict_object,
            parse_constant=nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputBlockedError(f"{field} is not strict UTF-8 JSON") from exc
    if type(value) is not dict:
        raise InputBlockedError(f"{field} must be a JSON object")
    return value


def _read_regular(path: Path, *, max_bytes: int) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise InputBlockedError(f"cannot open protected input: {path}") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid():
            raise InputBlockedError("input must be an owner-controlled regular file")
        if not 0 < before.st_size <= max_bytes:
            raise InputBlockedError("input size is outside the frozen bound")
        chunks: list[bytes] = []
        total = 0
        while True:
            block = os.read(descriptor, min(1024 * 1024, max_bytes + 1 - total))
            if not block:
                break
            chunks.append(block)
            total += len(block)
            if total > max_bytes:
                raise InputBlockedError("input exceeds the frozen size bound")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    current = os.stat(path, follow_symlinks=False)
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(
        getattr(before, name) != getattr(after, name)
        or getattr(after, name) != getattr(current, name)
        for name in fields
    ):
        raise InputBlockedError("input changed during descriptor-bound capture")
    return b"".join(chunks)


def _capture(path: Path, expected_sha: str, *, max_bytes: int) -> bytes:
    payload = _read_regular(path, max_bytes=max_bytes)
    if _hash_bytes(payload) != _sha(expected_sha, "expected input SHA-256"):
        raise InputBlockedError("input SHA-256 mismatch")
    return payload


def _date(value: object, field: str) -> date:
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


def _source(row: object) -> SourceIdentity:
    if type(row) is not dict:
        raise InputBlockedError("source identity must be an object")
    return SourceIdentity(
        row["source_url"],
        row["content_sha256"],
        _datetime(row["available_at"], "source available_at"),
        _datetime(row["retrieved_at"], "source retrieved_at"),
        row["revision_id"],
        row["supersedes_revision_id"],
    )


def _calendar(row: object) -> AcceptedSessionCalendar:
    if type(row) is not dict or type(row.get("session_rows")) is not list:
        raise InputBlockedError("calendar schema mismatch")
    sessions = tuple(
        AcceptedSession(
            _date(item["session_date"], "session_date"),
            _datetime(item["open_at"], "open_at"),
            _datetime(item["close_at"], "close_at"),
            _source(item["source"]),
            item["exchange_timezone"],
            item["is_early_close"],
            item["exchange_id"],
        )
        for item in row["session_rows"]
    )
    identity = row["calendar_identity"]
    frozen = CalendarIdentity(
        identity["exchange_id"],
        identity["exchange_timezone"],
        _date(identity["coverage_start"], "coverage_start"),
        _date(identity["coverage_end"], "coverage_end"),
        identity["session_count"],
        identity["session_dates_sha256"],
        identity["session_rows_sha256"],
        _source(identity["source_identity"]),
    )
    calendar = AcceptedSessionCalendar(sessions, identity=frozen)
    if calendar.exchange_id != "XNYS" or calendar.exchange_timezone != "America/New_York":
        raise InputBlockedError("calendar must be XNYS America/New_York")
    return calendar


def _status(row: object, symbol: str) -> StatusEvidence:
    if type(row) is not dict:
        raise InputBlockedError("status evidence must be an object")
    if row.get("symbol") != symbol or row.get("exchange_timezone") != "America/New_York":
        raise InputBlockedError("status evidence symbol or timezone mismatch")
    return StatusEvidence(
        row["status_id"],
        row["symbol"],
        row["kind"],
        row["value"],
        _date(row["effective_from"], "effective_from"),
        None if row["effective_to"] is None else _date(row["effective_to"], "effective_to"),
        row["exchange_timezone"],
        _source(row["source"]),
    )


def _action(row: object) -> CorporateActionIdentity:
    if type(row) is not dict or row.get("subject_id") not in {"SPY", "QQQ"}:
        raise InputBlockedError("corporate action symbol mismatch")
    if row.get("action_type") not in {"cash_dividend", "special_dividend"}:
        raise InputBlockedError("only frozen cash distributions are supported")
    return CorporateActionIdentity(
        row["subject_id"],
        row["action_id"],
        row["action_type"],
        _datetime(row["effective_at"], "action effective_at"),
        _source(row["source"]),
        row["exchange_timezone"],
        ex_date=_date(row["ex_date"], "ex_date"),
        record_date=_date(row["record_date"], "record_date"),
        pay_date=_date(row["pay_date"], "pay_date"),
        cash_amount=Decimal(row["cash_amount"]),
        currency=row["currency"],
        unit=row["unit"],
    )


def _signals(payload: bytes, receipt_payload: bytes) -> dict[str, tuple[Signal, ...]]:
    record = _json(payload, "STLFSI4 signal packet")
    receipt = _json(receipt_payload, "STLFSI4 signal receipt")
    if (
        record.get("schema_version") != "c29-stlfsi4-weekly-stress-change-signal-v1"
        or record.get("research_id") != RESEARCH_ID
        or record.get("series_id") != "STLFSI4"
        or record.get("signal_rule")
        != "latest PIT-qualified weekly STLFSI4 delta above zero means SPY; equal or lower means QQQ"
        or record.get("strategy_outcomes_opened") is not False
        or record.get("price_values_used_for_signal") is not False
        or record.get("database_opened") is not False
        or record.get("database_write") is not False
        or receipt.get("research_id") != RESEARCH_ID
        or receipt.get("status") != "INPUT_MATERIALIZED_STATE_SUPPORT_PASS"
        or receipt.get("signal_packet_sha256") != SIGNAL_SHA256
    ):
        raise InputBlockedError("STLFSI4 signal boundary mismatch")
    rows = record.get("signals")
    if type(rows) is not list or len(rows) != 188:
        raise InputBlockedError("STLFSI4 signal row count mismatch")
    parsed: dict[str, list[Signal]] = {
        "validation": [],
        "retrospective_holdout": [],
    }
    for row in rows:
        if type(row) is not dict or row.get("stage") not in {
            "development",
            "validation",
            "retrospective_holdout",
        }:
            raise InputBlockedError("STLFSI4 signal stage mismatch")
        current = row.get("current_selection")
        previous = row.get("previous_selection")
        if type(current) is not dict or type(previous) is not dict:
            raise InputBlockedError("STLFSI4 selections are required")
        for selection in (previous, current):
            row_hash = selection.get("row_sha256")
            identity = {key: value for key, value in selection.items() if key != "row_sha256"}
            if (
                selection.get("series_id") != "STLFSI4"
                or selection.get("source_class")
                != "OFFICIAL_ALFRED_STLFSI4_REALTIME_VINTAGE"
                or selection.get("raw_response_sha256")
                != "2a3a10a25fff09f12d5f223827edce071f40181a64d18d306a01443d15aa8465"
                or row_hash != _hash_bytes(_compact(identity))
            ):
                raise InputBlockedError("STLFSI4 source row identity mismatch")
        current_value = current.get("value_index")
        previous_value = previous.get("value_index")
        change = row.get("delta_index_points")
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            for value in (current_value, previous_value, change)
        ):
            raise InputBlockedError("STLFSI4 values must be finite")
        expected_change = float(current_value) - float(previous_value)
        expected_target = "SPY" if expected_change > 0.0 else "QQQ"
        if (
            not math.isclose(float(change), expected_change, rel_tol=0, abs_tol=1e-12)
            or row.get("target_symbol") != expected_target
        ):
            raise InputBlockedError("STLFSI4 signal arithmetic mismatch")
        identity = {
            "release_vintage_date": row["release_vintage_date"],
            "available_at": row["available_at"],
            "current_period_start_date": row["current_period_start_date"],
            "previous_period_start_date": row["previous_period_start_date"],
            "current_row_sha256": row["current_row_sha256"],
            "previous_row_sha256": row["previous_row_sha256"],
            "delta_index_points": change,
            "target_symbol": expected_target,
            "execution_session": row["execution_session"],
            "execution_open_at": row["execution_open_at"],
        }
        identity_sha = _hash_bytes(_compact(identity))
        if row.get("signal_identity_sha256") != identity_sha:
            raise InputBlockedError("STLFSI4 signal identity hash mismatch")
        if row["stage"] in parsed:
            parsed[row["stage"]].append(
                Signal(
                    row["stage"],
                    _date(row["holding_start_execution_session"], "holding start"),
                    _date(row["holding_end_execution_session"], "holding end"),
                    _datetime(row["available_at"], "signal available_at"),
                    expected_target,
                    identity_sha,
                )
            )
    output = {key: tuple(value) for key, value in parsed.items()}
    if (
        len(output["validation"]) != VALIDATION_INTERVALS
        or len(output["retrospective_holdout"]) != HOLDOUT_INTERVALS
    ):
        raise InputBlockedError("STLFSI4 split counts mismatch")
    support = record.get("state_support")
    if type(support) is not dict:
        raise InputBlockedError("STLFSI4 state support is missing")
    for stage, group in output.items():
        if any(
            left.end != right.start
            for left, right in zip(group, group[1:], strict=False)
        ):
            raise InputBlockedError("STLFSI4 signal intervals are not contiguous")
        states = tuple(row.target_symbol for row in group)
        observed = {
            "complete_intervals": len(states),
            "spy_intervals": states.count("SPY"),
            "qqq_intervals": states.count("QQQ"),
            "spy_to_qqq": sum(
                left == "SPY" and right == "QQQ"
                for left, right in zip(states, states[1:], strict=False)
            ),
            "qqq_to_spy": sum(
                left == "QQQ" and right == "SPY"
                for left, right in zip(states, states[1:], strict=False)
            ),
        }
        if support.get(stage) != observed:
            raise InputBlockedError("STLFSI4 state support mismatch")
    return output


def _execution(
    row: object,
    statuses: tuple[StatusEvidence, ...],
    *,
    symbol: str,
    signal_session: date,
    decision_at: datetime,
    execution_session: date,
    calendar: AcceptedSessionCalendar,
) -> ExecutionInput:
    if type(row) is not dict:
        raise InputBlockedError("execution input must be an object")
    accepted_signal = calendar.session_on(signal_session, as_of=decision_at)
    accepted_execution = calendar.session_on(execution_session, as_of=decision_at)
    decision_source = _source(row["decision_price_source"])
    execution_source = _source(row["source"])
    decision_price = row.get("decision_price")
    raw_open = row.get("raw_open")
    if (
        row.get("symbol") != symbol
        or row.get("market") != "us"
        or row.get("currency") != "USD"
        or row.get("decision_price_basis") != "raw_execution_units"
        or row.get("execution_price_basis") != "retrospective_daily_bar_open_fill"
        or _date(row["decision_price_session"], "decision price session")
        != signal_session
        or _datetime(row["decision_price_effective_at"], "decision price effective_at")
        != accepted_signal.close_at
        or _datetime(row["execution_price_effective_at"], "execution effective_at")
        != accepted_execution.open_at
        or decision_source.available_at > decision_at
        or execution_source.available_at < accepted_execution.open_at
        or any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or float(value) <= 0.0
            for value in (decision_price, raw_open)
        )
    ):
        raise InputBlockedError("execution price or timing identity mismatch")
    return ExecutionInput(
        symbol,
        "us",
        float(raw_open),
        "USD",
        execution_source,
        statuses,
        corporate_actions=(),
        decision_price=float(decision_price),
        decision_price_source=decision_source,
        decision_price_basis="raw_execution_units",
        execution_price_effective_at=accepted_execution.open_at,
        execution_price_basis="retrospective_daily_bar_open_fill",
    )


def _combined_snapshot(
    executions: tuple[ExecutionInput, ExecutionInput],
    *,
    calendar: AcceptedSessionCalendar,
    execution_session: date,
    decision_at: datetime,
) -> UniverseSnapshotIdentity:
    members = ("QQQ", "SPY")
    by_symbol = {row.symbol: row.status_records for row in executions}
    accepted = calendar.session_on(execution_session, as_of=decision_at)
    lifecycle_hash = lifecycle_coverage_sha256(
        members,
        accepted,
        decision_at,
        by_symbol,
        market="us",
    )
    sources = tuple(row.status_records[-1].source for row in executions)
    source = SourceIdentity(
        "https://www.sec.gov/Archives/edgar/data/1067839/000119312520018563/d835635d485bpos.htm",
        _hash_bytes(
            _compact(
                {
                    "members": members,
                    "source_hashes": sorted(item.content_sha256 for item in sources),
                }
            )
        ),
        max(item.available_at for item in sources),
        max(item.retrieved_at for item in sources),
        f"c29-spy-qqq-universe-{execution_session.isoformat()}",
    )
    return UniverseSnapshotIdentity(
        "us",
        calendar.identity.exchange_id,
        execution_session,
        len(members),
        ordered_members_sha256(members),
        lifecycle_hash,
        INCLUSION_RULE_SHA256,
        calendar_identity_sha256(calendar.identity),
        source,
    )


def _load_bundle(
    payload: bytes,
    receipt_payload: bytes,
    *,
    stage: str,
    signals: tuple[Signal, ...],
) -> Bundle:
    record = _json(payload, "C29 full runtime packet")
    receipt = _json(receipt_payload, "C29 full runtime receipt")
    if (
        record.get("schema_version") != "c29-stlfsi4-spy-qqq-full-runtime-v1"
        or record.get("research_id") != RESEARCH_ID
        or record.get("evidence_class") != "RETROSPECTIVE_SECONDARY_ONLY"
        or record.get("strategy_outcomes_opened") is not False
        or record.get("price_values_used_for_signal") is not False
        or record.get("adjusted_prices_used") is not False
        or record.get("source_selected_using_performance") is not False
        or record.get("database_opened") is not False
        or record.get("database_write") is not False
        or not str(record.get("corporate_action_mode", "")).startswith(
            "retrospective_accounting_only_not_signal_or_selection"
        )
        or receipt.get("research_id") != RESEARCH_ID
        or receipt.get("status") != "INPUT_MATERIALIZED_STATE_SUPPORT_PASS"
        or receipt.get("runtime_packet_sha256") != RUNTIME_SHA256
        or receipt.get("strategy_outcomes_opened") is not False
        or receipt.get("database_write") is not False
    ):
        raise InputBlockedError("C29 runtime boundary mismatch")
    raw_epochs = record.get("calendar_epochs")
    if type(raw_epochs) is not dict or set(raw_epochs) != {
        "xnys-2021-2022-2024-official-calendar",
        "xnys-2024-2025-2027-official-calendar",
    }:
        raise InputBlockedError("C29 calendar epochs mismatch")
    epochs = {key: _calendar(value) for key, value in raw_epochs.items()}
    raw_statuses = record.get("status_evidence")
    if type(raw_statuses) is not dict:
        raise InputBlockedError("C29 status evidence is missing")
    statuses = {
        symbol: tuple(_status(row, symbol) for row in raw_statuses.get(symbol, []))
        for symbol in ("QQQ", "SPY")
    }
    if len(statuses["QQQ"]) != 2 or len(statuses["SPY"]) != 4:
        raise InputBlockedError("C29 lifecycle coverage mismatch")
    raw_actions = record.get("corporate_actions")
    if type(raw_actions) is not list:
        raise InputBlockedError("C29 corporate actions are missing")
    all_actions = tuple(_action(row) for row in raw_actions)
    if len(all_actions) != 27 or len({row.action_id for row in all_actions}) != 27:
        raise InputBlockedError("C29 corporate action identities mismatch")
    stage_key = "validation" if stage == "validation" else "retrospective_holdout"
    raw_stage = record.get("stages", {}).get(stage_key)
    if type(raw_stage) is not dict:
        raise InputBlockedError("C29 runtime stage is missing")
    raw_points = raw_stage.get("execution_points")
    if type(raw_points) is not list or len(raw_points) != len(signals) + 1:
        raise InputBlockedError("C29 execution point count mismatch")
    points: list[Point] = []
    for index, raw in enumerate(raw_points):
        if type(raw) is not dict:
            raise InputBlockedError("C29 execution point must be an object")
        supplied_hash = raw.get("point_sha256")
        identity = dict(raw)
        identity.pop("point_sha256", None)
        if supplied_hash != _hash_bytes(_compact(identity)):
            raise InputBlockedError("C29 execution point hash mismatch")
        execution_session = _date(raw["execution_session"], "execution session")
        signal_session = _date(raw["signal_session"], "signal session")
        decision_at = _datetime(raw["decision_at"], "decision_at")
        signal = None if index == len(signals) else signals[index]
        next_execution = (
            None
            if signal is None
            else _date(raw_points[index + 1]["execution_session"], "next execution")
        )
        if signal is None:
            if any(
                raw.get(key) is not None
                for key in (
                    "target_symbol",
                    "signal_identity_sha256",
                    "signal_available_at",
                )
            ):
                raise InputBlockedError("terminal point carries a signal")
        elif (
            signal.start != execution_session
            or signal.end != next_execution
            or signal.available_at >= decision_at
            or raw.get("target_symbol") != signal.target_symbol
            or raw.get("signal_identity_sha256") != signal.identity_sha256
            or _datetime(raw["signal_available_at"], "runtime signal available_at")
            != signal.available_at
        ):
            raise InputBlockedError("C29 signal does not bind the runtime point")
        try:
            calendar = epochs[raw["decision_calendar_epoch_id"]]
        except KeyError as exc:
            raise InputBlockedError("unknown C29 calendar epoch") from exc
        if raw.get("execution_calendar_revision_id") is not None:
            raise InputBlockedError("C29 has no execution calendar revision")
        if calendar.next_session(signal_session, as_of=decision_at).session_date != execution_session:
            raise InputBlockedError("C29 execution is not the next accepted session")
        raw_executions = raw.get("executions")
        if type(raw_executions) is not dict or set(raw_executions) != {"QQQ", "SPY"}:
            raise InputBlockedError("C29 execution members mismatch")
        executions = tuple(
            _execution(
                raw_executions[symbol],
                statuses[symbol],
                symbol=symbol,
                signal_session=signal_session,
                decision_at=decision_at,
                execution_session=execution_session,
                calendar=calendar,
            )
            for symbol in ("QQQ", "SPY")
        )
        snapshot = _combined_snapshot(
            executions,
            calendar=calendar,
            execution_session=execution_session,
            decision_at=decision_at,
        )
        points.append(
            Point(
                signal_session,
                decision_at,
                execution_session,
                calendar,
                executions,
                snapshot,
                None if signal is None else signal.target_symbol,
            )
        )
    reconstruction = record.get("reconstruction_calendar")
    if type(reconstruction) is not dict or type(reconstruction.get("session_rows")) is not list:
        raise InputBlockedError("C29 reconstruction calendar is missing")
    reconstruction_dates = tuple(
        _date(row["session_date"], "reconstruction session")
        for row in reconstruction["session_rows"]
    )
    selected = tuple(
        day
        for day in reconstruction_dates
        if points[0].execution_session <= day <= points[-1].execution_session
    )
    raw_daily = raw_stage.get("daily_sessions")
    if type(raw_daily) is not list:
        raise InputBlockedError("C29 daily sessions are missing")
    daily = tuple(_date(value, "daily session") for value in raw_daily)
    if daily != selected:
        raise InputBlockedError("C29 daily session coverage mismatch")
    actions = tuple(
        action
        for action in all_actions
        if daily[0] <= action.effective_date <= daily[-1]
    )
    return Bundle(stage, tuple(points), daily, actions)


def _apply_actions(
    portfolio: Portfolio,
    session_date: date,
    actions: tuple[CorporateActionIdentity, ...],
) -> None:
    portfolio.start_session(session_date)
    for action in actions:
        if action.effective_date != session_date:
            continue
        if (
            action.action_type not in {"cash_dividend", "special_dividend"}
            or action.cash_amount is None
            or action.ex_date is None
            or action.pay_date is None
        ):
            raise InputBlockedError("cash action identity is incomplete")
        portfolio.apply_cash_distribution(
            action.subject_id,
            event_id=action.action_id,
            amount_per_share=float(action.cash_amount),
            ex_date=action.ex_date,
            pay_date=action.pay_date,
        )


def _rebalance(
    portfolio: Portfolio,
    point: Point,
    weights: dict[str, float],
    prior_stage_hash: str,
):
    return run_static_rebalance(
        portfolio,
        point.calendar,
        signal_session=point.signal_session,
        decision_at=point.decision_at,
        execution_inputs=point.executions,
        universe_members=("QQQ", "SPY"),
        universe_snapshot=point.snapshot,
        target_weights=lambda context: dict(weights),
        strategy_definition_sha256=DEFINITION_SHA256,
        strategy_adapter_sha256=ADAPTER_SHA256,
        slippage_bps=ONE_WAY_SLIPPAGE_BPS,
        prior_stage_hash=prior_stage_hash,
    )


def _simulate(
    bundle: Bundle,
) -> tuple[tuple[float, ...], tuple[float, ...], tuple[str, ...]]:
    point_by_date = {point.execution_session: point for point in bundle.points}
    actions_by_date = {
        day: tuple(action for action in bundle.actions if action.effective_date == day)
        for day in bundle.daily_sessions
    }
    strategy = Portfolio.us(INITIAL_CAPITAL)
    comparator = Portfolio.us(INITIAL_CAPITAL)
    strategy_navs = [INITIAL_CAPITAL]
    comparator_navs = [INITIAL_CAPITAL]
    strategy_stage = RUNTIME_SHA256
    comparator_stage = RUNTIME_RECEIPT_SHA256
    stage_hashes: list[str] = []
    for session_date in bundle.daily_sessions:
        daily_actions = actions_by_date[session_date]
        _apply_actions(strategy, session_date, daily_actions)
        _apply_actions(comparator, session_date, daily_actions)
        point = point_by_date.get(session_date)
        if point is None:
            continue
        if point.target_symbol is None:
            strategy_result = _rebalance(strategy, point, {}, strategy_stage)
            comparator_result = _rebalance(comparator, point, {}, comparator_stage)
            strategy, comparator = strategy_result.portfolio, comparator_result.portfolio
            strategy_navs.append(strategy_result.final_nav)
            comparator_navs.append(comparator_result.final_nav)
            stage_hashes.extend(
                (strategy_result.stage_hash, comparator_result.stage_hash)
            )
            continue
        strategy_result = _rebalance(
            strategy,
            point,
            {point.target_symbol: 1.0},
            strategy_stage,
        )
        strategy, strategy_stage = strategy_result.portfolio, strategy_result.stage_hash
        stage_hashes.append(strategy_stage)
        comparator_result = _rebalance(
            comparator,
            point,
            {"QQQ": 0.5, "SPY": 0.5},
            comparator_stage,
        )
        comparator, comparator_stage = (
            comparator_result.portfolio,
            comparator_result.stage_hash,
        )
        stage_hashes.append(comparator_stage)
        if point is bundle.points[0]:
            continue
        strategy_navs.append(strategy_result.final_nav)
        comparator_navs.append(comparator_result.final_nav)
    expected = (
        VALIDATION_INTERVALS if bundle.stage == "validation" else HOLDOUT_INTERVALS
    ) + 1
    if len(strategy_navs) != expected or len(comparator_navs) != expected:
        raise InputBlockedError("C29 split boundary path is incomplete")
    strategy_returns = tuple(
        right / left - 1.0
        for left, right in zip(strategy_navs, strategy_navs[1:], strict=True)
    )
    comparator_returns = tuple(
        right / left - 1.0
        for left, right in zip(comparator_navs, comparator_navs[1:], strict=True)
    )
    return strategy_returns, comparator_returns, tuple(stage_hashes)


def _decision(
    stage: str,
    strategy: tuple[float, ...],
    comparator: tuple[float, ...],
) -> dict[str, Any]:
    decision = (
        validation_decision(strategy, comparator)
        if stage == "validation"
        else holdout_decision(strategy, comparator)
    )
    record = {
        "stage": stage,
        "observed_intervals": decision.observed_intervals,
        "strategy": asdict(decision.strategy),
        "comparator_50_50": asdict(decision.comparator),
        "gates": {name: passed for name, passed in decision.gates},
        "all_gates_pass": decision.all_gates_pass,
    }
    if stage == "validation":
        record["arithmetic_mean_active_return"] = decision.arithmetic_mean_active_return
    else:
        record["inference"] = asdict(decision.inference)
    return record


def _private_parent(path: Path) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    metadata = path.parent.lstat()
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) & ~0o700
        or path.exists()
        or path.is_symlink()
    ):
        raise InputBlockedError(
            "one-use target must be absent under an owner-private directory"
        )


def _publish(path: Path, record: dict[str, Any]) -> str:
    _private_parent(path)
    payload = _compact(record)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        descriptor = os.open(temporary, flags, 0o600)
        try:
            written = 0
            while written < len(payload):
                count = os.write(descriptor, payload[written:])
                if count <= 0:
                    raise InputBlockedError("private publication was incomplete")
                written += count
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.link(temporary, path, follow_symlinks=False)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)
    if stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise InputBlockedError("private publication mode is not 0600")
    return _hash_bytes(payload)


def _claim(
    stage: str,
    runner_sha: str,
    validation_result_sha: str | None,
) -> dict[str, Any]:
    return {
        "schema_version": "c29-stlfsi4-spy-qqq-claim-v1",
        "research_id": RESEARCH_ID,
        "stage": stage,
        "claimed_at": datetime.now().astimezone().isoformat(),
        "definition_sha256": DEFINITION_SHA256,
        "adapter_sha256": ADAPTER_SHA256,
        "runner_sha256": runner_sha,
        "signal_packet_sha256": SIGNAL_SHA256,
        "signal_receipt_sha256": SIGNAL_RECEIPT_SHA256,
        "runtime_packet_sha256": RUNTIME_SHA256,
        "runtime_receipt_sha256": RUNTIME_RECEIPT_SHA256,
        "validation_result_sha256": validation_result_sha,
        "one_use_execution_consumed": True,
        "rerun_authorized": False,
    }


def _result(
    stage: str,
    classification: str,
    *,
    claim_sha: str,
    runner_sha: str,
    decision: dict[str, Any] | None,
    stage_hashes: tuple[str, ...] = (),
    error: Exception | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "c29-stlfsi4-spy-qqq-result-v1",
        "research_id": RESEARCH_ID,
        "stage": stage,
        "classification": classification,
        "evidence_class": "RETROSPECTIVE_SECONDARY_ONLY",
        "program_alpha": PROGRAM_ALPHA,
        "definition_sha256": DEFINITION_SHA256,
        "adapter_sha256": ADAPTER_SHA256,
        "runner_sha256": runner_sha,
        "signal_packet_sha256": SIGNAL_SHA256,
        "runtime_packet_sha256": RUNTIME_SHA256,
        "claim_sha256": claim_sha,
        "decision": decision,
        "stage_hashes": list(stage_hashes),
        "corporate_action_limitation": (
            "official historical distributions are retrospective account-reconstruction "
            "inputs and are not represented as PIT signal evidence"
        ),
        "error_type": None if error is None else type(error).__name__,
        "error_message": None if error is None else str(error),
        "strategy_candidate_available": False,
        "shadow": False,
        "paper": False,
        "broker": False,
        "live": False,
        "rerun_authorized": False,
    }


def _accepted_validation_result() -> tuple[bytes, str]:
    payload = _read_regular(VALIDATION_RESULT, max_bytes=2 * 1024 * 1024)
    payload_sha = _hash_bytes(payload)
    record = _json(payload, "validation result")
    if (
        record.get("research_id") != RESEARCH_ID
        or record.get("stage") != "validation"
        or record.get("classification")
        != "RETROSPECTIVE_SECONDARY_VALIDATION_PASS_HOLDOUT_UNLOCKED"
        or record.get("definition_sha256") != DEFINITION_SHA256
        or record.get("adapter_sha256") != ADAPTER_SHA256
        or record.get("signal_packet_sha256") != SIGNAL_SHA256
        or record.get("runtime_packet_sha256") != RUNTIME_SHA256
        or record.get("decision", {}).get("all_gates_pass") is not True
    ):
        raise InputBlockedError("holdout remains sealed by the validation result")
    return payload, payload_sha


def execute_stage(stage: str) -> dict[str, Any]:
    if stage not in {"validation", "holdout"}:
        raise InputBlockedError("stage must be validation or holdout")
    if _file_hash(DEFINITION) != DEFINITION_SHA256:
        raise InputBlockedError("definition bytes differ from the frozen identity")
    if _file_hash(ADAPTER) != ADAPTER_SHA256:
        raise InputBlockedError("adapter bytes differ from the frozen identity")
    if _core_identity() != (CORE_SOURCE_FILE_COUNT, CORE_SOURCE_SHA256):
        raise InputBlockedError("shared-core bytes differ from the frozen identity")
    definition = _json(
        _capture(DEFINITION, DEFINITION_SHA256, max_bytes=256 * 1024),
        "definition",
    )
    if (
        definition.get("research_id") != RESEARCH_ID
        or definition.get("program_multiplicity", {}).get("sole_primary_alpha")
        != PROGRAM_ALPHA
        or definition.get("source_identities", {}).get("adapter_sha256")
        != ADAPTER_SHA256
        or definition.get("source_identities", {}).get("runtime_packet_sha256")
        != RUNTIME_SHA256
        or definition.get("expected_inclusion_rule_sha256")
        != INCLUSION_RULE_SHA256
        or definition.get("boundaries", {}).get("strategy_candidate_available")
        is not False
    ):
        raise InputBlockedError("definition semantic identity mismatch")
    runner_sha = _file_hash(RUNNER)
    validation_result_sha = None
    if stage == "validation":
        if any(
            path.exists()
            for path in (
                VALIDATION_CLAIM,
                VALIDATION_RESULT,
                HOLDOUT_CLAIM,
                HOLDOUT_RESULT,
            )
        ):
            raise InputBlockedError("Cycle 29 one-use state is not pristine")
        claim_path, result_path = VALIDATION_CLAIM, VALIDATION_RESULT
        signal_stage = "validation"
    else:
        if HOLDOUT_CLAIM.exists() or HOLDOUT_RESULT.exists():
            raise InputBlockedError("Cycle 29 holdout one-use state is not pristine")
        _, validation_result_sha = _accepted_validation_result()
        claim_path, result_path = HOLDOUT_CLAIM, HOLDOUT_RESULT
        signal_stage = "retrospective_holdout"
    claim_sha = _publish(
        claim_path,
        _claim(stage, runner_sha, validation_result_sha),
    )
    try:
        signal_payload = _capture(
            SIGNAL_INPUT,
            SIGNAL_SHA256,
            max_bytes=2 * 1024 * 1024,
        )
        signal_receipt_payload = _capture(
            SIGNAL_RECEIPT,
            SIGNAL_RECEIPT_SHA256,
            max_bytes=256 * 1024,
        )
        signals = _signals(signal_payload, signal_receipt_payload)
        runtime_payload = _capture(
            RUNTIME_INPUT,
            RUNTIME_SHA256,
            max_bytes=32 * 1024 * 1024,
        )
        runtime_receipt_payload = _capture(
            RUNTIME_RECEIPT,
            RUNTIME_RECEIPT_SHA256,
            max_bytes=256 * 1024,
        )
        bundle = _load_bundle(
            runtime_payload,
            runtime_receipt_payload,
            stage=stage,
            signals=signals[signal_stage],
        )
        strategy, comparator, stage_hashes = _simulate(bundle)
        decision = _decision(stage, strategy, comparator)
        classification = (
            "RETROSPECTIVE_SECONDARY_VALIDATION_PASS_HOLDOUT_UNLOCKED"
            if stage == "validation" and decision["all_gates_pass"]
            else "RETROSPECTIVE_SECONDARY_VALIDATION_FAIL"
            if stage == "validation"
            else "RETROSPECTIVE_SECONDARY_PASS_PENDING_REVIEW"
            if decision["all_gates_pass"]
            else "RETROSPECTIVE_SECONDARY_HOLDOUT_FAIL"
        )
        record = _result(
            stage,
            classification,
            claim_sha=claim_sha,
            runner_sha=runner_sha,
            decision=decision,
            stage_hashes=stage_hashes,
        )
    except Exception as exc:
        record = _result(
            stage,
            "INPUT_BLOCKED_CLAIM_CONSUMED",
            claim_sha=claim_sha,
            runner_sha=runner_sha,
            decision=None,
            error=exc,
        )
    _publish(result_path, record)
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("validation", "holdout"), required=True)
    args = parser.parse_args()
    record = execute_stage(args.stage)
    decision = record.get("decision") or {}
    gates = decision.get("gates") or {}
    print(
        json.dumps(
            {
                "classification": record["classification"],
                "stage": record["stage"],
                "observed_intervals": decision.get("observed_intervals"),
                "gates_passed": sum(value is True for value in gates.values()),
                "gates_total": len(gates),
                "candidate": False,
                "rerun": False,
                "shadow": False,
                "paper": False,
                "broker": False,
                "live": False,
            },
            sort_keys=True,
        )
    )
    return 2 if record["classification"] == "INPUT_BLOCKED_CLAIM_CONSUMED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
