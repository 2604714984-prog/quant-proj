# Handoff: market_data Product-Route/Readiness Preparation

Send to WSL2 downstream thread `019f387b-e763-7c01-ae3d-6be552cdb6dc`.

Prompt-only. Do not pass model or thinking overrides.

```text
You are Codex-Dev for /home/rongyu/workspace/market_data.

Task batch: WINDOWS_WSL2_AUTHORIZED_CONTROLLED_ADVANCEMENT_20260707
Workstream: HG-EXEC-TASK-MD-PRODUCT-ROUTE-PREP-20260707

Controller: /home/rongyu/workspace/quant-proj
Task packet: /home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-authorized-controlled-advancement-20260707/spec.md
Decision log: /home/rongyu/workspace/quant-proj/reports/human_gate/decisions.jsonl

Assigned task:
- Prepare market_data product-read route/readiness replacement work using current accepted source evidence only.
- Produce old/new diff, rollback plan, validation matrix, access-gate regression, and external-audit packet material.
- Do not set production_recommendation_data_ready=true.
- Do not enable broker/order/paper/live/auto flags.
- Do not treat product-read preparation as recommendation readiness.
- Active product route replacement remains external-audit gated: return EXTERNAL_AUDIT_TRIGGER_OPEN=yes if a real activation diff is ready.

Forbidden:
- recommendation/advice;
- ticket, eligibility candidate, production readiness;
- broker/order/paper/live/auto;
- .env/key/token/auth/secret access or output;
- raw data import/migration into quant-proj.

Validation:
- old/new route diff;
- rollback path;
- focused tests PASS;
- access-gate regression PASS;
- JSON/YAML parse PASS;
- git diff --check PASS;
- forbidden readiness/broker/live/auto true scan PASS.

Completion callback:
Send prompt-only callback to Quant-Dispatcher thread 019f3830-4b44-7a83-944d-247a0d4dc169 with the unified callback envelope in the task packet.
```
