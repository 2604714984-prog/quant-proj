# WINDOWS_WSL2_FEATURE_MATERIALIZATION_AND_STRATEGY_DELTA_R21_20260708 US_Stock_Monitor Callback

Recorded: 2026-07-08 Asia/Shanghai
Controller: Quant-Dispatcher
Source thread: `019f387b-a161-7ad0-8678-f03a099612ba`
Batch: `WINDOWS_WSL2_FEATURE_MATERIALIZATION_AND_STRATEGY_DELTA_R21_20260708`
Target repo: `/home/rongyu/workspace/US_Stock_Monitor`

## Callback Status

Status: `DATA_REPORT_COMPLETE`; pushed to `origin/main`.

Branch: `main`
Commit: `71adb489760dc7ea2ee89f83da5bed90ca751f22`
Tree: `5893890b26adcb31599fb1c34ecd39a50d421c13`

Downstream reported `HEAD == origin/main == 71adb489760dc7ea2ee89f83da5bed90ca751f22`.

## Tasks

- `G-R21-1`: Global regime row extension completed with source health first, bounded public/no-secret fetch, local research staging, tracked report artifacts, validation evidence, and focused tests.

## Artifacts

Tracked artifacts:

- `reports/codex_dev/global_r21_regime_row_extension_20260708.json` sha256 `03846814e2ac38026c333e0d5a45deea53ae83d04cb8bc4095ec1ef77b7c337a`
- `reports/codex_dev/global_r21_regime_row_extension_20260708.md` sha256 `b6589899a786322a176f0463f4e82fef3187dfa8b36d2aaa2ac39106c0368552`
- `reports/codex_dev/global_r21_regime_row_extension_20260708.csv` sha256 `f56555aa6490a096f61acbf38e85132b7984652ad444059bab2909ac87a40012`
- `reports/codex_dev/global_r21_regime_row_extension_20260708_command_transcript.txt` sha256 `df774604aa7cc024f32700e704e7ce2337c47a82b783c7b7843d1d51882a5c6c`
- `reports/codex_dev/global_r21_regime_row_extension_20260708_validation.json` sha256 `ccd326de5ef66488d0bf6d77cf409075339862da69c962ae292d1ecbaf948973`

Ignored local staging artifacts:

- `data/r21_global_regime_extension/global_r21_regime_row_extension_20260708/manifest.json` sha256 `03846814e2ac38026c333e0d5a45deea53ae83d04cb8bc4095ec1ef77b7c337a`
- `data/r21_global_regime_extension/global_r21_regime_row_extension_20260708/daily_bars.csv.gz` sha256 `ed13823b1371c52d35b0b7a82fa22972dbc520ddf2552ac67a7cf65b80d891e2`
- `data/r21_global_regime_extension/global_r21_regime_row_extension_20260708/regime_extension.csv` sha256 `f56555aa6490a096f61acbf38e85132b7984652ad444059bab2909ac87a40012`

## Validation

- Command transcript recorded: PASS.
- Manifest/count/hash evidence: PASS.
- JSON parse PASS for tracked report JSON, ignored staging manifest, and validation JSON.
- Duplicate-key/missingness checks PASS: daily duplicate symbol-dates 0, regime duplicate symbol-dates 0, missing daily/regime symbols `[]`.
- Validation JSON PASS: daily_rows 4882, regime_rows 4882.
- `py_compile` PASS for `scripts/r21_global_regime_extension.py` and `scripts/simonlin_r20_global_smoke.py`.
- Focused pytest PASS: `tests/test_r21_global_regime_extension.py`, `tests/test_simonlin_r20_global_smoke.py`, `tests/test_us_metadata_repair.py`, 13 passed.
- `agent_safety_check.py` PASS.
- `git diff --check` and `git diff --cached --check` PASS.
- Forbidden overclaim/enabling scan PASS.
- Post-push verification PASS; `main` aligned with `origin/main` at `71adb489760dc7ea2ee89f83da5bed90ca751f22`.

## Source Health

- `ran_before_broader_fetch=true`.
- Required source health: PASS.
- Tencent quote public endpoint: PASS, parsed 4/4 health quotes.
- Tencent HK kline public endpoint: PASS, parsed 31 HK daily rows in health check.
- Nasdaq historical public endpoint: PASS, parsed 376 US daily rows in health check.
- Optional `global_stock_data_skill_raw`: WARN; raw GitHub reference fetch failed after 1 bounded attempt; no auth/paywall/circumvention attempted.

## Data Status

- Bounded date range: `2025-01-01..2026-07-08`.
- Max symbols: 13.
- Materialized symbols: `00700.HK`, `9988.HK`, `AAPL`, `FXI`, `GLD`, `HYG`, `KWEB`, `LQD`, `MSFT`, `NVDA`, `QQQ`, `SPY`, `TLT`.
- Daily rows: 4,882.
- Regime rows: 4,882.
- Schema status: PASS.
- Usage: `RESEARCH_ONLY_CONTEXT_ROWS`.
- Generated fields: date, symbol, market, asset_group, feature_version, source_status, daily_source, close, volume, return_1d, return_5d, return_20d, return_60d, realized_vol_20d, drawdown_from_60d_high, trend_state, context_only, research_only.
- Bad daily rows skipped: FXI 1, GLD 1, HYG 1, LQD 1, SPY 1.
- Data sources used: Tencent public quote endpoint, Tencent public HK fqkline endpoint, Nasdaq historical public endpoint.

## Results

- `GLOBAL_NEWS_MACRO_STATUS`: G-R21-1 global regime row extension PASS.
- Strategy results: not evaluated by this downstream support task.
- No strategy diagnostic/search, ranking, parameter selection, wide probe, or promotion performed.
- `STRATEGY_CANDIDATE_AVAILABLE=false`.

## Controller Interpretation

Accepted for controller tracking as optional US/global R21 support. The callback is already pushed to `origin/main` and can be included in strategy_work final sync after A_Share_Monitor and market_data accepted callbacks are complete.

## Boundary

Research-only public/no-secret source-local fetch and local staging/report/test writes only. No advice, `PENDING_HUMAN_REVIEW`, ticket, eligibility item, strategy promotion, readiness or registry activation, product-route activation, market_data activation, broker/order/paper/live/auto, daily signal push, raw-data migration into controller, active schema migration, or `.env`/key/token/auth/credential/secret access or output.

External-audit trigger open: `false`.

Fixes required: none for this bounded downstream support task.
