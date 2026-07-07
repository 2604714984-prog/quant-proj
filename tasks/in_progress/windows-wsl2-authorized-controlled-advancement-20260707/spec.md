# WINDOWS_WSL2_AUTHORIZED_CONTROLLED_ADVANCEMENT_20260707 Spec

## Objective

Use the user's 2026-07-07 broad authorization to unblock controlled research infrastructure and data-readiness work while preserving the system's no-advice, no-broker, no-secret, and audit-gated boundaries.

## Authorized Workstreams

| Workstream | Owner | Authorization record | Execution status |
|---|---|---|---|
| GPU CUDA Python / CUDA ML environment enablement and GPU Phase 2/3 resume | `A_Share_Monitor` | `HG-EXEC-TASK-GPU-ENV-PHASE2-PHASE3-20260707` | dispatched |
| A-share East Money coverage expansion and data repair | `A_Share_Monitor` | `HG-EXEC-TASK-A-EAST-MONEY-COVERAGE-20260707` | dispatched |
| US 44-symbol metadata repair / bounded US 300-symbol ingest | `US_Stock_Monitor` | `HG-EXEC-TASK-US-METADATA-REPAIR-20260707` | dispatched |
| market_data product-read route/readiness preparation and external-audit packet | `market_data` | `HG-EXEC-TASK-MD-PRODUCT-ROUTE-PREP-20260707` | dispatched |

## Shared Boundary

No local LLM deployment, no Qwen deployment, no recommendation/advice, no `PENDING_HUMAN_REVIEW` ticket unless a future explicit L4 task is created and all gates pass, no eligibility candidate, no production recommendation readiness, no broker/order/paper/live/auto, no secret access/output, and no raw-data migration into `quant-proj`.

## Callback Requirement

Each downstream thread must return a prompt-only callback to Quant-Dispatcher thread `019f3830-4b44-7a83-944d-247a0d4dc169`.

```text
CALLBACK_ENVELOPE:
BATCH: WINDOWS_WSL2_AUTHORIZED_CONTROLLED_ADVANCEMENT_20260707
TARGET_REPO:
WORKSTREAM:
HG_RECORD:
BRANCH:
COMMIT:
TREE:
STATUS:
TASKS_COMPLETED:
ARTIFACTS:
VALIDATION:
GPU_STATUS:
DATA_STATUS:
READINESS_STATUS:
KEY_RESULTS:
WARNINGS:
BLOCKERS:
BOUNDARY_RESULT:
EXTERNAL_AUDIT_TRIGGER_OPEN:
FIXES_REQUIRED:
NEXT_SOURCE_ACTION:
```
