# US-R US_Stock_Monitor Callback

CALLBACK_ENVELOPE:
BATCH: WINDOWS_WSL2_US_ADAPTIVE_QUALITY_RESEARCH_VERIFICATION_US_R_20260710
TARGET_REPO: /home/rongyu/workspace/US_Stock_Monitor
BRANCH: main
COMMIT: f25a1266cc9d2bfa77ef318d4d54d0e31f4cf125
TREE: c4fdf7d8a532736e459cf8eda15c76bea22eebeb
STATUS: COMPLETED_RESEARCH_ONLY_CONTINUE_RESEARCH_WITH_PROVENANCE_REPAIR
TASKS_COMPLETED: Reproduced US30W real-data pipeline, validated synthetic=false labels, verified run_daily disabled, confirmed evidence_trader was not invoked, ran bounded public source crosscheck, fixed diagnostics, return attribution, and 107-symbol universe provenance repair.
ARTIFACTS: US_Stock_Monitor reports/workspace_dispatch/us_r_*_20260710.* and scripts/run_us_r_adaptive_quality_verification.py; scripts/run_us_r_universe_provenance_repair.py.
VALIDATION: run_pipeline PASS; pytest PASS; py_compile PASS; agent_safety_check PASS; JSON/CSV parse PASS; git diff --check PASS; boundary scan PASS; origin/main verified.
REPRODUCTION_STATUS: PASS_REAL_DATA_PIPELINE; Adaptive+Quality full Sharpe 0.7880, validation Sharpe 1.8529, test Sharpe 0.7205, max drawdown -11.0%, fills 202.
UNIVERSE_BIAS_STATUS: PROVENANCE_REPAIRED_CURRENT_DIRECTORY_FILTER_WITH_EX_ANTE_DATE_LIMITATION; FULL_TICKERS=108, cache=107, current public directory members=107, WBA excluded because absent from current Nasdaq Trader directory; remaining limitation is ex-ante selection date not proven.
SOURCE_CROSSCHECK_STATUS: PASS_BOUNDED_SAMPLE for SPY, QQQ, AAPL, MSFT, NVDA via public Yahoo chart JSON.
DIAGNOSTICS_STATUS: PASS_FIXED_RESEARCH_DIAGNOSTICS_NO_PARAMETER_SELECTION.
FINAL_US01_LABEL: CONTINUE_RESEARCH
STRATEGY_CANDIDATE_AVAILABLE: false
BOUNDARY_RESULT: Research-only. No daily signal, active strategy, recommendation/advice, ticket, candidate promotion, readiness, product route, broker/order/paper/live/auto execution, test-result parameter selection, or secret access/output.
FIXES_REQUIRED: Ex-ante list dating still not proven; broader source crosscheck remains a future research hardening task.
NEXT_SOURCE_ACTION: Close US-R as research-only CONTINUE_RESEARCH; do not activate daily run or strategy candidate.
