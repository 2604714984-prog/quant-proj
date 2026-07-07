# Handoff: A_Share_Monitor Authorized Controlled Advancement

Send to WSL2 downstream thread `019f387b-617e-7273-b539-161216ae3002`.

Prompt-only. Do not pass model or thinking overrides.

```text
You are Codex-Dev for /home/rongyu/workspace/A_Share_Monitor.

Task batch: WINDOWS_WSL2_AUTHORIZED_CONTROLLED_ADVANCEMENT_20260707

Controller: /home/rongyu/workspace/quant-proj
Task packet: /home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-authorized-controlled-advancement-20260707/spec.md
Human-Gate source: /home/rongyu/workspace/quant-proj/reports/human_gate/windows_wsl2_broad_authorization_20260707.md
Decision log: /home/rongyu/workspace/quant-proj/reports/human_gate/decisions.jsonl

Assigned workstreams:

1. HG-EXEC-TASK-GPU-ENV-PHASE2-PHASE3-20260707
   - Install the minimal CUDA Python / CUDA ML stack needed in the A_Share_Monitor project environment to run research-only GPU numeric and ML diagnostics on RTX 5090.
   - Allowed package families: numpy/pandas/scipy/scikit-learn, xgboost GPU-capable build, torch CUDA build or cupy/numba equivalent needed for CUDA smoke/parity/MLP, and direct test dependencies.
   - Forbidden: local LLM, Qwen, transformers, RL frameworks, local chat serving, model download, secret access/output.
   - After environment smoke passes, resume Phase 2 numeric diagnostics and Phase 3 ML signal research from their controller task packets.

2. HG-EXEC-TASK-A-EAST-MONEY-COVERAGE-20260707
   - Perform bounded A-share East Money coverage expansion / diagnostics using allowed provider/network fetch and controlled local writes only where needed.
   - Preserve R15/R16 facts until source evidence changes: 77 CROSSCHECK_PASS, 121 CROSSCHECK_DATE_GAP, 2870 CROSSCHECK_MISSING_EAST_MONEY; 198 common symbols are overlap only.
   - No recommendation, ticket, strategy candidate, product route, production readiness, broker/order/paper/live/auto.

Required validation:
- nvidia-smi visible in WSL and Python CUDA smoke PASS before GPU outputs are trusted.
- CPU/GPU parity where applicable.
- Strict train/validation/test split and label leakage checks for ML.
- JSON parse PASS for JSON artifacts.
- git diff --check PASS.
- agent_safety_check.py PASS where applicable.
- forbidden local LLM/Qwen/recommendation/candidate/readiness/trading scan PASS.
- command transcript and manifest/count/hash evidence for any install, network fetch, DB/cache write, or generated data artifact.

Completion callback:
Send prompt-only callback to Quant-Dispatcher thread 019f3830-4b44-7a83-944d-247a0d4dc169 with the unified callback envelope in the task packet.
```
