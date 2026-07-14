# User-Dispatch Prompt — Manager Part 1 Central-Database Minimalization and Shadow Migration

Copy the complete fenced prompt below into the user-controlled Quant Manager conversation.

```text
RUN MANAGER_REPOSITORY_AUDIT_PART1_CENTRAL_DB_MINIMALIZATION_SHADOW_MIGRATION_20260714

WORKSTREAM:
QUANT_MANAGER_USER_CONTROLLED_ARCHITECTURE_SIMPLIFICATION

AUTHORITATIVE AUDIT:
https://github.com/2604714984-prog/quant-proj/blob/f6e302ce7c37562deaca3a243d1667e84426134e/reports/external_audit/repository_wide_architecture_and_central_db_lightweight_audit_part1_20260714.md

AUDITED CENTRAL-DATA REF:
repo: https://github.com/2604714984-prog/central-data-ingestion
PR: https://github.com/2604714984-prog/central-data-ingestion/pull/22
commit: f2d401e42aa8f7cd17a14d94c039f45ba6546d9d

PART 1 VERDICT:
ARCHITECTURE_VERDICT=REBUILD_MINIMAL
DATABASE_CONTENT_ACTION=KEEP_AND_MIGRATE_IN_PLACE
CONTROLLER_VERDICT=SIMPLIFY_NOW

CONTROL

The user controls this workstream. Manager owns decomposition, task publication, database-dialogue
dispatch, callback tracking, and acceptance coordination. The dedicated database conversation owns
implementation, testing, shadow runs, backups, migration execution, and snapshot publication.

Do not modify strategy formulas, backtest engines, validation splits, or research conclusions in this
task. Do not delete legacy database code before parity and rollback are proven. Do not expose secrets,
raw payloads, database binaries, or backups in Git.

==================================================
EXECUTION DECISION: PART 1 CHANGES AND PART 2 AUDIT RUN IN PARALLEL
==================================================

EXECUTION_MODE=PARALLEL_WITH_HARD_SCOPE_BOUNDARIES

Do not wait for Part 1 to finish before starting the Part 2 backtest/validation audit.

Part 1 may change only:
- central-data-ingestion adapters, normalization, validation, writer, backup, postcheck, CLI, tests;
- central-database metadata and migration tooling;
- quant-proj routine governance, task flow, runbooks, and CI.

Part 1 must not change:
- A-share/US backtest or strategy code;
- validation/test selection logic;
- the semantics of a snapshot pinned for Part 2;
- production database contents except through separately approved shadow/cutover stages.

Manager must pin exact research-repository commits for Part 2. Any DB semantic change must create a
new immutable snapshot, never silently alter an audited input.

==================================================
OBJECTIVE
==================================================

Replace the current multi-path runtime with one personal-project path:

provider adapter
 -> normalize
 -> validate
 -> one writer lock
 -> one backup when required
 -> one set-based DuckDB transaction
 -> postchecks
 -> one short run record

Keep and migrate the existing DuckDB in place. Do not pause essential collection while the new path
is built and shadow-tested. Prohibit any new writer lane, signature format, HG format, parallel schema
authority, or temporary uncommitted bridge.

==================================================
PHASE 0 — FREEZE AND DISPATCH
==================================================

Immediately:
1. Record current central-data branch/commit, active writer, DB path, size, SHA-256, relation count,
   latest backup, and rollback reference.
2. Mark current runtime `LEGACY_ACTIVE_DURING_SHADOW_MIGRATION`.
3. Freeze new control-layer development; allow only critical fixes and already-running essential data
   collection.
4. Create and push in quant-proj:
   - tasks/in_progress/central-db-minimalization-shadow-migration-20260714/spec.md
   - reports/workspace_dispatch/central_db_minimalization_shadow_migration_status_20260714.md
   - reports/agent_handoff/central_db_minimalization_shadow_migration_database_prompt_20260714.md
   - reports/central_database/manager/central_db_minimalization_parity_board_20260714.csv
5. Create issue `CENTRAL_DB_MINIMALIZATION_SHADOW_MIGRATION_20260714` linking the audit, task,
   implementation branch, and callbacks.

==================================================
PHASE 1 — BUILD THE MINIMAL PATH
==================================================

Create branch in central-data-ingestion:
`codex/central-db-minimal-writer-shadow-migration-20260714`

Do not delete or alter legacy active imports during Phase 1.

Target package:

central_data/
  config.py
  adapters/tushare.py
  normalize.py
  validate.py
  writer.py
  backup.py
  postcheck.py
  cli.py

Target maintainability range, not a rigid gate:
- runtime roughly 1,000–1,600 lines;
- focused tests roughly 600–900 lines;
- one operational CLI;
- one dataset-config format;
- one bulk writer;
- one short JSON run summary.

DATASET CONFIG
Use one simple versioned config containing dataset/source ids, target table, fields, natural keys,
append/upsert mode, available-at field, quality checks, backup policy, and provider options.
No Ed25519 signature, per-batch HG, or duplicated profile/schema/report authority for routine work.
Schema/key changes remain elevated migrations.

PROVIDER ADAPTER
Refactor Tushare Replay into a committed adapter that returns normalized rows/Arrow/DataFrame to the
writer. It must retain bounded request metadata but must not discard usable rows into aggregate-only
receipts. No temporary bridge outside Git. Secret values are read privately and never logged.

SET-BASED WRITER
The writer must:
1. accept Arrow/DataFrame/temp relation;
2. acquire one process-level writer lock;
3. create at most one recoverable backup for the mutation run/day under a small rotation;
4. begin one DuckDB transaction;
5. register incoming rows as a temporary relation;
6. reject null/duplicate natural keys;
7. classify inserts/no-ops/conflicts set-wise with SQL;
8. bulk INSERT/MERGE in a fixed number of statements;
9. write conflicts to meta.conflicts;
10. write one meta.ingest_runs row;
11. commit or rollback;
12. reopen and postcheck;
13. print one short summary.

Forbidden: per-row SELECT and per-row INSERT as the primary classification/write path.

Minimal metadata only:
meta.source_registry
meta.ingest_runs
meta.snapshots
meta.conflicts
meta.schema_versions

Do not recreate old receipt/checkpoint/HG hierarchies under new names.

BACKUP
Use one backup per mutation run, or one reusable daily backup for small routine increments, retaining
roughly 3–7 recovery points. Test restore on a temporary DB. Avoid repeated full-file hashing of the
same backup. Document whether DuckDB CHECKPOINT plus a copied closed DB is used.

POSTCHECK
At minimum record inserted/no-op/conflict counts, duplicates, required-field nulls, min/max date,
coverage where relevant, snapshot id, schema version, reopen success, and one affected-row/hash check.

TESTS
Required:
- config validation;
- set-based insert and idempotent replay;
- conflict quarantine;
- rollback under injected failure;
- writer-lock contention;
- backup/restore;
- reopen/postcheck;
- secret not logged;
- adapter-to-writer integration;
- routine path rejects schema/key change and historical-backfill misuse;
- forbidden-file scan.

Include one informational row-wise versus set-based benchmark; correctness is the release gate.

==================================================
PHASE 2 — SHADOW PARITY
==================================================

Shadow on a temporary DB copy/schema. For identical input compare actual database rows, not just
receipts:
- row counts and natural-key sets;
- inserted/no-op/conflict classification;
- affected values/hashes;
- date range and null/duplicate checks;
- rollback and backup restore;
- reopen/postcheck;
- elapsed time/I/O as informational evidence.

Required cases:
1. new rows;
2. exact replay;
3. conflicting same-key rows;
4. partial provider response;
5. failure before commit;
6. invalid schema;
7. writer lock held;
8. one bounded production-shaped same-source/same-schema batch on a safe copy/schema.

Shadow acceptance requires no unexplained row/key/value difference, clean rollback, successful
restore, passing postchecks, committed code/evidence, and no secret/raw DB in Git.

During shadow migration, essential legacy collection may continue. Do not add new layers to legacy.
Every snapshot must record which writer produced it. If a legacy batch is unsafe, block it rather than
creating another temporary bridge.

==================================================
PHASE 3 — CUTOVER AND LEGACY REDUCTION
==================================================

Cutover only after:
- Phase 1 tests pass;
- shadow parity and restore pass;
- 2–3 consecutive bounded runs succeed;
- user approves cutover;
- one external audit of the new writer/cutover evidence passes.

At cutover:
- switch routine same-source/same-schema increments to the new single CLI;
- tag the last legacy state and keep it read-only for a short rollback window;
- publish rollback commands;
- update registry, Manager prompts, and docs;
- remove old CLI entry points only after the switch.

After parity, apply the audit decisions:

KEEP
- focused quality validators;
- minimal exports;
- transaction/idempotency tests.

SIMPLIFY/REWRITE
- contracts.py -> one config-driven contract;
- tushare_replay.py -> provider adapter;
- routine_append.py -> minimal bulk writer;
- cli.py -> one operational CLI;
- source registry -> one live registry.

ARCHIVE FROM ACTIVE PACKAGE
- collector.py and SQLite storage;
- publisher.py copy/swap path;
- remediation.py one-time runtime;
- a0_route_mechanics.py;
- inactive deployment templates;
- crypto/path-attack tests targeting retired code.

DELETE FROM ACTIVE SURFACE AFTER CUTOVER
- authorization.py routine HG path;
- publish_authorization.py custom crypto/capability system;
- publisher_cli.py, routine_append_cli.py, tushare_replay_cli.py;
- per-lane routine receipts and duplicated signed schemas.

Archive means preserve immutable Git history/tag, but remove active imports, CLI entries, and CI.

==================================================
CONTROLLER AND CI SIMPLIFICATION
==================================================

Default routine flow:
User/Manager defines objective -> one executor -> automatic checks -> short callback.

For same-source/same-schema forward increments, remove prompt-inbox copying, per-operation task
folders, separate dispatcher/acceptance conversations, per-task HG, process audit, external audit,
and repeated registry refresh when pinned repo/schema are unchanged.

Keep one project registry, one current status board, one high-risk decision log, milestone commit refs,
and concise callbacks.

Use three risk classes:
- ROUTINE: same source/schema/key, forward append/upsert; executor + checks + callback.
- ELEVATED: new source, schema/key change, large backfill, overwrite/delete, DB move; user/Manager
  approval + dry run + backup + migration tests + rollback note + one independent review.
- TRADING_BOUNDARY: remains separate and forbidden.

Consolidate overlapping Human-Gate and recorded-execution documents into one short active policy;
mark old long-form documents historical.

CI target:
- central-data-ingestion: one required job for compile, Ruff, focused unit tests, one DuckDB
  integration, secret/forbidden scan; network test manual/scheduled.
- quant-proj: two jobs, `fast` and `integration`; retire separate merge-ref/branch-head jobs unless a
  concrete regression justifies them.

Separate CI simplification commits from writer-cutover commits for rollback clarity.

==================================================
ACCEPTANCE AND GITHUB
==================================================

Phase 1 gate: one CLI, no custom crypto/HG dependency in new path, no test/remediation private
imports, set-based writer, focused tests and DuckDB integration pass, production DB unchanged.

Phase 2 gate: row/key/value parity, replay/conflict/rollback/restore/postcheck pass, one bounded
production-shaped shadow batch, no uncommitted bridge.

Phase 3 gate: 2–3 successful runs, user approval, external audit, legacy tag and rollback, remote SHAs
verified.

Push orchestration to quant-proj and implementation/evidence to central-data-ingestion. Never commit
DuckDB/SQLite/Parquet, backups, raw payloads, `.env`, credentials, tokens, private keys, or unbounded
logs.

Required verification:
git diff --check
git status --short --branch
git rev-parse HEAD
git push -u origin "$(git branch --show-current)"
git ls-remote origin "refs/heads/$(git branch --show-current)"

==================================================
BOUNDARY
==================================================

Authorized: minimal writer development, temporary shadow DB/schema, backup/restore tests, governance
and CI simplification, code/tests/reports/task publication.

Separate user approval required: production cutover, active schema/key change, destructive operation,
physical DB move, large historical backfill, legacy deletion before parity.

Not authorized: strategy/backtest changes, recommendation, candidate promotion, readiness/product
route, broker/order/paper/live/auto, or secret output.

==================================================
STAGED CALLBACKS
==================================================

CALLBACK 1 — FREEZE_AND_DISPATCH
BATCH:
STATUS:
QUANT_PROJ_COMMIT:
TASK_SPEC_URL:
ISSUE_URL:
DATABASE_PROMPT_URL:
LEGACY_FREEZE_STATUS:
CURRENT_DB_IDENTITY:
PART2_PINNED_REFS_STATUS:
NEXT_ACTION:

CALLBACK 2 — MINIMAL_PATH_READY
STATUS:
CENTRAL_DATA_BRANCH:
IMPLEMENTATION_COMMIT:
ONE_CLI_STATUS:
SET_BASED_WRITER_STATUS:
CUSTOM_CRYPTO_REMOVED_FROM_NEW_PATH:
UNIT_TEST_STATUS:
DUCKDB_INTEGRATION_STATUS:
PRODUCTION_DB_MUTATED: false
FIXES_REQUIRED:
NEXT_ACTION:

CALLBACK 3 — SHADOW_PARITY
STATUS:
SHADOW_EVIDENCE_COMMIT:
SHADOW_CASES:
ROW_KEY_VALUE_PARITY:
IDEMPOTENT_REPLAY:
CONFLICT_STATUS:
ROLLBACK_STATUS:
BACKUP_RESTORE_STATUS:
POSTCHECK_STATUS:
PERFORMANCE_SUMMARY:
PRODUCTION_DB_MUTATED: false
FIXES_REQUIRED:
NEXT_ACTION:

CALLBACK 4 — CUTOVER_PROPOSAL
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
