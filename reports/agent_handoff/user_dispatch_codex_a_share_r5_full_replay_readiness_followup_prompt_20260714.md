# User-Dispatch Prompt — Codex A-Share R5 Full-Replay Readiness Follow-Up

Copy the complete fenced prompt below into the existing independent user-controlled Codex A-share conversation.

```text
RUN CODEX_A_SHARE_R5_FULL_REPLAY_READINESS_FOLLOWUP_20260714

WORKSTREAM:
A_SHARE_RESEARCH_CODEX_USER_CONTROLLED_INDEPENDENT

AUTHORITATIVE INTEGRATED AUDIT:
https://github.com/2604714984-prog/quant-proj/blob/71b97f6131fa211e2a5ed7e6c8d2b968a9b7bbb7/reports/external_audit/project_wide_remediation_integrated_external_audit_20260714.md

ISSUE-LEVEL AUDIT RECEIPT:
https://github.com/2604714984-prog/quant-proj/issues/26#issuecomment-4969889384

TARGET REPOSITORY:
https://github.com/2604714984-prog/quant_research_lab

AMEND THE EXISTING PR:
https://github.com/2604714984-prog/quant_research_lab/pull/6

CURRENT BRANCH:
codex/a-share-r5-mainline-integration-20260714

CURRENT AUDITED HEAD:
4e65fbe5889d6815a8454f80d1ea96ee0802c192

DO NOT CREATE R6, A NEW ENGINE, A NEW REPOSITORY, OR A SECOND PR.
PUSH THE NARROW FOLLOW-UP COMMITS TO THE EXISTING PR #6 BRANCH.

==================================================
MISSION
==================================================

Make the existing R5 engine safe and proportionate for an approximately CNY 400,000 personal
A-share research account, and make its code ready to consume a future accepted read-only central DB
callback.

This task does not run the full replay and does not select a strategy.

Allowed completion label:

```text
R5_FULL_REPLAY_CODE_READY_WAITING_FOR_ACCEPTED_DB_CALLBACK
```

Forbidden labels:

```text
FULL_REPLAY_COMPLETE
VALIDATED_STRATEGY
STRATEGY_CANDIDATE_AVAILABLE
SYSTEM_INTAKE_READY
REGIME_SWITCHING_EDGE
```

==================================================
CURRENT ACCEPTED WORK — DO NOT REBUILD
==================================================

Keep the already accepted implementations:

- causal D-close signal -> next-session execution;
- regime state/probability lag to the next actual session;
- train-only probabilistic detector fitting and hashes;
- sell-before-buy ordering;
- retained-position resize;
- reconciliation framework;
- dated tradability interface;
- clean wheel build and installed focused CI;
- fail-closed full-mode callback verification;
- frozen H1-H8/H11-H12 definitions;
- H9/H10 blocked.

Do not change strategy formulas, regime thresholds, GMM candidates, state-to-sleeve mapping, split
boundaries, or selection conclusions in this task.

==================================================
HARD ANTI-OVERDESIGN AND NON-SCOPE
==================================================

1. Modify only the existing R5 implementation.
2. No new event engine, allocator framework, DSL, plugin system, portfolio service, registry, database
   adapter framework, or generic execution platform.
3. No central DB read/write, provider call, strategy outcome run, parameter search, candidate
   promotion, or test-result selection.
4. Do not implement a full bottom-up regime allocator in this patch. The current return-level allocator
   must be labelled diagnostic-only; a bottom-up implementation may be separately considered only if
   at least two static specialists survive the future full replay.
5. Runtime net growth should remain below approximately +350 lines. Prefer replacing incorrect code
   and deleting tracked generated artifacts.
6. Do not add another required CI job. Amend the existing single test workflow.
7. Do not commit new Parquet, CSV, database, raw provider, or cache artifacts.
8. Only three concise evidence files may be added/updated:

```text
reports/codex_a_share_r5_repair/r5_full_replay_readiness_closeout_20260714.md
reports/codex_a_share_r5_repair/r5_full_replay_readiness_gate_20260714.json
reports/codex_a_share_r5_repair/r5_full_replay_readiness_pytest_20260714.xml
```

9. Any required change outside the allowlist below returns:

```text
SCOPE_EXPANSION_REQUIRES_USER_APPROVAL
```

==================================================
FILE ALLOWLIST
==================================================

```text
src/a_share_research_r5/config.py
src/a_share_research_r5/types.py
src/a_share_research_r5/accounting.py
src/a_share_research_r5/event_loop.py
src/a_share_research_r5/metrics.py
src/a_share_research_r5/signals.py
src/a_share_research_r5/specialists.py
src/a_share_research_r5/allocators.py
src/a_share_research_r5/gates.py
scripts/run_a_share_research_r5.py
tests/test_a_share_r5_accounting.py
tests/test_a_share_r5_event_loop.py
tests/test_a_share_r5_hypotheses.py
tests/test_a_share_r5_static_allocator.py
tests/test_a_share_r5_soft_allocator.py
tests/test_a_share_r5_hard_allocator.py
tests/test_a_share_r5_packets_and_gates.py
tests/test_a_share_r5_full_replay_readiness.py
.github/workflows/test.yml
.gitignore
pyproject.toml only if required for installed-test behavior
three concise evidence files listed above
```

Do not touch unrelated C2 files, central-data code, legacy A_Share source, or historical strategy
reports.

==================================================
PART 1 — FAIL-CLOSED HELD-POSITION VALUATION
==================================================

AUDIT DEFECT

`EventLoopEngine._market_value()` currently uses zero when a held symbol is absent from the supplied
price map. A missing open or close can therefore create a false -100% loss while reconciliation still
appears internally consistent.

REQUIRED POLICY

Maintain explicit last-accepted marks inside the existing EventLoopEngine.

For a held symbol on date D:

A. VALID CURRENT PRICE

- use the current finite positive price;
- update the last-accepted mark only when the value is accepted under the dated status contract.

B. CONFIRMED SUSPENSION

- use the latest prior accepted close for valuation;
- do not fill an order;
- record stale valuation evidence including symbol, date, reason and stale age;
- if no prior accepted mark exists, fail closed.

C. CONFIRMED DELISTING / TERMINAL EVENT

- require a finite explicit `terminal_value` from the dated input contract;
- apply the terminal accounting once according to a small explicit policy;
- do not infer zero value merely from a missing bar;
- if terminal evidence is absent or contradictory, fail closed.

D. UNEXPLAINED PROVIDER GAP

- fail the research run; do not silently use zero;
- do not forward-fill indefinitely;
- no positive strategy/gate result may survive such a gap.

IMPLEMENTATION LIMIT

Do not create a new pricing service or module. Implement the smallest reusable valuation helper within
`event_loop.py`, `accounting.py`, or existing types.

REQUIRED EVIDENCE

Extend daily evidence with concise fields such as:

```text
stale_valuation_count
terminal_event_count
valuation_gap_count
```

Holdings evidence should identify stale/terminal rows without producing a new report framework.

MANDATORY TESTS

1. Held symbol missing close + confirmed suspension carries prior accepted mark, not zero.
2. Held symbol missing open + confirmed suspension can be valued for pretrade equity but cannot fill.
3. Held symbol missing bar + no dated explanation raises a stable fail-closed exception.
4. Held symbol reaches delisting with terminal value: terminal accounting is applied exactly once.
5. Delisting without terminal value fails closed.
6. Missing prior mark fails closed.
7. A missing price cannot produce a silent -100% equity step.

==================================================
PART 2 — REAL CAPITAL AND EXECUTABLE POSITION COUNT
==================================================

AUDIT DEFECT

The current engine defaults to CNY 1,000,000 and treats the top 20% bucket as the final portfolio. For
an approximately CNY 400,000 account this can create hundreds of theoretical targets, zero-share
orders, and low-price selection bias.

REQUIRED CONFIG

Add the smallest explicit fields to `EngineConfig`:

```text
initial_cash
max_positions
minimum_position_lots or equivalent feasibility rule
```

Use these code defaults for personal-account smoke/research readiness:

```text
initial_cash = 400_000 CNY
max_positions = 15
lot_size = 100
```

The future full replay config may override `initial_cash` and `max_positions`, but must record the
actual user-authorized capital. Do not silently fall back to one million.

CANDIDATE POOL VS FINAL PORTFOLIO

Keep the preregistered `bucket_pct=0.20` as the candidate-pool rule.

Then construct the final executable target set as:

```text
ranked top-20% candidate pool
-> remove names that cannot purchase at least one configured lot under provisional equal weight
-> continue down the ranked candidate pool until max_positions is reached or candidates are exhausted
-> equal-weight only the final feasible names
```

Requirements:

- maximum final positions never exceeds `max_positions`;
- bucket percentage is applied once;
- no position is included with zero target shares;
- skipped unaffordable names are counted in evidence;
- if no feasible target remains, use the frozen cash fallback;
- retained targets are still resized through the existing incremental order logic.

Add concise evidence fields:

```text
candidate_pool_size
final_target_count
unaffordable_candidate_count
```

MANDATORY TESTS

1. A large universe produces a 20% candidate pool but no more than 15 final positions.
2. With CNY 400,000 and 100-share lots, an unaffordable high-price name is skipped rather than
   generating a zero-share target.
3. The engine fills the available slots from later ranked feasible candidates.
4. Final target weights sum to the permitted invested budget.
5. No holdings row has zero shares.
6. Custom capital and max-position values are honored.

==================================================
PART 3 — PROPORTIONATE A-SHARE COST CONTRACT
==================================================

The current bps-only cost contract is not sufficient for a CNY 400,000 account because minimum
commission can dominate small orders.

Extend the existing `CostConfig` and `execution_amounts()` only as needed to support:

```text
commission_bps
minimum_commission_cny
sell_stamp_duty_bps
transfer_fee_bps
slippage_bps
```

Rules:

- commission is charged separately on each filled buy/sell order;
- commission per order is `max(bps commission, minimum commission)`;
- stamp duty is sell-only;
- transfer fee direction follows the supplied full-replay cost config;
- slippage is applied exactly once;
- no-trade/rejected order has zero cost;
- reconciliation uses the same cost values as fills;
- the future full replay must provide an explicit user/broker cost profile rather than relying on an
  undocumented historical assumption.

Do not add a date-versioned fee database in this patch. The future full replay may use one documented,
conservative frozen fee schedule plus 2x stress.

MANDATORY TESTS

- small order triggers minimum commission;
- larger order uses bps commission;
- sell order charges commission + stamp duty + configured transfer fee;
- buy order does not charge sell stamp duty;
- rejected/no-trade order charges zero;
- reconciliation remains inside tolerance.

==================================================
PART 4 — CORRECT PERFORMANCE-METRIC NAMES
==================================================

`equity_metrics()` currently calculates CAGR divided by annualized volatility and labels it `sharpe`.

Required change:

```text
sharpe = annualized mean daily excess return / annualized daily-return volatility
```

Use a frozen zero risk-free rate by default unless a future config supplies another rate.

If CAGR/volatility remains useful, expose it separately as:

```text
cagr_to_volatility
```

Do not compare the old value with standard Sharpe as though they were the same metric.

Tests must use a hand-calculated return series and verify both fields.

==================================================
PART 5 — CURRENT REGIME ALLOCATORS MUST BE DIAGNOSTIC-ONLY
==================================================

The one-session lag repair is accepted. However, the current allocator operates on family return
series produced by averaging independently capitalized strategy equity curves. It is not yet a
stock-holdings-level shared account.

Do not build a new bottom-up allocator in this patch.

Instead:

1. Add explicit metadata to all current return-level allocator results:

```text
evidence_level = DIAGNOSTIC_FUND_OF_FUNDS_APPROXIMATION
system_intake_eligible = false
```

2. `gates.py` and packet validation must reject these allocator results as strategy/system-intake
   evidence.
3. Rename or annotate outputs so they cannot be confused with executable stock-level allocation.
4. Smoke may continue to test the diagnostic allocator timing and costs.
5. Future full replay may report the diagnostic comparison, but no dynamic allocator may be promoted.
6. A bottom-up stock-level allocator may receive a separate user dispatch only if at least two static
   sleeve specialists survive the future train/validation/full replay. It must reuse EventLoopEngine,
   not create another engine.

MANDATORY TESTS

- diagnostic allocator output carries both metadata fields;
- packet/gate rejects it for system-intake evidence;
- static individual-strategy evidence remains distinct;
- no result label can claim regime-switching strategy readiness from the diagnostic allocator.

==================================================
PART 6 — CENTRAL DB INPUT CONTRACT NAME ALIGNMENT
==================================================

The future callback contract and the current engine use different names for several dated fields.
Do not silently rely on aliases during full replay.

Add one small, explicit input-normalization function or contract check—inside the existing script or
engine code, not a new framework—that maps or rejects fields such as:

```text
is_suspended -> suspended
list_date -> listing_date
delist_date -> delisting_date
```

For limit execution, require an explicitly decision-time-safe field. Do not infer an open fill from the
execution day's closing condition. If the snapshot supplies only `up_limit`/`down_limit`, use a frozen
conservative open rule or reject the callback until the exact engine-ready status field exists.

The full-mode callback validator must prove that every field needed by EventLoopEngine can be
constructed without future information.

Required tests:

- accepted callback/fixture maps every required engine field explicitly;
- unknown or contradictory aliases fail closed;
- missing dated status field blocks full replay;
- no D close-derived field decides D open execution.

==================================================
PART 7 — REMOVE GENERATED RUNOPS BINARIES FROM THE ACTIVE PR
==================================================

PR #6 currently carries generated smoke Parquet/CSV evidence. Preserve the historical commits, but do
not require these generated files in the active mainline integration diff.

Required policy:

- remove generated `reports/runops/a_share_r5/*.parquet` and large generated CSV files from the active
  PR where practical without rewriting history;
- keep only concise JSON manifests/hashes, JUnit, test matrix and closeout evidence;
- CI generates smoke artifacts under `/tmp` and validates them there;
- update `.gitignore` so future generated runops binaries are not committed;
- do not delete immutable historical Git evidence.

This cleanup must not remove source, tests, frozen hypothesis manifests, or concise audit evidence.

==================================================
PART 8 — FULL MODE REMAINS BLOCKED
==================================================

Do not run `--mode full` in this task.

After code repair, full mode must still return a refusal unless:

1. an accepted immutable read-only central DB callback exists;
2. actual callback bytes/DB/export are verified;
3. required engine-ready dated fields are present;
4. actual capital and broker cost profile are supplied;
5. the user issues a fresh full-replay dispatch.

Allowed status:

```text
R5_FULL_REPLAY_CODE_READY_WAITING_FOR_ACCEPTED_DB_CALLBACK
```

==================================================
FOCUSED CI
==================================================

Amend the existing single workflow only.

Required sequence:

```text
compile / Ruff
build wheel
clean install outside repository root
focused R5 tests
bounded smoke in /tmp
artifact schema/hash checks
verify no generated Parquet/CSV is newly tracked
```

No second required CI job.

Run all existing R5 tests plus the new full-replay-readiness tests.

==================================================
ACCEPTANCE GATES
==================================================

MISSING_PRICE_GATE:

- no zero-default held valuation;
- suspension, terminal event and unexplained gap tests pass;
- missing prior mark fails closed.

CAPITAL_GATE:

- default personal baseline is CNY 400,000;
- final positions <= 15 by default;
- 20% is a candidate pool, not hundreds of final holdings;
- lot feasibility and unaffordable-name replacement pass.

COST_GATE:

- minimum commission and direction-specific fees are tested;
- fill and reconciliation costs match.

METRIC_GATE:

- standard Sharpe test passes;
- CAGR/volatility is separately named.

ALLOCATOR_GATE:

- current return-level soft/hard results are explicitly diagnostic-only;
- system-intake gate rejects them;
- no bottom-up allocator is added in this patch.

DATA_CONTRACT_GATE:

- dated field mapping is explicit and causal;
- callback with missing/unsafe fields is rejected.

ARTIFACT_GATE:

- CI smoke artifacts are generated and verified outside the repository;
- no new runops Parquet/CSV is tracked.

BOUNDARY_GATE:

- full replay not run;
- no strategy outcome, promotion, recommendation or trading path;
- `strategy_candidate_available=false`.

==================================================
GITHUB PROCEDURE
==================================================

Work on the existing PR #6 branch.

```bash
git status --short --branch
git rev-parse HEAD
# verify HEAD is the current PR head or record the new remote head before edits

git add <allowlisted source, tests, workflow and concise evidence only>
git diff --cached --check
git commit -m "A-share R5: make personal-capital replay path fail-closed and executable"
git push

git rev-parse HEAD
git ls-remote origin refs/heads/codex/a-share-r5-mainline-integration-20260714
git status --short --branch
```

Do not merge the PR. Return the new exact head to the user for external re-review.

==================================================
BOUNDARY
==================================================

Authorized:

- the narrow R5 source/test/workflow changes above;
- generated-artifact cleanup;
- updates to existing PR #6.

Not authorized:

- central DB access/write;
- provider/network fetch;
- full replay or strategy result inspection;
- formula/threshold/state-map changes;
- new strategies or parameter search;
- bottom-up regime allocator implementation;
- strategy candidate/readiness promotion;
- recommendation, broker, order, paper, live, or auto execution;
- secret output.

==================================================
CALLBACK
==================================================

BATCH: CODEX_A_SHARE_R5_FULL_REPLAY_READINESS_FOLLOWUP_20260714
STATUS:
PR_URL: https://github.com/2604714984-prog/quant_research_lab/pull/6
BRANCH: codex/a-share-r5-mainline-integration-20260714
BASELINE_HEAD: 4e65fbe5889d6815a8454f80d1ea96ee0802c192
NEW_HEAD:
IMMUTABLE_COMMIT_URL:
REMOTE_VERIFICATION_OUTPUT:
WORKTREE_STATUS:
RUNTIME_NET_LINE_DELTA:
MISSING_PRICE_STATUS:
TERMINAL_EVENT_STATUS:
CAPITAL_BASELINE_CNY:
MAX_POSITIONS_DEFAULT:
LOT_FEASIBILITY_STATUS:
MINIMUM_COMMISSION_STATUS:
COST_RECONCILIATION_STATUS:
SHARPE_STATUS:
ALLOCATOR_EVIDENCE_LEVEL:
ALLOCATOR_SYSTEM_INTAKE_ELIGIBLE: false
DATA_CONTRACT_ALIGNMENT_STATUS:
GENERATED_ARTIFACT_CLEANUP_STATUS:
FOCUSED_TEST_COUNT:
CI_URL:
FULL_REPLAY_STATUS: BLOCKED_WAITING_FOR_ACCEPTED_DB_CALLBACK_AND_FRESH_USER_DISPATCH
SYSTEM_INTAKE_READY: false
STRATEGY_CANDIDATE_AVAILABLE: false
FIXES_REQUIRED:
NEXT_ACTION: EXTERNAL_REVIEW_OF_NEW_EXACT_HEAD
```
