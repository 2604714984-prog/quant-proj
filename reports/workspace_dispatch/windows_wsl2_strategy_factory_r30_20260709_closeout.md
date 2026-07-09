# R30 Strategy Factory Closeout

Batch: `WINDOWS_WSL2_STRATEGY_FACTORY_R30_20260709`

Closeout status: `CLOSED_ACCEPTED_RESEARCH_ONLY_LOCAL_PROBE_ELIGIBLE_WITH_WARNINGS`

R30 is closed as a strategy factory batch because it reached the required terminal outcome `LOCAL_RESEARCH_PROBE_ELIGIBLE` for one research line: `liquidity_constrained_reversal`.

Carry-forward warnings:

- The eligible label is research-only and local/pass77 scoped.
- `strategy_candidate_available=false`.
- SmallCap remains `DO_NOT_RETRY_UNTIL_NEW_SOURCE_DIRECT_MARKET_CAP`.
- US30W remains observation-only until preservation improves.
- pass77 old repair reruns remain gated by new source evidence.
- ETF rotation remains retired under current evidence.

Final counts:

- `local_research_probe_eligible_count=1`
- `strategy_candidate_available=false`

Next source action: external audit R30. If accepted, dispatch a separate audited local research probe task for `liquidity_constrained_reversal` only.

Boundary result: `PASS_RESEARCH_ONLY`.
