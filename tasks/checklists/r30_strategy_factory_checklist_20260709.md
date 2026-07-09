# R30 Strategy Factory Checklist - 20260709

Batch: `WINDOWS_WSL2_STRATEGY_FACTORY_R30_20260709`

## Before running diagnostics

- [ ] Read R30 spec and dispatcher prompt.
- [ ] Read latest R29 result if available.
- [ ] Confirm strategy_candidate_available remains false.
- [ ] Confirm no active route/readiness/product/trading path is involved.

## Active surfaces

- [ ] SmallCap direct market-cap evidence status checked.
- [ ] US30W preservation status checked.
- [ ] pass77 direct/proxy evidence status checked.
- [ ] ETF rotation remains retired unless new evidence changes premise.

## Strategy factory loop

- [ ] Active surfaces processed first.
- [ ] If active surfaces blocked, new strategy families pre-registered before evaluation.
- [ ] No broad grid without pre-registration.
- [ ] No test-result parameter selection.
- [ ] Engine uses T+1 / conservative fill / cost / capacity assumptions.

## Final board

- [ ] Final board includes one of: LOCAL_RESEARCH_PROBE_ELIGIBLE / NO_VERIFIABLE_STRATEGY_UNDER_CURRENT_EVIDENCE / BLOCKED_BY_AUTH_OR_SOURCE_LIMIT.
- [ ] Every strategy surface has next_action.
- [ ] Failure memory updated.

## Boundary

- [ ] No actionable output.
- [ ] No candidate promotion.
- [ ] No readiness/product route.
- [ ] No daily signal.
- [ ] No broker/order/paper/live/auto.
- [ ] No full-frame wide3068.
- [ ] No secret output.
