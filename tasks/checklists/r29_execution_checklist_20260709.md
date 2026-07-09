# R29 Execution Checklist - 20260709

Batch: `WINDOWS_WSL2_SMALLCAP_DIRECT_MARKETCAP_R29_20260709`

## Before dispatch

- [ ] Read R28 result summary and closeout.
- [ ] Read R29 spec and dispatcher prompt.
- [ ] Confirm direct market-cap coverage is 0.0 in R28.
- [ ] Confirm strategy candidate availability remains false.

## Direct market-cap source work

- [ ] Public/no-secret source health completed.
- [ ] Direct market-cap materialization completed or unavailable proof written.
- [ ] No auth/secret/non-public source used.

## If materialized

- [ ] Direct-vs-proxy membership audit complete.
- [ ] Membership timing audit complete.
- [ ] Signal matrix rebuilt from direct market-cap membership.
- [ ] Metrics and robustness recomputed.
- [ ] Drift report completed.

## If unavailable

- [ ] DIRECT_MARKET_CAP_UNAVAILABLE label written.
- [ ] SmallCap local-probe reconsideration stopped until source evidence changes.

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
