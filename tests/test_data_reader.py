import os
from pathlib import Path
import shutil

import duckdb
import pytest

import quant_system.data.reader as reader_module
from quant_system.data.reader import DataReadError, database_info, query


def _database(path: Path) -> Path:
    with duckdb.connect(str(path)) as connection:
        connection.execute("CREATE SCHEMA market")
        connection.execute("CREATE TABLE market.daily(symbol VARCHAR, close DOUBLE)")
        connection.execute("INSERT INTO market.daily VALUES ('AAA', 10), ('BBB', 20)")
    return path


def test_database_info_uses_metadata_without_full_scan(tmp_path: Path) -> None:
    path = _database(tmp_path / "test.duckdb")
    info = database_info(path)

    assert info.path == str(path)
    assert info.size_bytes > 0
    assert [(item.schema, item.table) for item in info.tables] == [
        ("market", "daily")
    ]
    assert info.sha256 is None


def test_database_info_hashes_the_pinned_database(tmp_path: Path) -> None:
    path = _database(tmp_path / "test.duckdb")
    info = database_info(path, include_hash=True)

    assert info.sha256 is not None
    assert len(info.sha256) == 64


def test_query_is_read_only_and_bounded(tmp_path: Path) -> None:
    path = _database(tmp_path / "test.duckdb")
    result = query(path, "SELECT symbol, close FROM market.daily ORDER BY symbol", max_rows=1)

    assert result.columns == ("symbol", "close")
    assert result.rows == (("AAA", 10.0),)
    assert result.truncated is True

    with pytest.raises(DataReadError, match="read-only SELECT"):
        query(path, "DELETE FROM market.daily")
    assert query(path, "SELECT count(*) FROM market.daily").rows == ((2,),)


def test_query_rejects_multi_statement_and_external_file_writes(tmp_path: Path) -> None:
    path = _database(tmp_path / "test.duckdb")
    output = tmp_path / "escaped.csv"

    with pytest.raises(DataReadError, match="exactly one"):
        query(path, "SELECT 1; SELECT 2")
    with pytest.raises(DataReadError, match="read-only SELECT"):
        query(path, f"COPY (SELECT 1) TO '{output}'")

    assert not output.exists()


def test_query_disables_external_file_access(tmp_path: Path) -> None:
    path = _database(tmp_path / "test.duckdb")
    csv_path = tmp_path / "outside.csv"
    csv_path.write_text("value\n1\n", encoding="utf-8")

    with pytest.raises(DataReadError, match="read-only query failed"):
        query(path, f"SELECT * FROM read_csv_auto('{csv_path}')")


def test_reader_rejects_symlink_database(tmp_path: Path) -> None:
    path = _database(tmp_path / "test.duckdb")
    link = tmp_path / "link.duckdb"
    link.symlink_to(path)

    with pytest.raises(DataReadError, match="regular file"):
        database_info(link)


def test_reader_rejects_database_path_replacement(
    tmp_path: Path, monkeypatch
) -> None:
    path = _database(tmp_path / "test.duckdb")
    moved = tmp_path / "moved.duckdb"
    real_connect = reader_module.duckdb.connect
    replaced = False

    def replacing_connect(*args, **kwargs):
        nonlocal replaced
        if not replaced:
            replaced = True
            os.replace(path, moved)
            shutil.copy2(moved, path)
        return real_connect(*args, **kwargs)

    monkeypatch.setattr(reader_module.duckdb, "connect", replacing_connect)
    with pytest.raises(DataReadError, match="changed while"):
        database_info(path)
