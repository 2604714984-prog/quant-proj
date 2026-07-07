# WINDOWS_WSL2_AUTHORIZED_CONTROLLED_ADVANCEMENT_20260707 Dispatch Summary

Project: quant-proj
Role: Quant-Dispatcher
Prepared: 2026-07-07T13:46:58+08:00
Sent: 2026-07-07T13:46:58+08:00
Classification: broad Human-Gate authorization and controlled execution batch
External-audit trigger open now: `no`
Updated after callbacks: `yes` for market_data product-route preparation before any activation

## Controller Records

- Human-Gate authorization: `reports/human_gate/windows_wsl2_broad_authorization_20260707.md`
- RTX 5090 power cap policy: `reports/human_gate/windows_wsl2_5090_gpu_power_cap_policy_20260707.md`
- Decision log: `reports/human_gate/decisions.jsonl`
- Task packet: `tasks/in_progress/windows-wsl2-authorized-controlled-advancement-20260707/spec.md`

## Dispatch Matrix

| Target | WSL2 thread | Workstream | HG record | Status |
|---|---|---|---|---|
| `A_Share_Monitor` | `019f387b-617e-7273-b539-161216ae3002` | GPU env + Phase 2/3 resume; East Money coverage expansion | `HG-EXEC-TASK-GPU-ENV-PHASE2-PHASE3-20260707`; `HG-EXEC-TASK-A-EAST-MONEY-COVERAGE-20260707` | callback received; push PASS |
| `US_Stock_Monitor` | `019f387b-a161-7ad0-8678-f03a099612ba` | 44-symbol metadata repair / bounded US 300-symbol ingest | `HG-EXEC-TASK-US-METADATA-REPAIR-20260707` | callback received; push PASS |
| `market_data` | `019f387b-e763-7c01-ae3d-6be552cdb6dc` | product-read route/readiness preparation and audit packet material | `HG-EXEC-TASK-MD-PRODUCT-ROUTE-PREP-20260707` | callback received; Codex-Audit PASS; push PASS |

## Callback Records

- market_data: `reports/workspace_dispatch/windows_wsl2_authorized_controlled_advancement_20260707_market_data_callback.md`
- A_Share_Monitor: `reports/workspace_dispatch/windows_wsl2_authorized_controlled_advancement_20260707_a_share_callback.md`
- A_Share_Monitor push: `reports/workspace_dispatch/windows_wsl2_authorized_controlled_advancement_20260707_a_share_push_callback.md`
- Codex-Audit: `reports/workspace_dispatch/windows_wsl2_authorized_controlled_advancement_20260707_market_data_codex_audit_callback.md`
- market_data push: `reports/workspace_dispatch/windows_wsl2_authorized_controlled_advancement_20260707_market_data_push_callback.md`
- US_Stock_Monitor: `reports/workspace_dispatch/windows_wsl2_authorized_controlled_advancement_20260707_us_callback.md`
- US_Stock_Monitor push: `reports/workspace_dispatch/windows_wsl2_authorized_controlled_advancement_20260707_us_push_callback.md`
- Result summary: `reports/workspace_dispatch/windows_wsl2_authorized_controlled_advancement_20260707_result_summary.md`

## Audit Routing

- Codex-Audit thread: `019f3b34-44a9-7d71-87cc-6137c4d72e9b`
- Codex-Audit handoff: `reports/agent_handoff/windows_wsl2_authorized_controlled_advancement_market_data_codex_audit_handoff_20260707.md`
- User-operated external audit packet: `reports/agent_handoff/windows_wsl2_authorized_controlled_advancement_market_data_external_audit_packet_20260707.md`

## Required Callback

Each downstream must send prompt-only callback to dispatcher thread `019f3830-4b44-7a83-944d-247a0d4dc169`.

## Boundary

No local LLM/Qwen, no recommendation/advice, no production recommendation readiness, no broker/order/paper/live/auto, no secret access/output, and no raw-data migration into quant-proj. Subsequent RTX 5090 runs are capped at 400W unless separately authorized.
