"""Dependency-free accepted-session calendar backed by provided rows."""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .source_identity import (
    SourceIdentity,
    TypedObservationReceipt,
    require_aware_utc,
    require_sha256,
)


class CalendarIdentityError(ValueError):
    """Raised when an accepted calendar is unavailable or inconsistent."""


def session_dates_sha256(session_dates: Iterable[date]) -> str:
    """Hash one explicitly ordered accepted-session date set."""

    dates = tuple(session_dates)
    if not dates or any(type(day) is not date for day in dates):
        raise CalendarIdentityError("session_dates must contain at least one date")
    encoded = "\n".join(day.isoformat() for day in dates).encode()
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class CalendarIdentity:
    """Preaccepted identity whose bounds are the first and last accepted sessions."""

    exchange_id: str
    exchange_timezone: str
    coverage_start: date
    coverage_end: date
    session_count: int
    session_dates_sha256: str
    session_rows_sha256: str
    source_identity: SourceIdentity

    def __post_init__(self) -> None:
        exchange_id = str(self.exchange_id).strip()
        if not exchange_id:
            raise CalendarIdentityError("exchange_id is required")
        timezone_name = str(self.exchange_timezone).strip()
        if not timezone_name:
            raise CalendarIdentityError("exchange_timezone is required")
        try:
            ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise CalendarIdentityError(
                "exchange_timezone must name an installed IANA timezone"
            ) from exc
        if type(self.coverage_start) is not date or type(self.coverage_end) is not date:
            raise CalendarIdentityError("coverage bounds must be dates")
        if self.coverage_start > self.coverage_end:
            raise CalendarIdentityError("coverage_start cannot follow coverage_end")
        if type(self.session_count) is not int or self.session_count < 1:
            raise CalendarIdentityError("session_count must be a positive integer")
        for field_name in ("session_dates_sha256", "session_rows_sha256"):
            try:
                digest = require_sha256(getattr(self, field_name), field_name)
            except ValueError as exc:
                raise CalendarIdentityError(str(exc)) from exc
            object.__setattr__(self, field_name, digest)
        if not isinstance(self.source_identity, SourceIdentity):
            raise CalendarIdentityError("source_identity must be a SourceIdentity")
        object.__setattr__(self, "exchange_id", exchange_id)
        object.__setattr__(self, "exchange_timezone", timezone_name)


@dataclass(frozen=True)
class AcceptedSession:
    session_date: date
    open_at: datetime
    close_at: datetime
    source: SourceIdentity
    exchange_timezone: str
    is_early_close: bool = False
    exchange_id: str = ""
    observation_receipt: TypedObservationReceipt | None = None

    def __post_init__(self) -> None:
        if type(self.session_date) is not date:
            raise CalendarIdentityError("session_date must be a date")
        if not isinstance(self.source, SourceIdentity):
            raise CalendarIdentityError("source must be a canonical SourceIdentity")
        opened = require_aware_utc(self.open_at, "open_at")
        closed = require_aware_utc(self.close_at, "close_at")
        timezone_name = str(self.exchange_timezone).strip()
        if not timezone_name:
            raise CalendarIdentityError("exchange_timezone is required")
        try:
            exchange_zone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise CalendarIdentityError(
                "exchange_timezone must name an installed IANA timezone"
            ) from exc
        if (
            opened.astimezone(exchange_zone).date() != self.session_date
            or closed.astimezone(exchange_zone).date() != self.session_date
        ):
            raise CalendarIdentityError(
                "session open and close must fall on session_date in exchange_timezone"
            )
        if opened >= closed:
            raise CalendarIdentityError("session open must precede session close")
        if type(self.is_early_close) is not bool:
            raise CalendarIdentityError("is_early_close must be boolean")
        exchange_id = str(self.exchange_id).strip()
        if not exchange_id:
            raise CalendarIdentityError("exchange_id is required")
        object.__setattr__(self, "open_at", opened)
        object.__setattr__(self, "close_at", closed)
        object.__setattr__(self, "exchange_timezone", timezone_name)
        object.__setattr__(self, "exchange_id", exchange_id)


def session_rows_sha256(sessions: Iterable[AcceptedSession]) -> str:
    """Hash complete normalized session semantics and exact row provenance."""

    rows = tuple(sessions)
    if not rows or any(not isinstance(row, AcceptedSession) for row in rows):
        raise CalendarIdentityError("sessions must contain AcceptedSession values")
    payload = [
        {
            "session_date": row.session_date.isoformat(),
            "open_at": row.open_at.isoformat(),
            "close_at": row.close_at.isoformat(),
            "exchange_timezone": row.exchange_timezone,
            "exchange_id": row.exchange_id,
            "is_early_close": row.is_early_close,
            "source": _source_payload(row.source),
        }
        for row in rows
    ]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def calendar_identity_sha256(identity: CalendarIdentity) -> str:
    """Hash the exact accepted calendar identity used by dependent snapshots."""

    if not isinstance(identity, CalendarIdentity):
        raise CalendarIdentityError("identity must be a CalendarIdentity")
    payload = {
        "exchange_id": identity.exchange_id,
        "exchange_timezone": identity.exchange_timezone,
        "coverage_start": identity.coverage_start.isoformat(),
        "coverage_end": identity.coverage_end.isoformat(),
        "session_count": identity.session_count,
        "session_dates_sha256": identity.session_dates_sha256,
        "session_rows_sha256": identity.session_rows_sha256,
        "source_identity": _source_payload(identity.source_identity),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


class AcceptedSessionCalendar:
    """A small immutable calendar whose availability is checked at every lookup."""

    def __init__(
        self,
        sessions: Iterable[AcceptedSession],
        *,
        identity: CalendarIdentity,
    ) -> None:
        rows = tuple(sessions)
        if not isinstance(identity, CalendarIdentity):
            raise CalendarIdentityError("calendar identity is required")
        if not rows:
            raise CalendarIdentityError("at least one accepted session is required")
        if any(not isinstance(row, AcceptedSession) for row in rows):
            raise CalendarIdentityError("calendar rows must be AcceptedSession values")
        dates = tuple(row.session_date for row in rows)
        if any(current >= following for current, following in zip(dates, dates[1:])):
            raise CalendarIdentityError(
                "sessions must be unique and strictly ordered by session_date"
            )
        if any(current.close_at >= following.open_at for current, following in zip(rows, rows[1:])):
            raise CalendarIdentityError("session timestamps overlap or are unordered")
        timezones = {row.exchange_timezone for row in rows}
        if len(timezones) != 1:
            raise CalendarIdentityError("one calendar cannot mix exchange timezones")
        if identity.exchange_timezone != rows[0].exchange_timezone:
            raise CalendarIdentityError("calendar rows do not match identity timezone")
        exchange_ids = {row.exchange_id for row in rows}
        if len(exchange_ids) != 1 or identity.exchange_id != rows[0].exchange_id:
            raise CalendarIdentityError("calendar rows do not match identity exchange_id")
        if identity.coverage_start != dates[0] or identity.coverage_end != dates[-1]:
            raise CalendarIdentityError(
                "calendar rows do not match identity coverage bounds"
            )
        if identity.session_count != len(rows):
            raise CalendarIdentityError("calendar rows do not match identity session_count")
        if identity.session_dates_sha256 != session_dates_sha256(dates):
            raise CalendarIdentityError(
                "calendar rows do not match identity session_dates_sha256"
            )
        if identity.session_rows_sha256 != session_rows_sha256(rows):
            raise CalendarIdentityError(
                "calendar rows do not match identity session_rows_sha256"
            )
        self._sessions = rows
        self._dates = dates
        self._by_date = dict(zip(dates, rows, strict=True))
        self._exchange_timezone = rows[0].exchange_timezone
        self._exchange_id = rows[0].exchange_id
        self._identity = identity

    @property
    def session_dates(self) -> tuple[date, ...]:
        return self._dates

    @property
    def sessions(self) -> tuple[AcceptedSession, ...]:
        return self._sessions

    @property
    def exchange_timezone(self) -> str:
        return self._exchange_timezone

    @property
    def exchange_id(self) -> str:
        return self._exchange_id

    @property
    def identity(self) -> CalendarIdentity:
        return self._identity

    def session_on(self, session_date: date, *, as_of: datetime) -> AcceptedSession:
        if type(session_date) is not date:
            raise TypeError("session_date must be a date")
        try:
            row = self._by_date[session_date]
        except KeyError as exc:
            raise CalendarIdentityError(f"no accepted session for {session_date}") from exc
        return self._require_available(row, as_of)

    def next_session(self, after: date, *, as_of: datetime) -> AcceptedSession:
        if type(after) is not date:
            raise TypeError("after must be a date")
        position = bisect_right(self._dates, after)
        if position >= len(self._sessions):
            raise CalendarIdentityError(f"no accepted session after {after}")
        return self._require_available(self._sessions[position], as_of)

    def sessions_between(
        self,
        start: date,
        end: date,
        *,
        as_of: datetime,
    ) -> tuple[AcceptedSession, ...]:
        if type(start) is not date or type(end) is not date:
            raise TypeError("start and end must be dates")
        if start > end:
            raise ValueError("start cannot follow end")
        rows = tuple(row for row in self._sessions if start <= row.session_date <= end)
        return tuple(self._require_available(row, as_of) for row in rows)

    def _require_available(self, row: AcceptedSession, as_of: datetime) -> AcceptedSession:
        cutoff = require_aware_utc(as_of, "as_of")
        if self._identity.source_identity.available_at > cutoff:
            raise CalendarIdentityError("calendar identity was not available at as_of")
        if row.source.available_at > cutoff:
            raise CalendarIdentityError(
                f"calendar session {row.session_date} was not available at as_of"
            )
        return row


__all__ = [
    "AcceptedSession",
    "AcceptedSessionCalendar",
    "CalendarIdentity",
    "CalendarIdentityError",
    "calendar_identity_sha256",
    "session_rows_sha256",
    "session_dates_sha256",
]


def _source_payload(source: SourceIdentity) -> dict[str, object]:
    return {
        "source_url": source.source_url,
        "content_sha256": source.content_sha256,
        "available_at": source.available_at.isoformat(),
        "retrieved_at": source.retrieved_at.isoformat(),
        "revision_id": source.revision_id,
        "source_family_id": source.source_family_id,
        "provider_id": source.provider_id,
        "subject_id": source.subject_id,
        "supersedes_revision_id": source.supersedes_revision_id,
        "capture_receipt_sha256": source.capture_receipt_sha256,
        "publication_evidence_sha256": source.publication_evidence_sha256,
        "url_migration_receipt_sha256": source.url_migration_receipt_sha256,
    }
