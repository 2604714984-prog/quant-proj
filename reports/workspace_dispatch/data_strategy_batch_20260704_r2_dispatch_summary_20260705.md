# DATA_STRATEGY_BATCH_20260704_R2 Dispatch Summary

Quant-Dispatcher imported this batch on 2026-07-05.

This is an ordinary source-project Data + Strategy batch. No controller external-audit packet, ChatGPT external-audit packet, ticket task, product-route activation task, recommendation task, broker/order/paper/live/auto task, or production readiness task was created.

## Current Facts

- A-share A11 is aligned to `a_expand_20260704_l1_local1000_0317`.
- Current A11 run is `a11_research_20260704_154831`.
- Current A11 scope is `1000` factor rows, `203` research-only candidates, and `152` unique symbols.
- The old `83` A11 candidates are retained as baseline only.
- US still has `44` missing metadata symbols with local metadata/bar rows at `0`.
- US 300 remains blocked by missing metadata.
- US eligibility remains blocked by `NO_ACTIONABLE_FEEDBACK` / `EVIDENCE_GAP_PERSISTING`.
- market_data keeps A-share Level2 as research route only, with `candidate_product_read_allowed=false`.

## Global Boundaries

- `research_only=true` and `not_a_recommendation=true` are required for all strategy outputs.
- No `PENDING_HUMAN_REVIEW` ticket may be emitted in this batch.
- No BUY/SELL/HOLD advice, target price, target weight, position-size instruction, allocation, ticket payload, broker path, order path, paper-trading path, live-trading path, or auto-execution path is in scope.
- DB writes and network ingest are allowed only when the downstream source agent creates a task-level `HG-EXEC-TASK-*` record first and captures transcript, manifest, provider, symbol/date bounds, and explicit `--allow-write` / `--allow-network` evidence.
- registry/readiness work may update research/status evidence only; it must not activate product route or set production recommendation readiness.

## Dispatch Assignments

| Workstream | Agent | Agent ID | Scope | Commit/Push |
|---|---|---|---|---|
| A-share P0 data + strategy | Arendt | `019f2de6-2943-7772-b517-1f3105b5fa53` | `TASK-A-DATA-201/202/203`, `TASK-A-STRAT-201/202/203/204` in `/Users/rongyuxu/Desktop/A_Share_Monitor` | Agent may commit/push A-share repo after validation |
| US P0 data + strategy | Epicurus | `019f2de6-8908-7eb0-ab5d-6892b0a2225c` | `TASK-US-DATA-201/202/203`, `TASK-US-STRAT-201/202/203` in `/Users/rongyuxu/Desktop/US_Stock_Monitor` | Agent may commit/push US repo after validation |
| market_data + strategy_work P1 | Banach | `019f2de6-bef7-7f90-b73a-9edb77f0ff36` | `TASK-MD-201/202`, `TASK-SW-201` in `/Users/rongyuxu/Desktop/market_data` and `/Users/rongyuxu/Desktop/strategy_work` if present | Agent may commit/push changed repo(s) after validation |

## Dependency Handling

- `TASK-US-DATA-202` depends on `TASK-US-DATA-201`.
- `TASK-US-STRAT-203` depends on `TASK-US-DATA-202`, or must be plan-only if US 300 remains blocked.
- `TASK-MD-202` may use the latest available US repair status but must keep product-read false unless fully qualified in a future authorized task.
- A-share strategy tasks may run from the existing A11 Level2 run and should not wait for product-route activation.

## Expected Deliverables

### A-share

- `reports/codex_dev/task_a_data_201_a11_factor_table_lock.md`
- `reports/codex_dev/task_a_data_201_a11_factor_table_lock.json`
- `reports/codex_dev/task_a_data_202_level2_remaining_data_gap.md`
- `reports/codex_dev/task_a_data_202_level2_remaining_data_gap.json`
- `reports/codex_dev/task_a_data_203_a11_research_route_alignment.md`
- `reports/codex_dev/task_a_data_203_a11_research_route_alignment.json`
- `reports/codex_dev/task_a_strat_201_candidate_quality_breakdown.md`
- `reports/codex_dev/task_a_strat_201_candidate_quality_breakdown.json`
- `reports/codex_dev/task_a_strat_202_a11_experiment_comparison.md`
- `reports/codex_dev/task_a_strat_202_a11_experiment_comparison.json`
- `reports/codex_dev/task_a_strat_203_micro_account_simulation.md`
- `reports/codex_dev/task_a_strat_203_micro_account_simulation.json`
- `reports/codex_dev/task_a_strat_204_walk_forward_robustness.md`
- `reports/codex_dev/task_a_strat_204_walk_forward_robustness.json`

### US

- `reports/codex_dev/task_us_data_201_44_metadata_repair.md`
- `reports/codex_dev/task_us_data_201_44_metadata_repair.json`
- command transcript and manifest/hash summary for any write/network operation
- `reports/codex_dev/task_us_data_202_us300_expansion_rerun.md`
- `reports/codex_dev/task_us_data_202_us300_expansion_rerun.json`
- `reports/codex_dev/task_us_data_203_second_source_crosscheck_sample.md`
- `reports/codex_dev/task_us_data_203_second_source_crosscheck_sample.json`
- `reports/codex_dev/task_us_strat_201_no_eligibility_root_cause.md`
- `reports/codex_dev/task_us_strat_201_no_eligibility_root_cause.json`
- `reports/codex_dev/task_us_strat_202_qualitative_feedback_bootstrap.md`
- `reports/codex_dev/task_us_strat_202_qualitative_feedback_bootstrap.json`
- `reports/codex_dev/task_us_strat_203_us300_strategy_scan.md`
- `reports/codex_dev/task_us_strat_203_us300_strategy_scan.json`

### market_data / strategy_work

- `reports/codex_dev/task_md_201_a_share_level2_research_route_adapter.md`
- tests for the route semantics if code changes are made
- `reports/codex_dev/task_md_202_us300_registry_status.md`
- `reports/planning/NEXT_RESEARCH_TASKS_AFTER_A11_1000_US300.md`
- `reports/a_share/a11_203_candidate_research_summary.md`
- `reports/us_stock/us300_metadata_and_strategy_blockers.md`

## Dispatcher Acceptance Criteria

- Each agent final result must list changed files, validation, commit hash, and push status.
- Any DB write/network operation must have an `HG-EXEC-TASK-*` record and transcript before it is accepted.
- If a dependency remains blocked, the dependent report must say `BLOCKED_BY_DEPENDENCY` or `PLAN_ONLY`, not invent readiness.
- The batch closeout should answer:
  - A-share: whether a meaningful subset of the `203` research candidates deserves deeper research.
  - US: whether the `44` metadata blocker can be repaired and whether US 300 can proceed to strategy scanning.

## Status

- Dispatch status: `PARTIAL_COMPLETE_US_P0_BLOCKED`
- External audit packet: `NOT_CREATED`
- Controller audit packet: `NOT_CREATED`
- Ticket/product-route tasks: `NOT_CREATED`
- Closeout: `reports/workspace_dispatch/data_strategy_batch_20260704_r2_closeout_20260705.md`

## Priority Amendment 2026-07-05

The latest GitHub/current-file review keeps the batch inside the same Data + Strategy scope but sharpens execution priorities:

- A-share should prioritize robustness and candidate quality, not more gate/controller work.
- A-share `conservative_momentum_liquidity_affordability` is the first strategy to deep-dive because it has a small candidate set and positive median 20d/60d/120d returns in the latest review context.
- A-share low-vol strategy variants should not be prioritized merely because they produce more candidates; they need robustness and regime-dependency checks.
- A-share data-gap reporting must explicitly cover qfq_close missing `11`, turnover missing `4`, and whether suspension event history with only `3` rows affects strategy research.
- US should not let the `44` missing metadata symbols block all strategy research. Create a dual track:
  - `US-300A` / `US-239 metadata-valid research universe`: research-only strategy scan may proceed if local data supports it.
  - `US-300B`: pending metadata enrichment for the `44` missing symbols, split into active equity, ETF, delisted/historical, and unsupported/remove-from-current-universe.
- market_data should sync A-share research-route metadata wording to `Level2 accepted for research` while keeping product route disabled.
- market_data should express US-300A / US-300B as non-product research/status routes.
- strategy_work should synchronize current state away from old `265` A-share / `63` US descriptions toward A-share `1000 Level2 / 203 candidates / 152 unique` and US `239 valid + 44 metadata gap`.

Additional instructions were sent to all three downstream agents:

| Workstream | Agent ID | Amendment |
|---|---|---|
| A-share P0 | `019f2de6-2943-7772-b517-1f3105b5fa53` | Focus walk-forward robustness, 16 conservative-momentum deep dive, small data-gap impact, and deduped 1/2/3-symbol research pool feasibility. |
| US P0 | `019f2de6-8908-7eb0-ab5d-6892b0a2225c` | Add US-239/US-300A research-only scan path and split the 44 metadata gaps by active equity / ETF / delisted-historical / unsupported. |
| market_data + strategy_work | `019f2de6-bef7-7f90-b73a-9edb77f0ff36` | Follow up on Level2 accepted-for-research wording, US-300A/US-300B status expression, and strategy_work current-state sync. |

Reasonix sidecar status is tracked in `reports/workspace_dispatch/reasonix_data_strategy_batch_r2_sidecar_summary_20260705.md`.

The amendment does not authorize recommendations, tickets, product route activation, production readiness, broker/order/paper/live/auto, or controller/ChatGPT external-audit packets.
