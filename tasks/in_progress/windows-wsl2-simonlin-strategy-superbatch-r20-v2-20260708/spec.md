# WINDOWS_WSL2_SIMONLIN_STRATEGY_SUPERBATCH_R20_V2_20260708 Spec

## Objective

Run a unified research-only strategy-development superbatch after R19 closeout. R20_V2 must not blindly repeat R19's ETF 9,600-row grid or R18/R19 failed A-share searches. It must first import R16-R19 evidence, build experiment-store and negative-result memory, audit R19's 44 initially interesting ETF grid rows, explain A-share zero-wide results, and then run only justified delta searches using new SimonLin data, new features, new regimes, or new execution assumptions.

## R19 Baseline

- R19 closeout: `CLOSED_ACCEPTED_RESEARCH_ONLY_WITH_WARNINGS`.
- ETF snapshot: `etf_rotation_e1_20260707`, 30 symbols, 55,726 qfq OHLCV rows.
- ETF timing: close T signal, T+1 open execution, same-day close-to-close false.
- ETF robust grid v2: 9,600 pre-registered validation rows.
- ETF grid labels: `COST_LIMITED=3340`, `WEAK=1638`, `UNSTABLE=4578`, `INTERESTING=44`.
- ETF final hypothesis board: `INTERESTING=0`.
- Equity R19: 130 R18 rows clustered into 23 failure-mode/family clusters.
- Equity rescue diagnostics: 12 instability rows and 24 validation-failure rows.
- Equity wide eligible count: 0.
- Equity wide result: `NO_R19_EQUITY_WIDE_RESEARCH_PROBE_ELIGIBLE`.
- `STRATEGY_CANDIDATE_AVAILABLE=false`.
- East Money split: `77 CROSSCHECK_PASS / 121 CROSSCHECK_DATE_GAP / 2870 CROSSCHECK_MISSING_EAST_MONEY`.
- market_data product-route prep remains inactive and externally gated.

## Lane 0 - R19 Evidence Freeze And Preconditions

| Task | Name | Deliverables |
|---|---|---|
| `R20-0-1` | R19 evidence freeze | `reports/workspace_dispatch/r20_v2_r19_evidence_freeze_20260708.md`; `.json` |
| `R20-0-2` | R19 44 interesting-row audit | `reports/workspace_dispatch/etf_rotation_r20_audit_r19_interesting_44_20260708.md`; `.csv` |
| `R20-0-3` | A-share R18/R19 zero-wide postmortem | `reports/workspace_dispatch/a_share_r20_equity_zero_wide_postmortem_20260708.md`; `.json` |

Mandatory rule: no new search may run until these preconditions are complete.

## Lane 1 - Research-Friction Tooling

| Task | Name | Deliverables |
|---|---|---|
| `TOOL-R20-1` | Experiment store import | `reports/workspace_dispatch/tool_r20_experiment_store_import_20260708.md`; `reports/workspace_dispatch/tool_r20_experiment_store_schema_20260708.json` |
| `TOOL-R20-2` | Negative-result memory | `reports/workspace_dispatch/tool_r20_negative_result_memory_20260708.md`; `reports/workspace_dispatch/tool_r20_negative_result_memory.json`; `reports/workspace_dispatch/tool_r20_do_not_retry_20260708.md`; `reports/workspace_dispatch/tool_r20_retry_conditions_20260708.json` |
| `TOOL-R20-3` | Source health before fetch | `reports/workspace_dispatch/tool_r20_source_health_20260708.md`; `.json` |
| `TOOL-R20-4` | Unified research run command | `reports/workspace_dispatch/tool_r20_unified_research_run_command_20260708.md` |
| `TOOL-R20-5` | Preflight score before backtest | `reports/workspace_dispatch/tool_r20_preflight_score_20260708.md`; `reports/workspace_dispatch/tool_r20_preflight_score_schema_20260708.json` |
| `TOOL-R20-6` | Unified overclaim scan | `reports/workspace_dispatch/tool_r20_unified_overclaim_scan_20260708.md` |
| `TOOL-R20-7` | Artifact manifest compiler | `reports/workspace_dispatch/r20_unified_artifact_manifest_20260708.json` |
| `TOOL-R20-8` | Callback generator | `reports/workspace_dispatch/tool_r20_callback_generator_20260708.md` |
| `TOOL-R20-9` | Run budget and telemetry | `reports/workspace_dispatch/tool_r20_run_budget_telemetry_20260708.md`; `.json` |

Mandatory rules:

- Experiment store and failure memory must be generated before new search.
- Source health must run before fetch-heavy work.
- Every experiment must have a manifest and failure-memory check.

## Lane 2 - SimonLin Source Intake

| Task | Name | Deliverables |
|---|---|---|
| `SL-R20-1` | Repo capability inventory | `reports/workspace_dispatch/simonlin_r20_repo_capability_inventory_20260708.md`; `.json` |
| `SL-R20-2` | Source adapter priority matrix | `reports/workspace_dispatch/simonlin_r20_source_adapter_priority_matrix_20260708.md`; `.csv` |
| `SL-R20-3` | Source health smoke suite | `reports/workspace_dispatch/simonlin_r20_source_health_smoke_20260708.md`; `.json` |

Target repos:

- `simonlin1212/a-stock-data`
- `simonlin1212/global-stock-data`
- `simonlin1212/astock-peg`
- `simonlin1212/investment-news`
- `simonlin1212/globalpercent`
- `simonlin1212/TradingAgents-astock`
- `simonlin1212/Vibe-Research`

Stop on `LICENSE_REVIEW_REQUIRED`, `SOURCE_AUTH_REQUIRED`, or non-public/no-secret path.

## Lane 3 - ETF Main Strategy Lane

| Task | Name | Deliverables |
|---|---|---|
| `ETF-R20-1` | ETF amount/NAV/premium-discount first | `reports/workspace_dispatch/etf_rotation_r20_amount_nav_premium_intake_20260708.md`; `.csv` |
| `ETF-R20-2` | R19 interesting 44 focused robustness | `reports/workspace_dispatch/etf_rotation_r20_interesting_44_robustness_20260708.md`; `.csv` |
| `ETF-R20-3` | ETF universe v2 after source health | `reports/workspace_dispatch/etf_rotation_r20_universe_v2_20260708.md`; `.csv` |
| `ETF-R20-4` | ETF grid v3 delta search only | `reports/workspace_dispatch/etf_rotation_r20_grid_v3_delta_search_20260708.md`; `.csv` |
| `ETF-R20-5` | ETF macro/news/global regime overlay | `reports/workspace_dispatch/etf_rotation_r20_macro_news_regime_overlay_20260708.md`; `.csv` |
| `ETF-R20-6` | ETF hypothesis board v2 | `reports/workspace_dispatch/etf_rotation_r20_hypothesis_board_v2_20260708.md`; `.csv` |

Rules:

- Do not repeat R19 grid v2 without delta evidence.
- The 44 interesting rows must be audited.
- Amount/NAV/premium/liquidity gaps must be labelled when unavailable.
- Allowed labels only: `ETF_RESEARCH_INTERESTING_NEEDS_WIDE_RESEARCH`, `ETF_RESEARCH_WEAK`, `ETF_RESEARCH_UNSTABLE`, `ETF_RESEARCH_COST_LIMITED`, `ETF_RESEARCH_DATA_LIMITED`, `ETF_RESEARCH_DO_NOT_RETRY`.
- No daily signal push, recommendation, candidate, ticket, readiness, or product route.

## Lane 4 - A-share New-Feature Strategy Lane

| Task | Name | Deliverables |
|---|---|---|
| `A-R20-1` | PEG valuation factor intake | `reports/workspace_dispatch/a_share_r20_peg_valuation_factor_intake_20260708.md`; `.csv` |
| `A-R20-2` | Event, funds, hot-money feature intake | `reports/workspace_dispatch/a_share_r20_event_funds_hotmoney_feature_intake_20260708.md`; `.csv` |
| `A-R20-3` | `features_daily_v2_research` manifest | `reports/workspace_dispatch/a_share_r20_features_daily_v2_research_manifest_20260708.md`; `.json` |
| `A-R20-4` | A-share strategy search v2, new-feature-only | `reports/workspace_dispatch/a_share_r20_strategy_search_v2_new_feature_only_20260708.md`; `.csv` |

Rules:

- Retry only where new data, new feature, new regime, new universe, or new execution evidence justifies a retry.
- Do not retry R18/R19 failed combinations without new evidence.
- Do not select parameters from test results.

## Lane 5 - Global / US / HK Regime Lane

| Task | Name | Deliverables |
|---|---|---|
| `G-R20-1` | `global-stock-data` adapter smoke | `reports/workspace_dispatch/global_r20_global_stock_data_smoke_20260708.md`; `.json` |
| `G-R20-2` | Cross-market regime features | `reports/workspace_dispatch/global_r20_cross_market_regime_features_20260708.md`; `.csv` |

Smoke symbols include `SPY`, `QQQ`, `GLD`, `TLT`, `HYG`, `LQD`, `FXI`, `KWEB`, `AAPL`, `NVDA`, `MSFT`, `00700.HK`, and `9988.HK`.

## Lane 6 - News And Macro Lane

| Task | Name | Deliverables |
|---|---|---|
| `N-R20-1` | investment-news sector signal intake | `reports/workspace_dispatch/news_r20_investment_news_sector_signal_intake_20260708.md`; `.json` |
| `N-R20-2` | globalpercent macro probability intake | `reports/workspace_dispatch/macro_r20_globalpercent_probability_intake_20260708.md`; `.json` |
| `N-R20-3` | News/macro regime attribution | `reports/workspace_dispatch/news_macro_r20_regime_attribution_20260708.md`; `.csv` |

News and macro may be used only as attribution/regime evidence, never a direct trading signal.

## Lane 7 - TradingAgents Research Review Lane

| Task | Name | Deliverables |
|---|---|---|
| `TA-R20-1` | TradingAgents-Astock role template extraction only | `reports/workspace_dispatch/tradingagents_r20_role_template_extraction_20260708.md`; `.json` |
| `TA-R20-2` | Strategy hypothesis critique template | `reports/workspace_dispatch/tradingagents_r20_strategy_hypothesis_critique_template_20260708.md` |

Forbidden outputs: buy, hold, sell, final portfolio manager decision, investment plan, position sizing, candidate, or recommendation.

## Lane 8 - Combined Research Board

| Task | Name | Deliverables |
|---|---|---|
| `STRAT-R20-1` | Combined research board | `reports/workspace_dispatch/strategy_r20_combined_research_board_20260708.md`; `.csv` |
| `STRAT-R20-2` | Conditional wide research probe or skip | `reports/workspace_dispatch/strategy_r20_wide_research_probe_or_skip_20260708.md`; `.csv` |

Allowed labels: `RESEARCH_INTERESTING`, `RESEARCH_WEAK`, `RESEARCH_UNSTABLE`, `RESEARCH_COST_LIMITED`, `RESEARCH_DATA_LIMITED`, `RESEARCH_RETRY_ALLOWED`, `RESEARCH_DO_NOT_RETRY`.

If no strategy passes validation, walk-forward, bootstrap/permutation, cost, trade-count, data evidence, no-future, and failure-memory checks, output `NO_R20_WIDE_RESEARCH_PROBE_ELIGIBLE`.

## Lane 9 - market_data Support

| Task | Name | Deliverables |
|---|---|---|
| `MD-R20-1` | SimonLin research source contract | `reports/codex_dev/simonlin_r20_research_source_contract.md`; `.json` |
| `MD-R20-2` | R20 overclaim regression | `tests/test_simonlin_r20_overclaim_regression.py` |

No active registry/readiness/product-route change, no market_data activation, and no raw-data import into active route.

## Lane 10 - strategy_work Support

| Task | Name | Deliverables |
|---|---|---|
| `SW-R20-1` | Master strategy research memo | `reports/planning/windows_wsl2_simonlin_strategy_superbatch_r20_master_memo_20260708.md` |
| `SW-R20-2` | Final sync after source callbacks | `reports/planning/windows_wsl2_simonlin_strategy_superbatch_r20_final_sync_20260708.md` |

Final sync must not be created before accepted source callbacks.

## quant-proj

| Task | Name | Deliverables |
|---|---|---|
| `QP-R20-1` | Intake and dispatch | `reports/workspace_dispatch/windows_wsl2_simonlin_strategy_superbatch_r20_20260708_intake.md`; this task packet; dispatch summary |
| `QP-R20-2` | Result summary and closeout | `reports/workspace_dispatch/windows_wsl2_simonlin_strategy_superbatch_r20_20260708_result_summary.md`; `reports/workspace_dispatch/windows_wsl2_simonlin_strategy_superbatch_r20_20260708_closeout.md` |

## Validation

Required where applicable:

- JSON parse PASS.
- `git diff --check` PASS.
- Focused pytest PASS if code/tests changed.
- `agent_safety_check.py` PASS where applicable.
- Forbidden overclaim scan PASS.
- Source health generated before fetch-heavy work.
- Manifest/hash evidence for fetched/written artifacts.
- Experiment store import PASS before new strategy search.
- Failure memory generated before new strategy search.
- Callback envelope generated.

Additional A_Share_Monitor validation:

- No repeated ETF grid v2 without delta evidence.
- No full-frame wide3068.
- No daily signal push.
- No strategy candidate promotion.
- No recommendation wording.
- No unapproved DB/cache write outside fastpath/source-local research scope.

Additional market_data validation:

- No active registry change.
- No readiness change.
- No product-route activation.
- No market_data activation.
- No raw-data import into active route.
- No adapter/schema production change.

Additional strategy_work validation:

- No buy/hold/sell.
- No actionable ranking.
- No candidate promotion.
- No recommendation/advice.
- No placeholder final sync.

## Callback Envelope

```text
CALLBACK_ENVELOPE:
BATCH: WINDOWS_WSL2_SIMONLIN_STRATEGY_SUPERBATCH_R20_V2_20260708
TARGET_REPO:
BRANCH:
COMMIT:
TREE:
STATUS:
TASKS_COMPLETED:
ARTIFACTS:
VALIDATION:
SOURCE_HEALTH:
EXPERIMENT_STORE_STATUS:
FAILURE_MEMORY_STATUS:
R19_EVIDENCE_FREEZE_STATUS:
R19_INTERESTING_44_AUDIT_STATUS:
DATA_STATUS:
STRATEGY_RESULTS:
ETF_RESULTS:
A_SHARE_RESULTS:
GLOBAL_RESULTS:
NEWS_MACRO_RESULTS:
WIDE_RESEARCH_PROBE_ELIGIBLE_COUNT:
STRATEGY_CANDIDATE_AVAILABLE:
BOUNDARY_RESULT:
EXTERNAL_AUDIT_TRIGGER_OPEN:
FIXES_REQUIRED:
NEXT_SOURCE_ACTION:
```
