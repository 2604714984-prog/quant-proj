from __future__ import annotations

import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import duckdb
import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(
    0,
    str(
        REPO_ROOT
        / "research/archive/us_qqq_disclosed_top50_equal_weight_v1/scripts"
    ),
)

import materialize_us_qqq_disclosed_top50_v1 as materialize  # noqa: E402


def _filing() -> dict[str, str]:
    return {
        "accessionNumber": "0001067839-20-000001",
        "acceptanceDateTime": "2020-02-28T21:45:44.000Z",
        "filingDate": "2020-02-28",
        "form": "NPORT-P",
        "primaryDocument": "xslFormNPORT-P_X01/primary_doc.xml",
        "reportDate": "2019-12-31",
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
        identifiers = ET.SubElement(row, "identifiers")
        ET.SubElement(identifiers, "isin", value=f"US{index:09d}0")
        ET.SubElement(row, "balance").text = "10"
        ET.SubElement(row, "units").text = "NS"
        ET.SubElement(row, "curCd").text = "USD"
        ET.SubElement(row, "valUSD").text = str(1000 - index)
        ET.SubElement(row, "pctVal").text = "0.1"
        ET.SubElement(row, "payoffProfile").text = "Long"
        ET.SubElement(row, "assetCat").text = "EC"
    return ET.tostring(root)


def test_parse_snapshot_ranks_exactly_50_and_preserves_pit_time() -> None:
    summary, rows = materialize._parse_snapshot(
        _xml(),
        _filing(),
        "https://www.sec.gov/example.xml",
        "a" * 64,
        "2026-07-23T00:00:00+00:00",
    )

    assert summary["qualified_equity_count"] == 55
    assert summary["top50_count"] == 50
    assert sum(row["is_top50"] for row in rows) == 50
    assert rows[0]["security_rank"] == 1
    assert rows[-1]["security_rank"] == 55
    assert rows[0]["available_at"] == _filing()["acceptanceDateTime"]
    assert rows[0]["isin"].startswith("US")
    assert len(rows[0]["row_sha256"]) == 64


def test_parse_snapshot_fails_below_frozen_minimum() -> None:
    with pytest.raises(materialize.MaterializationError, match="fewer than 50"):
        materialize._parse_snapshot(
            _xml(49),
            _filing(),
            "https://www.sec.gov/example.xml",
            "a" * 64,
            "2026-07-23T00:00:00+00:00",
        )


def test_atomic_central_write_is_idempotent(tmp_path: Path) -> None:
    _, rows = materialize._parse_snapshot(
        _xml(),
        _filing(),
        "https://www.sec.gov/example.xml",
        "a" * 64,
        "2026-07-23T00:00:00+00:00",
    )
    database = tmp_path / "test.duckdb"

    first = materialize._write_central_database(database, "snapshot", rows)
    second = materialize._write_central_database(database, "snapshot", rows)

    assert first["inserted"] is True
    assert second["inserted"] is False
    assert first["row_count"] == second["row_count"] == 55
    connection = duckdb.connect(str(database), read_only=True)
    try:
        assert connection.execute(
            "SELECT COUNT(*) FROM us_equity_research.qqq_holdings_pit_research "
            "WHERE is_top50"
        ).fetchone()[0] == 50
    finally:
        connection.close()


def test_contract_keeps_strategy_outcomes_closed() -> None:
    contract = json.loads(
        (
            REPO_ROOT
            / "research/archive/us_qqq_disclosed_top50_equal_weight_v1/definitions/"
            "us_qqq_disclosed_top50_equal_weight_v1_materialization.json"
        ).read_text(encoding="utf-8")
    )

    assert contract["outcome_access"] is False
    assert contract["strategy_candidate_available"] is False
    assert contract["universe"]["minimum_snapshot_count"] == 24
    assert contract["central_table"]["destructive_migration_allowed"] is False
