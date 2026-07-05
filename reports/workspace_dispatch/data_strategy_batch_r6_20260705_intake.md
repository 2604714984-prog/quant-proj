# DATA_STRATEGY_BATCH_R6_20260705 Intake

Date: 2026-07-05
Source: GPT Pro external audit result for `DATA_STRATEGY_BATCH_R5_20260705`
Result file: `reports/agent_handoff/data_strategy_batch_r5_gpt_pro_external_audit_result_20260705.md`
Goal anchor: `reports/workspace_dispatch/continuous_closed_loop_goal_20260705.md`

## Dispatcher Classification

R6 is an ordinary research-only Data + Strategy batch.

Do not create:

- controller external-audit packet
- Codex-Audit task
- ticket task
- product-route activation task
- production-readiness task
- broker/order/paper/live/auto task

Allowed outputs:

- `DATA_REPORT`
- `STRATEGY_REPORT`
- `CODEX_ACCEPTANCE`
- `REASONIX_DRAFT`

Forbidden outputs:

- recommendation or investment advice
- ticket or `PENDING_HUMAN_REVIEW`
- product-route activation
- production readiness
- broker/order/paper/live/auto
- DB write, network ingest, schema migration, bulk ingest, readiness change, or registry activation without a separate task-level `HG-EXEC-*` record and transcript

## Dispatch Queue

### A_Share_Monitor

#### `TASK-A-R6-001` Conservative Momentum Robustness Deep Dive

Objective:

- Focus only on `conservative_momentum_liquidity_affordability`.
- Analyze the 6 kept candidates from R5.
- Compare 20d, 60d, 120d, and 252d returns.
- Compare volatility, drawdown, liquidity, and industry concentration.
- Produce `keep`, `rework`, or `drop` research decisions.

Constraints:

- No recommendation.
- No ticket.
- No buy/sell wording.
- Research metrics only.

#### `TASK-A-R6-002` Low-vol Rebuild Experiment

Objective:

- Test low-vol as a risk filter, not a candidate generator.
- Add a momentum floor or relative-strength filter.
- Compare against the R5 baseline.
- Output research metrics only.

Constraints:

- No ticket.
- No advice.
- No product-readiness claim.

### US_Stock_Monitor

#### `TASK-US-R6-001` US-239 Candidate Quality Breakdown

Objective:

- Analyze overlap among momentum/liquidity, low-vol, drawdown-controlled, SPY/QQQ relative strength, and quality proxy signals.
- Classify candidates into strong, medium, weak, and data-limited buckets.
- Explicitly flag sector-metadata and crosscheck limitations.

Constraints:

- No recommendation.
- No ticket.
- No eligibility candidate.

#### `TASK-US-R6-002` Metadata Enrichment Implementation Plan

Objective:

- Use the R5 44-symbol queue split.
- Design CSV/JSON metadata bootstrap for ETF, historical, merged, and provider-metadata groups.
- Provide dry-run implementation plan.

Constraints:

- Dry-run only unless a separate `HG-EXEC-*` is created.
- No network by default.
- No DB write by default.

#### `TASK-US-R6-003` Feedback Bootstrap Usability Test

Objective:

- Verify non-transactional feedback can create durable research feedback context.
- Ensure feedback remains research-only.

Constraints:

- Must not set recommendation authorization.
- Must not emit `eligibility_candidate`.
- Must not emit ticket.
- Forbidden fields: `buy_now`, `sell_now`, `entry_price`, `target_weight`, `position_size`, `order`, `broker`.

### market_data

#### `TASK-MD-R6-001` Research Route Consistency Regression

Objective:

- Verify A-share research route remains `PASS_LEVEL_2_FOR_RESEARCH` with `product_read_allowed=false`.
- Verify US-300A and US-300B remain research/enrichment only.
- Verify `production_recommendation_data_ready=false`.
- Verify `broker/live/auto=false`.

Constraints:

- Do not activate product route.
- Do not change readiness.

### strategy_work

#### `TASK-SW-R6-001` Research Memo Sync

Objective:

- Update research memos from R5 outputs.
- A-share: conservative momentum and low-vol decision.
- US: US-239 quality and 44-symbol enrichment queue.

Constraints:

- Research-only.
- Not product gate.
- No recommendation or ticket wording.

### Reasonix-DB

Advisory sidecar scope:

- `TASK-US-R6-002`
- `TASK-MD-R6-001`

Mode:

- `deepseek-v4-pro`
- effort `high`
- draft/advisory only
- no DB write, no network, no readiness promotion

### Reasonix-Strategy

Advisory sidecar scope:

- `TASK-A-R6-001`
- `TASK-A-R6-002`
- `TASK-US-R6-001`
- `TASK-US-R6-003`
- `TASK-SW-R6-001`

Mode:

- `deepseek-v4-pro`
- effort `high`
- research-only
- no advice, no ticket, no product promotion

## Next Dispatcher Action

Create downstream dispatch prompts for the listed R6 source-project tasks, preserving the boundaries above. Record sends in `reports/workspace_dispatch/data_strategy_batch_r6_20260705_dispatch_summary.md`.
