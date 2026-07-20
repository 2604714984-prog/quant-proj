# Manager task — PR #107 audit follow-up and broad US qualification program

Date: 2026-07-20  
Repository: `2604714984-prog/quant-proj`  
Audit target: PR #107 exact HEAD `9f9f0b443260f5d9509971099e73e6d88d272890`  
Review ID: `4732598307`

## Controlling verdict

```text
REWORK_REQUIRED_NARROW_SEMANTIC_CORRECTION
OUTCOME_BLIND_BOUNDARIES_ACCEPTED
NO_MECHANISM_READY_ACCEPTED
DO_NOT_MERGE_CURRENT_HEAD
```

PR #107 correctly keeps outcomes, prices, NAV, Validation, Holdout, database writes, candidate status, Shadow, Paper and live paths closed. Its current five priorities are provisional review items only.

The current HEAD cannot become the canonical atlas until the source, deduplication and scoring findings in the exact-head review are repaired.

## Phase 1 — dispatch one atlas-rework conversation

Send:

`reports/agent_handoff/pr107_atlas_semantic_rework_task_20260720.md`

Allowed scope:

- modify only the two JSON files already changed by PR #107;
- no new framework, runner, provider or database code;
- no price, return, NAV, Sharpe, Validation or Holdout access;
- no strategy implementation;
- keep the PR Draft;
- request a delta exact-head external review after CI.

Do not start a formal result lane before the corrected atlas is externally accepted.

## Phase 2 — parallel read-only qualification scouts

The following scouts may operate in parallel after Phase 1 is dispatched. They are not formal strategy families and may not open outcomes.

1. Daily ETF and broad-market mechanisms  
   `reports/agent_handoff/us_daily_market_mechanism_qualification_scout_20260720.md`

2. Survivor-aware stock data and price/liquidity mechanisms  
   `reports/agent_handoff/us_survivor_aware_stock_qualification_scout_20260720.md`

3. SEC filing, corporate-event and fundamental mechanisms  
   `reports/agent_handoff/us_sec_event_fundamental_qualification_scout_20260720.md`

4. High-cost intraday, options and text availability  
   `reports/agent_handoff/us_high_cost_data_availability_scout_20260720.md`

## Global control boundary

```text
FORMAL_CODE_WRITING_CONCURRENCY=0_UNTIL_PR107_DELTA_ACCEPTED
FORMAL_RESULT_CONCURRENCY=0
READ_ONLY_SCOUT_CONCURRENCY=4
PRICE_RETURN_ACCESS=false
VALIDATION_HOLDOUT_ACCESS=false
DATABASE_WRITE=false
PROVIDER_PURCHASE=false
STRATEGY_CANDIDATE_AVAILABLE=false
SHADOW=false
PAPER=false
LIVE=false
QLIB=false
RD_AGENT=false
```

A Scout may inspect public documentation, repository contracts and small official metadata samples. It may not retrieve or calculate historical strategy returns. Any local data inspection requires a fresh Manager dispatch and must remain schema/identity/coverage only.

## Broad search objective

The existing atlas is wide enough for the current cycle. Do not target a larger card count merely for volume.

The next objective is to turn the 63-card pool into evidence-based readiness cohorts:

```text
A. locally or cheaply qualifiable daily market mechanisms
B. survivor-aware stock mechanisms
C. SEC event/fundamental mechanisms
D. high-cost deferred mechanisms
```

Each Scout must return:

- exact mechanism IDs reviewed;
- source classification;
- minimum data contract;
- causal timing contract;
- expected sample size without reading returns;
- execution and transaction-cost risk;
- duplicate/failure-memory screen;
- `READY_FOR_PREREGISTRATION`, `BOUNDED_INPUT_TASK`, `PARK` or `CLOSE`;
- one recommended next mechanism at most.

A recommendation is not authorization.

## Formal mechanism selection after Scout completion

After the corrected atlas is accepted and Scout results are available, choose exactly one mechanism using this order:

1. all required input identities are already qualified or require one bounded task;
2. source class is `EXACT_MECHANISM_SOURCE`, or a clearly disclosed `ECONOMIC_PRIOR_ONLY` with lower score;
3. no overlap with a consumed lineage;
4. executable with USD 40,000, no leverage and conservative costs;
5. prospective observations can be collected after the frozen cutoff;
6. implementation remains narrow.

Do not select by score alone. Scores are navigation aids, not empirical evidence.

## Next formal deliverable

The first post-atlas formal PR must contain one of:

```text
A. frozen preregistration plus qualified immutable input identity;
B. terminal bounded input blocker;
C. after separate authorization, one numerical Development result.
```

It must not be another roadmap-only or shortlist-only PR.

## Program-level historical boundary

The 2010–2017 and 2018–2026-06 periods are consumed at program level. A later result on those dates is only:

```text
RETROSPECTIVE_SECONDARY_ONLY
```

A retrospective PASS cannot by itself create a strategy candidate. The only route to new independent evidence is zero-capital prospective Shadow on observations after the frozen historical cutoff, following exact-head external review.

## Prohibited actions

- merge PR #107 at its current HEAD;
- implement any of the five provisional finalists;
- restore exact-time M3;
- treat pre-FOMC, announcement reaction and next-session response as one mechanism;
- add another SPY/QQQ/GLD allocation variant;
- create a new research platform, registry, agent framework or backtest engine;
- enable Qlib, RD-Agent, Paper, broker or live integration;
- use card scores as probability of strategy success.

## Required Manager closeout

Return a short callback containing:

```text
PR107_REWORK_HEAD=
PR107_DELTA_REVIEW_STATUS=
DAILY_SCOUT_STATUS=
STOCK_SCOUT_STATUS=
SEC_SCOUT_STATUS=
HIGH_COST_SCOUT_STATUS=
FORMAL_MECHANISM_SELECTED=<none or one ID>
OUTCOME_ACCESS=false
STRATEGY_CANDIDATE_AVAILABLE=false
```
