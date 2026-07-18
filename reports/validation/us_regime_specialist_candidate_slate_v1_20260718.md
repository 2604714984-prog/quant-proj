# US Regime Specialist Candidate Slate V1

Date: 2026-07-18
Research ID: `US_REGIME_SPECIALIST_SCOUT_PHASE0_20260718`
Market / phase / status: `US` / `OUTCOME_FREE_DISCOVERY` / `blocked-on-data`
Branch / base / tree: `codex/us-regime-specialist-scout-phase0-20260718` / `1be178afc496f5e2abece8c71014b9d6cb82453b` / `960686e0c6ed9a63187e71f44792cfe349a479fd`

## Boundary and evidence snapshot

```text
OUTCOME_FREE=true
STRATEGY_RETURN_QUERY=false
STRATEGY_ADAPTER=false
DATABASE_WRITE=false
MARKET_DATA_PROVIDER_CALL=false
STRATEGY_CANDIDATE_AVAILABLE=false
```

No strategy-result/replication JSON, legacy strategy output, or US31/US36/US41/US46 output was opened. No closed-family parameter, universe, code, or headline was used. The sole local result artifact inspected was the permitted source-qualification file `research/reports/p3_spy_official_source_qualification_v1_result.json` (SHA256 `f809e2a004e9c4344d7b0ab79fd0ebba5377bae67eed50d117302f09399d061b`). It establishes partial SPY qualification: historical raw OHLC is entitlement-blocked; the official calendar covers only 2022-2025; split/lifecycle identity is incomplete; and distributions have retrospective dates/amounts but incomplete historical `announced_at` and revision lineage.

Read-only aggregate inspection of `quant_research.duckdb` (4,671,156,224 bytes) found:

- canonical `main.us_trade_calendar`: 0 rows;
- Nasdaq metadata: one current snapshot, 270 active symbols (240 equities and 30 ETFs), all `available_at` null and 0 canonical-eligible;
- Nasdaq bars: 559,959 rows / 270 symbols / 2018-01-02 to 2026-07-06, one snapshot, all `available_at` null, 0 canonical-eligible, raw-close only, no split/distribution fields;
- no VIX-like identity in `main.us_symbol_master` or Nasdaq metadata;
- corporate actions: 224 rows for only 2 symbols, with every `available_at` and `declaration_date` null;
- no qualified US PIT-fundamentals or shares-outstanding table in the 40-table catalog.

These are data-readiness facts, not strategy evidence. No price value, identifier ranking, strategy return, NAV, Sharpe ratio, or performance gate was queried. Scores below use `economic_prior/data_readiness/USD_account_feasibility/independence_from_closed_strategies/implementation_simplicity/turnover_and_cost_risk`, maxima `3/3/2/2/1/1`.

## Card 1 — Trend-up absolute trend plus participation

- `candidate_id`: `USRS-TREND-UP-ABS-PARTICIPATION-V1`
- `primary_state`: `TREND_UP`
- `economic_mechanism`: Positive absolute trend may persist among liquid US equities when the independent Observer confirms broad participation and low stress. Daniel and Moskowitz document strong average momentum returns but infrequent crashes after market declines, at high volatility, and during rebounds. That supports avoiding panic/rebound states; it does not validate this breadth gate or long-only basket.
- `activation_and_exit`: Activate only on a causally available Observer `TREND_UP`; exit on the first transition away; cash otherwise. No state or strategy threshold is defined here.
- `primary_sources`: Daniel and Moskowitz, [Momentum Crashes](https://www.nber.org/papers/w20439), NBER Working Paper 20439 / JFE 122(2).
- `required_data`: PIT-eligible US equity universe or frozen non-index listing rule; separate raw and adjusted OHLC identities; splits, cash distributions, delistings and terminal actions; `available_at` or retrospective-only label; volume/amount; qualified SPY trend/drawdown, breadth and low-stress Observer inputs; USD capital, whole-share lots, date-aware commission/spread/slippage/settlement. PIT fundamentals/shares are not required unless later added under new scope.
- `current_data_status`: `BLOCKED` by partial SPY qualification, empty canonical calendar, absent VIX/VIX3M, and a non-PIT/current-snapshot/corporate-action-incomplete equity panel.
- `survivorship_and_membership_risk`: `HARD_BLOCK`; the active-only 270-symbol snapshot cannot establish historical eligibility, delistings, or terminal actions.
- `capital_feasibility`: Intended 5-10 long positions. Whole shares are the conservative first screen; USD funding, FX, cash buffer and broker lots remain unfrozen. Fractional shares are planning-only and cannot rescue failure.
- `expected_turnover`: Weekly or monthly; exact lookback, rebalance day and holding rule remain unfrozen.
- `execution_risk`: Medium; next-open timing, gaps, state lag and corporate actions require qualified identities.
- `closed-strategy_independence`: New causal state, universe, formula and parameters; conceptual momentum overlap is acknowledged, but this is not a relabel or rescue.
- `score`: `8/12 = 3/0/1/2/1/1`
- `recommended_status`: `BLOCKED`

## Card 2 — Stress quality/low-risk long-only

- `candidate_id`: `USRS-STRESS-QUALITY-LOWRISK-LONGONLY-V1`
- `primary_state`: `STRESS`
- `economic_mechanism`: Revision-safe quality and ex-ante low-risk characteristics may preserve capital better than broad exposure during frozen stress. QMJ defines quality through safety, profitability, growth and management/payout; BAB links low-beta premia to leverage constraints. This unlevered long-only translation is new, not a replication of either long-short factor.
- `activation_and_exit`: Activate only on causally available Observer `STRESS`; exit on the first non-`STRESS` state; cash otherwise.
- `primary_sources`: Asness, Frazzini and Pedersen, [Quality Minus Junk](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2312432); Frazzini and Pedersen, [Betting Against Beta](https://www.sciencedirect.com/science/article/pii/S0304405X13002675), JFE 111(1).
- `required_data`: Card 1 identities plus PIT filing acceptance/`available_at`, revision lineage and units for profitability, growth, safety/leverage and payout; PIT shares and market cap; corporate-action-safe beta inputs; qualified stress inputs; USD whole-share capital and date-aware costs/settlement.
- `current_data_status`: `BLOCKED`; no qualified US PIT fundamentals/shares exist, and the panel, calendar, market-state inputs and lifecycle chain also fail readiness.
- `survivorship_and_membership_risk`: `HARD_BLOCK`; active-only symbols plus retrospectively revised fundamentals would create survivor and accounting look-ahead bias.
- `capital_feasibility`: Intended 5-10 unlevered long positions; whole-share screen mandatory, fractions planning-only, USD/broker capabilities unfrozen.
- `expected_turnover`: Monthly or after causally available filing updates; never before filing acceptance/availability.
- `execution_risk`: Medium-high. QMJ evidence is a composite long-short factor; BAB explicitly leverages low-beta and shorts high-beta. Removing leverage/shorting changes exposures and can import size, sector, profitability or investment tilts, so the long-only version has no direct published-factor entitlement.
- `closed-strategy_independence`: New US PIT lineage and state-frozen translation; no A-share defensive-low-volatility or rejected US parameter/result is inherited.
- `score`: `6/12 = 2/0/1/2/0/1`
- `recommended_status`: `BLOCKED`

## Card 3 — Stress-liquidity short-term residual reversal

- `candidate_id`: `USRS-STRESS-RESIDUAL-REVERSAL-V1`
- `primary_state`: `STRESS`
- `economic_mechanism`: Short-term market-residual losers among highly liquid equities may earn compensation for supplying liquidity when constrained intermediaries withdraw. Nagel interprets short-term reversal as a liquidity-provision proxy and links its expected return to VIX during turmoil; that does not establish a low-cost next-open long-only translation.
- `activation_and_exit`: Activate only in Observer `STRESS`; enter after a fully observed residual window at the next executable open; exit after a preregistered 1-5-session horizon or state exit; cash otherwise. No exact window is selected here.
- `primary_sources`: Nagel, [Evaporating Liquidity](https://academic.oup.com/rfs/article-abstract/25/7/2005/1602153), RFS 25(7).
- `required_data`: Survivor-complete PIT universe; raw/adjusted OHLC; splits, distributions, delistings and terminal actions; `available_at`; volume/dollar amount; qualified market-return and VIX state inputs; next-open quotes or conservative spread evidence; commissions/spread/slippage/settlement/lots/whole-share cash; 5-10 positions and overlap accounting.
- `current_data_status`: `FAILED_PHASE0_FEASIBILITY`; current bars are non-canonical raw-close without corporate actions or `available_at`, VIX/calendar are absent, and no spread/quote/conservative next-open evidence exists.
- `survivorship_and_membership_risk`: `HARD_BLOCK`; active-only membership and missing terminal actions are most damaging in the loser tail.
- `capital_feasibility`: Only planning-feasible for 5-10 whole-share positions; fractions planning-only; high churn needs explicit cash-rounding preflight.
- `expected_turnover`: Very high; daily ranking and intended 1-5-session holding.
- `execution_risk`: Very high; spread, gap, queue, stale-price and cost errors can dominate. The task's fail-before-implementation rule is triggered.
- `closed-strategy_independence`: New market-residual, state-frozen US hypothesis; no liquidity-shock-reversal output, parameter or code is reused.
- `score`: `6/12 = 3/0/1/2/0/0`
- `recommended_status`: `REJECT`

## Card 4 — Breadth recovery after drawdown

- `candidate_id`: `USRS-RECOVERY-BREADTH-BROAD-EXPOSURE-V1`
- `primary_state`: `RECOVERY_TAG`
- `economic_mechanism`: Broad participation recovery after a causal drawdown may support temporary re-risking. Momentum Crashes makes panic-to-rebound transitions economically relevant, but it is only adjacent evidence; the frozen source set has no direct primary prior for breadth-recovery timing.
- `activation_and_exit`: Activate only on Observer `RECOVERY_TAG`; exit on tag expiry or transition to `STRESS`/`UNKNOWN`; cash otherwise. Comparator is broad exposure or cash; no stock selection without an independent prior.
- `primary_sources`: Daniel and Moskowitz, [Momentum Crashes](https://www.nber.org/papers/w20439), used only as adjacent recovery-risk evidence.
- `required_data`: Qualified raw/adjusted broad-market or sector ETF OHLC; splits/distributions/lifecycle; official calendar; `available_at`; volume/amount; qualified drawdown/breadth Observer inputs; USD whole-share capital and date-aware costs/settlement. A stock version additionally needs a survivor-complete PIT universe and is outside this card.
- `current_data_status`: `BLOCKED`; SPY raw OHLC, lifecycle/PIT distributions and calendar are incomplete, breadth cannot use the current-snapshot panel, and the independent Observer has not supplied `RECOVERY_TAG`.
- `survivorship_and_membership_risk`: Broad exposure reduces stock-selection bias but does not cure retrospective ETF distributions, incomplete lifecycle, or biased breadth membership.
- `capital_feasibility`: One broad ETF or separately justified small sector basket; whole-share planning is simple, but USD/FX/broker rules remain unfrozen and fractions remain planning-only.
- `expected_turnover`: Episodic and expected below weekly; hold only for the frozen tag lifetime.
- `execution_risk`: Medium; transition lag, rebound gaps, stale breadth and distributions remain material.
- `closed-strategy_independence`: Broad-exposure comparator only; no rejected momentum/ETF formula, threshold, universe or result is inherited.
- `score`: `6/12 = 1/0/1/2/1/1`
- `recommended_status`: `BLOCKED`

## Recommended first family and stop condition

Recommend `USRS-TREND-UP-ABS-PARTICIPATION-V1` for user selection because it has the strongest permitted prior, simplest long-only shape, lower turnover, and a clean new-lineage requirement. Its score is exactly 8 but its status remains `BLOCKED`: this recommends a data-qualification/preregistration lane, not a task, adapter, backtest or outcome query.

Before formal work, the selected family needs an accepted independent Observer state contract; survivor-complete PIT equity identity or frozen non-index universe; canonical raw/adjusted prices with complete lifecycle identities; accepted calendar/state inputs; and a whole-share USD cost/settlement/capital preflight. Otherwise stop `US_STATE_OBSERVER_INPUT_BLOCKED` / `blocked-on-data` without consuming an outcome.

```text
CANDIDATE_COUNT=4
PROPOSED_COUNT=0
BLOCKED_COUNT=3
REJECTED_COUNT=1
TOP_CANDIDATE_ID=USRS-TREND-UP-ABS-PARTICIPATION-V1
TOP_CANDIDATE_STATE=TREND_UP
TOP_CANDIDATE_SCORE=8
STRATEGY_CANDIDATE_AVAILABLE=false
NEXT_ACTION=USER_SELECTS_FIRST_US_FAMILY
```
