# Handoff: strategy_work R18 Final Sync

Target thread: `019f3881-5293-74a1-8535-814bd83c8681`
Target repo: `/home/rongyu/workspace/strategy_work`
Batch: `WINDOWS_WSL2_STRATEGY_HYPOTHESIS_EXPANSION_BATCH_R18_20260707`
Workstream: `SW-WIN-R18-3_FINAL_SYNC`

## Source Inputs Now Available

Use these accepted and source-preserved callbacks:

- `A_Share_Monitor`: commit `81fab19db69ddd6caba59d52711275a34cf5c542`, tree `df258bb4f185ef3137cc0eb1ee1bbd3093e0fc2e`, pushed to `origin/codex/harden-a-share-research-pipeline`.
- `market_data`: commit `449de8537881f1b4a1dadb46dc71dba570787351`, tree `d2da92a0b8714e47066e7b36ac36296e75aa0206`, pushed to `origin/main`.
- `strategy_work` memo/map: commit `63cdb09dcac71b4c8779d2740fe073c570d7ac93`, tree `37cc3e699e402043c209db0f25a3ce3aff3bf475`, pushed to `origin/main`.

## Task

Complete `SW-WIN-R18-3` final sync.

Required deliverable:

- `reports/planning/windows_wsl2_strategy_hypothesis_expansion_batch_r18_final_sync_20260707.md`

The final sync must preserve:

- `WIDE_RESEARCH_PROBE_ELIGIBLE_COUNT=0`.
- `STRATEGY_CANDIDATE_AVAILABLE=false`.
- A-share R18 emitted zero `R18_WIDE_RESEARCH_PROBE_ELIGIBLE` rows.
- Conditional wide3068 result `NO_R18_WIDE_RESEARCH_PROBE_ELIGIBLE`.
- No chunked wide probe and no full-frame wide3068.
- market_data product-route prep remains inactive and R18 does not depend on it.
- R16 labels remain `WEAK=5`, `UNSTABLE=8`, `POSITIVE=1`.
- East Money split remains `77 CROSSCHECK_PASS`, `121 CROSSCHECK_DATE_GAP`, `2870 CROSSCHECK_MISSING_EAST_MONEY`.

## Boundary

Research-only final sync. Do not create recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket, eligibility candidate, strategy candidate promotion, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto path, raw-data migration, network ingest, DB/cache write or rebuild, schema migration, registry activation, market_data activation, actionable ranking, or secret output.

## Required Callback

```text
CALLBACK_ENVELOPE:
BATCH: WINDOWS_WSL2_STRATEGY_HYPOTHESIS_EXPANSION_BATCH_R18_20260707
TARGET_REPO: /home/rongyu/workspace/strategy_work
WORKSTREAM: SW-WIN-R18-3_FINAL_SYNC
BRANCH:
COMMIT:
TREE:
STATUS:
TASKS_COMPLETED:
ARTIFACTS:
VALIDATION:
KEY_RESULTS:
WIDE_RESEARCH_PROBE_ELIGIBLE_COUNT:
STRATEGY_CANDIDATE_AVAILABLE:
BOUNDARY_RESULT:
EXTERNAL_AUDIT_TRIGGER_OPEN:
FIXES_REQUIRED:
NEXT_SOURCE_ACTION:
```
