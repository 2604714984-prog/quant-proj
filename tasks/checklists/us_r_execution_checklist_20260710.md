# US-R Execution Checklist

- [ ] Freeze commits, trees, disabled daily launcher state, and cache hash.
- [ ] Reproduce baseline and Adaptive+Quality outputs.
- [ ] Validate synthetic/real labels.
- [ ] Verify `run_daily.sh` remains disabled.
- [ ] Confirm `evidence_trader.py` is not invoked by US-R.
- [ ] Audit universe selection bias.
- [ ] Run bounded source crosscheck or explain unavailable status.
- [ ] Run walk-forward/bootstrap diagnostics.
- [ ] Run cost/slippage/rebalance diagnostics.
- [ ] Run return attribution.
- [ ] Emit final decision board with one allowed label.
- [ ] Confirm no recommendation, no ticket, no active strategy, no daily signal,
      no paper/live/broker/auto path, no test-result parameter selection, and no
      secret output.
