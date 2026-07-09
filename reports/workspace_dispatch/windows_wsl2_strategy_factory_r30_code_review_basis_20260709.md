# R30 Code Review Basis - 20260709

This file records the GitHub code/evidence basis used to define R30.

## Reviewed code/evidence surfaces

- A_Share_Monitor `qta/backtest/engine.py` at commit `28cccf812045be6290da44291019f6fc58204fcf`.
- A_Share_Monitor `qta/backtest/fill_model.py`.
- A_Share_Monitor `qta/backtest/portfolio.py`.
- A_Share_Monitor `qta/backtest/metrics.py`.
- A_Share_Monitor `qta/strategies/rules.py`.
- A_Share_Monitor `qta/data/universe.py`.
- A_Share_Monitor SmallCap R26/R27/R28 evidence artifacts.
- market_data R28 contract.
- strategy_work R28 final sync.

## Code-level observations

- DailyBacktestEngine keeps T+1 order scheduling semantics by generating orders on signal date for the next trade date.
- The engine has chunked support and preserves pending orders, but wide/full-frame use should remain blocked where memory or evidence rules require chunked diagnostics.
- ConservativeDailyFillModel uses open execution, slippage, suspend/limit rejection, amount/volume capacity, and lot rounding.
- Portfolio accounting supports cash, costs, positions, lot sizing, realized PnL, and close mark-to-market.
- Rules evaluation now handles empty rules correctly: AND-empty is true, OR-empty is false.
- Universe filtering handles ST, suspended, list-days, delist, board, and amount filters, but direct market-cap membership is not provided by the generic universe filter and remains the SmallCap blocker.

## R30 implication

The project does not need more controller/gate review to continue strategy research. The engine is sufficient for research-only local diagnostics if evidence inputs are complete.

R30 should therefore focus on:

1. Resolving SmallCap direct market-cap evidence via R29 if incomplete.
2. Hardening SmallCap into local research probe eligibility if direct evidence passes.
3. If blocked, moving to US30W robustness and then pre-registered new strategy families.
4. Ending with a final strategy factory board, not another open-ended process report.
