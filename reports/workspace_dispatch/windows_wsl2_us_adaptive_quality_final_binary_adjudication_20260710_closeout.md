# CALLBACK_ENVELOPE

`BATCH`: `WINDOWS_WSL2_US_ADAPTIVE_QUALITY_FINAL_BINARY_ADJUDICATION_20260710`

`TARGET_REPO`: `/home/rongyu/workspace/us_stock_30w`

`BRANCH`: `master`; pushed and aligned with `origin/master`

`COMMIT`: `c50ea74fde8939cbedc79f274d15574f55e9aecf`

`TREE`: `ab07293d46ce903efb7497217c3f9d7fe50339fc`

`STATUS`: `FINAL_BINARY_REJECT_BENCHMARK_ONLY`

`DECISION`: `REJECT`

`ACTIVE_STRATEGY`: `false`

`USE_ACCEPTED`: `false`

`RESEARCH_DISPOSITION`: `BENCHMARK_ONLY`

`RETRY_DISPOSITION`: `DO_NOT_RETRY_CURRENT_CONFIGURATION`

`DECISION_RULE`: Accept only if every required gate passes; otherwise reject.

`PASS_GATES`: Reproducible real-data pipeline; close-T signal and next-session-open execution/no-lookahead implementation.

`FAILED_GATES`: Test-selection integrity; ex-ante universe provenance; survivorship robustness; corporate-action completeness.

`DECISIVE_EVIDENCE`: `scripts/improve_strat.py:316` computes the winning score using `test_s * 2` and test drawdown; `scripts/opt_r2.py:288` labels the highest Test Sharpe; the R22-002 report records an OOS-best test result during strategy evolution. The 106-removal audit reduced Full Sharpe by `-0.235326` and Validation Sharpe by `-0.310638`, with 15 added symbols producing 43 filled events.

`ARTIFACTS`: `reports/US30W-FINAL_BINARY_ADJUDICATION_20260710.md/json`; `scripts/run_final_binary_adjudication.py`; `tests/test_final_binary_adjudication.py`; updated Vault and R22-003 records.

`VALIDATION`: Binary adjudication assertions PASS; focused tests `8 passed`; complete one-command pipeline PASS; framework tests PASS; `py_compile` PASS; JSON parse/assertions PASS; `agent_safety_check.py` PASS; `git diff --check` PASS; source remote ref verified.

`STRATEGY_CANDIDATE_AVAILABLE`: `false`

`BOUNDARY_RESULT`: Research-only adjudication. No recommendation, ticket, candidate promotion, readiness/product route, daily signal, broker/order/live execution, or secret access/output. `evidence_trader.py` was not modified.

`NEXT_SOURCE_ACTION`: None for the current Adaptive+Quality configuration. Any future US strategy must start as a materially new, pre-registered strategy with an untouched holdout and deterministic point-in-time universe; it must not inherit this strategy's acceptance status.
