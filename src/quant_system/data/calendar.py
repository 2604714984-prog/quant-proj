"""Dependency-free accepted-session calendar backed by provided rows."""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .source_identity import SourceIdentity, require_aware_utc


class CalendarIdentityError(ValueError):
    """Raised when an accepted calendar is unavailable or inconsistent."""


@dataclass(frozen=True)
class AcceptedSession:
    session_date: date
    open_at: datetime
    close_at: datetime
    source: SourceIdentity
    exchange_timezone: str
    is_early_close: bool = False

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
        object.__setattr__(self, "open_at", opened)
        object.__setattr__(self, "close_at", closed)
        object.__setattr__(self, "exchange_timezone", timezone_name)


class AcceptedSessionCalendar:
    """A small immutable calendar whose availability is checked at every lookup."""

    def __init__(self, sessions: Iterable[AcceptedSession]) -> None:
        rows = tuple(sessions)
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
        self._sessions = rows
        self._dates = dates
        self._by_date = dict(zip(dates, rows, strict=True))
        self._exchange_timezone = rows[0].exchange_timezone

    @property
    def session_dates(self) -> tuple[date, ...]:
        return self._dates

    @property
    def exchange_timezone(self) -> str:
        return self._exchange_timezone

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

    @staticmethod
    def _require_available(row: AcceptedSession, as_of: datetime) -> AcceptedSession:
        cutoff = require_aware_utc(as_of, "as_of")
        if row.source.available_at > cutoff:
            raise CalendarIdentityError(
                f"calendar session {row.session_date} was not available at as_of"
            )
        return row


__all__ = ["AcceptedSession", "AcceptedSessionCalendar", "CalendarIdentityError"]
