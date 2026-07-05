# DATA_STRATEGY_BATCH_R7_20260705 Intake

Date: 2026-07-05
Dispatcher: Quant-Dispatcher
Source: fixed GPT Pro external-audit conversation `外审对话`
Source result: `reports/agent_handoff/data_strategy_batch_r6_gpt_pro_external_audit_result_20260705.md`
Prior closeout: `reports/workspace_dispatch/data_strategy_batch_r6_20260705_closeout.md`
Classification: ordinary research-only data/strategy batch

## Batch Verdict

- GPT Pro verdict: `ACCEPT`
- External-audit trigger open: `no`
- Required fixes: `none`
- Normalized next batch id: `DATA_STRATEGY_BATCH_R7_20260705`

## Tasks

### 1. A-R7 Two Keep Candidates Deep Validation

Target: `A_Share_Monitor`

Constraints:

- Continue from R6: conservative six became `2 KEEP_RESEARCH` / `4 REWORK_RESEARCH`.
- Inspect only the `2 KEEP_RESEARCH` candidates.
- Analyze factor strength, return stability, drawdown, liquidity, industry exposure, one-lot affordability, qfq/turnover completeness.
- Compare against the `4 REWORK_RESEARCH` candidates.
- Output keep / watch / drop as research labels only.
- No recommendation, no ticket, no buy/sell wording.

### 2. A-R7 Four Rework Candidates Repair Experiment

Target: `A_Share_Monitor`

Constraints:

- Inspect the `4 REWORK_RESEARCH` conservative candidates.
- Test which condition caused rework: volatility, drawdown, weak momentum persistence, liquidity, data gap, regime fragility.
- Propose modified thresholds for research experiment only.
- Do not promote to `KEEP` unless validation metrics improve.
- No recommendation, no ticket.

### 3. A-R7 Low-vol Overlay Decision Closeout

Target: `A_Share_Monitor`

Constraints:

- Continue from R6: low-vol overlay narrowed to `4` but remains too small/weak.
- Decide whether low-vol should be dropped, kept as risk filter only, or reworked later.
- Compare low-vol overlay against conservative momentum keep/rework set.
- Output decision: `DROP_FOR_NOW` / `RISK_FILTER_ONLY` / `REWORK_LATER`.
- No recommendation, no ticket.

### 4. A-R7 Candidate Dataset Consistency Check

Target: `A_Share_Monitor`

Constraints:

- Verify A11 candidate dataset, factor table, and R6 labels are internally consistent.
- Confirm no stale 83-candidate baseline is being treated as current.
- Confirm current research universe remains Level2 1000-symbol research input.
- Output data consistency report only.
- No product route activation.

### 5. US-R7 Strong Bucket Deep Dive

Target: `US_Stock_Monitor`

Constraints:

- Continue from R6 buckets: `60 strong` / `80 medium` / `91 weak` / `8 data-limited`.
- Inspect the `60 strong` research bucket only.
- Analyze overlap across momentum/liquidity, low-vol, drawdown-controlled, SPY/QQQ relative strength, quality proxy.
- Separate multi-signal names from single-filter pass names.
- Flag sector/crosscheck limitations.
- No recommendation, no ticket, no eligibility candidate.

### 6. US-R7 Medium/Weak Bucket Pruning Rules

Target: `US_Stock_Monitor`

Constraints:

- Derive pruning rules from the `80 medium` and `91 weak` buckets.
- Identify filters that are too loose.
- Reduce false positives before any future scan.
- Output revised research-only filter thresholds.
- No recommendation, no ticket.

### 7. US-R7 Data-limited Bucket Repair Map

Target: `US_Stock_Monitor`

Constraints:

- Inspect the `8 data-limited` candidates.
- Identify exact missing fields: metadata, sector, adjusted price, crosscheck, liquidity, history length.
- Map each missing field to a data-repair task.
- No DB write, no network unless separate `HG-EXEC` is created.

### 8. US-R7 44-symbol Metadata Gap Execution Design

Target: `US_Stock_Monitor`

Constraints:

- Continue from R6: 44-symbol metadata gap remains separate.
- Produce exact bootstrap input schema for ETF / historical / merged-renamed / provider-metadata groups.
- Define which symbols should be excluded from active-equity scan.
- Dry-run only unless separate `HG-EXEC` is created.
- No product readiness claim.

### 9. US-R7 Feedback Context Repair Plan

Target: `US_Stock_Monitor`

Constraints:

- Focus on no actionable feedback blocker.
- Test whether non-transactional feedback can generate durable research feedback context.
- Must not create `eligibility_candidate`.
- Must not emit ticket.
- Forbidden fields: `buy_now`, `sell_now`, `entry_price`, `target_weight`, `position_size`, `order`, `broker`.

### 10. MD-R7 Research Route Consistency Regression

Target: `market_data`

Constraints:

- Verify A-share Level2 research route remains research-only.
- Verify US-300A / US-300B remain research/enrichment only.
- `product_read_allowed=false`.
- `candidate_product_read_allowed=false` unless separately gated.
- `production_recommendation_data_ready=false`.
- `broker/live/auto=false`.

### 11. SW-R7 Research Memo Update

Target: `strategy_work`

Constraints:

- Update memos from R6/R7 state.
- A-share: `2 KEEP_RESEARCH` / `4 REWORK_RESEARCH` / low-vol overlay weak.
- US: `60 strong` / `80 medium` / `91 weak` / `8 data-limited` / 44 metadata gap separate.
- Research-only, not product gate.
- No recommendation language.

## Boundary Rules

- No recommendation/advice.
- No ticket or `PENDING_HUMAN_REVIEW`.
- No eligibility candidate.
- No product-route activation or production readiness.
- No broker/order/paper/live/auto.
- No ungated DB write, network ingest, schema migration, bulk ingest, readiness change, or registry activation.

