# Central DB minimalization and shadow migration status

## Current state

`PHASE_2_ACCEPTED_MAINLINE_INTEGRATION_DRAFT_PR_OPEN_CUTOVER_WAITING_FOR_USER_APPROVAL`

## Freeze and dispatch callback

```text
FREEZE_AND_DISPATCH:
STATUS: COMPLETE
QUANT_PROJ_BRANCH: codex/manager-central-db-minimalization-20260714
QUANT_PROJ_BASE: a1482e71b13554d53906f4205c4825d2a85fcd5c
QUANT_PROJ_BASE_TREE: 11739e2a12e8c20a0bc858a2cd0ac9cea283b4a2
TASK_SPEC_PATH: tasks/in_progress/central-db-minimalization-shadow-migration-20260714/spec.md
ISSUE_URL: https://github.com/2604714984-prog/quant-proj/issues/24
DATABASE_PROMPT_PATH: reports/agent_handoff/central_db_minimalization_shadow_migration_database_prompt_20260714.md
DATABASE_EXECUTOR_THREAD: 019f5c2a-859e-7ed2-8ecf-e94b84f454cb
LEGACY_FREEZE_STATUS: LEGACY_ACTIVE_DURING_SHADOW_MIGRATION
PART2_OWNER: EXTERNAL_INDEPENDENT_AUDITOR
PART2_MANAGER_EXECUTION: NOT_AUTHORIZED_BY_USER
PART2_PINNED_REFS_STATUS: EXISTING_EXTERNAL_AUDIT_REFS_RECORDED_ONLY_NO_NEW_MANAGER_AUDIT
NEXT_ACTION: DATABASE_EXECUTOR_PHASE_1_GREEN_PRECOMMIT
```

## Part 1 implementation and acceptance

- independently accepted frozen-base commit: `fdb4da2f8a07e71873bc7295388a2d432d01e849`
- frozen-base tree/parent: `872b81d504999d15cece9dbd597cc2c66c9b07db` / `f2d401e42aa8f7cd17a14d94c039f45ba6546d9d`
- independent verdict: `LUNA_ACCEPTANCE_VALID`, findings none
- accepted scope: exactly 11 files (`central_data/` minimal writer modules plus `tests/test_minimal_writer.py`)
- audited-base validation: focused `19/19`, full `183/183`, Ruff, py_compile, diff and boundary checks PASS
- current-main integration branch: `codex/central-db-minimal-writer-mainline-integration-20260714`
- current-main integration commit/tree/parent: `17f027785b7531534a6286821f9e0048dc633c6a` / `e3a5b0f99ec2d9c829a6a5fe89abf402903c7d83` / `d17c3b474a5a97867e9b502f57b4cd572c2ed77f`
- integration validation: focused `19/19`, current-main full suite `157/157`, Ruff, py_compile, diff and boundary checks PASS
- the 26-test difference is the frozen audit base's divergent `tests/test_tushare_replay.py`; its 15 supporting files are absent from current `main` and were not imported into the exact 11-file integration
- implementation Draft PR: `https://github.com/2604714984-prog/central-data-ingestion/pull/24`
- PR presentation: exactly 1 commit and 11 changed files
- accepted legacy-base branch and commit were preserved unchanged; no force push occurred
- production DB remained byte-identical at SHA-256 `936e1ee5230207b1ca59e1fd6245ad5a3c1dd957ae030441e8420c83e57a3869`
- no provider call, production write, cutover, legacy deletion, strategy/trading change, or Part 2 work occurred

## Cutover decision

`CUTOVER_PROPOSAL: WAITING_FOR_USER_APPROVAL`

Part 1 implementation and shadow evidence are complete enough to propose a bounded cutover, but this record does not authorize it. A later owner-approved cutover must preserve the canonical writer lock, take and verify a fresh prewrite backup, stop competing writers, run one bounded append through the minimal path, verify read-only reopen and idempotent replay, and retain immediate rollback. Legacy paths remain active until that separate approval and successful cutover.

## Production database T0 identity

- path: `/home/rongyu/workspace/quant_data/quant_research.duckdb`
- SHA-256: `936e1ee5230207b1ca59e1fd6245ad5a3c1dd957ae030441e8420c83e57a3869`
- bytes: `2411212800`
- mode/owner: `0600 / rongyu`
- relations: `54` (`39` base tables and `15` views)
- schema relation counts: `a_share=15`, `a_share_research=3`, `main=18`, `meta=5`, `research=1`, `us_equity_research=12`
- latest successful append evidence: `5,524` daily rows and `60` partial daily-basic rows for `20260713`, with zero duplicate natural keys
- accepted status of those rows: third-party structured secondary, retrieval-time availability, `canonical_pit_eligible=false`

## Recovery identity

- latest prewrite backup: `/home/rongyu/workspace/quant_data/.tushare_pilot_backups/quant_research.pre_a0_a1_20260714_d356add7.duckdb`
- backup SHA-256: `d356add782758746ea05666af38dd0f64918ae675ec3a7cd5e645588e44309d4`
- backup bytes: `2399678464`
- rollback rule: restore only under separate user approval after verifying the current writer is stopped and preserving the failed target for diagnosis
- writer lock path: `/home/rongyu/workspace/quant_data/.locks/quant_research.duckdb.writer.lock`
- Phase 0 writer state: no process held the production DB or canonical lock; no matching kernel lock was present
- stale alternate lock paths also exist at `/home/rongyu/workspace/quant_data/.quant_research.duckdb.writer.lock` and `/home/rongyu/workspace/quant_data/quant_research.duckdb.writer.lock`; the new path must use only the canonical `.locks/` path

## Repository identities

- audited central-data worktree: `/home/rongyu/workspace/.wt-central-db-lean-architecture-audit-20260714`
- audited branch/commit/tree: `agent/central-db-lean-architecture-audit-20260714` / `f2d401e42aa8f7cd17a14d94c039f45ba6546d9d` / `6f9692d9efafe2ee0f3521d774635e45121aefde`
- accepted shadow worktree: `/home/rongyu/workspace/.wt-central-db-minimal-writer-shadow-migration-20260714`
- accepted shadow branch/commit: `codex/central-db-minimal-writer-shadow-migration-20260714` / `fdb4da2f8a07e71873bc7295388a2d432d01e849`
- clean current-main integration worktree: `/home/rongyu/workspace/.wt-central-db-minimal-writer-mainline-integration-20260714`
- integration branch/commit: `codex/central-db-minimal-writer-mainline-integration-20260714` / `17f027785b7531534a6286821f9e0048dc633c6a`
- last useful production append used a temporary bridge outside Git; it is historical evidence and is forbidden as the future path
- existing durable legacy modules remain active only during shadow migration and must not be expanded
- existing DB2 task `tasks/in_progress/central-database-full-ingestion-db2-20260713/spec.md`, tracking issue `#19`, foundation acceptance, and `central_db_db2_final_summary_20260713.md` remain historical/operational context and are not closed by this Phase 0 record
- the Phase 0 snapshot recorded 29 registered worktrees; live read-only closure inspection records 33 after later isolated tasks were added
- no unrelated worktree or pre-existing untracked scope was absorbed into this branch

## Moving-production distinction

`PRODUCTION_DB_MUTATED_BY_MIGRATION=false` is the migration invariant. Essential legacy collection may independently change the live database while shadow work proceeds. Every shadow comparison therefore uses an immutable T0 copy, fixture, or temporary schema and records its own source SHA; it must not compare against a moving live target as if frozen.

## Part 2 boundary

The Manager did not start or perform Part 2. The following refs are only the pre-existing external audit's recorded deep-review identities and are not a new Manager audit:

- `quant_research_lab d5e902af4beab6826ebc34c9a940b881f25ad750`
- `A_Share_Monitor ab12cf99331a39a1396c7c7f885072a9f0f68c08`
- `US_Stock_Monitor 872f54211e56a162e713d987d904b49d2521bd25`
- `market_data 300d4cf902cafc7f8462991e761e658febdc1424`
- `strategy_work a050e20ba50ada3f8bb052585c667770dac2c2c4`
- `us_stock_30w 62abe5ba0213e9e7a8ade69db423fc71a3746357`

No research repository is modified by this workstream.
