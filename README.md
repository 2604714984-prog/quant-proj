# quant-proj

quant-proj is the single active code repository for this personal quantitative
research workspace. Mutable databases, raw downloads, caches, backups, and
credentials live outside Git under QUANT_DATA_ROOT.

The project deliberately keeps one small runtime surface:

- built-in defaults plus one optional external configuration file and
  environment-variable overrides;
- one CLI (quant);
- one central DuckDB access layer;
- small A-share and US market-semantics modules;
- one deterministic backtest core;
- one test suite and one CI workflow.

Legacy repositories and completed experiments are historical evidence, not
runtime dependencies. The complete pre-convergence tree is preserved at the
GitHub Release/tag `archive/pre-governance-convergence-20260721`.

## Local setup

~~~bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest
.venv/bin/ruff check .
~~~

The default settings are built into the package, so `quant info` also works
from a non-editable wheel without a copied `config/` directory. The default
project root is the source checkout when present and otherwise the current
directory. Override paths when needed:

~~~bash
export QUANT_DATA_ROOT=/home/rongyu/workspace/quant-data
quant info
~~~

Select an external TOML file with `quant --config PATH ...` or `QUANT_CONFIG`.

Market execution is fail-closed: callers must explicitly attest that bar and
event inputs are complete and available, and settlement/tax rules are selected
from the trade date. US settlement also carries the exact accepted-session
sequence; A-share custom commissions never disable statutory dated stamp tax.
This is deliberately a small contract rather than a data governance subsystem.

Production market-data retrieval and broker execution are intentionally not
part of this rebuild.

## Repository shape

The active branch contains the runtime, generic research primitives, their
tests, and the [minimal architecture](docs/architecture.md). Manager roadmaps,
task packets, mechanism registries, terminal experiment reports, and one-off
runners are intentionally kept out of the active tree.
