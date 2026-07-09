# Handoff - A_Share_Monitor R20_V2

Target repo: `/home/rongyu/workspace/A_Share_Monitor`
Controller repo: `/home/rongyu/workspace/quant-proj`
Callback target: Quant-Dispatcher thread `019f3830-4b44-7a83-944d-247a0d4dc169`
Batch: `WINDOWS_WSL2_SIMONLIN_STRATEGY_SUPERBATCH_R20_V2_20260708`

## Read First

- `/home/rongyu/workspace/quant-proj/reports/human_gate/windows_wsl2_simonlin_strategy_superbatch_r20_v2_authorization_20260708.md`
- `/home/rongyu/workspace/quant-proj/reports/workspace_dispatch/windows_wsl2_simonlin_strategy_superbatch_r20_20260708_intake.md`
- `/home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-simonlin-strategy-superbatch-r20-v2-20260708/spec.md`
- `/home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-simonlin-strategy-superbatch-r20-v2-20260708/human_gate.md`
- `/home/rongyu/workspace/quant-proj/reports/workspace_dispatch/windows_wsl2_parallel_strategy_search_batch_r19_20260707_closeout.md`
- `/home/rongyu/workspace/quant-proj/reports/workspace_dispatch/windows_wsl2_parallel_strategy_search_batch_r19_20260707_result_summary.md`

## Assigned Scope

Complete the source-side main R20_V2 lanes in `A_Share_Monitor`:

- Lane 0: `R20-0-1`, `R20-0-2`, `R20-0-3`
- Lane 1: `TOOL-R20-1` through `TOOL-R20-9`
- Lane 2: `SL-R20-1` through `SL-R20-3`
- Lane 3: `ETF-R20-1` through `ETF-R20-6`
- Lane 4: `A-R20-1` through `A-R20-4`
- Lane 6: `N-R20-1` through `N-R20-3`
- Lane 7: `TA-R20-1` through `TA-R20-2`
- Lane 8: `STRAT-R20-1` through `STRAT-R20-2`

If global/US/HK regime work is needed before `STRAT-R20-*`, use bounded public/no-secret source health and research artifacts locally, or record `PENDING_OPTIONAL_US_GLOBAL_CALLBACK` if waiting for the separate `US_Stock_Monitor` support callback.

## Execution Rules

- First import R16-R19 evidence, build experiment-store, build negative-result memory, and audit the R19 44 initially interesting ETF rows.
- Do not begin new strategy search until R19 evidence freeze, experiment-store import, failure memory, and source health preconditions pass.
- Do not repeat R19 ETF grid v2 without delta evidence.
- Do not retry R18/R19 failed A-share features without new data, new feature, new regime, new universe, or new execution evidence.
- Source health must run before fetch-heavy work.
- Stop with `LICENSE_REVIEW_REQUIRED` if license compatibility is unclear.
- Stop with `SOURCE_AUTH_REQUIRED` if a source requires secrets, credentials, auth files, paywall access, or non-public access.
- No raw-data migration into `quant-proj`.

## Required Validation

- JSON parse PASS where JSON artifacts exist.
- `py_compile` PASS for changed Python.
- Focused pytest PASS if code/tests changed.
- `agent_safety_check.py` PASS where applicable.
- `git diff --check` PASS.
- Forbidden overclaim scan PASS.
- Source health before fetch-heavy work PASS.
- Manifest/count/hash evidence for fetched/written artifacts.
- Experiment store import PASS before new strategy search.
- Failure memory generated before new strategy search.
- No daily signal push.
- No full-frame wide3068.
- No strategy candidate promotion.
- No recommendation/advice wording.

## Boundary

Research-only. No recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket, eligibility candidate, strategy candidate promotion, readiness promotion, registry activation, product-route activation, market_data activation, daily signal push, broker/order/paper/live/auto, raw-data migration into `quant-proj`, active schema migration, secret access/output, actionable ranking, or test-result parameter selection.

## Callback

Return the R20_V2 callback envelope from the task packet. Include source health, experiment-store status, failure-memory status, R19 freeze status, R19 interesting-44 audit status, data status, strategy results, ETF results, A-share results, global/news-macro results, wide eligible count, boundary result, external-audit trigger, fixes required, and next source action.
