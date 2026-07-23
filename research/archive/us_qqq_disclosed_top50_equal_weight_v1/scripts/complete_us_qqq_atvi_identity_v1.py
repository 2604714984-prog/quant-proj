"""Complete the single frozen ATVI identity gap from a historical SEC filing."""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any

import duckdb

import continue_us_qqq_top50_mapping_v1 as continuation
import smoke_us_qqq_disclosed_top50_v1 as smoke


RESEARCH_ID = smoke.RESEARCH_ID
EXECUTION_ID = f"{RESEARCH_ID}_ATVI_IDENTITY_COMPLETION"
INPUT_SHA256 = (
    "664c42e40d2c7280c8f528c3db10bc4a975b90c898890a8d1e39e37d3e4ab5d5"
)
CUSIP = "00507V109"
ISSUER = "Activision Blizzard, Inc."
TITLE = "Activision Blizzard, Inc."
SYMBOL = "ATVI"
SOURCE_URL = (
    "https://www.sec.gov/Archives/edgar/data/718877/"
    "000071887719000015/atvi-6302019x10xq.htm"
)


class CompletionError(RuntimeError):
    """The exact one-security identity completion failed."""


def _validate_source(raw: bytes) -> None:
    text = raw.decode("utf-8", errors="replace")
    text = re.sub(r"<[^>]+>", " ", text)
    text = " ".join(text.upper().split())
    required = (
        "ACTIVISION BLIZZARD",
        "ATVI",
        "NASDAQ GLOBAL SELECT MARKET",
    )
    missing = [value for value in required if value not in text]
    if missing:
        raise CompletionError(f"SEC identity text missing: {missing}")


def run(
    repo_root: Path,
    staging_root: Path,
    database_path: Path,
    result_path: Path,
) -> dict[str, Any]:
    input_path = (
        staging_root.parent
        / "mapping_continuation/normalized/final_cusip_mapping.csv"
    )
    contract_path = (
        repo_root
        / "research/definitions/"
        "us_qqq_disclosed_top50_equal_weight_v1_atvi_completion.json"
    )
    failure: str | None = None
    central: dict[str, Any] = {"attempted": False, "transaction_committed": False}
    completed_path = staging_root / "normalized" / "complete_cusip_mapping.csv"
    source_path = staging_root / "raw" / "atvi_2019_10q.htm"
    rows: list[dict[str, Any]] = []
    try:
        if continuation._sha256_file(input_path) != INPUT_SHA256:
            raise CompletionError("input mapping hash mismatch")
        metadata = smoke._download_once(SOURCE_URL, source_path)
        _validate_source(source_path.read_bytes())
        source_rows = list(csv.DictReader(input_path.open()))
        matches = [
            row
            for row in source_rows
            if row["cusip"] == CUSIP
            and row["issuer_name"] == ISSUER
            and row["security_title"] == TITLE
            and not row["symbol"]
        ]
        if len(matches) != 1:
            raise CompletionError(f"expected one exact ATVI gap, found {len(matches)}")
        for source in source_rows:
            row = dict(source)
            for key in ("yahoo_name_score", "yahoo_name_margin"):
                row[key] = float(row[key]) if row.get(key) else None
            if source is matches[0]:
                row.update(
                    {
                        "symbol": SYMBOL,
                        "figi_name": "ACTIVISION BLIZZARD INC",
                        "exchange_code": "NASDAQ",
                        "market_sector": "Equity",
                        "security_type": "Common Stock",
                        "security_type2": "Common Stock",
                        "mapping_status": "MAPPED_SEC_HISTORICAL_TRADING_SYMBOL",
                        "mapping_source": "SEC_10Q_COVER_PAGE",
                        "yahoo_name_score": None,
                        "yahoo_name_margin": None,
                        "source_response_sha256": metadata["sha256"],
                        "observed_at": metadata["retrieved_at"],
                    }
                )
            row["synthetic_data"] = False
            row["row_sha256"] = continuation._hash_value(
                {key: value for key, value in row.items() if key != "row_sha256"}
            )
            rows.append(row)
        mapped_count = sum(bool(row["symbol"]) for row in rows)
        if len(rows) != 93 or mapped_count != 93:
            raise CompletionError(f"incomplete final mapping: {mapped_count}/{len(rows)}")
        continuation._write_csv(completed_path, rows)
        normalized_sha = continuation._sha256_file(completed_path)
        central["attempted"] = True
        central = continuation._write_database(
            database_path,
            f"qqq_identity_complete_20260723_{normalized_sha[:16]}",
            rows,
        )
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        CompletionError,
        duckdb.Error,
    ) as exc:
        failure = f"{type(exc).__name__}: {exc}"
    mapped_count = sum(bool(row.get("symbol")) for row in rows)
    qualified = (
        failure is None
        and len(rows) == 93
        and mapped_count == 93
        and central.get("transaction_committed") is True
    )
    result = {
        "research_id": RESEARCH_ID,
        "execution_id": EXECUTION_ID,
        "date": datetime.now(UTC).date().isoformat(),
        "market": "US",
        "phase": "SINGLE_SECURITY_IDENTITY_COMPLETION",
        "current_status": "current" if qualified else "blocked-on-data",
        "result": (
            "SECURITY_MAPPING_COMPLETE_PRICE_ACQUISITION_AUTHORIZED"
            if qualified
            else "INPUT_BLOCKED"
        ),
        "failure": failure,
        "contract": {
            "path": str(contract_path),
            "sha256": continuation._sha256_file(contract_path),
        },
        "source": {
            "url": SOURCE_URL,
            "path": str(source_path),
            "sha256": continuation._sha256_file(source_path)
            if source_path.is_file()
            else None,
        },
        "counts": {
            "input_count": len(rows),
            "mapped_count": mapped_count,
            "unmapped_count": len(rows) - mapped_count,
        },
        "normalized_artifact": {
            "path": str(completed_path),
            "sha256": continuation._sha256_file(completed_path)
            if completed_path.is_file()
            else None,
        },
        "central_database": central,
        "quality_gates": {
            "exact_atvi_gap_completed": qualified,
            "all_93_cusips_mapped": qualified,
            "central_write_committed": central.get("transaction_committed") is True,
            "prices_or_returns_accessed": False,
        },
        "research_boundaries": {
            "strategy_candidate_available": False,
            "current_executable_stock_list_output": False,
            "broker_order_paper_live_auto_enabled": False,
        },
        "next_action": (
            "Qualify and fill adjusted daily prices for the complete mapped universe."
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
            "us_qqq_disclosed_top50_equal_weight_v1/atvi_completion"
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
            "us_qqq_disclosed_top50_equal_weight_v1_atvi_completion_20260723.json"
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
    return 0 if result["result"].startswith("SECURITY_MAPPING_COMPLETE") else 2


if __name__ == "__main__":
    raise SystemExit(main())
