from __future__ import annotations

from datetime import date, timedelta
import importlib.util
import json
import math
from pathlib import Path

import pytest

from quant_system.research import us_spy_gld_stress_safe_haven as sh


ROOT = Path(__file__).resolve().parents[1]
DEFINITION = ROOT / "research/definitions/us_spy_gld_stress_safe_haven_v1.json"
RUNNER = ROOT / "scripts/run_us_spy_gld_stress_safe_haven_once.py"


def _rows(days: int = 260, final_spy: float | None = None) -> tuple[sh.Bar, ...]:
    start = date(2020, 1, 1)
    rows = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        spy = final_spy if final_spy is not None and offset == 251 else 100.0
        rows.extend(
            (
                sh.Bar(day, "SPY", spy, spy, spy),
                sh.Bar(day, "GLD", 50.0, 50.0, 50.0),
            )
        )
    return tuple(rows)


def _view() -> sh.SplitView:
    days = tuple(date(2020, 1, 2) + timedelta(days=index) for index in range(4))
    gl = (100.0, 110.0, 120.0, 120.0)
    rows = tuple(
        row
        for index, day in enumerate(days)
        for row in (
            sh.Bar(day, "SPY", 100.0, 100.0, 100.0),
            sh.Bar(day, "GLD", gl[index], gl[index], gl[index]),
        )
    )
    intervals = (
        sh.Interval(days[0] - timedelta(days=1), days[0], days[1], True, -0.10),
        sh.Interval(days[0], days[1], days[2], True, -0.11),
        sh.Interval(days[1], days[2], days[3], False, -0.09),
    )
    return sh.SplitView(sh.Panel(days, rows), intervals)


def _metric(value: float = 0.1) -> dict[str, object]:
    return {
        "active_stress_interval_count": 60,
        "distinct_active_calendar_year_count": 3,
        "cagr": value,
        "daily_maximum_drawdown": -0.1,
        "calmar": 1.0,
        "positive_active_interval_fraction": 0.6,
        "largest_calendar_year_profit_contribution": 0.3,
    }


def _runner():
    spec = importlib.util.spec_from_file_location("safe_haven_runner", RUNNER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_definition_freezes_single_daily_rule_and_boundaries() -> None:
    value = json.loads(DEFINITION.read_text(encoding="utf-8"))
    assert value["research_id"] == "US_SPY_GLD_STRESS_SAFE_HAVEN_V1"
    assert value["strategy"]["variants"] == 1
    assert value["strategy"]["stress_window_common_sessions"] == 252
    assert "<= 0.90 times" in value["strategy"]["stress_condition"]
    assert len(value["primary_gates"]) == 10
    assert value["input_identity"]["expected_executable_slice_sha256"] == (
        "ffb9ccc81f82c4f1b316d45b884021906235282f0c131d9c55bc2e314fdfa399"
    )
    assert all(flag is False for flag in value["boundaries"].values())


def test_panel_rejects_missing_duplicate_and_invalid_prices() -> None:
    rows = _rows()
    cutoff = rows[-1].session_date
    assert len(sh.prepare_panel(rows, cutoff).dates) == 260
    with pytest.raises(sh.SafeHavenError, match="duplicate"):
        sh.prepare_panel(rows + (rows[0],), cutoff)
    missing = tuple(row for row in rows if not (row.session_date == rows[20].session_date and row.symbol == "GLD"))
    with pytest.raises(sh.SafeHavenError, match="missing"):
        sh.prepare_panel(missing, cutoff)
    with pytest.raises(sh.SafeHavenError, match="positive and finite"):
        sh.Bar(date(2020, 1, 1), "SPY", math.nan, 1.0, 1.0)


def test_exact_252_session_drawdown_and_timing() -> None:
    panel = sh.prepare_panel(_rows(final_spy=90.0), date(2020, 9, 16))
    first = sh.build_intervals(panel)[0]
    assert first.stress is True
    assert first.stress_score == pytest.approx(-0.10)
    assert first.entry_date == panel.dates[252]
    assert first.endpoint_date == panel.dates[253]
    panel = sh.prepare_panel(_rows(final_spy=90.0001), date(2020, 9, 16))
    assert sh.build_intervals(panel)[0].stress is False


def test_split_requires_all_three_interval_dates() -> None:
    panel = sh.prepare_panel(_rows(final_spy=90.0), date(2020, 9, 16))
    first = sh.build_intervals(panel)[0]
    view = sh.select_split(panel, (first,), first.decision_date, first.endpoint_date)
    assert view.intervals == (first,)
    assert view.panel.dates == (first.entry_date, first.endpoint_date)
    with pytest.raises(sh.SafeHavenError, match="no complete"):
        sh.select_split(panel, (first,), first.entry_date, first.endpoint_date)


def test_stress_sleeve_retains_position_and_attributes_exit_cost() -> None:
    outcome = sh.evaluate(_view(), "B4_GLD_STRESS_SAFE_HAVEN", 100)
    first_nav = 4.0 + 396 * 100.0
    second_nav = 4.0 + 396 * 110.0
    third_nav = 4.0 + 396 * 120.0 * 0.99
    assert outcome["_navs"] == pytest.approx((first_nav, second_nav, third_nav, third_nav))
    assert outcome["_active_interval_returns"] == pytest.approx(
        (second_nav / first_nav - 1.0, third_nav / second_nav - 1.0)
    )
    assert outcome["state_transition_count"] == 1
    assert outcome["complete_interval_count"] == 3
    assert outcome["active_stress_interval_count"] == 2
    assert outcome["cost_drag"] == pytest.approx((396.0 + 475.2) / 40_000.0)
    assert len(outcome["_utilizations"]) == 1


def test_comparators_share_state_but_use_frozen_assets() -> None:
    view = _view()
    cash = sh.evaluate(view, "B0_CASH", 15)
    spy = sh.evaluate(view, "B2_SPY_STRESS_SLEEVE", 15)
    gold = sh.evaluate(view, "B4_GLD_STRESS_SAFE_HAVEN", 15)
    assert cash["cumulative_net_return"] == 0.0
    assert spy["active_stress_interval_count"] == gold["active_stress_interval_count"] == 2
    assert spy["state_transition_count"] == gold["state_transition_count"] == 1
    assert spy["_daily_returns"] != gold["_daily_returns"]


def test_combined_path_chains_returns_without_cross_split_transition() -> None:
    first = sh.evaluate(_view(), "B4_GLD_STRESS_SAFE_HAVEN", 15)
    second_view = _view()
    shifted = timedelta(days=366)
    second_view = sh.SplitView(
        sh.Panel(
            tuple(day + shifted for day in second_view.panel.dates),
            tuple(
                sh.Bar(row.session_date + shifted, row.symbol, row.raw_open, row.adj_open, row.adj_close)
                for row in second_view.panel.rows
            ),
        ),
        tuple(
            sh.Interval(
                item.decision_date + shifted,
                item.entry_date + shifted,
                item.endpoint_date + shifted,
                item.stress,
                item.stress_score,
            )
            for item in second_view.intervals
        ),
    )
    second = sh.evaluate(second_view, "B4_GLD_STRESS_SAFE_HAVEN", 15)
    combined = sh.combine_outcomes((first, second))
    expected = math.prod(1.0 + value for value in (*first["_daily_returns"], *second["_daily_returns"])) - 1.0
    assert combined["cumulative_net_return"] == pytest.approx(expected)
    assert combined["state_transition_count"] == 2


def test_mean_bootstrap_uses_one_deterministic_stream_and_holm() -> None:
    series = tuple(
        tuple(0.001 * (index + 1) + leg * 0.0001 for index in range(25))
        for leg in range(4)
    )
    first = sh.mean_inference(series, draws=31, block=5, seed=7)
    second = sh.mean_inference(series, draws=31, block=5, seed=7)
    assert first == second
    assert [item["raw_p"] for item in first] == pytest.approx([0.03125] * 4)
    assert [item["holm_rank_threshold"] for item in first] == pytest.approx(
        [0.00625, 0.008333333333333333, 0.0125, 0.025]
    )


def test_nullable_metric_is_gate_failure_not_input_blocked() -> None:
    names = sh.COMPARATORS
    results = {
        split: {cost: {name: _metric() for name in names} for cost in ("15", "30")}
        for split in ("validation", "holdout", "combined")
    }
    results["holdout"]["15"][names[2]]["daily_maximum_drawdown"] = -0.2
    results["holdout"]["15"][names[2]]["calmar"] = 0.5
    results["combined"]["30"][names[2]]["daily_maximum_drawdown"] = -0.2
    inference = ({"passed": True},) * 4
    assert sh.adjudicate(results, inference)["status"].endswith("PASS_TO_EXTERNAL_REVIEW")
    results["combined"]["30"][names[4]]["largest_calendar_year_profit_contribution"] = None
    outcome = sh.adjudicate(results, inference)
    assert outcome["status"] == "RETROSPECTIVE_STRESS_SAFE_HAVEN_FAIL"
    assert outcome["gates_passed"] == 9
    forged = sh.adjudicate(results, ({"passed": "false"},) * 4)
    assert forged["status"] == "RETROSPECTIVE_STRESS_SAFE_HAVEN_FAIL"


def test_preclaim_input_failure_leaves_one_use_paths_retryable(monkeypatch, tmp_path, capsys) -> None:
    runner = _runner()
    monkeypatch.setattr(runner, "RESULT", tmp_path / "result.json")
    monkeypatch.setattr(runner, "RECEIPT", tmp_path / "run.json")
    blocked = {"status": "INPUT_BLOCKED"}
    receipt = {"result_sha256": "0" * 64}
    monkeypatch.setattr(runner, "_run", lambda *_a: (blocked, receipt, False))
    assert runner.main(["--execute", "--database", str(tmp_path / "db"),
                        "--expected-database-sha256", "0" * 64]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "INPUT_BLOCKED"
    assert list(tmp_path.iterdir()) == []


def test_failed_receipt_replacement_removes_owned_temporary(monkeypatch, tmp_path) -> None:
    runner = _runner()
    receipt = tmp_path / "run.json"
    receipt.write_bytes(runner._canonical({"status": "CLAIMED_RETROSPECTIVE_OUTCOME_RUN"}))
    monkeypatch.setattr(runner.os, "replace", lambda *_a: (_ for _ in ()).throw(OSError("boom")))
    with pytest.raises(OSError, match="boom"):
        runner._finalize(receipt, b"{}\n")
    assert list(tmp_path.iterdir()) == [receipt]


def test_runner_dry_run_does_not_open_database_or_write(monkeypatch, tmp_path, capsys) -> None:
    runner = _runner()
    monkeypatch.setattr(runner, "RESULT", tmp_path / "result.json")
    monkeypatch.setattr(runner, "RECEIPT", tmp_path / "run.json")
    monkeypatch.setattr(runner, "query", lambda *_a, **_k: pytest.fail("database opened"))
    monkeypatch.setattr(runner, "sha256_file", lambda *_a, **_k: pytest.fail("database hashed"))
    assert runner.main([]) == 0
    assert json.loads(capsys.readouterr().out)["database_opened"] is False
    assert list(tmp_path.iterdir()) == []


def test_runner_existing_output_rejects_before_git_or_database(monkeypatch, tmp_path) -> None:
    runner = _runner()
    result = tmp_path / "result.json"
    result.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(runner, "RESULT", result)
    monkeypatch.setattr(runner, "RECEIPT", tmp_path / "run.json")
    monkeypatch.setattr(runner, "_code_identity", lambda: pytest.fail("Git inspected"))
    with pytest.raises(runner.SafeHavenRunError, match="already exists"):
        runner._run(tmp_path / "never-open.db", "0" * 64)
