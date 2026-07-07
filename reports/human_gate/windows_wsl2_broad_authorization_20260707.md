# Windows WSL2 Broad Human-Gate Authorization - 20260707

Project: quant-proj
Role: Quant-Dispatcher
Recorded: 2026-07-07T13:46:58+08:00
Source: user message granting all previously discussed authorizations and permitting required installation; GPU hardware available is RTX 5090 only.

Power update: subsequent RTX 5090 runs must be locked to 400W. Higher power requires separate user authorization for that task.

## User Authorization Interpreted

The user authorized the controller to proceed with the categories previously identified as blocked or authorization-benefiting:

- research-only CUDA Python / CUDA ML environment enablement;
- GPU Phase 2 numeric diagnostics resume after CUDA Python smoke and CPU/GPU parity;
- GPU Phase 3 ML signal research resume after CUDA ML smoke and split/leakage validation;
- A-share East Money coverage expansion and A-share data repair requiring bounded network/provider fetch and controlled writes;
- US 44-symbol metadata repair / controlled US 300-symbol ingest requiring bounded network/provider fetch and controlled writes;
- market_data product-read route/readiness preparation and audit packet work.

## Non-Authorization

This does not authorize:

- local LLM, Qwen, or local chat model deployment;
- recommendation/advice;
- treating any ML/GPU/data output as a strategy candidate, recommendation, ticket, production readiness, or trading signal;
- broker APIs, order routing, order submission, paper trading, live trading, auto execution, system-generated orders/fills, trade plans, target weights, allocation, position sizing, or entry-price instructions;
- reading, printing, copying, committing, or exposing `.env`, keys, tokens, auth files, credentials, or secrets;
- moving raw DB/parquet/SQLite files into `quant-proj`;
- bypassing Codex-Dev validation, Codex-Audit, or user-operated GPT Pro / ChatGPT external audit where required.

## Execution Control

The broad user authorization is recorded as standing approval plus task-level execution records. Actual L1-L4 work still must use the matching `HG-EXEC-TASK-*` record, command transcript, bounded flags, manifest/count/hash evidence, Codex-Dev callback, and required audit gates.

For GPU work, downstream handoffs must include `GPU_POWER_LIMIT_WATTS=400`, record power-cap status in the callback, and stop before exceeding 400W unless a separate higher-power authorization exists.
