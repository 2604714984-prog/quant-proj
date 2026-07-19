from __future__ import annotations

from datetime import date, timedelta
import importlib.util
import json
import os
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "scripts/run_us_spy_session_decomposition_once.py"
DEFINITION = ROOT / "research/definitions/us_spy_session_decomposition_v1.json"
SPEC = importlib.util.spec_from_file_location("session_decomposition_runner", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


def _bars(count: int = 30, overnight: float = 1.01, intraday: float = 1.0):
    rows = []
    prior_close = 100.0
    for index in range(count):
        raw_open = prior_close * (overnight if index else 1.0)
        raw_close = raw_open * intraday
        rows.append(
            runner.Bar(
                date(2020, 1, 1) + timedelta(days=index),
                raw_open,
                raw_close,
                raw_open,
                raw_close,
            )
        )
        prior_close = raw_close
    return tuple(rows)


def test_overnight_and_intraday_accounts_isolate_the_frozen_session() -> None:
    bars = _bars(30, overnight=1.01, intraday=1.0)
    overnight = runner.simulate(bars, "B2_SPY_OVERNIGHT", 0)
    intraday = runner.simulate(bars, "B3_SPY_INTRADAY", 0)

    assert overnight["observation_count"] == 29
    assert overnight["cumulative_net_return"] > 0.30
    assert intraday["observation_count"] == 30
    assert intraday["cumulative_net_return"] == pytest.approx(0.0)


def test_costs_and_whole_shares_reduce_both_daily_accounts() -> None:
    bars = _bars(10, overnight=1.001, intraday=1.001)
    for account in ("B2_SPY_OVERNIGHT", "B3_SPY_INTRADAY"):
        gross = runner.simulate(bars, account, 0)
        net = runner.simulate(bars, account, 15)
        assert net["cumulative_net_return"] < gross["cumulative_net_return"]
        assert net["whole_share_trade_count"] == 2 * net["observation_count"]


def test_exact_five_and_fifteen_bps_cash_ledgers() -> None:
    assert runner._trade(40_000.0, 100.0, 1.0, 5 / 2 / 10_000) == pytest.approx(
        39_980.05
    )
    assert runner._trade(40_000.0, 100.0, 1.0, 15 / 2 / 10_000) == pytest.approx(
        39_940.15
    )


def test_adjusted_ratio_preserves_split_economics() -> None:
    bars = (
        runner.Bar(date(2020, 1, 2), 100.0, 100.0, 50.0, 50.0),
        runner.Bar(date(2020, 1, 3), 50.0, 50.0, 50.0, 50.0),
    )
    overnight = runner.simulate(bars, "B2_SPY_OVERNIGHT", 0)
    assert overnight["observation_count"] == 1
    assert overnight["cumulative_net_return"] == pytest.approx(0.0)


def test_segmented_combined_does_not_trade_across_split_boundary() -> None:
    validation = (
        runner.Bar(date(2017, 12, 28), 100.0, 100.0, 100.0, 100.0),
        runner.Bar(date(2017, 12, 29), 100.0, 100.0, 100.0, 100.0),
    )
    holdout = (
        runner.Bar(date(2018, 1, 2), 1_000.0, 1_000.0, 1_000.0, 1_000.0),
        runner.Bar(date(2018, 1, 3), 1_000.0, 1_000.0, 1_000.0, 1_000.0),
    )
    naive = runner.simulate(validation + holdout, "B2_SPY_OVERNIGHT", 0)
    segmented = runner.simulate_segmented(
        (validation, holdout), "B2_SPY_OVERNIGHT", 0
    )
    assert naive["cumulative_net_return"] > 8.0
    assert segmented["cumulative_net_return"] == pytest.approx(0.0)
    assert segmented["observation_count"] == 2


def test_buy_hold_uses_one_entry_and_one_liquidation() -> None:
    result = runner.simulate(
        _bars(20, overnight=1.001, intraday=1.002), "B1_SPY_BUY_HOLD", 5
    )
    assert result["whole_share_trade_count"] == 2
    assert result["observation_count"] == 20
    assert result["cumulative_net_return"] > 0.0


def test_duplicates_nonfinite_and_unknown_contracts_fail_closed() -> None:
    bars = list(_bars(3))
    bars[1] = runner.Bar(bars[0].session_date, 1.0, 1.0, 1.0, 1.0)
    with pytest.raises(runner.SessionDecompositionError, match="strictly increasing"):
        runner.simulate(bars, "B2_SPY_OVERNIGHT", 0)
    with pytest.raises(runner.SessionDecompositionError, match="positive and finite"):
        runner.Bar(date(2020, 1, 1), float("nan"), 1.0, 1.0, 1.0)
    with pytest.raises(runner.SessionDecompositionError, match="unknown account"):
        runner.simulate(_bars(), "UNKNOWN", 0)


def _metric(cagr: float, contribution: float | None = 0.3):
    return {"cagr": cagr, "maximum_positive_year_contribution": contribution}


def _periods(overnight: float, intraday: float, contribution: float | None = 0.3):
    output = {}
    for split in ("validation", "retrospective_holdout", "combined_validation_holdout"):
        output[split] = {}
        for cost in ("5", "15"):
            output[split][cost] = {
                "B2_SPY_OVERNIGHT": _metric(overnight, contribution),
                "B3_SPY_INTRADAY": _metric(intraday, contribution),
            }
    return output


@pytest.mark.parametrize(
    ("overnight", "intraday", "suffix"),
    [
        (0.1, -0.1, "OVERNIGHT_PASS_EXTERNAL_REVIEW"),
        (-0.1, 0.1, "INTRADAY_PASS_EXTERNAL_REVIEW"),
        (0.1, 0.1, "BOTH_PASS_EXTERNAL_REVIEW"),
        (-0.1, -0.1, "FAIL"),
    ],
)
def test_adjudication_is_mechanical(overnight: float, intraday: float, suffix: str) -> None:
    outcome = runner.adjudicate(_periods(overnight, intraday), 0)
    assert outcome["status"].endswith(suffix)
    assert outcome["specialists"]["B2_SPY_OVERNIGHT"]["gates_total"] == 7


def test_nonpositive_year_pool_fails_concentration_without_input_block() -> None:
    outcome = runner.adjudicate(_periods(-0.1, -0.1, None), 0)
    assert outcome["status"] == "RETROSPECTIVE_SESSION_DECOMPOSITION_FAIL"
    assert outcome["specialists"]["B2_SPY_OVERNIGHT"]["gates"][5]["passed"] is False


def test_concentration_exact_boundary_passes_and_above_boundary_fails() -> None:
    exact = runner.adjudicate(_periods(0.1, -0.1, 0.50), 0)
    above = runner.adjudicate(_periods(0.1, -0.1, 0.5000001), 0)
    assert exact["specialists"]["B2_SPY_OVERNIGHT"]["gates"][5]["passed"] is True
    assert above["specialists"]["B2_SPY_OVERNIGHT"]["gates"][5]["passed"] is False


def test_nonfinite_metrics_fail_closed_instead_of_passing() -> None:
    outcome = runner.adjudicate(_periods(float("inf"), float("inf"), float("-inf")), 0)
    assert outcome == {"status": "INPUT_BLOCKED", "specialists": {}}


@pytest.mark.parametrize("data_failures", [False, True, -1, 1.5, "0"])
def test_data_failure_count_requires_nonnegative_exact_integer(data_failures) -> None:
    assert runner.adjudicate(_periods(0.1, 0.1), data_failures) == {
        "status": "INPUT_BLOCKED",
        "specialists": {},
    }


def test_annual_contribution_uses_dollar_pnl_and_empty_pool_is_null() -> None:
    dates = (date(2020, 1, 1), date(2020, 12, 31), date(2021, 12, 31))
    share, _returns, pnl = runner._annual_contribution((0.10, 0.0, 0.10), dates, 100.0)
    assert pnl == pytest.approx({"2020": 10.0, "2021": 11.0})
    assert share == pytest.approx(11.0 / 21.0)
    empty, _returns, pnl = runner._annual_contribution((-0.1, -0.1), dates[:2], 100.0)
    assert empty is None
    assert pnl["2020"] < 0.0


def test_definition_freezes_single_decomposition_without_promotion() -> None:
    definition = json.loads(DEFINITION.read_text(encoding="utf-8"))
    assert runner._sha256(DEFINITION) == runner.DEFINITION_SHA256
    assert definition["research_id"] == runner.RESEARCH_ID
    assert definition["input_identity"]["required_snapshot_rows"] == 8418
    assert tuple(definition["specialist_gates"]["items"]) == runner.GATE_LABELS
    assert definition["interpretation"]["no_parameter_selection"] is True
    assert "no B1 holding period or B2 overnight interval crossing" in definition[
        "execution"
    ]["split_boundary"]
    assert definition["one_use"]["after_durable_claim"].startswith("Read price rows")
    assert not any(definition["boundaries"].values())


def test_default_is_no_outcome_dry_run(monkeypatch, capsys) -> None:
    monkeypatch.setattr(runner, "_run", lambda *_args: pytest.fail("dry run opened input"))
    assert runner.main([]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "database_opened": False,
        "files_written": False,
        "research_id": runner.RESEARCH_ID,
        "status": "DRY_RUN_NO_OUTCOME",
        "strategy_candidate_available": False,
    }


def test_strict_json_rejects_duplicate_and_nonfinite(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"a":1,"a":2}', encoding="utf-8")
    with pytest.raises(runner.SessionDecompositionError, match="duplicate JSON key"):
        runner._strict_json(duplicate)
    nonfinite = tmp_path / "nonfinite.json"
    nonfinite.write_text('{"a":NaN}', encoding="utf-8")
    with pytest.raises(runner.SessionDecompositionError, match="nonfinite JSON"):
        runner._strict_json(nonfinite)


def test_definition_hash_rejects_cost_split_or_boundary_mutation(
    monkeypatch, tmp_path: Path
) -> None:
    mutated = json.loads(DEFINITION.read_text(encoding="utf-8"))
    mutated["costs"]["primary_round_trip_bps"] = 999
    mutated["splits"]["validation"] = ["1900-01-01", "1900-01-02"]
    mutated["boundaries"]["strategy_candidate_available"] = True
    path = tmp_path / "definition.json"
    path.write_text(json.dumps(mutated), encoding="utf-8")
    monkeypatch.setattr(runner, "DEFINITION", path)
    with pytest.raises(runner.SessionDecompositionError, match="definition bytes differ"):
        runner._definition("a" * 64)


def _context():
    return (
        "b" * 40,
        "c" * 40,
        {"definition": "d" * 64, "runner": "e" * 64, "tests": "f" * 64},
    )


def _claim(database: Path, expected_sha256: str):
    commit, tree, files = _context()
    return {
        "schema_version": "us-spy-session-decomposition-run-v1",
        "research_id": runner.RESEARCH_ID,
        "status": "CLAIMED_RETROSPECTIVE_DIAGNOSTIC_RUN",
        "definition_commit": commit,
        "definition_tree": tree,
        "files_sha256": files,
        "database_filename": database.name,
        "expected_database_sha256": expected_sha256,
        "claimed_at_utc": "2026-07-20T00:00:00+00:00",
        "strategy_candidate_available": False,
    }


def _complete_metric(observations: int, trades: int):
    return {
        "observation_count": observations,
        "cumulative_net_return": 0.0,
        "cagr": -0.01,
        "annualized_volatility": 0.1,
        "maximum_drawdown": -0.1,
        "calmar": -0.1,
        "positive_observation_fraction": 0.4,
        "maximum_positive_year_contribution": 0.3,
        "maximum_positive_observation_contribution": 0.2,
        "whole_share_trade_count": trades,
        "annual_returns": {"2020": -0.01},
        "annual_pnl_usd": {"2020": -400.0},
    }


def _complete_periods():
    periods = {}
    for split, rows in runner.EXPECTED_SPLIT_ROWS.items():
        observations = {
            "B1_SPY_BUY_HOLD": rows,
            "B2_SPY_OVERNIGHT": rows - 1,
            "B3_SPY_INTRADAY": rows,
        }
        if split == "combined_validation_holdout":
            observations["B2_SPY_OVERNIGHT"] = 4145
        periods[split] = {}
        for cost in runner.COSTS:
            periods[split][str(cost)] = {}
            for account in runner.ACCOUNTS:
                trades = (
                    4
                    if account == "B1_SPY_BUY_HOLD" and split == "combined_validation_holdout"
                    else 2
                    if account == "B1_SPY_BUY_HOLD"
                    else 2 * observations[account]
                )
                periods[split][str(cost)][account] = _complete_metric(
                    observations[account], trades
                )
    return periods


def _complete_result(database: Path, expected_sha256: str):
    commit, tree, files = _context()
    periods = _complete_periods()
    adjudication = runner.adjudicate(periods, 0)
    return {
        "schema_version": "us-spy-session-decomposition-result-v1",
        "research_id": runner.RESEARCH_ID,
        "status": adjudication["status"],
        "classification": runner.CLASSIFICATION,
        "claim_sha256": runner.hashlib.sha256(
            runner._canonical(_claim(database, expected_sha256))
        ).hexdigest(),
        "repository_identity": {"commit": commit, "tree": tree, "files_sha256": files},
        "input_identity": {
            "database_filename": database.name,
            "database_sha256": expected_sha256,
            "database_sha256_before": expected_sha256,
            "database_sha256_after": expected_sha256,
            "database_unchanged": True,
            "table": runner.TABLE,
            "snapshot_id": runner.SNAPSHOT_ID,
            "symbol": runner.SYMBOL,
            "cutoff_inclusive": runner.CUTOFF.isoformat(),
            "schema": [
                ["trade_date", "DATE"],
                ["open", "DOUBLE"],
                ["close", "DOUBLE"],
                ["adj_open", "DOUBLE"],
                ["adj_close", "DOUBLE"],
            ],
            "snapshot_row_count": runner.EXPECTED_SNAPSHOT_ROWS,
            "consumed_row_count": runner.EXPECTED_CONSUMED_ROWS,
            "observed_date_start": "1993-01-29",
            "observed_date_end": "2026-07-10",
            "duplicate_date_count": 0,
            "split_row_counts": runner.EXPECTED_SPLIT_ROWS,
            "database_descriptor_identity": {
                "device": 1,
                "inode": 2,
                "size": 3,
                "mtime_ns": 4,
            },
            "missing_or_nonfinite_count": 0,
            "consumed_rows_sha256": "1" * 64,
        },
        "dominant_session_zero_cost_combined": {
            "status": "TIE",
            "overnight_log_return": 0.0,
            "intraday_log_return": 0.0,
        },
        "periods": periods,
        "adjudication": adjudication,
        "boundaries": runner._boundaries(),
    }


def test_combined_result_contract_locks_4145_overnight_observations() -> None:
    periods = _complete_periods()
    runner._validate_periods(periods)
    assert periods["combined_validation_holdout"]["0"]["B2_SPY_OVERNIGHT"][
        "observation_count"
    ] == 4145
    periods["combined_validation_holdout"]["0"]["B2_SPY_OVERNIGHT"][
        "observation_count"
    ] = 4146
    with pytest.raises(runner.SessionDecompositionError, match="observation count differs"):
        runner._validate_periods(periods)


def _mock_recovery_context(monkeypatch, database: Path) -> None:
    monkeypatch.setattr(runner, "_execution_identity", lambda *_args: _context())

    def preflight(*_args):
        descriptor = os.open(database, os.O_RDONLY)
        captured = os.fstat(descriptor)
        return descriptor, {
            "database_descriptor_identity": {
                "device": captured.st_dev,
                "inode": captured.st_ino,
                "size": captured.st_size,
                "mtime_ns": captured.st_mtime_ns,
            }
        }

    monkeypatch.setattr(runner, "_preflight_input", preflight)
    monkeypatch.setattr(runner, "_verify_database_capture", lambda *_args: None)


def test_preflight_failure_does_not_claim_or_consume_one_use(
    monkeypatch, tmp_path: Path
) -> None:
    result = tmp_path / "result.json"
    receipt = tmp_path / "receipt.json"
    database = tmp_path / "input.duckdb"
    database.write_bytes(b"not-a-database")
    monkeypatch.setattr(runner, "RESULT", result)
    monkeypatch.setattr(runner, "RECEIPT", receipt)
    monkeypatch.setattr(runner, "_execution_identity", lambda *_args: _context())
    monkeypatch.setattr(
        runner,
        "_preflight_input",
        lambda *_args: (_ for _ in ()).throw(runner.SessionDecompositionError("input")),
    )
    with pytest.raises(runner.SessionDecompositionError, match="input"):
        runner._run(database, "a" * 64)
    assert not result.exists()
    assert not receipt.exists()


def test_price_rows_are_read_only_after_durable_claim(monkeypatch, tmp_path: Path) -> None:
    result = tmp_path / "result.json"
    receipt = tmp_path / "receipt.json"
    database = tmp_path / "input.duckdb"
    database.write_bytes(b"input")
    descriptor = os.open(database, os.O_RDONLY)
    monkeypatch.setattr(runner, "RESULT", result)
    monkeypatch.setattr(runner, "RECEIPT", receipt)
    monkeypatch.setattr(runner, "_execution_identity", lambda *_args: _context())
    monkeypatch.setattr(runner, "_preflight_input", lambda *_args: (descriptor, {}))

    def after_claim(*_args):
        assert receipt.exists()
        raise runner.SessionDecompositionError("price read stopped")

    monkeypatch.setattr(runner, "_qualify_claimed_input", after_claim)
    outcome, _final, _claim_payload = runner._run(database, "a" * 64)
    assert outcome["status"] == "EXECUTION_ERROR_CONSUMED"
    assert json.loads(receipt.read_text())["status"] == (
        "CLAIMED_RETROSPECTIVE_DIAGNOSTIC_RUN"
    )


def test_database_symlink_and_preflight_replacement_are_rejected(
    monkeypatch, tmp_path: Path
) -> None:
    target = tmp_path / "target.duckdb"
    target.write_bytes(b"captured")
    link = tmp_path / "link.duckdb"
    link.symlink_to(target)
    expected = runner.hashlib.sha256(b"captured").hexdigest()
    with pytest.raises(runner.SessionDecompositionError, match="without following links"):
        runner._preflight_input(link, expected)

    database = tmp_path / "replace.duckdb"
    replacement = tmp_path / "replacement.duckdb"
    database.write_bytes(b"captured")
    replacement.write_bytes(b"replacement")

    def replace_while_captured(_descriptor):
        replacement.replace(database)
        return {}

    monkeypatch.setattr(runner, "_database_metadata", replace_while_captured)
    with pytest.raises(runner.SessionDecompositionError, match="path was replaced"):
        runner._preflight_input(database, expected)


def test_definition_and_output_json_reject_symlinks(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "definition.json"
    target.write_bytes(DEFINITION.read_bytes())
    link = tmp_path / "definition-link.json"
    link.symlink_to(target)
    monkeypatch.setattr(runner, "DEFINITION", link)
    with pytest.raises(runner.SessionDecompositionError, match="capture regular file"):
        runner._definition("a" * 64)
    with pytest.raises(runner.SessionDecompositionError, match="capture regular file"):
        runner._capture_json(link, require_canonical=True)


def test_descriptor_capture_rejects_path_replacement(monkeypatch, tmp_path: Path) -> None:
    path = tmp_path / "captured.json"
    replacement = tmp_path / "replacement.json"
    path.write_bytes(b'{"a":1}\n')
    replacement.write_bytes(b'{"a":2}\n')
    original_read = runner.os.read
    replaced = False

    def replacing_read(descriptor, size):
        nonlocal replaced
        block = original_read(descriptor, size)
        if block and not replaced:
            replacement.replace(path)
            replaced = True
        return block

    monkeypatch.setattr(runner.os, "read", replacing_read)
    with pytest.raises(runner.SessionDecompositionError, match="path was replaced"):
        runner._capture_regular_file(path)


def test_partial_complete_result_is_discarded_as_consumed_error(
    monkeypatch, tmp_path: Path
) -> None:
    result_path = tmp_path / "result.json"
    receipt_path = tmp_path / "receipt.json"
    database = tmp_path / "input.duckdb"
    database.write_bytes(b"input")
    expected = "a" * 64
    monkeypatch.setattr(runner, "RESULT", result_path)
    monkeypatch.setattr(runner, "RECEIPT", receipt_path)
    _mock_recovery_context(monkeypatch, database)
    claim = _claim(database, expected)
    partial_result = _complete_result(database, expected)
    partial_bytes = runner._canonical(partial_result)
    result_path.write_bytes(partial_bytes)
    receipt_path.write_bytes(runner._canonical(claim))
    recovered_result, recovered_receipt = runner._recover_partial_publication(
        database, expected
    )
    assert recovered_result["status"] == "EXECUTION_ERROR_CONSUMED"
    assert recovered_result["reason_class"] == "InterruptedAfterClaim"
    assert json.loads(result_path.read_text()) == recovered_result
    assert recovered_receipt["recovered_partial_publication"] is True
    assert recovered_receipt["discarded_partial_result_sha256"] == (
        runner.hashlib.sha256(partial_bytes).hexdigest()
    )
    assert recovered_receipt["claim_sha256"] == runner.hashlib.sha256(
        runner._canonical(claim)
    ).hexdigest()
    assert recovered_receipt["claimed_at_utc"] == claim["claimed_at_utc"]
    assert json.loads(receipt_path.read_text())["status"] == (
        "CONSUMED_RETROSPECTIVE_DIAGNOSTIC_RUN"
    )


def test_recovery_discards_minimal_or_forged_result(monkeypatch, tmp_path: Path) -> None:
    result_path = tmp_path / "result.json"
    receipt_path = tmp_path / "receipt.json"
    database = tmp_path / "input.duckdb"
    database.write_bytes(b"input")
    expected = "a" * 64
    monkeypatch.setattr(runner, "RESULT", result_path)
    monkeypatch.setattr(runner, "RECEIPT", receipt_path)
    _mock_recovery_context(monkeypatch, database)
    receipt_path.write_bytes(runner._canonical(_claim(database, expected)))
    forged_bytes = runner._canonical(
        {
            "research_id": runner.RESEARCH_ID,
            "status": "RETROSPECTIVE_SESSION_DECOMPOSITION_BOTH_PASS_EXTERNAL_REVIEW",
            "repository_identity": {},
        }
    )
    result_path.write_bytes(forged_bytes)
    result, receipt = runner._recover_partial_publication(database, expected)
    assert result["status"] == "EXECUTION_ERROR_CONSUMED"
    assert receipt["discarded_partial_result_sha256"] == runner.hashlib.sha256(
        forged_bytes
    ).hexdigest()


def test_result_is_bound_to_exact_claim_digest(tmp_path: Path) -> None:
    database = tmp_path / "input.duckdb"
    expected = "a" * 64
    claim = _claim(database, expected)
    result = _complete_result(database, expected)
    result["claim_sha256"] = "0" * 64
    with pytest.raises(runner.SessionDecompositionError, match="identity differs"):
        runner._validate_result(result, claim, database, expected)


def test_receipt_finalization_rechecks_published_result(monkeypatch, tmp_path: Path) -> None:
    receipt_path = tmp_path / "receipt.json"
    result_path = tmp_path / "result.json"
    database = tmp_path / "input.duckdb"
    expected = "a" * 64
    claim = _claim(database, expected)
    result_bytes = runner._canonical(_complete_result(database, expected))
    receipt_path.write_bytes(runner._canonical(claim))
    result_path.write_bytes(result_bytes)
    monkeypatch.setattr(runner, "RESULT", result_path)
    original_write = runner._exclusive_write

    def replace_after_temp_write(path, payload):
        original_write(path, payload)
        if ".final-" in path.name:
            result_path.write_bytes(b'{"forged":true}\n')

    monkeypatch.setattr(runner, "_exclusive_write", replace_after_temp_write)
    with pytest.raises(runner.SessionDecompositionError, match="published result changed"):
        runner._finalize_claim(
            receipt_path,
            runner._canonical({"status": "done"}),
            claim,
            result_bytes,
        )
    assert json.loads(receipt_path.read_text())["status"] == (
        "CLAIMED_RETROSPECTIVE_DIAGNOSTIC_RUN"
    )


def test_claim_without_result_recovers_as_consumed_error(monkeypatch, tmp_path: Path) -> None:
    result_path = tmp_path / "result.json"
    receipt_path = tmp_path / "receipt.json"
    database = tmp_path / "input.duckdb"
    database.write_bytes(b"input")
    expected = "a" * 64
    monkeypatch.setattr(runner, "RESULT", result_path)
    monkeypatch.setattr(runner, "RECEIPT", receipt_path)
    _mock_recovery_context(monkeypatch, database)
    receipt_path.write_bytes(runner._canonical(_claim(database, expected)))
    result, receipt = runner._recover_partial_publication(database, expected)
    assert result["status"] == "EXECUTION_ERROR_CONSUMED"
    assert result["reason_class"] == "InterruptedAfterClaim"
    assert receipt["status"] == "CONSUMED_RETROSPECTIVE_DIAGNOSTIC_RUN"
    assert result_path.exists()


def test_recovery_rejects_symlinked_result(monkeypatch, tmp_path: Path) -> None:
    result_path = tmp_path / "result.json"
    result_target = tmp_path / "result-target.json"
    receipt_path = tmp_path / "receipt.json"
    database = tmp_path / "input.duckdb"
    database.write_bytes(b"input")
    expected = "a" * 64
    monkeypatch.setattr(runner, "RESULT", result_path)
    monkeypatch.setattr(runner, "RECEIPT", receipt_path)
    _mock_recovery_context(monkeypatch, database)
    receipt_path.write_bytes(runner._canonical(_claim(database, expected)))
    result_target.write_bytes(runner._canonical(_complete_result(database, expected)))
    result_path.symlink_to(result_target)
    with pytest.raises(runner.SessionDecompositionError, match="capture regular file"):
        runner._recover_partial_publication(database, expected)


def test_main_preserves_database_symlink_for_nofollow_check(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "input.duckdb"
    target.write_bytes(b"input")
    link = tmp_path / "input-link.duckdb"
    link.symlink_to(target)

    def inspect(database, _expected):
        assert database.is_symlink()
        raise runner.SessionDecompositionError("symlink preserved")

    monkeypatch.setattr(runner, "_recover_partial_publication", inspect)
    with pytest.raises(runner.SessionDecompositionError, match="symlink preserved"):
        runner.main(
            [
                "--execute",
                "--database",
                str(link),
                "--expected-database-sha256",
                "a" * 64,
            ]
        )


def test_runner_is_read_only_and_has_no_network_path() -> None:
    source = RUNNER_PATH.read_text(encoding="utf-8")
    assert "read_only=True" in source
    assert "requests" not in source
    assert "urlopen" not in source
    assert "INSERT " not in source
    assert "UPDATE " not in source
