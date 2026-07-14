# CENTRAL_DB_MINIMALIZATION_SHADOW_MIGRATION_20260714

## Status

`PHASE_1_2_ACCEPTED_CUTOVER_PROPOSAL_WAITING_FOR_USER_APPROVAL`

## Controlling identities

- user-dispatch prompt blob: `3bb3958afcf6a4282e56036da5a5b2a32aba565b`
- prompt-introducing `quant-proj` commit: `a1482e71b13554d53906f4205c4825d2a85fcd5c`
- Part 1 audit commit: `f6e302ce7c37562deaca3a243d1667e84426134e`
- audited central-data commit: `f2d401e42aa8f7cd17a14d94c039f45ba6546d9d`
- architecture verdict: `REBUILD_MINIMAL`
- database content action: `KEEP_AND_MIGRATE_IN_PLACE`
- controller verdict: `SIMPLIFY_NOW`
- tracking issue: https://github.com/2604714984-prog/quant-proj/issues/24
- accepted frozen-base implementation commit/tree: `fdb4da2f8a07e71873bc7295388a2d432d01e849` / `872b81d504999d15cece9dbd597cc2c66c9b07db`
- current-main integration commit/tree: `17f027785b7531534a6286821f9e0048dc633c6a` / `e3a5b0f99ec2d9c829a6a5fe89abf402903c7d83`
- implementation Draft PR: https://github.com/2604714984-prog/central-data-ingestion/pull/24
- implementation PR scope: exactly one commit and 11 files

## Ownership

- Quant Manager owns scope, orchestration, evidence registration, and the cutover decision request.
- dedicated database task `019f5c2a-859e-7ed2-8ecf-e94b84f454cb` owns implementation, temporary-database tests, shadow parity, backup/restore tests, and callbacks.
- Part 2 audit is owned by an external independent auditor. The Manager must not execute, supplement, or accept Part 2.

## Objective

Build one committed path:

```text
provider adapter -> normalize -> validate -> one writer lock -> one backup policy
-> one set-based DuckDB transaction -> reopen/postchecks -> one short run record
```

The existing production DuckDB and legacy collection remain operational during shadow migration.
Existing DB2 issue `#19` and its task/foundation records remain open as legacy context; this migration does not silently close or rewrite them.

## Authorized now

1. Preserve the Phase 0 identity record and label the current path `LEGACY_ACTIVE_DURING_SHADOW_MIGRATION`.
2. Implement the new package on branch `codex/central-db-minimal-writer-shadow-migration-20260714`, based exactly on audited commit `f2d401e42aa8f7cd17a14d94c039f45ba6546d9d`.
3. Add one versioned dataset configuration, one Replay adapter, normalization, validation, set-based writer, backup/restore, postchecks, one CLI, and focused tests.
4. Use only mock, synthetic, fixture, or temporary DuckDB files for Phase 1 tests.
5. Run Phase 2 against an immutable temporary copy or schema. Compare actual row keys and values, not receipts.
6. Push implementation and evidence branches after automated checks and independent read-only acceptance.

## Required Phase 1 behavior

- no Ed25519, per-batch HG, test-fixture trust anchor, remediation-private import, or receipt hierarchy in the new routine path;
- Arrow, DataFrame, or DuckDB temporary relation input;
- null and duplicate natural keys rejected;
- insert, exact no-op, and differing-value conflict classified set-wise;
- a fixed number of bulk SQL statements rather than per-row lookup/insert;
- conflicts recorded in `meta.conflicts`;
- one run recorded in `meta.ingest_runs`;
- one transaction with rollback on any failure;
- post-commit reopen and row/date/null/duplicate checks;
- short secret-free JSON summary;
- routine refusal of schema/key changes and unapproved large backfills.

## Required Phase 2 cases

- new rows;
- exact replay;
- conflicting natural key;
- partial provider response;
- injected failure before commit;
- invalid schema;
- held writer lock;
- one production-shaped, same-source/same-schema batch using existing local rows or fixtures;
- backup restore and reopened postchecks.

Pass requires no unexplained row/key/value difference, clean rollback, successful restore, no production-DB mutation by the migration, and no uncommitted bridge.

## Separate user approval

- production cutover or any live write by the new path;
- schema/key change, DB move, large backfill, overwrite, delete, or production backup pruning;
- removing legacy imports, entry points, modules, or CI from the active surface;
- merging to protected/default branches;
- any new provider/network request.

## Prohibited

- research, backtest, strategy formula, split, conclusion, or outcome changes;
- recommendation, candidate/readiness promotion, or broker/order/paper/live/auto work;
- secrets, raw responses, DuckDB, SQLite, Parquet, backups, or private grants in Git;
- using the moving production DB as the shadow target;
- using either stale alternate lock path instead of `/home/rongyu/workspace/quant_data/.locks/quant_research.duckdb.writer.lock`;
- adding another writer lane, signature format, HG format, schema authority, receipt hierarchy, or temporary bridge.

## Stop condition

Stop after committed Phase 1/2 evidence at:

```text
CUTOVER_PROPOSAL: WAITING_FOR_USER_APPROVAL
```

No cutover is implied by shadow parity.
