# Handoff: A_Share_Monitor R19 Parallel Strategy Search

Target repo: `/home/rongyu/workspace/A_Share_Monitor`
Controller repo: `/home/rongyu/workspace/quant-proj`
Callback target: Quant-Dispatcher thread `019f3830-4b44-7a83-944d-247a0d4dc169`
Batch: `WINDOWS_WSL2_PARALLEL_STRATEGY_SEARCH_BATCH_R19_20260707`

## Read First

- `/home/rongyu/workspace/quant-proj/reports/agent_handoff/windows_wsl2_fastpath_and_r18_external_audit_result_20260708.md`
- `/home/rongyu/workspace/quant-proj/reports/workspace_dispatch/windows_wsl2_parallel_strategy_search_batch_r19_20260707_intake.md`
- `/home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-parallel-strategy-search-batch-r19-20260707/spec.md`
- `/home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-parallel-strategy-search-batch-r19-20260707/human_gate.md`

## Assigned Tasks

Complete:

- `ETF-R19-1` through `ETF-R19-7`.
- `A-WIN-R19-1` through `A-WIN-R19-5`.

Use the task definitions and deliverables in the spec exactly.

## Required Rules

- Research-only.
- No recommendation/advice.
- No ticket, eligibility candidate, strategy candidate promotion, readiness, product route, daily signal push, or trading path.
- Do not use ETF screenshot reproduction or leaderboard as actionable signal.
- No post-hoc parameter tuning or test-result parameter selection.
- Preserve close `T` signal and `T+1` open execution for ETF work.
- Do not run same-day close-to-close execution.
- Do not run full-frame wide strategy search.
- Run equity wide prequalification only if validation-safe rescue produces eligible rows; otherwise output `NO_R19_EQUITY_WIDE_RESEARCH_PROBE_ELIGIBLE`.
- Do not access `.env`, keys, tokens, auth, credentials, or secrets.
- Do not perform DB/registry/readiness/product-route/raw migration work.

## Callback Envelope

```text
CALLBACK_ENVELOPE:
BATCH: WINDOWS_WSL2_PARALLEL_STRATEGY_SEARCH_BATCH_R19_20260707
TARGET_REPO: /home/rongyu/workspace/A_Share_Monitor
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
