# Project ownership and deprecation plan

This project is optimized for one user, one WSL host, one DuckDB, research-only operation, and approximately CNY 400,000 of capital. Small, explicit paths are preferred over institutional-style orchestration.

## Final ownership matrix

| Repository | Final active responsibility | Frozen reference | Deprecation state |
|---|---|---|---|
| `quant-proj` | roadmap, status, decisions, audits | PR #27; exact post-patch head recorded externally | routine flow reduced to one issue/PR/CI/closeout; external re-review and merge pending |
| `central-data-ingestion` | target writer, provider adapters, routine append CLI | PR #24 `04a3258acb2ca6f924ea2e0bd222bf957ac7555e` | installed shadow runtime ready; CI runs `29344443374` and `29344446501` pass; production cutover not authorized |
| `market_data` | read-only catalog/client | PR #5 `47a6c6675fe0be173a5552461921d89ec6d60b09` | active writer removed; merge pending |
| `quant_research_lab` | target sole A-share research engine | user-controlled PR #6 `d3359a87c0873a76c5b374c281ed844ac5f29c98` | R5 code ready; full replay and sole-authority cutover blocked |
| `US_Stock_Monitor` | sole US research engine | PR #8 `22d79956be4755e7bdea3235f91c16284d48a242` | semantic repair branch green; external re-review and merge pending |
| `A_Share_Monitor` | unmigrated adapters, market rules, historical evidence | PR #8 `b6a4ddc48899a95c5b0c9e8cce03bb5e24b493eb` targets `main`; archive tag `archive/a-share-canonical-semantic-followup-pre-main-integration-20260714` | default-branch canonicalization complete in PR; external re-review and merge pending; broad deactivation still blocked |
| `us_stock_30w` | archived forensic evidence | `62abe5ba0213e9e7a8ade69db423fc71a3746357` | archive after required frozen specs/tests are copied to owners |
| `strategy_work` | archived knowledge and failure memory | `a050e20ba50ada3f8bb052585c667770dac2c2c4` | no new execution engine or trial authority |

Data-room and shared-report repositories are excluded from routine CI and dispatch.

## Required deprecation record

No active path is removed until its replacement reaches parity. Each completed deprecation must record:

1. replacement owner and immutable commit;
2. last active commit or tag;
3. rollback or forensic reference location;
4. active imports, CLI entries, CI jobs, and current-doc references removed;
5. focused parity and rollback evidence.

## Planned active-surface reductions

### Central database

- replacement owner: `central-data-ingestion`
- replacement reference: PR #24, head `04a3258acb2ca6f924ea2e0bd222bf957ac7555e`
- legacy reference: `market_data@300d4cf902cafc7f8462991e761e658febdc1424`
- parity implementation: `market_data` PR #5 removes the active `central_warehouse.py` writer and writer tests; active runtime is reduced by 1,074 net lines
- retain: a small read-only central-store catalog/query client and immutable Git history
- writer implementation: installed set-based shadow writer and routine CLI; focused backup/restore, idempotence, transport-sanitization, and clean-wheel tests pass
- rollback: latest verified production backup plus the frozen legacy Git refs; production cutover remains a separate owner decision

### A-share research

- replacement owner: `quant_research_lab` repaired R5 at user-controlled PR #6, head `d3359a87c0873a76c5b374c281ed844ac5f29c98`
- legacy reference: `A_Share_Monitor` preservation baseline `1a64e70873fc8a3c3d998e509cbcf690010ffef0`
- retain in legacy: only unmigrated adapters, market-specific rules, and historical evidence
- current blocker: QRL still reads A_Share cache/local DuckDB paths and imports old `qta` code in active research scripts
- required parity copy: T+1, suspension, limit-up/down, PIT financial availability, validation-only selection, and no-test-selection specifications still exist only in `A_Share_Monitor`
- remove only after those dependencies and specifications move: legacy strategy-engine imports, CLIs, CI entries, and current docs that imply authority
- rollback/reference: immutable R5 and legacy branch refs; full replay remains blocked pending accepted data callback and external re-review

### US research

- active owner: `US_Stock_Monitor` PR #8, head `22d79956be4755e7bdea3235f91c16284d48a242`
- forensic reference: `us_stock_30w@62abe5ba0213e9e7a8ade69db423fc71a3746357`
- remove after moving the two remaining historical callers: active research or dispatch claims in `us_stock_30w`
- retain: immutable forensic history and rejected-result evidence

### Controller

- replacement flow: one issue -> one PR -> focused CI -> short closeout
- remove from ordinary active flow: mandatory prompt-inbox copies, per-task packet folders, fixed callback UUIDs, model-route bindings, duplicate acceptance layers, and separate branch-head/merge identity jobs
- retain elevated controls only for material engine semantics, data/PIT/schema changes, destructive DB work, strategy intake, and future execution-stage opening
- historical task and audit artifacts remain immutable evidence and are not deleted

## Phase 3 adjudication

`BLOCKED_NOT_READY`

The target ownership is frozen, but the legacy repositories cannot yet be safely deactivated. The blocking evidence is narrow and concrete:

1. QRL still depends on A_Share cache/local-DB paths and old `qta` imports.
2. Six A-share semantic specifications have not yet been copied into the authoritative engine.
3. Database parity has not yet produced the final allowlist of A_Share adapters and market rules that must remain.
4. `US_Stock_Monitor` still has two historical callers tied to `us_stock_30w`.
5. The A-share pre-main integration tag now exists; final active-state archive tags still do not exist for `us_stock_30w` or `strategy_work`.

The minimum safe sequence is: obtain integrated external re-review of the exact updated heads; merge the semantic and database PRs only after clearance; make QRL a read-only central-data consumer; migrate the six specifications and remove old imports; move the two US historical callers; publish the final adapter allowlist; create the remaining immutable archive tags; then use narrow deactivation PRs. Direct broad deletion is prohibited because it would remove still-active semantics and rollback evidence.

Part 2 audit remains external-only and was not inspected, supplemented, accepted, or adjudicated by Quant Manager.

## Stop boundary

Any new repository, engine, writer, registry, signature/orchestration layer, unsupported provider, destructive DB action, or complexity increase without comparable deletion returns `SCOPE_EXPANSION_REQUIRES_USER_APPROVAL`.
