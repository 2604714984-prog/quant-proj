# CALLBACK_ENVELOPE

`BATCH`: `WINDOWS_WSL2_US_ADAPTIVE_QUALITY_SURVIVORSHIP_REAUDIT_20260710`

`TARGET_REPO`: `/home/rongyu/workspace/us_stock_30w`

`BRANCH`: `master`; pushed and aligned with `origin/master`

`COMMIT`: `5a07db5c5df2cff71fb5938a9431848461cf75d0`

`TREE`: `a7660e493fec3b38ff84f2f54f9c539b0dedacc6`

`STATUS`: `PARTIAL_SURVIVORSHIP_SENSITIVITY_NONZERO_NO_TEST_CHANGE`

`TASKS_COMPLETED`: Recovered the seven-name legacy audit scope from the existing compiled artifact; implemented a tracked public/no-auth Sina daily-bar adapter and bounded cache; extracted the Adaptive+Quality signal into shared source; repaired the one-command pipeline after script relocation; reran the 107-versus-114-symbol comparison; corrected the R22-003 report and removed its execution instructions.

`ARTIFACTS`: `scripts/run_survivorship_audit.py`; `scripts/adaptive_quality_core.py`; `tests/test_survivorship_audit.py`; `reports/US30W-R22-003_survivorship_reaudit_20260710.md`; `reports/US30W-R22-003_survivorship_reaudit_20260710.json`; `reports/US30W-R22-003_survivorship_reaudit_20260710.csv`; corrected `reports/US30W-R22-003_final.md`.

`VALIDATION`: Seven of seven fixed historical names passed field/date/duplicate/minimum-row validation. Full pipeline PASS with baseline and Adaptive+Quality metrics reproduced; full US framework tests PASS; focused survivorship tests `4 passed`; `py_compile` PASS; JSON/CSV assertions PASS; `agent_safety_check.py` PASS; `git diff --check` PASS; remote ref verified at the recorded commit.

`KEY_RESULTS`: Current 107-symbol full Sharpe `0.787952`, return `0.647107`, max drawdown `-0.110425`, test Sharpe `0.720499`, fills `202`. Expanded 114-symbol full Sharpe `0.771392`, return `0.633556`, max drawdown `-0.113954`, test Sharpe `0.720499`, fills `203`. ABMD generated two filled events. The prior zero-impact statement is false.

`SURVIVORSHIP_STATUS`: The risk was considered previously at framework and report level, but its source/evidence chain was incomplete. The new bounded audit is reproducible and shows nonzero full-period sensitivity. It is not a complete point-in-time membership reconstruction, so the risk remains partially open.

`STRATEGY_STATUS`: `CONTINUE_RESEARCH` lead only; `strategy_candidate_available=false`; no daily run or active-strategy status.

`BOUNDARY_RESULT`: Research-only. No recommendation, ticket, candidate promotion, readiness/product route, daily signal, broker/order/live execution, test-result parameter selection, or secret access/output.

`NEXT_SOURCE_ACTION`: Build or acquire a complete public point-in-time historical membership and delisted-security dataset with corporate-action evidence, then rerun the fixed audit without changing strategy parameters.
