# US-R Result Summary

## Status

`SUPERSEDED_BY_FINAL_BINARY_REJECT`

## Results

- US-01 Adaptive+Quality reproduced on the local real-data US30W pipeline.
- Final US-01 label: `BENCHMARK_ONLY`; binary decision `REJECT`.
- `strategy_candidate_available=false`.
- The strategy is not active and is not a daily-run item. The current configuration is `DO_NOT_RETRY_CURRENT_CONFIGURATION`.

This summary's earlier `CONTINUE_RESEARCH` result was superseded after the broader
106-removal survivorship audit and direct confirmation that historical optimization
ranked variants with test Sharpe.

## Evidence

- US_Stock_Monitor source evidence preserved at commit `f25a1266cc9d2bfa77ef318d4d54d0e31f4cf125`.
- US30W local cache remained at commit `7052c2b7ccd0d6fbb9b443c18101701a4ebb0f4e`; no remote is configured for that repo.
- Reproduction: Adaptive+Quality full Sharpe `0.7880`, validation Sharpe `1.8529`, test Sharpe `0.7205`, max drawdown `-11.0%`, fills `202`.
- Source crosscheck: bounded public sample PASS for SPY, QQQ, AAPL, MSFT, NVDA.
- Universe provenance: 107 cached symbols equal `FULL_TICKERS` current-directory filter; `WBA` excluded because absent from current public Nasdaq Trader directory.

## Warnings

- The original ex-ante selection date for `FULL_TICKERS` is not proven.
- The public source crosscheck is bounded, not a full vendor audit.
- This result does not create a candidate, readiness state, product route, daily signal, or execution path.

## Boundary

Research-only boundary held. No recommendation/advice, ticket, candidate promotion, readiness/product route, daily signal, broker/order/paper/live/auto execution, test-result parameter selection, raw-data migration, active registry/schema activation, or secret access/output.
