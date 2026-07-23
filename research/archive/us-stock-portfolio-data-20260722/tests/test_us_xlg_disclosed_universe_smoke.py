from __future__ import annotations

from datetime import date
import hashlib
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import smoke_us_xlg_disclosed_universe as smoke  # noqa: E402


def _atom_entry(accession: str, period: str, filing_date: str) -> str:
    compact = accession.replace("-", "")
    return f"""
    <entry>
      <updated>{filing_date}T12:34:56-04:00</updated>
      <content>
        <accession-number>{accession}</accession-number>
        <filing-date>{filing_date}</filing-date>
        <filing-href>https://www.sec.gov/Archives/edgar/data/1209466/{compact}/{accession}-index.htm</filing-href>
        <filing-type>NPORT-P</filing-type>
        <period>{period}</period>
      </content>
    </entry>
    """


def test_atom_selectors_are_frozen_and_outcome_independent() -> None:
    raw = (
        "<feed>"
        + _atom_entry("0000000000-19-000001", "2019-09-30", "2019-11-29")
        + _atom_entry("0000000000-22-000001", "2022-06-30", "2022-08-29")
        + _atom_entry("0000000000-25-000001", "2025-01-31", "2025-04-01")
        + _atom_entry("0000000000-26-000001", "2026-05-31", "2026-07-20")
        + "</feed>"
    ).encode()

    selected = smoke._select_four_entries(smoke._parse_atom_entries(raw))

    assert selected["EARLIEST_QUALIFIED"]["period"] == date(2019, 9, 30)
    assert selected["MID_2022"]["period"] == date(2022, 6, 30)
    assert selected["START_2025"]["period"] == date(2025, 1, 31)
    assert selected["LATEST_COMPLETE_PUBLIC"]["period"] == date(2026, 5, 31)


def test_nport_parser_checks_identity_and_excludes_non_common_rows() -> None:
    raw = b"""
    <edgarSubmission>
      <headerData>
        <filerInfo><filer><credentials><cik>1209466</cik></credentials></filer></filerInfo>
        <seriesClassInfo><seriesId>S000060793</seriesId><classId>C000197609</classId></seriesClassInfo>
      </headerData>
      <formData>
        <genInfo><repPdDate>2025-01-31</repPdDate></genInfo>
        <invstOrSecs>
          <invstOrSec>
            <name>Example Common Issuer</name><title>Common Stock</title>
            <cusip>123456789</cusip><assetCat>EC</assetCat>
            <identifiers><ticker value="EXM" /></identifiers>
          </invstOrSec>
          <invstOrSec>
            <name>Example Swap</name><title>Total Return Swap</title>
            <cusip>987654321</cusip><assetCat>DFE</assetCat>
          </invstOrSec>
        </invstOrSecs>
      </formData>
    </edgarSubmission>
    """

    summary = smoke._parse_nport_xml(raw)

    assert summary["report_date"] == "2025-01-31"
    assert summary["series_id_match"] is True
    assert summary["contract_id_match"] is True
    assert summary["registrant_cik_match"] is True
    assert summary["all_investment_rows"] == 2
    assert summary["eligible_common_equity_lines"] == 1
    assert summary["company_count"] == 1
    assert summary["excluded_investment_rows"] == 1


def test_next_complete_session_skips_early_close_holiday_and_weekend() -> None:
    assert smoke._next_complete_xnys_open("2025-07-02T15:00:00-04:00") == (
        "2025-07-07T09:30:00-04:00"
    )


def test_multiclass_snapshot_cannot_pass_without_frozen_60_session_input() -> None:
    summary = {
        "report_date": "2025-01-31",
        "company_count": 50,
        "eligible_common_equity_lines": 51,
        "duplicate_security_keys": 0,
        "issuer_name_conflict_count": 0,
        "multi_class_company_count": 1,
    }

    assert smoke._sec_snapshot_gate(summary, date(2025, 1, 31)) == [
        "trailing_60_session_dollar_volume_not_qualified_in_this_smoke"
    ]


def test_html_download_response_cannot_masquerade_as_csv_holdings() -> None:
    inspection = smoke._inspect_invesco_download(
        b"<html><body>shell,not,a,holdings,file</body></html>",
        "text/html;charset=utf-8",
    )

    assert inspection["format"] == "html"
    assert inspection["row_count"] is None
    assert inspection["column_count"] is None


def test_new_contract_and_prior_input_blocked_result_have_immutable_identities() -> None:
    contract = REPO_ROOT / "research/definitions/us_sp500_top50_xlg_disclosed_universe_v1.json"
    prior = REPO_ROOT / "research/results/us_stock_top50_input_blocked_20260722.json"

    assert hashlib.sha256(contract.read_bytes()).hexdigest() == smoke.CONTRACT_SHA256
    assert hashlib.sha256(prior.read_bytes()).hexdigest() == smoke.PRIOR_RESULT_SHA256
