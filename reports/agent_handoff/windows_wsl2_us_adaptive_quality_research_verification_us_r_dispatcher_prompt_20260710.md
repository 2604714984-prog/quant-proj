# Dispatcher Prompt - US-R Adaptive+Quality Research Verification

DISPATCH WINDOWS_WSL2_US_ADAPTIVE_QUALITY_RESEARCH_VERIFICATION_US_R_20260710

Read:

- `tasks/in_progress/windows-wsl2-us-adaptive-quality-research-verification-us-r-20260710/spec.md`
- `STRATEGY_VAULT/README.md`
- `STRATEGY_VAULT/US-R_batch/verification_record.md`
- `US_Stock_Monitor/reports/codex_dev/us_local_simulation_boundary_20260710.md`
- `us_stock_30w/reports/US30W-R22-002_final_strategy.md`

Goal:

Evaluate Adaptive+Quality as a US research lead. Do not prove usability. Decide
exactly one label: CONTINUE_RESEARCH, BENCHMARK_ONLY, REPAIR_REQUIRED, or
DO_NOT_RETRY.

Priority:

- Reproduce current pipeline outputs.
- Audit 107-symbol universe selection bias.
- Cross-check public/no-secret source sample if feasible.
- Run walk-forward/bootstrap/cost/rebalance diagnostics without test-result
  parameter selection.
- Attribute returns by beta, sector, concentration, and regime.

Boundary:

Research-only. Do not launch `evidence_trader.py`; local simulation is preserved
but not part of US-R execution. Do not create daily signal, paper/live path,
broker/order path, recommendation, ticket, candidate promotion, readiness, route,
or product activation.
