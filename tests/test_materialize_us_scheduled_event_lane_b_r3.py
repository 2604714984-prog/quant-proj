import json
from pathlib import Path
from urllib.request import HTTPRedirectHandler, Request

import pytest

from scripts import materialize_us_scheduled_event_lane_b_r3 as r3


def test_meeting_end_date_uses_heading_not_statement_url():
    assert r3.meeting_end_date("June 27-28 Meeting - 2007") == "2007-06-28"
    assert r3.meeting_end_date("January 31-February 1 Meeting - 1995") == "1995-02-01"
    assert r3.meeting_end_date("March 25 Meeting - 1997") == "1997-03-25"


def test_fomc_parser_separates_calls_and_anchors_exact_minutes_url():
    raw = b"""
    <div class="panel panel-default"><h5>June 27-28 Meeting - 2007</h5>
      <a href="/newsevents/press/monetary/20070618a.htm">Statement</a>
      <a href="/monetarypolicy/fomcminutes20070628.htm">HTML</a>
      <a href="/monetarypolicy/files/FOMC20070628meeting.pdf">Transcript (PDF)</a>
    </div>
    <div class="panel panel-default"><h5>August 10 Conference Call - 2007</h5>
      <a href="/newsevents/press/monetary/20070810a.htm">Statement</a>
    </div>
    """
    rows = r3.parse_fomc_year(raw, 2007)
    assert rows[0]["event_id"] == "FOMC-20070628"
    assert rows[0]["statement_url"].endswith("20070618a.htm")
    assert rows[0]["minutes_url"].endswith("fomcminutes20070628.htm")
    assert rows[0]["section"] == "SCHEDULED_MEETING"
    assert rows[1]["section"] == "CONFERENCE_CALL_EXCLUDED"


def test_same_day_last_update_is_observed_but_not_actual(monkeypatch, tmp_path):
    statement = b"""
      <p>Release Date: March 25, 1997</p>
      <p>For immediate release</p>
      <p>Last update: March 25, 1997 3:00 PM</p>
    """

    def fake_fetch(source_id, url, raw_root):
        raw = statement if source_id.endswith("_statement") else b"document"
        return (
            {
                "final_url": url,
                "redirect_chain": [],
                "redirect_count": 0,
                "sha256": r3.digest(raw),
                "source_id": source_id,
                "status": "MATERIALIZED",
                "url": url,
            },
            raw,
        )

    monkeypatch.setattr(r3, "fetch_once", fake_fetch)
    result = r3.materialize_fomc(
        [
            {
                "event_id": "FOMC-19970325",
                "meeting_label": "March 25 Meeting - 1997",
                "minutes_url": "https://www.federalreserve.gov/fomc/minutes/19970325.htm",
                "statement_date": "1997-03-25",
                "statement_url": "https://www.federalreserve.gov/statement.htm",
                "transcript_url": "https://www.federalreserve.gov/transcript.pdf",
            }
        ],
        tmp_path,
        [],
    )
    assert result["accepted_actual_timestamp_count"] == 0
    assert result["same_day_page_availability_timestamp_count_not_accepted_as_actual"] == 1
    assert (
        result["records"][0]["observed_same_day_page_availability_timestamp"]
        == "1997-03-25T15:00:00-05:00"
    )
    assert result["records"][0]["actual_publication_timestamp"] is None
    assert result["status"] == "INPUT_BLOCKED_NONTERMINAL"


def test_minutes_planned_time_is_not_actual():
    raw = b"The Committee approved a statement to be released at 2:15 p.m."
    assert r3.planned_minutes_time(raw) == "14:15:00"


def test_bls_index_and_embargo_header_parsers():
    index = b"""
      <h3>1998</h3>
      <a href="/news.release/history/empsit_110598.txt">October</a>
      <a href="/news.release/archives/empsit_11051998.pdf">October PDF</a>
    """
    links = r3.parse_bls_index(
        index,
        "empsit",
        "https://www.bls.gov/bls/news-release/empsit.htm",
    )
    assert len(links) == 2
    assert {(row["reference_year"], row["reference_month"]) for row in links} == {
        (1998, "October")
    }
    parsed = r3.parse_bls_release(
        b"FOR RELEASE: 1:30 P.M. (EST) Thursday, November 5, 1998"
    )
    assert parsed == {
        "actual_release_date": "1998-11-05",
        "actual_release_time_local": "13:30:00",
        "embargo_wording": "FOR RELEASE: 1:30 P.M. (EST) Thursday, November 5, 1998",
        "timezone": "America/New_York",
    }


def test_expiration_candidates_remain_unqualified_and_mutually_exclusive(tmp_path):
    parent = {"expiration_candidates": []}
    for index in range(192):
        event_date = f"{1800 + index:04d}-01-01"
        parent["expiration_candidates"].append(
            {
                "event_date": event_date,
                "mechanism": "M6" if index < 128 else "M7",
                "ordinary_third_friday": event_date,
            }
        )
    (tmp_path / "event_identities.json").write_text(json.dumps(parent))
    result = r3.materialize_expirations(tmp_path, set(), {})
    assert result["M6"]["candidate_count"] == 128
    assert result["M7"]["candidate_count"] == 64
    assert result["M6"]["status"] == "INPUT_BLOCKED_NONTERMINAL"
    assert result["M7"]["status"] == "INPUT_BLOCKED_NONTERMINAL"
    assert all(row["legal_contract_expiration_date"] is None for row in result["records"])


def test_insecure_same_host_redirect_is_upgraded_without_http_request(monkeypatch):
    monkeypatch.setattr(
        HTTPRedirectHandler,
        "redirect_request",
        lambda self, req, fp, code, msg, headers, newurl: newurl,
    )
    handler = r3.BoundedRedirects("https://www.federalreserve.gov/old")
    followed = handler.redirect_request(
        Request("https://www.federalreserve.gov/old"),
        None,
        302,
        "Found",
        {},
        "http://www.federalreserve.gov/new",
    )
    assert followed == "https://www.federalreserve.gov/new"
    assert handler.chain[0]["insecure_same_host_location_upgraded_without_http_request"] is True


def test_bls_event_slots_use_actual_release_period_boundary():
    slots = r3.bls_event_slots()
    assert len(slots) == 192
    assert slots[0] == {
        "expected_actual_release_month": "1994-01",
        "reference_month": "December",
        "reference_year": 1993,
    }
    assert slots[-1] == {
        "expected_actual_release_month": "2009-12",
        "reference_month": "November",
        "reference_year": 2009,
    }


def test_static_pdf_challenge_is_not_content_qualified():
    assert (
        r3.static_content_qualification("cboe_good_friday_2000", b"<html>challenge</html>")
        == "CONTENT_MISMATCH"
    )
    assert (
        r3.static_content_qualification("cboe_good_friday_2000", b"%PDF-1.7 data")
        == "CONTENT_QUALIFIED"
    )


def test_bls_rejects_links_from_unqualified_index(monkeypatch, tmp_path):
    challenge_with_link = b"""
      <h3>1994</h3>
      <a href="/news.release/history/cpi_021794.txt">January</a>
    """

    def forbidden_fetch(*args, **kwargs):
        raise AssertionError("unqualified index links must not be fetched")

    monkeypatch.setattr(r3, "fetch_once", forbidden_fetch)
    result = r3.materialize_bls(
        {
            "bls_cpi_index": challenge_with_link,
            "bls_empsit_index": challenge_with_link,
        },
        tmp_path,
        [],
        set(),
    )
    assert result["M4"]["index_linked_logical_reference_month_count"] == 0
    assert result["M5"]["index_linked_logical_reference_month_count"] == 0
    assert result["M4"]["materialized_event_record_count"] == 192
    assert result["M5"]["materialized_event_record_count"] == 192
    assert result["M4"]["status"] == "INPUT_BLOCKED_NONTERMINAL"


def test_boundary_source_has_no_database_or_outcome_access():
    source = Path(r3.__file__).read_text()
    forbidden = ("import duckdb", "SELECT trade_date", "adj_close", "event_return")
    assert not any(token in source for token in forbidden)
    assert '"price_or_return_accessed": False' in source
    assert '"strategy_execution_performed": False' in source


def test_fixed_url_rejects_nonofficial_or_insecure_hosts():
    with pytest.raises(ValueError):
        r3.fixed_url("http://www.federalreserve.gov/example")
    with pytest.raises(ValueError):
        r3.fixed_url("https://example.com/example")
