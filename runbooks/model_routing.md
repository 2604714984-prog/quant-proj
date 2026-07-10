# Sol Manager / Luna Delivery With Dedicated Strategy Research

Policy id: `SOL_MANAGER_LUNA_DELIVERY_V2`

The collaboration system has five working roles and one automated gate. The
default delivery path stays Luna-based. A separate, narrowly scoped
`strategy_work` path uses Sol/high for primary strategy research execution; it
does not turn that research thread into a dispatcher or final reviewer.

| Role | Model | Job |
|---|---|---|
| Quant-Manager | `gpt-5.6-sol` / high | Hard decomposition, scope, dependencies, exceptional evidence judgment |
| Quant-Dispatcher | `gpt-5.6-luna` / medium | Queue, bounded packets, callbacks, stall detection |
| Executor | `gpt-5.6-luna` / medium | Implementation, batch work, tests, evidence |
| Strategy Research Executor | `gpt-5.6-sol` / high | Dedicated `strategy_work` research execution, evidence, and prior-result continuity |
| Acceptance | `gpt-5.6-luna` / high, read-only | Final evidence acceptance |
| Codex-Audit | `gpt-5.6-luna` / high, read-only | Hash-bound process review with no filesystem writes or approval escalation |

## Default delivery path

```text
SOL_MANAGER
  -> LUNA_DISPATCHER
  -> LUNA_EXECUTOR
  -> AUTOMATED_GATE
       red   -> LUNA_REWORK or BLOCKED
       green -> LUNA_ACCEPTANCE
                  accepted -> done
                  clear correction -> LUNA_REWORK
                  unresolved evidence gap/conflict -> SOL_MANAGER
                                                     -> LUNA_FINAL_ACCEPTANCE
```

The dispatcher is an operations role, not another coordinator. It must not
repeat Manager reasoning or acceptance review.

## Dedicated strategy_work research path

The existing `strategy_work` research thread is bound to exactly:

- `RECOMMENDED_AGENT: strategy_research_executor`;
- `MODEL_ROLE: strategy_research_executor`;
- `MODEL: gpt-5.6-sol`;
- `REASONING_EFFORT: high`;
- `TARGET_PROJECT: strategy_work`.

Its path is separate from the default delivery path:

```text
SOL_MANAGER
  -> SOL_STRATEGY_RESEARCH_EXECUTOR
  -> AUTOMATED_GATE
       red   -> SOL_STRATEGY_RESEARCH_REWORK or BLOCKED
       green -> LUNA_ACCEPTANCE
```

`SOL_STRATEGY_RESEARCH_EXECUTOR` is a primary research execution role. It is
not `LUNA_DISPATCHER`, does not maintain queues or dispatch other workers, and
cannot emit final acceptance. The automated gate must bind its role and model
to the task packet. Final acceptance remains a separate read-only Luna/high
context. Normal implementation and batch execution remain Luna/medium.

### Active operational binding

This policy is currently bound to one existing research task, rather than being
a generic assertion that every Sol task is a strategy executor:

| Field | Bound value |
|---|---|
| Task id | `019f3881-5293-74a1-8535-814bd83c8681` |
| Title | `Strategy Work — Sol Research` |
| Target | `strategy_work` |
| Role | `strategy_research_executor` |
| Model | `gpt-5.6-sol` / `high` |
| Manager callback | `019f4c70-cac3-7211-8e04-47b8b51c819e` |
| Luna dispatcher reference (not this role) | `019f4ca0-2054-77e3-9559-7005c0f9b565` |
| Final acceptance | independent `codex_acceptance`, `gpt-5.6-luna` / `high`, read-only |

The research task returns its execution callback and automated-gate evidence
to the active Quant-Manager callback above. The manager then sends the green
record to a separate Luna acceptance context; the strategy task does not
self-accept and is never reclassified as Luna dispatcher.

Codex-Audit uses the dedicated `agents/luna-audit.toml` layer. Every audit
packet binds the reviewed commit/tree and `CONTEXT_DELTA_SHA256`; the sandbox
is `read-only` and approval policy is `never`. Findings return in the task
callback rather than being written into the reviewed repository.

## Two records

Each task uses only:

1. an execution gate record, validated with
   `scripts/validate_automated_gate_manifest.py`;
2. a Luna acceptance record, validated with
   `scripts/validate_luna_acceptance.py`.

The execution record binds the task packet, expected commands, callback,
artifacts, and Git refs. The acceptance record points to the green execution
record and contains the Luna decision. There is no separate routine Sol review
packet.

## Sol escalation

Only these reasons may return to Quant-Manager:

- `EVIDENCE_INSUFFICIENT_AFTER_ONE_BOUNDED_LUNA_REWORK`;
- `EVIDENCE_CONFLICT_UNRESOLVED_BY_DETERMINISTIC_CHECKS`.

The escalation carries only the disputed claim and evidence references. Test
failures, missing fields, formatting problems, tool failures, and environment
failures stay with Luna. After a Sol ruling, a new Luna acceptance record owns
the final result.

Sol/high execution in the dedicated `strategy_work` role is not a Sol evidence
escalation. A red strategy automated gate returns to that same bounded research
executor or becomes `BLOCKED`; it does not grant manager, dispatcher, or
acceptance authority to the research thread.

## Context and cost

- Reuse the task packet; send only changed requirements or failed gates.
- Before continuing strategy research, preserve the thread's prior findings in
  its authorized durable research memo or index and pass only the new research
  delta into the next execution turn.
- Store long command output in artifacts; callbacks contain exact summaries.
- Do not replay full task history to replacement executors.
- Do not ask Sol to restate a coherent Luna acceptance.

These routing rules do not change Human-Gate, research-only, secret, migration,
readiness, product-route, or broker/order/paper/live/auto boundaries.
