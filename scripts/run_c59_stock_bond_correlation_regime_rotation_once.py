"""One-use runner for the frozen Cycle 59 stock-bond-correlation SPY/QQQ lane."""

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
from research.adapters.c59_stock_bond_correlation_regime_rotation import (  # noqa: E402
    HOLDOUT_INTERVALS,
    INITIAL_CAPITAL,
    PROGRAM_ALPHA,
    RESEARCH_ID,
    VALIDATION_INTERVALS,
    holdout_decision,
    validation_decision,
)


DEFINITION = ROOT / "research/definitions/c59_stock_bond_correlation_regime_rotation_v1.json"
ADAPTER = ROOT / "research/adapters/c59_stock_bond_correlation_regime_rotation.py"
RUNNER = Path(__file__).resolve()
DEFINITION_SHA256 = "8331e0a285b01d0fa2c3148dae9c0fb665e33763c0f867b0c7f59617829dfff4"
ADAPTER_SHA256 = "5273173ec7e63f968c320376cc725eacb29311bf5195a0c40521f6a42574c522"
SIGNAL_SHA256 = "1dcdcee15897486aafc89c4afc1ca7a71a85b64dab00c990e1033a2346288e47"
RECEIPT_SHA256 = "020b640381fb69e70bacb3d91ed99cb014f63f1037c6f322a8fc67e739ac5ecd"
VALIDATION_BUNDLE_SHA256 = "499157cd45b6402aabb8f786ae7e60f9c4bb55992e60bab8ff03f1104baa5b8a"
HOLDOUT_BUNDLE_SHA256 = "ff4b02932079ad013da05dbffcf2dd6e25af8592450e5b09e4a2f00d9f61f8d4"
CORE_SOURCE_FILE_COUNT = 23
CORE_SOURCE_SHA256 = "46ae2fe342a40034b9caacb6cc48a182947a49da9d874de31a1fdb60be0b9a80"
INCLUSION_RULE_SHA256 = "89483ee34a4b87fcdb728889dc31c7dc7222f85b3071ff7a97c65148e1b6402e"
SIGNAL_INPUT = Path(
    "/home/rongyu/workspace/quant-data/staging/"
    "c59_stock_bond_correlation_regime_rotation_spy_qqq_v1/"
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
    record = _json(payload, "IPO risk appetite rotation input packet")
    expected_contract = {
        "left_symbol": "IPO",
        "right_symbol": "SPY",
        "return_window": (
            "last accepted XNYS adjusted close in M-2 to last accepted "
            "XNYS adjusted close in M-1 for execution month M"
        ),
        "target_rule": (
            "strict IPO prior-month total-return outperformance versus SPY "
            "selects QQQ; equal or underperformance selects SPY"
        ),
        "threshold": 0,
    }
    if (
        record.get("schema_version")
        != "epoch10-factor-leadership-input-packet-v1"
        or record.get("research_id") != RESEARCH_ID
        or record.get("strategy_outcomes_opened") is not False
        or record.get("price_values_used_for_signal") is not True
        or record.get("signal_price_values_used_for_materialization") is not True
        or record.get("adjusted_prices_used") is not True
        or record.get("database_opened") is not False
        or record.get("database_write") is not False
        or record.get("source_selected_using_performance") is not False
        or record.get("signal_contract") != expected_contract
    ):
        raise InputBlockedError("IPO risk appetite packet boundary mismatch")
    rows = record.get("signals")
    if type(rows) is not list or len(rows) != VALIDATION_INTERVALS + HOLDOUT_INTERVALS:
        raise InputBlockedError("IPO risk appetite signal row count mismatch")
    parsed: dict[str, list[Signal]] = {
        "validation": [],
        "retrospective_holdout": [],
    }
    expected_source = {
        "IPO": (
            "https://query1.finance.yahoo.com/v8/finance/chart/IPO?"
            "period1=1604188800&period2=1782864000&interval=1d&"
            "events=div%2Csplits&includeAdjustedClose=true",
            "861b016d17ab6fe3f3b48627d42841e542f260e56e5bee38af5bfc39c7f995aa",
        ),
        "SPY": (
            "https://query1.finance.yahoo.com/v8/finance/chart/SPY?"
            "period1=1604188800&period2=1782864000&interval=1d&"
            "events=div%2Csplits&includeAdjustedClose=true",
            "7957979c644fce48c6bd49a9e7e9c2f67d319a9ea9a7cee087f8692ca8d58b07",
        ),
    }
    expected_availability_rule = (
        "20:00 America/New_York after the accepted session close; "
        "retrospective-secondary current adjusted history"
    )
    for row in rows:
        if type(row) is not dict or row.get("stage") not in parsed:
            raise InputBlockedError("IPO risk appetite signal stage mismatch")
        left_current = row.get("left_current")
        left_previous = row.get("left_previous")
        right_current = row.get("right_current")
        right_previous = row.get("right_previous")
        selections = (left_current, left_previous, right_current, right_previous)
        if any(type(selection) is not dict for selection in selections):
            raise InputBlockedError("IPO risk appetite selections are required")
        for selection in selections:
            row_hash = selection.get("row_sha256")
            identity = {
                key: value for key, value in selection.items() if key != "row_sha256"
            }
            symbol = selection.get("symbol")
            source = expected_source.get(symbol)
            try:
                value = Decimal(selection.get("adjusted_close"))
            except (TypeError, ValueError, ArithmeticError) as exc:
                raise InputBlockedError(
                    "IPO risk appetite adjusted close is invalid"
                ) from exc
            if (
                source is None
                or selection.get("source_class")
                != "YAHOO_PUBLIC_CHART_RETROSPECTIVE_SECONDARY"
                or selection.get("source_url") != source[0]
                or selection.get("raw_response_sha256") != source[1]
                or selection.get("availability_rule")
                != expected_availability_rule
                or not value.is_finite()
                or value <= 0
                or row_hash
                != _hash_bytes(
                    json.dumps(
                        identity, sort_keys=True, separators=(",", ":")
                    ).encode()
                )
            ):
                raise InputBlockedError("IPO risk appetite source row identity mismatch")
        left_current_value = Decimal(left_current["adjusted_close"])
        left_previous_value = Decimal(left_previous["adjusted_close"])
        right_current_value = Decimal(right_current["adjusted_close"])
        right_previous_value = Decimal(right_previous["adjusted_close"])
        expected_cross_product = (
            left_current_value * right_previous_value
            - right_current_value * left_previous_value
        )
        try:
            cross_product = Decimal(row.get("relative_return_cross_product"))
        except (TypeError, ValueError, ArithmeticError) as exc:
            raise InputBlockedError(
                "IPO risk appetite cross product is invalid"
            ) from exc
        if not cross_product.is_finite() or cross_product != expected_cross_product:
            raise InputBlockedError("IPO risk appetite arithmetic mismatch")
        expected_state = "QQQ" if cross_product > 0 else "SPY"
        start = _date(row["holding_start_execution_session"], "holding start")
        end = _date(row["holding_end_execution_session"], "holding end")
        decision_at = _datetime(row["decision_at"], "signal decision_at")
        current_reference_month = _date(
            row.get("current_reference_month"), "current signal reference month"
        )
        previous_reference_month = _date(
            row.get("previous_reference_month"), "previous signal reference month"
        )
        expected_current_ordinal = start.year * 12 + start.month - 2
        expected_current_month = date(
            expected_current_ordinal // 12,
            expected_current_ordinal % 12 + 1,
            1,
        )
        current_session = _date(
            row.get("current_month_end_session"), "current month-end session"
        )
        previous_session = _date(
            row.get("previous_month_end_session"), "previous month-end session"
        )
        current_rows = (left_current, right_current)
        previous_rows = (left_previous, right_previous)
        if (
            current_reference_month != expected_current_month
            or not _prior_calendar_month_is_valid(
                previous_reference_month, current_reference_month
            )
            or current_session.year != current_reference_month.year
            or current_session.month != current_reference_month.month
            or previous_session.year != previous_reference_month.year
            or previous_session.month != previous_reference_month.month
            or current_session >= start
            or previous_session >= current_session
            or any(
                _date(item.get("reference_month"), "current reference month")
                != current_reference_month
                or _date(
                    item.get("accepted_month_end_session"),
                    "current accepted month-end session",
                )
                != current_session
                or _datetime(
                    item.get("available_at_conservative"),
                    "current adjusted-close available_at",
                )
                != datetime.combine(current_session, time(20, 0), NY)
                or _datetime(
                    item.get("available_at_conservative"),
                    "current adjusted-close available_at",
                )
                > decision_at
                for item in current_rows
            )
            or any(
                _date(item.get("reference_month"), "previous reference month")
                != previous_reference_month
                or _date(
                    item.get("accepted_month_end_session"),
                    "previous accepted month-end session",
                )
                != previous_session
                or _datetime(
                    item.get("available_at_conservative"),
                    "previous adjusted-close available_at",
                )
                != datetime.combine(previous_session, time(20, 0), NY)
                or _datetime(
                    item.get("available_at_conservative"),
                    "previous adjusted-close available_at",
                )
                > decision_at
                for item in previous_rows
            )
        ):
            raise InputBlockedError(
                "IPO risk appetite month identity or availability mismatch"
            )
        identity = {
            "stage": row["stage"],
            "holding_start_execution_session": start.isoformat(),
            "holding_end_execution_session": end.isoformat(),
            "decision_at": row["decision_at"],
            "previous_reference_month": previous_reference_month.isoformat(),
            "current_reference_month": current_reference_month.isoformat(),
            "current_month_end_session": current_session.isoformat(),
            "previous_month_end_session": previous_session.isoformat(),
            "left_current_row_sha256": left_current["row_sha256"],
            "left_previous_row_sha256": left_previous["row_sha256"],
            "right_current_row_sha256": right_current["row_sha256"],
            "right_previous_row_sha256": right_previous["row_sha256"],
            "relative_return_cross_product": str(cross_product),
            "target_symbol": expected_state,
        }
        if any(row.get(key) != value for key, value in identity.items()):
            raise InputBlockedError("IPO risk appetite signal arithmetic mismatch")
        identity_hash = _hash_bytes(
            json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
        )
        if row.get("signal_identity_sha256") != identity_hash:
            raise InputBlockedError("IPO risk appetite signal identity hash mismatch")
        parsed[row["stage"]].append(
            Signal(
                row["stage"],
                start,
                end,
                decision_at,
                expected_state,
                _sha(
                    row["signal_identity_sha256"],
                    "IPO risk appetite row SHA-256",
                ),
            )
        )
    output = {key: tuple(value) for key, value in parsed.items()}
    if (
        len(output["validation"]) != VALIDATION_INTERVALS
        or len(output["retrospective_holdout"]) != HOLDOUT_INTERVALS
    ):
        raise InputBlockedError("IPO risk appetite signal split count mismatch")
    support = record.get("state_support")
    if type(support) is not dict:
        raise InputBlockedError("IPO risk appetite state support is required")
    for stage, group in output.items():
        if any(
            left.end != right.start
            for left, right in zip(group, group[1:], strict=False)
        ):
            raise InputBlockedError(
                "IPO risk appetite signal intervals are not contiguous"
            )
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
            raise InputBlockedError("IPO risk appetite state support mismatch")
    return output


def _correlation_signals(payload: bytes) -> dict[str, tuple[Signal, ...]]:
    record = _json(payload, "stock-bond correlation input packet")
    expected_contract = {
        "window": (
            "63 paired daily log returns over 64 common accepted XNYS "
            "sessions ending at M-1 month-end"
        ),
        "statistic": (
            "ordinary sample Pearson correlation of SPY and TLT log returns"
        ),
        "target_rule": (
            "strictly negative selects QQQ; zero or positive selects SPY"
        ),
    }
    hashes = record.get("source_hashes")
    expected_hashes = {
        "c59_spy_yahoo_response_sha256": (
            "367958a98ce353e4ebf1f014016548ac1b4ff989bf48d724ef6e2d35b036564c"
        ),
        "c59_tlt_yahoo_response_sha256": (
            "af0c4691ccd2e072c487538adee3b55f580c286ae1afcf80dcf4174fbcf653e3"
        ),
        "c59_spy_fetch_receipt_sha256": (
            "7b04444f454e2209aaf310da4f36245ced04ba9359b8d005474e3060a2c35e6d"
        ),
        "c59_tlt_fetch_receipt_sha256": (
            "7b04444f454e2209aaf310da4f36245ced04ba9359b8d005474e3060a2c35e6d"
        ),
        "c59_reused_c33_market_scaffold_sha256": (
            "fa42bea9f2421a725c416c8588842341b9439c9796527f2021bb6b2312e2a242"
        ),
    }
    if (
        record.get("schema_version")
        != "c59-stock-bond-correlation-full-input-v1"
        or record.get("research_id") != RESEARCH_ID
        or record.get("strategy_outcomes_opened") is not False
        or record.get("price_values_used_for_signal") is not True
        or record.get("adjusted_prices_used") is not True
        or record.get("database_opened") is not False
        or record.get("database_write") is not False
        or record.get("source_selected_using_performance") is not False
        or record.get("signal_contract") != expected_contract
        or type(hashes) is not dict
        or any(hashes.get(key) != value for key, value in expected_hashes.items())
    ):
        raise InputBlockedError("stock-bond correlation packet boundary mismatch")
    rows = record.get("signals")
    if type(rows) is not list or len(rows) != VALIDATION_INTERVALS + HOLDOUT_INTERVALS:
        raise InputBlockedError("stock-bond correlation signal row count mismatch")
    parsed: dict[str, list[Signal]] = {
        "validation": [],
        "retrospective_holdout": [],
    }
    for row in rows:
        if type(row) is not dict or row.get("stage") not in parsed:
            raise InputBlockedError("stock-bond correlation signal stage mismatch")
        correlation = row.get("pearson_correlation")
        if (
            isinstance(correlation, bool)
            or not isinstance(correlation, (int, float))
            or not math.isfinite(float(correlation))
            or not -1.0 <= float(correlation) <= 1.0
        ):
            raise InputBlockedError("stock-bond correlation value is invalid")
        expected_state = "QQQ" if float(correlation) < 0.0 else "SPY"
        start = _date(row.get("holding_start_execution_session"), "holding start")
        end = _date(row.get("holding_end_execution_session"), "holding end")
        decision_at = _datetime(row.get("decision_at"), "signal decision_at")
        dates = row.get("window_session_dates")
        if type(dates) is not list or len(dates) != 64:
            raise InputBlockedError("stock-bond correlation window must have 64 sessions")
        window = tuple(_date(value, "window session") for value in dates)
        if len(set(window)) != 64 or tuple(sorted(window)) != window:
            raise InputBlockedError("stock-bond correlation sessions must be ordered and unique")
        expected_month = 12 if start.month == 1 else start.month - 1
        expected_year = start.year - 1 if start.month == 1 else start.year
        available_at = _datetime(
            row.get("available_at_conservative"), "signal available_at"
        )
        if (
            (window[-1].year, window[-1].month) != (expected_year, expected_month)
            or row.get("window_first_session") != window[0].isoformat()
            or row.get("window_last_session") != window[-1].isoformat()
            or row.get("paired_log_return_count") != 63
            or row.get("target_symbol") != expected_state
            or row.get("spy_response_sha256")
            != expected_hashes["c59_spy_yahoo_response_sha256"]
            or row.get("tlt_response_sha256")
            != expected_hashes["c59_tlt_yahoo_response_sha256"]
            or available_at != datetime.combine(window[-1], time(20, 0), NY)
            or available_at > decision_at
            or window[-1] >= start
        ):
            raise InputBlockedError("stock-bond correlation chronology mismatch")
        identity = {
            "stage": row["stage"],
            "holding_start_execution_session": start.isoformat(),
            "holding_end_execution_session": end.isoformat(),
            "decision_at": row["decision_at"],
            "window_first_session": window[0].isoformat(),
            "window_last_session": window[-1].isoformat(),
            "paired_log_return_count": 63,
            "pearson_correlation": correlation,
            "target_symbol": expected_state,
            "spy_response_sha256": expected_hashes[
                "c59_spy_yahoo_response_sha256"
            ],
            "tlt_response_sha256": expected_hashes[
                "c59_tlt_yahoo_response_sha256"
            ],
        }
        identity_hash = _hash_bytes(
            (
                json.dumps(identity, sort_keys=True, separators=(",", ":"))
                + "\n"
            ).encode()
        )
        if row.get("signal_identity_sha256") != identity_hash:
            raise InputBlockedError("stock-bond correlation signal identity mismatch")
        parsed[row["stage"]].append(
            Signal(
                row["stage"],
                start,
                end,
                decision_at,
                expected_state,
                _sha(identity_hash, "stock-bond correlation row SHA-256"),
            )
        )
    output = {key: tuple(value) for key, value in parsed.items()}
    support = record.get("state_support")
    if type(support) is not dict:
        raise InputBlockedError("stock-bond correlation state support is required")
    for stage, group in output.items():
        expected_count = (
            VALIDATION_INTERVALS if stage == "validation" else HOLDOUT_INTERVALS
        )
        if len(group) != expected_count or any(
            left.end != right.start
            for left, right in zip(group, group[1:], strict=False)
        ):
            raise InputBlockedError("stock-bond correlation interval mismatch")
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
            raise InputBlockedError("stock-bond correlation support mismatch")
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
        f"c40-spy-qqq-universe-{execution_session.isoformat()}",
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
    packet = _json(input_payload, "stock-bond correlation input packet")
    receipt = _json(
        receipt_payload,
        "stock-bond correlation materialization receipt",
    )
    retrieved_at = _datetime(receipt["created_at"], "input receipt created_at")
    if (
        packet.get("research_id") != RESEARCH_ID
        or receipt.get("research_id") != RESEARCH_ID
        or receipt.get("schema_version")
        != "c59-stock-bond-correlation-materialization-receipt-v1"
        or receipt.get("input_packet_sha256") != SIGNAL_SHA256
        or receipt.get("status")
        != "MATERIALIZED_OUTCOME_FREE_STATE_SUPPORT_PASS"
        or receipt.get("source_identities")
        != {
            "market_scaffold_sha256": (
                "fa42bea9f2421a725c416c8588842341b9439c9796527f2021bb6b2312e2a242"
            ),
            "spy_response_sha256": (
                "367958a98ce353e4ebf1f014016548ac1b4ff989bf48d724ef6e2d35b036564c"
            ),
            "tlt_response_sha256": (
                "af0c4691ccd2e072c487538adee3b55f580c286ae1afcf80dcf4174fbcf653e3"
            ),
            "spy_fetch_receipt_sha256": (
                "7b04444f454e2209aaf310da4f36245ced04ba9359b8d005474e3060a2c35e6d"
            ),
            "tlt_fetch_receipt_sha256": (
                "7b04444f454e2209aaf310da4f36245ced04ba9359b8d005474e3060a2c35e6d"
            ),
        }
        or receipt.get("database_sha256_before")
        != "aad5c8d01898eb48fda1c5ed6d6204274721267d65c6bd918f75edeec25ed85e"
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
                "stock-bond correlation signal does not bind the execution schedule"
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
        "schema_version": "c59-stock-bond-correlation-claim-v1",
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
        "schema_version": "c59-stock-bond-correlation-result-v1",
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
            raise InputBlockedError("Cycle 59 one-use state is not pristine")
        bundle_path, expected_bundle = VALIDATION_BUNDLE, VALIDATION_BUNDLE_SHA256
        claim_path, result_path = VALIDATION_CLAIM, VALIDATION_RESULT
        signal_stage = "validation"
    else:
        if HOLDOUT_CLAIM.exists() or HOLDOUT_RESULT.exists():
            raise InputBlockedError("Cycle 59 holdout one-use state is not pristine")
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
        signals = _correlation_signals(input_payload)
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
