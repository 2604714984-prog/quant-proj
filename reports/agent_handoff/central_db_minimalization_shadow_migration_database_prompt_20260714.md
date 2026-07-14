# Database executor prompt — central DB minimal writer shadow migration

## Assignment

- executor task: `019f5c2a-859e-7ed2-8ecf-e94b84f454cb`
- tracking issue: https://github.com/2604714984-prog/quant-proj/issues/24
- manager prompt blob: `3bb3958afcf6a4282e56036da5a5b2a32aba565b`
- audited central-data commit: `f2d401e42aa8f7cd17a14d94c039f45ba6546d9d`
- required branch: `codex/central-db-minimal-writer-shadow-migration-20260714`
- required worktree: `/home/rongyu/workspace/.wt-central-db-minimal-writer-shadow-migration-20260714`

## Execute

1. Preserve the audited legacy code unchanged and label it `LEGACY_ACTIVE_DURING_SHADOW_MIGRATION`.
2. Build `central_data/` with one config, Replay adapter, normalize, validate, writer, backup, postcheck, and CLI path.
3. The adapter must return normalized rows or an Arrow/DataFrame-compatible batch. It must not discard useful rows into aggregate-only receipts and must never expose credential contents.
4. Implement insert/no-op/conflict classification with DuckDB set operations. Per-row `SELECT` and per-row `INSERT` are forbidden as the main path.
5. Use one writer lock, one transaction, one run record, conflict quarantine, rollback, reopen, and concise JSON output.
6. Restrict backup/restore and writer integration tests to temporary files. Retain 3–7 temporary recovery points in the test policy; do not prune production backups.
7. Cover config validation, new rows, exact replay, conflicting values, rollback injection, held lock, backup/restore, reopen/postchecks, secret non-disclosure, adapter-to-writer integration, schema/key/backfill refusal, and forbidden-file scanning.
8. Add an informational row-wise versus set-based benchmark; it is not a pass threshold.
9. Run a production-shaped shadow case from existing local rows or fixtures without calling the provider network and without writing the production database.
10. Return exact file hashes, test commands/results, parity evidence, production DB before/after SHA, and remaining blockers.

## Do not execute

- no production cutover or live write by the new path;
- no provider/network request;
- no schema/key change, DB move, large backfill, overwrite, delete, or production backup pruning;
- no old module deletion, active import switch, entry-point removal, or default-branch merge;
- no research/backtest/outcome work;
- no raw payload, DB, backup, Parquet, credential, key, private grant, or lock file in Git;
- no new HG/signature/receipt/schema-authority/writer lane;
- no temporary bridge outside Git.

## Callback

Stop before commit/push and return:

```text
MINIMAL_PATH_READY:
STATUS: GREEN_PRECOMMIT or BLOCKED
CENTRAL_DATA_BRANCH:
BASE_COMMIT:
EXACT_FILES_AND_SHA256:
ONE_CLI_STATUS:
SET_BASED_WRITER_STATUS:
UNIT_TEST_STATUS:
DUCKDB_INTEGRATION_STATUS:
PRODUCTION_DB_SHA_BEFORE:
PRODUCTION_DB_SHA_AFTER:
PRODUCTION_DB_MUTATED_BY_MIGRATION: false
FIXES_REQUIRED:

SHADOW_PARITY:
STATUS:
SHADOW_SOURCE_IDENTITY:
ROW_KEY_VALUE_PARITY:
IDEMPOTENT_REPLAY:
CONFLICT_STATUS:
ROLLBACK_STATUS:
BACKUP_RESTORE_STATUS:
POSTCHECK_STATUS:
TEMPORARY_ARTIFACT_CLEANUP:
UNCOMMITTED_BRIDGE: false
NEXT_ACTION: MANAGER_READ_ONLY_ACCEPTANCE
```
