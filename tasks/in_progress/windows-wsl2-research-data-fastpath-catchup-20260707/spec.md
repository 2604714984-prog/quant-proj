# WINDOWS_WSL2_RESEARCH_DATA_FASTPATH_CATCHUP_20260707 Spec

Controller: Quant-Dispatcher
Created: 2026-07-07 Asia/Shanghai
Policy: `HG-POLICY-RESEARCH-DATA-FAST-PATH-20260707`

## Context

The user requested that previously blocked development work be run after removing per-task HG-EXEC friction for ordinary research data work.

The research-data fast path is active for bounded, public/no-secret, source-local, research-only data fetch/cache/report/test work. It does not authorize active schema/readiness/registry/product-route changes, recommendation, ticket, candidate promotion, raw-data migration into `quant-proj`, secrets, or trading paths.

## Objective

Resume previously blocked or stale-held research-data work that is now eligible under the fast path:

- A-share ETF E1 data fetch/load and E1 resume.
- A-share East Money coverage reconciliation beyond the earlier 20-symbol bounded probe.
- US current-universe metadata/daily staging cleanup and residual source-conflict diagnostics.

## Dispatch Matrix

| Target repo | Thread | Tasks |
|---|---|---|
| `/home/rongyu/workspace/A_Share_Monitor` | `019f387b-617e-7273-b539-161216ae3002` | `FP-A-1` through `FP-A-3` |
| `/home/rongyu/workspace/US_Stock_Monitor` | `019f387b-a161-7ad0-8678-f03a099612ba` | `FP-US-1` through `FP-US-3` |

## A_Share_Monitor Tasks

### FP-A-1 / Finish ETF E1 Data Fetch/Load And Resume E1

Continue `WINDOWS_WSL2_A_SHARE_ETF_ROTATION_STRATEGY_BATCH_E1_DATA_FETCH_LOAD_20260707` if it is already running. The research-data fast path means no additional per-task HG-EXEC is needed for bounded public/no-secret ETF data fetch/load or source-local research cache writes.

Carry forward the existing E1 bounds:

- max ETF symbols: `80`;
- date range: `20180101..20260707`;
- snapshot id: `etf_rotation_e1_20260707`;
- source-local staging/cache/report/test artifacts only.

If ETF data validates, resume original E1 tasks `ETF-E1-1` through `ETF-E1-11`.

### FP-A-2 / East Money Coverage Reconciliation Catchup

Run a research-only East Money coverage reconciliation catchup using public/no-secret sources and source-local artifacts only.

Bounds:

- max symbols: current A-share research universe, up to `3068`;
- date range: `20180101..20260707`;
- preserve previous `77 / 121 / 2870` split until source evidence explicitly changes;
- generated data remains research staging only.

Required outputs:

- coverage reconciliation report;
- manifest/count/hash evidence;
- updated split table if evidence changes;
- blockers table for unresolved symbols;
- no data-clear, readiness, product route, ticket, candidate, or recommendation state.

### FP-A-3 / Old A-share Data-Hold Audit

Audit old A-share data holds that referenced suspension/limit repair or network/write blockers. If they are already superseded by completed source evidence, produce a short supersession report. If research-only source-local fetch/cache evidence is still missing, run it under the fast path only when bounded and public/no-secret.

Do not change readiness, registry, product route, ticket/candidate state, or trading paths.

## US_Stock_Monitor Tasks

### FP-US-1 / Current-Universe Metadata Parser Cleanup

Continue from `HG-EXEC-TASK-US-METADATA-REPAIR-20260707`.

Fix or diagnose sourceable symbols that were excluded only because of `N/A` daily row parsing, then rerun bounded research-only current-universe staging if safe.

Bounds:

- max symbols: `320`;
- date range: `20180101..20260707`;
- public/no-secret sources only;
- source-local staging/cache/report/test artifacts only.

### FP-US-2 / Tencent-Only And Legacy 44 Source-Conflict Diagnostics

Run research-only diagnostics for:

- Tencent-visible but Nasdaq-current-directory-missing symbols;
- historical/delisted legacy 44 metadata symbols;
- ETF/non-equity symbols previously excluded from active-equity metadata.

Output a source-conflict table and recommended research handling labels only:

- `CURRENT_SOURCE_EXCLUDED`
- `TENCENT_ONLY_REQUIRES_POLICY`
- `HISTORICAL_DELISTED_EXCLUDED`
- `ETF_OR_NON_EQUITY_EXCLUDED`
- `SOURCEABLE_CURRENT_UNIVERSE`
- `INSUFFICIENT_SOURCE_EVIDENCE`

Do not synthesize active metadata.

### FP-US-3 / US 300 Research Staging Status

Produce a current status report for whether the old US 300-symbol ingest hold is now superseded by the completed current-universe staging or still needs separate work.

If bounded public/no-secret source-local staging can be completed safely, do it under the fast path. If product route, active registry, readiness, candidate/ticket, or raw migration is needed, stop and report `STILL_HARD_GATED`.

## Required Validation

- Command transcript for network/write tasks.
- Manifest/count/hash evidence for generated data.
- JSON parse PASS.
- Duplicate-key validation where daily rows are generated.
- Missingness/source-coverage validation where metadata rows are generated.
- `git diff --check` PASS.
- Focused tests PASS if code/tests changed.
- `agent_safety_check.py` PASS where applicable.
- Forbidden overclaim scan PASS.

## Hard Stop Conditions

- `SECRET_OR_ENV_ACCESS_REQUIRED`
- `UNBOUNDED_PROVIDER_SYNC_REQUIRED`
- `RAW_DATA_MIGRATION_INTO_QUANT_PROJ_REQUIRED`
- `ACTIVE_SCHEMA_MIGRATION_REQUIRED`
- `READINESS_PROMOTION_REQUIRED`
- `REGISTRY_ACTIVATION_REQUIRED`
- `PRODUCT_ROUTE_ACTIVATION_REQUIRED`
- `RECOMMENDATION_OR_TICKET_OR_CANDIDATE_REQUIRED`
- `BROKER_ORDER_PAPER_LIVE_AUTO_REQUIRED`

## Callback Envelope

```text
CALLBACK_ENVELOPE:
BATCH: WINDOWS_WSL2_RESEARCH_DATA_FASTPATH_CATCHUP_20260707
TARGET_REPO:
BRANCH:
COMMIT:
TREE:
STATUS:
TASKS_COMPLETED:
ARTIFACTS:
VALIDATION:
DATA_STATUS:
KEY_RESULTS:
WARNINGS:
BLOCKERS:
BOUNDARY_RESULT:
EXTERNAL_AUDIT_TRIGGER_OPEN:
FIXES_REQUIRED:
NEXT_SOURCE_ACTION:
```
