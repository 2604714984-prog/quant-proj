# PR #105 exact-head audit and broad result-oriented research program

Date: 2026-07-20  
Repository: `2604714984-prog/quant-proj`  
Review target: PR #105  
Reviewed HEAD: `85e2f1e803d10067f63cb6edce83911d1922a6b2`  
GitHub review ID: `4731989819`

## 1. Verdict

```text
VERDICT=
ACCEPT_TRUTHFUL_OUTCOME_FREE_INPUT_BLOCKER_EVIDENCE
CLOSE_WITHOUT_MERGE
BOUNDED_CONTINUATION_PERMITTED
```

The R3 artifacts honestly show:

```text
PARTIAL_OFFICIAL_IDENTITY_MATERIALIZATION_INPUT_BLOCKED_NO_OUTCOME
lane_b_input_qualified=false
price_or_return_access_authorized=false
development_atlas_execution_authorized=false
strategy_candidate_available=false
```

The exact evidence is accepted. The exact PR should close without merge.

## 2. Accepted facts

The following facts are accepted at the reviewed HEAD:

- 297 official objects were materialized and verified outside Git.
- The materialized bundle contains 98 FOMC statements, 98 minutes and 98 transcripts.
- The frozen FOMC denominator remains 98 scheduled Statement links; 10 Conference Call links remain excluded.
- Accepted record-level actual FOMC publication timestamps remain `0/98`; four same-day page-update timestamps were preserved only as non-accepted observations.
- CPI and Employment Situation routes are still nonterminal and materializable, but the current host returned HTTP 403 and no M4/M5 release identity was accepted.
- M6 and M7 remain 128 and 64 rule-derived candidates, with no complete versioned historical rule identity.
- The XNYS candidate contains 4,030 sessions, 41 early closes and seven ad-hoc closures; official record-level calendar identity remains incomplete.
- No price, return, Development, Validation, Holdout, Shadow, Paper, broker or live path was opened.
- Exact-head CI and the independent acceptance passed.

## 3. Why the exact PR should not merge

PR #105 adds eight files and about 19,971 lines, including:

- one one-off acquisition/materialization script;
- six large record-level qualification mirrors;
- one focused test file.

No mechanism is qualified and no authorized runtime consumer exists. The 131.7 MB source bundle also remains outside Git, so merging the large summaries does not make the evidence independently self-contained.

The PR, exact commit, review and hashes preserve the evidence without adding a large dead maintenance surface to the lightweight mainline.

```text
EVIDENCE_ACCEPTED=true
MERGE_MAINLINE=false
R3_RERUN=false
R3_REWRITE=false
```

## 4. Semantic findings that control the next phase

### 4.1 FOMC exact-time acceptance is unreachable in the R3 parser

`statement_evidence()` emits date-only or same-day-last-update classifications. `materialize_fomc()` accepts a timestamp only when the classification is `ACTUAL_EXPLICIT_OFFICIAL`, which the parser never emits.

Therefore:

```text
accepted_actual_timestamp_count=0
```

is a truthful result of the frozen R3 parser, but it is not proof that all possible official record-level evidence is absent.

Do not modify R3. Run one bounded, outcome-free final search in the already materialized official bytes and directly linked official Federal Reserve records. If the frozen 94-of-98 threshold remains impossible, close exact-time M3 as data unavailable.

### 4.2 Daily mechanisms should not inherit intraday identity requirements by default

The frozen exact-time M3 remains blocked. A later date-anchored daily mechanism may be created only under a new identity.

Potential new daily identity minima, subject to a separate outcome-blind review:

```text
M3-DATE-V2:
  official Statement release date
  next accepted session open
  same-session close

M4/M5-DATE-V2:
  official actual release date
  no intraday timestamp needed because the window ends on the prior session

M6/M7-RULE-V2:
  authoritative effective rule spans
  explicit holiday and exceptional-date evidence
  no requirement for one separate official document per ordinary event date
```

These are new contracts, not repairs or reruns of the frozen PR #97 mechanisms.

### 4.3 Daily calendar qualification must remain proportionate

For daily mechanisms, the controlling facts are:

- exact accepted session dates;
- official evidence for ad-hoc full closures;
- explicit reconciliation of every observed-date difference;
- actual daily open/close endpoints from the accepted price snapshot.

A complete official proof of all historical early-close clock times may remain diagnostic for daily-bar mechanisms unless the mechanism depends on the exact clock time. Intraday lanes retain the stricter requirement.

### 4.4 Mechanism-level independence must remain controlling

The merged Atlas definition permits partial results and independent mechanism qualification. A future task must not use an aggregate field such as:

```text
lane_b_input_qualified=false
```

as an all-or-nothing gate after an individual mechanism independently qualifies.

## 5. Immediate disposition

Manager shall:

```text
1. Close PR #105 without merge.
2. Record R3 as accepted outcome-free input-blocker evidence.
3. Preserve all raw evidence and hashes outside Git.
4. Run one bounded final identity-resolution task.
5. Do not access price or return data during identity resolution.
6. Do not dispatch another formal code/result mechanism concurrently.
7. Permit parallel read-only scouts that never access outcomes.
```

## 6. Broad-search operating model

The project now uses a two-speed model.

### 6.1 Wide discovery plane

This plane may run many read-only scouts in parallel.

Allowed:

- original-paper search;
- official-data route search;
- field and coverage checks;
- sample-size estimates;
- execution and cost analysis;
- duplicate and failure-memory screening;
- mechanism cards without returns.

Forbidden:

- price or return queries;
- Sharpe, CAGR, NAV or rankings;
- parameter grids;
- strategy implementation;
- choosing a mechanism based on historical performance;
- database writes;
- candidate or trading promotion.

Target:

```text
50-100 broad mechanism cards
10 working days
one shared outcome-free ledger
```

### 6.2 Narrow evidence plane

Only one code-writing/result mechanism may be active.

```text
one economic mechanism
one primary variant
at most one preregistered robustness variant
one Development result
one terminal PASS / FAIL / INPUT_BLOCKED
```

The 2010-2017 and 2018-2026-06 periods are already consumed at program level. A later historical PASS is only `RETROSPECTIVE_SECONDARY_ONLY` and may seek zero-capital prospective Shadow only after exact-head review.

## 7. Search universe

### 7.1 Daily ETF and broad-market mechanisms

Search cards should cover, without opening outcomes:

- date-anchored scheduled macro events;
- option and futures expiration effects;
- pre-holiday and post-holiday effects;
- overnight versus intraday decomposition;
- weekday and month-boundary mechanisms that are not exact duplicates of closed lineages;
- HYG/LQD credit-stress signals;
- Treasury-duration and equity-rate interactions;
- SPY/GLD correlation breakdowns;
- volatility and drawdown state transitions;
- recovery-state mechanisms;
- breadth and participation state mechanisms;
- sector and index-reconstitution events;
- Treasury auctions and refunding dates at daily frequency;
- PCE, GDP, ISM, retail-sales and jobless-claims release-date mechanisms;
- dollar, oil, inflation and rates cross-asset signals;
- static core plus small conditional sleeves.

No additional SPY/QQQ/GLD weighting, momentum or inverse-volatility variant may be formalized for at least 90 days.

### 7.2 Survivor-aware US stock mechanisms

Once data identity is feasible, search:

- 52-week-high proximity;
- residual momentum;
- short-term market-residual reversal;
- VIX-conditioned liquidity provision;
- stock-level overnight versus intraday patterns;
- industry momentum;
- Amihud and dollar-volume liquidity;
- volume and dollar-volume shocks;
- idiosyncratic volatility;
- MAX / lottery preference;
- low-beta long-only;
- price gaps and recovery;
- earnings-adjacent volume and liquidity;
- index inclusion and deletion effects;
- post-split and post-dividend event mechanisms.

No formal result may begin until survivor-aware membership, delisting terminal value, corporate actions, identifiers and immutable snapshots qualify.

### 7.3 Earnings, corporate events and fundamentals

Search:

- post-earnings-announcement drift;
- earnings-announcement premium;
- announcement-time and before/after-market identity;
- earnings surprise plus volume;
- post-announcement reversal;
- 8-K event categories;
- buyback announcements;
- dividend initiations, increases, cuts and omissions;
- insider open-market purchases;
- net issuance and repurchases;
- gross profitability;
- asset growth;
- accruals;
- investment and quality;
- value plus quality;
- financial distress and balance-sheet safety.

Use SEC as-filed and filing-time identities. Do not use current restated values as historical facts.

### 7.4 High-cost data mechanisms

Scout only; do not purchase or implement yet:

- FOMC/CPI/NFP intraday reactions;
- opening and closing auction imbalance;
- order-flow imbalance;
- last-hour momentum;
- option variance-risk premium;
- implied-volatility skew;
- earnings options;
- news sentiment;
- 10-K/10-Q textual change;
- conference-call language;
- analyst-estimate revisions.

Each high-cost card must state coverage start, license, total cost, reproducibility, sample size and why simpler data cannot answer the question.

## 8. Mechanism-card schema

Every scout returns the same compact card:

```text
mechanism_id
economic_mechanism
primary_original_source
market_role
universe
signal_and_holding_period
required_data
current_data_status
sample_size_estimate
turnover_and_cost_risk
USD_40000_execution_fit
survivorship_and_PIT_risk
closed-lineage_duplicate_screen
implementation_size_estimate
result_time_estimate
recommendation=ADVANCE|PARK|CLOSE
```

No card may contain historical strategy returns.

## 9. Selection rules after broad search

Manager may form a Development Atlas of 8-12 genuinely independent mechanisms from one economic family.

Parameter variants do not count as independent mechanisms.

```text
wide pool: 50-100 cards
Development Atlas: 8-12 mechanisms
formal Validation proposals: maximum 2
formal Holdout/secondary confirmation: maximum 1
active code-writing mechanism: exactly 1
```

A mechanism advances based on economic prior, data readiness, sample size, execution fit and independence—not on hidden or informal return checks.

## 10. Evidence and implementation budgets

```text
input resolution: 2-5 working days per bounded lane
development result: 2-3 working days
ordinary FAIL closure: same day after CI
strategy-specific runtime: target <= 400 lines
focused tests: target <= 200 lines
new architecture: 0
new database layer: 0
new runner framework: 0
new evidence framework: 0
```

## 11. External research basis

Primary or official starting points include:

- Federal Reserve FOMC historical materials: https://www.federalreserve.gov/monetarypolicy/fomc_historical_year.htm
- BLS Employment Situation archive: https://www.bls.gov/bls/news-release/empsit.htm
- BLS CPI archive: https://www.bls.gov/bls/news-release/cpi.htm
- SEC EDGAR APIs: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- SEC Financial Statement Data Sets: https://www.sec.gov/data-research/sec-markets-data/financial-statement-data-sets
- SEC Insider Transactions Data Sets: https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets
- George and Hwang, 52-week high: https://doi.org/10.1111/j.1540-6261.2004.00695.x
- Nagel, short-term reversal and liquidity: https://doi.org/10.1093/rfs/hhs066
- Bernard and Thomas, PEAD: https://doi.org/10.2307/2491062
- Novy-Marx, gross profitability: https://doi.org/10.1016/j.jfineco.2013.01.003

Literature is prior evidence only. Local frozen results and later prospective observations control promotion.

## 12. Final controlling state

```text
PRIMARY_MARKET=US
PR_105_EVIDENCE=ACCEPTED
PR_105_MAINLINE_MERGE=false
ACTIVE_FORMAL_RESULT_LANE=NONE_PENDING_IDENTITY_RESOLUTION
WIDE_READ_ONLY_SCOUTS=AUTHORIZED
PRICE_RETURN_ACCESS=false
DATABASE_WRITE=false
VALIDATED_SPECIALISTS=0
STRATEGY_CANDIDATE_AVAILABLE=false
SHADOW=false
PAPER=false
LIVE=false
```
