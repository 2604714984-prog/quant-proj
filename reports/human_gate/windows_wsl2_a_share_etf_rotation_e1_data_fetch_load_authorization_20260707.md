# Human-Gate Authorization: A-share ETF E1 Data Fetch/Load

Decision date: 2026-07-07 Asia/Shanghai
Controller: Quant-Dispatcher
Decision id: `HG-EXEC-TASK-A-ETF-E1-DATA-FETCH-LOAD-20260707`

## User Authorization

The user authorized an independent task-level HG-EXEC for bounded ETF data fetch/load after E1 stopped at `HG_EXEC_REQUIRED_FOR_ETF_DATA_FETCH`.

## Scope

This authorization permits A_Share_Monitor to perform a bounded A-share ETF OHLC/NAV data fetch/load needed to unblock:

`WINDOWS_WSL2_A_SHARE_ETF_ROTATION_STRATEGY_BATCH_E1_20260707`

The allowed data scope is limited to ETF research data for the E1 ETF rotation strategy family:

- Snapshot id: `etf_rotation_e1_20260707`
- Max ETF symbols: `80`
- Date range: `20180101..20260707`
- Provider/source: public/no-secret ETF data source or existing project provider path; comply with the controller `simonlin1212` source-candidate policy for any new provider candidate unless the source is already present in the project.
- Allowed local writes: controlled A_Share_Monitor staging/cache/report/test artifacts only.

After validated ETF data exists locally, A_Share_Monitor may resume the previously dispatched E1 research-only tasks.

## Required Evidence

- Command transcript.
- Manifest with symbol count, row count, date range, provider/source name, and source freshness.
- Hashes for generated raw/staged local ETF artifacts and summary reports.
- ETF universe coverage evidence.
- Missingness, duplicate key, listing-date, adjusted price/NAV, volume/amount, and timing audit.
- JSON parse validation where JSON artifacts are written.
- `git diff --check`.
- `agent_safety_check.py` where applicable.
- Forbidden overclaim scan.

## Boundary

This authorization does not permit recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket, eligibility candidate, strategy candidate promotion, data-clear promotion, readiness change, product-route activation, market_data activation, broker/order/paper/live/auto, daily signal push, raw-data migration into quant-proj, secret access/output, schema migration, or registry activation.

External-audit trigger open from this authorization: `no`.

## Stop Conditions

Stop and return a blocked callback if any of the following occurs:

- A secret, `.env`, token, key, credential, or auth file is required.
- Provider/source access cannot be performed through public/no-secret means.
- A new provider candidate conflicts with the controller source policy and no existing project provider path can be used.
- The task would exceed 80 ETF symbols or the approved date range without a new authorization.
- Unbounded provider sync is required.
- DB/cache writes are requested outside the allowed A_Share_Monitor project scope.
- Schema/readiness/registry/product-route activation is requested.
- Any recommendation, ticket, candidate, readiness, product, live/paper/broker/order, or daily signal output is attempted.
