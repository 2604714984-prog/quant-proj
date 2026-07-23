from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_us_current_top50_momentum_discovery_v0 as engine  # noqa: E402
import run_us_current_top50_data_materialization_v0_7_gsd as adapter  # noqa: E402


def _rows(count: int) -> list[dict[str, object]]:
    return [{"date": date(2026, 1, 1) + timedelta(days=i), "close": 10.0} for i in range(count)]


def test_contract_v0_6_core_and_manifest_are_immutable() -> None:
    contract = ROOT / "research/definitions/us_current_top50_data_materialization_v0_7_gsd.json"
    assert hashlib.sha256(contract.read_bytes()).hexdigest() == adapter.CONTRACT_SHA
    for relative, expected in adapter.PRESERVED.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
    assert hashlib.sha256((adapter.V06_ROOT / "evidence_manifest.json").read_bytes()).hexdigest() == adapter.V06_MANIFEST_SHA


def test_short_history_branch_preserves_27_real_sessions() -> None:
    primary = _rows(27)
    other = {row["date"]: row["close"] for row in primary}
    check = adapter.crosscheck_branched(primary, other)
    assert check["short_history"] is True
    assert check["history_row_count"] == 27
    assert check["overlap"] == 27
    assert check["passed"] is True


def test_long_history_branch_uses_latest_120() -> None:
    primary = _rows(150)
    other = {row["date"]: row["close"] for row in primary}
    check = adapter.crosscheck_branched(primary, other)
    assert check["short_history"] is False
    assert check["overlap"] == 120


def test_configuration_preserves_writer_and_no_preipo_fill() -> None:
    adapter.configure()
    assert engine.acquire_symbol is adapter.acquire_symbol
    assert engine.writer_rows is adapter.writer_rows
    assert engine.materialize is adapter.materialize
    source = (ROOT / "scripts/run_us_current_top50_data_materialization_v0_7_gsd.py").read_text()
    assert "forward_fill" not in source


def test_terminal_result_stops_before_writer_and_outcomes() -> None:
    result = json.loads(
        (
            ROOT
            / "research/results/us_current_top50_data_materialization_v0_7_gsd_input_blocked_20260723.json"
        ).read_text()
    )
    assert result["result"] == "INPUT_BLOCKED"
    assert result["mechanical_failure"]["common_complete_sessions"] == 26
    assert result["mechanical_failure"]["sessions_within_0_5_percent"] == 25
    assert result["central_data"]["writer_invoked"] is False
    assert result["central_data"]["unchanged"] is True
    assert result["formal_discovery"]["run_count"] == 0
