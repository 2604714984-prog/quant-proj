# DS A-Share C2 R4.1 Implementation External Audit Result — 20260713

## Audit target

- repository: `2604714984-prog/quant_research_lab`
- branch: `research/c2-remediation-r4-1-20260713`
- implementation commit: `b8edb61db6018976c9f7c952501f892cc9e4de87`
- immutable URL: `https://github.com/2604714984-prog/quant_research_lab/commit/b8edb61db6018976c9f7c952501f892cc9e4de87`

## Verdict

`REJECT_R4_1_IMPLEMENTATION_COMMIT_INCOMPLETE_AND_NONRUNNABLE`

The commit is not accepted as `R4_1_METHOD_PATCH_COMPLETE_WAITING_FOR_DB_SNAPSHOT`.

It may be retained only as:

`R4_1_PARTIAL_EVENT_LOOP_DRAFT`

The rejection is independent of the pending central-database callback. The submitted implementation commit is structurally incomplete, its behavioral test module cannot be collected successfully against the committed pipeline, and the claimed allocator/GMM/selection/packet/gate implementations are absent from the committed source.

## Accepted partial scope

The following code-level direction is useful and may be preserved in the next patch:

1. The branch and immutable commit resolve remotely.
2. The event loop processes queued orders at the start of the scheduled execution date and forms new signals after marking the current date.
3. Invalid/non-positive execution open is explicitly rejected.
4. Buy and sell commission fields, sell stamp duty, and slippage-adjusted execution prices are represented in the execution record.
5. H3 contains an explicit dated breadth check.
6. The task keeps the central snapshot as pending and does not claim strategy-candidate status.

These points are design progress only; no full-run or accepted method evidence exists.

## Critical findings

### 1. The committed pipeline ends during H5 and does not contain Parts 5–10

`scripts/run_c2_remediation_r4_1_pipeline.py` is only 342 lines and ends inside the H5 signal implementation. It does not contain committed implementations for:

- H6, H7, H8, H11, H12;
- hypothesis configuration and simulation execution;
- shared-capital static allocator;
- probability-weighted soft allocator;
- confirmed-state hard allocator;
- fallback allocator;
- train-only BIC component selection;
- model/scaler serialization and hashes;
- daily OOS probability output;
- selection ledger;
- packet generation/finalization;
- evidence-derived gates;
- callback generation.

Therefore the commit message and fix board overstate the committed implementation.

### 2. The behavioral tests cannot import the committed pipeline

`tests/test_c2r4_1_behavioral.py` imports `sig_H8`, but the committed pipeline defines only through `sig_H5`. Test collection should fail with an import error before assertions run.

The test module also imports the pipeline as a module, while the pipeline performs full 8.7M-row database loading at import time and has no `if __name__ == "__main__"` guard. This prevents isolated, portable unit tests and can trigger the same long-running workload during test collection.

No GitHub Actions run or committed pytest/JUnit transcript exists for the implementation commit.

### 3. The run transcript proves the pipeline did not execute the claimed parts

The committed `pipeline_output.txt` stops immediately after:

- Part 0;
- data loading;
- Part 1–3 declaration;
- Part 4 declaration.

It contains no simulation results, test results, allocator output, GMM output, selection ledger, packets, gates, or callback.

### 4. The H1 implementation contains a control-flow defect

The line:

```python
if len(dd)<5: return []; dd.loc[:,"_s"]=(dd["return_60"]+dd["return_20"])/2
```

places the `_s` assignment inside the one-line `if` suite after a return. When `len(dd) >= 5`, `_s` is not created, and the following `nlargest(..., "_s")` path should fail.

### 5. Target-universe rebalancing remains incomplete

The event loop creates orders only for symbols present in the new target set. It does not create sell orders for holdings removed from the target set. If a regime becomes inactive or the target set becomes empty, existing positions remain held rather than moving to cash/fallback.

This also means:

- stale holdings accumulate;
- regime deactivation is not enforced;
- fallback behavior is not implemented;
- the claimed incremental target-weight rebalance is incomplete.

### 6. Order execution ordering and sizing remain unsafe

Queued orders are processed in queue order rather than deterministically processing sells before buys. A buy may be rejected for insufficient cash even though same-date sells should fund it.

The engine calculates sell notional and costs before bounding the requested sell shares to actual holdings. Although the current queue generator may normally request a bounded net sale, the accounting function itself is not robust to an oversized sell order.

### 7. Execution-date tradability is still incomplete and contains future-information risk

The committed implementation checks only:

- open validity;
- static `is_st`;
- `is_limit_up`.

It does not load or enforce:

- suspension history;
- dated ST history;
- listing/delisting dates;
- execution-date limit-down sell restriction;
- locked-limit semantics;
- execution-date tradability history.

Moreover `is_limit_up`/`is_limit_down` are derived from the execution date's closing price versus limit price. Using D+1 close to decide whether an order could execute at D+1 open introduces future intraday information.

### 8. Bucket-size logic double-applies the percentage

Signal functions such as H1/H2/H3 already return approximately the top 20% of their eligible universe. The event engine then applies `bucket_pct` again to the returned signals, selecting approximately 20% of that 20% set. This is about 4% of the original eligible universe, not the preregistered 20%.

### 9. The tests remain weak even before the import failure

Examples:

- sell-commission test is vacuous when no sell occurs;
- H3 breadth test inspects source text rather than testing low/high breadth behavior;
- bucket-size test checks only that some orders exist, not the required selection count;
- no-test-leak test checks only date ordering;
- there are no allocator, GMM, packet, selection-ledger, or exit-gate behavioral tests in the committed test file.

### 10. The evidence boards are declarative and contradicted by the source

The critical-fix board marks all 22 findings `FIXED_AND_TESTED`, including allocators, GMM hashes, packet finalization, and evidence-derived gates, although those implementations are not present in the pipeline.

The hypothesis-fidelity CSV marks H6/H7/H8/H11/H12 as implemented even though the pipeline does not define those functions.

These artifacts are not accepted as generated evidence.

### 11. Required R4.1 artifacts and second commit are absent

The implementation commit does not contain the required:

- allocator daily equity/weights/trades;
- trade reconciliation;
- GMM component-selection report;
- model/scaler hashes;
- daily OOS probabilities;
- pytest XML/transcript;
- behavioral matrix derived from test results;
- selection ledger;
- packet templates/final packets;
- evidence-derived exit gates;
- callback envelope.

No packet-finalization commit has been submitted, which is consistent with the user's summary but confirms that R4.1 is not complete.

## Accepted status

```text
R4_1_IMPLEMENTATION_STATUS:
REJECTED_INCOMPLETE_NONRUNNABLE

EVENT_LOOP_STATUS:
PARTIAL_DRAFT

TEST_COLLECTION_STATUS:
EXPECTED_IMPORT_FAILURE

FULL_SIMULATION_STATUS:
NOT_RUN

STATIC_ALLOCATOR_STATUS:
NOT_COMMITTED

SOFT_ALLOCATOR_STATUS:
NOT_COMMITTED

HARD_ALLOCATOR_STATUS:
NOT_COMMITTED

FALLBACK_STATUS:
NOT_COMMITTED

GMM_TRAIN_ONLY_STATUS:
NOT_COMMITTED

SELECTION_LEDGER_STATUS:
NOT_COMMITTED

PACKET_STATUS:
NOT_COMMITTED

EXIT_GATE_STATUS:
NOT_COMMITTED

A_SHARE_DB_CALLBACK_STATUS:
WAITING

SYSTEM_INTAKE_READY:
false

STRATEGY_CANDIDATE_AVAILABLE:
false

S2_STATUS:
S2_CONTINUE_REQUIRED
```

## Required next patch

A narrow R4.1a implementation patch is required before any long full-data run:

1. Complete the pipeline source through every declared part.
2. Move data loading and execution behind a `main()` / `if __name__ == "__main__"` boundary.
3. Put reusable engine, allocator, detector, and validation components in import-safe modules.
4. Fix H1 control flow.
5. Add sell orders for removed targets and explicit liquidation on inactive/fallback states.
6. Process sells before buys; enforce robust share bounds and exact account reconciliation.
7. Add dated suspension/ST/listing/delist/limit execution contracts or explicit DB blockers.
8. Remove D+1-close-derived execution tradability decisions.
9. Correct bucket sizing so the preregistered percentage is applied once.
10. Implement shared-capital static/soft/hard/fallback allocators with daily ledgers.
11. Implement train-only component selection, model/scaler hashes, and daily OOS probabilities.
12. Add a real selection ledger and evidence-derived gates.
13. Replace weak tests and prove test collection/execution with a committed pytest/JUnit transcript.
14. Run a bounded toy/smoke workload first; only then run the 8.7M-row full workload.
15. Submit the implementation commit, followed by the required packet-finalization commit after the DB callback and full run.

## Boundary result

`PASS_RESEARCH_ONLY`

No recommendation, strategy candidate, ticket, readiness/product route, daily signal, broker/order/paper/live/auto activation, or secret output is accepted.

## Quant Manager action

- Register the implementation callback as received and externally rejected.
- Continue the central-database build independently.
- Do not release Codex strategy-packet system validation.
- Require R4.1a code completion and a passing bounded smoke/test package before authorizing the full-data computation.
- Keep `strategy_candidate_available=false` and `S2_CONTINUE_REQUIRED`.
