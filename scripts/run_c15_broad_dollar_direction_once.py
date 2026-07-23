"""One-use runner for the frozen Cycle 15 broad-dollar SPY/QQQ rotation lane."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import sys
from typing import Any
from zoneinfo import ZoneInfo


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
from research.adapters.c15_broad_dollar_direction import (  # noqa: E402
    HOLDOUT_INTERVALS,
    INITIAL_CAPITAL,
    PROGRAM_ALPHA,
    RESEARCH_ID,
    VALIDATION_INTERVALS,
    holdout_decision,
    validation_decision,
)


DEFINITION = ROOT / "research/definitions/c15_broad_dollar_direction_v1.json"
ADAPTER = ROOT / "research/adapters/c15_broad_dollar_direction.py"
RUNNER = Path(__file__).resolve()
DEFINITION_SHA256 = "7e48ec814331c3a57e71e8439b6bf6929b0338c188b212f877f799ab39d709c7"
ADAPTER_SHA256 = "46fdc46a7dd9a0acd93cf8accdd2dc897d874ede4b35b2d3af6bb6c9ec8939d7"
SIGNAL_SHA256 = "b6ebf7c4c4aea072930230f477c3e73767f0067352fa8ac0dcf10ea809fabcac"
RECEIPT_SHA256 = "237c7596d018f5dd26aa43eaea618cb754aec117f2f722365a5573fdc528551e"
VALIDATION_BUNDLE_SHA256 = "499157cd45b6402aabb8f786ae7e60f9c4bb55992e60bab8ff03f1104baa5b8a"
HOLDOUT_BUNDLE_SHA256 = "ff4b02932079ad013da05dbffcf2dd6e25af8592450e5b09e4a2f00d9f61f8d4"
CORE_SOURCE_FILE_COUNT = 23
CORE_SOURCE_SHA256 = "46ae2fe342a40034b9caacb6cc48a182947a49da9d874de31a1fdb60be0b9a80"
INCLUSION_RULE_SHA256 = "89483ee34a4b87fcdb728889dc31c7dc7222f85b3071ff7a97c65148e1b6402e"
SIGNAL_INPUT = Path(
    "/home/rongyu/workspace/quant-data/staging/"
    "c15_broad_dollar_direction_spy_qqq_rotation_v1/"
    "dollar_qqq_input_packet.json"
)
INPUT_RECEIPT = SIGNAL_INPUT.with_name("materialization_receipt.json")
SPY_ROOT = Path("/home/rongyu/workspace/quant-data/staging/us_fomc_policy_state_v2")
VALIDATION_BUNDLE = SPY_ROOT / "spy_validation_runtime_bundle_v2.json"
HOLDOUT_BUNDLE = SPY_ROOT / "spy_holdout_runtime_bundle_v2.json"
PRIVATE_ROOT = Path("/home/rongyu/workspace/quant-data/private_results")
VALIDATION_CLAIM = PRIVATE_ROOT / f"{RESEARCH_ID.lower()}_validation/claim.json"
VALIDATION_RESULT = VALIDATION_CLAIM.with_name("result.json")
HOLDOUT_CLAIM = PRIVATE_ROOT / f"{RESEARCH_ID.lower()}_holdout/claim.json"
HOLDOUT_RESULT = HOLDOUT_CLAIM.with_name("result.json")
ONE_WAY_SLIPPAGE_BPS = 10.0
QQQ_PRICE_URL = (
    "https://api.tiingo.com/tiingo/daily/QQQ/prices?"
    "startDate=1960-01-01&resampleFreq=daily"
)
QQQ_ACTION_URL = "https://api.nasdaq.com/api/quote/QQQ/dividends?assetclass=etf"
NY = ZoneInfo("America/New_York")


class InputBlockedError(ValueError):
    """Fail-closed identity, chronology, schema, or one-use error."""


@dataclass(frozen=True)
class Signal:
    stage: str
    start: date
    end: date
    signal_decision_at: datetime
    target_symbol: str
    selection_row_hash: str


@dataclass(frozen=True)
class Point:
    signal_session: date
    decision_at: datetime
    execution_session: date
    calendar: AcceptedSessionCalendar
    revision: AcceptedSessionCalendar | None
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


def _snapshot(row: object) -> UniverseSnapshotIdentity:
    if type(row) is not dict:
        raise InputBlockedError("universe snapshot must be an object")
    snapshot = UniverseSnapshotIdentity(
        row["market"],
        row["exchange_id"],
        _date(row["effective_session"], "effective_session"),
        row["member_count"],
        row["ordered_members_sha256"],
        row["lifecycle_coverage_sha256"],
        row["inclusion_rule_sha256"],
        row["calendar_identity_sha256"],
        _source(row["source_identity"]),
    )
    if (
        snapshot.market != "us"
        or snapshot.exchange_id != "XNYS"
        or snapshot.inclusion_rule_sha256 != INCLUSION_RULE_SHA256
    ):
        raise InputBlockedError("universe snapshot identity mismatch")
    return snapshot


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


def _signals(payload: bytes) -> dict[str, tuple[Signal, ...]]:
    record = _json(payload, "broad-dollar direction input packet")
    if (
        record.get("schema_version")
        != "c15-broad-dollar-direction-spy-qqq-input-packet-v1"
        or record.get("research_id") != RESEARCH_ID
        or record.get("strategy_outcomes_opened") is not False
        or record.get("spy_price_values_used_for_materialization") is not False
        or record.get("adjusted_prices_used") is not False
        or record.get("database_opened") is not False
        or record.get("database_write") is not False
    ):
        raise InputBlockedError("broad-dollar input packet boundary mismatch")
    rows = record.get("signals")
    if type(rows) is not list or len(rows) != VALIDATION_INTERVALS + HOLDOUT_INTERVALS:
        raise InputBlockedError("broad-dollar signal row count mismatch")
    parsed: dict[str, list[Signal]] = {"validation": [], "retrospective_holdout": []}
    for row in rows:
        if type(row) is not dict or row.get("stage") not in parsed:
            raise InputBlockedError("broad-dollar signal stage mismatch")
        identity = row.get("source_identity")
        if type(identity) is not dict:
            raise InputBlockedError("broad-dollar source identity is required")
        current = identity.get("reference_broad_dollar_index")
        prior = identity.get("prior_broad_dollar_index")
        change = row.get("monthly_change")
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            for value in (current, prior, change)
        ):
            raise InputBlockedError("broad-dollar values must be finite")
        if float(current) <= 0.0 or float(prior) <= 0.0:
            raise InputBlockedError("broad-dollar levels must be positive")
        expected_change = float(current) / float(prior) - 1.0
        if not math.isclose(float(change), expected_change, rel_tol=0, abs_tol=1e-15):
            raise InputBlockedError("broad-dollar change arithmetic mismatch")
        expected_state = "SPY" if float(current) > float(prior) else "QQQ"
        if row.get("state") != expected_state:
            raise InputBlockedError("broad-dollar state arithmetic mismatch")
        identity_hash = _hash_bytes(
            json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
        )
        parsed[row["stage"]].append(
            Signal(
                row["stage"],
                _date(row["holding_start_execution_session"], "holding start"),
                _date(row["holding_end_execution_session"], "holding end"),
                _datetime(row["decision_at"], "signal decision_at"),
                expected_state,
                _sha(row["row_sha256"], "broad-dollar row SHA-256"),
            )
        )
        if identity_hash != row["row_sha256"]:
            raise InputBlockedError("broad-dollar source identity hash mismatch")
    output = {key: tuple(value) for key, value in parsed.items()}
    if len(output["validation"]) != VALIDATION_INTERVALS or len(output["retrospective_holdout"]) != HOLDOUT_INTERVALS:
        raise InputBlockedError("broad-dollar signal split count mismatch")
    for group in output.values():
        if any(left.end != right.start for left, right in zip(group, group[1:], strict=False)):
            raise InputBlockedError("broad-dollar signal intervals are not contiguous")
    return output


def _spy_execution(
    row: object,
    statuses: tuple[StatusEvidence, ...],
    actions: tuple[CorporateActionIdentity, ...],
    *,
    signal_session: date,
    decision_at: datetime,
    calendar: AcceptedSessionCalendar,
) -> ExecutionInput:
    if type(row) is not dict:
        raise InputBlockedError("execution input must be an object")
    if row["symbol"] != "SPY" or row["market"] != "us" or row["currency"] != "USD":
        raise InputBlockedError("only the frozen US SPY execution input is allowed")
    if row["corporate_action_ids"] != [action.action_id for action in actions]:
        raise InputBlockedError("execution corporate-action mapping mismatch")
    expected_basis = "raw_pre_action_per_old_share" if actions else "raw_execution_units"
    decision_source = _source(row["decision_price_source"])
    price = row["decision_price"]
    raw_open = row["raw_open"]
    accepted_signal = calendar.session_on(signal_session, as_of=decision_at)
    execution_session = _date(row["session_date"], "execution session")
    accepted_execution = calendar.session_on(execution_session, as_of=decision_at)
    if (
        row["decision_price_basis"] != expected_basis
        or row["execution_price_basis"] != "retrospective_daily_bar_open_fill"
        or _date(row["decision_price_session"], "decision price session") != signal_session
        or _datetime(row["decision_price_effective_at"], "decision price effective_at") != accepted_signal.close_at
        or _datetime(row["execution_price_effective_at"], "execution price effective_at") != accepted_execution.open_at
        or decision_source.available_at > decision_at
        or any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0.0
            for value in (price, raw_open)
        )
    ):
        raise InputBlockedError("execution price or timing identity mismatch")
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
        execution_price_effective_at=_datetime(
            row["execution_price_effective_at"], "execution price effective_at"
        ),
        execution_price_basis=row["execution_price_basis"],
    )


def _qqq_lifecycle(
    packet: dict[str, Any], retrieved_at: datetime
) -> tuple[tuple[StatusEvidence, ...], SourceIdentity]:
    row = packet.get("qqq_lifecycle_evidence")
    if type(row) is not dict or row.get("ticker") != "QQQ":
        raise InputBlockedError("QQQ lifecycle evidence is missing")
    source = SourceIdentity(
        row["canonical_url"],
        _sha(row["record_sha256"], "QQQ lifecycle record SHA-256"),
        _datetime(row["normalized_available_at"], "QQQ lifecycle available_at"),
        retrieved_at,
        f"sec-{row['accession']}",
    )
    statuses = (
        StatusEvidence(
            "QQQ:listed",
            "QQQ",
            "listed",
            True,
            date(1999, 3, 10),
            None,
            "America/New_York",
            source,
        ),
        StatusEvidence(
            "QQQ:delisted",
            "QQQ",
            "delisted",
            False,
            date(1999, 3, 10),
            None,
            "America/New_York",
            source,
        ),
    )
    return statuses, source


def _qqq_actions(
    packet: dict[str, Any], retrieved_at: datetime
) -> tuple[CorporateActionIdentity, ...]:
    source_hash = _sha(
        packet["source_hashes"]["nasdaq_qqq_dividend_response_sha256"],
        "Nasdaq QQQ dividend SHA-256",
    )
    rows = packet.get("qqq_corporate_actions")
    if type(rows) is not list or len(rows) != 24:
        raise InputBlockedError("QQQ corporate-action count mismatch")
    actions: list[CorporateActionIdentity] = []
    for row in rows:
        ex_date = _date(row["ex_date"], "QQQ ex_date")
        available_at = datetime.combine(ex_date, time(0), tzinfo=NY)
        source = SourceIdentity(
            QQQ_ACTION_URL,
            source_hash,
            available_at,
            retrieved_at,
            f"nasdaq-qqq-dividend-{ex_date.isoformat()}",
        )
        actions.append(
            CorporateActionIdentity(
                "QQQ",
                f"QQQ:cash_dividend:{ex_date.isoformat()}",
                "cash_dividend",
                available_at,
                source,
                "America/New_York",
                ex_date=ex_date,
                record_date=_date(row["record_date"], "QQQ record_date"),
                pay_date=_date(row["pay_date"], "QQQ pay_date"),
                cash_amount=Decimal(str(row["cash_amount"])),
                currency="USD",
                unit="per_share",
            )
        )
    if len({action.action_id for action in actions}) != len(actions):
        raise InputBlockedError("QQQ corporate-action IDs must be unique")
    return tuple(actions)


def _qqq_execution(
    row: dict[str, Any],
    statuses: tuple[StatusEvidence, ...],
    actions: tuple[CorporateActionIdentity, ...],
    *,
    signal_session: date,
    decision_at: datetime,
    calendar: AcceptedSessionCalendar,
    tiingo_sha: str,
    retrieved_at: datetime,
) -> ExecutionInput:
    execution_session = _date(row["execution_session"], "QQQ execution session")
    if (
        row.get("signal_session") != signal_session.isoformat()
        or _datetime(row["decision_at"], "QQQ decision_at") != decision_at
        or row.get("stage") not in {"validation", "retrospective_holdout"}
    ):
        raise InputBlockedError("QQQ boundary does not bind the SPY schedule")
    accepted_signal = calendar.session_on(signal_session, as_of=decision_at)
    accepted_execution = calendar.session_on(execution_session, as_of=decision_at)
    decision_price = row.get("decision_price")
    raw_open = row.get("raw_open")
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) <= 0.0
        for value in (decision_price, raw_open)
    ):
        raise InputBlockedError("QQQ boundary price is invalid")
    decision_source = SourceIdentity(
        QQQ_PRICE_URL,
        tiingo_sha,
        accepted_signal.close_at + timedelta(hours=4),
        retrieved_at,
        f"tiingo-qqq-close-{signal_session.isoformat()}",
    )
    execution_source = SourceIdentity(
        QQQ_PRICE_URL,
        tiingo_sha,
        accepted_execution.close_at + timedelta(hours=4),
        retrieved_at,
        f"tiingo-qqq-open-{execution_session.isoformat()}",
    )
    if decision_source.available_at > decision_at:
        raise InputBlockedError("QQQ decision price is not available before decision")
    return ExecutionInput(
        "QQQ",
        "us",
        float(raw_open),
        "USD",
        execution_source,
        statuses,
        corporate_actions=actions,
        decision_price=float(decision_price),
        decision_price_source=decision_source,
        decision_price_basis=(
            "raw_pre_action_per_old_share" if actions else "raw_execution_units"
        ),
        execution_price_effective_at=accepted_execution.open_at,
        execution_price_basis="retrospective_daily_bar_open_fill",
    )


def _combined_snapshot(
    spy_snapshot: UniverseSnapshotIdentity,
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
    sources = tuple(row.status_records[0].source for row in executions)
    available_at = max(source.available_at for source in sources)
    retrieved_at = max(source.retrieved_at for source in sources)
    source_hash = _hash_bytes(
        json.dumps(
            {
                "members": members,
                "source_hashes": sorted(source.content_sha256 for source in sources),
                "spy_snapshot_source_hash": spy_snapshot.source_identity.content_sha256,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    )
    source = SourceIdentity(
        "https://www.sec.gov/Archives/edgar/data/1067839/000119312520018563/d835635d485bpos.htm",
        source_hash,
        available_at,
        retrieved_at,
        f"c15-spy-qqq-universe-{execution_session.isoformat()}",
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
    input_payload: bytes,
    receipt_payload: bytes,
    *,
    stage: str,
    signals: tuple[Signal, ...],
) -> Bundle:
    record = _json(payload, "SPY runtime bundle")
    packet = _json(input_payload, "broad-dollar/QQQ input packet")
    receipt = _json(receipt_payload, "broad-dollar/QQQ materialization receipt")
    retrieved_at = _datetime(receipt["created_at"], "input receipt created_at")
    if (
        packet.get("research_id") != RESEARCH_ID
        or receipt.get("research_id") != RESEARCH_ID
        or receipt.get("input_packet_sha256") != SIGNAL_SHA256
        or receipt.get("status") != "INPUT_MATERIALIZED_STATE_SUPPORT_PASS"
    ):
        raise InputBlockedError("input packet and receipt binding mismatch")
    raw_qqq_boundaries = packet.get("qqq_boundary_rows", {}).get(stage)
    expected_qqq_boundaries = 29 if stage == "validation" else 35
    if type(raw_qqq_boundaries) is not list or len(raw_qqq_boundaries) != expected_qqq_boundaries:
        raise InputBlockedError("QQQ boundary count mismatch")
    qqq_boundaries = {row["execution_session"]: row for row in raw_qqq_boundaries}
    if len(qqq_boundaries) != expected_qqq_boundaries:
        raise InputBlockedError("QQQ boundary sessions must be unique")
    qqq_statuses, _ = _qqq_lifecycle(packet, retrieved_at)
    qqq_all_actions = _qqq_actions(packet, retrieved_at)
    tiingo_sha = _sha(
        packet["source_hashes"]["tiingo_qqq_raw_sha256"],
        "Tiingo QQQ SHA-256",
    )
    expected_points = 30 if stage == "validation" else 36
    if (
        record.get("schema_version") != "c3-policy-last-fomc-move-runtime-v1"
        or record.get("stage") != stage
        or record.get("symbol") != "SPY"
        or type(record.get("execution_points")) is not list
        or len(record["execution_points"]) != expected_points
    ):
        raise InputBlockedError("SPY runtime bundle identity mismatch")
    reconstruction = _calendar(record["reconstruction_calendar"])
    epoch_rows = record["calendar_epochs"]
    if type(epoch_rows) is not dict or not epoch_rows:
        raise InputBlockedError("calendar epochs are required")
    epochs = {key: _calendar(value) for key, value in epoch_rows.items()}
    spy_actions = tuple(_action(value) for value in record["corporate_actions"])
    all_actions = spy_actions + qqq_all_actions
    if len({action.action_id for action in all_actions}) != len(all_actions):
        raise InputBlockedError("corporate action identities must be unique")
    raw_points = record["execution_points"][1:]
    if len(raw_points) != len(signals) + 1:
        raise InputBlockedError("selected SPY boundary count mismatch")
    points: list[Point] = []
    for index, raw in enumerate(raw_points):
        if type(raw) is not dict:
            raise InputBlockedError("execution point must be an object")
        execution_session = _date(raw["execution_session"], "execution session")
        decision_at = _datetime(raw["decision_at"], "decision_at")
        signal_session = _date(raw["signal_session"], "signal session")
        signal = None if index == len(signals) else signals[index]
        if signal is not None and (
            signal.start != execution_session
            or signal.end != _date(raw_points[index + 1]["execution_session"], "next execution session")
            or signal.signal_decision_at != decision_at
        ):
            raise InputBlockedError(
                "broad-dollar signal does not bind the execution schedule"
            )
        try:
            calendar = epochs[raw["decision_calendar_epoch_id"]]
            revision_id = raw["execution_calendar_revision_id"]
            revision = None if revision_id is None else epochs[revision_id]
        except KeyError as exc:
            raise InputBlockedError("unknown calendar epoch") from exc
        if calendar.next_session(signal_session, as_of=decision_at).session_date != execution_session:
            raise InputBlockedError("execution is not the next accepted session")
        spy_point_actions = tuple(
            action
            for action in spy_actions
            if action.effective_date == execution_session
        )
        qqq_point_actions = tuple(
            action
            for action in qqq_all_actions
            if action.effective_date == execution_session
        )
        spy_statuses = tuple(_status(value) for value in raw["status_evidence"])
        spy_execution = _spy_execution(
            raw["execution"],
            spy_statuses,
            spy_point_actions,
            signal_session=signal_session,
            decision_at=decision_at,
            calendar=calendar,
        )
        try:
            qqq_row = qqq_boundaries[execution_session.isoformat()]
        except KeyError as exc:
            raise InputBlockedError("QQQ execution boundary is missing") from exc
        qqq_execution = _qqq_execution(
            qqq_row,
            qqq_statuses,
            qqq_point_actions,
            signal_session=signal_session,
            decision_at=decision_at,
            calendar=calendar,
            tiingo_sha=tiingo_sha,
            retrieved_at=retrieved_at,
        )
        spy_snapshot = _snapshot(raw["universe_snapshot"])
        if spy_snapshot.effective_session != execution_session:
            raise InputBlockedError("universe snapshot session mismatch")
        executions = (qqq_execution, spy_execution)
        snapshot = _combined_snapshot(
            spy_snapshot,
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
                revision,
                executions,
                snapshot,
                None if signal is None else signal.target_symbol,
            )
        )
    if (
        any(point.target_symbol is None for point in points[:-1])
        or points[-1].target_symbol is not None
    ):
        raise InputBlockedError("only the final selected boundary may be terminal")
    raw_daily = record["daily_sessions"]
    if type(raw_daily) is not list:
        raise InputBlockedError("daily sessions must be a list")
    selected_start, selected_end = points[0].execution_session, points[-1].execution_session
    daily = tuple(
        day
        for value in raw_daily
        for day in (_date(value, "daily session"),)
        if selected_start <= day <= selected_end
    )
    expected_daily = tuple(
        day
        for day in reconstruction.session_dates
        if selected_start <= day <= selected_end
    )
    if daily != expected_daily:
        raise InputBlockedError("daily session coverage is incomplete")
    actions = tuple(
        action for action in all_actions if selected_start <= action.effective_date <= selected_end
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
            raise InputBlockedError("unsupported SPY/QQQ corporate action")


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
        execution_calendar_revision=point.revision,
        universe_members=("QQQ", "SPY"),
        universe_snapshot=point.snapshot,
        target_weights=lambda context: dict(weights),
        strategy_definition_sha256=DEFINITION_SHA256,
        strategy_adapter_sha256=ADAPTER_SHA256,
        slippage_bps=ONE_WAY_SLIPPAGE_BPS,
        prior_stage_hash=prior_stage_hash,
    )


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
        if point.target_symbol is None:
            strategy_result = _rebalance(strategy, point, {}, strategy_stage)
            benchmark_result = _rebalance(benchmark, point, {}, benchmark_stage)
            strategy, benchmark = strategy_result.portfolio, benchmark_result.portfolio
            strategy_navs.append(strategy_result.final_nav)
            benchmark_navs.append(benchmark_result.final_nav)
            stage_hashes.extend((strategy_result.stage_hash, benchmark_result.stage_hash))
            continue
        strategy_result = _rebalance(
            strategy,
            point,
            {point.target_symbol: 1.0},
            strategy_stage,
        )
        strategy, strategy_stage = strategy_result.portfolio, strategy_result.stage_hash
        stage_hashes.append(strategy_stage)
        benchmark_result = _rebalance(
            benchmark,
            point,
            {"QQQ": 0.5, "SPY": 0.5},
            benchmark_stage,
        )
        benchmark, benchmark_stage = (
            benchmark_result.portfolio,
            benchmark_result.stage_hash,
        )
        stage_hashes.append(benchmark_stage)
        if point is bundle.points[0]:
            continue
        strategy_navs.append(strategy_result.final_nav)
        benchmark_navs.append(benchmark_result.final_nav)
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
        raise InputBlockedError("one-use target must be absent under an owner-private directory")


def _publish(path: Path, record: dict[str, Any]) -> str:
    _private_parent(path)
    payload = json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
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


def _claim(stage: str, runner_sha: str, bundle_sha: str, validation_result_sha: str | None) -> dict[str, Any]:
    return {
        "schema_version": "c15-broad-dollar-direction-claim-v1",
        "research_id": RESEARCH_ID,
        "stage": stage,
        "claimed_at": datetime.now(timezone.utc).isoformat(),
        "definition_sha256": DEFINITION_SHA256,
        "adapter_sha256": ADAPTER_SHA256,
        "runner_sha256": runner_sha,
        "input_packet_sha256": SIGNAL_SHA256,
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
        "schema_version": "c15-broad-dollar-direction-result-v1",
        "research_id": RESEARCH_ID,
        "stage": stage,
        "classification": classification,
        "program_alpha": PROGRAM_ALPHA,
        "definition_sha256": DEFINITION_SHA256,
        "adapter_sha256": ADAPTER_SHA256,
        "runner_sha256": runner_sha,
        "input_packet_sha256": SIGNAL_SHA256,
        "claim_sha256": claim_sha,
        "runtime_bundle_sha256": bundle_sha,
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


def _accepted_validation_result() -> str:
    payload = _capture(VALIDATION_RESULT, _file_hash(VALIDATION_RESULT), max_bytes=2 * 1024 * 1024)
    record = _json(payload, "validation result")
    if (
        record.get("research_id") != RESEARCH_ID
        or record.get("stage") != "validation"
        or record.get("classification")
        != "RETROSPECTIVE_SECONDARY_VALIDATION_PASS_HOLDOUT_UNLOCKED"
        or record.get("definition_sha256") != DEFINITION_SHA256
        or record.get("adapter_sha256") != ADAPTER_SHA256
        or record.get("input_packet_sha256") != SIGNAL_SHA256
        or record.get("decision", {}).get("all_gates_pass") is not True
    ):
        raise InputBlockedError("holdout remains sealed by the validation result")
    return _hash_bytes(payload)


def execute_stage(stage: str) -> dict[str, Any]:
    if stage not in {"validation", "holdout"}:
        raise InputBlockedError("stage must be validation or holdout")
    if _file_hash(DEFINITION) != DEFINITION_SHA256:
        raise InputBlockedError("definition bytes differ from the frozen identity")
    if _file_hash(ADAPTER) != ADAPTER_SHA256:
        raise InputBlockedError("adapter bytes differ from the frozen identity")
    if _core_identity() != (CORE_SOURCE_FILE_COUNT, CORE_SOURCE_SHA256):
        raise InputBlockedError("shared-core bytes differ from the frozen identity")
    definition = _json(_capture(DEFINITION, DEFINITION_SHA256, max_bytes=256 * 1024), "definition")
    if (
        definition.get("research_id") != RESEARCH_ID
        or definition.get("program_multiplicity", {}).get("sole_primary_alpha") != PROGRAM_ALPHA
        or definition.get("source_identities", {}).get("adapter_sha256") != ADAPTER_SHA256
        or definition.get("boundaries", {}).get("strategy_candidate_available") is not False
    ):
        raise InputBlockedError("definition semantic identity mismatch")
    runner_sha = _file_hash(RUNNER)
    validation_result_sha = None
    if stage == "validation":
        if any(path.exists() for path in (VALIDATION_CLAIM, VALIDATION_RESULT, HOLDOUT_CLAIM, HOLDOUT_RESULT)):
            raise InputBlockedError("Cycle 15 one-use state is not pristine")
        bundle_path, expected_bundle = VALIDATION_BUNDLE, VALIDATION_BUNDLE_SHA256
        claim_path, result_path = VALIDATION_CLAIM, VALIDATION_RESULT
        signal_stage = "validation"
    else:
        if HOLDOUT_CLAIM.exists() or HOLDOUT_RESULT.exists():
            raise InputBlockedError("Cycle 15 holdout one-use state is not pristine")
        validation_result_sha = _accepted_validation_result()
        bundle_path, expected_bundle = HOLDOUT_BUNDLE, HOLDOUT_BUNDLE_SHA256
        claim_path, result_path = HOLDOUT_CLAIM, HOLDOUT_RESULT
        signal_stage = "retrospective_holdout"
    claim_sha = _publish(
        claim_path,
        _claim(stage, runner_sha, expected_bundle, validation_result_sha),
    )
    observed_bundle_sha: str | None = None
    try:
        input_payload = _capture(
            SIGNAL_INPUT,
            SIGNAL_SHA256,
            max_bytes=2 * 1024 * 1024,
        )
        receipt_payload = _capture(
            INPUT_RECEIPT,
            RECEIPT_SHA256,
            max_bytes=256 * 1024,
        )
        signals = _signals(input_payload)
        stage_signals = signals[signal_stage]
        bundle_payload = _capture(bundle_path, expected_bundle, max_bytes=64 * 1024 * 1024)
        observed_bundle_sha = _hash_bytes(bundle_payload)
        bundle = _load_bundle(
            bundle_payload,
            input_payload,
            receipt_payload,
            stage=stage,
            signals=stage_signals,
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
