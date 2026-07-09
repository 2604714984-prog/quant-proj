# WINDOWS_WSL2_5090_GPU_ML_SIGNAL_RESEARCH_PHASE3_20260707 Spec

## Objective

Use RTX 5090 GPU compute only for research-only ML signal diagnostics over existing local research data. Build strict temporal-split ML baselines and translate signals into research-only strategy hypotheses.

This batch must not deploy a local LLM or use GPU/ML output as recommendation, candidate, ticket, readiness, product-route, or trading-path evidence.

## Current Status

`BLOCKED_PRE_DISPATCH_CUDA_ML_ENV_UNAVAILABLE`

Phase 2 did not produce GPU numeric diagnostics. It closed as `BLOCKED_CUDA_PYTHON_UNAVAILABLE`. A fresh non-mutating Phase 3 environment check still shows no installed Python CUDA/ML stack in A_Share_Monitor `.venv` for the requested baselines.

## Classification

Ordinary research-only ML signal research batch.

External-audit trigger opened: `no`.

No task-level HG-EXEC is granted by this packet.

## Intended Owner

`A_Share_Monitor` fixed WSL2 downstream Codex-Dev thread, after the CUDA ML environment blocker is resolved.

## Tasks

| ID | Owner | Task | Dependency |
|---|---|---|---|
| `GPU-P3-1` | `A_Share_Monitor` | Frozen ML dataset and label contract. | existing local research data only |
| `GPU-P3-2` | `A_Share_Monitor` | GPU ML baseline models. | working Python CUDA/ML stack |
| `GPU-P3-3` | `A_Share_Monitor` | ML signal decile diagnostics. | `GPU-P3-1`, `GPU-P3-2` |
| `GPU-P3-4` | `A_Share_Monitor` | Meta-labeling prototype. | strict time split and leakage check |
| `GPU-P3-5` | `A_Share_Monitor` | Signal-to-strategy bridge. | research-only labels only |
| `GPU-P3-6` | `A_Share_Monitor` | Portfolio construction research. | no recommendation/readiness/trading output |
| `GPU-P3-7` | `A_Share_Monitor` | ML overfit and leakage audit. | all prior ML artifacts |

## Model Constraints

- Start with simple baselines only: logistic, MLP, XGBoost GPU.
- Do not start with transformer, reinforcement learning, or complex ensemble.
- Do not select the model based on test performance.
- Do not rewrite weak ML results as strategy candidates.
- If a requested baseline is unavailable because required libraries are absent, return `BLOCKED_CUDA_ML_ENV_UNAVAILABLE`; do not install packages or weaken the model constraints.

## Required Outputs If Resumed

Use these artifact names unless an implementation blocker requires a narrower fallback:

- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase3_ml_dataset_label_contract_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase3_ml_dataset_label_contract_20260707.json`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase3_gpu_ml_baselines_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase3_gpu_ml_baselines_20260707.csv`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase3_signal_decile_diagnostics_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase3_signal_decile_diagnostics_20260707.csv`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase3_meta_labeling_prototype_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase3_meta_labeling_prototype_20260707.csv`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase3_signal_to_strategy_bridge_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase3_signal_to_strategy_bridge_20260707.json`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase3_portfolio_construction_research_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase3_portfolio_construction_research_20260707.csv`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase3_ml_overfit_leakage_audit_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase3_ml_overfit_leakage_audit_20260707.json`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase3_summary_20260707.json`

Do not commit large binary tensor/model artifacts unless they are tiny deterministic fixtures. If local scratch tensors or models are needed, keep them out of git and record path, shape, dtype, hash, and cleanup status in a manifest.

## Validation If Resumed

- Strict train/validation/test split.
- Label leakage check.
- CPU/GPU parity where applicable.
- Permutation baseline.
- JSON parse PASS for JSON artifacts.
- `git diff --check` PASS.
- `agent_safety_check.py` PASS where applicable.
- forbidden local LLM scan PASS.
- forbidden recommendation/candidate/readiness/product/trading overclaim scan PASS.

## Stop Conditions

- `LOCAL_LLM_DEPLOYMENT_REQUIRED`
- `CUDA_NOT_VISIBLE_IN_WSL`
- `CUDA_ML_STACK_UNAVAILABLE`
- `PYTHON_CUDA_ML_SMOKE_FAIL`
- `CPU_GPU_PARITY_FAIL`
- `LABEL_LEAKAGE_DETECTED`
- `MODEL_SELECTED_BY_TEST_PERFORMANCE`
- `NETWORK_PROVIDER_FETCH_REQUIRED_WITHOUT_HG_EXEC`
- `DB_WRITE_OR_CACHE_REBUILD_REQUIRED_WITHOUT_HG_EXEC`
- `SCHEMA_READINESS_REGISTRY_CHANGE_REQUIRED`
- `SECRET_OR_ENV_ACCESS_REQUIRED`
- `TRANSFORMER_RL_COMPLEX_ENSEMBLE_STARTED`
- `ML_RESULT_PROMOTED_TO_STRATEGY_CANDIDATE`
- `ML_DIAGNOSTIC_WRITTEN_AS_RECOMMENDATION_OR_READINESS`

If a stop condition is encountered, stop and return `BLOCKED` with `GPU_STATUS`.

## Required Callback Envelope If Resumed

```text
CALLBACK_ENVELOPE:
BATCH: WINDOWS_WSL2_5090_GPU_ML_SIGNAL_RESEARCH_PHASE3_20260707
TARGET_REPO:
BRANCH:
COMMIT:
STATUS:
TASKS_COMPLETED:
ARTIFACTS:
VALIDATION:
GPU_STATUS:
KEY_RESULTS:
WARNINGS:
BOUNDARY_RESULT:
NEXT_SOURCE_ACTION:
```

## Boundary

Research-only. No local LLM deployment, no recommendation/advice, no `PENDING_HUMAN_REVIEW`, no ticket, no eligibility candidate, no data-clear promotion, no product-route activation, no production readiness, no broker/order/paper/live/auto, no provider/network fetch, no DB/cache rebuild/write, no schema/readiness/registry changes, no raw-data migration, no `.env` access, no key/token/auth/secret access or output, no transformer/RL/complex ensemble start, no model selection based on test performance, and no rewriting weak ML results as strategy candidates.
