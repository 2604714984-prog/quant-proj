"""One-use retrospective runner for the frozen Cycle 3 FOMC policy state."""

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
)
from quant_system.markets.universe import StatusEvidence, UniverseSnapshotIdentity  # noqa: E402
from research.adapters.c3_policy_last_fomc_move import (  # noqa: E402
    HOLDOUT_INTERVALS,
    INITIAL_CAPITAL,
    PROGRAM_ALPHA,
    RESEARCH_ID,
    VALIDATION_INTERVALS,
    PolicyState,
    holdout_decision,
    split_support,
    validation_decision,
)

DEFINITION = ROOT / "research/definitions/c3_policy_last_fomc_move_v1.json"
ADAPTER = ROOT / "research/adapters/c3_policy_last_fomc_move.py"
RUNNER = Path(__file__).resolve()
DEFINITION_SHA256 = "1b7f3d083b8dc71d9d566b2612f58e933f4173b9fa077d38d6b6988adc97135e"
ADAPTER_SHA256 = "54f8adf6f36a82ae34c615b1b63435ef763be8b3fb4c191e68406749072af2fa"
STATE_INPUT_SHA256 = "153b114ee2df45a232ef7986cc70802f3b8169eb698aa2761d1ade29c06cbbc3"
CALENDAR_INPUT_SHA256 = "08b1722c675012d89e0b4f92ed51f51160adbd1d54961c093c52101c067fc553"
VALIDATION_BUNDLE_SHA256 = "499157cd45b6402aabb8f786ae7e60f9c4bb55992e60bab8ff03f1104baa5b8a"
HOLDOUT_BUNDLE_SHA256 = "ff4b02932079ad013da05dbffcf2dd6e25af8592450e5b09e4a2f00d9f61f8d4"
CORE_SOURCE_FILE_COUNT = 23
CORE_SOURCE_SHA256 = "46ae2fe342a40034b9caacb6cc48a182947a49da9d874de31a1fdb60be0b9a80"
INCLUSION_RULE_SHA256 = "89483ee34a4b87fcdb728889dc31c7dc7222f85b3071ff7a97c65148e1b6402e"
STATE_INPUT = Path(
    "/home/rongyu/workspace/quant-data/staging/us_fomc_policy_state_v2/"
    "fomc_policy_direction_input_v2.json"
)
VALIDATION_BUNDLE = STATE_INPUT.with_name("spy_validation_runtime_bundle_v2.json")
HOLDOUT_BUNDLE = STATE_INPUT.with_name("spy_holdout_runtime_bundle_v2.json")
PRIVATE_ROOT = Path("/home/rongyu/workspace/quant-data/private_results")
VALIDATION_CLAIM = PRIVATE_ROOT / "c3_policy_last_fomc_move_v1_validation/claim.json"
VALIDATION_RESULT = VALIDATION_CLAIM.with_name("result.json")
HOLDOUT_CLAIM = PRIVATE_ROOT / "c3_policy_last_fomc_move_v1_holdout/claim.json"
HOLDOUT_RESULT = HOLDOUT_CLAIM.with_name("result.json")
ONE_WAY_SLIPPAGE_BPS = 10.0
_SOURCE_FIELDS = {"source_url", "content_sha256", "available_at", "retrieved_at", "revision_id", "supersedes_revision_id"}
_SESSION_FIELDS = {"session_date", "open_at", "close_at", "is_early_close", "exchange_id", "exchange_timezone", "row_sha256", "source"}
_CALENDAR_IDENTITY_FIELDS = {"exchange_id", "exchange_timezone", "coverage_start", "coverage_end", "session_count", "session_dates_sha256", "session_rows_sha256", "source_identity"}
_STATUS_FIELDS = {"status_id", "symbol", "kind", "value", "effective_from", "effective_to", "exchange_timezone", "source"}
_SNAPSHOT_FIELDS = {"market", "exchange_id", "effective_session", "member_count", "ordered_members_sha256", "lifecycle_coverage_sha256", "inclusion_rule_sha256", "calendar_identity_sha256", "source_identity"}
_ACTION_FIELDS = {"subject_id", "action_id", "action_type", "effective_at", "source", "exchange_timezone", "ex_date", "record_date", "pay_date", "split_ratio", "cash_amount", "currency", "unit", "new_subject_id"}
_EXECUTION_FIELDS = {"symbol", "market", "session_date", "raw_open", "currency", "source", "decision_price", "decision_price_session", "decision_price_effective_at", "decision_price_source", "decision_price_basis", "execution_price_effective_at", "execution_price_basis", "corporate_action_ids"}
_BUNDLE_FIELDS = {"schema_version", "research_id", "stage", "symbol", "state_input_sha256", "calendar_input_sha256", "reconstruction_calendar", "calendar_epochs", "execution_points", "daily_sessions", "corporate_actions"}
_POINT_FIELDS = {"signal_session", "decision_at", "execution_session", "decision_calendar_epoch_id", "execution_calendar_revision_id", "terminal_exit", "policy_state", "status_evidence", "universe_snapshot", "execution"}
_STATE_FIELDS = {"direction", "last_move_effective_date", "last_move_delta_percent", "spy_target_weight", "official_state_row_sha256"}
_OFFICIAL_TOP_FIELDS = {"acquisition", "calendar_identity", "database_write", "decision_count", "decision_rule", "decisions", "event_count", "events", "mechanism", "schema_version", "source_identities", "split_support", "stage", "strategy_candidate_available"}
_OFFICIAL_CALENDAR_FIELDS = {"calendar_rows_used", "row_count", "source_path_logical_name", "source_sha256", "timezone"}
_OFFICIAL_DECISION_FIELDS = {"decision_at", "decision_month", "decision_session", "decision_session_identity", "row_sha256", "selected_event", "state"}
_OFFICIAL_EVENT_FIELDS = {"content_sha256", "direction", "document_filename", "document_text_has_funds_rate_phrase", "effective_date", "linked_implementation_note_identity", "linked_implementation_notes", "new_lower_bound", "new_upper_bound", "old_lower_bound", "old_upper_bound", "release_at", "release_time_source_text", "retrieved_at", "row_sha256", "source_url", "statement_date", "target_range_index_sha256"}
_SESSION_IDENTITY_FIELDS = {"close_at", "early_close", "exchange", "is_open", "open_at", "row_sha256", "session_date", "snapshot_id", "source_available_at", "source_document_set_sha256", "source_url", "timezone"}
_SUPPORT_FIELDS = {"easing", "months", "tightening", "transitions"}


class InputBlockedError(ValueError):
    """Fail-closed identity, schema, chronology, or one-use error."""


@dataclass(frozen=True)
class Point:
    signal_session: date
    decision_at: datetime
    execution_session: date
    calendar: AcceptedSessionCalendar
    execution_calendar_revision: AcceptedSessionCalendar | None
    execution_input: ExecutionInput
    universe_snapshot: UniverseSnapshotIdentity
    policy_state: PolicyState
    state_row_sha256: str
    terminal_exit: bool


@dataclass(frozen=True)
class Bundle:
    stage: str
    reconstruction_calendar: AcceptedSessionCalendar
    points: tuple[Point, ...]
    daily_sessions: tuple[date, ...]
    actions: tuple[CorporateActionIdentity, ...]


@dataclass(frozen=True)
class OfficialBoundary:
    execution_session: date
    state: PolicyState
    row_sha256: str
    open_at: datetime
    close_at: datetime
    exchange_id: str
    exchange_timezone: str
    source_document_set_sha256: str
    source_available_at: datetime
    session_row_sha256: str


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


def _file_sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _core_identity() -> tuple[int, str]:
    rows: list[dict[str, str]] = []
    for path in sorted((ROOT / "src/quant_system").rglob("*.py")):
        if path.is_symlink() or not path.is_file():
            raise InputBlockedError("shared-core source must contain regular files")
        rows.append({"path": path.relative_to(ROOT).as_posix(), "sha256": _file_sha256(path)})
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
        record = json.loads(payload.decode("utf-8", errors="strict"), object_pairs_hook=_strict_object, parse_constant=lambda value: (_ for _ in ()).throw(InputBlockedError(f"nonfinite JSON constant: {value}")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputBlockedError(f"{field} is not strict UTF-8 JSON") from exc
    if type(record) is not dict:
        raise InputBlockedError(f"{field} must be a JSON object")
    return record


def _capture(path: Path, expected_sha256: str | None, *, max_bytes: int) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise InputBlockedError(f"cannot open protected input: {path}") from exc
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid():
            raise InputBlockedError("input must be an owner-controlled regular file")
        if stat.S_IMODE(before.st_mode) & ~0o600 or not 0 < before.st_size <= max_bytes:
            raise InputBlockedError("input mode or size is outside the frozen bound")
        chunks: list[bytes] = []
        size = 0
        while True:
            chunk = os.read(fd, min(1024 * 1024, max_bytes + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            if size > max_bytes:
                raise InputBlockedError("input exceeds the frozen size bound")
        after = os.fstat(fd)
    finally:
        os.close(fd)
    try:
        current = os.stat(path, follow_symlinks=False)
    except OSError as exc:
        raise InputBlockedError("input path changed during capture") from exc
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(getattr(before, field) != getattr(after, field) or getattr(after, field) != getattr(current, field) for field in fields):
        raise InputBlockedError("input changed during descriptor-bound capture")
    payload = b"".join(chunks)
    if expected_sha256 is not None and _sha256_bytes(payload) != _sha256(expected_sha256, "expected input SHA-256"):
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


def _load_official_states(payload: bytes) -> dict[str, tuple[OfficialBoundary, ...]]:
    record = _json(payload, "official policy-state input")
    _keys(record, _OFFICIAL_TOP_FIELDS, "official policy-state input")
    if record["schema_version"] != "us-fomc-policy-direction-input-v1" or record["mechanism"] != "C3_POLICY_LAST_FOMC_MOVE_DIRECTION_PRIMARY_DOCUMENT_STATE" or record["stage"] != "outcome_free_policy_state" or record["decision_count"] != 100 or record["strategy_candidate_available"] is not False:
        raise InputBlockedError("official policy-state top-level identity mismatch")
    calendar_identity = _keys(record["calendar_identity"], _OFFICIAL_CALENDAR_FIELDS, "official calendar identity")
    if _sha256(calendar_identity["source_sha256"], "official calendar source SHA-256") != CALENDAR_INPUT_SHA256 or calendar_identity["timezone"] != "America/New_York":
        raise InputBlockedError("official policy-state calendar identity mismatch")
    rows, events = record["decisions"], record["events"]
    if type(rows) is not list or len(rows) != 100 or type(events) is not list or len(events) != record["event_count"]:
        raise InputBlockedError("official policy-state row counts mismatch")
    event_hashes = {_sha256(_keys(event, _OFFICIAL_EVENT_FIELDS, "policy event")["row_sha256"], "event row SHA-256") for event in events}
    boundaries: list[OfficialBoundary] = []
    for raw in rows:
        row = _keys(raw, _OFFICIAL_DECISION_FIELDS, "policy decision")
        event = _keys(row["selected_event"], _OFFICIAL_EVENT_FIELDS, "selected policy event")
        session = _keys(row["decision_session_identity"], _SESSION_IDENTITY_FIELDS, "decision session identity")
        decision_at = _datetime(row["decision_at"], "official decision_at")
        execution_session = _date(row["decision_session"], "official decision_session")
        event_hash = _sha256(event["row_sha256"], "selected event row SHA-256")
        official_direction = row["state"]
        if event["direction"] != official_direction or official_direction not in {"EASING", "TIGHTENING"}:
            raise InputBlockedError("official policy-state direction must match exact uppercase vocabulary")
        direction = official_direction.lower()
        open_at = _datetime(session["open_at"], "official session open_at")
        close_at = _datetime(session["close_at"], "official session close_at")
        source_available_at = _datetime(session["source_available_at"], "official session source_available_at")
        if (
            event_hash not in event_hashes
            or session["session_date"] != row["decision_session"]
            or row["decision_month"] != execution_session.isoformat()[:7]
            or _datetime(event["release_at"], "event release_at") > decision_at
            or session["exchange"] != "XNYS"
            or session["timezone"] != "America/New_York"
            or session["is_open"] is not True
            or source_available_at > decision_at
            or not decision_at < open_at < close_at
        ):
            raise InputBlockedError("official policy-state event/session mapping mismatch")
        delta = _decimal(event["new_upper_bound"], "new upper bound") - _decimal(event["old_upper_bound"], "old upper bound")
        state = PolicyState(decision_at, direction, _date(event["effective_date"], "event effective_date"), float(delta), 1.0 if direction == "easing" else 0.0)
        boundaries.append(OfficialBoundary(execution_session, state, _sha256(row["row_sha256"], "decision row SHA-256"), open_at, close_at, session["exchange"], session["timezone"], _sha256(session["source_document_set_sha256"], "official calendar document SHA-256"), source_available_at, _sha256(session["row_sha256"], "official session row SHA-256")))
    if len({item.row_sha256 for item in boundaries}) != 100 or any(right.state.decision_at <= left.state.decision_at for left, right in zip(boundaries, boundaries[1:])):
        raise InputBlockedError("official policy-state decisions are duplicated or reordered")
    groups = {"development": tuple(boundaries[:34]), "validation": tuple(boundaries[34:64]), "holdout": tuple(boundaries[64:])}
    declared = record["split_support"]
    if type(declared) is not dict or set(declared) != {"development", "validation", "retrospective_holdout"}:
        raise InputBlockedError("official split-support schema mismatch")
    for split_id, group in groups.items():
        decision = split_support(tuple(item.state for item in group), split_id=split_id)
        key = "retrospective_holdout" if split_id == "holdout" else split_id
        observed = _keys(declared[key], _SUPPORT_FIELDS, "official split support")
        expected = {"months": len(group), "easing": decision.easing_count, "tightening": decision.tightening_count, "transitions": decision.adjacent_state_changes}
        if observed != expected or not decision.all_gates_pass:
            raise InputBlockedError(f"official {split_id} state-support identity failed")
    return groups


def _execution_actions(actions: tuple[CorporateActionIdentity, ...], session: date, supplied_ids: object) -> tuple[CorporateActionIdentity, ...]:
    expected = tuple(action for action in actions if action.effective_date == session)
    if supplied_ids != [action.action_id for action in expected]:
        raise InputBlockedError("execution action coverage is incomplete or reordered")
    return expected


def _source(row: object) -> SourceIdentity:
    item = _keys(row, _SOURCE_FIELDS, "source identity")
    return SourceIdentity(item["source_url"], item["content_sha256"], _datetime(item["available_at"], "source available_at"), _datetime(item["retrieved_at"], "source retrieved_at"), item["revision_id"], item["supersedes_revision_id"])


def _calendar(row: object) -> AcceptedSessionCalendar:
    item = _keys(row, {"calendar_identity", "session_rows"}, "calendar")
    if type(item["session_rows"]) is not list:
        raise InputBlockedError("calendar session_rows must be a list")
    sessions = tuple(AcceptedSession(_date(session["session_date"], "session_date"), _datetime(session["open_at"], "open_at"), _datetime(session["close_at"], "close_at"), _source(session["source"]), session["exchange_timezone"], session["is_early_close"], session["exchange_id"]) for raw in item["session_rows"] for session in (_keys(raw, _SESSION_FIELDS, "calendar session"),))
    identity = _keys(item["calendar_identity"], _CALENDAR_IDENTITY_FIELDS, "calendar identity")
    if identity["exchange_id"] != "XNYS" or identity["exchange_timezone"] != "America/New_York" or any(session.exchange_id != "XNYS" or session.exchange_timezone != "America/New_York" for session in sessions):
        raise InputBlockedError("runtime calendars must be XNYS America/New_York")
    frozen = CalendarIdentity(identity["exchange_id"], identity["exchange_timezone"], _date(identity["coverage_start"], "coverage_start"), _date(identity["coverage_end"], "coverage_end"), identity["session_count"], identity["session_dates_sha256"], identity["session_rows_sha256"], _source(identity["source_identity"]))
    return AcceptedSessionCalendar(sessions, identity=frozen)


def _calendar_epochs(rows: object) -> dict[str, AcceptedSessionCalendar]:
    if type(rows) is not dict or not rows or any(type(key) is not str or not key for key in rows):
        raise InputBlockedError("calendar epochs are required")
    digests = [_sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()) for value in rows.values()]
    if len(set(digests)) != len(digests):
        raise InputBlockedError("calendar epoch identities must not duplicate calendar bytes")
    return {key: _calendar(value) for key, value in rows.items()}


def _status(row: object) -> StatusEvidence:
    item = _keys(row, _STATUS_FIELDS, "status evidence")
    if item["symbol"] != "SPY" or item["exchange_timezone"] != "America/New_York":
        raise InputBlockedError("status evidence must identify SPY in America/New_York")
    ending = None if item["effective_to"] is None else _date(item["effective_to"], "effective_to")
    return StatusEvidence(item["status_id"], item["symbol"], item["kind"], item["value"], _date(item["effective_from"], "effective_from"), ending, item["exchange_timezone"], _source(item["source"]))


def _snapshot(row: object) -> UniverseSnapshotIdentity:
    item = _keys(row, _SNAPSHOT_FIELDS, "universe snapshot")
    if item["market"] != "us" or item["exchange_id"] != "XNYS":
        raise InputBlockedError("universe snapshot must identify the US XNYS venue")
    snapshot = UniverseSnapshotIdentity(item["market"], item["exchange_id"], _date(item["effective_session"], "effective_session"), item["member_count"], item["ordered_members_sha256"], item["lifecycle_coverage_sha256"], item["inclusion_rule_sha256"], item["calendar_identity_sha256"], _source(item["source_identity"]))
    if snapshot.inclusion_rule_sha256 != INCLUSION_RULE_SHA256:
        raise InputBlockedError("universe inclusion rule mismatch")
    return snapshot


def _action(row: object) -> CorporateActionIdentity:
    item = _keys(row, _ACTION_FIELDS, "corporate action")
    if item["subject_id"] != "SPY" or item["exchange_timezone"] != "America/New_York":
        raise InputBlockedError("corporate action must identify SPY in America/New_York")
    def optional_date(key: str) -> date | None:
        return None if item[key] is None else _date(item[key], key)

    return CorporateActionIdentity(item["subject_id"], item["action_id"], item["action_type"], _datetime(item["effective_at"], "action effective_at"), _source(item["source"]), item["exchange_timezone"], ex_date=optional_date("ex_date"), record_date=optional_date("record_date"), pay_date=optional_date("pay_date"), split_ratio=None if item["split_ratio"] is None else Decimal(item["split_ratio"]), cash_amount=None if item["cash_amount"] is None else Decimal(item["cash_amount"]), currency=item["currency"], unit=item["unit"], new_subject_id=item["new_subject_id"])


def _execution(
    row: object,
    statuses: tuple[StatusEvidence, ...],
    actions: tuple[CorporateActionIdentity, ...],
    *,
    signal_session: date,
    decision_at: datetime,
    calendar: AcceptedSessionCalendar,
) -> ExecutionInput:
    item = _keys(row, _EXECUTION_FIELDS, "execution input")
    if item["symbol"] != "SPY" or item["market"] != "us" or item["currency"] != "USD":
        raise InputBlockedError("only the frozen US SPY execution input is allowed")
    action_ids = tuple(action.action_id for action in actions)
    if item["corporate_action_ids"] != list(action_ids):
        raise InputBlockedError("execution corporate-action mapping mismatch")
    ordinary = {"cash_dividend", "special_dividend", "split", "reverse_split"}
    if any(action.action_type not in ordinary for action in actions):
        raise InputBlockedError("unsupported execution-day corporate action")
    expected_basis = "raw_pre_action_per_old_share" if actions else "raw_execution_units"
    decision_source = _source(item["decision_price_source"])
    price = item["decision_price"]
    accepted_signal = calendar.session_on(signal_session, as_of=decision_at)
    execution_effective_at = _datetime(item["execution_price_effective_at"], "execution_price_effective_at")
    accepted_execution = calendar.session_on(_date(item["session_date"], "session_date"), as_of=decision_at)
    if execution_effective_at != accepted_execution.open_at:
        raise InputBlockedError("execution price effective_at must equal accepted execution session open")
    if (
        item["decision_price_basis"] != expected_basis
        or item["execution_price_basis"] != "retrospective_daily_bar_open_fill"
        or _date(item["decision_price_session"], "decision_price_session") != signal_session
        or _datetime(item["decision_price_effective_at"], "decision_price_effective_at") != accepted_signal.close_at
        or decision_source.available_at > decision_at
        or isinstance(price, bool)
        or not isinstance(price, (int, float))
        or not math.isfinite(price)
        or price <= 0.0
    ):
        raise InputBlockedError("execution price basis mismatch")
    return ExecutionInput(item["symbol"], item["market"], item["raw_open"], item["currency"], _source(item["source"]), statuses, corporate_actions=actions, decision_price=price, decision_price_source=decision_source, decision_price_basis=item["decision_price_basis"], execution_price_effective_at=execution_effective_at, execution_price_basis=item["execution_price_basis"])


def _load_bundle(
    payload: bytes,
    *,
    stage: str,
    official_states: dict[str, tuple[OfficialBoundary, ...]],
) -> Bundle:
    expected_points = 30 if stage == "validation" else 36
    record = _json(payload, "runtime bundle")
    _keys(record, _BUNDLE_FIELDS, "runtime bundle")
    if (
        record["schema_version"] != "c3-policy-last-fomc-move-runtime-v1"
        or record["research_id"] != RESEARCH_ID
        or record["stage"] != stage
        or record["symbol"] != "SPY"
        or record["state_input_sha256"] != STATE_INPUT_SHA256
        or _sha256(record["calendar_input_sha256"], "runtime calendar input SHA-256") != CALENDAR_INPUT_SHA256
    ):
        raise InputBlockedError("runtime bundle frozen identity mismatch")
    reconstruction = _calendar(record["reconstruction_calendar"])
    epoch_rows = record["calendar_epochs"]
    epochs = _calendar_epochs(epoch_rows)
    raw_actions = record["corporate_actions"]
    if type(raw_actions) is not list:
        raise InputBlockedError("corporate_actions must be a list")
    actions = tuple(_action(row) for row in raw_actions)
    by_action = {action.action_id: action for action in actions}
    if len(by_action) != len(actions) or any(action.subject_id != "SPY" for action in actions):
        raise InputBlockedError("corporate actions must be unique SPY identities")
    raw_points = record["execution_points"]
    if type(raw_points) is not list or len(raw_points) != expected_points:
        raise InputBlockedError(f"{stage} requires exactly {expected_points} boundaries")
    points: list[Point] = []
    for raw, official in zip(raw_points, official_states[stage], strict=True):
        item = _keys(raw, _POINT_FIELDS, "execution point")
        decision_at = _datetime(item["decision_at"], "decision_at")
        execution_session = _date(item["execution_session"], "execution_session")
        state_row = _keys(item["policy_state"], _STATE_FIELDS, "policy state")
        state = PolicyState(
            decision_at,
            state_row["direction"],
            _date(state_row["last_move_effective_date"], "last_move_effective_date"),
            state_row["last_move_delta_percent"],
            state_row["spy_target_weight"],
        )
        if (
            execution_session != official.execution_session
            or state != official.state
            or state_row["official_state_row_sha256"] != official.row_sha256
        ):
            raise InputBlockedError("runtime policy state differs from official state input")
        point_actions = _execution_actions(
            actions, execution_session, item["execution"]["corporate_action_ids"]
        )
        if any(action.effective_date != execution_session for action in point_actions):
            raise InputBlockedError("execution actions must be effective on the execution session")
        statuses = tuple(_status(row) for row in item["status_evidence"])
        revision_id = item["execution_calendar_revision_id"]
        try:
            calendar = epochs[item["decision_calendar_epoch_id"]]
            revision = None if revision_id is None else epochs[revision_id]
            raw_calendar = epoch_rows[item["decision_calendar_epoch_id"]]
        except KeyError as exc:
            raise InputBlockedError("unknown calendar epoch identity") from exc
        matched_rows = [row for row in raw_calendar["session_rows"] if row["session_date"] == execution_session.isoformat()]
        if len(matched_rows) != 1:
            raise InputBlockedError("runtime execution-session calendar row is missing or duplicated")
        runtime_row = matched_rows[0]
        runtime_source = _source(runtime_row["source"])
        if runtime_row["open_at"] != official.open_at.isoformat() or runtime_row["close_at"] != official.close_at.isoformat() or runtime_row["exchange_id"] != official.exchange_id or runtime_row["exchange_timezone"] != official.exchange_timezone or runtime_source.content_sha256 != official.source_document_set_sha256 or runtime_source.available_at != official.source_available_at or runtime_row["row_sha256"] != official.session_row_sha256:
            raise InputBlockedError("runtime execution-session row differs from official policy-state input")
        signal_session = _date(item["signal_session"], "signal_session")
        execution = _execution(item["execution"], statuses, point_actions, signal_session=signal_session, decision_at=decision_at, calendar=calendar)
        if _date(item["execution"]["session_date"], "session_date") != execution_session:
            raise InputBlockedError("execution session mapping mismatch")
        points.append(
            Point(
                signal_session,
                decision_at,
                execution_session,
                calendar,
                revision,
                execution,
                _snapshot(item["universe_snapshot"]),
                state,
                _sha256(state_row["official_state_row_sha256"], "state row SHA-256"),
                item["terminal_exit"],
            )
        )
    frozen = tuple(points)
    if tuple(point.execution_session for point in frozen) != tuple(
        sorted(point.execution_session for point in frozen)
    ) or len({point.execution_session for point in frozen}) != len(frozen):
        raise InputBlockedError("execution sessions must be unique and chronological")
    if sum(point.terminal_exit is True for point in frozen) != 1 or not frozen[-1].terminal_exit:
        raise InputBlockedError("only the final boundary may be the terminal exit")
    if any(point.terminal_exit for point in frozen[:-1]):
        raise InputBlockedError("entry boundaries cannot be terminal exits")
    for point in frozen:
        local = point.decision_at.astimezone(__import__("zoneinfo").ZoneInfo("America/New_York"))
        if local.date() != point.execution_session or local.time().isoformat() != "09:00:00":
            raise InputBlockedError("decision must be 09:00 ET on the execution session")
        same_month = tuple(
            day for day in point.calendar.session_dates
            if (day.year, day.month) == (point.execution_session.year, point.execution_session.month)
        )
        if not same_month or same_month[0] != point.execution_session:
            raise InputBlockedError("execution must be the first accepted monthly session")
        if point.calendar.next_session(
            point.signal_session, as_of=point.decision_at
        ).session_date != (point.execution_session):
            raise InputBlockedError("execution must be the next accepted session")
    if not split_support(
        tuple(point.policy_state for point in frozen), split_id=stage
    ).all_gates_pass:
        raise InputBlockedError(f"{stage} state-support gates failed")
    raw_daily = record["daily_sessions"]
    if type(raw_daily) is not list:
        raise InputBlockedError("daily_sessions must be a list")
    daily = tuple(_date(value, "daily session") for value in raw_daily)
    expected_daily = tuple(
        session
        for session in reconstruction.session_dates
        if frozen[0].execution_session <= session <= frozen[-1].execution_session
    )
    if daily != expected_daily:
        raise InputBlockedError("daily session coverage is incomplete or reordered")
    if any(not daily[0] <= action.effective_date <= daily[-1] for action in actions):
        raise InputBlockedError("corporate action falls outside the split calendar")
    return Bundle(stage, reconstruction, frozen, daily, actions)


def _apply_actions(portfolio: Portfolio, session_date: date, actions: tuple[CorporateActionIdentity, ...]) -> None:
    portfolio.start_session(session_date)
    for action in actions:
        if action.effective_date != session_date:
            continue
        if action.action_type in {"cash_dividend", "special_dividend"}:
            assert action.cash_amount is not None and action.ex_date and action.pay_date
            portfolio.apply_cash_distribution("SPY", event_id=action.action_id, amount_per_share=float(action.cash_amount), ex_date=action.ex_date, pay_date=action.pay_date)
        elif action.action_type in {"split", "reverse_split"}:
            assert action.split_ratio is not None
            portfolio.apply_split("SPY", float(action.split_ratio), event_id=action.action_id)
        else:
            raise InputBlockedError("unsupported nonterminal SPY corporate action")


def _rebalance(portfolio: Portfolio, point: Point, target: float | None, prior_stage_hash: str):
    return run_static_rebalance(portfolio, point.calendar, signal_session=point.signal_session, decision_at=point.decision_at, execution_inputs=(point.execution_input,), execution_calendar_revision=point.execution_calendar_revision, universe_members=("SPY",), universe_snapshot=point.universe_snapshot, target_weights=lambda context: {} if target is None else {"SPY": target}, strategy_definition_sha256=DEFINITION_SHA256, strategy_adapter_sha256=ADAPTER_SHA256, slippage_bps=ONE_WAY_SLIPPAGE_BPS, prior_stage_hash=prior_stage_hash)


def _simulate(bundle: Bundle) -> tuple[tuple[float, ...], tuple[float, ...], tuple[str, ...]]:
    point_by_date = {point.execution_session: point for point in bundle.points}
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
            strategy, benchmark = strategy_result.portfolio, benchmark_result.portfolio
            strategy_navs.append(strategy_result.final_nav)
            benchmark_navs.append(benchmark_result.final_nav)
            stage_hashes.extend((strategy_result.stage_hash, benchmark_result.stage_hash))
            continue
        strategy_result = _rebalance(
            strategy,
            point,
            point.policy_state.spy_target_weight,
            strategy_stage,
        )
        strategy, strategy_stage = strategy_result.portfolio, strategy_result.stage_hash
        stage_hashes.append(strategy_stage)
        if point is bundle.points[0]:
            benchmark_result = _rebalance(benchmark, point, 1.0, benchmark_stage)
            benchmark, benchmark_stage = benchmark_result.portfolio, benchmark_result.stage_hash
            stage_hashes.append(benchmark_stage)
            continue
        _apply_actions(benchmark, session_date, daily_actions)
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
    expected = (VALIDATION_INTERVALS if bundle.stage == "validation" else HOLDOUT_INTERVALS) + 1
    if len(strategy_navs) != expected or len(benchmark_navs) != expected:
        raise InputBlockedError("split boundary path is incomplete")
    strategy_returns = tuple(
        right / left - 1.0 for left, right in zip(strategy_navs, strategy_navs[1:])
    )
    benchmark_returns = tuple(
        right / left - 1.0 for left, right in zip(benchmark_navs, benchmark_navs[1:])
    )
    return strategy_returns, benchmark_returns, tuple(stage_hashes)


def _decision(stage: str, strategy: tuple[float, ...], spy: tuple[float, ...]) -> dict[str, Any]:
    decision = validation_decision(strategy, spy) if stage == "validation" else holdout_decision(strategy, spy)
    extra = {"arithmetic_mean_active_return": decision.arithmetic_mean_active_return} if stage == "validation" else {"inference": asdict(decision.inference)}
    return {"stage": stage, "observed_intervals": decision.observed_intervals, "strategy": asdict(decision.strategy), "spy": asdict(decision.spy), "gates": {name: passed for name, passed in decision.gates}, "all_gates_pass": decision.all_gates_pass, **extra}


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
        raise InputBlockedError("one-use target must be absent under an owner-private directory")


def _publish(path: Path, record: dict[str, Any]) -> str:
    _private_parent(path)
    payload = json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
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


def _claim_record(stage: str, runner_sha256: str, state_sha256: str, expected_bundle_sha256: str) -> dict[str, Any]:
    return {
        "schema_version": "c3-policy-last-fomc-move-claim-v1",
        "research_id": RESEARCH_ID,
        "stage": stage,
        "claimed_at": datetime.now(timezone.utc).isoformat(),
        "definition_sha256": DEFINITION_SHA256,
        "adapter_sha256": ADAPTER_SHA256,
        "runner_sha256": runner_sha256,
        "official_policy_state_input_sha256": state_sha256,
        "accepted_xnys_calendar_sha256": CALENDAR_INPUT_SHA256,
        "expected_runtime_bundle_sha256": _sha256(expected_bundle_sha256, "expected runtime bundle SHA-256"),
        "one_use_execution_consumed": True,
        "rerun_authorized": False,
    }


def _result_record(
    stage: str,
    classification: str,
    *,
    claim_sha256: str,
    bundle_sha256: str | None,
    decision: dict[str, Any] | None,
    stage_hashes: tuple[str, ...] = (),
    error: Exception | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "c3-policy-last-fomc-move-result-v1",
        "research_id": RESEARCH_ID,
        "stage": stage,
        "classification": classification,
        "program_alpha": PROGRAM_ALPHA,
        "claim_sha256": claim_sha256,
        "runtime_bundle_sha256": bundle_sha256,
        "decision": decision,
        "stage_hashes": list(stage_hashes),
        "error_type": None if error is None else type(error).__name__,
        "error_message": None if error is None else str(error),
        "strategy_candidate_available": False,
        "shadow": False,
        "paper": False,
        "broker": False,
        "live": False,
        "rerun_authorized": False,
    }


def _stage(
    stage: str,
    bundle_path: Path,
    claim_path: Path,
    result_path: Path,
    *,
    runner_sha256: str,
    state_sha256: str,
    expected_bundle_sha256: str,
    official_states: dict[str, tuple[OfficialBoundary, ...]],
) -> dict[str, Any]:
    claim_sha = _publish(claim_path, _claim_record(stage, runner_sha256, state_sha256, expected_bundle_sha256))
    bundle_sha: str | None = None
    try:
        payload = _capture(bundle_path, expected_bundle_sha256, max_bytes=64 * 1024 * 1024)
        bundle_sha = _sha256_bytes(payload)
        bundle = _load_bundle(payload, stage=stage, official_states=official_states)
        strategy, spy, stage_hashes = _simulate(bundle)
        decision = _decision(stage, strategy, spy)
        classification = (
            "RETROSPECTIVE_SECONDARY_VALIDATION_PASS_HOLDOUT_UNLOCKED"
            if stage == "validation" and decision["all_gates_pass"]
            else "RETROSPECTIVE_SECONDARY_VALIDATION_FAIL"
            if stage == "validation"
            else "RETROSPECTIVE_SECONDARY_PASS_PENDING_EXTERNAL_REVIEW"
            if decision["all_gates_pass"]
            else "RETROSPECTIVE_SECONDARY_HOLDOUT_FAIL"
        )
        record = _result_record(stage, classification, claim_sha256=claim_sha, bundle_sha256=bundle_sha, decision=decision, stage_hashes=stage_hashes)
    except Exception as exc:
        record = _result_record(stage, "INPUT_BLOCKED_CLAIM_CONSUMED", claim_sha256=claim_sha, bundle_sha256=bundle_sha, decision=None, error=exc)
    _publish(result_path, record)
    return record


def execute_once() -> dict[str, Any]:
    if _file_sha256(DEFINITION) != DEFINITION_SHA256:
        raise InputBlockedError("definition bytes differ from the frozen identity")
    if _file_sha256(ADAPTER) != ADAPTER_SHA256:
        raise InputBlockedError("adapter bytes differ from the frozen identity")
    if _core_identity() != (CORE_SOURCE_FILE_COUNT, CORE_SOURCE_SHA256):
        raise InputBlockedError("shared-core bytes differ from the frozen identity")
    runner_sha = _file_sha256(RUNNER)
    state_payload = _capture(STATE_INPUT, STATE_INPUT_SHA256, max_bytes=8 * 1024 * 1024)
    state_sha = _sha256_bytes(state_payload)
    official_states = _load_official_states(state_payload)
    validation = _stage("validation", VALIDATION_BUNDLE, VALIDATION_CLAIM, VALIDATION_RESULT, runner_sha256=runner_sha, state_sha256=state_sha, expected_bundle_sha256=VALIDATION_BUNDLE_SHA256, official_states=official_states)
    if validation["classification"] != "RETROSPECTIVE_SECONDARY_VALIDATION_PASS_HOLDOUT_UNLOCKED":
        return validation
    return _stage("holdout", HOLDOUT_BUNDLE, HOLDOUT_CLAIM, HOLDOUT_RESULT, runner_sha256=runner_sha, state_sha256=state_sha, expected_bundle_sha256=HOLDOUT_BUNDLE_SHA256, official_states=official_states)


def main() -> int:
    record = execute_once()
    print(json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0 if record["classification"] != "INPUT_BLOCKED_CLAIM_CONSUMED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
