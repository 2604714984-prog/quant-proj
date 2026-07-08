# R21 Development-First Dispatcher Amendment

Date: 2026-07-08
Controller: Quant-Dispatcher
Batch: `WINDOWS_WSL2_FEATURE_MATERIALIZATION_AND_STRATEGY_DELTA_R21_20260708`

## Amendment

From now on, R21 prioritizes actual project progress and strategy research.

Do not expand safety policy work.
Do not ask for another architecture/gate review.
Do not stop for ordinary warnings.

## Hard Stops

Stop only for:

1. Secret, credential, key, token, auth, or `.env` access or output.
2. Broker/order/paper/live/auto execution or daily signal push.
3. Product route, readiness, active registry, or production adapter activation.
4. Actionable investment advice or ticket claim.
5. Test-result parameter selection.
6. Non-public, paywalled, auth-required, or anti-abuse-bypassing provider access.

Everything else should be logged as a warning and research should continue.

## R21 Required Delivery

ETF lane:

- Materialize ETF amount/NAV/premium/turnover for the 30-symbol ETF universe if possible.
- If unavailable, produce field-level unavailable evidence.
- Then run limitation-aware ETF delta diagnostics.

A-share lane:

- Materialize PEG/event/funds/hot-money feature rows for the 77-symbol pass-only universe.
- If rows validate, run new-feature-only delta diagnostics.
- If rows do not validate, skip with reason, not more policy reports.

Global/news/macro lane:

- Materialize date-indexed context/regime rows where possible.
- Never use them as direct signals.

Do not accept source-review-only completion for materialization lanes.

End with data rows, strategy diagnostics, failure updates, and concrete next experiments.
