# User Command - WINDOWS_WSL2_5090_GPU_ML_SIGNAL_RESEARCH_PHASE3_20260707

Imported: 2026-07-07 Asia/Shanghai
Role: Quant-Dispatcher

## Command Summary

The user provided a new research-only GPU ML signal research batch:

`WINDOWS_WSL2_5090_GPU_ML_SIGNAL_RESEARCH_PHASE3_20260707`

Context:

- Continue using RTX 5090 for ML signal research only.
- Do not deploy a local LLM.
- Do not use GPU output as recommendation or readiness evidence.

Goal:

- Build strict temporal-split ML baselines.
- Translate signals into research-only strategy hypotheses.
- Do not create strategy candidate, recommendation, ticket, readiness, product route, or trading path.

Tasks:

- `GPU-P3-1` Frozen ML dataset and label contract.
- `GPU-P3-2` GPU ML baseline models.
- `GPU-P3-3` ML signal decile diagnostics.
- `GPU-P3-4` Meta-labeling prototype.
- `GPU-P3-5` Signal-to-strategy bridge.
- `GPU-P3-6` Portfolio construction research.
- `GPU-P3-7` ML overfit and leakage audit.

Model constraints:

- Start with simple baselines: logistic, MLP, XGBoost GPU.
- Do not start with transformer, RL, or complex ensemble.
- Do not select model based on test performance.
- Do not rewrite weak ML results as strategy candidates.

Hard boundaries:

- no local LLM deployment;
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
- no `.env`, key, token, auth, or secret access.
