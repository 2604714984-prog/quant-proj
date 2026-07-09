# Prepared Handoff: A_Share_Monitor GPU Phase 3

Status: prepared but not sent.

Reason: Phase 2 closed as `BLOCKED_CUDA_PYTHON_UNAVAILABLE`, and a fresh non-mutating Phase 3 environment check shows no installed Python CUDA/ML libraries in A_Share_Monitor `.venv`.

Send only after the controller receives an approved already-installed CUDA ML environment path or separate environment/toolchain authorization.

```text
You are Codex-Dev for /home/rongyu/workspace/A_Share_Monitor.

Task batch: WINDOWS_WSL2_5090_GPU_ML_SIGNAL_RESEARCH_PHASE3_20260707

Controller: /home/rongyu/workspace/quant-proj
Task packet: /home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-5090-gpu-ml-signal-research-phase3-20260707/spec.md
Human-Gate classification: /home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-5090-gpu-ml-signal-research-phase3-20260707/human_gate.md

Context:
- Do not deploy a local LLM.
- Use RTX 5090 only for ML signal research.
- Do not use GPU/ML output as recommendation or readiness evidence.
- No strategy candidate, recommendation, ticket, readiness, product route, or trading path may be created.

Assigned tasks:
- GPU-P3-1 Frozen ML dataset and label contract.
- GPU-P3-2 GPU ML baseline models.
- GPU-P3-3 ML signal decile diagnostics.
- GPU-P3-4 Meta-labeling prototype.
- GPU-P3-5 Signal-to-strategy bridge.
- GPU-P3-6 Portfolio construction research.
- GPU-P3-7 ML overfit and leakage audit.

Hard requirements:
- Strict train/validation/test split.
- Label leakage check.
- CPU/GPU parity where applicable.
- Permutation baseline.
- Simple baselines only: logistic, MLP, XGBoost GPU.
- No transformer, RL, or complex ensemble.
- No model selection based on test performance.
- No rewriting weak ML results as strategy candidates.
- No local LLM, model download, or local chat serving.
- No network/provider fetch.
- No DB/cache rebuild or write.
- No schema/readiness/registry changes.
- No .env/key/token/auth/secret access or output.

If CUDA/ML libraries are unavailable or Python CUDA/ML smoke/parity fails, stop and return BLOCKED with GPU_STATUS. Do not install packages, deploy a local LLM/model/toolchain, or weaken boundaries.
```
