# WINDOWS_WSL2_TARGETED_STRATEGY_REPAIR_AND_PROBE_R25_20260708 dispatcher prompt

DISPATCH WINDOWS_WSL2_TARGETED_STRATEGY_REPAIR_AND_PROBE_R25_20260708

Use accepted R24 evidence.

Goal:
Continue strategy research, but stop expanding process. R25 must focus only on the strategy lines that survived R24:
1. A-share pass77 fixed features.
2. ETF amount/turnover regime-dependent rotation.
3. Final strategy decision board.

Do not reopen controller/gate cleanup.
Do not create process-only reports.
Do not run broad grids.
Do not introduce new strategy families.
Do not repeat R19/R20/R24 grids.
Do not use unaccepted R23 output as evidence.

Read first:
- `tasks/in_progress/windows-wsl2-targeted-strategy-repair-and-probe-r25-20260708/spec.md`
- `reports/agent_handoff/windows_wsl2_targeted_strategy_repair_and_probe_r25_dispatcher_prompt_20260708.md`
- `reports/workspace_dispatch/windows_wsl2_targeted_strategy_repair_and_probe_r25_20260708_intake.md`
- `tasks/checklists/r25_execution_checklist_20260708.md`
- R24 result summary and closeout.
- A_Share_Monitor R24 source artifacts.
- strategy_work R24 final sync.

A-share tasks:
Use only:
- `peg_proxy`
- `funds_flow_proxy_score`
- `hot_money_proxy_score`
- `amount_z20`
- `turnover_z20`

Run fixed repair experiments:
- source proxy repair
- date-neutralized repair
- low-turnover filter
- rank residualized repair
- regime-guarded repair
- reverse-signal research for `peg_proxy` only as failure analysis

Output:
- `reports/workspace_dispatch/a_share_r25_repair_feature_experiment_results.csv`
- `reports/workspace_dispatch/a_share_r25_pass77_repair_decision_board.csv`
- `reports/workspace_dispatch/a_share_r25_probe_or_retire_memo.md`

ETF tasks:
Use only R24 ETF amount/turnover evidence.
Do not rerun old grids.
Test only:
- `turnover_throttled_regime_on`
- `defensive_fallback_regime_on`
- `slower_rebalance_regime_on`

Regime filters must be predefined:
- `ETF_CONTEXT_NEUTRAL`
- `ETF_CONTEXT_RISK_ON`
- `ETF_CONTEXT_RISK_OFF`
- drawdown-safe period
- liquidity-high bucket

Output:
- `reports/workspace_dispatch/etf_r25_regime_dependent_rotation_results.csv`
- `reports/workspace_dispatch/etf_r25_regime_walkforward_stress.csv`
- `reports/workspace_dispatch/etf_r25_keep_benchmark_retire_board.csv`

Final decision:
Produce:
- `reports/workspace_dispatch/r25_final_strategy_decision_board.csv`
- `reports/workspace_dispatch/r25_final_strategy_research_memo.md`

Allowed final labels:
- `LOCAL_RESEARCH_PROBE_ELIGIBLE`
- `WIDE_RESEARCH_PROBE_ELIGIBLE`
- `CONTINUE_RESEARCH`
- `BENCHMARK_ONLY`
- `REPAIR_AGAIN_ON_NEW_DATA_ONLY`
- `RETIRE`
- `DO_NOT_RETRY`

Hard boundaries:
Research-only.
No recommendation.
No ticket.
No candidate promotion.
No readiness.
No product route.
No daily signal.
No broker/order/paper/live/auto.
No full-frame wide3068.
No test-result parameter selection.
No secret access.

Callback:
Return commit, artifacts, validation, A-share results, ETF results, final decision board counts, local/wide eligible count, strategy_candidate_available, boundary result, and next action.
