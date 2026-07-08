# WINDOWS_WSL2_TARGETED_STRATEGY_REPAIR_AND_PROBE_R25_20260708 intake

Recorded: 2026-07-09 Asia/Shanghai

## Intake status

Status: `INTAKE_RECORDED_READY_FOR_DISPATCH`

Controller branch: `codex/task-packet-r25-targeted-strategy-repair-and-probe-20260708`

## Why R25 exists

R24 closed the current strategy work with no local/wide probe eligibility and no strategy candidate, but it left two focused research openings:

- A-share pass77 feature repair: one `CONTINUE_RESEARCH` feature and four `REPAIR_FEATURE` features.
- ETF amount/turnover rotation: five `REGIME_DEPENDENT_ONLY` variants.

R25 is a targeted strategy repair/probe sprint, not a process cleanup or new architecture batch.

## Accepted R24 source evidence

| repo | branch | commit | tree | role |
| --- | --- | --- | --- | --- |
| `A_Share_Monitor` | `codex/task-packet-r20-v2-20260708` | `a9b4ac5b0c2ff3b48b5be60af01a1c3499f72124` | `3571b1f1342c4815bbf99a41733fb0368bdf4a5a` | R24 source artifacts |
| `strategy_work` | `main` | `c854ddc384b041143eafd7f5e6cd612ea1aeef04` | `84a186fb23227cc68f6f5a700cff0c2640491f3d` | R24 final sync |
| `quant-proj` | `codex/task-packet-r22-materialized-feature-strategy-lab-20260708` | `ebbe36df0c34e653f85565d3bd54ba878aeae8e6` | `606469af33c727180464accfb58a0c1cf293bb4e` | R24 controller closeout |

## R24 state to preserve

- `LOCAL_PROBE_ELIGIBLE=0`
- `WIDE_PROBE_ELIGIBLE=0`
- `STRATEGY_CANDIDATE_AVAILABLE=false`
- `CONTINUE_RESEARCH=1`
- `REPAIR_FEATURE=4`
- `REGIME_DEPENDENT_ONLY=6`

## R25 source targets

| target repo | requested work |
| --- | --- |
| `/home/rongyu/workspace/A_Share_Monitor` | Run A-share pass77 feature repair, ETF regime-dependent diagnostics, and final R25 decision board. |
| `/home/rongyu/workspace/strategy_work` | Prepare R25 strategy memo and final sync after accepted A_Share_Monitor R25 callback. |

`market_data` support is not required unless a source callback determines that overclaim contracts need R25 label updates. Do not create process-only market_data work by default.

## Expected source outputs

- `reports/workspace_dispatch/a_share_r25_repair_feature_experiment_results.csv`
- `reports/workspace_dispatch/a_share_r25_pass77_repair_decision_board.csv`
- `reports/workspace_dispatch/a_share_r25_probe_or_retire_memo.md`
- `reports/workspace_dispatch/etf_r25_regime_dependent_rotation_results.csv`
- `reports/workspace_dispatch/etf_r25_regime_walkforward_stress.csv`
- `reports/workspace_dispatch/etf_r25_keep_benchmark_retire_board.csv`
- `reports/workspace_dispatch/r25_final_strategy_decision_board.csv`
- `reports/workspace_dispatch/r25_final_strategy_research_memo.md`

## Boundary

Research-only. No actionable output, recommendation/advice, ticket, candidate promotion, readiness/product route, daily signal, broker/order/paper/live/auto, full-frame wide3068, test-result parameter selection, non-public/auth-required provider access, or secret output.

## Next step

Dispatch source work using `reports/agent_handoff/windows_wsl2_targeted_strategy_repair_and_probe_r25_dispatcher_prompt_20260708.md`.
