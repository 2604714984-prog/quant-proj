from __future__ import annotations

from datetime import date
import importlib.util
import json
from pathlib import Path
import socket
import sys
from types import SimpleNamespace

import pytest

from quant_system.research import swing_structure as swing


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_a_share_swing_structure_once.py"
SPEC = importlib.util.spec_from_file_location("swing_once", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


def _hash(character: str) -> str:
    return character * 64


def _git_hash(character: str) -> str:
    return character * 40


def _legacy_master_hash(
    *,
    source: str = "wsl2_chain_repair_20260706",
    snapshot_id: str = "wsl2_chain_repair_20260706_195210",
    symbol: str = "600000.SH",
    table: str = "symbol_master",
    tail: str = "",
) -> str:
    return f"{source}|{snapshot_id}|{table}|{symbol}|{tail}"


def _sessions() -> tuple[date, ...]:
    return (
        date(2021, 12, 29),
        date(2022, 1, 3),
        date(2022, 1, 31),
        date(2022, 2, 1),
        date(2022, 2, 28),
        date(2022, 3, 1),
    )


def _panel_row(symbol: str, day: date) -> runner.PanelRow:
    benchmark = symbol == swing.BENCHMARK_SYMBOL
    return runner.PanelRow(
        symbol=symbol,
        session_date=day,
        qfq_open=10.0,
        raw_open=10.0,
        prior_qfq_close=10.0,
        is_suspended=False,
        prior_is_st=False,
        prior_is_suspended=False,
        prior_list_status="L",
        raw_up_limit=None if benchmark else 12.0,
        raw_down_limit=None if benchmark else 8.0,
        prior_volume=10_000_000.0,
        prior_amount=1_000_000_000.0,
        current_row_hash=_hash("a"),
        prior_row_hash=_hash("b"),
    )


def test_default_is_no_database_socket_or_output(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        runner.preflight,
        "run_read_only_preflight",
        lambda *_: pytest.fail("database opened"),
    )
    monkeypatch.setattr(socket, "socket", lambda *_a, **_k: pytest.fail("socket opened"))
    monkeypatch.setattr(
        runner, "_exclusive_write", lambda *_: pytest.fail("output written")
    )
    assert runner.main(["--run-id", runner.RUN_ID]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report == {
        "database_opened": False,
        "historical_outcomes_opened": False,
        "output_written": False,
        "prospective_forward_outcomes_opened": False,
        "run_id": runner.RUN_ID,
        "status": "DRY_RUN_PLAN",
        "strategy_candidate_available": False,
    }


def test_only_exact_authorized_run_id_is_accepted() -> None:
    with pytest.raises(runner.HistoricalRunError, match="single authorized"):
        runner.main(["--run-id", f"{runner.RUN_ID}-RETRY"])


def test_git_identity_accepts_exact_lowercase_sha1_commit_and_tree(
    monkeypatch,
) -> None:
    values = iter((_git_hash("a"), _git_hash("b")))
    monkeypatch.setattr(
        runner.subprocess,
        "check_output",
        lambda *_args, **_kwargs: next(values),
    )
    assert runner._git_identity() == (_git_hash("a"), _git_hash("b"))


@pytest.mark.parametrize(
    "invalid",
    (
        "a" * 39,
        "a" * 41,
        "g" * 40,
        "A" * 40,
    ),
)
@pytest.mark.parametrize("position", (0, 1))
def test_git_identity_rejects_wrong_length_nonhex_and_uppercase(
    monkeypatch, invalid: str, position: int
) -> None:
    values = [_git_hash("a"), _git_hash("b")]
    values[position] = invalid
    outputs = iter(values)
    monkeypatch.setattr(
        runner.subprocess,
        "check_output",
        lambda *_args, **_kwargs: next(outputs),
    )
    with pytest.raises(runner.HistoricalRunError, match="lowercase Git SHA-1"):
        runner._git_identity()


def test_legacy_symbol_master_identity_is_exact_and_not_a_content_hash() -> None:
    value = _legacy_master_hash()
    assert len(value) == 85
    assert runner._legacy_symbol_master_identity(
        value,
        source="wsl2_chain_repair_20260706",
        snapshot_id="wsl2_chain_repair_20260706_195210",
        symbol="600000.SH",
    ) == value
    with pytest.raises(runner.HistoricalRunError, match="lowercase SHA-256"):
        runner._row_hash(value, "content row_hash")
    assert runner._row_hash(_hash("a"), "content row_hash") == _hash("a")


@pytest.mark.parametrize(
    ("value", "source", "snapshot_id", "symbol"),
    (
        ("x" * 85, "source", "snapshot", "600000.SH"),
        (_legacy_master_hash(source="other"), "source", "wsl2_chain_repair_20260706_195210", "600000.SH"),
        (_legacy_master_hash(snapshot_id="other"), "wsl2_chain_repair_20260706", "snapshot", "600000.SH"),
        (_legacy_master_hash(table="a_share_symbol_master"), "wsl2_chain_repair_20260706", "wsl2_chain_repair_20260706_195210", "600000.SH"),
        (_legacy_master_hash(symbol="600001.SH"), "wsl2_chain_repair_20260706", "wsl2_chain_repair_20260706_195210", "600000.SH"),
        (_legacy_master_hash(tail="20260101"), "wsl2_chain_repair_20260706", "wsl2_chain_repair_20260706_195210", "600000.SH"),
        (_legacy_master_hash(), "", "wsl2_chain_repair_20260706_195210", "600000.SH"),
        (_legacy_master_hash(), "wsl2|repair", "wsl2_chain_repair_20260706_195210", "600000.SH"),
        (_legacy_master_hash(), "wsl2_chain_repair_20260706", "", "600000.SH"),
        (_legacy_master_hash(), "wsl2_chain_repair_20260706", "snapshot|id", "600000.SH"),
        (_legacy_master_hash(), "wsl2_chain_repair_20260706", "wsl2_chain_repair_20260706_195210", ""),
        (_legacy_master_hash(), "wsl2_chain_repair_20260706", "wsl2_chain_repair_20260706_195210", "600000|SH"),
    ),
)
def test_legacy_symbol_master_identity_rejects_arbitrary_and_drifted_values(
    value: str, source: str, snapshot_id: str, symbol: str
) -> None:
    with pytest.raises(runner.HistoricalRunError, match="legacy symbol-master"):
        runner._legacy_symbol_master_identity(
            value,
            source=source,
            snapshot_id=snapshot_id,
            symbol=symbol,
        )


def test_masters_reads_and_validates_legacy_identity_components() -> None:
    class Result:
        def fetchall(self):
            return [
                (
                    "600000.SH",
                    "20100101",
                    None,
                    "wsl2_chain_repair_20260706",
                    "wsl2_chain_repair_20260706_195210",
                    _legacy_master_hash(),
                    False,
                )
            ]

    class Connection:
        def __init__(self) -> None:
            self.sql = ""

        def execute(self, sql):
            self.sql = sql
            return Result()

    connection = Connection()
    assert runner._masters(connection) == {"600000.SH": (date(2010, 1, 1), None)}
    assert "source,snapshot_id,row_hash" in connection.sql


def test_split_intervals_reset_and_purge_crossing_labels() -> None:
    intervals = runner._intervals(
        _sessions(), date(2022, 1, 1), date(2022, 3, 31)
    )
    assert intervals == (
        (date(2021, 12, 29), date(2022, 1, 3), date(2022, 2, 1)),
        (date(2022, 1, 31), date(2022, 2, 1), date(2022, 3, 1)),
    )
    assert all(entry.year == 2022 and exit_date.year == 2022 for _, entry, exit_date in intervals)


def test_bootstrap_has_fixed_nonconstant_golden_result() -> None:
    observed, p_value, lower = runner._bootstrap(
        (0.01, -0.02, 0.03, 0.04, -0.01), seed=20260819
    )
    assert observed == pytest.approx(0.01)
    assert p_value == pytest.approx(0.11948805119488051)
    assert lower == pytest.approx(-0.006)


def test_historical_pass_requires_same_variant_across_both_splits() -> None:
    def cell(variant: str, split: str, passed: bool) -> runner.CellResult:
        return runner.CellResult(
            variant,
            split,
            24,
            0,
            0.01,
            0.001,
            0.001,
            0.2,
            0.1,
            tuple((f"gate-{index}", passed) for index in range(6)),
        )

    crossed = (
        cell("SWING20", runner.GATED_SPLITS[0][0], True),
        cell("SWING20", runner.GATED_SPLITS[1][0], False),
        cell("SWING60", runner.GATED_SPLITS[0][0], False),
        cell("SWING60", runner.GATED_SPLITS[1][0], True),
    )
    assert runner._historical_status(crossed) == ("HISTORICAL_SCREENING_FAIL", ())
    passed = crossed[:2] + (
        cell("SWING60", runner.GATED_SPLITS[0][0], True),
        cell("SWING60", runner.GATED_SPLITS[1][0], True),
    )
    assert runner._historical_status(passed) == (
        "HISTORICAL_SCREENING_PASS",
        ("SWING60",),
    )


def test_evaluate_has_exact_six_gates_and_frozen_seed(monkeypatch) -> None:
    observed: dict[str, int] = {}

    def fake(values, *, seed):
        observed["seed"] = seed
        assert tuple(values) == pytest.approx((0.01, 0.01))
        return 0.01, 0.001, 0.001

    monkeypatch.setattr(runner, "_bootstrap", fake)
    result = runner._evaluate(
        swing.VARIANTS[0],
        runner.GATED_SPLITS[0],
        (0.02, 0.03),
        (0.01, 0.02),
        0,
    )
    assert observed["seed"] == 20260819
    assert tuple(name for name, _ in result.gates) == (
        "minimum_complete_interval_count",
        "zero_invalid_decisions_marks_and_accounting_failures",
        "mean_monthly_net_active_return_positive",
        "one_sided_bonferroni_p_value",
        "bonferroni_lower_bound_positive",
        "strategy_annualized_net_return_exceeds_benchmark",
    )
    assert len(result.gates) == 6


def test_synthetic_simulation_uses_shared_portfolio_and_resets(monkeypatch) -> None:
    sessions = _sessions()
    calendar = runner.preflight._accepted_calendar(sessions, _hash("c"))
    symbols = tuple(f"{600000 + index:06d}.SH" for index in range(15))

    def panel(_connection, session_date, _prior_date, requested):
        return {symbol: _panel_row(symbol, session_date) for symbol in requested}

    monkeypatch.setattr(runner, "_panel", panel)
    targets = {
        (date(2021, 12, 29), "SWING20"): runner.Target(
            date(2021, 12, 29), date(2022, 1, 3), "SWING20", symbols
        ),
        (date(2022, 1, 31), "SWING20"): runner.Target(
            date(2022, 1, 31), date(2022, 2, 1), "SWING20", symbols
        ),
    }
    strategy, benchmark, counts, invalid = runner._simulate_cell(
        object(),
        calendar,
        sessions,
        targets,
        variant_id="SWING20",
        split=("synthetic", date(2022, 1, 1), date(2022, 3, 31), 2, 1),
        slippage_bps=50.0,
    )
    assert len(strategy) == len(benchmark) == 2
    assert all(value > -1 for value in strategy + benchmark)
    assert invalid == 0
    assert sum(
        count
        for key, count in counts.items()
        if key.startswith("benchmark:buy:") and key != "benchmark:buy:zero_request"
    ) == 1


@pytest.mark.parametrize(
    "reason", ("capacity:volume", "capacity:amount", "slippage_crosses_down_limit")
)
def test_residual_sell_outside_shared_retry_lifecycle_fails_closed(reason: str) -> None:
    symbol = "600000.SH"
    result = SimpleNamespace(
        receipts=(
            SimpleNamespace(
                side="sell",
                symbol=symbol,
                requested_shares=100.0,
                filled_shares=0.0,
                reason=reason,
            ),
        ),
        portfolio=SimpleNamespace(positions={symbol: object()}),
    )
    with pytest.raises(runner.HistoricalRunError, match="shared retry lifecycle"):
        runner._new_blocked_orders({}, result, object())


def test_execute_claims_before_outcomes_and_finalizes_once(monkeypatch, tmp_path) -> None:
    database = tmp_path / "input.duckdb"
    database.write_bytes(b"frozen")
    output = tmp_path / "result.json"
    marker = tmp_path / "result.run.json"
    monkeypatch.setattr(
        runner.preflight,
        "run_read_only_preflight",
        lambda _: {"status": "PREFLIGHT_PASS"},
    )
    prepared = SimpleNamespace(code_commit=_git_hash("c"), code_tree=_git_hash("d"))
    monkeypatch.setattr(runner, "prepare_historical", lambda *_: prepared)
    monkeypatch.setattr(runner, "close_prepared", lambda value: value is prepared)

    def execute(value, _preflight):
        assert value is prepared
        assert marker.is_file()
        claimed = json.loads(marker.read_text())
        assert claimed["status"] == "CLAIMED_BEFORE_HISTORICAL_OUTCOME_ACCESS"
        return {
            "status": "HISTORICAL_SCREENING_FAIL",
            "strategy_candidate_available": False,
        }

    monkeypatch.setattr(runner, "execute_historical", execute)
    assert runner.main(
        [
            "--run-id",
            runner.RUN_ID,
            "--execute",
            "--db",
            str(database),
            "--output",
            str(output),
            "--run-marker",
            str(marker),
        ]
    ) == 0
    assert json.loads(marker.read_text())["status"] == "CONSUMED_HISTORICAL_OUTCOME_PUBLISHED"
    assert json.loads(output.read_text())["strategy_candidate_available"] is False
    with pytest.raises(runner.HistoricalRunError, match="must not preexist"):
        runner.main(
            [
                "--run-id",
                runner.RUN_ID,
                "--execute",
                "--db",
                str(database),
                "--output",
                str(output),
                "--run-marker",
                str(marker),
            ]
        )


def test_preflight_failure_does_not_consume_run(monkeypatch, tmp_path) -> None:
    database = tmp_path / "input.duckdb"
    database.write_bytes(b"frozen")
    marker = tmp_path / "blocked.run.json"
    monkeypatch.setattr(
        runner.preflight,
        "run_read_only_preflight",
        lambda _: {"status": "INPUT_BLOCKED"},
    )
    with pytest.raises(runner.HistoricalRunError, match="did not pass"):
        runner.main(
            [
                "--run-id",
                runner.RUN_ID,
                "--execute",
                "--db",
                str(database),
                "--output",
                str(tmp_path / "blocked.json"),
                "--run-marker",
                str(marker),
            ]
        )
    assert not marker.exists()


def test_post_preflight_preparation_failure_does_not_consume_run(
    monkeypatch, tmp_path
) -> None:
    database = tmp_path / "input.duckdb"
    database.write_bytes(b"frozen")
    marker = tmp_path / "prepare-blocked.run.json"
    monkeypatch.setattr(
        runner.preflight,
        "run_read_only_preflight",
        lambda _: {"status": "PREFLIGHT_PASS"},
    )
    monkeypatch.setattr(
        runner.subprocess,
        "check_output",
        lambda *_args, **_kwargs: "a" * 39,
    )
    monkeypatch.setattr(
        runner,
        "prepare_historical",
        lambda *_: runner._git_identity(),
    )
    output = tmp_path / "prepare-blocked.json"
    with pytest.raises(runner.HistoricalRunError, match="lowercase Git SHA-1"):
        runner.main(
            [
                "--run-id",
                runner.RUN_ID,
                "--execute",
                "--db",
                str(database),
                "--output",
                str(output),
                "--run-marker",
                str(marker),
            ]
        )
    assert not marker.exists()
    assert not output.exists()


def test_malformed_legacy_master_prepare_writes_no_marker_or_result(
    monkeypatch, tmp_path
) -> None:
    class Result:
        def fetchall(self):
            return [
                (
                    "600000.SH",
                    "20100101",
                    None,
                    "wsl2_chain_repair_20260706",
                    "wsl2_chain_repair_20260706_195210",
                    "x" * 85,
                    False,
                )
            ]

    class Connection:
        def execute(self, _sql):
            return Result()

    database = tmp_path / "input.duckdb"
    database.write_bytes(b"frozen")
    output = tmp_path / "malformed-master.json"
    marker = tmp_path / "malformed-master.run.json"
    monkeypatch.setattr(
        runner.preflight,
        "run_read_only_preflight",
        lambda _: {"status": "PREFLIGHT_PASS"},
    )
    monkeypatch.setattr(
        runner,
        "prepare_historical",
        lambda *_: runner._masters(Connection()),
    )
    with pytest.raises(runner.HistoricalRunError, match="row identity differs"):
        runner.main(
            [
                "--run-id",
                runner.RUN_ID,
                "--execute",
                "--db",
                str(database),
                "--output",
                str(output),
                "--run-marker",
                str(marker),
            ]
        )
    assert not marker.exists()
    assert not output.exists()


def test_panel_query_is_bounded_at_historical_cutoff() -> None:
    class Result:
        def fetchall(self):
            return [
                (
                    "600000.SH",
                    10.0,
                    10.0,
                    9.9,
                    False,
                    False,
                    False,
                    "L",
                    11.0,
                    9.0,
                    1_000_000.0,
                    100_000_000.0,
                    _hash("a"),
                    _hash("b"),
                    runner.QUALITY,
                    False,
                )
            ]

    class Connection:
        def __init__(self):
            self.sql = ""
            self.parameters = []

        def execute(self, sql, parameters):
            self.sql = sql
            self.parameters = parameters
            return Result()

    connection = Connection()
    runner._panel(
        connection,
        date(2026, 6, 30),
        date(2026, 6, 29),
        ("600000.SH",),
    )
    assert "c.trade_date<=?" in connection.sql
    assert "20260630" in connection.parameters
    assert all("2027" not in str(value) for value in connection.parameters)
