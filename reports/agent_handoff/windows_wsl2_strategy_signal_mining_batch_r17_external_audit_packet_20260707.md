# External Audit Packet - R17 Strategy Signal Mining

Project: quant-proj
Role: Quant-Dispatcher
Prepared: 2026-07-07 Asia/Shanghai
Submission: user-operated external audit through GitHub / GitHub connector

## Review Request

Please externally review `WINDOWS_WSL2_STRATEGY_SIGNAL_MINING_BATCH_R17_20260707` using GitHub / GitHub connector as the primary evidence source.

This external audit packet is user-requested. R17 itself did not open a controller external-audit trigger. It is not an activation request, not a recommendation request, and not a trading or readiness request.

## Verdict Requested

Please return:

```text
VERDICT:
EXTERNAL_AUDIT_TRIGGER_OPEN:
FIXES_REQUIRED:
ACCEPTED_SCOPE:
REJECTED_OR_BLOCKED_SCOPE:
BOUNDARY_RESULT:
NEXT_TASKS:
```

## Expected Review Scope

Review the GitHub files and commits listed below. Do not rely on oral summaries.

You do not need to manually expand every row of every CSV, but please verify the controller closeout, source summaries, JSON/schema files, final sync, validation claims, and key source refs are internally consistent.

## Controller Evidence

Repository: `https://github.com/2604714984-prog/quant-proj`

Controller closeout commit before this audit packet:

- Commit: `ae9a2e1d4ce2fbf6d38ee83cb198cee52054b7eb`
- Tree: `280e289cf2f1818e1ea78832bc946c823a86b235`

Primary controller files to review:

- R17 closeout: https://github.com/2604714984-prog/quant-proj/blob/ae9a2e1d4ce2fbf6d38ee83cb198cee52054b7eb/reports/workspace_dispatch/windows_wsl2_strategy_signal_mining_batch_r17_20260707_closeout.md
- R17 result summary: https://github.com/2604714984-prog/quant-proj/blob/ae9a2e1d4ce2fbf6d38ee83cb198cee52054b7eb/reports/workspace_dispatch/windows_wsl2_strategy_signal_mining_batch_r17_20260707_result_summary.md
- R17 dispatch summary: https://github.com/2604714984-prog/quant-proj/blob/ae9a2e1d4ce2fbf6d38ee83cb198cee52054b7eb/reports/workspace_dispatch/windows_wsl2_strategy_signal_mining_batch_r17_20260707_dispatch_summary.md
- R17 intake: https://github.com/2604714984-prog/quant-proj/blob/ae9a2e1d4ce2fbf6d38ee83cb198cee52054b7eb/reports/workspace_dispatch/windows_wsl2_strategy_signal_mining_batch_r17_20260707_intake.md
- R17 task packet: https://github.com/2604714984-prog/quant-proj/blob/ae9a2e1d4ce2fbf6d38ee83cb198cee52054b7eb/tasks/in_progress/windows-wsl2-strategy-signal-mining-batch-r17-20260707/spec.md
- R17 A-share callback: https://github.com/2604714984-prog/quant-proj/blob/ae9a2e1d4ce2fbf6d38ee83cb198cee52054b7eb/reports/workspace_dispatch/windows_wsl2_strategy_signal_mining_batch_r17_20260707_a_share_callback.md
- R17 A-share push callback: https://github.com/2604714984-prog/quant-proj/blob/ae9a2e1d4ce2fbf6d38ee83cb198cee52054b7eb/reports/workspace_dispatch/windows_wsl2_strategy_signal_mining_batch_r17_20260707_a_share_push_callback.md
- R17 market_data callback: https://github.com/2604714984-prog/quant-proj/blob/ae9a2e1d4ce2fbf6d38ee83cb198cee52054b7eb/reports/workspace_dispatch/windows_wsl2_strategy_signal_mining_batch_r17_20260707_market_data_callback.md
- R17 market_data push callback: https://github.com/2604714984-prog/quant-proj/blob/ae9a2e1d4ce2fbf6d38ee83cb198cee52054b7eb/reports/workspace_dispatch/windows_wsl2_strategy_signal_mining_batch_r17_20260707_market_data_push_callback.md
- R17 strategy_work callback: https://github.com/2604714984-prog/quant-proj/blob/ae9a2e1d4ce2fbf6d38ee83cb198cee52054b7eb/reports/workspace_dispatch/windows_wsl2_strategy_signal_mining_batch_r17_20260707_strategy_work_callback.md
- GPU power cap revocation: https://github.com/2604714984-prog/quant-proj/blob/ae9a2e1d4ce2fbf6d38ee83cb198cee52054b7eb/reports/human_gate/windows_wsl2_5090_gpu_power_cap_revocation_20260707.md
- Post-R15 external audit result that produced R17: https://github.com/2604714984-prog/quant-proj/blob/ae9a2e1d4ce2fbf6d38ee83cb198cee52054b7eb/reports/agent_handoff/windows_wsl2_post_r15_development_external_audit_result_20260707.md

## A_Share_Monitor Evidence

Repository: `https://github.com/2604714984-prog/A_Share_Monitor`

- Commit: `e9ed119f69413d7432904e11f12f7c4ff3c9243f`
- Tree: `f942b4c910a73e946915f67db66f908e429a9c91`
- Branch after push: `origin/codex/harden-a-share-research-pipeline`

Primary files to review:

- R17 strategy signal evidence freeze MD: https://github.com/2604714984-prog/A_Share_Monitor/blob/e9ed119f69413d7432904e11f12f7c4ff3c9243f/reports/workspace_dispatch/windows_wsl2_r17_strategy_signal_evidence_freeze_20260707.md
- R17 strategy signal evidence freeze JSON: https://github.com/2604714984-prog/A_Share_Monitor/blob/e9ed119f69413d7432904e11f12f7c4ff3c9243f/reports/workspace_dispatch/windows_wsl2_r17_strategy_signal_evidence_freeze_20260707.json
- R17 factor signal mining MD: https://github.com/2604714984-prog/A_Share_Monitor/blob/e9ed119f69413d7432904e11f12f7c4ff3c9243f/reports/workspace_dispatch/windows_wsl2_r17_factor_signal_mining_20260707.md
- R17 factor signal mining CSV: https://github.com/2604714984-prog/A_Share_Monitor/blob/e9ed119f69413d7432904e11f12f7c4ff3c9243f/reports/workspace_dispatch/windows_wsl2_r17_factor_signal_mining_20260707.csv
- R17 GPU ML signal bridge MD: https://github.com/2604714984-prog/A_Share_Monitor/blob/e9ed119f69413d7432904e11f12f7c4ff3c9243f/reports/workspace_dispatch/windows_wsl2_r17_gpu_ml_signal_bridge_20260707.md
- R17 GPU ML signal bridge CSV: https://github.com/2604714984-prog/A_Share_Monitor/blob/e9ed119f69413d7432904e11f12f7c4ff3c9243f/reports/workspace_dispatch/windows_wsl2_r17_gpu_ml_signal_bridge_20260707.csv
- R17 pre-registered signal transformations MD: https://github.com/2604714984-prog/A_Share_Monitor/blob/e9ed119f69413d7432904e11f12f7c4ff3c9243f/reports/workspace_dispatch/windows_wsl2_r17_pre_registered_signal_transformations_20260707.md
- R17 pre-registered signal transformations JSON: https://github.com/2604714984-prog/A_Share_Monitor/blob/e9ed119f69413d7432904e11f12f7c4ff3c9243f/reports/workspace_dispatch/windows_wsl2_r17_pre_registered_signal_transformations_20260707.json
- R17 small/medium diagnostics MD: https://github.com/2604714984-prog/A_Share_Monitor/blob/e9ed119f69413d7432904e11f12f7c4ff3c9243f/reports/workspace_dispatch/windows_wsl2_r17_small_medium_signal_strategy_diagnostics_20260707.md
- R17 small/medium diagnostics CSV: https://github.com/2604714984-prog/A_Share_Monitor/blob/e9ed119f69413d7432904e11f12f7c4ff3c9243f/reports/workspace_dispatch/windows_wsl2_r17_small_medium_signal_strategy_diagnostics.csv
- R17 wide3068 probe result/skip MD: https://github.com/2604714984-prog/A_Share_Monitor/blob/e9ed119f69413d7432904e11f12f7c4ff3c9243f/reports/workspace_dispatch/windows_wsl2_r17_wide3068_chunked_probe_result_or_skip_20260707.md
- R17 wide3068 probe result/skip CSV: https://github.com/2604714984-prog/A_Share_Monitor/blob/e9ed119f69413d7432904e11f12f7c4ff3c9243f/reports/workspace_dispatch/windows_wsl2_r17_wide3068_chunked_probe_result_or_skip.csv
- R17 trade/cost rescue MD: https://github.com/2604714984-prog/A_Share_Monitor/blob/e9ed119f69413d7432904e11f12f7c4ff3c9243f/reports/workspace_dispatch/windows_wsl2_r17_trade_cost_rescue_for_signal_strategies_20260707.md
- R17 trade/cost rescue CSV: https://github.com/2604714984-prog/A_Share_Monitor/blob/e9ed119f69413d7432904e11f12f7c4ff3c9243f/reports/workspace_dispatch/windows_wsl2_r17_trade_cost_rescue_for_signal_strategies.csv
- R17 GPU power policy compliance: https://github.com/2604714984-prog/A_Share_Monitor/blob/e9ed119f69413d7432904e11f12f7c4ff3c9243f/reports/workspace_dispatch/windows_wsl2_r17_gpu_power_policy_compliance_20260707.md
- R17 summary JSON: https://github.com/2604714984-prog/A_Share_Monitor/blob/e9ed119f69413d7432904e11f12f7c4ff3c9243f/reports/workspace_dispatch/windows_wsl2_r17_strategy_signal_mining_summary_20260707.json
- R17 generator script: https://github.com/2604714984-prog/A_Share_Monitor/blob/e9ed119f69413d7432904e11f12f7c4ff3c9243f/scripts/generate_windows_wsl2_r17_strategy_signal_mining.py
- R17 tests: https://github.com/2604714984-prog/A_Share_Monitor/blob/e9ed119f69413d7432904e11f12f7c4ff3c9243f/tests/test_windows_wsl2_r17_strategy_signal_mining.py

## market_data Evidence

Repository: `https://github.com/2604714984-prog/market_data`

- Commit: `84b752da2a602995aa5a1ce95755385a4ad44455`
- Tree: `3bdab5f40169452b59c54136335f44266a5b7eab`
- Branch after push: `origin/main`

Primary files to review:

- R17 product-route prep inactive boundary: https://github.com/2604714984-prog/market_data/blob/84b752da2a602995aa5a1ce95755385a4ad44455/reports/codex_dev/windows_wsl2_r17_product_route_prep_inactive_boundary_20260707.md
- R17 strategy signal manifest schema MD: https://github.com/2604714984-prog/market_data/blob/84b752da2a602995aa5a1ce95755385a4ad44455/reports/codex_dev/windows_wsl2_r17_strategy_signal_manifest_schema.md
- R17 strategy signal manifest schema JSON: https://github.com/2604714984-prog/market_data/blob/84b752da2a602995aa5a1ce95755385a4ad44455/reports/codex_dev/windows_wsl2_r17_strategy_signal_manifest_schema.json

## strategy_work Evidence

Repository: `https://github.com/2604714984-prog/strategy_work`

- Commit: `3e2215f56d19ee2bf6c85176be189ceae1b3f0a3`
- Tree: `e6d2fb2c13918fac34850989123250a2c9ea821d`
- Branch after push: `origin/main`

Primary files to review:

- R17 strategy memo: https://github.com/2604714984-prog/strategy_work/blob/3e2215f56d19ee2bf6c85176be189ceae1b3f0a3/reports/planning/windows_wsl2_strategy_signal_mining_batch_r17_20260707_strategy_memo.md
- R17 final sync: https://github.com/2604714984-prog/strategy_work/blob/3e2215f56d19ee2bf6c85176be189ceae1b3f0a3/reports/planning/windows_wsl2_strategy_signal_mining_batch_r17_final_sync_20260707.md

## Facts To Verify

Please verify:

1. R17 is correctly closed as `CLOSED_ACCEPTED_RESEARCH_ONLY_WITH_WARNINGS`.
2. R17 did not open a controller-required external-audit trigger.
3. `strategy_candidate_available=false` is preserved across controller, A_Share_Monitor, market_data, and strategy_work.
4. R17 found no wide-prequalified strategy rows.
5. Wide3068 result is `NO_R17_WIDE_PROBE_ELIGIBLE_STRATEGY`.
6. A_Share_Monitor did not run full-frame wide3068 and did not run chunked wide3068 because no family qualified.
7. The single positive diagnostic factor, `medium_overlap_198_not_pass / low_vol_20`, is not promoted to candidate/readiness/recommendation and did not satisfy the same-universe pass-only gate.
8. R16 factor labels remain `WEAK=5`, `UNSTABLE=8`, `POSITIVE=1`.
9. East Money split remains `77 CROSSCHECK_PASS`, `121 CROSSCHECK_DATE_GAP`, `2870 CROSSCHECK_MISSING_EAST_MONEY`.
10. market_data product-route prep remains inactive and separated; no registry/readiness/product route changed.
11. The RTX 5090 400W cap revocation is power-policy only and did not authorize broader scope.
12. No reviewed file creates recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket, eligibility candidate, strategy candidate promotion, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, raw-data migration, secret exposure, DB write, network ingest, schema migration, registry activation, market_data activation, or ranked actionable list.

## Known Warnings

- No strategy candidate is available.
- R17 found no wide-prequalified strategy.
- The single positive diagnostic factor remains overlap-only and did not satisfy the same-universe pass-only gate.
- East Money coverage remains partial under the preserved `77/121/2870` split.
- market_data product-route prep remains inactive and external-audit gated before any separate activation task.

## Requested Outcome

If accepted, please provide the next ordinary research-only task list. Do not propose recommendation, ticket, eligibility candidate, readiness, product-route activation, broker/order/paper/live/auto, or market_data activation unless you explicitly identify a real boundary trigger and required separate gates.
