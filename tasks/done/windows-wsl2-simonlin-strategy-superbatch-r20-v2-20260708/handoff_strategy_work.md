# Handoff - strategy_work R20_V2

Target repo: `/home/rongyu/workspace/strategy_work`
Controller repo: `/home/rongyu/workspace/quant-proj`
Callback target: Quant-Dispatcher thread `019f3830-4b44-7a83-944d-247a0d4dc169`
Batch: `WINDOWS_WSL2_SIMONLIN_STRATEGY_SUPERBATCH_R20_V2_20260708`

## Read First

- `/home/rongyu/workspace/quant-proj/reports/workspace_dispatch/windows_wsl2_simonlin_strategy_superbatch_r20_20260708_intake.md`
- `/home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-simonlin-strategy-superbatch-r20-v2-20260708/spec.md`
- `/home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-simonlin-strategy-superbatch-r20-v2-20260708/human_gate.md`
- `/home/rongyu/workspace/quant-proj/reports/workspace_dispatch/windows_wsl2_parallel_strategy_search_batch_r19_20260707_closeout.md`

## Assigned Scope

- `SW-R20-1` Master strategy research memo.
- `SW-R20-2` Final sync after accepted callbacks.

Deliverables:

- `reports/planning/windows_wsl2_simonlin_strategy_superbatch_r20_master_memo_20260708.md`
- `reports/planning/windows_wsl2_simonlin_strategy_superbatch_r20_final_sync_20260708.md`

## Rules

- `SW-R20-1` may be created from baseline/controller R20 intake and R19 closeout before source callbacks.
- `SW-R20-2` must not be created until accepted `A_Share_Monitor`, `market_data`, and any optional `US_Stock_Monitor` R20 callbacks are available.
- Do not create placeholder final sync.
- Distinguish research evidence from actionability.
- Preserve `strategy_candidate_available=false` unless a later source callback explicitly reports otherwise; this batch should not create candidate promotion.

## Required Validation

- `git diff --check HEAD~1..HEAD` PASS.
- Forbidden action-word scan PASS.
- No buy/hold/sell scan PASS.
- No candidate promotion scan PASS.
- No recommendation/advice scan PASS.
- No actionable ranking scan PASS.
- No placeholder final sync artifact before source callbacks.

## Boundary

Research-only memo work. No recommendation/advice, buy/hold/sell decision, `PENDING_HUMAN_REVIEW`, ticket, eligibility candidate, strategy candidate promotion, product-route activation, readiness change, broker/order/paper/live/auto, daily signal push, actionable ranking, raw-data migration, network ingest, DB/cache write/rebuild, schema migration, registry activation, market_data activation, or secret output.

## Callback

Return the R20_V2 callback envelope. If `SW-R20-2` is gated, return `STATUS=CODEX_ACCEPTANCE_SW_R20_MASTER_MEMO_SOURCE_SYNC_GATED` and list the missing source callbacks.
