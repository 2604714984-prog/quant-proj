# Windows + WSL2 New Machine Checklist

Project: quant-proj
Target: WSL2 Ubuntu on Windows
Workspace rule: use `~/workspace`, not `/mnt/c`

## 1. Create Workspace

```bash
mkdir -p ~/workspace
cd ~/workspace
```

## 2. Clone Repositories

```bash
git clone https://github.com/2604714984-prog/quant-proj.git quant-proj
git clone https://github.com/2604714984-prog/A_Share_Monitor.git A_Share_Monitor
git clone https://github.com/2604714984-prog/US_Stock_Monitor.git US_Stock_Monitor
git clone https://github.com/2604714984-prog/market_data.git market_data
git clone https://github.com/2604714984-prog/strategy_work.git strategy_work
```

## 3. Checkout Expected Branches

```bash
cd ~/workspace/A_Share_Monitor
git checkout codex/harden-a-share-research-pipeline

cd ~/workspace/US_Stock_Monitor
git checkout main

cd ~/workspace/market_data
git checkout main

cd ~/workspace/strategy_work
git checkout main

cd ~/workspace/quant-proj
git checkout main
```

## 4. Create Compatibility Symlinks

```bash
sudo mkdir -p /Users/rongyuxu/Desktop
ln -sfn "$HOME/workspace/quant-proj" "/Users/rongyuxu/Desktop/quant proj"
ln -sfn "$HOME/workspace/A_Share_Monitor" "/Users/rongyuxu/Desktop/A_Share_Monitor"
ln -sfn "$HOME/workspace/US_Stock_Monitor" "/Users/rongyuxu/Desktop/US_Stock_Monitor"
ln -sfn "$HOME/workspace/market_data" "/Users/rongyuxu/Desktop/market_data"
ln -sfn "$HOME/workspace/strategy_work" "/Users/rongyuxu/Desktop/strategy_work"
```

## 5. Inspect Migration Documents First

```bash
sed -n '1,220p' ~/workspace/quant-proj/reports/agent_handoff/windows_wsl2_migration_handoff_20260706.md
sed -n '1,220p' ~/workspace/quant-proj/reports/workspace_dispatch/windows_wsl2_migration_source_repo_heads_20260706.txt
sed -n '1,220p' ~/workspace/quant-proj/reports/workspace_dispatch/windows_wsl2_migration_source_data_inventory_20260706.md
sed -n '1,220p' ~/workspace/strategy_work/MIGRATION.md
sed -n '1,220p' ~/workspace/strategy_work/reports/planning/MIGRATION_GUIDE.md
```

## 6. Install Minimal Dev Dependencies

Prefer project-native setup once each repo's setup files are inspected:

```bash
python3 --version
cd ~/workspace/A_Share_Monitor && python3 -m pip install -e ".[dev]"
cd ~/workspace/US_Stock_Monitor && python3 -m pip install -e ".[dev]"
```

If project extras are unavailable, install only the minimal packages needed for smoke tests after reading repo docs.

## 7. First Smoke Checks

Use lightweight checks only:

```bash
cd ~/workspace/quant-proj
git status --short --branch
git tag --list 'data-strategy-r13-interim-external-audit-20260706'

cd ~/workspace/A_Share_Monitor
git status --short --branch
python3 -m qta --help

cd ~/workspace/strategy_work
git status --short --branch
ls configs
```

## 8. Data Rebuild / Validation Rule

Do not copy old raw data by default. Rebuild or validate a fresh Windows WSL2 snapshot under WSL paths. If provider/network ingest, DB write, schema migration, bulk ingest, readiness change, registry activation, or raw-data migration is needed, stop and create a task-level `HG-EXEC` approval record first.

## 9. Commands Not To Run Yet

```bash
# Do not run full-frame wide3068 strategy search.
python -m qta research discover --config ~/workspace/strategy_work/configs/bare_minimum_r13_wide3068.yaml

# Do not run old full returned-DataFrame feature builds over wide cache.
python - <<'PY'
from qta.data.data_store import ParquetDataStore
from qta.features.store import FeatureStore
store = ParquetDataStore('data/cache')
feat = FeatureStore(store).build()
PY

# Do not perform provider/network ingest until HG-EXEC exists.
python scripts/fill_baostock.py --allow-network
python scripts/expand_cache_300.py --count 3300 --force
```

## 10. Next Engineering Step

Start from the R13C A_Share_Monitor implementation. Verify chunked StrategySearch/backtest on small cache, then wide cache, without loading full `features_daily` into pandas. Keep all outputs research-only.

## Boundary

This checklist does not authorize recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket emission, eligibility candidates, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto behavior, provider/network ingest, DB/schema migration, readiness changes, registry activation, provider-data persistence, raw-data migration, `.env` reads, key output, or secret handling.
