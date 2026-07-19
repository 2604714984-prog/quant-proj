# PR #101 exact-head audit and post-checkpoint research plan

Date: 2026-07-19  
Repository: `2604714984-prog/quant-proj`  
Review target: PR #101  
Reviewed HEAD: `70f1acf97a80b3a0da0d4c7bf06c1e23bab3b14e`  
Review ID: `4731100512`

## Verdict

```text
ACCEPT_EXACT_HEAD_WITH_FORWARD_ONLY_CLARIFICATION
```

PR #101 may be marked Ready and merged only while its HEAD remains exact.

No architecture, shared-core, database or backtest-engine rework is required.

## Accepted program state

The following five recent US retrospective results are valid terminal evidence for their exact frozen mechanisms:

```text
PR #93  SPY 200-session trend/cash                FAIL
PR #94  SPY classic turn-of-month                 FAIL
PR #96  SPY/QQQ/GLD dual momentum                 FAIL
PR #98  full-liquidation capped inverse volatility FAIL
PR #100 SPY-drawdown GLD stress safe-haven        FAIL
```

They remain closed. They may not be retuned, rerun, regime-relabeled, combined as sleeves or used to rescue one another.

The 2010-2017 validation interval and the 2018-2026-06 retrospective-holdout interval are consumed at the research-program level. A later PASS on the same dates is only:

```text
RETROSPECTIVE_SECONDARY_ONLY
```

It cannot by itself create candidate, Paper, live, funded or automatic-trading authority.

Gate counts are mechanism-specific replay facts. `7/8` is not closer to acceptance than `6/10`; terminal status remains binary.

## Forward-only clarification

Historical holdout exhaustion must not make the project incapable of collecting new evidence.

A genuinely new mechanism may follow this path:

```text
frozen development result
-> one frozen retrospective-secondary confirmation
-> exact-head external review
-> PROSPECTIVE_SHADOW_ELIGIBLE
```

Shadow begins only on observations strictly after the frozen historical cutoff. It has no capital, no order and no position effect.

A retrospective-secondary PASS does not set:

```text
strategy_candidate_available=true
```

Paper or funded use requires separately accepted prospective evidence.

## Sole next active research line

```text
US_SCHEDULED_EVENT_ATLAS_DEVELOPMENT_V1
LANE_B_DAILY_SCHEDULED_EVENTS
```

Merged PR #97 is the controlling frozen definition.

No new shortlist and no fourth SPY/QQQ/GLD allocation strategy is required.

## Immediate objective

Produce the first Lane B numerical development result with the smallest honest input scope.

The priority order is:

```text
1. M3 FOMC next-session open-to-close
2. M6 monthly options expiration
3. M7 quarterly options/futures expiration
4. M4 CPI pre-release negative control
5. M5 NFP pre-release negative control
```

M4 and M5 can never be promoted. They are controls, not strategies.

A partial Atlas result is valid. M3 must not wait for every other mechanism if M3 independently qualifies.

## Phase 1: M3 input materialization

### Required artifacts

Use a local versioned evidence bundle outside Git for raw source bytes.

Git may contain only narrow parser code, focused tests, hashes, manifests and aggregate qualification.

Materialize:

```text
A. Official FOMC event identities, 1994-2009
B. Pinned and reconciled XNYS session calendar, 1994-2009
C. Existing SPY development slice identity
D. One immutable joint input manifest
```

### FOMC event table

Minimum columns:

```text
event_id
event_type
official_timestamp_et
official_release_date
source_url
source_bytes_sha256
retrieved_at_utc
revision_or_reschedule_identity
qualification_status
```

Use actual historical release times. Do not backfill modern 14:00 practices into older events.

Primary route:

```text
https://www.federalreserve.gov/monetarypolicy/fomc_historical.htm
```

### XNYS calendar

Generate a candidate calendar with one pinned `exchange_calendars` version.

Then compare every date against the 4,030 observed SPY development dates and explain every difference with accepted exception evidence.

Minimum fields:

```text
session_date
open_et
close_et
early_close
unscheduled_closure
generator_version
source_set_sha256
calendar_rows_sha256
```

Calendar acceptance rule:

```text
observed_SPY_dates == accepted_XNYS_dates
```

or every difference must have a separately accepted official exception.

### SPY slice

Reuse the frozen 1994-01-03 through 2009-12-31 SPY slice already identified in PR #97.

Do not rewrite canonical DuckDB.

Bind:

```text
snapshot_id
row_count=4030
date range
ordered rows SHA-256
raw/adjusted field identity
corporate-action classification
```

### M3 qualification gate

M3 may proceed only if all are true:

```text
structural events >= 24
complete events >= 24
distinct years >= 6
completeness >= 95%
duplicate event IDs = 0
missing official timestamps = 0
calendar conflicts = 0
price endpoint failures remain within the frozen completeness rule
```

## Phase 2: M3 development result

After M3 input qualification passes, run exactly one development result on:

```text
1994-01-01 through 2009-12-31
```

Use the frozen PR #97 mechanism without modification:

```text
entry: first accepted NYSE session open strictly after the FOMC timestamp
exit: same session close
primary round-trip cost: 15 bps
stress round-trip cost: 30 bps
whole shares
USD 40,000
cash interest: zero
```

Publish:

```text
event count
year count
15 bps mean event return
30 bps mean event return
ordinary block-bootstrap lower bound
null-centered raw p-value
Holm-adjusted p-value
largest positive event contribution
largest positive year contribution
exact eight-gate vector
PASS / FAIL / INPUT_BLOCKED
```

Blocked mechanisms remain p-value 1.0 in the frozen eight-test family.

A PASS stops for exact-head review. It does not authorize validation or a candidate.

## Phase 3: M6 and M7

After M3 reaches a terminal development result, materialize exact historical expiration identities.

Do not infer the entire historical table from a single modern rule without exception review.

Official starting references:

```text
OCC ETF Options:
https://www.theocc.com/clearance-and-settlement/clearing/etf-options

OCC Quarterly Options:
https://www.theocc.com/clearance-and-settlement/clearing/quarterly-options
```

Required checks:

```text
monthly and quarterly mechanisms are mutually exclusive
holiday shifts are explicit
historical rule changes are identified
session dates reconcile to the accepted XNYS calendar
```

Run each qualified mechanism once. Do not alter the Atlas family or selection rule.

## Phase 4: M4 and M5 controls

Materialize BLS actual release identities from official archives.

Primary routes:

```text
https://www.bls.gov/bls/archived_sched.htm
https://www.bls.gov/bls/newsrels.htm
```

M4 and M5 remain non-promotable.

A positive control alarm only affects M1 event-specificity; it does not become a tradable candidate.

## Lane A and Lane C disposition

Lane A and Lane C receive only a bounded data-availability decision.

```text
combined budget cap: USD 400
maximum elapsed time: 5 working days
```

Required before any purchase:

```text
sample event days
exact minute coverage
timezone and RTH/extended-hours labels
gap policy
raw/adjusted identity
license and reproducibility
```

If exact coverage cannot be established within budget:

```text
TERMINAL_DATA_UNAVAILABLE_WITHIN_BUDGET_NO_OUTCOME
```

Daily proxies are forbidden.

## Next mechanisms after Lane B

No new mechanism starts while Lane B has an active code-writing result.

After Lane B reaches a terminal point, use this order.

### Tier 1: existing daily ETF data

```text
1. SPY overnight versus intraday decomposition
2. SPY pre-holiday effect
3. HYG/LQD credit-stress gate, only after adjusted identities qualify
```

Each receives one variant and one result.

Do not start another SPY/QQQ/GLD weighting or momentum variant for at least 90 days.

### Tier 2: survivor-aware US stock data

Only after historical membership, delisting, terminal value and corporate actions qualify:

```text
1. 52-week-high proximity
2. short-term market-residual reversal
3. stock-level overnight versus intraday atlas
4. low-idiosyncratic-risk or liquidity mechanisms
```

### Tier 3: PIT event and fundamental data

Only after filing and announcement availability identities qualify:

```text
1. post-earnings-announcement drift
2. earnings-announcement premium
3. gross profitability
4. asset growth
5. net issuance / buyback mechanisms
```

### Tier 4: high-cost data

Deferred until a simpler mechanism reaches prospective Shadow:

```text
FOMC intraday
options variance-risk premium
order flow and auction imbalance
news sentiment
10-K / 10-Q text
conference-call language
```

## Research operating budget

```text
one active code-writing mechanism
one primary variant
at most one preregistered robustness variant
no parameter grid
no plan-only PR
next substantive PR contains a number or terminal blocker
```

Time budgets:

```text
input materialization: 3-5 working days
one development result: 2-3 working days
ordinary FAIL closure: same day after CI
```

## Thirty-day deliverables

Minimum target:

```text
1 accepted Lane B input manifest
1 M3 numerical development result
1 M6/M7 numerical result or terminal blocker
1 independent daily-data mechanism result
0 new architecture
0 Qlib or RD-Agent integration
0 broker or live work
```

## Progress definition

Counts as progress:

```text
numerical development result
validation result
prospective Shadow event
terminal data-unavailable closure
```

Does not count as progress:

```text
shortlist
provider survey
roadmap-only PR
increased test count
implementation without a result
```

## External research basis

The search direction is grounded in, but not entitled to, the following priors:

- Lucca and Moench, `The Pre-FOMC Announcement Drift`.
- Kurov, Wolfe and Gilbert, `The Disappearing Pre-FOMC Announcement Drift`.
- Savor and Wilson, scheduled macroeconomic announcement premia.
- Lou, Polk and Skouras, overnight versus intraday expected returns.
- George and Hwang, the 52-week-high mechanism.

Literature is a prior. Only frozen local results and future prospective evidence control promotion.
