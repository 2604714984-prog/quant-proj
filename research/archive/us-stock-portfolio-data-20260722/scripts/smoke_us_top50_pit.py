"""Smoke SEC inputs needed for the frozen dynamic historical US Top-50 universe.

The script downloads only bounded official JSON responses into WSL staging.  It
does not rank securities, emit constituents, open DuckDB, or compute returns.
SEC frames are tested only as coverage-discovery inputs; they are not promoted
to PIT observations because the frames contract is last-filed by entity.
"""

from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from typing import Any

from smoke_us_stock_data import (
    SmokeError,
    _request,
    _sha256,
    _strict_json,
    _utc_now,
    _write_json,
)


CONTRACT_SHA256 = "ebd3c4aa7a250befa5e3327daed1c7def9cd19ef26005e2612300456e851263c"
SEC_FRAME_BASE = "https://data.sec.gov/api/xbrl/frames/dei"
SEC_TICKER_EXCHANGE_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
PUBLIC_FLOAT_PERIODS = ("CY2018Q2I", "CY2020Q2I", "CY2022Q2I", "CY2024Q2I")
SHARES_PERIODS = ("CY2018Q4I", "CY2020Q4I", "CY2022Q4I", "CY2024Q4I")


def _finite_positive(value: Any) -> bool:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return False
    return parsed.is_finite() and parsed > 0


def _fetch_json(
    *, staging: Path, document_id: str, url: str
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    metadata, raw = _request(
        url=url,
        destination=staging / "sec" / f"{document_id}.json",
    )
    if metadata["http_status"] != 200:
        return None, metadata
    return _strict_json(raw, document_id), metadata


def _frame_summary(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
        raise SmokeError("SEC frame returned malformed data rows")
    ciks = [str(row.get("cik")) for row in data]
    forms = sorted({str(row.get("form")) for row in data if row.get("form")})
    filed_dates = sorted(str(row["filed"]) for row in data if row.get("filed"))
    end_dates = sorted(str(row["end"]) for row in data if row.get("end"))
    accepted_fields = sum(
        any(key.lower().startswith("accept") for key in row) for row in data
    )
    class_identity_fields = sum(
        any(
            key in row
            for key in (
                "ticker",
                "tradingSymbol",
                "shareClass",
                "securityTitle",
                "security_id",
            )
        )
        for row in data
    )
    positive_values = sum(_finite_positive(row.get("val")) for row in data)
    return {
        "taxonomy": payload.get("taxonomy"),
        "tag": payload.get("tag"),
        "unit": payload.get("uom"),
        "row_count": len(data),
        "unique_cik_count": len(set(ciks)),
        "duplicate_cik_rows": len(ciks) - len(set(ciks)),
        "positive_value_rows": positive_values,
        "invalid_or_nonpositive_value_rows": len(data) - positive_values,
        "forms": forms,
        "min_filed_date": filed_dates[0] if filed_dates else None,
        "max_filed_date": filed_dates[-1] if filed_dates else None,
        "min_fact_end_date": end_dates[0] if end_dates else None,
        "max_fact_end_date": end_dates[-1] if end_dates else None,
        "rows_with_acceptance_timestamp_field": accepted_fields,
        "rows_with_share_class_identity_field": class_identity_fields,
    }


def _ticker_map_summary(payload: dict[str, Any]) -> dict[str, Any]:
    fields = payload.get("fields")
    data = payload.get("data")
    if (
        not isinstance(fields, list)
        or not all(isinstance(field, str) for field in fields)
        or not isinstance(data, list)
        or any(not isinstance(row, list) or len(row) != len(fields) for row in data)
    ):
        raise SmokeError("SEC ticker-exchange map returned malformed rows")
    field_index = {field: index for index, field in enumerate(fields)}
    required = {"cik", "name", "ticker", "exchange"}
    if not required.issubset(field_index):
        raise SmokeError("SEC ticker-exchange map is missing required fields")
    business_keys = [
        (
            str(row[field_index["cik"]]),
            str(row[field_index["ticker"]]),
            str(row[field_index["exchange"]]),
        )
        for row in data
    ]
    exchanges = sorted(
        {str(row[field_index["exchange"]]) for row in data if row[field_index["exchange"]]}
    )
    return {
        "fields": fields,
        "row_count": len(data),
        "unique_business_keys": len(set(business_keys)),
        "duplicate_business_keys": len(business_keys) - len(set(business_keys)),
        "exchanges": exchanges,
        "historical_effective_date_field_present": any(
            field.lower() in {"effective_date", "start_date", "end_date", "available_at"}
            for field in fields
        ),
        "share_class_identifier_field_present": any(
            field.lower() in {"share_class", "security_id", "cusip", "figi"}
            for field in fields
        ),
    }


def run(contract_path: Path, staging: Path) -> dict[str, Any]:
    contract_raw = contract_path.read_bytes()
    contract = _strict_json(contract_raw, "Top-50 data contract")
    contract_sha256 = _sha256(contract_raw)
    if contract_sha256 != CONTRACT_SHA256:
        raise SmokeError(
            f"contract identity mismatch: expected={CONTRACT_SHA256} actual={contract_sha256}"
        )

    documents: list[dict[str, Any]] = []
    response_failures: list[dict[str, Any]] = []
    public_float_frames: dict[str, dict[str, Any]] = {}
    shares_frames: dict[str, dict[str, Any]] = {}

    for period in PUBLIC_FLOAT_PERIODS:
        document_id = f"entity_public_float_{period}"
        payload, metadata = _fetch_json(
            staging=staging,
            document_id=document_id,
            url=f"{SEC_FRAME_BASE}/EntityPublicFloat/USD/{period}.json",
        )
        documents.append(metadata)
        if payload is None:
            response_failures.append(
                {
                    "document_id": document_id,
                    "http_status": metadata["http_status"],
                    "transport_error": metadata.get("transport_error"),
                }
            )
        else:
            public_float_frames[period] = _frame_summary(payload)

    for period in SHARES_PERIODS:
        document_id = f"common_shares_outstanding_{period}"
        payload, metadata = _fetch_json(
            staging=staging,
            document_id=document_id,
            url=(
                f"{SEC_FRAME_BASE}/EntityCommonStockSharesOutstanding/shares/"
                f"{period}.json"
            ),
        )
        documents.append(metadata)
        if payload is None:
            response_failures.append(
                {
                    "document_id": document_id,
                    "http_status": metadata["http_status"],
                    "transport_error": metadata.get("transport_error"),
                }
            )
        else:
            shares_frames[period] = _frame_summary(payload)

    ticker_payload, ticker_metadata = _fetch_json(
        staging=staging,
        document_id="company_tickers_exchange_current",
        url=SEC_TICKER_EXCHANGE_URL,
    )
    documents.append(ticker_metadata)
    ticker_summary: dict[str, Any] | None = None
    if ticker_payload is None:
        response_failures.append(
            {
                "document_id": "company_tickers_exchange_current",
                "http_status": ticker_metadata["http_status"],
                "transport_error": ticker_metadata.get("transport_error"),
            }
        )
    else:
        ticker_summary = _ticker_map_summary(ticker_payload)

    all_frames = [*public_float_frames.values(), *shares_frames.values()]
    frame_rows = sum(int(summary["row_count"]) for summary in all_frames)
    accepted_timestamp_rows = sum(
        int(summary["rows_with_acceptance_timestamp_field"]) for summary in all_frames
    )
    class_identity_rows = sum(
        int(summary["rows_with_share_class_identity_field"]) for summary in all_frames
    )
    gates = {
        "official_response_contract": {
            "pass": not response_failures,
            "requested_documents": 9,
            "successful_documents": 9 - len(response_failures),
            "failures": response_failures,
        },
        "frame_values_finite_positive": {
            "pass": bool(all_frames)
            and all(summary["invalid_or_nonpositive_value_rows"] == 0 for summary in all_frames),
            "frame_rows": frame_rows,
            "invalid_or_nonpositive_rows": sum(
                int(summary["invalid_or_nonpositive_value_rows"])
                for summary in all_frames
            ),
        },
        "exact_source_available_at": {
            "pass": frame_rows > 0 and accepted_timestamp_rows == frame_rows,
            "frame_rows": frame_rows,
            "rows_with_acceptance_timestamp": accepted_timestamp_rows,
            "reason": "Frame rows expose filed dates but not exact accession acceptance timestamps.",
        },
        "security_share_class_identity": {
            "pass": frame_rows > 0 and class_identity_rows == frame_rows,
            "frame_rows": frame_rows,
            "rows_with_share_class_identity": class_identity_rows,
            "reason": "Entity frames do not identify a tradable share class for security-level capitalization.",
        },
        "survivor_aware_ticker_era_map": {
            "pass": bool(ticker_summary)
            and bool(ticker_summary["historical_effective_date_field_present"]),
            "reason": "The bounded SEC ticker-exchange file is a current map without historical effective dates.",
        },
        "permanent_security_identifier": {
            "pass": bool(ticker_summary)
            and bool(ticker_summary["share_class_identifier_field_present"]),
            "reason": "The bounded SEC ticker-exchange file has issuer CIK but no permanent share-class identifier.",
        },
        "dynamic_pit_top50_reconstructible": {
            "pass": False,
            "reason": "Exact accepted_at, historical ticker eras, and class-level shares are not jointly available from these bounded endpoints.",
        },
    }
    blocking_failures = sorted(name for name, gate in gates.items() if not gate["pass"])
    result = {
        "research_id": contract["research_id"],
        "universe_identity": contract["universe_identity"]["identity"],
        "phase": "top50_pit_source_smoke",
        "status": "SMOKE_PASS" if not blocking_failures else "SMOKE_FAIL",
        "current": True,
        "strategy_candidate_available": False,
        "contract_path": str(contract_path),
        "contract_sha256": contract_sha256,
        "market_cap_basis": "TOTAL_MARKET_CAP",
        "adr_policy": "EXCLUDE",
        "qualified_start_date": None,
        "public_float_frames": public_float_frames,
        "shares_outstanding_frames": shares_frames,
        "ticker_exchange_map": ticker_summary,
        "gates": gates,
        "blocking_failures": blocking_failures,
        "source_documents": documents,
        "central_database_opened": False,
        "central_database_write": False,
        "top50_constituents_computed": False,
        "top50_constituents_emitted": False,
        "return_computation": False,
        "signal_computation": False,
        "portfolio_computation": False,
        "boundary_result": "PIT_INPUT_SMOKE_ONLY_NO_RANKING_NO_CENTRAL_WRITE",
    }
    _write_json(staging / "smoke_result.json", result)
    _write_json(
        staging / "source_manifest.json",
        {
            "generated_at": _utc_now(),
            "source_documents": documents,
            "raw_document_count": len(documents),
            "raw_byte_count": sum(int(document["byte_count"]) for document in documents),
        },
    )
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path("research/definitions/us_stock_top50_data_contract_v2.json"),
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
            "phase": "top50_pit_source_smoke",
            "status": "SMOKE_FAIL",
            "strategy_candidate_available": False,
            "blocking_failures": ["source_response_contract"],
            "fatal_error": f"{type(exc).__name__}: {exc}",
            "central_database_opened": False,
            "central_database_write": False,
            "top50_constituents_computed": False,
            "boundary_result": "PIT_INPUT_SMOKE_ONLY_NO_RANKING_NO_CENTRAL_WRITE",
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
