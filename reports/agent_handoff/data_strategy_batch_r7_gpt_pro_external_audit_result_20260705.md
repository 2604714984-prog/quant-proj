# DATA_STRATEGY_BATCH_R7_20260705 GPT Pro External Audit Result

Captured: 2026-07-05
Conversation: fixed GPT Pro `外审对话`
Controller request: `reports/external_audit/data_strategy_batch_r7_gpt_pro_external_audit_request_20260705.md`
Controller commit submitted: `1fae88255ab214e529591a563c4f225bd2d89b52`
Controller tree submitted: `d43dc9b0cca7cd013f4a8fa18bd0958999115e54`

## Verdict

```text
VERDICT: ACCEPT
EXTERNAL_AUDIT_TRIGGER_OPEN: no
FIXES_REQUIRED:
- none
NEXT_TASK_BATCH: DATA_STRATEGY_BATCH_R8_20260705
```

## R8 Task Batch

1. target: `A_Share_Monitor`
   task: `A-R8 Two KEEP_RESEARCH Candidate Evidence Pack`
   constraints:
   - build a compact evidence pack for the 2 KEEP_RESEARCH conservative candidates
   - include factor values, return windows, volatility, drawdown, liquidity, industry, one-lot affordability, data completeness
   - compare each against the 4 REWORK_RESEARCH candidates
   - output research-only keep/watch/drop labels
   - no recommendation, no ticket, no buy/sell wording

2. target: `A_Share_Monitor`
   task: `A-R8 Four REWORK_RESEARCH Candidate Threshold Repair`
   constraints:
   - test modified thresholds only for the 4 REWORK_RESEARCH conservative candidates
   - isolate whether repair comes from momentum persistence, drawdown cap, volatility cap, liquidity floor, or data repair
   - produce before/after research metrics
   - do not promote to ticket eligibility
   - no recommendation, no ticket

3. target: `A_Share_Monitor`
   task: `A-R8 Conservative Momentum Mini-Walkforward`
   constraints:
   - run mini walk-forward only for the 2 keep + 4 rework set
   - test period stability across 2018-2021, 2022-2023, 2024-2026
   - mark candidates as robust / recent-only / bear-fragile / insufficient
   - no recommendation, no ticket

4. target: `A_Share_Monitor`
   task: `A-R8 Low-vol Overlay Archive Decision`
   constraints:
   - continue from R7: overlay narrowed to 4 but remains too small/weak
   - decide archive / keep as risk-filter-only / rework later
   - if archived, preserve rationale and stop running it as primary candidate generator
   - no recommendation, no ticket

5. target: `US_Stock_Monitor`
   task: `US-R8 Strong Bucket Multi-Signal Ranking Research`
   constraints:
   - continue from R7: 60 strong bucket
   - split strong bucket into multi-signal vs single-filter pass
   - prioritize names with overlap across momentum/liquidity, drawdown, relative strength, quality proxy
   - explicitly flag missing sector and crosscheck limitations
   - no recommendation, no ticket, no eligibility candidate

6. target: `US_Stock_Monitor`
   task: `US-R8 Medium/Weak Bucket Reduction Experiment`
   constraints:
   - use the 80 medium and 91 weak buckets to tighten filters
   - propose revised thresholds that reduce weak false positives
   - report candidate count before/after
   - preserve all outputs as research-only
   - no recommendation, no ticket

7. target: `US_Stock_Monitor`
   task: `US-R8 Data-Limited Eight Repair Checklist`
   constraints:
   - inspect the 8 data-limited candidates
   - produce exact missing-field checklist per symbol
   - map each missing field to metadata / sector / crosscheck / price-history / feedback tasks
   - no DB write or network unless separate HG-EXEC is created

8. target: `US_Stock_Monitor`
   task: `US-R8 44-Symbol Metadata Bootstrap Dry-Run Spec`
   constraints:
   - continue from R7 metadata execution design
   - produce final dry-run CSV/JSON schema for ETF / historical / merged-renamed / provider-metadata groups
   - identify active-equity exclusions clearly
   - dry-run only unless separate HG-EXEC is created
   - no product-readiness claim

9. target: `US_Stock_Monitor`
   task: `US-R8 Feedback Context Test Fixture`
   constraints:
   - create test fixture for non-transactional feedback context only
   - verify durable research feedback context can be created
   - must not set actionable_feedback_for_ticket=true
   - must not create eligibility_candidate
   - forbidden fields: buy_now, sell_now, entry_price, target_weight, position_size, order, broker

10. target: `market_data`
    task: `MD-R8 Research Route Drift Check`
    constraints:
    - verify A-share Level2 remains research-only
    - verify US-300A/US-300B remain research/enrichment only
    - check no drift toward product_read_allowed=true
    - production_recommendation_data_ready=false
    - broker/live/auto=false

11. target: `strategy_work`
    task: `SW-R8 Research State Sync`
    constraints:
    - update memos from R7/R8 state
    - A-share: 2 keep / 4 rework / low-vol weak/archive decision
    - US: 60 strong / 80 medium / 91 weak / 8 data-limited / 44 metadata gap
    - research-only, not product gate
    - no recommendation language

## Boundary Notes

- R7 is accepted as ordinary research-only data/strategy work.
- R8 remains ordinary research-only data/strategy work.
- No recommendation/advice authorized.
- No PENDING_HUMAN_REVIEW ticket authorized.
- No eligibility candidate authorized.
- No product route or production readiness authorized.
- No broker/order/paper/live/auto authorized.
- No ungated DB write, network ingest, schema migration, bulk ingest, readiness change, or registry activation authorized.
- Any future recommendation, ticket emission, product route activation, readiness promotion, broker/order/live action, or DB/network execution requires a separate gated task and review path.
