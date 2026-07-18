# Manager Task — Fast Path from Strategy Research to Shadow and Paper Validation

Date: 2026-07-18
Repository: `2604714984-prog/quant-proj`
Status: `PLANNING_ONLY_NOT_LIVE_AUTHORIZATION`

Read first:

```text
reports/agent_handoff/manager_v2_control_constitution_v2_20260716.md
reports/external_audit/pr84_pr85_joint_external_audit_20260718.md
```

## Objective

Find the first strategy that can move through:

```text
aggregate feasibility
-> capital and board-lot feasibility
-> historical validation
-> conditional holdout
-> live-data Shadow
-> simulated paper execution
```

This task does not authorize broker connectivity, real-money orders, automatic execution, or candidate promotion.

## Immediate order

```text
1. Correct and merge PR #85.
2. Rework PR #84 under the accepted narrow task.
3. Add the missing capital and board-lot feasibility gate before any outcome.
4. Run Relative Variance validation only if every pre-outcome gate passes.
5. Open holdout only after accepted validation PASS.
6. Start Shadow only after accepted holdout PASS.
```

## Usability gates

### Historical economic acceptance

Requires the frozen primary endpoint and risk gates to pass after frozen costs.

### Shadow eligibility

Requires:

```text
accepted validation and holdout
frozen code and input identities
zero unresolved accounting or execution defects
capital and board-lot feasibility at the intended pilot scale
```

Shadow authorizes target generation only.

### Paper eligibility

Requires stable live-data Shadow and exact target reconciliation. Paper authorizes a simulator only.

## Live-first constraints for every future family

Freeze before outcomes:

```text
historical capital assumption
intended pilot scale
maximum instruments
board-lot feasibility
minimum commission effect
rebalance frequency
maximum target turnover
cash fallback
```

For an A-share whole-lot portfolio, calculate the smallest capital that allows each intended nonzero position to hold at least one 100-share lot. Report only aggregate feasibility values before outcome access.

A family whose faithful minimum scale exceeds the intended pilot scale must close before returns or be classified research-only.

## Relative Variance pre-outcome requirements

PR #84 must not open validation until all are complete:

```text
closed Family42 runtime dependency removed
candidate exclusions frozen exhaustively
one historical evidence mode selected
roadmap conflict removed
numeric historical capital frozen
aggregate board-lot and invested-ratio feasibility completed
minimum commission and capacity effects checked
```

Current 30-stock design must not be reduced after feasibility results are observed.

### Decision tree

```text
CAPITAL_FEASIBILITY_FAIL -> close without outcome
VALIDATION_FAIL -> close permanently
VALIDATION_PASS -> independent review before holdout
HOLDOUT_FAIL -> close permanently
HOLDOUT_PASS -> SHADOW_ELIGIBLE only
INPUT_BLOCKED -> repair only a concrete input or representation defect
```

## Next research lane if Relative Variance closes

Priority:

```text
low abnormal-turnover / anti-speculation
```

First phase is a read-only data identity check only:

```text
free-float identity
turnover definition and units
historical coverage
availability and revision identity
candidate breadth
turnover and capacity aggregates
board-lot feasibility
```

If the required turnover identity is incomplete, close before adapter work. Do not substitute raw amount or raw volume without a newly approved economic hypothesis.

## Final research lane

The final lane should be selected for live simplicity:

```text
uses already-qualified data
one primary variant
5 to 10 instruments at most
weekly or monthly rebalance
long-only and unlevered
cash allowed
small enough to reproduce faithfully at pilot scale
```

Preferred class for user consideration:

```text
absolute trend or risk-off exposure on a frozen high-liquidity ordinary-A basket
```

This must be a new time-series exposure hypothesis, not a repair of failed cross-sectional Relative Strength.

## Shadow stage

Minimum operational observation:

```text
20 accepted sessions
at least one scheduled rebalance event
zero missed runs
zero identity drift
zero unresolved target differences
zero nonfinite values
```

A Shadow record may include aggregate target and rejection counts, but no order submission.

## Paper stage

Use a one-way boundary:

```text
quant-proj frozen targets
-> explicit export
-> external simulator such as vn.py paper_account
```

Do not import vn.py into the research core.

Paper acceptance requires:

```text
one complete scheduled rebalance
exact order/receipt reconciliation
no duplicate or out-of-scope orders
cash and position reconciliation
restart recovery test
manual stop control test
```

Paper fills are operational evidence, not alpha evidence, and cannot alter the strategy.

## Real-money boundary

Any real-money pilot, broker gateway, order submission, or automatic execution requires a new explicit user instruction and independent review. Before automated submission, the user and broker must confirm applicable API permissions and programmatic-trading reporting requirements.

## Resource allocation

```text
70% strategy hypothesis and historical evidence
20% strategy-required data and capital feasibility
10% Macro Risk Shadow
0% new platform, new engine, new Agent framework, or synthesizer
```

## Callback

```text
STATUS:
CURRENT_V2_MAIN:
PR_85_STATUS:
PR_84_STATUS:
ACTIVE_FAMILY:
CAPITAL_FEASIBILITY_STATUS:
VALIDATION_STATUS:
HOLDOUT_STATUS:
SHADOW_STATUS:
PAPER_STATUS:
REAL_MONEY_AUTHORIZED:false
STRATEGY_CANDIDATE_AVAILABLE:false
NEXT_ACTION:
BLOCKERS:
```
