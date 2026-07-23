from __future__ import annotations

import json
from pathlib import Path
import sys

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

import map_us_qqq_top50_cusips_v1 as mapping  # noqa: E402


def _mapped(ticker: str = "AAPL") -> dict:
    return {
        "data": [
            {
                "figi": "BBG000B9XRY4",
                "ticker": ticker,
                "name": "APPLE INC",
                "exchCode": "US",
                "marketSector": "Equity",
                "securityType": "Common Stock",
                "securityType2": "Common Stock",
                "compositeFIGI": "BBG000B9XRY4",
                "shareClassFIGI": "BBG001S5N8V8",
            },
            {
                "figi": "foreign",
                "ticker": "APC",
                "name": "APPLE INC",
                "exchCode": "GR",
                "marketSector": "Equity",
                "securityType2": "Common Stock",
            },
        ]
    }


def test_selects_exact_us_composite_equity() -> None:
    status, selected = mapping._select_mapping(_mapped())

    assert status == "MAPPED_UNIQUE_US_COMPOSITE"
    assert selected["ticker"] == "AAPL"
    assert selected["exchCode"] == "US"


def test_warning_is_no_match() -> None:
    status, selected = mapping._select_mapping(
        {"warning": "No identifier found."}
    )

    assert status == "NO_MATCH"
    assert selected is None


def test_distinct_us_composites_fail_closed() -> None:
    value = _mapped()
    value["data"].append(
        {
            **value["data"][0],
            "ticker": "OTHER",
            "compositeFIGI": "BBGOTHER",
        }
    )

    with pytest.raises(mapping.MappingError, match="ambiguous"):
        mapping._select_mapping(value)


def test_mapping_database_write_is_idempotent(tmp_path: Path) -> None:
    row = {
        "cusip": "037833100",
        "issuer_name": "Apple Inc.",
        "security_title": "Common Stock",
        "symbol": "AAPL",
        "figi": "BBG000B9XRY4",
        "composite_figi": "BBG000B9XRY4",
        "share_class_figi": "BBG001S5N8V8",
        "figi_name": "APPLE INC",
        "exchange_code": "US",
        "market_sector": "Equity",
        "security_type": "Common Stock",
        "security_type2": "Common Stock",
        "mapping_status": "MAPPED_UNIQUE_US_COMPOSITE",
        "batch_index": 1,
        "source_request_sha256": "a" * 64,
        "source_response_sha256": "b" * 64,
        "observed_at": "2026-07-23T00:00:00+00:00",
        "synthetic_data": False,
        "row_sha256": "c" * 64,
    }
    database = tmp_path / "test.duckdb"

    first = mapping._write_database(database, "snapshot", [row])
    second = mapping._write_database(database, "snapshot", [row])

    assert first["inserted"] is True
    assert second["inserted"] is False
    connection = duckdb.connect(str(database), read_only=True)
    try:
        assert connection.execute(
            "SELECT symbol FROM us_equity_research.qqq_security_mapping_research"
        ).fetchone()[0] == "AAPL"
    finally:
        connection.close()


def test_contract_keeps_price_and_outcome_closed() -> None:
    contract = json.loads(
        (
            REPO_ROOT
            / "research/archive/us_qqq_disclosed_top50_equal_weight_v1/definitions/"
            "us_qqq_disclosed_top50_equal_weight_v1_mapping.json"
        ).read_text(encoding="utf-8")
    )

    assert contract["outcome_access"] is False
    assert contract["mapping"]["minimum_mapping_coverage"] == 0.98
    assert contract["central_table"]["destructive_migration_allowed"] is False
