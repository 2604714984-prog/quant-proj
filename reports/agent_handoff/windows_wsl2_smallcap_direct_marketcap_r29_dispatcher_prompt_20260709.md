# Dispatcher Prompt - R29 SmallCap Direct MarketCap

Batch: `WINDOWS_WSL2_SMALLCAP_DIRECT_MARKETCAP_R29_20260709`

Read:

- `tasks/in_progress/windows-wsl2-smallcap-direct-marketcap-r29-20260709/spec.md`
- R28 result summary and closeout.
- R28 SmallCap row-level evidence artifacts.
- R28 leakage/timing audit.

## Execute

Run R29 as an ordinary research-only direct market-cap evidence resolution batch.

## Objective

Resolve the single remaining SmallCap blocker: direct market-cap membership snapshots.

If direct market-cap membership can be materialized from public/no-secret accepted sources, rebuild the SmallCap matrix and rerun leakage/timing and robustness checks.

If direct market-cap membership cannot be materialized, produce explicit field-unavailable evidence and stop SmallCap local-probe reconsideration until source evidence changes.

## Priority

- Direct market-cap source health and materialization.
- Direct-vs-proxy membership audit.
- Timing/leakage audit for direct membership.
- Matrix rebuild only if direct membership evidence passes.
- Final decision board.

## Boundary

Research-only. No actionable output, candidate promotion, readiness/product route, daily signal, broker/order/paper/live/auto path, active registry/schema change, credential output, or full-frame wide3068.

## Callback

Return the callback envelope required in the task packet, including direct market-cap source status, materialization status, timing audit result, matrix rebuild status, local probe prequalification result, candidate availability, boundary result, fixes required, and next source action.
