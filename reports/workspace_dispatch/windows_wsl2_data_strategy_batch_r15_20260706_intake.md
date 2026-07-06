# WINDOWS_WSL2_DATA_STRATEGY_AND_BASE_BATCH_R15_20260706 Intake

Project: quant-proj
Role: Quant-Dispatcher
Imported: 2026-07-07
Source: user-pasted GPT Pro / GitHub connector file-level external-audit conclusion
Original intake copy: `tasks/inbox/20260707-windows-wsl2-data-strategy-and-base-batch-r15-external-audit-command.md`
Status: DISPATCH_PREPARED

## Classification

Ordinary research-only data/strategy/data-base batch.

External-audit trigger opened: `no`

Reason:

- Verdict was `VERIFIED_ACCEPT_WITH_WARNINGS`.
- `EXTERNAL_AUDIT_TRIGGER_OPEN: no`.
- `FIXES_REQUIRED: none before the next ordinary data/strategy batch`.
- Tasks are evidence hardening, chunked execution hardening, strategy-quality diagnostics, market_data research contract work, and strategy_work memos.
- No task authorizes recommendation, `PENDING_HUMAN_REVIEW`, ticket, eligibility candidate, product route, production readiness, broker/order/paper/live/auto, raw-data migration, secrets, network/provider fetch, DB/cache rebuild, schema/readiness/registry changes, or registry activation.

## Verified R14 Facts To Carry Forward

- A_Share_Monitor R14 evidence commit: `dd3089e2a9c1693ea0571db37c185d6584f1bc14`.
- A_Share_Monitor repair package commit: `735ac8f18266a3720d1b0e729ed6b203539d758e`.
- strategy_work sync: `2bfbe33e654e7ceb76117ab7b156ff44f2d979be`.
- quant-proj receipt anchor in audit command: `61c71087cb33ac55c6f00b9aa7da12e8a111a13b`.
- East Money crosscheck remains partial:
  - `77` `CROSSCHECK_PASS` symbols.
  - `121` `CROSSCHECK_DATE_GAP` symbols.
  - `2870` `CROSSCHECK_MISSING_EAST_MONEY` symbols.
- Survivor-bias active rejection disappeared from candidate rejection reasons, but survivor-bias risk is not proven fully eliminated.
- All strategy reruns remain rejected.
- Remaining blockers are strategy-quality and robustness blockers: parameter instability, cost stress, trade-count weakness, drawdown, and negative validation/test behavior.
- wide3068 full-frame remains blocked.
- chunked StrategySearch/backtest remains required.
- R14 memory telemetry unit naming must be normalized in R15.

## Dispatch Scope

### A_Share_Monitor

- `A-WIN-R15-1`: East Money coverage expansion priority queue.
- `A-WIN-R15-2`: East Money date-gap diagnostics.
- `A-WIN-R15-3`: controlled East Money HG-EXEC plan only.
- `A-WIN-R15-4`: survivor-bias evidence hardening v2.
- `A-WIN-R15-5`: `features_daily` lineage and staging assumptions manifest.
- `A-WIN-R15-6`: tradability evidence base.
- `A-WIN-R15-7`: full-frame guard finalization.
- `A-WIN-R15-8`: memory telemetry unit normalization.
- `A-WIN-R15-9`: metadata-only table profiling.
- `A-WIN-R15-10`: chunked feature reader hardening.
- `A-WIN-R15-11`: chunked backtest equivalence expansion.
- `A-WIN-R15-12`: strategy rejection research agenda.
- `A-WIN-R15-13`: cost-stress decomposition.
- `A-WIN-R15-14`: parameter instability surface.
- `A-WIN-R15-15`: pre-registered broad strategy family diagnostics.

### market_data

- `MD-WIN-R15-1`: A-share wide feature research data-base contract.
- `MD-WIN-R15-2`: cross-repo evidence bridge.
- `MD-WIN-R15-3`: negative overclaim regression tests.
- `MD-WIN-R15-4`: research data-base manifest schema draft.

### strategy_work

- `SW-WIN-R15-1`: broad R15 strategy memo.
- `SW-WIN-R15-2`: strategy-quality blocker roadmap.
- `SW-WIN-R15-3`: final sync after source acceptances only.

### quant-proj

- `QP-WIN-R15-1`: R15 intake and source receipt.
- `QP-WIN-R15-2`: R15 result summary and closeout after callbacks.

## Optional US Branch

Not dispatched in this controller pass because the external-audit command framed the US tasks as optional:

- `US-WIN-R15-1`: US metadata blocker continuation.
- `US-WIN-R15-2`: US second-source HG-EXEC plan only.

Quant-Dispatcher may dispatch these only if the user explicitly asks to include the optional US branch.

## Boundary

R15 is research-only. It does not authorize recommendation/advice,
`PENDING_HUMAN_REVIEW`, ticket emission, eligibility candidates, data-clear
promotion, product-route activation, production readiness,
broker/order/paper/live/auto behavior, raw-data migration, `.env` access, key
output, or secret handling.

Future network/provider fetch, DB/cache rebuild, schema/readiness/registry
changes, and registry activation require separate task-level HG-EXEC evidence
and transcript.
