# Dispatcher Prompt - R29 Direct Market-Cap Membership

Batch: `WINDOWS_WSL2_DIRECT_MARKETCAP_MEMBERSHIP_R29_20260709`

Read:

- `tasks/in_progress/windows-wsl2-direct-marketcap-membership-r29-20260709/spec.md`
- R28 result or final sync artifacts.
- A_Share_Monitor R28 row-level evidence artifacts.
- market_data R28 contract.
- strategy_work R28 final sync.

## Execute

Run R29 as an ordinary research-only direct market-cap evidence completion batch.

## Objective

Resolve the exact blocker that prevented SmallCap Low Turnover local probe reconsideration in R28: direct market-cap membership snapshots.

Do not search for new strategies. Do not rerun pass77 repairs. Do not reopen ETF rotation.

## Priority

1. Find or materialize direct total_mv / circ_mv / market_cap evidence for SmallCap decision dates and symbols.
2. Rebuild the pre-trade signal matrix using direct market-cap membership.
3. Compare direct membership against the R28 amount/amount_ma20 proxy membership.
4. Rerun leakage/timing audit and matrix-based robustness diagnostics.
5. Decide whether SmallCap becomes LOCAL_RESEARCH_PROBE_ELIGIBLE or remains EVIDENCE_INCOMPLETE.

## Boundary

Research-only. No actionable output, candidate promotion, readiness/product route, daily signal, broker/order/paper/live/auto path, active registry/schema change, credential output, or full-frame wide3068.

## Callback

Return the callback envelope required in the task packet, including direct market-cap coverage status, signal matrix status, leakage/timing audit result, robustness status, local probe prequalification result, candidate availability, boundary result, fixes required, and next source action.
