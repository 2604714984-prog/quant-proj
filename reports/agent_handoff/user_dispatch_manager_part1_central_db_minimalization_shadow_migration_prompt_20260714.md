# User-Dispatch Prompt — Manager Part 1 Central-Database Minimalization and Shadow Migration

Copy the complete fenced prompt below into the user-controlled Quant Manager conversation.

```text
RUN MANAGER_REPOSITORY_AUDIT_PART1_CENTRAL_DB_MINIMALIZATION_SHADOW_MIGRATION_20260714

WORKSTREAM:
QUANT_MANAGER_USER_CONTROLLED_ARCHITECTURE_SIMPLIFICATION

CONTROL

This Manager workstream is controlled by the user.
The Manager owns decomposition, dependency ordering, task publication, database-dialogue dispatch,
callback registration, and acceptance coordination.

The dedicated central-database conversation owns implementation, testing, shadow runs, database
backups, migration execution, and snapshot publication.

The Manager must not:

- modify A-share or US strategy formulas;
- alter backtest-engine behavior before the Part 2 audit findings;
- choose strategy winners or regime thresholds;
- promote strategy candidates;
- activate broker/order/paper/live/auto paths;
- expose credentials or database binaries;
- delete legacy database code before shadow parity and rollback are proven.

==================================================
AUTHORITATIVE PART 1 AUDIT
==================================================

LATEST REPORT:
https://github.com/2604714984-prog/quant-proj/blob/main/reports/external_audit/repository_wide_architecture_and_central_db_lightweight_audit_part1_20260714.md

IMMUTABLE REPORT:
https://github.com/2604714984-prog/quant-proj/blob/f6e302ce7c37562deaca3a243d1667e84426134e/reports/external_audit/repository_wide_architecture_and_central_db_lightweight_audit_part1_20260714.md

AUDITED CENTRAL-DATA REF:
repository: https://github.com/2604714984-prog/central-data-ingestion
PR: https://github.com/2604714984-prog/central-data-ingestion/pull/22
commit: f2d401e42aa8f7cd17a14d94c039f45ba6546d9d

AUDITED CONTROLLER ADDENDUM REF:
repository: https://github.com/2604714984-prog/quant-proj
PR: https://github.com/2604714984-prog/quant-proj/pull/22
commit: 0e90a2647a84010476470d83ebee017db7f5d20b

PART 1 VERDICT:

ARCHITECTURE_VERDICT: REBUILD_MINIMAL
DATABASE_CONTENT_ACTION: KEEP_AND_MIGRATE_IN_PLACE
CONTROLLER_VERDICT: SIMPLIFY_NOW
CURRENT_ARCHITECTURE: DISPROPORTIONATE_FOR_PERSONAL_PROJECT

==================================================
EXECUTION DECISION — RUN PART 1 CHANGES AND PART 2 AUDIT IN PARALLEL
==================================================

EXECUTION_MODE:
PARALLEL_WITH_HARD_SCOPE_BOUNDARIES

Do not wait for all Part 1 modifications to finish before the Part 2 backtest/validation audit starts.
Run them in parallel because they affect different risk domains.

PART 1 MAY CHANGE:

- `central-data-ingestion` ingestion/writer/backup/postcheck/CLI code;
- central-database operational metadata and migration tooling;
- `quant-proj` routine governance, task-flow, CI, and runbook simplification;
- database-dialogue prompts and Manager orchestration files.

PART 1 MUST NOT CHANGE:

- A-share or US backtest-engine code;
- strategy selection code;
- validation/test split logic;
- research conclusions;
- accepted data semantics used by a pinned Part 2 audit target;
- existing central database contents except through separately authorized shadow/cutover steps.

PART 2 AUDIT COORDINATION:

1. Pin exact commits for every research/backtest repository before Part 2 review.
2. Do not rewrite those commits while they are being audited.
3. If a critical corruption or secret issue is found, create a narrow emergency patch and preserve the
   original audit ref.
4. Any schema-semantic change that would alter backtest inputs is elevated work and must be versioned
   as a new snapshot; do not silently mutate the audit dataset.
5. Continue ordinary essential data collection, but prohibit new writer lanes, signature formats,
   authorization layers, or parallel schema authorities.

==================================================
PRIMARY OBJECTIVE
==================================================

Replace the current multi-path central-database runtime with one minimal, durable path suitable for:

- one user;
- one WSL host;
- one local DuckDB;
- research-only operation;
- approximately CNY 400,000 capital;
- no multi-tenancy, SLA, regulatory platform, or live-trading route.

Target routine flow:

provider adapter
  -> normalize
  -> validate
  -> one writer lock
  -> one backup when required
  -> one set-based DuckDB transaction
  -> postchecks
  -> one short run record

Do not rebuild or discard the existing database contents.
Do not interrupt necessary data collection while the new path is being built and shadow-tested.

==================================================
PHASE 0 — FREEZE, STOP EXPANSION, AND PUBLISH THE TASK
==================================================

Immediately perform the following governance freeze:

1. Freeze the current central-data audit ref, current production branch, and current DuckDB identity.
2. Record current database path, size, SHA-256, relation count, backup location, and active writer path.
3. Prohibit new:
   - runtime writer lanes;
   - signature/profile formats;
   - HG/capability formats;
   - publisher implementations;
   - overlapping staging stores;
   - per-lane receipt schemas;
   - ordinary-task acceptance layers.
4. Allow only critical repairs and completion of already-running essential data collection.
5. Mark the existing architecture `LEGACY_ACTIVE_DURING_SHADOW_MIGRATION`.

Create and push in `quant-proj`:

- `tasks/in_progress/central-db-minimalization-shadow-migration-20260714/spec.md`;
- `reports/workspace_dispatch/central_db_minimalization_shadow_migration_intake_20260714.md`;
- `reports/workspace_dispatch/central_db_minimalization_shadow_migration_status_20260714.md`;
- `reports/agent_handoff/central_db_minimalization_shadow_migration_database_prompt_20260714.md`;
- `reports/central_database/manager/central_db_minimalization_decision_log_20260714.md`;
- `reports/central_database/manager/central_db_minimalization_parity_board_20260714.csv`.

Create a GitHub issue in `quant-proj` titled:

`CENTRAL_DB_MINIMALIZATION_SHADOW_MIGRATION_20260714`

The issue must link the Part 1 audit, task spec, implementation branch, status board, and callbacks.

==================================================
PHASE 1 — BUILD THE MINIMAL PATH ON AN ISOLATED BRANCH
==================================================

Create a new central-data branch:

`codex/central-db-minimal-writer-shadow-migration-20260714`

Do not modify or delete the legacy path during this phase.

Target active package structure:

```text
central_data/
  __init__.py
  config.py
  adapters/
    __init__.py
    tushare.py
  normalize.py
  validate.py
  writer.py
  backup.py
  postcheck.py
  cli.py
```

A different minimal name is acceptable only if the same responsibilities remain clear.

Target scope:

- approximately 1,000–1,600 runtime lines;
- approximately 600–900 focused test lines;
- one operational CLI;
- one dataset config format;
- one bulk writer;
- one short run summary.

Do not treat line count as a pass/fail gate. Use it as a strong maintainability target and document
any justified excess.

==================================================
PHASE 1A — ONE DATASET CONFIG AS DECLARATIVE AUTHORITY
==================================================

Replace signed operational profiles, duplicated field maps, and multiple schemas with one simple
versioned dataset configuration.

Each dataset config should contain only necessary fields such as:

```text
dataset_id
source_id
target_schema
target_table
fields
natural_keys
mode: append | upsert
available_at_field
snapshot_policy
backup_policy
quality_checks
provider_options
```

Rules:

- physical DuckDB schema and constraints remain enforced truth;
- config is the operational declaration;
- reports and run summaries are generated from config and database facts;
- no Ed25519 signature;
- no one-use HG file for routine same-source/same-schema increments;
- no duplicated JSON schema/profile/report authority.

Schema/key changes remain elevated and require an explicit migration.

==================================================
PHASE 1B — PROVIDER ADAPTER AND DIRECT ROW HANDOFF
==================================================

Refactor the accepted Tushare Replay path into a provider adapter that returns normalized rows or an
Arrow/DataFrame object directly to the writer.

Requirements:

- secret read only from environment or owner-only private file;
- secret value never logged or serialized;
- bounded request/date/symbol scope;
- source and retrieval metadata;
- timeout and rate-limit behavior;
- no central write inside the adapter;
- no aggregate-only receipt that discards the rows needed by the writer;
- no temporary bridge outside Git.

The durable path must be reproducible from committed code:

```text
adapter.fetch -> normalize -> validate -> writer.write
```

==================================================
PHASE 1C — SET-BASED BULK DUCKDB WRITER
==================================================

Rebuild `routine_append` functionality as one minimal bulk writer.

Required behavior:

1. Accept an Arrow table, DataFrame, or temporary relation.
2. Acquire one process-level writer lock.
3. Create at most one recoverable backup for the mutation run, subject to daily/run rotation policy.
4. Begin one DuckDB transaction.
5. Register incoming rows as a temporary relation.
6. Validate schema and natural-key nulls/duplicates.
7. Classify rows set-wise:
   - inserts;
   - exact no-ops;
   - conflicting existing natural keys.
8. Write inserts/upserts in one or a small fixed number of SQL statements.
9. Write conflicts to `meta.conflicts`.
10. Write one row to `meta.ingest_runs`.
11. Commit or rollback atomically.
12. Reopen the database and execute postchecks.
13. Emit one short JSON summary.

Forbidden implementation pattern:

- one `SELECT` per incoming row;
- one `INSERT` per incoming row;
- Python loops as the primary key classification mechanism.

Required metadata schema only:

```text
meta.source_registry
meta.ingest_runs
meta.snapshots
meta.conflicts
meta.schema_versions
```

Do not recreate the old routine-append receipt/checkpoint/HG table hierarchy under new names.

==================================================
PHASE 1D — BACKUP AND ROLLBACK POLICY
==================================================

Keep backup safety but remove repeated whole-database work.

Required policy:

- one backup per mutation run, or one reusable backup per UTC/local day for small routine increments;
- explicit rotation, initially 3–7 recent recovery points;
- backup path excluded from Git;
- backup creation recorded once in the run record;
- restore command tested on a temporary database;
- no repeated full-file hashing of the same backup multiple times in one run;
- one source hash and one final backup verification are sufficient unless a failure is detected.

For DuckDB, test whether `CHECKPOINT` plus one copied closed database is safer/faster than copying an
open file. Document the chosen procedure.

==================================================
PHASE 1E — POSTCHECKS AND RUN RECORD
==================================================

Minimum postchecks:

- inserted/no-op/conflict counts;
- natural-key duplicate count;
- null checks on required fields;
- min/max date;
- expected symbol/session coverage when applicable;
- source and snapshot id;
- database reopen succeeds;
- affected-row sample/hash or deterministic aggregate hash;
- schema version matches config.

One run record is enough. Suggested fields:

```text
run_id
dataset_id
source_id
started_at
finished_at
status
snapshot_id
input_rows
inserted_rows
noop_rows
conflict_rows
min_date
max_date
backup_path
config_version
source_hash
query_hash
error_summary
```

Do not generate multiple nested receipts unless a specific elevated migration requires them.

==================================================
PHASE 1F — FOCUSED TESTS
==================================================

Required tests:

1. import safety;
2. config validation;
3. natural-key duplicate/null rejection;
4. set-based insert;
5. idempotent replay;
6. conflicting natural key quarantine;
7. transaction rollback under injected failure;
8. writer lock contention;
9. backup creation and temporary restore;
10. database reopen/postcheck;
11. secret not logged;
12. adapter-to-writer end-to-end fixture;
13. schema migration refusal on routine path;
14. historical backfill classified as elevated;
15. database/raw files excluded from Git.

At least one DuckDB integration test must validate the full minimal path.

Add an informational benchmark comparing the new set-based path to the legacy row-wise path on a
small fixture. Functional correctness is the gate; benchmark speed is not a hard release threshold.

==================================================
PHASE 2 — SHADOW RUN AND PARITY
==================================================

After Phase 1 tests pass, shadow the minimal path without replacing production routine writes.

Shadow options:

- a temporary DuckDB copy;
- an isolated temporary schema;
- a bounded snapshot clone.

For identical input, compare:

- accepted row count;
- natural-key set;
- inserted/no-op/conflict classification;
- affected-row values/hashes;
- min/max dates;
- null/duplicate results;
- rollback result;
- backup/restore result;
- final database reopen;
- elapsed time and I/O as informational metrics.

Required shadow cases:

1. new rows;
2. exact idempotent replay;
3. conflicting same-key rows;
4. partial provider response;
5. failure before commit;
6. failure after temporary relation creation;
7. invalid schema;
8. locked writer;
9. one real bounded same-source/same-schema daily batch, using a safe copy or temporary schema.

Do not compare the new path only against the legacy path's receipts. Compare actual database rows and
natural keys.

Shadow acceptance requires:

- no unexplained data difference;
- rollback leaves target unchanged;
- backup restores correctly;
- postchecks pass;
- no secret or raw database enters Git;
- short callback and immutable commits exist.

==================================================
PHASE 2B — CONTINUOUS DATA COLLECTION DURING MIGRATION
==================================================

Do not pause necessary data collection by default.

While shadow parity is incomplete:

- existing accepted routine collection may continue;
- no new architecture layer may be added to the legacy path;
- each legacy production mutation must still use lock, backup, transaction, and postcheck;
- newly fetched data may be staged for later minimal-writer import when safe;
- non-urgent canonical writes should prefer the shadow path once it is stable;
- data callbacks must record which writer produced each snapshot.

If the current legacy writer is operationally unsafe for a specific batch, stop that batch and return a
blocker rather than improvising another temporary bridge.

==================================================
PHASE 3 — CUTOVER AND ACTIVE-SURFACE REDUCTION
==================================================

Cutover is allowed only after:

- all Phase 1 tests pass;
- shadow parity passes;
- backup/restore passes;
- at least 2–3 consecutive bounded routine runs succeed;
- the user approves the cutover;
- one external review of the new writer/cutover evidence is completed.

At cutover:

1. switch same-source/same-schema routine increments to the one new CLI;
2. retain the legacy path read-only for a short rollback window;
3. tag the last legacy state;
4. record rollback commands;
5. update source registry and Manager prompts;
6. remove old CLI entry points from `pyproject.toml`;
7. archive or delete active legacy modules according to the Part 1 decision table.

Module actions after cutover:

KEEP:

- focused validation logic from `quality.py`;
- minimal package exports;
- high-value transaction/idempotency tests.

SIMPLIFY/REWRITE:

- `contracts.py` -> one config-driven contract;
- `tushare_replay.py` -> provider adapter;
- `routine_append.py` -> minimal bulk writer;
- `cli.py` -> one operational CLI;
- source registry -> one live registry.

ARCHIVE FROM ACTIVE PACKAGE:

- `collector.py`;
- `storage.py` and SQLite staging;
- `publisher.py` copy/swap path;
- `remediation.py` one-time runtime;
- `a0_route_mechanics.py`;
- inactive deployment templates;
- crypto/path-attack test suites whose only target is retired code.

DELETE FROM ACTIVE SURFACE AFTER PARITY:

- `authorization.py` routine HG path;
- `publish_authorization.py` custom Ed25519/capability system;
- `publisher_cli.py`;
- `routine_append_cli.py`;
- `tushare_replay_cli.py`;
- per-lane routine receipts and duplicated signed schemas.

`ARCHIVE` means preserve through immutable Git tags/history and remove from active imports/CLI/tests.

==================================================
CONTROLLER AND GOVERNANCE SIMPLIFICATION
==================================================

The default personal-project flow must become:

```text
User/Manager defines objective
  -> one executor performs work
  -> automatic checks
  -> short callback
```

For routine same-source/same-schema forward increments, remove the requirement for:

- copying the prompt to an inbox file;
- a dedicated task directory;
- a separate dispatcher conversation;
- a separate deterministic acceptance conversation;
- per-task Human-Gate/HG record;
- Codex process audit;
- ChatGPT external audit;
- repeated registry refresh when the same pinned repository and schema are unchanged.

Keep only:

- one project registry;
- one current status board;
- one high-risk decision log;
- immutable refs for milestone audits;
- concise callbacks.

Use three risk classes:

ROUTINE:

- same source;
- same schema;
- fixed natural key;
- forward incremental range;
- insert/upsert only.

Flow: executor + automatic checks + short callback.

ELEVATED:

- new source;
- schema/key change;
- large historical backfill;
- overwrite/delete;
- physical database move.

Flow: user/Manager approval + dry run + backup + migration tests + rollback note + one independent
review.

TRADING_BOUNDARY:

- broker/order/paper/live/auto and recommendation activation remain separate and forbidden unless the
user opens a new explicit stage.

Consolidate Human-Gate and recorded-execution rules into one short active policy. Mark superseded
long-form documents historical instead of maintaining overlapping active rules.

==================================================
CI SIMPLIFICATION
==================================================

CENTRAL-DATA REPOSITORY:

Use one required PR job containing:

```text
compile
Ruff
focused unit tests
one DuckDB integration test
secret/forbidden-file scan
```

Use one manual/scheduled provider-network job only where necessary.

QUANT-PROJ:

Reduce ordinary PR CI to two required jobs:

1. `fast`: parse, compile, Ruff, focused tests, secret scan;
2. `integration`: registry and fixture validation.

Record tested commit/merge identity inside job output. Retire separate merge-ref and branch-head jobs
unless a concrete regression proves they are needed.

Do not change CI on the same commit that performs production writer cutover; separate CI
simplification from cutover for easier rollback.

==================================================
PART 2 PARALLEL-AUDIT GUARDRAILS
==================================================

While this task runs, the repository-wide Part 2 audit of backtest and validation reliability proceeds
in parallel.

Manager responsibilities:

- publish pinned audit refs for all research repositories;
- block unrelated edits to those exact audit branches until Part 2 evidence is captured;
- allow new development branches, but do not replace the pinned refs;
- do not dispatch broad backtest-engine fixes before Part 2 verdict;
- preserve central database snapshot ids and data semantics used by the audit;
- expose any data changes as new immutable snapshots;
- report any interaction between database migration and backtest inputs immediately.

The Part 1 task may complete Phase 1 and Phase 2 before Part 2 finishes. Routine-writer cutover may also
proceed after its own acceptance because it does not require a strategy conclusion, provided database
schema/data semantics are unchanged and the rollback path is proven.

==================================================
ACCEPTANCE GATES
==================================================

PHASE 1 GATES:

- minimal source package complete;
- one operational CLI;
- no custom crypto/HG dependency;
- no test/remediation private dependency;
- set-based writer implementation;
- focused test suite pass;
- DuckDB integration pass;
- secret/forbidden-file scan pass;
- no database content mutation in production.

PHASE 2 GATES:

- shadow row/natural-key parity;
- idempotent replay parity;
- conflict classification accepted;
- rollback and restore pass;
- postchecks pass;
- performance evidence recorded;
- at least one production-shaped bounded shadow batch;
- no temporary uncommitted bridge.

PHASE 3 GATES:

- 2–3 consecutive successful bounded runs;
- user cutover approval;
- external review of new writer/cutover evidence;
- legacy rollback window defined;
- old entry points removed only after cutover;
- GitHub refs and remote SHAs verified.

==================================================
MANDATORY GITHUB PUBLICATION
==================================================

Manager must publish orchestration files before dispatch.
The database conversation must push source/tests/evidence for every phase.

Required repositories:

- `quant-proj`: task, issue, status, prompts, callback registry;
- `central-data-ingestion`: minimal implementation, tests, shadow evidence, migration notes.

Do not commit:

- DuckDB/SQLite files;
- database backups;
- raw provider payloads;
- Parquet caches;
- `.env`;
- credentials, tokens, private keys, connection strings;
- unbounded logs or temporary worktrees.

Required remote verification:

```bash
git diff --check
git status --short --branch
git rev-parse HEAD
git push -u origin "$(git branch --show-current)"
git ls-remote origin "refs/heads/$(git branch --show-current)"
```

==================================================
BOUNDARY
==================================================

Authorized:

- central-database ingestion/writer simplification;
- backup/restore and shadow tests;
- same-source/same-schema shadow writes on temporary DB/schema;
- routine governance and CI simplification;
- code, tests, reports, manifests, and task publication.

Requires separate user approval:

- production cutover;
- active schema/key change;
- destructive overwrite/delete;
- physical DB move;
- historical backfill beyond the frozen batch;
- legacy code deletion before parity.

Not authorized:

- strategy selection or modification;
- backtest-engine changes before Part 2 findings;
- recommendation/advice;
- strategy candidate promotion;
- readiness/product route;
- broker/order/paper/live/auto;
- secret output.

==================================================
STAGED MANAGER CALLBACKS
==================================================

CALLBACK 1 — FREEZE AND DISPATCH

CALLBACK_ENVELOPE:
BATCH: MANAGER_REPOSITORY_AUDIT_PART1_CENTRAL_DB_MINIMALIZATION_SHADOW_MIGRATION_20260714
STAGE: FREEZE_AND_DISPATCH
STATUS:
QUANT_PROJ_BRANCH:
QUANT_PROJ_COMMIT:
TASK_SPEC_URL:
TRACKING_ISSUE_URL:
DATABASE_DIALOGUE_PROMPT_URL:
LEGACY_ARCHITECTURE_FREEZE_STATUS:
CURRENT_DB_IDENTITY:
PART2_PINNED_AUDIT_REFS_STATUS:
NEXT_ACTION:

CALLBACK 2 — MINIMAL PATH READY

CALLBACK_ENVELOPE:
BATCH: MANAGER_REPOSITORY_AUDIT_PART1_CENTRAL_DB_MINIMALIZATION_SHADOW_MIGRATION_20260714
STAGE: MINIMAL_PATH_READY
STATUS:
CENTRAL_DATA_BRANCH:
IMPLEMENTATION_COMMIT:
IMMUTABLE_COMMIT_URL:
RUNTIME_LINES:
TEST_LINES:
ONE_CLI_STATUS:
SET_BASED_WRITER_STATUS:
CUSTOM_CRYPTO_REMOVED_FROM_NEW_PATH:
UNIT_TEST_STATUS:
DUCKDB_INTEGRATION_STATUS:
PRODUCTION_DB_MUTATED: false
FIXES_REQUIRED:
NEXT_ACTION:

CALLBACK 3 — SHADOW PARITY

CALLBACK_ENVELOPE:
BATCH: MANAGER_REPOSITORY_AUDIT_PART1_CENTRAL_DB_MINIMALIZATION_SHADOW_MIGRATION_20260714
STAGE: SHADOW_PARITY
STATUS:
SHADOW_EVIDENCE_COMMIT:
SHADOW_CASES_RUN:
ROW_PARITY_STATUS:
NATURAL_KEY_PARITY_STATUS:
IDEMPOTENT_REPLAY_STATUS:
CONFLICT_STATUS:
ROLLBACK_STATUS:
BACKUP_RESTORE_STATUS:
POSTCHECK_STATUS:
PERFORMANCE_SUMMARY:
PRODUCTION_DB_MUTATED: false
FIXES_REQUIRED:
NEXT_ACTION:

CALLBACK 4 — CUTOVER_PROPOSAL

CALLBACK_ENVELOPE:
BATCH: MANAGER_REPOSITORY_AUDIT_PART1_CENTRAL_DB_MINIMALIZATION_SHADOW_MIGRATION_20260714
STAGE: CUTOVER_PROPOSAL
STATUS: WAITING_FOR_USER_APPROVAL
SUCCESSFUL_BOUNDED_RUN_COUNT:
CUTOVER_COMMIT:
LEGACY_TAG:
ROLLBACK_COMMANDS_URL:
EXTERNAL_REVIEW_URL:
CI_SIMPLIFICATION_STATUS:
CONTROLLER_SIMPLIFICATION_STATUS:
PROPOSED_CUTOVER_TIME:
FIXES_REQUIRED:
NEXT_ACTION: USER_DECISION_REQUIRED

FINAL CALLBACK — POST-CUTOVER

CALLBACK_ENVELOPE:
BATCH: MANAGER_REPOSITORY_AUDIT_PART1_CENTRAL_DB_MINIMALIZATION_SHADOW_MIGRATION_20260714
STAGE: POST_CUTOVER
STATUS:
ACTIVE_WRITER:
ACTIVE_CLI:
PRODUCTION_SNAPSHOT_ID:
CUTOVER_COMMIT:
LEGACY_READ_ONLY_WINDOW:
ARCHIVED_MODULES:
DELETED_ACTIVE_ENTRYPOINTS:
BACKUP_STATUS:
ROLLBACK_STATUS:
QUALITY_GATE_STATUS:
PART2_AUDIT_STATUS:
BOUNDARY_RESULT:
FIXES_REQUIRED:
NEXT_ACTION:
```
