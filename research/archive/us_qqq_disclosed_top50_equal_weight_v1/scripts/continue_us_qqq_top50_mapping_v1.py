"""Outcome-free continuation for the 11 unresolved QQQ CUSIP identities."""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
from difflib import SequenceMatcher
import hashlib
import io
import json
from pathlib import Path
import re
import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import duckdb

import map_us_qqq_top50_cusips_v1 as initial
import smoke_us_qqq_disclosed_top50_v1 as smoke


RESEARCH_ID = smoke.RESEARCH_ID
EXECUTION_ID = f"{RESEARCH_ID}_MAPPING_CONTINUATION"
FAILED_RESULT_SHA256 = (
    "6635e13528bf92d3e9992e715626549a46e647c4e6ec96daf5bd48f483e66679"
)
INITIAL_MAPPING_SHA256 = (
    "4b83939437b7fd0d1c35111e421b450cfb21dd91ade22f4653c4756503b31fa6"
)
MINIMUM_MAPPED = 92
YAHOO_SEARCH = "https://query2.finance.yahoo.com/v1/finance/search"
ALLOWED_EXCHANGES = {"NMS", "NYQ", "NGM", "NCM", "NAS", "PNK"}
TABLE_NAME = initial.TABLE_NAME


class ContinuationError(RuntimeError):
    """A frozen continuation identity gate failed."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_value(value: Any) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    return hashlib.sha256(raw).hexdigest()


LEGAL_TOKENS = {
    "A",
    "CLASS",
    "CORP",
    "CORPORATION",
    "GROUP",
    "HOLDING",
    "HOLDINGS",
    "INC",
    "INCORPORATED",
    "LIMITED",
    "LTD",
    "NEW",
    "NV",
    "PLC",
}


def _normalize_name(value: str) -> str:
    normalized = value.upper().replace("&", " AND ")
    normalized = re.sub(r"[^A-Z0-9]+", " ", normalized)
    return " ".join(token for token in normalized.split() if token not in LEGAL_TOKENS)


def _openfigi_results(raw_root: Path) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for batch_index in range(1, 11):
        request_path = raw_root / f"batch_{batch_index:02d}.request.json"
        response_path = raw_root / f"batch_{batch_index:02d}.response.json"
        jobs = json.loads(request_path.read_text(encoding="utf-8"))
        responses = json.loads(response_path.read_text(encoding="utf-8"))
        if len(jobs) != len(responses):
            raise ContinuationError("preserved OpenFIGI job/response count mismatch")
        for job, response in zip(jobs, responses, strict=True):
            results[str(job["idValue"])] = {
                "response": response,
                "source_response_sha256": _sha256_file(response_path),
                "batch_index": batch_index,
            }
    return results


def _unique_us_venue(
    response: dict[str, Any],
) -> tuple[str, dict[str, Any] | None]:
    data = response.get("data")
    if not isinstance(data, list):
        return "NO_US_VENUE_MATCH", None
    candidates: dict[tuple[Any, ...], dict[str, Any]] = {}
    for item in data:
        exchange = str(item.get("exchCode", ""))
        if (
            isinstance(item, dict)
            and exchange.startswith("U")
            and exchange != "US"
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
        return "NO_US_VENUE_MATCH", None
    if len(candidates) != 1:
        return "AMBIGUOUS_US_VENUE_MATCH", None
    return "MAPPED_UNIQUE_OPENFIGI_US_VENUE", next(iter(candidates.values()))


def _central_exact_name(
    connection: duckdb.DuckDBPyConnection, issuer_name: str
) -> tuple[str, dict[str, Any] | None]:
    target = _normalize_name(issuer_name)
    candidates = connection.execute(
        """
        SELECT DISTINCT symbol, name
        FROM us_equity_research.nasdaq_security_metadata_research
        WHERE symbol IS NOT NULL AND name IS NOT NULL
        """
    ).fetchall()
    exact = sorted(
        {(str(symbol), str(name)) for symbol, name in candidates if _normalize_name(name) == target}
    )
    if not exact:
        return "NO_CENTRAL_EXACT_NAME", None
    if len(exact) != 1:
        return "AMBIGUOUS_CENTRAL_EXACT_NAME", None
    symbol, name = exact[0]
    return "MAPPED_CENTRAL_EXACT_NAME", {
        "ticker": symbol,
        "name": name,
        "exchCode": None,
        "marketSector": "Equity",
        "securityType": "Common Stock",
        "securityType2": "Common Stock",
        "figi": None,
        "compositeFIGI": None,
        "shareClassFIGI": None,
    }


def _download_yahoo_search(
    cusip: str, issuer_name: str, raw_root: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    params = {
        "q": issuer_name,
        "quotesCount": 10,
        "newsCount": 0,
        "enableFuzzyQuery": "false",
    }
    url = f"{YAHOO_SEARCH}?{urlencode(params)}"
    body_path = raw_root / f"{cusip}.json"
    metadata_path = raw_root / f"{cusip}.metadata.json"
    if body_path.is_file() and metadata_path.is_file():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if (
            metadata.get("requested_url") != url
            or metadata.get("sha256") != _sha256_file(body_path)
        ):
            raise ContinuationError(f"cached Yahoo identity mismatch: {cusip}")
        return json.loads(body_path.read_text(encoding="utf-8")), {
            **metadata,
            "cache_reused": True,
        }
    if body_path.exists() or metadata_path.exists():
        raise ContinuationError(f"incomplete Yahoo cache: {cusip}")
    request = Request(
        url,
        headers={
            "User-Agent": smoke.USER_AGENT,
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        },
    )
    time.sleep(1.0)
    with urlopen(request, timeout=30) as response:  # noqa: S310
        status = int(response.status)
        raw = response.read(5 * 1024 * 1024 + 1)
    if status != 200 or len(raw) > 5 * 1024 * 1024:
        raise ContinuationError(f"Yahoo search response failure: {cusip}")
    payload = json.loads(raw)
    metadata = {
        "requested_url": url,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "http_status": status,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "byte_count": len(raw),
        "automatic_retry_count": 0,
        "price_or_return_fields_read": False,
    }
    smoke._write_atomic(body_path, raw)
    smoke._write_json_atomic(metadata_path, metadata)
    return payload, {**metadata, "cache_reused": False}


def _select_yahoo(
    payload: dict[str, Any], issuer_name: str
) -> tuple[str, dict[str, Any] | None, float | None, float | None]:
    target = _normalize_name(issuer_name)
    candidates: list[tuple[float, str, dict[str, Any]]] = []
    for quote in payload.get("quotes") or []:
        if (
            not isinstance(quote, dict)
            or quote.get("quoteType") != "EQUITY"
            or quote.get("exchange") not in ALLOWED_EXCHANGES
            or not quote.get("symbol")
        ):
            continue
        names = [
            str(quote.get(key))
            for key in ("longname", "shortname")
            if quote.get(key)
        ]
        if not names:
            continue
        score = max(
            SequenceMatcher(None, target, _normalize_name(name)).ratio()
            for name in names
        )
        candidates.append((score, str(quote["symbol"]), {"names": names, **{
            "ticker": quote["symbol"],
            "name": names[0],
            "exchCode": quote.get("exchange"),
            "marketSector": "Equity",
            "securityType": "Equity",
            "securityType2": "Common Stock",
            "figi": None,
            "compositeFIGI": None,
            "shareClassFIGI": None,
        }}))
    candidates.sort(key=lambda item: (-item[0], item[1]))
    if not candidates:
        return "NO_YAHOO_MATCH", None, None, None
    best_score, _, best = candidates[0]
    second_score = candidates[1][0] if len(candidates) > 1 else 0.0
    margin = best_score - second_score
    if best_score < 0.75 or margin < 0.15:
        return "AMBIGUOUS_YAHOO_MATCH", None, best_score, margin
    return "MAPPED_YAHOO_UNIQUE_NAME", best, best_score, margin


def _resolved_rows(
    initial_rows: list[dict[str, str]],
    openfigi: dict[str, dict[str, Any]],
    database_path: Path,
    staging_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    connection = duckdb.connect(str(database_path), read_only=True)
    counts: dict[str, int] = {}
    output: list[dict[str, Any]] = []
    try:
        for source in initial_rows:
            selected: dict[str, Any] | None = None
            status = source["mapping_status"]
            source_kind = "OPENFIGI_US_COMPOSITE"
            response_sha = source["source_response_sha256"]
            yahoo_score: float | None = None
            yahoo_margin: float | None = None
            if source["symbol"]:
                selected = {
                    "ticker": source["symbol"],
                    "name": source["figi_name"],
                    "exchCode": source["exchange_code"],
                    "marketSector": source["market_sector"],
                    "securityType": source["security_type"],
                    "securityType2": source["security_type2"],
                    "figi": source["figi"],
                    "compositeFIGI": source["composite_figi"],
                    "shareClassFIGI": source["share_class_figi"],
                }
            else:
                preserved = openfigi[source["cusip"]]
                status, selected = _unique_us_venue(preserved["response"])
                response_sha = preserved["source_response_sha256"]
                source_kind = "OPENFIGI_US_VENUE"
                if selected is None:
                    status, selected = _central_exact_name(
                        connection, source["issuer_name"]
                    )
                    source_kind = "CENTRAL_EXACT_NAME"
                    if selected is not None:
                        response_sha = _hash_value(selected)
                if selected is None:
                    payload, metadata = _download_yahoo_search(
                        source["cusip"],
                        source["issuer_name"],
                        staging_root / "yahoo_search",
                    )
                    status, selected, yahoo_score, yahoo_margin = _select_yahoo(
                        payload, source["issuer_name"]
                    )
                    source_kind = "YAHOO_NAME_SEARCH"
                    response_sha = metadata["sha256"]
            counts[source_kind] = counts.get(source_kind, 0) + 1
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
                "mapping_source": source_kind,
                "yahoo_name_score": yahoo_score,
                "yahoo_name_margin": yahoo_margin,
                "source_response_sha256": response_sha,
                "observed_at": datetime.now(UTC).isoformat(),
                "synthetic_data": False,
            }
            row["row_sha256"] = _hash_value(row)
            output.append(row)
    finally:
        connection.close()
    return output, counts


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    smoke._write_atomic(path, output.getvalue().encode())


def _write_database(
    database_path: Path, snapshot_id: str, rows: list[dict[str, Any]]
) -> dict[str, Any]:
    connection = duckdb.connect(str(database_path))
    inserted = False
    try:
        connection.execute("BEGIN TRANSACTION")
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
                mapping_source VARCHAR NOT NULL,
                yahoo_name_score DOUBLE,
                yahoo_name_margin DOUBLE,
                source_response_sha256 VARCHAR NOT NULL,
                observed_at TIMESTAMPTZ NOT NULL,
                row_sha256 VARCHAR NOT NULL,
                synthetic_data BOOLEAN NOT NULL,
                UNIQUE(snapshot_id, cusip)
            )
            """
        )
        existing = connection.execute(
            f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE snapshot_id=?", [snapshot_id]
        ).fetchone()[0]
        if existing not in {0, len(rows)}:
            raise ContinuationError(f"partial mapping snapshot exists: {existing}")
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
                    row["mapping_source"],
                    row["yahoo_name_score"],
                    row["yahoo_name_margin"],
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
        row_count, mapped_count = connection.execute(
            f"SELECT COUNT(*),COUNT(symbol) FROM {TABLE_NAME} WHERE snapshot_id=?",
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
        "row_count": row_count,
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
    failed_result = (
        repo_root
        / "research/results/us_qqq_disclosed_top50_equal_weight_v1_mapping_20260723.json"
    )
    initial_csv = (
        staging_root.parent / "openfigi/normalized/cusip_mapping.csv"
    )
    failure: str | None = None
    rows: list[dict[str, Any]] = []
    source_counts: dict[str, int] = {}
    central: dict[str, Any] = {"attempted": False, "transaction_committed": False}
    normalized_path = staging_root / "normalized" / "final_cusip_mapping.csv"
    try:
        if _sha256_file(failed_result) != FAILED_RESULT_SHA256:
            raise ContinuationError("preserved failed mapping result changed")
        if _sha256_file(initial_csv) != INITIAL_MAPPING_SHA256:
            raise ContinuationError("preserved initial mapping CSV changed")
        initial_rows = list(csv.DictReader(initial_csv.open()))
        openfigi = _openfigi_results(staging_root.parent / "openfigi/raw")
        rows, source_counts = _resolved_rows(
            initial_rows, openfigi, database_path, staging_root
        )
        mapped_count = sum(row["symbol"] is not None for row in rows)
        if mapped_count < MINIMUM_MAPPED:
            raise ContinuationError(
                f"only {mapped_count} of {len(rows)} CUSIPs mapped"
            )
        _write_csv(normalized_path, rows)
        normalized_sha = _sha256_file(normalized_path)
        if write_database:
            central["attempted"] = True
            central = _write_database(
                database_path,
                f"qqq_identity_20260723_{normalized_sha[:16]}",
                rows,
            )
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        ContinuationError,
        duckdb.Error,
    ) as exc:
        failure = f"{type(exc).__name__}: {exc}"
    mapped_count = sum(row.get("symbol") is not None for row in rows)
    qualified = (
        failure is None
        and mapped_count >= MINIMUM_MAPPED
        and (not write_database or central.get("transaction_committed") is True)
    )
    contract = (
        repo_root
        / "research/definitions/"
        "us_qqq_disclosed_top50_equal_weight_v1_mapping_continuation.json"
    )
    result = {
        "research_id": RESEARCH_ID,
        "execution_id": EXECUTION_ID,
        "date": datetime.now(UTC).date().isoformat(),
        "market": "US",
        "phase": "SECURITY_IDENTITY_MAPPING_CONTINUATION",
        "current_status": "current" if qualified else "blocked-on-data",
        "result": (
            "SECURITY_MAPPING_QUALIFIED_PRICE_ACQUISITION_AUTHORIZED"
            if qualified
            else "INPUT_BLOCKED"
        ),
        "failure": failure,
        "contract": {"path": str(contract), "sha256": _sha256_file(contract)},
        "preserved_failed_route": {
            "path": str(failed_result),
            "sha256": _sha256_file(failed_result),
        },
        "counts": {
            "input_cusip_count": len(rows),
            "mapped_count": mapped_count,
            "unmapped_count": len(rows) - mapped_count,
            "mapping_coverage": mapped_count / len(rows) if rows else 0.0,
            "mapping_sources": source_counts,
        },
        "normalized_artifact": {
            "path": str(normalized_path),
            "sha256": _sha256_file(normalized_path)
            if normalized_path.is_file()
            else None,
            "byte_count": normalized_path.stat().st_size
            if normalized_path.is_file()
            else None,
        },
        "central_database": central,
        "quality_gates": {
            "failed_route_preserved": _sha256_file(failed_result)
            == FAILED_RESULT_SHA256,
            "at_least_92_of_93_mapped": mapped_count >= MINIMUM_MAPPED,
            "central_write_committed_if_requested": not write_database
            or central.get("transaction_committed") is True,
            "price_or_return_fields_read": False,
        },
        "research_boundaries": {
            "strategy_candidate_available": False,
            "current_executable_stock_list_output": False,
            "broker_order_paper_live_auto_enabled": False,
        },
        "next_action": (
            "Qualify mapped-symbol adjusted daily price coverage."
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
            "us_qqq_disclosed_top50_equal_weight_v1/mapping_continuation"
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
            "us_qqq_disclosed_top50_equal_weight_v1_mapping_continuation_20260723.json"
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
