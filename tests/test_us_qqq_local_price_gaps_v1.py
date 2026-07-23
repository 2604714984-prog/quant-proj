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

import complete_us_qqq_local_price_gaps_v1 as gaps  # noqa: E402


def test_local_parser_is_conservatively_unadjusted(tmp_path: Path) -> None:
    path = tmp_path / "ABC.csv"
    path.write_text(
        "date,open,high,low,close,volume\n"
        "2020-01-02,10,11,9,10.5,100\n"
        "2020-01-03,10.5,12,10,11,110\n"
    )

    rows = gaps._parse_local(path, "ABC", "a" * 64)

    assert len(rows) == 2
    assert rows[0]["adj_close"] == rows[0]["close"]
    assert "NO_DIVIDEND_ADJUSTMENT" in rows[0]["quality_status"]
