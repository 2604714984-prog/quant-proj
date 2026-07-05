# DATA_STRATEGY_BATCH_R8_20260705 GPT Pro External Audit Result

Captured: 2026-07-05
Conversation: fixed GPT Pro `外审对话`
Controller request: `reports/external_audit/data_strategy_batch_r8_gpt_pro_external_audit_request_20260705.md`
Controller request commit submitted: `0ce25be1c39fe8892592c6d3bfcc189e9fc5e7d6`
Controller request tree submitted: `0b662e5fb732404b7e48f294a633efca6b5f2934`
Closeout commit submitted: `ad9003561590792a8b62f4abf1decbf885c48cdc`
Closeout tree submitted: `89a1b92bfebb57a6c83e54815da122070d49c905`

## Verdict

```text
VERDICT: ACCEPT
EXTERNAL_AUDIT_TRIGGER_OPEN: no
FIXES_REQUIRED: none

NEXT_BATCH:
DATA_STRATEGY_BATCH_R9_20260705
```

## R9 Task Batch

1. target: `A_Share_Monitor`
   task: `A-R9 Single ROBUST Candidate Evidence Dossier`
   constraints:
   - focus only on the 1 ROBUST conservative candidate from R8
   - build a research-only dossier: factor profile, return windows, volatility, drawdown, liquidity, industry, one-lot cash, qfq/turnover completeness, stale-data checks
   - compare against the 1 RECENT_ONLY candidate and 4 BEAR_FRAGILE candidates
   - output KEEP_RESEARCH / WATCH_RESEARCH / DROP_RESEARCH only
   - no recommendation, no ticket, no buy/sell wording

2. target: `A_Share_Monitor`
   task: `A-R9 RECENT_ONLY Candidate Regime Validation`
   constraints:
   - inspect the 1 RECENT_ONLY candidate from R8
   - determine whether recent-only behavior is recoverable with a regime filter or should remain WATCH_RESEARCH
   - test against 2018-2021 / 2022-2023 / 2024-2026 windows
   - no promotion to ticket or recommendation

3. target: `A_Share_Monitor`
   task: `A-R9 Four BEAR_FRAGILE Candidate Drop/Rework Decision`
   constraints:
   - inspect the 4 BEAR_FRAGILE candidates
   - decide DROP_FOR_NOW / REWORK_LATER / KEEP_AS_STRESS_CASE
   - identify exact failure: bear-market drawdown, volatility spike, weak momentum persistence, liquidity, data quality
   - no recommendation, no ticket

4. target: `A_Share_Monitor`
   task: `A-R9 Conservative Momentum Parameter Narrowing`
   constraints:
   - use R8 evidence to narrow conservative momentum thresholds
   - reduce fragile candidates while preserving the single robust candidate if possible
   - report before/after candidate count and stability
   - research-only; no ticket eligibility claim

5. target: `US_Stock_Monitor`
   task: `US-R9 Strong Bucket Sector/Crosscheck Gap Overlay`
   constraints:
   - continue from R8 60 strong bucket
   - overlay sector availability, crosscheck status, metadata completeness, and price-history completeness
   - separate signal-strong candidates from data-blocked candidates
   - no recommendation, no ticket, no eligibility candidate

6. target: `US_Stock_Monitor`
   task: `US-R9 Tightened Filter 61-Candidate Review`
   constraints:
   - continue from R8 medium+weak reduction: 171 to 61
   - inspect the 61 survivors under tightened signal-only dry run
   - classify as STRONG_RESEARCH / MEDIUM_RESEARCH / DATA_BLOCKED / DROP_RESEARCH
   - explicitly document whether weakness was removed or merely hidden by stricter filters
   - no recommendation, no ticket

7. target: `US_Stock_Monitor`
   task: `US-R9 Sector Metadata Repair Dry-run`
   constraints:
   - design sector metadata repair for US-239 / US-300A only
   - produce schema and dry-run validation
   - no DB write, no network unless separate HG-EXEC is created
   - no product readiness claim

8. target: `US_Stock_Monitor`
   task: `US-R9 44-Symbol Metadata Bootstrap Fixture`
   constraints:
   - create or validate a dry-run fixture for the 44-symbol metadata gap
   - keep ETF / historical / merged-renamed / provider-metadata groups separate
   - identify active-equity exclusions
   - dry-run only unless separate HG-EXEC is created
   - no product route, no HITL readiness

9. target: `US_Stock_Monitor`
   task: `US-R9 Feedback Context Non-Authorization Test`
   constraints:
   - test that non-transactional feedback creates research context only
   - must not set actionable_feedback_for_ticket=true
   - must not create eligibility_candidate
   - must not emit ticket
   - forbidden fields: buy_now, sell_now, entry_price, target_weight, position_size, allocation, order, broker

10. target: `market_data`
    task: `MD-R9 Data-Route Boundary Regression`
    constraints:
    - verify A-share Level2 remains research-only
    - verify US-300A remains research-scan only
    - verify US-300B remains metadata-enrichment only
    - product_read_allowed=false
    - production_recommendation_data_ready=false
    - broker/live/auto=false

11. target: `strategy_work`
    task: `SW-R9 Research Memo Refresh`
    constraints:
    - update memos from R8/R9 state
    - A-share: 1 robust, 1 recent-only, 4 bear-fragile, low-vol archived
    - US: 60 strong, 61 tightened survivors, 44 metadata gap, sector/crosscheck blockers
    - research-only, not product gate
    - no recommendation language

## Boundary Notes

- R8 is accepted as ordinary research-only data/strategy work.
- R9 must remain ordinary research-only data/strategy work.
- No recommendation/advice authorized.
- No PENDING_HUMAN_REVIEW ticket authorized.
- No eligibility candidate authorized.
- No product route or production readiness authorized.
- No broker/order/paper/live/auto authorized.
- No ungated DB write, network ingest, schema migration, bulk ingest, readiness change, or registry activation authorized.
- Any future recommendation, ticket emission, product route activation, readiness promotion, broker/order/live action, or DB/network execution requires a separate gated task and review path.
- This preserves the bounded research-only pattern from prior accepted research batches.
