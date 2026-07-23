from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_us_current_top50_momentum_discovery_v0 as engine  # noqa: E402
import run_us_current_top50_momentum_discovery_v0_2 as adapter  # noqa: E402


def _table(count: int) -> bytes:
    rows = ["<table><tr><th>Symbol</th><th>Company</th><th>Weight</th></tr>"]
    rows.extend(
        f"<tr><td>T{i:02}</td><td>Issuer {i}</td><td>{100 / count:.6f}%</td></tr>"
        for i in range(count)
    )
    rows.append("</table>")
    return "".join(rows).encode()


def _freeze(root: Path, raw: bytes, *, challenge: bool = False) -> None:
    universe = root / "universe"
    universe.mkdir(parents=True)
    (universe / "stockanalysis_browser_dom.html").write_bytes(raw)
    (universe / "stockanalysis_browser_metadata.json").write_text(
        json.dumps(
            {
                "url": adapter.STOCKANALYSIS_URL,
                "final_url": adapter.STOCKANALYSIS_URL,
                "retrieved_at": "2026-07-23T00:00:00Z",
                "title": "XLG Holdings",
                "sha256": hashlib.sha256(raw).hexdigest(),
                "challenge_detected": challenge,
                "browser": "Chromium via Playwright CLI",
            }
        )
    )


def test_contract_and_all_preserved_prior_bytes_are_immutable() -> None:
    contract = ROOT / "research/definitions/us_current_top50_momentum_discovery_v0_2.json"
    assert hashlib.sha256(contract.read_bytes()).hexdigest() == adapter.CONTRACT_SHA
    for relative, expected in adapter.PRESERVED.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_browser_dom_freezes_exactly_50_companies(tmp_path: Path) -> None:
    _freeze(tmp_path, _table(50))
    rows, identity = adapter.universe(tmp_path)
    assert len(rows) == 50
    assert identity["companies"] == 50
    assert identity["source"] == "STOCKANALYSIS_PLAYWRIGHT_DOM_V0_2"
    assert len(json.loads((tmp_path / "universe/frozen_rows.json").read_text())) == 50


@pytest.mark.parametrize("failure", ["challenge", "hash", "count"])
def test_browser_dom_fails_closed(failure: str, tmp_path: Path) -> None:
    raw = _table(49 if failure == "count" else 50)
    _freeze(tmp_path, raw, challenge=failure == "challenge")
    if failure == "hash":
        path = tmp_path / "universe/stockanalysis_browser_metadata.json"
        metadata = json.loads(path.read_text())
        metadata["sha256"] = "0" * 64
        path.write_text(json.dumps(metadata))
    with pytest.raises(engine.Blocked):
        adapter.universe(tmp_path)


def test_adapter_is_small_and_uses_only_frozen_same_provider_dom() -> None:
    source = (ROOT / "scripts/run_us_current_top50_momentum_discovery_v0_2.py").read_text()
    logical = [
        line for line in source.splitlines() if line.strip() and not line.lstrip().startswith("#")
    ]
    assert len(logical) <= 110
    assert source.count("https://") == 1
    assert "engine.fetch(" not in source
    assert "invesco.com" not in source.lower()
