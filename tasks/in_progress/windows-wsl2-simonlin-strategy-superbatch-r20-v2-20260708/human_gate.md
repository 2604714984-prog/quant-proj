# Human-Gate Classification - R20_V2 SimonLin Strategy Superbatch

Batch: `WINDOWS_WSL2_SIMONLIN_STRATEGY_SUPERBATCH_R20_V2_20260708`
Recorded: 2026-07-08 Asia/Shanghai
Authorization record: `reports/human_gate/windows_wsl2_simonlin_strategy_superbatch_r20_v2_authorization_20260708.md`

## Classification

Research-data fast path plus explicit R20_V2 research-only authorization.

Per-task `HG-EXEC` required: `no` for bounded public/no-secret research fetches, source-local research cache/staging/report/test writes, isolated dependency installation, source-local experiment stores, GPU/CPU numerical diagnostics, and friction-reduction tooling under this R20_V2 scope.

External-audit trigger open: `no`.

## Authorized For R20_V2

- SimonLin public repo clone/read and license/source inventory.
- Bounded public/no-secret endpoint smoke tests and research fetches.
- Source-local research artifacts: CSV, Parquet, JSON, JSONL, SQLite, DuckDB, reports, command transcripts, manifests, hashes, and tests.
- Isolated repo-local Python/Node dependency installation required for research adapters, source health, numeric diagnostics, or validation.
- RTX 5090 research diagnostics under the currently recorded host/driver default GPU power policy with telemetry where feasible.
- DS API or configured external LLM/API endpoints for report drafting, summarization, critique, and code review only, without exposing secrets.

## Not Authorized

- Recommendation/advice.
- `PENDING_HUMAN_REVIEW`, ticket, eligibility candidate, or strategy candidate promotion.
- Readiness promotion, data-clear promotion, active registry activation, active schema migration, product-route activation, market_data activation.
- Broker/order/paper/live/auto or daily signal push.
- Raw-data migration into `quant-proj`.
- `.env`, token, key, credential, auth, or secret access/output.
- Unbounded provider sync or circumvention of provider blocks/rate limits/paywalls/auth/anti-abuse systems.
- TradingAgents buy/hold/sell, PEG labels, news heat, macro probability, ETF leaderboard, ML score, or shadow leaderboard as actionable advice.
- Test-result parameter selection.

## Stop Conditions

- `R19_RESULTS_NOT_IMPORTED_BEFORE_NEW_SEARCH`
- `R19_INTERESTING_44_IGNORED`
- `ETF_GRID_V2_REPEATED_WITHOUT_DELTA`
- `A_SHARE_R18_R19_FAILED_FEATURES_RETRIED_WITHOUT_NEW_EVIDENCE`
- `SOURCE_HEALTH_NOT_RUN_BEFORE_FETCH`
- `PROVIDER_FETCH_UNBOUNDED`
- `SOURCE_AUTH_REQUIRED`
- `LICENSE_REVIEW_REQUIRED`
- `SECRET_OR_ENV_ACCESS_REQUIRED`
- `PRODUCT_ROUTE_ACTIVATION_ATTEMPTED`
- `READINESS_PROMOTION_ATTEMPTED`
- `REGISTRY_ACTIVATION_ATTEMPTED`
- `RAW_DATA_MIGRATION_INTO_QUANT_PROJ`
- `RECOMMENDATION_OR_TICKET_LANGUAGE`
- `STRATEGY_CANDIDATE_PROMOTION`
- `TRADINGAGENTS_BUY_HOLD_SELL_USED`
- `NEWS_OR_MACRO_USED_AS_DIRECT_SIGNAL`
- `ETF_DAILY_SIGNAL_PUSH_ATTEMPTED`
- `TEST_RESULT_USED_FOR_PARAMETER_SELECTION`
- `FAILURE_MEMORY_IGNORED_FOR_DUPLICATE_SEARCH`
- `SHADOW_LEADERBOARD_USED_AS_ACTIONABLE_RANKING`
- `EXPERIMENT_WITHOUT_MANIFEST`
- `CALLBACK_ENVELOPE_MISSING`
