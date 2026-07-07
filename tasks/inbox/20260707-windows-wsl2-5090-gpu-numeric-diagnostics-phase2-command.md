# User Command - WINDOWS_WSL2_5090_GPU_NUMERIC_DIAGNOSTICS_PHASE2_20260707

Imported: 2026-07-07 Asia/Shanghai
Role: Quant-Dispatcher

## Command Summary

The user provided a new research-only GPU numeric diagnostics batch:

`WINDOWS_WSL2_5090_GPU_NUMERIC_DIAGNOSTICS_PHASE2_20260707`

Goal:

- Use RTX 5090 only for numerical research acceleration.
- Analyze factor quality, statistical significance, cost/capacity, regime behavior, and data anomalies for quant-proj.
- Do not deploy a local LLM, Qwen, or any local chat model.
- DS API / external LLM tools may handle language/report assistance outside local LLM deployment.
- Do not create a strategy candidate, recommendation, ticket, readiness, product route, or trading path.

Tasks:

- `GPU-P2-1` CUDA readiness and numeric environment.
- `GPU-P2-2` Tensorized factor dataset builder.
- `GPU-P2-3` CPU-GPU parity baseline.
- `GPU-P2-4` Factor predictive diagnostics.
- `GPU-P2-5` Bootstrap and permutation significance.
- `GPU-P2-6` Factor neutralization diagnostics.
- `GPU-P2-7` Cost and capacity surface.
- `GPU-P2-8` Regime factor attribution.
- `GPU-P2-9` Data and feature anomaly scan.

Hard boundaries:

- no local LLM deployment;
- no Qwen deployment;
- no recommendation/advice;
- no `PENDING_HUMAN_REVIEW`;
- no ticket;
- no eligibility candidate;
- no data-clear promotion;
- no product-route activation;
- no production readiness;
- no broker/order/paper/live/auto;
- no provider/network fetch unless separate HG-EXEC exists;
- no DB/cache rebuild unless separate HG-EXEC exists;
- no schema/readiness/registry changes;
- no `.env`, key, token, auth, or secret access;
- no post-hoc strategy selection based on test results.
