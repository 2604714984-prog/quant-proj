# Manager Task — Actual-Result Reset and US SPY State Baseline

Date: 2026-07-19  
Repository: `2604714984-prog/quant-proj`  
Authority: user request for actual empirical output rather than additional planning artifacts

## 1. Audit verdict

The project architecture remains reliable and lightweight, but the US-first phase has not produced a strategy or state result:

```text
PR #89: one input-qualification JSON -> US_STATE_OBSERVER_INPUT_BLOCKED
PR #90: one candidate-slate Markdown -> 0 proposed, 3 blocked, 1 rejected
PR #91: two adjudication/roadmap files -> no lineage, code, outcome or Shadow record
```

This is process activity, not strategy progress.

PR #91 exact head `988cdc212dd7bcf75d8a69e3f3d487b46f4d3527` is factually acceptable but must close without merge. Preserve the branch as selection memory. Do not merge another roadmap mutation.

## 2. Immediate operating reset

Until the result sprint below terminates, prohibit:

```text
new candidate slate
new roadmap or constitution
new literature-only PR
Qlib integration
RD-Agent integration
new provider framework
new database schema or writer
new state framework
new stock-selection family
Paper, broker, order or live work
```

The next substantive PR must contain an actual immutable historical result or a concise `INPUT_BLOCKED` result. It may not terminate as another plan.

## 3. Authorized result sprint

Dispatch exactly one implementation conversation using:

```text
reports/agent_handoff/us_spy_200d_state_baseline_result_task_20260719.md
```

This is a broad-market state benchmark, not a new Alpha discovery and not a resurrection of archived `us_momentum_41k` or `us_regime_41k`.

Purpose:

```text
Determine whether a simple, fully frozen SPY trend/cash gate has empirical value
on the already available retrospective US adjusted-price data.
```

## 4. Required output

The implementation PR must deliver:

```text
one frozen definition JSON
one small deterministic module or script
focused tests
one immutable result JSON
one immutable run receipt
```

Normal maximum:

```text
runtime code <= 250 lines
one implementation PR
one pre-result commit plus one result commit
no additional task or audit document
```

## 5. Decision handling

Allowed terminal states:

```text
RETROSPECTIVE_BASELINE_PASS_TO_SHADOW_REVIEW
RETROSPECTIVE_BASELINE_FAIL
INPUT_BLOCKED
```

Rules:

```text
PASS:
request exact-head external review; no automatic Shadow activation

FAIL:
merge concise negative evidence and close permanently

INPUT_BLOCKED:
merge one concise blocker result and stop; do not construct a provider/data platform
```

At every terminal state:

```text
strategy_candidate_available=false
paper_authorized=false
broker_authorized=false
live_authorized=false
```

## 6. Manager callback

Return only:

```text
STATUS:
PR_91_STATUS:
IMPLEMENTATION_TASK_URL:
RESULT_PR_URL:
RESULT_HEAD:
RESULT_STATUS:
PRIMARY_METRICS:
STRESS_METRICS:
RESULT_JSON_URL:
RUN_RECEIPT_URL:
STRATEGY_CANDIDATE_AVAILABLE: false
NEXT_ACTION:
```

## Final directive

The project has enough plans. The next accepted milestone is a reproducible number-bearing result, not another research route description.
