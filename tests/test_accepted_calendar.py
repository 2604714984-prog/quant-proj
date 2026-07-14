from dataclasses import replace
from datetime import date, datetime, timezone
import hashlib

import pytest

from quant_system.data.calendar import (
    AcceptedSession,
    AcceptedSessionCalendar,
    CalendarIdentityError,
)
from quant_system.data.source_identity import SourceIdentity, SourceIdentityError


UTC = timezone.utc


def _calendar_source(
    revision: str,
    *,
    available_at: datetime = datetime(2026, 7, 1, tzinfo=UTC),
) -> SourceIdentity:
    return SourceIdentity(
        source_url=f"https://www.nyse.com/publicdocs/{revision}.json",
        content_sha256=hashlib.sha256(revision.encode()).hexdigest(),
        available_at=available_at,
        retrieved_at=max(available_at, datetime(2026, 7, 2, tzinfo=UTC)),
        revision_id=revision,
    )


def _rows() -> tuple[AcceptedSession, AcceptedSession]:
    source = _calendar_source("calendar-2026")
    return (
        AcceptedSession(
            session_date=date(2026, 7, 3),
            open_at=datetime(2026, 7, 3, 13, 30, tzinfo=UTC),
            close_at=datetime(2026, 7, 3, 17, tzinfo=UTC),
            source=source,
            exchange_timezone="America/New_York",
            is_early_close=True,
        ),
        AcceptedSession(
            session_date=date(2026, 7, 6),
            open_at=datetime(2026, 7, 6, 13, 30, tzinfo=UTC),
            close_at=datetime(2026, 7, 6, 20, tzinfo=UTC),
            source=source,
            exchange_timezone="America/New_York",
        ),
    )


def test_calendar_preserves_early_close_and_next_accepted_session() -> None:
    calendar = AcceptedSessionCalendar(_rows())
    cutoff = datetime(2026, 7, 2, tzinfo=UTC)

    early = calendar.session_on(date(2026, 7, 3), as_of=cutoff)
    following = calendar.next_session(date(2026, 7, 3), as_of=cutoff)

    assert early.is_early_close is True
    assert calendar.exchange_timezone == "America/New_York"
    assert early.close_at == datetime(2026, 7, 3, 17, tzinfo=UTC)
    assert following.session_date == date(2026, 7, 6)
    assert (
        calendar.sessions_between(
            date(2026, 7, 3),
            date(2026, 7, 6),
            as_of=cutoff,
        )
        == _rows()
    )


def test_calendar_fails_when_source_was_not_available_at_cutoff() -> None:
    late_source = _calendar_source(
        "late-calendar",
        available_at=datetime(2026, 7, 7, tzinfo=UTC),
    )
    row = AcceptedSession(
        session_date=date(2026, 7, 8),
        open_at=datetime(2026, 7, 8, 13, 30, tzinfo=UTC),
        close_at=datetime(2026, 7, 8, 20, tzinfo=UTC),
        source=late_source,
        exchange_timezone="America/New_York",
    )
    calendar = AcceptedSessionCalendar((row,))

    with pytest.raises(CalendarIdentityError, match="not available"):
        calendar.session_on(
            date(2026, 7, 8),
            as_of=datetime(2026, 7, 6, tzinfo=UTC),
        )


def test_calendar_rejects_duplicate_reordered_and_mixed_timezone_rows() -> None:
    first, second = _rows()
    with pytest.raises(CalendarIdentityError, match="strictly ordered"):
        AcceptedSessionCalendar((second, first))
    with pytest.raises(CalendarIdentityError, match="strictly ordered"):
        AcceptedSessionCalendar((first, first))
    with pytest.raises(CalendarIdentityError, match="mix exchange timezones"):
        AcceptedSessionCalendar((first, replace(second, exchange_timezone="UTC")))


def test_calendar_rejects_naive_times_and_invalid_lookup_ranges() -> None:
    source = _calendar_source("calendar")
    with pytest.raises(CalendarIdentityError, match="canonical SourceIdentity"):
        AcceptedSession(
            session_date=date(2026, 7, 3),
            open_at=datetime(2026, 7, 3, 13, 30, tzinfo=UTC),
            close_at=datetime(2026, 7, 3, 20, tzinfo=UTC),
            source=object(),  # type: ignore[arg-type]
            exchange_timezone="America/New_York",
        )
    with pytest.raises(SourceIdentityError, match="timezone-aware"):
        AcceptedSession(
            session_date=date(2026, 7, 3),
            open_at=datetime(2026, 7, 3, 9, 30),
            close_at=datetime(2026, 7, 3, 16),
            source=source,
            exchange_timezone="America/New_York",
        )
    calendar = AcceptedSessionCalendar(_rows())
    with pytest.raises(ValueError, match="cannot follow"):
        calendar.sessions_between(
            date(2026, 7, 6),
            date(2026, 7, 3),
            as_of=datetime(2026, 7, 2, tzinfo=UTC),
        )
    with pytest.raises(CalendarIdentityError, match="no accepted session"):
        calendar.next_session(
            date(2026, 7, 6),
            as_of=datetime(2026, 7, 2, tzinfo=UTC),
        )


def test_calendar_rejects_unknown_timezone_and_local_date_mismatch() -> None:
    source = _calendar_source("timezone-calendar")
    with pytest.raises(CalendarIdentityError, match="IANA timezone"):
        AcceptedSession(
            session_date=date(2026, 7, 3),
            open_at=datetime(2026, 7, 3, 13, 30, tzinfo=UTC),
            close_at=datetime(2026, 7, 3, 20, tzinfo=UTC),
            source=source,
            exchange_timezone="Not/A_Timezone",
        )
    with pytest.raises(CalendarIdentityError, match="session_date"):
        AcceptedSession(
            session_date=date(2026, 7, 3),
            open_at=datetime(2026, 7, 3, 1, tzinfo=UTC),
            close_at=datetime(2026, 7, 3, 2, tzinfo=UTC),
            source=source,
            exchange_timezone="America/New_York",
        )
