from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_us_current_top50_momentum_discovery_v0 as engine  # noqa: E402
import run_us_current_top50_data_materialization_v0_9_gsd as adapter  # noqa: E402


def test_contract_v0_8_core_and_manifest_are_immutable() -> None:
    contract = ROOT / "research/definitions/us_current_top50_data_materialization_v0_9_gsd.json"
    assert hashlib.sha256(contract.read_bytes()).hexdigest() == adapter.CONTRACT_SHA
    for relative, expected in adapter.PRESERVED.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
    assert hashlib.sha256((adapter.V08_ROOT / "evidence_manifest.json").read_bytes()).hexdigest() == adapter.V08_MANIFEST_SHA


def test_nine_real_rows_are_canonical_but_unresolved() -> None:
    start = date(2026, 7, 10)
    primary = [{"date": start + timedelta(days=i), "close": 10.0} for i in range(9)]
    other = {row["date"]: row["close"] for row in primary}
    check = adapter.crosscheck_any(primary, other)
    assert check["history_row_count"] == 9
    assert check["crosscheck_status"] == "UNRESOLVED"
    assert check["qualification_reason"] == "INSUFFICIENT_LT20_HISTORY"


def test_configuration_reuses_v0_8_publication_with_v0_9_identity() -> None:
    adapter.configure()
    assert engine.materialize is adapter.materialize
    assert engine.SNAPSHOT == adapter.SNAPSHOT
    assert adapter.v08.SNAPSHOT == adapter.SNAPSHOT


def test_tiny_history_with_missing_sina_is_unresolved_not_blocked() -> None:
    start = date(2026, 7, 10)
    primary = [{"date": start + timedelta(days=i), "close": 10.0} for i in range(9)]
    check = adapter.crosscheck_any(primary, {})
    assert check["crosscheck_status"] == "UNRESOLVED"
    assert check["overlap"] == 0


def test_terminal_result_is_fail_and_canonical_data_remains_ready() -> None:
    result = json.loads(
        (
            ROOT
            / "research/results/us_current_top50_data_materialization_v0_9_gsd_discovery_fail_20260723.json"
        ).read_text()
    )
    assert result["result"] == "DISCOVERY_FAIL"
    assert result["formal_run"]["run_count"] == 1
    assert result["gates"]["net_sharpe_at_least_benchmark"] is False
    assert result["central_data"]["status"] == "CENTRAL_DATA_READY"
    assert result["central_data"]["price_symbol_count"] == 52
    assert result["strategy_candidate_available"] is False
