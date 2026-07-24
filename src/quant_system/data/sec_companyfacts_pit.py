"""Acquire a bounded SEC company-facts PIT snapshot for disclosed QQQ names."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import date, datetime, timezone
import fcntl
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import time
from typing import Any, Iterator
import urllib.request

import duckdb

from .writer import DataWriteError, append_rows


HOLDINGS_SNAPSHOT = "qqq_nport_pit_20260723_a10cf2fcdafa4dd8"
MAPPING_SNAPSHOT = "qqq_identity_complete_20260723_767fbc6dbfa92cb9"
TABLE = "us_sec_companyfacts_pit_research"
FORMS = {"10-K", "20-F", "40-F"}
START_DATE = date(2017, 1, 1)
QUALIFICATION_FRACTION = 0.80
HISTORICAL_CIKS = {
    "ATVI": (718877, "ACTIVISION BLIZZARD, INC."),
    "CELG": (816284, "CELGENE CORP"),
    "WBA": (1618921, "WALGREENS BOOTS ALLIANCE, INC."),
}
CONCEPTS = {
    ("us-gaap", "NetIncomeLoss"): "income",
    ("us-gaap", "Assets"): "assets",
    ("ifrs-full", "ProfitLoss"): "income",
    ("ifrs-full", "Assets"): "assets",
}
TABLE_COLUMNS = (
    ("snapshot_id", "VARCHAR NOT NULL"),
    ("row_sha256", "VARCHAR NOT NULL"),
    ("symbol", "VARCHAR NOT NULL"),
    ("cik", "BIGINT NOT NULL"),
    ("entity_name", "VARCHAR NOT NULL"),
    ("taxonomy", "VARCHAR NOT NULL"),
    ("concept", "VARCHAR NOT NULL"),
    ("unit", "VARCHAR NOT NULL"),
    ("value", "DOUBLE NOT NULL"),
    ("start_date", "DATE"),
    ("end_date", "DATE NOT NULL"),
    ("filed_date", "DATE NOT NULL"),
    ("available_at", "DATE NOT NULL"),
    ("form", "VARCHAR NOT NULL"),
    ("fiscal_year", "INTEGER"),
    ("fiscal_period", "VARCHAR"),
    ("accession_number", "VARCHAR NOT NULL"),
    ("frame", "VARCHAR"),
    ("source_url", "VARCHAR NOT NULL"),
    ("source_sha256", "VARCHAR NOT NULL"),
    ("retrieved_at", "TIMESTAMPTZ NOT NULL"),
    ("synthetic_data", "BOOLEAN NOT NULL"),
)


class QualificationError(RuntimeError):
    """Raised when the bounded input cannot support the declared table."""


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
            default=str,
        )
        + "\n"
    ).encode("utf-8")


def _rows_bytes(rows: list[dict[str, Any]]) -> bytes:
    expected = tuple(name for name, _sql_type in TABLE_COLUMNS)
    if any(tuple(row) != expected for row in rows):
        raise QualificationError("normalized row columns do not match the table contract")
    return (
        json.dumps(
            rows,
            ensure_ascii=False,
            sort_keys=False,
            separators=(",", ":"),
            allow_nan=False,
            default=str,
        )
        + "\n"
    ).encode("utf-8")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _atomic_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_bytes(raw)
    os.replace(temporary, path)


def _decode(raw: bytes, encoding: str | None) -> bytes:
    return gzip.decompress(raw) if encoding == "gzip" or raw[:2] == b"\x1f\x8b" else raw


def _request_json(url: str, user_agent: str) -> tuple[bytes, dict[str, Any]]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept-Encoding": "gzip",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        raw = _decode(response.read(), response.headers.get("Content-Encoding", "").lower())
        if response.status != 200:
            raise QualificationError(f"SEC returned HTTP {response.status}: {url}")
    document = json.loads(raw)
    if not isinstance(document, dict):
        raise QualificationError(f"SEC response is not an object: {url}")
    return raw, document


def ticker_map(document: dict[str, Any]) -> dict[str, tuple[int, str]]:
    result: dict[str, tuple[int, str]] = {}
    for value in document.values():
        if not isinstance(value, dict):
            continue
        ticker = str(value.get("ticker", "")).upper().replace(".", "-")
        title = str(value.get("title", "")).strip()
        cik = value.get("cik_str")
        if ticker and title and isinstance(cik, int):
            result[ticker] = (cik, title)
    result.update(HISTORICAL_CIKS)
    return result


def universe_symbols(database: Path) -> list[str]:
    connection = duckdb.connect(str(database), read_only=True)
    try:
        rows = connection.execute(
            """
            SELECT DISTINCT upper(m.symbol) AS symbol
            FROM us_equity_research.qqq_holdings_pit_research h
            JOIN us_equity_research.qqq_security_mapping_research m
              ON h.cusip=m.cusip
            WHERE h.snapshot_id=?
              AND m.snapshot_id=?
              AND h.is_top50
              AND m.symbol IS NOT NULL
            ORDER BY 1
            """,
            [HOLDINGS_SNAPSHOT, MAPPING_SNAPSHOT],
        ).fetchall()
    finally:
        connection.close()
    symbols = sorted({str(row[0]).replace(".", "-") for row in rows})
    if len(symbols) < 50:
        raise QualificationError("QQQ PIT universe contains fewer than 50 mapped symbols")
    return symbols


def _date(value: object) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _row_identity(row: dict[str, Any]) -> str:
    keys = (
        "symbol",
        "cik",
        "taxonomy",
        "concept",
        "unit",
        "value",
        "start_date",
        "end_date",
        "filed_date",
        "form",
        "fiscal_year",
        "fiscal_period",
        "accession_number",
        "frame",
        "source_sha256",
    )
    return _sha256(_canonical({key: row[key] for key in keys}))


def extract_rows(
    *,
    symbol: str,
    cik: int,
    document: dict[str, Any],
    source_url: str,
    source_sha256: str,
    retrieved_at: datetime,
) -> list[dict[str, Any]]:
    entity_name = str(document.get("entityName", "")).strip()
    facts = document.get("facts")
    if not entity_name or not isinstance(facts, dict):
        raise QualificationError(f"companyfacts identity is incomplete for {symbol}")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for (taxonomy, concept), _kind in CONCEPTS.items():
        taxonomy_facts = facts.get(taxonomy, {})
        if not isinstance(taxonomy_facts, dict):
            continue
        fact = taxonomy_facts.get(concept, {})
        units = fact.get("units", {}) if isinstance(fact, dict) else {}
        if not isinstance(units, dict):
            continue
        for unit, observations in units.items():
            if not isinstance(observations, list):
                continue
            for observation in observations:
                if not isinstance(observation, dict) or observation.get("form") not in FORMS:
                    continue
                end = _date(observation.get("end"))
                filed = _date(observation.get("filed"))
                accession = observation.get("accn")
                value = observation.get("val")
                if (
                    end is None
                    or end < START_DATE
                    or filed is None
                    or not isinstance(accession, str)
                    or not accession
                    or not isinstance(value, (int, float))
                    or not math.isfinite(float(value))
                ):
                    continue
                fiscal_year = observation.get("fy")
                row = {
                    "snapshot_id": "",
                    "row_sha256": "",
                    "symbol": symbol,
                    "cik": cik,
                    "entity_name": entity_name,
                    "taxonomy": taxonomy,
                    "concept": concept,
                    "unit": str(unit),
                    "value": float(value),
                    "start_date": _date(observation.get("start")),
                    "end_date": end,
                    "filed_date": filed,
                    "available_at": filed,
                    "form": str(observation["form"]),
                    "fiscal_year": fiscal_year if isinstance(fiscal_year, int) else None,
                    "fiscal_period": (
                        str(observation["fp"]) if observation.get("fp") is not None else None
                    ),
                    "accession_number": accession,
                    "frame": (
                        str(observation["frame"])
                        if observation.get("frame") is not None
                        else None
                    ),
                    "source_url": source_url,
                    "source_sha256": source_sha256,
                    "retrieved_at": retrieved_at,
                    "synthetic_data": False,
                }
                identity = _row_identity(row)
                if identity in seen:
                    continue
                row["row_sha256"] = identity
                seen.add(identity)
                rows.append(row)
    return rows


def qualification(
    rows: list[dict[str, Any]], symbols: list[str]
) -> tuple[dict[str, Any], set[str]]:
    coverage: dict[str, dict[str, set[str]]] = {}
    for row in rows:
        kind = CONCEPTS[(str(row["taxonomy"]), str(row["concept"]))]
        coverage.setdefault(str(row["symbol"]), {}).setdefault(kind, set()).add(
            str(row["unit"])
        )
    qualified = {
        symbol
        for symbol, kinds in coverage.items()
        if kinds.get("income", set()) & kinds.get("assets", set())
    }
    fraction = len(qualified) / len(symbols)
    result = {
        "symbol_count": len(symbols),
        "qualified_symbol_count": len(qualified),
        "qualified_fraction": fraction,
        "minimum_fraction": QUALIFICATION_FRACTION,
        "missing_or_unqualified_symbols": sorted(set(symbols) - qualified),
        "passed": fraction >= QUALIFICATION_FRACTION,
    }
    return result, qualified


@contextmanager
def _database_writer_lock(database: Path, timeout_seconds: float = 30.0) -> Iterator[None]:
    lock_path = database.with_suffix(database.suffix + ".writer.lock")
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        deadline = time.monotonic() + timeout_seconds
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError as exc:
                if time.monotonic() >= deadline:
                    raise DataWriteError("writer lock is held") from exc
                time.sleep(0.05)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def ensure_table(database: Path) -> None:
    definitions = ", ".join(f"{name} {sql_type}" for name, sql_type in TABLE_COLUMNS)
    with _database_writer_lock(database):
        connection = duckdb.connect(str(database))
        try:
            connection.execute("BEGIN")
            connection.execute("CREATE SCHEMA IF NOT EXISTS us_equity_research")
            connection.execute(
                f"CREATE TABLE IF NOT EXISTS us_equity_research.{TABLE} ({definitions})"
            )
            actual = tuple(
                (str(row[0]), str(row[1]), str(row[2]))
                for row in connection.execute(
                    "SELECT column_name, data_type, is_nullable "
                    "FROM information_schema.columns "
                    "WHERE table_schema='us_equity_research' AND table_name=? "
                    "ORDER BY ordinal_position",
                    [TABLE],
                ).fetchall()
            )
            expected = tuple(
                (
                    name,
                    (
                        "TIMESTAMP WITH TIME ZONE"
                        if sql_type.replace(" NOT NULL", "") == "TIMESTAMPTZ"
                        else sql_type.replace(" NOT NULL", "")
                    ),
                    "NO" if "NOT NULL" in sql_type else "YES",
                )
                for name, sql_type in TABLE_COLUMNS
            )
            if actual != expected:
                raise DataWriteError("SEC company-facts target table contract mismatch")
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--user-agent")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--input-run", type=Path)
    return parser.parse_args(argv)


def _execute_staged(
    *, database: Path, data_root: Path, input_run: Path
) -> dict[str, Any]:
    run = input_run.resolve(strict=True)
    staging_root = (data_root / "staging" / "us_sec_companyfacts_pit_v1").resolve(
        strict=True
    )
    if not run.is_relative_to(staging_root):
        raise QualificationError("input run must stay inside the SEC staging root")
    receipt_path = run / "receipt.json"
    rows_path = run / "rows.json"
    receipt = json.loads(receipt_path.read_bytes())
    rows_raw = rows_path.read_bytes()
    rows_sha = _sha256(rows_raw)
    rows = json.loads(rows_raw)
    if (
        not isinstance(receipt, dict)
        or receipt.get("status") not in {"INPUT_QUALIFIED", "COMPLETED"}
        or receipt.get("qualification", {}).get("passed") is not True
        or receipt.get("rows_sha256") != rows_sha
        or receipt.get("database") != str(database)
        or receipt.get("target") != f"us_equity_research.{TABLE}"
        or not isinstance(rows, list)
        or not rows
    ):
        raise QualificationError("staged run does not match the qualified contract")
    expected = tuple(name for name, _sql_type in TABLE_COLUMNS)
    if any(not isinstance(row, dict) or tuple(row) != expected for row in rows):
        raise QualificationError("staged rows do not match the table contract")
    snapshot_id = receipt.get("snapshot_id")
    if not isinstance(snapshot_id, str) or any(
        row.get("snapshot_id") != snapshot_id for row in rows
    ):
        raise QualificationError("staged rows do not match the snapshot identity")
    ensure_table(database)
    result = append_rows(
        database,
        schema="us_equity_research",
        table=TABLE,
        natural_keys=("snapshot_id", "row_sha256"),
        rows=rows,
        batch_id=snapshot_id,
        source_sha256=rows_sha,
        max_rows=100_000,
        lock_timeout_seconds=30,
    )
    receipt["writes"] = True
    receipt["status"] = "COMPLETED"
    receipt["append_result"] = result.to_dict()
    _atomic_write(receipt_path, _canonical(receipt))
    return receipt


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    database = args.database.resolve(strict=True)
    data_root = args.data_root.resolve(strict=True)
    if not (database == data_root or database.is_relative_to(data_root)):
        raise QualificationError("database must stay inside data root")
    if args.execute:
        if args.input_run is None:
            raise QualificationError("--execute requires a qualified --input-run")
        receipt = _execute_staged(
            database=database, data_root=data_root, input_run=args.input_run
        )
        print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, default=str))
        return 0
    if args.input_run is not None:
        raise QualificationError("--input-run is only valid with --execute")
    if args.user_agent is None:
        raise QualificationError("dry-run acquisition requires --user-agent")
    if "@" not in args.user_agent or "example.com" in args.user_agent.lower():
        raise QualificationError("SEC user agent must contain a real contact email")
    if not 1 <= args.workers <= 4:
        raise QualificationError("workers must be between 1 and 4")

    run_at = datetime.now(timezone.utc)
    run_key = run_at.strftime("%Y%m%dT%H%M%SZ")
    output = data_root / "staging" / "us_sec_companyfacts_pit_v1" / run_key
    raw_dir = output / "raw"

    ticker_url = "https://www.sec.gov/files/company_tickers.json"
    ticker_raw, ticker_document = _request_json(ticker_url, args.user_agent)
    _atomic_write(raw_dir / "company_tickers.json", ticker_raw)
    mapping = ticker_map(ticker_document)
    symbols = universe_symbols(database)
    missing_ciks = sorted(set(symbols) - set(mapping))
    if missing_ciks:
        raise QualificationError(f"missing SEC CIK mapping: {missing_ciks}")

    documents: dict[str, tuple[int, str, bytes, dict[str, Any]]] = {}

    def fetch(symbol: str) -> tuple[str, int, str, bytes, dict[str, Any]]:
        cik, _title = mapping[symbol]
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
        raw, document = _request_json(url, args.user_agent)
        return symbol, cik, url, raw, document

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(fetch, symbol): symbol for symbol in symbols}
        for future in as_completed(futures):
            symbol, cik, url, raw, document = future.result()
            documents[symbol] = (cik, url, raw, document)
            _atomic_write(raw_dir / f"CIK{cik:010d}.json", raw)

    rows: list[dict[str, Any]] = []
    manifest = {
        "ticker_source": {"url": ticker_url, "sha256": _sha256(ticker_raw)},
        "companies": [],
    }
    for symbol in symbols:
        cik, url, raw, document = documents[symbol]
        source_sha = _sha256(raw)
        company_rows = extract_rows(
            symbol=symbol,
            cik=cik,
            document=document,
            source_url=url,
            source_sha256=source_sha,
            retrieved_at=run_at,
        )
        rows.extend(company_rows)
        manifest["companies"].append(
            {"symbol": symbol, "cik": cik, "url": url, "sha256": source_sha}
        )

    qualified, _qualified_symbols = qualification(rows, symbols)
    manifest_sha = _sha256(_canonical(manifest))
    snapshot_id = f"US_SEC_COMPANYFACTS_PIT_V1_{run_at:%Y%m%d}_{manifest_sha[:12]}"
    for row in rows:
        row["snapshot_id"] = snapshot_id
    rows.sort(key=lambda row: (str(row["symbol"]), str(row["row_sha256"])))
    rows_raw = _rows_bytes(rows)
    rows_sha = _sha256(rows_raw)
    _atomic_write(output / "manifest.json", _canonical(manifest))
    _atomic_write(output / "rows.json", rows_raw)

    receipt = {
        "snapshot_id": snapshot_id,
        "phase": "DATA_QUALIFICATION",
        "status": "INPUT_QUALIFIED" if qualified["passed"] else "INPUT_BLOCKED",
        "writes": False,
        "database": str(database),
        "target": f"us_equity_research.{TABLE}",
        "row_count": len(rows),
        "rows_sha256": rows_sha,
        "manifest_sha256": manifest_sha,
        "qualification": qualified,
        "output": str(output),
        "strategy_outcomes_accessed": False,
        "strategy_candidate_available": False,
    }
    _atomic_write(output / "receipt.json", _canonical(receipt))
    if not qualified["passed"]:
        print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
