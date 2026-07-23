"""One-shot, outcome-free SEC N-PORT 2025 Q1 bulk ZIP feasibility smoke.

The script resolves exactly one quarterly link from the official SEC data page,
downloads exactly that ZIP with no retries, and streams only the target XLG
relations. Raw data and filtered rows stay under the WSL data-root staging area.
It never imports or opens DuckDB and never reads market returns.
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import UTC, datetime
import hashlib
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import Any, BinaryIO, Iterator
from urllib.error import HTTPError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
import zipfile


EXECUTION_ID = "SEC_NPORT_BULK_ZIP_V1_SMOKE_2025Q1"
CONTRACT_SHA256 = "23fd3dcb235fdd58e390f5a737359e4cf3f1afcfdd444e7e8aadf695e7d2d761"
LANDING_URL = "https://www.sec.gov/data-research/sec-markets-data/form-n-port-data-sets"
TARGET_ANCHOR = "2025 Q1"
SERIES_ID = "S000060793"
CLASS_ID = "C000197609"
USER_AGENT = "quant-proj-research/2.0 (+https://github.com/2604714984-prog/quant-proj)"
MAX_LANDING_BYTES = 10 * 1024 * 1024
MAX_ZIP_BYTES = 800 * 1024 * 1024
CHUNK_BYTES = 1024 * 1024
PROGRESS_BYTES = 64 * 1024 * 1024
OLD_RESULTS = {
    "research/results/us_stock_top50_input_blocked_20260722.json": (
        "36d0581465ea37d26d695bfaa4e1ca1efbc190880b44148058cd30ba712d0877"
    ),
    "research/results/us_sp500_top50_xlg_disclosed_universe_v1_input_blocked_20260722.json": (
        "f7da25e80b6f9aefaab59b74086fcd98f9f8d16265bdfa1b26f7461cf93d58a6"
    ),
}

ACCESSION_FIELDS = ("ACCESSION_NUMBER", "ACCESSION_NO", "ACCESSIONNUMBER")
SERIES_FIELDS = ("SERIES_ID", "SERIESID")
CLASS_FIELDS = ("CLASS_ID", "CLASSID", "CONTRACT_ID", "CLASS_CONTRACT_ID")
REPORT_FIELDS = (
    "REPORT_DATE",
    "REPORT_ENDING_PERIOD",
    "REPORT_PERIOD",
    "REPORT_PERIOD_END_DATE",
)
FILING_FIELDS = ("FILING_DATE", "FILED_DATE")
ACCEPTED_FIELDS = (
    "ACCEPTED_AT",
    "ACCEPTANCE_DATETIME",
    "ACCEPTANCE_DATE_TIME",
    "PUBLIC_DISSEMINATION_DATETIME",
    "PUBLIC_DISSEMINATION_TIME",
)
HOLDING_ID_FIELDS = ("HOLDING_ID", "HOLDINGID", "POSITION_ID", "INVESTMENT_ID")
ISSUER_FIELDS = ("ISSUER_NAME", "NAME", "ISSUER")
TITLE_FIELDS = ("ISSUER_TITLE", "TITLE", "SECURITY_TITLE")
CUSIP_FIELDS = ("ISSUER_CUSIP", "CUSIP")
ASSET_FIELDS = ("ASSET_CAT", "ASSET_CATEGORY", "INSTRUMENT_TYPE")
BALANCE_FIELDS = ("BALANCE", "QUANTITY")
VALUE_FIELDS = ("CURRENCY_VALUE", "VALUE", "FAIR_VALUE")
CURRENCY_FIELDS = ("CURRENCY_CODE", "CURRENCY")


class SmokeError(RuntimeError):
    """A frozen acquisition or schema gate failed."""


class _AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._href: str | None = None
        self._text: list[str] = []
        self.anchors: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a" or self._href is not None:
            return
        values = {key.lower(): value for key, value in attrs}
        href = values.get("href")
        if href:
            self._href = href
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((" ".join("".join(self._text).split()), self._href))
            self._href = None
            self._text = []


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    raw = (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        + "\n"
    ).encode()
    with temporary.open("wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SmokeError(f"invalid staged JSON: {path}") from exc
    if not isinstance(value, dict):
        raise SmokeError(f"staged JSON root is not an object: {path}")
    return value


def _verify_guard(path: Path, expected_sha256: str) -> dict[str, Any]:
    if not path.is_file():
        raise SmokeError(f"guarded file missing: {path}")
    actual = _sha256_file(path)
    if actual != expected_sha256:
        raise SmokeError(f"guarded file SHA256 changed: {path}")
    stat = path.stat()
    return {
        "path": str(path),
        "sha256": actual,
        "byte_count": stat.st_size,
        "inode": stat.st_ino,
    }


def _git_text(repo_root: Path, *arguments: str) -> str:
    completed = subprocess.run(  # noqa: S603
        ["git", "-C", str(repo_root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.rstrip("\n")


def _capture_repo_identity(repo_root: Path) -> dict[str, Any]:
    return {
        "worktree": str(repo_root.resolve()),
        "branch": _git_text(repo_root, "branch", "--show-current"),
        "head": _git_text(repo_root, "rev-parse", "HEAD"),
        "tree": _git_text(repo_root, "rev-parse", "HEAD^{tree}"),
        "status_short": _git_text(
            repo_root, "status", "--short", "--branch", "--untracked-files=all"
        ).splitlines(),
    }


def _capture_db_identity(path: Path) -> dict[str, Any]:
    resolved = path.resolve(strict=True)
    stat = resolved.stat()
    lsof = subprocess.run(  # noqa: S603
        ["lsof", "-t", "--", str(resolved)],
        check=False,
        capture_output=True,
        text=True,
    )
    if lsof.returncode not in {0, 1}:
        raise SmokeError(f"lsof failed for canonical DB with exit {lsof.returncode}")
    wal = Path(f"{resolved}.wal")
    wal_identity: dict[str, Any] | None = None
    if wal.exists():
        wal_stat = wal.stat()
        wal_identity = {
            "path": str(wal),
            "device": wal_stat.st_dev,
            "inode": wal_stat.st_ino,
            "size": wal_stat.st_size,
            "mtime_ns": wal_stat.st_mtime_ns,
            "sha256": _sha256_file(wal),
        }
    return {
        "path": str(resolved),
        "device": stat.st_dev,
        "device_hex": format(stat.st_dev, "x"),
        "inode": stat.st_ino,
        "mode_octal": format(stat.st_mode & 0o7777, "o"),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "ctime_ns": stat.st_ctime_ns,
        "sha256": _sha256_file(resolved),
        "wal": wal_identity,
        "openers": sorted(set(lsof.stdout.split())),
        "database_connection_opened": False,
        "file_read_for_identity_hash_only": True,
    }


def _db_unchanged(before: dict[str, Any], after: dict[str, Any]) -> bool:
    keys = ("path", "device", "inode", "mode_octal", "size", "mtime_ns", "sha256", "wal")
    return all(before.get(key) == after.get(key) for key in keys)


def _parse_content_length(headers: dict[str, str]) -> int | None:
    value = headers.get("content-length")
    if value is None:
        return None
    try:
        parsed = int(value)
    except ValueError as exc:
        raise SmokeError(f"invalid Content-Length: {value!r}") from exc
    if parsed < 0:
        raise SmokeError(f"negative Content-Length: {parsed}")
    return parsed


def _download_once(
    *, url: str, destination: Path, accept: str, maximum_bytes: int, timeout: float
) -> dict[str, Any]:
    metadata_path = destination.with_suffix(destination.suffix + ".metadata.json")
    if metadata_path.exists():
        metadata = _read_json(metadata_path)
        if metadata.get("requested_url") != url:
            raise SmokeError(f"staged request URL collision: {metadata_path}")
        if metadata.get("success"):
            if not destination.is_file():
                raise SmokeError(f"successful staged body missing: {destination}")
            actual_sha = _sha256_file(destination)
            if metadata.get("sha256") != actual_sha:
                raise SmokeError(f"staged body SHA256 mismatch: {destination}")
            if metadata.get("byte_count") != destination.stat().st_size:
                raise SmokeError(f"staged body byte count mismatch: {destination}")
        return {**metadata, "cache_reused": True}
    if destination.exists() or destination.with_suffix(destination.suffix + ".part").exists():
        raise SmokeError(f"unaccounted staged download path exists: {destination}")

    request = Request(url, headers={"Accept": accept, "User-Agent": USER_AGENT}, method="GET")
    retrieved_at = _utc_now()
    response: BinaryIO | None = None
    status: int | None = None
    final_url: str | None = None
    headers: dict[str, str] = {}
    transport_error: str | None = None
    failure: str | None = None
    sha256: str | None = None
    byte_count = 0
    temporary = destination.with_suffix(destination.suffix + ".part")

    try:
        try:
            response = urlopen(request, timeout=timeout)  # noqa: S310
        except HTTPError as exc:
            response = exc
        status_value = getattr(response, "status", None) or getattr(response, "code", None)
        status = int(status_value) if status_value is not None else None
        final_url = str(response.geturl())
        headers = {str(key).lower(): str(value) for key, value in response.headers.items()}
        content_length = _parse_content_length(headers)
        if content_length is not None and content_length > maximum_bytes:
            failure = f"content_length_exceeds_limit:{content_length}>{maximum_bytes}"
        elif status is None or not 200 <= status < 300:
            failure = f"http_status_not_success:{status}"
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256()
            next_progress = PROGRESS_BYTES
            with temporary.open("xb") as handle:
                while chunk := response.read(CHUNK_BYTES):
                    byte_count += len(chunk)
                    if byte_count > maximum_bytes:
                        failure = f"stream_exceeds_limit:{byte_count}>{maximum_bytes}"
                        break
                    handle.write(chunk)
                    digest.update(chunk)
                    if byte_count >= next_progress:
                        print(f"downloaded_bytes={byte_count}", flush=True)
                        next_progress += PROGRESS_BYTES
                handle.flush()
                os.fsync(handle.fileno())
            if failure is None:
                sha256 = digest.hexdigest()
                os.replace(temporary, destination)
            elif temporary.exists():
                temporary.unlink()
    except OSError as exc:
        transport_error = f"{type(exc).__name__}: {exc}"
        failure = "transport_error"
        if temporary.exists():
            temporary.unlink()
    finally:
        if response is not None:
            response.close()

    metadata = {
        "requested_url": url,
        "retrieved_at": retrieved_at,
        "http_status": status,
        "final_url": final_url,
        "response_headers": headers,
        "content_length": _parse_content_length(headers) if headers else None,
        "content_type": headers.get("content-type"),
        "byte_count": byte_count,
        "sha256": sha256,
        "body_path": str(destination) if sha256 else None,
        "maximum_bytes": maximum_bytes,
        "request_user_agent": USER_AGENT,
        "retry_count": 0,
        "transport_error": transport_error,
        "failure": failure,
        "success": failure is None and sha256 is not None,
    }
    _write_json_atomic(metadata_path, metadata)
    return {**metadata, "cache_reused": False}


def _parse_quarter_link(raw_html: bytes, base_url: str = LANDING_URL) -> str:
    parser = _AnchorParser()
    try:
        parser.feed(raw_html.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise SmokeError("SEC landing page is not UTF-8 HTML") from exc
    matches = [urljoin(base_url, href) for text, href in parser.anchors if text == TARGET_ANCHOR]
    if len(matches) != 1:
        raise SmokeError(f"expected one exact {TARGET_ANCHOR!r} anchor, found {len(matches)}")
    resolved = matches[0]
    parsed = urlparse(resolved)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not (host == "sec.gov" or host.endswith(".sec.gov")):
        raise SmokeError(f"quarter link is not SEC-hosted HTTPS: {resolved}")
    return resolved


def _normalize_field(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", value.strip().upper()).strip("_")


def _first_present(columns: list[str] | tuple[str, ...], candidates: tuple[str, ...]) -> str | None:
    available = set(columns)
    return next((candidate for candidate in candidates if candidate in available), None)


def _safe_zip_members(infos: list[zipfile.ZipInfo]) -> list[str]:
    failures: list[str] = []
    names = [info.filename for info in infos]
    duplicates = sorted(name for name, count in Counter(names).items() if count > 1)
    if duplicates:
        failures.append(f"duplicate_member_names:{len(duplicates)}")
    for info in infos:
        path = PurePosixPath(info.filename)
        if path.is_absolute() or ".." in path.parts:
            failures.append(f"unsafe_member_path:{info.filename}")
        if info.flag_bits & 0x1:
            failures.append(f"encrypted_member:{info.filename}")
    return failures


def _decode_header(raw: bytes) -> tuple[str, list[str]]:
    try:
        text = raw.decode("utf-8-sig").rstrip("\r\n")
    except UnicodeDecodeError:
        text = raw.decode("latin-1").rstrip("\r\n")
    candidates = ("\t", "|", ",")
    delimiter = max(candidates, key=text.count)
    if text.count(delimiter) == 0:
        raise SmokeError("table header has no recognized delimiter")
    columns = next(csv.reader([text], delimiter=delimiter))
    normalized = [_normalize_field(column) for column in columns]
    if not all(normalized) or len(normalized) != len(set(normalized)):
        raise SmokeError("table header has blank or duplicate normalized columns")
    return delimiter, normalized


def _schema_inventory(archive: zipfile.ZipFile) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    for info in archive.infolist():
        suffix = PurePosixPath(info.filename).suffix.lower()
        item: dict[str, Any] = {
            "member": info.filename,
            "compressed_bytes": info.compress_size,
            "uncompressed_bytes": info.file_size,
            "crc32": f"{info.CRC:08x}",
            "is_dir": info.is_dir(),
        }
        if not info.is_dir() and suffix in {".tsv", ".txt", ".csv"}:
            try:
                with archive.open(info, "r") as handle:
                    raw = handle.readline(2 * 1024 * 1024)
                delimiter, columns = _decode_header(raw)
                item["delimiter"] = {"\t": "tab", "|": "pipe", ",": "comma"}[delimiter]
                item["columns"] = columns
            except (OSError, RuntimeError, SmokeError, zipfile.BadZipFile) as exc:
                item["header_error"] = f"{type(exc).__name__}: {exc}"
        inventory.append(item)
    return inventory


def _table_candidates(
    inventory: list[dict[str, Any]], required_any: tuple[tuple[str, ...], ...]
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for item in inventory:
        columns = item.get("columns")
        if not isinstance(columns, list):
            continue
        if all(_first_present(columns, group) is not None for group in required_any):
            matches.append(item)
    return matches


def _delimiter_value(item: dict[str, Any]) -> str:
    values = {"tab": "\t", "pipe": "|", "comma": ","}
    try:
        return values[str(item["delimiter"])]
    except KeyError as exc:
        raise SmokeError(f"unsupported delimiter for {item.get('member')}") from exc


def _iter_member_rows(
    archive: zipfile.ZipFile, item: dict[str, Any]
) -> Iterator[dict[str, str]]:
    delimiter = _delimiter_value(item)
    with archive.open(str(item["member"]), "r") as raw_handle:
        text_handle = io.TextIOWrapper(raw_handle, encoding="utf-8-sig", newline="")
        reader = csv.DictReader(text_handle, delimiter=delimiter)
        if reader.fieldnames is None:
            raise SmokeError(f"missing header in {item['member']}")
        raw_fields = list(reader.fieldnames)
        normalized = [_normalize_field(field) for field in raw_fields]
        if not all(normalized) or len(normalized) != len(set(normalized)):
            raise SmokeError(f"invalid normalized header in {item['member']}")
        for raw_row in reader:
            yield {
                normalized[index]: str(raw_row.get(raw_field) or "").strip()
                for index, raw_field in enumerate(raw_fields)
            }


def _write_filtered_rows(path: Path, rows: list[dict[str, str]]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    with temporary.open("wb") as handle:
        for row in rows:
            raw = (
                json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n"
            ).encode()
            handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    return {
        "path": str(path),
        "row_count": len(rows),
        "byte_count": path.stat().st_size,
        "sha256": _sha256_file(path),
    }


def _value(row: dict[str, str], candidates: tuple[str, ...]) -> str:
    field = _first_present(tuple(row), candidates)
    return row.get(field, "") if field else ""


def _collect_target_rows(
    archive: zipfile.ZipFile,
    inventory: list[dict[str, Any]],
    filtered_root: Path,
) -> dict[str, Any]:
    identity_tables = _table_candidates(inventory, (ACCESSION_FIELDS, SERIES_FIELDS))
    class_tables = _table_candidates(inventory, (ACCESSION_FIELDS, CLASS_FIELDS))
    if not identity_tables:
        raise SmokeError("no accession-plus-series relation in ZIP schema")
    if not class_tables:
        raise SmokeError("no accession-plus-class relation in ZIP schema")

    series_rows: list[dict[str, str]] = []
    class_rows: list[dict[str, str]] = []
    source_members: dict[str, list[str]] = {"series": [], "class": []}
    for item in identity_tables:
        matched = [
            row for row in _iter_member_rows(archive, item) if _value(row, SERIES_FIELDS) == SERIES_ID
        ]
        if matched:
            source_members["series"].append(str(item["member"]))
            series_rows.extend(matched)
    for item in class_tables:
        matched = [
            row for row in _iter_member_rows(archive, item) if _value(row, CLASS_FIELDS) == CLASS_ID
        ]
        if matched:
            source_members["class"].append(str(item["member"]))
            class_rows.extend(matched)
    series_accessions = {_value(row, ACCESSION_FIELDS) for row in series_rows}
    class_accessions = {_value(row, ACCESSION_FIELDS) for row in class_rows}
    target_accessions = sorted((series_accessions & class_accessions) - {""})
    if not target_accessions:
        raise SmokeError("series and class did not resolve to a common accession")

    relation_artifacts = {
        "series": _write_filtered_rows(filtered_root / "series_rows.jsonl", series_rows),
        "class": _write_filtered_rows(filtered_root / "class_rows.jsonl", class_rows),
    }

    submission_tables = _table_candidates(inventory, (ACCESSION_FIELDS, REPORT_FIELDS))
    if not submission_tables:
        raise SmokeError("no accession-plus-report-period submission relation")
    submission_rows: list[dict[str, str]] = []
    submission_members: list[str] = []
    for item in submission_tables:
        matched = [
            row
            for row in _iter_member_rows(archive, item)
            if _value(row, ACCESSION_FIELDS) in target_accessions
        ]
        if matched:
            submission_members.append(str(item["member"]))
            submission_rows.extend(matched)
    if not submission_rows:
        raise SmokeError("target accession has no submission/report row")
    relation_artifacts["submission"] = _write_filtered_rows(
        filtered_root / "submission_rows.jsonl", submission_rows
    )

    holding_tables = _table_candidates(
        inventory,
        (
            ACCESSION_FIELDS,
            HOLDING_ID_FIELDS,
            ISSUER_FIELDS,
            ASSET_FIELDS,
            BALANCE_FIELDS,
            VALUE_FIELDS,
            CURRENCY_FIELDS,
        ),
    )
    if not holding_tables:
        raise SmokeError("no holding relation with the frozen required field groups")
    holding_rows: list[dict[str, str]] = []
    holding_members: list[str] = []
    for item in holding_tables:
        print(f"scan_holding_member={item['member']}", flush=True)
        matched = [
            row
            for row in _iter_member_rows(archive, item)
            if _value(row, ACCESSION_FIELDS) in target_accessions
        ]
        if matched:
            holding_members.append(str(item["member"]))
            holding_rows.extend(matched)
    if not holding_rows:
        raise SmokeError("target accession has no holdings rows")
    relation_artifacts["holdings"] = _write_filtered_rows(
        filtered_root / "holding_rows.jsonl", holding_rows
    )

    accepted_fields = sorted(
        {
            field
            for row in submission_rows
            for field in ACCEPTED_FIELDS
            if field in row and row[field]
        }
    )
    report_dates = sorted({_value(row, REPORT_FIELDS) for row in submission_rows} - {""})
    filing_dates = sorted({_value(row, FILING_FIELDS) for row in submission_rows} - {""})
    accepted_values = sorted({row[field] for row in submission_rows for field in accepted_fields})

    holding_keys = [
        (_value(row, ACCESSION_FIELDS), _value(row, HOLDING_ID_FIELDS)) for row in holding_rows
    ]
    missing_holding_ids = sum(not holding_id for _, holding_id in holding_keys)
    duplicate_keys = sum(count - 1 for count in Counter(holding_keys).values() if count > 1)
    asset_categories = Counter(_value(row, ASSET_FIELDS).upper() or "<BLANK>" for row in holding_rows)
    ordinary_rows = [row for row in holding_rows if _value(row, ASSET_FIELDS).upper() == "EC"]
    company_keys: set[str] = set()
    for row in ordinary_rows:
        cusip = re.sub(r"[^A-Z0-9]", "", _value(row, CUSIP_FIELDS).upper())
        issuer = re.sub(r"[^A-Z0-9]", "", _value(row, ISSUER_FIELDS).upper())
        company_keys.add(f"CUSIP6:{cusip[:6]}" if len(cusip) >= 6 else f"ISSUER:{issuer}")
    company_keys.discard("ISSUER:")

    gates = {
        "unique_xlg_series_and_class_identity": len(target_accessions) >= 1,
        "at_least_one_public_historical_snapshot": bool(report_dates and holding_rows),
        "ordinary_equity_cash_and_derivative_distinguishability": bool(asset_categories),
        "ordinary_equity_counts_available": bool(ordinary_rows and company_keys),
        "report_date_distinct_from_accepted_or_public_time": bool(
            report_dates and accepted_values and set(report_dates).isdisjoint(accepted_values)
        ),
        "no_duplicate_accession_holding_key": (
            missing_holding_ids == 0 and duplicate_keys == 0
        ),
        "revision_rule_mechanically_executable": bool(accepted_values),
    }
    return {
        "source_members": {
            **source_members,
            "submission": submission_members,
            "holdings": holding_members,
        },
        "filtered_artifacts": relation_artifacts,
        "target_accession_count": len(target_accessions),
        "series_row_count": len(series_rows),
        "class_row_count": len(class_rows),
        "submission_row_count": len(submission_rows),
        "holding_row_count": len(holding_rows),
        "ordinary_equity_security_line_count": len(ordinary_rows),
        "ordinary_equity_company_count": len(company_keys),
        "asset_category_counts": dict(sorted(asset_categories.items())),
        "report_periods": report_dates,
        "filing_dates": filing_dates,
        "accepted_or_public_fields": accepted_fields,
        "accepted_or_public_value_count": len(accepted_values),
        "missing_holding_id_count": missing_holding_ids,
        "duplicate_accession_holding_key_count": duplicate_keys,
        "gates": gates,
    }


def _zip_evidence(zip_path: Path, staging_root: Path) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(zip_path, "r") as archive:
            infos = archive.infolist()
            safety_failures = _safe_zip_members(infos)
            manifest = [
                {
                    "member": info.filename,
                    "compressed_bytes": info.compress_size,
                    "uncompressed_bytes": info.file_size,
                    "crc32": f"{info.CRC:08x}",
                    "compression_method": info.compress_type,
                    "flag_bits": info.flag_bits,
                    "is_dir": info.is_dir(),
                }
                for info in infos
            ]
            _write_json_atomic(staging_root / "zip_manifest.json", manifest)
            if safety_failures:
                raise SmokeError(";".join(safety_failures))
            inventory = _schema_inventory(archive)
            _write_json_atomic(staging_root / "schema_inventory.json", inventory)
            target = _collect_target_rows(archive, inventory, staging_root / "filtered")
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        raise SmokeError(f"invalid or unreadable ZIP: {type(exc).__name__}: {exc}") from exc
    return {
        "member_count": len(manifest),
        "total_compressed_bytes": sum(item["compressed_bytes"] for item in manifest),
        "total_uncompressed_bytes": sum(item["uncompressed_bytes"] for item in manifest),
        "unsafe_or_duplicate_member_failures": safety_failures,
        "manifest_path": str(staging_root / "zip_manifest.json"),
        "manifest_sha256": _sha256_file(staging_root / "zip_manifest.json"),
        "schema_inventory_path": str(staging_root / "schema_inventory.json"),
        "schema_inventory_sha256": _sha256_file(staging_root / "schema_inventory.json"),
        "target": target,
    }


def _execute(repo_root: Path, staging_root: Path) -> dict[str, Any]:
    contract_path = repo_root / "research/definitions/sec_nport_bulk_zip_v1_smoke_2025q1.json"
    guards = {
        "contract": _verify_guard(contract_path, CONTRACT_SHA256),
        "old_results": [
            _verify_guard(repo_root / relative, expected) for relative, expected in OLD_RESULTS.items()
        ],
    }
    staging_root.mkdir(parents=True, exist_ok=True)
    raw_root = staging_root / "raw"
    landing_path = raw_root / "sec_form_n_port_data_sets.html"
    landing = _download_once(
        url=LANDING_URL,
        destination=landing_path,
        accept="text/html,application/xhtml+xml",
        maximum_bytes=MAX_LANDING_BYTES,
        timeout=60.0,
    )
    if not landing["success"]:
        raise SmokeError(f"official landing page GET failed: {landing['failure']}")
    if urlparse(str(landing["final_url"])).hostname not in {"www.sec.gov", "sec.gov"}:
        raise SmokeError(f"landing page redirected off SEC: {landing['final_url']}")
    resolved_url = _parse_quarter_link(landing_path.read_bytes())
    resolution = {
        "execution_id": EXECUTION_ID,
        "resolved_at": _utc_now(),
        "landing_url": LANDING_URL,
        "landing_sha256": landing["sha256"],
        "anchor_text": TARGET_ANCHOR,
        "resolved_zip_url": resolved_url,
        "contract_sha256": CONTRACT_SHA256,
    }
    resolution_path = staging_root / "resolved_2025q1_url.json"
    if resolution_path.exists():
        previous = _read_json(resolution_path)
        comparable = {key: value for key, value in previous.items() if key != "resolved_at"}
        expected = {key: value for key, value in resolution.items() if key != "resolved_at"}
        if comparable != expected:
            raise SmokeError("resolved URL identity changed from staged resolution")
    else:
        _write_json_atomic(resolution_path, resolution)
    resolution_sha = _sha256_file(resolution_path)
    print(f"resolved_zip_url={resolved_url}", flush=True)
    print(f"resolved_url_manifest_sha256={resolution_sha}", flush=True)

    zip_path = raw_root / "sec_nport_2025q1.zip"
    download = _download_once(
        url=resolved_url,
        destination=zip_path,
        accept="application/zip,application/octet-stream;q=0.9,*/*;q=0.1",
        maximum_bytes=MAX_ZIP_BYTES,
        timeout=300.0,
    )
    if not download["success"]:
        raise SmokeError(f"resolved SEC ZIP GET failed: {download['failure']}")
    if not zipfile.is_zipfile(zip_path):
        raise SmokeError("resolved SEC response is not a ZIP archive")
    zip_info = _zip_evidence(zip_path, staging_root)
    target_gates = zip_info["target"]["gates"]
    gates = {
        "official_sec_origin_and_stable_raw_sha256": bool(
            download["sha256"]
            and urlparse(str(download["final_url"])).hostname in {"www.sec.gov", "sec.gov"}
        ),
        **target_gates,
        "preserved_terminal_evidence_byte_identity_unchanged": True,
    }
    failures = sorted(name for name, passed in gates.items() if not passed)
    return {
        "execution_id": EXECUTION_ID,
        "phase": "INPUT_ONLY_FEASIBILITY_SMOKE",
        "terminal_outcome": "BULK_ROUTE_FEASIBLE" if not failures else "INPUT_BLOCKED",
        "strategy_candidate_available": False,
        "outcome_accessed": False,
        "central_database_opened_or_written": False,
        "guards": guards,
        "landing_page": landing,
        "resolved_url_manifest": {
            "path": str(resolution_path),
            "sha256": resolution_sha,
            "resolved_zip_url": resolved_url,
        },
        "zip_download": download,
        "zip": zip_info,
        "gates": gates,
        "gate_failures": failures,
        "report_date_available_at_rule": (
            "report period is economic time only; accepted/public dissemination time is required "
            "and must remain a separate field"
        ),
        "next_action_if_feasible": (
            "Materialize the four frozen disclosed snapshots only after isolated-copy writer, "
            "backup, idempotency, and full data-quality gates."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--staging-root", type=Path, required=True)
    parser.add_argument("--canonical-db", type=Path, required=True)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    staging_root = args.staging_root.resolve()
    staging_root.mkdir(parents=True, exist_ok=True)
    evidence_path = staging_root / "smoke_evidence.json"
    started_at = _utc_now()
    preflight = {
        "captured_at": _utc_now(),
        "repo": _capture_repo_identity(repo_root),
        "canonical_db": _capture_db_identity(args.canonical_db),
        "old_result_guards": [
            _verify_guard(repo_root / relative, expected)
            for relative, expected in OLD_RESULTS.items()
        ],
    }
    preflight_path = staging_root / "preflight_state.json"
    _write_json_atomic(preflight_path, preflight)
    try:
        evidence = _execute(repo_root, staging_root)
    except SmokeError as exc:
        evidence = {
            "execution_id": EXECUTION_ID,
            "phase": "INPUT_ONLY_FEASIBILITY_SMOKE",
            "terminal_outcome": "INPUT_BLOCKED",
            "strategy_candidate_available": False,
            "outcome_accessed": False,
            "central_database_opened_or_written": False,
            "mechanical_failure": str(exc),
            "started_at": started_at,
            "finished_at": _utc_now(),
        }
    postflight = {
        "captured_at": _utc_now(),
        "repo": _capture_repo_identity(repo_root),
        "canonical_db": _capture_db_identity(args.canonical_db),
        "old_result_guards": [
            _verify_guard(repo_root / relative, expected)
            for relative, expected in OLD_RESULTS.items()
        ],
    }
    postflight_path = staging_root / "postflight_state.json"
    _write_json_atomic(postflight_path, postflight)
    db_unchanged = _db_unchanged(preflight["canonical_db"], postflight["canonical_db"])
    old_results_unchanged = (
        preflight["old_result_guards"] == postflight["old_result_guards"]
    )
    evidence["preflight_state"] = {
        "path": str(preflight_path),
        "sha256": _sha256_file(preflight_path),
    }
    evidence["postflight_state"] = {
        "path": str(postflight_path),
        "sha256": _sha256_file(postflight_path),
    }
    evidence["canonical_db_unchanged"] = db_unchanged
    evidence["preserved_terminal_evidence_unchanged"] = old_results_unchanged
    if "gates" in evidence:
        evidence["gates"]["central_database_byte_identity_unchanged"] = db_unchanged
        evidence["gates"][
            "preserved_terminal_evidence_byte_identity_unchanged"
        ] = old_results_unchanged
        evidence["gate_failures"] = sorted(
            name for name, passed in evidence["gates"].items() if not passed
        )
        evidence["terminal_outcome"] = (
            "BULK_ROUTE_FEASIBLE" if not evidence["gate_failures"] else "INPUT_BLOCKED"
        )
    elif not db_unchanged or not old_results_unchanged:
        evidence["mechanical_failure"] = (
            f"{evidence['mechanical_failure']}; postflight_identity_guard_failed"
        )
    evidence["finished_at"] = _utc_now()
    evidence["started_at"] = started_at
    _write_json_atomic(evidence_path, evidence)
    print(
        json.dumps(
            {
                "execution_id": EXECUTION_ID,
                "terminal_outcome": evidence["terminal_outcome"],
                "gate_failures": evidence.get("gate_failures", [evidence.get("mechanical_failure")]),
                "smoke_evidence_path": str(evidence_path),
                "smoke_evidence_sha256": _sha256_file(evidence_path),
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        flush=True,
    )
    return 0 if evidence["terminal_outcome"] == "BULK_ROUTE_FEASIBLE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
