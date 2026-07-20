#!/usr/bin/env python3
"""Build the frozen US pre-holiday calendar input qualification bundle.

The utility is deliberately offline and one-off. It verifies exact private
official-document bytes and writes aggregate calendar/event identities only.
It never reads prices, outcomes, credentials, or a database.
"""

from __future__ import annotations

import argparse
import calendar
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, timedelta
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any


QUALIFICATION_ID = "US_PRE_HOLIDAY_CALENDAR_INPUT_QUALIFICATION_V1"
TARGET_START = date(2010, 1, 1)
TARGET_END = date(2026, 6, 30)
QUALIFIED_ANNUAL_YEARS = frozenset(range(2022, 2027))
BLOCKED_ANNUAL_YEARS = tuple(range(2010, 2022))
OUTPUT_NAMES = (
    "holiday_denominator.json",
    "accepted_pre_holiday_sessions.json",
    "early_close_identity.json",
    "ad_hoc_closure_identity.json",
    "source_manifest.json",
    "input_qualification.json",
)


def _spec(
    source_id: str,
    filename: str,
    url: str,
    content_sha256: str,
    byte_count: int,
    role: str,
    year: int | None = None,
    content_type: str = "application/pdf",
) -> dict[str, Any]:
    return {
        "bytes": byte_count,
        "content_sha256": content_sha256,
        "content_type": content_type,
        "filename": filename,
        "role": role,
        "source_id": source_id,
        "url": url,
        "year": year,
    }


SOURCE_SPECS: tuple[dict[str, Any], ...] = (
    _spec(
        "nyse_annual_calendar_2022",
        "ICE_NYSE_2022_Yearly_Trading_Calendar.pdf",
        "https://www.nyse.com/publicdocs/ICE_NYSE_2022_Yearly_Trading_Calendar.pdf",
        "2c2e63b780c4a373d8d546904ae46c8ba7e8070ad9357d23d2c92749985bb6c9",
        111260,
        "OFFICIAL_NYSE_ANNUAL_CALENDAR",
        2022,
    ),
    _spec(
        "nyse_annual_calendar_2023",
        "ICE_NYSE_2023_Yearly_Trading_Calendar.pdf",
        "https://www.nyse.com/publicdocs/ICE_NYSE_2023_Yearly_Trading_Calendar.pdf",
        "3d28b46a7197424c822087fb7117cdf3f303bd9a73f29660525b605f542bcfe2",
        112881,
        "OFFICIAL_NYSE_ANNUAL_CALENDAR",
        2023,
    ),
    _spec(
        "nyse_annual_calendar_2024",
        "ICE_NYSE_2024_Yearly_Trading_Calendar.pdf",
        "https://www.nyse.com/publicdocs/ICE_NYSE_2024_Yearly_Trading_Calendar.pdf",
        "02282e733512d1f112230372efccfd18f81599c682af94bb6f21fd9bccbfd145",
        115340,
        "OFFICIAL_NYSE_ANNUAL_CALENDAR",
        2024,
    ),
    _spec(
        "nyse_annual_calendar_2025",
        "ICE_NYSE_2025_Yearly_Trading_Calendar.pdf",
        "https://www.nyse.com/publicdocs/ICE_NYSE_2025_Yearly_Trading_Calendar.pdf",
        "3e8b540ad74474bc12a0aba473dbca28f37e0a5c1795cf66701b9a506a34226e",
        115262,
        "OFFICIAL_NYSE_ANNUAL_CALENDAR",
        2025,
    ),
    _spec(
        "nyse_annual_calendar_2026",
        "ICE_NYSE_2026_Yearly_Trading_Calendar.pdf",
        "https://www.nyse.com/publicdocs/nyse/ICE_NYSE_2026_Yearly_Trading_Calendar.pdf",
        "70f5577eb43e60a9dbbecaae3cec23d0f02028c05c7f175013bb3e97816d394f",
        232670,
        "OFFICIAL_NYSE_ANNUAL_CALENDAR",
        2026,
    ),
    _spec(
        "nyse_current_hours_page_2026",
        "NYSE_2026_Holidays_and_Trading_Hours.html",
        "https://www.nyse.com/trade/hours-calendars",
        "6385a2a07313aee09c5f28a6d5df2931e0a617252b4c833b2aeeafdad4e44cac",
        109670,
        "OFFICIAL_NYSE_CURRENT_HOURS_PAGE",
        2026,
        "text/html; charset=utf-8",
    ),
    _spec(
        "sec_nyse_rule_51_2010",
        "SEC_34-61810-ex5_NYSE_Rule51.pdf",
        "https://www.sec.gov/files/rules/sro/nyse/2010/34-61810-ex5.pdf",
        "43105f9ac7e2188532b9bb37ead1198b90cf51797d0993b13f5be449620513a3",
        27408,
        "OFFICIAL_SEC_HOSTED_NYSE_EMERGENCY_CLOSURE_RULE",
        2010,
    ),
    _spec(
        "sec_nyse_pillar_rule_7_2_2017",
        "SEC_34-81225_NYSE_Pillar_Rule72.pdf",
        "https://www.sec.gov/files/rules/sro/nyse/2017/34-81225.pdf",
        "a6ef98843c9a9e157e805c31acf6be0e76f966085f044e825e90f609c39c0b61",
        184364,
        "OFFICIAL_SEC_HOSTED_NYSE_HOLIDAY_RULE",
        2017,
    ),
    _spec(
        "nyse_rule_7_2_juneteenth",
        "SR-NYSE-2021-56.pdf",
        (
            "https://www.nyse.com/publicdocs/nyse/markets/nyse/rule-filings/filings/"
            "2021/SR-NYSE-2021-56.pdf"
        ),
        "092a460f7c10aebed5942b01840bfb6086e1a78fba693958a4570af9b4add7c5",
        84120,
        "OFFICIAL_NYSE_RULE_7_2_JUNETEENTH_FILING",
        2021,
    ),
    _spec(
        "sec_nyse_sandy_closure_2012",
        "SEC_34-70097_Sandy.pdf",
        "https://www.sec.gov/files/rules/sro/nysearca/2013/34-70097.pdf",
        "62d4faadddc1beee4d3e7fa6802f5284a8a983f3f8b73deb7340b840b76eb2e1",
        66175,
        "OFFICIAL_SEC_HOSTED_NYSE_SANDY_CLOSURE_FILING",
        2012,
    ),
    _spec(
        "nyse_bush_closure_2018",
        "NYSE_Arca_Options_18-06_Bush.pdf",
        (
            "https://www.nyse.com/publicdocs/nyse/markets/arca-options/"
            "rule-interpretations/2018/NYSE%20Arca%20Options%2018-06.pdf"
        ),
        "046fb35bcc6e9600d96d5c7f7de63b1f59989cc04a445dbdeeb7b4e08add6e5b",
        152116,
        "OFFICIAL_NYSE_BUSH_DAY_OF_MOURNING_BULLETIN",
        2018,
    ),
    _spec(
        "nyse_carter_closure_2025",
        "NYSE_National_Day_of_Mourning_20250102.pdf",
        (
            "https://www.nyse.com/publicdocs/nyse/markets/american-options/"
            "rule-interpretations/2025/National_Day_of_Mourning_20250102.pdf"
        ),
        "a4640ce5466cfa262cfe387a20f97b3bbc7ee213a9ce819c4ac7d3717db493c7",
        81203,
        "OFFICIAL_NYSE_CARTER_DAY_OF_MOURNING_MEMO",
        2025,
    ),
)


ANNUAL_MARKET_CLOSED_DATES: dict[int, tuple[str, ...]] = {
    2022: (
        "2022-01-17", "2022-02-21", "2022-04-15", "2022-05-30", "2022-06-20",
        "2022-07-04", "2022-09-05", "2022-11-24", "2022-12-26",
    ),
    2023: (
        "2023-01-02", "2023-01-16", "2023-02-20", "2023-04-07", "2023-05-29",
        "2023-06-19", "2023-07-04", "2023-09-04", "2023-11-23", "2023-12-25",
    ),
    2024: (
        "2024-01-01", "2024-01-15", "2024-02-19", "2024-03-29", "2024-05-27",
        "2024-06-19", "2024-07-04", "2024-09-02", "2024-11-28", "2024-12-25",
    ),
    2025: (
        "2025-01-01", "2025-01-09", "2025-01-20", "2025-02-17", "2025-04-18",
        "2025-05-26", "2025-06-19", "2025-07-04", "2025-09-01", "2025-11-27",
        "2025-12-25",
    ),
    2026: (
        "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25",
        "2026-06-19", "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25",
    ),
}
ANNUAL_EARLY_CLOSE_DATES: dict[int, tuple[str, ...]] = {
    2022: ("2022-11-25",),
    2023: ("2023-07-03", "2023-11-24"),
    2024: ("2024-07-03", "2024-11-29", "2024-12-24"),
    2025: ("2025-07-03", "2025-11-28", "2025-12-24"),
    2026: ("2026-11-27", "2026-12-24"),
}
AD_HOC_BLOCKS: tuple[dict[str, Any], ...] = (
    {
        "block_id": "ADHOC_2012_SANDY",
        "closure_dates": ("2012-10-29", "2012-10-30"),
        "label": "Hurricane Sandy emergency closure",
        "source_ids": ("sec_nyse_rule_51_2010", "sec_nyse_sandy_closure_2012"),
    },
    {
        "block_id": "ADHOC_2018_BUSH",
        "closure_dates": ("2018-12-05",),
        "label": "National Day of Mourning for President George H. W. Bush",
        "source_ids": ("nyse_bush_closure_2018",),
    },
    {
        "block_id": "ADHOC_2025_CARTER",
        "closure_dates": ("2025-01-09",),
        "label": "National Day of Mourning for President Jimmy Carter",
        "source_ids": ("nyse_carter_closure_2025",),
    },
)


class QualificationError(ValueError):
    """Raised when official input or calendar semantics fail closed."""


def _pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in values:
        if key in result:
            raise QualificationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _nonfinite(value: str) -> None:
    raise QualificationError(f"nonfinite JSON constant: {value}")


def strict_load_bytes(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_nonfinite
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise QualificationError("invalid UTF-8 JSON") from exc
    if type(value) is not dict:
        raise QualificationError("top-level JSON value must be an object")
    return value


def canonical_json(value: Any) -> bytes:
    text = json.dumps(value, allow_nan=False, ensure_ascii=True, indent=2, sort_keys=True)
    return f"{text}\n".encode("ascii")


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_regular(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise QualificationError(f"source must be a regular non-symlink file: {path.name}")
    return path.read_bytes()


def _parse_headers(raw: bytes) -> dict[str, str]:
    lines = raw.decode("latin-1").replace("\r\n", "\n").split("\n")
    status_positions = [index for index, line in enumerate(lines) if line.startswith("HTTP/")]
    if not status_positions:
        raise QualificationError("HTTP status is absent from metadata headers")
    final_status = lines[status_positions[-1]].split()
    if len(final_status) < 2 or final_status[1] != "200":
        raise QualificationError("final HTTP status must be 200")
    safe: dict[str, str] = {"http_status": "200"}
    allowed = {"content-length", "content-type", "date", "etag", "last-modified"}
    for line in lines[status_positions[-1] + 1 :]:
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        lowered = key.strip().lower()
        if lowered in allowed:
            safe[lowered.replace("-", "_")] = value.strip()
    return safe


def _parse_meta(raw: bytes) -> dict[str, Any]:
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise QualificationError("invalid UTF-8 retrieval metadata") from exc
    if len(lines) != 5:
        raise QualificationError("retrieval metadata must contain exactly five lines")
    try:
        return {
            "http_status": int(lines[0]),
            "url": lines[1],
            "redirects_followed": int(lines[2]),
            "bytes": int(lines[3]),
            "content_type": lines[4],
        }
    except ValueError as exc:
        raise QualificationError("retrieval metadata contains a non-integer field") from exc


def qualify_sources(
    source_dir: Path, specs: Sequence[Mapping[str, Any]] = SOURCE_SPECS
) -> dict[str, Any]:
    expected_payloads = {str(spec["filename"]) for spec in specs}
    expected_ids = {str(spec["source_id"]) for spec in specs}
    if len(expected_payloads) != len(specs) or len(expected_ids) != len(specs):
        raise QualificationError("source filenames and IDs must be unique")
    allowed = set(expected_payloads)
    allowed.update(f"{name}.meta" for name in expected_payloads)
    allowed.update(f"{name}.meta.headers" for name in expected_payloads)
    observed = {
        path.name for path in source_dir.iterdir() if path.is_file() or path.is_symlink()
    }
    if observed - allowed:
        raise QualificationError("source directory contains an unexpected file")

    resources: list[dict[str, Any]] = []
    for spec in specs:
        filename = str(spec["filename"])
        raw = _read_regular(source_dir / filename)
        if len(raw) != spec["bytes"] or sha256_bytes(raw) != spec["content_sha256"]:
            raise QualificationError(f"source bytes changed: {spec['source_id']}")
        content_type = str(spec["content_type"])
        if content_type == "application/pdf" and not raw.startswith(b"%PDF-"):
            raise QualificationError(f"source is not a PDF: {spec['source_id']}")
        if content_type.startswith("text/html") and b"<html" not in raw[:2000].lower():
            raise QualificationError(f"source is not HTML: {spec['source_id']}")

        header_raw = _read_regular(source_dir / f"{filename}.meta.headers")
        safe_headers = _parse_headers(header_raw)
        if safe_headers.get("content_type") != content_type:
            raise QualificationError(f"HTTP content type changed: {spec['source_id']}")
        header_length = safe_headers.get("content_length")
        if header_length is not None and int(header_length) != len(raw):
            raise QualificationError(f"HTTP content length changed: {spec['source_id']}")

        meta_raw = _read_regular(source_dir / f"{filename}.meta")
        meta = _parse_meta(meta_raw)
        if (
            meta["http_status"] != 200
            or meta["url"] != spec["url"]
            or meta["bytes"] != len(raw)
            or meta["content_type"] != content_type
        ):
            raise QualificationError(f"retrieval identity changed: {spec['source_id']}")
        resources.append(
            {
                "bytes": len(raw),
                "content_sha256": sha256_bytes(raw),
                "content_type": content_type,
                "filename": filename,
                "http_date": safe_headers.get("date"),
                "http_etag": safe_headers.get("etag"),
                "http_last_modified": safe_headers.get("last_modified"),
                "http_status": 200,
                "redirects_followed": meta["redirects_followed"],
                "retrieval_headers_sha256": sha256_bytes(header_raw),
                "retrieval_meta_sha256": sha256_bytes(meta_raw),
                "role": spec["role"],
                "source_id": spec["source_id"],
                "url": spec["url"],
                "year": spec["year"],
            }
        )
    return {
        "authentication_used": False,
        "cookies_or_session_used_for_request": False,
        "credential_material_published": False,
        "network_performed_by_qualification": False,
        "qualification_id": QUALIFICATION_ID,
        "resource_count": len(resources),
        "resources": resources,
        "source_directory_published": False,
        "source_snapshot_sha256": sha256_bytes(canonical_json(resources)),
        "version": 1,
    }


def _nth_weekday(year: int, month: int, weekday: int, occurrence: int) -> date:
    days = [week[weekday] for week in calendar.monthcalendar(year, month) if week[weekday]]
    return date(year, month, days[occurrence - 1])


def _last_weekday(year: int, month: int, weekday: int) -> date:
    weeks = calendar.monthcalendar(year, month)
    day = next(week[weekday] for week in reversed(weeks) if week[weekday])
    return date(year, month, day)


def _easter(year: int) -> date:
    """Return Gregorian Easter using the Meeus/Jones/Butcher algorithm."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    ell = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ell) // 451
    month = (h + ell - 7 * m + 114) // 31
    day = (h + ell - 7 * m + 114) % 31 + 1
    return date(year, month, day)


def _observed_fixed(day: date, *, saturday_prior_friday: bool = True) -> date | None:
    if day.weekday() == calendar.SATURDAY:
        return day - timedelta(days=1) if saturday_prior_friday else None
    if day.weekday() == calendar.SUNDAY:
        return day + timedelta(days=1)
    return day


def scheduled_holidays_for_year(year: int) -> tuple[tuple[str, date], ...]:
    rows: list[tuple[str, date | None]] = [
        ("NEW_YEARS_DAY", _observed_fixed(date(year, 1, 1), saturday_prior_friday=False)),
        ("MARTIN_LUTHER_KING_JR_DAY", _nth_weekday(year, 1, calendar.MONDAY, 3)),
        ("PRESIDENTS_DAY", _nth_weekday(year, 2, calendar.MONDAY, 3)),
        ("GOOD_FRIDAY", _easter(year) - timedelta(days=2)),
        ("MEMORIAL_DAY", _last_weekday(year, 5, calendar.MONDAY)),
    ]
    if year >= 2022:
        rows.append(("JUNETEENTH", _observed_fixed(date(year, 6, 19))))
    rows.extend(
        [
            ("INDEPENDENCE_DAY", _observed_fixed(date(year, 7, 4))),
            ("LABOR_DAY", _nth_weekday(year, 9, calendar.MONDAY, 1)),
            ("THANKSGIVING_DAY", _nth_weekday(year, 11, calendar.THURSDAY, 4)),
            ("CHRISTMAS_DAY", _observed_fixed(date(year, 12, 25))),
        ]
    )
    return tuple((name, day) for name, day in rows if day is not None)


def _iso_dates(values: Iterable[str]) -> set[date]:
    return {date.fromisoformat(value) for value in values}


def _ad_hoc_dates(blocks: Sequence[Mapping[str, Any]] = AD_HOC_BLOCKS) -> set[date]:
    return {
        date.fromisoformat(value)
        for block in blocks
        for value in block["closure_dates"]
    }


def _validate_official_calendar_constants() -> None:
    ad_hoc = _ad_hoc_dates()
    for year in sorted(QUALIFIED_ANNUAL_YEARS):
        scheduled = {day for _, day in scheduled_holidays_for_year(year)}
        observed = _iso_dates(ANNUAL_MARKET_CLOSED_DATES[year])
        expected = scheduled | {day for day in ad_hoc if day.year == year}
        if observed != expected:
            raise QualificationError(f"annual market-closed dates disagree for {year}")
        early = _iso_dates(ANNUAL_EARLY_CLOSE_DATES[year])
        if early & observed or any(day.weekday() >= 5 for day in early):
            raise QualificationError(f"annual early-close dates disagree for {year}")


def _rule_source_ids_for_year(year: int) -> list[str]:
    if year <= 2016:
        return ["sec_nyse_rule_51_2010", "sec_nyse_pillar_rule_7_2_2017"]
    if year <= 2021:
        return ["sec_nyse_pillar_rule_7_2_2017"]
    return ["sec_nyse_pillar_rule_7_2_2017", "nyse_rule_7_2_juneteenth"]


def build_holiday_denominator() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for year in range(TARGET_START.year, TARGET_END.year + 1):
        for holiday_name, closure_date in scheduled_holidays_for_year(year):
            if not TARGET_START <= closure_date <= TARGET_END:
                continue
            qualified = year in QUALIFIED_ANNUAL_YEARS
            if closure_date.weekday() >= 5:
                raise QualificationError("weekend date cannot enter the holiday denominator")
            rows.append(
                {
                    "annual_calendar_source_id": (
                        f"nyse_annual_calendar_{year}" if qualified else None
                    ),
                    "closure_date": closure_date.isoformat(),
                    "holiday_name": holiday_name,
                    "included_in_accepted_denominator": qualified,
                    "qualification_status": (
                        "ACCEPTED_OFFICIAL_ANNUAL_CALENDAR"
                        if qualified
                        else "UNQUALIFIED_ANNUAL_ARCHIVE_AND_EARLY_CLOSE_IDENTITY_MISSING"
                    ),
                    "rule_source_ids": _rule_source_ids_for_year(year),
                }
            )
    dates = [row["closure_date"] for row in rows]
    if dates != sorted(dates) or len(dates) != len(set(dates)):
        raise QualificationError("holiday denominator dates must be unique and ordered")
    accepted = [row for row in rows if row["included_in_accepted_denominator"]]
    return {
        "accepted_denominator_count": len(accepted),
        "blocked_candidate_count": len(rows) - len(accepted),
        "definition": (
            "Scheduled NYSE full-day holiday closures only; weekends and ad-hoc closures "
            "never enter the denominator."
        ),
        "formal_rules": [
            "New Year's Day; Saturday year-end exception is not back-shifted to Friday",
            "third Monday in January for Martin Luther King Jr. Day",
            "third Monday in February for Presidents Day",
            "Friday before Gregorian Easter for Good Friday",
            "last Monday in May for Memorial Day",
            "Juneteenth from 2022 with Friday/Monday weekend observation",
            "Independence Day with Friday/Monday weekend observation",
            "first Monday in September for Labor Day",
            "fourth Thursday in November for Thanksgiving Day",
            "Christmas Day with Friday/Monday weekend observation",
        ],
        "historical_rule_version_complete_2010_2016": False,
        "qualification_id": QUALIFICATION_ID,
        "rows": rows,
        "target_end": TARGET_END.isoformat(),
        "target_start": TARGET_START.isoformat(),
        "total_candidate_count": len(rows),
        "version": 1,
    }


def build_ad_hoc_identity(
    blocks: Sequence[Mapping[str, Any]] = AD_HOC_BLOCKS,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    seen_dates: set[date] = set()
    for block in blocks:
        dates = tuple(date.fromisoformat(value) for value in block["closure_dates"])
        if tuple(sorted(dates)) != dates or len(set(dates)) != len(dates):
            raise QualificationError("ad-hoc closure dates must be unique and ordered")
        if any((following - current).days != 1 for current, following in zip(dates, dates[1:])):
            raise QualificationError("each ad-hoc closure block must be contiguous")
        if seen_dates.intersection(dates):
            raise QualificationError("ad-hoc closure dates cannot overlap")
        seen_dates.update(dates)
        rows.append(
            {
                "block_id": block["block_id"],
                "closure_date_count": len(dates),
                "closure_dates": [value.isoformat() for value in dates],
                "included_in_holiday_denominator": False,
                "label": block["label"],
                "source_ids": list(block["source_ids"]),
            }
        )
    return {
        "block_count": len(rows),
        "closure_date_count": len(seen_dates),
        "continuous_blocks_are_single_events": True,
        "holiday_denominator_inclusion_count": 0,
        "qualification_id": QUALIFICATION_ID,
        "rows": rows,
        "version": 1,
    }


def build_early_close_identity() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    source_full_year_observed_count = sum(map(len, ANNUAL_EARLY_CLOSE_DATES.values()))
    for year in sorted(ANNUAL_EARLY_CLOSE_DATES):
        for value in ANNUAL_EARLY_CLOSE_DATES[year]:
            day = date.fromisoformat(value)
            if not TARGET_START <= day <= TARGET_END:
                continue
            rows.append(
                {
                    "annual_calendar_source_id": f"nyse_annual_calendar_{year}",
                    "close_time_local": "13:00:00",
                    "exchange_timezone": "America/New_York",
                    "generates_event_independently": False,
                    "session_date": value,
                }
            )
    session_dates = [row["session_date"] for row in rows]
    if session_dates != sorted(session_dates) or len(session_dates) != len(set(session_dates)):
        raise QualificationError("early-close rows must be unique and ordered")
    return {
        "definition": "Early close is a session attribute only and never creates an event.",
        "qualification_id": QUALIFICATION_ID,
        "row_count": len(rows),
        "rows": rows,
        "source_full_year_observed_count": source_full_year_observed_count,
        "target_period_end": TARGET_END.isoformat(),
        "target_period_start": TARGET_START.isoformat(),
        "version": 1,
    }


def _previous_session(closure: date, all_closures: set[date]) -> date:
    candidate = closure - timedelta(days=1)
    while candidate.weekday() >= 5 or candidate in all_closures:
        candidate -= timedelta(days=1)
    return candidate


def build_accepted_preholiday_sessions(
    denominator: Mapping[str, Any], early_close_identity: Mapping[str, Any]
) -> dict[str, Any]:
    scheduled = {date.fromisoformat(row["closure_date"]) for row in denominator["rows"]}
    all_closures = scheduled | _ad_hoc_dates()
    early_closes = {
        date.fromisoformat(row["session_date"])
        for row in early_close_identity["rows"]
    }
    rows: list[dict[str, Any]] = []
    for holiday in denominator["rows"]:
        if not holiday["included_in_accepted_denominator"]:
            continue
        closure = date.fromisoformat(holiday["closure_date"])
        session = _previous_session(closure, all_closures)
        rows.append(
            {
                "annual_calendar_source_id": holiday["annual_calendar_source_id"],
                "closure_date": closure.isoformat(),
                "holiday_name": holiday["holiday_name"],
                "is_early_close": session in early_closes,
                "session_date": session.isoformat(),
            }
        )
    session_dates = [row["session_date"] for row in rows]
    closure_dates = [row["closure_date"] for row in rows]
    if len(session_dates) != len(set(session_dates)):
        raise QualificationError("one accepted session cannot represent multiple closures")
    if len(closure_dates) != len(set(closure_dates)):
        raise QualificationError("one closure cannot map to multiple accepted sessions")
    if any(row["session_date"] >= row["closure_date"] for row in rows):
        raise QualificationError("pre-holiday session must precede the closure")
    return {
        "accepted_event_count": len(rows),
        "early_close_event_count": sum(row["is_early_close"] for row in rows),
        "event_definition": (
            "One last accepted XNYS session before each accepted scheduled full-day holiday."
        ),
        "ordinary_early_close_generates_event": False,
        "qualification_id": QUALIFICATION_ID,
        "rows": rows,
        "version": 1,
    }


def build_bundle(
    source_dir: Path, specs: Sequence[Mapping[str, Any]] = SOURCE_SPECS
) -> dict[str, dict[str, Any]]:
    _validate_official_calendar_constants()
    source_manifest = qualify_sources(source_dir, specs)
    denominator = build_holiday_denominator()
    early_closes = build_early_close_identity()
    ad_hoc = build_ad_hoc_identity()
    sessions = build_accepted_preholiday_sessions(denominator, early_closes)
    components: dict[str, dict[str, Any]] = {
        "holiday_denominator.json": denominator,
        "accepted_pre_holiday_sessions.json": sessions,
        "early_close_identity.json": early_closes,
        "ad_hoc_closure_identity.json": ad_hoc,
        "source_manifest.json": source_manifest,
    }
    component_hashes = {
        name: sha256_bytes(canonical_json(value)) for name, value in sorted(components.items())
    }
    components["input_qualification.json"] = {
        "accepted_annual_calendar_years": sorted(QUALIFIED_ANNUAL_YEARS),
        "accepted_pre_holiday_event_count": sessions["accepted_event_count"],
        "ad_hoc_block_count": ad_hoc["block_count"],
        "ad_hoc_closure_date_count": ad_hoc["closure_date_count"],
        "blocked_annual_calendar_years": list(BLOCKED_ANNUAL_YEARS),
        "boundaries": {
            "database_or_cache_write_performed": False,
            "market_price_data_accessed": False,
            "network_performed_by_qualification": False,
            "outcome_accessed": False,
            "strategy_candidate_available": False,
            "strategy_execution_performed": False,
        },
        "component_sha256": component_hashes,
        "current_status": "blocked-on-data",
        "early_close_identity_complete_2010_2021": False,
        "gate_counts": None,
        "input_scope": "CALENDAR_AND_PRE_HOLIDAY_EVENT_IDENTITY_ONLY",
        "price_panel_checked": False,
        "qualification_id": QUALIFICATION_ID,
        "residual_blockers": [
            "official_annual_calendar_archives_missing_2010_2021",
            "official_early_close_identity_incomplete_2010_2021",
            "historical_rule_version_identity_incomplete_2010_2016",
            "full_2010_2026_calendar_input_cannot_be_accepted_until_all_gaps_close",
        ],
        "source_snapshot_sha256": source_manifest["source_snapshot_sha256"],
        "status": "INPUT_BLOCKED_NONTERMINAL",
        "strategy_candidate_available": False,
        "target_end": TARGET_END.isoformat(),
        "target_start": TARGET_START.isoformat(),
        "version": 1,
    }
    if tuple(components) != OUTPUT_NAMES:
        raise QualificationError("output scope changed")
    return components


def write_bundle(bundle: Mapping[str, Mapping[str, Any]], output_dir: Path) -> dict[str, str]:
    if output_dir.exists():
        raise QualificationError("output directory already exists; overwrite is forbidden")
    if set(bundle) != set(OUTPUT_NAMES):
        raise QualificationError("bundle must contain exactly the six frozen JSON files")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent))
    hashes: dict[str, str] = {}
    try:
        for name in OUTPUT_NAMES:
            raw = canonical_json(bundle[name])
            (temporary / name).write_bytes(raw)
            hashes[name] = sha256_bytes(raw)
        os.replace(temporary, output_dir)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return hashes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    if args.source_dir is None and args.output_dir is None:
        print(
            json.dumps(
                {
                    "files_written": False,
                    "network_executed": False,
                    "qualification_id": QUALIFICATION_ID,
                    "source_count": len(SOURCE_SPECS),
                    "status": "DRY_RUN_PLAN",
                },
                sort_keys=True,
            )
        )
        return 0
    if args.source_dir is None or args.output_dir is None:
        raise QualificationError("--source-dir and --output-dir must be supplied together")
    bundle = build_bundle(args.source_dir)
    hashes = write_bundle(bundle, args.output_dir)
    print(
        json.dumps(
            {
                "file_count": len(hashes),
                "files": hashes,
                "status": bundle["input_qualification.json"]["status"],
                "strategy_candidate_available": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
