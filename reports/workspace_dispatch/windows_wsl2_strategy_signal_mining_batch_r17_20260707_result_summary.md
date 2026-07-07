# WINDOWS_WSL2_STRATEGY_SIGNAL_MINING_BATCH_R17_20260707 Result Summary

Project: quant-proj
Role: Quant-Dispatcher
Recorded: 2026-07-07 Asia/Shanghai
Status: `A_SHARE_RESUME_AUTHORIZED_AFTER_GPU_POWER_CAP_REVOCATION_MARKET_DATA_ACCEPTED`
External-audit trigger open for R17: `no`

## Received Callbacks

| Source | Commit | Status | Follow-up |
|---|---|---|---|
| `A_Share_Monitor` | `a1d57f55a94382e20bfd4a184ad21c42bf9bde37` | `BLOCKED_SUPERSEDED_BY_USER_POWER_POLICY_REVOCATION` | prior 400W cap blocker superseded; resume under host/driver default GPU power policy |
| `market_data` | `84b752da2a602995aa5a1ce95755385a4ad44455` | `ACCEPTED_RESEARCH_ONLY_WITH_VALIDATION_PASS` | push-only follow-up needed; route activation remains blocked |

## Pending

- `strategy_work` R17 final sync is gated because A_Share_Monitor R17 is blocked.
- R17 A-share signal mining is now authorized to resume because the user explicitly revoked the 400W cap and directed continuation.
- `market_data` R17 commit `84b752da2a602995aa5a1ce95755385a4ad44455` is local ahead of `origin/main` by 1 per controller verification; push confirmation is pending.

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

## market_data Accepted Scope

market_data completed the R17 boundary/schema work:

- product-route prep remains inactive and separated;
- current active route remains the 50-symbol `MARKET-DATA-1` route;
- R17 strategy mining does not depend on the prepared product route;
- `R17_WIDE_PROBE_ELIGIBLE` is encoded as not candidate, readiness, recommendation, or ticket evidence.

## Boundary Result

No recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket, eligibility candidate, strategy candidate promotion, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, raw-data migration, unapproved network/provider fetch, DB/cache write/rebuild, secret output, or unrecorded GPU policy change occurred.

## Next Controller Action

Resume the A_Share_Monitor R17 tasks under the revoked 400W cap policy and obtain a push-only confirmation for market_data commit `84b752da2a602995aa5a1ce95755385a4ad44455`.
