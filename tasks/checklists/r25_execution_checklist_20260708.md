# R25 execution checklist

Batch: `WINDOWS_WSL2_TARGETED_STRATEGY_REPAIR_AND_PROBE_R25_20260708`

## Before diagnostics

- [ ] Read R25 spec, dispatcher prompt, intake, and this checklist.
- [ ] Read R24 controller result summary and closeout.
- [ ] Read A_Share_Monitor R24 final memo, decision board, pass77 board, ETF board, and summary JSON.
- [ ] Read strategy_work R24 final sync.
- [ ] Confirm unaccepted R23 outputs are not used as evidence.

## A-share pass77

- [ ] Use only the five accepted pass77 fixed features.
- [ ] Pre-register fixed repairs before evaluation.
- [ ] Run source proxy, date-neutralized, low-turnover, rank residualized, regime-guarded repairs.
- [ ] Run reverse-signal research for `peg_proxy` only as failure analysis.
- [ ] Write required A-share artifacts.

## ETF regime-dependent diagnostics

- [ ] Use only R24 ETF amount/turnover evidence.
- [ ] Do not rerun old broad grids.
- [ ] Test only the three fixed ETF regime-on strategies.
- [ ] Use predefined regime filters only.
- [ ] Run regime walk-forward, cost, drawdown, and turnover stress.
- [ ] Write required ETF artifacts.

## Final decision

- [ ] Write final strategy decision board.
- [ ] Keep eligible labels as research-only labels.
- [ ] Keep `strategy_candidate_available=false` unless a later explicit protocol changes it.
- [ ] If no eligible rows, explicitly classify lines as continue, benchmark, repair-on-new-data-only, retire, or do-not-retry.

## Validation

- [ ] CSV parse PASS.
- [ ] JSON parse PASS where JSON artifacts exist.
- [ ] `git diff --check` PASS.
- [ ] Boundary scan PASS.
- [ ] Focused tests / `py_compile` if code changes.

## Boundary

- [ ] Research-only boundary preserved.
- [ ] No recommendation/advice, actionable output, ticket, candidate promotion, readiness/product route, daily signal, trading path, full-frame wide3068, test-result parameter selection, or secret output.
