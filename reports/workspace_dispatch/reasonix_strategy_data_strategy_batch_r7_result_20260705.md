# Reasonix-Strategy Research Draft

## Status
RESEARCH_DRAFT — process/strategy advisory only; no candidate-row data available in this session

## VERDICT

This draft is **strategy-architectural advisory**, not a candidate-level conclusion. I do not have concrete candidate rows, backtest CSVs, factor scores, or regression outputs in this session. Downstream Codex-Dev must supply candidate-level reports before any label, promotion, or gate decision can finalize. Every label below is a **research label design**, not a trading signal and not a recommendation.

---

## STRATEGY_OBSERVATIONS

### A-SHARE

**T1 — Two KEEP_RESEARCH Candidates vs Four REWORK_RESEARCH Candidates**

Without seeing the factor loadings or backtest curves, the structural comparative dimensions are:

| Dimension | KEEP_RESEARCH (2) | REWORK_RESEARCH (4) | Research Question |
|---|---|---|---|
| **Signal persistence** | Presumed stable IC decay | Likely rapid IC collapse or reversal | Compare rolling 20/60-day IC rank decay slopes |
| **Drawdown profile** | Presumed controlled max-DD | Likely tail-event drawdowns | Compare max-DD / Calmar ratio over regime windows (2022 bear, 2024 rally, 2025 vol spikes) |
| **Regime sensitivity** | May cluster in momentum-friendly regimes | May fail in mean-reversion or vol-expansion regimes | Regime-conditional return decomposition (up/down/sideways market × low/high VIX proxy) |
| **Factor crowding** | Unknown | Possible overfit or crowded factor decay | Pairwise return correlation among KEEP+REWORK to detect shared factor risk |
| **Turnover / capacity** | Unknown | May have liquidity or slippage erosion | Compare implied turnover and spread-cost estimates |

**Research label design (advisory only):**
- *KEEP_RESEARCH* → passes ≥3 of: IC decay slope ≤ -0.01/day, Calmar ≥ 0.5 in worst regime, pairwise corr ≤ 0.4 with others, turnover ≤ 200% annual.
- *WATCH_RESEARCH* → passes 1-2 of the above; hold for next re-eval cycle.
- *DROP_RESEARCH* → passes 0; archive the config for factor library reference only.

**Required Codex-Dev work:** Run the four-dimension diagnostic on all 6 candidates and produce a matrix. Only then can KEEP/WATCH/DROP labels finalize.

---

**T2 — Four REWORK_RESEARCH Candidates: Failure-Mode Diagnosis**

Plausible failure modes, each with a threshold-experiment idea:

| Failure Mode | Diagnostic | Threshold Experiment |
|---|---|---|
| **Volatility kill** | Factor returns conditional on VIXFXI/ATR percentile | Re-test with vol-regime filter: skip signals when 20d realized vol > 80th percentile |
| **Momentum decay** | Rolling 60d IC; check if IC drifts to zero or negative post-2024 | Apply momentum persistence floor: require 3-month trailing return rank ≥ 60th percentile before entry |
| **Liquidity erosion** | Compare fill-price simulation with Amihud illiquidity proxy | Add min daily turnover filter (e.g., 50M CNY) and re-test |
| **Regime fragility** | Partition returns by CSI 300 trend direction and vol regime | Add regime-gate: long-only in bull/neutral; cash in bear+high-vol |
| **Data gap / stale universe** | Check if candidate symbols exist in current Level2 1000-symbol research input | Re-run on current universe; flag any symbol that disappeared between R5→R7 |
| **Overfit / data-snooping** | Walk-forward vs static in-sample comparison | Split 2021-2023 train / 2024-2025 walk-forward; if OOS IC < 0.5 × IS IC, flag overfit |

**Rule:** Do not promote any REWORK candidate to KEEP_RESEARCH unless ≥2 threshold experiments yield statistically meaningful improvement (p < 0.05 on OOS IC improvement, or Calmar improvement ≥ 0.1).

**Required Codex-Dev work:** Run the six-diagnostic panel on the 4 REWORK candidates; report which failure modes are active; run threshold experiments; report OOS metrics.

---

**T3 — Low-Vol Overlay Disposition**

Analysis: 4-record evidence is too small. A low-vol overlay built on 4 candidates cannot be statistically distinguished from noise. Comparing against the conservative momentum set:

- If the 4 low-vol names overlap with the 2 KEEP_RESEARCH momentum names, the low-vol signal is likely redundant (momentum already selecting them).
- If there is zero overlap, the low-vol names are providing orthogonal exposure — but with 4 records, confidence is too low to act.

**Decision: DROP_FOR_NOW** — with a research footnote:
- Retain the low-vol config in `strategy_work/archive/low_vol_overlay_r6.yaml` as a reference.
- Revisit only when ≥20 candidate records pass the same filter in a future research cycle (R8+).
- Do NOT promote to RISK_FILTER_ONLY because a risk filter needs statistical stability, which 4 records cannot provide.

**Rationale for rejecting RISK_FILTER_ONLY:** A risk filter applied to a momentum portfolio would need to show it reduces drawdowns without gutting returns. With n=4, any backtest result is a sample-size artifact.

**Required Codex-Dev work:** Archive the low-vol config; add a research-note tag `R7_DROP_FOR_NOW` with the 20-record revisit threshold.

---

**T4 — Dataset Consistency Check**

Key points:
- No stale 83-symbol baseline treated as current.
- Current universe: Level2 1000-symbol research input.
- Verify that all A-share candidate runs (KEEP + REWORK) reference the correct universe snapshot and date range.
- Check that no config accidentally points to a pre-Level2 universe filter.

**Required Codex-Dev work:** Audit all active A-share strategy configs for universe reference; confirm universe snapshot hash or date matches current Level2 research input; flag any drift.

---

### US STOCK

**T5 — 60 Strong Bucket: Signal-Overlap Diagnostics**

60 candidates is enough for statistical analysis. Research-only diagnostic plan:

1. **Pairwise return correlation matrix** — cluster candidates into signal families. If 60 names reduce to, say, 5-8 orthogonal signal clusters, the effective diversification is much lower than 60.
2. **Single-filter vs multi-filter pass-through** — For each candidate, decompose: did it pass because of one dominant filter (e.g., momentum score > threshold, everything else marginal) or did it clear multiple independent filters? Tag single-filter pass names as `CONCENTRATED_RISK`.
3. **Sector concentration check** — What fraction of the 60 fall into the top 3 GICS sectors? If >50%, flag as sector-concentration risk.
4. **Cross-signal redundancy** — For any pair with return correlation > 0.7, tag the lower-Sharpe one as `REDUNDANT_WATCH`.
5. **Factor attribution** — Regress each candidate's returns against common factors (market, size, value, momentum, quality, low-vol). Flag any candidate with R² > 0.8 to a single factor as `FACTOR_PROXY` (not an independent alpha source).

**Research labels:** `CORE_SIGNAL` (orthogonal, multi-filter, diversified), `CONCENTRATED_RISK`, `REDUNDANT_WATCH`, `FACTOR_PROXY`.

**Required Codex-Dev work:** Run the five-diagnostic panel; produce cluster heatmap, sector pie chart, and single-filter-pass list.

---

**T6 — 80 Medium / 91 Weak: Pruning Principles**

For the 80 medium bucket:
- Apply stricter multi-filter consensus: require ≥2 independent filters to agree (not just pass).
- Raise the combined score threshold by 0.5σ relative to the strong-bucket median.
- Add a minimum holding-period return floor: if a candidate has negative return over the most recent 60-day window, defer to next cycle.
- Tag candidates that are "medium now but were strong in R5" as `DECAYING` — these may signal regime rotation.

For the 91 weak bucket:
- **Do not use as a source of new candidates.** These are a control group for false-positive analysis.
- Research use: compute what fraction of weak-bucket candidates would have entered the strong bucket if one filter were relaxed. This identifies which filters are doing the heaviest lifting.
- If any weak candidate appears in >3 consecutive weak buckets, archive it permanently.

**Required Codex-Dev work:** Implement medium-bucket re-scoring script; produce weak-bucket filter-sensitivity report.

---

**T7 — 8 Data-Limited Candidates: Repair Mapping**

These 8 candidates are missing required fields — not strategy failures. Repair tasks:

| Task | Description | Gate |
|---|---|---|
| Identify missing fields per candidate | Column-level audit: which required field(s) is/are null/empty | Codex-Dev |
| Source the missing data | Determine if missing from primary feed, enrichment pipeline, or schema mismatch | Reasonix-DB-Maintainer |
| Re-ingest and re-score | After field repair, re-run through the scoring pipeline | Codex-Dev (HG-EXEC if DB write) |
| Re-classify | After re-scoring, assign to strong/medium/weak bucket | Codex-Dev |

**No DB/network execution without separate HG-EXEC gate.** This task is a mapping only.

---

**T8 — 44-Symbol Metadata Bootstrap Schema**

These 44 symbols have a metadata gap (likely missing sector, market-cap, or liquidity classification), not a strategy-quality gap. Dry-run design:

1. **Schema fields needed:** gics_sector, gics_industry, market_cap_rank, avg_daily_volume_20d, exchange, is_active_equity.
2. **Active-equity exclusions:** ETFs, ADRs, preferred shares, SPACs, warrants, closed-end funds. Apply a security-type filter from the data vendor's classification field.
3. **Bootstrap approach:** Cross-reference the 44 symbols against a reference data source (e.g., vendor symbology file, exchange master). Fill missing fields. Flag any symbol that cannot be resolved as `UNRESOLVED_METADATA`.
4. **Dry-run only:** Produce a fill report (X of 44 resolved, Y unresolvable) without writing to any production database.

**No product readiness.** This is a schema design and dry-run report only.

**Required Codex-Dev work:** Draft the bootstrap script; run dry-run; produce fill report.

---

**T9 — Feedback Context Repair Plan**

Non-transactional feedback only. Forbidden fields: `buy_now`, `sell_now`, `entry_price`, `target_weight`, `position_size`, `order`, `broker`.

Allowed repair dimensions:
- Research commentary on factor construct (e.g., "momentum lookback window may be too short for this sector").
- Data-quality flags (e.g., "these symbols have stale market-cap data").
- Regime notes (e.g., "this signal family underperforms in high-vol environments").
- Suggested config parameter ranges for next research cycle.

**Required Codex-Dev work:** Audit all feedback-emitting code paths; strip forbidden fields; add allowed-field allowlist; add unit test that fails if any forbidden field appears in feedback output.

---

**T10 — Market Data Research Route Consistency**

Rules to harden:
- A-share: data path → Level2 research input only; `product_read_allowed=false`.
- US: data path → 300A/B research/enrichment only; `product_read_allowed=false`.
- `candidate_product_read_allowed=false` unless separately gated by HG-EXEC.
- `production_recommendation_data_ready=false` — this flag must stay false across all modules.
- `broker/live/auto=false` — hard block at config level, not just convention.

**Required Codex-Dev work:** Add config-level flags for each data route; add startup assertion that fails if any product-route flag is true; add integration test.

---

**T11 — Strategy Work Memo Update**

Memo should record:
- R6→R7 state transitions for A-share (2 KEEP, 4 REWORK, low-vol → DROP_FOR_NOW).
- R6→R7 state for US (60/80/91/8/44 bucket structure preserved, with pruning rules added).
- Research-only boundary: explicitly state that no recommendation, ticket, eligibility candidate, product route, or production readiness exists.
- Next-cycle triggers: when to revisit REWORK candidates, when to revisit low-vol, when to re-run US pruning.

**Avoid:** Any language suggesting "ready for trading," "recommended," "eligible," "approved," "promoted to production."

**Required Codex-Dev work:** Update `strategy_work/RESEARCH_MEMO.md` with R7 state.

---

## TASK_MAPPING

| Task | Status This Draft | Requires Codex-Dev | Requires HG |
|---|---|---|---|
| T1 A KEEP deep-validate | Advisory dimensions only; no candidate data | Yes — diagnostic matrix | No |
| T2 A REWORK diagnosis | Failure-mode hypotheses only | Yes — 6-diagnostic panel + experiments | No |
| T3 A Low-vol disposition | **DROP_FOR_NOW** (advisory) | Yes — archive config | No |
| T4 A Dataset consistency | Checklist only | Yes — universe audit | No |
| T5 US Strong bucket | Diagnostic plan only | Yes — 5-panel diagnostic | No |
| T6 US Medium/Weak pruning | Pruning principles only | Yes — re-scoring + sensitivity | No |
| T7 US Data-limited repair | Repair task mapping only | Yes — field audit; HG-EXEC for DB write | Yes (DB write) |
| T8 US Metadata bootstrap | Schema design only | Yes — dry-run script | No |
| T9 US Feedback repair | Repair plan only | Yes — code audit + allowlist | No |
| T10 Market data route | Consistency rules only | Yes — config flags + tests | No |
| T11 Memo update | Content guidance only | Yes — write memo | No |

---

## BOUNDARY_CHECK

| Boundary | Status |
|---|---|
| Buy/sell advice | ✅ Not emitted |
| Recommendation ticket | ✅ Not emitted |
| PENDING_HUMAN_REVIEW | ✅ Not emitted |
| Eligibility candidate | ✅ Not emitted |
| Product-route activation | ✅ Not emitted |
| Production readiness | ✅ Not emitted |
| Broker/order/paper/live/auto | ✅ Not emitted |
| Ungated DB write/network/schema/bulk | ✅ Not emitted |
| Registry activation | ✅ Not emitted |
| Entry price / target weight / position size | ✅ Not emitted |

---

## NEXT_HANDOFF

1. **Codex-Dev** — Execute the 11 "Required Codex-Dev work" items above, in priority order: T1→T2 (A-share candidate diagnostics first), then T5→T6 (US diagnostics), then T4, T7-T11. Produce per-task reports under `strategy_work/r7/`.
2. **Reasonix-DB-Maintainer** — For T7, supply field-level audit of the 8 data-limited US candidates (read-only; no DB write).
3. **Human-Gate** — Required only for T7 DB-write step and any future product-route activation. Not required for the research draft itself.
4. **Quant-Dispatcher** — After Codex-Dev produces candidate-level reports, re-dispatch a Reasonix-Strategy follow-up with concrete data for label finalization.

---

## Explicit Non-Authorization

This document is a research architectural draft. It does not constitute buy/sell advice, does not authorize recommendations, does not authorize broker API access, order routing, order submission, auto execution, paper trading, or live trading. No candidate rows have been reviewed. No labels (KEEP/WATCH/DROP) are final. No product route is activated. No production readiness is claimed.
