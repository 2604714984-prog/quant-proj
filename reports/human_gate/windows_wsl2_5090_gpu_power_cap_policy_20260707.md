# Windows WSL2 RTX 5090 GPU Power Cap Policy - 20260707

Project: quant-proj
Role: Quant-Dispatcher
Recorded: 2026-07-07T14:51:45+08:00
Source: user directive that subsequent RTX 5090 runs must be locked to 400W; higher power requires separate authorization.

## Standing Constraint

All subsequent RTX 5090 numerical research, ML research, CUDA smoke, and GPU diagnostic work must use a 400W power cap unless the user grants a separate higher-power authorization for that specific task.

## Dispatch Requirement

Future GPU handoffs must include:

- `GPU_POWER_LIMIT_WATTS: 400`;
- no intentional run above 400W;
- callback field for `GPU_POWER_CAP_STATUS`;
- stop condition `GPU_POWER_LIMIT_ABOVE_400W_WITHOUT_AUTH`;
- stop condition `GPU_POWER_CAP_REQUIRED_BUT_NOT_VERIFIABLE` for workloads expected to require sustained high power.

## Higher-Power Path

Any task that needs more than 400W must return `BLOCKED_NEEDS_HIGHER_GPU_POWER_AUTHORIZATION` and request a separate task-level authorization before continuing.

## Boundary

This policy does not authorize local LLM/Qwen deployment, recommendation/advice, ticket creation, eligibility candidate creation, product-route activation, production readiness, broker/order/paper/live/auto, provider/network fetch, DB/cache write, schema/readiness/registry change, raw-data migration, or secret access/output.
