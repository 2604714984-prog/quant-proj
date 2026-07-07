# WINDOWS_WSL2_STRATEGY_SIGNAL_MINING_BATCH_R17_20260707 Result Summary

Project: quant-proj
Role: Quant-Dispatcher
Recorded: 2026-07-07 Asia/Shanghai
Status: `CLOSED_ACCEPTED_RESEARCH_ONLY_WITH_WARNINGS`
External-audit trigger open for R17: `no`

## Received Callbacks

| Source | Commit | Status | Follow-up |
|---|---|---|---|
| `A_Share_Monitor` | `e9ed119f69413d7432904e11f12f7c4ff3c9243f` | `COMPLETED_RESEARCH_ONLY_WITH_WARNINGS` | pushed to origin branch; no wide-eligible strategy |
| `market_data` | `84b752da2a602995aa5a1ce95755385a4ad44455` | `ACCEPTED_RESEARCH_ONLY_WITH_VALIDATION_PASS` | pushed to origin/main; route activation remains blocked |
| `strategy_work` | `3e2215f56d19ee2bf6c85176be189ceae1b3f0a3` | `CODEX_ACCEPTANCE_SW_R17_FINAL_SYNC_RESEARCH_ONLY_WITH_WARNINGS` | pushed to origin/main; final sync complete |

## Final State

- `strategy_work` R17 final sync is complete.
- A_Share_Monitor R17 completed after the user explicitly revoked the 400W cap and directed continuation.
- A_Share_Monitor R17 commit `e9ed119f69413d7432904e11f12f7c4ff3c9243f` is pushed to `origin/codex/harden-a-share-research-pipeline`.
- `market_data` R17 commit `84b752da2a602995aa5a1ce95755385a4ad44455` is pushed to `origin/main`.
- `strategy_work` final sync commit `3e2215f56d19ee2bf6c85176be189ceae1b3f0a3` is pushed to `origin/main`.

## A_Share_Monitor Prior Blocker

R17 stopped before `A-WIN-R17-1` through `A-WIN-R17-8`.

Observed GPU state:

- RTX 5090 visible.
- Current power limit: `600.00W`.
- Prior required power limit before revocation: `400W`.
- Attempt to run `nvidia-smi -pl 400` failed with `Insufficient Permissions`.
- Sustained GPU work executed: `false`.

Controller confirmed the same permission blocker from both Windows and WSL command contexts.

## GPU Power Policy Revocation

After the blocker, the user explicitly revoked the 400W cap and directed R17 to continue.

New controller record:

- `reports/human_gate/windows_wsl2_5090_gpu_power_cap_revocation_20260707.md`
- decision id: `HG-STANDING-GPU-POWER-CAP-REVOKED-R17-20260707`

R17 may proceed under host/driver default GPU power policy. Downstream must still report observed power limit/draw and preserve all research-only boundaries.

## A_Share_Monitor Accepted Scope

A_Share_Monitor completed `A-WIN-R17-1` through `A-WIN-R17-8` as research-only signal mining:

- evidence freeze preserved R16 labels `WEAK=5`, `UNSTABLE=8`, `POSITIVE=1`;
- East Money split preserved as `77/121/2870`;
- single positive factor identified as `medium_overlap_198_not_pass / low_vol_20`;
- four signal transformations pre-registered before diagnostics;
- small/medium transformed-signal diagnostics produced 8 rows and 0 wide-prequalified rows;
- wide3068 result: `NO_R17_WIDE_PROBE_ELIGIBLE_STRATEGY`;
- no chunked wide probe executed and no full-frame wide3068 run attempted;
- `strategy_candidate_available=false`.

GPU policy status: `GPU_POWER_POLICY_REVOKED_PROCEEDED_UNDER_HOST_DRIVER_DEFAULT`; observed power limit stayed `600.0W`; sustained CuPy fixed matrix-multiply workload executed; no privileged or manual power-limit change was attempted.

## market_data Accepted Scope

market_data completed the R17 boundary/schema work:

- product-route prep remains inactive and separated;
- current active route remains the 50-symbol `MARKET-DATA-1` route;
- R17 strategy mining does not depend on the prepared product route;
- `R17_WIDE_PROBE_ELIGIBLE` is encoded as not candidate, readiness, recommendation, or ticket evidence.

## Push Confirmations

- A_Share_Monitor push PASS: `origin/codex/harden-a-share-research-pipeline` resolves to `e9ed119f69413d7432904e11f12f7c4ff3c9243f`.
- market_data push PASS: `origin/main` resolves to `84b752da2a602995aa5a1ce95755385a4ad44455`.
- strategy_work push PASS: `origin/main` aligned with `3e2215f56d19ee2bf6c85176be189ceae1b3f0a3`.

## strategy_work Final Sync

strategy_work completed:

- `reports/planning/windows_wsl2_strategy_signal_mining_batch_r17_20260707_strategy_memo.md`
- `reports/planning/windows_wsl2_strategy_signal_mining_batch_r17_final_sync_20260707.md`

Validation: `git diff --check HEAD~1..HEAD` PASS; forbidden action-word scan PASS; no candidate promotion scan PASS; no recommendation/advice scan PASS; push PASS.

## Boundary Result

No recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket, eligibility candidate, strategy candidate promotion, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, raw-data migration, unapproved network/provider fetch, DB/cache write/rebuild, secret output, or unrecorded GPU policy change occurred.

## Next Controller Action

R17 is closed. No further R17 source action is required. Any future work should be opened as a new research-only task batch unless a separate approved scope change is provided.
