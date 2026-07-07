# Windows WSL2 Post-R15 Development Progress Summary - 20260707

Project: quant-proj
Role: Quant-Dispatcher
Prepared: 2026-07-07 Asia/Shanghai
Scope: progress since the user-pasted R15 GitHub / GitHub connector external-audit result.

## Baseline

Last user-operated external audit result:

- File: `reports/agent_handoff/windows_wsl2_data_strategy_batch_r15_external_audit_result_20260707.md`
- Verdict: `VERIFIED_ACCEPT_WITH_WARNINGS`
- External-audit trigger open: `no`
- Fixes required before next ordinary strategy-search batch: `none`

Baseline facts preserved after R15:

- East Money split remains `77 CROSSCHECK_PASS`, `121 CROSSCHECK_DATE_GAP`, and `2870 CROSSCHECK_MISSING_EAST_MONEY`.
- `198` common symbols are overlap evidence only, not `198` pass.
- Survivor-bias evidence improved but did not eliminate all scope limits.
- wide3068 full-frame StrategySearch remains unsafe; wide3068 work is chunked-only.
- All strategy reruns remain rejected.
- `strategy_candidate_available=false`.

## Current State

Current controller status: all downstream callbacks for `WINDOWS_WSL2_AUTHORIZED_CONTROLLED_ADVANCEMENT_20260707` have been received and recorded. The only open gate is the user-operated GitHub / GitHub connector external-audit verdict for the market_data product-route preparation package. No product-route activation is allowed before that verdict and a later separate activation task.

## Completed Since R15 External Audit

### R16 Strategy Discovery

Batch: `WINDOWS_WSL2_STRATEGY_DISCOVERY_BATCH_R16_20260707`
Status: `CLOSED_ACCEPTED_RESEARCH_ONLY_WITH_WARNINGS`
External-audit trigger open: `no`

Accepted source states:

| Repo | Commit | Status |
|---|---|---|
| `A_Share_Monitor` | `f5805d9cede3efb114fa01de810cf27a97ef7a6f` | completed and pushed |
| `market_data` | `3c6c95172517de6fb908d73defa72c9fa1f28f85` | completed and pushed |
| `strategy_work` | `094af646175131bc60b0c9aabc7c785cba0c13a6` | final sync completed and pushed |

Key outcome:

- R15 accepted-state evidence was frozen before new search.
- Factor diagnostics produced `FACTOR_DIAGNOSTIC_WEAK=5`, `FACTOR_DIAGNOSTIC_UNSTABLE=8`, and `FACTOR_DIAGNOSTIC_POSITIVE=1`.
- 13 pre-registered strategy hypothesis families were produced.
- Small/medium scout diagnostics produced no family eligible for wide3068.
- `NO_WIDE_DIAGNOSTIC_ELIGIBLE_STRATEGY` was recorded.
- No wide3068 diagnostic run was executed.
- `strategy_candidate_available=false`.

### A_Share_Monitor GPU / East Money Controlled Advancement

Batch: `WINDOWS_WSL2_AUTHORIZED_CONTROLLED_ADVANCEMENT_20260707`
Commit: `a1d57f55a94382e20bfd4a184ad21c42bf9bde37`
Status: `COMPLETED_RESEARCH_ONLY_WITH_WARNINGS`, pushed
External-audit trigger open: `no`

Completed:

- Minimal authorized CUDA numeric/ML stack installed in the project `.venv`.
- RTX 5090 CUDA smoke passed.
- GPU Phase 2 numeric diagnostics completed.
- GPU Phase 3 ML signal research completed.
- CPU/GPU parity passed with tolerance `1e-05`.
- Strict split and label leakage audit passed.
- Focused pytest passed with `15 passed`.
- Bounded East Money probe ran for 20 symbols; 7 symbols succeeded and 13,450 rows were fetched.

Warnings:

- XGBoost trained on CUDA but prediction emitted a CPU-input fallback warning.
- East Money probe is bounded count/hash evidence only and does not overwrite the R15/R16 `77/121/2870` facts.

### US_Stock_Monitor Metadata Repair

Batch: `WINDOWS_WSL2_AUTHORIZED_CONTROLLED_ADVANCEMENT_20260707`
Commit: `9264773852daf46b4abf09f347f571c5f118d634`
Status: `COMPLETED_WITH_WARNINGS`, pushed
External-audit trigger open: `no`

Completed:

- Added flag-gated controlled helper `scripts/repair_us_metadata.py`.
- Added tests `tests/test_us_metadata_repair.py`.
- Ran bounded public/no-secret metadata and daily staging for snapshot `us_metadata_repair_20260707`.
- Wrote 263 metadata rows and 425,329 daily rows for 263 symbols.
- Current staged daily universe has 0 missing metadata and 0 duplicate keys.
- Focused tests passed with `5 passed`; safety scan and smoke passed.

Warnings:

- Some Tencent-visible symbols were excluded because Nasdaq Trader did not source them in this run.
- 17 historical/delisted legacy symbols were excluded.
- 7 selected symbols produced `N/A` parse errors and were not written.
- Raw staged data remains local ignored data and was not committed.

### market_data Product-Route Preparation

Batch: `WINDOWS_WSL2_AUTHORIZED_CONTROLLED_ADVANCEMENT_20260707`
Commit: `64840aa60e520cb7f0aa17078b941e0c4bc1586e`
Status: `ACCEPTED_PRODUCT_ROUTE_PREP_EXTERNAL_AUDIT_GATED`, pushed
External-audit trigger open: `yes`

Completed:

- Prepared old/new route diff.
- Prepared rollback plan.
- Prepared validation matrix.
- Added access-gate regression.
- Prepared source-side external-audit material.
- Codex-Audit reviewed the prep commit and returned `PASS`, with no fixes required.

Prepared route facts:

- Old active route remains `MARKET-DATA-1` / `local_17b656b7acaebc19963a32d8` / 50 symbols / 86,817 rows.
- Prepared replacement route targets `a_db_2_core_297_20260702_193900` / 281 symbols / 572,661 rows.
- Active registry changed: `false`.
- Prepared route is inactive.

Open gate:

- User-operated GitHub / GitHub connector external-audit verdict is required before any activation request.
- Any later activation must be a separate authorized/audited change with rollback and access-gate validation.

### RTX 5090 Power Policy

File: `reports/human_gate/windows_wsl2_5090_gpu_power_cap_policy_20260707.md`

New standing constraint:

- Future RTX 5090 numerical research, ML research, CUDA smoke, and GPU diagnostic work must use `GPU_POWER_LIMIT_WATTS=400`.
- Higher-than-400W operation requires a separate user authorization before execution.
- Future GPU callbacks must include `GPU_POWER_CAP_STATUS`.

## Remaining Gates

- User-operated GitHub / GitHub connector external audit for the market_data product-route preparation package.
- No market_data activation task may start before that verdict.
- Broader East Money reconciliation/integration remains a future separately authorized task if desired.
- Any complete legacy US metadata repair beyond source-based current-universe staging requires a separate source/policy decision.

## Boundary State

No recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket, eligibility candidate, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, raw-data migration into `quant-proj`, secret access/output, or higher-than-400W GPU authorization has occurred.
