# Human-Gate Classification - WINDOWS_WSL2_5090_GPU_ML_SIGNAL_RESEARCH_PHASE3_20260707

Project: quant-proj
Role: Quant-Dispatcher
Prepared: 2026-07-07 Asia/Shanghai

## Classification

`L0_RESEARCH_ONLY_ML_SIGNAL_RESEARCH`

No task-level HG-EXEC is granted by this packet.

Current execution status: `BLOCKED_PRE_DISPATCH_CUDA_ML_ENV_UNAVAILABLE`.

## Allowed If Environment Exists

- Read existing local research data and existing source artifacts needed for ML signal diagnostics.
- Run `nvidia-smi` and bounded local CUDA/Python ML smoke tests.
- Run bounded local CPU/GPU ML parity diagnostics.
- Write research-only reports, JSON, CSV summaries, deterministic tests, and manifests.
- Use local scratch tensor/model files only if they are not committed and are recorded in a manifest.

## Not Authorized

- local LLM deployment;
- recommendation/advice;
- `PENDING_HUMAN_REVIEW`, ticket, or eligibility candidate;
- data-clear promotion;
- product-route activation;
- production readiness;
- broker/order/paper/live/auto;
- provider/network fetch;
- DB/cache rebuild or write;
- schema migration;
- readiness change;
- registry activation;
- raw-data migration;
- `.env`, key, token, auth, credential, or secret access/output;
- transformer/RL/complex ensemble start;
- model selection based on test performance;
- rewriting weak ML results as strategy candidates;
- package/toolchain/model installation without separate user authorization.

## Stop Conditions

- CUDA is not visible in WSL.
- Python CUDA/ML smoke fails.
- required Python CUDA/ML libraries are unavailable.
- CPU/GPU parity fails.
- label leakage is detected.
- model selection depends on test performance.
- ML diagnostics require network/provider fetch.
- ML diagnostics require DB/cache rebuild/write.
- ML diagnostics require schema/readiness/registry changes.
- any local LLM deployment is required.
- any secret/environment access is required.
- diagnostics are being promoted into candidate, recommendation, ticket, readiness, product route, or trading path.

If a stop condition is encountered, downstream must stop and return `BLOCKED` with `GPU_STATUS` in the callback envelope.
