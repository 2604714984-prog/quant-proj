# Relative Variance PR #84 — Capital and Board-Lot Feasibility Addendum

Date: 2026-07-18
Status: `MANDATORY_BEFORE_HISTORICAL_OUTCOME`
Repository: `2604714984-prog/quant-proj`
Target PR: `#84`
Reviewed head before rework: `44199bc4ec9f825750283c62b0242f7981f30fd6`

This file supplements, and does not replace:

```text
reports/agent_handoff/relative_variance_pr84_narrow_rework_20260718.md
```

## Reason

The current definition freezes a 30-stock target basket and shared A-share execution semantics, but it does not freeze a numeric starting capital. A result produced without a numeric capital would leave board-lot rounding, minimum commission, invested ratio, and effective position count underdetermined.

A strategy intended for eventual pilot use must prove that it can be reproduced at a realistic capital scale before holding-period outcomes are opened.

## Mandatory definition changes

Freeze:

```text
historical_initial_cash_cny=400000
basket_size=30
lot_size_shares=100
commission and tax model=current accepted shared A-share contract
leverage=false
remaining_cash_return=0
```

Do not change the 30-stock basket after observing feasibility.

Record an intended pilot-scale ceiling as a planning field only. It does not authorize real-money activity.

## Aggregate capital-feasibility scan

For every retained interval, compute from the already frozen target weights and qualified execution opens:

```text
minimum capital required for one board lot in every intended nonzero target
nonzero position count after board-lot rounding at CNY 400,000
managed invested ratio after board-lot rounding and costs
comparator invested ratio after board-lot rounding and costs
minimum-commission drag
capacity rejections
market-rule rejections
```

The scan may use formation information, target exposure, execution prices, and existing shared execution rules. It must not read or publish subsequent holding-period returns, NAV, validation gates, holdout outcomes, forward outcomes, rankings, or security identifiers.

## Required aggregate fields

```text
status
retained_interval_count_by_split
historical_initial_cash_cny
basket_size
maximum_minimum_faithful_capital_cny
minimum_nonzero_managed_positions
minimum_nonzero_comparator_positions
minimum_managed_invested_ratio
minimum_comparator_invested_ratio
maximum_minimum_commission_drag_bps
capacity_rejection_count
market_rule_rejection_count
invalid_capital_interval_count
holding_returns_opened=false
holdout_outcomes_opened=false
forward_outcomes_opened=false
strategy_candidate_available=false
```

## Gate

Use one frozen gate before outcomes:

```text
invalid_capital_interval_count == 0
minimum_nonzero_comparator_positions == 30
minimum_comparator_invested_ratio >= 0.90
minimum_nonzero_managed_positions >= 24
minimum_managed_invested_ratio >= max(0.80 * intended_exposure, intended_exposure - 0.10)
```

The managed invested-ratio comparison is against the frozen intended exposure for that interval, not against 100% capital.

If the gate is not met:

```text
STATUS=LIVE_FEASIBILITY_FAIL_NO_OUTCOME
HISTORICAL_OUTCOME_AUTHORIZED=false
```

Close the family as the fast-live candidate. Do not reduce basket size, alter exposure, change capital, remove expensive stocks, or add replacements after observing the result.

## Evidence-mode clarification

PR #84 must choose exactly one historical mode before outcome access:

```text
A. retrospective QFQ secondary economic screen
or
B. account-level execution evidence with complete corporate-action identity
```

For the current snapshot, mode A is the narrow permitted route. It must be labeled:

```text
RETROSPECTIVE_PERSONAL_RESEARCH_GRADE_SECONDARY_NOT_STRICT_PIT
NOT_ACCOUNT_LEVEL_CANDIDATE_EVIDENCE
```

Do not claim that QFQ prices plus the Event Loop constitute full account-level corporate-action evidence.

## Allowed files

Use the narrowest possible changes within PR #84. Expected files:

```text
research/definitions/a_share_relative_variance_managed_liquid_equity_v1.json
scripts/run_a_share_relative_variance_management_preflight.py
src/quant_system/research/relative_variance_management.py only if a pure helper is needed
tests/test_relative_variance_management.py
aggregate preflight result JSON
```

Do not modify shared Event Loop, Portfolio, market semantics, database, provider code, or Manager control documents.

## Validation

```text
focused tests
full repository tests
Ruff
git diff --check
strict JSON
read-only database before/after identity
no WAL
no holding-period outcome access
```

## Callback

```text
STATUS:
BASE_COMMIT:
PR_URL:
HEAD_SHA:
HISTORICAL_INITIAL_CASH_CNY:
MAXIMUM_MINIMUM_FAITHFUL_CAPITAL_CNY:
MINIMUM_NONZERO_MANAGED_POSITIONS:
MINIMUM_NONZERO_COMPARATOR_POSITIONS:
MINIMUM_MANAGED_INVESTED_RATIO:
MINIMUM_COMPARATOR_INVESTED_RATIO:
INVALID_CAPITAL_INTERVAL_COUNT:
CAPITAL_FEASIBILITY_STATUS:
HISTORICAL_OUTCOME_AUTHORIZED:false
STRATEGY_CANDIDATE_AVAILABLE:false
NEXT_ACTION:EXTERNAL_REVIEW
```
