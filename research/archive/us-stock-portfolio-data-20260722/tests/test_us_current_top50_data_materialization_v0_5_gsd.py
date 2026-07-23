from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_us_current_top50_momentum_discovery_v0 as engine  # noqa: E402
import run_us_current_top50_data_materialization_v0_5_gsd as adapter  # noqa: E402


def test_contract_v0_4_core_and_staging_are_immutable() -> None:
    contract = ROOT / "research/definitions/us_current_top50_data_materialization_v0_5_gsd.json"
    assert hashlib.sha256(contract.read_bytes()).hexdigest() == adapter.CONTRACT_SHA
    for relative, expected in adapter.PRESERVED.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
    for relative, expected in adapter.V04_STAGING.items():
        assert hashlib.sha256((adapter.V04_ROOT / relative).read_bytes()).hexdigest() == expected


def test_explicit_period_identity_is_daily_and_bounded() -> None:
    assert adapter.PERIOD1 == 1420070400
    assert adapter.PERIOD2 == 1784764800
    source = (ROOT / "scripts/run_us_current_top50_data_materialization_v0_5_gsd.py").read_text()
    assert '"interval": "1d"' in source
    assert '"events": "div,splits"' in source
    assert '"includeAdjustedClose": "true"' in source
    assert '"range": "max"' not in source


def test_configuration_keeps_existing_writer_and_final_scope() -> None:
    adapter.configure()
    assert engine.universe is adapter.universe
    assert engine.acquire_symbol is adapter.acquire_symbol
    assert engine.materialize is adapter.materialize
    assert engine.SNAPSHOT == adapter.SNAPSHOT


def test_terminal_result_stops_on_crosscheck_before_write_and_outcomes() -> None:
    result = json.loads(
        (
            ROOT
            / "research/results/us_current_top50_data_materialization_v0_5_gsd_input_blocked_20260723.json"
        ).read_text()
    )
    assert result["result"] == "INPUT_BLOCKED"
    assert result["successful_input_gates"]["final_selected_stock_lines"] == 50
    assert result["requests"]["stooq_requests"] == 1
    assert result["central_data"]["writer_invoked"] is False
    assert result["central_data"]["unchanged"] is True
    assert result["formal_discovery"]["run_count"] == 0
