from __future__ import annotations

from datetime import UTC, datetime
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

import acquire_us_qqq_top50_prices_v1 as prices  # noqa: E402


def test_yahoo_parser_builds_adjusted_rows_without_strategy_returns() -> None:
    payload = {
        "chart": {
            "result": [
                {
                    "timestamp": [1577836800, 1577923200],
                    "indicators": {
                        "quote": [
                            {
                                "open": [10.0, 11.0],
                                "high": [11.0, 12.0],
                                "low": [9.0, 10.0],
                                "close": [10.0, 11.0],
                                "volume": [100, 110],
                            }
                        ],
                        "adjclose": [{"adjclose": [5.0, 5.5]}],
                    },
                    "events": {},
                }
            ]
        }
    }
    metadata = {
        "requested_url": "https://query2.finance.yahoo.com/example",
        "sha256": "a" * 64,
        "retrieved_at": "2026-07-23T00:00:00+00:00",
    }

    rows = prices._parse_yahoo(json.dumps(payload).encode(), "ABC", metadata)

    assert len(rows) == 2
    assert rows[0]["adj_open"] == 5.0
    assert rows[1]["gross_return_factor"] == 1.1
    assert rows[0]["snapshot_id"] == prices.PRICE_SNAPSHOT


def test_formation_close_is_first_close_strictly_after_acceptance() -> None:
    qqq_dates = [
        datetime(2026, 7, 22, tzinfo=UTC).date(),
        datetime(2026, 7, 23, tzinfo=UTC).date(),
    ]
    before_close = datetime(2026, 7, 22, 18, 0, tzinfo=UTC)
    after_close = datetime(2026, 7, 22, 21, 0, tzinfo=UTC)

    assert prices._formation_close(before_close, qqq_dates) == qqq_dates[0]
    assert prices._formation_close(after_close, qqq_dates) == qqq_dates[1]
