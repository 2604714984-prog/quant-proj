"""Outcome-free SEC smoke for QQQ disclosed top-50 equity snapshots."""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, date, datetime
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import time
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
import zlib


RESEARCH_ID = "US_QQQ_DISCLOSED_TOP50_EQUAL_WEIGHT_V1"
EXECUTION_ID = f"{RESEARCH_ID}_SEC_SMOKE"
CIK_PADDED = "0001067839"
CIK_ARCHIVE = "1067839"
REGISTRANT_NAME = "INVESCO QQQ TRUST, SERIES 1"
FORM = "NPORT-P"
SAMPLE_REPORT_DATES = (
    "2019-12-31",
    "2021-12-31",
    "2023-12-31",
    "2024-12-31",
    "2025-12-31",
)
SUBMISSIONS_URL = f"https://data.sec.gov/submissions/CIK{CIK_PADDED}.json"
USER_AGENT = "QuantProjResearch 2604714984@qq.com"
MINIMUM_RECENT_FILINGS = 24
MAXIMUM_RESPONSE_BYTES = 50 * 1024 * 1024
REQUEST_INTERVAL_SECONDS = 0.75


class SmokeError(RuntimeError):
    """A frozen input qualification gate failed."""


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _write_atomic(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    with temporary.open("wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _write_json_atomic(path: Path, value: Any) -> None:
    raw = (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        + "\n"
    ).encode()
    _write_atomic(path, raw)


def _decode_body(raw: bytes, encoding: str) -> bytes:
    normalized = encoding.lower().strip()
    if not normalized:
        return raw
    if normalized == "gzip":
        return gzip.decompress(raw)
    if normalized == "deflate":
        try:
            return zlib.decompress(raw)
        except zlib.error:
            return zlib.decompress(raw, -zlib.MAX_WBITS)
    raise SmokeError(f"unsupported Content-Encoding: {encoding}")


def _download_once(url: str, destination: Path) -> dict[str, Any]:
    metadata_path = destination.with_suffix(destination.suffix + ".metadata.json")
    if destination.is_file() and metadata_path.is_file():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        actual_sha = _sha256_file(destination)
        if metadata.get("requested_url") != url or metadata.get("sha256") != actual_sha:
            raise SmokeError(f"cached source identity mismatch: {destination}")
        return {**metadata, "cache_reused": True}
    if destination.exists() or metadata_path.exists():
        raise SmokeError(f"incomplete cached source state: {destination}")

    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in {"www.sec.gov", "data.sec.gov"}:
        raise SmokeError(f"non-SEC source rejected: {url}")
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json, application/xml, text/xml;q=0.9",
        },
    )
    time.sleep(REQUEST_INTERVAL_SECONDS)
    with urlopen(request, timeout=45) as response:  # noqa: S310
        status = int(response.status)
        headers = {key.lower(): value for key, value in response.headers.items()}
        wire = response.read(MAXIMUM_RESPONSE_BYTES + 1)
        final_url = response.geturl()
    if status != 200:
        raise SmokeError(f"SEC HTTP status {status}: {url}")
    if len(wire) > MAXIMUM_RESPONSE_BYTES:
        raise SmokeError(f"SEC response exceeds byte limit: {url}")
    body = _decode_body(wire, headers.get("content-encoding", ""))
    if len(body) > MAXIMUM_RESPONSE_BYTES:
        raise SmokeError(f"decoded SEC response exceeds byte limit: {url}")
    metadata = {
        "requested_url": url,
        "final_url": final_url,
        "retrieved_at": _utc_now(),
        "http_status": status,
        "request_user_agent": USER_AGENT,
        "content_type": headers.get("content-type"),
        "content_encoding": headers.get("content-encoding"),
        "response_date": headers.get("date"),
        "byte_count": len(body),
        "sha256": _sha256_bytes(body),
        "automatic_retry_count": 0,
        "success": True,
    }
    _write_atomic(destination, body)
    _write_json_atomic(metadata_path, metadata)
    return {**metadata, "cache_reused": False}


def _recent_columns(submissions: dict[str, Any]) -> dict[str, list[Any]]:
    try:
        recent = submissions["filings"]["recent"]
    except (KeyError, TypeError) as exc:
        raise SmokeError("SEC submissions feed lacks filings.recent") from exc
    if not isinstance(recent, dict):
        raise SmokeError("SEC submissions filings.recent is not an object")
    required = (
        "accessionNumber",
        "acceptanceDateTime",
        "filingDate",
        "form",
        "primaryDocument",
        "reportDate",
    )
    columns: dict[str, list[Any]] = {}
    for key in required:
        value = recent.get(key)
        if not isinstance(value, list):
            raise SmokeError(f"SEC submissions recent column missing: {key}")
        columns[key] = value
    lengths = {len(value) for value in columns.values()}
    if len(lengths) != 1:
        raise SmokeError("SEC submissions recent columns have inconsistent lengths")
    return columns


def _select_filings(submissions: dict[str, Any]) -> tuple[list[dict[str, str]], int]:
    if str(submissions.get("cik", "")).zfill(len(CIK_PADDED)) != CIK_PADDED:
        raise SmokeError("SEC submissions CIK mismatch")
    if submissions.get("name") != REGISTRANT_NAME:
        raise SmokeError("SEC submissions registrant name mismatch")
    columns = _recent_columns(submissions)
    rows = [
        {key: str(values[index]) for key, values in columns.items()}
        for index in range(len(columns["form"]))
    ]
    nport_rows = [row for row in rows if row["form"] == FORM]
    selected: list[dict[str, str]] = []
    for report_date in SAMPLE_REPORT_DATES:
        matches = [row for row in nport_rows if row["reportDate"] == report_date]
        if len(matches) != 1:
            raise SmokeError(
                f"expected one {FORM} filing for {report_date}, found {len(matches)}"
            )
        selected.append(matches[0])
    return selected, len(nport_rows)


def _filing_url(filing: dict[str, str]) -> str:
    accession = filing["accessionNumber"].replace("-", "")
    document = Path(filing["primaryDocument"]).name
    if not accession.isdigit() or document != "primary_doc.xml":
        raise SmokeError("unexpected SEC accession or primary document identity")
    return (
        f"https://www.sec.gov/Archives/edgar/data/{CIK_ARCHIVE}/"
        f"{accession}/{document}"
    )


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _first_text(element: ET.Element, name: str) -> str | None:
    for child in element.iter():
        if _local_name(child.tag) == name:
            text = (child.text or "").strip()
            return text or None
    return None


def _parse_xml_snapshot(
    raw: bytes, filing: dict[str, str]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise SmokeError("invalid SEC N-PORT XML") from exc
    report_date = _first_text(root, "repPdDate")
    if report_date != filing["reportDate"]:
        raise SmokeError(
            f"N-PORT report date mismatch: {report_date} != {filing['reportDate']}"
        )
    accepted_at = filing["acceptanceDateTime"]
    try:
        accepted_date = datetime.fromisoformat(accepted_at.replace("Z", "+00:00")).date()
        period_date = date.fromisoformat(report_date)
    except ValueError as exc:
        raise SmokeError("invalid SEC availability or report date") from exc
    if accepted_date <= period_date:
        raise SmokeError("SEC accepted_at is not strictly after report date")

    qualified: list[dict[str, Any]] = []
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
        except ValueError:
            continue
        if not name or not title or not cusip or value_usd <= 0:
            continue
        qualified.append(
            {
                "accession_number": filing["accessionNumber"],
                "report_date": report_date,
                "accepted_at": accepted_at,
                "filing_date": filing["filingDate"],
                "name": name,
                "title": title,
                "cusip": cusip,
                "value_usd": value_usd,
                "currency": "USD",
                "asset_category": "EC",
                "payoff_profile": "Long",
            }
        )
    identities = [(row["cusip"], row["title"]) for row in qualified]
    duplicate_count = len(identities) - len(set(identities))
    if duplicate_count:
        raise SmokeError(f"duplicate CUSIP/title identities: {duplicate_count}")
    qualified.sort(key=lambda row: (-row["value_usd"], row["cusip"], row["title"]))
    if len(qualified) < 50:
        raise SmokeError(f"fewer than 50 qualified equities: {len(qualified)}")
    top50 = qualified[:50]
    summary = {
        "report_date": report_date,
        "filing_date": filing["filingDate"],
        "accepted_at": accepted_at,
        "accession_number": filing["accessionNumber"],
        "all_position_count": all_position_count,
        "qualified_equity_count": len(qualified),
        "unique_qualified_identity_count": len(set(identities)),
        "duplicate_qualified_identity_count": duplicate_count,
        "top50_count": len(top50),
        "top50_total_filed_value_usd": sum(row["value_usd"] for row in top50),
        "minimum_top50_filed_value_usd": min(row["value_usd"] for row in top50),
    }
    return summary, top50


def _write_top50_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    _write_atomic(path, output.getvalue().encode())


def run(repo_root: Path, staging_root: Path, result_path: Path) -> dict[str, Any]:
    contract_path = (
        repo_root
        / "research/definitions/us_qqq_disclosed_top50_equal_weight_v1_smoke.json"
    )
    raw_root = staging_root / "raw"
    normalized_root = staging_root / "normalized"
    source_artifacts: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []
    failure: str | None = None
    recent_nport_count = 0
    try:
        submissions_path = raw_root / "qqq_submissions.json"
        submissions_meta = _download_once(SUBMISSIONS_URL, submissions_path)
        source_artifacts.append(
            {
                "path": str(submissions_path),
                "sha256": submissions_meta["sha256"],
                "byte_count": submissions_meta["byte_count"],
                "requested_url": SUBMISSIONS_URL,
            }
        )
        submissions = json.loads(submissions_path.read_text(encoding="utf-8"))
        selected, recent_nport_count = _select_filings(submissions)
        if recent_nport_count < MINIMUM_RECENT_FILINGS:
            raise SmokeError(
                f"only {recent_nport_count} recent NPORT-P filings; "
                f"need {MINIMUM_RECENT_FILINGS}"
            )
        for filing in selected:
            url = _filing_url(filing)
            xml_path = raw_root / f"{filing['reportDate']}_{filing['accessionNumber']}.xml"
            xml_meta = _download_once(url, xml_path)
            source_artifacts.append(
                {
                    "path": str(xml_path),
                    "sha256": xml_meta["sha256"],
                    "byte_count": xml_meta["byte_count"],
                    "requested_url": url,
                }
            )
            summary, top50 = _parse_xml_snapshot(xml_path.read_bytes(), filing)
            csv_path = normalized_root / f"{filing['reportDate']}_top50.csv"
            _write_top50_csv(csv_path, top50)
            summary["normalized_top50_path"] = str(csv_path)
            summary["normalized_top50_sha256"] = _sha256_file(csv_path)
            snapshots.append(summary)
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        SmokeError,
    ) as exc:
        failure = f"{type(exc).__name__}: {exc}"

    qualified = failure is None and len(snapshots) == len(SAMPLE_REPORT_DATES)
    result = {
        "research_id": RESEARCH_ID,
        "execution_id": EXECUTION_ID,
        "date": datetime.now(UTC).date().isoformat(),
        "market": "US",
        "phase": "INPUT_QUALIFICATION_SMOKE",
        "current_status": "current" if qualified else "blocked-on-data",
        "result": (
            "SMOKE_QUALIFIED_FULL_MATERIALIZATION_AUTHORIZED"
            if qualified
            else "INPUT_BLOCKED"
        ),
        "failure": failure,
        "contract": {
            "path": str(contract_path),
            "sha256": _sha256_file(contract_path),
        },
        "repository": {
            "branch": os.popen(f"git -C {repo_root} branch --show-current").read().strip(),
            "head": os.popen(f"git -C {repo_root} rev-parse HEAD").read().strip(),
            "tree": os.popen(f"git -C {repo_root} rev-parse HEAD^{{tree}}").read().strip(),
        },
        "input_counts": {
            "recent_nport_p_filings": recent_nport_count,
            "frozen_sample_count": len(SAMPLE_REPORT_DATES),
            "qualified_sample_count": len(snapshots),
        },
        "source_artifacts": source_artifacts,
        "snapshot_summaries_without_security_names": snapshots,
        "quality_gates": {
            "registrant_identity_exact": recent_nport_count > 0,
            "at_least_24_recent_nport_p_filings": recent_nport_count
            >= MINIMUM_RECENT_FILINGS,
            "five_frozen_filings_qualified": qualified,
            "at_least_50_qualified_equities_each": qualified
            and all(item["qualified_equity_count"] >= 50 for item in snapshots),
            "unique_security_identities_each": qualified
            and all(
                item["duplicate_qualified_identity_count"] == 0 for item in snapshots
            ),
            "report_and_acceptance_dates_distinct": qualified,
            "central_database_connection_or_write_attempted": False,
            "returns_or_strategy_outcomes_accessed": False,
        },
        "research_boundaries": {
            "strategy_candidate_available": False,
            "portfolio_constructed": False,
            "current_executable_stock_list_output": False,
            "broker_order_paper_live_auto_enabled": False,
        },
        "next_action": (
            "Materialize all qualified NPORT-P snapshots and perform CUSIP-to-price "
            "mapping qualification."
            if qualified
            else "Stop this research identity; do not access returns or relax gates."
        ),
    }
    _write_json_atomic(result_path, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--staging-root",
        type=Path,
        default=Path(
            "/home/rongyu/workspace/quant-data/staging/"
            "us_qqq_disclosed_top50_equal_weight_v1/sec_smoke"
        ),
    )
    parser.add_argument(
        "--result",
        type=Path,
        default=Path(
            "research/results/"
            "us_qqq_disclosed_top50_equal_weight_v1_sec_smoke_20260723.json"
        ),
    )
    args = parser.parse_args()
    result = run(
        args.repo_root.resolve(),
        args.staging_root.resolve(),
        (args.repo_root / args.result).resolve()
        if not args.result.is_absolute()
        else args.result.resolve(),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["result"].startswith("SMOKE_QUALIFIED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
