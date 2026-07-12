# ADR: Research Core and Actionable Capability Boundary

Status: `ACCEPTED_FOR_REMEDIATION_R1`

Date: 2026-07-12

## Decision

The default research entry points are pure research and evidence surfaces. The
controller follows the same boundary. They must not expose ticket emission,
manual-fill, broker, order, paper, live, or automatic-execution commands.

The A-share HITL implementation, if retained, is a separately controlled
module and a separate audit scope. During Remediation R1 its durable ledger
write capability is hard-disabled. Any later enablement requires a new
controller decision, an independently accepted capability review, a durable
human gate, and a command-bound execution attestation. A HITL ticket is not an
order and must never be routable automatically.

Manual-fill is classified only as user-entered bookkeeping for an event that
the user states has already occurred. It is outside the research-only core,
disabled by default, and may not generate a side, symbol, price, quantity,
weight, or timing instruction.

Broker integration, order routing or submission, system-generated fills,
paper trading, live trading, and automatic execution remain forbidden.

## Consequences

- External-review documents must describe retained HITL/manual-fill code
  honestly; they may not claim that a capability is absent when it is merely
  disabled or isolated.
- A machine-readable capability matrix is authoritative for capability facts.
- CI must fail if the default CLI exposes an actionable command or if prose
  disagrees with the capability matrix.
- Infrastructure remediation does not reopen any rejected or blocked strategy.
- `strategy_candidate_available` remains `false` throughout this stage.
