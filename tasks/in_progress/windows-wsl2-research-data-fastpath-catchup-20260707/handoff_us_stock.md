# Handoff: US_Stock_Monitor Fastpath Catchup

Send to WSL2 downstream thread `019f387b-a161-7ad0-8678-f03a099612ba`.

Prompt-only. Do not pass model or thinking overrides.

```text
You are Codex-Dev for /home/rongyu/workspace/US_Stock_Monitor.

Task batch: WINDOWS_WSL2_RESEARCH_DATA_FASTPATH_CATCHUP_20260707
Controller: /home/rongyu/workspace/quant-proj

Read first:
- /home/rongyu/workspace/quant-proj/reports/human_gate/windows_wsl2_research_data_fast_path_policy_20260707.md
- /home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-research-data-fastpath-catchup-20260707/spec.md
- /home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-research-data-fastpath-catchup-20260707/human_gate.md
- /home/rongyu/workspace/quant-proj/reports/workspace_dispatch/windows_wsl2_authorized_controlled_advancement_20260707_us_callback.md

Policy:
Research-data fast path is active. Per-task HG-EXEC is no longer required for bounded, public/no-secret, source-local, research-only network fetch and research cache/staging/report/test writes. Transcript, manifest/count/hash evidence, validation, and callback are still required.

Tasks:
1. FP-US-1: Current-universe metadata parser cleanup.
   - Continue from commit 9264773852daf46b4abf09f347f571c5f118d634.
   - Diagnose/fix sourceable symbols excluded only due N/A daily row parsing.
   - Rerun bounded current-universe research staging if safe.
   - max symbols: 320
   - date range: 20180101..20260707
2. FP-US-2: Tencent-only and legacy 44 source-conflict diagnostics.
   - Output research handling labels only.
   - Do not synthesize active metadata.
3. FP-US-3: US 300 research staging status.
   - Decide whether the old US 300 ingest hold is superseded by current-universe staging or still requires separate hard-gated work.
   - If bounded public/no-secret source-local staging can be completed safely, do it under fast path.
   - If product route, active registry, readiness, candidate/ticket, or raw migration is needed, stop with STILL_HARD_GATED.

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
