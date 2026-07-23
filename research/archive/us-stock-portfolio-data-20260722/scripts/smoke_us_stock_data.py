"""Run the frozen, outcome-blind US stock data source smoke.

This script writes only raw HTTP responses and a machine-readable smoke summary
under the caller-supplied staging directory.  It never opens the canonical
DuckDB and never computes returns, signals, ranks, or portfolios.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, time, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DOLT_BASE = "https://www.dolthub.com/api/v1alpha1/post-no-preference/stocks/master"
DOLT_COMMIT = "t83d0tqifiqnkg2qdm45e7ktcfdq5cbe"
YAHOO_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
USER_AGENT = "quant-proj-research/2.0 (+https://github.com/2604714984-prog/quant-proj)"
SAFE_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")

YAHOO_CROSSCHECK_SYMBOLS = (
    "AAPL",
    "AMGN",
    "AMZN",
    "CRM",
    "DOW",
    "GE",
    "HON",
    "IBM",
    "INTC",
    "JPM",
    "KO",
    "META",
    "MSFT",
    "NVDA",
    "PFE",
    "PG",
    "SHW",
    "UNH",
    "WMT",
    "XOM",
)
YAHOO_TERMINAL_PROBES = (
    "ATVI",
    "CELG",
    "DWDP",
    "FRC",
    "RTN",
    "SIVB",
    "TWTR",
    "UTX",
    "VMW",
    "XLNX",
)


class SmokeError(RuntimeError):
    """Raised when the primary source cannot satisfy its response contract."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _write_bytes(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def _request(
    *,
    url: str,
    destination: Path,
    query: dict[str, str] | None = None,
    timeout_seconds: float = 45.0,
) -> tuple[dict[str, Any], bytes]:
    effective_url = url
    if query:
        effective_url = f"{url}?{urlencode(query)}"
    metadata_path = destination.with_suffix(destination.suffix + ".metadata.json")
    if metadata_path.exists():
        cached_metadata = _strict_json(metadata_path.read_bytes(), str(metadata_path))
        if cached_metadata.get("url") != effective_url:
            raise SmokeError(f"staging URL collision at {metadata_path}")
        if destination.exists():
            cached_raw = destination.read_bytes()
            if (
                cached_metadata.get("byte_count") != len(cached_raw)
                or cached_metadata.get("content_sha256") != _sha256(cached_raw)
            ):
                raise SmokeError(f"staging content hash mismatch at {destination}")
            return {**cached_metadata, "cache_reused": True}, cached_raw
        if cached_metadata.get("transport_error"):
            return {**cached_metadata, "cache_reused": True}, b""
        raise SmokeError(f"staging response body missing at {destination}")
    if destination.exists():
        raise SmokeError(f"staging metadata missing at {destination}")
    request = Request(
        effective_url,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        method="GET",
    )
    retrieved_at = _utc_now()
    status: int
    headers: dict[str, str]
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            status = int(response.status)
            headers = {str(k).lower(): str(v) for k, v in response.headers.items()}
            raw = response.read()
    except HTTPError as exc:
        status = int(exc.code)
        headers = {str(k).lower(): str(v) for k, v in exc.headers.items()}
        raw = exc.read()
    except OSError as exc:
        metadata = {
            "url": effective_url,
            "retrieved_at": retrieved_at,
            "http_status": None,
            "byte_count": 0,
            "content_sha256": None,
            "content_type": None,
            "etag": None,
            "last_modified": None,
            "body_path": None,
            "transport_error": f"{type(exc).__name__}: {exc}",
        }
        _write_json(metadata_path, metadata)
        return metadata, b""
    _write_bytes(destination, raw)
    metadata = {
        "url": effective_url,
        "retrieved_at": retrieved_at,
        "http_status": status,
        "byte_count": len(raw),
        "content_sha256": _sha256(raw),
        "content_type": headers.get("content-type"),
        "etag": headers.get("etag"),
        "last_modified": headers.get("last-modified"),
        "body_path": str(destination),
    }
    _write_json(metadata_path, metadata)
    return metadata, raw


def _strict_json(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SmokeError(f"{label} did not return valid JSON") from exc
    if not isinstance(value, dict):
        raise SmokeError(f"{label} returned a non-object JSON root")
    return value


def _dolt_query(staging: Path, name: str, sql: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    metadata, raw = _request(
        url=DOLT_BASE,
        destination=staging / "dolthub" / f"{name}.json",
        query={"q": sql},
    )
    if metadata["http_status"] is None:
        raise SmokeError(
            f"DoltHub {name} transport failure: {metadata.get('transport_error')}"
        )
    payload = _strict_json(raw, f"DoltHub {name}")
    if metadata["http_status"] != 200 or payload.get("query_execution_status") != "Success":
        raise SmokeError(
            f"DoltHub {name} failed: http={metadata['http_status']} "
            f"status={payload.get('query_execution_status')} "
            f"message={payload.get('query_execution_message')}"
        )
    rows = payload.get("rows")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise SmokeError(f"DoltHub {name} returned malformed rows")
    return rows, metadata


def _sql_symbols(symbols: list[str] | tuple[str, ...]) -> str:
    if not symbols or any(SAFE_NAME.fullmatch(symbol) is None for symbol in symbols):
        raise SmokeError("unsafe or empty symbol set")
    return ",".join(f"'{symbol}'" for symbol in symbols)


def _decimal(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise SmokeError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise SmokeError(f"non-finite decimal value: {value!r}")
    return result


def _epoch(day: date) -> int:
    return int(datetime.combine(day, time.min, tzinfo=timezone.utc).timestamp())


def _yahoo_fetch(staging: Path, symbol: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    metadata, raw = _request(
        url=f"{YAHOO_BASE}/{symbol}",
        destination=staging / "yahoo" / f"{symbol}.json",
        query={
            "period1": str(_epoch(date(2018, 1, 1))),
            "period2": str(_epoch(date(2026, 7, 23))),
            "interval": "1d",
            "events": "div,splits",
            "includeAdjustedClose": "true",
        },
    )
    if metadata["http_status"] is None:
        return None, metadata
    try:
        payload = _strict_json(raw, f"Yahoo {symbol}")
    except SmokeError:
        return None, metadata
    chart = payload.get("chart")
    if metadata["http_status"] != 200 or not isinstance(chart, dict):
        return None, metadata
    results = chart.get("result")
    if chart.get("error") is not None or not isinstance(results, list) or len(results) != 1:
        return None, metadata
    result = results[0]
    return (result if isinstance(result, dict) else None), metadata


def _yahoo_close_map(result: dict[str, Any]) -> dict[str, Decimal]:
    timestamps = result.get("timestamp")
    indicators = result.get("indicators")
    if not isinstance(timestamps, list) or not isinstance(indicators, dict):
        return {}
    quotes = indicators.get("quote")
    if not isinstance(quotes, list) or len(quotes) != 1 or not isinstance(quotes[0], dict):
        return {}
    closes = quotes[0].get("close")
    if not isinstance(closes, list) or len(closes) != len(timestamps):
        return {}
    output: dict[str, Decimal] = {}
    for timestamp, close in zip(timestamps, closes, strict=True):
        if close is None:
            continue
        day = datetime.fromtimestamp(int(timestamp), tz=timezone.utc).date().isoformat()
        output[day] = _decimal(close)
    return output


def _yahoo_actions(result: dict[str, Any], event_type: str) -> dict[str, Decimal]:
    events = result.get("events")
    if not isinstance(events, dict):
        return {}
    raw_events = events.get(event_type)
    if not isinstance(raw_events, dict):
        return {}
    output: dict[str, Decimal] = {}
    for event in raw_events.values():
        if not isinstance(event, dict) or "date" not in event:
            continue
        day = datetime.fromtimestamp(int(event["date"]), tz=timezone.utc).date().isoformat()
        if event_type == "dividends" and event.get("amount") is not None:
            output[day] = _decimal(event["amount"])
        elif event_type == "splits":
            numerator = event.get("numerator")
            denominator = event.get("denominator")
            if numerator is not None and denominator not in {None, 0}:
                output[day] = _decimal(numerator) / _decimal(denominator)
    return output


def _yahoo_bar_summary(result: dict[str, Any]) -> dict[str, Any]:
    timestamps = result.get("timestamp")
    indicators = result.get("indicators")
    if not isinstance(timestamps, list) or not isinstance(indicators, dict):
        return {"row_count": 0, "duplicate_dates": 0, "invalid_core": 1}
    quotes = indicators.get("quote")
    if not isinstance(quotes, list) or len(quotes) != 1 or not isinstance(quotes[0], dict):
        return {"row_count": 0, "duplicate_dates": 0, "invalid_core": 1}
    quote = quotes[0]
    columns = {name: quote.get(name) for name in ("open", "high", "low", "close", "volume")}
    if any(not isinstance(values, list) or len(values) != len(timestamps) for values in columns.values()):
        return {"row_count": 0, "duplicate_dates": 0, "invalid_core": 1}
    days: list[str] = []
    invalid_core = 0
    valid_rows = 0
    for index, timestamp in enumerate(timestamps):
        day = datetime.fromtimestamp(int(timestamp), tz=timezone.utc).date().isoformat()
        days.append(day)
        values = {name: columns[name][index] for name in columns}
        if any(value is None for value in values.values()):
            invalid_core += 1
            continue
        numeric = {name: _decimal(value) for name, value in values.items()}
        if (
            any(value < 0 for value in numeric.values())
            or numeric["high"] < max(numeric["open"], numeric["close"], numeric["low"])
            or numeric["low"] > min(numeric["open"], numeric["close"], numeric["high"])
        ):
            invalid_core += 1
        else:
            valid_rows += 1
    unique_days = set(days)
    return {
        "row_count": len(timestamps),
        "valid_rows": valid_rows,
        "duplicate_dates": len(days) - len(unique_days),
        "invalid_core": invalid_core,
        "min_date": min(unique_days) if unique_days else None,
        "max_date": max(unique_days) if unique_days else None,
    }


def run(contract_path: Path, staging: Path) -> dict[str, Any]:
    contract_raw = contract_path.read_bytes()
    contract = _strict_json(contract_raw, "data contract")
    symbols = contract["smoke_cohort"]["symbols"]
    required_cases = contract["smoke_cohort"]["required_cases"]
    if len(symbols) != contract["smoke_cohort"]["count"] or len(set(symbols)) != len(symbols):
        raise SmokeError("contract smoke cohort count or uniqueness mismatch")
    symbol_sql = _sql_symbols(symbols)
    as_of = f"'{DOLT_COMMIT}'"

    metadata_rows, metadata_doc = _dolt_query(
        staging,
        "smoke_symbol_metadata",
        "SELECT act_symbol,security_name,listing_exchange,market_category,is_etf,"
        "round_lot_size,is_test_issue,financial_status,cqs_symbol,nasdaq_symbol,"
        "is_next_shares,last_seen FROM symbol AS OF "
        f"{as_of} WHERE act_symbol IN ({symbol_sql}) ORDER BY act_symbol",
    )
    anchor_dates = (
        "2018-01-02",
        "2019-01-02",
        "2020-01-02",
        "2021-01-04",
        "2022-01-03",
        "2023-01-03",
        "2024-01-02",
        "2025-01-02",
        "2026-01-02",
        "2026-07-21",
    )
    anchor_rows, anchor_doc = _dolt_query(
        staging,
        "smoke_anchor_rows",
        "SELECT date,act_symbol,open,high,low,close,volume FROM ohlcv AS OF "
        f"{as_of} WHERE date IN ({_sql_symbols(anchor_dates)}) "
        f"AND act_symbol IN ({symbol_sql}) ORDER BY act_symbol,date",
    )
    split_rows, split_doc = _dolt_query(
        staging,
        "smoke_splits",
        "SELECT act_symbol,ex_date,to_factor,for_factor FROM split AS OF "
        f"{as_of} WHERE act_symbol IN ({symbol_sql}) ORDER BY act_symbol,ex_date",
    )
    dividend_symbols = required_cases["cash_dividend"]
    dividend_rows, dividend_doc = _dolt_query(
        staging,
        "smoke_dividends",
        "SELECT act_symbol,ex_date,amount FROM dividend AS OF "
        f"{as_of} WHERE act_symbol IN ({_sql_symbols(dividend_symbols)}) "
        "AND ex_date>='2018-01-01' ORDER BY act_symbol,ex_date",
    )
    recent_rows, recent_doc = _dolt_query(
        staging,
        "smoke_recent_crosscheck_rows",
        "SELECT date,act_symbol,open,high,low,close,volume FROM ohlcv AS OF "
        f"{as_of} WHERE date IN "
        f"({_sql_symbols(('2026-07-15', '2026-07-16', '2026-07-17', '2026-07-20', '2026-07-21'))}) "
        "AND act_symbol IN "
        f"({_sql_symbols(YAHOO_CROSSCHECK_SYMBOLS)}) ORDER BY act_symbol,date",
    )
    last_seen_pairs = sorted(
        (str(row["last_seen"]), str(row["act_symbol"]))
        for row in metadata_rows
        if row.get("last_seen") is not None
        and str(row["act_symbol"]) in YAHOO_TERMINAL_PROBES
    )
    if not last_seen_pairs or any(
        SAFE_NAME.fullmatch(day) is None or SAFE_NAME.fullmatch(symbol) is None
        for day, symbol in last_seen_pairs
    ):
        raise SmokeError("missing or unsafe terminal last_seen keys")
    terminal_predicates = " OR ".join(
        f"(date='{day}' AND act_symbol='{symbol}')" for day, symbol in last_seen_pairs
    )
    terminal_rows, terminal_doc = _dolt_query(
        staging,
        "smoke_terminal_rows",
        "SELECT date,act_symbol,open,high,low,close,volume FROM ohlcv AS OF "
        f"{as_of} WHERE {terminal_predicates} ORDER BY act_symbol",
    )

    yahoo_results: dict[str, dict[str, Any]] = {}
    yahoo_documents: list[dict[str, Any]] = []
    yahoo_failures: list[str] = []
    for symbol in symbols:
        result, document = _yahoo_fetch(staging, symbol)
        yahoo_documents.append(document)
        if result is None:
            yahoo_failures.append(symbol)
        else:
            yahoo_results[symbol] = result

    recent_by_symbol: dict[str, list[dict[str, Any]]] = {}
    for row in recent_rows:
        recent_by_symbol.setdefault(str(row["act_symbol"]), []).append(row)
    close_comparisons: list[dict[str, Any]] = []
    close_failures: list[dict[str, Any]] = []
    for symbol in YAHOO_CROSSCHECK_SYMBOLS:
        yahoo = yahoo_results.get(symbol)
        if yahoo is None:
            continue
        closes = _yahoo_close_map(yahoo)
        for row in recent_by_symbol.get(symbol, []):
            day = str(row["date"])
            if day not in closes:
                continue
            dolt_close = _decimal(row["close"])
            yahoo_close = closes[day]
            absolute_difference = abs(dolt_close - yahoo_close)
            tolerance = max(Decimal("0.01"), abs(yahoo_close) * Decimal("0.001"))
            comparison = {
                "symbol": symbol,
                "date": day,
                "dolt_close": str(dolt_close),
                "yahoo_close": str(yahoo_close),
                "absolute_difference": str(absolute_difference),
                "tolerance": str(tolerance),
                "pass": absolute_difference <= tolerance,
            }
            close_comparisons.append(comparison)
            if not comparison["pass"]:
                close_failures.append(comparison)

    dolt_splits: dict[str, dict[str, Decimal]] = {}
    invalid_split_rows: list[dict[str, Any]] = []
    for row in split_rows:
        to_factor = _decimal(row["to_factor"])
        for_factor = _decimal(row["for_factor"])
        if to_factor <= 0 or for_factor <= 0:
            invalid_split_rows.append(
                {
                    "act_symbol": str(row["act_symbol"]),
                    "ex_date": str(row["ex_date"]),
                    "to_factor": str(to_factor),
                    "for_factor": str(for_factor),
                }
            )
            continue
        dolt_splits.setdefault(str(row["act_symbol"]), {})[str(row["ex_date"])] = (
            to_factor / for_factor
        )
    split_checks: list[dict[str, Any]] = []
    for symbol in required_cases["split"]:
        yahoo = yahoo_results.get(symbol)
        yahoo_splits = _yahoo_actions(yahoo, "splits") if yahoo is not None else {}
        for day, ratio in dolt_splits.get(symbol, {}).items():
            if day < "2018-01-01":
                continue
            observed = yahoo_splits.get(day)
            split_checks.append(
                {
                    "symbol": symbol,
                    "ex_date": day,
                    "dolt_ratio": str(ratio),
                    "yahoo_ratio": str(observed) if observed is not None else None,
                    "pass": observed == ratio,
                }
            )

    dolt_dividends: dict[str, dict[str, Decimal]] = {}
    for row in dividend_rows:
        dolt_dividends.setdefault(str(row["act_symbol"]), {})[str(row["ex_date"])] = _decimal(
            row["amount"]
        )
    dividend_checks: list[dict[str, Any]] = []
    for symbol in dividend_symbols:
        yahoo = yahoo_results.get(symbol)
        yahoo_dividends = _yahoo_actions(yahoo, "dividends") if yahoo is not None else {}
        for day, amount in dolt_dividends.get(symbol, {}).items():
            observed = yahoo_dividends.get(day)
            difference = abs(observed - amount) if observed is not None else None
            dividend_checks.append(
                {
                    "symbol": symbol,
                    "ex_date": day,
                    "dolt_amount": str(amount),
                    "yahoo_amount": str(observed) if observed is not None else None,
                    "pass": difference is not None and difference <= Decimal("0.0001"),
                }
            )

    metadata_symbols = {str(row["act_symbol"]) for row in metadata_rows}
    yahoo_summaries = {
        symbol: _yahoo_bar_summary(result) for symbol, result in yahoo_results.items()
    }
    required_terminal = set(required_cases["historically_delisted_or_acquired"])
    terminal_with_history = sorted(
        symbol
        for symbol in required_terminal
        if symbol in yahoo_summaries and int(yahoo_summaries[symbol]["row_count"]) >= 252
    )
    invalid_core_rows = sum(int(summary["invalid_core"]) for summary in yahoo_summaries.values())
    duplicate_dates = sum(int(summary["duplicate_dates"]) for summary in yahoo_summaries.values())
    source_documents = [
        metadata_doc,
        anchor_doc,
        split_doc,
        dividend_doc,
        recent_doc,
        terminal_doc,
        *yahoo_documents,
    ]
    gates = {
        "contract_identity": {
            "pass": _sha256(contract_raw)
            == "2ca2f33b364a2e88c16a8d07128cad2dc9ef43fa7170faa0c1b55ee2d9dacd48",
            "contract_sha256": _sha256(contract_raw),
        },
        "metadata_explicit_for_all_symbols": {
            "pass": len(metadata_symbols) == len(symbols),
            "present": len(metadata_symbols),
            "required": len(symbols),
            "missing": sorted(set(symbols) - metadata_symbols),
        },
        "terminal_case_bar_history": {
            "pass": len(terminal_with_history) == len(required_terminal),
            "present": terminal_with_history,
            "missing_or_short": sorted(required_terminal - set(terminal_with_history)),
        },
        "unique_bar_keys": {
            "pass": duplicate_dates == 0,
            "duplicate_groups": duplicate_dates,
            "dolt_schema_primary_key": ["date", "act_symbol"],
        },
        "finite_nonnegative_valid_ohlcv": {
            "pass": invalid_core_rows == 0,
            "invalid_rows": invalid_core_rows,
        },
        "cross_source_close": {
            "pass": len(close_comparisons) >= 20 and not close_failures,
            "comparison_count": len(close_comparisons),
            "failure_count": len(close_failures),
        },
        "named_split_cases": {
            "pass": bool(split_checks) and all(item["pass"] for item in split_checks),
            "checks": len(split_checks),
            "failures": sum(not item["pass"] for item in split_checks),
        },
        "positive_split_factors": {
            "pass": not invalid_split_rows,
            "invalid_rows": invalid_split_rows,
        },
        "named_dividend_cases": {
            "pass": bool(dividend_checks) and all(item["pass"] for item in dividend_checks),
            "checks": len(dividend_checks),
            "failures": sum(not item["pass"] for item in dividend_checks),
        },
        "merger_or_delist_recovery": {
            "pass": False,
            "reason": "Dolt source has no merger cash, delisting return, bankruptcy recovery, or terminal-value field.",
        },
        "source_available_at": {
            "pass": False,
            "reason": "Dolt source rows have event dates but no provider publication timestamp or historical vintages.",
        },
    }
    blocking_failures = sorted(name for name, gate in gates.items() if not gate["pass"])
    result = {
        "research_id": contract["research_id"],
        "phase": "source_smoke",
        "status": "SMOKE_PASS" if not blocking_failures else "SMOKE_FAIL",
        "current": True,
        "strategy_candidate_available": False,
        "contract_path": str(contract_path),
        "contract_sha256": _sha256(contract_raw),
        "dolt_snapshot": {
            "repository": "post-no-preference/stocks",
            "commit": DOLT_COMMIT,
            "license": "CC-BY-SA-4.0",
        },
        "input_counts": {
            "smoke_symbols": len(symbols),
            "metadata_rows": len(metadata_rows),
            "anchor_rows": len(anchor_rows),
            "split_rows": len(split_rows),
            "dividend_rows": len(dividend_rows),
            "recent_crosscheck_rows": len(recent_rows),
            "terminal_tail_rows": len(terminal_rows),
            "yahoo_successes": len(yahoo_results),
            "yahoo_failures": yahoo_failures,
        },
        "gates": gates,
        "blocking_failures": blocking_failures,
        "close_failures": close_failures,
        "yahoo_bar_summaries": yahoo_summaries,
        "split_checks": split_checks,
        "invalid_split_rows": invalid_split_rows,
        "dividend_checks": dividend_checks,
        "source_documents": source_documents,
        "central_database_opened": False,
        "central_database_write": False,
        "return_computation": False,
        "signal_computation": False,
        "portfolio_computation": False,
        "boundary_result": "OUTCOME_BLIND_STAGING_ONLY_NO_CENTRAL_WRITE",
    }
    _write_json(staging / "smoke_result.json", result)
    _write_json(
        staging / "source_manifest.json",
        {
            "generated_at": _utc_now(),
            "source_documents": source_documents,
            "raw_document_count": len(source_documents),
            "raw_byte_count": sum(int(item["byte_count"]) for item in source_documents),
        },
    )
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path("research/definitions/us_stock_portfolio_data_contract_v1.json"),
    )
    parser.add_argument("--staging-dir", type=Path, required=True)
    parser.add_argument("--execute-network-smoke", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.execute_network_smoke:
        raise SystemExit("--execute-network-smoke is required")
    staging = args.staging_dir.resolve()
    try:
        result = run(args.contract.resolve(), staging)
    except SmokeError as exc:
        result = {
            "phase": "source_smoke",
            "status": "SMOKE_FAIL",
            "current": True,
            "strategy_candidate_available": False,
            "blocking_failures": ["source_response_contract"],
            "fatal_error": f"{type(exc).__name__}: {exc}",
            "central_database_opened": False,
            "central_database_write": False,
            "return_computation": False,
            "signal_computation": False,
            "portfolio_computation": False,
            "boundary_result": "OUTCOME_BLIND_STAGING_ONLY_NO_CENTRAL_WRITE",
        }
        _write_json(staging / "smoke_result.json", result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "blocking_failures": result["blocking_failures"],
                "result_path": str(staging / "smoke_result.json"),
            },
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    )
    return 0 if result["status"] == "SMOKE_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
