from __future__ import annotations

from datetime import date, timedelta
import importlib.util
import json
from pathlib import Path
import sys
import math

import pytest

from quant_system.research.us_spy_200d_trend_cash import (
    DailyBar,
    MonthlyInterval,
    SPYTrendCashError,
    adjudicate,
    build_monthly_intervals,
    combine_outcomes,
    evaluate,
    select_split,
)


ROOT = Path(__file__).resolve().parents[1]
DEFINITION = ROOT / "research/definitions/us_spy_200d_trend_cash_retrospective_baseline_v1.json"
RUNNER_PATH = ROOT / "scripts/run_us_spy_200d_trend_cash_result.py"
RUNNER_SPEC = importlib.util.spec_from_file_location("spy_baseline_runner", RUNNER_PATH)
assert RUNNER_SPEC is not None and RUNNER_SPEC.loader is not None
runner = importlib.util.module_from_spec(RUNNER_SPEC)
sys.modules[RUNNER_SPEC.name] = runner
RUNNER_SPEC.loader.exec_module(runner)


def _bars(count: int = 260) -> tuple[DailyBar, ...]:
    first = date(2020, 1, 1)
    return tuple(
        DailyBar(first + timedelta(days=index), 100.0 + index, 100.0 + index)
        for index in range(count)
    )


def test_monthly_intervals_use_inclusive_close_sma_and_next_open_returns() -> None:
    intervals = build_monthly_intervals(_bars(), date(2020, 12, 31))

    assert intervals
    first = intervals[0]
    assert first.decision_date == date(2020, 7, 31)
    assert first.entry_date == date(2020, 8, 1)
    assert first.exit_date == date(2020, 9, 1)
    assert first.trend_on is True
    assert first.spy_return == pytest.approx(31.0 / 313.0)


def test_split_purges_interval_crossing_a_boundary() -> None:
    intervals = build_monthly_intervals(_bars(350), date(2021, 12, 31))
    selected = select_split(intervals, date(2020, 9, 1), date(2020, 10, 31))

    assert len(selected) == 1
    assert selected[0].entry_date == date(2020, 9, 1)
    assert selected[0].exit_date == date(2020, 10, 1)


def test_costs_include_entry_transitions_and_final_liquidation() -> None:
    intervals = build_monthly_intervals(_bars(), date(2020, 12, 31))[:3]
    outcome = evaluate(intervals, "B1_SPY_BUY_HOLD", 15)
    cash = evaluate(intervals, "B0_CASH", 15)

    assert outcome["one_way_turnover"] == 2.0
    assert outcome["state_transition_count"] == 0
    assert outcome["cost_drag"] > 0.0
    gross = evaluate(intervals, "B1_SPY_BUY_HOLD", 0)
    assert outcome["cumulative_net_return"] == pytest.approx(
        (1.0 + gross["cumulative_net_return"]) * (1.0 - 0.0015) ** 2 - 1.0
    )
    assert cash["cumulative_net_return"] == 0.0
    assert cash["one_way_turnover"] == 0.0


def test_combined_outcomes_recomputes_full_metrics_from_return_series() -> None:
    intervals = (
        MonthlyInterval(date(2020, 1, 31), date(2020, 2, 1), date(2020, 3, 1), 0.1, True),
        MonthlyInterval(date(2020, 2, 29), date(2020, 3, 1), date(2020, 4, 1), -0.1, True),
        MonthlyInterval(date(2020, 3, 31), date(2020, 4, 1), date(2020, 5, 1), 0.1, True),
    )
    left, right = intervals[:2], intervals[2:]
    outcomes = (evaluate(left, "B1_SPY_BUY_HOLD", 15), evaluate(right, "B1_SPY_BUY_HOLD", 15))
    combined = combine_outcomes(
        outcomes
    )

    assert combined["complete_month_count"] == sum(
        item["complete_month_count"] for item in outcomes
    )
    assert combined["annualized_volatility"] is not None
    assert combined["maximum_drawdown"] is not None
    assert combined["calmar"] is not None
    assert combined["positive_month_fraction"] is not None
    gross = math.prod(1.0 + value for item in outcomes for value in item["_gross_returns"])
    net = math.prod(1.0 + value for item in outcomes for value in item["_net_returns"])
    assert combined["cost_drag"] == pytest.approx(gross - net)


def test_invalid_dates_fail_closed() -> None:
    with pytest.raises(SPYTrendCashError, match="strictly increasing"):
        build_monthly_intervals(
            (DailyBar(date(2020, 1, 1), 1.0, 1.0), DailyBar(date(2020, 1, 1), 1.0, 1.0)),
            date(2020, 1, 2),
        )


def _result(cagr: float, drawdown: float, calmar: float, market: float) -> dict[str, float]:
    return {
        "cagr": cagr,
        "maximum_drawdown": drawdown,
        "calmar": calmar,
        "time_in_market": market,
    }


def test_adjudication_is_eight_mechanical_gates() -> None:
    results = {
        "validation": {
            "15": {"B1": _result(0.1, -0.2, 0.5, 1.0), "B2": _result(0.1, -0.1, 1.0, 0.5)}
        },
        "holdout": {
            "15": {"B1": _result(0.1, -0.2, 0.5, 1.0), "B2": _result(0.1, -0.1, 1.0, 0.5)}
        },
        "combined": {
            "15": {"B1": _result(0.1, -0.2, 0.5, 1.0), "B2": _result(0.06, -0.1, 0.6, 0.5)},
            "30": {"B1": _result(0.1, -0.2, 0.5, 1.0), "B2": _result(0.01, -0.1, 0.1, 0.5)},
        },
    }

    outcome = adjudicate(results, 0)
    assert outcome["status"] == "RETROSPECTIVE_BASELINE_PASS_TO_SHADOW_REVIEW"
    assert outcome["gates_passed"] == 8
    assert adjudicate(results, 1)["status"] == "RETROSPECTIVE_BASELINE_FAIL"


def test_definition_freezes_data_mechanics_gates_and_boundaries() -> None:
    definition = json.loads(DEFINITION.read_text(encoding="utf-8"))

    assert definition["research_id"] == runner.RESEARCH_ID
    assert definition["status"] == "DEFINITION_FROZEN_NOT_EXECUTED"
    assert definition["input_identity"]["snapshot_id"] == runner.SNAPSHOT_ID
    assert definition["input_identity"]["required_row_count"] == 8418
    assert definition["state"]["moving_average_sessions"] == 200
    assert definition["execution"]["execution_price"] == "adj_open"
    assert definition["costs"] == {
        "primary_one_way_bps": 15,
        "stress_one_way_bps": 30,
        "additional_slippage_model": False,
    }
    assert tuple(definition["primary_gates"]) == runner.GATE_LABELS
    assert definition["metric_formulas"]["annualized_volatility"].startswith(
        "sample standard deviation"
    )
    assert not any(definition["boundaries"].values())


def test_runner_default_is_dry_run_without_opening_database_or_writing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        runner,
        "_run",
        lambda *_args, **_kwargs: pytest.fail("dry run must not open the database"),
    )

    assert runner.main([]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output == {
        "database_opened": False,
        "files_written": False,
        "research_id": runner.RESEARCH_ID,
        "status": "DRY_RUN_NO_OUTCOME",
        "strategy_candidate_available": False,
    }


def test_strict_json_rejects_duplicate_and_nonfinite_values(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"a":1,"a":2}', encoding="utf-8")
    with pytest.raises(runner.BaselineRunError, match="duplicate JSON key"):
        runner._strict_json(duplicate)

    nonfinite = tmp_path / "nonfinite.json"
    nonfinite.write_text('{"a":NaN}', encoding="utf-8")
    with pytest.raises(runner.BaselineRunError, match="nonfinite JSON constant"):
        runner._strict_json(nonfinite)


def test_post_claim_calculation_error_publishes_input_blocked_and_prevents_retry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    expected_hash = "a" * 64
    database = tmp_path / "input.duckdb"
    database.write_bytes(b"frozen-input")
    result_path = tmp_path / "result.json"
    receipt_path = tmp_path / "run.json"
    interval = MonthlyInterval(
        date(2020, 1, 31), date(2020, 2, 3), date(2020, 3, 2), 0.01, True
    )
    monkeypatch.setattr(runner, "RESULT", result_path)
    monkeypatch.setattr(runner, "RECEIPT", receipt_path)
    monkeypatch.setattr(runner, "_locked_code_identity", lambda: ("b" * 40, "c" * 40))
    monkeypatch.setattr(
        runner,
        "_strict_json",
        lambda path: {} if path == runner.DEFINITION else json.loads(path.read_text()),
    )
    monkeypatch.setattr(runner, "_validate_definition", lambda *_args: None)
    monkeypatch.setattr(runner, "_sha256", lambda _path: expected_hash)
    monkeypatch.setattr(
        runner,
        "_database_rows",
        lambda _path: ((DailyBar(date(2020, 1, 1), 1.0, 1.0),), {}),
    )
    monkeypatch.setattr(runner.baseline, "build_monthly_intervals", lambda *_args: (interval,))
    monkeypatch.setattr(runner.baseline, "select_split", lambda *_args: (interval,))
    monkeypatch.setattr(
        runner,
        "_period_results",
        lambda *_args: (_ for _ in ()).throw(runner.BaselineRunError("after claim")),
    )

    result, receipt = runner._run(database, expected_hash)
    assert json.loads(receipt_path.read_text())["status"] == "CLAIMED_RETROSPECTIVE_OUTCOME_RUN"
    assert result["status"] == "INPUT_BLOCKED"
    assert receipt["status"] == "CONSUMED_RETROSPECTIVE_INPUT_BLOCKED"
    result_bytes = runner._canonical(result)
    runner._exclusive_write(result_path, result_bytes)
    runner._finalize_claim(receipt_path, runner._canonical(receipt))
    assert json.loads(result_path.read_text())["periods"] is None
    assert json.loads(receipt_path.read_text())["status"] == "CONSUMED_RETROSPECTIVE_INPUT_BLOCKED"
    with pytest.raises(runner.BaselineRunError, match="already exists"):
        runner._run(database, expected_hash)
