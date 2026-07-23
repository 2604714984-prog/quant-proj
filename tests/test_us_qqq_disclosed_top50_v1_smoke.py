from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(
    0,
    str(
        REPO_ROOT
        / "research/archive/us_qqq_disclosed_top50_equal_weight_v1/scripts"
    ),
)

import smoke_us_qqq_disclosed_top50_v1 as smoke  # noqa: E402


def _submissions() -> dict:
    rows = []
    for report_date in smoke.SAMPLE_REPORT_DATES:
        year = int(report_date[:4]) + 1
        rows.append(
            {
                "accessionNumber": f"0001067839-{str(year)[-2:]}-000001",
                "acceptanceDateTime": f"{year}-02-28T20:00:00.000Z",
                "filingDate": f"{year}-02-28",
                "form": "NPORT-P",
                "primaryDocument": "xslFormNPORT-P_X01/primary_doc.xml",
                "reportDate": report_date,
            }
        )
    while len(rows) < smoke.MINIMUM_RECENT_FILINGS:
        index = len(rows)
        rows.append(
            {
                "accessionNumber": f"0001067839-20-{index:06d}",
                "acceptanceDateTime": "2020-06-01T20:00:00.000Z",
                "filingDate": "2020-06-01",
                "form": "NPORT-P",
                "primaryDocument": "xslFormNPORT-P_X01/primary_doc.xml",
                "reportDate": f"2020-03-{(index % 28) + 1:02d}",
            }
        )
    keys = list(rows[0])
    return {
        "cik": "1067839",
        "name": smoke.REGISTRANT_NAME,
        "filings": {"recent": {key: [row[key] for row in rows] for key in keys}},
    }


def _xml(position_count: int = 55) -> bytes:
    root = ET.Element("edgarSubmission")
    form_data = ET.SubElement(root, "formData")
    ET.SubElement(form_data, "repPdDate").text = "2019-12-31"
    investments = ET.SubElement(form_data, "invstOrSecs")
    for index in range(position_count):
        row = ET.SubElement(investments, "invstOrSec")
        ET.SubElement(row, "name").text = f"Company {index:02d}"
        ET.SubElement(row, "title").text = f"Common Stock {index:02d}"
        ET.SubElement(row, "cusip").text = f"{index:09d}"
        ET.SubElement(row, "balance").text = "1"
        ET.SubElement(row, "curCd").text = "USD"
        ET.SubElement(row, "valUSD").text = str(1000 - index)
        ET.SubElement(row, "payoffProfile").text = "Long"
        ET.SubElement(row, "assetCat").text = "EC"
    return ET.tostring(root)


def test_selects_exact_frozen_filings_and_counts_route_coverage() -> None:
    selected, count = smoke._select_filings(_submissions())

    assert [row["reportDate"] for row in selected] == list(smoke.SAMPLE_REPORT_DATES)
    assert count == smoke.MINIMUM_RECENT_FILINGS


@pytest.mark.parametrize("cik", ["1067839", "0001067839"])
def test_accepts_sec_cik_with_or_without_leading_zeroes(cik: str) -> None:
    submissions = _submissions()
    submissions["cik"] = cik

    selected, _ = smoke._select_filings(submissions)

    assert len(selected) == len(smoke.SAMPLE_REPORT_DATES)


def test_duplicate_frozen_report_date_fails_closed() -> None:
    submissions = _submissions()
    recent = submissions["filings"]["recent"]
    for key in recent:
        recent[key].append(recent[key][0])

    with pytest.raises(smoke.SmokeError, match="expected one"):
        smoke._select_filings(submissions)


def test_filing_url_uses_registrant_archive_and_document_basename() -> None:
    filing = _select_first()

    assert smoke._filing_url(filing) == (
        "https://www.sec.gov/Archives/edgar/data/1067839/"
        "000106783920000001/primary_doc.xml"
    )


def _select_first() -> dict[str, str]:
    return smoke._select_filings(_submissions())[0][0]


def test_xml_snapshot_qualifies_and_ranks_exactly_50() -> None:
    filing = _select_first()
    summary, top50 = smoke._parse_xml_snapshot(_xml(), filing)

    assert summary["qualified_equity_count"] == 55
    assert summary["duplicate_qualified_identity_count"] == 0
    assert summary["top50_count"] == 50
    assert len(top50) == 50
    assert top50[0]["value_usd"] > top50[-1]["value_usd"]
    assert datetime.fromisoformat(filing["acceptanceDateTime"].replace("Z", "+00:00"))


def test_fewer_than_50_equities_fails_closed() -> None:
    with pytest.raises(smoke.SmokeError, match="fewer than 50"):
        smoke._parse_xml_snapshot(_xml(49), _select_first())


def test_contract_keeps_outcomes_and_database_closed() -> None:
    contract = json.loads(
        (
            REPO_ROOT
            / "research/archive/us_qqq_disclosed_top50_equal_weight_v1/definitions/"
            "us_qqq_disclosed_top50_equal_weight_v1_smoke.json"
        ).read_text(encoding="utf-8")
    )

    assert contract["outcome_access"] is False
    assert contract["strategy_candidate_available"] is False
    assert contract["scope"]["central_database_write_allowed"] is False
    assert contract["scope"]["positions_per_snapshot"] == 50
    assert contract["source_contract"]["request_user_agent"].endswith("@qq.com")
