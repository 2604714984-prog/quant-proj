"""One-use runner for the frozen C64 SKEW impulse SPY/QQQ rotation lane."""

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
from research.adapters.c64_cboe_skew_tail_risk_impulse_rotation import (  # noqa: E402
    HOLDOUT_INTERVALS,
    INITIAL_CAPITAL,
    PROGRAM_ALPHA,
    RESEARCH_ID,
    VALIDATION_INTERVALS,
    holdout_decision,
    validation_decision,
)


DEFINITION = ROOT / "research/definitions/c64_cboe_skew_tail_risk_impulse_rotation_v1.json"
ADAPTER = ROOT / "research/adapters/c64_cboe_skew_tail_risk_impulse_rotation.py"
RUNNER = Path(__file__).resolve()
DEFINITION_SHA256 = "e249691561ded642e8318306cfc05df71f6ae8c551a153c294e51badc378e44e"
ADAPTER_SHA256 = "61bd240034a96a811714f4b9480bd84fb8905f4e927cdd7748e64501de56d687"
SIGNAL_SHA256 = "33fc2bb1000ab64e06dbe9cac04211190f26ba352618da71bac6c9e0ea7a9759"
RECEIPT_SHA256 = "35842218c3e78c5c00e8f6406ab8081d4c7aeb6c04f4eaba4443a5fd8376c273"
VALIDATION_BUNDLE_SHA256 = "499157cd45b6402aabb8f786ae7e60f9c4bb55992e60bab8ff03f1104baa5b8a"
HOLDOUT_BUNDLE_SHA256 = "ff4b02932079ad013da05dbffcf2dd6e25af8592450e5b09e4a2f00d9f61f8d4"
CORE_SOURCE_FILE_COUNT = 23
CORE_SOURCE_SHA256 = "46ae2fe342a40034b9caacb6cc48a182947a49da9d874de31a1fdb60be0b9a80"
INCLUSION_RULE_SHA256 = "89483ee34a4b87fcdb728889dc31c7dc7222f85b3071ff7a97c65148e1b6402e"
SIGNAL_INPUT = Path(
    "/home/rongyu/workspace/quant-data/staging/"
    "c64_cboe_skew_tail_risk_impulse_rotation_spy_qqq_v1/"
    "full_input_packet.json"
)
INPUT_RECEIPT = SIGNAL_INPUT.with_name("full_materialization_receipt.json")
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


def _prior_calendar_month_is_valid(previous: date, current: date) -> bool:
    if previous.day != 1 or current.day != 1:
        return False
    previous_ordinal = previous.year * 12 + previous.month - 1
    current_ordinal = current.year * 12 + current.month - 1
    return previous_ordinal + 1 == current_ordinal


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
    record = _json(payload, "SKEW tail-risk impulse input packet")
    expected_contract = {
        "series_id": "CBOE_SKEW",
        "return_window": (
            "last finite positive SKEW close in M-2 versus M-1 for "
            "execution month M"
        ),
        "target_rule": "strict SKEW decline selects QQQ; equality or increase selects SPY",
        "threshold_index_points": 0.0,
    }
    if (
        record.get("schema_version")
        != "c64-skew-tail-risk-impulse-input-packet-v1"
        or record.get("research_id") != RESEARCH_ID
        or record.get("strategy_outcomes_opened") is not False
        or record.get("price_values_used_for_signal") is not True
        or record.get("spy_price_values_used_for_materialization") is not False
        or record.get("adjusted_prices_used") is not False
        or record.get("database_opened") is not False
        or record.get("database_write") is not False
        or record.get("source_selected_using_performance") is not False
        or record.get("signal_contract") != expected_contract
    ):
        raise InputBlockedError("SKEW packet boundary mismatch")
    rows = record.get("signals")
    if type(rows) is not list or len(rows) != VALIDATION_INTERVALS + HOLDOUT_INTERVALS:
        raise InputBlockedError("SKEW signal row count mismatch")
    parsed: dict[str, list[Signal]] = {
        "validation": [],
        "retrospective_holdout": [],
    }
    expected_raw_sha = "21cca8b0d43aa9d2d5eb25d78d42dbe4b8a652c27fced06783ce3c5ca1a11ba0"
    expected_url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/%5ESKEW?"
        "period1=1604188800&period2=1782864000&interval=1d&"
        "events=div%2Csplits&includeAdjustedClose=true"
    )
    expected_availability_rule = (
        "20:00 America/New_York after accepted close; "
        "retrospective-secondary current history"
    )
    for row in rows:
        if type(row) is not dict or row.get("stage") not in parsed:
            raise InputBlockedError("SKEW signal stage mismatch")
        current = row.get("current_selection")
        previous = row.get("previous_selection")
        if type(current) is not dict or type(previous) is not dict:
            raise InputBlockedError("SKEW selections are required")
        for selection in (previous, current):
            row_hash = selection.get("row_sha256")
            identity = {
                key: value for key, value in selection.items() if key != "row_sha256"
            }
            value = selection.get("close_index_points")
            if (
                selection.get("series_id") != "CBOE_SKEW"
                or selection.get("source_class")
                != "YAHOO_PUBLIC_CHART_RETROSPECTIVE_SECONDARY"
                or selection.get("source_url") != expected_url
                or selection.get("raw_response_sha256") != expected_raw_sha
                or selection.get("availability_rule") != expected_availability_rule
                or isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or float(value) <= 0.0
                or row_hash
                != _hash_bytes(
                    json.dumps(
                        identity, sort_keys=True, separators=(",", ":")
                    ).encode()
                )
            ):
                raise InputBlockedError("SKEW source row identity mismatch")
        current_value = float(current["close_index_points"])
        previous_value = float(previous["close_index_points"])
        change = row.get("delta_index_points")
        if (
            isinstance(change, bool)
            or not isinstance(change, (int, float))
            or not math.isfinite(float(change))
            or not math.isclose(
                float(change), current_value - previous_value, rel_tol=0, abs_tol=1e-12
            )
        ):
            raise InputBlockedError("SKEW change arithmetic mismatch")
        expected_state = "QQQ" if float(change) < 0.0 else "SPY"
        start = _date(row["holding_start_execution_session"], "holding start")
        end = _date(row["holding_end_execution_session"], "holding end")
        decision_at = _datetime(row["decision_at"], "signal decision_at")
        current_reference = _date(
            row.get("current_reference_month"), "current reference month"
        )
        previous_reference = _date(
            row.get("previous_reference_month"), "previous reference month"
        )
        current_observation = _date(
            row.get("current_observation_date"), "current observation date"
        )
        previous_observation = _date(
            row.get("previous_observation_date"), "previous observation date"
        )
        expected_current_ordinal = start.year * 12 + start.month - 2
        expected_current = date(
            expected_current_ordinal // 12,
            expected_current_ordinal % 12 + 1,
            1,
        )
        if (
            current_reference != expected_current
            or not _prior_calendar_month_is_valid(previous_reference, current_reference)
            or (current_observation.year, current_observation.month)
            != (current_reference.year, current_reference.month)
            or (previous_observation.year, previous_observation.month)
            != (previous_reference.year, previous_reference.month)
            or current_observation
            != _date(current.get("observation_date"), "current source observation")
            or previous_observation
            != _date(previous.get("observation_date"), "previous source observation")
            or current_observation >= start
            or previous_observation >= current_observation
            or _datetime(current["available_at_conservative"], "current available_at")
            > decision_at
            or _datetime(previous["available_at_conservative"], "previous available_at")
            > decision_at
        ):
            raise InputBlockedError("SKEW observation or availability mismatch")
        identity = {
            "stage": row["stage"],
            "holding_start_execution_session": start.isoformat(),
            "holding_end_execution_session": end.isoformat(),
            "decision_at": row["decision_at"],
            "current_reference_month": current_reference.isoformat(),
            "previous_reference_month": previous_reference.isoformat(),
            "current_observation_date": current_observation.isoformat(),
            "previous_observation_date": previous_observation.isoformat(),
            "current_row_sha256": current["row_sha256"],
            "previous_row_sha256": previous["row_sha256"],
            "delta_index_points": float(change),
            "target_symbol": expected_state,
        }
        if any(row.get(key) != value for key, value in identity.items()):
            raise InputBlockedError("SKEW signal arithmetic mismatch")
        identity_hash = _hash_bytes(
            json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
        )
        if row.get("signal_identity_sha256") != identity_hash:
            raise InputBlockedError("SKEW signal identity hash mismatch")
        parsed[row["stage"]].append(
            Signal(
                row["stage"],
                start,
                end,
                decision_at,
                expected_state,
                _sha(row["signal_identity_sha256"], "SKEW row SHA-256"),
            )
        )
    output = {key: tuple(value) for key, value in parsed.items()}
    if (
        len(output["validation"]) != VALIDATION_INTERVALS
        or len(output["retrospective_holdout"]) != HOLDOUT_INTERVALS
    ):
        raise InputBlockedError("SKEW signal split count mismatch")
    support = record.get("state_support")
    if type(support) is not dict:
        raise InputBlockedError("SKEW state support is required")
    for stage, group in output.items():
        if any(
            left.end != right.start
            for left, right in zip(group, group[1:], strict=False)
        ):
            raise InputBlockedError("SKEW signal intervals are not contiguous")
        states = tuple(item.target_symbol for item in group)
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
            raise InputBlockedError("SKEW state support mismatch")
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
        f"c64-spy-qqq-universe-{execution_session.isoformat()}",
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
    packet = _json(input_payload, "SKEW impulse/QQQ input packet")
    receipt = _json(
        receipt_payload,
        "SKEW impulse/QQQ materialization receipt",
    )
    retrieved_at = _datetime(receipt["created_at"], "input receipt created_at")
    if (
        packet.get("research_id") != RESEARCH_ID
        or receipt.get("research_id") != RESEARCH_ID
        or receipt.get("schema_version")
        != "c64-skew-full-materialization-receipt-v1"
        or receipt.get("source_url")
        != (
            "https://query1.finance.yahoo.com/v8/finance/chart/%5ESKEW?"
            "period1=1604188800&period2=1782864000&interval=1d&"
            "events=div%2Csplits&includeAdjustedClose=true"
        )
        or receipt.get("raw_fetch_receipt_sha256")
        != "944c29258962f921ef1f41e29f0d8e6ed6daac03159c4c5b2b2d8447a8d25cbf"
        or receipt.get("raw_response_sha256")
        != "21cca8b0d43aa9d2d5eb25d78d42dbe4b8a652c27fced06783ce3c5ca1a11ba0"
        or receipt.get("input_packet_sha256") != SIGNAL_SHA256
        or receipt.get("status") != "MATERIALIZED_OUTCOME_FREE_STATE_SUPPORT_PASS"
        or receipt.get("support_passes") is not True
        or receipt.get("database_sha256_before")
        != "f87722ecf19f9813bb161e365b0e5aa5069ef3d4a16471ad712abb131d7e9fdd"
        or receipt.get("database_sha256_after")
        != receipt.get("database_sha256_before")
        or receipt.get("database_wal_absent") is not True
        or receipt.get("database_write") is not False
        or receipt.get("strategy_outcomes_opened") is not False
        or receipt.get("strategy_candidate_available") is not False
    ):
        raise InputBlockedError("input packet and receipt binding mismatch")
    packet_stage = "retrospective_holdout" if stage == "holdout" else stage
    raw_qqq_boundaries = packet.get("qqq_boundary_rows", {}).get(packet_stage)
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
            or not signal.signal_decision_at < decision_at
        ):
            raise InputBlockedError(
                "SKEW signal does not bind the execution schedule"
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
    strategy_returns = _adjacent_returns(strategy_navs)
    benchmark_returns = _adjacent_returns(benchmark_navs)
    return strategy_returns, benchmark_returns, tuple(stage_hashes)


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
            "schema_version": "c64-skew-tail-risk-claim-v1",
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
        "schema_version": "c64-skew-tail-risk-result-v1",
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
        or definition.get("expected_inclusion_rule_sha256")
        != INCLUSION_RULE_SHA256
        or definition.get("boundaries", {}).get("strategy_candidate_available") is not False
    ):
        raise InputBlockedError("definition semantic identity mismatch")
    runner_sha = _file_hash(RUNNER)
    validation_result_sha = None
    if stage == "validation":
        if any(path.exists() for path in (VALIDATION_CLAIM, VALIDATION_RESULT, HOLDOUT_CLAIM, HOLDOUT_RESULT)):
            raise InputBlockedError("Cycle 37 one-use state is not pristine")
        bundle_path, expected_bundle = VALIDATION_BUNDLE, VALIDATION_BUNDLE_SHA256
        claim_path, result_path = VALIDATION_CLAIM, VALIDATION_RESULT
        signal_stage = "validation"
    else:
        if HOLDOUT_CLAIM.exists() or HOLDOUT_RESULT.exists():
            raise InputBlockedError("Cycle 37 holdout one-use state is not pristine")
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
