# WINDOWS_WSL2_EVIDENCE_BACKED_STRATEGY_PROBE_R27_20260709 result summary

Recorded: 2026-07-09 Asia/Shanghai

## Verdict

Status: `ACCEPTED_RESEARCH_ONLY_NO_PROBE_ELIGIBLE`

R27 completed as an evidence-backed research-only hardening batch after R25/R26 external audit. It focused on SmallCap Low Turnover, US30W-R22-002, and the pass77 direct/proxy gate. It did not reopen retired ETF rotation or rerun pass77 repairs without improved source evidence.

## Accepted source state

| repo | branch | commit | tree | status |
| --- | --- | --- | --- | --- |
| A_Share_Monitor | `codex/r27-evidence-backed-strategy-probe-20260709` | `01e63bc532d1c1d75ab326fa607f953ed321b62d` | `24fd77a85b61570efd3e0b167b428c21ec089d96` | `COMPLETED_RESEARCH_ONLY_NO_PROBE_ELIGIBLE` |
| market_data | `codex/r27-evidence-backed-strategy-contract-20260709` | `bb215009e95fdfb69b397570f03258e168d5a4d8` | `708c7dacdf2a65377dbcb512bbe8c27ac5796070` | `ACCEPTED_RESEARCH_ONLY_CONTRACT_WITH_VALIDATION_PASS` |
| strategy_work | `main` | `b36641db36ee20e42ceaf40f9c2d12de6da8f259` | `e903928a11f301af3b33357cbe4a6036d3780583` | `CODEX_ACCEPTANCE_SW_R27_FINAL_SYNC_RESEARCH_ONLY_NO_PROBE_ELIGIBLE` |

## SmallCap status

`CONTINUE_RESEARCH`

R27 confirmed SmallCap Low Turnover is the strongest evidence-backed research line, but it remains blocked from local probe eligibility.

Key diagnostics:

- R27 sign-flip permutations: 500.
- R27 block-bootstrap runs: 500.
- Recomputed train Sharpe: `0.984330`.
- Sign-flip p-value greater/equal real: `0.012`.
- Walk-forward rows: 12.
- Cost/capacity rows: 18.
- Universe sensitivity rows: 12.

Main blocker: the accepted evidence package still lacks a preserved row-level pre-trade signal matrix and market-cap membership snapshot for full leakage/timing audit.

## US30W status

`REMOTE_PRESERVATION_REQUIRED` for adaptive quality and `OBSERVATION_ONLY` for baseline.

R27 reran the local real-data pipeline:

- Rerun output: `/home/rongyu/workspace/us_stock_30w/outputs/pipeline_20260709_014140`
- `synthetic_data=false`.
- `us_stock_30w` still has no remote configured.

## pass77 repair gate status

`REPAIR_ON_NEW_EVIDENCE_ONLY`

R27 reviewed the five fixed pass77 features and accepted no new direct public source field. Therefore, no pass77 strategy rerun was allowed.

## Final board counts

| status | count |
| --- | ---: |
| `CONTINUE_RESEARCH` | 1 |
| `OBSERVATION_ONLY` | 1 |
| `REMOTE_PRESERVATION_REQUIRED` | 1 |
| `REPAIR_ON_NEW_EVIDENCE_ONLY` | 1 |
| `RETIRE` | 1 |

`local_research_probe_eligible_count=0`

`wide_research_probe_eligible_count=0`

`strategy_candidate_available=false`

## Validation

- A_Share_Monitor R27 script `py_compile` PASS.
- A_Share_Monitor focused pytest PASS: 7 passed.
- A_Share_Monitor JSON parse PASS: 7 files.
- A_Share_Monitor CSV parse PASS: 9 files.
- A_Share_Monitor `agent_safety_check.py` PASS.
- A_Share_Monitor `git diff --check` PASS.
- A_Share_Monitor branch push and remote verification PASS.
- market_data focused pytest PASS: 3 passed.
- market_data JSON parse PASS.
- market_data `git diff --check` PASS.
- market_data branch push and remote verification PASS.
- strategy_work final sync `git diff --check` PASS.
- strategy_work push PASS.

## Boundary result

Research-only boundary preserved. No actionable output, recommendation/advice, ticket, candidate promotion, readiness/product-route/registry activation, daily signal, broker/order/paper/live/auto path, raw-data migration, active schema change, full-frame wide3068, test-result parameter selection, non-public/auth-required provider access, or secret output occurred.

## Fixes required

`none` for R27 research-only closeout.

Carry-forward blockers:

- SmallCap needs row-level signal matrix and market-cap membership preservation before local probe eligibility can be reconsidered.
- US30W needs remote preservation or mirrored evidence before stronger handling.
- pass77 needs direct public source evidence before repair reruns.
- ETF amount/turnover rotation remains retired under current accepted evidence.

## Next source action

Close R27 as research-only no-probe-eligible. Any next batch should focus on SmallCap evidence completeness or US30W remote preservation rather than broad strategy search.
