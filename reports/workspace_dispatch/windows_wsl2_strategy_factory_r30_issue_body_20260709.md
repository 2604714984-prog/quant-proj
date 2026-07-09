# R30 Strategy Factory Tracking

Batch: `WINDOWS_WSL2_STRATEGY_FACTORY_R30_20260709`

Branch: `codex/task-packet-r29-direct-marketcap-membership-20260709`

## Goal

Run one large research-only strategy factory until it reaches a clear research outcome:

- `LOCAL_RESEARCH_PROBE_ELIGIBLE`, or
- `NO_VERIFIABLE_STRATEGY_UNDER_CURRENT_EVIDENCE`, or
- `BLOCKED_BY_AUTH_OR_SOURCE_LIMIT`.

## Priority

1. Resolve SmallCap direct market-cap gate via R29 if incomplete.
2. If SmallCap passes, run decisive local-probe research diagnostics.
3. If blocked, harden US30W and pass77 evidence gates.
4. If all active surfaces are blocked, run pre-registered new strategy families.
5. End with a final strategy factory board.

## Boundary

Research-only tracking issue. No production activation or actionable output.
