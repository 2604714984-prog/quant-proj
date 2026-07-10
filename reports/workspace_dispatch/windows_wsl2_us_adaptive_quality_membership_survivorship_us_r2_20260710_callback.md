# CALLBACK_ENVELOPE

> Intermediate result superseded by the final binary adjudication: `REJECT` / `BENCHMARK_ONLY`.

`BATCH`: `WINDOWS_WSL2_US_ADAPTIVE_QUALITY_MEMBERSHIP_SURVIVORSHIP_US_R2_20260710`

`TARGET_REPO`: `/home/rongyu/workspace/us_stock_30w`

`BRANCH`: `master`; pushed and aligned with `origin/master`

`COMMIT`: `88283741acdf486d35f29a3c35f4da4c5d889423`

`TREE`: `7ca056d2ad5fcaa62dc1d2a1082d00e1fbce83c7`

`STATUS`: `BROAD_REMOVAL_SENSITIVITY_PASS_WITH_EX_ANTE_LIMITATION`

`TASKS_COMPLETED`: Parsed and hashed the public 2020-2025 S&P 500 change table; reconstructed membership intervals for removed tickers; materialized and validated public/no-auth Sina histories; added point-in-time eligibility to the fixed Adaptive+Quality signal; reran the current 107-symbol baseline against a base-plus-removed-membership sensitivity universe; updated the R22-003 report and research status.

`SOURCE_HEALTH`: Wikipedia change table HTTP PASS and parsed `119` bounded events; normalized event-table SHA-256 `b57480e61a2932999c205e349cc5ba046e900739bed87bb135bf1393b85d8c31`. Sina public/no-auth daily source returned history for all `106` unique removed tickers.

`MATERIALIZED_DATA_STATUS`: Base symbols `107`; expanded symbols `213`; accepted removed histories `106/106`; 100 histories have at least 252 rows; six short membership episodes cannot satisfy the 252-row momentum warmup; duplicate/date/field validation PASS; no stale position remained after an added symbol's last available bar.

`DIAGNOSTICS_STATUS`: Point-in-time eligibility was enforced in both market breadth and symbol selection. Fifteen added historical symbols generated `43` filled events. Test outcomes were diagnostic only and were not used to select parameters.

`KEY_RESULTS`: Current 107-symbol Full Sharpe `0.787952`, Full Return `0.647107`, Max Drawdown `-0.110425`, Validation Sharpe `1.852881`, Test Sharpe `0.720499`. Expanded sensitivity Full Sharpe `0.552626`, Full Return `0.407722`, Max Drawdown `-0.146720`, Validation Sharpe `1.542243`, Test Sharpe `0.722682`. Deltas are `-0.235326`, `-0.239385`, `-0.036295`, `-0.310638`, and `+0.002183`, respectively.

`STRATEGY_STATUS`: `REPAIR_REQUIRED`; research lead retained; not active; `strategy_candidate_available=false`.

`LIMITATIONS`: The original 107 symbols still lack an ex-ante selection date. The public membership table is secondary evidence rather than an official licensed constituent feed. Public price history does not reconstruct every corporate action.

`VALIDATION`: `py_compile` PASS; focused tests `6 passed`; complete one-command pipeline PASS; framework tests PASS; JSON/CSV assertions PASS; `agent_safety_check.py` PASS; `git diff --check` PASS; remote ref verified at the recorded commit.

`BOUNDARY_RESULT`: Research-only. No recommendation, ticket, candidate promotion, readiness/product route, daily signal, broker/order/live execution, full-frame unrelated strategy search, test-result parameter selection, or secret access/output.

`NEXT_SOURCE_ACTION`: Replace the manual current-list universe with a pre-registered deterministic universe rule or an official point-in-time constituent dataset, then rerun Adaptive+Quality unchanged. Do not tune parameters against the diagnostic test segment.
