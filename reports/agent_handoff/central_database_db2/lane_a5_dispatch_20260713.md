# Database DB2 Lane A5 Dispatch

BATCH_ID: CENTRAL_DB_DB2_A5_20260713
LANE_ID: A5
PRIORITY: P1
TARGET_DATABASE: /home/rongyu/workspace/quant_data/quant_research.duckdb
TARGET_TABLES: a_share_source_documents_research|a_share_financial_facts_research|a_share_fundamentals_pit
OWNER_REPOSITORY: https://github.com/2604714984-prog/central-data-ingestion
OWNER_BASE_COMMIT: 5801bc2819fc7d37fffe6bdab298ed8ca1c31b6d
SOURCE_POLICY: SSE/SZSE/CNINFO primary PDF/XBRL with accepted structured secondary tie-out
SYMBOL_SCOPE: A0 symbols with staged bounded pilots before full universe
DATE_RANGE: all legally/technically available annual and interim periods
REQUIRED_FIELDS: ts_code|report_period|announced_at|effective_at|revision|concept|value|unit|consolidation_scope|source_url|content_sha256|quality_status
PRIMARY_KEY: must be frozen per physical table before execution; duplicate count must be zero
PIT_REQUIREMENTS: no fact before actual publication; revisions append only
ADJUSTMENT_REQUIREMENTS: statement/restatement versioning required
CORPORATE_ACTION_REQUIREMENTS: issuer identity and report revision chain required
QUALITY_THRESHOLDS: primary tie-out required; conflicts quarantined; balance and period checks pass
DEPENDENCIES: A0|A2|A3
EXECUTION_MODE: ROUTINE_APPEND_AFTER_PROFILE_ACCEPTANCE
BACKUP_REQUIREMENTS: one accepted daily checkpoint before the first mutation
ROLLBACK_REQUIREMENTS: append batch is replay-safe; rollback may affect only the batch and its staging/receipt
TESTS_REQUIRED: schema, chronology, available_at, key uniqueness, coverage, hash parity, replay, rollback
ARTIFACTS_REQUIRED: code/tests, source manifest, quality report, snapshot metadata, read-only export hashes, callback
CALLBACK_SCHEMA: A_SHARE_PIT_FUNDAMENTALS_READY
GITHUB_BRANCH: codex/central-db-db2-a5-20260713
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
