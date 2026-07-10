# Repository-wide audit remediation

Status: `REMEDIATED_RESEARCH_RESULTS_REMAIN_INVALID_FOR_STRATEGY_SELECTION`

The 2026-07-10 repository-wide audit findings were reproduced and repaired in the
source repositories. Historical strategy-selection conclusions remain frozen and
must be regenerated under the corrected methodology; no prior promising/pass label
is carried forward.

## Source preservation

- `US_Stock_Monitor`: `548f351b7ea37df0350ceb0a6075541d8830fdf5`
- `A_Share_Monitor`: `d40e5abfdbe95d6491e42f2f83231421d7b17057`
- `market_data`: `39cb26a60839b2546f19a75bc9eb80cb331ca4c3`
- `strategy_work`: `b21dd904f5874085aaf6fdbb69d3eaeb1b638506`
- `us_stock_30w`: `5a07db5c5df2cff71fb5938a9431848461cf75d0`

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
- CI now installs dependencies and runs pytest plus repository-wide tracked-Python
  Ruff/compile checks in the source repositories.
- The obsolete standalone `qlib_train.py` path was removed; repository-wide Python
  lint now covers tracked package, test, and utility-script code.
- GPU evidence tests validate recorded package versions without requiring generic
  CPU-only CI runners to install the source workstation's CUDA environment.
- The US30W Adaptive+Quality survivorship check was recovered from a local compiled
  artifact, reimplemented as tracked source, rerun against seven validated historical
  names, and corrected. The prior zero-impact claim is superseded: full Sharpe changed
  from `0.787952` to `0.771392`, full return changed by `-0.013551`, and one added name
  generated two filled events. The test segment was unchanged, but complete
  point-in-time membership remains unproven.

## Validation

- `US_Stock_Monitor`: full pytest PASS; all tracked Python Ruff PASS; safety PASS.
- `A_Share_Monitor`: full pytest PASS; all tracked Python Ruff PASS; safety PASS.
- `market_data`: `113 passed`; full Ruff PASS.
- `strategy_work`: `11 passed`; scoped tracked Python Ruff PASS.
- `git diff --check`: required before each source commit and PASS.
- GitHub Actions `research-validation` is green on the current source commits.

## Remote repository governance

- `A_Share_Monitor` now uses `main` as its default branch; the aligned historical
  branches remain at the same source commit.
- Public `strategy_work/main` has enforced branch protection: strict
  `static-validation`, admin enforcement, linear history, conversation resolution,
  and force-push/deletion denial.
- GitHub returned HTTP 403 for branch protection and rulesets on the four private
  repositories because the current account plan requires GitHub Pro or public
  visibility for that feature. Their CI remains active and green; repository
  visibility was not weakened to bypass the plan restriction.

## Research effect

All strategy-selection outputs produced before these fixes are historical evidence,
not current selection evidence. `strategy_candidate_available=false`. New strategy
claims require rerunning the affected research from pinned snapshots with the corrected
split, purge, execution, valuation, and snapshot rules.

The post-fix US30W survivorship re-audit is current research evidence only. It keeps
Adaptive+Quality as a research lead, not an active strategy. A complete historical
membership reconstruction is still required before this specific risk can be closed.
