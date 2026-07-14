# Project-wide remediation and minimalization status

## Current state

`PHASES_0_TO_2_IMPLEMENTED_PRS_GREEN_PHASE_3_BLOCKED`

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
| `quant-proj` | `main` | `158c6c797cca5e5dedacdcf9f5e47403eb2ab10b` | PR #27, head `14dcee0a44f253b8324dbacaf256684ca5912815`; one required CI job PASS |
| `central-data-ingestion` | `main` | `d17c3b474a5a97867e9b502f57b4cd572c2ed77f` | PR #24, head `94326205df275ebc7490a1084d0849a9000bbdee`; CI PASS |
| `market_data` | `main` | `300d4cf902cafc7f8462991e761e658febdc1424` | PR #5, head `47a6c6675fe0be173a5552461921d89ec6d60b09`; read-only conversion CI PASS |
| `quant_research_lab` | `master` | `6b98b94d0cdd674d6e07cce93726f204ab3a6594` | PR #6, head `4e65fbe5889d6815a8454f80d1ea96ee0802c192`; R5 CI PASS |
| `US_Stock_Monitor` | `main` | `872f54211e56a162e713d987d904b49d2521bd25` | PR #8, head `252fe19be632943389f31d025c2789aca452df74`; CI PASS |
| `A_Share_Monitor` | `main` | `ab12cf99331a39a1396c7c7f885072a9f0f68c08` | PR #8, head `7951e0669609d7e0bfa8325d47b14f4b954750c9`, based on canonical repair lane `a82ac7de579a9240e30bca85e01893deb45c4eff` |
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

- A-share R5 and legacy semantic repairs: `ACCEPTED_IMPLEMENTED_PR_OPEN`; no full central-DB replay or strategy outcome run
- US missing-price/D+1/selection repairs: `ACCEPTED_IMPLEMENTED_PR_GREEN`
- minimal central writer: `IMPLEMENTED_PR_GREEN_CUTOVER_WAITING_FOR_OWNER_DECISION`
- `market_data` read-only parity: `IMPLEMENTED_PR_GREEN`
- controller flow and CI reduction: `IMPLEMENTED_PR_GREEN`; five jobs reduced to one without adding a controller layer
- ownership/deprecation execution: `BLOCKED_NOT_READY`; QRL still imports legacy `qta`/data paths, six A-share semantic specifications remain legacy-only, archive tags and the final adapter allowlist do not yet exist
- research resume: `BLOCKED`; data cutover and Phase 3 authority consolidation are not complete
- Part 2 audit: `EXTERNAL_ONLY_NOT_PERFORMED_OR_ADJUDICATED_BY_MANAGER`

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

## Callback 2 - P0_CLOSED

```text
STATUS: P0_CODE_AND_FOCUSED_CI_CLOSED_PENDING_PR_MERGES
A_SHARE_R5_COMMIT: 4e65fbe5889d6815a8454f80d1ea96ee0802c192
A_SHARE_R5_CI_URL: https://github.com/2604714984-prog/quant_research_lab/actions/runs/29333270104/job/87086152235
ALLOCATOR_LAG_STATUS: PASS
A_SHARE_METRICS_STATUS: PASS
PIT_STATUS: PASS_FAIL_CLOSED
A_SHARE_CANONICAL_BRANCH: codex/a-share-canonical-semantic-followup-20260714@7951e0669609d7e0bfa8325d47b14f4b954750c9
US_MISSING_PRICE_STATUS: PASS; https://github.com/2604714984-prog/US_Stock_Monitor/pull/8
OPEN_P0_FINDINGS: 0 code findings; PR merges remain pending
NEXT_ACTION: merge the independently accepted green semantic PRs; do not open strategy outcomes
```

## Callback 3 - DATABASE_PARITY

```text
STATUS: DATABASE_PARITY_IMPLEMENTED_PRS_GREEN_CUTOVER_NOT_AUTHORIZED
CENTRAL_WRITER_COMMIT: 94326205df275ebc7490a1084d0849a9000bbdee
SHADOW_PARITY_URL: https://github.com/2604714984-prog/central-data-ingestion/pull/24
ONE_WRITER_STATUS: PASS; central-data-ingestion only
ONE_CLI_STATUS: PASS; ingest and aggregate read-only audit are subcommands of the same CLI
MARKET_DATA_READ_ONLY_STATUS: PASS_PENDING_MERGE; https://github.com/2604714984-prog/market_data/pull/5
ARCHIVED_ACTIVE_PATHS: market_data central_warehouse writer, SQLite staging, copy/swap publisher, and duplicate writer tests removed from the active surface
BACKUP_RESTORE_STATUS: PASS_IN_FOCUSED_TESTS; production cutover not run
NEXT_ACTION: merge parity PRs, then request a separate explicit production cutover decision
```

## Callback 4 - PROJECT_CONSOLIDATED

```text
STATUS: PARTIAL_BLOCKED_ON_PHASE3_DEPENDENCIES_AND_DATABASE_CUTOVER
FINAL_OWNERSHIP_URL: reports/architecture/project_ownership_and_deprecation_20260714.md
ACTIVE_WRITER: central-data-ingestion
ACTIVE_A_SHARE_ENGINE: quant_research_lab target; legacy dependencies still block sole-authority cutover
ACTIVE_US_ENGINE: US_Stock_Monitor
ROUTINE_CONTROLLER_FLOW: one issue -> one branch/PR -> focused CI -> short closeout
REQUIRED_CI_JOB_COUNTS: quant-proj=1; central-data-ingestion=1; market_data=1; quant_research_lab=1; US_Stock_Monitor=1; A_Share_Monitor=1
ACTIVE_MODULE_REDUCTION: quant-proj net -1238 lines; market_data active runtime net -1074 lines; central writer net +43 lines
MINIMUM_DATA_SCOPE_STATUS: writer path ready; production cutover and new ingestion not performed
RESEARCH_RESUME_STATUS: BLOCKED
STRATEGY_CANDIDATE_AVAILABLE: false
FIXES_REQUIRED: merge open PRs; make an explicit DB cutover decision; migrate QRL legacy data/qta dependencies and six semantic specs; produce the final adapter allowlist; create archive tags; then use narrow deactivation PRs
NEXT_ACTION: finish those dependency gates before removing legacy engines or reopening research
```
