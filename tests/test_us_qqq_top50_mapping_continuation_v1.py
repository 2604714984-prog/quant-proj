from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(
    0,
    str(
        REPO_ROOT
        / "research/archive/us_qqq_disclosed_top50_equal_weight_v1/scripts"
    ),
)

import continue_us_qqq_top50_mapping_v1 as continuation  # noqa: E402


def test_name_normalization_removes_only_frozen_legal_tokens() -> None:
    assert continuation._normalize_name("Lam Research Corp.") == "LAM RESEARCH"
    assert continuation._normalize_name("Atlassian Corp. PLC") == "ATLASSIAN"


def test_unique_openfigi_us_venue_is_accepted() -> None:
    result = {
        "data": [
            {
                "ticker": "CELG",
                "compositeFIGI": "BBG1",
                "shareClassFIGI": "BBG2",
                "securityType2": "Common Stock",
                "marketSector": "Equity",
                "exchCode": "UW",
            },
            {
                "ticker": "CELG",
                "compositeFIGI": "FOREIGN",
                "shareClassFIGI": "FOREIGN",
                "securityType2": "Common Stock",
                "marketSector": "Equity",
                "exchCode": "SW",
            },
        ]
    }

    status, selected = continuation._unique_us_venue(result)

    assert status == "MAPPED_UNIQUE_OPENFIGI_US_VENUE"
    assert selected["ticker"] == "CELG"


def test_yahoo_selection_uses_names_not_market_fields() -> None:
    payload = {
        "quotes": [
            {
                "symbol": "LRCX",
                "longname": "Lam Research Corporation",
                "quoteType": "EQUITY",
                "exchange": "NMS",
                "regularMarketPrice": 999.0,
            },
            {
                "symbol": "OTHER",
                "longname": "Unrelated Company",
                "quoteType": "EQUITY",
                "exchange": "NMS",
                "regularMarketPrice": 1.0,
            },
        ]
    }

    status, selected, score, margin = continuation._select_yahoo(
        payload, "Lam Research Corp."
    )

    assert status == "MAPPED_YAHOO_UNIQUE_NAME"
    assert selected["ticker"] == "LRCX"
    assert score == 1.0
    assert margin >= 0.15
    assert "regularMarketPrice" not in selected


def test_yahoo_ambiguous_name_fails_closed() -> None:
    payload = {
        "quotes": [
            {
                "symbol": "ABC",
                "longname": "Example Holdings",
                "quoteType": "EQUITY",
                "exchange": "NMS",
            },
            {
                "symbol": "ABD",
                "longname": "Example Holding",
                "quoteType": "EQUITY",
                "exchange": "NMS",
            },
        ]
    }

    status, selected, _, _ = continuation._select_yahoo(
        payload, "Example Holdings"
    )

    assert status == "AMBIGUOUS_YAHOO_MATCH"
    assert selected is None
