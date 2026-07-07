# Handoff: A_Share_Monitor ETF E1 Data Fetch/Load

Send to WSL2 downstream thread `019f387b-617e-7273-b539-161216ae3002`.

Prompt-only. Do not pass model or thinking overrides.

```text
You are Codex-Dev for /home/rongyu/workspace/A_Share_Monitor.

Task batch: WINDOWS_WSL2_A_SHARE_ETF_ROTATION_STRATEGY_BATCH_E1_DATA_FETCH_LOAD_20260707
Parent batch: WINDOWS_WSL2_A_SHARE_ETF_ROTATION_STRATEGY_BATCH_E1_20260707
Controller: /home/rongyu/workspace/quant-proj

Controller records:
- /home/rongyu/workspace/quant-proj/reports/human_gate/windows_wsl2_a_share_etf_rotation_e1_data_fetch_load_authorization_20260707.md
- /home/rongyu/workspace/quant-proj/reports/human_gate/decisions.jsonl
- /home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-a-share-etf-rotation-strategy-batch-e1-data-fetch-load-20260707/spec.md
- /home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-a-share-etf-rotation-strategy-batch-e1-data-fetch-load-20260707/human_gate.md
- /home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-a-share-etf-rotation-strategy-batch-e1-20260707/spec.md
- /home/rongyu/workspace/quant-proj/reports/workspace_dispatch/windows_wsl2_a_share_etf_rotation_strategy_batch_e1_20260707_result_summary.md

Workstream:
- HG-EXEC-TASK-A-ETF-E1-DATA-FETCH-LOAD-20260707

User authorization:
The user authorized an independent HG-EXEC for bounded ETF data fetch/load after E1 stopped at HG_EXEC_REQUIRED_FOR_ETF_DATA_FETCH.

Allowed scope:
- Fetch/load a bounded A-share ETF OHLC/NAV research dataset for E1.
- Snapshot id: etf_rotation_e1_20260707.
- Max ETF symbols: 80.
- Date range: 20180101..20260707.
- Network is allowed only for bounded public/no-secret ETF data fetch.
- Writes are allowed only for controlled local A_Share_Monitor staging/cache/report/test artifacts.
- After ETF data validation passes, resume ETF-E1-1 through ETF-E1-11 from the original E1 spec.

Required data evidence:
- command transcript;
- manifest with provider/source, symbol count, row count, date range, freshness, and hashes;
- ETF universe coverage evidence;
- missingness, duplicate key, listing-date, adjusted price/NAV, amount/volume, and timing audit;
- explicit T close signal / T+1 execution timing; no same-day close-to-close execution.

Provider/source rule:
- Use public/no-secret data only.
- Prefer existing project provider paths where available.
- For any new provider/data-source candidate, comply with the controller simonlin1212 source-candidate policy unless the existing project code already provides the source path.
- Stop if secrets, .env, keys, tokens, credentials, or auth are required.

Forbidden:
- recommendation/advice;
- PENDING_HUMAN_REVIEW;
- ticket;
- eligibility candidate;
- strategy candidate promotion;
- readiness change;
- product-route activation;
- market_data activation;
- broker/order/paper/live/auto;
- daily signal push;
- raw-data migration into quant-proj;
- unbounded provider sync;
- schema/readiness/registry changes;
- secret access/output.

Required validation:
- JSON parse PASS for JSON artifacts.
- Duplicate symbol-date validation PASS.
- Listing-date validation PASS.
- Timing/no-future audit PASS.
- py_compile PASS for changed Python files.
- focused pytest PASS if code/tests changed.
- agent_safety_check.py PASS where applicable.
- git diff --check PASS.
- forbidden overclaim scan PASS.

Callback:
Send prompt-only callback to Quant-Dispatcher thread 019f3830-4b44-7a83-944d-247a0d4dc169 using the callback envelope in the task packet.
```
