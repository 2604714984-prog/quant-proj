from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_us_current_top50_momentum_discovery_v0 as engine  # noqa: E402
import run_us_current_top50_momentum_discovery_v0_1 as adapter  # noqa: E402


def _table(count: int) -> bytes:
    rows = ["<table><tr><th>Symbol</th><th>Company</th><th>Weight</th></tr>"]
    rows.extend(
        f"<tr><td>T{i:02}</td><td>Issuer {i}</td><td>{100 / count:.6f}%</td></tr>"
        for i in range(count)
    )
    rows.append("</table>")
    return "".join(rows).encode()


def test_v0_1_contract_and_all_preserved_v0_bytes_are_immutable() -> None:
    contract = ROOT / "research/definitions/us_current_top50_momentum_discovery_v0_1.json"
    assert hashlib.sha256(contract.read_bytes()).hexdigest() == adapter.CONTRACT_SHA
    for relative, expected in adapter.PRESERVED.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_configuration_changes_identity_without_modifying_v0_files() -> None:
    adapter.configure()

    assert engine.RID == adapter.RID
    assert engine.SNAPSHOT == adapter.SNAPSHOT
    assert engine.OFFICIAL == adapter.STOCKANALYSIS_URL
    assert engine.guards is adapter.guards
    assert engine.universe is adapter.universe


def test_direct_stockanalysis_universe_freezes_exactly_50_companies(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    raw = _table(50)

    def fake_fetch(url: str, path: Path) -> dict[str, object]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return {"url": url, "status": 200, "sha256": hashlib.sha256(raw).hexdigest()}

    monkeypatch.setattr(engine, "fetch", fake_fetch)

    rows, identity = adapter.universe(tmp_path)

    assert len(rows) == 50
    assert identity["companies"] == 50
    assert identity["official_crosscheck"] is False
    frozen = json.loads((tmp_path / "universe/frozen_rows.json").read_text())
    assert len(frozen) == 50


def test_direct_universe_fails_closed_on_wrong_count(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    raw = _table(49)

    def fake_fetch(url: str, path: Path) -> dict[str, object]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return {"url": url, "status": 200}

    monkeypatch.setattr(engine, "fetch", fake_fetch)

    with pytest.raises(engine.Blocked, match="stockanalysis_universe_identity"):
        adapter.universe(tmp_path)


def test_adapter_is_small_and_has_no_official_or_third_universe_source() -> None:
    source = (ROOT / "scripts/run_us_current_top50_momentum_discovery_v0_1.py").read_text()
    logical = [
        line for line in source.splitlines() if line.strip() and not line.lstrip().startswith("#")
    ]

    assert len(logical) <= 100
    assert "invesco.com" not in source.lower()
    assert source.count("https://") == 1


def test_terminal_result_stops_before_prices_writes_and_outcomes() -> None:
    path = (
        ROOT
        / "research/results/us_current_top50_momentum_discovery_v0_1_input_blocked_20260723.json"
    )
    result = json.loads(path.read_text())

    assert result["result"] == "INPUT_BLOCKED"
    assert result["source_attempts"]["stockanalysis"]["http_status"] == 403
    assert result["source_attempts"]["official_universe_requests"] == 0
    assert result["source_attempts"]["yahoo_price_requests"] == 0
    assert result["source_attempts"]["stooq_price_requests"] == 0
    assert result["central_data"]["writer_invoked"] is False
    assert result["central_data"]["unchanged"] is True
    assert result["formal_discovery"]["run_count"] == 0
    assert result["strategy_candidate_available"] is False
