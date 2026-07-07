# Paste Prompt - Research Data Fastpath Catchup External Audit

Use this prompt in the user-operated GitHub / GitHub connector external-audit conversation.

```text
Please perform a GitHub-connector external audit of the closed research-data fastpath catchup batch:

WINDOWS_WSL2_RESEARCH_DATA_FASTPATH_CATCHUP_20260707

Do not rely on this summary alone. Read the GitHub files and commits listed in the controller audit packet:

https://github.com/2604714984-prog/quant-proj/blob/main/reports/agent_handoff/windows_wsl2_research_data_fastpath_catchup_external_audit_packet_20260707.md

Primary question:
Can this batch be accepted as CLOSED_ACCEPTED_RESEARCH_ONLY_WITH_WARNINGS, with EXTERNAL_AUDIT_TRIGGER_OPEN=no and FIXES_REQUIRED=none before the next ordinary research-only task batch?

Key GitHub evidence to read:

Controller:
- Result summary: https://github.com/2604714984-prog/quant-proj/blob/37803ab65e8f83fd9f6faa10a1fb3d95d02dc949/reports/workspace_dispatch/windows_wsl2_research_data_fastpath_catchup_20260707_result_summary.md
- Closeout: https://github.com/2604714984-prog/quant-proj/blob/37803ab65e8f83fd9f6faa10a1fb3d95d02dc949/reports/workspace_dispatch/windows_wsl2_research_data_fastpath_catchup_20260707_closeout.md
- A-share callback: https://github.com/2604714984-prog/quant-proj/blob/37803ab65e8f83fd9f6faa10a1fb3d95d02dc949/reports/workspace_dispatch/windows_wsl2_research_data_fastpath_catchup_20260707_a_share_callback.md
- US callback: https://github.com/2604714984-prog/quant-proj/blob/37803ab65e8f83fd9f6faa10a1fb3d95d02dc949/reports/workspace_dispatch/windows_wsl2_research_data_fastpath_catchup_20260707_us_stock_callback.md
- Research-data fast path policy: https://github.com/2604714984-prog/quant-proj/blob/37803ab65e8f83fd9f6faa10a1fb3d95d02dc949/reports/human_gate/windows_wsl2_research_data_fast_path_policy_20260707.md

A_Share_Monitor:
- Commit: db43041f28537787a5bdf941142a9cebb2c1c962
- ETF data manifest: https://github.com/2604714984-prog/A_Share_Monitor/blob/db43041f28537787a5bdf941142a9cebb2c1c962/reports/workspace_dispatch/etf_rotation_e1_data_fetch_load_manifest_20260707.json
- ETF data report: https://github.com/2604714984-prog/A_Share_Monitor/blob/db43041f28537787a5bdf941142a9cebb2c1c962/reports/workspace_dispatch/etf_rotation_e1_data_fetch_load_report_20260707.md
- ETF no-future/data audit: https://github.com/2604714984-prog/A_Share_Monitor/blob/db43041f28537787a5bdf941142a9cebb2c1c962/reports/workspace_dispatch/etf_rotation_e1_data_audit_20260707.md
- ETF screenshot reproduction: https://github.com/2604714984-prog/A_Share_Monitor/blob/db43041f28537787a5bdf941142a9cebb2c1c962/reports/workspace_dispatch/etf_rotation_e1_screenshot_reproduction_20260707.md
- ETF research-only leaderboard notes: https://github.com/2604714984-prog/A_Share_Monitor/blob/db43041f28537787a5bdf941142a9cebb2c1c962/reports/workspace_dispatch/etf_rotation_e1_research_only_leaderboard_notes_20260707.md
- East Money reconciliation: https://github.com/2604714984-prog/A_Share_Monitor/blob/db43041f28537787a5bdf941142a9cebb2c1c962/reports/workspace_dispatch/windows_wsl2_fastpath_east_money_coverage_reconciliation_20260707.md
- A-share data-hold audit: https://github.com/2604714984-prog/A_Share_Monitor/blob/db43041f28537787a5bdf941142a9cebb2c1c962/reports/workspace_dispatch/windows_wsl2_fastpath_a_share_data_hold_audit_20260707.md

US_Stock_Monitor:
- Commit: a25b2a0693cc267a8bc7658fd3525723dcaca6f0
- US fastpath report: https://github.com/2604714984-prog/US_Stock_Monitor/blob/a25b2a0693cc267a8bc7658fd3525723dcaca6f0/reports/codex_dev/fp_us_metadata_fastpath_20260707_report.md
- US fastpath manifest: https://github.com/2604714984-prog/US_Stock_Monitor/blob/a25b2a0693cc267a8bc7658fd3525723dcaca6f0/reports/codex_dev/fp_us_metadata_fastpath_20260707_manifest.json
- US fastpath validation: https://github.com/2604714984-prog/US_Stock_Monitor/blob/a25b2a0693cc267a8bc7658fd3525723dcaca6f0/reports/codex_dev/fp_us_metadata_fastpath_20260707_validation.json
- US parser/test changes: https://github.com/2604714984-prog/US_Stock_Monitor/blob/a25b2a0693cc267a8bc7658fd3525723dcaca6f0/tests/test_us_metadata_repair.py

Please verify especially:
- The batch is research-only and can be closed accepted with warnings.
- ETF E1 data fetch/load completed with 30 ETF symbols and 55,726 rows.
- ETF timing uses close T signal and T+1 open execution; no same-day close-to-close execution.
- ETF screenshot-family reproduction is not treated as recommendation, candidate, readiness, product route, or trading signal.
- East Money broad coverage reconciliation remains provider-blocked with 0 accepted new rows; the prior 77 / 121 / 2870 split is unchanged.
- US staging completed for 270 symbols and 559,959 daily rows with duplicate-key and missingness validation passing.
- US parser cleanup salvaged previously blocked symbols by skipping sparse N/A rows at row level.
- US legacy/Tencent-only diagnostics are research labels only and do not synthesize active metadata.
- DB write, registry/readiness/product-route activation, raw-data migration, market_data activation, recommendation/advice, ticket, eligibility candidate, strategy candidate promotion, broker/order/paper/live/auto, daily signal push, active schema migration, and secrets remain blocked or forbidden.

Return:

VERDICT:
EXTERNAL_AUDIT_TRIGGER_OPEN:
FIXES_REQUIRED:
ACCEPTED_SCOPE:
REJECTED_OR_BLOCKED_SCOPE:
BOUNDARY_RESULT:
NEXT_TASKS:
```
