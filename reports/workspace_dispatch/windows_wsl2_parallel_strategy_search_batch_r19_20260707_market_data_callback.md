# WINDOWS_WSL2_PARALLEL_STRATEGY_SEARCH_BATCH_R19_20260707 market_data Callback

Recorded: 2026-07-08 Asia/Shanghai
Controller: Quant-Dispatcher
Source thread: `019f387b-e763-7c01-ae3d-6be552cdb6dc`
Batch: `WINDOWS_WSL2_PARALLEL_STRATEGY_SEARCH_BATCH_R19_20260707`
Target repo: `/home/rongyu/workspace/market_data`

## Callback Status

Status: `ACCEPTED_RESEARCH_ONLY_WITH_VALIDATION_PASS`

Branch: `main`

Commit: `fd9c20452708afd6e7a5956bc8bd4514dba3568b`
Tree: `56b460107486d742e2f5ce3d79fe5d6613410806`

## Tasks

- `MD-R19-1` ETF research manifest schema.
- `MD-R19-2` no-overclaim tests for ETF research outputs.

## Artifacts

- `reports/codex_dev/etf_rotation_r19_research_manifest_schema.md`
- `reports/codex_dev/etf_rotation_r19_research_manifest_schema.json`
- `tests/test_etf_rotation_r19_overclaim.py`

## Validation

Reported validation:

- Focused pytest PASS: `/home/rongyu/workspace/A_Share_Monitor/.venv/bin/python -m pytest -q tests/test_etf_rotation_r19_overclaim.py` => 6 passed.
- `py_compile` PASS.
- JSON parse PASS.
- `git diff HEAD~1..HEAD --check` PASS.
- Forbidden overclaim scan PASS.
- Working tree clean.
- Note: system `python3` lacks pytest, so the existing `A_Share_Monitor` WSL venv pytest was used.

## Key Results

ETF lane:

- Manifest schema encodes ETF dataset `etf_rotation_e1_20260707` with 30 ETF symbols and 55,726 qfq OHLCV rows.
- Timing is close T signal and T+1 open execution.
- Same-day close-to-close execution is `false`.
- ETF screenshot reproduction is research-only and non-actionable.
- Robust grid pre-registration, cost/liquidity limitation label for Tencent qfq lacking amount/NAV, walk-forward controls, and permutation/bootstrap research controls are encoded.
- Negative tests reject treating ETF leaderboard, screenshot reproduction, ETF hypothesis labels, or ETF/equity regime transfer as recommendation, ticket, readiness, candidate, product route, daily signal push, or investment advice.

Equity carry-forward:

- R18 carry-forward preserved: `WIDE_RESEARCH_PROBE_ELIGIBLE_COUNT=0`.
- `strategy_candidate_available=false`.
- East Money split remains `77/121/2870`.
- ETF/equity regime transfer is encoded as research diagnostic only with `combined_trading_instruction=false` and `equity_candidate_promotion=false`.

## Controller Interpretation

Accepted for controller tracking as research-only market_data R19 manifest and overclaim support.

Current follow-up:

1. Push existing market_data commit `fd9c20452708afd6e7a5956bc8bd4514dba3568b`.
2. Preserve no product-route activation, no registry/readiness change, and no daily signal path.
3. Use the pushed source callback as an input for strategy_work R19 final sync.

## Boundary

No product-route activation, active registry/readiness/schema/adapter/raw-data/product-route change, raw data import, raw-data migration, recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket, eligibility candidate, strategy candidate promotion, production readiness, broker/order/paper/live/auto, daily signal push, market_data activation, full-frame wide strategy search, unapproved DB/cache write or rebuild, or secret output.

External-audit trigger open: `no`.

Fixes required: none.
