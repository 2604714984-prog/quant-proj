# Task — PR #84 Relative Variance Narrow Rework

Date: 2026-07-18  
Repository: `2604714984-prog/quant-proj`  
Original reviewed head: `44199bc4ec9f825750283c62b0242f7981f30fd6`

## Start gate

Do not start until the Manager confirms:

```text
PR_85=MERGED_AFTER_ROADMAP_CORRECTION
PR_84=REBASED_ON_CURRENT_V2_MAIN
PR_84_ROADMAP_CHANGE=REMOVED
```

Read:

```text
reports/external_audit/pr84_pr85_joint_external_audit_20260718.md
reports/agent_handoff/manager_v2_control_constitution_v2_20260716.md
```

## Required fixes

### 1. Remove closed-lineage dependency

`src/quant_system/research/relative_variance_management.py` must not import bootstrap mechanics from:

```text
quant_system.backtest.permanent_portfolio
```

Implement a private deterministic helper in the Relative Variance module using:

```text
numpy.random.Generator(PCG64(seed))
block length=3 months
draw count=10000 in the frozen validation contract
circular wrapping
truncate to exact N
```

Keep it small. Do not create or generalize a bootstrap framework. Remove the closed Family42 module from the definition's binding and update exact hashes/tests.

### 2. Freeze candidate exclusions

Replace the current open-ended exclusion wording with an exhaustive list matching the accepted preflight SQL. Allowed exclusions are only:

```text
not an accepted ordinary A-share symbol/board
listing date absent, malformed, or after decision
fewer than 274 consecutive accepted sessions since listing
missing/duplicate/nonfinite/nonpositive QFQ close identity in the 274-session window
missing/nonfinite/negative amount in the exact 20-session window
wrong snapshot/quality/synthetic/row-hash identity
```

No ST, volatility, momentum, industry, market-cap, future status, discretionary quality, or result-informed filter may be added before ranking. No replacement after the top 30.

### 3. Freeze the historical return representation

The current definition mixes QFQ signal data with shared account/Event Loop language without specifying the valuation identity. Choose and freeze exactly one of the following before any outcome:

#### Authorized lightweight choice — secondary QFQ economic screen

```text
classification=RETROSPECTIVE_SECONDARY_QFQ_ECONOMIC_SCREEN_NOT_ACCOUNT_EVIDENCE
signal=QFQ closes
entry/exit return identity=explicit frozen QFQ open convention
cost=existing frozen 50-bps one-way turnover rule
capacity/limit/status fields=aggregate feasibility and execution-stress diagnostics only
account-level Event Loop claim=false
candidate eligibility=false
```

The result may only decide `VALIDATION_PASS_TO_EXTERNAL_REVIEW` or terminal `VALIDATION_FAIL`; it cannot become a candidate.

#### Alternative account-level choice

If shared Event Loop/account-level evidence is retained, stop and report blocked until complete A-share dividend/split/rights identities and their availability are qualified. Do not invent or infer corporate actions.

Do not combine the two representations.

### 4. Preserve all frozen economic choices

Do not change:

```text
one variant
30-stock basket
252/21 variance windows
exposure=min(1, baseline/current)
no leverage
cash return=0
50-bps one-way cost
validation split
1/60 alpha
bootstrap draws/seeds
gates
```

## Allowed files

```text
research/definitions/a_share_relative_variance_managed_liquid_equity_v1.json
src/quant_system/research/relative_variance_management.py
scripts/run_a_share_relative_variance_management_preflight.py
reports/validation/a_share_relative_variance_management_preflight_v1_20260718.json
tests/test_relative_variance_management.py
```

The roadmap file must not be present in the rebased PR.

## Validation

```text
focused tests
full repository tests
Ruff
git diff --check
wheel build
fresh install and pip check
repository-external quant info
preflight byte-for-byte reproduction
central DB SHA unchanged and no WAL
```

No validation return, holdout, forward, provider, database write, security identifier, or candidate output.

## Callback

```text
STATUS:
BASE_COMMIT:
NEW_HEAD:
CHANGED_FILES:
ROADMAP_FILE_REMOVED:
CLOSED_MODULE_IMPORT_REMOVED:
PRIVATE_BOOTSTRAP_HELPER_STATUS:
CANDIDATE_EXCLUSION_LIST_FROZEN:
RETURN_REPRESENTATION:
DEFINITION_SHA256:
MODULE_SHA256:
PREFLIGHT_RESULT_SHA256:
FOCUSED_TESTS:
FULL_TESTS:
CI_STATUS:
DATABASE_UNCHANGED:
HISTORICAL_VALIDATION_OPENED:false
STRATEGY_CANDIDATE_AVAILABLE:false
NEXT_ACTION:EXTERNAL_DELTA_REVIEW
```
