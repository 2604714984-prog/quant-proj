#!/usr/bin/env python3
"""One-off, outcome-free Lane B input materializer.

Raw public-source bytes are content-addressed below ``--data-root``.  This
script does not read prices, returns, validation or holdout data and never
writes DuckDB.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

START, END = date(1994, 1, 1), date(2009, 12, 31)
PMC_VERSION = "5.1.3"
URLS = {
    "occ_etf_options_rule": "https://www.theocc.com/clearance-and-settlement/clearing/etf-options",
    "sec_quarterly_expiration_rule": "https://www.sec.gov/files/rules/proposed/34-44743.htm",
    **{f"fed_fomc_{year}": f"https://www.federalreserve.gov/monetarypolicy/fomchistorical{year}.htm" for year in range(1994, 2010)},
    **{f"bls_schedule_{year}": f"https://www.bls.gov/schedule/{year}/home.htm" for year in range(1994, 2010)},
}


def canonical(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def fetch(url: str) -> tuple[bytes, str | None]:
    request = Request(url, headers={"User-Agent": "quant-research-lane-b/1.0"})
    with urlopen(request, timeout=45) as response:  # nosec B310: fixed public routes
        return response.read(), response.headers.get("Last-Modified")


def text_from_html(raw: bytes) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw.decode("utf-8", "replace"))))


def bls_schedule_identities(year: int, raw: bytes, source_hash: str) -> list[dict[str, str]]:
    """Extract date/time identities from the official *schedule*, not outcomes."""
    text = text_from_html(raw)
    month = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    weekday = r"(?:Monday|Tuesday|Wednesday|Thursday|Friday)"
    pattern = re.compile(rf"({weekday}, {month} \d{{1,2}}, {year})\s+(\d{{2}}:\d{{2}}\s+[AP]M)\s+([^<]{{0,120}}?)(?=(?:{weekday}, {month}|$))")
    result: list[dict[str, str]] = []
    for day_text, time_text, release in pattern.findall(text):
        if "Consumer Price Index" in release:
            mechanism = "M4"
            kind = "CPI"
        elif "Employment Situation" in release:
            mechanism = "M5"
            kind = "EMPLOYMENT_SITUATION"
        else:
            continue
        day = datetime.strptime(day_text, "%A, %B %d, %Y").date()
        result.append({"mechanism": mechanism, "event_kind": kind, "event_date": day.isoformat(), "scheduled_time_local": time_text, "timezone": "America/New_York", "source_sha256": source_hash, "identity_status": "OFFICIAL_SCHEDULE_ONLY_NOT_ACTUAL_RECONCILED", "missing_reason": "The BLS annual schedule is official but is not proof of final actual/revised release identity."})
    return result


def third_friday(year: int, month: int) -> date:
    first = date(year, month, 1)
    return date(year, month, 1 + ((4 - first.weekday()) % 7) + 14)


def expiration_identities(sessions: set[date]) -> list[dict[str, str]]:
    result = []
    for year in range(START.year, END.year + 1):
        for month in range(1, 13):
            ordinary = third_friday(year, month)
            event = ordinary
            while event not in sessions and event >= date(year, month, 1):
                event = date.fromordinal(event.toordinal() - 1)
            if event not in sessions:
                continue
            result.append({"mechanism": "M7" if month in (3, 6, 9, 12) else "M6", "event_date": event.isoformat(), "ordinary_third_friday": ordinary.isoformat(), "identity_status": "RULE_DERIVED_OFFICIAL_RULE_NOT_HISTORICAL_IDENTITY", "missing_reason": "OCC/SEC rule documents do not independently identify this historical expiration date."})
    return result


def materialize(data_root: Path, duckdb_path: Path) -> dict[str, object]:
    import duckdb
    import pandas_market_calendars as mcal
    if mcal.__version__ != PMC_VERSION:
        raise RuntimeError(f"pandas_market_calendars {mcal.__version__}, expected {PMC_VERSION}")
    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    raw_root = data_root / "raw"
    raw_root.mkdir(parents=True, exist_ok=True)
    resources, bls_events, fomc_routes = [], [], []
    for source_id, url in URLS.items():
        try:
            raw, modified = fetch(url)
        except Exception as exc:
            resources.append({"source_id": source_id, "url": url, "retrieved_at": retrieved_at, "status": "UNAVAILABLE", "missing_reason": f"{type(exc).__name__}: {exc}"})
            continue
        sha = digest(raw)
        name = f"{source_id}.{sha}.raw"
        (raw_root / name).write_bytes(raw)
        resources.append({"source_id": source_id, "url": url, "filename": f"raw/{name}", "sha256": sha, "bytes": len(raw), "retrieved_at": retrieved_at, "server_last_modified": modified, "status": "MATERIALIZED"})
        if source_id.startswith("bls_schedule_"):
            bls_events.extend(bls_schedule_identities(int(source_id[-4:]), raw, sha))
        if source_id.startswith("fed_fomc_"):
            fomc_routes.append({"source_id": source_id, "source_sha256": sha, "identity_status": "OFFICIAL_ARCHIVE_BYTES_MATERIALIZED_PARSING_AMBIGUOUS", "missing_reason": "The historical page is preserved but no date/time identity is inferred without a record-level official statement mapping."})
    schedule = mcal.get_calendar("NYSE").schedule(START.isoformat(), END.isoformat())
    sessions = {item.date() for item in schedule.index}
    db_sha_before = file_digest(duckdb_path)
    connection = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        parity = connection.execute("SELECT snapshot_id, COUNT(*) AS source_row_count, COUNT(DISTINCT trade_date) AS distinct_date_count, COUNT(*) - COUNT(DISTINCT trade_date) AS duplicate_date_count FROM us_equity_research.us_daily_total_return_research WHERE symbol = 'SPY' AND trade_date BETWEEN ? AND ? GROUP BY snapshot_id", [START, END]).fetchall()
        date_rows = connection.execute("SELECT trade_date FROM us_equity_research.us_daily_total_return_research WHERE symbol = 'SPY' AND trade_date BETWEEN ? AND ? ORDER BY trade_date", [START, END]).fetchall()
    finally:
        connection.close()
    db_sha_after = file_digest(duckdb_path)
    if len(parity) != 1 or parity[0][0] != "tiingo_raw_20260711T142010Z_5c24877d23cfc4a0":
        raise RuntimeError("unexpected SPY snapshot identity")
    snapshot_id, source_row_count, distinct_date_count, duplicate_date_count = parity[0]
    spy_dates = {row[0] for row in date_rows}
    if db_sha_before != db_sha_after or source_row_count != 4030 or distinct_date_count != 4030 or duplicate_date_count != 0 or sessions != spy_dates or len(sessions) != 4030:
        raise RuntimeError("NYSE candidate does not exactly reconcile to frozen SPY date keys")
    calendar_rows = [{"session_date": index.date().isoformat(), "open_utc": row.market_open.isoformat(), "close_utc": row.market_close.isoformat()} for index, row in schedule.iterrows()]
    events = {"bls_schedule_candidates": bls_events, "fomc_routes": fomc_routes, "expiration_candidates": expiration_identities(sessions)}
    for name, rows, key in (("bls", bls_events, lambda row: (row["mechanism"], row["event_date"])), ("expiration", events["expiration_candidates"], lambda row: (row["mechanism"], row["event_date"]))):
        if len({key(row) for row in rows}) != len(rows):
            raise RuntimeError(f"duplicate {name} identity")
    if len(events["expiration_candidates"]) != 192:
        raise RuntimeError("incomplete monthly/quarterly expiration candidate coverage")
    (data_root / "xnys_nyse_candidate.json").write_bytes(canonical(calendar_rows))
    (data_root / "event_identities.json").write_bytes(canonical(events))
    outputs = {name: {"filename": name, "bytes": (data_root / name).stat().st_size, "sha256": file_digest(data_root / name)} for name in ("event_identities.json", "xnys_nyse_candidate.json")}
    manifest = {"schema_version": "us-scheduled-event-lane-b-output-manifest-v1", "outputs": outputs, "receipt_self_hash_excluded_reason": "Receipt is written after this manifest and references its immutable hash to avoid self-hash recursion."}
    (data_root / "output_manifest.json").write_bytes(canonical(manifest))
    repo = Path(__file__).resolve().parents[1]
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=repo, text=True).splitlines()
    receipt = {"schema_version": "us-scheduled-event-lane-b-materialization-v1", "retrieved_at": retrieved_at, "materializer": {"path": "scripts/materialize_us_scheduled_event_lane_b.py", "sha256": file_digest(Path(__file__))}, "repository": {"head": head, "dirty_paths": dirty}, "output_manifest": {"filename": "output_manifest.json", "sha256": file_digest(data_root / "output_manifest.json")}, "calendar": {"package": "pandas_market_calendars", "version": PMC_VERSION, "session_count": len(sessions), "spy_date_key_count": len(spy_dates), "spy_not_calendar": 0, "calendar_not_spy": 0, "status": "CANDIDATE_RECONCILED_NOT_OFFICIALLY_ACCEPTED", "remaining_exception_evidence": "Obtain official historical NYSE closure/early-close evidence before acceptance."}, "spy_date_parity": {"database_path": str(duckdb_path), "database_sha256_before": db_sha_before, "database_sha256_after": db_sha_after, "snapshot_id": snapshot_id, "source_row_count": source_row_count, "distinct_date_count": distinct_date_count, "duplicate_date_count": duplicate_date_count}, "counts": {"route_count": len(resources), "materialized_raw_count": sum(row["status"] == "MATERIALIZED" for row in resources), "unavailable_route_count": sum(row["status"] == "UNAVAILABLE" for row in resources), "bls_schedule_candidates": len(bls_events), "fomc_identity_candidates": 0, "fomc_unparsed_official_routes": len(fomc_routes), "expiration_rule_candidates": len(events["expiration_candidates"])}, "boundaries": {"database_access_mode": "read_only_date_keys_only", "database_write_performed": False, "price_or_return_query": False, "strategy_outcome_accessed": False, "validation_or_holdout_accessed": False, "strategy_candidate_available": False}, "source_resources": resources, "remaining_blockers": ["FOMC event dates/timestamps remain unparsed rather than inferred from ambiguous historical archive pages.", "BLS schedule candidates require final actual/revision reconciliation.", "M6/M7 identities are rule-derived candidates, not accepted official historical event identities.", "NYSE candidate is not official-calendar accepted until historical exception evidence is preserved."]}
    (data_root / "receipt.json").write_bytes(canonical(receipt))
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--duckdb-path", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(materialize(args.data_root, args.duckdb_path), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
