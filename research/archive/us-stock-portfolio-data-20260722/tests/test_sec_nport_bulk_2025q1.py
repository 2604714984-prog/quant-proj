from __future__ import annotations

from email.message import Message
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import smoke_sec_nport_bulk_2025q1 as smoke  # noqa: E402


def _add_table(archive: zipfile.ZipFile, name: str, header: str, rows: list[str]) -> None:
    archive.writestr(name, (header + "\n" + "\n".join(rows) + "\n").encode())


def _synthetic_archive(path: Path, *, include_accepted_at: bool = True) -> None:
    submission_header = "ACCESSION_NUMBER\tREPORT_DATE\tFILING_DATE"
    submission_row = "0001\t2025-01-31\t2025-03-03"
    if include_accepted_at:
        submission_header += "\tACCEPTED_AT"
        submission_row += "\t2025-03-03T17:01:02-05:00"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        _add_table(
            archive,
            "FUND_REPORTED_INFO.tsv",
            "ACCESSION_NUMBER\tSERIES_ID\tSERIES_NAME",
            ["0001\tS000060793\tInvesco S&P 500 Top 50 ETF"],
        )
        _add_table(
            archive,
            "CLASS_ID.tsv",
            "ACCESSION_NUMBER\tCLASS_ID",
            ["0001\tC000197609"],
        )
        _add_table(archive, "SUBMISSION.tsv", submission_header, [submission_row])
        _add_table(
            archive,
            "FUND_REPORTED_HOLDING.tsv",
            (
                "ACCESSION_NUMBER\tHOLDING_ID\tISSUER_NAME\tISSUER_TITLE\tISSUER_CUSIP"
                "\tASSET_CAT\tBALANCE\tCURRENCY_VALUE\tCURRENCY_CODE"
            ),
            [
                "0001\th1\tExample One\tCommon Stock\t123456789\tEC\t10\t100\tUSD",
                "0001\th2\tExample Swap\tSwap\t\tDFE\t1\t2\tUSD",
            ],
        )


def test_quarter_link_resolution_is_exact_unique_and_sec_hosted() -> None:
    raw = b"""
    <html><body>
      <a href="/files/dera/data/form-n-port-data-sets/2025q1_nport.zip">2025 Q1</a>
      <a href="/files/dera/data/form-n-port-data-sets/2024q4_nport.zip">2024 Q4</a>
    </body></html>
    """

    assert smoke._parse_quarter_link(raw) == (
        "https://www.sec.gov/files/dera/data/form-n-port-data-sets/2025q1_nport.zip"
    )


@pytest.mark.parametrize(
    "raw",
    [
        b'<a href="https://example.com/x.zip">2025 Q1</a>',
        b'<a href="/a.zip">2025 Q1</a><a href="/b.zip">2025 Q1</a>',
        b'<a href="/a.zip">2025 Q1 revised</a>',
    ],
)
def test_quarter_link_resolution_fails_closed(raw: bytes) -> None:
    with pytest.raises(smoke.SmokeError):
        smoke._parse_quarter_link(raw)


def test_zip_safety_rejects_traversal_duplicate_and_encryption_flag() -> None:
    safe = zipfile.ZipInfo("safe.tsv")
    traversal = zipfile.ZipInfo("../escape.tsv")
    encrypted = zipfile.ZipInfo("encrypted.tsv")
    encrypted.flag_bits |= 0x1

    failures = smoke._safe_zip_members([safe, traversal, encrypted, safe])

    assert "duplicate_member_names:1" in failures
    assert "unsafe_member_path:../escape.tsv" in failures
    assert "encrypted_member:encrypted.tsv" in failures


def test_dynamic_schema_filter_extracts_only_target_and_passes_identity_gates(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "sample.zip"
    _synthetic_archive(archive_path)

    evidence = smoke._zip_evidence(archive_path, tmp_path / "stage")
    target = evidence["target"]

    assert target["target_accession_count"] == 1
    assert target["holding_row_count"] == 2
    assert target["ordinary_equity_security_line_count"] == 1
    assert target["ordinary_equity_company_count"] == 1
    assert target["duplicate_accession_holding_key_count"] == 0
    assert target["accepted_or_public_fields"] == ["ACCEPTED_AT"]
    assert all(target["gates"].values())
    filtered = Path(target["filtered_artifacts"]["holdings"]["path"])
    assert filtered.is_file()
    assert "Example One" in filtered.read_text(encoding="utf-8")


def test_missing_accepted_public_timestamp_fails_closed(tmp_path: Path) -> None:
    archive_path = tmp_path / "sample.zip"
    _synthetic_archive(archive_path, include_accepted_at=False)

    target = smoke._zip_evidence(archive_path, tmp_path / "stage")["target"]

    assert target["report_periods"] == ["2025-01-31"]
    assert target["filing_dates"] == ["2025-03-03"]
    assert target["accepted_or_public_fields"] == []
    assert target["gates"]["report_date_distinct_from_accepted_or_public_time"] is False
    assert target["gates"]["revision_rule_mechanically_executable"] is False


class _FakeResponse(io.BytesIO):
    def __init__(self, body: bytes, *, content_length: int) -> None:
        super().__init__(body)
        self.status = 200
        self.headers = Message()
        self.headers["Content-Length"] = str(content_length)
        self.headers["Content-Type"] = "application/zip"

    def geturl(self) -> str:
        return "https://www.sec.gov/test.zip"


def test_download_enforces_content_length_before_body_and_writes_no_part(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    response = _FakeResponse(b"should-not-be-read", content_length=101)
    monkeypatch.setattr(smoke, "urlopen", lambda request, timeout: response)
    destination = tmp_path / "raw.zip"

    metadata = smoke._download_once(
        url="https://www.sec.gov/test.zip",
        destination=destination,
        accept="application/zip",
        maximum_bytes=100,
        timeout=1.0,
    )

    assert metadata["success"] is False
    assert metadata["failure"] == "content_length_exceeds_limit:101>100"
    assert metadata["byte_count"] == 0
    assert not destination.exists()
    assert not destination.with_suffix(".zip.part").exists()
    staged = json.loads(destination.with_suffix(".zip.metadata.json").read_text())
    assert staged["retry_count"] == 0


def test_contract_old_results_and_no_duckdb_import_are_immutable() -> None:
    contract = REPO_ROOT / "research/definitions/sec_nport_bulk_zip_v1_smoke_2025q1.json"
    source = REPO_ROOT / "scripts/smoke_sec_nport_bulk_2025q1.py"

    assert hashlib.sha256(contract.read_bytes()).hexdigest() == smoke.CONTRACT_SHA256
    for relative, expected in smoke.OLD_RESULTS.items():
        assert hashlib.sha256((REPO_ROOT / relative).read_bytes()).hexdigest() == expected
    assert "import duckdb" not in source.read_text(encoding="utf-8")


def test_terminal_result_is_fail_closed_and_contains_no_strategy_output() -> None:
    path = (
        REPO_ROOT
        / "research/results/sec_nport_bulk_zip_v1_smoke_2025q1_input_blocked_20260722.json"
    )
    result = json.loads(path.read_text(encoding="utf-8"))

    assert result["result"] == "INPUT_BLOCKED"
    assert result["network_evidence"]["landing_page_get_attempt_count"] == 1
    assert result["network_evidence"]["zip_get_attempt_count"] == 0
    assert result["network_evidence"]["retry_count"] == 0
    assert result["canonical_database"]["write_attempted"] is False
    assert result["canonical_database"]["database_connection_opened"] is False
    assert result["research_boundaries"]["strategy_candidate_available"] is False
    assert result["research_boundaries"]["current_executable_stock_list_output"] is False
