# User-Dispatch Prompt — Manager Part 1 Central-Database Minimalization

Copy the fenced prompt into the user-controlled Quant Manager conversation.

```text
RUN MANAGER_PART1_CENTRAL_DB_MINIMALIZATION_SHADOW_MIGRATION_20260714

WORKSTREAM: QUANT_MANAGER_USER_CONTROLLED_ARCHITECTURE_SIMPLIFICATION

AUDIT:
https://github.com/2604714984-prog/quant-proj/blob/f6e302ce7c37562deaca3a243d1667e84426134e/reports/external_audit/repository_wide_architecture_and_central_db_lightweight_audit_part1_20260714.md

AUDITED CENTRAL-DATA REF:
https://github.com/2604714984-prog/central-data-ingestion/pull/22
commit f2d401e42aa8f7cd17a14d94c039f45ba6546d9d

FROZEN VERDICT:
ARCHITECTURE_VERDICT=REBUILD_MINIMAL
DATABASE_CONTENT_ACTION=KEEP_AND_MIGRATE_IN_PLACE
CONTROLLER_VERDICT=SIMPLIFY_NOW

CONTROL
The user controls this workstream. Manager publishes tasks, dispatches the dedicated database
conversation, tracks callbacks, and coordinates acceptance. The database conversation implements,
tests, performs shadow runs, manages backups, and publishes snapshots.

Do not modify strategy formulas, backtest engines, validation splits, or research conclusions. Do not
delete legacy database code before parity and rollback are proven. Do not commit secrets, raw payloads,
DuckDB/SQLite/Parquet files, or backups.

==================================================
RUN PART 1 CHANGES AND PART 2 AUDIT IN PARALLEL
==================================================

EXECUTION_MODE=PARALLEL_WITH_HARD_SCOPE_BOUNDARIES

Start Part 2 immediately; do not wait for this migration to finish.

Part 1 may change only central-data-ingestion, DB operational metadata, quant-proj governance/runbooks,
and related CI. It must not change research/backtest code or silently alter a snapshot pinned for Part
2. Manager must pin exact research commits. Any data-semantic change creates a new snapshot.

==================================================
OBJECTIVE
==================================================

Replace the current multi-path runtime with:

provider adapter -> normalize -> validate -> one lock -> one backup -> one set-based DuckDB
transaction -> postchecks -> one short run record

Keep the existing database and essential collection operating during shadow migration. Immediately
prohibit new writer lanes, signature/HG formats, parallel schema authorities, receipt hierarchies, or
uncommitted temporary bridges.

==================================================
PHASE 0 — FREEZE AND DISPATCH
==================================================

1. Record current branch/commit, active writer, DB path/size/SHA/relation count, latest backup, and
   rollback reference.
2. Mark legacy runtime `LEGACY_ACTIVE_DURING_SHADOW_MIGRATION`.
3. Freeze new control-layer work; allow critical fixes and essential collection only.
4. Create in quant-proj:
   - tasks/in_progress/central-db-minimalization-shadow-migration-20260714/spec.md
   - reports/workspace_dispatch/central_db_minimalization_shadow_migration_status_20260714.md
   - reports/agent_handoff/central_db_minimalization_shadow_migration_database_prompt_20260714.md
   - reports/central_database/manager/central_db_minimalization_parity_board_20260714.csv
5. Create issue `CENTRAL_DB_MINIMALIZATION_SHADOW_MIGRATION_20260714`.

==================================================
PHASE 1 — MINIMAL PATH
==================================================

Create central-data branch:
`codex/central-db-minimal-writer-shadow-migration-20260714`

Do not alter legacy active imports yet.

Target package:
central_data/config.py
central_data/adapters/tushare.py
central_data/normalize.py
central_data/validate.py
central_data/writer.py
central_data/backup.py
central_data/postcheck.py
central_data/cli.py

Targets, not rigid quotas: one CLI; one config format; one bulk writer; one short summary; about
1,000–1,600 runtime lines and 600–900 focused test lines.

CONFIG
Use one versioned dataset config: dataset/source ids, target table, fields, natural keys, append/upsert
mode, available-at field, quality checks, backup policy, provider options. Routine work uses no
Ed25519, signed profile, per-batch HG, or duplicated schema/report authority. Schema/key changes are
explicit elevated migrations.

ADAPTER
Refactor Replay into a committed adapter returning rows/Arrow/DataFrame to the writer. Preserve
bounded request/source/retrieval metadata. Never log secrets. Do not discard rows into aggregate-only
receipts and do not use an out-of-Git bridge.

SET-BASED WRITER
- accept Arrow/DataFrame/temp relation;
- one process writer lock;
- at most one recoverable backup per run/day under small rotation;
- one DuckDB transaction;
- reject null/duplicate natural keys;
- classify insert/no-op/conflict set-wise with SQL;
- bulk INSERT/MERGE in a fixed number of statements;
- conflicts -> meta.conflicts;
- one meta.ingest_runs row;
- commit/rollback, reopen, postcheck, short JSON summary.

Forbidden: per-row SELECT and per-row INSERT as the main path.

Keep only:
meta.source_registry
meta.ingest_runs
meta.snapshots
meta.conflicts
meta.schema_versions

BACKUP
Retain about 3–7 recovery points. Test restore on a temporary DB. Avoid repeated full-file hashing of
the same backup. Document safe DuckDB checkpoint/copy procedure.

TESTS
Config validation; set-based insert; idempotent replay; conflict quarantine; rollback injection; lock
contention; backup/restore; reopen/postcheck; secret non-disclosure; adapter-to-writer integration;
routine refusal of schema/key change and large backfill; forbidden-file scan. Include one informational
row-wise versus set-based benchmark.

==================================================
PHASE 2 — SHADOW PARITY
==================================================

Run on a temporary DB copy/schema. Compare actual rows, not receipts:
- row counts, natural-key sets, values/hashes;
- insert/no-op/conflict classification;
- date/null/duplicate checks;
- rollback, backup restore, reopen/postcheck;
- timing/I/O as informational evidence.

Cases: new rows, exact replay, conflicting key, partial response, failure before commit, invalid schema,
held lock, and one bounded production-shaped same-source/same-schema batch.

Pass requires no unexplained row/key/value difference, clean rollback, successful restore, passing
postchecks, committed evidence, and no temporary bridge.

Essential legacy collection may continue while shadowing. Do not add new legacy layers. Each snapshot
must record its writer. Block unsafe batches instead of improvising another bridge.

==================================================
PHASE 3 — CUTOVER AND LEGACY REDUCTION
==================================================

Cutover only after Phase 1 tests, shadow parity, restore, 2–3 successful bounded runs, user approval,
and one external audit of writer/cutover evidence.

At cutover: switch routine increments to the one CLI; tag legacy; retain short read-only rollback
window; publish rollback commands; update registry/docs; then remove old entry points.

After parity:
KEEP focused quality validators and transaction/idempotency tests.
REWRITE contracts -> one config, Replay -> adapter, routine_append -> bulk writer, cli -> one CLI.
ARCHIVE collector.py, SQLite storage, publisher copy/swap, remediation runtime, a0 route mechanics,
inactive deployment templates, retired crypto/path tests.
DELETE FROM ACTIVE SURFACE authorization.py, publish_authorization.py, publisher_cli.py,
routine_append_cli.py, tushare_replay_cli.py, per-lane receipts, duplicated signed schemas.

Archive means preserve immutable Git history/tag while removing active imports, entry points, and CI.

==================================================
CONTROLLER AND CI SIMPLIFICATION
==================================================

Routine flow:
User/Manager objective -> one executor -> automatic checks -> short callback.

For same-source/same-schema forward increments remove prompt-inbox copies, per-operation task folders,
separate dispatcher/acceptance conversations, per-task HG, process audit, external audit, and repeated
registry refresh when repo/schema are unchanged.

Keep one project registry, one status board, one high-risk decision log, milestone refs, concise
callbacks.

Risk classes:
ROUTINE = same source/schema/key, forward append/upsert; executor + checks + callback.
ELEVATED = new source, schema/key change, large backfill, overwrite/delete, DB move; approval + dry run
+ backup + migration test + rollback note + one independent review.
TRADING_BOUNDARY remains separate and forbidden.

Consolidate overlapping Human-Gate/recorded-execution documents into one short active policy and mark
old long-form rules historical.

CI:
central-data-ingestion: one required compile/Ruff/unit/DuckDB-integration/secret-scan job; provider
network tests manual/scheduled.
quant-proj: two jobs, fast and integration; retire separate merge-ref/branch-head jobs unless a real
regression justifies them. Keep CI simplification separate from cutover commits.

==================================================
GATES, GITHUB, AND BOUNDARY
==================================================

Phase 1: one CLI, no crypto/HG dependency in new path, no test/remediation private imports, set-based
writer, focused tests/integration pass, production DB unchanged.
Phase 2: row/key/value parity, replay/conflict/rollback/restore/postcheck pass, bounded production-shaped
shadow batch, no uncommitted bridge.
Phase 3: 2–3 successful runs, user approval, external audit, legacy tag/rollback, remote SHA verified.

Push orchestration to quant-proj and implementation/evidence to central-data-ingestion. Verify:
git diff --check
git status --short --branch
git rev-parse HEAD
git push -u origin "$(git branch --show-current)"
git ls-remote origin "refs/heads/$(git branch --show-current)"

Authorized: minimal writer, temporary shadow DB/schema, backup/restore tests, governance/CI
simplification. Separate approval: production cutover, schema/key change, destructive operation, DB
move, large backfill, legacy deletion before parity. Not authorized: research/backtest change,
recommendation, candidate/readiness, broker/order/paper/live/auto, secret output.

==================================================
STAGED CALLBACKS
==================================================

FREEZE_AND_DISPATCH:
STATUS:
QUANT_PROJ_COMMIT:
TASK_SPEC_URL:
ISSUE_URL:
DATABASE_PROMPT_URL:
LEGACY_FREEZE_STATUS:
CURRENT_DB_IDENTITY:
PART2_PINNED_REFS_STATUS:
NEXT_ACTION:

MINIMAL_PATH_READY:
STATUS:
CENTRAL_DATA_BRANCH:
IMPLEMENTATION_COMMIT:
ONE_CLI_STATUS:
SET_BASED_WRITER_STATUS:
UNIT_TEST_STATUS:
DUCKDB_INTEGRATION_STATUS:
PRODUCTION_DB_MUTATED: false
FIXES_REQUIRED:
NEXT_ACTION:

SHADOW_PARITY:
STATUS:
SHADOW_EVIDENCE_COMMIT:
ROW_KEY_VALUE_PARITY:
IDEMPOTENT_REPLAY:
CONFLICT_STATUS:
ROLLBACK_STATUS:
BACKUP_RESTORE_STATUS:
POSTCHECK_STATUS:
PRODUCTION_DB_MUTATED: false
FIXES_REQUIRED:
NEXT_ACTION:

CUTOVER_PROPOSAL:
STATUS: WAITING_FOR_USER_APPROVAL
SUCCESSFUL_BOUNDED_RUN_COUNT:
CUTOVER_COMMIT:
LEGACY_TAG:
ROLLBACK_URL:
EXTERNAL_AUDIT_URL:
CI_SIMPLIFICATION_STATUS:
CONTROLLER_SIMPLIFICATION_STATUS:
NEXT_ACTION: USER_DECISION_REQUIRED
```
