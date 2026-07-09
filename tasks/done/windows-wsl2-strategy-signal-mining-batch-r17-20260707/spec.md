# WINDOWS_WSL2_STRATEGY_SIGNAL_MINING_BATCH_R17_20260707 Spec

## Objective

Use the accepted R16 plus GPU Phase2/Phase3 evidence to mine concrete strategy hypotheses and signal transformations.

Do not revisit controller/gate architecture. Do not activate market_data routes. Do not create recommendation, ticket, eligibility candidate, readiness, product route, or trading path.

## Classification

Ordinary research-only strategy signal mining batch.

External-audit trigger opened by this R17 batch: `no`.

The market_data product-route prep / future activation external-audit gate remains open separately and is not an activation permission.

## Required Inputs

- R16 factor diagnostics and hypothesis catalog.
- R16 small/medium scout diagnostics.
- GPU Phase2 parity, factor, significance, neutralization, cost/capacity, regime, and anomaly outputs.
- GPU Phase3 ML signal outputs.
- R15/R16 East Money split: `77 CROSSCHECK_PASS`, `121 CROSSCHECK_DATE_GAP`, `2870 CROSSCHECK_MISSING_EAST_MONEY`.
- Survivor-bias scope limits.
- Full-frame wide3068 StrategySearch unsafe guard.
- RTX 5090 power policy: the prior 400W cap was revoked by the user on 2026-07-07T16:32:56+08:00; R17 may proceed under host/driver default GPU power policy while reporting observed telemetry.

## Tasks

| ID | Owner | Task | Dependency |
|---|---|---|---|
| `A-WIN-R17-1` | `A_Share_Monitor` | Freeze post-R16 GPU evidence surface. | accepted R16 + GPU Phase2/3 artifacts |
| `A-WIN-R17-2` | `A_Share_Monitor` | Mine the single positive factor and unstable-factor clusters. | `A-WIN-R17-1` |
| `A-WIN-R17-3` | `A_Share_Monitor` | GPU ML signal decile-to-strategy bridge. | `A-WIN-R17-1` |
| `A-WIN-R17-4` | `A_Share_Monitor` | Pre-register strategy transformations from signal evidence. | `A-WIN-R17-2`, `A-WIN-R17-3` |
| `A-WIN-R17-5` | `A_Share_Monitor` | Small-cache diagnostic backtests for transformed signals. | `A-WIN-R17-4` |
| `A-WIN-R17-6` | `A_Share_Monitor` | Wide3068 chunked probe only for pre-qualified families. | `A-WIN-R17-5`, full-frame guard active |
| `A-WIN-R17-7` | `A_Share_Monitor` | Trade-count and cost rescue for ML/factor-derived signals. | `A-WIN-R17-5` or `A-WIN-R17-6` if run |
| `A-WIN-R17-8` | `A_Share_Monitor` | GPU power-policy telemetry and compliance report. | any R17 GPU work |
| `MD-WIN-R17-1` | `market_data` | Keep product-route prep inactive and separated. | market_data prep audit state |
| `MD-WIN-R17-2` | `market_data` | Strategy-signal evidence manifest extension. | A-share R17 artifact paths |
| `SW-WIN-R17-1` | `strategy_work` | Strategy signal mining memo. | R17 dispatch; final facts require source callbacks |
| `SW-WIN-R17-2` | `strategy_work` | Final sync after A-share and market_data callbacks. | accepted A-share and market_data R17 callbacks |
| `QP-WIN-R17-1` | `quant-proj` | Intake, task packet, Human-Gate classification, dispatch summary. | done by dispatcher |
| `QP-WIN-R17-2` | `quant-proj` | Result summary and closeout. | downstream callbacks |

## Required A_Share_Monitor Deliverables

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
- `reports/workspace_dispatch/windows_wsl2_r17_gpu_power_policy_compliance_20260707.md`

## Required market_data Deliverables

- `reports/codex_dev/windows_wsl2_r17_product_route_prep_inactive_boundary_20260707.md`
- `reports/codex_dev/windows_wsl2_r17_strategy_signal_manifest_schema.md`
- `reports/codex_dev/windows_wsl2_r17_strategy_signal_manifest_schema.json`

## Required strategy_work Deliverables

- `reports/planning/windows_wsl2_strategy_signal_mining_batch_r17_20260707_strategy_memo.md`
- `reports/planning/windows_wsl2_strategy_signal_mining_batch_r17_final_sync_20260707.md`

## R17 Signal Rules

- Identify the one R16 positive factor and explain why it did not create a wide-eligible strategy.
- Cluster unstable factor failure modes without promoting or discarding them as strategy claims.
- Map GPU Phase3 ML scores into research-only signal structures before backtesting.
- Pre-register transformations before diagnostic backtests.
- Do not select parameters from test results.
- A family may only receive `R17_WIDE_PROBE_ELIGIBLE`, never candidate status.
- `R17_WIDE_PROBE_ELIGIBLE` is not candidate/readiness/ticket/recommendation evidence.

## Wide3068 Rule

Full-frame wide3068 StrategySearch remains blocked.

Only run a wide3068 chunked probe if A-WIN-R17-5 produces pre-qualified families under explicit pre-registered rules. If none qualify, output `NO_R17_WIDE_PROBE_ELIGIBLE_STRATEGY`.

## GPU Power Rule

The previous `GPU_POWER_LIMIT_WATTS=400` rule is revoked by user instruction.

R17 GPU work may proceed under host/driver default power policy. Downstream must record observed `power.limit`, `power.draw` where available, and whether sustained GPU work was executed.

Do not attempt privileged power-limit changes unless explicitly requested in a later task.

## Required Validation

A_Share_Monitor:

- py_compile PASS for changed Python files.
- focused pytest PASS.
- `agent_safety_check.py` PASS where applicable.
- JSON parse PASS where applicable.
- `git diff --check` PASS.
- forbidden overclaim scan PASS.
- full-frame wide3068 not run.
- no market_data route activation.
- no unapproved network/provider fetch.
- no unapproved DB/cache rebuild or write.
- GPU power-policy status recorded for GPU work.

market_data:

- focused pytest PASS if tests are changed.
- JSON parse PASS where applicable.
- `git diff --check` PASS.
- no product/readiness/registry activation.
- no raw data import.
- prepared route remains inactive.

strategy_work:

- `git diff --check` PASS.
- forbidden action-word scan PASS.
- no candidate promotion.
- no recommendation/advice.
- final sync only after A-share and market_data callbacks.

## Stop Conditions

- `FULL_FRAME_WIDE_STRATEGY_SEARCH_ATTEMPTED`
- `MARKET_DATA_PRODUCT_ROUTE_ACTIVATION_ATTEMPTED`
- `R17_WIDE_PROBE_ELIGIBLE_WRITTEN_AS_CANDIDATE`
- `TEST_RESULT_USED_TO_SELECT_PARAMETERS`
- `RECOMMENDATION_OR_TICKET_LANGUAGE_APPEARS`
- `SECRET_OR_ENV_ACCESS_REQUIRED`
- `NETWORK_OR_DB_WRITE_REQUIRED_WITHOUT_HG_EXEC`

## Required Callback Envelope

```text
CALLBACK_ENVELOPE:
BATCH: WINDOWS_WSL2_STRATEGY_SIGNAL_MINING_BATCH_R17_20260707
TARGET_REPO:
BRANCH:
COMMIT:
TREE:
STATUS:
TASKS_COMPLETED:
ARTIFACTS:
VALIDATION:
KEY_RESULTS:
STRATEGY_CANDIDATE_AVAILABLE:
GPU_POWER_POLICY_STATUS:
BOUNDARY_RESULT:
EXTERNAL_AUDIT_TRIGGER_OPEN:
FIXES_REQUIRED:
NEXT_SOURCE_ACTION:
```

## Boundary

Research-only. No recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket, eligibility candidate, strategy candidate promotion, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, raw-data migration, `.env` access, key output, secret handling, schema/readiness/registry change, or market_data activation is authorized.
