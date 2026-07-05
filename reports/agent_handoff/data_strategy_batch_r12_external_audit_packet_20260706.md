# DATA_STRATEGY_BATCH_R12_20260705 External-Audit Packet

Project: quant-proj
Prepared: 2026-07-06
Role: Quant-Dispatcher
Packet type: GPT Pro external-audit / next-batch request

## Publication Repositories

Controller repo:

- `https://github.com/2604714984-prog/quant-proj`
- branch: `main`
- publication ref: use the pushed controller commit/tag that contains this packet

Source repos checked for current pushed state:

| Repository | Branch | Current pushed ref |
|---|---|---:|
| `A_Share_Monitor` | `codex/harden-a-share-research-pipeline` | `fdfcb2a53caac64986bdeb1f09babd52d19ee52d` |
| `strategy_work` | `main` | `4f68f9c75274fc339e2b81c708eddb2f72476339` |
| `US_Stock_Monitor` | `main` | `c808e05bc9a76aaa4ff59bf54c383460541d67da` |
| `market_data` | `main` | `ff24166479638b0f35e1cd7a8d0f1d01cdafb495` |

## Primary Controller Entry Points

- `reports/workspace_dispatch/data_strategy_batch_r12_20260705_closeout.md`
- `reports/workspace_dispatch/data_strategy_batch_r12_20260705_result_summary.md`
- `reports/workspace_dispatch/data_source_priority_strategy_clean_cache_rerun_20260705.md`
- `reports/workspace_dispatch/feature_store_build_rollback_20260705.md`
- `reports/workspace_dispatch/project_file_push_and_packet_prep_20260706.md`

## Review Request

Please review `DATA_STRATEGY_BATCH_R12_20260705` and the post-closeout source-repo cleanup records, then return:

1. `VERDICT`
2. `EXTERNAL_AUDIT_TRIGGER_OPEN`: yes/no
3. `FIXES_REQUIRED`
4. `NEXT_DATA_STRATEGY_BATCH`

## Scope

This is an ordinary research-only data/strategy closeout packet plus the user's requested housekeeping/push record.

The project objective is to find a research-valid A-share strategy candidate by improving:

- data quality;
- data-source evidence;
- safe feature construction;
- strategy experiments;
- candidate blocker reduction;
- wider-sample validation.

Do not turn this into controller/gate architecture review unless a true boundary trigger opened. The project should not loop on dispatcher/controller/process/gate architecture at this stage.

## Key Current Outcome

R12 closed as `CLOSED_ACCEPTED_WITH_WARNINGS`.

Important warnings:

- A-share still has no true post-freeze forward holdout.
- The `600177.SH` evidence remains baseline/in-snapshot only, not a true forward holdout.
- A-share temporal stress weakens the strict-v2 conclusion.
- Amount/size artifact risk remains.
- US metadata/provenance/crosscheck blockers persist; controlled complete rows, valid imports, and data-clear rows remain `0`.
- market_data keeps US-300A pending criteria and blocks baseline-only A-share rows from being treated as true forward holdout.
- strategy_work records that 50/100/200-symbol samples are not enough; the next practical path is wider 3068-symbol feature construction and rerun.

Post-closeout cleanup:

- `A_Share_Monitor` restored `FeatureStore.build()` compatibility after the strict memory guard broke ordinary research calls.
- Explicit chunked construction remains available through `build_to_store()`.
- `A_Share_Monitor` now keeps survivor-bias and cost-stress gates strict by default, while allowing research-only configs to explicitly disable those two gate reasons.
- `strategy_work`, `US_Stock_Monitor`, `A_Share_Monitor`, and `market_data` current refs have been pushed or verified up to date.

## Practical Next Issue

The next useful task should focus on this:

```text
Build features_daily safely for the cleaned 3068-symbol A-share data/cache without using a full in-memory FeatureStore.build() over the entire cache, then rerun low_vol_quality on the wider cross-section.
```

Expected next-batch shape:

- inspect `data/cache` table coverage and whether `features_daily` already exists;
- run or fix `python -m qta features build_to_store` for `data/cache`;
- verify `features_daily` coverage and key fields;
- update `strategy_work/configs/bare_minimum.yaml` to use the 3068-symbol cache and research-only gate settings;
- rerun `bare_minimum`;
- if test Sharpe is positive, rerun `lowvol_quality_focused`;
- archive leaderboard/candidate registry into `strategy_work`;
- report blockers without emitting recommendation or ticket.

## Boundary

No recommendation, buy/sell advice, ticket, `PENDING_HUMAN_REVIEW`, eligibility candidate, data-clear promotion, product route, production readiness, broker/order/paper/live/auto, raw-data migration, or secret handling is authorized.

DB writes, network ingest, schema changes, bulk ingest, readiness changes, and registry activation remain gated by task-level HG-EXEC evidence and transcript.

Reasonix/DeepSeek outputs remain draft/advisory until Codex-Dev implements and validates them.

## Ready-To-Send Prompt

```text
Project: quant-proj
Controller repo: https://github.com/2604714984-prog/quant-proj
Controller branch: main
Packet entry: reports/agent_handoff/data_strategy_batch_r12_external_audit_packet_20260706.md

Please review DATA_STRATEGY_BATCH_R12_20260705 and the post-closeout project file organization/push record.

Return:
1. VERDICT
2. EXTERNAL_AUDIT_TRIGGER_OPEN yes/no
3. FIXES_REQUIRED
4. NEXT_DATA_STRATEGY_BATCH

Primary controller files:
- reports/workspace_dispatch/data_strategy_batch_r12_20260705_closeout.md
- reports/workspace_dispatch/data_strategy_batch_r12_20260705_result_summary.md
- reports/workspace_dispatch/data_source_priority_strategy_clean_cache_rerun_20260705.md
- reports/workspace_dispatch/feature_store_build_rollback_20260705.md
- reports/workspace_dispatch/project_file_push_and_packet_prep_20260706.md

Current pushed source refs:
- A_Share_Monitor codex/harden-a-share-research-pipeline: fdfcb2a53caac64986bdeb1f09babd52d19ee52d
- strategy_work main: 4f68f9c75274fc339e2b81c708eddb2f72476339
- US_Stock_Monitor main: c808e05bc9a76aaa4ff59bf54c383460541d67da
- market_data main: ff24166479638b0f35e1cd7a8d0f1d01cdafb495

Scope:
ordinary research-only data/strategy batch plus user-requested project file organization/push. Do not turn this into controller/gate architecture review unless a true boundary trigger opened.

Key current outcome:
R12 is accepted with warnings. A-share still lacks true post-freeze holdout; US remains blocked by metadata/provenance/crosscheck/second-source evidence; market_data keeps product/data-clear gates closed; strategy_work indicates wider-sample validation is now the practical path. FeatureStore.build compatibility was restored, while build_to_store remains the safe large-cache path. Survivor-bias and cost-stress gate reasons remain strict by default but can be explicitly disabled for research-only experiments.

Current practical next issue:
Build features_daily safely for the cleaned 3068-symbol A-share data/cache without full-cache in-memory FeatureStore.build(), then rerun low_vol_quality on the wider cross-section.

Boundary:
No recommendation, ticket/PENDING_HUMAN_REVIEW, eligibility candidate, data-clear promotion, product route, production readiness, broker/order/paper/live/auto, raw-data migration, or secret handling is authorized.
```
