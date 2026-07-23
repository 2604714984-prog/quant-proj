from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_us_current_top50_momentum_discovery_v0 as engine  # noqa: E402
import run_us_current_top50_momentum_discovery_v0_3_gsd as adapter  # noqa: E402


def test_contract_prior_bytes_and_pinned_source_are_immutable() -> None:
    contract = ROOT / "research/definitions/us_current_top50_momentum_discovery_v0_3_gsd.json"
    assert hashlib.sha256(contract.read_bytes()).hexdigest() == adapter.CONTRACT_SHA
    for relative, expected in adapter.PRESERVED.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
    for relative, expected in adapter.SOURCE_HASHES.items():
        assert hashlib.sha256((adapter.GSD_REPO / relative).read_bytes()).hexdigest() == expected


def test_top_holdings_parser_accepts_exactly_50_companies(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    rows = [{"symbol": f"T{i:02}", "holdingName": f"Issuer {i}", "holdingPercent": {"raw": 0.02}} for i in range(50)]
    raw = json.dumps({"quoteSummary": {"result": [{"topHoldings": {"holdings": rows}}]}}).encode()
    path = tmp_path / "universe/yahoo_xlg_top_holdings.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(raw)
    engine.dump(path.with_suffix(".json.metadata.json"), {"url": adapter.XLG_SUMMARY, "module": "topHoldings", "source_function": "yahoo_quote_summary", "status": 200, "sha256": hashlib.sha256(raw).hexdigest()})
    parsed, _ = adapter._top_holdings(tmp_path)
    assert adapter._valid_identity(parsed)


def test_stooq_parser_preserves_rows() -> None:
    raw = b"Date,Open,High,Low,Close,Volume\n" + b"\n".join(f"2020-01-{i:02},1,1,1,1,1".encode() for i in range(1, 32))
    raw += b"\n" + b"\n".join(f"2020-02-{i:02},1,1,1,1,1".encode() for i in range(1, 29))
    with pytest.raises(engine.Blocked, match="invalid_stooq_history"):
        adapter.stooq_rows(raw)
    valid = b"Date,Open,High,Low,Close,Volume\n" + b"\n".join(
        f"{date(2020, 3, 1) + timedelta(days=i)},1,1,1,1,1".encode() for i in range(61)
    )
    assert adapter.stooq_rows(valid)[date(2020, 3, 1)] == 1.0


def test_configuration_uses_pinned_adapters_and_no_stockanalysis_or_playwright() -> None:
    adapter.configure()
    assert engine.universe is adapter.universe
    assert engine.acquire_symbol is adapter.acquire_symbol
    source = (ROOT / "scripts/run_us_current_top50_momentum_discovery_v0_3_gsd.py").read_text()
    assert "stockanalysis.com" not in source.lower()
    assert "playwright" not in source.lower()


def test_unicode_company_identity_groups_share_classes() -> None:
    assert adapter.company_id("谷歌-A") == adapter.company_id("谷歌-C")
    assert adapter.company_id("伯克希尔哈撒韦-A") == adapter.company_id("伯克希尔哈撒韦-B")


def test_terminal_result_stops_before_prices_writes_and_outcomes() -> None:
    result = json.loads(
        (
            ROOT
            / "research/results/us_current_top50_momentum_discovery_v0_3_gsd_input_blocked_20260723.json"
        ).read_text()
    )
    assert result["result"] == "INPUT_BLOCKED"
    assert result["raw_inputs"]["price_files"] == 0
    assert result["central_data"]["writer_invoked"] is False
    assert result["central_data"]["unchanged"] is True
    assert result["formal_discovery"]["run_count"] == 0
    assert result["strategy_candidate_available"] is False
