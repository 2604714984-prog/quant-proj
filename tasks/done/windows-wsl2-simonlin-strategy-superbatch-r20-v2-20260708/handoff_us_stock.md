# Handoff - US_Stock_Monitor R20_V2 Optional Global/US Support

Target repo: `/home/rongyu/workspace/US_Stock_Monitor`
Controller repo: `/home/rongyu/workspace/quant-proj`
Callback target: Quant-Dispatcher thread `019f3830-4b44-7a83-944d-247a0d4dc169`
Batch: `WINDOWS_WSL2_SIMONLIN_STRATEGY_SUPERBATCH_R20_V2_20260708`

## Read First

- `/home/rongyu/workspace/quant-proj/reports/human_gate/windows_wsl2_simonlin_strategy_superbatch_r20_v2_authorization_20260708.md`
- `/home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-simonlin-strategy-superbatch-r20-v2-20260708/spec.md`
- `/home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-simonlin-strategy-superbatch-r20-v2-20260708/human_gate.md`

## Assigned Scope

Optional global/US/HK support lane:

- `G-R20-1` global-stock-data adapter smoke.
- `G-R20-2` cross-market regime features.

Smoke symbols:

- `SPY`, `QQQ`, `GLD`, `TLT`, `HYG`, `LQD`, `FXI`, `KWEB`, `AAPL`, `NVDA`, `MSFT`, `00700.HK`, `9988.HK`.

Deliverables may use `reports/codex_dev/` if the repo convention prefers it, but must preserve the R20 artifact names from the spec and include a manifest/count/hash report.

## Rules

- Public/no-secret only.
- Source health must run before any broader fetch.
- Source-local research staging/report/test writes only.
- No active registry/readiness/product-route/schema changes.
- No raw-data migration into `quant-proj`.
- No recommendation, ticket, candidate, daily signal, or trading path.
- If source requires auth, token, secret, paywall, or anti-abuse circumvention, stop with `SOURCE_AUTH_REQUIRED` or `SOURCE_DEFERRED`.

## Required Validation

- JSON parse PASS.
- Focused tests if code/tests changed.
- `git diff --check` PASS.
- Forbidden overclaim scan PASS.
- Manifest/count/hash evidence for any fetched/written artifacts.
- Duplicate-key/missingness checks where data is generated.

## Callback

Return R20_V2 callback envelope. `GLOBAL_RESULTS` must summarize source health, symbols attempted, symbols accepted, row counts, schema status, and whether cross-market features are usable as research-only regime evidence.
