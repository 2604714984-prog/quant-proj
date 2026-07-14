"""Effective-dated security-universe predicate over accepted PIT identities."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from quant_system.data import AcceptedSession, SourceIdentity, select_source_revision

from .common import (
    MarketDataError,
    require_aware_datetime,
    require_date,
    require_nonempty_text,
)

StatusKind = Literal["listed", "delisted", "st", "suspended"]
REQUIRED_STATUS_KINDS: tuple[StatusKind, ...] = (
    "listed",
    "delisted",
    "st",
    "suspended",
)


@dataclass(frozen=True)
class StatusEvidence:
    status_id: str
    symbol: str
    kind: StatusKind
    value: bool
    effective_from: date
    effective_to: date | None
    exchange_timezone: str
    source: SourceIdentity

    def __post_init__(self) -> None:
        require_nonempty_text(self.status_id, "status_id")
        require_nonempty_text(self.symbol, "symbol")
        if self.kind not in REQUIRED_STATUS_KINDS:
            raise MarketDataError(f"unsupported status kind: {self.kind!r}")
        if type(self.value) is not bool:
            raise MarketDataError("status value must be boolean")
        require_date(self.effective_from, "effective_from")
        if self.effective_to is not None:
            require_date(self.effective_to, "effective_to")
            if self.effective_to <= self.effective_from:
                raise MarketDataError("effective_to must be later than effective_from")
        timezone_name = require_nonempty_text(self.exchange_timezone, "exchange_timezone")
        try:
            ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise MarketDataError("exchange_timezone must be an installed IANA timezone") from exc
        if not isinstance(self.source, SourceIdentity):
            raise MarketDataError("source must be a canonical SourceIdentity")

    def effective_on(self, session: date) -> bool:
        return self.effective_from <= session and (
            self.effective_to is None or session < self.effective_to
        )


@dataclass(frozen=True)
class UniverseDecision:
    eligible: bool
    reasons: tuple[str, ...]
    evidence: tuple[tuple[StatusKind, str, SourceIdentity], ...]


def evaluate_universe(
    symbol: str,
    session: AcceptedSession,
    decision_at: datetime,
    records: tuple[StatusEvidence, ...] | list[StatusEvidence],
) -> UniverseDecision:
    """Evaluate a symbol from one complete, nonoverlapping PIT status set."""

    symbol = require_nonempty_text(symbol, "symbol")
    if not isinstance(session, AcceptedSession):
        raise MarketDataError("session must be an AcceptedSession")
    cutoff = require_aware_datetime(decision_at, "decision_at")
    if cutoff > session.open_at:
        raise MarketDataError("decision_at cannot follow the accepted-session open")
    if session.source.available_at > cutoff:
        raise MarketDataError("accepted-session source was unavailable at decision_at")
    frozen = tuple(records)
    if any(not isinstance(record, StatusEvidence) for record in frozen):
        raise MarketDataError("records must contain only StatusEvidence values")
    global_identities: dict[str, list[StatusEvidence]] = defaultdict(list)
    for record in frozen:
        global_identities[record.status_id].append(record)
    for revisions in global_identities.values():
        identities = {
            (record.symbol, record.kind, record.exchange_timezone)
            for record in revisions
        }
        if len(identities) != 1:
            raise MarketDataError(
                "status revisions must share symbol, kind, and exchange_timezone"
            )

    selected: dict[StatusKind, StatusEvidence] = {}
    for kind in REQUIRED_STATUS_KINDS:
        candidates = tuple(
            record
            for record in frozen
            if record.symbol == symbol
            and record.kind == kind
        )
        by_status_id: dict[str, list[StatusEvidence]] = defaultdict(list)
        for record in candidates:
            by_status_id[record.status_id].append(record)
        matches: list[StatusEvidence] = []
        for revisions in by_status_id.values():
            if len({record.exchange_timezone for record in revisions}) != 1:
                raise MarketDataError(f"{kind} revisions cannot mix exchange timezones")
            if all(record.source.available_at > cutoff for record in revisions):
                continue
            selected_source = select_source_revision(
                (record.source for record in revisions),
                as_of=cutoff,
            )
            selected_record = next(
                record for record in revisions if record.source == selected_source
            )
            if selected_record.effective_on(session.session_date):
                if selected_record.exchange_timezone != session.exchange_timezone:
                    raise MarketDataError(
                        f"effective {kind} evidence uses a different exchange timezone"
                    )
                matches.append(selected_record)
        if not matches:
            raise MarketDataError(
                f"missing effective {kind} identity available by decision_at"
            )
        if len(matches) != 1:
            raise MarketDataError(f"overlapping effective {kind} identities")
        selected[kind] = matches[0]

    reasons: list[str] = []
    if not selected["listed"].value:
        reasons.append("not_listed")
    if selected["delisted"].value:
        reasons.append("delisted")
    if selected["st"].value:
        reasons.append("st")
    if selected["suspended"].value:
        reasons.append("suspended")
    evidence = tuple(
        (kind, selected[kind].status_id, selected[kind].source)
        for kind in REQUIRED_STATUS_KINDS
    )
    return UniverseDecision(not reasons, tuple(reasons), evidence)
