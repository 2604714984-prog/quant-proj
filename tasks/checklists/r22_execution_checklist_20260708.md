# R22 Execution Checklist - 20260708

Batch: `WINDOWS_WSL2_MATERIALIZED_FEATURE_STRATEGY_LAB_R22_20260708`

## Before dispatch

- [ ] Read C1 result summary and closeout.
- [ ] Read R22 spec.
- [ ] Confirm wide eligible count remains 0.
- [ ] Confirm candidate availability remains false.

## Before diagnostics

- [ ] C1/R21 evidence freeze complete.
- [ ] Experiment store import complete.
- [ ] Failure memory update complete.
- [ ] Source-health complete for any source-heavy work.

## ETF lane

- [ ] 32,482 amount/turnover rows validated.
- [ ] NAV/premium limitation preserved unless field evidence improves.
- [ ] R19/R20 grids not repeated without new evidence.
- [ ] Liquidity-aware diagnostics use amount/turnover.
- [ ] No daily signal output.

## A-share lane

- [ ] 136,767 pass77 feature rows validated.
- [ ] Feature timing and missingness audited.
- [ ] Validation/test divergence attributed.
- [ ] No pass77 result promoted beyond pass77 evidence scope.
- [ ] No test-result parameter selection.

## Global/news/macro lane

- [ ] Context rows aligned to research dates.
- [ ] Context used only for attribution/divergence explanation.
- [ ] No direct signal use.

## Before closeout

- [ ] JSON parse PASS.
- [ ] git diff check PASS.
- [ ] focused tests PASS if code changed.
- [ ] overclaim scan PASS.
- [ ] artifact manifest compiled.
- [ ] source callbacks received.
- [ ] strategy_work final sync complete.
- [ ] controller result summary and closeout complete.
