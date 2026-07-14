# Repository-wide Audit — Part 1

## Architecture, governance process, and central-database lightweight redesign

**Audit date:** 2026-07-14  
**Scope:** personal research project; one owner; one WSL host; one local DuckDB; approximately CNY 400,000 capital; no live-trading route in scope.

## Audit identities

### Central database implementation

- repository: `2604714984-prog/central-data-ingestion`
- draft PR: `#22`
- branch: `agent/central-db-lean-architecture-audit-20260714`
- commit: `f2d401e42aa8f7cd17a14d94c039f45ba6546d9d`
- tree: `6f9692d9efafe2ee0f3521d774635e45121aefde`

### Controller addendum

- repository: `2604714984-prog/quant-proj`
- draft PR: `#22`
- branch: `agent/central-db-external-audit-addendum-20260714`
- commit: `0e90a2647a84010476470d83ebee017db7f5d20b`

## Method

- repository-wide tracked-file inventory through the frozen audit manifests;
- risk-based line-level semantic review of write paths, acquisition paths, authorization, backup, locking, provenance, task dispatch, acceptance, and CI;
- cross-file consistency review of README, runtime entry points, runbooks, registries, and external-audit claims;
- bounded dynamic reproduction of row-wise versus set-based DuckDB ingestion;
- no database mutation, provider request, credential access, or source-repository edit.

Low-risk reports and static profile artifacts were reviewed through their manifests, schemas, and architectural role. Line-level review concentrated on the runtime and governance files capable of causing data corruption, operational delay, duplicated authority, or maintenance friction.

# SCOPE RESULT

## Overall architecture verdict

`REBUILD_MINIMAL`

This verdict applies to the **ingestion and governance code path**, not to deleting or rebuilding the existing DuckDB contents.

## Controller/governance verdict

`SIMPLIFY_NOW`

## Proportionality verdict

`CURRENT_ARCHITECTURE_DISPROPORTIONATE_FOR_PERSONAL_PROJECT`

The current controls are closer to a multi-role institutional change-management system than to a reliable personal research warehouse.

# FILES AND COMMITS REVIEWED

The audit covered the frozen PRs and the highest-risk active files, including:

- `central_data_ingestion/routine_append.py`
- `central_data_ingestion/publisher.py`
- `central_data_ingestion/publish_authorization.py`
- `central_data_ingestion/remediation.py`
- `central_data_ingestion/a0_route_mechanics.py`
- `central_data_ingestion/tushare_replay.py`
- `central_data_ingestion/authorization.py`
- `central_data_ingestion/collector.py`
- `central_data_ingestion/storage.py`
- `central_data_ingestion/contracts.py`
- `central_data_ingestion/quality.py`
- `central_data_ingestion/cli.py`
- `central_data_ingestion/publisher_cli.py`
- `central_data_ingestion/routine_append_cli.py`
- `central_data_ingestion/tushare_replay_cli.py`
- `pyproject.toml`
- `README.md`
- central source registry, provider profiles, audit evidence, and schemas
- `quant-proj/README.md`
- `quant-proj/AGENTS.md`
- `runbooks/human_gate.md`
- `runbooks/recorded_execution_mode.md`
- `runbooks/registry_refresh.md`
- `prompts/task_dispatcher.md`
- `registry/agents.yaml`
- `registry/projects.yaml`
- task board and consolidated external-audit package
- CI runs attached to both audit PR heads.

# STATIC FINDINGS

## 1. The repository has multiple overlapping ingestion/publication systems

At least four paths overlap:

1. the original SQLite staging collector;
2. the Gate-B copy/swap publisher;
3. the signed `routine_append` writer;
4. the Replay qualification adapter plus an uncommitted temporary bridge.

There is no single durable path from:

```text
provider response -> normalized rows -> canonical DuckDB write
```

The only successful Replay append used a temporary bridge outside Git, while the durable Replay adapter intentionally retained zero rows. This is the clearest sign that the architecture optimizes its control documents more successfully than its core data flow.

## 2. The active runtime is too large for the actual operating scope

Frozen inventory:

- 19 production Python modules;
- 6,689 runtime lines;
- 9 test files and 3,425 test lines;
- 34 JSON profiles/schemas/packets/reports;
- 5 deployment templates.

The largest runtime modules are control-heavy rather than provider or normalization logic:

- `publisher.py`: 1,237 lines;
- `routine_append.py`: 1,159 lines;
- `remediation.py`: 869 lines;
- `tushare_replay.py`: 617 lines;
- `a0_route_mechanics.py`: 587 lines;
- `publish_authorization.py`: 576 lines.

## 3. The routine writer is set-oriented database work implemented row by row

`routine_append.py` performs one natural-key lookup per incoming row and then inserts accepted rows one at a time. This increases runtime, failure surface, code size, and verification complexity.

A temporary DuckDB relation plus one anti-join or `MERGE` can classify inserts/no-ops/conflicts in one set operation and write in one statement.

## 4. Backup and hash policy performs excessive whole-database work

The live database is approximately 2.4 GB. The checkpoint implementation copies the whole database and repeatedly hashes the target before and after publication.

One checkpoint logically processes approximately four database-sized streams:

```text
read source + write target + verify target + verify published target
```

That is roughly 9.6 GB of logical I/O for a 2.4 GB database before the actual ingest work. This is unjustified for every profile/day in a single-user warehouse.

## 5. Custom authorization is more dangerous than the threat it addresses

The repository contains:

- a custom pure-Python Ed25519 verifier;
- signed profiles and batches;
- one-use HG records;
- descriptor-bound receipts;
- symlink/inode/path-replacement defenses;
- controller trust anchors;
- multiple immutable JSON sidecars.

For one operator on one local WSL host, this adds a large security-sensitive code surface. It protects against multi-actor local adversaries that are outside the actual project threat model, while creating its own implementation and maintenance risk.

A local routine job needs file permissions, a single writer lock, explicit CLI flags, a transaction, and a short run record—not a custom capability system.

## 6. Production logic depends on test or remediation internals

`routine_append.py` imports private helpers from `publish_authorization.py` and the writer lock from `remediation.py`. Its trust-anchor path points into `tests/fixtures`.

This is strong evidence that one-time audit/remediation machinery has become part of the production dependency graph.

## 7. There are multiple competing schema authorities

Schema and contract meaning is distributed among:

- Python endpoint allowlists and field rules;
- signed JSON profiles;
- JSON schemas;
- source registry reports;
- physical DuckDB table schemas;
- task packets and acceptance documents.

A personal project should have one declarative dataset configuration and the physical table schema as the enforced truth.

## 8. Documentation and runtime entry points disagree

The central repository README states that the central publisher is not implemented or enabled, while `pyproject.toml` exposes a `central-data-publisher` command and the repository contains a 1,237-line publisher implementation.

The publisher may be test-only, but exposing it as a normal package entry point creates operational ambiguity.

## 9. Source qualification is too far removed from actual ingestion

The source registry is detailed, but accepted canonical datasets remained at zero in the consolidated package. The Replay adapter is capable of qualification but intentionally emits aggregate receipts, stages zero rows, and performs zero central writes.

Source qualification should be a validation stage inside a real adapter, not a separate operational universe.

## 10. Governance duplicates the same controls across many documents and roles

The controller duplicates approval and evidence rules across:

- `AGENTS.md`;
- Human-Gate runbook;
- recorded-execution runbook;
- dispatcher prompt;
- model-routing registry;
- agent registry;
- task specs;
- handoffs;
- dispatch summaries;
- callback envelopes;
- acceptance tasks;
- process audits;
- external audits.

The active role model includes Manager, Dispatcher, Dev, Acceptance, multiple Reasonix roles, Audit, External Audit, and Human Gate. That can be appropriate for a team or regulated platform, but not as the default path for routine work by one person.

## 11. Routine tasks create too many artifacts

The default task flow preserves the raw prompt, classifies multiple dimensions, creates a task directory, spec, handoff, board entry, dispatch summary, callback, acceptance, and sometimes another audit packet.

That overhead is a direct cause of slow strategy and data iteration.

## 12. Green CI proves consistency, not proportionality

The central-data PR passed one sensible job containing compile, Ruff, pytest, and secret scans.

The controller PR passed five jobs, including separate merge-ref, branch-head, integration-identity, and fixture-reproduction jobs. These checks are internally consistent, but they do not prove that the surrounding governance model is appropriate.

# DYNAMIC REPRODUCTIONS

## 1. Synthetic DuckDB row-write benchmark

Environment:

- DuckDB 1.5.4;
- in-memory database;
- 500 synthetic daily rows;
- three repetitions;
- same natural key and schema.

Median results:

```text
row-wise SELECT + INSERT: 1.0927 s
bulk anti-join INSERT:     0.0769 s
speed ratio:               14.2x
```

Idempotent/no-op replay:

```text
row-wise key SELECTs:      0.5864 s
set-based anti-join:       0.0885 s
speed ratio:               6.6x
```

This is not a production throughput benchmark. It reproduces the direction and magnitude of the architectural problem: Python/database round-trips dominate small batches that DuckDB can classify set-wise.

## 2. Existing live append evidence

The frozen evidence records a successful append of:

- 5,524 daily rows;
- 60 partial daily-basic rows;
- zero duplicate natural keys;

using two requests, one backup, one writer lock, one transaction, and postchecks. The repository path that performed the actual conversion/write was not preserved in Git.

The dynamic evidence therefore supports a simpler durable writer, not the existing multi-path system.

# CRITICAL BUGS AND HIGH-RISK DESIGN DEFECTS

## Critical

1. **No durable end-to-end primary path.** The accepted provider boundary does not deliver rows to the accepted writer.
2. **Production dependency on test/remediation internals.** Routine ingestion imports private crypto/remediation helpers and uses a test-fixture trust anchor.
3. **Multiple mutation paths.** Publisher and routine append implement different write/rollback models.
4. **Non-reproducible successful bridge.** The path that completed the useful write is outside Git.

## High

1. row-wise lookup and insert;
2. repeated whole-DB checkpoint/hash work;
3. custom cryptographic authorization;
4. duplicated schema authorities;
5. all-or-nothing batch quarantine around row conflicts;
6. operational ambiguity from test-only entry points;
7. controller workflow requires too many people/agents/artifacts for routine changes.

# MODULE DECISIONS

| Module or group | Decision | Target |
|---|---|---|
| `quality.py` | KEEP | focused validators |
| `contracts.py` | SIMPLIFY | config-driven contract |
| `__init__.py` | KEEP | minimal exports |
| `tushare_replay.py` | SIMPLIFY | provider adapter |
| `routine_append.py` | REBUILD_MINIMAL | one bulk writer |
| `cli.py` | SIMPLIFY | one CLI |
| `collector.py` | ARCHIVE | remove active path |
| `storage.py` | ARCHIVE | retire SQLite staging |
| `authorization.py` | DELETE | no routine HG |
| `publisher.py` | ARCHIVE | remove copy/swap path |
| `publisher_cli.py` | DELETE | remove entry point |
| `publish_authorization.py` | DELETE | remove custom crypto |
| `routine_append_cli.py` | DELETE | merge into one CLI |
| `tushare_replay_cli.py` | DELETE | merge into one CLI |
| `remediation.py` | ARCHIVE | one-time history only |
| `a0_route_mechanics.py` | ARCHIVE | generic smoke helper |
| signed profiles/schemas | SIMPLIFY | one dataset config |
| per-lane receipts | DELETE | one run record |
| deployment templates | ARCHIVE | keep one timer only |
| source registry reports | SIMPLIFY | one live registry |
| crypto/path-attack tests | ARCHIVE | retain Git history |
| core writer tests | KEEP | transaction/idempotency |

`ARCHIVE` means remove from the active package and CLI surface after parity, while preserving the immutable Git tag/branch. It does not require carrying dead runtime files indefinitely.

# MINIMUM SAFETY INVARIANTS TO KEEP

1. credentials in environment or owner-only file; never log values;
2. one process-level writer lock;
3. one recoverable backup per mutation run, with a small rotation;
4. one DuckDB transaction and rollback on error;
5. fixed natural keys and unique constraints;
6. idempotent replay;
7. conflicts written to one quarantine table;
8. row-count, date-range, null, duplicate, and reopen postchecks;
9. source, retrieval time, available time, snapshot id, and content/query hash;
10. explicit schema migration for schema changes;
11. database/raw payloads/secrets excluded from Git;
12. one short run record and one error log.

Controls that are not required for ordinary local ingestion:

- Ed25519 profile signatures;
- per-batch HG files;
- one-use controller capabilities;
- independent model acceptance for every append;
- descriptor-bound multi-artifact receipt chains;
- copy/swap publication;
- multiple whole-database backups per day;
- per-lane external audit;
- task packet directories for same-source/same-schema daily increments.

# TARGET DESIGN

## Package

```text
central_data/
  config.py
  adapters/
    tushare.py
    <future_source>.py
  normalize.py
  validate.py
  writer.py
  backup.py
  postcheck.py
  cli.py
```

Target size:

```text
runtime: 1,000-1,600 lines
tests:     600-900 lines
CLI:       one entry point
routine manifests: one short run record
```

## Database metadata

Keep only a small metadata schema:

```text
meta.source_registry
meta.ingest_runs
meta.snapshots
meta.conflicts
meta.schema_versions
```

Market data remains in market schemas such as:

```text
a_share.*
us.*
macro.*
derived.*
```

## Routine write path

```text
adapter.fetch()
  -> normalize rows
  -> validate batch
  -> acquire one writer lock
  -> create one backup if needed
  -> register incoming Arrow/DataFrame/temp table
  -> classify insert/no-op/conflict with SQL
  -> bulk INSERT or MERGE in one transaction
  -> write meta.ingest_runs
  -> COMMIT
  -> reopen and run postchecks
  -> print one short JSON summary
```

## Risk levels

### Routine

- same source;
- same schema;
- forward incremental range;
- insert/upsert under fixed keys.

Required:

```text
normal CLI command + automatic checks + short report
```

No task packet, signature, independent model acceptance, or external audit.

### Elevated

- new source;
- schema migration;
- key change;
- large historical backfill;
- overwrite/delete;
- physical DB move.

Required:

```text
user/manager approval + dry run + backup + migration test + rollback note
```

### Trading boundary

Remain separate and forbidden. Database simplification does not relax broker/order/paper/live controls.

# CONTROLLER TARGET DESIGN

## Default personal-project flow

```text
User/Manager defines objective
  -> one executor performs work
  -> automatic tests/checks
  -> short callback
```

Add a separate audit only for:

- new central writer;
- schema/key migration;
- destructive operation;
- backtest engine change;
- strategy acceptance milestone;
- trading-system boundary change.

## Remove from ordinary work

- copying every prompt into an inbox file;
- one task directory for every small operation;
- separate dispatcher and acceptance conversations for deterministic work;
- repeated registry refresh before same-repo routine tasks;
- repeated Human-Gate records for routine same-schema ingestion;
- external audit for ordinary research-only increments.

## Keep

- one project registry;
- one current status board;
- one high-risk decision log;
- immutable commit refs for milestone audits;
- concise callbacks.

# CI TARGET

## Central data repository

Keep one PR job:

```text
compile
Ruff
focused unit tests
one DuckDB integration test
secret/forbidden-file scan
```

Add one scheduled or manual integration job only when provider/network fixtures are needed.

## Controller repository

Reduce five PR jobs to two:

1. `fast`: parse, compile, Ruff, unit, secret scan;
2. `integration`: registry and fixture validation.

Exact tested SHA can be recorded inside the job output. Separate merge-ref and branch-head test jobs are not proportionate for this repository.

# MIGRATION PLAN

## Phase 1 — Freeze and build minimal path

- tag/freeze the current PR and database identity;
- stop adding new control modules, signatures, schemas, and runtime lanes;
- implement the minimal adapter/validator/bulk-writer path on a new branch;
- run unit and temporary-DuckDB tests;
- do not delete legacy code yet.

## Phase 2 — Shadow and cut over

- connect Tushare Replay rows directly to the minimal writer;
- shadow-run against a database copy or temporary schema;
- compare counts, natural keys, hashes, conflicts, and rollback;
- switch routine same-source/same-schema writes to the new CLI;
- retain legacy path as read-only fallback for two or three successful runs.

## Phase 3 — Remove active legacy surface

- remove old CLI entry points;
- archive/delete publisher, custom authorization, old SQLite staging, route-smoke, and remediation runtime modules;
- consolidate tests and controller runbooks;
- retain one tag and rollback instructions;
- update Manager and database-conversation prompts to use the minimal flow.

# SHOULD MODIFICATIONS START AFTER PART 1?

`YES, IN A STAGED WAY.`

Do not wait for Parts 2 and 3 before stopping further central-database overdesign. The Manager is actively adding data, so continuing to build on the current framework will multiply migration cost.

Start immediately with:

1. freeze current architecture and database identities;
2. prohibit new runtime lanes, signature formats, task packet layers, or writer implementations;
3. build the minimal writer on a separate branch;
4. keep current data collection operational until shadow parity passes;
5. do not delete or merge legacy paths until rollback and parity are proven.

Part 2—the backtest and validation reliability audit—should proceed in parallel. Part 1 does not authorize changes to research or backtest code; those changes should wait for Part 2 findings.

# VERDICT

```text
ARCHITECTURE_VERDICT: REBUILD_MINIMAL
DATABASE_CONTENT_ACTION: KEEP_AND_MIGRATE_IN_PLACE
CONTROLLER_VERDICT: SIMPLIFY_NOW
ROUTINE_OPERATION_MODEL: USER/MANAGER -> DB EXECUTOR -> AUTOMATED CHECKS -> SHORT CALLBACK
EXTERNAL_AUDIT_FOR_ROUTINE_APPEND: NO
EXTERNAL_AUDIT_FOR_NEW_WRITER_CUTOVER: YES, ONCE
SYSTEM_INTAKE_READY: false
STRATEGY_CANDIDATE_AVAILABLE: false
```

# NEXT ACTION

1. give the Manager a bounded **central-database minimalization and shadow-migration** task;
2. pause further architecture expansion, but do not pause essential data collection;
3. start Part 2 audit in parallel;
4. after shadow parity, cut over routine ingestion and archive legacy code;
5. do not proceed from Part 1 directly into strategy or trading activation.
