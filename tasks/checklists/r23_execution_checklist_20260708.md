# R23 Execution Checklist - 20260708

Batch: `WINDOWS_WSL2_VALIDATION_DIVERGENCE_BREAKTHROUGH_R23_20260708`

## Before dispatch

- [ ] Read R22 result summary and closeout.
- [ ] Read R23 spec and dispatcher prompt.
- [ ] Confirm no local or wide probe was eligible in R22.
- [ ] Confirm candidate availability remains false.

## Before diagnostics

- [ ] R22 evidence freeze complete.
- [ ] Experiment store import complete.
- [ ] Failure memory update complete.
- [ ] Source health complete for any source-heavy task.

## A-share divergence lane

- [ ] Period attribution complete.
- [ ] Symbol-cohort attribution complete.
- [ ] Feature construction audit complete.
- [ ] Outlier/winsorization sensitivity complete.
- [ ] Regime attribution complete.
- [ ] Cost/turnover attribution complete.

## Transformation lane

- [ ] Transformations pre-registered before evaluation.
- [ ] No test-result parameter selection.
- [ ] Holdout/test reported diagnostic-only.

## ETF lane

- [ ] Instability decomposed under amount/turnover context.
- [ ] No old ETF grid rerun without new evidence.
- [ ] NAV/premium status updated or unavailable label preserved.

## Closeout

- [ ] JSON parse PASS.
- [ ] git diff check PASS.
- [ ] focused tests PASS if code changed.
- [ ] overclaim scan PASS.
- [ ] artifact manifest compiled.
- [ ] source callbacks received.
- [ ] strategy_work final sync complete.
- [ ] controller result summary and closeout complete.
