# Project ownership and deprecation plan

This project is optimized for one user, one WSL host, one DuckDB, research-only operation, and approximately CNY 400,000 of capital. Small, explicit paths are preferred over institutional-style orchestration.

## Final ownership matrix

| Repository | Final active responsibility | Frozen reference | Deprecation state |
|---|---|---|---|
| `quant-proj` | roadmap, status, decisions, audits | `158c6c797cca5e5dedacdcf9f5e47403eb2ab10b` | controller flow reduction in progress |
| `central-data-ingestion` | sole writer, provider adapters, routine append CLI | `d17c3b474a5a97867e9b502f57b4cd572c2ed77f`; integration `17f027785b7531534a6286821f9e0048dc633c6a` | replacement accepted; production cutover not authorized |
| `market_data` | read-only catalog/client | `300d4cf902cafc7f8462991e761e658febdc1424` | active writer removal pending parity |
| `quant_research_lab` | sole A-share research engine | `6b98b94d0cdd674d6e07cce93726f204ab3a6594`; R5 audited base `d5e902af4beab6826ebc34c9a940b881f25ad750` | R5 semantic repair in progress |
| `US_Stock_Monitor` | sole US research engine | `872f54211e56a162e713d987d904b49d2521bd25` | narrow semantic repair in progress |
| `A_Share_Monitor` | unmigrated adapters, market rules, historical evidence | main `ab12cf99331a39a1396c7c7f885072a9f0f68c08`; preservation base `1a64e70873fc8a3c3d998e509cbcf690010ffef0` | canonical repair lane selected; divergent main retained as evidence only |
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
- replacement reference: Draft PR #24, head `17f027785b7531534a6286821f9e0048dc633c6a`
- legacy reference: `market_data@300d4cf902cafc7f8462991e761e658febdc1424`
- remove after parity: active `market_data` writer entry points, SQLite staging, copy/swap publisher, custom signature and duplicate receipt/CLI paths
- retain: a small read-only central-store client and immutable Git history
- rollback: latest verified production backup plus the frozen legacy Git refs; production cutover remains a separate owner decision

### A-share research

- replacement owner: `quant_research_lab` repaired R5
- legacy reference: `A_Share_Monitor` preservation baseline `1a64e70873fc8a3c3d998e509cbcf690010ffef0`
- retain in legacy: only unmigrated adapters, market-specific rules, and historical evidence
- remove after semantic parity: legacy strategy-engine imports, CLIs, CI entries, and current docs that imply authority
- rollback/reference: immutable R5 and legacy branch refs; no full replay until the read-only snapshot callback is accepted

### US research

- active owner: `US_Stock_Monitor@872f54211e56a162e713d987d904b49d2521bd25` plus the narrow semantic repair
- forensic reference: `us_stock_30w@62abe5ba0213e9e7a8ade69db423fc71a3746357`
- remove after copying required specs/tests: active research or dispatch claims in `us_stock_30w`
- retain: immutable forensic history and rejected-result evidence

### Controller

- replacement flow: one issue -> one branch/PR -> focused CI -> one short closeout
- remove from ordinary active flow: mandatory prompt-inbox copies, per-task packet folders, fixed callback UUIDs, model-route bindings, duplicate acceptance layers, and separate branch-head/merge identity jobs
- retain elevated controls only for material engine semantics, data/PIT/schema changes, destructive DB work, strategy intake, and future execution-stage opening
- historical task and audit artifacts remain immutable evidence and are not deleted

## Stop boundary

Any new repository, engine, writer, registry, signature/orchestration layer, unsupported provider, destructive DB action, or complexity increase without comparable deletion returns `SCOPE_EXPANSION_REQUIRES_USER_APPROVAL`.
