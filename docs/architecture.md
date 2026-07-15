# Minimal architecture

The active system has two filesystem responsibilities:

~~~text
/home/rongyu/workspace/
|-- quant-proj/   # this single Git repository
\-- quant-data/   # mutable data and private runtime state, never committed
~~~

Within the repository:

~~~text
config/                    runtime defaults
src/quant_system/data/     DuckDB reads and append-only writes
src/quant_system/markets/  market-specific execution constraints
src/quant_system/backtest/ deterministic portfolio accounting
src/quant_system/research/ research definitions without outcome data
tests/                     one test suite
~~~

The project does not reproduce the previous dispatcher, task-packet, registry,
multi-repository, or product-route layers. A data import is a CLI call that
validates input, writes in one transaction, and returns a compact receipt.

## Data safety proportional to risk

- Read queries open DuckDB in read-only mode.
- Routine ingestion is append-only and transactional.
- Duplicate natural keys and conflicting existing rows fail closed. Exact
  already-present rows are counted as existing; there is no overwrite policy.
- Destructive migrations are separate commands and require a backup.
- Credentials are injected at runtime and never persisted by the application.

Configuration defaults are defined in code so an installed wheel does not
depend on repository-level files under `config/`. A local settings file and
environment variables remain optional overrides. Project and data roots must
be separate in both directions; neither may contain the other.

Execution inputs carry one explicit qualification assertion covering source
completeness and availability. Missing unexplained bars and unqualified
positive prices fail closed. The small date rules are fixed in code: A-share
sell stamp tax is 0.1% before 2023-08-28 and 0.05% from that date, while US
equity settlement is T+3 before 2017-09-05, T+2 from that date through
2024-05-27, and T+1 from 2024-05-28. A custom A-share commission model changes
commission only; the statutory dated stamp-tax schedule remains active. US sale
settlement must be bound to the complete, strictly increasing accepted-session
sequence after the trade date.

A-share buys require 100-share board lots. Sells may use board lots, or may
fully liquidate a remaining odd lot whose identity was created by a recorded
corporate-action adjustment; arbitrary partial odd-lot sales fail closed.

## Migration rule

The rebuild selectively reimplements accepted behavior. It does not copy whole
legacy repositories or import their Git histories. Frozen source commit and tree
identities are recorded in docs/migration/legacy_inventory.json.
