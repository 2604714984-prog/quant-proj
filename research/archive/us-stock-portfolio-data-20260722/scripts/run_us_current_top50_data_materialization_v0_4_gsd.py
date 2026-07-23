"""V0.4: select 50 lines from the frozen 52-line GSD universe, then publish once."""

from __future__ import annotations

from pathlib import Path
from statistics import median
from typing import Any

import run_us_current_top50_momentum_discovery_v0 as engine
import run_us_current_top50_momentum_discovery_v0_3_gsd as prior


RID = "US_CURRENT_TOP50_DATA_MATERIALIZATION_V0_4_GSD"
CONTRACT_SHA = "42d702a1551002f7cae3ae1eb1c6b63b8a2e8ac705c45960fa901f9426c9dbc2"
SNAPSHOT = "US_CURRENT_TOP50_DATA_MATERIALIZATION_V0_4_GSD_20260723"
V03_ROOT = Path("/home/rongyu/workspace/quant-data/staging/us_current_top50_momentum_discovery_v0_3_gsd")
BASE_MATERIALIZE = engine.materialize
PRESERVED = {
    "research/definitions/us_current_top50_momentum_discovery_v0_3_gsd.json": "6ff104e67479cdcee23eec6116b35b55468320d7ca1e8d10264f5f7a830a86b7",
    "scripts/run_us_current_top50_momentum_discovery_v0_3_gsd.py": "b375dececddd66be1474dac672d5e2d17cf3cdb60315614e01038e0b314cf667",
    "tests/test_us_current_top50_momentum_discovery_v0_3_gsd.py": "4371247878bfcea365620429ed48f04e066eb210c7fb84872c7bcae46d015fd0",
    "research/results/us_current_top50_momentum_discovery_v0_3_gsd_input_blocked_20260723.json": "34c13b5aaa8538d51822ea8ffb7fd2e234676b171d3ab71d9ba9a25b90beceb3",
}
V03_MANIFEST_SHA = "4a283ae7a526a72fc4477213c3fded4ad3ceb6ab650946dad9ecc420d72a5d9e"


def guards(repo: Path) -> None:
    contract = repo / "research/definitions/us_current_top50_data_materialization_v0_4_gsd.json"
    if engine.sha(contract) != CONTRACT_SHA:
        raise engine.Blocked("v0_4_contract_sha_changed")
    for relative, expected in PRESERVED.items():
        if engine.sha(repo / relative) != expected:
            raise engine.Blocked(f"preserved_v0_3_byte_changed:{relative}")
    if engine.sha(V03_ROOT / "source_manifest.json") != V03_MANIFEST_SHA:
        raise engine.Blocked("preserved_v0_3_manifest_changed")
    for relative, expected in prior.SOURCE_HASHES.items():
        if engine.sha(prior.GSD_REPO / relative) != expected:
            raise engine.Blocked(f"pinned_source_changed:{relative}")


def raw_candidates() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    primary, primary_meta = prior._top_holdings(V03_ROOT)
    if len(primary) != 10:
        raise engine.Blocked(f"frozen_primary_identity_changed:{len(primary)}")
    nasdaq, nasdaq_meta = prior._eastmoney_market(V03_ROOT, "m:105")
    nyse, nyse_meta = prior._eastmoney_market(V03_ROOT, "m:106")
    merged = sorted(nasdaq + nyse, key=lambda row: (-float(row["market_cap"]), str(row["symbol"])))
    company_order: list[str] = []
    for row in merged:
        company = prior.company_id(str(row["name"]))
        if company not in company_order:
            company_order.append(company)
        if len(company_order) == 50:
            break
    selected_companies = set(company_order)
    candidates = [row for row in merged if prior.company_id(str(row["name"])) in selected_companies]
    candidates.sort(key=lambda row: (-float(row["market_cap"]), str(row["symbol"])))
    companies = {prior.company_id(str(row["name"])) for row in candidates}
    if len(candidates) != 52 or len(companies) != 50:
        raise engine.Blocked(f"v0_4_raw_identity:lines={len(candidates)}:companies={len(companies)}")
    source = {
        "pinned_commit": prior.GSD_COMMIT,
        "primary_count": len(primary),
        "primary_sha256": primary_meta["sha256"],
        "nasdaq_sha256": nasdaq_meta["sha256"],
        "nyse_sha256": nyse_meta["sha256"],
    }
    return candidates, source


def select_lines(candidates: list[dict[str, Any]], root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in candidates:
        groups.setdefault(prior.company_id(str(row["name"])), []).append(row)
    duplicates = {company: rows for company, rows in groups.items() if len(rows) > 1}
    if sorted(len(rows) for rows in duplicates.values()) != [2, 2]:
        raise engine.Blocked("v0_4_multiclass_group_identity")
    winners: dict[str, str] = {}
    evidence: dict[str, Any] = {}
    for company, members in sorted(duplicates.items()):
        histories, metadata = {}, {}
        for member in members:
            symbol = str(member["symbol"])
            histories[symbol], metadata[symbol] = prior._yahoo_chart(symbol, root)
        common = sorted(set.intersection(*(set(histories[str(member["symbol"])][i]["date"] for i in range(len(histories[str(member["symbol"])]))) for member in members)))
        common = common[-60:]
        if len(common) != 60:
            raise engine.Blocked("v0_4_multiclass_60_common_sessions_missing")
        scores: dict[str, float] = {}
        for member in members:
            symbol = str(member["symbol"])
            by_date = {row["date"]: row for row in histories[symbol]}
            scores[symbol] = median(float(by_date[day]["close"]) * float(by_date[day]["volume"]) for day in common)
        best = max(scores.values())
        winner = sorted(symbol for symbol, score in scores.items() if score == best)[0]
        winners[company] = winner
        evidence[company] = {
            "members": sorted(scores),
            "common_dates": [str(day) for day in common],
            "liquidity_medians": scores,
            "winner": winner,
            "yahoo_sha256": {symbol: metadata[symbol]["sha256"] for symbol in sorted(metadata)},
            "tie_break": "ascending ticker only if medians exactly equal",
        }
    final = []
    for row in candidates:
        company = prior.company_id(str(row["name"]))
        if company not in winners or str(row["symbol"]) == winners[company]:
            final.append(row)
    if len(final) != 50 or len({prior.company_id(str(row["name"])) for row in final}) != 50:
        raise engine.Blocked("v0_4_final_50_identity")
    return final, evidence


def universe(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw, source = raw_candidates()
    engine.dump(root / "universe/raw_52_identity.json", {"rows": raw, "source": source})
    final, class_evidence = select_lines(raw, root)
    engine.dump(root / "universe/class_selection.json", class_evidence)
    engine.dump(root / "universe/frozen_rows.json", final)
    return final, {
        "source": "PINNED_GSD_EASTMONEY_TOTAL_MARKET_CAP_WITH_YAHOO_LIQUIDITY_CLASS_SELECTION",
        "raw_security_lines": 52,
        "companies": 50,
        "selected_security_lines": 50,
        "multiclass_companies": 2,
        "source_identity": source,
    }


def materialize(repo: Path, root: Path, db: Path) -> dict[str, Any]:
    guards(repo)
    final = engine.json.loads((root / "universe/frozen_rows.json").read_text())
    symbols = [str(row["symbol"]) for row in final] + ["SPY", "XLG"]
    if len(symbols) != 52 or len(set(symbols)) != 52:
        raise engine.Blocked("v0_4_canonical_symbol_identity")
    for symbol in symbols:
        _, check = prior.acquire_symbol(symbol, root)
        if not check["crosscheck"]["passed"]:
            raise engine.Blocked(f"v0_4_canonical_crosscheck_failed:{symbol}")
    return BASE_MATERIALIZE(repo, root, db)


def configure() -> None:
    prior.configure()
    engine.RID = RID
    engine.SNAPSHOT = SNAPSHOT
    engine.CONTRACT_SHA = CONTRACT_SHA
    engine.guards = guards
    engine.universe = universe
    engine.materialize = materialize
    engine.company = prior.company_id
    engine.__file__ = __file__


def main() -> int:
    configure()
    return engine.main()


if __name__ == "__main__":
    raise SystemExit(main())
