# Reasonix-DB R10 Advisory Draft

## Verdict

**PASS — advisory only; no execution authorized.**

All five tasks are well-scoped research/dry-run/plan work. No boundary drift detected. The critical design risks are in criteria precision (US-R10-1), fixture/provider isolation (US-R10-2), and the DATA_CLEAR_RESEARCH label guardrail (MD-R10-1).

---

## 1. US-R10-1 — Data-Clear Criteria for US-239

### Status: PASS (Design Review)

### 1.1 Criteria Field Definitions (Advisory)

| Field | DATA_BLOCKED Definition | DATA_CLEAR_RESEARCH Threshold |
|-------|------------------------|-------------------------------|
| **sector** | NULL or UNCLASSIFIED | Non-null, matches GICS/ICB/TRBC from canonical provider |
| **asset_type** | NULL or ambiguous (e.g. `""`, `"OTHER"`) | One of `EQUITY`, `ETF`, `ADR` — explicitly set |
| **metadata_provenance** | Source provider unknown or single-provider only | At least one named provider with fetch timestamp; crosscheck source logged |
| **adjusted_close** | NULL for any trading day in lookback window (504 days) | Non-null for ≥ 95% of trading days; gaps ≤ 5 consecutive days and flagged |
| **row_level_crosscheck** | Not run or crosscheck failure unresolved | Crosscheck passed: OHLCV rows from provider-A match provider-B within tolerance for ≥ 98% of overlapping dates |
| **price_history_completeness** | Missing ≥ 10% of expected trading days in window | Missing ≤ 2% of expected trading days; gap streaks ≤ 3 days |
| **freshness** | max(date) < T-5 trading days | max(date) ≥ T-2 trading days |

### 1.2 Application to 60 Signal-Strong vs 61 Tightened Survivors

| Set | Expected Blockers | Suggested Blocker-Count Schema |
|-----|-------------------|-------------------------------|
| 60 signal-strong | Sector/asset_type likely already populated; blockers will be crosscheck/freshness gaps | `{symbol, blocked_fields: [list], clearable: bool, missing_for_clear: [list]}` |
| 61 tightened survivors | Sector/asset_type likely the dominant blockers; metadata_provenance likely single-provider or NULL | `{symbol, blocked_fields: [list], dominant_blocker: string, estimated_repair_lanes: [M1/M2/M3/M4/M5]}` |

### 1.3 Risks

- **Risk R10-1a:** If `DATA_CLEAR_RESEARCH` is misinterpreted downstream as "data is production-grade," it becomes a backdoor readiness claim. The label must carry an explicit suffix: `DATA_CLEAR_RESEARCH_ONLY` to prevent ambiguity.
- **Risk R10-1b:** The 95%/98%/2% thresholds are arbitrary without calibration against the actual US-239 data distribution. A symbol with 94.8% adjusted-close completeness is not meaningfully worse than one with 95.1%. Consider a **composite score** rather than hard cutoffs, with a `BORDERLINE` category for symbols within 2% of any threshold.
- **Risk R10-1c:** Crosscheck depends on two providers having overlapping coverage. If a symbol only exists in one provider, `row_level_crosscheck` is impossible — this should result in `CROSSCHECK_NOT_APPLICABLE`, not `BLOCKED`.

---

## 2. US-R10-2 — Sector and Asset-Type Fixture Build Plan

### Status: PASS (Schema Design)

### 2.1 Dry-Run Fixture Schema (Advisory)

```csv
symbol, source_type, field, user_supplied_value, provider_value, provider_source, match, notes
```

| Column | Type | Meaning |
|--------|------|---------|
| `symbol` | string | Ticker |
| `source_type` | enum | `USER_CSV` or `PROVIDER_DERIVED` |
| `field` | enum | `sector`, `asset_type`, `industry`, `sub_industry` |
| `user_supplied_value` | string | Value from user-supplied CSV (may be empty) |
| `provider_value` | string | Value from Poly.io / Tiingo / EODHD (empty in dry-run) |
| `provider_source` | string | Provider name or `DRY_RUN_NO_FETCH` |
| `match` | enum | `MATCH`, `MISMATCH`, `USER_ONLY`, `PROVIDER_ONLY`, `BOTH_NULL`, `PENDING` |
| `notes` | string | Free text |

### 2.2 Classification Rules

- **USER_CSV**: Field value originates from a user-supplied spreadsheet or manual curation. Must be cross-validated against provider before adoption.
- **PROVIDER_DERIVED**: Field value originates from an API call to Poly.io / Tiingo / EODHD reference data. Must carry provenance timestamp.
- **BOTH_NULL**: Neither source has the value — this is a genuine blocker.
- **USER_ONLY / PROVIDER_ONLY**: One source has it; the other doesn't — requires resolution rule (which source wins).

### 2.3 Risks

- **Risk R10-2a:** User-supplied CSV may contain stale or incorrect sector assignments. Without provider cross-validation, adopting user-supplied values silently propagates errors.
- **Risk R10-2b:** Fixture must target US-239 and US-300A only per task scope. US-300B symbols must not appear in the fixture unless explicitly requested.

---

## 3. US-R10-3 — Row-Level Crosscheck Sample Plan

### Status: PASS (Plan Design)

### 3.1 Sampling Strategy

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Total sample | 20 symbols | |
| From 60 signal-strong | 12 symbols | Stratified: 4 large-cap, 4 mid-cap, 4 small/micro |
| From 61 tightened survivors | 8 symbols | Stratified by dominant blocker field |
| Date range | 2025-07-01 to 2026-07-01 (252 trading days) | Full recent year |
| Source pairing | Poly.io vs Tiingo (primary); fallback EODHD if one missing | |

### 3.2 Required Columns Per Row

```
symbol, date, provider_a_close, provider_b_close, provider_a_volume, provider_b_volume,
close_diff_pct, volume_diff_pct, pass_tolerance, mismatch_category, notes
```

### 3.3 Tolerance Rules

| Metric | Tolerance | Mismatch Category If Exceeded |
|--------|-----------|-------------------------------|
| Close price difference | ≤ 0.5% | `PRICE_MISMATCH` |
| Volume difference | ≤ 2.0% | `VOLUME_MISMATCH` |
| Date present in A, missing in B | 0 allowed | `DATE_MISSING_B` |
| Date present in B, missing in A | 0 allowed | `DATE_MISSING_A` |
| Either close NULL | 0 allowed | `NULL_CLOSE` |

### 3.4 Failure Handling

| Category | Action |
|----------|--------|
| `PRICE_MISMATCH` | Flag row; if ≥ 2% of rows for a symbol, mark symbol `CROSSCHECK_FAILED` |
| `VOLUME_MISMATCH` | Flag row; if ≥ 5% of rows, mark symbol `CROSSCHECK_WARN` |
| `DATE_MISSING_*` | Count missing dates; if ≥ 1% of expected days, mark symbol `CROSSCHECK_INCOMPLETE` |
| `NULL_CLOSE` | Symbol immediately `DATA_BLOCKED` |

### 3.5 Risks

- **Risk R10-3a:** 20 symbols may not be representative. If the 61 tightened survivors are concentrated in micro-cap where provider coverage is sparse, the sample may over-represent large-caps from the 60 signal-strong set. Mitigation: ensure stratification by market-cap tier.
- **Risk R10-3b:** Corporate actions (splits, dividends) on the same date across providers may produce apparent PRICE_MISMATCH even when both are correct (e.g., one provider adjusts, the other doesn't for 1 day). The crosscheck must account for adjustment-factor differences.

---

## 4. US-R10-4 — 44-Symbol Metadata Queue Split

### Status: PASS (Manifest Design)

### 4.1 Five-Way Split

| Queue | Criteria | Expected Count (Illustrative) | Action |
|-------|----------|------------------------------|--------|
| **actionable-now** | All NULL fields have a deterministic provider source; no network fetch required (metadata already cached locally) | ~8–12 | Eligible for dry-run fixture population (HG-EXEC required for write) |
| **needs-provider** | NULL fields require live provider API call; no local cache exists | ~12–18 | Queue for separate HG-EXEC with network authorization |
| **ETF-schema** | Symbol is an ETF; NULL fields are ETF-specific (expense_ratio, aum, holdings_date, underlying_index) | ~3–6 | Route to ETF-specific schema; different provider endpoints needed |
| **historical-only** | Symbol is delisted/merged/renamed; metadata is archival | ~3–5 | Mark `historical_only=true`; exclude from active-scan pipelines |
| **exclude-from-active-scan** | Symbol is active equity but fully bootstrapped (R8 exclusion rule) | ~3–6 | Confirm exclusion; log reason |

### 4.2 Dry-Run Import Manifest Schema

```json
{
  "manifest_id": "r10-44-metadata-split-001",
  "generated_at": "2026-07-05T...",
  "queues": {
    "actionable_now": {
      "count": 0,
      "symbols": [],
      "fields_fillable": {}
    },
    "needs_provider": {
      "count": 0,
      "symbols": [],
      "required_endpoints": []
    },
    "etf_schema": {
      "count": 0,
      "symbols": []
    },
    "historical_only": {
      "count": 0,
      "symbols": []
    },
    "exclude_from_active_scan": {
      "count": 0,
      "symbols": [],
      "exclusion_reasons": {}
    }
  }
}
```

### 4.3 Risks

- **Risk R10-4a:** The `actionable_now` queue must not silently write to DB. Even locally cached metadata requires HG-EXEC because the registry considers any metadata population a readiness-affecting change.
- **Risk R10-4b:** `historical_only` symbols must carry `survivor_bias_flag=true` to prevent them from being counted in active-universe statistics downstream.

---

## 5. MD-R10-1 — Data-Clear Boundary Contract

### Status: PASS (Contract Design)

### 5.1 Label Definitions (Must Be Codified)

| Label | Meaning | What It Does NOT Mean |
|-------|---------|----------------------|
| `DATA_CLEAR_RESEARCH_ONLY` | All data-clear criteria per US-R10-1 are met; symbol is safe for research scans, factor calculation, backtesting | Does NOT mean production-ready, recommendation-eligible, or broker-actionable |
| `PASS_LEVEL_2_FOR_RESEARCH` (A-share Level2) | Data passes Level 2 checks (completeness, freshness, qfq, turnover) for research use only | Does NOT mean `PASS_LEVEL_2` in the product-readiness sense |
| `DATA_BLOCKED_RESEARCH` | ≥1 data-clear criterion not met; symbol excluded from research scans until repaired | Research-internal only; not a product gate |

### 5.2 Gate Contract

| Route | Allowed Label | product_read_allowed | production_recommendation_data_ready | broker/live/auto |
|-------|---------------|---------------------|--------------------------------------|------------------|
| A-share Level2 | `PASS_LEVEL_2_FOR_RESEARCH` only | `false` | `false` | `false` |
| US-300A | `DATA_CLEAR_RESEARCH_ONLY` (if criteria met) | `false` | `false` | `false` |
| US-300B | Metadata-enrichment only; no DATA_CLEAR label | `false` | `false` | `false` |

### 5.3 Boundary Confirmation

Per the R9 registry snapshot (2026-07-04) and the R8 GPT Pro `ACCEPT` verdict:

| Assertion | Confirmed? |
|-----------|------------|
| `product_read_allowed=false` on all routes | ✅ |
| `production_recommendation_data_ready=false` on all routes | ✅ |
| `broker_api_allowed=false` on all routes | ✅ |
| `live_trading_allowed=false` on all routes | ✅ |
| `auto_execution` not present/not true | ✅ |
| `eligibility_candidate` not present/not true | ✅ |
| `recommendation_runtime_enabled=false` | ✅ |
| US route `INGEST_PREFLIGHT_BLOCKED` still in effect | ✅ |
| No PENDING_HUMAN_REVIEW tickets emitted | ✅ |

### 5.4 Risks

- **Risk R10-5a (CRITICAL):** `DATA_CLEAR_RESEARCH_ONLY` is a new label not present in the R9 registry. It must be accompanied by an explicit guard in `registry/projects.yaml` — a new field `research_label_scope: "research_only"` that downstream consumers must check before interpreting DATA_CLEAR as anything beyond research. Without this guard, the label is indistinguishable from a product-readiness signal.
- **Risk R10-5b:** A-share Level2 currently holds `WARNING_LEVEL_1`. Upgrading to `PASS_LEVEL_2_FOR_RESEARCH` changes the label. Even if it's research-scoped, the label change requires a registry refresh and a separate justification that the original WARNING_LEVEL_1 blockers (`LIMIT_PRICE_COVERAGE_LOW`, `SUSPENSION_CAPABILITY_INCOMPLETE`, `MICRO_RECOMMENDATION_DATA_NOT_READY`) have been resolved or are irrelevant to research use.

---

## 6. Aggregate Risk Register

| ID | Risk | Severity | Mitigation |
|----|------|----------|------------|
| R10-5a | DATA_CLEAR label ambiguity — could be misread as production-ready | **High** | Add `research_label_scope` guard field; suffix all labels with `_RESEARCH_ONLY` |
| R10-5b | A-share WARNING→PASS label change without blocker resolution | **Medium** | Audit original WARNING_LEVEL_1 blockers before label change |
| R10-1b | Hard thresholds create false BLOCKED/BORDERLINE assignments | **Medium** | Use composite scoring with BORDERLINE tier |
| R10-1c | Crosscheck impossible for single-provider symbols | **Medium** | Add `CROSSCHECK_NOT_APPLICABLE` category |
| R10-3a | Sampling bias toward large-caps in crosscheck | **Low** | Stratify by market-cap tier |
| R10-4a | `actionable_now` queue writes without HG-EXEC | **Medium** | Require explicit HG-EXEC even for cached-metadata writes |

---

## 7. Explicit Non-Authorization

> **This Reasonix-DB R10 advisory does not authorize:**
>
> - Any recommendation, trading advice, buy/sell signal, position suggestion, target weight, entry price, or allocation instruction.
> - Any `PENDING_HUMAN_REVIEW` ticket emission.
> - Any `eligibility_candidate` tag.
> - Any `product_read_allowed=true`, `production_recommendation_data_ready=true`, `broker_api_allowed=true`, `live_trading_allowed=true`, or any auto-execution flag.
> - Any `product route activation` or `production readiness` claim.
> - Any DB write, network ingest, schema migration, bulk ingest, readiness change, or registry activation.
> - Any provider API call that persists data locally.
> - Any promotion of `DATA_CLEAR_RESEARCH_ONLY` or `PASS_LEVEL_2_FOR_RESEARCH` to imply recommendation/product/broker readiness.
>
> The labels `DATA_CLEAR_RESEARCH_ONLY` and `PASS_LEVEL_2_FOR_RESEARCH` are **research-scoped data-quality markers only**. They carry zero recommendation, product, broker, or trading authorization.
>
> All execution remains gated behind `human_gate` + separate `HG-EXEC` as defined in the R9 intake boundaries and R8 GPT Pro `ACCEPT` verdict.

---

REASONIX_DB_R10_DRAFT_READY
