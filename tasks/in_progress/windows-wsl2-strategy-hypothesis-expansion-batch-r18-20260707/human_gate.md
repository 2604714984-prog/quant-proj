# Human-Gate Classification - R18 Strategy Hypothesis Expansion

Batch: `WINDOWS_WSL2_STRATEGY_HYPOTHESIS_EXPANSION_BATCH_R18_20260707`
Classification: ordinary research-only strategy hypothesis expansion
External-audit trigger opened by intake: `no`

## Allowed

- Offline/local research diagnostics on already accepted source evidence.
- Research-only factor, interaction, regime, cost, trade-count, drawdown, ML-filter, meta-label, portfolio construction, bootstrap/permutation, walk-forward, and shadow leaderboard diagnostics.
- Chunked wide3068 research probe only if prequalified by `A-WIN-R18-17`.
- Controller records, downstream callbacks, validation artifacts, result summary, and closeout.

## Not Authorized

- Recommendation/advice.
- `PENDING_HUMAN_REVIEW`, ticket, eligibility candidate, strategy candidate promotion.
- Product-route activation, data-clear promotion, production readiness.
- broker/order/paper/live/auto.
- Raw-data migration.
- `.env`, key, token, auth, credential, or secret access/output.
- Full-frame wide3068 strategy search.
- Unapproved provider/network fetch.
- DB/cache write or rebuild.
- Schema/readiness/registry change.
- market_data activation.
- Using test results to choose parameters.
- Using shadow leaderboard as actionable ranking.
- Using ML score as recommendation.

## Separate Authorization Required

Any provider/network fetch, DB/cache write or rebuild, schema/readiness/registry change, product-route activation, or market_data activation requires separate task-level HG-EXEC and any required external audit gate.
