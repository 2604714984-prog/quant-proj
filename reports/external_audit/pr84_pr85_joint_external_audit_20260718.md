# Joint External Audit — PR #84 and PR #85

Date: 2026-07-18  
Repository: `2604714984-prog/quant-proj`

## Exact review targets

```text
PR #84 HEAD=44199bc4ec9f825750283c62b0242f7981f30fd6
PR #85 HEAD=c9f380f2b510fc26d142631dba2604eb6c755581
```

## Verdicts

```text
PR_85_PRICE_VOLUME_FEASIBILITY=ACCEPT_TERMINAL_FEASIBILITY_CLOSE
PR_85_ROADMAP=REWORK_REQUIRED_BEFORE_MERGE

PR_84_PREFLIGHT=ACCEPTED
PR_84_MERGE_OR_OUTCOME=NARROW_REWORK_REQUIRED

ARCHITECTURE_REBUILD_REQUIRED=false
STRATEGY_CANDIDATE_AVAILABLE=false
```

## PR #85 adjudication

The China price-volume trend replication lane is correctly closed as:

```text
FEASIBILITY_BLOCKED_CLOSE_NO_ADAPTER_NO_OUTCOME
```

The published factor is not a simple price-up/volume-up rule. It requires 18 price/volume signals, monthly cross-sectional coefficient estimation, recursive EMA forecasts, market-cap and E/P controls, exclusion of the smallest 30%, value-weighted long-short portfolio formation, and point-in-time financial availability. The local snapshot lacks non-null `total_mv`/`circ_mv`, an E/P equivalent, and A-share `available_at`; the author workbook contains factor returns rather than stock-level formation inputs. The feasibility JSON truthfully preserves those gaps and crosses no outcome, write, forward, or candidate boundary.

Two roadmap corrections are mandatory:

1. Restore precedence:

```text
latest explicit user instruction
> manager_v2_control_constitution_v2_20260716.md
> merged AGENTS.md
> current roadmap
> accepted task artifact
```

2. Replace the internally inconsistent `high-prior` stop budget with a prospective budget applying to every new economic-hypothesis lane, whether it closes at feasibility, preflight, or outcome. Recommended operating form:

```text
budget_effective_from=PR_85_MERGE_COMMIT
maximum_additional_research_lanes=2
consumed_after_effective_commit=0
remaining_additional_research_lanes=2
```

## PR #84 adjudication

The aggregate preflight is accepted:

```text
PREFLIGHT_PASS
split intervals=23 / 23 / 29
minimum selected=30
invalid interval/variance/panel counts=0
holding returns opened=false
holdout/forward opened=false
```

Before merge or historical outcome, make four narrow corrections:

1. Remove the active import from the closed Family42 module `quant_system.backtest.permanent_portfolio`. Implement the tiny deterministic three-month PCG64 circular-start routine privately in the Relative Variance module. Do not create a statistics framework.
2. Replace discretionary `candidate_exclusions` wording with one exhaustive allowed exclusion list matching the preflight query; forbid all additional filters and replacements.
3. Freeze one unambiguous historical return representation. QFQ-signal data, raw execution opens, adjusted marks, and corporate actions cannot remain implicit. A secondary QFQ screen must be labelled non-executable and non-candidate; an account-level Event Loop result requires complete corporate-action semantics.
4. After corrected PR #85 merges, rebase PR #84 and remove its roadmap modification. PR #85 remains the single roadmap authority.

Do not alter the exposure formula, windows, 50-bps cost, validation split, alpha, or gates in response to this audit.

## Merge and research order

```text
1. Correct PR #85 roadmap text.
2. Delta-review and merge PR #85.
3. Rebase PR #84 onto updated v2-main and drop its roadmap file.
4. Apply PR #84 narrow semantic fixes.
5. Run focused/full CI and request delta review.
6. If accepted, run validation only.
7. Open retrospective holdout only after an accepted validation pass.
8. Start no other code-writing family meanwhile.
```

## Development priority

The main development priority remains strategy research, not architecture. The immediate sequence is:

```text
Relative Variance exact validation decision
-> low abnormal-turnover / anti-speculation input feasibility
-> one final high-prior lane under the prospective stop budget
```

Macro Risk remains read-only Shadow. Strategy combination remains blocked until two independently passing families also have prospective Shadow evidence.
