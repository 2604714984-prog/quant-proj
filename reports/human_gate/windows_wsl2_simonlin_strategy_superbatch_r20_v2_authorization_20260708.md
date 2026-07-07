# R20_V2 Research-Only Authorization

Decision date: 2026-07-08 Asia/Shanghai
Controller: Quant-Dispatcher
Decision id: `HG-STANDING-R20-V2-RESEARCH-ONLY-SIMONLIN-SUPERBATCH-20260708`
Batch: `WINDOWS_WSL2_SIMONLIN_STRATEGY_SUPERBATCH_R20_V2_20260708`

## User Direction

The user authorized R20 as one large research-only SimonLin strategy superbatch.

The user authorizes all reasonable bounded public/no-secret research data fetches, source-local research cache/staging/report/test writes, isolated dependency installation, GPU/CPU numerical research, experiment-store tooling, and friction-reduction tools needed to complete the batch.

## Authorized

- Public/no-secret network fetches from SimonLin repositories and documented public data-source paths, bounded by provider, endpoint, symbol/universe, date range, output path, transcript, manifest, counts, and hashes.
- Source-local research cache/staging writes, including CSV, Parquet, JSON, JSONL, SQLite, DuckDB, reports, transcripts, manifests, tests, and temporary artifacts inside the relevant source repository.
- Source-local research data rebuilds needed for diagnostics, provided they do not alter active production registry/readiness/product-route state and do not migrate raw data into `quant-proj`.
- Installing reasonable Python/Node dependencies into repo-local virtual environments or isolated environments for SimonLin research adapters, ETF research, global data smoke tests, GPU/CPU numeric tasks, experiment-store tooling, and validation tests.
- Cloning or reading public GitHub repositories under `simonlin1212` for research-source intake, license inventory, adapter design, and source-health smoke tests.
- Adapting public code snippets or endpoint logic only when license-compatible and with attribution recorded. If license compatibility is unclear, downstream must stop with `LICENSE_REVIEW_REQUIRED`.
- Bounded CPU/GPU numerical research jobs, including ETF robustness diagnostics, A-share factor diagnostics, bootstrap/permutation, walk-forward, ML-signal diagnostics, and experiment-store generation.
- RTX 5090 use under the currently recorded host/driver default GPU power policy unless the user later reinstates a cap. GPU telemetry must still be reported where feasible.
- Already-configured external LLM/API endpoints, including DS API, for text summarization, report drafting, hypothesis drafting, or code review only, without printing or exposing secrets.
- Unified run commands, source-health manifests, experiment stores, failure memory, do-not-retry records, preflight scoring, overclaim scans, callback generators, and artifact indexes to reduce research friction.

## Not Authorized

- Recommendation/advice.
- `PENDING_HUMAN_REVIEW`, ticket, eligibility candidate, or strategy candidate promotion.
- Product-route activation, market_data activation, readiness promotion, active registry change, active schema migration, broker/order/paper/live/auto, or daily signal push.
- Raw-data migration into `quant-proj`.
- Secret, `.env`, token, key, credential, or auth-file reading/output.
- Unbounded provider sync.
- Circumventing provider blocks, rate limits, paywalls, auth, or anti-abuse systems.
- Using TradingAgents buy/hold/sell output, PEG labels, news heat, macro probability, ETF leaderboard, ML score, or shadow leaderboard as actionable advice.
- Selecting strategy parameters from test results.
- Hiding failed experiments or omitting negative results.

## Classification

R20_V2 is authorized under `RESEARCH_DATA_FAST_PATH` plus explicit R20_V2 standing authorization for bounded installs and source-local research tooling.

Task-level `HG-EXEC-TASK-*` records are not required for ordinary bounded public/no-secret research fetches, source-local research cache/staging/report/test writes, experiment-store generation, isolated dependency installation, or GPU/CPU numerical diagnostics under this R20_V2 scope.

Boundary-changing actions remain blocked and require a separate explicit task and required audit gate.

## External Audit Trigger

Opened by this authorization: `no`.

R20_V2 does not request product-route activation, readiness promotion, ticket/candidate creation, recommendation, raw-data migration, broker/order/paper/live/auto, or secret handling.

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
