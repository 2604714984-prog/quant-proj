from pathlib import Path

import duckdb
import pytest

from quant_system.data.writer import DataWriteError, append_rows


SOURCE_A = "a" * 64
SOURCE_B = "b" * 64


def _database(path: Path) -> Path:
    with duckdb.connect(str(path)) as connection:
        connection.execute("CREATE SCHEMA market")
        connection.execute(
            "CREATE TABLE market.daily("
            "symbol VARCHAR NOT NULL, trade_date DATE NOT NULL, "
            "close DOUBLE, source VARCHAR NOT NULL)"
        )
    return path


def _rows(close: float = 10.0) -> list[dict[str, object]]:
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
    assert replay.inserted_rows == 2
    assert second_identity.inserted_rows == 0
    assert second_identity.existing_rows == 2
    with duckdb.connect(str(path), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM market.daily").fetchone() == (2,)
        assert connection.execute(
            "SELECT count(*) FROM _quant_meta.ingest_runs"
        ).fetchone() == (2,)


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


def test_duplicate_natural_keys_fail_before_write(tmp_path: Path) -> None:
    path = _database(tmp_path / "test.duckdb")
    rows = _rows()
    rows.append(dict(rows[0]))

    with pytest.raises(DataWriteError, match="duplicate natural keys"):
        _append(path, rows, "batch-001", SOURCE_A)
    with duckdb.connect(str(path), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM market.daily").fetchone() == (0,)


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
