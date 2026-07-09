# WINDOWS_WSL2_SMALLCAP_EVIDENCE_COMPLETION_R28_20260709 result summary

Recorded: 2026-07-09 Asia/Shanghai

## Verdict

Status: `ACCEPTED_RESEARCH_ONLY_EVIDENCE_INCOMPLETE_NO_PROBE_ELIGIBLE`

R28 completed SmallCap evidence completion work. It generated the missing row-level pre-trade signal matrix, universe membership snapshot, entry candidate diagnostics, post-trade fill linkage, manifest hashes, leakage/timing audit, matrix-rebuild diagnostics, and local probe prequalification board.

The result is still no local probe eligibility because direct market-cap membership evidence is unavailable in the accepted local cache.

## Accepted source state

| repo | branch | commit | tree | status |
| --- | --- | --- | --- | --- |
| A_Share_Monitor | `codex/r28-smallcap-evidence-completion-20260709` | `28cccf812045be6290da44291019f6fc58204fcf` | `bf51c510e56944973f05926c1c34e698683e5041` | `COMPLETED_RESEARCH_ONLY_EVIDENCE_INCOMPLETE_NO_PROBE_ELIGIBLE` |
| market_data | `codex/r28-smallcap-evidence-contract-20260709` | `cd0d6a0370bd78bcd7af0428a7f774bd66f07999` | `574f2bc498d32a5b01b8597d7ff3db397f6b99aa` | `ACCEPTED_RESEARCH_ONLY_CONTRACT_WITH_VALIDATION_PASS` |
| strategy_work | `main` | `6a109180009cc6c058ebc68b4120d651eab8e221` | `c6379f8f02ea4885419c8eade339a0aa47ef20b1` | `CODEX_ACCEPTANCE_SW_R28_FINAL_SYNC_RESEARCH_ONLY_EVIDENCE_INCOMPLETE_NO_PROBE_ELIGIBLE` |

## SmallCap row-level evidence status

`PASS_WITH_MARKET_CAP_PROXY_LIMITATION`

Generated evidence:

- `reports/runops/smallcap_r28_signal_matrix_20260709/pre_trade_signal_matrix.parquet`
- `reports/runops/smallcap_r28_signal_matrix_20260709/universe_membership_snapshot.parquet`
- `reports/runops/smallcap_r28_signal_matrix_20260709/entry_candidate_diagnostics.csv`
- `reports/runops/smallcap_r28_signal_matrix_20260709/post_trade_fill_linkage.csv`
- `reports/runops/smallcap_r28_signal_matrix_20260709/manifest.json`

Direct market-cap coverage in the accepted local cache is 0, so R28 preserved an amount/amount_ma20 proxy universe membership path and recorded the limitation.

## Leakage and timing audit

`PASS_WITH_MARKET_CAP_PROXY_LIMITATION`

- Signal fields were built from decision-date rows.
- Entry ranking uses `signal_score`.
- Forward-return ranking use is false.
- Split leakage detected is false.
- Test-result parameter selection is false.
- Direct market-cap membership remains missing.

## Robustness status

`MATRIX_REBUILD_DIAGNOSTIC_COMPLETE`

R28 rebuilt diagnostic metrics from the preserved row-level matrix. The rebuild is a matrix-level diagnostic, not a full production fill simulation.

## Local probe prequalification

`EVIDENCE_INCOMPLETE`

`local_research_probe_eligible_count=0`

`wide_research_probe_eligible_count=0`

`strategy_candidate_available=false`

## US30W preservation status

`CONTROLLER_SIDE_HASH_MIRROR_ONLY`

`us_stock_30w` still has no remote configured. R28 preserved a controller-side hash mirror only and did not treat US30W as remote-preserved evidence.

## Validation

- A_Share_Monitor R28 script `py_compile` PASS.
- A_Share_Monitor focused pytest PASS: 11 passed.
- A_Share_Monitor JSON parse PASS.
- A_Share_Monitor CSV/parquet read PASS.
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

`none` for R28 research-only closeout.

Carry-forward blocker:

- Direct market-cap membership snapshots are required before SmallCap local probe prequalification can be reconsidered.

## Next source action

Close R28 as research-only evidence-incomplete/no-probe-eligible. The next useful batch should materialize direct market-cap evidence or stop SmallCap probe reconsideration until such evidence exists.
