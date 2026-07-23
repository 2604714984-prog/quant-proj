"""Acquire and materialize uniform Yahoo prices before strategy outcome access."""

from __future__ import annotations

import argparse
from datetime import UTC, date, datetime, time as daytime
import hashlib
import json
from pathlib import Path
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import duckdb

import continue_us_qqq_top50_mapping_v1 as continuation
import smoke_us_qqq_disclosed_top50_v1 as smoke


RESEARCH_ID = smoke.RESEARCH_ID
EXECUTION_ID = f"{RESEARCH_ID}_PRICE_INPUTS"
HOLDINGS_SNAPSHOT = "qqq_nport_pit_20260723_a10cf2fcdafa4dd8"
MAPPING_SNAPSHOT = "qqq_identity_complete_20260723_767fbc6dbfa92cb9"
PRICE_SNAPSHOT = "US_QQQ_DISCLOSED_TOP50_EQUAL_WEIGHT_V1_YAHOO_20260723"
PERIOD1 = 1546300800
PERIOD2 = 1784851200
EXPECTED_SYMBOLS = 92
MINIMUM_ENTRY_COVERAGE = 0.98
MINIMUM_POSITIONS = 49
YAHOO_BASE = "https://query2.finance.yahoo.com/v8/finance/chart"
STOOQ_BASE = "https://stooq.com/q/d/l/"


class PriceInputError(RuntimeError):
    """A frozen price input gate failed."""


def _hash_value(value: Any) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    return hashlib.sha256(raw).hexdigest()


def _required_inputs(
    database_path: Path,
) -> tuple[list[str], list[dict[str, Any]]]:
    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        symbols = [
            row[0]
            for row in connection.execute(
                """
                SELECT DISTINCT m.symbol
                FROM us_equity_research.qqq_holdings_pit_research h
                JOIN us_equity_research.qqq_security_mapping_research m USING(cusip)
                WHERE h.snapshot_id=? AND h.is_top50 AND m.snapshot_id=?
                ORDER BY m.symbol
                """,
                [HOLDINGS_SNAPSHOT, MAPPING_SNAPSHOT],
            ).fetchall()
        ]
        holdings = [
            {
                "report_date": row[0],
                "accepted_at": row[1],
                "cusip": row[2],
                "symbol": row[3],
                "security_rank": row[4],
            }
            for row in connection.execute(
                """
                SELECT h.report_date,h.accepted_at,h.cusip,m.symbol,h.security_rank
                FROM us_equity_research.qqq_holdings_pit_research h
                JOIN us_equity_research.qqq_security_mapping_research m USING(cusip)
                WHERE h.snapshot_id=? AND h.is_top50 AND m.snapshot_id=?
                ORDER BY h.report_date,h.security_rank
                """,
                [HOLDINGS_SNAPSHOT, MAPPING_SNAPSHOT],
            ).fetchall()
        ]
    finally:
        connection.close()
    if len(symbols) != EXPECTED_SYMBOLS or len(holdings) != 1350:
        raise PriceInputError(
            f"unexpected mapped input shape: {len(symbols)} symbols, "
            f"{len(holdings)} positions"
        )
    return symbols, holdings


def _download(
    url: str, destination: Path, maximum_bytes: int = 20 * 1024 * 1024
) -> dict[str, Any]:
    metadata_path = destination.with_suffix(destination.suffix + ".metadata.json")
    if destination.is_file() and metadata_path.is_file():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if (
            metadata.get("requested_url") != url
            or metadata.get("sha256") != continuation._sha256_file(destination)
        ):
            raise PriceInputError(f"cached price source mismatch: {destination}")
        return {**metadata, "cache_reused": True}
    if destination.exists() or metadata_path.exists():
        raise PriceInputError(f"incomplete price cache: {destination}")
    request = Request(
        url,
        headers={
            "User-Agent": smoke.USER_AGENT,
            "Accept": "application/json,text/csv;q=0.9",
            "Accept-Encoding": "identity",
        },
    )
    time.sleep(0.6)
    try:
        with urlopen(request, timeout=45) as response:  # noqa: S310
            status = int(response.status)
            raw = response.read(maximum_bytes + 1)
            final_url = response.geturl()
    except (HTTPError, URLError) as exc:
        metadata = {
            "requested_url": url,
            "retrieved_at": datetime.now(UTC).isoformat(),
            "success": False,
            "failure": f"{type(exc).__name__}: {exc}",
            "automatic_retry_count": 0,
        }
        smoke._write_json_atomic(metadata_path, metadata)
        return metadata
    if status != 200 or len(raw) > maximum_bytes:
        raise PriceInputError(f"price source response failure: {url}")
    metadata = {
        "requested_url": url,
        "final_url": final_url,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "http_status": status,
        "success": True,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "byte_count": len(raw),
        "automatic_retry_count": 0,
    }
    smoke._write_atomic(destination, raw)
    smoke._write_json_atomic(metadata_path, metadata)
    return {**metadata, "cache_reused": False}


def _yahoo_url(symbol: str) -> str:
    params = {
        "period1": PERIOD1,
        "period2": PERIOD2,
        "interval": "1d",
        "events": "div,splits",
        "includeAdjustedClose": "true",
    }
    return f"{YAHOO_BASE}/{quote(symbol, safe='')}?{urlencode(params)}"


def _parse_yahoo(
    raw: bytes, symbol: str, metadata: dict[str, Any]
) -> list[dict[str, Any]]:
    payload = json.loads(raw)
    results = payload.get("chart", {}).get("result") or []
    if len(results) != 1:
        raise PriceInputError(f"Yahoo chart result missing: {symbol}")
    result = results[0]
    timestamps = result.get("timestamp") or []
    quote_block = (result.get("indicators", {}).get("quote") or [{}])[0]
    adjusted = (
        (result.get("indicators", {}).get("adjclose") or [{}])[0].get("adjclose")
        or []
    )
    events = result.get("events") or {}
    dividends = {
        int(key): float(value["amount"])
        for key, value in (events.get("dividends") or {}).items()
    }
    splits = {
        int(key): float(value.get("numerator", 1)) / float(value.get("denominator", 1))
        for key, value in (events.get("splits") or {}).items()
        if float(value.get("denominator", 1)) != 0
    }
    rows: list[dict[str, Any]] = []
    for index, timestamp in enumerate(timestamps):
        try:
            close = quote_block["close"][index]
            volume = quote_block["volume"][index]
            adj_close = adjusted[index]
        except (IndexError, KeyError):
            continue
        if close is None or volume is None or adj_close is None or close <= 0:
            continue
        values = {
            key: quote_block.get(key, [None] * len(timestamps))[index]
            for key in ("open", "high", "low")
        }
        if any(value is None for value in values.values()):
            continue
        factor = float(adj_close) / float(close)
        trade_date = datetime.fromtimestamp(int(timestamp), UTC).date()
        row = {
            "snapshot_id": PRICE_SNAPSHOT,
            "symbol": symbol,
            "trade_date": trade_date.isoformat(),
            "source_timestamp": datetime.fromtimestamp(
                int(timestamp), UTC
            ).isoformat(),
            "open": float(values["open"]),
            "high": float(values["high"]),
            "low": float(values["low"]),
            "close": float(close),
            "volume": int(volume),
            "adj_open": float(values["open"]) * factor,
            "adj_high": float(values["high"]) * factor,
            "adj_low": float(values["low"]) * factor,
            "adj_close": float(adj_close),
            "adj_volume": int(round(float(volume) / factor)) if factor > 0 else None,
            "div_cash": dividends.get(int(timestamp), 0.0),
            "split_factor": splits.get(int(timestamp), 1.0),
            "gross_return_factor": 1.0,
            "adjusted_reference_factor": factor,
            "adjusted_reference_relative_error": 0.0,
            "source_url": metadata["requested_url"],
            "source_document_sha256": metadata["sha256"],
            "observed_at": metadata["retrieved_at"],
            "available_at": metadata["retrieved_at"],
            "availability_basis": "RETROSPECTIVE_YAHOO_QUERY2_NOT_PIT",
            "price_adjustment_status": "YAHOO_ADJ_CLOSE_RATIO",
            "quality_status": "RESEARCH_PRIMARY_YAHOO_NO_REQUIRED_CROSSCHECK",
            "conflict_flags_json": "{}",
            "synthetic_data": False,
        }
        rows.append(row)
    rows.sort(key=lambda row: row["trade_date"])
    for index, row in enumerate(rows):
        if index:
            row["gross_return_factor"] = (
                row["adj_close"] / rows[index - 1]["adj_close"]
            )
        row["row_sha256"] = _hash_value(row)
    if not rows:
        raise PriceInputError(f"no valid Yahoo daily rows: {symbol}")
    return rows


def _formation_close(accepted_at: datetime, qqq_dates: list[date]) -> date:
    eastern = ZoneInfo("America/New_York")
    for day in qqq_dates:
        market_close = datetime.combine(day, daytime(16, 0), eastern).astimezone(UTC)
        if market_close > accepted_at.astimezone(UTC):
            return day
    raise PriceInputError(f"no QQQ close after acceptance: {accepted_at}")


def _entry_coverage(
    holdings: list[dict[str, Any]], rows_by_symbol: dict[str, list[dict[str, Any]]]
) -> dict[str, Any]:
    qqq_dates = [
        date.fromisoformat(row["trade_date"]) for row in rows_by_symbol["QQQ"]
    ]
    available = {
        symbol: {date.fromisoformat(row["trade_date"]) for row in rows}
        for symbol, rows in rows_by_symbol.items()
    }
    per_formation: list[dict[str, Any]] = []
    for report_date in sorted({row["report_date"] for row in holdings}):
        positions = [row for row in holdings if row["report_date"] == report_date]
        accepted_at = positions[0]["accepted_at"]
        execution_date = _formation_close(accepted_at, qqq_dates)
        priced = sum(execution_date in available.get(row["symbol"], set()) for row in positions)
        per_formation.append(
            {
                "report_date": report_date.isoformat(),
                "accepted_at": accepted_at.isoformat(),
                "execution_date": execution_date.isoformat(),
                "position_count": len(positions),
                "priced_position_count": priced,
            }
        )
    priced_total = sum(item["priced_position_count"] for item in per_formation)
    position_total = sum(item["position_count"] for item in per_formation)
    return {
        "formation_count": len(per_formation),
        "position_total": position_total,
        "priced_position_total": priced_total,
        "coverage": priced_total / position_total,
        "minimum_priced_positions": min(
            item["priced_position_count"] for item in per_formation
        ),
        "per_formation_without_security_names": per_formation,
    }


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    raw = b"".join(
        (
            json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False)
            + "\n"
        ).encode()
        for row in rows
    )
    smoke._write_atomic(path, raw)


def _write_database(database_path: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    connection = duckdb.connect(str(database_path))
    inserted = False
    try:
        connection.execute("BEGIN TRANSACTION")
        existing = connection.execute(
            """
            SELECT COUNT(*) FROM us_equity_research.us_daily_total_return_research
            WHERE snapshot_id=?
            """,
            [PRICE_SNAPSHOT],
        ).fetchone()[0]
        if existing not in {0, len(rows)}:
            raise PriceInputError(f"partial price snapshot exists: {existing}")
        if existing == 0:
            columns = list(rows[0])
            placeholders = ",".join("?" for _ in columns)
            values = [tuple(row[column] for column in columns) for row in rows]
            connection.executemany(
                "INSERT INTO us_equity_research.us_daily_total_return_research "
                f"({','.join(columns)}) VALUES ({placeholders})",
                values,
            )
            inserted = True
        final_count, symbols = connection.execute(
            """
            SELECT COUNT(*),COUNT(DISTINCT symbol)
            FROM us_equity_research.us_daily_total_return_research
            WHERE snapshot_id=?
            """,
            [PRICE_SNAPSHOT],
        ).fetchone()
        duplicates = connection.execute(
            """
            SELECT COUNT(*) FROM (
              SELECT symbol,trade_date,COUNT(*) n
              FROM us_equity_research.us_daily_total_return_research
              WHERE snapshot_id=?
              GROUP BY 1,2 HAVING n>1
            )
            """,
            [PRICE_SNAPSHOT],
        ).fetchone()[0]
        if final_count != len(rows) or duplicates:
            raise PriceInputError("central price post-write validation failed")
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()
    return {
        "database_path": str(database_path),
        "table": "us_equity_research.us_daily_total_return_research",
        "snapshot_id": PRICE_SNAPSHOT,
        "inserted": inserted,
        "row_count": final_count,
        "symbol_count": symbols,
        "duplicate_symbol_date_count": duplicates,
        "transaction_committed": True,
    }


def run(
    repo_root: Path,
    staging_root: Path,
    database_path: Path,
    result_path: Path,
) -> dict[str, Any]:
    failure: str | None = None
    coverage: dict[str, Any] = {}
    central: dict[str, Any] = {"attempted": False, "transaction_committed": False}
    rows_by_symbol: dict[str, list[dict[str, Any]]] = {}
    source_receipts: list[dict[str, Any]] = []
    normalized_path = staging_root / "normalized" / "daily_rows.jsonl"
    stooq_receipts: list[dict[str, Any]] = []
    try:
        symbols, holdings = _required_inputs(database_path)
        for symbol in [*symbols, "QQQ"]:
            url = _yahoo_url(symbol)
            path = staging_root / "raw/yahoo" / f"{symbol}.json"
            metadata = _download(url, path)
            source_receipts.append(
                {
                    "symbol_hash": hashlib.sha256(symbol.encode()).hexdigest(),
                    "success": metadata.get("success", False),
                    "sha256": metadata.get("sha256"),
                    "byte_count": metadata.get("byte_count"),
                }
            )
            if metadata.get("success"):
                rows_by_symbol[symbol] = _parse_yahoo(
                    path.read_bytes(), symbol, metadata
                )
        if "QQQ" not in rows_by_symbol:
            raise PriceInputError("QQQ price calendar missing")
        coverage = _entry_coverage(holdings, rows_by_symbol)
        if (
            coverage["coverage"] < MINIMUM_ENTRY_COVERAGE
            or coverage["minimum_priced_positions"] < MINIMUM_POSITIONS
        ):
            raise PriceInputError(
                f"entry coverage failed: {coverage['coverage']:.6f}, "
                f"minimum {coverage['minimum_priced_positions']}"
            )
        sample = sorted(symbols)[::10]
        if "QQQ" not in sample:
            sample.append("QQQ")
        for symbol in sample:
            params = {
                "s": f"{symbol.lower()}.us",
                "i": "d",
                "d1": "20190101",
                "d2": "20260723",
            }
            url = f"{STOOQ_BASE}?{urlencode(params)}"
            path = staging_root / "raw/stooq" / f"{symbol}.csv"
            metadata = _download(url, path, maximum_bytes=10 * 1024 * 1024)
            stooq_receipts.append(
                {
                    "symbol_hash": hashlib.sha256(symbol.encode()).hexdigest(),
                    "success": metadata.get("success", False),
                    "sha256": metadata.get("sha256"),
                    "byte_count": metadata.get("byte_count"),
                }
            )
        all_rows = [
            row
            for symbol in sorted(rows_by_symbol)
            for row in rows_by_symbol[symbol]
        ]
        _write_jsonl(normalized_path, all_rows)
        central["attempted"] = True
        central = _write_database(database_path, all_rows)
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        PriceInputError,
        duckdb.Error,
    ) as exc:
        failure = f"{type(exc).__name__}: {exc}"
    qualified = (
        failure is None
        and coverage.get("coverage", 0) >= MINIMUM_ENTRY_COVERAGE
        and coverage.get("minimum_priced_positions", 0) >= MINIMUM_POSITIONS
        and central.get("transaction_committed") is True
    )
    contract = (
        repo_root
        / "research/definitions/us_qqq_disclosed_top50_equal_weight_v1_prices.json"
    )
    result = {
        "research_id": RESEARCH_ID,
        "execution_id": EXECUTION_ID,
        "date": datetime.now(UTC).date().isoformat(),
        "market": "US",
        "phase": "PRICE_INPUT_QUALIFICATION_AND_MATERIALIZATION",
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
        "counts": {
            "required_security_symbol_count": EXPECTED_SYMBOLS,
            "yahoo_success_symbol_count_including_qqq": len(rows_by_symbol),
            "yahoo_failure_symbol_count": EXPECTED_SYMBOLS + 1
            - len(rows_by_symbol),
            "normalized_price_row_count": central.get("row_count", 0),
        },
        "entry_coverage": coverage,
        "yahoo_source_receipts_without_symbols": source_receipts,
        "stooq_diagnostic_receipts_without_symbols": stooq_receipts,
        "normalized_artifact": {
            "path": str(normalized_path),
            "sha256": continuation._sha256_file(normalized_path)
            if normalized_path.is_file()
            else None,
            "byte_count": normalized_path.stat().st_size
            if normalized_path.is_file()
            else None,
        },
        "central_database": central,
        "quality_gates": {
            "entry_price_coverage_at_least_98_percent": coverage.get("coverage", 0)
            >= MINIMUM_ENTRY_COVERAGE,
            "at_least_49_priced_positions_each_formation": coverage.get(
                "minimum_priced_positions", 0
            )
            >= MINIMUM_POSITIONS,
            "qqq_calendar_present": "QQQ" in rows_by_symbol,
            "central_write_committed": central.get("transaction_committed") is True,
            "strategy_returns_accessed": False,
        },
        "research_boundaries": {
            "strategy_candidate_available": False,
            "portfolio_constructed": False,
            "broker_order_paper_live_auto_enabled": False,
        },
        "next_action": (
            "Freeze the one-use equal-weight-vs-QQQ strategy contract."
            if qualified
            else "Stop this research identity without strategy execution."
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
            "us_qqq_disclosed_top50_equal_weight_v1/prices"
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
            "us_qqq_disclosed_top50_equal_weight_v1_prices_20260723.json"
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
