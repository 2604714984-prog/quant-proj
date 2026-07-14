# Registry refresh: R2 Wave 0

The seven repositories in the Repository-wide remediation scope were inspected read-only on 2026-07-13. Every live checkout was clean. Exact live branch, commit, tree, and upstream facts are recorded in `registry/projects.yaml`; the immutable audit refs, pull requests and CI runs remain separately frozen in `reports/remediation_r2/R2_BASELINE_FREEZE_20260713.json`.

The central database is `/home/rongyu/workspace/quant_data/quant_research.duckdb`, SHA-256 `65e2c1354380b69b563b1846ec61871c6f99c46156736dc1954939278093c5c5`, 1,001,926,656 bytes. Wave 0 does not authorize provider calls or database mutation. The selected central-writer implementation boundary is the private `market_data` repository, with its publisher disabled pending Gate B.

No `.env`, credential, provider payload, raw database, Parquet, cache, output, or log artifact was copied into the controller workspace. `strategy_candidate_available=false` remains fixed.
