# Handoff: US_Stock_Monitor Authorized Metadata Repair

Send to WSL2 downstream thread `019f387b-a161-7ad0-8678-f03a099612ba`.

Prompt-only. Do not pass model or thinking overrides.

```text
You are Codex-Dev for /home/rongyu/workspace/US_Stock_Monitor.

Task batch: WINDOWS_WSL2_AUTHORIZED_CONTROLLED_ADVANCEMENT_20260707
Workstream: HG-EXEC-TASK-US-METADATA-REPAIR-20260707

Controller: /home/rongyu/workspace/quant-proj
Task packet: /home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-authorized-controlled-advancement-20260707/spec.md
Decision log: /home/rongyu/workspace/quant-proj/reports/human_gate/decisions.jsonl

Assigned task:
- Repair the US 44-symbol metadata blocker and, if needed, run bounded US 300-symbol metadata/daily ingest under recorded execution.
- Use source candidates consistent with the controller data-source policy, prioritizing user-approved public/no-secret sources and simonlin1212/global-stock-data when provider expansion is needed.
- Use --allow-network and --allow-write only for the exact bounded scope recorded in HG-EXEC-TASK-US-METADATA-REPAIR-20260707.

Forbidden:
- recommendation/advice;
- ticket, eligibility candidate, product route activation, production readiness;
- broker/order/paper/live/auto;
- .env/key/token/auth/secret access or output;
- raw-data migration into quant-proj.

Validation:
- command transcript and manifest/count/hash evidence;
- duplicate-key and missing-metadata validation;
- JSON parse PASS;
- focused tests PASS;
- git diff --check PASS;
- forbidden overclaim/enabling scan PASS.

Completion callback:
Send prompt-only callback to Quant-Dispatcher thread 019f3830-4b44-7a83-944d-247a0d4dc169 with the unified callback envelope in the task packet.
```
