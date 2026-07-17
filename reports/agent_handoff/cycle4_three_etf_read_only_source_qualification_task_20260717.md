# Cycle 4 Task — Fixed Three-ETF Read-Only Source Qualification

Date: 2026-07-17  
Repository: `2604714984-prog/quant-proj`  
Default branch: `v2-main`  
Status: `AUTHORIZED_READ_ONLY_SOURCE_QUALIFICATION_ONLY`

## Authority and base

Read in order:

1. `reports/agent_handoff/manager_v2_control_constitution_v2_20260716.md`
2. `reports/external_audit/cycle4_three_etf_external_audit_verdict_20260717.md`
3. `reports/agent_handoff/manager_cycle4_etf_rework_and_coordination_task_20260717.md`
4. this task

This is a separate read-only lane. It may not edit the listed-fund semantic PR,
write the central database, implement Cycle 4, calculate a strategy outcome, or
coordinate directly with the semantic subagent.

## Fixed scope

Qualify exactly:

```text
510300.SH — domestic equity ETF
511010.SH — government-bond ETF
518880.SH — gold ETF
```

Frozen historical cutoff:

```text
2026-06-30 inclusive
```

Do not add or substitute an ETF.

## Purpose

Determine whether explicit public sources can support one coherent,
retrospective, immutable three-ETF snapshot without fabricating any field or
changing the central data contract.

This task may conclude that the source contract is incomplete. A negative result
is acceptable and closes Cycle 4 without outcome access.

## Source policy

Use:

```text
one canonical source per dataset
at most one read-only cross-check source per dataset
no automatic source selection
no automatic source fusion
```

A single vendor is not required to supply every dataset. Every field must map to
one explicit canonical source and one deterministic transformation.

Candidate interfaces that may be evaluated include:

```text
Tushare fund_daily — daily OHLC, volume and amount
Tushare fund_basic / etf_basic — product and listing identity
Tushare fund_adj — adjustment factor
Tushare fund_nav — NAV and announced cumulative-distribution cross-check
SSE and fund-manager announcements — cash-distribution event identity
existing accepted SSE calendar — session identity
official SSE trading rules — effective-dated price-limit and trading-rule identity
```

The list is not a completeness claim. If an interface cannot satisfy the frozen
contract, record the gap and stop; do not invent a substitute.

Existing configured credentials may be used without displaying, logging, or
committing them. Do not request or print a secret. Public/no-secret official
sources are preferred.

## Required dataset matrix

For each fixed ETF, qualify these domains separately:

```text
1. product identity and listing date
2. accepted trade calendar
3. raw daily open/high/low/close in CNY
4. daily volume in SHARES
5. daily amount in CNY
6. adjustment factor and adjusted-price construction identity
7. suspension / non-trading handling
8. price-limit rule or authoritative daily limits
9. cash-distribution event identity
10. split, symbol-change, termination or other corporate-action absence/presence
11. source URL, content hash, revision identity and actual retrieval time
12. deterministic row and snapshot identity
```

For each domain report:

```text
canonical source
optional cross-check source
coverage dates
row/event count
null count
duplicate count
unit
actual retrieval timestamp
historical availability classification
PASS / MISSING / CONFLICT / NOT_APPLICABLE
```

## Mandatory unit rules

If Tushare `fund_daily` is used, test and record:

```text
volume_shares = vol_in_lots * 100
amount_cny = amount_in_thousand_cny * 1000
```

Do not infer amount from OHLC and volume.

Reject nonfinite, negative, mixed-unit, duplicate-key, or silently rounded input.

## Historical availability classification

Rows retrieved now must not be backdated.

Record:

```text
retrieved_at = actual retrieval time
historical_available_at = UNKNOWN_NOT_PIT_QUALIFIED unless an explicit archived
                           publication identity proves otherwise
classification = RETROSPECTIVE_PERSONAL_RESEARCH_GRADE_SECONDARY_NOT_STRICT_PIT
```

Do not claim strict PIT or prospective eligibility.

## Suspension and missing-row handling

Do not treat an absent daily bar as proof of suspension.

For each missing accepted-session row, require one of:

```text
explicit qualified suspension/non-trading evidence
explicit product-not-yet-listed or already-terminated identity
otherwise: unexplained gap and FAIL
```

Do not forward-fill an execution bar, volume, amount, limit, or state.

## Price-limit matrix

For each instrument, produce:

```text
product type
applicable exchange rule identity
effective-date ranges
limit percentage or authoritative daily values
prior-close definition
rounding/tick rule
source identity
```

Accept only:

```text
authoritative daily upper/lower limits
or
an externally reviewable official rule plus exact prior close and rounding mechanics
```

If neither exists, mark the instrument `LIMIT_SEMANTICS_INCOMPLETE`.

Do not calculate daily limits under an unreviewed assumption.

## Corporate actions and distributions

For every cash distribution in the frozen sample, require:

```text
subject_id
event_id
action_type
announcement/source identity
available_at or explicit retrospective-unknown classification
ex_date
record_date
pay_date
cash amount per fund share in CNY
```

Cross-check adjusted factors/NAV against announced events, but do not replace
account-level cash events with a `qfq` label.

If a split, symbol change, termination, or other unsupported event occurs in the
sample, record it and return `SOURCE_MATRIX_INCOMPLETE_PENDING_SEMANTIC_REVIEW`.

## Trading-model assumption

Record `share_t_plus_one=true` only as the frozen conservative Cycle 4 model
constraint. Do not claim it is a universal exchange fact for every ETF class.
The strategy contains no same-session round trip.

## Output and repository scope

Publish one authoritative aggregate JSON under:

```text
reports/validation/cycle4_three_etf_source_qualification_v1.json
```

The JSON may contain source URLs and aggregate identities but no credentials,
raw payloads, security rankings, trend states, returns, NAV, or strategy gates.

A short PR description is sufficient; do not add a parallel evidence framework,
sidecar family, provider adapter, or permanent downloader.

Any temporary fetch/inspection code remains outside Git. Bind its SHA-256 and
exact invocation in the JSON if it materially determines the result.

## Terminal statuses

Use exactly one:

```text
SOURCE_QUALIFICATION_COMPLETE_PENDING_SEMANTIC_ACCEPTANCE
SOURCE_QUALIFICATION_INCOMPLETE_CLOSE_CYCLE4
SOURCE_ACCESS_BLOCKED_NO_CONCLUSION
```

### Complete

Requires every fixed instrument and domain to be complete without fabrication.
It does not authorize a database write. Return to the Manager.

### Incomplete

List the exact missing/conflicting domains and recommend:

```text
CLOSED_DATA_AND_SEMANTIC_CONTRACT_INCOMPLETE_NO_OUTCOME
```

Do not propose a broader universe, parameter change, or source fusion.

### Access blocked

Use only when source access or configured credential availability prevented a
meaningful qualification. Do not silently substitute a weaker source.

## Validation

Before opening the result PR:

```text
strict JSON parse passes
duplicate JSON keys rejected
nonfinite values absent
all three fixed ETF identities present
all units explicit
all source URLs HTTPS and credential-free
no database write
no Git-tracked raw payload or credential
no returns/NAV/trend/gates
exact one-result-file scope
```

## Terminal callback

```text
STATUS:
QUALIFICATION_PR_URL:
HEAD_SHA:
RESULT_URL:
RESULT_SHA256:
FIXED_SYMBOLS:510300.SH,511010.SH,518880.SH
PRODUCT_IDENTITY:
RAW_OHLC:
VOLUME_SHARES:
AMOUNT_CNY:
ADJUSTMENT_IDENTITY:
SUSPENSION_HANDLING:
LIMIT_SEMANTICS:
DISTRIBUTION_EVENTS:
OTHER_CORPORATE_ACTIONS:
COMMON_QUALIFIED_DATE_COUNT:
HISTORICAL_AVAILABILITY_CLASSIFICATION:
SOURCE_MATRIX_COMPLETE:
DATABASE_WRITE:false
STRATEGY_OUTCOME_ACCESS:false
NEXT_ACTION:
```

## Boundary

Read-only data research. No strategy recommendation, candidate, readiness,
broker, order, paper, live, or automatic execution.
