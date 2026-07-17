# Cycle 4 Task — Listed-Fund Cash-Distribution Semantic Repair

Date: 2026-07-17  
Repository: `2604714984-prog/quant-proj`  
Default branch: `v2-main`  
Status: `AUTHORIZED_FOR_ONE_NARROW_SEMANTIC_PR`

## Authority and base

Read in order:

1. `reports/agent_handoff/manager_v2_control_constitution_v2_20260716.md`
2. `reports/external_audit/cycle4_three_etf_external_audit_verdict_20260717.md`
3. `reports/agent_handoff/manager_cycle4_etf_rework_and_coordination_task_20260717.md`
4. this task

Start from the first merged `v2-main` commit containing this task file. Record the
exact base commit and tree before editing.

This task authorizes one narrow shared-semantic implementation PR. It does not
authorize ETF data import, provider access, Cycle 4 strategy code, returns, NAV,
prospective access, a candidate, or a trading path.

## Defect to repair

The existing rich `CorporateActionIdentity` supports cash distributions, but the
current shared execution path cannot apply an A-share listed-fund distribution:

```text
event_loop rejects corporate_actions for market="a_share"
Portfolio.apply_cash_distribution rejects non-US portfolios
```

This prevents a held listed ETF from receiving its qualified ex-date entitlement
and pay-date cash through the accepted event loop.

## Frozen semantic scope

Support only rich, source-bound listed-fund actions with:

```text
action_type = cash_dividend or special_dividend
subject_id and globally unique event_id
explicit effective_at / ex_date / record_date / pay_date
explicit CNY cash amount per fund share
source and revision identity
source.available_at no later than the decision cutoff
```

Required behavior:

```text
entitlement is frozen from session-open shares on ex-date
pay-date cash is credited exactly once
selling after entitlement freeze does not remove the entitlement
buying on or after ex-date does not receive the prior entitlement
no automatic reinvestment
no duplicate cash credit
late, incomplete or wrong-symbol identity fails before mutation
adjusted prices are not used to double-count the distribution
```

This task does not authorize:

```text
stock-dividend tax modeling
arbitrary A-share stock corporate actions
ETF creation/redemption modeling
NAV accounting
new action types
new corporate-action framework
new event engine
```

The supplied cash amount must be defined as the exact cash credited per qualified
listed-fund share. Do not infer withholding or tax semantics inside this patch.

## Allowed implementation surface

Prefer changes only to:

```text
src/quant_system/backtest/portfolio.py
src/quant_system/backtest/event_loop.py
tests/test_backtest_core.py
one new focused test file only if an existing file cannot express the event-loop cases
```

`src/quant_system/data/source_identity.py` already contains the required rich
identity and is not expected to change. If a change appears necessary, stop and
return `SCOPE_EXPANSION_REQUIRES_USER_APPROVAL` before editing it.

Do not add a new runtime module.

## Implementation constraints

### Portfolio

Generalize the existing exactly-once cash-distribution mechanism so it can be
used by an A-share listed-fund portfolio while preserving current US behavior.

Reuse:

```text
_session_open_shares
PendingCash
_applied_distribution_action_ids
start_session settlement
finite-value checks
```

Do not create a second entitlement ledger.

### Event loop

Permit only rich `cash_dividend` and `special_dividend` identities on an
A-share execution input.

Continue to reject:

```text
raw action labels without CorporateActionIdentity
unsupported action types
terminal_action on A-share inputs
late source identity
wrong effective date
wrong subject identity
duplicate global action IDs
```

The existing action ordering must remain:

```text
start session
settle due pending cash
apply ex-date corporate actions
then process sells and buys
```

### Costs and trading rules

Do not change the stock stamp-tax schedule or `Portfolio.a_share()`.

The Cycle 4 ETF adapter will later use the existing generic constructor with:

```text
sell_tax_rate=0
lot_size=100
share_t_plus_one=true
a_share_stamp_tax_schedule=false
```

This PR only proves that the generic zero-tax listed-fund path and distribution
path coexist correctly.

## Mandatory focused tests

At minimum prove:

```text
1. A-share ETF held at ex-date session open receives the frozen entitlement.
2. Pay-date credits the exact cash once.
3. Selling after ex-date preserves the frozen pending entitlement.
4. Buying on ex-date does not receive that event's entitlement.
5. Reusing an event_id never double credits.
6. Late source identity fails before cash, positions or pending cash mutate.
7. Missing/wrong dates, currency, unit or subject fail closed.
8. Existing US cash-distribution tests remain unchanged and pass.
9. A-share stock stamp-tax behavior remains unchanged.
10. Generic listed-fund zero sell-tax behavior remains unchanged.
11. Ordinary A-share input without a corporate action behaves byte/receipt-equivalently.
```

Include one synthetic event-loop test that exercises the full accepted path, not
only direct `Portfolio` method calls.

## Validation

Before opening the PR:

```text
focused tests pass
full repository tests pass
Ruff passes
wheel build and installed-package CI pass
git diff --check passes
no provider or database access
no result or prospective data access
no new framework or unrelated files
```

Keep runtime growth small. If the implementation exceeds 150 net runtime lines,
stop and explain why before continuing.

## PR and review boundary

Open one PR with a neutral title such as:

```text
Support source-bound A-share ETF cash distributions
```

The PR must remain unmerged after CI. Return the Manager Callback B and stop for
full independent external review.

No Cycle 4 source import or PR A may rely on this code before that review accepts
the exact head.

## Terminal callback

```text
STATUS:
BASE_COMMIT:
PR_URL:
HEAD_SHA:
CHANGED_FILES:
RUNTIME_NET_LINE_DELTA:
FOCUSED_TEST_COUNT:
FULL_CI_STATUS:
A_SHARE_ETF_EX_DATE_ENTITLEMENT:
PAY_DATE_EXACTLY_ONCE:
POST_EX_DATE_SELL_PRESERVES_ENTITLEMENT:
EX_DATE_BUY_EXCLUDED:
LATE_IDENTITY_FAILS_BEFORE_MUTATION:
US_DISTRIBUTION_REGRESSION:
A_SHARE_STOCK_TAX_REGRESSION:
ETF_ZERO_TAX_REGRESSION:
DATABASE_OR_PROVIDER_ACCESS:false
STRATEGY_OUTCOME_ACCESS:false
NEXT_ACTION:EXTERNAL_REVIEW
```

## Boundary

Research infrastructure only. No recommendation, candidate, strategy result,
readiness route, broker, order, paper, live, or automatic execution.
