# Human-Gate Classification: E1 ETF Data Fetch/Load

Decision date: 2026-07-07 Asia/Shanghai
Decision id: `HG-EXEC-TASK-A-ETF-E1-DATA-FETCH-LOAD-20260707`

## Classification

Task-level HG-EXEC approved for bounded network ingest and controlled local cache/staging write.

Permission level:

- `L2_CONTROLLED_NETWORK_INGEST`
- `L1_CONTROLLED_CACHE_WRITE`

External-audit trigger open: `no`.

## Allowed

- Bounded public/no-secret ETF data fetch/load.
- Up to 80 A-share ETF symbols.
- Date range `20180101..20260707`.
- Controlled local A_Share_Monitor staging/cache/report/test writes.
- Manifest/count/hash evidence.
- Resume E1 research-only diagnostics after data validation.

## Not Authorized

- Secrets, `.env`, token, key, auth, or credential access/output.
- Unbounded provider sync.
- Provider/source expansion outside the authorization.
- DB/cache writes outside A_Share_Monitor task scope.
- Schema migration.
- Readiness change.
- Registry activation.
- market_data activation.
- Product-route activation.
- Recommendation/advice.
- `PENDING_HUMAN_REVIEW`.
- Ticket.
- Eligibility candidate.
- Strategy candidate promotion.
- Broker/order/paper/live/auto.
- Daily signal push.
- Raw-data migration into quant-proj.

## Stop Rule

If any forbidden action is needed to proceed, stop and return `BLOCKED` with the relevant stop condition. Do not widen the scope in-source.
