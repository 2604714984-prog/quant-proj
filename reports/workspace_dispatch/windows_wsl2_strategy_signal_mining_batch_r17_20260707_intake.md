# WINDOWS_WSL2_STRATEGY_SIGNAL_MINING_BATCH_R17_20260707 Intake

Project: quant-proj
Role: Quant-Dispatcher
Imported: 2026-07-07 Asia/Shanghai
Source: user-pasted GitHub connector external-audit result and R17 next-task list
Status: DISPATCH_PREPARED

## Classification

Ordinary research-only strategy signal mining batch.

External-audit trigger opened by R17: `no`.

Reason:

- The post-R15 GitHub connector external audit returned `VERIFIED_ACCEPT_WITH_WARNINGS`.
- Fixes required: `none before the next research-only strategy / GPU-signal development batch`.
- The only open audit gate is market_data product-route prep / future activation, which is not part of R17 activation scope.
- R17 explicitly forbids recommendation/advice, tickets, eligibility candidates, strategy candidate promotion, readiness, product-route activation, broker/order/paper/live/auto, raw-data migration, secrets, full-frame wide strategy search, and unapproved network/DB writes. The prior 400W GPU stop condition is superseded by the later user revocation record.

## Accepted Evidence Inputs

- R16 strategy discovery: `CLOSED_ACCEPTED_RESEARCH_ONLY_WITH_WARNINGS`.
- R16 factor diagnostics: `FACTOR_DIAGNOSTIC_WEAK=5`, `FACTOR_DIAGNOSTIC_UNSTABLE=8`, `FACTOR_DIAGNOSTIC_POSITIVE=1`.
- R16 hypothesis catalog: 13 pre-registered strategy hypothesis families.
- R16 scout result: `NO_WIDE_DIAGNOSTIC_ELIGIBLE_STRATEGY`.
- `strategy_candidate_available=false`.
- GPU Phase2/Phase3 research diagnostics accepted with warnings.
- East Money bounded probe accepted as probe-only evidence; R15/R16 `77/121/2870` split remains preserved.
- US metadata repair accepted as bounded current-universe staging with warnings.
- market_data product-route prep accepted as preparation only; no activation.
- RTX 5090 400W power cap policy was accepted as a standing constraint, then superseded by the user's 2026-07-07T16:32:56+08:00 revocation for R17 continuation under host/driver default GPU power policy.

## Dispatch Scope

### A_Share_Monitor

- `A-WIN-R17-1`: Freeze post-R16 GPU evidence surface.
- `A-WIN-R17-2`: Mine the single positive factor and unstable-factor clusters.
- `A-WIN-R17-3`: GPU ML signal decile-to-strategy bridge.
- `A-WIN-R17-4`: Pre-register strategy transformations from signal evidence.
- `A-WIN-R17-5`: Small-cache diagnostic backtests for transformed signals.
- `A-WIN-R17-6`: Wide3068 chunked probe only for pre-qualified families.
- `A-WIN-R17-7`: Trade-count and cost rescue for ML/factor-derived signals.
- `A-WIN-R17-8`: GPU power-policy telemetry and compliance report.

### market_data

- `MD-WIN-R17-1`: Keep product-route prep inactive and separated.
- `MD-WIN-R17-2`: Strategy-signal evidence manifest extension.

### strategy_work

- `SW-WIN-R17-1`: Strategy signal mining memo.
- `SW-WIN-R17-2`: Final sync after A-share and market_data callbacks.

### quant-proj

- `QP-WIN-R17-1`: R17 intake, task packet, Human-Gate classification, and dispatch summary.
- `QP-WIN-R17-2`: R17 result summary and closeout after downstream callbacks.

## Boundary

Research-only. No recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket, eligibility candidate, strategy candidate promotion, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, raw-data migration, `.env` access, key output, secret handling, schema/readiness/registry change, or market_data activation is authorized.

Future provider/network fetch, DB/cache write or rebuild, route activation, or privileged GPU power-policy changes require separate task-level authorization.
