from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ISSUE_URL = "https://github.com/2604714984-prog/quant-proj/issues/19"
DB_PATH = "/home/rongyu/workspace/quant_data/quant_research.duckdb"
DB_OWNER = "https://github.com/2604714984-prog/central-data-ingestion"
DB_OWNER_COMMIT = "5801bc2819fc7d37fffe6bdab298ed8ca1c31b6d"
QUEUE_ORDER = ["A0", "A1", "A2", "A3", "U0", "U1", "U2", "U3", "A4", "A5", "A6", "U4", "U5", "U6", "X1", "X2"]


LANES = {
    "A0": dict(priority="P0", market="A_SHARE", dataset="core market/calendar/symbol history", tables="a_share_trade_calendar|a_share_daily_raw|a_share_symbol_master_history", fields="ts_code|trade_date|open|high|low|close|pre_close|volume|amount|pct_chg|source|source_timestamp|ingested_at|quality_status|name|exchange|board|list_date|delist_date|list_status|status_effective_from|status_effective_to", scope="all SSE/SZSE common A shares", dates="full available history through latest completed session", source="official exchange calendars plus accepted public/authorized structured market source", pit="source_timestamp and immutable available_at no later than consumer cutoff", adjustment="raw prices only; no adjusted or total-return label", corporate="listing/delisting identity required", quality="duplicate keys=0; expected sessions complete; no future rows; listing consistency", deps="FOUNDATION", callback="A_SHARE_DB_CALLBACK_P0_CORE"),
    "A1": dict(priority="P0", market="A_SHARE", dataset="daily basic/market cap/valuation", tables="a_share_daily_basic", fields="ts_code|trade_date|circ_mv|total_mv|turnover_rate|volume_ratio|pe|pe_ttm|pb|ps|ps_ttm|dv_ratio|source|available_at|ingested_at|quality_status", scope="A0 symbols", dates="A0 date range", source="official or explicitly authorized structured source; relay is secondary/unqualified unless separately accepted", pit="available by decision-date close; revision identity retained", adjustment="not applicable", corporate="share-count changes must reconcile with corporate actions", quality="duplicate keys=0; raw join>=98%; circ_mv and total_mv eligible-symbol coverage>=98%; systemic missing clusters=0", deps="A0", callback="A_SHARE_DB_CALLBACK_P0_CIRC_MV"),
    "A2": dict(priority="P1", market="A_SHARE", dataset="adjustment/corporate actions", tables="a_share_adj_factor|a_share_daily_adjusted|a_share_corporate_actions", fields="ts_code|trade_date|adj_factor|event_type|ex_date|record_date|pay_date|effective_date|available_at|source|revision|quality_status", scope="A0 symbols", dates="A0 date range", source="official announcement documents plus accepted structured cross-check", pit="document publication timestamp controls availability", adjustment="formula and raw/adjusted reconciliation required; total_return only with dividends", corporate="dividends|splits|bonus|rights|other share changes", quality="duplicate keys=0; unexplained factor discontinuities=0; event reconciliation pass", deps="A0", callback="A_SHARE_DB_CALLBACK_P1_ADJUSTMENT"),
    "A3": dict(priority="P1", market="A_SHARE", dataset="tradability/status history", tables="a_share_st_status_history|a_share_suspension_history|a_share_limit_price_status|a_share_tradability_daily", fields="ts_code|trade_date|status|effective_from|effective_to|up_limit|down_limit|locked_flag|available_at|source|quality_status", scope="A0 symbols", dates="A0 date range", source="SSE/SZSE/CNINFO official status and announcement surfaces plus accepted structured source", pit="status must be known before signal/execution cutoff", adjustment="not applicable", corporate="suspension/resumption and delist status required", quality="duplicate keys=0; interval overlap=0; missing status fails closed", deps="A0|A2", callback="A_SHARE_DB_CALLBACK_P1_TRADABILITY"),
    "A4": dict(priority="P2", market="A_SHARE", dataset="industry/sector/board history", tables="a_share_industry_classification_history", fields="ts_code|taxonomy|taxonomy_version|industry_code|industry_name|effective_from|effective_to|available_at|source_document_sha256|quality_status", scope="A0 symbols", dates="full historically versioned coverage", source="official/public classification documents; current-only snapshots cannot backfill history", pit="effective-dated and publication-dated", adjustment="not applicable", corporate="symbol lifecycle linkage required", quality="interval overlap=0; mapped-industry coverage declared; current-only rows quarantined", deps="A0", callback="A_SHARE_INDUSTRY_HISTORY_READY"),
    "A5": dict(priority="P1", market="A_SHARE", dataset="PIT fundamentals", tables="a_share_source_documents_research|a_share_financial_facts_research|a_share_fundamentals_pit", fields="ts_code|report_period|announced_at|effective_at|revision|concept|value|unit|consolidation_scope|source_url|content_sha256|quality_status", scope="A0 symbols with staged bounded pilots before full universe", dates="all legally/technically available annual and interim periods", source="SSE/SZSE/CNINFO primary PDF/XBRL with accepted structured secondary tie-out", pit="no fact before actual publication; revisions append only", adjustment="statement/restatement versioning required", corporate="issuer identity and report revision chain required", quality="primary tie-out required; conflicts quarantined; balance and period checks pass", deps="A0|A2|A3", callback="A_SHARE_PIT_FUNDAMENTALS_READY"),
    "A6": dict(priority="P2", market="A_SHARE", dataset="direct events/fund flows", tables="a_share_financing_balance_daily|a_share_fund_flow_direct|a_share_block_trades|a_share_lockup_releases|a_share_dividend_events|a_share_earnings_events|a_share_buyback_events", fields="symbol|event_date|publication_timestamp|effective_date|event_type|value|unit|source|revision|quality_status", scope="A0 symbols where direct records exist", dates="full qualified history", source="official/public direct row-backed sources only", pit="publication timestamp mandatory", adjustment="not applicable", corporate="event identity and revision chain required", quality="synthetic proxy labels prohibited; missing direct source remains blocked", deps="A0|A2|A3", callback="A_SHARE_EVENT_FUND_FLOW_CALLBACK"),
    "U0": dict(priority="P0", market="US", dataset="calendar/symbol master", tables="us_trade_calendar|us_symbol_master_history", fields="symbol|session_date|open_time|close_time|half_day|exchange|asset_type|currency|inception_date|delist_date|effective_from|effective_to|available_at|source", scope="NYSE/Nasdaq ETFs and equities required by U1-U6", dates="calendar 2010-01-01 through current year end; symbol full history", source="NYSE/Nasdaq/SEC official public sources and accepted authorized cross-check", pit="historically effective identities; current-only membership is unqualified", adjustment="not applicable", corporate="ticker changes/delist lifecycle required", quality="duplicate keys=0; holidays/half-days complete; no invented pre-inception rows", deps="FOUNDATION", callback="US_DB_CALLBACK_P0_CALENDAR"),
    "U1": dict(priority="P0", market="US", dataset="QQQ/GLD strict total-return inputs", tables="us_etf_daily_adjusted|us_corporate_actions", fields="symbol|trade_date|open|high|low|close|adjusted_close|total_return_index|volume|dividend_amount|split_factor|available_at|source|quality_status", scope="QQQ|GLD", dates="2016-01-01 through latest completed session", source="official sponsor/SEC documents plus accepted authorized price source and independent reconciliation", pit="publication/availability identity required for actions", adjustment="explicit dividend+split methodology; raw close is not total return", corporate="dividends/splits/expense treatment reconciled", quality="duplicate keys=0; expected sessions complete; action reconciliation pass", deps="U0", callback="US_DB_CALLBACK_P0A"),
    "U2": dict(priority="P1", market="US", dataset="regime core ETFs", tables="us_etf_daily_adjusted|us_corporate_actions", fields="same as U1", scope="SPY|TLT|HYG|LQD", dates="full available history through latest completed session", source="same qualified policy as U1", pit="same as U1", adjustment="same as U1", corporate="same as U1", quality="same as U1 with inception-aware coverage", deps="U0|U1", callback="US_DB_CALLBACK_P0B"),
    "U3": dict(priority="P1", market="US", dataset="sector ETF breadth", tables="us_etf_daily_adjusted|us_corporate_actions", fields="same as U1", scope="XLK|XLF|XLE|XLV|XLI|XLP|XLY|XLB|XLU|XLRE|XLC", dates="inception through latest completed session", source="same qualified policy as U1", pit="same as U1", adjustment="same as U1", corporate="same as U1", quality="duplicate keys=0; pre-inception fabrication=0; coverage declared", deps="U0|U1", callback="US_DB_CALLBACK_P1"),
    "U4": dict(priority="P2", market="US", dataset="volatility/rates/credit/macro PIT", tables="us_volatility_daily|us_rates_daily|us_credit_context_daily|us_macro_releases_pit", fields="series_id|observation_date|value|release_timestamp|vintage|revision|available_at|source|quality_status", scope="approved public market/macro series", dates="full qualified history", source="CBOE/Treasury/FRED/BLS/BEA official public sources", pit="original release and vintages retained; revisions not backdated", adjustment="not applicable", corporate="not applicable", quality="duplicate vintage keys=0; release chronology pass; missing vintages declared", deps="U0", callback="US_CONTEXT_PIT_READY"),
    "U5": dict(priority="P2", market="US", dataset="equity daily/membership/survivorship", tables="us_equity_daily_adjusted|us_index_membership_history|us_symbol_change_history|us_corporate_actions", fields="symbol|trade_date|adjusted_open|adjusted_close|volume|membership_from|membership_to|delist_return|available_at|source|quality_status", scope="accepted broad US universe including staged 270 symbols", dates="full accepted history", source="official/authorized source with raw mirror and lifecycle evidence", pit="historical membership and lifecycle, not current-only", adjustment="dividend/split adjusted and delisting-aware", corporate="mergers/ticker changes/delistings required", quality="survivorship controls pass; duplicate keys=0; lifecycle reconciliation pass", deps="U0|U1", callback="US_EQUITY_SURVIVORSHIP_CALLBACK"),
    "U6": dict(priority="P2", market="US", dataset="PIT fundamentals/earnings", tables="us_fundamentals_pit|us_earnings_events_pit|us_estimate_surprise_pit", fields="symbol|accession|report_period|accepted_at|available_at|concept|value|unit|revision|source_sha256|quality_status", scope="U5 accepted universe", dates="full SEC-available history", source="SEC EDGAR primary documents; estimates only from separately licensed source", pit="acceptance timestamp/accession/revision identity required", adjustment="statement/restatement handling required", corporate="issuer/ticker lifecycle linkage required", quality="duplicate accession/concept keys=0; restatements append only; primary identity pass", deps="U0|U5", callback="US_PIT_FUNDAMENTALS_EARNINGS_CALLBACK"),
    "X1": dict(priority="P3", market="CROSS", dataset="derived feature stores", tables="a_share_feature_store|us_feature_store|regime_feature_store", fields="entity|as_of|feature|value|source_dataset|source_snapshot_id|formula|lookback|minimum_periods|available_time|PIT_status|derivation_commit|hash", scope="accepted upstream datasets only", dates="upstream qualified ranges", source="deterministic derivation from accepted snapshots", pit="inherit strictest upstream availability", adjustment="documented per feature", corporate="inherit upstream action identity", quality="undocumented derived columns=0; reproducible hash parity", deps="A0|A1|A2|A3|A4|A5|A6|U0|U1|U2|U3|U4|U5|U6", callback="DERIVED_FEATURE_STORE_READY"),
    "X2": dict(priority="P3", market="CROSS", dataset="source health/update/snapshot automation", tables="meta.dataset_catalog|meta.snapshot_registry|meta.quality_runs|meta.routine_append_runs", fields="dataset_id|snapshot_id|source_health|stale_at|schema_hash|quality_status|receipt_sha256|rollback_reference", scope="all accepted datasets", dates="continuous operations", source="accepted ingestion profiles only", pit="no weakening of upstream PIT contract", adjustment="no weakening of upstream adjustment contract", corporate="no weakening of upstream action contract", quality="idempotent update; stale/schema/duplicate guards; immutable receipts and exports", deps="ALL_ACCEPTED_LANES", callback="CENTRAL_DB_FULL_DATA_CALLBACK"),
}


def _render_csv(rows: list[dict[str, str]], fieldnames: list[str]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def _prompt(lane_id: str, lane: dict[str, str]) -> bytes:
    batch_id = f"CENTRAL_DB_DB2_{lane_id}_20260713"
    mode = "ROUTINE_APPEND_AFTER_PROFILE_ACCEPTANCE"
    return f"""# Database DB2 Lane {lane_id} Dispatch

BATCH_ID: {batch_id}
LANE_ID: {lane_id}
PRIORITY: {lane['priority']}
TARGET_DATABASE: {DB_PATH}
TARGET_TABLES: {lane['tables']}
OWNER_REPOSITORY: {DB_OWNER}
OWNER_BASE_COMMIT: {DB_OWNER_COMMIT}
SOURCE_POLICY: {lane['source']}
SYMBOL_SCOPE: {lane['scope']}
DATE_RANGE: {lane['dates']}
REQUIRED_FIELDS: {lane['fields']}
PRIMARY_KEY: must be frozen per physical table before execution; duplicate count must be zero
PIT_REQUIREMENTS: {lane['pit']}
ADJUSTMENT_REQUIREMENTS: {lane['adjustment']}
CORPORATE_ACTION_REQUIREMENTS: {lane['corporate']}
QUALITY_THRESHOLDS: {lane['quality']}
DEPENDENCIES: {lane['deps']}
EXECUTION_MODE: {mode}
BACKUP_REQUIREMENTS: one accepted daily checkpoint before the first mutation
ROLLBACK_REQUIREMENTS: append batch is replay-safe; rollback may affect only the batch and its staging/receipt
TESTS_REQUIRED: schema, chronology, available_at, key uniqueness, coverage, hash parity, replay, rollback
ARTIFACTS_REQUIRED: code/tests, source manifest, quality report, snapshot metadata, read-only export hashes, callback
CALLBACK_SCHEMA: {lane['callback']}
GITHUB_BRANCH: codex/central-db-db2-{lane_id.lower()}-20260713
STOP_CONDITIONS: source ambiguity; authorization drift; schema drift; failed quality threshold; rollback failure; secret exposure; writer conflict
ACQUISITION_AUTHORITY: separate machine-verifiable single-use authority; consumed before the first provider or network attempt
STAGING_BOUNDARY: isolated content-addressed staging only; no central warehouse write during acquisition
RESULT_ACCEPTANCE: fresh independent read-only acceptance of source identity, schema, chronology, quality, cleanup, and immutable hashes
CENTRAL_APPEND_AUTHORITY: separate locked single-writer append authority issued only after result acceptance
ROUTINE_FAST_LANE_LIMIT: already-qualified source and profile, unchanged schema and natural key, same append semantics; one command plus immutable receipt

## Execution control

This file is a frozen task definition, not network or database authority. The dedicated database
thread must return a design packet and exact source/profile identity before execution. An elevated
acquisition consumes a per-lane single-use authority before its first attempt and writes only to
isolated staging. Its result receives fresh independent acceptance before the controller may issue
a separate locked single-writer central-append authority. Only an already-qualified source/profile
with unchanged schema, natural key, and append semantics may use the routine fast lane without
per-batch Sol/Luna/human review. New sources, schema or natural-key changes, historical backfill,
overwrite/delete, or canonical/product promotion remain elevated and require separate
machine-verifiable records.

No strategy selection, result access, candidate/readiness promotion, recommendation, signal,
broker/order/paper/live/auto path, credential output, database binary commit, or raw dump commit.
strategy_candidate_available=false.
""".encode()


def build(args: argparse.Namespace) -> dict[Path, bytes]:
    files: dict[Path, bytes] = {}
    manager = Path("reports/central_database/manager")
    prompts = Path("reports/agent_handoff/central_database_db2")
    task = Path("tasks/in_progress/central-database-full-ingestion-db2-20260713")

    files[manager / "central_db_foundation_acceptance_20260713.md"] = f"""# Central DB Foundation Acceptance

Status: `CENTRAL_DB_FOUNDATION_READY`

Accepted implementation repository: {DB_OWNER}

Accepted implementation commit: `{DB_OWNER_COMMIT}`

Independent foundation callback: `{args.foundation_callback}`

Foundation callback SHA-256: `{args.foundation_sha256}`

Foundation callback commit/tree: `{args.foundation_commit}` / `{args.foundation_tree}`

The accepted callback covers the logical contract, physical topology, owner repositories,
ingestion entrypoints, schema and snapshot policies, dataset catalog, backup/rollback,
single-writer lock, read-only exports, PIT and available-at handling, corporate actions,
survivorship, calendars, quality gates, secrets, GitHub delivery, and snapshot registry.

Routine append fast lane is merged in PR #3. Routine prequalified batches do not require
per-batch Sol/Luna/human review. Elevated categories remain: new source, schema/natural-key
change, historical backfill, overwrite/delete, and canonical/product promotion.

No ingestion was dispatched before this acceptance record and registry refresh.
""".encode()

    files[manager / "central_db_full_ingestion_dependency_graph_20260713.md"] = (
        "# Central DB Full Ingestion Dependency Graph\n\n"
        "`FOUNDATION -> {A0,U0}`\n\n"
        "`A0 -> A1 -> A2 -> A3 -> {A4,A5,A6}`\n\n"
        "`U0 -> U1 -> {U2,U3,U5}; U0 -> U4; U5 -> U6`\n\n"
        "`{A0,A1,A2,A3,A4,A5,A6,U0,U1,U2,U3,U4,U5,U6} -> X1`; `{all accepted lanes} -> X2`\n\n"
        "Only one physical writer may run. A-share and US callbacks release independently.\n"
    ).encode()

    headers = ["lane_id", "priority", "market", "dataset", "physical_table", "required_fields", "symbol_scope", "date_range", "source_policy", "PIT_requirement", "adjustment_requirement", "corporate_action_requirement", "quality_thresholds", "dependencies", "owner_repository", "implementation_branch", "status", "callback_path", "snapshot_id", "blocking_reason", "next_action"]
    rows = []
    for lane_id in QUEUE_ORDER:
        lane = LANES[lane_id]
        callback_path = f"reports/central_database/callbacks/{lane['callback']}.json"
        rows.append(dict(lane_id=lane_id, priority=lane["priority"], market=lane["market"], dataset=lane["dataset"], physical_table=lane["tables"], required_fields=lane["fields"], symbol_scope=lane["scope"], date_range=lane["dates"], source_policy=lane["source"], PIT_requirement=lane["pit"], adjustment_requirement=lane["adjustment"], corporate_action_requirement=lane["corporate"], quality_thresholds=lane["quality"], dependencies=lane["deps"], owner_repository=DB_OWNER, implementation_branch=f"codex/central-db-db2-{lane_id.lower()}-20260713", status="NOT_DISPATCHED", callback_path=callback_path, snapshot_id="", blocking_reason="", next_action="dispatch when dependencies are accepted"))
        files[prompts / f"lane_{lane_id.lower()}_dispatch_20260713.md"] = _prompt(lane_id, lane)
    files[manager / "central_db_full_ingestion_task_matrix_20260713.csv"] = _render_csv(rows, headers)

    board_headers = ["lane_id", "priority", "status", "callback_path", "snapshot_id", "blocking_reason", "next_action"]
    files[manager / "central_db_db2_status_board_20260713.csv"] = _render_csv([{key: row[key] for key in board_headers} for row in rows], board_headers)
    files[manager / "central_db_db2_callback_registry_20260713.csv"] = _render_csv([], ["lane_id", "callback_label", "callback_path", "callback_sha256", "owner_commit", "snapshot_id", "accepted_at", "acceptance_verdict", "released_to_user"])
    files[manager / "central_db_db2_blocker_board_20260713.csv"] = _render_csv([], ["lane_id", "blocker_class", "evidence", "first_observed_at", "retry_allowed", "required_next_action", "status"])
    files[manager / "central_db_db2_final_summary_20260713.md"] = b"# Central DB DB2 Final Summary\n\nStatus: IN_PROGRESS\n\nTracking issue: " + ISSUE_URL.encode() + b"\n\nThis file is updated only from accepted immutable callbacks.\n"

    files[task / "spec.md"] = f"""# CENTRAL_DATABASE_FULL_INGESTION_DB2_20260713

Status: READY_TO_DISPATCH_AFTER_GITHUB_PRESERVATION

Tracking issue: {ISSUE_URL}

Foundation acceptance: `reports/central_database/manager/central_db_foundation_acceptance_20260713.md`

Task matrix: `reports/central_database/manager/central_db_full_ingestion_task_matrix_20260713.csv`

Queue order: {' -> '.join(QUEUE_ORDER)}

The dedicated database thread owns all physical database implementation and writes. The manager
owns orchestration, dependency tracking, callback acceptance, status publication, and external
audit assembly. Routine append is one-command and receipt-driven after a signed profile has been
accepted. Heavy gates apply only to elevated categories documented in the foundation acceptance.

Every lane prompt is independently testable and cannot itself authorize network or database
mutation. Each elevated lane uses a single-use acquisition authority, isolated staging, fresh
independent result acceptance, and a separate locked central-append authority. The routine fast
lane is limited to an already-qualified source/profile with unchanged schema, natural key, and
append semantics. Callbacks must declare commit/tree, backup, rollback, schema, primary key,
row/symbol/date coverage, duplicate count, PIT/adjustment/corporate-action semantics, snapshot ID,
export hashes, worktree state, and GitHub URLs.

Boundary: research data only; strategy_candidate_available=false; no recommendation, readiness,
signal, broker/order/paper/live/auto, secret output, database binary commit, or unbounded raw dump.
""".encode()

    files[task / "handoff.md"] = (
        "# Handoff\n\n"
        "Executor: dedicated central-database conversation `019f5c2a-859e-7ed2-8ecf-e94b84f454cb`.\n\n"
        "The manager releases one lane at a time in the frozen queue order and records immutable callbacks.\n"
        "The first lane opens only after this packet is committed, pushed, and independently accepted.\n"
    ).encode()
    files[task / "gate_commands.txt"] = (
        f"/home/rongyu/workspace/A_Share_Monitor/.venv/bin/python scripts/build_central_db_db2_manager_packet.py --check --foundation-callback {args.foundation_callback} --foundation-sha256 {args.foundation_sha256} --foundation-commit {args.foundation_commit} --foundation-tree {args.foundation_tree}\n"
        "/home/rongyu/workspace/A_Share_Monitor/.venv/bin/python -m pytest -q tests/test_central_db_db2_manager_packet.py\n"
        "/home/rongyu/workspace/A_Share_Monitor/.venv/bin/python -m ruff check scripts/build_central_db_db2_manager_packet.py tests/test_central_db_db2_manager_packet.py\n"
        "/home/rongyu/workspace/A_Share_Monitor/.venv/bin/python -c \"import pathlib,yaml; yaml.safe_load(pathlib.Path('registry/projects.yaml').read_text()); yaml.safe_load(pathlib.Path('registry/agents.yaml').read_text())\"\n"
        "git diff --check\n"
    ).encode()

    manifest_entries = []
    for path, body in sorted(files.items(), key=lambda item: str(item[0])):
        manifest_entries.append({"path": str(path), "sha256": hashlib.sha256(body).hexdigest()})
    manifest = {"packet_id": "CENTRAL_DATABASE_FULL_INGESTION_DB2_20260713", "issue_url": ISSUE_URL, "foundation_callback_sha256": args.foundation_sha256, "lane_order": QUEUE_ORDER, "files": manifest_entries, "strategy_candidate_available": False}
    files[manager / "central_db_db2_manager_packet_manifest_20260713.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    return files


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--foundation-callback", required=True)
    parser.add_argument("--foundation-sha256", required=True)
    parser.add_argument("--foundation-commit", required=True)
    parser.add_argument("--foundation-tree", required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if any(not value or "PENDING" in value for value in (args.foundation_callback, args.foundation_sha256, args.foundation_commit, args.foundation_tree)):
        raise SystemExit("real accepted foundation identities are required")
    expected = build(args)
    mismatches = []
    for relative, body in expected.items():
        target = ROOT / relative
        if args.check:
            if not target.is_file() or target.read_bytes() != body:
                mismatches.append(str(relative))
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
    if mismatches:
        raise SystemExit("manager packet mismatch: " + ", ".join(mismatches))
    print(f"manager packet {'check' if args.check else 'write'}: PASS ({len(expected)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
