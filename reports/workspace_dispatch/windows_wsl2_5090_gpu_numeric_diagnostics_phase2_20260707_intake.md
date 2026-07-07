# WINDOWS_WSL2_5090_GPU_NUMERIC_DIAGNOSTICS_PHASE2_20260707 Intake

Project: quant-proj
Role: Quant-Dispatcher
Imported: 2026-07-07 Asia/Shanghai
Source: user-pasted task list
Original intake copy: `tasks/inbox/20260707-windows-wsl2-5090-gpu-numeric-diagnostics-phase2-command.md`
Status: BLOCKED_CUDA_PYTHON_UNAVAILABLE

## Classification

Ordinary research-only numeric diagnostics batch.

External-audit trigger opened: `no`

Reason:

- The batch uses GPU only for numerical research acceleration.
- It explicitly forbids local LLM/Qwen deployment and all trading/product/readiness routes.
- It does not authorize recommendations, `PENDING_HUMAN_REVIEW`, tickets, eligibility candidates, readiness, product routes, broker/order/paper/live/auto, raw-data migration, secrets, network/provider fetch, DB/cache rebuild, schema changes, readiness changes, or registry activation.
- CUDA readiness is an environment validation task only.
- Factor diagnostics, bootstrap/permutation, neutralization, cost/capacity, regime attribution, and anomaly scans are research-only diagnostics.

## Dispatch Target

Primary downstream: `A_Share_Monitor`

Reason:

- The current factor and strategy research artifacts, `features_daily` evidence, and chunked StrategySearch guardrails are in A_Share_Monitor.
- The batch is numeric factor diagnostics, not controller code, market_data registry activation, or strategy_work memo-only work.

Not dispatched:

- `market_data`: no registry/schema/readiness/contract change is authorized.
- `strategy_work`: no memo/final-sync task is requested in this batch.
- `US_Stock_Monitor`: no US-specific task is requested.

## Tasks

- `GPU-P2-1`: CUDA readiness and numeric environment.
- `GPU-P2-2`: Tensorized factor dataset builder.
- `GPU-P2-3`: CPU-GPU parity baseline.
- `GPU-P2-4`: Factor predictive diagnostics.
- `GPU-P2-5`: Bootstrap and permutation significance.
- `GPU-P2-6`: Factor neutralization diagnostics.
- `GPU-P2-7`: Cost and capacity surface.
- `GPU-P2-8`: Regime factor attribution.
- `GPU-P2-9`: Data and feature anomaly scan.

## Boundary

Research-only. No local LLM deployment, no Qwen deployment, no recommendation/advice, no `PENDING_HUMAN_REVIEW`, no ticket, no eligibility candidate, no data-clear promotion, no product-route activation, no production readiness, no broker/order/paper/live/auto, no provider/network fetch, no DB/cache rebuild/write, no schema/readiness/registry changes, no raw-data migration, no `.env` access, no key/token/auth/secret access or output, and no post-hoc strategy selection based on test results.
