# WINDOWS_WSL2_A_SHARE_ETF_ROTATION_STRATEGY_BATCH_E1_DATA_FETCH_LOAD_20260707 Spec

Controller: Quant-Dispatcher
Created: 2026-07-07 Asia/Shanghai
Decision id: `HG-EXEC-TASK-A-ETF-E1-DATA-FETCH-LOAD-20260707`
Parent batch: `WINDOWS_WSL2_A_SHARE_ETF_ROTATION_STRATEGY_BATCH_E1_20260707`

## Context

E1 was dispatched as a research-only A-share ETF rotation strategy-family batch and stopped correctly because local ETF data was unavailable.

A_Share_Monitor reported:

- local `features_daily` contains 3068 stock symbols;
- ETF-like prefix scan returned 0 symbols;
- all probe ETF codes were absent;
- no provider/network fetch or DB/cache write occurred.

The user has now authorized a separate bounded HG-EXEC ETF data fetch/load task to unblock E1.

## Objective

Fetch/load a bounded local ETF OHLC/NAV research dataset for E1, validate it, then resume the E1 research-only ETF rotation diagnostics if the dataset passes local validation.

This is not a recommendation, candidate, readiness, product route, ticket, or trading task.

## Scope

| Field | Value |
|---|---|
| Target repo | `/home/rongyu/workspace/A_Share_Monitor` |
| Target thread | `019f387b-617e-7273-b539-161216ae3002` |
| Snapshot id | `etf_rotation_e1_20260707` |
| Max ETF symbols | `80` |
| Date range | `20180101..20260707` |
| Network | allowed only for bounded public/no-secret ETF data fetch |
| Write | allowed only for controlled local A_Share_Monitor staging/cache/report/test artifacts |
| Registry/readiness/product route | not allowed |

## Allowed Work

1. Select/freeze E1 ETF universes within the approved bound:
   - `screenshot_14_etf_universe`;
   - `liquid_core_etf_universe_20_30`;
   - `domestic_only_etf_universe`.
2. Fetch/load ETF OHLC/NAV data for up to 80 ETF symbols.
3. Write controlled local staging/cache artifacts in A_Share_Monitor.
4. Generate manifest/count/hash evidence.
5. Validate missingness, duplicate symbol-date keys, listing-date constraints, adjustment/NAV availability, amount/volume coverage, and date ranges.
6. Record no-future timing assumptions for E1:
   - signal uses close at T;
   - execution is T+1;
   - no same-day close-to-close execution.
7. Resume E1 tasks after data validation:
   - `ETF-E1-1` through `ETF-E1-11`.

## Required Deliverables

Data fetch/load authorization artifacts:

- `reports/runops/etf_rotation_e1_data_fetch_load_20260707/command_transcript.txt`
- `reports/workspace_dispatch/etf_rotation_e1_data_fetch_load_manifest_20260707.json`
- `reports/workspace_dispatch/etf_rotation_e1_data_fetch_load_report_20260707.md`
- `reports/workspace_dispatch/etf_rotation_e1_data_quality_validation_20260707.json`

E1 resume artifacts remain the original E1 deliverables from:

- `tasks/in_progress/windows-wsl2-a-share-etf-rotation-strategy-batch-e1-20260707/spec.md`

## Validation

- Command transcript captured.
- Manifest/count/hash evidence present.
- JSON parse PASS.
- Duplicate symbol-date validation PASS.
- Listing-date validation PASS.
- No same-day close-to-close timing PASS.
- `py_compile` PASS for changed Python files.
- Focused pytest PASS if code/tests changed.
- `agent_safety_check.py` PASS where applicable.
- `git diff --check` PASS.
- Forbidden overclaim scan PASS.

## Stop Conditions

- `SECRET_OR_ENV_ACCESS_REQUIRED`
- `PROVIDER_SOURCE_NOT_PUBLIC_NO_SECRET`
- `NEW_PROVIDER_CANDIDATE_POLICY_CONFLICT`
- `ETF_SYMBOL_LIMIT_EXCEEDED`
- `DATE_RANGE_EXPANDED_WITHOUT_AUTH`
- `UNBOUNDED_PROVIDER_SYNC_REQUIRED`
- `DB_OR_CACHE_WRITE_OUTSIDE_ALLOWED_SCOPE`
- `SCHEMA_READINESS_REGISTRY_CHANGE_REQUESTED`
- `MARKET_DATA_PRODUCT_ROUTE_ACTIVATION_ATTEMPTED`
- `RECOMMENDATION_OR_TICKET_LANGUAGE_APPEARS`
- `STRATEGY_CANDIDATE_PROMOTION_ATTEMPTED`
- `DAILY_SIGNAL_PUSH_ATTEMPTED`

## Callback Envelope

```text
CALLBACK_ENVELOPE:
BATCH: WINDOWS_WSL2_A_SHARE_ETF_ROTATION_STRATEGY_BATCH_E1_DATA_FETCH_LOAD_20260707
PARENT_BATCH: WINDOWS_WSL2_A_SHARE_ETF_ROTATION_STRATEGY_BATCH_E1_20260707
TARGET_REPO:
WORKSTREAM: HG-EXEC-TASK-A-ETF-E1-DATA-FETCH-LOAD-20260707
BRANCH:
COMMIT:
TREE:
STATUS:
TASKS_COMPLETED:
ARTIFACTS:
VALIDATION:
ETF_DATA_STATUS:
ETF_SYMBOL_COUNT:
ETF_ROW_COUNT:
DATE_RANGE:
PROVIDER_SOURCE:
KEY_RESULTS:
WIDE_OR_LIVE_SIGNAL_STATUS:
STRATEGY_CANDIDATE_AVAILABLE:
BOUNDARY_RESULT:
EXTERNAL_AUDIT_TRIGGER_OPEN:
FIXES_REQUIRED:
NEXT_SOURCE_ACTION:
```
