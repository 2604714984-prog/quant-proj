# Recorded Execution Mode V1

Status: active
Mode id: `RECORDED_EXECUTION_MODE_V1`
Owner: `Quant-Dispatcher`

This mode replaces the older posture of "do not run anything that creates real state" with controlled execution:

```text
Allowed only when recorded:
- Human-Gate record
- command transcript
- bounded command flags
- manifest/status evidence
- Codex acceptance
```

This is not a trading-boundary change. It allows controlled data, registry, readiness, and `PENDING_HUMAN_REVIEW` workflows. It does not authorize broker/order/execution behavior.

## Permission Levels

### L0_RESEARCH_DIAGNOSTIC

Allowed by default:

- factor experiments;
- threshold sweeps;
- read-only DB queries;
- strategy diagnosis;
- report generation;
- Codex lightweight acceptance;
- Reasonix advisory review.

Not allowed at L0:

- DB writes;
- network ingest;
- registry activation;
- readiness status change;
- ticket emission.

### L1_CONTROLLED_DB_WRITE

Allowed with Human-Gate record:

- real DuckDB or SQLite writes;
- local snapshot append or refresh;
- canonical table refresh;
- crosscheck table write;
- manifest or readiness draft write;
- raw payload download to ignored path;
- parquet/cache write to ignored path.

Required:

- `permission_level=L1_CONTROLLED_DB_WRITE`;
- `--allow-write`;
- explicit `snapshot_id`;
- output path must be ignored or otherwise excluded from source control when it contains raw/generated data;
- manifest, counts, and hashes;
- command transcript;
- Codex acceptance.

### L2_CONTROLLED_NETWORK_INGEST

Allowed with Human-Gate record:

- Tushare ingest;
- Yahoo/Nasdaq/Stooq/free-source ingest;
- Baostock/Akshare ingest;
- US universe expansion;
- A-share universe expansion.

Required:

- `permission_level=L2_CONTROLLED_NETWORK_INGEST`;
- `--allow-network`;
- explicit provider;
- bounded date range and symbol count;
- no `.env` read;
- key from environment only if needed;
- no key value output;
- rate limit or retry behavior recorded;
- network transcript summary;
- raw payloads ignored;
- Codex acceptance.

### L3_REGISTRY_READINESS_CHANGE

Allowed with Human-Gate record:

- `research_readiness=true`;
- `local_research_ready=true`;
- `product_read_candidate=true`;
- registry draft activation;
- research data route activation;
- source snapshot accepted for experiments.

Required:

- old route;
- new route;
- reason;
- snapshot id;
- row count;
- symbol count;
- date range;
- crosscheck status;
- rollback path;
- approver;
- command transcript;
- Codex acceptance.

Still not allowed without separate higher review:

- active product route replacing a previous route;
- HITL data readiness used by ticket gate;
- `production_recommendation_data_ready=true`;
- `broker_execution_data_ready=true`;
- `auto_execution_data_ready=true`;
- `live_trading_allowed=true`.

Broker, live, and auto execution remain forbidden.

### L4_PENDING_HUMAN_REVIEW_TICKET

Allowed with Human-Gate record only when all relevant gates pass:

- emit `PENDING_HUMAN_REVIEW` only;
- write ignored ticket ledger;
- require `human_review_required=true`.

Required:

- all data, evidence, risk, and review gates pass;
- no active unresolved blocker;
- ticket schema validation pass;
- ticket status is exactly `PENDING_HUMAN_REVIEW`;
- `broker_api_allowed=false`;
- `order_routing_allowed=false`;
- `auto_execution_allowed=false`;
- `manual_fill_runtime_enabled=false`;
- `paper_trading_allowed=false`;
- `live_trading_allowed=false`;
- command transcript;
- Codex acceptance.

If new ticket-gate logic is introduced, set `external_audit_required=true` before routine use.

## Still Forbidden

- broker API;
- order routing;
- order submission;
- auto execution;
- paper trading;
- live trading;
- system-generated orders;
- system-generated fills;
- broker-synced fills;
- trade plan;
- entry price instruction;
- target weight;
- position sizing;
- allocation;
- secret handling changes;
- `.env` reads;
- key value output.

## Dispatcher Rule

Do not say controlled data or HITL tasks are categorically impossible. Instead:

- DB writes can run with Human-Gate, `--allow-write`, transcript, manifest, and Codex acceptance.
- Network ingest can run with Human-Gate, `--allow-network`, provider bounds, transcript, and Codex acceptance.
- Registry activation can run with Human-Gate, old/new diff, rollback path, transcript, and Codex acceptance.
- Readiness changes can run when they do not overclaim data readiness as recommendation or trading readiness.
- `PENDING_HUMAN_REVIEW` tickets can be emitted only as human-review entries, never as orders or trade plans.
