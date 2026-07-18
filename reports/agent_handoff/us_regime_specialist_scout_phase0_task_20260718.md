# Task — US Regime Specialist Scout Phase 0

Date: 2026-07-18  
Target repository: `2604714984-prog/quant-proj`  
Workstream: `US_REGIME_SPECIALIST_SCOUT_READ_ONLY`

## Mission

Produce a small, evidence-backed slate of US equity regime-specialist hypotheses for
user selection. Do not implement or backtest a strategy.

The research objective is not an all-weather strategy. Each candidate must specify
one market state, one specialist mechanism, activation/exit rules and cash outside
the state.

## Hard boundaries

```text
OUTCOME_FREE=true
STRATEGY_ADAPTER=false
STRATEGY_RETURN_QUERY=false
NAV_OR_SHARPE=false
DATABASE_WRITE=false
PROVIDER_CALL=false unless separately authorized
STRATEGY_SELECTION_BY_BACKTEST=false
STRATEGY_CANDIDATE_AVAILABLE=false
```

Use primary papers and official source documentation. SEO summaries, social-media
claims and vendor marketing cannot establish an economic prior.

## Repository boundary

These repositories are reference and failure memory only:

```text
2604714984-prog/US_Stock_Monitor
2604714984-prog/us_stock_30w
2604714984-prog/strategy_work
```

Do not reuse rejected US31/US36/US41/US46 parameters, output or code. Do not treat
the old US46 headline as candidate evidence.

## Candidate states

Every candidate must use exactly one primary state:

```text
TREND_UP
RANGE
STRESS
RECOVERY_TAG
CROSS_STATE_WITH_EXPLICIT_FORBIDDEN_STATE
```

The state definition comes from the independent Market State Observer workstream.
The scout may state required state inputs but may not define thresholds from
strategy performance.

## Required candidate families

Assess at least the following four families.

### 1. TREND_UP — absolute trend plus participation

Hypothesis:

```text
liquid US equities with positive absolute trend may persist when broad participation
is strong and market stress is low
```

Primary prior:

- Daniel and Moskowitz, `Momentum Crashes`: https://www.nber.org/papers/w20439
- time-series and cross-sectional momentum primary literature as applicable

Must distinguish the new hypothesis from rejected static US momentum/ETF lineages.
No old parameter or universe may be carried forward.

### 2. STRESS — quality or low-risk long-only

Hypothesis:

```text
revision-safe high-quality or low-risk liquid equities may preserve capital better
than broad exposure during a preregistered stress state
```

Primary priors:

- Asness, Frazzini and Pedersen, `Quality Minus Junk`:
  https://papers.ssrn.com/abstract=2312432
- Frazzini and Pedersen, `Betting Against Beta`:
  https://doi.org/10.1016/j.jfineco.2013.10.005

Explicitly include published criticisms and implementation sensitivity. A long-only
translation is a new hypothesis, not a direct factor replication.

### 3. RANGE or STRESS-LIQUIDITY — short-term residual reversal

Hypothesis:

```text
short-term market-residual losers among highly liquid US equities may earn a
liquidity-provision premium in a frozen state
```

Primary prior:

- Nagel, `Evaporating Liquidity`:
  https://academic.oup.com/rfs/article-abstract/25/7/2005/1602153

This family must fail before implementation if daily bars, spreads or conservative
cost/next-open feasibility cannot support the intended holding period.

### 4. RECOVERY_TAG — breadth recovery after drawdown

Hypothesis:

```text
broad participation recovery after a frozen market drawdown may support a temporary
re-risking sleeve
```

The default comparator is simple broad exposure or cash. Stock selection needs an
independent prior; otherwise keep the candidate at broad-market/sector level.

## Candidate scoring

Score each candidate before any strategy return access:

```text
economic_prior:0..3
data_readiness:0..3
USD_account_feasibility:0..2
independence_from_closed_strategies:0..2
implementation_simplicity:0..1
turnover_and_cost_risk:0..1 where 1 is low risk
```

Maximum score is 12. A candidate below 8 cannot be recommended for formal work.

## Required data and execution audit

For each candidate list exact required fields and identities:

```text
raw and adjusted prices
split and cash-distribution identity
delisting and terminal-action identity
historical universe or explicit non-index universe rule
available_at or retrospective-only classification
volume and amount
VIX / breadth / credit state inputs if used
PIT fundamentals and shares outstanding if used
USD capital, whole/fractional-share assumption
commission, spread, slippage and settlement
expected positions, holding period and turnover
```

Do not assume fractional shares. Report two capital cases if the intended broker
might support them:

```text
whole-share feasibility
fractional-share planning-only feasibility
```

The first research screen must use the more conservative authorized case.

## Required output

Create one concise report with no more than four candidate cards:

```text
reports/validation/us_regime_specialist_candidate_slate_v1_20260718.md
```

Each card contains:

```text
candidate_id
primary_state
economic_mechanism
primary_sources
required_data
current_data_status
survivorship_and_membership_risk
capital_feasibility
expected_turnover
execution_risk
closed-strategy_independence
score
recommended_status=PROPOSE_FOR_USER_SELECTION|BLOCKED|REJECT
```

Also provide one recommended first family, but do not create its task or code. The
user makes the final selection.

## Selection principles

Prefer:

```text
strong primary prior
qualified current data
5 to 10 positions or an explicitly justified alternative
weekly or monthly turnover where possible
cash as a valid inactive state
simple causal activation
small code surface
```

Reject or block:

```text
survivorship-biased current-constituent panels
unqualified adjusted-price or corporate-action chains
paper-only signals with no implementable long-only translation
strategies requiring shorting, leverage or options for the first live path
high-frequency signals without spread and queue evidence
post-hoc states
```

## GitHub publication

Create one branch and one Draft PR. Push and verify exact remote head. Do not merge.
Stop for Manager and user selection.

## Callback

```text
BATCH:US_REGIME_SPECIALIST_SCOUT_PHASE0_20260718
STATUS:
BASE_COMMIT:
PR_URL:
HEAD_SHA:
CANDIDATE_COUNT:
PROPOSED_COUNT:
BLOCKED_COUNT:
REJECTED_COUNT:
TOP_CANDIDATE_ID:
TOP_CANDIDATE_STATE:
TOP_CANDIDATE_SCORE:
DATA_GAPS:
STRATEGY_RETURNS_ACCESSED:false
STRATEGY_CODE_CREATED:false
STRATEGY_CANDIDATE_AVAILABLE:false
NEXT_ACTION:USER_SELECTS_FIRST_US_FAMILY
```
