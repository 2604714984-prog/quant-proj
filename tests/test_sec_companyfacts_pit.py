import gzip
from pathlib import Path

import duckdb
from quant_system.data.sec_companyfacts_pit import (
    _decode,
    _rows_bytes,
    TABLE_COLUMNS,
    ensure_table,
    extract_rows,
    qualification,
    ticker_map,
)


def test_decode_gzip():
    raw = b'{"ok":true}'
    assert _decode(gzip.compress(raw), "gzip") == raw
    assert _decode(raw, "") == raw


def test_ticker_map_includes_historical_symbols():
    result = ticker_map({"0": {"ticker": "BRK.B", "title": "Berkshire", "cik_str": 1}})
    assert result["BRK-B"] == (1, "Berkshire")
    assert result["ATVI"][0] == 718877
    assert result["CELG"][0] == 816284
    assert result["WBA"][0] == 1618921


def test_extract_rows_uses_filed_date_and_filters_forms():
    document = {
        "entityName": "Example Inc.",
        "facts": {
            "us-gaap": {
                "NetIncomeLoss": {
                    "units": {
                        "USD": [
                            {
                                "start": "2023-01-01",
                                "end": "2023-12-31",
                                "filed": "2024-02-15",
                                "form": "10-K",
                                "fy": 2023,
                                "fp": "FY",
                                "accn": "0001",
                                "val": 10,
                            },
                            {
                                "start": "2023-01-01",
                                "end": "2023-12-31",
                                "filed": "2024-02-15",
                                "form": "10-Q",
                                "accn": "ignored",
                                "val": 10,
                            },
                        ]
                    }
                },
                "Assets": {
                    "units": {
                        "USD": [
                            {
                                "end": "2023-12-31",
                                "filed": "2024-02-15",
                                "form": "10-K",
                                "fy": 2023,
                                "fp": "FY",
                                "accn": "0001",
                                "val": 100,
                            }
                        ]
                    }
                },
            }
        },
    }
    from datetime import datetime, timezone

    rows = extract_rows(
        symbol="EX",
        cik=1,
        document=document,
        source_url="https://example.invalid",
        source_sha256="a" * 64,
        retrieved_at=datetime(2026, 7, 24, tzinfo=timezone.utc),
    )
    assert len(rows) == 2
    assert {row["concept"] for row in rows} == {"NetIncomeLoss", "Assets"}
    assert {str(row["available_at"]) for row in rows} == {"2024-02-15"}
    assert all(row["row_sha256"] for row in rows)
    rows[0]["snapshot_id"] = "snapshot"
    rows[1]["snapshot_id"] = "snapshot"
    assert _rows_bytes(rows).startswith(b'[{"snapshot_id":"snapshot","row_sha256":')
    assert tuple(rows[0]) == tuple(name for name, _sql_type in TABLE_COLUMNS)


def test_qualification_requires_common_unit_for_income_and_assets():
    rows = [
        {"symbol": "A", "taxonomy": "us-gaap", "concept": "NetIncomeLoss", "unit": "USD"},
        {"symbol": "A", "taxonomy": "us-gaap", "concept": "Assets", "unit": "USD"},
        {"symbol": "B", "taxonomy": "ifrs-full", "concept": "ProfitLoss", "unit": "EUR"},
        {"symbol": "B", "taxonomy": "ifrs-full", "concept": "Assets", "unit": "USD"},
    ]
    result, qualified = qualification(rows, ["A", "B"])
    assert qualified == {"A"}
    assert result["qualified_fraction"] == 0.5
    assert not result["passed"]


def test_ensure_table_is_idempotent(tmp_path: Path):
    database = tmp_path / "test.duckdb"
    duckdb.connect(str(database)).close()
    ensure_table(database)
    ensure_table(database)
    with duckdb.connect(str(database), read_only=True) as connection:
        assert connection.execute(
            "SELECT count(*) FROM information_schema.columns "
            "WHERE table_schema='us_equity_research' "
            "AND table_name='us_sec_companyfacts_pit_research'"
        ).fetchone() == (22,)
