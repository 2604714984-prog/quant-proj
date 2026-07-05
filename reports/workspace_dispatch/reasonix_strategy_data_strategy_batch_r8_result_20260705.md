# Reasonix-Strategy R8 Draft Result

Project: quant-proj
Batch: DATA_STRATEGY_BATCH_R8_20260705
Role: Reasonix-Strategy persistent sidecar
Session policy: persistent CLI-like session, keep open and reuse
Model policy: deepseek-v4-pro, effort high
Transcript note: the persistent strategy session appended this R8 result to `reports/workspace_dispatch/reasonix_strategy_data_strategy_batch_r7_20260705.jsonl`; this R8-specific summary is the controller index for the R8 result.

## Status

`REASONIX_DRAFT_READY`

Verdict: `PASS_DRAFT_ONLY`

This is an advisory research draft only. It does not authorize recommendation, ticket, eligibility candidate, product route, production readiness, broker/order/paper/live/auto, DB write, network ingest, schema migration, bulk ingest, readiness change, or registry activation.

## Scope Covered

| R8 task | Result |
|---|---|
| Task 1, A-share two KEEP_RESEARCH evidence pack | Drafted evidence-pack fields and label rules for KEEP/WATCH/DROP research classifications. |
| Task 2, four REWORK_RESEARCH threshold repair | Drafted one-dimension-at-a-time repair protocol and before/after criteria. |
| Task 3, conservative momentum mini-walkforward | Drafted 2018-2021, 2022-2023, and 2024-2026 regime partitions plus ROBUST/RECENT_ONLY/BEAR_FRAGILE/INSUFFICIENT labels. |
| Task 4, low-vol overlay decision | Recommended `ARCHIVE` because n=4 is insufficient, with revisit threshold at 20 records. |
| Task 5, US strong bucket multi-signal ranking | Drafted multi-signal vs single-filter split, five signal-family matrix, diversification ranking, and sector/correlation flags. |
| Task 6, US medium/weak bucket reduction | Drafted tighter medium-bucket filter experiment with weak bucket as control. |
| Task 9, US feedback fixture | Drafted forbidden/allowed field tests to keep feedback non-transactional. |
| Task 11, strategy_work memo sync | Drafted R8 research-state memo content and boundary wording. |

## Key Handoff Points

- Codex-Dev priority suggested by Reasonix-Strategy: run walkforward first, then evidence packs, then repair experiments, then archive, then US ranking/reduction, feedback fixture, and memo sync.
- The two KEEP_RESEARCH labels must be rechecked against the four REWORK candidates; a KEEP candidate can be downgraded if it underperforms the best rework on multiple metrics.
- REWORK candidates can only become `REPAIRED_IN_RESEARCH` in R8; any KEEP reconsideration belongs to a later batch after evidence is produced.
- Low-vol overlay should be archived from the primary research generator, with a revisit threshold of at least 20 same-cycle records.
- US strong-bucket work should check signal breadth, signal balance, sector concentration, pairwise correlation, and common-factor proxy risk.
- Feedback fixture must forbid transactional fields such as entry price, target weight, position size, broker/order fields, eligibility candidate, and actionable feedback for ticket.

## Risks Called Out

- Walkforward overfit due to only three partitions.
- Repair-experiment multiplicity across four candidates and multiple repair dimensions.
- Survivorship bias if universes are not point-in-time.
- Sector concentration confounding in US strong-bucket momentum signals.
- Medium-bucket tighter filters may introduce size or sector bias.
- Stale reference data can invalidate sector and metadata conclusions.
- In-sample leakage risk if threshold repair is validated on the same period that exposed the failure.

## Boundary Check

- Buy/sell advice: not present
- Recommendation ticket: not present
- `PENDING_HUMAN_REVIEW`: not emitted
- Eligibility candidate: not emitted
- Product-route activation: not present
- Production readiness: not present
- Broker/order/paper/live/auto: not present
- Ungated DB write/network/schema: not present
- Registry activation: not present

