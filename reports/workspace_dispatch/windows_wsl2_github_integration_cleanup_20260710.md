# GitHub Integration Cleanup 20260710

## Branch Alignment

Fast-forwarded stale remote branches to their current fact-source branches:

- `quant-proj/main` -> `6124d1109bb0ccd3ba37c3960e969e831517fb6a`
- `A_Share_Monitor/main` -> `1bd3bb954c52ed068a526a2afe6b041e6b4b0ca8`
- `A_Share_Monitor/codex/harden-a-share-research-pipeline` -> `1bd3bb954c52ed068a526a2afe6b041e6b4b0ca8`
- `market_data/main` -> `5571cc4e75cba3cdece97d524da4fb7f6bca379e`
- `US_Stock_Monitor/main` -> `4c2f269a030eba30b6d0329ffc25332e286382f6`

## US Boundary Cleanup

`US_Stock_Monitor/main` now removes the duplicate local simulation / paper-style research scripts from that repo. The reproducible research pipeline remains in `us_stock_30w`; US-R evidence remains preserved in `US_Stock_Monitor` reports.

## CI

Added minimal GitHub Actions validation workflows to:

- `quant-proj`
- `A_Share_Monitor`
- `market_data`
- `US_Stock_Monitor`
- `strategy_work`

The workflow compiles tracked Python files, parses tracked JSON outside data/output/runops paths, and runs the local safety check when present.

## Large Artifact Handling

No destructive history rewrite was performed. Existing tracked large artifacts remain preserved. Future work should move large parquet/CSV/SQLite/zip outputs to external artifact storage and keep only manifests and hashes in Git.

## Remaining Warnings

- Branch protection still requires repository settings work.
- Large artifacts remain in historical Git objects.
- `strategy_work` visibility should be checked in GitHub settings if strategy research must remain private.
