from decimal import Decimal
import os
from pathlib import Path
import shutil

import duckdb
import pytest

import quant_system.data.writer as writer_module
from quant_system.data.writer import DataWriteError, append_rows


SOURCE_A = "a" * 64
SOURCE_B = "b" * 64


def _database(path: Path, *, close_type: str = "DOUBLE") -> Path:
    assert close_type in {"FLOAT", "REAL", "DOUBLE"}
    with duckdb.connect(str(path)) as connection:
        connection.execute("CREATE SCHEMA market")
        connection.execute(
            "CREATE TABLE market.daily("
            "symbol VARCHAR NOT NULL, trade_date DATE NOT NULL, "
            f"close {close_type}, source VARCHAR NOT NULL)"
        )
    return path


def _rows(close: object = 10.0) -> list[dict[str, object]]:
    return [
        {
            "symbol": "AAA",
            "trade_date": "2026-07-14",
            "close": close,
            "source": "fixture",
        },
        {
            "symbol": "BBB",
            "trade_date": "2026-07-14",
            "close": 20.0,
            "source": "fixture",
        },
    ]


def _append(path: Path, rows: list[dict[str, object]], batch: str, source: str):
    return append_rows(
        path,
        schema="market",
        table="daily",
        natural_keys=("symbol", "trade_date"),
        rows=rows,
        batch_id=batch,
        source_sha256=source,
    )


def test_append_and_exact_replay_are_idempotent(tmp_path: Path) -> None:
    path = _database(tmp_path / "test.duckdb")

    first = _append(path, _rows(), "batch-001", SOURCE_A)
    replay = _append(path, _rows(), "batch-001", SOURCE_A)
    second_identity = _append(path, _rows(), "batch-002", SOURCE_B)

    assert first.status == "COMPLETED"
    assert first.inserted_rows == 2
    assert replay.status == "IDEMPOTENT_REPLAY"
    assert replay.inserted_rows == 0
    assert replay.existing_rows == 2
    assert second_identity.inserted_rows == 0
    assert second_identity.existing_rows == 2
    with duckdb.connect(str(path), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM market.daily").fetchone() == (2,)
        assert connection.execute(
            "SELECT count(*) FROM _quant_meta.ingest_runs"
        ).fetchone() == (2,)
        assert connection.execute(
            "SELECT inserted_rows, existing_rows FROM _quant_meta.ingest_runs "
            "WHERE batch_id='batch-001'"
        ).fetchone() == (2, 0)


@pytest.mark.parametrize("close_type", ["FLOAT", "REAL", "DOUBLE"])
@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_staging_rejects_nonfinite_values_in_every_floating_column_type(
    tmp_path: Path,
    close_type: str,
    value: str,
) -> None:
    path = _database(tmp_path / "test.duckdb", close_type=close_type)

    with pytest.raises(DataWriteError, match="nonfinite floating"):
        _append(path, _rows(close=value), "batch-001", SOURCE_A)

    with duckdb.connect(str(path), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM market.daily").fetchone() == (0,)
        assert connection.execute(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema='_quant_meta' AND table_name='ingest_runs'"
        ).fetchone() == (0,)


def test_conflict_rolls_back_entire_batch(tmp_path: Path) -> None:
    path = _database(tmp_path / "test.duckdb")
    _append(path, _rows(), "batch-001", SOURCE_A)

    with pytest.raises(DataWriteError, match="conflict"):
        _append(path, _rows(close=99.0), "batch-002", SOURCE_B)

    with duckdb.connect(str(path), read_only=True) as connection:
        assert connection.execute(
            "SELECT close FROM market.daily WHERE symbol='AAA'"
        ).fetchone() == (10.0,)
        assert connection.execute(
            "SELECT count(*) FROM _quant_meta.ingest_runs"
        ).fetchone() == (1,)


def test_batch_id_cannot_be_rebound(tmp_path: Path) -> None:
    path = _database(tmp_path / "test.duckdb")
    _append(path, _rows(), "batch-001", SOURCE_A)

    with pytest.raises(DataWriteError, match="different input"):
        _append(path, _rows(), "batch-001", SOURCE_B)


def test_exact_replay_requires_all_target_rows_to_still_exist(tmp_path: Path) -> None:
    path = _database(tmp_path / "test.duckdb")
    _append(path, _rows(), "batch-001", SOURCE_A)
    with duckdb.connect(str(path)) as connection:
        connection.execute("DELETE FROM market.daily WHERE symbol='BBB'")

    with pytest.raises(DataWriteError, match="target rows are missing"):
        _append(path, _rows(), "batch-001", SOURCE_A)


def test_exact_replay_rejects_target_value_drift(tmp_path: Path) -> None:
    path = _database(tmp_path / "test.duckdb")
    _append(path, _rows(), "batch-001", SOURCE_A)
    with duckdb.connect(str(path)) as connection:
        connection.execute("UPDATE market.daily SET close=99 WHERE symbol='AAA'")

    with pytest.raises(DataWriteError, match="conflict"):
        _append(path, _rows(), "batch-001", SOURCE_A)


def test_duplicate_natural_keys_fail_before_write(tmp_path: Path) -> None:
    path = _database(tmp_path / "test.duckdb")
    rows = _rows()
    rows.append(dict(rows[0]))

    with pytest.raises(DataWriteError, match="duplicate natural keys"):
        _append(path, rows, "batch-001", SOURCE_A)
    with duckdb.connect(str(path), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM market.daily").fetchone() == (0,)


def test_staging_type_coercion_cannot_create_duplicate_natural_keys(
    tmp_path: Path,
) -> None:
    path = _database(tmp_path / "test.duckdb")
    rows = _rows()
    rows[0]["symbol"] = 1
    rows[1]["symbol"] = "1"

    with pytest.raises(DataWriteError, match="staging conversion produced duplicate"):
        _append(path, rows, "batch-001", SOURCE_A)
    with duckdb.connect(str(path), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM market.daily").fetchone() == (0,)


def test_duplicate_target_keys_fail_closed_without_negative_counts(tmp_path: Path) -> None:
    path = _database(tmp_path / "test.duckdb")
    _append(path, _rows(), "batch-001", SOURCE_A)
    with duckdb.connect(str(path)) as connection:
        connection.execute(
            "INSERT INTO market.daily VALUES ('AAA', '2026-07-14', 10, 'fixture')"
        )

    with pytest.raises(DataWriteError, match="target contains duplicate"):
        _append(path, _rows(), "batch-002", SOURCE_B)
    with duckdb.connect(str(path), read_only=True) as connection:
        assert connection.execute(
            "SELECT count(*) FROM _quant_meta.ingest_runs"
        ).fetchone() == (1,)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), Decimal("-Infinity")])
def test_natural_keys_must_be_finite(tmp_path: Path, value: object) -> None:
    path = _database(tmp_path / "test.duckdb")
    rows = _rows()
    rows[0]["symbol"] = value

    with pytest.raises(DataWriteError, match="must be finite"):
        _append(path, rows, "batch-001", SOURCE_A)


def test_public_writer_rejects_private_metadata_schema(tmp_path: Path) -> None:
    path = _database(tmp_path / "test.duckdb")

    with pytest.raises(DataWriteError, match="private"):
        append_rows(
            path,
            schema="_quant_meta",
            table="ingest_runs",
            natural_keys=("batch_id",),
            rows=[{"batch_id": "forged"}],
            batch_id="batch-001",
            source_sha256=SOURCE_A,
        )


@pytest.mark.parametrize(
    "table_sql",
    [
        (
            "CREATE TABLE _quant_meta.ingest_runs("
            "batch_id VARCHAR NOT NULL, target VARCHAR NOT NULL, "
            "source_sha256 VARCHAR NOT NULL, batch_sha256 VARCHAR NOT NULL, "
            "row_count BIGINT NOT NULL, inserted_rows BIGINT NOT NULL, "
            "existing_rows BIGINT NOT NULL, completed_at TIMESTAMPTZ NOT NULL)"
        ),
        (
            "CREATE TABLE _quant_meta.ingest_runs("
            "batch_id VARCHAR PRIMARY KEY, target VARCHAR NOT NULL, "
            "source_sha256 VARCHAR NOT NULL, batch_sha256 VARCHAR NOT NULL, "
            "row_count INTEGER NOT NULL, inserted_rows BIGINT NOT NULL, "
            "existing_rows BIGINT NOT NULL, completed_at TIMESTAMPTZ NOT NULL)"
        ),
    ],
)
def test_existing_metadata_table_must_match_exact_contract(
    tmp_path: Path, table_sql: str
) -> None:
    path = _database(tmp_path / "test.duckdb")
    with duckdb.connect(str(path)) as connection:
        connection.execute("CREATE SCHEMA _quant_meta")
        connection.execute(table_sql)

    with pytest.raises(DataWriteError, match="immutable contract"):
        _append(path, _rows(), "batch-001", SOURCE_A)
    with duckdb.connect(str(path), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM market.daily").fetchone() == (0,)


@pytest.mark.parametrize(
    ("inserted", "existing"),
    [(-1, 3), (1, 0)],
)
def test_replay_rejects_forged_metadata_counts(
    tmp_path: Path, inserted: int, existing: int
) -> None:
    path = _database(tmp_path / "test.duckdb")
    _append(path, _rows(), "batch-001", SOURCE_A)
    with duckdb.connect(str(path)) as connection:
        connection.execute(
            "UPDATE _quant_meta.ingest_runs "
            "SET inserted_rows=?, existing_rows=? WHERE batch_id='batch-001'",
            [inserted, existing],
        )

    with pytest.raises(DataWriteError, match="replay counts"):
        _append(path, _rows(), "batch-001", SOURCE_A)


def test_input_columns_must_match_target_order(tmp_path: Path) -> None:
    path = _database(tmp_path / "test.duckdb")
    rows = [
        {
            "trade_date": "2026-07-14",
            "symbol": "AAA",
            "close": 10.0,
            "source": "fixture",
        }
    ]

    with pytest.raises(DataWriteError, match="target order"):
        _append(path, rows, "batch-001", SOURCE_A)


def test_writer_rejects_symlink_database(tmp_path: Path) -> None:
    path = _database(tmp_path / "test.duckdb")
    link = tmp_path / "link.duckdb"
    link.symlink_to(path)

    with pytest.raises(DataWriteError, match="regular file"):
        _append(link, _rows(), "batch-001", SOURCE_A)


def test_writer_rejects_hard_linked_lock_file(tmp_path: Path) -> None:
    path = _database(tmp_path / "test.duckdb")
    lock = path.with_suffix(".duckdb.writer.lock")
    lock.write_bytes(b"")
    os.link(lock, tmp_path / "lock-alias")

    with pytest.raises(DataWriteError, match="single-link"):
        _append(path, _rows(), "batch-001", SOURCE_A)


def test_writer_rejects_nonregular_lock_path(tmp_path: Path) -> None:
    path = _database(tmp_path / "test.duckdb")
    path.with_suffix(".duckdb.writer.lock").mkdir()

    with pytest.raises(DataWriteError, match="writer lock"):
        _append(path, _rows(), "batch-001", SOURCE_A)


def test_writer_rejects_hard_linked_database(tmp_path: Path) -> None:
    path = _database(tmp_path / "test.duckdb")
    alias = tmp_path / "database-alias.duckdb"
    os.link(path, alias)

    with pytest.raises(DataWriteError, match="single-link regular file"):
        _append(alias, _rows(), "batch-001", SOURCE_A)
    with duckdb.connect(str(path), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM market.daily").fetchone() == (0,)


def test_writer_rejects_database_hardlink_created_during_append(
    tmp_path: Path, monkeypatch
) -> None:
    path = _database(tmp_path / "test.duckdb")
    alias = tmp_path / "late-database-alias.duckdb"
    real_target_columns = writer_module._target_columns

    def linking_target_columns(connection, schema: str, table: str):
        columns = real_target_columns(connection, schema, table)
        os.link(path, alias)
        return columns

    monkeypatch.setattr(writer_module, "_target_columns", linking_target_columns)
    with pytest.raises(DataWriteError, match="path identity changed"):
        _append(path, _rows(), "batch-001", SOURCE_A)
    with duckdb.connect(str(path), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM market.daily").fetchone() == (0,)


def test_writer_rolls_back_if_database_path_is_replaced(
    tmp_path: Path, monkeypatch
) -> None:
    path = _database(tmp_path / "test.duckdb")
    moved = tmp_path / "moved.duckdb"
    real_target_columns = writer_module._target_columns

    def replacing_target_columns(connection, schema: str, table: str):
        columns = real_target_columns(connection, schema, table)
        os.replace(path, moved)
        shutil.copy2(moved, path)
        return columns

    monkeypatch.setattr(writer_module, "_target_columns", replacing_target_columns)
    with pytest.raises(DataWriteError, match="path identity changed"):
        _append(path, _rows(), "batch-001", SOURCE_A)

    with duckdb.connect(str(path), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM market.daily").fetchone() == (0,)


def test_writer_reports_postcommit_database_path_replacement_as_ambiguous(
    tmp_path: Path, monkeypatch
) -> None:
    path = _database(tmp_path / "test.duckdb")
    moved = tmp_path / "committed.duckdb"
    real_assert = writer_module._assert_path_identity
    checks = 0

    def replacing_third_check(
        active_path: Path, descriptor: int, identity: tuple[int, int]
    ) -> None:
        nonlocal checks
        checks += 1
        if checks == 3:
            os.replace(path, moved)
            shutil.copy2(moved, path)
        real_assert(active_path, descriptor, identity)

    monkeypatch.setattr(writer_module, "_assert_path_identity", replacing_third_check)
    with pytest.raises(DataWriteError, match="committed.*ambiguous"):
        _append(path, _rows(), "batch-001", SOURCE_A)

    with duckdb.connect(str(moved), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM market.daily").fetchone() == (2,)
    with duckdb.connect(str(path), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM market.daily").fetchone() == (0,)


def test_writer_checks_database_identity_after_connection_close(
    tmp_path: Path, monkeypatch
) -> None:
    path = _database(tmp_path / "test.duckdb")
    pristine = tmp_path / "pristine.duckdb"
    committed = tmp_path / "committed.duckdb"
    shutil.copy2(path, pristine)
    real_connect = writer_module.duckdb.connect

    class CloseReplacingConnection:
        def __init__(self, connection) -> None:
            self.connection = connection

        def __getattr__(self, name: str):
            return getattr(self.connection, name)

        def close(self) -> None:
            self.connection.close()
            os.replace(path, committed)
            os.replace(pristine, path)

    def replacing_connect(*args, **kwargs):
        return CloseReplacingConnection(real_connect(*args, **kwargs))

    monkeypatch.setattr(writer_module.duckdb, "connect", replacing_connect)
    with pytest.raises(DataWriteError, match="committed.*ambiguous"):
        _append(path, _rows(), "batch-001", SOURCE_A)

    with real_connect(str(committed), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM market.daily").fetchone() == (2,)
    with real_connect(str(path), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM market.daily").fetchone() == (0,)
