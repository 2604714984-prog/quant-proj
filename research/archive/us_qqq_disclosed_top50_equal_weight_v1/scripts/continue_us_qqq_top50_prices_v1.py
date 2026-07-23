"""Fill exactly three frozen Yahoo price gaps from Stooq, outcome-free."""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
import hashlib
import io
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import duckdb

import acquire_us_qqq_top50_prices_v1 as prices
import continue_us_qqq_top50_mapping_v1 as continuation
import smoke_us_qqq_disclosed_top50_v1 as smoke


RESEARCH_ID = smoke.RESEARCH_ID
EXECUTION_ID = f"{RESEARCH_ID}_PRICE_CONTINUATION"
FAILED_RESULT_SHA256 = (
    "5f3c7e2a593bd57f201426b221c3a998f37acd398e2b9381d331a75bce4a61a1"
)
GAPS = ("ATVI", "CELG", "WBA")
COMBINED_SNAPSHOT = "US_QQQ_DISCLOSED_TOP50_EQUAL_WEIGHT_V1_YAHOO_STOOQ_20260723"


class PriceContinuationError(RuntimeError):
    """The frozen three-symbol continuation failed."""


def _parse_stooq(
    raw: bytes, symbol: str, metadata: dict[str, Any]
) -> list[dict[str, Any]]:
    text = raw.decode("utf-8-sig", errors="strict")
    reader = csv.DictReader(io.StringIO(text))
    required = {"Date", "Open", "High", "Low", "Close", "Volume"}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise PriceContinuationError(f"invalid Stooq schema: {symbol}")
    rows: list[dict[str, Any]] = []
    for source in reader:
        try:
            day = datetime.strptime(source["Date"], "%Y-%m-%d").date()
            open_price = float(source["Open"])
            high = float(source["High"])
            low = float(source["Low"])
            close = float(source["Close"])
            volume = int(float(source["Volume"]))
        except (TypeError, ValueError):
            continue
        if close <= 0 or day.year < 2019:
            continue
        row = {
            "snapshot_id": COMBINED_SNAPSHOT,
            "symbol": symbol,
            "trade_date": day.isoformat(),
            "source_timestamp": datetime.combine(
                day, datetime.min.time(), UTC
            ).isoformat(),
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "adj_open": open_price,
            "adj_high": high,
            "adj_low": low,
            "adj_close": close,
            "adj_volume": volume,
            "div_cash": 0.0,
            "split_factor": 1.0,
            "gross_return_factor": 1.0,
            "adjusted_reference_factor": 1.0,
            "adjusted_reference_relative_error": 0.0,
            "source_url": metadata["requested_url"],
            "source_document_sha256": metadata["sha256"],
            "observed_at": metadata["retrieved_at"],
            "available_at": metadata["retrieved_at"],
            "availability_basis": "RETROSPECTIVE_STOOQ_NOT_PIT",
            "price_adjustment_status": "STOOQ_CLOSE_NO_DIVIDEND_ADJUSTMENT",
            "quality_status": (
                "RESEARCH_SECONDARY_STOOQ_CLOSE_NO_DIVIDEND_ADJUSTMENT"
            ),
            "conflict_flags_json": json.dumps(
                {"missing_dividend_adjustment": True}, sort_keys=True
            ),
            "synthetic_data": False,
        }
        rows.append(row)
    rows.sort(key=lambda row: row["trade_date"])
    for index, row in enumerate(rows):
        if index:
            row["gross_return_factor"] = (
                row["adj_close"] / rows[index - 1]["adj_close"]
            )
        row["row_sha256"] = prices._hash_value(row)
    if not rows:
        raise PriceContinuationError(f"no valid Stooq rows: {symbol}")
    return rows


def run(
    repo_root: Path,
    staging_root: Path,
    database_path: Path,
    result_path: Path,
) -> dict[str, Any]:
    failed_result = (
        repo_root
        / "research/results/us_qqq_disclosed_top50_equal_weight_v1_prices_20260723.json"
    )
    failure: str | None = None
    rows_by_symbol: dict[str, list[dict[str, Any]]] = {}
    stooq: list[dict[str, Any]] = []
    coverage: dict[str, Any] = {}
    central: dict[str, Any] = {"attempted": False, "transaction_committed": False}
    normalized_path = staging_root / "normalized" / "daily_rows.jsonl"
    try:
        if continuation._sha256_file(failed_result) != FAILED_RESULT_SHA256:
            raise PriceContinuationError("preserved failed price result changed")
        symbols, holdings = prices._required_inputs(database_path)
        prices.PRICE_SNAPSHOT = COMBINED_SNAPSHOT
        yahoo_root = staging_root.parent / "prices/raw/yahoo"
        for symbol in [*symbols, "QQQ"]:
            path = yahoo_root / f"{symbol}.json"
            metadata_path = path.with_suffix(path.suffix + ".metadata.json")
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if metadata.get("success"):
                rows_by_symbol[symbol] = prices._parse_yahoo(
                    path.read_bytes(), symbol, metadata
                )
        for symbol in GAPS:
            params = {
                "s": f"{symbol.lower()}.us",
                "i": "d",
                "d1": "20190101",
                "d2": "20260723",
            }
            url = f"{prices.STOOQ_BASE}?{urlencode(params)}"
            path = staging_root / "raw/stooq_gaps" / f"{symbol}.csv"
            metadata = prices._download(url, path, maximum_bytes=10 * 1024 * 1024)
            stooq.append(
                {
                    "symbol_hash": hashlib.sha256(symbol.encode()).hexdigest(),
                    "success": metadata.get("success", False),
                    "sha256": metadata.get("sha256"),
                    "byte_count": metadata.get("byte_count"),
                }
            )
            if metadata.get("success"):
                rows_by_symbol[symbol] = _parse_stooq(
                    path.read_bytes(), symbol, metadata
                )
        coverage = prices._entry_coverage(holdings, rows_by_symbol)
        if (
            coverage["coverage"] < prices.MINIMUM_ENTRY_COVERAGE
            or coverage["minimum_priced_positions"] < prices.MINIMUM_POSITIONS
        ):
            raise PriceContinuationError(
                f"combined entry coverage failed: {coverage['coverage']:.6f}, "
                f"minimum {coverage['minimum_priced_positions']}"
            )
        all_rows = [
            row
            for symbol in sorted(rows_by_symbol)
            for row in rows_by_symbol[symbol]
        ]
        prices._write_jsonl(normalized_path, all_rows)
        central["attempted"] = True
        central = prices._write_database(database_path, all_rows)
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        PriceContinuationError,
        prices.PriceInputError,
        duckdb.Error,
    ) as exc:
        failure = f"{type(exc).__name__}: {exc}"
    qualified = (
        failure is None
        and coverage.get("coverage", 0) >= prices.MINIMUM_ENTRY_COVERAGE
        and coverage.get("minimum_priced_positions", 0) >= prices.MINIMUM_POSITIONS
        and central.get("transaction_committed") is True
    )
    contract = (
        repo_root
        / "research/definitions/"
        "us_qqq_disclosed_top50_equal_weight_v1_price_continuation.json"
    )
    result = {
        "research_id": RESEARCH_ID,
        "execution_id": EXECUTION_ID,
        "date": datetime.now(UTC).date().isoformat(),
        "market": "US",
        "phase": "PRICE_INPUT_CONTINUATION",
        "current_status": "current" if qualified else "blocked-on-data",
        "result": (
            "PRICE_INPUTS_QUALIFIED_PREREGISTRATION_AUTHORIZED"
            if qualified
            else "INPUT_BLOCKED"
        ),
        "failure": failure,
        "contract": {
            "path": str(contract),
            "sha256": continuation._sha256_file(contract),
        },
        "preserved_failed_route": {
            "path": str(failed_result),
            "sha256": continuation._sha256_file(failed_result),
        },
        "stooq_gap_receipts_without_symbols": stooq,
        "counts": {
            "combined_symbol_count_including_qqq": len(rows_by_symbol),
            "combined_price_row_count": central.get("row_count", 0),
        },
        "entry_coverage": coverage,
        "normalized_artifact": {
            "path": str(normalized_path),
            "sha256": continuation._sha256_file(normalized_path)
            if normalized_path.is_file()
            else None,
        },
        "central_database": central,
        "quality_gates": {
            "failed_route_preserved": continuation._sha256_file(failed_result)
            == FAILED_RESULT_SHA256,
            "entry_coverage_at_least_98_percent": coverage.get("coverage", 0)
            >= prices.MINIMUM_ENTRY_COVERAGE,
            "at_least_49_positions_each": coverage.get(
                "minimum_priced_positions", 0
            )
            >= prices.MINIMUM_POSITIONS,
            "central_write_committed": central.get("transaction_committed") is True,
            "strategy_returns_accessed": False,
        },
        "limitations": [
            "Stooq gap rows use close without inferred dividend adjustment.",
            "A security unavailable at formation is excluded from that formation.",
        ],
        "research_boundaries": {
            "strategy_candidate_available": False,
            "portfolio_constructed": False,
            "broker_order_paper_live_auto_enabled": False,
        },
        "next_action": (
            "Freeze and execute the one-use equal-weight-vs-QQQ validation."
            if qualified
            else "Stop this research identity."
        ),
    }
    smoke._write_json_atomic(result_path, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--staging-root",
        type=Path,
        default=Path(
            "/home/rongyu/workspace/quant-data/staging/"
            "us_qqq_disclosed_top50_equal_weight_v1/price_continuation"
        ),
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("/home/rongyu/workspace/quant-data/quant_research.duckdb"),
    )
    parser.add_argument(
        "--result",
        type=Path,
        default=Path(
            "research/results/"
            "us_qqq_disclosed_top50_equal_weight_v1_price_continuation_20260723.json"
        ),
    )
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    result_path = (
        (repo_root / args.result).resolve()
        if not args.result.is_absolute()
        else args.result.resolve()
    )
    result = run(
        repo_root,
        args.staging_root.resolve(),
        args.database.resolve(),
        result_path,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["result"].startswith("PRICE_INPUTS_QUALIFIED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
