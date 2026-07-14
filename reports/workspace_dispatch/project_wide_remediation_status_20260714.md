# Project-wide remediation and minimalization status

## Current state

`NARROW_PATCHES_GREEN_AWAITING_EXTERNAL_REREVIEW_AND_MERGE`

- umbrella issue: https://github.com/2604714984-prog/quant-proj/issues/26
- controlling prompt blob: `aae017397af65b4f2d066dc1bdfa4e9a6cf0d012`
- controller base commit/tree: `c1ffc8b829454a81dd4d7f46ba9e25ef6826fe96` / `00571b36c83c45abce475495f81e486485271835`
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
| `quant-proj` | `main` | `c1ffc8b829454a81dd4d7f46ba9e25ef6826fe96` | PR #27 rebased onto current `main`; exact post-patch head is tracked externally after commit |
| `central-data-ingestion` | `main` | `d17c3b474a5a97867e9b502f57b4cd572c2ed77f` | PR #24, head `04a3258acb2ca6f924ea2e0bd222bf957ac7555e`; CI runs `29344443374` and `29344446501` PASS; installed shadow runtime ready; production cutover not authorized |
| `market_data` | `main` | `300d4cf902cafc7f8462991e761e658febdc1424` | PR #5, head `47a6c6675fe0be173a5552461921d89ec6d60b09`; read-only conversion CI PASS |
| `quant_research_lab` | `master` | `6b98b94d0cdd674d6e07cce93726f204ab3a6594` | user-controlled PR #6, head `d3359a87c0873a76c5b374c281ed844ac5f29c98`; CI runs `29342986169` and `29342992328` PASS; R5 code ready; full replay blocked |
| `US_Stock_Monitor` | `main` | `872f54211e56a162e713d987d904b49d2521bd25` | PR #8, head `22d79956be4755e7bdea3235f91c16284d48a242`; CI run `29342004020` PASS |
| `A_Share_Monitor` | `main` | `ab12cf99331a39a1396c7c7f885072a9f0f68c08` | PR #8, head `b6a4ddc48899a95c5b0c9e8cce03bb5e24b493eb`, now based on `main`; canonicalization complete in PR pending external re-review and merge; pre-integration head retained by tag `archive/a-share-canonical-semantic-followup-pre-main-integration-20260714` |
| `us_stock_30w` | `master` | `62abe5ba0213e9e7a8ade69db423fc71a3746357` | evidence-only pending archive |
| `strategy_work` | `main` | `a050e20ba50ada3f8bb052585c667770dac2c2c4` | knowledge/failure-memory pending archive |

All implementation work must use isolated worktrees pinned to the applicable live ref or explicitly frozen audited baseline. Divergent root checkouts are evidence, not implementation bases.

## Freeze decisions

- no new repository, engine, writer, registry authority, signature format, receipt hierarchy, dispatcher layer, acceptance layer, or speculative provider
- target central writer: `central-data-ingestion`; current implementation remains shadow-only until a separate cutover decision
- one A-share engine: `quant_research_lab`
- one US engine: `US_Stock_Monitor`
- new strategy families, parameter searches, speculative data lanes, and candidate promotion remain frozen
- ordinary work target: one issue -> one PR -> focused CI -> short closeout
- elevated review remains only for engine semantics, PIT/schema/data changes, destructive DB work, strategy intake, or execution-stage opening
- Part 2 audit remains external-only

## Workstream status

- original audit findings: `ORIGINAL_AUDIT_FINDINGS_CLOSED_IN_REPAIR_BRANCHES`; exact updated heads still require integrated external re-review before merge
- A-share R5 and legacy semantic repairs: `IMPLEMENTED_PRS_GREEN_PENDING_EXTERNAL_REREVIEW_AND_MERGE`; QRL is user-controlled and full replay remains blocked
- full replay: `FULL_REPLAY_BLOCKERS_OPEN`
- US missing-price/D+1/selection repairs: `IMPLEMENTED_PR_GREEN_PENDING_EXTERNAL_REREVIEW_AND_MERGE`
- minimal central writer: `MINIMAL_WRITER_INSTALLED_SHADOW_RUNTIME_READY`; `PRODUCTION_CUTOVER_NOT_AUTHORIZED`
- `market_data` read-only parity: `IMPLEMENTED_PR_GREEN`
- controller flow and CI reduction: `PATCHED_LOCALLY_AWAITING_FRESH_INDEPENDENT_ACCEPTANCE`; five jobs reduced to one without adding a controller layer
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
BLOCKERS: exact updated heads require integrated external re-review; full replay and production cutover remain closed
NEXT_ACTION: freeze and independently accept the updated controller bytes, then publish exact refs for external re-review
```

## Callback 2 - ORIGINAL_AUDIT_FINDINGS_CLOSED

```text
STATUS: ORIGINAL_AUDIT_FINDINGS_CLOSED_IN_REPAIR_BRANCHES
A_SHARE_R5_COMMIT: d3359a87c0873a76c5b374c281ed844ac5f29c98
A_SHARE_R5_CI_URLS: https://github.com/2604714984-prog/quant_research_lab/actions/runs/29342986169 ; https://github.com/2604714984-prog/quant_research_lab/actions/runs/29342992328
A_SHARE_R5_STATE: CODE_READY_FULL_REPLAY_BLOCKED_USER_CONTROLLED
FULL_REPLAY_BLOCKERS_OPEN: true
ALLOCATOR_LAG_STATUS: PASS
A_SHARE_METRICS_STATUS: PASS
PIT_STATUS: PASS_FAIL_CLOSED
A_SHARE_DEFAULT_BRANCH_CANONICALIZATION=COMPLETE_IN_PR_PENDING_EXTERNAL_REREVIEW_AND_MERGE; PR #8@b6a4ddc48899a95c5b0c9e8cce03bb5e24b493eb targets main
A_SHARE_ARCHIVE_TAG: archive/a-share-canonical-semantic-followup-pre-main-integration-20260714
US_MISSING_PRICE_STATUS: REPAIR_BRANCH_GREEN_PENDING_EXTERNAL_REREVIEW_AND_MERGE; PR #8@22d79956be4755e7bdea3235f91c16284d48a242; CI run 29342004020 PASS
MERGE_GATE: independent integrated external re-review of exact updated heads
NEXT_ACTION: request external re-review; do not merge or open strategy outcomes before it clears
```

## Callback 3 - DATABASE_PARITY

```text
STATUS: MINIMAL_WRITER_INSTALLED_SHADOW_RUNTIME_READY
CENTRAL_WRITER_COMMIT: 04a3258acb2ca6f924ea2e0bd222bf957ac7555e
SHADOW_PARITY_URL: https://github.com/2604714984-prog/central-data-ingestion/pull/24
CENTRAL_CI_RUNS: 29344443374, 29344446501
SHADOW_RUNTIME_STATUS: READY_PENDING_EXTERNAL_REREVIEW_AND_MERGE
PRODUCTION_CUTOVER_NOT_AUTHORIZED: true
MARKET_DATA_READ_ONLY_STATUS: REPAIR_BRANCH_GREEN_PENDING_EXTERNAL_REREVIEW_AND_MERGE; https://github.com/2604714984-prog/market_data/pull/5
ARCHIVED_ACTIVE_PATHS: market_data central_warehouse writer, SQLite staging, copy/swap publisher, and duplicate writer tests removed from the active surface
BACKUP_RESTORE_STATUS: PASS_IN_FOCUSED_TESTS; production cutover not run
NEXT_ACTION: request integrated external re-review; merge only after clearance; keep production cutover as a separate future decision
```

## Callback 4 - PROJECT_INTEGRATION_PENDING

```text
STATUS: PENDING_EXTERNAL_REREVIEW_MERGE_AND_PHASE3_DEPENDENCIES
FINAL_OWNERSHIP_URL: reports/architecture/project_ownership_and_deprecation_20260714.md
TARGET_WRITER: central-data-ingestion; installed shadow runtime only; production cutover not authorized
ACTIVE_A_SHARE_ENGINE: quant_research_lab target; legacy dependencies still block sole-authority cutover
ACTIVE_US_ENGINE: US_Stock_Monitor
ROUTINE_CONTROLLER_FLOW: one issue -> one PR -> focused CI -> short closeout
REQUIRED_CI_JOB_COUNTS: quant-proj=1; central-data-ingestion=1; market_data=1; quant_research_lab=1; US_Stock_Monitor=1; A_Share_Monitor=1
ACTIVE_MODULE_REDUCTION: quant-proj and market_data remain net-negative versus their frozen bases
MINIMUM_DATA_SCOPE_STATUS: writer path ready; production cutover and new ingestion not performed
RESEARCH_RESUME_STATUS: BLOCKED
STRATEGY_CANDIDATE_AVAILABLE: false
FIXES_REQUIRED: obtain independent integrated external re-review of exact updated heads; merge only after clearance; keep full replay and production cutover blocked; then finish the narrow dependency migrations before deactivation
NEXT_ACTION: publish exact updated refs and CI evidence to issue #26 for external re-review; do not remove legacy engines or reopen research
```
