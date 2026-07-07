# Windows WSL2 RTX 5090 GPU Power Cap Policy - 20260707

Project: quant-proj
Role: Quant-Dispatcher
Recorded: 2026-07-07T14:51:45+08:00
Source: user directive that subsequent RTX 5090 runs must be locked to 400W; higher power requires separate authorization.

Status update: superseded on 2026-07-07T16:32:56+08:00 by `reports/human_gate/windows_wsl2_5090_gpu_power_cap_revocation_20260707.md` after the user explicitly revoked the 400W limit and directed R17 to continue.

## Historical Standing Constraint

At record time, subsequent RTX 5090 numerical research, ML research, CUDA smoke, and GPU diagnostic work had to use a 400W power cap unless the user granted a separate higher-power authorization for that specific task. This is no longer the active policy after the supersession record below.

## Historical Dispatch Requirement

At record time, future GPU handoffs had to include:

- `GPU_POWER_LIMIT_WATTS: 400`;
- no intentional run above 400W;
- callback field for `GPU_POWER_CAP_STATUS`;
- stop condition `GPU_POWER_LIMIT_ABOVE_400W_WITHOUT_AUTH`;
- stop condition `GPU_POWER_CAP_REQUIRED_BUT_NOT_VERIFIABLE` for workloads expected to require sustained high power.

## Historical Higher-Power Path

At record time, any task needing more than 400W had to return `BLOCKED_NEEDS_HIGHER_GPU_POWER_AUTHORIZATION` and request a separate task-level authorization before continuing. This path is superseded by the later revocation record.

## Boundary

This policy does not authorize local LLM/Qwen deployment, recommendation/advice, ticket creation, eligibility candidate creation, product-route activation, production readiness, broker/order/paper/live/auto, provider/network fetch, DB/cache write, schema/readiness/registry change, raw-data migration, or secret access/output.

## Supersession

The 400W cap, its higher-power stop condition, and its verification requirement are no longer active after the revocation record. Future GPU work must follow the latest controller power-policy record.
