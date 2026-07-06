# WINDOWS_WSL2_DATA_STRATEGY_AND_BASE_BATCH_R15_20260706 Spec

## Objective

Run a broad research-only A-share data/strategy development batch plus
corresponding market_data research data-base contract tasks and strategy_work
memo sync.

The batch must not tune parameters to find a pass. It must harden partial data
evidence, survivor-bias evidence, chunked execution, strategy rejection
diagnostics, and research-only data-base contracts.

## Classification

Ordinary research-only data/strategy/data-base batch.

External-audit trigger opened: `no`.

## Verified Inputs

- A_Share_Monitor R14 evidence commit: `dd3089e2a9c1693ea0571db37c185d6584f1bc14`.
- A_Share_Monitor repair package commit: `735ac8f18266a3720d1b0e729ed6b203539d758e`.
- strategy_work sync: `2bfbe33e654e7ceb76117ab7b156ff44f2d979be`.
- East Money split: `77` pass, `121` date-gap, `2870` missing.
- All strategy reruns remain rejected.
- wide3068 full-frame remains blocked; chunked mode is required.

## Tasks

| ID | Owner | Task | Dependency |
|---|---|---|---|
| `A-WIN-R15-1` | `A_Share_Monitor` | East Money coverage expansion priority queue. | none |
| `A-WIN-R15-2` | `A_Share_Monitor` | East Money date-gap diagnostics for 121 symbols. | R14 gap matrix |
| `A-WIN-R15-3` | `A_Share_Monitor` | Controlled East Money HG-EXEC plan only. | none; no network |
| `A-WIN-R15-4` | `A_Share_Monitor` | Survivor-bias evidence hardening v2. | R14 survivor evidence |
| `A-WIN-R15-5` | `A_Share_Monitor` | `features_daily` lineage and staging assumptions manifest. | R14 feature rebuild |
| `A-WIN-R15-6` | `A_Share_Monitor` | Tradability evidence base. | local staging data only |
| `A-WIN-R15-7` | `A_Share_Monitor` | Full-frame guard finalization. | chunked guard exists |
| `A-WIN-R15-8` | `A_Share_Monitor` | Memory telemetry unit normalization. | R14 telemetry warning |
| `A-WIN-R15-9` | `A_Share_Monitor` | Metadata-only table profiling. | chunked profile path |
| `A-WIN-R15-10` | `A_Share_Monitor` | Chunked feature reader hardening. | chunked reader exists |
| `A-WIN-R15-11` | `A_Share_Monitor` | Chunked backtest equivalence expansion. | small/mini caches |
| `A-WIN-R15-12` | `A_Share_Monitor` | Strategy rejection research agenda. | rerun rejection evidence |
| `A-WIN-R15-13` | `A_Share_Monitor` | Cost-stress decomposition. | rerun artifacts |
| `A-WIN-R15-14` | `A_Share_Monitor` | Parameter instability surface. | no best-parameter promotion |
| `A-WIN-R15-15` | `A_Share_Monitor` | Pre-registered broad strategy family diagnostics. | plan first |
| `MD-WIN-R15-1` | `market_data` | A-share wide feature research data-base contract. | R14/R15 evidence references |
| `MD-WIN-R15-2` | `market_data` | Cross-repo evidence bridge. | A-share evidence paths |
| `MD-WIN-R15-3` | `market_data` | Negative overclaim regression tests. | none |
| `MD-WIN-R15-4` | `market_data` | Research data-base manifest schema draft. | none |
| `SW-WIN-R15-1` | `strategy_work` | Broad R15 strategy memo. | can start after dispatch |
| `SW-WIN-R15-2` | `strategy_work` | Strategy-quality blocker roadmap. | can start after dispatch |
| `SW-WIN-R15-3` | `strategy_work` | Final sync after source acceptances. | A-share + market_data callbacks |
| `QP-WIN-R15-1` | `quant-proj` | R15 intake and source receipt. | done by dispatcher |
| `QP-WIN-R15-2` | `quant-proj` | R15 result summary and closeout. | downstream callbacks |

## Stop Conditions

- `FULL_FRAME_WIDE_STRATEGY_SEARCH_ATTEMPTED`
- `OOM_OR_MEMORY_PRESSURE_UNBOUNDED`
- `NETWORK_PROVIDER_FETCH_REQUIRED_WITHOUT_HG_EXEC`
- `DB_SCHEMA_CHANGE_REQUIRED_WITHOUT_HG_EXEC`
- `REGISTRY_OR_READINESS_CHANGE_REQUIRED`
- `PRODUCT_ROUTE_ACTIVATION_REQUIRED`
- `SECRET_OR_ENV_ACCESS_REQUIRED`
- `STRATEGY_RESULT_BEING_PROMOTED_TO_TICKET_OR_RECOMMENDATION`
- `EAST_MONEY_PARTIAL_COVERAGE_WRITTEN_AS_FULL_COVERAGE`
- `SURVIVOR_BIAS_IMPROVED_WRITTEN_AS_ELIMINATED`

## Required Callback Envelope

```text
CALLBACK_ENVELOPE:
BATCH: WINDOWS_WSL2_DATA_STRATEGY_AND_BASE_BATCH_R15_20260706
TARGET_REPO:
BRANCH:
COMMIT:
TREE:
STATUS:
TASKS_COMPLETED:
ARTIFACTS:
VALIDATION:
KEY_RESULTS:
WARNINGS:
BLOCKERS:
BOUNDARY_RESULT:
EXTERNAL_AUDIT_TRIGGER_OPEN:
FIXES_REQUIRED:
NEXT_SOURCE_ACTION:
```

## Boundary

Research-only. No recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket,
eligibility candidate, data-clear promotion, product-route activation,
production readiness, broker/order/paper/live/auto, raw-data migration, `.env`
access, key output, or secret handling. Future network/provider fetch,
DB/cache rebuild, schema/readiness/registry changes, and registry activation
require separate task-level HG-EXEC evidence and transcript.
