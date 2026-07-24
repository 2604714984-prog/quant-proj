from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import hashlib

import pytest

from quant_system.data.calendar import (
    AcceptedSession,
    AcceptedSessionCalendar,
    CalendarIdentity,
    CalendarIdentityError,
    session_dates_sha256,
    session_rows_sha256,
)
from quant_system.data.source_identity import SourceIdentity, SourceIdentityError


UTC = timezone.utc


def _calendar_source(
    revision: str,
    *,
    available_at: datetime = datetime(2026, 7, 1, tzinfo=UTC),
    content_sha256: str | None = None,
) -> SourceIdentity:
    return SourceIdentity(
        source_url="https://www.nyse.com/publicdocs/calendar.json",
        content_sha256=content_sha256 or hashlib.sha256(revision.encode()).hexdigest(),
        available_at=available_at,
        retrieved_at=max(available_at, datetime(2026, 7, 2, tzinfo=UTC)),
        revision_id=revision,
        source_family_id="nyse-calendar",
        provider_id="nyse",
        subject_id="XNYS",
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
            exchange_id="XNYS",
        ),
        AcceptedSession(
            session_date=date(2026, 7, 6),
            open_at=datetime(2026, 7, 6, 13, 30, tzinfo=UTC),
            close_at=datetime(2026, 7, 6, 20, tzinfo=UTC),
            source=source,
            exchange_timezone="America/New_York",
            exchange_id="XNYS",
        ),
    )


def _identity(
    rows: tuple[AcceptedSession, ...],
    *,
    source: SourceIdentity | None = None,
) -> CalendarIdentity:
    dates = tuple(row.session_date for row in rows)
    rows_sha = session_rows_sha256(rows)
    return CalendarIdentity(
        exchange_id="XNYS",
        exchange_timezone=rows[0].exchange_timezone,
        coverage_start=dates[0],
        coverage_end=dates[-1],
        session_count=len(dates),
        session_dates_sha256=session_dates_sha256(dates),
        session_rows_sha256=rows_sha,
        source_identity=source or _calendar_source("calendar-aggregate"),
    )


def test_calendar_preserves_early_close_and_next_accepted_session() -> None:
    calendar = AcceptedSessionCalendar(_rows(), identity=_identity(_rows()))
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
        exchange_id="XNYS",
    )
    calendar = AcceptedSessionCalendar((row,), identity=_identity((row,)))

    with pytest.raises(CalendarIdentityError, match="not available"):
        calendar.session_on(
            date(2026, 7, 8),
            as_of=datetime(2026, 7, 6, tzinfo=UTC),
        )


def test_calendar_rejects_duplicate_reordered_and_mixed_timezone_rows() -> None:
    first, second = _rows()
    with pytest.raises(CalendarIdentityError, match="strictly ordered"):
        AcceptedSessionCalendar((second, first), identity=_identity((first, second)))
    with pytest.raises(CalendarIdentityError, match="strictly ordered"):
        AcceptedSessionCalendar((first, first), identity=_identity((first, second)))
    with pytest.raises(CalendarIdentityError, match="mix exchange timezones"):
        AcceptedSessionCalendar(
            (first, replace(second, exchange_timezone="UTC")),
            identity=_identity((first, second)),
        )


def test_calendar_rejects_naive_times_and_invalid_lookup_ranges() -> None:
    source = _calendar_source("calendar")
    with pytest.raises(CalendarIdentityError, match="canonical SourceIdentity"):
        AcceptedSession(
            session_date=date(2026, 7, 3),
            open_at=datetime(2026, 7, 3, 13, 30, tzinfo=UTC),
            close_at=datetime(2026, 7, 3, 20, tzinfo=UTC),
            source=object(),  # type: ignore[arg-type]
            exchange_timezone="America/New_York",
            exchange_id="XNYS",
        )
    with pytest.raises(SourceIdentityError, match="timezone-aware"):
        AcceptedSession(
            session_date=date(2026, 7, 3),
            open_at=datetime(2026, 7, 3, 9, 30),
            close_at=datetime(2026, 7, 3, 16),
            source=source,
            exchange_timezone="America/New_York",
            exchange_id="XNYS",
        )
    calendar = AcceptedSessionCalendar(_rows(), identity=_identity(_rows()))
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
            exchange_id="XNYS",
        )
    with pytest.raises(CalendarIdentityError, match="session_date"):
        AcceptedSession(
            session_date=date(2026, 7, 3),
            open_at=datetime(2026, 7, 3, 1, tzinfo=UTC),
            close_at=datetime(2026, 7, 3, 2, tzinfo=UTC),
            source=source,
            exchange_timezone="America/New_York",
            exchange_id="XNYS",
        )


def test_calendar_identity_rejects_missing_or_changed_coverage() -> None:
    source = _calendar_source("three-session-calendar")
    rows = tuple(
        AcceptedSession(
            session_date=day,
            open_at=datetime(2026, 7, day.day, 13, 30, tzinfo=UTC),
            close_at=datetime(2026, 7, day.day, 20, tzinfo=UTC),
            source=source,
            exchange_timezone="America/New_York",
            exchange_id="XNYS",
        )
        for day in (date(2026, 7, 1), date(2026, 7, 2), date(2026, 7, 3))
    )
    identity = _identity(rows)
    with pytest.raises(CalendarIdentityError, match="session_count"):
        AcceptedSessionCalendar((rows[0], rows[2]), identity=identity)
    with pytest.raises(CalendarIdentityError, match="session_count"):
        AcceptedSessionCalendar(rows, identity=replace(identity, session_count=4))
    with pytest.raises(CalendarIdentityError, match="session_dates_sha256"):
        AcceptedSessionCalendar(
            rows,
            identity=replace(identity, session_dates_sha256="f" * 64),
        )
    with pytest.raises(CalendarIdentityError, match="calendar identity is required"):
        AcceptedSessionCalendar(rows, identity=None)  # type: ignore[arg-type]


def test_calendar_identity_source_must_be_available_at_lookup() -> None:
    rows = _rows()
    late = _calendar_source(
        "late-aggregate",
        available_at=datetime(2026, 7, 7, tzinfo=UTC),
    )
    calendar = AcceptedSessionCalendar(rows, identity=_identity(rows, source=late))

    with pytest.raises(CalendarIdentityError, match="identity was not available"):
        calendar.session_on(
            rows[0].session_date,
            as_of=datetime(2026, 7, 2, tzinfo=UTC),
        )


def test_calendar_identity_binds_full_session_semantics_and_timezone() -> None:
    rows = _rows()
    identity = _identity(rows)
    assert identity.source_identity.content_sha256 != identity.session_rows_sha256
    changed_close = replace(
        rows[0],
        close_at=rows[0].close_at - timedelta(hours=1),
        is_early_close=False,
    )
    with pytest.raises(CalendarIdentityError, match="session_rows_sha256"):
        AcceptedSessionCalendar((changed_close, rows[1]), identity=identity)
    changed_source = replace(rows[0], source=_calendar_source("different-row-source"))
    with pytest.raises(CalendarIdentityError, match="session_rows_sha256"):
        AcceptedSessionCalendar((changed_source, rows[1]), identity=identity)
    shanghai_rows = tuple(
        AcceptedSession(
            session_date=row.session_date,
            open_at=datetime.combine(
                row.session_date,
                datetime.min.time(),
                timezone.utc,
            )
            + timedelta(hours=1, minutes=30),
            close_at=datetime.combine(
                row.session_date,
                datetime.min.time(),
                timezone.utc,
            )
            + timedelta(hours=7),
            source=row.source,
            exchange_timezone="Asia/Shanghai",
            exchange_id="XSHG",
        )
        for row in rows
    )
    with pytest.raises(CalendarIdentityError, match="identity timezone"):
        AcceptedSessionCalendar(shanghai_rows, identity=identity)
