# Database DB2 Lane A3 Dispatch

BATCH_ID: CENTRAL_DB_DB2_A3_20260713
LANE_ID: A3
PRIORITY: P1
TARGET_DATABASE: /home/rongyu/workspace/quant_data/quant_research.duckdb
TARGET_TABLES: a_share_st_status_history|a_share_suspension_history|a_share_limit_price_status|a_share_tradability_daily
OWNER_REPOSITORY: https://github.com/2604714984-prog/central-data-ingestion
OWNER_BASE_COMMIT: 5801bc2819fc7d37fffe6bdab298ed8ca1c31b6d
SOURCE_POLICY: SSE/SZSE/CNINFO official status and announcement surfaces plus accepted structured source
SYMBOL_SCOPE: A0 symbols
DATE_RANGE: A0 date range
REQUIRED_FIELDS: ts_code|trade_date|status|effective_from|effective_to|up_limit|down_limit|locked_flag|available_at|source|quality_status
PRIMARY_KEY: must be frozen per physical table before execution; duplicate count must be zero
PIT_REQUIREMENTS: status must be known before signal/execution cutoff
ADJUSTMENT_REQUIREMENTS: not applicable
CORPORATE_ACTION_REQUIREMENTS: suspension/resumption and delist status required
QUALITY_THRESHOLDS: duplicate keys=0; interval overlap=0; missing status fails closed
DEPENDENCIES: A0|A2
EXECUTION_MODE: ROUTINE_APPEND_AFTER_PROFILE_ACCEPTANCE
BACKUP_REQUIREMENTS: one accepted daily checkpoint before the first mutation
ROLLBACK_REQUIREMENTS: append batch is replay-safe; rollback may affect only the batch and its staging/receipt
TESTS_REQUIRED: schema, chronology, available_at, key uniqueness, coverage, hash parity, replay, rollback
ARTIFACTS_REQUIRED: code/tests, source manifest, quality report, snapshot metadata, read-only export hashes, callback
CALLBACK_SCHEMA: A_SHARE_DB_CALLBACK_P1_TRADABILITY
GITHUB_BRANCH: codex/central-db-db2-a3-20260713
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
