from __future__ import annotations

from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import acquire_us_top50_profitability_v1 as research  # noqa: E402


def test_analyze_requires_public_timestamp_and_comparable_fields() -> None:
    income = []
    balance = []
    for quarter in range(1, 5):
        common = {
            "REPORT_DATE": f"2025-0{quarter}-30",
            "REPORT_TYPE": "Q",
            "NOTICE_DATE": f"2025-0{quarter + 1}-15",
            "CURRENCY": "USD",
        }
        income.extend(
            [
                {**common, "STD_ITEM_CODE": "REV", "ITEM_NAME": "营业收入"},
                {**common, "STD_ITEM_CODE": "COST", "ITEM_NAME": "营业成本"},
            ]
        )
        balance.append(
            {**common, "STD_ITEM_CODE": "ASSETS", "ITEM_NAME": "资产总计"}
        )
    result = research.analyze({"income": income, "balance": balance})
    assert all(result["gates"].values())
    assert result["timestamp_fields"] == ["NOTICE_DATE"]


def test_analyze_fails_without_public_timestamp() -> None:
    rows = {
        "income": [
            {
                "REPORT_DATE": "2025-03-31",
                "ITEM_NAME": "Gross Profit",
                "CURRENCY": "USD",
            }
        ],
        "balance": [
            {
                "REPORT_DATE": "2025-03-31",
                "ITEM_NAME": "Total Assets",
                "CURRENCY": "USD",
            }
        ],
    }
    result = research.analyze(rows)
    assert result["gates"]["public_timestamp"] is False
