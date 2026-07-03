# Standing Human-Gate Authorization

Decision ID: `HG-STANDING-20260704`
Created at: 2026-07-04T01:50:00+08:00
Requested by: user
Status: active

## Authorized Categories

The user granted standing authorization for future execution of:

- DB writes;
- schema migration;
- bulk data ingest;
- registry activation;
- readiness status changes;
- entering a real HITL ticket gate.

## Required Per-Task Execution Record

Before each actual execution, create an `HG-EXEC-*` record in `reports/human_gate/decisions.jsonl` with:

- task id;
- exact command or command family;
- target database, registry, or ticket path;
- source commit/tree or data snapshot id;
- allowed write scope;
- forbidden paths;
- stop conditions;
- validation expected after execution.

## Non-Authorization

This standing authorization does not authorize:

- broker API enablement;
- order routing or order submission;
- auto execution;
- paper trading;
- live trading;
- reading, printing, copying, or committing `.env` or secret values;
- moving raw DB, parquet, SQLite, or payload files into `quant-proj`;
- treating any HITL ticket as an approved trade;
- bypassing Codex-Dev validation or required audit packaging.

## HITL Boundary

Entering the real HITL ticket gate means the system may produce human-review tickets when separately validated and recorded. It does not mean the ticket is approved, actionable, or executable.
