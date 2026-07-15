from __future__ import annotations

from datetime import date
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
from types import SimpleNamespace

import pytest

from quant_system.data.reader import QueryResult


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_cleanroom_us_four.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("run_cleanroom_us_four", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _mini_definition() -> dict:
    row_sha = "a" * 64
    consumed = hashlib.sha256()
    for row in _mini_rows():
        values = (
            row[0],
            row[1],
            row[2].isoformat(),
            float(row[3]).hex(),
            row[4],
            row[5],
            None,
            row[7],
            row[8],
            row[9],
            row[10],
        )
        consumed.update(
            (json.dumps(values, separators=(",", ":"), allow_nan=False) + "\n").encode()
        )
    return {
        "data_identity": {
            "row_count": 6,
            "snapshot_id": "snapshot",
            "symbols": ["GLD", "QQQ", "SPY"],
            "concat_row_sha256": hashlib.sha256((row_sha * 6).encode("ascii")).hexdigest(),
            "consumed_slice_sha256": consumed.hexdigest(),
            "rows_per_symbol": 2,
            "distinct_trade_dates": 2,
            "availability_basis": "UNKNOWN",
            "quality_status": "PASS_RETROSPECTIVE_ONLY_UNQUALIFIED_PIT",
            "conflict_flags_json": "[]",
            "synthetic_data": False,
        },
        "historical_external_replication": {
            "start_date": "2005-01-03",
            "end_date": "2005-01-04",
        },
    }


def _mini_rows() -> tuple[tuple, ...]:
    row_sha = "a" * 64
    source_sha = "b" * 64
    rows = []
    for session_date, factors in (
        (date(2005, 1, 3), {"GLD": 1.01, "QQQ": 1.02, "SPY": 1.03}),
        (date(2005, 1, 4), {"GLD": 1.04, "QQQ": 1.05, "SPY": 1.06}),
    ):
        for symbol in ("GLD", "QQQ", "SPY"):
            rows.append(
                (
                    "snapshot",
                    symbol,
                    session_date,
                    factors[symbol],
                    row_sha,
                    source_sha,
                    None,
                    "UNKNOWN",
                    "PASS_RETROSPECTIVE_ONLY_UNQUALIFIED_PIT",
                    "[]",
                    False,
                )
            )
    return tuple(rows)


def test_frozen_definition_is_strict_and_hash_bound():
    module = _load_script()
    definition, digest = module._load_definition()
    assert digest == module.DEFINITION_SHA256
    assert definition["definition_id"] == (
        "US31_US36_US41_US46_CLEANROOM_MIGRATION_REPLAY_V1_20260715"
    )
    assert definition["lineage_controls"]["legacy_python_permitted_as_implementation_input"] is False
    assert definition["data_identity"]["strict_pit_eligible"] is False
    assert definition["data_identity"]["consumed_slice_sha256"] == (
        "785bc3f3ef7286fe9ef15b4f17bb1b5eddaea84150e4b83ce54682f072f75e1c"
    )


def test_definition_freezes_exact_four_text_only_rules():
    module = _load_script()
    definition, _ = module._load_definition()
    assert {
        item["strategy_id"]: item["target_weights"]
        for item in definition["strategies"]
    } == {
        "US31": {"GLD": 0.5, "SPY": 0.5},
        "US36": {"QQQ": 0.5, "SPY": 0.5},
        "US41": {
            "GLD": 0.3333333333333333,
            "QQQ": 0.3333333333333333,
            "SPY": 0.3333333333333333,
        },
        "US46": {"GLD": 0.5, "QQQ": 0.5},
    }
    assert definition["portfolio_contract"]["rebalance_interval_sessions"] == 63
    assert definition["portfolio_contract"]["cost_bps"] == [10, 50]
    assert definition["portfolio_contract"]["initialization_cost_bps"] == 0
    assert definition["mechanical_resolutions"]["rebalance_anchor"] == "per_interval"
    assert definition["mechanical_resolutions"]["common_session_panel"] == (
        "global_SPY_QQQ_GLD"
    )
    assert definition["inference"] == {
        "primary_series": "daily arithmetic net excess return",
        "moving_block_sessions": 20,
        "bootstrap_draws": 20000,
        "prng": "NumPy Generator with PCG64",
        "historical_seed_base": 680031364146,
        "seed_formula": (
            "historical_seed_base + 10 * strategy_order_index + comparator_order_index"
        ),
        "null_centering": "subtract observed sample mean before resampling",
        "one_sided_p_value": (
            "(1 + count(centered_bootstrap_mean >= observed_uncentered_mean)) / "
            "(bootstrap_draws + 1)"
        ),
        "quantile_method": "linear",
        "look_alpha": 0.025,
        "test_count": 8,
        "holm_order": "raw p ascending; ties by strategy order then comparator order",
        "holm_threshold": "look_alpha / (8 - rank + 1)",
        "holm_adjusted_p": "max over j<=rank of min(1, (8-j+1) * p_(j))",
        "holm_lower_bound": (
            "observed_mean - quantile(centered_bootstrap_means, "
            "1-threshold, method=linear)"
        ),
        "strategy_pass_rule": (
            "both comparator tests have positive observed mean, adjusted_p <= "
            "look_alpha, and lower_bound > 0"
        ),
    }
    assert [item["sha256"] for item in definition["text_sources"]] == [
        "95e6f42e7d711c523b83b1c36a5e24ab1e6c635869abd7119a9033b86011bca4",
        "8b00b22c6193bb12d2eeb88697b4cd574fc3c186d7aa6075d42e91333c018294",
        "8b5680fde7e05b3c8ae44cb143d9d1c0d59ab9a83c7eebc9e34a44f3fdeb7888",
        "ae2b1c8b2c41b43cca6bb6f5625084c21051d8e47e18b7cdc3da54ff65b8378f",
    ]


def test_default_path_opens_no_database_socket_or_output(monkeypatch, capsys):
    module = _load_script()
    monkeypatch.setattr(module, "query", lambda *args, **kwargs: pytest.fail("database opened"))
    monkeypatch.setattr(
        module,
        "_publish",
        lambda *args, **kwargs: pytest.fail("output written"),
    )
    monkeypatch.setattr(
        socket,
        "socket",
        lambda *args, **kwargs: pytest.fail("socket opened"),
    )
    assert module.main([]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "database_opened": False,
        "definition_sha256": module.DEFINITION_SHA256,
        "network_used": False,
        "output_written": False,
        "status": "VALIDATE_DEFINITION_ONLY",
    }


def test_panel_reader_locks_shape_order_quality_and_slice_hash(monkeypatch, tmp_path):
    module = _load_script()
    result = QueryResult(module.EXPECTED_COLUMNS, _mini_rows(), False)
    monkeypatch.setattr(module, "query", lambda *args, **kwargs: result)
    panel = module._load_panel(tmp_path / "unused.duckdb", _mini_definition())
    assert panel == (
        (date(2005, 1, 3), (("GLD", 1.01), ("QQQ", 1.02), ("SPY", 1.03))),
        (date(2005, 1, 4), (("GLD", 1.04), ("QQQ", 1.05), ("SPY", 1.06))),
    )


@pytest.mark.parametrize(
    "row_index,column_index,bad_value,match",
    [
        (0, 1, "BAD", "symbol or trade-date"),
        (0, 3, float("nan"), "finite and positive"),
        (3, 3, 9.99, "actual consumed source-slice hash changed"),
        (0, 4, "0" * 64, "row hash changed"),
        (3, 5, "c" * 64, "actual consumed source-slice hash changed"),
        (0, 6, "2026-01-01", "quality boundary"),
        (0, 9, "[\"conflict\"]", "quality boundary"),
        (0, 10, True, "quality boundary"),
    ],
)
def test_panel_reader_fails_closed_on_identity_drift(
    monkeypatch,
    tmp_path,
    row_index,
    column_index,
    bad_value,
    match,
):
    module = _load_script()
    rows = [list(row) for row in _mini_rows()]
    rows[row_index][column_index] = bad_value
    result = QueryResult(module.EXPECTED_COLUMNS, tuple(tuple(row) for row in rows), False)
    monkeypatch.setattr(module, "query", lambda *args, **kwargs: result)
    with pytest.raises(module.CleanroomReplayError, match=match):
        module._load_panel(tmp_path / "unused.duckdb", _mini_definition())


def test_panel_reader_rejects_missing_rows_before_simulation(monkeypatch, tmp_path):
    module = _load_script()
    result = QueryResult(module.EXPECTED_COLUMNS, _mini_rows()[:-1], False)
    monkeypatch.setattr(module, "query", lambda *args, **kwargs: result)
    with pytest.raises(module.CleanroomReplayError, match="row count changed"):
        module._load_panel(tmp_path / "unused.duckdb", _mini_definition())


def test_atomic_publish_is_non_overwriting(tmp_path):
    module = _load_script()
    output = tmp_path / "result.json"
    digest, sidecar = module._publish({"finite": 1.0}, output)
    assert hashlib.sha256(output.read_bytes()).hexdigest() == digest
    assert sidecar.read_text(encoding="ascii") == f"{digest}  result.json\n"
    with pytest.raises(module.CleanroomReplayError, match="already exists"):
        module._publish({"finite": 2.0}, output)


def test_git_identity_accepts_sha1_and_sha256_repositories(monkeypatch):
    module = _load_script()

    def fake_run(args, **kwargs):
        del kwargs
        if args[1:] == ["status", "--porcelain=v1"]:
            return SimpleNamespace(stdout="")
        if args[1:] == ["rev-parse", "HEAD"]:
            return SimpleNamespace(stdout=f"{'a' * fake_run.object_id_length}\n")
        raise AssertionError(args)

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    for length in (40, 64):
        fake_run.object_id_length = length
        assert module._git_identity() == "a" * length


def test_git_identity_rejects_dirty_or_invalid_source(monkeypatch):
    module = _load_script()
    responses = iter(
        (
            SimpleNamespace(stdout=" M pyproject.toml\n"),
            SimpleNamespace(stdout=f"{'a' * 40}\n"),
        )
    )
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: next(responses))
    with pytest.raises(module.CleanroomReplayError, match="clean committed worktree"):
        module._git_identity()
