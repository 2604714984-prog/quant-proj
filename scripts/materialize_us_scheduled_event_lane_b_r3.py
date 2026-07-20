#!/usr/bin/env python3
"""Materialize Lane B R3 official event identities without opening outcomes.

The script reads the accepted Lane B v1 public-document bundle, performs one
bounded GET per official URL, and writes raw content-addressed bytes outside
Git.  It never imports DuckDB and never reads prices, returns, validation, or
holdout data.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from zoneinfo import ZoneInfo

TASK_ID = "US_SCHEDULED_EVENT_LANE_B_OFFICIAL_IDENTITY_MATERIALIZATION_R3"
EXPECTED_PARENT_OUTPUT_MANIFEST_SHA256 = (
    "66703c6805b811e8d7a9ab1b03ccf47ea794b839134200a7c4333dd75cb926b8"
)
EXPECTED_PARENT_RECEIPT_SHA256 = (
    "032a681069c42bb78b8c1c4401c949f70ad3195275452f3bbf3cb6ea14cbfdf8"
)
MAX_RESPONSE_BYTES = 20 * 1024 * 1024
TIMEOUT_SECONDS = 30
USER_AGENT = "quant-proj/2.0 2604714984-prog@users.noreply.github.com"
ALLOWED_HOSTS = {
    "cdn.cboe.com",
    "federalreserve.gov",
    "sec.gov",
    "theocc.com",
    "www.bls.gov",
    "www.cmegroup.com",
    "www.federalreserve.gov",
    "www.nyse.com",
    "www.sec.gov",
    "www.theocc.com",
}
HOST_EQUIVALENCE = (
    frozenset({"federalreserve.gov", "www.federalreserve.gov"}),
    frozenset({"sec.gov", "www.sec.gov"}),
    frozenset({"theocc.com", "www.theocc.com"}),
)
MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
EXPECTED_FOMC_BY_YEAR = {
    1994: 5,
    1995: 3,
    1996: 1,
    1997: 1,
    1998: 2,
    1999: 6,
    **{year: 8 for year in range(2000, 2010)},
}
AD_HOC_CLOSURES = [
    "1994-04-27",
    "2001-09-11",
    "2001-09-12",
    "2001-09-13",
    "2001-09-14",
    "2004-06-11",
    "2007-01-02",
]
STATIC_SOURCES = {
    "bls_cpi_index": "https://www.bls.gov/bls/news-release/cpi.htm",
    "bls_empsit_index": "https://www.bls.gov/bls/news-release/empsit.htm",
    "bls_historical_release_dates": "https://www.bls.gov/bls/histreleasedates.pdf",
    "occ_historical_odd_index": (
        "https://www.theocc.com/company-information/documents-and-archives/"
        "options-disclosure-document/historical-options-disclosure-documents"
    ),
    "sec_standard_expiration_rule": "https://www.sec.gov/files/rules/final/34-45956.htm",
    "sec_occ_expiration_change": (
        "https://www.sec.gov/rules-regulations/self-regulatory-organization-rulemaking/"
        "sr-occ-2013-802"
    ),
    "cboe_good_friday_2000": (
        "https://cdn.cboe.com/resources/regulation/circulars/regulatory/RG00-039.pdf"
    ),
    "cboe_good_friday_2008": (
        "https://cdn.cboe.com/resources/regulation/circulars/regulatory/RG08-019.pdf"
    ),
    "cme_good_friday_2008": (
        "https://www.cmegroup.com/tools-information/lookups/advisories/market-data/"
        "Q2008-045.html"
    ),
    "sec_1997_market_break_report": "https://www.sec.gov/news/studies/tradrep.htm",
    "sec_2001_market_recovery": "https://www.sec.gov/news/testimony/ts102003sec.htm",
    "sec_2004_reagan_closure": "https://www.sec.gov/news/press/2004-77.htm",
    "nyse_current_hours_calendar": "https://www.nyse.com/markets/hours-calendars",
}
STATIC_TEXT_MARKERS = {
    "bls_cpi_index": ("consumer price index", "archived news releases"),
    "bls_empsit_index": ("employment situation", "archived news releases"),
    "occ_historical_odd_index": ("historical", "options disclosure"),
    "sec_standard_expiration_rule": ("34-45956",),
    "sec_occ_expiration_change": ("sr-occ-2013-802",),
    "cme_good_friday_2008": ("q2008-045",),
    "sec_1997_market_break_report": ("october 27, 1997",),
    "sec_2001_market_recovery": ("september 11",),
    "sec_2004_reagan_closure": ("june 11",),
    "nyse_current_hours_calendar": ("holidays",),
}
STATIC_PDF_SOURCES = {
    "bls_historical_release_dates",
    "cboe_good_friday_2000",
    "cboe_good_friday_2008",
}


def canonical(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def file_digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def clean_html(raw: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()


def fixed_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"non-official or non-HTTPS URL: {url}")
    return url


def equivalent_hosts(host: str) -> frozenset[str]:
    return next((group for group in HOST_EQUIVALENCE if host in group), frozenset({host}))


class BoundedRedirects(HTTPRedirectHandler):
    def __init__(self, initial_url: str) -> None:
        super().__init__()
        self.count = 0
        self.chain: list[dict[str, str | int]] = []
        initial_host = urlparse(initial_url).hostname
        if initial_host is None:
            raise ValueError("redirect policy requires an initial host")
        self.allowed_hosts = equivalent_hosts(initial_host)

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        self.count += 1
        if self.count > 3:
            raise HTTPError(newurl, code, "redirect ceiling exceeded", headers, fp)
        resolved = urljoin(req.full_url, newurl)
        parsed = urlparse(resolved)
        request_host = urlparse(req.full_url).hostname
        if parsed.hostname not in self.allowed_hosts:
            raise ValueError(f"redirect host outside frozen equivalence set: {resolved}")
        followed_url = resolved
        insecure_same_host_upgrade = False
        if parsed.scheme == "http" and parsed.hostname == request_host:
            followed_url = parsed._replace(scheme="https").geturl()
            insecure_same_host_upgrade = True
        fixed_url(followed_url)
        self.chain.append(
            {
                "followed_url": followed_url,
                "http_status": code,
                "insecure_same_host_location_upgraded_without_http_request": (
                    insecure_same_host_upgrade
                ),
                "location": resolved,
            }
        )
        return super().redirect_request(req, fp, code, msg, headers, followed_url)


def extension(url: str, content_type: str | None) -> str:
    path_suffix = Path(urlparse(url).path).suffix.lower()
    if path_suffix in {".htm", ".html", ".pdf", ".txt"}:
        return path_suffix
    if content_type and "pdf" in content_type.lower():
        return ".pdf"
    if content_type and "text" in content_type.lower():
        return ".txt"
    return ".bin"


def fetch_once(source_id: str, url: str, raw_root: Path) -> tuple[dict[str, Any], bytes | None]:
    fixed_url(url)
    redirect_handler = BoundedRedirects(url)
    opener = build_opener(ProxyHandler({}), redirect_handler)
    started_at = utc_now()
    request = Request(
        url,
        headers={
            "Accept": "text/html,application/pdf,text/plain;q=0.9,*/*;q=0.5",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with opener.open(request, timeout=TIMEOUT_SECONDS) as response:  # nosec B310
            final_url = response.geturl()
            fixed_url(final_url)
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            completed_at = utc_now()
            if len(raw) > MAX_RESPONSE_BYTES:
                raise ValueError("response byte ceiling exceeded")
            sha = digest(raw)
            suffix = extension(final_url, response.headers.get("Content-Type"))
            filename = f"raw/{source_id}.{sha}{suffix}"
            (raw_root.parent / filename).write_bytes(raw)
            return (
                {
                    "bytes": len(raw),
                    "completed_at_utc": completed_at,
                    "content_type": response.headers.get("Content-Type"),
                    "etag": response.headers.get("ETag"),
                    "filename": filename,
                    "final_url": final_url,
                    "http_date": response.headers.get("Date"),
                    "last_modified": response.headers.get("Last-Modified"),
                    "redirect_chain": redirect_handler.chain,
                    "redirect_count": redirect_handler.count,
                    "sha256": sha,
                    "source_id": source_id,
                    "started_at_utc": started_at,
                    "status": "MATERIALIZED",
                    "url": url,
                },
                raw,
            )
    except HTTPError as exc:
        denial = exc.read(MAX_RESPONSE_BYTES + 1)
        return (
            {
                "completed_at_utc": utc_now(),
                "error_class": "HTTPError",
                "http_status": exc.code,
                "redirect_count": redirect_handler.count,
                "redirect_chain": redirect_handler.chain,
                "response_bytes": len(denial),
                "response_sha256": digest(denial),
                "source_id": source_id,
                "started_at_utc": started_at,
                "status": "UNAVAILABLE",
                "url": url,
            },
            None,
        )
    except (OSError, TimeoutError, URLError, ValueError) as exc:
        return (
            {
                "completed_at_utc": utc_now(),
                "error_class": type(exc).__name__,
                "error_message": str(exc),
                "redirect_count": redirect_handler.count,
                "redirect_chain": redirect_handler.chain,
                "source_id": source_id,
                "started_at_utc": started_at,
                "status": "UNAVAILABLE",
                "url": url,
            },
            None,
        )


def static_content_qualification(source_id: str, raw: bytes | None) -> str:
    if raw is None:
        return "TRANSPORT_UNAVAILABLE"
    if source_id in STATIC_PDF_SOURCES:
        return "CONTENT_QUALIFIED" if raw.startswith(b"%PDF-") else "CONTENT_MISMATCH"
    markers = STATIC_TEXT_MARKERS.get(source_id)
    if markers is None:
        return "NO_MARKER_CONTRACT"
    text = raw.decode("utf-8", "replace").lower()
    return "CONTENT_QUALIFIED" if all(marker in text for marker in markers) else "CONTENT_MISMATCH"


def meeting_end_date(heading: str) -> str:
    match = re.fullmatch(r"(.+) (?:Meeting|Conference Call) - ((?:19|20)\d{2})", heading)
    if not match:
        raise ValueError(f"unrecognized scheduled-meeting heading: {heading}")
    date_text, year_text = match.groups()
    cross_month = re.fullmatch(
        r"[A-Z][a-z]+\s+\d{1,2}-([A-Z][a-z]+)\s+(\d{1,2})",
        date_text,
    )
    same_month = re.fullmatch(r"([A-Z][a-z]+)\s+\d{1,2}-(\d{1,2})", date_text)
    single = re.fullmatch(r"([A-Z][a-z]+)\s+(\d{1,2})", date_text)
    if cross_month:
        month, day = cross_month.groups()
    elif same_month:
        month, day = same_month.groups()
    elif single:
        month, day = single.groups()
    else:
        raise ValueError(f"unrecognized meeting date range: {heading}")
    return datetime.strptime(f"{month} {day}, {year_text}", "%B %d, %Y").date().isoformat()


def parse_fomc_year(raw: bytes, year: int) -> list[dict[str, str | None]]:
    text = raw.decode("utf-8", "replace")
    records: list[dict[str, str | None]] = []
    for panel in text.split('<div class="panel panel-default">')[1:]:
        heading_match = re.search(r"<h5>(.*?)</h5>", panel, re.I | re.S)
        if not heading_match:
            continue
        heading = clean_html(heading_match.group(1))
        links = []
        for href, label in re.findall(
            r"<a\s+[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",
            panel,
            re.I | re.S,
        ):
            links.append((urljoin("https://www.federalreserve.gov/", href), clean_html(label)))
        statements = [url for url, label in links if label == "Statement"]
        if not statements:
            continue
        if "Conference Call" in heading:
            section = "CONFERENCE_CALL_EXCLUDED"
        elif "Meeting" in heading:
            section = "SCHEDULED_MEETING"
        else:
            section = "UNCLASSIFIED"
        minutes = next(
            (
                url
                for url, _label in links
                if re.search(
                    r"/(?:fomc/minutes/(?:\d{4}/)?\d{8}(?:min)?|"
                    r"monetarypolicy/fomc(?:minutes)?\d{8})\.htm$",
                    urlparse(url).path,
                    re.I,
                )
            ),
            None,
        )
        transcripts = [url for url, label in links if label.startswith("Transcript")]
        event_date = meeting_end_date(heading)
        records.append(
            {
                "event_id": f"FOMC-{event_date.replace('-', '')}",
                "meeting_label": heading,
                "minutes_url": minutes,
                "section": section,
                "statement_date": event_date,
                "statement_url": statements[0],
                "transcript_url": transcripts[0] if transcripts else None,
                "year_page": f"fed_fomc_{year}",
            }
        )
    return records


def statement_evidence(raw: bytes) -> dict[str, str | None]:
    text = clean_html(raw.decode("utf-8", "replace"))
    release_match = re.search(
        r"Release Date:\s*([A-Z][a-z]+\s+\d{1,2},\s+\d{4})",
        text,
    )
    update_match = re.search(
        r"Last update:\s*([A-Z][a-z]+\s+\d{1,2},\s+\d{4}),?\s+"
        r"(\d{1,2}:\d{2})\s*(AM|PM)",
        text,
        re.I,
    )
    release_date = None
    page_time = None
    basis = "OFFICIAL_STATEMENT_PAGE_DATE_ONLY"
    if release_match:
        release_date = datetime.strptime(release_match.group(1), "%B %d, %Y").date().isoformat()
    if update_match:
        update_date = datetime.strptime(update_match.group(1), "%B %d, %Y").date().isoformat()
        if update_date == release_date and "For immediate release" in text:
            page_time = datetime.strptime(
                f"{update_match.group(2)} {update_match.group(3).upper()}", "%I:%M %p"
            ).time().strftime("%H:%M:%S")
            basis = "OFFICIAL_STATEMENT_PAGE_SAME_DAY_LAST_UPDATE_TIME"
    return {
        "page_availability_time_local": page_time,
        "release_date": release_date,
        "time_evidence_basis": basis,
    }


def planned_minutes_time(raw: bytes | None) -> str | None:
    if raw is None:
        return None
    text = clean_html(raw.decode("utf-8", "replace"))
    match = re.search(
        r"(?:to be released|for release)\s+at\s+(\d{1,2}:\d{2})\s*([ap]\.m\.)",
        text,
        re.I,
    )
    if not match:
        return None
    return datetime.strptime(
        f"{match.group(1)} {match.group(2).replace('.', '').upper()}", "%I:%M %p"
    ).time().strftime("%H:%M:%S")


class BLSIndexParser(HTMLParser):
    def __init__(self, series: str) -> None:
        super().__init__()
        self.series = series
        self.in_heading = False
        self.heading_parts: list[str] = []
        self.reference_year: int | None = None
        self.anchor_href: str | None = None
        self.anchor_parts: list[str] = []
        self.links: list[dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"h2", "h3", "h4", "h5"}:
            self.in_heading = True
            self.heading_parts = []
        if tag == "a":
            self.anchor_href = dict(attrs).get("href")
            self.anchor_parts = []

    def handle_data(self, data: str) -> None:
        if self.in_heading:
            self.heading_parts.append(data)
        if self.anchor_href is not None:
            self.anchor_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"h2", "h3", "h4", "h5"} and self.in_heading:
            heading = " ".join("".join(self.heading_parts).split())
            match = re.search(r"\b(199[4-9]|200\d)\b", heading)
            self.reference_year = int(match.group(1)) if match else None
            self.in_heading = False
        if tag == "a" and self.anchor_href is not None:
            label = " ".join("".join(self.anchor_parts).split())
            path = self.anchor_href.lower()
            if (
                self.reference_year is not None
                and f"/{self.series}_" in path
                and path.endswith((".txt", ".pdf", ".htm", ".html"))
            ):
                month = next(
                    (
                        name
                        for name in (
                            "January",
                            "February",
                            "March",
                            "April",
                            "May",
                            "June",
                            "July",
                            "August",
                            "September",
                            "October",
                            "November",
                            "December",
                        )
                        if name.lower() in label.lower()
                    ),
                    None,
                )
                self.links.append(
                    {
                        "href": self.anchor_href,
                        "label": label,
                        "reference_month": month,
                        "reference_year": self.reference_year,
                    }
                )
            self.anchor_href = None
            self.anchor_parts = []


def parse_bls_index(raw: bytes, series: str, base_url: str) -> list[dict[str, Any]]:
    parser = BLSIndexParser(series)
    parser.feed(raw.decode("utf-8", "replace"))
    result = []
    seen = set()
    for row in parser.links:
        url = urljoin(base_url, row["href"])
        key = (row["reference_year"], row["reference_month"], url)
        if key in seen:
            continue
        seen.add(key)
        result.append({**row, "url": url})
    return result


def parse_bls_release(raw: bytes) -> dict[str, str | None]:
    text = clean_html(raw.decode("latin-1", "replace"))
    match = re.search(
        r"(?:embargoed(?:\s+until)?|for\s+release:)\s*"
        r"(\d{1,2}:\d{2})\s*(a\.?m\.?|p\.?m\.?)\s*"
        r"\((EST|EDT|ET)\)\s*"
        r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+"
        r"([A-Z][a-z]+\s+\d{1,2},\s+\d{4})",
        text,
        re.I,
    )
    if not match:
        return {
            "actual_release_date": None,
            "actual_release_time_local": None,
            "embargo_wording": None,
            "timezone": None,
        }
    local_time = datetime.strptime(
        f"{match.group(1)} {match.group(2).replace('.', '').upper()}", "%I:%M %p"
    ).time().strftime("%H:%M:%S")
    return {
        "actual_release_date": datetime.strptime(match.group(4), "%B %d, %Y")
        .date()
        .isoformat(),
        "actual_release_time_local": local_time,
        "embargo_wording": match.group(0),
        "timezone": "America/New_York",
    }


def bls_event_slots() -> list[dict[str, Any]]:
    slots = []
    for actual_year in range(1994, 2010):
        for actual_month_index, actual_month in enumerate(MONTHS, start=1):
            if actual_month_index == 1:
                reference_year = actual_year - 1
                reference_month = "December"
            else:
                reference_year = actual_year
                reference_month = MONTHS[actual_month_index - 2]
            slots.append(
                {
                    "expected_actual_release_month": f"{actual_year}-{actual_month_index:02d}",
                    "reference_month": reference_month,
                    "reference_year": reference_year,
                }
            )
    return slots


def parent_fomc_sources(parent_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    receipt_path = parent_root / "receipt.json"
    manifest_path = parent_root / "output_manifest.json"
    if file_digest(receipt_path) != EXPECTED_PARENT_RECEIPT_SHA256:
        raise ValueError("parent receipt is not the accepted Lane B v1 identity")
    if file_digest(manifest_path) != EXPECTED_PARENT_OUTPUT_MANIFEST_SHA256:
        raise ValueError("parent output manifest is not the accepted Lane B v1 identity")
    output_manifest = json.loads(manifest_path.read_text())
    for filename, identity in output_manifest["outputs"].items():
        child_path = parent_root / filename
        if file_digest(child_path) != identity["sha256"]:
            raise ValueError(f"parent output child hash mismatch: {filename}")
        if child_path.stat().st_size != identity["bytes"]:
            raise ValueError(f"parent output child size mismatch: {filename}")
    receipt = json.loads(receipt_path.read_text())
    source_rows = {
        row["source_id"]: row
        for row in receipt["source_resources"]
        if row["source_id"].startswith("fed_fomc_") and row["status"] == "MATERIALIZED"
    }
    if sorted(source_rows) != [f"fed_fomc_{year}" for year in range(1994, 2010)]:
        raise ValueError("parent bundle lacks the 16 frozen FOMC year pages")
    resources = []
    candidates = []
    for year in range(1994, 2010):
        row = source_rows[f"fed_fomc_{year}"]
        source_path = parent_root / row["filename"]
        if file_digest(source_path) != row["sha256"]:
            raise ValueError(f"parent FOMC hash mismatch: {source_path.name}")
        resources.append(
            {
                "bytes": source_path.stat().st_size,
                "filename": f"scheduled_events/lane_b/v1/{row['filename']}",
                "sha256": row["sha256"],
                "source_id": row["source_id"],
                "status": "PARENT_BUNDLE_REFERENCED",
                "url": row["url"],
            }
        )
        candidates.extend(parse_fomc_year(source_path.read_bytes(), year))
    scheduled = [row for row in candidates if row["section"] == "SCHEDULED_MEETING"]
    calls = [row for row in candidates if row["section"] == "CONFERENCE_CALL_EXCLUDED"]
    counts = {year: 0 for year in EXPECTED_FOMC_BY_YEAR}
    for row in scheduled:
        counts[int(str(row["statement_date"])[:4])] += 1
    if counts != EXPECTED_FOMC_BY_YEAR or len(scheduled) != 98 or len(calls) != 10:
        raise ValueError(f"unexpected FOMC denominator: scheduled={len(scheduled)} calls={len(calls)}")
    return resources, scheduled


def materialize_fomc(
    candidates: list[dict[str, Any]], raw_root: Path, resources: list[dict[str, Any]]
) -> dict[str, Any]:
    records = []
    for candidate in sorted(candidates, key=lambda row: row["statement_date"]):
        token = candidate["event_id"].replace("-", "_").lower()
        statement_resource, statement_raw = fetch_once(
            f"{token}_statement", str(candidate["statement_url"]), raw_root
        )
        resources.append(statement_resource)
        minutes_resource = None
        minutes_raw = None
        if candidate["minutes_url"]:
            minutes_resource, minutes_raw = fetch_once(
                f"{token}_minutes", str(candidate["minutes_url"]), raw_root
            )
            resources.append(minutes_resource)
        transcript_resource = None
        if candidate["transcript_url"]:
            transcript_resource, _transcript_raw = fetch_once(
                f"{token}_transcript", str(candidate["transcript_url"]), raw_root
            )
            resources.append(transcript_resource)
        evidence = (
            statement_evidence(statement_raw)
            if statement_raw is not None
            else {
                "page_availability_time_local": None,
                "release_date": None,
                "time_evidence_basis": "STATEMENT_BYTES_UNAVAILABLE",
            }
        )
        page_time = evidence["page_availability_time_local"]
        release_date = evidence["release_date"]
        statement_date_matches = release_date == candidate["statement_date"]
        page_timestamp = None
        if page_time is not None and statement_date_matches:
            local = datetime.fromisoformat(f"{release_date}T{page_time}").replace(
                tzinfo=ZoneInfo("America/New_York")
            )
            page_timestamp = local.isoformat()
        accepted = evidence["time_evidence_basis"] == "ACTUAL_EXPLICIT_OFFICIAL"
        records.append(
            {
                "accepted_actual_timestamp": accepted,
                "actual_publication_date": release_date if statement_date_matches else None,
                "actual_publication_timestamp": None,
                "event_id": candidate["event_id"],
                "meeting_dates": candidate["meeting_label"],
                "minutes": (
                    {
                        "final_url": minutes_resource.get("final_url"),
                        "planned_time_observed_not_accepted": planned_minutes_time(minutes_raw),
                        "sha256": minutes_resource.get("sha256"),
                        "status": minutes_resource["status"],
                        "url": candidate["minutes_url"],
                    }
                    if minutes_resource is not None
                    else None
                ),
                "missing_reason": (
                    None
                    if accepted
                    else (
                        "A same-release-day page Last update time is preserved but is not "
                        "accepted as first-publication evidence."
                        if page_timestamp is not None
                        else "Official records do not expose an accepted record-level actual time."
                    )
                ),
                "observed_same_day_page_availability_timestamp": page_timestamp,
                "qualification_status": (
                    "ACTUAL_PUBLICATION_TIMESTAMP_ACCEPTED"
                    if accepted
                    else "ACTUAL_PUBLICATION_TIMESTAMP_UNRESOLVED"
                ),
                "revision_or_cancellation_status": "UNQUALIFIED",
                "statement": {
                    "retrieved_at_utc": statement_resource.get("completed_at_utc"),
                    "final_url": statement_resource.get("final_url"),
                    "redirect_chain": statement_resource.get("redirect_chain", []),
                    "redirect_count": statement_resource.get("redirect_count", 0),
                    "release_date": release_date,
                    "release_date_matches_meeting_end_date": statement_date_matches,
                    "sha256": statement_resource.get("sha256"),
                    "status": statement_resource["status"],
                    "timestamp_evidence_source_id": statement_resource["source_id"],
                    "time_evidence_basis": evidence["time_evidence_basis"],
                    "url": candidate["statement_url"],
                },
                "timezone": "America/New_York" if page_timestamp is not None else None,
                "transcript": (
                    {
                        "final_url": transcript_resource.get("final_url"),
                        "sha256": transcript_resource.get("sha256"),
                        "status": transcript_resource["status"],
                        "url": candidate["transcript_url"],
                    }
                    if transcript_resource is not None
                    else None
                ),
            }
        )
    accepted_count = sum(row["accepted_actual_timestamp"] for row in records)
    page_time_count = sum(
        row["observed_same_day_page_availability_timestamp"] is not None for row in records
    )
    status = "IDENTITY_QUALIFIED" if accepted_count >= 94 else "INPUT_BLOCKED_NONTERMINAL"
    return {
        "accepted_actual_timestamp_count": accepted_count,
        "conference_call_links_excluded": 10,
        "maximum_allowed_incomplete": 4,
        "minimum_required_at_95_percent": 94,
        "records": records,
        "same_day_page_availability_timestamp_count_not_accepted_as_actual": page_time_count,
        "scheduled_statement_denominator": 98,
        "status": status,
    }


def materialize_bls(
    raw_by_source: dict[str, bytes | None],
    raw_root: Path,
    resources: list[dict[str, Any]],
    qualified_index_ids: set[str],
) -> dict[str, Any]:
    series_outputs = {}
    for mechanism, series, index_id in (
        ("M4", "cpi", "bls_cpi_index"),
        ("M5", "empsit", "bls_empsit_index"),
    ):
        index_raw = raw_by_source[index_id] if index_id in qualified_index_ids else None
        links = (
            parse_bls_index(index_raw, series, STATIC_SOURCES[index_id])
            if index_raw is not None
            else []
        )
        logical: dict[tuple[int, str | None], list[dict[str, Any]]] = {}
        for link in links:
            logical.setdefault((link["reference_year"], link["reference_month"]), []).append(link)
        records = []
        for slot in bls_event_slots():
            reference_year = slot["reference_year"]
            reference_month = slot["reference_month"]
            representations = logical.get((reference_year, reference_month), [])
            parsed_representations = []
            source_identities = []
            for index, link in enumerate(representations, start=1):
                source_id = f"bls_{series}_{reference_year}_{reference_month}_{index}".lower()
                resource, raw = fetch_once(source_id, link["url"], raw_root)
                resources.append(resource)
                parsed = None
                if raw is not None and not link["url"].lower().endswith(".pdf"):
                    parsed = parse_bls_release(raw)
                    if parsed["actual_release_date"] is not None:
                        parsed_representations.append(parsed)
                source_identities.append(
                    {
                        "final_url": resource.get("final_url"),
                        "parsed_release_header": parsed,
                        "retrieved_at_utc": resource.get("completed_at_utc"),
                        "sha256": resource.get("sha256"),
                        "source_id": source_id,
                        "status": resource["status"],
                        "url": link["url"],
                    }
                )
            identities = {
                (
                    item["actual_release_date"],
                    item["actual_release_time_local"],
                    item["timezone"],
                )
                for item in parsed_representations
            }
            accepted_release = parsed_representations[0] if len(identities) == 1 else None
            unparsed_materialized = any(
                item["status"] == "MATERIALIZED"
                and (
                    item["parsed_release_header"] is None
                    or item["parsed_release_header"]["actual_release_date"] is None
                )
                for item in source_identities
            )
            conflict = (
                series == "empsit"
                and reference_year == 1998
                and reference_month == "October"
            )
            release_in_slot = bool(
                accepted_release
                and str(accepted_release["actual_release_date"]).startswith(
                    slot["expected_actual_release_month"]
                )
            )
            accepted = bool(
                accepted_release
                and release_in_slot
                and not conflict
                and not unparsed_materialized
            )
            if not representations:
                identity_status = "OFFICIAL_ARCHIVE_LINK_UNRESOLVED"
            elif conflict:
                identity_status = "EARLIEST_PUBLIC_AVAILABILITY_CONFLICT"
            elif len(identities) > 1:
                identity_status = "CONFLICTING_REPRESENTATION_HEADERS"
            elif unparsed_materialized:
                identity_status = "REPRESENTATION_PARSER_INCOMPLETE"
            elif accepted:
                identity_status = "ACTUAL_RELEASE_HEADER_ACCEPTED"
            elif accepted_release and not release_in_slot:
                identity_status = "ACTUAL_RELEASE_MONTH_CONFLICT"
            else:
                identity_status = "ACTUAL_RELEASE_HEADER_UNRESOLVED"
            records.append(
                {
                    "accepted_actual_identity": accepted,
                    "actual_release": accepted_release,
                    "expected_actual_release_month": slot["expected_actual_release_month"],
                    "identity_status": identity_status,
                    "mechanism": mechanism,
                    "reference_month": reference_month,
                    "reference_year": reference_year,
                    "representation_count": len(representations),
                    "reschedule_or_delay_status": (
                        "EARLIEST_PUBLICATION_CONFLICT"
                        if conflict
                        else (
                            "ACTUAL_HEADER_PRESERVED_NO_SCHEDULE_INFERENCE"
                            if accepted_release is not None
                            else "NO_ACTUAL_HEADER_AVAILABLE"
                        )
                    ),
                    "revision_or_reissue_status": (
                        "MULTIPLE_REPRESENTATIONS_CONSISTENT"
                        if (
                            len(source_identities) > 1
                            and len(identities) == 1
                            and not unparsed_materialized
                        )
                        else "NOT_QUALIFIED"
                    ),
                    "source_identities": source_identities,
                }
            )
        accepted_count = sum(row["accepted_actual_identity"] for row in records)
        series_outputs[mechanism] = {
            "accepted_actual_release_identity_count": accepted_count,
            "actual_event_time_denominator": 192,
            "denominator_contract": (
                "Actual releases dated 1994-01-01 through 2009-12-31; December 1993 "
                "reference releases belong to January 1994 and December 2009 reference "
                "releases in January 2010 are excluded."
            ),
            "excluded_reference_period": {
                "reason": "December 2009 reference release occurred in January 2010.",
                "reference_month": "December",
                "reference_year": 2009,
                "representation_urls": [
                    row["url"] for row in logical.get((2009, "December"), [])
                ],
            },
            "index_linked_logical_reference_month_count": len(logical),
            "materialized_event_record_count": len(records),
            "records": records,
            "status": (
                "IDENTITY_QUALIFIED"
                if accepted_count >= 183
                else "INPUT_BLOCKED_NONTERMINAL"
            ),
            "unresolved_expected_event_slot_count": sum(
                not row["accepted_actual_identity"] for row in records
            ),
        }
    return {
        "M4": series_outputs["M4"],
        "M5": series_outputs["M5"],
        "status": (
            "BLS_IDENTITIES_QUALIFIED"
            if all(row["status"] == "IDENTITY_QUALIFIED" for row in series_outputs.values())
            else "BLS_INPUT_BLOCKED_NONTERMINAL"
        ),
    }


def materialize_expirations(
    parent_root: Path,
    materialized_ids: set[str],
    source_hashes: dict[str, str | None],
) -> dict[str, Any]:
    parent = json.loads((parent_root / "event_identities.json").read_text())
    candidates = parent["expiration_candidates"]
    if len(candidates) != 192:
        raise ValueError("parent expiration denominator is not 192")
    records = []
    for row in candidates:
        ordinary = row["ordinary_third_friday"]
        last_session = row["event_date"]
        exception_sources: list[str] = []
        if last_session == "2000-04-20":
            exception_sources = ["cboe_good_friday_2000"]
        elif last_session == "2008-03-20":
            exception_sources = ["cboe_good_friday_2008", "cme_good_friday_2008"]
        accepted_exception = bool(exception_sources) and all(
            source_id in materialized_ids for source_id in exception_sources
        )
        records.append(
            {
                "candidate_date": last_session,
                "exception_source_ids": exception_sources,
                "exception_source_materialized": accepted_exception,
                "exception_source_sha256": [source_hashes.get(item) for item in exception_sources],
                "identity_status": (
                    "OFFICIAL_EXCEPTION_OBSERVED_MECHANISM_STILL_UNQUALIFIED"
                    if accepted_exception
                    else "RULE_CANDIDATE_HISTORICAL_VERSION_UNQUALIFIED"
                ),
                "last_trading_session": last_session,
                "legal_contract_expiration_date": None,
                "mechanism": row["mechanism"],
                "options_identity": None,
                "ordinary_third_friday": ordinary,
                "expiration_processing_session": None,
                "futures_identity_for_m7": None,
                "rule_effective_end": None,
                "rule_effective_start": None,
                "rule_version": None,
                "strategy_event_session": last_session,
            }
        )
    m6 = [row for row in records if row["mechanism"] == "M6"]
    m7 = [row for row in records if row["mechanism"] == "M7"]
    shifts = [row for row in records if row["last_trading_session"] != row["ordinary_third_friday"]]
    if len(m6) != 128 or len(m7) != 64:
        raise ValueError("unexpected M6/M7 mechanism denominator")
    if len({row["candidate_date"] for row in records}) != 192:
        raise ValueError("expiration candidate dates are not unique")
    if {row["candidate_date"] for row in m6} & {row["candidate_date"] for row in m7}:
        raise ValueError("M6 and M7 candidate identities are not mechanically disjoint")
    return {
        "M6": {
            "accepted_official_historical_identity_count": 0,
            "blocking_reason": (
                "RECORD_LEVEL_RULE_VERSION_AND_2003_EXCEPTION_IDENTITY_INCOMPLETE"
            ),
            "candidate_count": len(m6),
            "status": "INPUT_BLOCKED_NONTERMINAL",
        },
        "M7": {
            "accepted_official_historical_identity_count": 0,
            "blocking_reason": "VERSIONED_HISTORICAL_RULE_IDENTITY_INCOMPLETE",
            "candidate_count": len(m7),
            "status": "INPUT_BLOCKED_NONTERMINAL",
        },
        "official_exception_observation_count": sum(
            row["exception_source_materialized"] for row in shifts
        ),
        "records": records,
        "shifted_candidate_count": len(shifts),
        "status": "M6_M7_INPUT_BLOCKED_NONTERMINAL",
    }


def materialize_xnys(
    parent_root: Path,
    materialized_ids: set[str],
    source_hashes: dict[str, str | None],
) -> dict[str, Any]:
    rows = json.loads((parent_root / "xnys_nyse_candidate.json").read_text())
    eastern = ZoneInfo("America/New_York")
    early = []
    for row in rows:
        close = datetime.fromisoformat(row["close_utc"]).astimezone(eastern)
        if (close.hour, close.minute) < (16, 0):
            source_id = "sec_1997_market_break_report" if row["session_date"] == "1997-10-27" else None
            early.append(
                {
                    "candidate_close_local": close.strftime("%H:%M:%S"),
                    "official_source_id": source_id,
                    "official_source_materialized": source_id in materialized_ids if source_id else False,
                    "official_source_sha256": source_hashes.get(source_id) if source_id else None,
                    "session_date": row["session_date"],
                    "status": (
                        "OFFICIAL_EXCEPTION_OBSERVED_CANDIDATE_STILL_NOT_CALENDAR_ACCEPTED"
                        if source_id in materialized_ids
                        else "OFFICIAL_RECORD_LEVEL_EVIDENCE_UNRESOLVED"
                    ),
                }
            )
    closures = []
    for day in AD_HOC_CLOSURES:
        if day.startswith("2001-09-"):
            source_id = "sec_2001_market_recovery"
        elif day == "2004-06-11":
            source_id = "sec_2004_reagan_closure"
        else:
            source_id = None
        closures.append(
            {
                "closure_date": day,
                "official_source_id": source_id,
                "official_source_materialized": source_id in materialized_ids if source_id else False,
                "official_source_sha256": source_hashes.get(source_id) if source_id else None,
                "status": (
                    "OFFICIAL_CLOSURE_OBSERVED_CANDIDATE_STILL_NOT_CALENDAR_ACCEPTED"
                    if source_id in materialized_ids
                    else "OFFICIAL_RECORD_LEVEL_EVIDENCE_UNRESOLVED"
                ),
            }
        )
    if len(rows) != 4030 or len(early) != 41 or len(closures) != 7:
        raise ValueError("unexpected XNYS candidate identity counts")
    receipt = json.loads((parent_root / "receipt.json").read_text())
    return {
        "ad_hoc_full_closures": closures,
        "candidate_generator_identity": {
            "candidate_file_sha256": file_digest(parent_root / "xnys_nyse_candidate.json"),
            "package": receipt["calendar"]["package"],
            "version": receipt["calendar"]["version"],
        },
        "candidate_ad_hoc_full_closure_count": len(closures),
        "candidate_early_close_count": len(early),
        "candidate_session_count": len(rows),
        "early_closes": early,
        "official_ad_hoc_observation_count": sum(
            row["official_source_materialized"] for row in closures
        ),
        "official_early_close_observation_count": sum(
            row["official_source_materialized"] for row in early
        ),
        "ordinary_holiday_identity_status": "OFFICIAL_HISTORICAL_RECORDS_NOT_MATERIALIZED",
        "status": "PARTIAL_OFFICIAL_EXCEPTION_EVIDENCE_CANDIDATE_RECONCILED_NOT_ACCEPTED",
    }


def write_json(path: Path, value: object) -> str:
    path.write_bytes(canonical(value))
    return file_digest(path)


def materialize(parent_root: Path, output_root: Path, report_root: Path) -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[1]
    output_root = output_root.resolve()
    report_root = report_root.resolve()
    expected_report_root = (
        repo_root / "reports/validation/us_scheduled_event_lane_b_r3"
    ).resolve()
    if report_root != expected_report_root:
        raise ValueError("report root must be the frozen R3 repository path")
    if output_root.is_relative_to(repo_root):
        raise ValueError("raw evidence output root must be outside the Git worktree")
    output_staging = output_root.with_name(f".{output_root.name}.staging")
    report_staging = report_root.with_name(f".{report_root.name}.staging")
    if any(path.exists() for path in (output_root, report_root, output_staging, report_staging)):
        raise FileExistsError("R3 final and staging roots must all be absent")
    raw_root = output_staging / "raw"
    raw_root.mkdir(parents=True, mode=0o700)
    output_staging.chmod(0o700)
    report_staging.mkdir(parents=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True).strip()
    tree = subprocess.check_output(
        ["git", "rev-parse", "HEAD^{tree}"], cwd=repo_root, text=True
    ).strip()
    resources, fomc_candidates = parent_fomc_sources(parent_root)
    raw_by_source: dict[str, bytes | None] = {}
    for source_id, url in STATIC_SOURCES.items():
        resource, raw = fetch_once(source_id, url, raw_root)
        resource["content_qualification_status"] = static_content_qualification(source_id, raw)
        resources.append(resource)
        raw_by_source[source_id] = raw
    materialized_ids = {
        row["source_id"]
        for row in resources
        if row.get("content_qualification_status") == "CONTENT_QUALIFIED"
    }
    fomc = materialize_fomc(fomc_candidates, raw_root, resources)
    bls = materialize_bls(
        raw_by_source,
        raw_root,
        resources,
        materialized_ids,
    )
    source_hashes = {
        row["source_id"]: row.get("sha256")
        for row in resources
        if row["source_id"] in materialized_ids
    }
    expirations = materialize_expirations(parent_root, materialized_ids, source_hashes)
    xnys = materialize_xnys(parent_root, materialized_ids, source_hashes)
    source_manifest = {
        "acquisition_contract": {
            "allowed_hosts": sorted(ALLOWED_HOSTS),
            "maximum_redirects_per_request": 3,
            "maximum_response_bytes": MAX_RESPONSE_BYTES,
            "method": "GET",
            "proxy_disabled": True,
            "retries": 0,
            "timeout_seconds": TIMEOUT_SECONDS,
        },
        "boundaries": {
            "canonical_database_accessed": False,
            "canonical_database_write_performed": False,
            "price_or_return_accessed": False,
            "provider_or_credential_accessed": False,
            "strategy_candidate_available": False,
            "strategy_execution_performed": False,
        },
        "materializer": {
            "path": "scripts/materialize_us_scheduled_event_lane_b_r3.py",
            "sha256": file_digest(Path(__file__)),
        },
        "parent_bundle": {
            "event_identities_sha256": file_digest(parent_root / "event_identities.json"),
            "output_manifest_sha256": file_digest(parent_root / "output_manifest.json"),
            "receipt_sha256": file_digest(parent_root / "receipt.json"),
            "xnys_candidate_sha256": file_digest(parent_root / "xnys_nyse_candidate.json"),
        },
        "repository": {"base_commit": head, "base_tree": tree},
        "resources": resources,
        "retrieved_at_utc": utc_now(),
        "schema_version": "lane-b-official-source-manifest-r3",
        "task_id": TASK_ID,
    }
    manifest_path = report_staging / "official_source_manifest.json"
    manifest_sha = write_json(manifest_path, source_manifest)
    common = {
        "official_source_manifest": {
            "path": "reports/validation/us_scheduled_event_lane_b_r3/official_source_manifest.json",
            "sha256": manifest_sha,
        },
        "repository": {"base_commit": head, "base_tree": tree},
        "strategy_candidate_available": False,
        "task_id": TASK_ID,
    }
    fomc_path = report_staging / "fomc_m3_identity_qualification.json"
    bls_path = report_staging / "bls_m4_m5_identity_qualification.json"
    expiration_path = report_staging / "expiration_m6_m7_identity_qualification.json"
    xnys_path = report_staging / "xnys_exception_qualification.json"
    hashes = {
        "fomc": write_json(fomc_path, {**common, **fomc}),
        "bls": write_json(bls_path, {**common, **bls}),
        "expiration": write_json(expiration_path, {**common, **expirations}),
        "xnys": write_json(xnys_path, {**common, **xnys}),
    }
    mechanisms = {
        "M3": fomc["status"],
        "M4": bls["M4"]["status"],
        "M5": bls["M5"]["status"],
        "M6": expirations["M6"]["status"],
        "M7": expirations["M7"]["status"],
    }
    joint = {
        **common,
        "artifacts": {
            "bls_m4_m5_identity_qualification.json": hashes["bls"],
            "expiration_m6_m7_identity_qualification.json": hashes["expiration"],
            "fomc_m3_identity_qualification.json": hashes["fomc"],
            "xnys_exception_qualification.json": hashes["xnys"],
        },
        "development_atlas_execution_authorized": False,
        "lane_b_input_qualified": (
            all(value == "IDENTITY_QUALIFIED" for value in mechanisms.values())
            and xnys["status"] == "OFFICIAL_CALENDAR_IDENTITIES_ACCEPTED"
        ),
        "mechanisms": mechanisms,
        "next_action": (
            "Fresh exact-head input review only. Price, return and Development access remain closed."
        ),
        "price_or_return_access_authorized": False,
        "schema_version": "lane-b-official-identity-joint-qualification-r3",
        "status": "PARTIAL_OFFICIAL_IDENTITY_MATERIALIZATION_INPUT_BLOCKED_NO_OUTCOME",
        "strategy_candidate_available": False,
        "xnys_calendar_identity_qualified": (
            xnys["status"] == "OFFICIAL_CALENDAR_IDENTITIES_ACCEPTED"
        ),
    }
    joint_path = report_staging / "lane_b_official_identity_joint_qualification.json"
    joint_sha = write_json(joint_path, joint)
    output_staging.replace(output_root)
    report_staging.replace(report_root)
    return {
        "joint_sha256": joint_sha,
        "mechanisms": mechanisms,
        "report_root": str(report_root),
        "status": joint["status"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--report-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(materialize(args.parent_root, args.output_root, args.report_root), indent=2))


if __name__ == "__main__":
    main()
