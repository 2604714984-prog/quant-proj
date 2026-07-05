# REASONIX_STRATEGY_R10_DRAFT_READY

## Status
RESEARCH_DRAFT — advisory sidecar for R10 strategy tasks; synthesized from compact task envelope and R9 state carry-forward; no candidate data reviewed in this session.

## PASS / WARN

| Task | Verdict | Rationale |
|---|---|---|
| A-R10-1 Conservative Momentum v2 | **PASS (design sound)** | Well-scoped: starts from R9 anchor, targets factor separation, defines measurable thresholds, constrains to A11 dataset. Risk: parameter-narrowing 6→1 from R9 may repeat if v2 thresholds are too tight. |
| A-R10-2 Robust Peer-Control Test | **PASS (design sound)** | Essential validity check. Single-robust risk is the top A-share fragility from R9. Peer comparison is the right next step. Risk: industry/liquidity matching may be confounded if 600177.SH is in a sparse peer group. |
| A-R10-3 A11 Leakage/Staleness Check | **PASS (design sound)** | Housekeeping task that is overdue. The snapshot-mismatch gate flagged in R9 A-share acceptance needs resolution. Risk: if leakage is found, all R5-R9 labels are conditional on remediation. |
| US-R10-5 Feedback Context Mapping | **PASS (design sound)** | Continues the R8/R9 test-fixture trajectory. Non-transactional feedback is a hard boundary; this task tests it programmatically. Risk: backlog scoring must not become a stealth eligibility score. |
| SW-R10-1 Research Decision Ledger | **PASS (design sound)** | Memo refresh is routine but important. R9→R10 state transitions (v2 spec, peer-control, staleness check, US metadata plan) need a single source of truth. |

No WARN or BLOCKED tasks. All five are well-scoped, research-only, and do not cross recommendation/product boundaries.

---

## Strategy Interpretation

### A-R10-1 — Conservative Momentum v2: Factor Separation

This is the logical R10 anchor task. The R9 outcome (1 robust, 1 recent-only, 4 fragile) raises a sharp question: **what factor(s) separate the 1 from the 5?** The v2 specification should isolate these dimensions:

| Factor | Hypothesis | Threshold Design Principle |
|---|---|---|
| **Momentum persistence** | Robust candidate has slower IC decay; fragile candidates show rapid decay or reversal | Require 60d→20d IC decay slope ≥ -0.005 (flat or positive). Fragile candidates likely fail here first. |
| **Drawdown cap** | Robust candidate avoids tail drawdowns that fragile candidates hit | Require max regime-level drawdown ≤ 20%. This alone may eliminate several BEAR_FRAGILE candidates. |
| **Liquidity floor** | Robust candidate trades in a liquidity regime that supports momentum; fragile candidates may be illiquid | Require avg daily volume ≥ 50M CNY. Small-cap momentum is often noise, not signal. |
| **Volatility cap** | Robust candidate's signal does not degrade in high-vol regimes; fragile candidates get washed out | Require high-vol-regime Sharpe ≥ -0.2 (not disastrously negative). |
| **Data completeness** | Robust candidate has clean, gap-free factor history; fragile candidates may have data artifacts | Require <5% missing periods in factor history; flag gaps >10 consecutive days. |

**Before/After projection (advisory estimate, not computed):**
- Input: R9 6-candidate set (1 ROBUST + 1 RECENT_ONLY + 4 BEAR_FRAGILE)
- After v2 thresholds applied to the full 203-record/152-symbol A11 dataset:
  - The single ROBUST candidate (600177.SH) should pass.
  - The RECENT_ONLY candidate (600060.SH) may or may not pass — likely fails momentum persistence.
  - The 4 BEAR_FRAGILE candidates almost certainly fail on ≥2 thresholds.
  - New candidates from the broader 152-symbol set may enter if they clear all 5 thresholds. This is the key value of expanding beyond the R9 6-candidate set.

**Fragility reduction:** If v2 identifies even 2-3 new candidates that pass all 5 thresholds, the single-point robust failure risk from R9 is materially reduced. If it identifies 0 new candidates, the momentum concept itself should be questioned — not the parameterization.

**Cautions:**
- v2 thresholds must be set before seeing the results, not tuned to include/exclude specific candidates. Pre-register the 5 threshold values in the R10 task spec to avoid data-snooping.
- The A11 dataset (203 records, 152 symbols) is still a small sample. A v2 pass rate of, say, 3/152 = 2% has a wide confidence interval.

---

### A-R10-2 — Robust Candidate Peer-Control Test

This task addresses the single most important R9 residual risk: **is 600177.SH genuinely distinctive, or is it a lucky sector/liquidity artifact?**

**Peer-matching design principles:**

| Dimension | Matching Approach | What to Test |
|---|---|---|
| **Industry** | Match to same GICS industry or Shenwan sector peers within Level2 1000-symbol universe | Is 600177.SH's return/Sharpe/drawdown profile top-decile within its industry? If no, the "robust" label is an industry effect, not a stock-specific signal. |
| **Liquidity** | Match to same avg-daily-volume decile peers | Is 600177.SH's momentum persistence unusual for its liquidity tier? Mid-cap momentum often looks better in backtest due to lower transaction costs being ignored. |
| **Size** | Match to same market-cap quintile | Does the candidate's drawdown resilience simply reflect being a large-cap in a flight-to-quality regime? |

**Output: peer percentile ranks for:**
- Return (annualized excess)
- Volatility (annualized)
- Max drawdown
- Liquidity (avg daily volume)
- One-lot affordability (share price × 100)
- Data quality (completeness %, gap count)

**Interpretation guardrails:**
- If 600177.SH is >80th percentile on return AND >80th percentile on drawdown resilience AND not in the most-liquid decile, it is plausibly a distinctive alpha candidate.
- If it's >80th percentile on return but only median on drawdown, the ROBUST label may be a bull-regime artifact — the 2022-23 bear test was not severe enough.
- If it's top-decile on liquidity, the signal may be a liquidity premium, not a momentum alpha.
- **This is not a ranking as a buy list.** It is a validity check on the ROBUST classification.

---

### A-R10-3 — A11 Dataset Leakage/Staleness Check

Housekeeping with potentially significant consequences.

**Verification checklist:**

| Check | Pass Condition | If Failed |
|---|---|---|
| **83-baseline isolation** | No R5-R9 report, config, or backtest references the old 83-candidate baseline as the active universe | Tag the stale reference; re-run affected analysis on current 203-record A11 dataset |
| **Snapshot ID consistency** | Current snapshot ID matches across all active configs, reports, and memo entries | Identify drift source; reconcile to current snapshot |
| **Run ID traceability** | Every backtest/report carries a run ID that maps to a specific A11 dataset version | Backfill missing run IDs; flag untraceable results |
| **Symbol count** | Active universe = 152 symbols (A11); no report uses a different count without explicit justification | Flag discrepancies; document acceptable deviations (e.g., sector sub-universes) |
| **Factor row count** | Factor data rows align with 203 records; no duplicate rows or missing symbols | Deduplicate; investigate gaps |
| **Candidate label consistency** | Same symbol+run combination does not carry conflicting labels (e.g., KEEP_RESEARCH in one report and DROP_FOR_NOW in another) | Resolve conflict; prefer most recent label; flag the mismatch |

**Risk:** If leakage is found (e.g., a REWORK_LATER backtest accidentally used the 83-candidate baseline), the affected R5-R9 candidate labels are conditional on re-running with the clean A11 dataset. This could change dispositions.

**Staleness check:** Any JSON artifact, report, or memo entry referencing a snapshot older than the current A11 snapshot should be flagged as `STALE_REFERENCE` and noted in the research ledger.

---

### US-R10-5 — Feedback Context to Research Backlog Mapping

This task extends the R8/R9 non-transactional feedback boundary into the research backlog system.

**Design constraints:**

1. Feedback context entries may populate research backlog fields: `signal_family`, `factor_z_scores`, `regime_note`, `data_quality_flag`, `config_parameter_suggestion`, `research_cycle`, `bucket`, `composite_score`, `filter_results`, `research_note`.

2. Forbidden fields must be blocked at the mapping layer, not just at the output layer:
   - `actionable_feedback_for_ticket` must never be set to `true`.
   - `eligibility_candidate` must never be created.
   - `buy_now`, `sell_now`, `entry_price`, `target_weight`, `position_size`, `allocation`, `order`, `broker` must never appear in any backlog record.

3. **Backlog scoring must be a research prioritization score, not a stealth eligibility score.** The distinction:
   - Allowed: "This candidate's signal decay slope is worsening; prioritize re-evaluation in R11."
   - Forbidden: "This candidate is ready for recommendation review."

**Test design:**

```python
# Conceptual test fixture

FORBIDDEN_IN_BACKLOG = {
    "buy_now", "sell_now", "entry_price", "target_weight",
    "position_size", "allocation", "order", "broker"
}

def test_no_forbidden_fields_in_backlog():
    for record in read_all_backlog_records():
        for field in FORBIDDEN_IN_BACKLOG:
            assert field not in record, f"Forbidden field in backlog: {field}"

def test_no_eligibility_candidate_created():
    assert count_eligibility_candidates() == 0

def test_actionable_feedback_never_true():
    for record in read_all_backlog_records():
        assert record.get("actionable_feedback_for_ticket") is not True

def test_backlog_scoring_is_research_only():
    # Backlog priority scores must be derived from research dimensions
    # (signal decay, data quality, regime flag), not from recommendation dimensions
    for record in read_all_backlog_records():
        assert "recommendation_score" not in record
        assert "trade_urgency" not in record
```

**Risk:** If the backlog scoring formula uses weights or thresholds that implicitly rank candidates by "trade readiness," the boundary is crossed even without explicit forbidden fields. The scoring methodology itself must be audited.

---

### SW-R10-1 — Research Decision Ledger Update

**Required entries for the R10 memo refresh:**

**A-share section:**
- Conservative momentum v2 specification drafted; 5-threshold design (momentum persistence, drawdown cap, liquidity floor, volatility cap, data completeness); awaiting execution on A11 dataset.
- Single robust candidate (600177.SH) peer-control test designed; industry/liquidity/size matching against Level2 1000-symbol universe.
- A11 dataset staleness/leakage check pending; R5-R9 labels conditional on clean verification.
- R9 state preserved: 1 ROBUST, 1 RECENT_ONLY, 4 BEAR_FRAGILE with dispositions; low-vol archived.

**US section:**
- DATA_BLOCKED status persists: 60 strong + 61 medium survivors all blocked on sector/asset-type metadata.
- Feedback-to-backlog mapping designed; non-transactional boundary hardened.
- 44-symbol metadata gap and sector-crosscheck blockers remain the binding constraint.
- Data-clear criteria defined but not yet satisfiable until metadata repair executes (HG-EXEC required).

**Cross-market:**
- R10 is a validation-and-cleanup cycle (peer-control, staleness, feedback boundary), not an expansion cycle.
- Research-only; no product gate; no recommendation language.

---

## Candidate-Quality Cautions

| Caution | Applies To | Detail |
|---|---|---|
| **Single-point risk unresolved** | A-share | R10's v2 spec and peer-control test can diagnose the single-robust problem but cannot fix it unless new candidates emerge from the broader A11 dataset. |
| **Threshold pre-registration** | A-R10-1 | If v2 thresholds are tuned post-hoc to include/exclude specific candidates, the v2 label is data-snooped. Thresholds must be set before running the A11 scan. |
| **Peer-group sparsity** | A-R10-2 | If 600177.SH is in a niche industry with <5 Level2 peers, the peer-control test has low statistical power. Flag this as a limitation, not a free pass. |
| **Leakage could unwind labels** | A-R10-3 | If the staleness check finds that fragile/rework candidates were evaluated against the wrong dataset, their dispositions may change. This is a feature, not a bug — but be prepared for label churn. |
| **US backlog scoring creep** | US-R10-5 | The feedback-to-backlog mapping is a narrow channel. Monitor for scope expansion: backlog scores must not become a ranking for "which candidates to monitor most closely for trading." |
| **Metadata repair still the US bottleneck** | US (all) | No amount of strategy research design can substitute for the missing sector/asset-type data. R10 US tasks are preparatory; real progress requires HG-EXEC metadata repair. |

---

## Memo Consistency Notes

**Pre-existing R9 items that must carry forward into R10:**

1. A-share low-vol overlay archived → must remain archived. No backdoor reactivation via v2.
2. 4 BEAR_FRAGILE dispositions (2 DROP_FOR_NOW, 1 REWORK_LATER, 1 KEEP_AS_STRESS_CASE) → must not be silently upgraded without explicit re-evaluation and a new walkforward.
3. US DATA_BLOCKED status → must not be described as "awaiting minor data fixes." The blockers (sector, asset-type, 44-symbol gap) are structural.
4. `product_read_allowed=false`, `production_recommendation_data_ready=false`, `broker/live/auto=false` → must remain false in all references.

**New R10 entries that must be added:**

5. v2 thresholds pre-registered values (to prevent post-hoc tuning).
6. Peer-control test methodology and peer-group definition.
7. A11 staleness check results (PASS/FAIL per check) and any label contingencies.
8. US feedback-to-backlog mapping rules and forbidden-field test results.

---

## Boundary Confirmation

| Boundary | Status |
|---|---|
| Buy/sell advice | ✅ Not present |
| Recommendation / ticket | ✅ Not present |
| PENDING_HUMAN_REVIEW | ✅ Not emitted |
| Eligibility candidate | ✅ Not created |
| Product-route activation | ✅ Not present |
| Production readiness | ✅ Not claimed |
| Broker / order / paper / live / auto | ✅ Not present |
| DB write / network / schema / bulk / readiness / registry change | ✅ Not authorized |
| `actionable_feedback_for_ticket=true` | ✅ Not set |
| `buy_now`, `sell_now`, `entry_price`, `target_weight`, `position_size`, `allocation`, `order`, `broker` | ✅ Not present in any field design |
| Backlog scoring as stealth eligibility | ✅ Addressed with explicit test fixture |

---

## Explicit Non-Authorization

This document is a research advisory sidecar for R10 strategy task design. It does not constitute buy/sell advice or trading recommendations. No candidate has been promoted to an eligibility or tradable status. No product route is activated. No production readiness is claimed. No broker API, order routing, order submission, auto execution, paper trading, or live trading is authorized. All labels (KEEP_RESEARCH, WATCH_RESEARCH, DROP_FOR_NOW, REWORK_LATER, KEEP_AS_STRESS_CASE, ROBUST, RECENT_ONLY, BEAR_FRAGILE, DATA_BLOCKED, MEDIUM_RESEARCH, DROP_RESEARCH) are research classifications only. No ticket has been emitted. No PENDING_HUMAN_REVIEW status exists. No eligibility candidate has been created. DB writes and metadata repair require separate HG-EXEC authorization not present here.

REASONIX_STRATEGY_R10_DRAFT_READY
