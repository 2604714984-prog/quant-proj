from __future__ import annotations

import json
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

import continue_us_qqq_top50_prices_v1 as continuation  # noqa: E402


def test_stooq_parser_marks_missing_dividend_adjustment() -> None:
    raw = (
        b"Date,Open,High,Low,Close,Volume\n"
        b"2019-01-02,10,11,9,10.5,100\n"
        b"2019-01-03,10.5,12,10,11,110\n"
    )
    metadata = {
        "requested_url": "https://stooq.com/example",
        "sha256": "a" * 64,
        "retrieved_at": "2026-07-23T00:00:00+00:00",
    }

    rows = continuation._parse_stooq(raw, "ABC", metadata)

    assert len(rows) == 2
    assert rows[0]["adj_close"] == rows[0]["close"]
    assert "NO_DIVIDEND_ADJUSTMENT" in rows[0]["quality_status"]
    assert json.loads(rows[0]["conflict_flags_json"])[
        "missing_dividend_adjustment"
    ] is True
