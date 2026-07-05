# DATA_STRATEGY_BATCH_R11_20260705 GPT Pro External Review Submission

Prepared: 2026-07-05
Prepared by: Quant-Dispatcher
Purpose: closed-loop verdict and next task intake
Conversation: fresh GPT Pro `New Audit Handoff`

## Request To GPT Pro

You are the external process/research reviewer for `quant-proj`.

Project final objective: build and maintain a staged quant research system that improves data quality, strategy experiments, and candidate quality until the research evidence is strong enough for later human-reviewed stages. Do not turn this review into another controller/gate architecture loop. The controller/gate process is already accepted. Focus on what the next data and strategy development tasks should be.

Review scope:

- Batch: `DATA_STRATEGY_BATCH_R11_20260705`
- Controller repo: `https://github.com/2604714984-prog/quant-proj`
- Controller commit: `3bad8aa94535608a6000b8229068687131f36300`
- Controller tree: `b4b67df9499647870200fcb3126fb16127da3890`
- Closeout: `reports/workspace_dispatch/data_strategy_batch_r11_20260705_closeout.md`
- Result summary: `reports/workspace_dispatch/data_strategy_batch_r11_20260705_result_summary.md`
- Intake: `reports/workspace_dispatch/data_strategy_batch_r11_20260705_intake.md`
- Dispatch summary: `reports/workspace_dispatch/data_strategy_batch_r11_20260705_dispatch_summary.md`
- Reasonix sidecar summary: `reports/workspace_dispatch/reasonix_data_strategy_batch_r11_sidecar_summary_20260705.md`

Source anchors:

- `A_Share_Monitor`: `codex/harden-a-share-research-pipeline`, commit `05b79ddabb05003067e1ae86e10411604271ff26`, tree `05a99d23041fc09d54796501a35789fdf0caa182`
- `US_Stock_Monitor`: `codex/duckdb-provider`, commit `c9dce3782df1e250987129c7ce5350c786e1821d`, tree `ed1bd5c17cfd804ee06fabb509fa42c72e148392`
- `market_data`: `codex/data-strategy-r10-market-data-data-clear`, commit `96a325423d00af02c8829d85d770b7d73e30c6f6`, tree `287fe38fc93d3e0852951638205c99a734e81d0e`
- `strategy_work`: `main`, commit `ad33605ec3ae001bc7c17b132f7333f76f60ae74`, tree `b84fd7ea66c0a6c771ea021eeabe68111888f11b`

R11 results:

- A-share: no valid post-freeze A11 forward holdout data is locally available. `strict_v2` retains only `2` records / `1` symbol (`600177.SH`); balanced variants retain `3` records / `2` symbols and `7` records / `4` symbols. Peer-control stress says risk-control distinctiveness survives, but amount-scale artifact risk remains. Ticket candidate records remain `0`; `ticket_emitted=false`.
- US: metadata blocker matrix has `165` rows across `60` signal-strong, `61` tightened survivors, and `44` metadata-queue records. Current blocked counts remain `121` signal-review records and `44` metadata-queue records. Validator is `IMPORT_BLOCKED_DRY_RUN_ONLY`. Offline crosscheck harness is synthetic-only with research evidence count `0` and data-clear row count `0`. Tighter filters do not improve evidence readiness.
- market_data: US-300A remains `DATA_CLEAR_RESEARCH_PENDING_CRITERIA`, not `DATA_CLEAR_RESEARCH`. `DATA_CLEAR_RESEARCH` requires all seven criteria plus clean evidence statuses. A-share inventory found four canonical snapshots; only `a_expand_20260704_l1_local1000_0317` contains `600177.SH`, with `1000` symbols, `2,059,000` rows, date range `20180102..20260701`, and `2,059` holdout rows in the inventory view.
- strategy_work: final R11 memo sync completed after source acceptances and did not promote source configs/routes.
- Reasonix sidecars: advisory drafts only, not final authority.

Boundary state:

- R11 is ordinary research-only/data-strategy work.
- No recommendation/advice.
- No `PENDING_HUMAN_REVIEW`.
- No ticket.
- No eligibility candidate.
- No product-route activation.
- No production readiness.
- No broker/order/paper/live/auto.
- No DB write/network/schema/bulk/readiness/registry change from controller.
- No raw-data migration or secret handling.

Please return:

1. Verdict on R11 closeout: `ACCEPT`, `ACCEPT_WITH_FIXES`, or `REJECT`.
2. Whether an external-audit trigger opened: yes/no, with reason.
3. Required fixes before the next batch, if any.
4. The next concrete task batch named exactly `DATA_STRATEGY_BATCH_R12_20260705`.

Important direction for R12:

- Stay focused on data quality, strategy experiments, and candidate quality.
- Do not ask for another controller/gate architecture review unless a real boundary change opens.
- Prefer tasks that directly address the current blockers:
  - A-share lack of post-freeze/forward holdout evidence and single-symbol over-narrowness.
  - A-share amount-scale artifact risk and peer-control robustness.
  - US sector/asset/provenance/crosscheck metadata blockers.
  - US synthetic-only crosscheck being zero research evidence.
  - market_data US-300A data-clear criteria and A-share snapshot coverage evidence.
- Keep all work research-only unless a separate explicit boundary-trigger task is created.
