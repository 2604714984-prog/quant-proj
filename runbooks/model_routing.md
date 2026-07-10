# Sol Manager / Luna Delivery

Policy id: `SOL_MANAGER_LUNA_DELIVERY_V1`

The collaboration system has four working roles and one automated gate. It is
intentionally small: no routine packet is reviewed twice by Sol.

| Role | Model | Job |
|---|---|---|
| Quant-Manager | `gpt-5.6-sol` / high | Hard decomposition, scope, dependencies, exceptional evidence judgment |
| Quant-Dispatcher | `gpt-5.6-luna` / medium | Queue, bounded packets, callbacks, stall detection |
| Executor | `gpt-5.6-luna` / medium | Implementation, batch work, tests, evidence |
| Acceptance | `gpt-5.6-luna` / high, read-only | Final evidence acceptance |

## One path

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

## Context and cost

- Reuse the task packet; send only changed requirements or failed gates.
- Store long command output in artifacts; callbacks contain exact summaries.
- Do not replay full task history to replacement executors.
- Do not ask Sol to restate a coherent Luna acceptance.

These routing rules do not change Human-Gate, research-only, secret, migration,
readiness, product-route, or broker/order/paper/live/auto boundaries.
