"""V0.1 adapter: direct StockAnalysis universe over the frozen V0 engine."""

from __future__ import annotations

from pathlib import Path

import run_us_current_top50_momentum_discovery_v0 as engine


RID = "US_CURRENT_TOP50_MOMENTUM_DISCOVERY_V0_1"
CONTRACT_SHA = "d8e728a6ab927dd628c2c449575137fc4cb679d32656d79621974de524c10e43"
SNAPSHOT = "US_CURRENT_TOP50_MOMENTUM_DISCOVERY_V0_1_20260723"
STOCKANALYSIS_URL = "https://stockanalysis.com/etf/xlg/holdings/"
PRESERVED = {
    "research/definitions/us_current_top50_momentum_discovery_v0.json": "a4b1126132fd8492cd1d2560a9e76b8c8485ce3282d0b109727db6dc8475f663",
    "scripts/run_us_current_top50_momentum_discovery_v0.py": "0df8309fc26417d0c927a5b573f10f324924873ad50916bcf2524cdecef9ba73",
    "tests/test_us_current_top50_momentum_discovery_v0.py": "586da9838c0006700f07161e31485abdeb4abf73d150213b5ed838cdcac80d37",
    "research/results/us_current_top50_momentum_discovery_v0_input_blocked_20260722.json": "d1995e946caabd9542309da636807a43166b74b44a2adcae7375cdcf55fc244e",
    "research/results/us_stock_top50_input_blocked_20260722.json": "36d0581465ea37d26d695bfaa4e1ca1efbc190880b44148058cd30ba712d0877",
    "research/results/us_sp500_top50_xlg_disclosed_universe_v1_input_blocked_20260722.json": "f7da25e80b6f9aefaab59b74086fcd98f9f8d16265bdfa1b26f7461cf93d58a6",
    "research/results/sec_nport_bulk_zip_v1_smoke_2025q1_input_blocked_20260722.json": "fd401efa9ddcc404fd3e919eae0f83eb24cf4e2a2f8c2a90915f038e419823dd",
}


def guards(repo: Path) -> None:
    contract = repo / "research/definitions/us_current_top50_momentum_discovery_v0_1.json"
    if engine.sha(contract) != CONTRACT_SHA:
        raise engine.Blocked("v0_1_contract_sha_changed")
    for relative, expected in PRESERVED.items():
        if engine.sha(repo / relative) != expected:
            raise engine.Blocked(f"preserved_byte_changed:{relative}")


def universe(root: Path) -> tuple[list[dict[str, object]], dict[str, object]]:
    path = root / "universe/stockanalysis_xlg_holdings.html"
    metadata = engine.fetch(STOCKANALYSIS_URL, path)
    if metadata["status"] != 200:
        raise engine.Blocked(f"stockanalysis_http_status:{metadata['status']}")
    rows = engine.parse_holdings_html(path.read_bytes())
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
        "source": "STOCKANALYSIS_DIRECT_V0_1",
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
