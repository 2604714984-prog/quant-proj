"""V0.2 adapter: frozen Playwright DOM from the same StockAnalysis universe."""

from __future__ import annotations

import json
from pathlib import Path

import run_us_current_top50_momentum_discovery_v0 as engine


RID = "US_CURRENT_TOP50_MOMENTUM_DISCOVERY_V0_2"
CONTRACT_SHA = "f8bd96c27638b99a83a67fb520f427d2902c4fb88eac3fe1ab8e3108fd40cf2e"
SNAPSHOT = "US_CURRENT_TOP50_MOMENTUM_DISCOVERY_V0_2_20260723"
STOCKANALYSIS_URL = "https://stockanalysis.com/etf/xlg/holdings/"
PRESERVED = {
    "research/definitions/us_current_top50_momentum_discovery_v0_1.json": "d8e728a6ab927dd628c2c449575137fc4cb679d32656d79621974de524c10e43",
    "scripts/run_us_current_top50_momentum_discovery_v0_1.py": "181fd72340adde5203764a29cf672b9df3aef623001a1f8b7605bdb1b0de898a",
    "tests/test_us_current_top50_momentum_discovery_v0_1.py": "173e57abcd837575cf8f1f348886227711b55675e8fe0f94cf33c8a6a18a6ba3",
    "research/results/us_current_top50_momentum_discovery_v0_1_input_blocked_20260723.json": "28473d5e9bce69f8e230dc529bf03489bb380dfd6eba0b99b19857fc647f24e1",
    "research/results/us_current_top50_momentum_discovery_v0_input_blocked_20260722.json": "d1995e946caabd9542309da636807a43166b74b44a2adcae7375cdcf55fc244e",
    "research/results/us_stock_top50_input_blocked_20260722.json": "36d0581465ea37d26d695bfaa4e1ca1efbc190880b44148058cd30ba712d0877",
    "research/results/us_sp500_top50_xlg_disclosed_universe_v1_input_blocked_20260722.json": "f7da25e80b6f9aefaab59b74086fcd98f9f8d16265bdfa1b26f7461cf93d58a6",
    "research/results/sec_nport_bulk_zip_v1_smoke_2025q1_input_blocked_20260722.json": "fd401efa9ddcc404fd3e919eae0f83eb24cf4e2a2f8c2a90915f038e419823dd",
}


def guards(repo: Path) -> None:
    contract = repo / "research/definitions/us_current_top50_momentum_discovery_v0_2.json"
    if engine.sha(contract) != CONTRACT_SHA:
        raise engine.Blocked("v0_2_contract_sha_changed")
    for relative, expected in PRESERVED.items():
        if engine.sha(repo / relative) != expected:
            raise engine.Blocked(f"preserved_byte_changed:{relative}")


def universe(root: Path) -> tuple[list[dict[str, object]], dict[str, object]]:
    dom_path = root / "universe/stockanalysis_browser_dom.html"
    metadata_path = root / "universe/stockanalysis_browser_metadata.json"
    if not dom_path.is_file() or not metadata_path.is_file():
        raise engine.Blocked("stockanalysis_browser_artifact_missing")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    raw = dom_path.read_bytes()
    if metadata.get("url") != STOCKANALYSIS_URL:
        raise engine.Blocked("stockanalysis_browser_url_identity")
    if metadata.get("sha256") != engine.hashlib.sha256(raw).hexdigest():
        raise engine.Blocked("stockanalysis_browser_dom_hash")
    if metadata.get("challenge_detected") is not False:
        raise engine.Blocked("stockanalysis_browser_challenge")
    rows = engine.parse_holdings_html(raw)
    rows = [
        row
        for row in rows
        if engine.re.fullmatch(r"[A-Z][A-Z0-9-]{0,9}", str(row["symbol"]))
    ]
    companies = {engine.company(str(row["name"])) for row in rows}
    if len(rows) not in {50, 51} or len(companies) != 50:
        raise engine.Blocked(
            f"stockanalysis_universe_identity:lines={len(rows)}:companies={len(companies)}"
        )
    engine.dump(root / "universe/frozen_rows.json", rows)
    return rows, {
        "source": "STOCKANALYSIS_PLAYWRIGHT_DOM_V0_2",
        "source_metadata": metadata,
        "security_lines": len(rows),
        "companies": len(companies),
        "official_crosscheck": False,
    }


def configure() -> None:
    engine.RID = RID
    engine.SNAPSHOT = SNAPSHOT
    engine.OFFICIAL = STOCKANALYSIS_URL
    engine.CONTRACT_SHA = CONTRACT_SHA
    engine.guards = guards
    engine.universe = universe
    engine.__file__ = __file__


def main() -> int:
    configure()
    return engine.main()


if __name__ == "__main__":
    raise SystemExit(main())
