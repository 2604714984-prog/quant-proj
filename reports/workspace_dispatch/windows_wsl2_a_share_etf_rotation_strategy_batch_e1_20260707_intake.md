# WINDOWS_WSL2_A_SHARE_ETF_ROTATION_STRATEGY_BATCH_E1_20260707 Intake

Project: quant-proj
Role: Quant-Dispatcher
Imported: 2026-07-07 Asia/Shanghai
Source: user-supplied ETF momentum rotation hypothesis and task list
Status: `DISPATCH_PREPARED`

## Classification

Ordinary research-only A-share ETF rotation strategy-family batch.

External-audit trigger opened by E1 intake: `no`.

Reason:

- The screenshot/backtest is treated as a research hypothesis only, not accepted evidence.
- The batch explicitly forbids recommendation, ticket, eligibility candidate, readiness, product route, broker/order/paper/live/auto, daily signal push, and strategy candidate promotion.
- Provider/network fetch is not authorized. If ETF data is not already locally available, downstream must stop with `HG_EXEC_REQUIRED_FOR_ETF_DATA_FETCH`.

## Hypothesis To Test

A-share ETF grouped momentum rotation:

- ETF universe around the screenshot idea: 14 ETFs grouped into broad/style/overseas/defensive.
- 20-day momentum.
- Rebalance every 5 trading days.
- Per-group max one ETF.
- Top3 selected.
- Weights `50/25/25`.
- Full investment with `skip_negative=false`.

The reported screenshot result is not controller evidence and must not be used as a strategy claim until reproduced under strict data, timing, cost, and validation controls.

## Assumptions To Freeze And Test

- Whether the ETF universe was fixed ex ante rather than selected with hindsight.
- Whether parameters were pre-registered rather than optimized after seeing results.
- Whether signal timing avoids same-day close-to-close execution.
- Whether ETF adjustment, dividends, suspension, volume, slippage, and cross-border ETF premium/discount effects are handled.
- Whether the 640-day sample is too short and overfit to a recent regime.

## Dispatch Target

`A_Share_Monitor` only:

- fixed thread `019f387b-617e-7273-b539-161216ae3002`
- target repo `/home/rongyu/workspace/A_Share_Monitor`
- tasks `ETF-E1-1` through `ETF-E1-11`

## Boundary

Research-only. No recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket, eligibility candidate, strategy candidate promotion, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, daily signal push, raw-data migration, `.env` access, key output, secret handling, network/provider fetch, DB/cache write or rebuild, schema migration, registry activation, market_data activation, or actionable ranking is authorized.

If local ETF data is unavailable, downstream must stop and return `HG_EXEC_REQUIRED_FOR_ETF_DATA_FETCH`; no provider/network fetch is authorized by this intake.
