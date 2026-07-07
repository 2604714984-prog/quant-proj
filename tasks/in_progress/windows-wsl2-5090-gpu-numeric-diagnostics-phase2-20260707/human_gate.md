# Human-Gate Classification - WINDOWS_WSL2_5090_GPU_NUMERIC_DIAGNOSTICS_PHASE2_20260707

Project: quant-proj
Role: Quant-Dispatcher
Prepared: 2026-07-07 Asia/Shanghai

## Classification

`L0_RESEARCH_ONLY_NUMERIC_DIAGNOSTICS`

No task-level HG-EXEC is granted by this packet.

## Allowed

- Read existing local research data and existing source artifacts needed for diagnostics.
- Run `nvidia-smi` and bounded local CUDA/Python numeric smoke tests.
- Run bounded local CPU/GPU numeric diagnostics.
- Write research-only reports, JSON, CSV summaries, deterministic tests, and manifests.
- Use local scratch tensor files only if they are not committed and are recorded in a manifest.

## Not Authorized

- local LLM deployment;
- Qwen deployment;
- model download or local chat model serving;
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
- post-hoc strategy selection based on test results.

## Stop Conditions

- CUDA is not visible in WSL.
- Python CUDA smoke fails.
- CPU/GPU parity fails.
- numeric diagnostics require network/provider fetch.
- numeric diagnostics require DB/cache rebuild/write.
- numeric diagnostics require schema/readiness/registry changes.
- any local LLM/Qwen deployment is required.
- any secret/environment access is required.
- diagnostics are being promoted into candidate, recommendation, ticket, readiness, product route, or trading path.

If a stop condition is encountered, downstream must stop and return `BLOCKED` with `GPU_STATUS` in the callback envelope.
