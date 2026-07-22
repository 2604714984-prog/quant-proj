"""One-use retrospective runner for the frozen Cycle 7 SPY VRP strategy."""

# ruff: noqa: E402

from __future__ import annotations

import hashlib
import json
import math
import os
import stat
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "src", ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from quant_system.backtest import ExecutionInput, Portfolio, run_static_rebalance
from quant_system.data import (
    AcceptedSession,
    AcceptedSessionCalendar,
    CalendarIdentity,
    CorporateActionIdentity,
    SourceIdentity,
)
from quant_system.markets.universe import (
    StatusEvidence,
    UniverseSnapshotIdentity,
    validate_universe_snapshot,
)
from research.adapters.c7_spy_variance_risk_premium import (
    HOLDOUT_INTERVALS,
    INITIAL_CAPITAL,
    PROGRAM_ALPHA,
    RESEARCH_ID,
    VALIDATION_INTERVALS,
    holdout_decision,
    validation_decision,
)

DEFINITION = ROOT / "research/definitions/c7_spy_variance_risk_premium_v1.json"
ADAPTER = ROOT / "research/adapters/c7_spy_variance_risk_premium.py"
RUNNER = Path(__file__).resolve()
DEFINITION_SHA256 = "c08464b342f53e679f6d3f59a856a830e7728b6aa536060c5a72cf414af40da3"
ADAPTER_SHA256 = "1248feb8a33e0f045a0fa8363dfff1e377b1dbb2f64a876c916e66b31701ab4e"
PARENT_PREREGISTRATION_SHA256 = (
    "5d49f6be8e3ceb331357650f1b6b34d10b6fc604b571c6bd546a953752f025bf"
)
SIGNAL_INPUT_SHA256 = (
    "12ff1ceed8432670e4327cd0dc115a4bb5a021b43216bf528bd28d195456eaff"
)
SUPPORT_RECEIPT_SHA256 = (
    "2faa47dd5e705d87711bc99488a3a55458a5b96121f8148fd291d4ec1778ddac"
)
WEEKLY_VIX_INPUT_SHA256 = (
    "3a221b43b625634f456a4e29a010b7eb8746508933aaeba1b29e3540911a4491"
)
CALENDAR_INPUT_SHA256 = (
    "08b1722c675012d89e0b4f92ed51f51160adbd1d54961c093c52101c067fc553"
)
VALIDATION_BUNDLE_SHA256 = (
    "51c402ef95ab93a235dd38c862be517f9f0ed06fa47c3bb91becc33e914aa2d6"
)
HOLDOUT_BUNDLE_SHA256 = (
    "120eeeacd724af31125c7209985621d90d1edd1c95cfe068098fc3bf903a8db1"
)
CORE_SOURCE_FILE_COUNT = 23
CORE_SOURCE_SHA256 = (
    "46ae2fe342a40034b9caacb6cc48a182947a49da9d874de31a1fdb60be0b9a80"
)
INCLUSION_RULE_SHA256 = (
    "89483ee34a4b87fcdb728889dc31c7dc7222f85b3071ff7a97c65148e1b6402e"
)
C6_RESEARCH_ID = "C6_VIX_WEEKLY_CHANGE_IMPULSE_SPY_CASH_V1"

STAGING_ROOT = Path(
    "/home/rongyu/workspace/quant-data/staging/c7_spy_variance_risk_premium_v1"
)
SIGNAL_INPUT = STAGING_ROOT / "signal_input.json"
SUPPORT_RECEIPT = STAGING_ROOT / "receipt.json"
C6_ROOT = Path(
    "/home/rongyu/workspace/quant-data/staging/"
    "c6_vix_weekly_change_impulse_spy_cash_v1"
)
VALIDATION_BUNDLE = C6_ROOT / "spy_validation_runtime_bundle.json"
HOLDOUT_BUNDLE = C6_ROOT / "spy_holdout_runtime_bundle.json"
PRIVATE_ROOT = Path("/home/rongyu/workspace/quant-data/private_results")
VALIDATION_CLAIM = PRIVATE_ROOT / "c7_spy_variance_risk_premium_v1_validation/claim.json"
VALIDATION_RESULT = VALIDATION_CLAIM.with_name("result.json")
HOLDOUT_CLAIM = PRIVATE_ROOT / "c7_spy_variance_risk_premium_v1_holdout/claim.json"
HOLDOUT_RESULT = HOLDOUT_CLAIM.with_name("result.json")
ONE_WAY_SLIPPAGE_BPS = 10.0

_SOURCE_FIELDS = {
    "source_url",
    "content_sha256",
    "available_at",
    "retrieved_at",
    "revision_id",
    "supersedes_revision_id",
}
_SESSION_FIELDS = {
    "session_date",
    "open_at",
    "close_at",
    "is_early_close",
    "exchange_id",
    "exchange_timezone",
    "row_sha256",
    "source",
}
_CALENDAR_IDENTITY_FIELDS = {
    "exchange_id",
    "exchange_timezone",
    "coverage_start",
    "coverage_end",
    "session_count",
    "session_dates_sha256",
    "session_rows_sha256",
    "source_identity",
}
_STATUS_FIELDS = {
    "status_id",
    "symbol",
    "kind",
    "value",
    "effective_from",
    "effective_to",
    "exchange_timezone",
    "source",
}
_SNAPSHOT_FIELDS = {
    "market",
    "exchange_id",
    "effective_session",
    "member_count",
    "ordered_members_sha256",
    "lifecycle_coverage_sha256",
    "inclusion_rule_sha256",
    "calendar_identity_sha256",
    "source_identity",
}
_ACTION_FIELDS = {
    "subject_id",
    "action_id",
    "action_type",
    "effective_at",
    "source",
    "exchange_timezone",
    "ex_date",
    "record_date",
    "pay_date",
    "split_ratio",
    "cash_amount",
    "currency",
    "unit",
    "new_subject_id",
}
_EXECUTION_FIELDS = {
    "symbol",
    "market",
    "session_date",
    "raw_open",
    "currency",
    "source",
    "decision_price",
    "decision_price_session",
    "decision_price_effective_at",
    "decision_price_source",
    "decision_price_basis",
    "execution_price_effective_at",
    "execution_price_basis",
    "corporate_action_ids",
}
_POINT_FIELDS = {
    "signal_session",
    "decision_at",
    "execution_session",
    "decision_calendar_epoch_id",
    "execution_calendar_revision_id",
    "terminal_exit",
    "state_row_sha256",
    "status_evidence",
    "universe_snapshot",
    "execution",
}
_BUNDLE_FIELDS = {
    "schema_version",
    "research_id",
    "stage",
    "symbol",
    "state_input_sha256",
    "calendar_input_sha256",
    "reconstruction_calendar",
    "calendar_epochs",
    "execution_points",
    "daily_sessions",
    "corporate_actions",
}
_SIGNAL_ROW_FIELDS = {
    "decision_at",
    "distribution_action_ids",
    "execution_session",
    "realized_variance_hex",
    "row_sha256",
    "signal_session",
    "split_membership",
    "target_weight",
    "variance_risk_premium_hex",
    "vix_row_sha256",
    "vix_variance_hex",
    "weekly_source_point_sha256",
}


class InputBlockedError(ValueError):
    """Fail-closed identity, schema, chronology, or one-use error."""


@dataclass(frozen=True)
class SignalBoundary:
    signal_session: date
    decision_at: datetime
    execution_session: date
    split: str
    target_weight: float
    row_sha256: str
    vix_row_sha256: str


@dataclass(frozen=True)
class Point:
    signal: SignalBoundary
    calendar: AcceptedSessionCalendar
    execution_calendar_revision: AcceptedSessionCalendar | None
    execution_input: ExecutionInput
    universe_snapshot: UniverseSnapshotIdentity
    terminal_exit: bool


@dataclass(frozen=True)
class Bundle:
    stage: str
    points: tuple[Point, ...]
    daily_sessions: tuple[date, ...]
    actions: tuple[CorporateActionIdentity, ...]


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256(value: object, field: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise InputBlockedError(f"{field} must be a lowercase SHA-256")
    return value


def _runtime_sha(value: str, field: str) -> str:
    if value.startswith("__PATCH_C7_"):
        raise InputBlockedError(f"{field} is not patched")
    return _sha256(value, field)


def _file_sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _core_identity() -> tuple[int, str]:
    rows: list[dict[str, str]] = []
    for path in sorted((ROOT / "src/quant_system").rglob("*.py")):
        if path.is_symlink() or not path.is_file():
            raise InputBlockedError("shared core must contain regular Python files")
        rows.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": _file_sha256(path),
            }
        )
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    return len(rows), _sha256_bytes(payload)


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


def _capture(
    path: Path,
    expected_sha256: str,
    *,
    max_bytes: int,
    private: bool = True,
) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise InputBlockedError(f"cannot open protected input: {path}") from exc
    try:
        before = os.fstat(fd)
        mode = stat.S_IMODE(before.st_mode)
        if not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid():
            raise InputBlockedError("input must be an owner-controlled regular file")
        if (private and mode & ~0o600) or (not private and mode & 0o022):
            raise InputBlockedError("input mode is outside the frozen bound")
        if not 0 < before.st_size <= max_bytes:
            raise InputBlockedError("input size is outside the frozen bound")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(fd, min(1024 * 1024, max_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                raise InputBlockedError("input exceeds the frozen size bound")
        after = os.fstat(fd)
    finally:
        os.close(fd)
    try:
        current = os.stat(path, follow_symlinks=False)
    except OSError as exc:
        raise InputBlockedError("input path changed during capture") from exc
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(
        getattr(before, field) != getattr(after, field)
        or getattr(after, field) != getattr(current, field)
        for field in fields
    ):
        raise InputBlockedError("input changed during descriptor-bound capture")
    payload = b"".join(chunks)
    if _sha256_bytes(payload) != _sha256(expected_sha256, "expected SHA-256"):
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


def _decimal(value: object, field: str) -> Decimal:
    if isinstance(value, bool):
        raise InputBlockedError(f"{field} must be finite")
    try:
        number = Decimal(str(value))
    except Exception as exc:
        raise InputBlockedError(f"{field} must be finite") from exc
    if not number.is_finite():
        raise InputBlockedError(f"{field} must be finite")
    return number


def _keys(row: object, expected: set[str], field: str) -> dict[str, Any]:
    if type(row) is not dict or set(row) != expected:
        raise InputBlockedError(f"{field} schema mismatch")
    return row


def _source(row: object) -> SourceIdentity:
    item = _keys(row, _SOURCE_FIELDS, "source identity")
    return SourceIdentity(
        item["source_url"],
        item["content_sha256"],
        _datetime(item["available_at"], "source available_at"),
        _datetime(item["retrieved_at"], "source retrieved_at"),
        item["revision_id"],
        item["supersedes_revision_id"],
    )


def _calendar(row: object) -> AcceptedSessionCalendar:
    item = _keys(row, {"calendar_identity", "session_rows"}, "calendar")
    if type(item["session_rows"]) is not list:
        raise InputBlockedError("calendar session_rows must be a list")
    sessions = tuple(
        AcceptedSession(
            _date(session["session_date"], "session_date"),
            _datetime(session["open_at"], "open_at"),
            _datetime(session["close_at"], "close_at"),
            _source(session["source"]),
            session["exchange_timezone"],
            session["is_early_close"],
            session["exchange_id"],
        )
        for raw in item["session_rows"]
        for session in (_keys(raw, _SESSION_FIELDS, "calendar session"),)
    )
    identity = _keys(
        item["calendar_identity"],
        _CALENDAR_IDENTITY_FIELDS,
        "calendar identity",
    )
    if (
        identity["exchange_id"] != "XNYS"
        or identity["exchange_timezone"] != "America/New_York"
        or any(
            session.exchange_id != "XNYS"
            or session.exchange_timezone != "America/New_York"
            for session in sessions
        )
    ):
        raise InputBlockedError("runtime calendars must be XNYS America/New_York")
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
    return AcceptedSessionCalendar(sessions, identity=frozen)


def _calendar_epochs(rows: object) -> dict[str, AcceptedSessionCalendar]:
    if type(rows) is not dict or not rows:
        raise InputBlockedError("calendar epochs are required")
    digests = [
        _sha256_bytes(
            json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        )
        for value in rows.values()
    ]
    if len(set(digests)) != len(digests):
        raise InputBlockedError("calendar epoch identities must not duplicate bytes")
    return {key: _calendar(value) for key, value in rows.items()}


def _status(row: object) -> StatusEvidence:
    item = _keys(row, _STATUS_FIELDS, "status evidence")
    if item["symbol"] != "SPY" or item["exchange_timezone"] != "America/New_York":
        raise InputBlockedError("status evidence must identify SPY")
    ending = (
        None
        if item["effective_to"] is None
        else _date(item["effective_to"], "effective_to")
    )
    return StatusEvidence(
        item["status_id"],
        item["symbol"],
        item["kind"],
        item["value"],
        _date(item["effective_from"], "effective_from"),
        ending,
        item["exchange_timezone"],
        _source(item["source"]),
    )


def _snapshot(row: object) -> UniverseSnapshotIdentity:
    item = _keys(row, _SNAPSHOT_FIELDS, "universe snapshot")
    snapshot = UniverseSnapshotIdentity(
        item["market"],
        item["exchange_id"],
        _date(item["effective_session"], "effective_session"),
        item["member_count"],
        item["ordered_members_sha256"],
        item["lifecycle_coverage_sha256"],
        item["inclusion_rule_sha256"],
        item["calendar_identity_sha256"],
        _source(item["source_identity"]),
    )
    if (
        snapshot.market != "us"
        or snapshot.exchange_id != "XNYS"
        or snapshot.inclusion_rule_sha256 != INCLUSION_RULE_SHA256
    ):
        raise InputBlockedError("universe snapshot identity mismatch")
    return snapshot


def _action(row: object) -> CorporateActionIdentity:
    item = _keys(row, _ACTION_FIELDS, "corporate action")
    if item["subject_id"] != "SPY" or item["exchange_timezone"] != "America/New_York":
        raise InputBlockedError("corporate action must identify SPY")

    def optional_date(key: str) -> date | None:
        return None if item[key] is None else _date(item[key], key)

    return CorporateActionIdentity(
        item["subject_id"],
        item["action_id"],
        item["action_type"],
        _datetime(item["effective_at"], "action effective_at"),
        _source(item["source"]),
        item["exchange_timezone"],
        ex_date=optional_date("ex_date"),
        record_date=optional_date("record_date"),
        pay_date=optional_date("pay_date"),
        split_ratio=(
            None
            if item["split_ratio"] is None
            else _decimal(item["split_ratio"], "split_ratio")
        ),
        cash_amount=(
            None
            if item["cash_amount"] is None
            else _decimal(item["cash_amount"], "cash_amount")
        ),
        currency=item["currency"],
        unit=item["unit"],
        new_subject_id=item["new_subject_id"],
    )


def _signal_rows(payload: bytes, definition: dict[str, Any]) -> dict[str, tuple[SignalBoundary, ...]]:
    record = _json(payload, "signal input")
    expected_top = {
        "definition_sha256",
        "research_id",
        "schema_version",
        "selected_monthly_rows",
        "signal_formula",
        "source_identities",
        "support",
        "support_status",
    }
    _keys(record, expected_top, "signal input")
    if (
        record["schema_version"] != "c7-spy-variance-risk-premium-signal-input-v1"
        or record["research_id"] != RESEARCH_ID
        or record["definition_sha256"] != PARENT_PREREGISTRATION_SHA256
        or record["signal_formula"] != definition["signal"]
        or record["support_status"] != "PASS_STATE_SUPPORT"
    ):
        raise InputBlockedError("signal input frozen identity mismatch")
    if record["source_identities"] != {
        "holdout_spy_bundle_sha256": HOLDOUT_BUNDLE_SHA256,
        "validation_spy_bundle_sha256": VALIDATION_BUNDLE_SHA256,
        "weekly_vix_input_sha256": WEEKLY_VIX_INPUT_SHA256,
    }:
        raise InputBlockedError("signal source identities mismatch")
    expected_support = definition["runtime_materialization"]["accepted_support"]
    if record["support"] != expected_support:
        raise InputBlockedError("signal support differs from accepted definition")
    raw_rows = record["selected_monthly_rows"]
    if type(raw_rows) is not list or len(raw_rows) != 66:
        raise InputBlockedError("signal input requires exactly 66 boundaries")
    parsed: list[SignalBoundary] = []
    for raw in raw_rows:
        item = _keys(raw, _SIGNAL_ROW_FIELDS, "signal row")
        split = item["split_membership"]
        if split not in {"validation", "holdout"}:
            raise InputBlockedError("signal split is invalid")
        signal_session = _date(item["signal_session"], "signal_session")
        execution_session = _date(item["execution_session"], "execution_session")
        decision_at = _datetime(item["decision_at"], "decision_at")
        local = decision_at.astimezone(ZoneInfo("America/New_York"))
        target = item["target_weight"]
        if (
            target not in {0.0, 1.0}
            or not signal_session < execution_session
            or local.date() != execution_session
            or local.time().isoformat() != "09:00:00"
        ):
            raise InputBlockedError("signal timing or target mapping mismatch")
        try:
            premium = float.fromhex(item["variance_risk_premium_hex"])
            vix_variance = float.fromhex(item["vix_variance_hex"])
            realized_variance = float.fromhex(item["realized_variance_hex"])
        except (TypeError, ValueError) as exc:
            raise InputBlockedError("signal variances must use finite hex floats") from exc
        if (
            not all(math.isfinite(value) for value in (premium, vix_variance, realized_variance))
            or vix_variance < 0.0
            or realized_variance < 0.0
            or premium != vix_variance - realized_variance
            or target != (1.0 if premium > 0.0 else 0.0)
        ):
            raise InputBlockedError("signal variance arithmetic mismatch")
        if (
            type(item["weekly_source_point_sha256"]) is not list
            or len(item["weekly_source_point_sha256"]) != 5
        ):
            raise InputBlockedError("signal requires five weekly source identities")
        for digest in item["weekly_source_point_sha256"]:
            _sha256(digest, "weekly source point SHA-256")
        if type(item["distribution_action_ids"]) is not list:
            raise InputBlockedError("distribution_action_ids must be a list")
        parsed.append(
            SignalBoundary(
                signal_session,
                decision_at,
                execution_session,
                split,
                float(target),
                _sha256(item["row_sha256"], "signal row SHA-256"),
                _sha256(item["vix_row_sha256"], "VIX row SHA-256"),
            )
        )
    if len({row.row_sha256 for row in parsed}) != len(parsed):
        raise InputBlockedError("signal row identities must be unique")
    groups = {
        stage: tuple(row for row in parsed if row.split == stage)
        for stage in ("validation", "holdout")
    }
    if {stage: len(rows) for stage, rows in groups.items()} != {
        "validation": VALIDATION_INTERVALS + 1,
        "holdout": HOLDOUT_INTERVALS + 1,
    }:
        raise InputBlockedError("signal split boundary counts mismatch")
    for rows in groups.values():
        dates = tuple(row.execution_session for row in rows)
        if dates != tuple(sorted(dates)) or len(dates) != len(set(dates)):
            raise InputBlockedError("signal boundaries are reordered or duplicated")
        months = tuple(
            row.signal_session.year * 12 + row.signal_session.month for row in rows
        )
        if any(right - left != 1 for left, right in zip(months, months[1:])):
            raise InputBlockedError("signal rows must use consecutive calendar months")
    for stage, rows in groups.items():
        interval_states = tuple(row.target_weight for row in rows[:-1])
        observed_support = {
            "boundaries": len(rows),
            "complete_intervals": len(interval_states),
            "spy_state_intervals": sum(value == 1.0 for value in interval_states),
            "cash_state_intervals": sum(value == 0.0 for value in interval_states),
            "spy_to_cash": sum(
                left == 1.0 and right == 0.0
                for left, right in zip(interval_states, interval_states[1:])
            ),
            "cash_to_spy": sum(
                left == 0.0 and right == 1.0
                for left, right in zip(interval_states, interval_states[1:])
            ),
        }
        if observed_support != expected_support[stage]:
            raise InputBlockedError("signal rows do not reproduce accepted support")
    return groups


def _support_receipt(payload: bytes, definition: dict[str, Any]) -> None:
    record = _json(payload, "support receipt")
    if (
        record.get("schema_version")
        != "c7-spy-variance-risk-premium-state-support-receipt-v1"
        or record.get("research_id") != RESEARCH_ID
        or record.get("definition_sha256") != PARENT_PREREGISTRATION_SHA256
        or record.get("signal_input_sha256") != SIGNAL_INPUT_SHA256
        or record.get("support")
        != definition["runtime_materialization"]["accepted_support"]
        or record.get("status") != "PASS_STATE_SUPPORT"
        or record.get("strategy_outcome_access") is not False
        or record.get("validation_run") is not False
        or record.get("holdout_opened") is not False
        or record.get("database_write") is not False
    ):
        raise InputBlockedError("support receipt contract mismatch")


def _execution(
    row: object,
    statuses: tuple[StatusEvidence, ...],
    actions: tuple[CorporateActionIdentity, ...],
    *,
    signal: SignalBoundary,
    calendar: AcceptedSessionCalendar,
) -> ExecutionInput:
    item = _keys(row, _EXECUTION_FIELDS, "execution input")
    if item["symbol"] != "SPY" or item["market"] != "us" or item["currency"] != "USD":
        raise InputBlockedError("only frozen US SPY execution is allowed")
    if item["corporate_action_ids"] != [action.action_id for action in actions]:
        raise InputBlockedError("execution corporate-action mapping mismatch")
    ordinary = {"cash_dividend", "special_dividend", "split", "reverse_split"}
    if any(action.action_type not in ordinary for action in actions):
        raise InputBlockedError("unsupported execution-day corporate action")
    expected_basis = "raw_pre_action_per_old_share" if actions else "raw_execution_units"
    accepted_signal = calendar.session_on(signal.signal_session, as_of=signal.decision_at)
    accepted_execution = calendar.session_on(
        signal.execution_session,
        as_of=signal.decision_at,
    )
    decision_source = _source(item["decision_price_source"])
    price = item["decision_price"]
    raw_open = item["raw_open"]
    valid_prices = (
        not isinstance(price, bool)
        and isinstance(price, (int, float))
        and math.isfinite(price)
        and price > 0.0
        and not isinstance(raw_open, bool)
        and isinstance(raw_open, (int, float))
        and math.isfinite(raw_open)
        and raw_open > 0.0
    )
    if (
        item["decision_price_basis"] != expected_basis
        or item["execution_price_basis"] != "retrospective_daily_bar_open_fill"
        or _date(item["decision_price_session"], "decision_price_session")
        != signal.signal_session
        or _datetime(item["decision_price_effective_at"], "decision_price_effective_at")
        != accepted_signal.close_at
        or _date(item["session_date"], "session_date") != signal.execution_session
        or _datetime(
            item["execution_price_effective_at"],
            "execution_price_effective_at",
        )
        != accepted_execution.open_at
        or decision_source.available_at > signal.decision_at
        or not valid_prices
    ):
        raise InputBlockedError("execution price basis or calendar identity mismatch")
    return ExecutionInput(
        item["symbol"],
        item["market"],
        float(raw_open),
        item["currency"],
        _source(item["source"]),
        statuses,
        corporate_actions=actions,
        decision_price=float(price),
        decision_price_source=decision_source,
        decision_price_basis=item["decision_price_basis"],
        execution_price_effective_at=_datetime(
            item["execution_price_effective_at"],
            "execution_price_effective_at",
        ),
        execution_price_basis=item["execution_price_basis"],
    )


def _load_bundle(
    payload: bytes,
    *,
    stage: str,
    signals: tuple[SignalBoundary, ...],
) -> Bundle:
    record = _json(payload, "runtime bundle")
    _keys(record, _BUNDLE_FIELDS, "runtime bundle")
    expected_raw_boundaries = 130 if stage == "validation" else 157
    if (
        record["schema_version"] != "c6-vix-weekly-change-runtime-v1"
        or record["research_id"] != C6_RESEARCH_ID
        or record["stage"] != stage
        or record["symbol"] != "SPY"
        or record["state_input_sha256"] != WEEKLY_VIX_INPUT_SHA256
        or record["calendar_input_sha256"] != CALENDAR_INPUT_SHA256
    ):
        raise InputBlockedError("runtime bundle frozen identity mismatch")
    reconstruction = _calendar(record["reconstruction_calendar"])
    epochs = _calendar_epochs(record["calendar_epochs"])
    raw_points = record["execution_points"]
    if type(raw_points) is not list or len(raw_points) != expected_raw_boundaries:
        raise InputBlockedError("runtime weekly boundary count mismatch")
    point_map: dict[str, dict[str, Any]] = {}
    for raw in raw_points:
        item = _keys(raw, _POINT_FIELDS, "execution point")
        key = item["signal_session"]
        if type(key) is not str or key in point_map:
            raise InputBlockedError("runtime signal sessions must be unique")
        point_map[key] = item
    raw_daily = record["daily_sessions"]
    if type(raw_daily) is not list:
        raise InputBlockedError("daily_sessions must be a list")
    complete_daily = tuple(_date(value, "daily session") for value in raw_daily)
    expected_complete = tuple(
        session
        for session in reconstruction.session_dates
        if complete_daily[0] <= session <= complete_daily[-1]
    )
    if complete_daily != expected_complete:
        raise InputBlockedError("runtime daily session coverage is incomplete")
    first = signals[0].execution_session
    last = signals[-1].execution_session
    daily = tuple(day for day in complete_daily if first <= day <= last)
    expected_daily = tuple(
        day for day in reconstruction.session_dates if first <= day <= last
    )
    if daily != expected_daily:
        raise InputBlockedError("selected monthly daily coverage is incomplete")
    raw_actions = record["corporate_actions"]
    if type(raw_actions) is not list:
        raise InputBlockedError("corporate_actions must be a list")
    all_actions = tuple(_action(row) for row in raw_actions)
    if len({action.action_id for action in all_actions}) != len(all_actions):
        raise InputBlockedError("corporate action identities must be unique")
    actions = tuple(
        action for action in all_actions if first <= action.effective_date <= last
    )
    if any(action.effective_date not in set(daily) for action in actions):
        raise InputBlockedError("corporate action must use an accepted split session")
    points: list[Point] = []
    for index, signal in enumerate(signals):
        try:
            item = point_map[signal.signal_session.isoformat()]
            calendar = epochs[item["decision_calendar_epoch_id"]]
            revision_id = item["execution_calendar_revision_id"]
            revision = None if revision_id is None else epochs[revision_id]
        except KeyError as exc:
            raise InputBlockedError("selected signal has no runtime identity") from exc
        if (
            item["decision_at"] != signal.decision_at.isoformat()
            or item["execution_session"] != signal.execution_session.isoformat()
            or item["state_row_sha256"] != signal.vix_row_sha256
            or calendar.next_session(
                signal.signal_session,
                as_of=signal.decision_at,
            ).session_date
            != signal.execution_session
        ):
            raise InputBlockedError("selected signal differs from runtime identity")
        statuses = tuple(_status(value) for value in item["status_evidence"])
        execution_actions = tuple(
            action for action in actions if action.effective_date == signal.execution_session
        )
        if item["execution"]["corporate_action_ids"] != [
            action.action_id for action in execution_actions
        ]:
            raise InputBlockedError("execution action coverage is incomplete")
        execution = _execution(
            item["execution"],
            statuses,
            execution_actions,
            signal=signal,
            calendar=calendar,
        )
        snapshot = _snapshot(item["universe_snapshot"])
        if snapshot.effective_session != signal.execution_session:
            raise InputBlockedError("universe snapshot session mismatch")
        validate_universe_snapshot(
            snapshot,
            market="us",
            calendar_identity=calendar.identity,
            session=calendar.session_on(
                signal.execution_session,
                as_of=signal.decision_at,
            ),
            decision_at=signal.decision_at,
            members=("SPY",),
            records_by_symbol={"SPY": statuses},
        )
        points.append(
            Point(
                signal,
                calendar,
                revision,
                execution,
                snapshot,
                index == len(signals) - 1,
            )
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
        if action.action_type in {"cash_dividend", "special_dividend"}:
            assert action.cash_amount is not None and action.ex_date and action.pay_date
            portfolio.apply_cash_distribution(
                "SPY",
                event_id=action.action_id,
                amount_per_share=float(action.cash_amount),
                ex_date=action.ex_date,
                pay_date=action.pay_date,
            )
        elif action.action_type in {"split", "reverse_split"}:
            assert action.split_ratio is not None
            portfolio.apply_split(
                "SPY",
                float(action.split_ratio),
                event_id=action.action_id,
            )
        else:
            raise InputBlockedError("unsupported nonterminal SPY corporate action")


def _rebalance(
    portfolio: Portfolio,
    point: Point,
    target: float | None,
    prior_stage_hash: str,
):
    return run_static_rebalance(
        portfolio,
        point.calendar,
        signal_session=point.signal.signal_session,
        decision_at=point.signal.decision_at,
        execution_inputs=(point.execution_input,),
        execution_calendar_revision=point.execution_calendar_revision,
        universe_members=("SPY",),
        universe_snapshot=point.universe_snapshot,
        target_weights=lambda context: {} if target is None else {"SPY": target},
        strategy_definition_sha256=DEFINITION_SHA256,
        strategy_adapter_sha256=ADAPTER_SHA256,
        slippage_bps=ONE_WAY_SLIPPAGE_BPS,
        prior_stage_hash=prior_stage_hash,
    )


def _simulate(bundle: Bundle) -> tuple[tuple[float, ...], tuple[float, ...], tuple[str, ...]]:
    point_by_date = {point.signal.execution_session: point for point in bundle.points}
    actions_by_date = {
        day: tuple(action for action in bundle.actions if action.effective_date == day)
        for day in bundle.daily_sessions
    }
    strategy = Portfolio.us(INITIAL_CAPITAL)
    benchmark = Portfolio.us(INITIAL_CAPITAL)
    strategy_navs = [INITIAL_CAPITAL]
    benchmark_navs = [INITIAL_CAPITAL]
    strategy_stage = "0" * 64
    benchmark_stage = "0" * 64
    stage_hashes: list[str] = []
    for session_date in bundle.daily_sessions:
        point = point_by_date.get(session_date)
        daily_actions = actions_by_date[session_date]
        if point is None:
            _apply_actions(strategy, session_date, daily_actions)
            _apply_actions(benchmark, session_date, daily_actions)
            continue
        if point.terminal_exit:
            strategy_result = _rebalance(strategy, point, None, strategy_stage)
            benchmark_result = _rebalance(benchmark, point, None, benchmark_stage)
            strategy = strategy_result.portfolio
            benchmark = benchmark_result.portfolio
            strategy_navs.append(strategy_result.final_nav)
            benchmark_navs.append(benchmark_result.final_nav)
            stage_hashes.extend((strategy_result.stage_hash, benchmark_result.stage_hash))
            continue
        strategy_result = _rebalance(
            strategy,
            point,
            point.signal.target_weight,
            strategy_stage,
        )
        strategy = strategy_result.portfolio
        strategy_stage = strategy_result.stage_hash
        stage_hashes.append(strategy_stage)
        if point is bundle.points[0]:
            benchmark_result = _rebalance(benchmark, point, 1.0, benchmark_stage)
            benchmark = benchmark_result.portfolio
            benchmark_stage = benchmark_result.stage_hash
            stage_hashes.append(benchmark_stage)
            continue
        _apply_actions(benchmark, session_date, daily_actions)
        raw_open = point.execution_input.open_price
        if raw_open is None or not math.isfinite(raw_open) or raw_open <= 0.0:
            raise InputBlockedError("benchmark boundary requires a positive raw open")
        strategy_navs.append(strategy_result.final_nav)
        benchmark_navs.append(benchmark.nav({"SPY": float(raw_open)}))
    expected = (VALIDATION_INTERVALS if bundle.stage == "validation" else HOLDOUT_INTERVALS) + 1
    if len(strategy_navs) != expected or len(benchmark_navs) != expected:
        raise InputBlockedError("monthly split boundary path is incomplete")
    strategy_returns = tuple(
        right / left - 1.0 for left, right in zip(strategy_navs, strategy_navs[1:])
    )
    benchmark_returns = tuple(
        right / left - 1.0 for left, right in zip(benchmark_navs, benchmark_navs[1:])
    )
    return strategy_returns, benchmark_returns, tuple(stage_hashes)


def _decision(
    stage: str,
    strategy: tuple[float, ...],
    spy: tuple[float, ...],
) -> dict[str, Any]:
    decision = (
        validation_decision(strategy, spy)
        if stage == "validation"
        else holdout_decision(strategy, spy)
    )
    extra = (
        {"arithmetic_mean_active_return": decision.arithmetic_mean_active_return}
        if stage == "validation"
        else {"inference": asdict(decision.inference)}
    )
    return {
        "stage": stage,
        "observed_intervals": decision.observed_intervals,
        "strategy": asdict(decision.strategy),
        "spy": asdict(decision.spy),
        "gates": {name: passed for name, passed in decision.gates},
        "all_gates_pass": decision.all_gates_pass,
        **extra,
    }


def _private_parent(path: Path) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    parent = path.parent.lstat()
    if (
        not stat.S_ISDIR(parent.st_mode)
        or parent.st_uid != os.getuid()
        or stat.S_IMODE(parent.st_mode) & ~0o700
        or path.exists()
        or path.is_symlink()
    ):
        raise InputBlockedError("one-use target must be absent under a private directory")


def _publish(path: Path, record: dict[str, Any]) -> str:
    _private_parent(path)
    payload = json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(temporary, flags, 0o600)
        try:
            written = 0
            while written < len(payload):
                count = os.write(fd, payload[written:])
                if count <= 0:
                    raise InputBlockedError("private publication was incomplete")
                written += count
            os.fsync(fd)
        finally:
            os.close(fd)
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
    return _sha256_bytes(payload)


def _claim_record(stage: str, runner_sha256: str, bundle_sha256: str) -> dict[str, Any]:
    return {
        "schema_version": "c7-spy-variance-risk-premium-claim-v1",
        "research_id": RESEARCH_ID,
        "stage": stage,
        "claimed_at": datetime.now(timezone.utc).isoformat(),
        "definition_sha256": DEFINITION_SHA256,
        "adapter_sha256": ADAPTER_SHA256,
        "runner_sha256": runner_sha256,
        "signal_input_sha256": SIGNAL_INPUT_SHA256,
        "runtime_bundle_sha256": bundle_sha256,
        "one_use_execution_consumed": True,
        "rerun_authorized": False,
    }


def _result_record(
    stage: str,
    classification: str,
    *,
    claim_sha256: str,
    bundle_sha256: str,
    decision: dict[str, Any] | None,
    stage_hashes: tuple[str, ...] = (),
    error: Exception | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "c7-spy-variance-risk-premium-result-v1",
        "research_id": RESEARCH_ID,
        "stage": stage,
        "classification": classification,
        "program_alpha": PROGRAM_ALPHA,
        "claim_sha256": claim_sha256,
        "runtime_bundle_sha256": bundle_sha256,
        "signal_input_sha256": SIGNAL_INPUT_SHA256,
        "decision": decision,
        "stage_hashes": list(stage_hashes),
        "error_type": None if error is None else type(error).__name__,
        "error_message": None if error is None else str(error),
        "strategy_candidate_available": False,
        "rerun_authorized": False,
        "shadow": False,
        "paper": False,
        "broker": False,
        "live": False,
    }


def _stage(
    stage: str,
    bundle_path: Path,
    expected_bundle_sha256: str,
    signals: tuple[SignalBoundary, ...],
    claim_path: Path,
    result_path: Path,
    *,
    runner_sha256: str,
) -> dict[str, Any]:
    payload = _capture(
        bundle_path,
        expected_bundle_sha256,
        max_bytes=64 * 1024 * 1024,
    )
    bundle = _load_bundle(payload, stage=stage, signals=signals)
    bundle_sha256 = _sha256_bytes(payload)
    claim_sha256 = _publish(
        claim_path,
        _claim_record(stage, runner_sha256, bundle_sha256),
    )
    try:
        strategy, spy, stage_hashes = _simulate(bundle)
        decision = _decision(stage, strategy, spy)
        if stage == "validation":
            classification = (
                "RETROSPECTIVE_SECONDARY_VALIDATION_PASS_HOLDOUT_UNLOCKED"
                if decision["all_gates_pass"]
                else "RETROSPECTIVE_SECONDARY_VALIDATION_FAIL"
            )
        else:
            classification = (
                "RETROSPECTIVE_SECONDARY_PASS_PENDING_REVIEW"
                if decision["all_gates_pass"]
                else "RETROSPECTIVE_SECONDARY_HOLDOUT_FAIL"
            )
        record = _result_record(
            stage,
            classification,
            claim_sha256=claim_sha256,
            bundle_sha256=bundle_sha256,
            decision=decision,
            stage_hashes=stage_hashes,
        )
    except Exception as exc:
        record = _result_record(
            stage,
            "INPUT_BLOCKED_CLAIM_CONSUMED",
            claim_sha256=claim_sha256,
            bundle_sha256=bundle_sha256,
            decision=None,
            error=exc,
        )
    _publish(result_path, record)
    return record


def _targets_absent() -> None:
    targets = {VALIDATION_CLAIM, VALIDATION_RESULT, HOLDOUT_CLAIM, HOLDOUT_RESULT}
    if len(targets) != 4 or any(path.exists() or path.is_symlink() for path in targets):
        raise InputBlockedError("one-use claim or result target already exists")


def _validate_definition(payload: bytes) -> dict[str, Any]:
    definition = _json(payload, "definition")
    runtime = definition.get("runtime_materialization")
    source = definition.get("source_identities")
    boundaries = definition.get("boundaries")
    if type(runtime) is not dict or type(source) is not dict or type(boundaries) is not dict:
        raise InputBlockedError("definition identity sections are missing")
    if (
        definition.get("research_id") != RESEARCH_ID
        or definition.get("status") != "PREREGISTERED_INPUT_MATERIALIZED_CODE_READY"
        or runtime.get("parent_preregistration_sha256")
        != PARENT_PREREGISTRATION_SHA256
        or runtime.get("signal_packet_sha256") != SIGNAL_INPUT_SHA256
        or runtime.get("state_support_receipt_sha256") != SUPPORT_RECEIPT_SHA256
        or runtime.get("validation_bundle_sha256") != VALIDATION_BUNDLE_SHA256
        or runtime.get("holdout_bundle_sha256") != HOLDOUT_BUNDLE_SHA256
        or runtime.get("status") != "PASS_STATE_SUPPORT"
        or source.get("weekly_vix_input_sha256") != WEEKLY_VIX_INPUT_SHA256
        or source.get("validation_spy_bundle_sha256") != VALIDATION_BUNDLE_SHA256
        or source.get("holdout_spy_bundle_sha256") != HOLDOUT_BUNDLE_SHA256
        or source.get("shared_core_commit")
        != "35b3246e40f8315e2bbef847d995a3b6d3a3b4fc"
        or boundaries.get("outcome_access") is not False
        or boundaries.get("strategy_candidate_available") is not False
    ):
        raise InputBlockedError("definition does not bind exact frozen identities")
    code = definition.get("code_identity")
    if (
        type(code) is not dict
        or code.get("adapter_sha256") != ADAPTER_SHA256
        or code.get("shared_core_source_file_count") != CORE_SOURCE_FILE_COUNT
        or code.get("shared_core_source_sha256") != CORE_SOURCE_SHA256
        or code.get("universe_inclusion_rule_sha256") != INCLUSION_RULE_SHA256
    ):
        raise InputBlockedError("definition code identity mismatch")
    return definition


def execute_once() -> dict[str, Any]:
    definition_sha256 = _runtime_sha(DEFINITION_SHA256, "definition SHA-256")
    adapter_sha256 = _runtime_sha(ADAPTER_SHA256, "adapter SHA-256")
    _targets_absent()
    definition_payload = _capture(
        DEFINITION,
        definition_sha256,
        max_bytes=256 * 1024,
        private=False,
    )
    definition = _validate_definition(definition_payload)
    if _file_sha256(ADAPTER) != adapter_sha256:
        raise InputBlockedError("adapter bytes differ from frozen identity")
    if _core_identity() != (CORE_SOURCE_FILE_COUNT, CORE_SOURCE_SHA256):
        raise InputBlockedError("shared-core bytes differ from frozen identity")
    signal_payload = _capture(
        SIGNAL_INPUT,
        SIGNAL_INPUT_SHA256,
        max_bytes=2 * 1024 * 1024,
    )
    support_payload = _capture(
        SUPPORT_RECEIPT,
        SUPPORT_RECEIPT_SHA256,
        max_bytes=64 * 1024,
    )
    signals = _signal_rows(signal_payload, definition)
    _support_receipt(support_payload, definition)
    runner_sha256 = _file_sha256(RUNNER)
    validation = _stage(
        "validation",
        VALIDATION_BUNDLE,
        VALIDATION_BUNDLE_SHA256,
        signals["validation"],
        VALIDATION_CLAIM,
        VALIDATION_RESULT,
        runner_sha256=runner_sha256,
    )
    if (
        validation["classification"]
        != "RETROSPECTIVE_SECONDARY_VALIDATION_PASS_HOLDOUT_UNLOCKED"
    ):
        return validation
    return _stage(
        "holdout",
        HOLDOUT_BUNDLE,
        HOLDOUT_BUNDLE_SHA256,
        signals["holdout"],
        HOLDOUT_CLAIM,
        HOLDOUT_RESULT,
        runner_sha256=runner_sha256,
    )


def main() -> int:
    record = execute_once()
    public = {
        "classification": record["classification"],
        "result_path": str(
            HOLDOUT_RESULT if record["stage"] == "holdout" else VALIDATION_RESULT
        ),
        "result_sha256": _file_sha256(
            HOLDOUT_RESULT if record["stage"] == "holdout" else VALIDATION_RESULT
        ),
        "strategy_candidate_available": False,
    }
    print(json.dumps(public, sort_keys=True, separators=(",", ":")))
    return 2 if record["classification"] == "INPUT_BLOCKED_CLAIM_CONSUMED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
