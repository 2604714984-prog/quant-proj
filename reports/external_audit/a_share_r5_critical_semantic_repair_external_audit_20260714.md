# A-Share R5 Critical Semantic Repair — External Audit

Date: 2026-07-14

## Audit targets

### Authoritative R5 repair

- repository: `2604714984-prog/quant_research_lab`
- branch: `codex/a-share-r5-critical-semantic-repair-20260714`
- commit: `320c344f4c6eb7ddd6d8a790b0b13dd087a3fbd0`
- baseline: `d5e902af4beab6826ebc34c9a940b881f25ad750`
- CI run: `https://github.com/2604714984-prog/quant_research_lab/actions/runs/29328874289`

### Legacy A-share semantic repair

- repository: `2604714984-prog/A_Share_Monitor`
- branch: `codex/a-share-canonical-semantic-repair-20260714`
- commit: `a82ac7de579a9240e30bca85e01893deb45c4eff`
- preservation baseline: `1a64e70873fc8a3c3d998e509cbcf690010ffef0`
- divergent reviewed main: `ab12cf99331a39a1396c7c7f885072a9f0f68c08`
- CI run: `https://github.com/2604714984-prog/A_Share_Monitor/actions/runs/29329049359`

## Verdict

`ACCEPT_CODE_REPAIR_STAGE_WITH_CARRY_FORWARD_WARNINGS`

The submitted changes close the specific code-repair findings from the repository-wide audit sufficiently to freeze these commits as the accepted pre-database semantic baseline.

This verdict does **not** accept a strategy, a full-data replay, a central-database callback, system intake, paper trading, or any execution route.

```text
CODE_REPAIR_STATUS=ACCEPTED
FULL_REPLAY_STATUS=BLOCKED_WAITING_FOR_ACCEPTED_DB_CALLBACK_AND_FRESH_USER_DISPATCH
SYSTEM_INTAKE_READY=false
STRATEGY_CANDIDATE_AVAILABLE=false
```

## Accepted R5 scope

1. **Same-day regime lookahead is repaired for the current allocator interface.**
   - Dynamic state/probability decisions are mapped to the next actual session.
   - The first row falls back to cash when no prior decision exists.
   - Decision date, effective date, and `state_lag_sessions=1` are recorded.
   - Turnover and cost are charged on the effective date.
   - The alternating-winner reproduction records the old artificial path (`1.4641`) and the repaired lagged path (`0.7290`).

2. **Failure-sensitive timing tests exist and passed.**
   - Same-day state mutation cannot alter same-day return.
   - Dynamic decisions take effect on a later session.
   - Missing prior probability does not forward-fill future state.

3. **Packaging is repaired.**
   - `a_share_research_r5` is included in package discovery.
   - Wheel and sdist build in CI.
   - The wheel is installed into a clean virtual environment.
   - CI asserts the imported package resolves from the clean environment's `site-packages`.

4. **Independent CI is verified at the exact repair commit.**
   - GitHub Actions checked out `320c344f4c6eb7ddd6d8a790b0b13dd087a3fbd0`.
   - Compile, Ruff, build, clean install, 45 focused tests, bounded smoke, and artifact-hash checks completed successfully.

5. **The full replay remains fail-closed.**
   - No callback: return code 2.
   - Structurally accepted callback: full replay still returns code 3 and requires a fresh user dispatch.
   - No production central database was accessed or written.

## Accepted legacy A-share scope

1. Missing held prices now distinguish:
   - confirmed suspension/temporary halt;
   - explicit delisting terminal value;
   - unexplained provider gap with bounded stale tolerance;
   - missing prior mark, which fails closed.

2. Monthly and yearly return series now use consecutive period-end equity values, preserving cross-period boundary returns.

3. Simple benchmark difference is now named `excess_total_return`; the misleading alpha field was removed.

4. Absence of availability metadata can no longer yield a positive no-future PASS:
   - proven price-only columns: bounded warning;
   - fundamental, event, industry, membership, or unknown columns: fail.

5. Validation evidence controls selection. Test trade counts are diagnostic and cannot change the selection result.

6. GitHub Actions checked out `a82ac7de579a9240e30bca85e01893deb45c4eff` and completed the repository's full compile/JSON/safety/Ruff/pytest workflow successfully.

## Carry-forward warnings

### W1 — Meta-allocator execution interval must be proven in the full replay

The one-session lag fixes the audited same-day state/return leak. The current sleeve series are produced from strategy equity percentage changes, which are normally close-to-close account returns. A decision observed at close D can be executed no earlier than D+1 open.

Before treating soft/hard allocation as executable strategy evidence, the full replay must prove one of the following:

1. allocator returns are measured over the actual effective execution interval (for example D+1 open to D+1 close plus an explicit overnight policy); or
2. allocation is executed at underlying holdings level through the event loop; or
3. the sleeve allocator is explicitly labelled diagnostic-only and cannot produce system-intake evidence.

Do not silently treat close-to-close sleeve returns as if capital could be reallocated at the prior close after observing that close.

### W2 — The database callback validator is structural, not the final data audit

The current code verifies required fields and fail-closed flags, but it does not independently prove that:

- `owner_repository` and `owner_commit` resolve to the claimed Git object;
- the read-only database/export path exists;
- declared database/source/export hashes match actual bytes or registered dataset snapshots;
- every required field and PIT semantic is present in the physical data.

The Manager/database external audit must establish those facts before the callback is delivered to R5.

### W3 — The legacy PIT classifier is not the future source of truth

The legacy classifier is acceptably fail-closed for the audited missing-availability defect, but it remains a name-based heuristic. Central-database dataset contracts and the R5 snapshot callback must be authoritative for PIT status. Do not use the legacy heuristic to qualify new fundamental/event datasets.

### W4 — Canonical A_Share_Monitor branch integration remains a Manager task

The repair branch was created narrowly from the preservation baseline and intentionally did not merge divergent `origin/main`. The semantic patch is accepted, but the repository is not canonicalized until Manager:

- selects the canonical branch;
- integrates or cherry-picks the accepted semantic commits;
- tags the displaced branch state;
- confirms no safety fix is lost;
- removes duplicate research paths from active ownership later.

## Immediate project status updates

Manager should mark:

```text
P0-1_R5_ALLOCATOR_SAME_DAY_LOOKAHEAD=CLOSED
P0-2_A_SHARE_MISSING_PRICE_SEMANTICS=CODE_CLOSED_CANONICAL_MERGE_PENDING
P0-3_MONTHLY_YEARLY_RETURNS=CLOSED
P0-4_PIT_MISSING_FAIL_OPEN=CLOSED_FOR_LEGACY_PATH
P1-1_R5_PACKAGE_DISCOVERY=CLOSED
P1-2_R5_CLEAN_INSTALL_CI=CLOSED
P1-4_TEST_TRADE_COUNT_SELECTION=CLOSED
P1-5_EXCESS_RETURN_ALPHA_LABEL=CLOSED
```

Do not mark central PIT qualification or full replay complete.

## Required next operations

### Now

1. Freeze both accepted commits. Do not continue ordinary A-share code changes.
2. Send this audit result and the two immutable commits to Manager for the project remediation board.
3. Continue central-database minimalization and minimum-data ingestion.
4. Manager selects and integrates the canonical legacy A-share branch; no new research development should occur in `A_Share_Monitor`.
5. The independent Codex A-share conversation waits. It does not run full mode and does not add another framework.

### When Manager reports the database stage complete

1. Externally audit the minimal writer, shadow parity, backup/restore, and the immutable A-share callback.
2. Verify actual owner commit, read-only access, snapshot IDs/hashes, required fields, row/date coverage, natural-key uniqueness, and PIT/tradability qualification.
3. Only after that audit, send a fresh, narrow full-replay dispatch to the existing R5 branch.
4. The full replay must:
   - pin code, snapshot, config, hypotheses, detector, state map, and splits;
   - report train/validation before held-out test access;
   - freeze survivors;
   - use the test period once;
   - prove allocator execution-interval alignment;
   - compare static, soft, hard, and cash fallback;
   - preserve `NO_VALIDATED_A_SHARE_STRATEGY` as a valid result.
5. Submit the full replay once for external audit before any system-intake decision.

## External-audit trigger

```text
EXTERNAL_AUDIT_TRIGGER_OPEN=false for further code-repair work
NEXT_TRIGGER_1=central database minimal-writer cutover/callback
NEXT_TRIGGER_2=R5 full-data replay and strategy intake evidence
```

## Boundary result

`PASS_RESEARCH_ONLY`

No recommendation, ticket, strategy promotion, product/readiness activation, broker, order, paper, live, or automatic execution path is authorized.
