```markdown
# Reasonix-Strategy Research Draft

## Status
RESEARCH_DRAFT

## Scope
DATA_STRATEGY_BATCH_R6_20260705 — research-only investigation across A‑share and US‑equity candidate universes, covering robustness diagnostics, risk‑filter design, candidate quality bucketing, bootstrap usability exploration, and a research‑memo synchronisation task. No production config promotion, no recommendation, no live trading.

## Hypotheses

### A‑R6‑001 (conservative momentum + liquidity + affordability, 6 kept A‑share candidates)
1. The six retained A‑share candidates exhibit non‑trivial sensitivity to the momentum lookback window and the liquidity definition (daily turnover vs. free‑float‑adjusted turnover).  
2. Affordability (price/median price of peer group) correlates with liquidity constraints in small‑cap names, potentially creating a hidden leverage when both are used as independent filters.  
3. A conservative (longer‑lookback, smoothed) momentum definition reduces turnover and improves out‑of‑sample stability without destroying the core signal.

### A‑R6‑002 (low‑vol as risk filter with momentum floor)
1. A minimum momentum condition (e.g. 12‑month excess return > 0 or positive 6‑month SMA spread) combined with low‑vol selection will reduce drawdowns in sideways A‑share markets compared to a pure low‑vol portfolio.  
2. The interaction between low‑vol and momentum is regime‑dependent; the momentum floor may become an unintentional sector‑concentration driver.

### US‑R6‑001 (US‑239 candidate quality buckets by signal overlap and metadata limits)
1. Signal overlap (correlation of raw factor ranks) can separate candidates into “diversified” and “redundant” buckets, helping avoid double‑counting.  
2. Metadata limits (e.g. missing earnings dates, thin ADR liquidity, recent IPO < 12 months) act as stronger disqualifiers than marginal factor scores; bucketing by metadata quality may reveal a cluster of candidates that are consistently uninvestable.  
3. A two‑dimensional bucketing (signal‑overlap × metadata‑completeness) yields a more actionable quality classification than a single composite score.

### US‑R6‑003 (feedback bootstrap research‑only usability)
1. A bootstrap‑based feedback mechanism (e.g. sampling historical strategy variants and re‑estimating stability) can flag overfit‑sensitive parameters without using the test split.  
2. The bootstrap procedure, constrained to research‑only evaluation, can be packaged as a reusable `research/bootstrap_feedback` module that emits a stability report but never drives automatic selection.

### SW‑R6‑001 (research memo sync)
1. Research memos scattered across task packets, Reasonix outputs, and Codex‑Dev notes contain duplicative or outdated hypotheses; a single synced memo per batch will reduce misalignment.  
2. A structured `research_memo.md` template (scope, hypotheses, open questions, decisions) can be effectively maintained through Reasonix‑Strategy drafts and periodic review.

## Evidence Gaps

- **A‑R6‑001**: Historical sensitivity of the six candidates to varying momentum lookbacks (3, 6, 9, 12 months) and liquidity thresholds has not been systematically quantified. No holdout‑period validation exists.
- **A‑R6‑002**: The interaction between a momentum floor and the low‑vol selection has not been evaluated on A‑share‑specific data (e.g. the 2015‑2016 crash recovery, the 2021‑2022 regulatory sell‑off).
- **US‑R6‑001**: No explicit map of signal‑overlap correlation matrix across the US‑239 universe. Metadata completeness scores are not yet defined or uniformly recorded.
- **US‑R6‑003**: Bootstrap methods have not been previously implemented in this workspace; potential computational cost and appropriate block‑length choices for weekly rebalancing are unknown.
- **SW‑R6‑001**: Current research memos are fragmented; a survey of existing memo artefacts has not been performed.

## Draft Config / Experiment Plan

- **A‑R6‑001**  
  *Experiment*: Run a sensitivity analysis on the six candidates: vary momentum lookback (3/6/9/12 months), liquidity threshold (percentile 20‑40) and affordability proxy (price rank).  
  *Output*: Heatmap of hit rates, turnover, and drawdowns on the validation (pre‑holdout) window.  
  *Deliverable*: A diagnostic report, not a new config.

- **A‑R6‑002**  
  *Experiment*: Construct two simulated portfolios on A‑share universe (pure low‑vol vs. low‑vol + momentum floor). Compare risk metrics (max drawdown, volatility, Sharpe) across regime segments (bull/bear/sideways as defined by simple SH300 moving‑average regime).  
  *Output*: Side‑by‑side performance table and commentary on regime dependence.

- **US‑R6‑001**  
  *Experiment*: Compute pairwise rank‑IC correlation between all factors for the US‑239 candidates over a trailing 24 months. Build a “signal overlap” matrix and cluster candidates. Define metadata completeness (fields: earnings date freshness, ADR flag, IPO date, daily volume consistency) and assign a 0‑1 quality score.  
  *Output*: A 2‑D bucketing grid (overlap cluster × metadata score) with candidate counts per bucket.

- **US‑R6‑003**  
  *Experiment*: Implement a time‑series bootstrap (block length ~4 weeks) that resamples historical returns; for each resample, recompute strategy rank and record parameter‑stability metrics. Compare variability across resamples.  
  *Output*: A stability report (coefficient of variation of key metrics); no automated selection.  
  *Constraint*: Must remain `research/` only; no link to live signal generation.

- **SW‑R6‑001**  
  *Process*: Audit current research memos in `strategy_work/` and `tasks/backlog/...`, then create a consolidated `research/memos/DATA_STRATEGY_BATCH_R6_20260705_memo.md`. The memo must include a status table for every task, with hypothesis, evidence gap, open questions, and a decision‑pending flag.  
  *Update*: Reasonix‑Strategy will push a draft; human gate and Codex‑Dev will review before finalisation.

## Overfit And Data Risks

- **A‑R6‑001**: Only six candidates; any parameter optimisation will be fragile. Any discovered “optimal” lookback is likely noise unless confirmed on a broader A‑share universe.
- **A‑R6‑002**: Regime segmentation may itself be overfit (choice of lookback for regime identifier). The momentum floor may reduce drawdowns in the sample but amplify tail risk in an unseen liquidity‑crunch regime.
- **US‑R6‑001**: Bucketing based on a 24‑month correlation could be unstable; a single market regime (2023‑2024) dominates the window. Metadata quality scores are unaudited and may embed survivorship bias.
- **US‑R6‑003**: Bootstrap stationarity assumptions are questionable for US equities with structural breaks (e.g. Fed pivot, COVID). Block‑length and resampling method can heavily influence the conclusion.
- **SW‑R6‑001**: Memo synchronisation alone does not improve research quality; a sync that merely compiles outdated ideas could reinforce stale hypotheses and obscure fresh evidence.

## Required Human-Gate Decisions

1. Approval to run the sensitivity / bootstrap experiments on the validation split (not test split) and store intermediate diagnostics under `strategy_work/` or a designated `research/experiments/` path.
2. Approval of the metadata completeness fields proposed for US‑R6‑001 and whether any additional source (e.g. Refinitiv fields) should be included.
3. Decision on whether the consolidated research memo (SW‑R6‑001) should be treated as the authoritative batch hypothesis record, and who must sign off on changes.
4. Explicit confirmation that none of the R6 tasks should, now or later, evolve into recommendation‑generating tasks without a new approval gate.

## Required Codex-Dev Work

1. **A‑R6‑001 & A‑R6‑002**: Implement research‑only scripts to load cleaned A‑share daily data (from DS‑curated sources), compute variant factors, and produce comparison tables/plots. No updates to `A_Share_Monitor` config.
2. **US‑R6‑001**: Build the signal‑overlap computation and the metadata quality scoring pipeline; output a CSV bucketing report. Integrate only under `research/us_candidates/`.
3. **US‑R6‑003**: Develop a time‑series bootstrap utility in the research toolbox, with a clear warning header that it must not feed into live parameter selection. Provide a stability report output.
4. **SW‑R6‑001**: Produce a consolidated memo stub, pull in existing artefacts, and mark any missing or conflicting items for human review. Maintain the memo in the workspace-research area.
5. All work must remain behind research‑only gates; no source‑repo strategy configs may be altered without a separate task and acceptance.

## Explicit Non-Authorization
This document is a research draft only. It does not constitute buy/sell advice, does not authorise recommendations, broker API usage, order routing, order submission, automatic execution, paper trading, live trading, or any trading‑adjacent activity. It does not promote any configuration into `A_Share_Monitor` or `US_Stock_Monitor` and does not create `eligibility_candidate` or product‑readiness claims. No recommendation tickets are to be emitted.
```

— turns:1 cache:87.7% cost:$0.002463 save-vs-claude:94.7%

transcript: reports/workspace_dispatch/reasonix_strategy_data_strategy_batch_r6_retry_20260705.jsonl
  → npx reasonix replay reports/workspace_dispatch/reasonix_strategy_data_strategy_batch_r6_retry_20260705.jsonl
