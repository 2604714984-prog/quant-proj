# Repository-wide audit remediation

Status: `REMEDIATED_RESEARCH_RESULTS_REMAIN_INVALID_FOR_STRATEGY_SELECTION`

The 2026-07-10 repository-wide audit findings were reproduced and repaired in the
source repositories. Historical strategy-selection conclusions remain frozen and
must be regenerated under the corrected methodology; no prior promising/pass label
is carried forward.

## Source preservation

- `US_Stock_Monitor`: `548f351b7ea37df0350ceb0a6075541d8830fdf5`
- `A_Share_Monitor`: `3657c00cfece21ba750d3c74e6834d3cb69b5917`
- `market_data`: `111cfed09955090fc3bd2fa0d7c7362aa3ba9a3b`
- `strategy_work`: `372144ce1e6d5ecad7c17bc8bdd08ea68bc41fa4`

## Corrected defects

- Strategy selection now uses train/validation only; holdout/forward results are
  diagnostic and forward labels are purged when they cross a split boundary.
- Remaining factor, liquidity, PEG, negative-PE, rebalance, and path-audit status
  calculations no longer use holdout/test outcomes to select or rank research lines.
- DuckDB raw/basic/symbol joins include `snapshot_id`.
- US explicit empty targets liquidate existing holdings on the next session; the
  backtest calendar uses the union of symbol dates.
- US corporate actions are deduplicated and hashed into snapshot identity; orphan
  action rows no longer count as price-history coverage; imported source files carry
  hashes.
- A US CSV import marked as real now requires a matching source-provenance sidecar;
  the caller flag alone is rejected.
- The optional vectorized scanner uses chronological train/validation/diagnostic-test
  splits, shifts signals one bar, ranks by validation only, and fails visibly on engine
  errors.
- A-share missing held prices are valued conservatively instead of at purchase cost;
  all-in cost basis includes buy fees.
- Invalid strategy expressions fail closed; named strategy families retain their
  identity and grid values are expanded rather than silently collapsed.
- FeatureStore enforces its in-memory limit and refuses a filtered-read failure that
  would otherwise fall back to a full-table load.
- Parquet writes stage before replacement; DuckDB cache ingestion is transactional.
- Manual fills validate date/time/value fields, reject duplicate IDs, and preserve
  positions belonging to other accounts.
- A10 evidence is verified against the pinned Git tag, commit, tree, and blob bytes.
- `market_data` now checks physical database facts. The stale A-share product-readable
  claim was removed because the pinned snapshot currently has zero physical canonical
  rows; both unified routes remain blocked pending requalification.
- Schema dumps contain column metadata and row counts only, never sample data rows.
- Controller project registry was replaced with current source commits and a local
  Git-object validator.
- CI now installs dependencies and runs pytest plus Ruff in the source repositories.
- The obsolete standalone `qlib_train.py` path was removed; repository-wide Python
  lint now covers tracked package, test, and utility-script code.

## Validation

- `US_Stock_Monitor`: full pytest PASS; all tracked Python Ruff PASS; safety PASS.
- `A_Share_Monitor`: full pytest PASS; all tracked Python Ruff PASS; safety PASS.
- `market_data`: `113 passed`; full Ruff PASS.
- `strategy_work`: `11 passed`; scoped tracked Python Ruff PASS.
- `git diff --check`: required before each source commit and PASS.

## Research effect

All strategy-selection outputs produced before these fixes are historical evidence,
not current selection evidence. `strategy_candidate_available=false`. New strategy
claims require rerunning the affected research from pinned snapshots with the corrected
split, purge, execution, valuation, and snapshot rules.
