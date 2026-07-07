# WINDOWS_WSL2_STRATEGY_DISCOVERY_BATCH_R16_20260707 Intake

Project: quant-proj
Role: Quant-Dispatcher
Imported: 2026-07-07 Asia/Shanghai
Source: user-pasted R15 external-audit result and R16 next-batch task list
Status: DISPATCH_PREPARED

## Classification

Ordinary research-only strategy discovery / strategy diagnosis / strategy rescue batch.

External-audit trigger opened: `no`

Reason:

- External review verdict for R15 was `VERIFIED_ACCEPT_WITH_WARNINGS`.
- `EXTERNAL_AUDIT_TRIGGER_OPEN: no`.
- `FIXES_REQUIRED: none before next ordinary strategy-search batch`.
- R16 objective is strategy discovery on the R15 research-only data and chunked execution base.
- R16 explicitly forbids recommendations, tickets, eligibility candidates, readiness, product routes, broker/order/paper/live/auto, raw-data migration, secrets, network/provider fetch, DB/cache rebuild, schema/readiness/registry changes, and registry activation.

## Verified R15 Facts To Carry Forward

- R15 status: `CLOSED_ACCEPTED_RESEARCH_ONLY_WITH_WARNINGS`.
- East Money coverage remains partial:
  - `77 CROSSCHECK_PASS`
  - `121 CROSSCHECK_DATE_GAP`
  - `2870 CROSSCHECK_MISSING_EAST_MONEY`
- 198 common symbols are overlap evidence only.
- Survivor-bias evidence improved but did not eliminate all scope limits.
- wide3068 full-frame StrategySearch remains `BLOCKED_FULL_FRAME_STRATEGY_SEARCH_UNSAFE`.
- wide3068 work is chunked-only.
- All strategy reruns remain rejected.
- `strategy_candidate_available=false`.
- market_data contract remains `RESEARCH_STAGING_ONLY_NOT_DATA_CLEAR`.
- No registry, readiness, data-clear, or product route changed.

## Dispatch Scope

### A_Share_Monitor

- `A-WIN-R16-1`: Strategy evidence freeze before new search.
- `A-WIN-R16-2`: Factor predictive diagnostics before strategy construction.
- `A-WIN-R16-3`: Pre-registered strategy hypothesis catalog.
- `A-WIN-R16-4`: Strategy scout run on small and medium caches.
- `A-WIN-R16-5`: Wide3068 chunked diagnostic run for eligible families.
- `A-WIN-R16-6`: Trade-count rescue diagnostics.
- `A-WIN-R16-7`: Cost-aware strategy redesign diagnostics.
- `A-WIN-R16-8`: Parameter stability and cluster selection map.
- `A-WIN-R16-9`: Regime and period attribution.
- `A-WIN-R16-10`: Strategy-family rejection taxonomy v2.
- `A-WIN-R16-11`: Research-only shadow leaderboard.

### market_data

- `MD-WIN-R16-1`: Strategy-search evidence manifest extension.
- `MD-WIN-R16-2`: Negative tests for strategy-search overclaim.
- `MD-WIN-R16-3`: Feature/factor evidence bridge.

### strategy_work

- `SW-WIN-R16-1`: R16 strategy discovery memo.
- `SW-WIN-R16-2`: Strategy research map by blocker.
- `SW-WIN-R16-3`: Final sync after A-share and market_data acceptances.

### quant-proj

- `QP-WIN-R16-1`: R16 intake.
- `QP-WIN-R16-2`: R16 result summary and closeout after downstream callbacks.

## Not Dispatched

`US_Stock_Monitor` remains ready but is not dispatched for R16 because the reviewed task list only includes an optional US branch if explicitly requested. No explicit US R16 task was issued.

## Boundary

Research-only. No recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket, eligibility candidate, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, raw-data migration, `.env` access, key output, secret handling, DB write, network ingest, schema migration, readiness change, or registry activation is authorized.

Future provider/network fetch, DB/cache rebuild, schema/readiness/registry changes require separate task-level HG-EXEC evidence and transcript.

