# Downstream Completion Callback Protocol

Project: quant-proj
Role: Quant-Dispatcher
Recorded: 2026-07-06
Status: ACTIVE_PROTOCOL

## User Directive

When a downstream Codex thread receives a Quant-Dispatcher task, it must report completion back to the dispatcher thread after finishing the task.

Dispatcher thread id:

```text
019f2766-7c5f-7562-b2e3-b4d76de7bfa9
```

## Required Callback

At task completion, the downstream Codex thread should send a prompt-only message to the dispatcher thread with:

- batch id
- task id or task range
- source repo and working directory
- final status: `CODEX_ACCEPTANCE`, `DATA_REPORT`, `STRATEGY_REPORT`, `BLOCKED`, or `ACCEPTED_WITH_WARNINGS`
- commit, tree, branch, and push status when files changed
- changed files and key artifacts
- validation results
- residual blockers
- explicit boundary statement

Preferred callback envelope:

```xml
<codex_delegation>
  <source_thread_id>DOWNSTREAM_THREAD_ID</source_thread_id>
  <input>
  CALLBACK_TO_QUANT_DISPATCHER
  Project: ...
  Batch: ...
  Status: ...
  Commit: ...
  Tree: ...
  Artifacts: ...
  Validation: ...
  Boundary: ...
  </input>
</codex_delegation>
```

## Fallback

If a downstream Codex thread cannot send a message to the dispatcher thread, its final answer must still include the same callback envelope and begin with the final status token. Quant-Dispatcher will recover it by coarse polling.

## Acknowledgements

- `A_Share_Monitor` thread `019f32bd-082d-73e2-b902-3d48b8d198ba`: acknowledged via `CODEX_ACCEPTANCE / STANDING_PROTOCOL_UPDATE_ACK`.
- `strategy_work` thread `019f30c3-247e-7f43-af60-96164539a183`: acknowledged via `CALLBACK / STANDING_PROTOCOL_UPDATE_ACK`.
- `US_Stock_Monitor` thread `019f32bd-af98-7eb0-bc5c-d1067e1fb145`: acknowledged via `CODEX_ACCEPTANCE - STANDING_PROTOCOL_UPDATE_20260706`; local memory note reported at `/Users/rongyuxu/.codex/memories/extensions/ad_hoc/notes/20260706T062846-quant-dispatcher-completion-callback.md`.
- `market_data` thread `019f3283-a821-7002-961b-6f533d3518c2`: standing protocol update sent; thread remains in older approval-blocked active turn, acknowledgement not yet recorded in controller.

## Standing Dispatch Addition

All future Quant-Dispatcher handoffs must include:

```text
Completion callback required: after finishing, send a prompt-only callback to Quant-Dispatcher thread 019f2766-7c5f-7562-b2e3-b4d76de7bfa9 with CODEX_ACCEPTANCE/DATA_REPORT/STRATEGY_REPORT or BLOCKED, commit/tree, artifacts, validation, residual blockers, and boundary statement. If the thread tool is unavailable, include the callback envelope in your final answer.
```

## Boundary

This callback protocol is controller coordination only. It does not authorize recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket emission, eligibility candidates, product-route activation, production readiness, broker/order/paper/live/auto behavior, DB writes, network ingest, schema migration, bulk ingest, readiness changes, registry activation, provider-data persistence, raw-data migration, `.env` reads, key output, or secret handling.
