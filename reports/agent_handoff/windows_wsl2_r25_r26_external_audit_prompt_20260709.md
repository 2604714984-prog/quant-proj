# R25 and R26 External Audit Prompt

Please perform a GitHub/local-evidence external audit of:

1. `WINDOWS_WSL2_TARGETED_STRATEGY_REPAIR_AND_PROBE_R25_20260708`
2. `WINDOWS_WSL2_REPORT_EVIDENCE_REMEDIATION_R26_20260709`

Use the controller summaries and closeouts first:

- `reports/workspace_dispatch/windows_wsl2_targeted_strategy_repair_and_probe_r25_20260708_result_summary.md`
- `reports/workspace_dispatch/windows_wsl2_targeted_strategy_repair_and_probe_r25_20260708_closeout.md`
- `reports/workspace_dispatch/windows_wsl2_report_evidence_remediation_r26_20260709_result_summary.md`
- `reports/workspace_dispatch/windows_wsl2_report_evidence_remediation_r26_20260709_closeout.md`

Then verify the source artifacts.

## R25 source evidence to verify

### A_Share_Monitor

Repo: `/home/rongyu/workspace/A_Share_Monitor`

Branch: `codex/task-packet-r25-targeted-strategy-repair-and-probe-20260708`

Commit: `fe0b7a8a7ff7c0afcb5b2952cf8cfc123a8e8647`

Tree: `a783667aa25c8732eb64926ae6ad325fecb49446`

Remote: `origin/codex/task-packet-r25-targeted-strategy-repair-and-probe-20260708`

Primary artifacts:

- `reports/workspace_dispatch/a_share_r25_repair_feature_experiment_results.csv`
- `reports/workspace_dispatch/a_share_r25_pass77_repair_decision_board.csv`
- `reports/workspace_dispatch/a_share_r25_probe_or_retire_memo.md`
- `reports/workspace_dispatch/etf_r25_regime_dependent_rotation_results.csv`
- `reports/workspace_dispatch/etf_r25_regime_walkforward_stress.csv`
- `reports/workspace_dispatch/etf_r25_keep_benchmark_retire_board.csv`
- `reports/workspace_dispatch/r25_final_strategy_decision_board.csv`
- `reports/workspace_dispatch/r25_final_strategy_research_memo.md`
- `reports/workspace_dispatch/windows_wsl2_r25_targeted_strategy_repair_and_probe_summary_20260708.json`
- `reports/runops/r25_targeted_strategy_repair_and_probe_20260708/r25_input_manifest_20260708.json`
- `reports/runops/r25_targeted_strategy_repair_and_probe_20260708/command_transcript.txt`

Expected R25 findings:

- A-share repair rows: 26.
- `REPAIRED_RESEARCH_SIGNAL=16`, `STILL_DIVERGENT=9`, `REVERSE_ONLY=1`.
- `peg_proxy=CONTINUE_RESEARCH`.
- Four other pass77 features are `REPAIR_AGAIN_ON_NEW_DATA_ONLY`.
- ETF fixed regime-on variants tested: 3.
- `RETIRE_ETF_ROTATION=3`.
- Final counts: `CONTINUE_RESEARCH=1`, `REPAIR_AGAIN_ON_NEW_DATA_ONLY=4`, `RETIRE=3`, local eligible 0, wide eligible 0.
- `STRATEGY_CANDIDATE_AVAILABLE=false`.

### strategy_work

Repo: `/home/rongyu/workspace/strategy_work`

Branch: `main`

Commit: `83192e737ae929eb00ee795f606bec4cc3eef17c`

Tree: `5e67f90109f99d1de5e1b6d0220edcf101127e61`

Remote: `origin/main`

Primary artifacts:

- `reports/planning/windows_wsl2_targeted_strategy_repair_and_probe_r25_strategy_memo_20260708.md`
- `reports/planning/windows_wsl2_targeted_strategy_repair_and_probe_r25_final_sync_20260708.md`

## R26 source evidence to verify

### us_stock_30w

Repo: `/home/rongyu/workspace/us_stock_30w`

Branch: `master`

Commit: `4f6a0ecfe398c942c45d36cc02604788c5c49268`

Tree: `38cb48ad12e744edd44c6c10b76c0ec30a610d4d`

Remote: none configured.

US30W-R22-001 artifacts:

- `reports/US30W-R22-001_strategy_report.md`
- `reports/US30W-R22-001_reaudit_remediation_20260709.md`
- `reports/US30W-R22-001_reaudit_remediation_20260709.json`
- `reports/US30W-R22-001_reaudit_remediation_20260709_command_transcript.txt`

US30W-R22-002 artifacts:

- `reports/US30W-R22-002_final_strategy.md`, sha256 `b5e2ece8b8cf0af538619e77a61330b53331e398d848582110aa4e85666fc8aa`
- `scripts/run_pipeline.sh`, sha256 `5f40d325070aa5ea314b9126b6317254327939af780d2a33af9a74140599f8d8`
- `outputs/pipeline_20260709_003550/baseline.json`, sha256 `2f3d8ecde1c9cf37ce96aaf7a3142b566edb72fa846eeec32c6f188a04dc9ce0`
- `outputs/pipeline_20260709_003550/adaptive_quality.json`, sha256 `321c1a932336f856467f65f83951183c51ea8f4ab487bcbda80ad35c83e4ef9c`

Expected US30W-R22-002 reproduction:

- Run: `cd /home/rongyu/workspace/us_stock_30w && bash scripts/run_pipeline.sh`
- Stage 0 safety PASS.
- Stage 1 data: 107 symbols, real snapshot.
- Baseline: Full Sharpe +0.6440, validation Sharpe +2.4278, test Sharpe +0.5609, max drawdown -20.5%, fills 133.
- Adaptive quality: Full Sharpe +0.7880, validation Sharpe +1.8529, test Sharpe +0.7205, max drawdown -11.0%, fills 202.
- Stage 4 audit: 15 passed, safety PASS.
- JSON outputs must have `synthetic_data=false`.
- Accepted status is research-only observation evidence, not candidate/paper/live/readiness/product/trading evidence.

### US_Stock_Monitor

Repo: `/home/rongyu/workspace/US_Stock_Monitor`

Branch: `main`

Commit: `499414a70b99d031ede7ecc89d6a64751c74eacc`

Tree: `c9bfa3c0a4c52fb24fe6b576d85a26d647c600e6`

Remote: `origin/main`

Use this repo only as support evidence for US30W remediation. Confirm tracked state is clean and local-only probes are not evidence inputs.

### A_Share_Monitor SmallCap remediation

Repo: `/home/rongyu/workspace/A_Share_Monitor`

Branch: `codex/r26-smallcap-remediation-20260709`

Commit: `b10ebfb4b2fd518fa7c6f178210212de44fd93ac`

Tree: `5dd269faaf0d14dfa2e404919313091ea0dbeb0f`

Remote: `origin/codex/r26-smallcap-remediation-20260709`

Primary artifacts:

- `reports/workspace_dispatch/smallcap_low_turnover_reaudit_remediation_20260709.md`
- `reports/workspace_dispatch/smallcap_low_turnover_reaudit_remediation_20260709.json`
- `scripts/smallcap_low_turnover_evidence_gen.py`
- `tests/test_smallcap_r26_engine_fixes.py`
- `reports/runops/smallcap_low_turnover_r26_audit_evidence_20260709/`

Expected SmallCap remediation findings:

- Engine/rules fixes are committed, not dirty local diff:
  - `qta/backtest/engine.py`
  - `qta/strategies/rules.py`
- Evidence generator is committed:
  - `scripts/smallcap_low_turnover_evidence_gen.py`
- Source-local evidence package is tracked under:
  - `reports/runops/smallcap_low_turnover_r26_audit_evidence_20260709/`
- R21/R23/unaccepted leftovers were not included in commit `b10ebfb...`; they were archived in stash:
  - `stash@{0}: On codex/r26-smallcap-remediation-20260709: archive-unaccepted-r21-r23-r26-leftovers-20260709`
- Accepted status is research-only evidence package available; `STRATEGY_CANDIDATE_AVAILABLE=false`, `PAPER_TRADING_CANDIDATE=false`, `LIVE_TRADING=false`.

## Primary audit questions

1. Can R25 be accepted as `CLOSED_ACCEPTED_RESEARCH_ONLY_NO_PROBE_ELIGIBLE` with no fixes required?
2. Can R26 be accepted as `CLOSED_ACCEPTED_RESEARCH_ONLY_REPORT_EVIDENCE_REMEDIATION` with no fixes required?
3. Are US30W-R22-001 prior unsupported claims corrected and downgraded?
4. Is US30W-R22-002 reproducible as real-data research-only observation evidence?
5. Are SmallCap Low Turnover engine fixes, evidence generator, tests, and tracked evidence package committed and reproducible enough for research-only evidence acceptance?
6. Did any reviewed artifact create recommendation/advice, ticket, candidate promotion, readiness/product route, daily signal, broker/order/paper/live/auto, full-frame wide3068, test-result parameter selection, or secret exposure?

Return:

```text
VERDICT:
R25_STATUS:
R26_STATUS:
EXTERNAL_AUDIT_TRIGGER_OPEN:
FIXES_REQUIRED:
ACCEPTED_SCOPE:
REJECTED_OR_BLOCKED_SCOPE:
BOUNDARY_RESULT:
NEXT_TASKS:
```
