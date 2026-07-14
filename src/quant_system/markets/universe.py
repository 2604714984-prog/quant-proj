"""Effective-dated, availability-aware security-universe predicate."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from .common import (
    MarketDataError,
    require_aware_datetime,
    require_date,
    require_nonempty_text,
    require_sha256,
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
    symbol: str
    kind: StatusKind
    value: bool
    effective_from: date
    effective_to: date | None
    available_at: datetime
    identity: str
    source_sha256: str

    def __post_init__(self) -> None:
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
        require_aware_datetime(self.available_at, "available_at")
        require_nonempty_text(self.identity, "identity")
        require_sha256(self.source_sha256)

    def effective_on(self, session: date) -> bool:
        return self.effective_from <= session and (
            self.effective_to is None or session < self.effective_to
        )


@dataclass(frozen=True)
class UniverseDecision:
    eligible: bool
    reasons: tuple[str, ...]
    evidence: tuple[tuple[StatusKind, str, str], ...]


def evaluate_universe(
    symbol: str,
    session: date,
    available_at_cutoff: datetime,
    records: tuple[StatusEvidence, ...] | list[StatusEvidence],
) -> UniverseDecision:
    """Evaluate a symbol only from complete status facts known by the cutoff."""

    symbol = require_nonempty_text(symbol, "symbol")
    require_date(session, "session")
    cutoff = require_aware_datetime(available_at_cutoff, "available_at_cutoff")
    frozen = tuple(records)
    if any(not isinstance(record, StatusEvidence) for record in frozen):
        raise MarketDataError("records must contain only StatusEvidence values")
    selected: dict[StatusKind, StatusEvidence] = {}
    for kind in REQUIRED_STATUS_KINDS:
        matches = tuple(
            record
            for record in frozen
            if record.symbol == symbol
            and record.kind == kind
            and record.effective_on(session)
            and record.available_at <= cutoff
        )
        if not matches:
            raise MarketDataError(
                f"missing effective {kind} identity available by the cutoff"
            )
        if len(matches) != 1:
            raise MarketDataError(f"ambiguous effective {kind} identity")
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
        (kind, selected[kind].identity, selected[kind].source_sha256)
        for kind in REQUIRED_STATUS_KINDS
    )
    return UniverseDecision(not reasons, tuple(reasons), evidence)
