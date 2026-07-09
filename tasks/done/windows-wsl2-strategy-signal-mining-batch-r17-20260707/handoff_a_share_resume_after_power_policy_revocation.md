# Resume Handoff: A_Share_Monitor R17 After GPU Power Policy Revocation

Target repo: `/home/rongyu/workspace/A_Share_Monitor`
Controller repo: `/home/rongyu/workspace/quant-proj`
Callback target: Quant-Dispatcher thread `019f3830-4b44-7a83-944d-247a0d4dc169`
Batch: `WINDOWS_WSL2_STRATEGY_SIGNAL_MINING_BATCH_R17_20260707`

## Resume Authorization

The user revoked the prior RTX 5090 400W cap and directed R17 to continue.

Controller record:

- `reports/human_gate/windows_wsl2_5090_gpu_power_cap_revocation_20260707.md`
- decision id: `HG-STANDING-GPU-POWER-CAP-REVOKED-R17-20260707`

R17 may proceed under host/driver default GPU power policy. The last observed state was `power.limit=600.00W`, `default=600.00W`, and `max=600.00W`.

## Resume Scope

Resume `A-WIN-R17-1` through `A-WIN-R17-8` from the prior blocked state. Do not rerun already completed pre-flight work unless needed.

The prior stop conditions `GPU_POWER_LIMIT_ABOVE_400W_WITHOUT_AUTH` and `GPU_POWER_CAP_REQUIRED_BUT_NOT_VERIFIABLE` are superseded for this batch.

## Required GPU Reporting

Instead of enforcing 400W, record:

- observed `power.limit`;
- observed `power.draw` where available;
- whether sustained GPU work was executed;
- whether any privileged power-limit change was attempted.

Do not attempt privileged power-limit changes unless separately requested.

## Unchanged Boundary

Research-only. No recommendation/advice, ticket, eligibility candidate, strategy candidate promotion, product route, readiness, broker/order/paper/live/auto, secrets, raw-data migration, unapproved network/provider fetch, unapproved DB/cache write, or full-frame wide3068.

## Callback Envelope

```text
CALLBACK_ENVELOPE:
BATCH: WINDOWS_WSL2_STRATEGY_SIGNAL_MINING_BATCH_R17_20260707
TARGET_REPO: /home/rongyu/workspace/A_Share_Monitor
BRANCH:
COMMIT:
TREE:
STATUS:
TASKS_COMPLETED:
ARTIFACTS:
VALIDATION:
KEY_RESULTS:
STRATEGY_CANDIDATE_AVAILABLE:
GPU_POWER_POLICY_STATUS:
BOUNDARY_RESULT:
EXTERNAL_AUDIT_TRIGGER_OPEN:
FIXES_REQUIRED:
NEXT_SOURCE_ACTION:
```
