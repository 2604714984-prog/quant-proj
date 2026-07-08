# R27 Execution Checklist - 20260709

Batch: `WINDOWS_WSL2_EVIDENCE_BACKED_STRATEGY_PROBE_R27_20260709`

## Before dispatch

- [ ] Read R25 result summary and closeout.
- [ ] Read R26 result summary and closeout.
- [ ] Read R27 spec and dispatcher prompt.
- [ ] Confirm strategy candidate availability remains false.

## SmallCap lane

- [ ] Evidence generator rerun or reproducibility check complete.
- [ ] Higher-count permutation/bootstrap stress complete or runtime-limited reason recorded.
- [ ] Walk-forward stress complete.
- [ ] Cost/capacity stress complete.
- [ ] Universe sensitivity complete.
- [ ] Leakage/timing audit complete.

## US30W lane

- [ ] Pipeline rerun complete or local-only blocker recorded.
- [ ] synthetic_data=false checked.
- [ ] Metric drift check complete.
- [ ] Remote preservation plan written if remote is still absent.
- [ ] Robustness stress complete or blocked.

## pass77 gate

- [ ] Direct/proxy validation smoke complete or blocked.
- [ ] alpha-vs-control board complete.
- [ ] No strategy rerun without improved direct/proxy evidence.

## Closeout

- [ ] JSON parse PASS.
- [ ] CSV parse PASS.
- [ ] git diff check PASS.
- [ ] tests PASS if code changed.
- [ ] overclaim scan PASS.
- [ ] final board complete.
- [ ] source callbacks received.
- [ ] strategy_work final sync complete.
- [ ] controller result summary and closeout complete.
