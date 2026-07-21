"""One-off, injected-input SPY volatility-managed historical validation.

It can load only one exact private validation bundle and has no database, provider,
or network path. A real run remains hard-gated on current code and core identities.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import stat
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_SOURCE_ROOT = _REPOSITORY_ROOT / "src"
for _path in (_SOURCE_ROOT, _REPOSITORY_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from quant_system.backtest import (  # noqa: E402
    ExecutionInput,
    ExecutionReceipt,
    Portfolio,
    run_static_rebalance,
)
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
    validate_universe_snapshot,
)

from research.adapters.us_spy_volatility_managed import (  # noqa: E402
    INITIAL_CAPITAL,
    RETROSPECTIVE_ACTION_BASIS,
    CloseObservation,
    InputContractError,
    build_signal_feature,
    cohort_returns,
    validation_gate_decision,
)

OFFICIAL_ACTION_PROJECTION_SHA256 = (
    "caf871c657e8c1ff258e8733c8ef49409da1c66c911b5a48f2148cdf9cc3f12a"
)
OFFICIAL_ACTION_COUNT = 34
OFFICIAL_ACTION_RETRIEVED_AT = datetime.fromisoformat("2026-07-21T08:13:17.580138+00:00")
OFFICIAL_ACTION_AVAILABLE_AT_BASIS = (
    "OFFICIAL_SOURCE_RETRIEVED_20260721_HISTORICAL_PUBLICATION_TIME_NOT_BACKDATED"
)
PR117_REVIEWED_HEAD = "03ddff47b55f558cb93a4340dfeafc04e2953f92"
PR117_MERGED_MAIN_HEAD = "6897f80325f2499895ea4928aa7a445bb2d73501"
STATUS_CORE_REVIEWED_HEAD = "da9fb5855e2402804027a6f99109ca146dd81e18"
EXECUTION_CORE_REVIEWED_HEAD = "f2b3e622903dae0bf30dafbd4899af67f2571c13"
EXPECTED_INCLUSION_RULE_SHA256 = "89483ee34a4b87fcdb728889dc31c7dc7222f85b3071ff7a97c65148e1b6402e"
VALIDATION_CALENDAR_PROJECTION_SHA256 = (
    "23b8f4ffe7c82c73a18b1a883da01d6c3b14c31c30725062726b95b6eb12ea31"
)
QUALIFIED_MARKET_ROWS_SHA256 = "818ac5f04a072e1d8e6e7b27b42a7753f31ea9e09d11c65c7e78bb16e418394d"
VALIDATION_BUNDLE_FILE_SHA256 = "fcf4b487b1b798c6afcfc774339d2066a45238431253e27b14ed5d1a4cc369c9"
VALIDATION_RUNTIME_INPUT_BUNDLE_SHA256 = "db865aaaa169f926064a31cd608955557ffef1261e252281f2352d8a45d34cd8"
VALIDATION_CALENDAR_IDENTITY_SHA256 = "020cb50b360d04c551b539386b99307d4bd9bbdc925504fe2a5a1e5bbb71e4e9"
VALIDATION_CALENDAR_MAPPING_FILE_SHA256 = "75bb2f0d15d07ca5ab9a58b702665493ddedc4e7321066a141beb46b24667cee"
VALIDATION_CALENDAR_MAPPING_SHA256 = "36300dd6763fc8be3a53ddd70a1f3b1b6a1b058967bc0a7e6c79cb99b5510530"
VALIDATION_MARKET_RUNTIME_SHA256 = "6e00567c8a7bc065a542d031b6f441a829b40c236a8b6d8470e4e0513d72a8ee"
VALIDATION_ACTION_IDENTITY_SHA256 = "25cf12430457b6efd63d26b6db81f485b99392d8d505ba057c0961e26664c35c"
HOLDOUT_CALENDAR_PROJECTION_SHA256: str | None = None
HOLDOUT_RUNTIME_INPUT_BUNDLE_SHA256: str | None = None
VALIDATION_CALENDAR_SESSION_COUNT = 987
VALIDATION_OFFICIAL_ACTION_COUNT = 15
HOLDOUT_CALENDAR_SESSION_COUNT: int | None = None
HOLDOUT_OFFICIAL_ACTION_COUNT: int | None = None
ONE_WAY_SLIPPAGE_BPS = 10.0
VALIDATION_QUERY_BOUNDS = (date(2018, 1, 2), date(2021, 12, 1))
HOLDOUT_QUERY_BOUNDS = (date(2021, 12, 1), date(2026, 6, 1))
VALIDATION_ENTRY_MONTHS = tuple(
    (year, month)
    for year in range(2018, 2022)
    for month in range(1, 13)
    if (year, month) >= (2018, 3) and (year, month) <= (2021, 11)
)
HOLDOUT_ENTRY_MONTHS = tuple(
    (year, month)
    for year in range(2022, 2027)
    for month in range(1, 13)
    if (year, month) >= (2022, 1) and (year, month) <= (2026, 5)
)
_REPORT_PATH = (
    _REPOSITORY_ROOT / "research" / "reports" / "us_spy_volatility_managed_exposure_v1.json"
)
_ADAPTER_PATH = _REPOSITORY_ROOT / "research" / "adapters" / "us_spy_volatility_managed.py"
_RUNNER_PATH = Path(__file__).resolve()
_NEW_YORK = ZoneInfo("America/New_York")
_PROJECTION_KEYS = (
    "available_at_basis",
    "distribution",
    "event_type",
    "ex_date",
    "payment_date",
    "record_date",
    "source_document_sha256",
    "source_url",
    "symbol",
)


class InputBlockedError(InputContractError):
    """Permanent fail-closed input/identity/coverage/chronology error."""


@dataclass(frozen=True)
class RuntimeAuthorization:
    preregistration_status: str
    preregistration_json_sha256: str
    strategy_adapter_sha256: str
    causal_core_reviewed_head: str
    causal_core_merged_main_head: str
    status_core_reviewed_head: str
    execution_core_reviewed_head: str
    strategy_runner_sha256: str
    reconstruction_calendar_identity_sha256: str
    calendar_epoch_mapping_sha256: str
    qualified_market_rows_sha256: str
    input_bundle_sha256: str


@dataclass(frozen=True)
class ExecutionPoint:
    closes: tuple[CloseObservation, ...]
    actions: tuple[CorporateActionIdentity, ...]
    calendar: AcceptedSessionCalendar
    decision_at: datetime
    execution_session: date
    execution_input: ExecutionInput
    universe_snapshot: UniverseSnapshotIdentity
    execution_calendar_revision: AcceptedSessionCalendar | None = None


@dataclass(frozen=True)
class CohortSimulation:
    strategy_boundary_navs: tuple[float, ...]
    benchmark_boundary_navs: tuple[float, ...]
    strategy_returns: tuple[float, ...]
    benchmark_returns: tuple[float, ...]
    strategy_receipts: tuple[ExecutionReceipt, ...]
    benchmark_receipts: tuple[ExecutionReceipt, ...]


@dataclass(frozen=True)
class TerminalClassification:
    status: str
    permanent_closure: bool
    holdout_opened: bool
    strategy_candidate_available: bool = False


@dataclass(frozen=True)
class ValidationReceipt:
    strategy_boundary_navs: tuple[float, ...]
    benchmark_boundary_navs: tuple[float, ...]
    result_sha256: str


def _sha256(value: object, field: str) -> str:
    digest = str(value)
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise InputBlockedError(f"{field} must be a lowercase SHA-256 digest")
    return digest


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InputBlockedError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_definition() -> tuple[bytes, dict[str, Any]]:
    try:
        payload = _REPORT_PATH.read_bytes()
        record = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=_strict_object,
            parse_constant=lambda value: (_ for _ in ()).throw(
                InputBlockedError(f"non-finite JSON constant: {value}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputBlockedError("strategy definition JSON is invalid") from exc
    if type(record) is not dict:
        raise InputBlockedError("strategy definition must be a JSON object")
    return payload, record


def _definition_inclusion_rule_sha256(record: dict[str, Any]) -> str:
    try:
        value = record["outcome_blind_frozen_specification"][
            "expected_inclusion_rule_sha256"
        ]
    except (KeyError, TypeError) as exc:
        raise InputBlockedError("strategy definition inclusion rule is invalid") from exc
    return _sha256(value, "expected_inclusion_rule_sha256")


def _iso_date(value: object, field: str) -> date:
    if type(value) is not str:
        raise InputBlockedError(f"{field} must be an ISO date string")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise InputBlockedError(f"{field} must be an ISO date string") from exc
    if parsed.isoformat() != value:
        raise InputBlockedError(f"{field} must use canonical ISO format")
    return parsed


def _projection_rows(projection_bytes: bytes) -> tuple[dict[str, Any], ...]:
    if type(projection_bytes) is not bytes:
        raise InputBlockedError("official action projection must be immutable bytes")
    if hashlib.sha256(projection_bytes).hexdigest() != OFFICIAL_ACTION_PROJECTION_SHA256:
        raise InputBlockedError("official action projection full hash mismatch")
    try:
        text = projection_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise InputBlockedError("official action projection must be UTF-8") from exc
    lines = text.splitlines()
    if len(lines) != OFFICIAL_ACTION_COUNT or not text.endswith("\n"):
        raise InputBlockedError("official action projection must contain exactly 34 JSONL rows")
    rows: list[dict[str, Any]] = []
    for line in lines:
        try:
            row = json.loads(line, object_pairs_hook=_strict_object)
        except (json.JSONDecodeError, InputBlockedError) as exc:
            raise InputBlockedError("official action projection contains invalid JSON") from exc
        if type(row) is not dict or tuple(row) != _PROJECTION_KEYS:
            raise InputBlockedError("official action projection row schema/order mismatch")
        if any(type(value) is not str for value in row.values()):
            raise InputBlockedError("official action projection values must be strings")
        if row["symbol"] != "SPY" or row["event_type"] != "CASH_DISTRIBUTION":
            raise InputBlockedError("official action projection instrument/type mismatch")
        if row["available_at_basis"] != OFFICIAL_ACTION_AVAILABLE_AT_BASIS:
            raise InputBlockedError("official action availability basis mismatch")
        _sha256(row["source_document_sha256"], "source_document_sha256")
        if not row["source_url"].startswith("https://"):
            raise InputBlockedError("official action source must be HTTPS")
        ex_date = _iso_date(row["ex_date"], "ex_date")
        record_date = _iso_date(row["record_date"], "record_date")
        payment_date = _iso_date(row["payment_date"], "payment_date")
        if not ex_date <= record_date <= payment_date:
            raise InputBlockedError("official action date chronology mismatch")
        try:
            amount = Decimal(row["distribution"])
        except InvalidOperation as exc:
            raise InputBlockedError("official distribution must be decimal") from exc
        if not amount.is_finite() or amount <= 0:
            raise InputBlockedError("official distribution must be finite and positive")
        rows.append(row)
    dates = tuple(_iso_date(row["ex_date"], "ex_date") for row in rows)
    if tuple(sorted(dates)) != dates or len(set(dates)) != len(dates):
        raise InputBlockedError("official action rows must be uniquely date ordered")
    return tuple(rows)


def official_actions_from_projection(
    projection_bytes: bytes,
    calendar: AcceptedSessionCalendar,
) -> tuple[CorporateActionIdentity, ...]:
    """Parse all frozen bytes and materialize only the calendar-covered actions."""

    rows = _projection_rows(projection_bytes)
    actions: list[CorporateActionIdentity] = []
    for row in rows:
        ex_date = _iso_date(row["ex_date"], "ex_date")
        if not (
            calendar.identity.coverage_start
            <= ex_date
            <= calendar.identity.coverage_end
        ):
            continue
        try:
            session = calendar.session_on(ex_date, as_of=OFFICIAL_ACTION_RETRIEVED_AT)
        except (TypeError, ValueError) as exc:
            raise InputBlockedError(
                "official action ex-date lacks an accepted XNYS session"
            ) from exc
        source = SourceIdentity(
            row["source_url"],
            row["source_document_sha256"],
            OFFICIAL_ACTION_RETRIEVED_AT,
            OFFICIAL_ACTION_RETRIEVED_AT,
            f"ssga-distribution-{ex_date.isoformat()}",
        )
        actions.append(
            CorporateActionIdentity(
                "SPY",
                derived_action_id(ex_date),
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


def validate_runtime_authorization(
    authorization: RuntimeAuthorization | None,
    reconstruction_calendar: AcceptedSessionCalendar,
    points: tuple[ExecutionPoint, ...] = (),
    *,
    expected_calendar_projection_sha256: str = VALIDATION_CALENDAR_PROJECTION_SHA256,
) -> None:
    if not isinstance(authorization, RuntimeAuthorization):
        raise InputBlockedError(
            "real execution requires the current JSON identity and merged PR117 identity"
        )
    report_bytes, report = _read_definition()
    if report.get("status") != "PREREGISTERED_NOT_EXECUTED":
        raise InputBlockedError("current JSON status is not PREREGISTERED_NOT_EXECUTED")
    if authorization.preregistration_status != report["status"]:
        raise InputBlockedError("JSON current state is not PREREGISTERED_NOT_EXECUTED")
    if _sha256(authorization.preregistration_json_sha256, "preregistration_json_sha256") != (
        hashlib.sha256(report_bytes).hexdigest()
    ):
        raise InputBlockedError("preregistration JSON does not match current bytes")
    if _sha256(authorization.strategy_adapter_sha256, "strategy_adapter_sha256") != (
        _file_sha256(_ADAPTER_PATH)
    ):
        raise InputBlockedError("strategy adapter does not match current bytes")
    if authorization.causal_core_reviewed_head != PR117_REVIEWED_HEAD:
        raise InputBlockedError("causal core must equal the exact reviewed PR117 head")
    if authorization.causal_core_merged_main_head != PR117_MERGED_MAIN_HEAD:
        raise InputBlockedError("causal core must equal the merged PR117 main head")
    if authorization.status_core_reviewed_head != STATUS_CORE_REVIEWED_HEAD:
        raise InputBlockedError("status core must equal the exact reviewed head")
    if authorization.execution_core_reviewed_head != EXECUTION_CORE_REVIEWED_HEAD:
        raise InputBlockedError("execution core must equal the exact reviewed head")
    if authorization.strategy_runner_sha256 != _file_sha256(_RUNNER_PATH):
        raise InputBlockedError("strategy runner does not match current bytes")
    if authorization.reconstruction_calendar_identity_sha256 != calendar_identity_sha256(
        reconstruction_calendar.identity
    ):
        raise InputBlockedError("runtime reconstruction calendar identity mismatch")
    if (
        reconstruction_calendar.identity.source_identity.content_sha256
        != _sha256(
            expected_calendar_projection_sha256,
            "expected_calendar_projection_sha256",
        )
    ):
        raise InputBlockedError(
            "reconstruction calendar source is not the frozen ZoneInfo projection"
        )
    if points and authorization.calendar_epoch_mapping_sha256 != (
        calendar_epoch_mapping_sha256(points)
    ):
        raise InputBlockedError("runtime rolling calendar epoch mapping mismatch")
    if _definition_inclusion_rule_sha256(report) != EXPECTED_INCLUSION_RULE_SHA256:
        raise InputBlockedError("definition inclusion rule does not match frozen code")
    if authorization.qualified_market_rows_sha256 != QUALIFIED_MARKET_ROWS_SHA256:
        raise InputBlockedError("qualified market-row aggregate identity mismatch")
    _sha256(authorization.input_bundle_sha256, "input_bundle_sha256")


def assert_zero_distribution_execution_overlap(
    actions: tuple[CorporateActionIdentity, ...],
    first_session_executions: tuple[date, ...],
) -> None:
    execution_dates = set(first_session_executions)
    overlaps = tuple(
        action.action_id
        for action in actions
        if action.action_type in {"cash_dividend", "special_dividend"}
        and action.effective_date in execution_dates
    )
    if overlaps:
        raise InputBlockedError(
            "distribution/execution overlap drifted from the frozen count of zero"
        )


def _apply_daily_actions(
    portfolios: tuple[Portfolio, Portfolio],
    session_date: date,
    actions: tuple[CorporateActionIdentity, ...],
) -> None:
    for portfolio in portfolios:
        portfolio.start_session(session_date)
        for action in actions:
            if action.effective_date != session_date:
                continue
            if action.action_type in {"cash_dividend", "special_dividend"}:
                assert action.cash_amount is not None
                assert action.ex_date is not None and action.pay_date is not None
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
                raise InputBlockedError("unsupported action in daily accounting")


def _source_payload(source: SourceIdentity) -> dict[str, object]:
    return {
        "source_url": source.source_url,
        "content_sha256": source.content_sha256,
        "available_at": source.available_at.isoformat(),
        "retrieved_at": source.retrieved_at.isoformat(),
        "revision_id": source.revision_id,
        "supersedes_revision_id": source.supersedes_revision_id,
    }


def calendar_epoch_mapping_sha256(points: tuple[ExecutionPoint, ...]) -> str:
    if type(points) is not tuple or not points:
        raise InputBlockedError("calendar epoch mapping requires execution points")
    payload = []
    for point in points:
        if not isinstance(point, ExecutionPoint) or not isinstance(
            point.calendar, AcceptedSessionCalendar
        ):
            raise InputBlockedError("calendar epoch mapping requires accepted point calendars")
        calendar_sha = calendar_identity_sha256(point.calendar.identity)
        if point.universe_snapshot.calendar_identity_sha256 != calendar_sha:
            raise InputBlockedError("point universe snapshot/calendar identity mismatch")
        payload.append(
            {
                "execution_session": point.execution_session.isoformat(),
                "calendar_identity_sha256": calendar_sha,
                "execution_calendar_revision_identity_sha256": (
                    None
                    if point.execution_calendar_revision is None
                    else calendar_identity_sha256(
                        point.execution_calendar_revision.identity
                    )
                ),
            }
        )
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def official_actions_identity_sha256(
    actions: tuple[CorporateActionIdentity, ...],
) -> str:
    payload = [
        {
            "subject_id": action.subject_id,
            "action_id": action.action_id,
            "action_type": action.action_type,
            "effective_at": action.effective_at.isoformat(),
            "ex_date": None if action.ex_date is None else action.ex_date.isoformat(),
            "record_date": (
                None if action.record_date is None else action.record_date.isoformat()
            ),
            "pay_date": None if action.pay_date is None else action.pay_date.isoformat(),
            "cash_amount": (
                None if action.cash_amount is None else str(action.cash_amount)
            ),
            "currency": action.currency,
            "unit": action.unit,
            "source": _source_payload(action.source),
        }
        for action in actions
    ]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def runtime_market_rows_sha256(points: tuple[ExecutionPoint, ...]) -> str:
    if type(points) is not tuple or not points:
        raise InputBlockedError("runtime market rows require execution points")
    payload: list[dict[str, object]] = []
    for point in points:
        if not isinstance(point, ExecutionPoint):
            raise InputBlockedError("runtime market rows require ExecutionPoint values")
        payload.append(
            {
                "decision_at": point.decision_at.isoformat(),
                "execution_session": point.execution_session.isoformat(),
                "calendar_identity_sha256": calendar_identity_sha256(
                    point.calendar.identity
                ),
                "closes": [
                    {
                        "session_date": close.session_date.isoformat(),
                        "raw_close": float(close.raw_close).hex(),
                        "source": _source_payload(close.source),
                    }
                    for close in point.closes
                ],
                "execution": {
                    "open_price": None
                    if point.execution_input.open_price is None
                    else float(point.execution_input.open_price).hex(),
                    "decision_price": None
                    if point.execution_input.decision_price is None
                    else float(point.execution_input.decision_price).hex(),
                    "source": _source_payload(point.execution_input.source),
                    "decision_price_source": None
                    if point.execution_input.decision_price_source is None
                    else _source_payload(point.execution_input.decision_price_source),
                    "decision_price_basis": point.execution_input.decision_price_basis,
                    "execution_price_effective_at": (
                        None
                        if point.execution_input.execution_price_effective_at is None
                        else point.execution_input.execution_price_effective_at.isoformat()
                    ),
                    "execution_price_basis": point.execution_input.execution_price_basis,
                },
                "universe": {
                    "effective_session": point.universe_snapshot.effective_session.isoformat(),
                    "ordered_members_sha256": point.universe_snapshot.ordered_members_sha256,
                    "lifecycle_coverage_sha256": point.universe_snapshot.lifecycle_coverage_sha256,
                    "inclusion_rule_sha256": point.universe_snapshot.inclusion_rule_sha256,
                    "calendar_identity_sha256": point.universe_snapshot.calendar_identity_sha256,
                    "source": _source_payload(point.universe_snapshot.source_identity),
                },
            }
        )
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def runtime_input_bundle_sha256(
    reconstruction_calendar: AcceptedSessionCalendar,
    points: tuple[ExecutionPoint, ...],
    projection_bytes: bytes,
) -> str:
    official_actions = official_actions_from_projection(
        projection_bytes,
        reconstruction_calendar,
    )
    payload = {
        "reconstruction_calendar_identity_sha256": calendar_identity_sha256(
            reconstruction_calendar.identity
        ),
        "qualified_calendar_projection_sha256": (
            reconstruction_calendar.identity.source_identity.content_sha256
        ),
        "calendar_epoch_mapping_sha256": calendar_epoch_mapping_sha256(points),
        "qualified_market_rows_sha256": QUALIFIED_MARKET_ROWS_SHA256,
        "runtime_market_rows_sha256": runtime_market_rows_sha256(points),
        "action_projection_sha256": hashlib.sha256(projection_bytes).hexdigest(),
        "stage_official_action_count": len(official_actions),
        "official_actions_identity_sha256": official_actions_identity_sha256(
            official_actions
        ),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _point_signal(
    point: ExecutionPoint,
    official_actions: tuple[CorporateActionIdentity, ...],
):
    if not isinstance(point, ExecutionPoint):
        raise InputBlockedError("execution point identity is required")
    if point.universe_snapshot.inclusion_rule_sha256 != EXPECTED_INCLUSION_RULE_SHA256:
        raise InputBlockedError("universe snapshot inclusion rule does not match definition")
    if point.universe_snapshot.calendar_identity_sha256 != calendar_identity_sha256(
        point.calendar.identity
    ):
        raise InputBlockedError("execution point calendar does not match its universe snapshot")
    if point.universe_snapshot.effective_session != point.execution_session:
        raise InputBlockedError("universe snapshot/execution session mismatch")
    close_dates = tuple(close.session_date for close in point.closes)
    relevant = tuple(
        action for action in official_actions if action.effective_date in set(close_dates[1:])
    )
    if point.actions != relevant:
        raise InputBlockedError("execution point actions do not match exact projection contents")
    return build_signal_feature(
        point.calendar,
        point.closes,
        actions=point.actions,
        expected_action_ids=tuple(action.action_id for action in relevant),
        action_evidence_basis=RETROSPECTIVE_ACTION_BASIS,
        decision_at=point.decision_at,
        execution_session=point.execution_session,
    )


def _rebalance(
    portfolio: Portfolio,
    point: ExecutionPoint,
    authorization: RuntimeAuthorization,
    signal_session: date,
    target: float | None,
    prior_stage_hash: str,
):
    row = point.execution_input
    if row.symbol != "SPY" or row.market != "us":
        raise InputBlockedError("execution input must be the fixed US SPY instrument")
    if row.corporate_actions or row.action_types:
        raise InputBlockedError("daily actions must not be duplicated in the rebalance input")
    if row.decision_price_basis != "raw_execution_units":
        raise InputBlockedError("SPY decision price must use raw_execution_units")
    if row.execution_price_basis != "retrospective_daily_bar_open_fill":
        raise InputBlockedError("SPY execution open must use the retrospective daily-bar basis")
    execution = point.calendar.session_on(point.execution_session, as_of=point.decision_at)
    if row.execution_price_effective_at != execution.open_at:
        raise InputBlockedError("SPY execution event must equal the accepted-session open")
    execution_source_local = row.source.available_at.astimezone(_NEW_YORK)
    if execution_source_local.date() != point.execution_session or (
        execution_source_local.hour,
        execution_source_local.minute,
        execution_source_local.second,
        execution_source_local.microsecond,
    ) != (20, 0, 0, 0):
        raise InputBlockedError(
            "SPY retrospective open source must use the same-session 20:00 "
            "America/New_York convention"
        )
    final_close = point.closes[-1]
    if (
        row.decision_price != final_close.raw_close
        or row.decision_price_source != final_close.source
    ):
        raise InputBlockedError("SPY decision price must equal the final causal raw close")
    if point.universe_snapshot.inclusion_rule_sha256 != EXPECTED_INCLUSION_RULE_SHA256:
        raise InputBlockedError("universe snapshot inclusion rule does not match definition")
    if signal_session >= point.execution_session:
        raise InputBlockedError("signal/execution chronology is invalid")
    weights = {} if target is None else {"SPY": target}
    result = run_static_rebalance(
        portfolio,
        point.calendar,
        signal_session=signal_session,
        decision_at=point.decision_at,
        execution_inputs=(row,),
        execution_calendar_revision=point.execution_calendar_revision,
        universe_members=("SPY",),
        universe_snapshot=point.universe_snapshot,
        target_weights=lambda context: (
            weights
            if context.execution_session.session_date == point.execution_session
            else (_ for _ in ()).throw(InputBlockedError("execution session drift"))
        ),
        strategy_definition_sha256=authorization.preregistration_json_sha256,
        strategy_adapter_sha256=authorization.strategy_adapter_sha256,
        slippage_bps=ONE_WAY_SLIPPAGE_BPS,
        prior_stage_hash=prior_stage_hash,
    )
    return result


def _simulate_cohorts(
    reconstruction_calendar: AcceptedSessionCalendar,
    entry_points: tuple[ExecutionPoint, ...],
    final_exit: ExecutionPoint,
    *,
    daily_sessions: tuple[date, ...],
    action_projection_bytes: bytes,
    authorization: RuntimeAuthorization,
    expected_months: tuple[tuple[int, int], ...],
    expected_calendar_bounds: tuple[date, date],
    expected_calendar_session_count: int,
    expected_official_action_count: int,
    expected_calendar_projection_sha256: str,
    expected_input_bundle_sha256: str | None,
) -> CohortSimulation:
    """Run one fresh strategy/benchmark split solely from injected immutable rows."""

    if reconstruction_calendar.identity.coverage_start != expected_calendar_bounds[0] or (
        reconstruction_calendar.identity.coverage_end != expected_calendar_bounds[1]
    ):
        raise InputBlockedError("stage calendar coverage does not match frozen bounds")
    if (
        reconstruction_calendar.identity.session_count != expected_calendar_session_count
        or len(reconstruction_calendar.session_dates) != expected_calendar_session_count
    ):
        raise InputBlockedError("stage calendar session count does not match frozen count")
    official_actions = official_actions_from_projection(
        action_projection_bytes,
        reconstruction_calendar,
    )
    if len(official_actions) != expected_official_action_count:
        raise InputBlockedError("stage official action count does not match frozen count")
    all_points = entry_points + (final_exit,)
    validate_runtime_authorization(
        authorization,
        reconstruction_calendar,
        all_points,
        expected_calendar_projection_sha256=expected_calendar_projection_sha256,
    )
    expected_cohorts = len(expected_months)
    if len(entry_points) != expected_cohorts or expected_cohorts < 2:
        raise InputBlockedError("split entry cohort count is incomplete")
    actual_months = tuple(
        (point.execution_session.year, point.execution_session.month) for point in entry_points
    )
    if actual_months != expected_months:
        raise InputBlockedError("entry points do not match the exact frozen cohort months")
    last_year, last_month = expected_months[-1]
    expected_final_month = (last_year + 1, 1) if last_month == 12 else (last_year, last_month + 1)
    if (
        final_exit.execution_session.year,
        final_exit.execution_session.month,
    ) != expected_final_month:
        raise InputBlockedError("final exit does not match the exact frozen exit month")
    actual_bundle_sha = runtime_input_bundle_sha256(
        reconstruction_calendar,
        all_points,
        action_projection_bytes,
    )
    if expected_input_bundle_sha256 is None:
        raise InputBlockedError("runtime input bundle identity has not been frozen")
    if (
        authorization.input_bundle_sha256 != expected_input_bundle_sha256
        or actual_bundle_sha != expected_input_bundle_sha256
    ):
        raise InputBlockedError("runtime input bundle content identity mismatch")
    signals = {
        point.execution_session: _point_signal(point, official_actions)
        for point in all_points
    }
    execution_dates = tuple(point.execution_session for point in entry_points) + (
        final_exit.execution_session,
    )
    if any(
        current >= following for current, following in zip(execution_dates, execution_dates[1:])
    ):
        raise InputBlockedError("entry and exit sessions must be strictly chronological")
    assert_zero_distribution_execution_overlap(official_actions, execution_dates)
    expected_daily = tuple(
        day
        for day in reconstruction_calendar.session_dates
        if execution_dates[0] <= day <= execution_dates[-1]
    )
    if daily_sessions != expected_daily:
        raise InputBlockedError("daily sessions must be complete, accepted, and consecutive")
    point_by_date = {point.execution_session: point for point in entry_points}
    if len(point_by_date) != len(entry_points) or final_exit.execution_session in point_by_date:
        raise InputBlockedError("duplicate execution point")

    strategy = Portfolio.us(INITIAL_CAPITAL)
    benchmark = Portfolio.us(INITIAL_CAPITAL)
    strategy_navs = [INITIAL_CAPITAL]
    benchmark_navs = [INITIAL_CAPITAL]
    strategy_receipts: list[ExecutionReceipt] = []
    benchmark_receipts: list[ExecutionReceipt] = []
    strategy_stage = "0" * 64
    benchmark_stage = "0" * 64

    for session_date in daily_sessions:
        _apply_daily_actions((strategy, benchmark), session_date, official_actions)
        point = point_by_date.get(session_date)
        if point is None and session_date != final_exit.execution_session:
            continue
        if point is not None:
            strategy_result = _rebalance(
                strategy,
                point,
                authorization,
                signals[point.execution_session].signal_session,
                signals[point.execution_session].target_weight,
                strategy_stage,
            )
            strategy = strategy_result.portfolio
            strategy_stage = strategy_result.stage_hash
            strategy_receipts.extend(strategy_result.receipts)
            if point is entry_points[0]:
                benchmark_result = _rebalance(
                    benchmark,
                    point,
                    authorization,
                    signals[point.execution_session].signal_session,
                    1.0,
                    benchmark_stage,
                )
                benchmark = benchmark_result.portfolio
                benchmark_stage = benchmark_result.stage_hash
                benchmark_receipts.extend(benchmark_result.receipts)
                continue
            raw_open = point.execution_input.open_price
            if (
                isinstance(raw_open, bool)
                or raw_open is None
                or not math.isfinite(raw_open)
                or raw_open <= 0
            ):
                raise InputBlockedError("benchmark boundary requires a finite positive raw open")
            strategy_navs.append(strategy_result.final_nav)
            benchmark_navs.append(benchmark.nav({"SPY": float(raw_open)}))
            continue

        strategy_result = _rebalance(
            strategy,
            final_exit,
            authorization,
            signals[final_exit.execution_session].signal_session,
            None,
            strategy_stage,
        )
        benchmark_result = _rebalance(
            benchmark,
            final_exit,
            authorization,
            signals[final_exit.execution_session].signal_session,
            None,
            benchmark_stage,
        )
        strategy = strategy_result.portfolio
        benchmark = benchmark_result.portfolio
        strategy_receipts.extend(strategy_result.receipts)
        benchmark_receipts.extend(benchmark_result.receipts)
        strategy_navs.append(strategy_result.final_nav)
        benchmark_navs.append(benchmark_result.final_nav)

    strategy_boundaries = tuple(strategy_navs)
    benchmark_boundaries = tuple(benchmark_navs)
    return CohortSimulation(
        strategy_boundaries,
        benchmark_boundaries,
        cohort_returns(strategy_boundaries, expected_cohorts=expected_cohorts),
        cohort_returns(benchmark_boundaries, expected_cohorts=expected_cohorts),
        tuple(strategy_receipts),
        tuple(benchmark_receipts),
    )


def _require_query_bounds(
    query_start: date,
    query_end: date,
    expected: tuple[date, date],
    stage: str,
) -> None:
    if type(query_start) is not date or type(query_end) is not date or query_start > query_end:
        raise InputBlockedError(f"{stage} query bounds are invalid")
    if (query_start, query_end) != expected:
        raise InputBlockedError(f"{stage} query bounds must equal the exact frozen interval")


def _validation_receipt_digest(
    strategy_navs: tuple[float, ...],
    benchmark_navs: tuple[float, ...],
) -> str:
    strategy_returns = cohort_returns(strategy_navs, expected_cohorts=45)
    benchmark_returns = cohort_returns(benchmark_navs, expected_cohorts=45)
    decision = validation_gate_decision(
        strategy_returns,
        benchmark_returns,
        strategy_navs,
        benchmark_navs,
    )
    payload = {
        "stage": "validation",
        "query_start": VALIDATION_QUERY_BOUNDS[0].isoformat(),
        "query_end": VALIDATION_QUERY_BOUNDS[1].isoformat(),
        "strategy_boundary_navs": [float(value).hex() for value in strategy_navs],
        "benchmark_boundary_navs": [float(value).hex() for value in benchmark_navs],
        "strategy_returns": [float(value).hex() for value in strategy_returns],
        "benchmark_returns": [float(value).hex() for value in benchmark_returns],
        "gates": list(decision.gates),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def validation_receipt(simulation: CohortSimulation) -> ValidationReceipt:
    if not isinstance(simulation, CohortSimulation):
        raise InputBlockedError("validation receipt requires an actual cohort simulation")
    digest = _validation_receipt_digest(
        simulation.strategy_boundary_navs,
        simulation.benchmark_boundary_navs,
    )
    return ValidationReceipt(
        simulation.strategy_boundary_navs,
        simulation.benchmark_boundary_navs,
        digest,
    )


def require_holdout_unlocked(receipt: object) -> None:
    if not isinstance(receipt, ValidationReceipt):
        raise InputBlockedError("holdout requires an immutable validation receipt")
    if _sha256(receipt.result_sha256, "validation result_sha256") != (
        _validation_receipt_digest(
            receipt.strategy_boundary_navs,
            receipt.benchmark_boundary_navs,
        )
    ):
        raise InputBlockedError("validation receipt content identity mismatch")
    strategy_returns = cohort_returns(receipt.strategy_boundary_navs, expected_cohorts=45)
    benchmark_returns = cohort_returns(receipt.benchmark_boundary_navs, expected_cohorts=45)
    decision = validation_gate_decision(
        strategy_returns,
        benchmark_returns,
        receipt.strategy_boundary_navs,
        receipt.benchmark_boundary_navs,
    )
    if not decision.all_gates_pass:
        raise InputBlockedError("holdout requires recomputed all-gates-true validation evidence")


def simulate_validation(
    calendar: AcceptedSessionCalendar,
    entry_points: tuple[ExecutionPoint, ...],
    final_exit: ExecutionPoint,
    *,
    daily_sessions: tuple[date, ...],
    action_projection_bytes: bytes,
    authorization: RuntimeAuthorization,
    query_start: date,
    query_end: date,
) -> CohortSimulation:
    _require_query_bounds(query_start, query_end, VALIDATION_QUERY_BOUNDS, "validation")
    return _simulate_cohorts(
        calendar,
        entry_points,
        final_exit,
        daily_sessions=daily_sessions,
        action_projection_bytes=action_projection_bytes,
        authorization=authorization,
        expected_months=VALIDATION_ENTRY_MONTHS,
        expected_calendar_bounds=VALIDATION_QUERY_BOUNDS,
        expected_calendar_session_count=VALIDATION_CALENDAR_SESSION_COUNT,
        expected_official_action_count=VALIDATION_OFFICIAL_ACTION_COUNT,
        expected_calendar_projection_sha256=VALIDATION_CALENDAR_PROJECTION_SHA256,
        expected_input_bundle_sha256=VALIDATION_RUNTIME_INPUT_BUNDLE_SHA256,
    )


def simulate_holdout(
    validation_result: ValidationReceipt,
    calendar: AcceptedSessionCalendar,
    entry_points: tuple[ExecutionPoint, ...],
    final_exit: ExecutionPoint,
    *,
    daily_sessions: tuple[date, ...],
    action_projection_bytes: bytes,
    authorization: RuntimeAuthorization,
    query_start: date,
    query_end: date,
) -> CohortSimulation:
    require_holdout_unlocked(validation_result)
    _require_query_bounds(query_start, query_end, HOLDOUT_QUERY_BOUNDS, "holdout")
    if HOLDOUT_CALENDAR_PROJECTION_SHA256 is None:
        raise InputBlockedError("holdout calendar identity has not been qualified")
    if HOLDOUT_RUNTIME_INPUT_BUNDLE_SHA256 is None:
        raise InputBlockedError("holdout runtime input bundle identity has not been frozen")
    if HOLDOUT_CALENDAR_SESSION_COUNT is None or HOLDOUT_OFFICIAL_ACTION_COUNT is None:
        raise InputBlockedError("holdout calendar/action dimensions have not been frozen")
    return _simulate_cohorts(
        calendar,
        entry_points,
        final_exit,
        daily_sessions=daily_sessions,
        action_projection_bytes=action_projection_bytes,
        authorization=authorization,
        expected_months=HOLDOUT_ENTRY_MONTHS,
        expected_calendar_bounds=HOLDOUT_QUERY_BOUNDS,
        expected_calendar_session_count=HOLDOUT_CALENDAR_SESSION_COUNT,
        expected_official_action_count=HOLDOUT_OFFICIAL_ACTION_COUNT,
        expected_calendar_projection_sha256=HOLDOUT_CALENDAR_PROJECTION_SHA256,
        expected_input_bundle_sha256=HOLDOUT_RUNTIME_INPUT_BUNDLE_SHA256,
    )


def classify_terminal(*, stage: str, complete: bool, passed: bool) -> TerminalClassification:
    if not complete:
        return TerminalClassification("INPUT_BLOCKED", True, False)
    if stage == "validation":
        if passed:
            raise InputContractError("a validation pass unlocks holdout and is not terminal")
        return TerminalClassification("HISTORICAL_VALIDATION_FAIL", True, False)
    if stage != "holdout":
        raise InputContractError("stage must be validation or holdout")
    if not passed:
        return TerminalClassification("HISTORICAL_HOLDOUT_FAIL", True, True)
    return TerminalClassification(
        "HISTORICAL_PASS_PENDING_EXTERNAL_REVIEW",
        False,
        True,
    )


def derived_action_id(ex_date: date) -> str:
    """Deterministic fallback identity; runtime must still equal PR117's exact tuple."""

    if type(ex_date) is not date:
        raise InputBlockedError("ex_date must be a date")
    payload = f"{OFFICIAL_ACTION_PROJECTION_SHA256}|SPY|{ex_date.isoformat()}"
    return "spy-state-street-" + hashlib.sha256(payload.encode()).hexdigest()


def _capture_bundle(path: Path) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid():
            raise InputBlockedError("bundle must be an owner-controlled regular file")
        if stat.S_IMODE(before.st_mode) & ~0o600 or not 0 < before.st_size <= 8 * 1024 * 1024:
            raise InputBlockedError("bundle mode or size is outside the frozen limit")
        payload = b""
        while chunk := os.read(fd, 1024 * 1024):
            payload += chunk
            if len(payload) > 8 * 1024 * 1024:
                raise InputBlockedError("bundle exceeds the frozen size limit")
        after = os.fstat(fd)
    finally:
        os.close(fd)
    current = os.stat(path, follow_symlinks=False)
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(getattr(before, key) != getattr(after, key) or getattr(after, key) != getattr(current, key) for key in fields):
        raise InputBlockedError("bundle changed during descriptor-bound capture")
    if hashlib.sha256(payload).hexdigest() != VALIDATION_BUNDLE_FILE_SHA256:
        raise InputBlockedError("bundle raw SHA-256 mismatch")
    return payload


def _source(row: dict[str, Any]) -> SourceIdentity:
    return SourceIdentity(row["source_url"], row["content_sha256"], datetime.fromisoformat(row["available_at"]), datetime.fromisoformat(row["retrieved_at"]), row["revision_id"], row["supersedes_revision_id"])


def _calendar(row: dict[str, Any]) -> AcceptedSessionCalendar:
    sessions = tuple(
        AcceptedSession(
            _iso_date(item["session_date"], "session_date"), datetime.fromisoformat(item["open_at"]),
            datetime.fromisoformat(item["close_at"]), SourceIdentity(
                item["source_url"], item["source_document_set_sha256"],
                datetime.fromisoformat(item["source_available_at"]), OFFICIAL_ACTION_RETRIEVED_AT,
                item["snapshot_id"],
            ), item["timezone"], item["early_close"], item["exchange"],
        )
        for item in row["session_rows"]
    )
    identity = row["calendar_identity"]
    calendar = AcceptedSessionCalendar(
        sessions,
        identity=CalendarIdentity(
            identity["exchange_id"], identity["exchange_timezone"],
            _iso_date(identity["coverage_start"], "coverage_start"),
            _iso_date(identity["coverage_end"], "coverage_end"), identity["session_count"],
            identity["session_dates_sha256"], identity["session_rows_sha256"],
            _source(identity["source_identity"]),
        ),
    )
    return calendar


def _load_validation_bundle(payload: bytes) -> tuple[Any, ...]:
    try:
        record = json.loads(
            payload.decode("utf-8", errors="strict"), object_pairs_hook=_strict_object,
            parse_constant=lambda value: (_ for _ in ()).throw(InputBlockedError(value)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputBlockedError("bundle is not strict UTF-8 JSON") from exc
    if (record["schema_version"], record["stage"], record["symbol"]) != (
        "us-spy-vol-managed-validation-runtime-input-v1", "validation", "SPY",
    ) or (record["query_start"], record["query_end"]) != (
        VALIDATION_QUERY_BOUNDS[0].isoformat(), VALIDATION_QUERY_BOUNDS[1].isoformat(),
    ):
        raise InputBlockedError("bundle fixed identity mismatch")
    reconstruction = _calendar(record["reconstruction_calendar"])
    epoch_rows = record["calendar_epochs"]
    epochs = tuple(_calendar(epoch_rows[key]) for key in ("a0", "a1", "b"))
    by_id = {item.identity.source_identity.revision_id: item for item in epochs}
    if len(by_id) != 3 or epoch_rows["point_mapping_sha256"] != VALIDATION_CALENDAR_MAPPING_FILE_SHA256:
        raise InputBlockedError("calendar epoch identity mismatch")
    projection = record["action_projection_jsonl"].encode()
    official_actions = official_actions_from_projection(projection, reconstruction)
    points: list[ExecutionPoint] = []
    for item in record["execution_points"]:
        decision = datetime.fromisoformat(item["decision_at"])
        closes = tuple(
            CloseObservation(
                _iso_date(row["session_date"], "close session"), row["raw_close"], _source(row["source"])
            )
            for row in item["trailing_22_closes"]
        )
        statuses = tuple(
            StatusEvidence(
                row["status_id"], row["symbol"], row["kind"], row["value"],
                _iso_date(row["effective_from"], "effective_from"),
                None if row["effective_to"] is None else _iso_date(row["effective_to"], "effective_to"),
                row["exchange_timezone"], _source(row["source"]),
            )
            for row in item["status_evidence"]
        )
        raw = item["execution"]
        execution_day = _iso_date(raw["session_date"], "execution session")
        execution = ExecutionInput(
            raw["symbol"], raw["market"], raw["raw_open"], raw["currency"],
            _source(raw["source"]), statuses, decision_price=raw["decision_price"],
            decision_price_source=_source(raw["decision_price_source"]),
            decision_price_basis=raw["decision_price_basis"],
            execution_price_effective_at=datetime.fromisoformat(raw["execution_price_effective_at"]),
            execution_price_basis=raw["execution_price_basis"],
        )
        raw = item["universe_snapshot"]
        snapshot = UniverseSnapshotIdentity(
            raw["market"], raw["exchange_id"], _iso_date(raw["effective_session"], "effective_session"),
            raw["member_count"], raw["ordered_members_sha256"], raw["lifecycle_coverage_sha256"],
            raw["inclusion_rule_sha256"], raw["calendar_identity_sha256"], _source(raw["source_identity"]),
        )
        calendar = by_id[item["decision_calendar_epoch_id"]]
        revision_id = item["execution_calendar_revision_id"]
        revision = None if revision_id is None else by_id[revision_id]
        point = ExecutionPoint(
            closes, tuple(action for action in official_actions if action.effective_date in {row.session_date for row in closes[1:]}),
            calendar, decision, execution_day, execution, snapshot, revision,
        )
        validate_universe_snapshot(
            snapshot, market="us", calendar_identity=calendar.identity,
            session=calendar.session_on(execution_day, as_of=decision), decision_at=decision,
            members=("SPY",), records_by_symbol={"SPY": statuses},
        )
        if closes[-1].session_date.isoformat() != item["signal_session"]:
            raise InputBlockedError("signal-session identity mismatch")
        points.append(point)
    frozen = tuple(points)
    if len(frozen) != 46 or len(reconstruction.session_dates) != 987:
        raise InputBlockedError("bundle dimensions mismatch")
    identities = (calendar_identity_sha256(reconstruction.identity), calendar_epoch_mapping_sha256(frozen),
                  runtime_market_rows_sha256(frozen), official_actions_identity_sha256(official_actions))
    if identities != (VALIDATION_CALENDAR_IDENTITY_SHA256, VALIDATION_CALENDAR_MAPPING_SHA256,
                      VALIDATION_MARKET_RUNTIME_SHA256, VALIDATION_ACTION_IDENTITY_SHA256):
        raise InputBlockedError("calendar/market/action semantic identity mismatch")
    if runtime_input_bundle_sha256(reconstruction, frozen, projection) != VALIDATION_RUNTIME_INPUT_BUNDLE_SHA256:
        raise InputBlockedError("runtime semantic identity mismatch")
    daily = tuple(_iso_date(row["session_date"], "daily session") for row in record["daily_sessions"])
    return reconstruction, frozen[:-1], frozen[-1], daily, projection


def _target(path: Path) -> None:
    parent = path.parent.stat()
    if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.getuid() or stat.S_IMODE(parent.st_mode) & ~0o700 or path.exists() or path.is_symlink()):
        raise InputBlockedError("claim/result path must be absent beneath an owner-private directory")


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
    return hashlib.sha256(payload).hexdigest()


def _run_once(bundle: Path, claim: Path, result: Path, expected: tuple[str, str, str]) -> int:
    report_bytes, report = _read_definition()
    actual = (hashlib.sha256(report_bytes).hexdigest(), _file_sha256(_ADAPTER_PATH), _file_sha256(_RUNNER_PATH))
    if tuple(_sha256(value, "expected code identity") for value in expected) != actual or report.get("status") != "PREREGISTERED_NOT_EXECUTED":
        raise InputBlockedError("definition/adapter/runner identity mismatch")
    if claim == result:
        raise InputBlockedError("claim and result paths must differ")
    _target(result)
    claim_sha = _publish(claim, {"research_id": "US_SPY_VOLATILITY_MANAGED_EXPOSURE_V1",
        "stage": "validation", "claimed_at": datetime.now(timezone.utc).isoformat(),
        "bundle_file_sha256": VALIDATION_BUNDLE_FILE_SHA256, "definition_sha256": actual[0],
        "adapter_sha256": actual[1], "runner_sha256": actual[2]})
    calendar, entries, final_exit, daily_sessions, projection = _load_validation_bundle(_capture_bundle(bundle))
    authorization = RuntimeAuthorization(report["status"], actual[0], actual[1], PR117_REVIEWED_HEAD,
        PR117_MERGED_MAIN_HEAD, STATUS_CORE_REVIEWED_HEAD, EXECUTION_CORE_REVIEWED_HEAD, actual[2],
        VALIDATION_CALENDAR_IDENTITY_SHA256, VALIDATION_CALENDAR_MAPPING_SHA256,
        QUALIFIED_MARKET_ROWS_SHA256, VALIDATION_RUNTIME_INPUT_BUNDLE_SHA256)
    simulation = simulate_validation(
        calendar, entries, final_exit, daily_sessions=daily_sessions,
        action_projection_bytes=projection, authorization=authorization,
        query_start=VALIDATION_QUERY_BOUNDS[0], query_end=VALIDATION_QUERY_BOUNDS[1],
    )
    decision = validation_gate_decision(simulation.strategy_returns, simulation.benchmark_returns,
        simulation.strategy_boundary_navs, simulation.benchmark_boundary_navs)
    receipt = validation_receipt(simulation)
    _publish(result, {
        "research_id": "US_SPY_VOLATILITY_MANAGED_EXPOSURE_V1", "stage": "validation",
        "classification": "VALIDATION_PASS_HOLDOUT_LOCKED" if decision.all_gates_pass else "HISTORICAL_VALIDATION_FAIL",
        "completed": True, "observed_cohorts": decision.observed_cohorts, "gates": dict(decision.gates),
        "strategy_metrics_hex": {key: float(value).hex() for key, value in vars(decision.strategy).items()},
        "benchmark_metrics_hex": {key: float(value).hex() for key, value in vars(decision.benchmark).items()},
        "strategy_boundary_navs_hex": [float(value).hex() for value in simulation.strategy_boundary_navs],
        "benchmark_boundary_navs_hex": [float(value).hex() for value in simulation.benchmark_boundary_navs],
        "validation_receipt_sha256": receipt.result_sha256, "claim_sha256": claim_sha,
        "bundle_file_sha256": VALIDATION_BUNDLE_FILE_SHA256, "runtime_bundle_sha256": VALIDATION_RUNTIME_INPUT_BUNDLE_SHA256,
        "code_and_core_sha256": {"definition": actual[0], "adapter": actual[1], "runner": actual[2], "causal_core": PR117_REVIEWED_HEAD, "status_core": STATUS_CORE_REVIEWED_HEAD, "execution_core": EXECUTION_CORE_REVIEWED_HEAD}, "input_semantic_sha256": {"reconstruction_calendar": VALIDATION_CALENDAR_IDENTITY_SHA256, "calendar_mapping": VALIDATION_CALENDAR_MAPPING_SHA256, "market_rows": VALIDATION_MARKET_RUNTIME_SHA256, "actions": VALIDATION_ACTION_IDENTITY_SHA256},
        "holdout_opened": False, "strategy_candidate_available": False,
    })
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    for name in ("bundle", "claim", "result"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    for name in ("definition", "adapter", "runner"):
        parser.add_argument(f"--expected-{name}-sha256", required=True)
    args = parser.parse_args(argv)
    expected = (args.expected_definition_sha256, args.expected_adapter_sha256, args.expected_runner_sha256)
    return _run_once(args.bundle, args.claim, args.result, expected)


if __name__ == "__main__":
    main()
