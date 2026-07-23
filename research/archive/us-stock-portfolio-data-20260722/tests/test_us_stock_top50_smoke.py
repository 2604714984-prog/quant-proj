from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import smoke_us_stock_data as stock_smoke  # noqa: E402
import smoke_us_top50_pit as top50_smoke  # noqa: E402


def test_sql_symbols_rejects_unsafe_or_empty_values() -> None:
    assert stock_smoke._sql_symbols(("AAPL", "2026-07-21")) == "'AAPL','2026-07-21'"
    with pytest.raises(stock_smoke.SmokeError):
        stock_smoke._sql_symbols(())
    with pytest.raises(stock_smoke.SmokeError):
        stock_smoke._sql_symbols(("AAPL'); DROP TABLE ohlcv; --",))


def test_yahoo_bar_summary_detects_duplicate_and_invalid_core_rows() -> None:
    result = {
        "timestamp": [1_704_067_200, 1_704_067_200, 1_704_153_600],
        "indicators": {
            "quote": [
                {
                    "open": [10, 10, 10],
                    "high": [11, 11, 9],
                    "low": [9, 9, 8],
                    "close": [10.5, 10.5, 10],
                    "volume": [100, 100, 100],
                }
            ]
        },
    }

    summary = stock_smoke._yahoo_bar_summary(result)

    assert summary["row_count"] == 3
    assert summary["duplicate_dates"] == 1
    assert summary["invalid_core"] == 1
    assert summary["valid_rows"] == 2


def test_sec_frame_summary_proves_entity_level_pit_gaps() -> None:
    payload = {
        "taxonomy": "dei",
        "tag": "EntityCommonStockSharesOutstanding",
        "uom": "shares",
        "data": [
            {
                "cik": 1,
                "entityName": "Example One",
                "end": "2024-12-31",
                "val": 100,
                "accn": "0000000001-25-000001",
                "form": "10-K",
                "filed": "2025-02-01",
            },
            {
                "cik": 2,
                "entityName": "Example Two",
                "end": "2024-12-31",
                "val": 200,
                "accn": "0000000002-25-000001",
                "form": "10-K",
                "filed": "2025-02-02",
            },
        ],
    }

    summary = top50_smoke._frame_summary(payload)

    assert summary["row_count"] == 2
    assert summary["positive_value_rows"] == 2
    assert summary["rows_with_acceptance_timestamp_field"] == 0
    assert summary["rows_with_share_class_identity_field"] == 0


def test_current_ticker_map_cannot_claim_historical_security_identity() -> None:
    payload = {
        "fields": ["cik", "name", "ticker", "exchange"],
        "data": [[1, "Example One", "ONE", "Nasdaq"]],
    }

    summary = top50_smoke._ticker_map_summary(payload)

    assert summary["duplicate_business_keys"] == 0
    assert summary["historical_effective_date_field_present"] is False
    assert summary["share_class_identifier_field_present"] is False


def test_frozen_v2_contract_has_dynamic_top50_identity_and_fail_closed_coverage() -> None:
    contract = json.loads(
        (REPO_ROOT / "research/definitions/us_stock_top50_data_contract_v2.json").read_text(
            encoding="utf-8"
        )
    )

    universe = contract["universe_identity"]
    assert universe["rank_count"] == 50
    assert universe["dynamic_history_required"] is True
    assert universe["current_constituent_backfill_forbidden"] is True
    assert universe["metric"]["selected"] == "TOTAL_MARKET_CAP"
    assert universe["metric"]["issuer_level_shares_substitution_forbidden"] is True
    assert universe["adr_policy"]["included"] is False
    assert contract["usable_coverage_at_freeze"]["qualified_start_date"] is None
    assert contract["strategy_candidate_available"] is False


def test_staged_smoke_results_never_claim_db_write_or_top50_output() -> None:
    result_paths = (
        Path(
            "/home/rongyu/workspace/quant-data/staging/"
            "us_stock_portfolio_20260722/smoke_v2/smoke_result.json"
        ),
        Path(
            "/home/rongyu/workspace/quant-data/staging/"
            "us_stock_portfolio_20260722/top50_pit_v1/smoke_result.json"
        ),
    )

    for result_path in result_paths:
        result = json.loads(result_path.read_text(encoding="utf-8"))
        assert result["status"] == "SMOKE_FAIL"
        assert result["strategy_candidate_available"] is False
        assert result["central_database_opened"] is False
        assert result["central_database_write"] is False
    top50_result = json.loads(result_paths[1].read_text(encoding="utf-8"))
    assert top50_result["top50_constituents_computed"] is False
    assert top50_result["top50_constituents_emitted"] is False
