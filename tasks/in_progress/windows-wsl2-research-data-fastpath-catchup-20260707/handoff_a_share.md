# Handoff: A_Share_Monitor Fastpath Catchup

Send to WSL2 downstream thread `019f387b-617e-7273-b539-161216ae3002`.

Prompt-only. Do not pass model or thinking overrides.

```text
You are Codex-Dev for /home/rongyu/workspace/A_Share_Monitor.

Task batch: WINDOWS_WSL2_RESEARCH_DATA_FASTPATH_CATCHUP_20260707
Controller: /home/rongyu/workspace/quant-proj

Read first:
- /home/rongyu/workspace/quant-proj/reports/human_gate/windows_wsl2_research_data_fast_path_policy_20260707.md
- /home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-research-data-fastpath-catchup-20260707/spec.md
- /home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-research-data-fastpath-catchup-20260707/human_gate.md
- /home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-a-share-etf-rotation-strategy-batch-e1-data-fetch-load-20260707/spec.md
- /home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-a-share-etf-rotation-strategy-batch-e1-20260707/spec.md

Policy:
Research-data fast path is active. Per-task HG-EXEC is no longer required for bounded, public/no-secret, source-local, research-only network fetch and research cache/staging/report/test writes. Transcript, manifest/count/hash evidence, validation, and callback are still required.

Tasks:
1. FP-A-1: Finish ETF E1 data fetch/load if already running, then resume ETF-E1-1 through ETF-E1-11 if ETF data validates.
   - max ETF symbols: 80
   - date range: 20180101..20260707
   - snapshot id: etf_rotation_e1_20260707
2. FP-A-2: Run East Money coverage reconciliation catchup for the current A-share research universe up to 3068 symbols, public/no-secret only, source-local research artifacts only.
   - preserve prior 77/121/2870 split until source evidence explicitly changes.
3. FP-A-3: Audit old A-share data holds that referenced suspension/limit repair or network/write blockers; mark superseded if already resolved, or produce bounded research-only evidence if still missing.

Forbidden:
- recommendation/advice;
- PENDING_HUMAN_REVIEW, ticket, eligibility candidate, strategy candidate promotion;
- readiness promotion, registry activation, product-route activation, market_data activation;
- broker/order/paper/live/auto, daily signal push;
- raw-data migration into quant-proj;
- active schema migration;
- .env/key/token/auth/credential/secret access/output;
- unbounded provider sync.

Required validation:
- command transcript for network/write tasks;
- manifest/count/hash evidence for generated data;
- JSON parse PASS;
- duplicate-key and missingness checks where data is generated;
- py_compile PASS for changed Python;
- focused pytest PASS if code/tests changed;
- agent_safety_check.py PASS where applicable;
- git diff --check PASS;
- forbidden overclaim scan PASS.

Callback:
Send prompt-only callback to Quant-Dispatcher thread 019f3830-4b44-7a83-944d-247a0d4dc169 using the callback envelope in the task packet.
```
