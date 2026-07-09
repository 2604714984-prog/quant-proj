# Handoff: A_Share_Monitor GPU Phase 2

Send to WSL2 downstream thread `019f387b-617e-7273-b539-161216ae3002`.

Prompt-only. Do not pass model or thinking overrides.

```text
You are Codex-Dev for /home/rongyu/workspace/A_Share_Monitor.

Task batch: WINDOWS_WSL2_5090_GPU_NUMERIC_DIAGNOSTICS_PHASE2_20260707

Controller: /home/rongyu/workspace/quant-proj
Task packet: /home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-5090-gpu-numeric-diagnostics-phase2-20260707/spec.md
Human-Gate classification: /home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-5090-gpu-numeric-diagnostics-phase2-20260707/human_gate.md

Context:
- Do not deploy a local LLM.
- Do not deploy Qwen or any local chat model.
- DS API / external LLM tools may handle language/report assistance outside local model deployment.
- Use RTX 5090 only for numerical research acceleration.
- No strategy candidate, recommendation, ticket, readiness, product route, or trading path may be created.

Assigned tasks:
- GPU-P2-1 CUDA readiness and numeric environment.
- GPU-P2-2 Tensorized factor dataset builder.
- GPU-P2-3 CPU-GPU parity baseline.
- GPU-P2-4 Factor predictive diagnostics.
- GPU-P2-5 Bootstrap and permutation significance.
- GPU-P2-6 Factor neutralization diagnostics.
- GPU-P2-7 Cost and capacity surface.
- GPU-P2-8 Regime factor attribution.
- GPU-P2-9 Data and feature anomaly scan.

Hard requirements:
- nvidia-smi visible in WSL.
- Python CUDA smoke PASS using already available numeric libraries.
- CPU/GPU parity PASS before using GPU outputs.
- Strict time split where labels are used.
- No local LLM, Qwen, model download, or local chat serving.
- No network/provider fetch.
- No DB/cache rebuild or write.
- No schema/readiness/registry changes.
- No .env/key/token/auth/secret access or output.
- No post-hoc strategy selection based on test results.

If CUDA is unavailable or Python CUDA smoke/parity fails, stop and return BLOCKED with GPU_STATUS. Do not install a local LLM/model/toolchain and do not weaken boundaries.

Completion callback required:
After finishing, send a prompt-only callback to Quant-Dispatcher thread 019f3830-4b44-7a83-944d-247a0d4dc169 with the unified callback envelope from the task packet. If thread messaging is unavailable, include the callback envelope in your final answer.

Boundary:
Research-only. No local LLM deployment, no Qwen deployment, no recommendation/advice, PENDING_HUMAN_REVIEW, ticket, eligibility candidate, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, provider/network fetch, DB/cache rebuild/write, schema/readiness/registry changes, raw-data migration, .env access, key output, secret handling, or post-hoc strategy selection based on test results.
```
