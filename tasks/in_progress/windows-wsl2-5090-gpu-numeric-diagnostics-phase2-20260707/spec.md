# WINDOWS_WSL2_5090_GPU_NUMERIC_DIAGNOSTICS_PHASE2_20260707 Spec

## Objective

Use RTX 5090 GPU compute only for numerical research acceleration over existing local research data. Analyze factor quality, statistical significance, cost/capacity, regime behavior, and data/feature anomalies.

This batch must not deploy a local LLM, Qwen, or any local chat model. It must not create a strategy candidate, recommendation, ticket, eligibility candidate, readiness state, product route, or trading path.

## Classification

Ordinary research-only numeric diagnostics batch.

External-audit trigger opened: `no`.

## Owner

`A_Share_Monitor` fixed WSL2 downstream Codex-Dev thread.

## Tasks

| ID | Owner | Task | Dependency |
|---|---|---|---|
| `GPU-P2-1` | `A_Share_Monitor` | CUDA readiness and numeric environment. | none |
| `GPU-P2-2` | `A_Share_Monitor` | Tensorized factor dataset builder. | existing local research data only |
| `GPU-P2-3` | `A_Share_Monitor` | CPU-GPU parity baseline. | `GPU-P2-1`, `GPU-P2-2` |
| `GPU-P2-4` | `A_Share_Monitor` | Factor predictive diagnostics. | `GPU-P2-3` |
| `GPU-P2-5` | `A_Share_Monitor` | Bootstrap and permutation significance. | `GPU-P2-3`, strict time split |
| `GPU-P2-6` | `A_Share_Monitor` | Factor neutralization diagnostics. | `GPU-P2-3` |
| `GPU-P2-7` | `A_Share_Monitor` | Cost and capacity surface. | `GPU-P2-3` |
| `GPU-P2-8` | `A_Share_Monitor` | Regime factor attribution. | `GPU-P2-3`, strict time split |
| `GPU-P2-9` | `A_Share_Monitor` | Data and feature anomaly scan. | `GPU-P2-2` |

## Required Outputs

Use these artifact names unless an implementation blocker requires a narrower fallback:

- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase2_cuda_readiness_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase2_cuda_readiness_20260707.json`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase2_tensor_dataset_manifest_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase2_tensor_dataset_manifest_20260707.json`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase2_cpu_gpu_parity_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase2_cpu_gpu_parity_20260707.json`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase2_factor_predictive_diagnostics_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase2_factor_predictive_diagnostics_20260707.csv`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase2_bootstrap_permutation_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase2_bootstrap_permutation_20260707.csv`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase2_factor_neutralization_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase2_factor_neutralization_20260707.csv`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase2_cost_capacity_surface_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase2_cost_capacity_surface_20260707.csv`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase2_regime_factor_attribution_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase2_regime_factor_attribution_20260707.csv`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase2_data_feature_anomaly_scan_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase2_data_feature_anomaly_scan_20260707.csv`
- `reports/workspace_dispatch/windows_wsl2_5090_gpu_phase2_summary_20260707.json`
- tests/scripts used for deterministic diagnostics, if created.

Do not commit large binary tensor datasets unless they are tiny deterministic fixtures. If local scratch tensors are needed, keep them out of git and record path, shape, dtype, hash, and cleanup status in the manifest.

## Numeric Requirements

- `nvidia-smi` must be visible in WSL.
- Python CUDA smoke must pass using already available numeric libraries.
- If CUDA Python libraries are unavailable, report `BLOCKED_CUDA_PYTHON_UNAVAILABLE`; do not install or download a local LLM/model/toolchain.
- CPU-GPU parity must pass before relying on GPU numeric outputs.
- Where labels or forward returns are used, use strict time splits and avoid post-hoc test-result parameter selection.
- Record tolerances, seeds, dtypes, device, driver/runtime versions, and deterministic limitations.

## Validation

- `nvidia-smi` visible in WSL.
- Python CUDA smoke PASS.
- CPU/GPU parity PASS for numeric outputs.
- Strict time split where labels are used.
- JSON parse PASS for JSON artifacts.
- `git diff --check` PASS.
- `agent_safety_check.py` PASS where applicable.
- forbidden local LLM/Qwen scan PASS on changed artifacts and scripts.
- forbidden overclaim scan PASS.

## Stop Conditions

- `LOCAL_LLM_DEPLOYMENT_REQUIRED`
- `QWEN_DEPLOYMENT_REQUIRED`
- `CUDA_NOT_VISIBLE_IN_WSL`
- `PYTHON_CUDA_SMOKE_FAIL`
- `CPU_GPU_PARITY_FAIL`
- `NETWORK_PROVIDER_FETCH_REQUIRED_WITHOUT_HG_EXEC`
- `DB_WRITE_OR_CACHE_REBUILD_REQUIRED_WITHOUT_HG_EXEC`
- `SCHEMA_READINESS_REGISTRY_CHANGE_REQUIRED`
- `SECRET_OR_ENV_ACCESS_REQUIRED`
- `POST_HOC_STRATEGY_SELECTION_FROM_TEST_RESULTS`
- `STRATEGY_RESULT_PROMOTED_TO_CANDIDATE`
- `NUMERIC_DIAGNOSTIC_WRITTEN_AS_RECOMMENDATION`

If a stop condition is encountered, stop and return `BLOCKED` with `GPU_STATUS`.

## Required Callback Envelope

```text
CALLBACK_ENVELOPE:
BATCH: WINDOWS_WSL2_5090_GPU_NUMERIC_DIAGNOSTICS_PHASE2_20260707
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

Research-only. No local LLM deployment, no Qwen deployment, no recommendation/advice, no `PENDING_HUMAN_REVIEW`, no ticket, no eligibility candidate, no data-clear promotion, no product-route activation, no production readiness, no broker/order/paper/live/auto, no provider/network fetch, no DB/cache rebuild/write, no schema/readiness/registry changes, no raw-data migration, no `.env` access, no key/token/auth/secret access or output, and no post-hoc strategy selection based on test results.
