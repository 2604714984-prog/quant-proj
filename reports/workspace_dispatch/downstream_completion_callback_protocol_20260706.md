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

## Windows WSL2 Runtime Update

Recorded: 2026-07-07
Status: OLD_THREAD_IDS_NOT_VISIBLE_ON_CURRENT_HOST

Current Windows WSL2 dispatcher thread id:

```text
019f3830-4b44-7a83-944d-247a0d4dc169
```

Codex thread inspection on the current local host found only the new
Quant-Dispatcher thread for this quant workspace. The old fixed downstream
thread ids from the Mac-side controller records were not visible:

- `A_Share_Monitor` old thread `019f32bd-082d-73e2-b902-3d48b8d198ba`: `No Codex thread found`
- `strategy_work` old thread `019f30c3-247e-7f43-af60-96164539a183`: `No Codex thread found`
- `US_Stock_Monitor` old thread `019f32bd-af98-7eb0-bc5c-d1067e1fb145`: `No Codex thread found`
- `market_data` old thread `019f3283-a821-7002-961b-6f533d3518c2`: `No Codex thread found`

Send-message smoke tests to the old `market_data` and `A_Share_Monitor` thread
ids also returned `No Codex thread found`.

Interpretation:

- The old callback target and downstream thread acknowledgements remain
  historical Mac-side records.
- New Windows WSL2 downstream handoffs must use the current dispatcher thread id
  above after WSL2-visible downstream Codex threads are established.
- If a downstream thread tool is unavailable, the final answer must include the
  callback envelope.

## Windows WSL2 Downstream Threads

Recorded: 2026-07-07
Status: READY_ACKNOWLEDGED

The user directed Quant-Dispatcher to create new downstream threads on the
Windows WSL2 host. New thread ids and initialization acknowledgements:

| Project | New thread id | Status |
|---|---|---|
| `A_Share_Monitor` | `019f387b-617e-7273-b539-161216ae3002` | `CODEX_ACCEPTANCE / A_SHARE_MONITOR_WSL2_DOWNSTREAM_THREAD_READY` |
| `US_Stock_Monitor` | `019f387b-a161-7ad0-8678-f03a099612ba` | `CODEX_ACCEPTANCE / US_STOCK_MONITOR_WSL2_DOWNSTREAM_THREAD_READY` |
| `market_data` | `019f387b-e763-7c01-ae3d-6be552cdb6dc` | `CODEX_ACCEPTANCE / MARKET_DATA_WSL2_DOWNSTREAM_THREAD_READY` |
| `strategy_work` | `019f3881-5293-74a1-8535-814bd83c8681` | `CODEX_ACCEPTANCE / STRATEGY_WORK_WSL2_DOWNSTREAM_THREAD_READY` |

All four acknowledgements confirm the callback target:

```text
019f3830-4b44-7a83-944d-247a0d4dc169
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
Completion callback required: after finishing, send a prompt-only callback to the active Quant-Dispatcher thread with CODEX_ACCEPTANCE/DATA_REPORT/STRATEGY_REPORT or BLOCKED, commit/tree, artifacts, validation, residual blockers, and boundary statement. On the Windows WSL2 host, the active dispatcher thread is 019f3830-4b44-7a83-944d-247a0d4dc169. If the thread tool is unavailable, include the callback envelope in your final answer.
```

## Boundary

This callback protocol is controller coordination only. It does not authorize recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket emission, eligibility candidates, product-route activation, production readiness, broker/order/paper/live/auto behavior, DB writes, network ingest, schema migration, bulk ingest, readiness changes, registry activation, provider-data persistence, raw-data migration, `.env` reads, key output, or secret handling.
