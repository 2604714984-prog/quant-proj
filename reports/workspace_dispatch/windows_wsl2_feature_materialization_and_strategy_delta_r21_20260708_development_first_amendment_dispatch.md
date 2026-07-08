# WINDOWS_WSL2_FEATURE_MATERIALIZATION_AND_STRATEGY_DELTA_R21_20260708 Development-First Amendment Dispatch

Recorded: 2026-07-08 Asia/Shanghai
Controller: Quant-Dispatcher
Batch: `WINDOWS_WSL2_FEATURE_MATERIALIZATION_AND_STRATEGY_DELTA_R21_20260708`

## Reason

The user issued a R21 development-first amendment after the initial R21 source callbacks and before controller closeout.

The amendment changes controller interpretation:

- Do not accept source-review-only completion for materialization lanes.
- Do not expand safety policy work.
- Do not ask for another architecture/gate review.
- Do not stop for ordinary warnings.
- Continue research unless a hard stop is triggered.

## Hard Stops

Stop only for:

1. Secret, credential, key, token, auth, or `.env` access or output.
2. Broker/order/paper/live/auto execution or daily signal push.
3. Product route, readiness, active registry, or production adapter activation.
4. Actionable investment advice or ticket claim.
5. Test-result parameter selection.
6. Non-public, paywalled, auth-required, or anti-abuse-bypassing provider access.

## Dispatch

| Target | Thread | Workstream | Status |
|---|---|---|---|
| `A_Share_Monitor` | `019f387b-617e-7273-b539-161216ae3002` | `R21_DEVELOPMENT_FIRST_AMENDMENT_A_SHARE_CONTINUATION` | dispatched |
| `strategy_work` | `019f3881-5293-74a1-8535-814bd83c8681` | `R21_DEVELOPMENT_FIRST_FINAL_SYNC_HOLD` | dispatched |

## Required A-share Continuation

- Materialize ETF amount/NAV/premium/turnover for the 30-symbol ETF universe if possible.
- If unavailable, produce field-level unavailable evidence.
- Then run limitation-aware ETF delta diagnostics.
- Materialize PEG/event/funds/hot-money feature rows for the 77-symbol pass-only universe.
- If rows validate, run new-feature-only delta diagnostics.
- If rows do not validate, skip with reason.
- Produce failure updates and concrete next experiments.

## Controller Interpretation

R21 is no longer ready for final closeout based on the earlier limitation-preservation callback alone. Final sync and closeout must wait for the amended A_Share_Monitor continuation result.

## Boundary

Research-only. No actionable output, recommendation/advice, candidate promotion, readiness promotion, route activation, daily signal push, raw-data migration into controller, active schema/registry activation, full-frame wide3068, test-result parameter selection, non-public/auth-required provider access, or credential output.
