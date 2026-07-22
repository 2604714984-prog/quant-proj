"""One-use staged runner for the frozen M119-03 term-spread state."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import stat
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

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
from quant_system.paths import AppPaths  # noqa: E402
from research.adapters.us_spy_h15_10y3m_state import (  # noqa: E402
    INFERENCE_COHORTS,
    INITIAL_CAPITAL,
    MECHANISM_ID,
    ONE_WAY_SLIPPAGE_BPS,
    PROGRAM_ALPHA,
    PROGRAM_FAMILY_ID,
    RateObservation,
    inference_decision,
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
CORE_SOURCE_FILE_COUNT = 23
CORE_SOURCE_SHA256 = "46ae2fe342a40034b9caacb6cc48a182947a49da9d874de31a1fdb60be0b9a80"
SCREEN_A_DEFINITION_SHA256 = (
    "d33d7143c982f178308f165de5f42c99ce773642e2e36897490de0504bf58d20"
)
SCREEN_A_ADAPTER_SHA256 = (
    "084f7ce73884786ea7d7dbb9cfcd702b735883b671ce59a3678a569110cd6999"
)
SCREEN_A_RUNNER_SHA256 = (
    "f7200cd0d9aafa2f20fac353845746802e3f2592940f29b31d96222d9be1f2ad"
)
SCREEN_A_PRIVATE_RESULT_SHA256 = (
    "bb9ec3c4dffda8d02ed401f1f91f03e6ff9987d6ca4259ccf4b4d59cfc8f4ae6"
)
SCREEN_A_CLAIM_SHA256 = (
    "962d97a029a1f0c1c0416fcdee1a71d8ccca75be998d62345c3c55a2da475053"
)
SCREEN_A_PUBLIC_REPORT_SHA256 = (
    "40af63646f096d8b472ffc94147e62636138796e56b5e3ebad012b7a89933fa4"
)
PRIOR_TERMINAL_REPORT_SHA256 = (
    "d5ee84c3e7605db3d5221d09e228c557d6b9dc0073f9968813c136042dd21d51"
)
CONTINUATION_1_AUTHORIZATION_REPORT_SHA256 = (
    "594d031efb80e233ae653120045639310e9670e29c11902117cdad8fd64c85e3"
)
PRIOR_CONTINUATION_1_CLAIM_SHA256 = (
    "f8aeb6c0b27a455c3e011d40ed3aaf80b0e069fbc65ec3802323e59b4704a713"
)
PRIOR_CONTINUATION_1_RESULT_SHA256 = (
    "b51d47e41841957b58c7182d5f3e54e299043e7cce127437c239ade7fcd2633f"
)
INFERENCE_B_DEFINITION_SHA256 = (
    "73d599bd2b01c9aacdf14d50836f489ad26e192db9d26c89db363f8a169d113f"
)
INFERENCE_B_BUNDLE_SHA256 = (
    "95217d01da3d11e6e1ee5d312d1c533210e45558a7421e5c2a8bb30058be2ed5"
)
INFERENCE_B_H15_SHA256 = (
    "f3aaa554282a4f011db6f8f656c2cd01dcc11675ce75c2736c13efd880e3b375"
)
INFERENCE_B_H15_SELECTION_QUERY_SHA256 = (
    "82a385452e36159e2fe96b7b725ce8078481f185fad6a7bf8474f7dbf9ccb12a"
)
INFERENCE_B_DATABASE_SHA256 = (
    "4e7bd0792241087c7c4da05de32b75a7450baa1dda0342a326ef4c02aa42a92e"
)
ACTION_RETRIEVED_AT = datetime.fromisoformat("2026-07-21T08:13:17.580138+00:00")
DEFINITION = ROOT / "research" / "definitions" / "us_spy_h15_10y3m_state_v1.json"
SCREEN_A_PUBLIC_REPORT = ROOT / "research" / "reports" / "us_spy_h15_10y3m_state_v1.json"
ADAPTER = ROOT / "research" / "adapters" / "us_spy_h15_10y3m_state.py"
RUNNER = Path(__file__).resolve()
DATA_ROOT = AppPaths.discover(project_root=ROOT, environ={}).data_root
SCREEN_A_PRIVATE_RESULT_RELATIVE = Path(
    "private_results/us_spy_h15_10y3m_state_v1_screen_a_44bcd9a1/result.json"
)
INFERENCE_B_BUNDLE_RELATIVE = Path(
    "staging/us_spy_h15_10y3m_state_v1_technical_continuation_1/"
    "us_spy_h15_inference_b_runtime_input_v1.json"
)
INFERENCE_B_H15_RELATIVE = Path(
    "staging/us_spy_h15_10y3m_state_v1_technical_continuation_1/"
    "h15_inference_b_signal_input_v1.json"
)
INFERENCE_B_CLAIM_RELATIVE = Path(
    "private_results/us_spy_h15_10y3m_state_v1_inference_b_technical_continuation_2/"
    "claim.json"
)
SCREEN_A_PRIVATE_RESULT = DATA_ROOT / SCREEN_A_PRIVATE_RESULT_RELATIVE
INFERENCE_B_BUNDLE = DATA_ROOT / INFERENCE_B_BUNDLE_RELATIVE
INFERENCE_B_H15 = DATA_ROOT / INFERENCE_B_H15_RELATIVE
INFERENCE_B_CLAIM = DATA_ROOT / INFERENCE_B_CLAIM_RELATIVE
INFERENCE_B_RESULT = INFERENCE_B_CLAIM.with_name("result.json")
INFERENCE_B_RESULT_RELATIVE = INFERENCE_B_CLAIM_RELATIVE.with_name("result.json")
_NEW_YORK = ZoneInfo("America/New_York")
ENTRY_MONTHS = tuple(
    (year, month)
    for year in range(2018, 2022)
    for month in range(1, 13)
    if (2018, 3) <= (year, month) <= (2021, 11)
)
SIGNAL_MONTHS = tuple(
    (year, month)
    for year in range(2018, 2022)
    for month in range(1, 13)
    if (2018, 2) <= (year, month) <= (2021, 11)
)
INFERENCE_ENTRY_MONTHS = tuple(
    (year, month)
    for year in range(2022, 2027)
    for month in range(1, 13)
    if (2022, 1) <= (year, month) <= (2026, 5)
)
INFERENCE_SIGNAL_MONTHS = tuple(
    (year, month)
    for year in range(2021, 2027)
    for month in range(1, 13)
    if (2021, 12) <= (year, month) <= (2026, 5)
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


def _core_source_identity() -> tuple[int, str]:
    entries = []
    for path in sorted((ROOT / "src" / "quant_system").rglob("*.py")):
        if path.is_symlink() or not path.is_file():
            raise InputBlockedError("shared-core source must use regular Python files")
        entries.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": _file_sha256(path),
            }
        )
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    return len(entries), _sha256_bytes(payload)


def _require_core_identity() -> None:
    if _core_source_identity() != (CORE_SOURCE_FILE_COUNT, CORE_SOURCE_SHA256):
        raise InputBlockedError("shared-core source bytes differ from the frozen identity")


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
    external_market = row["market"]
    if external_market != "US":
        raise InputBlockedError("external market identity must be exact US")
    return ExecutionInput(
        row["symbol"],
        "us",
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


def _require_stage_schedule(
    frozen: tuple[Point, ...],
    *,
    entry_months: tuple[tuple[int, int], ...],
    signal_months: tuple[tuple[int, int], ...],
    terminal_month: tuple[int, int],
) -> None:
    if len(frozen) != len(entry_months) + 1 or sum(
        point.terminal_exit for point in frozen
    ) != 1:
        raise InputBlockedError("SPY bundle entry/terminal dimensions mismatch")
    if tuple(
        (point.execution_session.year, point.execution_session.month)
        for point in frozen[:-1]
    ) != entry_months:
        raise InputBlockedError("entry months are incomplete or reordered")
    if len(signal_months) != len(frozen) or tuple(
        (point.signal_session.year, point.signal_session.month) for point in frozen
    ) != signal_months:
        raise InputBlockedError("signal months are incomplete or reordered")
    if (frozen[-1].execution_session.year, frozen[-1].execution_session.month) != (
        terminal_month
    ):
        raise InputBlockedError("terminal exit month mismatch")
    if frozen[-1].terminal_exit is not True or any(point.terminal_exit for point in frozen[:-1]):
        raise InputBlockedError("terminal-exit flags are invalid")
    for point in frozen:
        local_decision = point.decision_at.astimezone(_NEW_YORK)
        if local_decision.date() != point.signal_session or local_decision.time() != time(20, 5):
            raise InputBlockedError("decision time is not the frozen signal-session 20:05 ET")
        same_month = tuple(
            session
            for session in point.calendar.session_dates
            if (session.year, session.month)
            == (point.signal_session.year, point.signal_session.month)
        )
        if not same_month or same_month[-1] != point.signal_session:
            raise InputBlockedError("signal session is not the final accepted session of its month")
        if (
            point.calendar.next_session(point.signal_session, as_of=point.decision_at).session_date
            != point.execution_session
        ):
            raise InputBlockedError("execution is not the next accepted session after the signal")


def _load_bundle(
    payload: bytes,
    *,
    schema_version: str = "us-spy-vol-managed-validation-runtime-input-v1",
    stage: str = "validation",
    query_start: str = "2018-01-02",
    query_end: str = "2021-12-01",
    entry_months: tuple[tuple[int, int], ...] = ENTRY_MONTHS,
    signal_months: tuple[tuple[int, int], ...] = SIGNAL_MONTHS,
    terminal_month: tuple[int, int] = (2021, 12),
    reconstruction_session_count: int = 987,
    calendar_epoch_count: int = 3,
    action_count: int = 15,
) -> tuple[
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
        schema_version,
        stage,
        "SPY",
        query_start,
        query_end,
    ):
        raise InputBlockedError("SPY bundle fixed identity mismatch")
    reconstruction = _calendar(record["reconstruction_calendar"])
    if len(reconstruction.session_dates) != reconstruction_session_count:
        raise InputBlockedError("reconstruction calendar session count mismatch")
    epoch_rows = record["calendar_epochs"]
    if type(epoch_rows) is not dict or len(epoch_rows) != calendar_epoch_count:
        raise InputBlockedError("calendar epochs are incomplete")
    epochs = tuple(_calendar(epoch_rows[key]) for key in sorted(epoch_rows))
    by_revision = {item.identity.source_identity.revision_id: item for item in epochs}
    if len(by_revision) != calendar_epoch_count:
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
    _require_stage_schedule(
        frozen,
        entry_months=entry_months,
        signal_months=signal_months,
        terminal_month=terminal_month,
    )

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
    if len(actions) != action_count:
        raise InputBlockedError("cash-distribution count mismatch")
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


def _load_h15(
    payload: bytes,
    points: tuple[Point, ...],
    *,
    schema_version: str = "us-spy-h15-10y3m-state-v1",
    stage: str = "validation_input",
    spy_bundle_sha256: str = BASE_BUNDLE_SHA256,
    row_count: int = 45,
    selection_query_sha256: str = H15_SELECTION_QUERY_SHA256,
    database_sha256: str = "4e7bd0792241087c7c4da05de32b75a7450baa1dda0342a326ef4c02aa42a92e",
    bundle_hash_field: str = "spy_bundle_sha256",
) -> tuple[float, ...]:
    record = _json(payload, "H.15 input")
    expected_top = {
        "schema_version": schema_version,
        "stage": stage,
        "source_table": "us_macro_research.alfred_h15_yield_observations_research",
        "source_class": "OFFICIAL_ALFRED_H15",
        "row_count": row_count,
        "response_set_sha256": "338a8da0720f16045cd3325a5dc07241292c149e836bce1149af3de8bb97cc14",
        "db_postwrite_sha256": database_sha256,
    }
    if any(record.get(key) != value for key, value in expected_top.items()):
        raise InputBlockedError("H.15 top-level identity mismatch")
    if record.get(bundle_hash_field) != spy_bundle_sha256:
        raise InputBlockedError("H.15 runtime-bundle identity mismatch")
    if record.get("raw_response_sha256") != {
        "DGS10": "b59608fa97f00d945292ea77472079d419eee582b0a5ee5af4a2dfa3f5a2f55c",
        "DGS3MO": "6ec27c0460be9365e3648d3f1ed10e4af685aaf232065c1ae19d67cd70766fcf",
    }:
        raise InputBlockedError("H.15 raw response identity mismatch")
    if record.get("selection_proof") != {
        "algorithm_id": "ALFRED_H15_LATEST_COMMON_ELIGIBLE_OBSERVATION_V1",
        "query_sha256": selection_query_sha256,
        "replayed_db_sha256": expected_top["db_postwrite_sha256"],
        "decisions_verified": row_count,
        "mismatch_count": 0,
        "later_eligible_common_count": 0,
    }:
        raise InputBlockedError("H.15 latest-common selection proof mismatch")
    rows = record.get("rows")
    if type(rows) is not list or len(rows) != row_count:
        raise InputBlockedError("H.15 input row count mismatch")
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
    if len(weights) not in {45, INFERENCE_COHORTS} or len(points) != len(weights) + 1:
        raise InputBlockedError("stage target-weight dimensions are invalid")
    point_by_date = {point.execution_session: point for point in points}
    if len(point_by_date) != len(points):
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
    expected_boundaries = len(weights) + 1
    if len(strategy_navs) != expected_boundaries or len(benchmark_navs) != (
        expected_boundaries
    ):
        raise InputBlockedError("stage boundary path is incomplete")
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


def _hex_floats(values: object, field: str, expected: int) -> tuple[float, ...]:
    if type(values) is not list or len(values) != expected:
        raise InputBlockedError(f"{field} dimensions mismatch")
    parsed: list[float] = []
    for value in values:
        if type(value) is not str:
            raise InputBlockedError(f"{field} must contain hexadecimal floats")
        try:
            number = float.fromhex(value)
        except ValueError as exc:
            raise InputBlockedError(f"{field} contains an invalid hexadecimal float") from exc
        if not math.isfinite(number) or number <= 0.0:
            raise InputBlockedError(f"{field} must contain positive finite NAVs")
        parsed.append(number)
    return tuple(parsed)


def _require_screen_a_unlocked(payload: bytes) -> None:
    record = _json(payload, "Screen-A private result")
    expected_top = {
        "schema_version": "us-spy-h15-10y3m-state-screen-a-private-result-v1",
        "research_id": "US_SPY_H15_10Y3M_STATE_V1",
        "mechanism_id": MECHANISM_ID,
        "program_family_id": PROGRAM_FAMILY_ID,
        "program_alpha": PROGRAM_ALPHA,
        "stage": "RETROSPECTIVE_SECONDARY_SCREEN_A",
        "classification": "RETROSPECTIVE_SECONDARY_SCREEN_A_PASS_INFERENCE_B_UNLOCKED",
        "observed_cohorts": 45,
        "one_use_execution_consumed": True,
        "rerun_authorized": False,
        "inference_b_opened": False,
        "strategy_candidate_available": False,
        "shadow": False,
        "paper": False,
        "broker": False,
        "live": False,
    }
    if any(record.get(key) != value for key, value in expected_top.items()):
        raise InputBlockedError("Screen-A unlock receipt fields mismatch")
    expected_identity = {
        "definition_sha256": SCREEN_A_DEFINITION_SHA256,
        "adapter_sha256": SCREEN_A_ADAPTER_SHA256,
        "runner_sha256": SCREEN_A_RUNNER_SHA256,
        "base_bundle_sha256": BASE_BUNDLE_SHA256,
        "h15_input_sha256": H15_INPUT_SHA256,
        "core_commit": CORE_COMMIT,
        "core_tree": CORE_TREE,
        "core_source_sha256": CORE_SOURCE_SHA256,
        "claim_sha256": SCREEN_A_CLAIM_SHA256,
    }
    if record.get("identity") != expected_identity:
        raise InputBlockedError("Screen-A unlock identity mismatch")
    strategy_navs = _hex_floats(
        record.get("strategy_boundary_navs_hex"), "strategy Screen-A NAVs", 46
    )
    benchmark_navs = _hex_floats(
        record.get("benchmark_boundary_navs_hex"), "benchmark Screen-A NAVs", 46
    )
    decision = screen_decision(strategy_navs, benchmark_navs)
    if not decision.all_gates_pass or record.get("gates") != dict(decision.gates):
        raise InputBlockedError("Screen-A gates do not recompute to all true")
    if record.get("strategy_metrics_hex") != {
        key: float(value).hex() for key, value in vars(decision.strategy).items()
    } or record.get("benchmark_metrics_hex") != {
        key: float(value).hex() for key, value in vars(decision.benchmark).items()
    }:
        raise InputBlockedError("Screen-A metrics do not recompute exactly")
    if record.get("sharpe_difference_hex") != float(decision.sharpe_difference).hex():
        raise InputBlockedError("Screen-A Sharpe difference does not recompute exactly")
    if _file_sha256(SCREEN_A_PUBLIC_REPORT) != PRIOR_TERMINAL_REPORT_SHA256:
        raise InputBlockedError("prior terminal report identity mismatch")


def _require_inference_contract(payload: bytes, adapter_sha256: str) -> None:
    record = _json(payload, "Inference-B definition")
    if (
        record.get("schema_version"),
        record.get("research_id"),
        record.get("mechanism_id"),
        record.get("status"),
        record.get("strategy_candidate_available"),
    ) != (
        "us-spy-h15-10y3m-state-prereg-v1",
        "US_SPY_H15_10Y3M_STATE_V1",
        MECHANISM_ID,
        "PREREGISTERED_NOT_EXECUTED",
        False,
    ):
        raise InputBlockedError("Inference-B definition identity mismatch")
    freeze = record.get("inference_b_execution_freeze")
    if type(freeze) is not dict or set(freeze) != {
        "lineage",
        "paths",
        "stage_contract",
        "bootstrap_contract",
        "input_identities",
        "implementation",
        "terminal_rules",
        "boundaries",
    }:
        raise InputBlockedError("Inference-B execution-freeze fields drifted")
    if freeze.get("lineage") != {
        "parent_definition_sha256": SCREEN_A_DEFINITION_SHA256,
        "screen_a_execution_commit": "44bcd9a1ffcd78db030d1bbf5de21b4f72c5c532",
        "screen_a_private_result_sha256": SCREEN_A_PRIVATE_RESULT_SHA256,
        "screen_a_claim_sha256": SCREEN_A_CLAIM_SHA256,
        "screen_a_public_report_sha256": SCREEN_A_PUBLIC_REPORT_SHA256,
    }:
        raise InputBlockedError("Inference-B lineage identity mismatch")
    if freeze.get("paths") != {
        "screen_a_private_result": str(SCREEN_A_PRIVATE_RESULT_RELATIVE),
        "runtime_bundle": str(INFERENCE_B_BUNDLE_RELATIVE),
        "h15_input": str(INFERENCE_B_H15_RELATIVE),
        "claim": str(INFERENCE_B_CLAIM_RELATIVE),
        "result": str(INFERENCE_B_RESULT_RELATIVE),
    }:
        raise InputBlockedError("Inference-B canonical paths mismatch")
    if freeze.get("stage_contract") != {
        "label": "RETROSPECTIVE_SECONDARY_INFERENCE_B",
        "entry_months": "2022-01 through 2026-05 inclusive",
        "signal_months": "2021-12 through 2026-04 inclusive",
        "terminal_signal_month": "2026-05",
        "terminal_exit_month": "2026-06",
        "purged_interval": "2021-12 open through 2022-01 open",
        "query_start": "2021-12-01",
        "query_end": "2026-06-01",
        "required_complete_cohorts": INFERENCE_COHORTS,
        "required_execution_points": INFERENCE_COHORTS + 1,
        "reconstruction_session_count": 2134,
        "required_daily_session_count": 1106,
        "calendar_epoch_count": 2,
        "corporate_action_count": 34,
    }:
        raise InputBlockedError("Inference-B stage contract mismatch")
    if freeze.get("bootstrap_contract") != {
        "primary_statistic": "monthly Sharpe(strategy) minus monthly Sharpe(SPY)",
        "method": "paired stationary bootstrap",
        "resamples": 10000,
        "expected_block_months": 6,
        "restart_probability": "1/6",
        "seed": 11903,
        "rng": "Python random.Random MT19937 random() sequence",
        "index_algorithm": (
            "first=floor(U*n); thereafter restart with probability 1/6 to "
            "floor(U*n), otherwise advance prior index by one modulo n"
        ),
        "pairing": "one shared index path resamples strategy and SPY monthly returns",
        "replicate_statistic": (
            "sqrt(12)*mean(strategy)/sample_stdev(strategy) minus "
            "sqrt(12)*mean(SPY)/sample_stdev(SPY)"
        ),
        "quantile_interpolation": "linear rank=(N-1)*alpha",
        "local_alpha": 0.05,
        "program_alpha": PROGRAM_ALPHA,
        "invalid_replicate_rule": (
            "any nonfinite statistic or zero standard deviation is a terminal fail-closed result"
        ),
        "gates": [
            "local one-sided lower bound is strictly positive",
            "program one-sided lower bound is strictly positive",
        ],
    }:
        raise InputBlockedError("Inference-B bootstrap contract mismatch")
    if freeze.get("input_identities") != {
        "runtime_bundle_schema": "us-spy-h15-10y3m-state-inference-b-runtime-input-v1",
        "runtime_bundle_sha256": INFERENCE_B_BUNDLE_SHA256,
        "h15_schema": "us-spy-h15-10y3m-state-inference-b-v1",
        "h15_sha256": INFERENCE_B_H15_SHA256,
        "h15_selection_query_sha256": INFERENCE_B_H15_SELECTION_QUERY_SHA256,
        "h15_database_sha256": INFERENCE_B_DATABASE_SHA256,
        "h15_response_set_sha256": (
            "338a8da0720f16045cd3325a5dc07241292c149e836bce1149af3de8bb97cc14"
        ),
        "h15_rows": INFERENCE_COHORTS,
    }:
        raise InputBlockedError("Inference-B input identity mismatch")
    if freeze.get("implementation") != {
        "adapter_sha256": adapter_sha256,
        "runner_sha256_bound_at_one_use_invocation": True,
        "shared_core_commit": CORE_COMMIT,
        "shared_core_tree": CORE_TREE,
        "shared_core_source_sha256": CORE_SOURCE_SHA256,
    }:
        raise InputBlockedError("Inference-B implementation identity mismatch")
    if freeze.get("terminal_rules") != {
        "pass": "RETROSPECTIVE_SECONDARY_PASS_PENDING_EXTERNAL_REVIEW",
        "fail": "RETROSPECTIVE_SECONDARY_INFERENCE_B_FAIL",
        "pre_inference_error": "INPUT_BLOCKED",
        "claim_and_result_paths_are_single_use": True,
        "rerun_after_any_claim": False,
        "inference_attempt_consumed_at_claim": True,
        "inference_outcome_opened_at_runtime_bundle_capture_attempt": True,
        "technical_continuation_limit": 2,
    }:
        raise InputBlockedError("Inference-B terminal rules mismatch")
    if freeze.get("boundaries") != {
        "network_or_provider_call": False,
        "database_write": False,
        "parameter_change": False,
        "strategy_candidate_available": False,
        "shadow": False,
        "paper": False,
        "broker": False,
        "live": False,
    }:
        raise InputBlockedError("Inference-B boundaries mismatch")
    if record.get("technical_continuation_1") != {
        "owner_authorized": True,
        "reason": (
            "the prior claim stopped before the first completed rebalance because the "
            "runtime bundle used the unsupported label raw_signal_session_close for an "
            "otherwise raw execution-unit decision close"
        ),
        "economic_contract_changed": False,
        "signal_dates_costs_account_comparator_statistics_and_gates_changed": False,
        "prior_inference_outcome_computed": False,
        "repair": (
            "replace decision_price_basis with raw_execution_units in exactly 54 execution "
            "records and rebind the unchanged H15 rows to the repaired bundle"
        ),
        "prior_terminal_report_sha256": CONTINUATION_1_AUTHORIZATION_REPORT_SHA256,
        "prior_claim_sha256": (
            "9573ded969d2c2284aa739fb78c02f6f319d62a6ab43cdfe75e0ac0dd6021f6c"
        ),
        "prior_result_sha256": (
            "705ffbce5915c1eacb21316005263bb31e147b3a871acd005a886ed0296e40b0"
        ),
        "attempt_limit": 1,
        "further_retry_allowed": False,
    }:
        raise InputBlockedError("Inference-B technical continuation contract mismatch")
    if record.get("technical_continuation_2") != {
        "owner_authorized": True,
        "authorization_basis": (
            "the owner directed completion of data-blocked strategies on 2026-07-23; "
            "the prior continuation produced no Inference-B strategy statistic"
        ),
        "reason": (
            "the prior continuation passed the exact external market label US directly "
            "into the shared-core internal market enum us and stopped before the first "
            "completed rebalance"
        ),
        "economic_contract_changed": False,
        "signal_dates_costs_account_comparator_statistics_and_gates_changed": False,
        "prior_inference_statistic_computed": False,
        "prior_inference_result_metrics_present": False,
        "repair": (
            "require the exact external market label US and map only that value to the "
            "shared-core internal market enum us before any callback"
        ),
        "prior_terminal_report_sha256": PRIOR_TERMINAL_REPORT_SHA256,
        "prior_claim_sha256": PRIOR_CONTINUATION_1_CLAIM_SHA256,
        "prior_result_sha256": PRIOR_CONTINUATION_1_RESULT_SHA256,
        "attempt_limit": 1,
        "further_retry_allowed": False,
    }:
        raise InputBlockedError("Inference-B continuation-2 contract mismatch")


def _run_inference_once(expected_hashes: tuple[str, str]) -> None:
    definition_bytes = DEFINITION.read_bytes()
    definition = _json(definition_bytes, "definition")
    if (
        _sha256_bytes(definition_bytes) != INFERENCE_B_DEFINITION_SHA256
        or definition.get("status") != "PREREGISTERED_NOT_EXECUTED"
    ):
        raise InputBlockedError("definition is not preregistered-not-executed")
    actual_hashes = (_file_sha256(ADAPTER), _file_sha256(RUNNER))
    if tuple(_sha256(value, "expected code identity") for value in expected_hashes) != actual_hashes:
        raise InputBlockedError("adapter/runner identity mismatch")
    _require_inference_contract(definition_bytes, actual_hashes[0])
    _require_core_identity()
    if len(
        {
            SCREEN_A_PRIVATE_RESULT,
            INFERENCE_B_BUNDLE,
            INFERENCE_B_H15,
            INFERENCE_B_CLAIM,
            INFERENCE_B_RESULT,
        }
    ) != 5:
        raise InputBlockedError("Inference-B canonical paths must be distinct")
    _target(INFERENCE_B_CLAIM)
    _target(INFERENCE_B_RESULT)
    identity = {
        "parent_definition_sha256": SCREEN_A_DEFINITION_SHA256,
        "inference_definition_sha256": INFERENCE_B_DEFINITION_SHA256,
        "adapter_sha256": actual_hashes[0],
        "runner_sha256": actual_hashes[1],
        "screen_a_private_result_sha256": SCREEN_A_PRIVATE_RESULT_SHA256,
        "screen_a_public_report_sha256": SCREEN_A_PUBLIC_REPORT_SHA256,
        "runtime_bundle_sha256": INFERENCE_B_BUNDLE_SHA256,
        "h15_input_sha256": INFERENCE_B_H15_SHA256,
        "h15_selection_query_sha256": INFERENCE_B_H15_SELECTION_QUERY_SHA256,
        "h15_database_sha256": INFERENCE_B_DATABASE_SHA256,
        "core_commit": CORE_COMMIT,
        "core_tree": CORE_TREE,
        "core_source_sha256": CORE_SOURCE_SHA256,
    }
    claim_sha256 = _publish(
        INFERENCE_B_CLAIM,
        {
            "schema_version": "us-spy-h15-10y3m-state-inference-b-claim-v1",
            "research_id": "US_SPY_H15_10Y3M_STATE_V1",
            "mechanism_id": MECHANISM_ID,
            "program_family_id": PROGRAM_FAMILY_ID,
            "program_alpha": PROGRAM_ALPHA,
            "stage": "RETROSPECTIVE_SECONDARY_INFERENCE_B",
            "technical_continuation_id": "PREOUTCOME_TECHNICAL_CONTINUATION_2",
            "claimed_at": datetime.now(timezone.utc).isoformat(),
            **identity,
        },
    )
    identity["claim_sha256"] = claim_sha256
    inference_outcome_opened = False
    try:
        screen_result = _capture(
            SCREEN_A_PRIVATE_RESULT,
            SCREEN_A_PRIVATE_RESULT_SHA256,
            max_bytes=2 * 1024 * 1024,
        )
        _require_screen_a_unlocked(screen_result)
        inference_outcome_opened = True
        bundle = _capture(
            INFERENCE_B_BUNDLE,
            INFERENCE_B_BUNDLE_SHA256,
            max_bytes=8 * 1024 * 1024,
        )
        h15 = _capture(INFERENCE_B_H15, INFERENCE_B_H15_SHA256, max_bytes=1024 * 1024)
        _, points, daily_sessions, actions = _load_bundle(
            bundle,
            schema_version="us-spy-h15-10y3m-state-inference-b-runtime-input-v1",
            stage="inference_b_input",
            query_start="2021-12-01",
            query_end="2026-06-01",
            entry_months=INFERENCE_ENTRY_MONTHS,
            signal_months=INFERENCE_SIGNAL_MONTHS,
            terminal_month=(2026, 6),
            reconstruction_session_count=2134,
            calendar_epoch_count=2,
            action_count=34,
        )
        if len(daily_sessions) != 1106:
            raise InputBlockedError("Inference-B daily-session count mismatch")
        weights = _load_h15(
            h15,
            points,
            schema_version="us-spy-h15-10y3m-state-inference-b-v1",
            stage="inference_b_input",
            spy_bundle_sha256=INFERENCE_B_BUNDLE_SHA256,
            row_count=INFERENCE_COHORTS,
            selection_query_sha256=INFERENCE_B_H15_SELECTION_QUERY_SHA256,
            database_sha256=INFERENCE_B_DATABASE_SHA256,
            bundle_hash_field="runtime_bundle_sha256",
        )
        strategy_navs, benchmark_navs, strategy_hashes, benchmark_hashes = _simulate(
            points,
            daily_sessions,
            actions,
            weights,
            INFERENCE_B_DEFINITION_SHA256,
            actual_hashes[0],
        )
    except Exception as exc:
        _publish(
            INFERENCE_B_RESULT,
            {
                "schema_version": "us-spy-h15-10y3m-state-inference-b-private-result-v1",
                "research_id": "US_SPY_H15_10Y3M_STATE_V1",
                "mechanism_id": MECHANISM_ID,
                "program_family_id": PROGRAM_FAMILY_ID,
                "program_alpha": PROGRAM_ALPHA,
                "stage": "RETROSPECTIVE_SECONDARY_INFERENCE_B",
                "classification": "INPUT_BLOCKED",
                "error_type": type(exc).__name__,
                "identity": identity,
                "inference_attempt_consumed": True,
                "inference_outcome_opened": inference_outcome_opened,
                "one_use_execution_consumed": True,
                "rerun_authorized": False,
                "strategy_candidate_available": False,
                "shadow": False,
                "paper": False,
                "broker": False,
                "live": False,
            },
        )
        raise

    try:
        decision = inference_decision(
            strategy_navs,
            benchmark_navs,
            screen_a_unlocked=True,
        )
    except Exception as exc:
        _publish(
            INFERENCE_B_RESULT,
            {
                "schema_version": "us-spy-h15-10y3m-state-inference-b-private-result-v1",
                "research_id": "US_SPY_H15_10Y3M_STATE_V1",
                "mechanism_id": MECHANISM_ID,
                "program_family_id": PROGRAM_FAMILY_ID,
                "program_alpha": PROGRAM_ALPHA,
                "stage": "RETROSPECTIVE_SECONDARY_INFERENCE_B",
                "classification": "RETROSPECTIVE_SECONDARY_INFERENCE_B_FAIL",
                "observed_cohorts": INFERENCE_COHORTS,
                "inference_failure_reason": "FAIL_CLOSED_INVALID_INFERENCE_STATISTIC",
                "inference_error_type": type(exc).__name__,
                "gates": {
                    "local_lower_bound_positive": False,
                    "program_lower_bound_positive": False,
                },
                "strategy_boundary_navs_hex": [float(value).hex() for value in strategy_navs],
                "benchmark_boundary_navs_hex": [float(value).hex() for value in benchmark_navs],
                "strategy_stage_hashes": strategy_hashes,
                "benchmark_stage_hashes": benchmark_hashes,
                "identity": identity,
                "inference_attempt_consumed": True,
                "inference_outcome_opened": True,
                "one_use_execution_consumed": True,
                "rerun_authorized": False,
                "strategy_candidate_available": False,
                "shadow": False,
                "paper": False,
                "broker": False,
                "live": False,
            },
        )
        return

    classification = (
        "RETROSPECTIVE_SECONDARY_PASS_PENDING_EXTERNAL_REVIEW"
        if decision.all_gates_pass
        else "RETROSPECTIVE_SECONDARY_INFERENCE_B_FAIL"
    )
    result = {
        "schema_version": "us-spy-h15-10y3m-state-inference-b-private-result-v1",
        "research_id": "US_SPY_H15_10Y3M_STATE_V1",
        "mechanism_id": MECHANISM_ID,
        "program_family_id": PROGRAM_FAMILY_ID,
        "program_alpha": PROGRAM_ALPHA,
        "stage": "RETROSPECTIVE_SECONDARY_INFERENCE_B",
        "classification": classification,
        "observed_cohorts": decision.observed_cohorts,
        "gates": dict(decision.gates),
        "strategy_metrics_hex": {
            key: float(value).hex() for key, value in vars(decision.strategy).items()
        },
        "benchmark_metrics_hex": {
            key: float(value).hex() for key, value in vars(decision.benchmark).items()
        },
        "observed_sharpe_difference_hex": float(decision.observed_sharpe_difference).hex(),
        "local_lower_bound_hex": float(decision.local_lower_bound).hex(),
        "program_lower_bound_hex": float(decision.program_lower_bound).hex(),
        "strategy_boundary_navs_hex": [float(value).hex() for value in strategy_navs],
        "benchmark_boundary_navs_hex": [float(value).hex() for value in benchmark_navs],
        "strategy_stage_hashes": strategy_hashes,
        "benchmark_stage_hashes": benchmark_hashes,
        "identity": identity,
        "inference_attempt_consumed": True,
        "inference_outcome_opened": True,
        "one_use_execution_consumed": True,
        "rerun_authorized": False,
        "strategy_candidate_available": False,
        "shadow": False,
        "paper": False,
        "broker": False,
        "live": False,
    }
    _publish(INFERENCE_B_RESULT, result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-adapter-sha256", required=True)
    parser.add_argument("--expected-runner-sha256", required=True)
    args = parser.parse_args(argv)
    _run_inference_once(
        (args.expected_adapter_sha256, args.expected_runner_sha256),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
