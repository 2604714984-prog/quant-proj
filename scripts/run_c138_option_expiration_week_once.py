"""One-use runner for frozen C138 SPY option-expiration-week research."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
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
from research.adapters.c138_option_expiration_week import (  # noqa: E402
    HOLDOUT_INTERVALS,
    INITIAL_CAPITAL,
    RESEARCH_ID,
    VALIDATION_INTERVALS,
    holdout_decision,
    validation_decision,
)


DEFINITION = ROOT / "research/definitions/c138_option_expiration_week_v1.json"
ADAPTER = ROOT / "research/adapters/c138_option_expiration_week.py"
RUNNER = Path(__file__).resolve()
DEFINITION_SHA256 = "17d03260418c5286265594fd8c0649f61380d27c759bfa4bd39a58aaba2ec202"
ADAPTER_SHA256 = "af7c871826b425f76b1c6b92e8ca6c8a80755c494f299728a8d0ddd61155037d"
INPUT_PACKET_SHA256 = "74cb3945fbf2871134f98e2d67c5dad8a110b07f596c2461f1575d2ee0953617"
RECEIPT_SHA256 = "4aae4d478ad9b5e8acbd9e857fc49dadeed42b5aecc7dd53041598e2ff3d48e6"
VALIDATION_BUNDLE_SHA256 = "1800618b8702c370f68f305f0562c643a0578e7e437dd2b4c3989f4eafb07e56"
HOLDOUT_BUNDLE_SHA256 = "20f4d49649dc0355e1b8b1ae1b3ca63bd400fc49a364045a9d4257c47f3562e1"
DATABASE_SHA256 = "f87722ecf19f9813bb161e365b0e5aa5069ef3d4a16471ad712abb131d7e9fdd"
CORE_SOURCE_FILE_COUNT = 23
CORE_SOURCE_SHA256 = "46ae2fe342a40034b9caacb6cc48a182947a49da9d874de31a1fdb60be0b9a80"
INCLUSION_RULE_SHA256 = "89483ee34a4b87fcdb728889dc31c7dc7222f85b3071ff7a97c65148e1b6402e"
INPUT_ROOT = Path(
    "/home/rongyu/workspace/quant-data/staging/"
    "c138_spy_option_expiration_week_premium_v1"
)
INPUT_PACKET = INPUT_ROOT / "full_input_packet.json"
INPUT_RECEIPT = INPUT_ROOT / "materialization_receipt.json"
VALIDATION_BUNDLE = INPUT_ROOT / "validation_runtime_bundle.json"
HOLDOUT_BUNDLE = INPUT_ROOT / "retrospective_holdout_runtime_bundle.json"
DATABASE = Path("/home/rongyu/workspace/quant-data/quant_research.duckdb")
PRIVATE_ROOT = Path("/home/rongyu/workspace/quant-data/private_results")
VALIDATION_CLAIM = PRIVATE_ROOT / f"{RESEARCH_ID.lower()}_validation/claim.json"
VALIDATION_RESULT = VALIDATION_CLAIM.with_name("result.json")
HOLDOUT_CLAIM = PRIVATE_ROOT / f"{RESEARCH_ID.lower()}_holdout/claim.json"
HOLDOUT_RESULT = HOLDOUT_CLAIM.with_name("result.json")
ONE_WAY_SLIPPAGE_BPS = 10.0


class InputBlockedError(ValueError):
    """Fail-closed identity, chronology, schema, or one-use error."""


@dataclass(frozen=True)
class Point:
    signal_session: date
    decision_at: datetime
    execution_session: date
    calendar: AcceptedSessionCalendar
    revision: AcceptedSessionCalendar | None
    execution: ExecutionInput
    snapshot: UniverseSnapshotIdentity
    strategy_target_symbol: str | None
    comparator_target_symbol: str | None


@dataclass(frozen=True)
class Bundle:
    stage: str
    points: tuple[Point, ...]
    daily_sessions: tuple[date, ...]
    actions: tuple[CorporateActionIdentity, ...]


def _hash_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _file_hash(path: Path) -> str:
    return _hash_bytes(path.read_bytes())


def _sha(value: object, field: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise InputBlockedError(f"{field} must be a lowercase SHA-256")
    return value


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
    return len(rows), _hash_bytes(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    )


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


def _capture(path: Path, expected_sha: str, *, max_bytes: int) -> bytes:
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
    payload = b"".join(chunks)
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


def _status(row: object) -> StatusEvidence:
    if type(row) is not dict:
        raise InputBlockedError("status evidence must be an object")
    if row["symbol"] != "SPY" or row["exchange_timezone"] != "America/New_York":
        raise InputBlockedError("status evidence must identify SPY")
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
    if type(row) is not dict:
        raise InputBlockedError("corporate action must be an object")
    if row["subject_id"] != "SPY" or row["exchange_timezone"] != "America/New_York":
        raise InputBlockedError("corporate action must identify SPY")

    def optional_date(key: str) -> date | None:
        return None if row[key] is None else _date(row[key], key)

    return CorporateActionIdentity(
        row["subject_id"],
        row["action_id"],
        row["action_type"],
        _datetime(row["effective_at"], "action effective_at"),
        _source(row["source"]),
        row["exchange_timezone"],
        ex_date=optional_date("ex_date"),
        record_date=optional_date("record_date"),
        pay_date=optional_date("pay_date"),
        split_ratio=None if row["split_ratio"] is None else Decimal(row["split_ratio"]),
        cash_amount=None if row["cash_amount"] is None else Decimal(row["cash_amount"]),
        currency=row["currency"],
        unit=row["unit"],
        new_subject_id=row["new_subject_id"],
    )


def _validate_packet_receipt(
    packet_payload: bytes, receipt_payload: bytes
) -> tuple[dict[str, Any], dict[str, Any]]:
    packet = _json(packet_payload, "C138 input packet")
    receipt = _json(receipt_payload, "C138 materialization receipt")
    if (
        packet.get("schema_version") != "c138-spy-option-expiration-week-input-v1"
        or packet.get("research_id") != RESEARCH_ID
        or packet.get("status") != "INPUT_MATERIALIZED_SUPPORT_PASS"
        or packet.get("source_selected_using_performance") is not False
        or packet.get("price_values_used_for_signal") is not False
        or packet.get("strategy_outcomes_opened") is not False
        or packet.get("database_write") is not False
        or packet.get("strategy_candidate_available") is not False
        or receipt.get("schema_version")
        != "c138-spy-option-expiration-week-receipt-v1"
        or receipt.get("research_id") != RESEARCH_ID
        or receipt.get("status") != "INPUT_MATERIALIZED_SUPPORT_PASS"
        or receipt.get("input_packet_sha256") != INPUT_PACKET_SHA256
        or receipt.get("database_sha256_before") != DATABASE_SHA256
        or receipt.get("database_sha256_after") != DATABASE_SHA256
        or receipt.get("database_wal_absent") is not True
        or receipt.get("database_write") is not False
        or receipt.get("strategy_outcomes_opened") is not False
        or receipt.get("strategy_candidate_available") is not False
    ):
        raise InputBlockedError("input packet and receipt boundary mismatch")
    expected_support = {
        "validation": {
            "complete_weekly_intervals": VALIDATION_INTERVALS,
            "first_boundary": "2021-01-04",
            "fourth_friday_comparator_intervals": 29,
            "overlap_intervals": 0,
            "terminal_boundary": "2023-05-30",
            "third_friday_strategy_intervals": 29,
        },
        "retrospective_holdout": {
            "complete_weekly_intervals": HOLDOUT_INTERVALS,
            "first_boundary": "2023-07-03",
            "fourth_friday_comparator_intervals": 35,
            "overlap_intervals": 0,
            "terminal_boundary": "2026-06-01",
            "third_friday_strategy_intervals": 35,
        },
    }
    if receipt.get("state_support") != expected_support:
        raise InputBlockedError("frozen state support mismatch")
    return packet, receipt


def _execution(
    row: object,
    statuses: tuple[StatusEvidence, ...],
    actions: tuple[CorporateActionIdentity, ...],
    *,
    signal_session: date,
    execution_session: date,
    decision_at: datetime,
    calendar: AcceptedSessionCalendar,
) -> ExecutionInput:
    if type(row) is not dict:
        raise InputBlockedError("execution input must be an object")
    expected_keys = {
        "corporate_action_ids",
        "currency",
        "decision_price",
        "decision_price_basis",
        "decision_price_effective_at",
        "decision_price_session",
        "decision_price_source",
        "decision_source_row_sha256",
        "execution_price_basis",
        "execution_price_effective_at",
        "market",
        "raw_open",
        "session_date",
        "source",
        "source_row_sha256",
        "symbol",
    }
    if type(row) is not dict or set(row) != expected_keys:
        raise InputBlockedError("execution input schema mismatch")
    if row["symbol"] != "SPY" or row["market"] != "us" or row["currency"] != "USD":
        raise InputBlockedError("only frozen US SPY execution is allowed")
    if row["corporate_action_ids"] != [action.action_id for action in actions]:
        raise InputBlockedError("execution corporate-action mapping mismatch")
    accepted_signal = calendar.session_on(signal_session, as_of=decision_at)
    accepted_execution = calendar.session_on(execution_session, as_of=decision_at)
    expected_basis = "raw_pre_action_per_old_share" if actions else "raw_execution_units"
    decision_source = _source(row["decision_price_source"])
    price = row["decision_price"]
    raw_open = row["raw_open"]
    if (
        row["decision_price_basis"] != expected_basis
        or row["execution_price_basis"] != "retrospective_daily_bar_open_fill"
        or _date(row["decision_price_session"], "decision price session")
        != signal_session
        or _date(row["session_date"], "execution session") != execution_session
        or _datetime(
            row["decision_price_effective_at"], "decision price effective_at"
        )
        != accepted_signal.close_at
        or _datetime(
            row["execution_price_effective_at"], "execution price effective_at"
        )
        != accepted_execution.open_at
        or decision_source.available_at > decision_at
        or any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or float(value) <= 0.0
            for value in (price, raw_open)
        )
    ):
        raise InputBlockedError("execution price or timing identity mismatch")
    _sha(row["source_row_sha256"], "source row SHA-256")
    _sha(row["decision_source_row_sha256"], "decision source row SHA-256")
    return ExecutionInput(
        "SPY",
        "us",
        float(raw_open),
        "USD",
        _source(row["source"]),
        statuses,
        corporate_actions=actions,
        decision_price=float(price),
        decision_price_source=decision_source,
        decision_price_basis=row["decision_price_basis"],
        execution_price_effective_at=accepted_execution.open_at,
        execution_price_basis=row["execution_price_basis"],
    )


def _snapshot(
    statuses: tuple[StatusEvidence, ...],
    *,
    calendar: AcceptedSessionCalendar,
    execution_session: date,
    decision_at: datetime,
) -> UniverseSnapshotIdentity:
    members = ("SPY",)
    accepted = calendar.session_on(execution_session, as_of=decision_at)
    lifecycle_hash = lifecycle_coverage_sha256(
        members,
        accepted,
        decision_at,
        {"SPY": statuses},
        market="us",
    )
    sources = tuple(status.source for status in statuses)
    source = SourceIdentity(
        "https://www.sec.gov/Archives/edgar/data/884394/",
        _hash_bytes(
            json.dumps(
                sorted(source.content_sha256 for source in sources),
                separators=(",", ":"),
            ).encode()
        ),
        max(source.available_at for source in sources),
        max(source.retrieved_at for source in sources),
        f"c138-spy-universe-{execution_session.isoformat()}",
    )
    return UniverseSnapshotIdentity(
        "us",
        calendar.identity.exchange_id,
        execution_session,
        1,
        ordered_members_sha256(members),
        lifecycle_hash,
        INCLUSION_RULE_SHA256,
        calendar_identity_sha256(calendar.identity),
        source,
    )


def _load_bundle(
    bundle_payload: bytes,
    packet: dict[str, Any],
    receipt: dict[str, Any],
    *,
    stage: str,
) -> Bundle:
    record = _json(bundle_payload, "C138 runtime bundle")
    packet_stage = "retrospective_holdout" if stage == "holdout" else stage
    expected_intervals = (
        VALIDATION_INTERVALS if stage == "validation" else HOLDOUT_INTERVALS
    )
    expected_bundle_sha = (
        VALIDATION_BUNDLE_SHA256 if stage == "validation" else HOLDOUT_BUNDLE_SHA256
    )
    if (
        record.get("schema_version")
        != "c138-spy-option-expiration-week-runtime-v1"
        or record.get("research_id") != RESEARCH_ID
        or record.get("stage") != packet_stage
        or record.get("symbol") != "SPY"
        or record.get("strategy_outcomes_opened") is not False
        or record.get("database_write") is not False
        or packet.get("stages", {})
        .get(packet_stage, {})
        .get("runtime_bundle_sha256")
        != expected_bundle_sha
        or receipt.get("runtime_bundle_sha256", {}).get(packet_stage)
        != expected_bundle_sha
    ):
        raise InputBlockedError("runtime bundle identity mismatch")
    reconstruction = _calendar(record["reconstruction_calendar"])
    epoch_rows = record.get("calendar_epochs")
    if type(epoch_rows) is not dict or not epoch_rows:
        raise InputBlockedError("calendar epochs are required")
    epochs = {key: _calendar(value) for key, value in epoch_rows.items()}
    actions = tuple(_action(value) for value in record["corporate_actions"])
    if len({action.action_id for action in actions}) != len(actions):
        raise InputBlockedError("corporate action identities must be unique")
    raw_points = record.get("execution_points")
    if type(raw_points) is not list or len(raw_points) != expected_intervals + 1:
        raise InputBlockedError("weekly execution point count mismatch")
    points: list[Point] = []
    for index, raw in enumerate(raw_points):
        if type(raw) is not dict:
            raise InputBlockedError("execution point must be an object")
        execution_session = _date(raw["execution_session"], "execution session")
        signal_session = _date(raw["signal_session"], "signal session")
        decision_at = _datetime(raw["decision_at"], "decision_at")
        terminal = index == len(raw_points) - 1
        ordinal = raw["calendar_friday_ordinal"]
        expected_strategy = None if terminal or ordinal != 3 else "SPY"
        expected_comparator = None if terminal or ordinal != 4 else "SPY"
        if (
            type(ordinal) is not int
            or not 1 <= ordinal <= 5
            or raw["strategy_target_symbol"] != expected_strategy
            or raw["comparator_target_symbol"] != expected_comparator
            or raw["terminal_exit"] is not terminal
            or _date(raw["calendar_week_start"], "calendar week start").weekday()
            != 0
            or _date(raw["calendar_week_end"], "calendar week end").weekday()
            != 6
            or decision_at.astimezone(calendar_timezone()).date()
            != execution_session
            or (
                decision_at.astimezone(calendar_timezone()).hour,
                decision_at.astimezone(calendar_timezone()).minute,
            )
            != (9, 0)
        ):
            raise InputBlockedError("weekly target or chronology mismatch")
        try:
            calendar = epochs[raw["decision_calendar_epoch_id"]]
            revision_id = raw["execution_calendar_revision_id"]
            revision = None if revision_id is None else epochs[revision_id]
        except KeyError as exc:
            raise InputBlockedError("unknown calendar epoch") from exc
        if (
            calendar.next_session(signal_session, as_of=decision_at).session_date
            != execution_session
        ):
            raise InputBlockedError("execution is not the next accepted session")
        statuses = tuple(_status(value) for value in raw["status_evidence"])
        point_actions = tuple(
            action for action in actions if action.effective_date == execution_session
        )
        execution = _execution(
            raw["execution"],
            statuses,
            point_actions,
            signal_session=signal_session,
            execution_session=execution_session,
            decision_at=decision_at,
            calendar=calendar,
        )
        snapshot = _snapshot(
            statuses,
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
                revision,
                execution,
                snapshot,
                expected_strategy,
                expected_comparator,
            )
        )
    if any(
        left.execution_session >= right.execution_session
        for left, right in zip(points, points[1:], strict=False)
    ):
        raise InputBlockedError("weekly execution sessions must increase")
    raw_daily = record.get("daily_sessions")
    if type(raw_daily) is not list:
        raise InputBlockedError("daily sessions must be a list")
    start, end = points[0].execution_session, points[-1].execution_session
    daily = tuple(_date(value, "daily session") for value in raw_daily)
    expected_daily = tuple(
        day for day in reconstruction.session_dates if start <= day <= end
    )
    if daily != expected_daily:
        raise InputBlockedError("daily session coverage is incomplete")
    return Bundle(packet_stage, tuple(points), daily, actions)


def calendar_timezone():
    from zoneinfo import ZoneInfo

    return ZoneInfo("America/New_York")


def _apply_actions(
    portfolio: Portfolio,
    session_date: date,
    actions: tuple[CorporateActionIdentity, ...],
) -> None:
    portfolio.start_session(session_date)
    for action in actions:
        if action.effective_date != session_date:
            continue
        if action.action_type in {"cash_dividend", "special_dividend"}:
            if action.cash_amount is None or action.ex_date is None or action.pay_date is None:
                raise InputBlockedError("cash action identity is incomplete")
            portfolio.apply_cash_distribution(
                action.subject_id,
                event_id=action.action_id,
                amount_per_share=float(action.cash_amount),
                ex_date=action.ex_date,
                pay_date=action.pay_date,
            )
        elif action.action_type in {"split", "reverse_split"}:
            if action.split_ratio is None:
                raise InputBlockedError("split action identity is incomplete")
            portfolio.apply_split(
                action.subject_id,
                float(action.split_ratio),
                event_id=action.action_id,
            )
        else:
            raise InputBlockedError("unsupported SPY corporate action")


def _rebalance(
    portfolio: Portfolio,
    point: Point,
    target_symbol: str | None,
    prior_stage_hash: str,
):
    weights = {} if target_symbol is None else {"SPY": 1.0}
    return run_static_rebalance(
        portfolio,
        point.calendar,
        signal_session=point.signal_session,
        decision_at=point.decision_at,
        execution_inputs=(point.execution,),
        execution_calendar_revision=point.revision,
        universe_members=("SPY",),
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
    strategy_stage = "0" * 64
    comparator_stage = "0" * 64
    stage_hashes: list[str] = []
    for session_date in bundle.daily_sessions:
        point = point_by_date.get(session_date)
        daily_actions = actions_by_date[session_date]
        if point is None:
            _apply_actions(strategy, session_date, daily_actions)
            _apply_actions(comparator, session_date, daily_actions)
            continue
        strategy_result = _rebalance(
            strategy,
            point,
            point.strategy_target_symbol,
            strategy_stage,
        )
        comparator_result = _rebalance(
            comparator,
            point,
            point.comparator_target_symbol,
            comparator_stage,
        )
        strategy, strategy_stage = (
            strategy_result.portfolio,
            strategy_result.stage_hash,
        )
        comparator, comparator_stage = (
            comparator_result.portfolio,
            comparator_result.stage_hash,
        )
        stage_hashes.extend((strategy_stage, comparator_stage))
        if point is bundle.points[0]:
            continue
        strategy_navs.append(strategy_result.final_nav)
        comparator_navs.append(comparator_result.final_nav)
    expected = (
        VALIDATION_INTERVALS
        if bundle.stage == "validation"
        else HOLDOUT_INTERVALS
    ) + 1
    if len(strategy_navs) != expected or len(comparator_navs) != expected:
        raise InputBlockedError("weekly NAV path is incomplete")
    return (
        _adjacent_returns(strategy_navs),
        _adjacent_returns(comparator_navs),
        tuple(stage_hashes),
    )


def _adjacent_returns(navs: list[float]) -> tuple[float, ...]:
    if type(navs) is not list or len(navs) < 2:
        raise InputBlockedError("NAV path must contain at least two points")
    normalized: list[float] = []
    for value in navs:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or float(value) <= 0.0
        ):
            raise InputBlockedError("NAV values must be finite and positive")
        normalized.append(float(value))
    return tuple(
        right / left - 1.0
        for left, right in zip(normalized, normalized[1:], strict=False)
    )


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
        "comparator_fourth_friday_week": asdict(decision.comparator),
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
    payload = json.dumps(
        record, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
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


def _accepted_validation_result() -> str:
    if not VALIDATION_CLAIM.exists() or not VALIDATION_RESULT.exists():
        raise InputBlockedError("holdout requires a completed validation")
    result_payload = _capture(
        VALIDATION_RESULT,
        _file_hash(VALIDATION_RESULT),
        max_bytes=256 * 1024,
    )
    result = _json(result_payload, "validation result")
    if (
        result.get("research_id") != RESEARCH_ID
        or result.get("stage") != "validation"
        or result.get("classification")
        != "RETROSPECTIVE_SECONDARY_VALIDATION_PASS"
        or result.get("decision", {}).get("all_gates_pass") is not True
        or result.get("rerun_authorized") is not False
    ):
        raise InputBlockedError("validation result does not authorize holdout")
    return _hash_bytes(result_payload)


def _claim(
    stage: str,
    runner_sha: str,
    bundle_sha: str,
    validation_result_sha: str | None,
) -> dict[str, Any]:
    return {
        "schema_version": "c138-option-expiration-week-claim-v1",
        "research_id": RESEARCH_ID,
        "stage": stage,
        "claimed_at": datetime.now(timezone.utc).isoformat(),
        "definition_sha256": DEFINITION_SHA256,
        "adapter_sha256": ADAPTER_SHA256,
        "runner_sha256": runner_sha,
        "input_packet_sha256": INPUT_PACKET_SHA256,
        "materialization_receipt_sha256": RECEIPT_SHA256,
        "expected_runtime_bundle_sha256": bundle_sha,
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
    bundle_sha: str | None,
    decision: dict[str, Any] | None,
    stage_hashes: tuple[str, ...] = (),
    error: Exception | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "c138-option-expiration-week-result-v1",
        "research_id": RESEARCH_ID,
        "stage": stage,
        "classification": classification,
        "claim_sha256": claim_sha,
        "definition_sha256": DEFINITION_SHA256,
        "adapter_sha256": ADAPTER_SHA256,
        "runner_sha256": runner_sha,
        "input_packet_sha256": INPUT_PACKET_SHA256,
        "materialization_receipt_sha256": RECEIPT_SHA256,
        "runtime_bundle_sha256": bundle_sha,
        "decision": decision,
        "stage_hashes": list(stage_hashes),
        "error_type": None if error is None else type(error).__name__,
        "error_message": None if error is None else str(error),
        "database_sha256": _file_hash(DATABASE),
        "database_write": False,
        "strategy_candidate_available": False,
        "rerun_authorized": False,
        "shadow": False,
        "paper": False,
        "broker": False,
        "live": False,
    }


def run(stage: str) -> tuple[Path, str, dict[str, Any]]:
    if stage not in {"validation", "holdout"}:
        raise InputBlockedError("stage must be validation or holdout")
    if _file_hash(DATABASE) != DATABASE_SHA256 or Path(f"{DATABASE}.wal").exists():
        raise InputBlockedError("central database identity changed or WAL exists")
    if _file_hash(DEFINITION) != DEFINITION_SHA256:
        raise InputBlockedError("definition SHA-256 mismatch")
    if _file_hash(ADAPTER) != ADAPTER_SHA256:
        raise InputBlockedError("adapter SHA-256 mismatch")
    if _core_identity() != (CORE_SOURCE_FILE_COUNT, CORE_SOURCE_SHA256):
        raise InputBlockedError("shared-core identity mismatch")
    runner_sha = _file_hash(RUNNER)
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
            raise InputBlockedError("C138 validation one-use state is not pristine")
        bundle_path, expected_bundle = (
            VALIDATION_BUNDLE,
            VALIDATION_BUNDLE_SHA256,
        )
        claim_path, result_path = VALIDATION_CLAIM, VALIDATION_RESULT
        validation_result_sha = None
    else:
        if HOLDOUT_CLAIM.exists() or HOLDOUT_RESULT.exists():
            raise InputBlockedError("C138 holdout one-use state is not pristine")
        validation_result_sha = _accepted_validation_result()
        bundle_path, expected_bundle = HOLDOUT_BUNDLE, HOLDOUT_BUNDLE_SHA256
        claim_path, result_path = HOLDOUT_CLAIM, HOLDOUT_RESULT
    claim_sha = _publish(
        claim_path,
        _claim(stage, runner_sha, expected_bundle, validation_result_sha),
    )
    observed_bundle_sha: str | None = None
    try:
        packet_payload = _capture(
            INPUT_PACKET, INPUT_PACKET_SHA256, max_bytes=2 * 1024 * 1024
        )
        receipt_payload = _capture(
            INPUT_RECEIPT, RECEIPT_SHA256, max_bytes=256 * 1024
        )
        packet, receipt = _validate_packet_receipt(packet_payload, receipt_payload)
        bundle_payload = _capture(
            bundle_path, expected_bundle, max_bytes=128 * 1024 * 1024
        )
        observed_bundle_sha = _hash_bytes(bundle_payload)
        bundle = _load_bundle(
            bundle_payload, packet, receipt, stage=stage
        )
        strategy, comparator, stage_hashes = _simulate(bundle)
        decision = _decision(stage, strategy, comparator)
        classification = (
            "RETROSPECTIVE_SECONDARY_VALIDATION_PASS"
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
            bundle_sha=observed_bundle_sha,
            decision=decision,
            stage_hashes=stage_hashes,
        )
    except Exception as exc:
        record = _result(
            stage,
            "INPUT_BLOCKED_CLAIM_CONSUMED",
            claim_sha=claim_sha,
            runner_sha=runner_sha,
            bundle_sha=observed_bundle_sha,
            decision=None,
            error=exc,
        )
    result_sha = _publish(result_path, record)
    if _file_hash(DATABASE) != DATABASE_SHA256 or Path(f"{DATABASE}.wal").exists():
        raise InputBlockedError("central database changed during execution")
    return result_path, result_sha, record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("validation", "holdout"), required=True)
    args = parser.parse_args()
    result_path, result_sha, record = run(args.stage)
    print(
        json.dumps(
            {
                "classification": record["classification"],
                "result_path": str(result_path),
                "result_sha256": result_sha,
                "gate_pass_count": (
                    None
                    if record["decision"] is None
                    else sum(record["decision"]["gates"].values())
                ),
                "gate_total_count": (
                    None
                    if record["decision"] is None
                    else len(record["decision"]["gates"])
                ),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
