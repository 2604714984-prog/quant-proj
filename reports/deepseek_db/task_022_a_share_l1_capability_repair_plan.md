# TASK-022 A-Share L1 Capability Repair Plan

Date: 2026-07-04
Role: `Reasonix-DB`
Model: `deepseek-v4-pro`
Effort: `high`
Mode: `L0_RESEARCH_DIAGNOSTIC`
Transcript: `reports/workspace_dispatch/reasonix_db_task_022_context_20260704.jsonl`

## Status

`WARNING`

The A-share L1 snapshot has missing suspension events and low limit-price coverage. Repair requires local read-only diagnosis first, then possible canonicalization, and only then a network-ingest fallback if local raw data is insufficient.

## Scope

- source project: `A_Share_Monitor`
- snapshot: `a_expand_20260704_l1_local1000_0317`
- symbols: `1000`
- canonical rows: `2,059,000`
- date range: `20180102..20260701`
- current readiness: `WARNING` / `Level 1`
- product read allowed: `false`
- local research allowed: `true`, with warnings
- `phase3_evidence_ready=false`
- `micro_recommendation_data_ready_with_warnings=false`

## Findings

### Suspension Events

The snapshot's suspension status is `WARNING_EVENT_TABLE_EMPTY` with 0 rows.

A-share suspension events should come from a trade-halt or suspension/status table, such as a raw suspension feed, raw trade status table, or provider daily status feed. Since ST/list coverage is `PASS` with coverage `1.0`, Reasonix-DB infers that symbol-status information likely exists somewhere in the local data surface or provider feed, but the canonical suspension-event target was not populated.

### Limit-Price Coverage

Limit-price coverage is low at `0.4`. Limit-price data depends on previous close and the correct limit-band rule, which can vary by ST status, board, IPO phase, or relisting/suspension behavior.

Likely causes:

- missing previous close for some `(symbol, date)` pairs;
- missing or uncanonicalized raw limit data;
- provider only emitting limit fields for some days;
- canonicalization not covering IPO, post-suspension, or ST-specific rules.

### Local Data May Exist But Not Be Canonicalized

Because TASK-007 used `local-duckdb-existing`, local raw tables may already contain suspension, trade-status, daily OHLC, previous close, or limit-band reference data. The next step should not start with network ingest. It should first inspect local tables and coverage in read-only mode.

### Network Requirement

Network ingest is not the default next step. It becomes necessary only if read-only diagnosis proves local raw data is absent or insufficient for suspension and limit-price repair.

## Repair Plan

### Phase A - Read-Only Local Diagnosis

1. Connect to the existing DuckDB file used for the snapshot in read-only mode.
2. List all tables.
3. Search candidate raw tables for suspension or halt fields, such as `is_suspended`, `trade_status`, `halt_code`, or provider-specific status names.
4. Search candidate raw tables for previous close, limit-up, limit-down, board/ST status, and daily OHLC fields.
5. Compare raw table coverage against the snapshot symbol-date matrix.
6. Report exact row counts, column names, date range, and missing dimensions.

### Phase B - Local Canonicalization Draft

If sufficient local raw data exists:

- draft SQL to populate canonical suspension events from raw suspension/status data;
- draft SQL or transformation logic to improve daily limit-price coverage from prior close plus board/ST-specific limit rules;
- do not execute writes until a unique pre-execution `HG-EXEC-TASK-*` record exists.

### Phase C - Network-Ingest Fallback

If local raw data is insufficient:

- produce a precise network-ingest specification for the same 1000-symbol universe and `20180102..20260701` date range;
- include provider endpoint, expected fields, date/symbol bounds, and stop conditions;
- do not run network ingest until a unique pre-execution `HG-EXEC-TASK-*` record exists.

### Phase D - Validation After Repair

After any later approved repair:

- rerun snapshot readiness evaluation;
- verify suspension status no longer reports `WARNING_EVENT_TABLE_EMPTY`;
- verify limit-price coverage no longer reports `WARNING_LOW_COVERAGE`;
- verify no regression in ST/list or canonical row counts;
- do not mark Phase 3 or micro recommendation readiness without separate validation and Human-Gate approval.

## Exact Next DB-Ops Task

`DB-REPAIR-022-A`: diagnose missing suspension events and low limit-price coverage for snapshot `a_expand_20260704_l1_local1000_0317`.

Expected Codex-Dev scope:

- list DuckDB tables in read-only mode;
- identify raw suspension/status and limit-price/previous-close tables;
- report coverage against snapshot symbol-date matrix;
- draft canonicalization SQL if local raw data is sufficient;
- otherwise produce a network-ingest specification;
- stop before any write or network action unless a unique `HG-EXEC-TASK-*` exists.

## Human-Gate Required Later

Human-Gate is required before:

- local DB write or canonicalization execution;
- network ingest;
- readiness status change;
- registry activation;
- any HITL ticket gate.

## Non-Authorization

This plan does not authorize recommendations, buy/sell advice, HITL ticket emission, broker APIs, order routing, order submission, auto execution, paper trading, live trading, trade plans, entry prices, target weights, position sizing, allocation, product-read activation, readiness upgrade, DB writes, network ingest, raw-data migration, `.env` access, or secret handling.
