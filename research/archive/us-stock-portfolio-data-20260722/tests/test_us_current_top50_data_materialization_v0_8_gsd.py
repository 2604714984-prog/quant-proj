from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_us_current_top50_momentum_discovery_v0 as engine  # noqa: E402
import run_us_current_top50_data_materialization_v0_8_gsd as adapter  # noqa: E402


def test_contract_v0_7_core_and_manifest_are_immutable() -> None:
    contract = ROOT / "research/definitions/us_current_top50_data_materialization_v0_8_gsd.json"
    assert hashlib.sha256(contract.read_bytes()).hexdigest() == adapter.CONTRACT_SHA
    for relative, expected in adapter.PRESERVED.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
    assert hashlib.sha256((adapter.V07_ROOT / "evidence_manifest.json").read_bytes()).hexdigest() == adapter.V07_MANIFEST_SHA


def test_single_short_history_conflict_is_unresolved_not_deleted() -> None:
    start = date(2026, 1, 1)
    primary = [{"date": start + timedelta(days=i), "close": 10.0} for i in range(27)]
    other = {row["date"]: row["close"] for row in primary[:-1]}
    other[primary[0]["date"]] = 9.5
    check = adapter.crosscheck_unresolved(primary, other)
    assert check["crosscheck_status"] == "UNRESOLVED"
    assert check["passed"] is False
    assert check["overlap"] == 26
    assert len(check["conflicts"]) == 1


def test_writer_marks_unresolved_without_changing_yahoo_values(monkeypatch) -> None:
    base = [{"close": 10.0, "row_sha256": "old", "quality_status": "old", "conflict_flags_json": "{}"}]
    monkeypatch.setattr(adapter, "BASE_WRITER_ROWS", lambda symbol, rows, meta: [dict(base[0])])
    meta = {"crosscheck": {"crosscheck_status": "UNRESOLVED", "overlap": 26, "pass_ratio": 25 / 26, "short_history": True, "history_first_date": "2026-01-01", "history_row_count": 27, "conflicts": [{"date": "2026-01-02"}], "passed": False}}
    output = adapter.writer_rows("ZZZ", [], meta)
    assert output[0]["close"] == 10.0
    assert output[0]["quality_status"] == "RESEARCH_CANONICAL_CROSSCHECK_UNRESOLVED"


def test_configuration_uses_custom_publication_and_qualified_only_run_identity() -> None:
    adapter.configure()
    assert engine.materialize is adapter.materialize
    assert engine.writer_rows is adapter.writer_rows


def test_terminal_v0_8_result_preserves_db_and_outcomes() -> None:
    result = json.loads(
        (
            ROOT
            / "research/results/us_current_top50_data_materialization_v0_8_gsd_input_blocked_20260723.json"
        ).read_text()
    )
    assert result["result"] == "INPUT_BLOCKED"
    assert result["mechanical_failure"]["available_post_listing_rows"] == 9
    assert result["central_data"]["writer_invoked"] is False
    assert result["central_data"]["unchanged"] is True
    assert result["formal_discovery"]["run_count"] == 0
