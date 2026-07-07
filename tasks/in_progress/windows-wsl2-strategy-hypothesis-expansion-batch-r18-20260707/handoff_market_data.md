# Handoff: market_data R18 Boundary And Manifest Support

Target repo: `/home/rongyu/workspace/market_data`
Controller repo: `/home/rongyu/workspace/quant-proj`
Callback target: Quant-Dispatcher thread `019f3830-4b44-7a83-944d-247a0d4dc169`
Batch: `WINDOWS_WSL2_STRATEGY_HYPOTHESIS_EXPANSION_BATCH_R18_20260707`

## Assigned Tasks

- `MD-WIN-R18-1`: keep product-route prep inactive.
- `MD-WIN-R18-2`: R18 strategy research manifest schema.
- `MD-WIN-R18-3`: overclaim tests for R18 strategy outputs.

## Required Deliverables

- `reports/codex_dev/windows_wsl2_r18_product_route_prep_inactive_boundary_20260707.md`
- `reports/codex_dev/windows_wsl2_r18_strategy_research_manifest_schema.md`
- `reports/codex_dev/windows_wsl2_r18_strategy_research_manifest_schema.json`
- `tests/test_windows_wsl2_r18_strategy_overclaim.py`

## Required Rules

- R18 must not depend on the prepared DB-2 product route.
- Do not activate product routes.
- Do not change active registry, readiness, schemas, adapters, raw data, or product routes.
- Encode all candidate/readiness/product flags as false.
- Negative tests must reject overclaims that treat wide research eligibility, shadow leaderboard, positive validation, bootstrap pass, wide probe, ML score, or meta-label output as recommendation, ticket, readiness, product route, candidate, or investment advice.

## Callback Envelope

```text
CALLBACK_ENVELOPE:
BATCH: WINDOWS_WSL2_STRATEGY_HYPOTHESIS_EXPANSION_BATCH_R18_20260707
TARGET_REPO: /home/rongyu/workspace/market_data
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
