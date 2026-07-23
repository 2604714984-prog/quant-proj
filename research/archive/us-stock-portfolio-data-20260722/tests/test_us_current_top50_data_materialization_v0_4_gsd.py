from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_us_current_top50_momentum_discovery_v0 as engine  # noqa: E402
import run_us_current_top50_data_materialization_v0_4_gsd as adapter  # noqa: E402


def test_contract_and_v0_3_bytes_are_immutable() -> None:
    contract = ROOT / "research/definitions/us_current_top50_data_materialization_v0_4_gsd.json"
    assert hashlib.sha256(contract.read_bytes()).hexdigest() == adapter.CONTRACT_SHA
    for relative, expected in adapter.PRESERVED.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
    assert hashlib.sha256((adapter.V03_ROOT / "source_manifest.json").read_bytes()).hexdigest() == adapter.V03_MANIFEST_SHA


def test_select_lines_uses_median_liquidity_and_ascending_tie(monkeypatch, tmp_path: Path) -> None:
    candidates = [{"symbol": f"S{i:02}", "name": f"Issuer {i}", "market_cap": 100 - i} for i in range(48)]
    candidates += [
        {"symbol": "D1-A", "name": "Dual One-A", "market_cap": 50},
        {"symbol": "D1-B", "name": "Dual One-B", "market_cap": 49},
        {"symbol": "D2-A", "name": "Dual Two-A", "market_cap": 48},
        {"symbol": "D2-B", "name": "Dual Two-B", "market_cap": 47},
    ]

    def fake_chart(symbol, root):
        score = {"D1-A": 3, "D1-B": 2, "D2-A": 1, "D2-B": 1}[symbol]
        rows = [{"date": engine.date(2020, 1, 1) + engine.timedelta(days=i), "close": score, "volume": 1} for i in range(60)]
        return rows, {"sha256": symbol.lower()}

    monkeypatch.setattr(adapter.prior, "_yahoo_chart", fake_chart)
    selected, evidence = adapter.select_lines(candidates, tmp_path)
    assert len(selected) == 50
    assert evidence[adapter.prior.company_id("Dual One-A")]["winner"] == "D1-A"
    assert evidence[adapter.prior.company_id("Dual Two-A")]["winner"] == "D2-A"


def test_configuration_keeps_final_scope_and_existing_writer() -> None:
    adapter.configure()
    assert engine.universe is adapter.universe
    assert engine.materialize is adapter.materialize
    assert engine.SNAPSHOT == adapter.SNAPSHOT


def test_terminal_result_stops_before_canonical_write_and_outcomes() -> None:
    result = json.loads(
        (
            ROOT
            / "research/results/us_current_top50_data_materialization_v0_4_gsd_input_blocked_20260723.json"
        ).read_text()
    )
    assert result["result"] == "INPUT_BLOCKED"
    assert result["requests"]["stooq_requests"] == 0
    assert result["central_data"]["writer_invoked"] is False
    assert result["central_data"]["unchanged"] is True
    assert result["formal_discovery"]["run_count"] == 0
    assert result["strategy_candidate_available"] is False
