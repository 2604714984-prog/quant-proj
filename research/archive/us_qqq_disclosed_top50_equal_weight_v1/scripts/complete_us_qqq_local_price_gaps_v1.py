"""Complete ATVI/WBA prices from fixed local Sina caches; leave CELG unavailable."""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

import duckdb

import acquire_us_qqq_top50_prices_v1 as prices
import continue_us_qqq_top50_mapping_v1 as mapping
import smoke_us_qqq_disclosed_top50_v1 as smoke


RESEARCH_ID = smoke.RESEARCH_ID
EXECUTION_ID = f"{RESEARCH_ID}_LOCAL_PRICE_GAP_COMPLETION"
SNAPSHOT = "US_QQQ_DISCLOSED_TOP50_EQUAL_WEIGHT_V1_YAHOO_SINA_CACHE_20260723"
STOOQ_PL_FAILURE_SHA = (
    "8f2ed27e431cea6d60986bb35fdecbd546dfd500135edb056f3a86e33f491da3"
)
LOCAL_FILES = {
    "ATVI": (
        Path(
            "/home/rongyu/workspace/quant-data/recovery/legacy-local/us_stock_30w/"
            "data/cache/sp500_removed_membership_v1/ATVI.csv"
        ),
        "5b2038ec2ad619864afce8343daa9e18a755c24b7c8d5175805f825be82bb500",
    ),
    "WBA": (
        Path(
            "/home/rongyu/workspace/quant-data/recovery/legacy-local/us_stock_30w/"
            "data/cache/sp500_removed_membership_v1/WBA.csv"
        ),
        "a8880450cec04464d2ae8f54f4b0a2c52bc65f244826e7566ab27e0abd859a1f",
    ),
}


class LocalGapError(RuntimeError):
    """A fixed local cache identity or coverage gate failed."""


def _parse_local(
    path: Path, symbol: str, source_sha256: str
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    observed = datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat()
    for source in csv.DictReader(path.open()):
        try:
            day = datetime.strptime(source["date"], "%Y-%m-%d").date()
            open_price = float(source["open"])
            high = float(source["high"])
            low = float(source["low"])
            close = float(source["close"])
            volume = int(float(source["volume"]))
        except (KeyError, TypeError, ValueError):
            continue
        if day.year < 2019 or close <= 0:
            continue
        row = {
            "snapshot_id": SNAPSHOT,
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
            "source_url": f"local-sina-cache:{path.name}",
            "source_document_sha256": source_sha256,
            "observed_at": observed,
            "available_at": observed,
            "availability_basis": "RETROSPECTIVE_LOCAL_SINA_CACHE_NOT_PIT",
            "price_adjustment_status": "SINA_CLOSE_NO_DIVIDEND_ADJUSTMENT",
            "quality_status": "RESEARCH_SECONDARY_SINA_CACHE_NO_DIVIDEND_ADJUSTMENT",
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
        raise LocalGapError(f"no usable local cache rows: {symbol}")
    return rows


def run(
    repo_root: Path,
    staging_root: Path,
    database_path: Path,
    result_path: Path,
) -> dict[str, Any]:
    stooq_result = (
        repo_root
        / "research/results/"
        "us_qqq_disclosed_top50_equal_weight_v1_stooq_pl_transport_20260723.json"
    )
    failure: str | None = None
    rows_by_symbol: dict[str, list[dict[str, Any]]] = {}
    coverage: dict[str, Any] = {}
    central: dict[str, Any] = {"attempted": False, "transaction_committed": False}
    normalized_path = staging_root / "normalized/daily_rows.jsonl"
    try:
        if mapping._sha256_file(stooq_result) != STOOQ_PL_FAILURE_SHA:
            raise LocalGapError("preserved Stooq Poland failure changed")
        symbols, holdings = prices._required_inputs(database_path)
        prices.PRICE_SNAPSHOT = SNAPSHOT
        yahoo_root = staging_root.parent / "prices/raw/yahoo"
        for symbol in [*symbols, "QQQ"]:
            path = yahoo_root / f"{symbol}.json"
            metadata = json.loads(
                path.with_suffix(path.suffix + ".metadata.json").read_text()
            )
            if metadata.get("success"):
                rows_by_symbol[symbol] = prices._parse_yahoo(
                    path.read_bytes(), symbol, metadata
                )
        for symbol, (path, expected_sha) in LOCAL_FILES.items():
            if mapping._sha256_file(path) != expected_sha:
                raise LocalGapError(f"local source hash mismatch: {symbol}")
            rows_by_symbol[symbol] = _parse_local(path, symbol, expected_sha)
        coverage = prices._entry_coverage(holdings, rows_by_symbol)
        if (
            coverage["coverage"] < prices.MINIMUM_ENTRY_COVERAGE
            or coverage["minimum_priced_positions"] < prices.MINIMUM_POSITIONS
        ):
            raise LocalGapError(
                f"local completion coverage failed: {coverage['coverage']:.6f}, "
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
        LocalGapError,
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
        "us_qqq_disclosed_top50_equal_weight_v1_local_gap_completion.json"
    )
    result = {
        "research_id": RESEARCH_ID,
        "execution_id": EXECUTION_ID,
        "date": datetime.now(UTC).date().isoformat(),
        "market": "US",
        "phase": "LOCAL_PRICE_GAP_COMPLETION",
        "current_status": "current" if qualified else "blocked-on-data",
        "result": (
            "PRICE_INPUTS_QUALIFIED_PREREGISTRATION_AUTHORIZED"
            if qualified
            else "INPUT_BLOCKED"
        ),
        "failure": failure,
        "contract": {
            "path": str(contract),
            "sha256": mapping._sha256_file(contract),
        },
        "counts": {
            "combined_symbol_count_including_qqq": len(rows_by_symbol),
            "combined_price_row_count": central.get("row_count", 0),
        },
        "entry_coverage": coverage,
        "central_database": central,
        "normalized_artifact": {
            "path": str(normalized_path),
            "sha256": mapping._sha256_file(normalized_path)
            if normalized_path.is_file()
            else None,
        },
        "quality_gates": {
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
            "ATVI and WBA local Sina cache rows have no inferred dividend adjustment.",
            "CELG is unavailable at the first post-disclosure formation and excluded.",
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
            "us_qqq_disclosed_top50_equal_weight_v1/local_gap_completion"
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
            "us_qqq_disclosed_top50_equal_weight_v1_local_gap_completion_20260723.json"
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
