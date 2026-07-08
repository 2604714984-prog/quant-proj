# WINDOWS_WSL2_REPORT_EVIDENCE_REMEDIATION_R26_20260709 result summary

Recorded: 2026-07-09 Asia/Shanghai

## Verdict

Status: `ACCEPTED_RESEARCH_ONLY_REPORT_EVIDENCE_REMEDIATION`

R26 remediated the report evidence issues for the US30W reports and SmallCap Low Turnover report chain. The accepted outcome is evidence hygiene and research-only closeout, not strategy promotion.

## Accepted source state

| repo | branch | commit | tree | status |
| --- | --- | --- | --- | --- |
| us_stock_30w | `master` | `4f6a0ecfe398c942c45d36cc02604788c5c49268` | `38cb48ad12e744edd44c6c10b76c0ec30a610d4d` | local clean; no remote configured |
| US_Stock_Monitor | `main` | `499414a70b99d031ede7ecc89d6a64751c74eacc` | `c9bfa3c0a4c52fb24fe6b576d85a26d647c600e6` | pushed to `origin/main` |
| A_Share_Monitor | `codex/r26-smallcap-remediation-20260709` | `b10ebfb4b2fd518fa7c6f178210212de44fd93ac` | `5dd269faaf0d14dfa2e404919313091ea0dbeb0f` | pushed to origin branch |

## US30W-R22-001 remediation

The old US30W-R22-001 report framing was corrected. The prior phase2/deep-validation framing is invalidated because the executable phase2 path remains synthetic and rejected the momentum row on rerun. The real-data headline metrics are retained only as source-local reproducible research observation evidence from the tracked real-data pipeline.

Key accepted artifacts:

- `/home/rongyu/workspace/us_stock_30w/reports/US30W-R22-001_strategy_report.md`
- `/home/rongyu/workspace/us_stock_30w/reports/US30W-R22-001_reaudit_remediation_20260709.md`
- `/home/rongyu/workspace/us_stock_30w/reports/US30W-R22-001_reaudit_remediation_20260709.json`
- `/home/rongyu/workspace/us_stock_30w/reports/US30W-R22-001_reaudit_remediation_20260709_command_transcript.txt`

## US30W-R22-002 closeout

US30W-R22-002 is accepted only as reproducible research-only observation evidence.

Accepted report and pipeline:

- `/home/rongyu/workspace/us_stock_30w/reports/US30W-R22-002_final_strategy.md`, sha256 `b5e2ece8b8cf0af538619e77a61330b53331e398d848582110aa4e85666fc8aa`
- `/home/rongyu/workspace/us_stock_30w/scripts/run_pipeline.sh`, sha256 `5f40d325070aa5ea314b9126b6317254327939af780d2a33af9a74140599f8d8`

Controller-observed reproduction:

- Output dir: `/home/rongyu/workspace/us_stock_30w/outputs/pipeline_20260709_003550`
- Latest matching local output dir: `/home/rongyu/workspace/us_stock_30w/outputs/pipeline_20260709_003610`
- `baseline.json` sha256 `2f3d8ecde1c9cf37ce96aaf7a3142b566edb72fa846eeec32c6f188a04dc9ce0`
- `adaptive_quality.json` sha256 `321c1a932336f856467f65f83951183c51ea8f4ab487bcbda80ad35c83e4ef9c`

Observed metrics:

| strategy | full Sharpe | validation Sharpe | test Sharpe | max drawdown | fills |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline | +0.6440 | +2.4278 | +0.5609 | -20.5% | 133 |
| adaptive_quality | +0.7880 | +1.8529 | +0.7205 | -11.0% | 202 |

Both output JSON files record `synthetic_data=false`. Strategy status remains research observation only: `strategy_candidate_available=false`, `paper_trading_candidate=false`, `live_status=false`, and `readiness_or_product_route=false`.

## SmallCap Low Turnover remediation

SmallCap Low Turnover report boundary and reproducibility issues were remediated in A_Share_Monitor.

Accepted commit:

- `b10ebfb4b2fd518fa7c6f178210212de44fd93ac` on `origin/codex/r26-smallcap-remediation-20260709`

Key accepted artifacts:

- `reports/workspace_dispatch/smallcap_low_turnover_reaudit_remediation_20260709.md`, sha256 `c97d0bb060058d9d13e431bb8ca5dd05535cb2df0f3cdf91e9435c0d48ee99b7`
- `reports/workspace_dispatch/smallcap_low_turnover_reaudit_remediation_20260709.json`, sha256 `f4aa029f03ff1adac5eca719a7e3012f1430645c029371268ce7d04578c12977`
- `scripts/smallcap_low_turnover_evidence_gen.py`, sha256 `8314a725850f381a65b7b633b0f48b9fbb154d5801054da28f03b2ae4ebe5ce5`
- `tests/test_smallcap_r26_engine_fixes.py`, sha256 `be94dc6660a8451d82a9aac64622ad0d65bd96c932786279fa60f45224e6ff2c`
- `reports/runops/smallcap_low_turnover_r26_audit_evidence_20260709/manifest.json`, sha256 `12f198a64ceda547ea65425a411460c186a4cf940bcc4e74f45cf60de14a7646`

Committed engine/rules fixes:

- `qta/backtest/engine.py`: `_entry_candidates` supports `signal_score`; `_exit_reason` checks `max_holding_days`.
- `qta/strategies/rules.py`: empty rules are mode-aware, so empty exit rules no longer force exit under `mode != "any"`.

Tracked source-local evidence package:

- `engine_results.json`
- `equity_train.csv`, `equity_val.csv`, `equity_test.csv`
- `trades_train.csv`, `trades_val.csv`, `trades_test.csv`
- `raw_ic_train.csv`, `raw_ic_val.csv`
- `permutation_test.json`
- `manifest.json`

Accepted evidence status:

- `REPORT_REMEDIATION_RESULT=RESEARCH_ONLY_EVIDENCE_PACKAGE_AVAILABLE`
- `ENGINE_FIXES=COMMITTED`
- `EVIDENCE_PACKAGE=SOURCE_LOCAL_TRACKED`
- `STRATEGY_CANDIDATE_AVAILABLE=false`
- `PAPER_TRADING_CANDIDATE=false`
- `LIVE_TRADING=false`

Unaccepted leftovers were archived by stash, not deleted:

- `stash@{0}: On codex/r26-smallcap-remediation-20260709: archive-unaccepted-r21-r23-r26-leftovers-20260709`

## Validation

- US30W real pipeline rerun PASS.
- US30W JSON parse PASS.
- US30W tracked state clean.
- US_Stock_Monitor tracked state clean and pushed.
- SmallCap evidence generator `py_compile` PASS.
- SmallCap evidence generator execution PASS.
- SmallCap focused pytest PASS: `5 passed`.
- A_Share_Monitor `agent_safety_check.py` PASS.
- A_Share_Monitor JSON parse PASS.
- A_Share_Monitor `git diff --cached --check` PASS before commit.
- A_Share_Monitor branch pushed and remote verified.

## Boundary result

Research-only boundary preserved. No recommendation/advice, ticket, candidate promotion, readiness/product-route/registry activation, daily signal, broker/order/paper/live/auto path, raw-data migration, active schema change, non-public/auth-required provider access, or secret output occurred.

## Fixes required

`none` for R26 external audit acceptance.

Carry-forward caveats:

- `/home/rongyu/workspace/us_stock_30w` has no remote configured, so US30W evidence is local-only unless a remote is added.
- US30W phase2/deep-validation path remains synthetic and does not support prior real-data headline claims.
- US30W-R22-002 filename/content contains legacy `final` wording, but accepted status is research-only observation evidence.
- SmallCap evidence is research-only; no paper/live/readiness/product/candidate status is accepted.

## Next source action

External audit can verify R26 as research-only evidence remediation. Configure a remote for `us_stock_30w` only if remote preservation is required.
