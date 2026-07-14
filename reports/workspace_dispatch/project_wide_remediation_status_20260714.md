# Project-wide remediation and minimalization status

## Current state

`PROJECT_FREEZE_COMPLETE_IMPLEMENTATION_IN_PROGRESS`

- umbrella issue: https://github.com/2604714984-prog/quant-proj/issues/26
- controlling prompt blob: `aae017397af65b4f2d066dc1bdfa4e9a6cf0d012`
- controller base commit/tree: `158c6c797cca5e5dedacdcf9f5e47403eb2ab10b` / `7db80c09eb7ffe3799e4ec878f395afae3e72888`
- frozen external-audit ref: `f816e3c9bd92c274f34ecf901de02e4a914205a8`
- external audit contents are accepted as an input and were not re-performed, supplemented, or accepted by Quant Manager
- `WHOLE_PROJECT_ARCHITECTURE=SIMPLIFY_NOW`
- `CENTRAL_DATABASE=REBUILD_MINIMAL`
- `BACKTEST_VALIDATION=CONDITIONALLY_USABLE_AFTER_CRITICAL_FIXES`
- `STRATEGY_DEVELOPMENT=PROCESS_AND_ENGINE_BOTTLENECK`
- `STRATEGY_CANDIDATE_AVAILABLE=false`

## Frozen live-default refs

| Repository | Default branch | Frozen live ref | Current implementation lane |
|---|---|---|---|
| `quant-proj` | `main` | `158c6c797cca5e5dedacdcf9f5e47403eb2ab10b` | `codex/project-wide-remediation-minimalization-20260714` |
| `central-data-ingestion` | `main` | `d17c3b474a5a97867e9b502f57b4cd572c2ed77f` | PR #24, head `17f027785b7531534a6286821f9e0048dc633c6a` |
| `market_data` | `main` | `300d4cf902cafc7f8462991e761e658febdc1424` | read-only conversion pending parity |
| `quant_research_lab` | `master` | `6b98b94d0cdd674d6e07cce93726f204ab3a6594` | `codex/a-share-r5-critical-semantic-repair-20260714` |
| `US_Stock_Monitor` | `main` | `872f54211e56a162e713d987d904b49d2521bd25` | narrow semantic-fix branch dispatched |
| `A_Share_Monitor` | `main` | `ab12cf99331a39a1396c7c7f885072a9f0f68c08` | canonical repair lane from preservation baseline `1a64e70873fc8a3c3d998e509cbcf690010ffef0` |
| `us_stock_30w` | `master` | `62abe5ba0213e9e7a8ade69db423fc71a3746357` | evidence-only pending archive |
| `strategy_work` | `main` | `a050e20ba50ada3f8bb052585c667770dac2c2c4` | knowledge/failure-memory pending archive |

All implementation work must use isolated worktrees pinned to the applicable live ref or explicitly frozen audited baseline. Divergent root checkouts are evidence, not implementation bases.

## Freeze decisions

- no new repository, engine, writer, registry authority, signature format, receipt hierarchy, dispatcher layer, acceptance layer, or speculative provider
- one central writer: `central-data-ingestion`
- one A-share engine: `quant_research_lab`
- one US engine: `US_Stock_Monitor`
- new strategy families, parameter searches, speculative data lanes, and candidate promotion remain frozen
- ordinary work target: one issue, one implementation PR, focused CI, one short closeout
- elevated review remains only for engine semantics, PIT/schema/data changes, destructive DB work, strategy intake, or execution-stage opening
- Part 2 audit remains external-only

## Workstream status

- A-share R5 and legacy semantic repairs: `DISPATCHED_CODE_ONLY_NO_FULL_REPLAY`
- US missing-price/D+1/selection repairs: `DISPATCHED_CODE_ONLY`
- existing minimal central writer: `ACCEPTED_DRAFT_PR_CUTOVER_WAITING_FOR_USER_APPROVAL`
- central-writer ownership and `market_data` read-only parity: `PENDING_DATABASE_EXECUTOR`
- controller flow and CI reduction: `IN_PROGRESS`
- ownership/deprecation execution: `PENDING_SEMANTIC_AND_DB_PARITY`
- research resume: `BLOCKED_UNTIL_P0_AND_READ_ONLY_SNAPSHOT_CONTRACT_PASS`

## Callback 1 - PROJECT_FREEZE

```text
STATUS: PROJECT_FREEZE_COMPLETE
UMBRELLA_ISSUE_URL: https://github.com/2604714984-prog/quant-proj/issues/26
STATUS_BOARD_URL: reports/workspace_dispatch/project_wide_remediation_board_20260714.csv
PINNED_REFS: eight live-default refs recorded above
OWNERSHIP_DRAFT_URL: reports/architecture/project_ownership_and_deprecation_20260714.md
DB_TASK_CONTINUED: true; existing task and PR #24 retained, not duplicated
BLOCKERS: P0 semantic fixes, writer parity/read-only conversion, destructive cutover requires owner approval
NEXT_ACTION: close code-only P0 findings and central ownership parity in parallel
```
