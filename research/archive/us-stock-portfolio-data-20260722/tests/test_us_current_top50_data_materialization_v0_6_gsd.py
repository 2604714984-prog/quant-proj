from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_us_current_top50_momentum_discovery_v0 as engine  # noqa: E402
import run_us_current_top50_data_materialization_v0_6_gsd as adapter  # noqa: E402


def test_contract_v0_5_core_and_staging_are_immutable() -> None:
    contract = ROOT / "research/definitions/us_current_top50_data_materialization_v0_6_gsd.json"
    assert hashlib.sha256(contract.read_bytes()).hexdigest() == adapter.CONTRACT_SHA
    for relative, expected in adapter.PRESERVED.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
    for relative, expected in adapter.V05_STAGING.items():
        assert hashlib.sha256((adapter.V05_ROOT / relative).read_bytes()).hexdigest() == expected


def test_sina_parser_and_latest_crosscheck() -> None:
    start = date(2026, 1, 1)
    items = [{"d": str(start + timedelta(days=i)), "c": "10", "o": "9", "h": "11", "l": "8", "v": "1"} for i in range(120)]
    raw = f"var x=({json.dumps(items)});".encode()
    sina = adapter.sina_rows(raw)
    primary = [{"date": day, "close": close} for day, close in sorted(sina.items())]
    check = adapter.crosscheck_latest(primary, sina)
    assert check["overlap"] == 120
    assert check["pass_ratio"] == 1.0
    assert check["passed"] is True


def test_configuration_uses_sina_crosscheck_and_existing_writer() -> None:
    adapter.configure()
    assert engine.acquire_symbol is adapter.acquire_symbol
    assert engine.writer_rows is adapter.writer_rows
    assert engine.materialize is adapter.materialize
    source = (ROOT / "scripts/run_us_current_top50_data_materialization_v0_6_gsd.py").read_text()
    assert "stooq_url" not in source


def test_terminal_result_stops_before_writer_and_outcomes() -> None:
    result = json.loads(
        (
            ROOT
            / "research/results/us_current_top50_data_materialization_v0_6_gsd_input_blocked_20260723.json"
        ).read_text()
    )
    assert result["result"] == "INPUT_BLOCKED"
    assert result["successful_gates"]["five_symbol_smoke"] == "SMOKE_PASS"
    assert result["mechanical_failure"]["available_complete_daily_sessions"] == 27
    assert result["requests"]["stooq"] == 0
    assert result["central_data"]["writer_invoked"] is False
    assert result["formal_discovery"]["run_count"] == 0
