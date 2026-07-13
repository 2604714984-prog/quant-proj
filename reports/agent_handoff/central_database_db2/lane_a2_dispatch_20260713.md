# Database DB2 Lane A2 Dispatch

BATCH_ID: CENTRAL_DB_DB2_A2_20260713
LANE_ID: A2
PRIORITY: P1
TARGET_DATABASE: /home/rongyu/workspace/quant_data/quant_research.duckdb
TARGET_TABLES: a_share_adj_factor|a_share_daily_adjusted|a_share_corporate_actions
OWNER_REPOSITORY: https://github.com/2604714984-prog/central-data-ingestion
OWNER_BASE_COMMIT: 5801bc2819fc7d37fffe6bdab298ed8ca1c31b6d
SOURCE_POLICY: official announcement documents plus accepted structured cross-check
SYMBOL_SCOPE: A0 symbols
DATE_RANGE: A0 date range
REQUIRED_FIELDS: ts_code|trade_date|adj_factor|event_type|ex_date|record_date|pay_date|effective_date|available_at|source|revision|quality_status
PRIMARY_KEY: must be frozen per physical table before execution; duplicate count must be zero
PIT_REQUIREMENTS: document publication timestamp controls availability
ADJUSTMENT_REQUIREMENTS: formula and raw/adjusted reconciliation required; total_return only with dividends
CORPORATE_ACTION_REQUIREMENTS: dividends|splits|bonus|rights|other share changes
QUALITY_THRESHOLDS: duplicate keys=0; unexplained factor discontinuities=0; event reconciliation pass
DEPENDENCIES: A0
EXECUTION_MODE: ROUTINE_APPEND_AFTER_PROFILE_ACCEPTANCE
BACKUP_REQUIREMENTS: one accepted daily checkpoint before the first mutation
ROLLBACK_REQUIREMENTS: append batch is replay-safe; rollback may affect only the batch and its staging/receipt
TESTS_REQUIRED: schema, chronology, available_at, key uniqueness, coverage, hash parity, replay, rollback
ARTIFACTS_REQUIRED: code/tests, source manifest, quality report, snapshot metadata, read-only export hashes, callback
CALLBACK_SCHEMA: A_SHARE_DB_CALLBACK_P1_ADJUSTMENT
GITHUB_BRANCH: codex/central-db-db2-a2-20260713
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
