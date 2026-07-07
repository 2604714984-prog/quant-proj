# Handoff: market_data R17 Strategy Signal Manifest

Target repo: `/home/rongyu/workspace/market_data`
Controller repo: `/home/rongyu/workspace/quant-proj`
Callback target: Quant-Dispatcher thread `019f3830-4b44-7a83-944d-247a0d4dc169`
Batch: `WINDOWS_WSL2_STRATEGY_SIGNAL_MINING_BATCH_R17_20260707`

## Assigned Tasks

- `MD-WIN-R17-1`: Keep product-route prep inactive and separated.
- `MD-WIN-R17-2`: Strategy-signal evidence manifest extension.

## Required Deliverables

- `reports/codex_dev/windows_wsl2_r17_product_route_prep_inactive_boundary_20260707.md`
- `reports/codex_dev/windows_wsl2_r17_strategy_signal_manifest_schema.md`
- `reports/codex_dev/windows_wsl2_r17_strategy_signal_manifest_schema.json`

## Required Boundary

- No product-route activation.
- No active registry change.
- No readiness change.
- No raw data import.
- R17 strategy mining must not depend on the prepared product route.
- The current active route remains current until a separate activation task is externally approved.
- `R17_WIDE_PROBE_ELIGIBLE` must be encoded as not candidate, not readiness, not recommendation, and not ticket evidence.

## Validation

Run focused tests if tests are changed, JSON parse for JSON artifacts, `git diff --check`, and forbidden activation/readiness/raw-data scans.

## Callback

Return the required R17 callback envelope prompt-only to the Quant-Dispatcher thread.
