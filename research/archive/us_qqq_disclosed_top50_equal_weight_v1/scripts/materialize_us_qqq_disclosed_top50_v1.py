"""Materialize all qualified QQQ N-PORT equity snapshots without returns access."""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, date, datetime
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
from typing import Any
import xml.etree.ElementTree as ET

import duckdb


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import smoke_us_qqq_disclosed_top50_v1 as smoke  # noqa: E402


RESEARCH_ID = smoke.RESEARCH_ID
EXECUTION_ID = f"{RESEARCH_ID}_MATERIALIZATION"
MINIMUM_SNAPSHOTS = 24
TABLE_NAME = "us_equity_research.qqq_holdings_pit_research"
SNAPSHOT_PREFIX = "qqq_nport_pit_20260723"


class MaterializationError(RuntimeError):
    """A frozen full materialization gate failed."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _row_sha256(row: dict[str, Any]) -> str:
    material = json.dumps(
        row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    return hashlib.sha256(material).hexdigest()


def _git(repo_root: Path, *arguments: str) -> str:
    return subprocess.run(  # noqa: S603
        ["git", "-C", str(repo_root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _all_nport_filings(submissions: dict[str, Any]) -> list[dict[str, str]]:
    if str(submissions.get("cik", "")).zfill(len(smoke.CIK_PADDED)) != smoke.CIK_PADDED:
        raise MaterializationError("SEC submissions CIK mismatch")
    if submissions.get("name") != smoke.REGISTRANT_NAME:
        raise MaterializationError("SEC submissions registrant name mismatch")
    columns = smoke._recent_columns(submissions)
    rows = [
        {key: str(values[index]) for key, values in columns.items()}
        for index in range(len(columns["form"]))
        if str(columns["form"][index]) == smoke.FORM
    ]
    rows.sort(key=lambda row: (row["reportDate"], row["acceptanceDateTime"]))
    report_dates = [row["reportDate"] for row in rows]
    if len(rows) < MINIMUM_SNAPSHOTS:
        raise MaterializationError(
            f"only {len(rows)} exact NPORT-P snapshots; need {MINIMUM_SNAPSHOTS}"
        )
    if len(report_dates) != len(set(report_dates)):
        raise MaterializationError("duplicate exact NPORT-P report dates")
    return rows


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _first_text(element: ET.Element, name: str) -> str | None:
    for child in element.iter():
        if _local_name(child.tag) == name:
            text = (child.text or "").strip()
            return text or None
    return None


def _identifier_value(position: ET.Element, identifier: str) -> str | None:
    for child in position.iter():
        if _local_name(child.tag) == identifier:
            value = (child.attrib.get("value") or child.text or "").strip()
            return value or None
    return None


def _parse_snapshot(
    raw: bytes,
    filing: dict[str, str],
    source_url: str,
    source_sha256: str,
    observed_at: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise MaterializationError("invalid SEC N-PORT XML") from exc
    report_date = _first_text(root, "repPdDate")
    if report_date != filing["reportDate"]:
        raise MaterializationError(
            f"report date mismatch for {filing['accessionNumber']}"
        )
    accepted_at = filing["acceptanceDateTime"]
    try:
        accepted_date = datetime.fromisoformat(accepted_at.replace("Z", "+00:00")).date()
        period_date = date.fromisoformat(report_date)
    except ValueError as exc:
        raise MaterializationError("invalid report or acceptance date") from exc
    if accepted_date <= period_date:
        raise MaterializationError("acceptance date is not after report date")

    eligible: list[dict[str, Any]] = []
    all_position_count = 0
    for position in root.iter():
        if _local_name(position.tag) != "invstOrSec":
            continue
        all_position_count += 1
        fields = {
            _local_name(child.tag): (child.text or "").strip()
            for child in position
        }
        if (
            fields.get("assetCat") != "EC"
            or fields.get("payoffProfile") != "Long"
            or fields.get("curCd") != "USD"
        ):
            continue
        name = fields.get("name", "")
        title = fields.get("title", "")
        cusip = fields.get("cusip", "")
        try:
            value_usd = float(fields.get("valUSD", ""))
            balance = float(fields.get("balance", ""))
            pct_value = float(fields.get("pctVal", ""))
        except ValueError:
            continue
        if not name or not title or not cusip or value_usd <= 0 or balance < 0:
            continue
        row = {
            "accession_number": filing["accessionNumber"],
            "report_date": report_date,
            "filing_date": filing["filingDate"],
            "accepted_at": accepted_at,
            "issuer_name": name,
            "security_title": title,
            "cusip": cusip,
            "isin": _identifier_value(position, "isin"),
            "balance": balance,
            "units": fields.get("units") or None,
            "value_usd": value_usd,
            "pct_value": pct_value,
            "currency": "USD",
            "asset_category": "EC",
            "payoff_profile": "Long",
            "source_url": source_url,
            "source_document_sha256": source_sha256,
            "observed_at": observed_at,
            "available_at": accepted_at,
            "availability_basis": "SEC_ACCEPTANCE_DATETIME",
            "quality_status": "PASS_SEC_NPORT_PIT_IDENTITY",
            "synthetic_data": False,
        }
        eligible.append(row)
    identities = [(row["cusip"], row["security_title"]) for row in eligible]
    if len(identities) != len(set(identities)):
        raise MaterializationError(
            f"duplicate position identity for {filing['accessionNumber']}"
        )
    eligible.sort(
        key=lambda row: (-row["value_usd"], row["cusip"], row["security_title"])
    )
    if len(eligible) < 50:
        raise MaterializationError(
            f"fewer than 50 eligible equities for {filing['accessionNumber']}"
        )
    for rank, row in enumerate(eligible, start=1):
        row["security_rank"] = rank
        row["is_top50"] = rank <= 50
        row["row_sha256"] = _row_sha256(row)
    summary = {
        "accession_number": filing["accessionNumber"],
        "report_date": report_date,
        "accepted_at": accepted_at,
        "all_position_count": all_position_count,
        "qualified_equity_count": len(eligible),
        "top50_count": sum(row["is_top50"] for row in eligible),
        "duplicate_position_identity_count": 0,
    }
    return summary, eligible


def _cached_source(
    staging_root: Path, smoke_root: Path, filing: dict[str, str], url: str
) -> tuple[Path, dict[str, Any]]:
    filename = f"{filing['reportDate']}_{filing['accessionNumber']}.xml"
    for root in (smoke_root / "raw", staging_root / "raw"):
        path = root / filename
        metadata_path = path.with_suffix(path.suffix + ".metadata.json")
        if path.is_file() and metadata_path.is_file():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if (
                metadata.get("requested_url") == url
                and metadata.get("sha256") == _sha256_file(path)
            ):
                return path, {**metadata, "cache_reused": True}
            raise MaterializationError(f"cached filing identity mismatch: {path}")
    path = staging_root / "raw" / filename
    return path, smoke._download_once(url, path)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise MaterializationError("no normalized holdings rows")
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    smoke._write_atomic(path, output.getvalue().encode())


def _snapshot_id(normalized_sha256: str) -> str:
    return f"{SNAPSHOT_PREFIX}_{normalized_sha256[:16]}"


def _write_central_database(
    database_path: Path, snapshot_id: str, rows: list[dict[str, Any]]
) -> dict[str, Any]:
    connection = duckdb.connect(str(database_path))
    inserted = False
    try:
        connection.execute("BEGIN TRANSACTION")
        connection.execute("CREATE SCHEMA IF NOT EXISTS us_equity_research")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS us_equity_research.qqq_holdings_pit_research (
                snapshot_id VARCHAR NOT NULL,
                accession_number VARCHAR NOT NULL,
                report_date DATE NOT NULL,
                filing_date DATE NOT NULL,
                accepted_at TIMESTAMPTZ NOT NULL,
                issuer_name VARCHAR NOT NULL,
                security_title VARCHAR NOT NULL,
                cusip VARCHAR NOT NULL,
                isin VARCHAR,
                balance DOUBLE NOT NULL,
                units VARCHAR,
                value_usd DOUBLE NOT NULL,
                pct_value DOUBLE NOT NULL,
                currency VARCHAR NOT NULL,
                asset_category VARCHAR NOT NULL,
                payoff_profile VARCHAR NOT NULL,
                security_rank INTEGER NOT NULL,
                is_top50 BOOLEAN NOT NULL,
                source_url VARCHAR NOT NULL,
                source_document_sha256 VARCHAR NOT NULL,
                observed_at TIMESTAMPTZ NOT NULL,
                available_at TIMESTAMPTZ NOT NULL,
                availability_basis VARCHAR NOT NULL,
                quality_status VARCHAR NOT NULL,
                row_sha256 VARCHAR NOT NULL,
                synthetic_data BOOLEAN NOT NULL,
                UNIQUE(snapshot_id, accession_number, cusip, security_title)
            )
            """
        )
        existing = connection.execute(
            f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE snapshot_id = ?",
            [snapshot_id],
        ).fetchone()[0]
        if existing not in {0, len(rows)}:
            raise MaterializationError(
                f"partial central snapshot exists: {existing} of {len(rows)} rows"
            )
        if existing == 0:
            values = [
                (
                    snapshot_id,
                    row["accession_number"],
                    row["report_date"],
                    row["filing_date"],
                    row["accepted_at"],
                    row["issuer_name"],
                    row["security_title"],
                    row["cusip"],
                    row["isin"],
                    row["balance"],
                    row["units"],
                    row["value_usd"],
                    row["pct_value"],
                    row["currency"],
                    row["asset_category"],
                    row["payoff_profile"],
                    row["security_rank"],
                    row["is_top50"],
                    row["source_url"],
                    row["source_document_sha256"],
                    row["observed_at"],
                    row["available_at"],
                    row["availability_basis"],
                    row["quality_status"],
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
        final_count = connection.execute(
            f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE snapshot_id = ?",
            [snapshot_id],
        ).fetchone()[0]
        top50_count = connection.execute(
            f"SELECT COUNT(*) FROM {TABLE_NAME} "
            "WHERE snapshot_id = ? AND is_top50",
            [snapshot_id],
        ).fetchone()[0]
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
        "top50_row_count": top50_count,
        "transaction_committed": True,
    }


def run(
    repo_root: Path,
    staging_root: Path,
    smoke_root: Path,
    database_path: Path,
    result_path: Path,
    write_database: bool,
) -> dict[str, Any]:
    contract_path = (
        repo_root
        / "research/definitions/"
        "us_qqq_disclosed_top50_equal_weight_v1_materialization.json"
    )
    smoke_result_path = (
        repo_root
        / "research/results/"
        "us_qqq_disclosed_top50_equal_weight_v1_sec_smoke_20260723.json"
    )
    failure: str | None = None
    summaries: list[dict[str, Any]] = []
    all_rows: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    normalized_path = staging_root / "normalized" / "qqq_nport_equities.csv"
    central_write: dict[str, Any] = {
        "attempted": False,
        "transaction_committed": False,
    }
    try:
        smoke_result = json.loads(smoke_result_path.read_text(encoding="utf-8"))
        if (
            smoke_result.get("result")
            != "SMOKE_QUALIFIED_FULL_MATERIALIZATION_AUTHORIZED"
        ):
            raise MaterializationError("smoke prerequisite did not qualify")
        submissions_path = smoke_root / "raw" / "qqq_submissions.json"
        submissions_meta_path = submissions_path.with_suffix(
            submissions_path.suffix + ".metadata.json"
        )
        submissions_meta = json.loads(
            submissions_meta_path.read_text(encoding="utf-8")
        )
        if submissions_meta.get("sha256") != _sha256_file(submissions_path):
            raise MaterializationError("smoke submissions source hash mismatch")
        submissions = json.loads(submissions_path.read_text(encoding="utf-8"))
        filings = _all_nport_filings(submissions)
        for filing in filings:
            url = smoke._filing_url(filing)
            path, metadata = _cached_source(staging_root, smoke_root, filing, url)
            sources.append(
                {
                    "report_date": filing["reportDate"],
                    "accession_number": filing["accessionNumber"],
                    "path": str(path),
                    "url": url,
                    "sha256": metadata["sha256"],
                    "byte_count": metadata["byte_count"],
                }
            )
            summary, rows = _parse_snapshot(
                path.read_bytes(),
                filing,
                url,
                metadata["sha256"],
                metadata["retrieved_at"],
            )
            summaries.append(summary)
            all_rows.extend(rows)
        if len(summaries) < MINIMUM_SNAPSHOTS:
            raise MaterializationError("full snapshot count below frozen minimum")
        if any(summary["top50_count"] != 50 for summary in summaries):
            raise MaterializationError("one or more snapshots lack exactly 50 top rows")
        _write_csv(normalized_path, all_rows)
        normalized_sha = _sha256_file(normalized_path)
        snapshot_id = _snapshot_id(normalized_sha)
        if write_database:
            central_write["attempted"] = True
            central_write = _write_central_database(
                database_path, snapshot_id, all_rows
            )
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        MaterializationError,
        duckdb.Error,
    ) as exc:
        failure = f"{type(exc).__name__}: {exc}"

    qualified = (
        failure is None
        and len(summaries) >= MINIMUM_SNAPSHOTS
        and all(summary["top50_count"] == 50 for summary in summaries)
        and (not write_database or central_write.get("transaction_committed") is True)
    )
    normalized_sha = _sha256_file(normalized_path) if normalized_path.is_file() else None
    result = {
        "research_id": RESEARCH_ID,
        "execution_id": EXECUTION_ID,
        "date": datetime.now(UTC).date().isoformat(),
        "market": "US",
        "phase": "PIT_INPUT_MATERIALIZATION",
        "current_status": "current" if qualified else "blocked-on-data",
        "result": (
            "PIT_HOLDINGS_MATERIALIZED_PRICE_MAPPING_REQUIRED"
            if qualified
            else "INPUT_BLOCKED"
        ),
        "failure": failure,
        "repository": {
            "branch": _git(repo_root, "branch", "--show-current"),
            "head": _git(repo_root, "rev-parse", "HEAD"),
            "tree": _git(repo_root, "rev-parse", "HEAD^{tree}"),
            "status_short": _git(
                repo_root, "status", "--short", "--untracked-files=all"
            ).splitlines(),
        },
        "contract": {
            "path": str(contract_path),
            "sha256": _sha256_file(contract_path),
        },
        "smoke_prerequisite": {
            "path": str(smoke_result_path),
            "sha256": _sha256_file(smoke_result_path),
        },
        "input_counts": {
            "snapshot_count": len(summaries),
            "qualified_equity_row_count": len(all_rows),
            "top50_row_count": sum(
                summary["top50_count"] for summary in summaries
            ),
            "unique_top50_cusip_count": len(
                {
                    row["cusip"]
                    for row in all_rows
                    if row.get("is_top50") is True
                }
            ),
        },
        "snapshot_summaries_without_security_names": summaries,
        "source_documents": sources,
        "normalized_artifact": {
            "path": str(normalized_path),
            "sha256": normalized_sha,
            "byte_count": normalized_path.stat().st_size
            if normalized_path.is_file()
            else None,
        },
        "central_database": central_write,
        "quality_gates": {
            "at_least_24_exact_nport_p_snapshots": len(summaries)
            >= MINIMUM_SNAPSHOTS,
            "at_least_50_qualified_equities_each": qualified
            and all(
                summary["qualified_equity_count"] >= 50 for summary in summaries
            ),
            "exactly_50_top50_rows_each": qualified
            and all(summary["top50_count"] == 50 for summary in summaries),
            "no_duplicate_position_identity": qualified
            and all(
                summary["duplicate_position_identity_count"] == 0
                for summary in summaries
            ),
            "central_write_committed_if_requested": not write_database
            or central_write.get("transaction_committed") is True,
            "returns_or_strategy_outcomes_accessed": False,
        },
        "research_boundaries": {
            "strategy_candidate_available": False,
            "portfolio_constructed": False,
            "current_executable_stock_list_output": False,
            "broker_order_paper_live_auto_enabled": False,
        },
        "next_action": (
            "Resolve CUSIP-to-symbol identity, qualify central daily prices, and "
            "stop before returns if coverage is below 98%."
            if qualified
            else "Stop this research identity; do not access returns or relax gates."
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
            "us_qqq_disclosed_top50_equal_weight_v1/sec_full"
        ),
    )
    parser.add_argument(
        "--smoke-root",
        type=Path,
        default=Path(
            "/home/rongyu/workspace/quant-data/staging/"
            "us_qqq_disclosed_top50_equal_weight_v1/sec_smoke"
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
            "us_qqq_disclosed_top50_equal_weight_v1_materialization_20260723.json"
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
        args.smoke_root.resolve(),
        args.database.resolve(),
        result_path,
        args.write_database,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["result"].startswith("PIT_HOLDINGS_MATERIALIZED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
