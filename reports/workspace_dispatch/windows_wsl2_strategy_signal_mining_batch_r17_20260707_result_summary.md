# WINDOWS_WSL2_STRATEGY_SIGNAL_MINING_BATCH_R17_20260707 Result Summary

Project: quant-proj
Role: Quant-Dispatcher
Recorded: 2026-07-07 Asia/Shanghai
Status: `PARTIAL_CALLBACKS_RECEIVED_A_SHARE_BLOCKED_GPU_POWER_CAP_MARKET_DATA_ACCEPTED`
External-audit trigger open for R17: `no`

## Received Callbacks

| Source | Commit | Status | Follow-up |
|---|---|---|---|
| `A_Share_Monitor` | `a1d57f55a94382e20bfd4a184ad21c42bf9bde37` | `BLOCKED` | needs verifiable 400W RTX 5090 power cap before GPU-dependent R17 work |
| `market_data` | `84b752da2a602995aa5a1ce95755385a4ad44455` | `ACCEPTED_RESEARCH_ONLY_WITH_VALIDATION_PASS` | push-only follow-up needed; route activation remains blocked |

## Pending

- `strategy_work` R17 final sync is gated because A_Share_Monitor R17 is blocked.
- R17 A-share signal mining remains blocked until `GPU_POWER_LIMIT_WATTS=400` is verifiably enforced or the user explicitly authorizes a different non-sustained-GPU path.
- `market_data` R17 commit `84b752da2a602995aa5a1ce95755385a4ad44455` is local ahead of `origin/main` by 1 per controller verification; push confirmation is pending.

## A_Share_Monitor Blocker

R17 stopped before `A-WIN-R17-1` through `A-WIN-R17-8`.

Observed GPU state:

- RTX 5090 visible.
- Current power limit: `600.00W`.
- Required power limit: `400W`.
- Attempt to run `nvidia-smi -pl 400` failed with `Insufficient Permissions`.
- Sustained GPU work executed: `false`.

Controller confirmed the same permission blocker from both Windows and WSL command contexts.

## market_data Accepted Scope

market_data completed the R17 boundary/schema work:

- product-route prep remains inactive and separated;
- current active route remains the 50-symbol `MARKET-DATA-1` route;
- R17 strategy mining does not depend on the prepared product route;
- `R17_WIDE_PROBE_ELIGIBLE` is encoded as not candidate, readiness, recommendation, or ticket evidence.

## Boundary Result

No recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket, eligibility candidate, strategy candidate promotion, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, raw-data migration, unapproved network/provider fetch, DB/cache write/rebuild, secret output, or >400W GPU execution occurred.

## Next Controller Action

Ask the user to set or authorize a host/driver-level mechanism that makes `nvidia-smi` report `power.limit=400.00W` for the RTX 5090, then redispatch or resume the A_Share_Monitor R17 tasks. Do not run sustained GPU-dependent R17 work while the reported power limit remains `600.00W`.

Also obtain a push-only confirmation for market_data commit `84b752da2a602995aa5a1ce95755385a4ad44455`.
