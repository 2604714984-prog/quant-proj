import json
from pathlib import Path

import duckdb

from quant_system.cli import main


def _database(path: Path) -> Path:
    with duckdb.connect(str(path)) as connection:
        connection.execute("CREATE SCHEMA market")
        connection.execute(
            "CREATE TABLE market.daily("
            "symbol VARCHAR NOT NULL, trade_date DATE NOT NULL, close DOUBLE)"
        )
    return path


def test_append_cli_is_dry_run_by_default(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    db = _database(tmp_path / "test.duckdb")
    rows = tmp_path / "rows.json"
    rows.write_text(
        json.dumps(
            [{"symbol": "AAA", "trade_date": "2026-07-14", "close": 10.0}]
        ),
        encoding="utf-8",
    )
    project = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("QUANT_PROJECT_ROOT", str(project))
    monkeypatch.setenv("QUANT_DATA_ROOT", str(tmp_path))

    result = main(
        [
            "data",
            "append",
            "--db",
            str(db),
            "--schema",
            "market",
            "--table",
            "daily",
            "--keys",
            "symbol,trade_date",
            "--input",
            str(rows),
            "--batch-id",
            "batch-001",
            "--source-sha256",
            "a" * 64,
        ]
    )

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "DRY_RUN"
    assert payload["writes"] is False
    with duckdb.connect(str(db), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM market.daily").fetchone() == (0,)
        assert connection.execute(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema='_quant_meta'"
        ).fetchone() == (0,)


def test_append_cli_requires_execute_and_then_writes(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    db = _database(tmp_path / "test.duckdb")
    rows = tmp_path / "rows.jsonl"
    rows.write_text(
        '{"symbol":"AAA","trade_date":"2026-07-14","close":10.0}\n',
        encoding="utf-8",
    )
    project = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("QUANT_PROJECT_ROOT", str(project))
    monkeypatch.setenv("QUANT_DATA_ROOT", str(tmp_path))

    result = main(
        [
            "data",
            "append",
            "--db",
            str(db),
            "--schema",
            "market",
            "--table",
            "daily",
            "--keys",
            "symbol,trade_date",
            "--input",
            str(rows),
            "--batch-id",
            "batch-001",
            "--source-sha256",
            "a" * 64,
            "--execute",
        ]
    )

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "COMPLETED"
    assert payload["inserted_rows"] == 1
