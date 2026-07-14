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
- Duplicate natural keys fail unless the caller explicitly selects a documented
  conflict policy.
- Destructive migrations are separate commands and require a backup.
- Credentials are injected at runtime and never persisted by the application.

## Migration rule

The rebuild selectively reimplements accepted behavior. It does not copy whole
legacy repositories or import their Git histories. Frozen source commit and tree
identities are recorded in docs/migration/legacy_inventory.json.
