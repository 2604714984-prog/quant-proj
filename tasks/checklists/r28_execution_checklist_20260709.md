# R28 Execution Checklist - 20260709

Batch: `WINDOWS_WSL2_SMALLCAP_EVIDENCE_COMPLETION_R28_20260709`

## Before dispatch

- [ ] Read R27 result summary and closeout.
- [ ] Read R28 spec and dispatcher prompt.
- [ ] Confirm SmallCap is CONTINUE_RESEARCH but not local-probe eligible.
- [ ] Confirm strategy candidate availability remains false.

## SmallCap evidence completion

- [ ] Row-level pre-trade signal matrix generated.
- [ ] Market-cap universe membership snapshot generated.
- [ ] Entry candidate diagnostics generated.
- [ ] Post-trade fill linkage separated from pre-trade evidence.
- [ ] Hash manifest complete.

## Leakage/timing audit

- [ ] Signal fields pre-trade availability verified.
- [ ] Universe membership timing verified.
- [ ] Entry ranking audit complete.
- [ ] Split leakage audit complete.
- [ ] Test-result parameter selection check complete.

## Robustness

- [ ] Metrics rebuilt from row-level matrix.
- [ ] Permutation/bootstrap update complete or runtime-limited reason recorded.
- [ ] Walk-forward and cost/capacity update complete.
- [ ] Drift versus R26/R27 explained.

## Closeout

- [ ] JSON parse PASS.
- [ ] CSV/parquet read PASS.
- [ ] git diff check PASS.
- [ ] focused tests PASS if code changed.
- [ ] overclaim scan PASS.
- [ ] final board complete.
- [ ] source callbacks received.
- [ ] strategy_work final sync complete.
- [ ] controller result summary and closeout complete.
