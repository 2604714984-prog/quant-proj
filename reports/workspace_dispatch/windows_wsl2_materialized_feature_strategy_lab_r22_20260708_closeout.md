# WINDOWS_WSL2_MATERIALIZED_FEATURE_STRATEGY_LAB_R22_20260708 closeout

Recorded: 2026-07-08 Asia/Shanghai

## Closeout status

`CLOSED_ACCEPTED_RESEARCH_ONLY_WITH_NO_PROBE_ELIGIBLE`

R22 is closed as a research-only materialized-feature diagnostics batch. It is not a recommendation, ticket, candidate, readiness, product-route, registry, daily-signal, or trading batch.

## Final accepted commits

| repo | commit | preserved |
| --- | --- | --- |
| quant-proj | this closeout commit | controller R22 branch |
| A_Share_Monitor | `9a450019a07f55534bb2eddedd401b56825f6683` | `origin/codex/task-packet-r20-v2-20260708` |
| market_data | `9e097fe959bed433fae5dfae75493dba7b08f10e` | `origin/main` |
| strategy_work | `bb6a0d953e1aa5dfeb80f7303cf54c80ee2cd00e` | `origin/main` |

## Final result

R22 successfully ran diagnostics on materialized C1/R21 evidence. The result is negative for probe eligibility:

- `local_research_probe_eligible_count=0`
- `wide_research_probe_eligible_count=0`
- `strategy_candidate_available=false`

## Accepted scope

- ETF amount/turnover row evidence was used for liquidity-aware and turnover-throttled diagnostics.
- Partial ETF NAV/premium evidence was preserved with limitation context.
- pass77 fixed-feature rows were used for quality, IC/decile/stability, divergence, neutralized/opposite, regime-conditioned, pair/triple, walk-forward, and bootstrap diagnostics.
- global/news/macro rows were used only as context and divergence attribution.
- market_data preserved probe labels as research-only labels.
- strategy_work final sync accepted the no-probe result.

## Rejected or blocked scope

- No local research probe is eligible.
- No wide research probe is eligible.
- No full-frame wide3068 was attempted.
- No pass77 finding was promoted beyond pass77 evidence scope.
- No news/macro context was used as a direct signal.
- No strategy candidate is available.

## External audit trigger

`EXTERNAL_AUDIT_TRIGGER_OPEN=no`

R22 did not activate market_data routes, readiness, registry state, production adapters, product paths, daily signals, or trading paths. No controller-required external-audit trigger remains open for R22 closeout.

## Fixes required

`none`

## Carry-forward warnings

- ETF NAV/premium evidence remains partial.
- pass77 evidence remains pass77-scoped and cannot be generalized to wider A-share universes.
- validation/test divergence remains the central strategy blocker.
- local and wide research probe eligibility remain zero.
- strategy candidate availability remains false.

## Next task direction

Continue research-only work by focusing on blocker decomposition, feature transformations that do not use test-result parameter selection, and additional public/no-secret materialization only where it changes the failed premise. Do not reopen broad rule cleanup or old grid reruns without new evidence.
