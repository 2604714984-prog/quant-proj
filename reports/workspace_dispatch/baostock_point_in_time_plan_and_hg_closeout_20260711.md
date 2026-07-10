# BaoStock Point-in-Time Plan And HG Closeout

Status: `EXECUTION_BLOCKED_NETWORK_STALL_ROLLED_BACK`

## Accepted private plan

- responsible Luna task: `/root/baostock_plan_manifest`
  (`019f4cd0-fe98-7f40-8bdb-90412ed8a24e`);
- path:
  `/home/rongyu/workspace/.private_quant_inputs/baostock_fundamental_smoke/plan_20260703_6ea528568de5.json`;
- file mode: `0600`;
- file SHA-256:
  `7245c93bdc8dcd6ea340feb7b94b82245c6ffb9963fd8a65ed732e5f0c6cbf8a`;
- canonical planning SHA-256:
  `5cb64436f663a84e5c208ad1d5d0e3531b2b6c5fdbfa0862f942de03f361203b`;
- source SHA-256:
  `a1a8f9c3cb4c637e4ee53cd74fc9fe51b11ff3b43bc5858c73580c295f09e350`;
- eligible read-only source aggregates: 4,996 rows, SH 2,228, SZ 2,768;
- selected shape: 30 unique tokens, SH/SZ 15/15, each year 10, all
  quarters, exact preregistered cell quotas;
- selector and token both use
  `SHA256(implementation_commit|exchange|normalized_provider_code|year|quarter)`;
- dry run: no socket, provider import, network execution, or file write;
  `strategy_candidate_available=false`.

No provider identifiers are present in this controller record.

## One bounded HG attempt

The initial durable grant covered only commit
`6ea528568de57da85eec3b12aec37a7a444ae5a3`, the accepted plan, endpoint
`public-api.baostock.com:10030`, 30 bundles, 182 primary requests, at most 30
retries, one retry per request, and an immutable research snapshot. Its grant
record SHA-256 was
`e8616f9e083c9b34597278cf8a7f8b2260086db61cbc6d7d1c147aa5380ef483`.

Executor `/root/baostock_smoke_executor`
(`019f4cda-2d82-7351-9fdc-5a69f471a396`) stalled before materialization. The
bounded rollback terminated the process and removed only the new staging
snapshot. Manager verification found no published snapshot or files, a clean
implementation worktree, and an unchanged remote ref.

## Durable retry denial

The same HG path is closed against reuse:

- path:
  `/home/rongyu/workspace/.private_quant_inputs/baostock_fundamental_smoke/hg_exec_20260711_6ea528568de5.json`;
- mode: `0600`;
- current SHA-256:
  `0ed7cf55b165ea892d3d858c5ea9ca66187090d69bcab2e3377e3e0443c6b14c`;
- status: `HG_EXEC_DENIED`;
- retry authorized: `false`;
- implementation gate: confirmed to reject the closed record.

No automatic retry is authorized. No snapshot exists, so independent Luna
snapshot acceptance is not applicable. No canonical DB/cache file, prior
snapshot, strategy state, readiness/product route, broker/order/paper/live/auto
surface, or secret was touched.
