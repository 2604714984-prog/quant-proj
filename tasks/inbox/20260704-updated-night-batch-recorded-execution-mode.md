# UPDATED_NIGHT_BATCH_RECORDED_EXECUTION_MODE_20260704

Source: user-provided ChatGPT task list
Imported by: `Quant-Dispatcher`
Status: imported and packetized

## Requested Operating Mode

Adopt `RECORDED_EXECUTION_MODE_V1`.

Controlled execution is allowed when all required records exist:

- Human-Gate record;
- command transcript;
- required explicit flags such as `--allow-network` or `--allow-write`;
- manifest/status evidence;
- Codex acceptance.

## Permission Levels

- `L0_RESEARCH_DIAGNOSTIC`: default, read-only, no network, no DB write, no registry activation, no ticket emission.
- `L1_CONTROLLED_DB_WRITE`: allowed with Human-Gate, `--allow-write`, snapshot id, manifest/counts/hashes, transcript, Codex acceptance.
- `L2_CONTROLLED_NETWORK_INGEST`: allowed with Human-Gate, `--allow-network`, provider/date/symbol bounds, transcript, Codex acceptance.
- `L3_REGISTRY_READINESS_CHANGE`: allowed with Human-Gate, old/new diff, rollback path, transcript, Codex acceptance.
- `L4_PENDING_HUMAN_REVIEW_TICKET`: allowed with Human-Gate and all gates passing; may emit `PENDING_HUMAN_REVIEW` only.

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
- `.env` read;
- key value output.

## Follow-Up Tasks Requested

1. `US-DB-OPS-2 controlled US 300-symbol expansion`
2. `A-DB-OPS controlled A-share 500/1000 expansion`
3. `market_data registry/readiness controlled update`
4. `A11 research-to-HITL gated ticket attempt`
5. `US strategy experiment to ticket refresh attempt`
