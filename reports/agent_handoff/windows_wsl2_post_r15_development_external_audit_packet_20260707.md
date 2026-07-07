# External Audit Packet - Post-R15 Development Since Last External Audit

Project: quant-proj
Role: Quant-Dispatcher
Prepared: 2026-07-07 Asia/Shanghai
Submission: user-operated GPT Pro / ChatGPT external audit

## Review Request

Please externally review the work completed since the last user-operated R15 external audit. This packet covers R16 strategy discovery, authorized GPU/ML numeric research, bounded East Money probing, US metadata repair, market_data product-route preparation, Codex-Audit result, and the new RTX 5090 400W power cap policy.

This packet is an audit handoff and progress review. It is not an activation request, not a recommendation request, and not a trading or readiness request.

## Last External Audit Baseline

Last external audit file:

- `reports/agent_handoff/windows_wsl2_data_strategy_batch_r15_external_audit_result_20260707.md`

Baseline verdict:

- `VERIFIED_ACCEPT_WITH_WARNINGS`
- `EXTERNAL_AUDIT_TRIGGER_OPEN: no`
- `FIXES_REQUIRED: none before next ordinary strategy-search batch`

Facts that must remain preserved:

- East Money split: `77 CROSSCHECK_PASS`, `121 CROSSCHECK_DATE_GAP`, `2870 CROSSCHECK_MISSING_EAST_MONEY`.
- `198` common symbols are overlap evidence only, not `198` pass.
- Survivor-bias evidence improved but did not eliminate all scope limits.
- wide3068 full-frame StrategySearch remains unsafe; wide3068 work is chunked-only.
- All strategy reruns remain rejected.
- `strategy_candidate_available=false`.

## Controller Progress Summary

Controller records created for this post-R15 period:

- Progress summary: `reports/workspace_dispatch/windows_wsl2_post_r15_development_progress_summary_20260707.md`
- Packet manifest: `reports/agent_handoff/windows_wsl2_post_r15_development_external_audit_packet_manifest_20260707.sha256`
- R16 result summary: `reports/workspace_dispatch/windows_wsl2_strategy_discovery_batch_r16_20260707_result_summary.md`
- R16 closeout: `reports/workspace_dispatch/windows_wsl2_strategy_discovery_batch_r16_20260707_closeout.md`
- Controlled advancement result summary: `reports/workspace_dispatch/windows_wsl2_authorized_controlled_advancement_20260707_result_summary.md`
- market_data Codex-Audit callback: `reports/workspace_dispatch/windows_wsl2_authorized_controlled_advancement_20260707_market_data_codex_audit_callback.md`
- RTX 5090 power policy: `reports/human_gate/windows_wsl2_5090_gpu_power_cap_policy_20260707.md`

Current controller status:

- R16 is closed as accepted research-only with warnings.
- A_Share_Monitor controlled GPU/East Money work is completed and pushed.
- US_Stock_Monitor metadata repair / bounded staging is completed and pushed.
- market_data product-route preparation is completed, pushed, and Codex-Audit PASS.
- The only open gate is user-operated external audit for market_data product-route preparation before any activation.

## Development Since Last External Audit

### 1. R16 Strategy Discovery

Batch: `WINDOWS_WSL2_STRATEGY_DISCOVERY_BATCH_R16_20260707`
Classification: ordinary research-only strategy discovery batch
External-audit trigger open: `no`
Final status: `CLOSED_ACCEPTED_RESEARCH_ONLY_WITH_WARNINGS`

Source commits:

| Repo | Commit | Tree | Status |
|---|---|---|---|
| `A_Share_Monitor` | `f5805d9cede3efb114fa01de810cf27a97ef7a6f` | `82cfc366837c165bffae688ee72143be1e98389b` | pushed |
| `market_data` | `3c6c95172517de6fb908d73defa72c9fa1f28f85` | `531bcd2110de43dc37c49b55348e71b9e65f75c8` | pushed |
| `strategy_work` | `094af646175131bc60b0c9aabc7c785cba0c13a6` | `d71b67bbcdb4f5e889ac6bcb6c113e2801e5a4b6` | pushed |

Key results:

- R15 accepted-state evidence was frozen.
- Factor diagnostics used only allowed labels.
- Factor diagnostic counts: `WEAK=5`, `UNSTABLE=8`, `POSITIVE=1`.
- 13 pre-registered hypothesis families were produced.
- Small/medium scout diagnostics produced no wide-eligible strategy family.
- `NO_WIDE_DIAGNOSTIC_ELIGIBLE_STRATEGY` was recorded.
- wide3068 diagnostic run was not executed.
- Trade-count, cost-aware, parameter-cluster, regime/period, rejection-taxonomy, and research-only shadow leaderboard diagnostics were generated.
- `strategy_candidate_available=false`.

Validation reported:

- A_Share_Monitor: py_compile PASS, focused pytest PASS with `18 passed`, `agent_safety_check.py` PASS, JSON parse PASS, `git diff --check` PASS, forbidden overclaim scan PASS, full-frame wide3068 not run, no network/provider fetch, no DB/cache rebuild.
- market_data: focused pytest PASS with `5 passed`, JSON parse PASS, diff-check PASS, no product/readiness/registry true flags, no raw data import true flags.
- strategy_work: diff-check PASS, forbidden wording scans PASS, no candidate promotion, no placeholder final sync, pushed final sync.

Audit focus:

- Confirm R16 is correctly closed as research-only and does not require fixes before further ordinary research.
- Confirm no R16 artifact creates recommendation, candidate, ticket, readiness, product route, or trading path.

### 2. A_Share_Monitor GPU Numeric / ML Signal Research and East Money Probe

Batch: `WINDOWS_WSL2_AUTHORIZED_CONTROLLED_ADVANCEMENT_20260707`
Workstreams:

- `HG-EXEC-TASK-GPU-ENV-PHASE2-PHASE3-20260707`
- `HG-EXEC-TASK-A-EAST-MONEY-COVERAGE-20260707`

Source state:

- Repo: `/home/rongyu/workspace/A_Share_Monitor`
- Branch: `codex/harden-a-share-research-pipeline`
- Commit: `a1d57f55a94382e20bfd4a184ad21c42bf9bde37`
- Tree: `730dfd62f186f9bba0515963ed43c67214b8f580`
- Push: pushed to origin
- Status: `COMPLETED_RESEARCH_ONLY_WITH_WARNINGS`
- External-audit trigger open: `no`

Completed:

- Minimal authorized CUDA numeric/ML stack installed in project `.venv`.
- GPU Phase 2 numeric diagnostics completed with CUDA smoke, tensor dataset, CPU/GPU parity, predictive diagnostics, bootstrap/permutation, neutralization, cost/capacity, regime attribution, and anomaly scan.
- GPU Phase 3 ML signal research completed with strict split dataset/label contract, GPU ML baselines, decile diagnostics, meta-labeling prototype, signal-to-strategy bridge, portfolio construction research, and overfit/leakage audit.
- Bounded East Money probe completed for 20 symbols.

Validation reported:

- `nvidia-smi` visible in WSL: PASS, NVIDIA GeForce RTX 5090, driver `610.47`, `32607 MiB`.
- Python CUDA smoke PASS: CuPy `14.1.1`, CUDA runtime `12090`, one RTX 5090 device, XGBoost CUDA smoke PASS.
- CPU/GPU parity PASS with tolerance `1e-05`.
- Strict train/validation/test split and label leakage audit PASS.
- Focused pytest PASS with `15 passed`.
- `agent_safety_check.py` PASS.
- JSON parse PASS for 11 JSON artifacts.
- Forbidden local LLM/Qwen/recommendation/candidate/readiness/trading scan PASS.
- Secret/key/token/auth scan PASS.

Warnings:

- XGBoost prediction emitted a CPU-input fallback warning due CPU input vs CUDA booster.
- East Money probe succeeded for 7 of 20 symbols and fetched 13,450 rows; this is bounded evidence only.
- Prior R15/R16 East Money `77/121/2870` facts are not overwritten.

Audit focus:

- Confirm GPU/ML outputs remain research diagnostics only.
- Confirm no strategy candidate, recommendation, ticket, readiness, product route, or trading path is created.
- Confirm the bounded East Money probe does not become data-clear, readiness, or full coverage expansion evidence.

### 3. US_Stock_Monitor Metadata Repair / Bounded Staging

Batch: `WINDOWS_WSL2_AUTHORIZED_CONTROLLED_ADVANCEMENT_20260707`
Workstream: `HG-EXEC-TASK-US-METADATA-REPAIR-20260707`

Source state:

- Repo: `/home/rongyu/workspace/US_Stock_Monitor`
- Branch: `main`
- Commit: `9264773852daf46b4abf09f347f571c5f118d634`
- Tree: `79e8b2acb49d6861a456c2fa054fbf00926d33f6`
- Push: pushed to `origin/main`
- Status: `COMPLETED_WITH_WARNINGS`
- External-audit trigger open: `no`

Completed:

- Added `scripts/repair_us_metadata.py`.
- Added `tests/test_us_metadata_repair.py`.
- Ran bounded public/no-secret metadata and daily staging with `--allow-network --allow-write`.
- Generated command transcript, manifest, validation artifact, and report.

Key data result:

- Selected symbols attempted: `270`.
- Metadata rows written: `263`.
- Daily rows written: `425329`.
- Daily symbols written: `263`.
- Metadata duplicate symbols: `0`.
- Daily duplicate symbol-dates: `0`.
- Missing metadata for daily symbols: `[]`.
- Legacy 44 hash remains `b680b7a6d4c82acb`.

Validation reported:

- JSON parse PASS.
- Focused tests PASS with `5 passed`.
- Safety scan PASS.
- Smoke PASS.
- `git diff --cached --check` PASS before commit.
- Forbidden overclaim/enabling scan PASS.

Warnings:

- Nasdaq Trader current directory did not source `WBA`, `MMC`, `SQ`, `CTRA`, and `JNPR`; they were Tencent-visible only and excluded.
- 17 historical/delisted legacy symbols were excluded.
- 7 selected symbols produced `N/A` parse errors and were not written.
- Raw staged data is local ignored data and was not committed.

Audit focus:

- Confirm current-universe staging is accepted with warnings.
- Confirm residual legacy/historical exclusions are correctly recorded as a future source/policy decision rather than silently filled.
- Confirm no recommendation, eligibility, readiness, product route, or trading path is created.

### 4. market_data Product-Route Preparation

Batch: `WINDOWS_WSL2_AUTHORIZED_CONTROLLED_ADVANCEMENT_20260707`
Workstream: `HG-EXEC-TASK-MD-PRODUCT-ROUTE-PREP-20260707`

Source state:

- Repo: `/home/rongyu/workspace/market_data`
- Branch: `main`
- Commit: `64840aa60e520cb7f0aa17078b941e0c4bc1586e`
- Tree: `714ac212837c57a1ae42f3dec1a00c80b04ea09c`
- Push: pushed to `origin/main`
- Status: `ACCEPTED_PRODUCT_ROUTE_PREP_EXTERNAL_AUDIT_GATED`
- External-audit trigger open: `yes`

Source artifacts:

- `reports/codex_dev/windows_wsl2_authorized_controlled_advancement_md_product_route_prep_diff_20260707.json`
- `reports/codex_dev/windows_wsl2_authorized_controlled_advancement_md_product_route_prep_diff_20260707.md`
- `reports/codex_dev/windows_wsl2_authorized_controlled_advancement_md_product_route_prep_rollback_20260707.md`
- `reports/codex_dev/windows_wsl2_authorized_controlled_advancement_md_validation_matrix_20260707.json`
- `reports/codex_dev/windows_wsl2_authorized_controlled_advancement_md_external_audit_packet_20260707.md`
- `tests/test_windows_wsl2_md_product_route_prep_20260707.py`

Route facts:

- Old active route remains `MARKET-DATA-1` / `local_17b656b7acaebc19963a32d8` / 50 symbols / 86,817 rows.
- Prepared replacement route targets `a_db_2_core_297_20260702_193900` / 281 symbols / 572,661 rows.
- Active registry changed: `false`.
- Prepared route is `PREPARED_NOT_ACTIVE_EXTERNAL_AUDIT_REQUIRED`.

Validation reported:

- Focused tests PASS with `6 passed`.
- Access-gate regression PASS.
- JSON parse PASS.
- `git diff HEAD~1..HEAD --check` PASS.
- Forbidden readiness/broker/live/auto true scan PASS.
- Raw data import true scan PASS.

Codex-Audit result:

- Reviewed commit: `64840aa60e520cb7f0aa17078b941e0c4bc1586e`
- Status: `PASS`
- Findings requiring source fixes: none
- External-audit trigger open: `YES_APPROPRIATE`
- Boundary result: PASS

Audit focus:

- Confirm product-route preparation can be accepted as preparation only.
- Confirm external-audit trigger is correctly open before activation.
- Confirm no active registry replacement, readiness activation, product route activation, recommendation readiness, ticket, eligibility candidate, broker/live/auto, raw import, schema migration, or secret access occurred.
- Confirm later activation requires a separate authorized and audited task.

### 5. RTX 5090 Power Cap Policy

Policy file:

- `reports/human_gate/windows_wsl2_5090_gpu_power_cap_policy_20260707.md`

New rule:

- Subsequent RTX 5090 numerical research, ML research, CUDA smoke, and GPU diagnostic work must use `GPU_POWER_LIMIT_WATTS=400`.
- Higher-than-400W operation requires separate user authorization before execution.
- Future callbacks must include `GPU_POWER_CAP_STATUS`.

Audit focus:

- Confirm this is a restrictive power policy only.
- Confirm it does not authorize broader GPU workload scope, local LLM/Qwen, model deployment, product activation, readiness promotion, or trading.

## Open Items / Residual Blockers

- User-operated external audit verdict is still required for market_data product-route preparation before any activation.
- No market_data activation task has been created.
- Broader East Money reconciliation/integration remains a future separately authorized task.
- Complete legacy US metadata repair for Tencent-only/current-source conflicts and historical/delisted names requires a separate source/policy decision if needed.
- Future RTX 5090 workloads above 400W require separate authorization.

## Boundary Statement

Across the post-R15 work reviewed in this packet:

- No recommendation/advice was produced.
- No `PENDING_HUMAN_REVIEW` ticket was created.
- No eligibility candidate was created.
- No strategy candidate was promoted.
- No data-clear promotion occurred.
- No product-route activation occurred.
- No production readiness was claimed.
- No broker/order/paper/live/auto path was enabled.
- No raw-data migration into `quant-proj` occurred.
- No `.env`, key, token, auth, credential, or secret output occurred.
- No local LLM or Qwen deployment occurred.
- No higher-than-400W RTX 5090 authorization was granted.

## External Audit Questions

1. Can R16 be accepted as closed research-only strategy discovery with warnings and no required fixes before the next ordinary research batch?
2. Can the A_Share_Monitor GPU Phase2/Phase3 and bounded East Money probe be accepted as research-only diagnostics with warnings?
3. Can the US_Stock_Monitor metadata repair / bounded staging be accepted with warnings, preserving residual legacy-source exclusions as future policy/source work?
4. Can the market_data product-route prep package be accepted as preparation-only, with no activation permission?
5. Is `EXTERNAL_AUDIT_TRIGGER_OPEN: yes` appropriate only for the market_data product-route preparation before any activation?
6. Are any fixes required before the user may authorize a later, separate market_data activation task?
7. Does the RTX 5090 400W cap correctly preserve a more restrictive execution boundary?

## Expected Verdict Format

```text
VERDICT:
EXTERNAL_AUDIT_TRIGGER_OPEN:
FIXES_REQUIRED:
ACCEPTED_SCOPE:
REJECTED_OR_BLOCKED_SCOPE:
BOUNDARY_RESULT:
NEXT_TASKS:
```
