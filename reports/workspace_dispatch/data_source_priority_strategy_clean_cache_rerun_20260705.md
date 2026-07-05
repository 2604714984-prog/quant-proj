# Strategy Clean-Cache Rerun Result

Date: 2026-07-05
Controller role: Quant-Dispatcher
Source project: strategy_work
Source repo path: `/Users/rongyuxu/Desktop/strategy_work`
Source commit: `b0d7d823f956067c6e58fef013dfc5e2e721c1ea`
Source tree: `5978bb83503f68dd29017d9c54962262ac881f45`
Source push: `origin/main`

## Scope

User requested a local A-share strategy rerun from `strategy_work`, focused on finding a clean cache, updating the strategy config, running `bare_minimum`, running `lowvol_quality_focused` if the minimum run had positive test Sharpe, then archiving the leaderboard and candidate registry in `strategy_work`.

Classification: ordinary research-only strategy/data-quality work.

External-audit trigger opened: `no`.

## Cache Selection

Inspected A-share local caches from `/Users/rongyuxu/Desktop/A_Share_Monitor`.

Selected clean cache:

- `data/phase3_real_small_cache_20260630_50`
- `daily=86817` rows
- `daily` symbols: `50`
- `daily` duplicate `ts_code/trade_date` rows: `0`
- `features_daily=86817` rows

Rejected as current target:

- `data/cache`: 3068 symbols, duplicate-free daily, but no `features_daily` at inspection time.
- `data/cache_expanded`: 3068 symbols but duplicate daily rows were present.

## Config Changes

Updated in `strategy_work`:

- `configs/bare_minimum.yaml`
- `configs/lowvol_quality_focused.yaml`

Both now point at `data/phase3_real_small_cache_20260630_50`.

`bare_minimum.yaml` preserves:

- `ma_window: [120]`
- `fail_on_data_quality_fail: false`

## Run Results

### bare_minimum

Command:

```bash
cd /Users/rongyuxu/Desktop/A_Share_Monitor
python -m qta research discover --config /Users/rongyuxu/Desktop/strategy_work/configs/bare_minimum.yaml
```

Run dir:

- `outputs/bare_minimum/research_20260705_161817`

Leaderboard summary:

- strategy: `auto_low_vol_quality_e7b5d574c0`
- label: `rejected`
- reasons: `negative_validation|parameter_instability_fail|cost_stress_fail`
- test return: `0.018857732433001262`
- test Sharpe: `0.14278796046568734`
- data quality: `PASS`
- survivor bias: `PASS`
- cost stress: `FAIL`

Because test Sharpe was positive, the focused run was executed.

### lowvol_quality_focused

Command:

```bash
cd /Users/rongyuxu/Desktop/A_Share_Monitor
python -m qta research discover --config /Users/rongyuxu/Desktop/strategy_work/configs/lowvol_quality_focused.yaml
```

Run dir:

- `outputs/lowvol_quality_pilot/research_20260705_161927`

Leaderboard summary:

| strategy_id | label | reasons | test_return | test_sharpe | data_quality | survivor_bias | cost_stress |
|---|---|---|---:|---:|---|---|---|
| `auto_low_vol_quality_686e80f39d` | rejected | `trade_count_too_low|validation_trade_count_too_low` | 0.0000 | 0.0000 | PASS | PASS | PASS |
| `auto_defensive_momentum_a7af75d44d` | rejected | `parameter_instability_fail` | -0.0901 | -0.0934 | PASS | PASS | PASS |
| `auto_low_vol_quality_9d59a3cc1b` | rejected | `max_drawdown_reject|negative_validation|parameter_instability_fail|cost_stress_fail` | -0.1147 | -0.2745 | PASS | PASS | FAIL |
| `auto_defensive_momentum_ba4775b255` | rejected | `parameter_instability_fail|cost_stress_fail` | -0.0992 | -0.1125 | PASS | PASS | FAIL |

## Archived Artifacts In strategy_work

- `reports/a_share/bare_minimum_20260705_161817/leaderboard.csv`
- `reports/a_share/bare_minimum_20260705_161817/candidate_registry.json`
- `reports/a_share/lowvol_quality_pilot_20260705_161927/leaderboard.csv`
- `reports/a_share/lowvol_quality_pilot_20260705_161927/candidate_registry.json`
- `reports/SUMMARY.md`

## Interpretation

The `fina_indicator` / data-quality gate mis-kill path is no longer the active blocker in the selected clean cache. The minimum run has `data_quality_status=PASS` and `survivor_bias_status=PASS`.

The remaining blockers are strategy quality and robustness blockers:

- negative validation
- parameter instability
- cost stress failure
- trade-count weakness on some focused variants

The clean 50-symbol cache is useful as a gate/debug sample, but it is too narrow to prove candidate quality. The next data-source priority should be building `features_daily` safely for the cleaned 3068-symbol `data/cache` and then rerunning the same strategy configs on a wider cross-section.

## Boundary Statement

No recommendation, ticket, product route, production readiness, broker/order path, paper trading, live trading, auto execution, raw-data migration, or secret handling was authorized or performed.
