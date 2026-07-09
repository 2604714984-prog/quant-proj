# Handoff: market_data R19 ETF Research Manifest And Overclaim Tests

Target repo: `/home/rongyu/workspace/market_data`
Controller repo: `/home/rongyu/workspace/quant-proj`
Callback target: Quant-Dispatcher thread `019f3830-4b44-7a83-944d-247a0d4dc169`
Batch: `WINDOWS_WSL2_PARALLEL_STRATEGY_SEARCH_BATCH_R19_20260707`

## Read First

- `/home/rongyu/workspace/quant-proj/reports/agent_handoff/windows_wsl2_fastpath_and_r18_external_audit_result_20260708.md`
- `/home/rongyu/workspace/quant-proj/reports/workspace_dispatch/windows_wsl2_parallel_strategy_search_batch_r19_20260707_intake.md`
- `/home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-parallel-strategy-search-batch-r19-20260707/spec.md`
- `/home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-parallel-strategy-search-batch-r19-20260707/human_gate.md`

## Assigned Tasks

- `MD-R19-1`: ETF research manifest schema.
- `MD-R19-2`: no-overclaim tests for ETF research outputs.

## Required Deliverables

- `reports/codex_dev/etf_rotation_r19_research_manifest_schema.md`
- `reports/codex_dev/etf_rotation_r19_research_manifest_schema.json`
- `tests/test_etf_rotation_r19_overclaim.py`

## Required Rules

- Do not activate product routes.
- Do not change active registry, readiness, schemas, adapters, raw data, or product routes.
- Encode all candidate/readiness/product/recommendation/ticket/daily-signal flags as false.
- Negative tests must reject treating ETF leaderboard, screenshot reproduction, ETF hypothesis labels, or ETF/equity regime transfer as recommendation, ticket, readiness, candidate, product route, or daily signal push.

## Callback Envelope

```text
CALLBACK_ENVELOPE:
BATCH: WINDOWS_WSL2_PARALLEL_STRATEGY_SEARCH_BATCH_R19_20260707
TARGET_REPO: /home/rongyu/workspace/market_data
BRANCH:
COMMIT:
TREE:
STATUS:
TASKS_COMPLETED:
ARTIFACTS:
VALIDATION:
ETF_KEY_RESULTS:
EQUITY_KEY_RESULTS:
STRATEGY_CANDIDATE_AVAILABLE:
BOUNDARY_RESULT:
EXTERNAL_AUDIT_TRIGGER_OPEN:
FIXES_REQUIRED:
NEXT_SOURCE_ACTION:
```
