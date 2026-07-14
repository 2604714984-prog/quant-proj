# quant-proj

quant-proj is the single active code repository for this personal quantitative
research workspace. Mutable databases, raw downloads, caches, backups, and
credentials live outside Git under QUANT_DATA_ROOT.

The project deliberately keeps one small runtime surface:

- one configuration file plus environment-variable overrides;
- one CLI (quant);
- one central DuckDB access layer;
- small A-share and US market-semantics modules;
- one deterministic backtest core;
- one test suite and one CI workflow.

Legacy repositories remain frozen migration sources. They are not runtime
dependencies and their orchestration layers are not copied into this project.

## Local setup

~~~bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest
.venv/bin/ruff check .
~~~

The default data location is resolved outside the repository. Override it when
needed:

~~~bash
export QUANT_DATA_ROOT=/home/rongyu/workspace/quant-data
quant info
~~~

Production market-data retrieval and broker execution are intentionally not
part of this rebuild.
