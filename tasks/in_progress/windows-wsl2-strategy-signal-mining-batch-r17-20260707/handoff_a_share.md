# Handoff: A_Share_Monitor R17 Strategy Signal Mining

Target repo: `/home/rongyu/workspace/A_Share_Monitor`
Controller repo: `/home/rongyu/workspace/quant-proj`
Callback target: Quant-Dispatcher thread `019f3830-4b44-7a83-944d-247a0d4dc169`
Batch: `WINDOWS_WSL2_STRATEGY_SIGNAL_MINING_BATCH_R17_20260707`

## Assigned Tasks

- `A-WIN-R17-1`: Freeze post-R16 GPU evidence surface.
- `A-WIN-R17-2`: Mine the single positive factor and unstable-factor clusters.
- `A-WIN-R17-3`: GPU ML signal decile-to-strategy bridge.
- `A-WIN-R17-4`: Pre-register strategy transformations from signal evidence.
- `A-WIN-R17-5`: Small-cache diagnostic backtests for transformed signals.
- `A-WIN-R17-6`: Wide3068 chunked probe only for pre-qualified families.
- `A-WIN-R17-7`: Trade-count and cost rescue for ML/factor-derived signals.
- `A-WIN-R17-8`: 400W GPU telemetry and compliance report.

## Required Context

- R16 accepted state: no wide-eligible family, `strategy_candidate_available=false`.
- Factor diagnostic counts: `WEAK=5`, `UNSTABLE=8`, `POSITIVE=1`.
- GPU Phase2/Phase3 accepted as research diagnostics only.
- East Money bounded probe is probe-only; R15/R16 `77/121/2870` split remains preserved unless a later accepted source evidence update changes it.
- Full-frame wide3068 StrategySearch remains blocked.
- RTX 5090 power cap: `GPU_POWER_LIMIT_WATTS=400`.

## Required Deliverables

- `reports/workspace_dispatch/windows_wsl2_r17_strategy_signal_evidence_freeze_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_r17_strategy_signal_evidence_freeze_20260707.json`
- `reports/workspace_dispatch/windows_wsl2_r17_factor_signal_mining_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_r17_factor_signal_mining_20260707.csv`
- `reports/workspace_dispatch/windows_wsl2_r17_gpu_ml_signal_bridge_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_r17_gpu_ml_signal_bridge_20260707.csv`
- `reports/workspace_dispatch/windows_wsl2_r17_pre_registered_signal_transformations_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_r17_pre_registered_signal_transformations_20260707.json`
- `reports/workspace_dispatch/windows_wsl2_r17_small_medium_signal_strategy_diagnostics_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_r17_small_medium_signal_strategy_diagnostics.csv`
- `reports/workspace_dispatch/windows_wsl2_r17_wide3068_chunked_probe_result_or_skip_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_r17_wide3068_chunked_probe_result_or_skip.csv`
- `reports/workspace_dispatch/windows_wsl2_r17_trade_cost_rescue_for_signal_strategies_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_r17_trade_cost_rescue_for_signal_strategies.csv`
- `reports/workspace_dispatch/windows_wsl2_r17_gpu_400w_compliance_20260707.md`

## Validation

Run focused validation appropriate to changed files, including py_compile, focused pytest, JSON parse, `git diff --check`, safety/overclaim scans, full-frame guard check, and GPU power cap status for GPU work.

## Boundary

Research-only. No recommendation/advice, ticket, eligibility candidate, strategy candidate promotion, product route, readiness, broker/order/paper/live/auto, secrets, raw-data migration, unapproved network/provider fetch, unapproved DB/cache write, full-frame wide3068, or >400W GPU operation.
