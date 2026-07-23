"""Map frozen QQQ top-50 CUSIPs to US composite tickers via OpenFIGI."""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
import hashlib
import io
import json
from pathlib import Path
import time
from typing import Any
from urllib.request import Request, urlopen

import duckdb

import smoke_us_qqq_disclosed_top50_v1 as smoke


RESEARCH_ID = smoke.RESEARCH_ID
EXECUTION_ID = f"{RESEARCH_ID}_CUSIP_MAPPING"
INPUT_SNAPSHOT = "qqq_nport_pit_20260723_a10cf2fcdafa4dd8"
EXPECTED_CUSIPS = 93
MINIMUM_COVERAGE = 0.98
ENDPOINT = "https://api.openfigi.com/v3/mapping"
JOBS_PER_REQUEST = 10
REQUEST_INTERVAL_SECONDS = 2.5
TABLE_NAME = "us_equity_research.qqq_security_mapping_research"


class MappingError(RuntimeError):
    """A frozen security identity mapping gate failed."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _row_sha256(row: dict[str, Any]) -> str:
    raw = json.dumps(
        row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    return hashlib.sha256(raw).hexdigest()


def _input_cusips(database_path: Path) -> list[dict[str, str]]:
    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        rows = connection.execute(
            """
            SELECT cusip, min(issuer_name) AS issuer_name,
                   min(security_title) AS security_title
            FROM us_equity_research.qqq_holdings_pit_research
            WHERE snapshot_id = ? AND is_top50
            GROUP BY cusip
            ORDER BY cusip
            """,
            [INPUT_SNAPSHOT],
        ).fetchall()
    finally:
        connection.close()
    values = [
        {"cusip": str(cusip), "issuer_name": issuer, "security_title": title}
        for cusip, issuer, title in rows
    ]
    if len(values) != EXPECTED_CUSIPS:
        raise MappingError(
            f"expected {EXPECTED_CUSIPS} unique top50 CUSIPs, found {len(values)}"
        )
    return values


def _post_batch(
    batch_index: int, jobs: list[dict[str, str]], raw_root: Path
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not jobs or len(jobs) > JOBS_PER_REQUEST:
        raise MappingError(f"invalid OpenFIGI batch size: {len(jobs)}")
    request_path = raw_root / f"batch_{batch_index:02d}.request.json"
    response_path = raw_root / f"batch_{batch_index:02d}.response.json"
    metadata_path = raw_root / f"batch_{batch_index:02d}.metadata.json"
    request_raw = json.dumps(
        jobs, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode()
    if request_path.is_file() and response_path.is_file() and metadata_path.is_file():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if (
            request_path.read_bytes() != request_raw
            or metadata.get("request_sha256") != _sha256_file(request_path)
            or metadata.get("response_sha256") != _sha256_file(response_path)
        ):
            raise MappingError(f"cached OpenFIGI batch mismatch: {batch_index}")
        response = json.loads(response_path.read_text(encoding="utf-8"))
        return response, {**metadata, "cache_reused": True}
    if request_path.exists() or response_path.exists() or metadata_path.exists():
        raise MappingError(f"incomplete OpenFIGI batch cache: {batch_index}")

    smoke._write_atomic(request_path, request_raw)
    request = Request(
        ENDPOINT,
        method="POST",
        data=request_raw,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": smoke.USER_AGENT,
        },
    )
    time.sleep(REQUEST_INTERVAL_SECONDS)
    with urlopen(request, timeout=45) as response:  # noqa: S310
        status = int(response.status)
        headers = {key.lower(): value for key, value in response.headers.items()}
        response_raw = response.read(20 * 1024 * 1024 + 1)
    if status != 200 or len(response_raw) > 20 * 1024 * 1024:
        raise MappingError(f"OpenFIGI response failure for batch {batch_index}")
    parsed = json.loads(response_raw)
    if not isinstance(parsed, list) or len(parsed) != len(jobs):
        raise MappingError(f"OpenFIGI response count mismatch for batch {batch_index}")
    metadata = {
        "batch_index": batch_index,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "http_status": status,
        "job_count": len(jobs),
        "request_sha256": _sha256_file(request_path),
        "response_sha256": hashlib.sha256(response_raw).hexdigest(),
        "response_byte_count": len(response_raw),
        "rate_limit": headers.get("ratelimit-limit"),
        "rate_limit_remaining": headers.get("ratelimit-remaining"),
        "rate_limit_reset": headers.get("ratelimit-reset"),
        "automatic_retry_count": 0,
    }
    smoke._write_atomic(response_path, response_raw)
    smoke._write_json_atomic(metadata_path, metadata)
    return parsed, {**metadata, "cache_reused": False}


def _select_mapping(result: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    data = result.get("data")
    if not isinstance(data, list):
        if "warning" in result:
            return "NO_MATCH", None
        raise MappingError(f"OpenFIGI mapping error: {result.get('error')}")
    candidates: dict[tuple[Any, ...], dict[str, Any]] = {}
    for item in data:
        if (
            isinstance(item, dict)
            and item.get("exchCode") == "US"
            and item.get("marketSector") == "Equity"
            and item.get("ticker")
        ):
            key = (
                item.get("ticker"),
                item.get("compositeFIGI"),
                item.get("shareClassFIGI"),
                item.get("securityType2"),
            )
            candidates[key] = item
    if not candidates:
        return "NO_US_COMPOSITE_EQUITY", None
    if len(candidates) != 1:
        raise MappingError(
            f"ambiguous US composite equity mapping: {sorted(candidates)}"
        )
    return "MAPPED_UNIQUE_US_COMPOSITE", next(iter(candidates.values()))


def _normalized_rows(
    inputs: list[dict[str, str]],
    staging_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    normalized: list[dict[str, Any]] = []
    batch_receipts: list[dict[str, Any]] = []
    for batch_index, start in enumerate(range(0, len(inputs), JOBS_PER_REQUEST), 1):
        batch = inputs[start : start + JOBS_PER_REQUEST]
        jobs = [{"idType": "ID_CUSIP", "idValue": item["cusip"]} for item in batch]
        response, receipt = _post_batch(batch_index, jobs, staging_root / "raw")
        batch_receipts.append(receipt)
        for source, result in zip(batch, response, strict=True):
            status, selected = _select_mapping(result)
            row = {
                "cusip": source["cusip"],
                "issuer_name": source["issuer_name"],
                "security_title": source["security_title"],
                "symbol": selected.get("ticker") if selected else None,
                "figi": selected.get("figi") if selected else None,
                "composite_figi": selected.get("compositeFIGI") if selected else None,
                "share_class_figi": selected.get("shareClassFIGI") if selected else None,
                "figi_name": selected.get("name") if selected else None,
                "exchange_code": selected.get("exchCode") if selected else None,
                "market_sector": selected.get("marketSector") if selected else None,
                "security_type": selected.get("securityType") if selected else None,
                "security_type2": selected.get("securityType2") if selected else None,
                "mapping_status": status,
                "batch_index": batch_index,
                "source_request_sha256": receipt["request_sha256"],
                "source_response_sha256": receipt["response_sha256"],
                "observed_at": receipt["retrieved_at"],
                "synthetic_data": False,
            }
            row["row_sha256"] = _row_sha256(row)
            normalized.append(row)
    return normalized, batch_receipts


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    smoke._write_atomic(path, output.getvalue().encode())


def _mapping_snapshot(normalized_sha256: str) -> str:
    return f"qqq_openfigi_20260723_{normalized_sha256[:16]}"


def _write_database(
    database_path: Path, snapshot_id: str, rows: list[dict[str, Any]]
) -> dict[str, Any]:
    connection = duckdb.connect(str(database_path))
    inserted = False
    try:
        connection.execute("BEGIN TRANSACTION")
        connection.execute("CREATE SCHEMA IF NOT EXISTS us_equity_research")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS us_equity_research.qqq_security_mapping_research (
                snapshot_id VARCHAR NOT NULL,
                cusip VARCHAR NOT NULL,
                issuer_name VARCHAR NOT NULL,
                security_title VARCHAR NOT NULL,
                symbol VARCHAR,
                figi VARCHAR,
                composite_figi VARCHAR,
                share_class_figi VARCHAR,
                figi_name VARCHAR,
                exchange_code VARCHAR,
                market_sector VARCHAR,
                security_type VARCHAR,
                security_type2 VARCHAR,
                mapping_status VARCHAR NOT NULL,
                batch_index INTEGER NOT NULL,
                source_request_sha256 VARCHAR NOT NULL,
                source_response_sha256 VARCHAR NOT NULL,
                observed_at TIMESTAMPTZ NOT NULL,
                row_sha256 VARCHAR NOT NULL,
                synthetic_data BOOLEAN NOT NULL,
                UNIQUE(snapshot_id, cusip)
            )
            """
        )
        existing = connection.execute(
            f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE snapshot_id=?",
            [snapshot_id],
        ).fetchone()[0]
        if existing not in {0, len(rows)}:
            raise MappingError(f"partial mapping snapshot exists: {existing}")
        if existing == 0:
            values = [
                (
                    snapshot_id,
                    row["cusip"],
                    row["issuer_name"],
                    row["security_title"],
                    row["symbol"],
                    row["figi"],
                    row["composite_figi"],
                    row["share_class_figi"],
                    row["figi_name"],
                    row["exchange_code"],
                    row["market_sector"],
                    row["security_type"],
                    row["security_type2"],
                    row["mapping_status"],
                    row["batch_index"],
                    row["source_request_sha256"],
                    row["source_response_sha256"],
                    row["observed_at"],
                    row["row_sha256"],
                    row["synthetic_data"],
                )
                for row in rows
            ]
            placeholders = ",".join("?" for _ in values[0])
            connection.executemany(
                f"INSERT INTO {TABLE_NAME} VALUES ({placeholders})", values
            )
            inserted = True
        final_count, mapped_count = connection.execute(
            f"SELECT COUNT(*), COUNT(symbol) FROM {TABLE_NAME} WHERE snapshot_id=?",
            [snapshot_id],
        ).fetchone()
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()
    return {
        "database_path": str(database_path),
        "table": TABLE_NAME,
        "snapshot_id": snapshot_id,
        "inserted": inserted,
        "row_count": final_count,
        "mapped_count": mapped_count,
        "transaction_committed": True,
    }


def run(
    repo_root: Path,
    staging_root: Path,
    database_path: Path,
    result_path: Path,
    write_database: bool,
) -> dict[str, Any]:
    failure: str | None = None
    normalized: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    central_write: dict[str, Any] = {
        "attempted": False,
        "transaction_committed": False,
    }
    normalized_path = staging_root / "normalized" / "cusip_mapping.csv"
    try:
        inputs = _input_cusips(database_path)
        normalized, receipts = _normalized_rows(inputs, staging_root)
        _write_csv(normalized_path, normalized)
        normalized_sha = _sha256_file(normalized_path)
        mapped_count = sum(row["symbol"] is not None for row in normalized)
        coverage = mapped_count / len(normalized)
        if coverage < MINIMUM_COVERAGE:
            raise MappingError(
                f"mapping coverage {coverage:.6f} below {MINIMUM_COVERAGE:.6f}"
            )
        if write_database:
            central_write["attempted"] = True
            central_write = _write_database(
                database_path, _mapping_snapshot(normalized_sha), normalized
            )
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        MappingError,
        duckdb.Error,
    ) as exc:
        failure = f"{type(exc).__name__}: {exc}"
    mapped_count = sum(row.get("symbol") is not None for row in normalized)
    coverage = mapped_count / len(normalized) if normalized else 0.0
    qualified = (
        failure is None
        and coverage >= MINIMUM_COVERAGE
        and (not write_database or central_write.get("transaction_committed") is True)
    )
    contract_path = (
        repo_root
        / "research/definitions/us_qqq_disclosed_top50_equal_weight_v1_mapping.json"
    )
    result = {
        "research_id": RESEARCH_ID,
        "execution_id": EXECUTION_ID,
        "date": datetime.now(UTC).date().isoformat(),
        "market": "US",
        "phase": "SECURITY_IDENTITY_MAPPING",
        "current_status": "current" if qualified else "blocked-on-data",
        "result": (
            "SECURITY_MAPPING_QUALIFIED_PRICE_ACQUISITION_AUTHORIZED"
            if qualified
            else "INPUT_BLOCKED"
        ),
        "failure": failure,
        "contract": {
            "path": str(contract_path),
            "sha256": _sha256_file(contract_path),
        },
        "input_snapshot_id": INPUT_SNAPSHOT,
        "counts": {
            "input_cusip_count": len(normalized),
            "mapped_unique_us_composite_count": mapped_count,
            "unmapped_count": len(normalized) - mapped_count,
            "mapping_coverage": coverage,
            "batch_count": len(receipts),
        },
        "batch_receipts": receipts,
        "normalized_artifact": {
            "path": str(normalized_path),
            "sha256": _sha256_file(normalized_path)
            if normalized_path.is_file()
            else None,
            "byte_count": normalized_path.stat().st_size
            if normalized_path.is_file()
            else None,
        },
        "central_database": central_write,
        "quality_gates": {
            "exactly_93_input_cusips": len(normalized) == EXPECTED_CUSIPS,
            "response_count_and_order_match": len(normalized) == EXPECTED_CUSIPS,
            "mapping_coverage_at_least_98_percent": coverage >= MINIMUM_COVERAGE,
            "central_write_committed_if_requested": not write_database
            or central_write.get("transaction_committed") is True,
            "prices_or_returns_accessed": False,
        },
        "research_boundaries": {
            "strategy_candidate_available": False,
            "current_executable_stock_list_output": False,
            "broker_order_paper_live_auto_enabled": False,
        },
        "next_action": (
            "Qualify mapped-symbol daily adjusted price coverage and fill only "
            "missing histories from frozen free sources."
            if qualified
            else "Stop this research identity; do not access prices or returns."
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
            "us_qqq_disclosed_top50_equal_weight_v1/openfigi"
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
            "us_qqq_disclosed_top50_equal_weight_v1_mapping_20260723.json"
        ),
    )
    parser.add_argument("--write-database", action="store_true")
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
        args.write_database,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["result"].startswith("SECURITY_MAPPING_QUALIFIED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
