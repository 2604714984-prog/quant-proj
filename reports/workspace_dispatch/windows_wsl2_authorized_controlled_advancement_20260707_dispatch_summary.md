# WINDOWS_WSL2_AUTHORIZED_CONTROLLED_ADVANCEMENT_20260707 Dispatch Summary

Project: quant-proj
Role: Quant-Dispatcher
Prepared: 2026-07-07T13:46:58+08:00
Sent: 2026-07-07T13:46:58+08:00
Classification: broad Human-Gate authorization and controlled execution batch
External-audit trigger open now: `no`

## Controller Records

- Human-Gate authorization: `reports/human_gate/windows_wsl2_broad_authorization_20260707.md`
- Decision log: `reports/human_gate/decisions.jsonl`
- Task packet: `tasks/in_progress/windows-wsl2-authorized-controlled-advancement-20260707/spec.md`

## Dispatch Matrix

| Target | WSL2 thread | Workstream | HG record | Status |
|---|---|---|---|---|
| `A_Share_Monitor` | `019f387b-617e-7273-b539-161216ae3002` | GPU env + Phase 2/3 resume; East Money coverage expansion | `HG-EXEC-TASK-GPU-ENV-PHASE2-PHASE3-20260707`; `HG-EXEC-TASK-A-EAST-MONEY-COVERAGE-20260707` | sent |
| `US_Stock_Monitor` | `019f387b-a161-7ad0-8678-f03a099612ba` | 44-symbol metadata repair / bounded US 300-symbol ingest | `HG-EXEC-TASK-US-METADATA-REPAIR-20260707` | sent |
| `market_data` | `019f387b-e763-7c01-ae3d-6be552cdb6dc` | product-read route/readiness preparation and audit packet material | `HG-EXEC-TASK-MD-PRODUCT-ROUTE-PREP-20260707` | sent |

## Required Callback

Each downstream must send prompt-only callback to dispatcher thread `019f3830-4b44-7a83-944d-247a0d4dc169`.

## Boundary

No local LLM/Qwen, no recommendation/advice, no production recommendation readiness, no broker/order/paper/live/auto, no secret access/output, and no raw-data migration into quant-proj.
