from __future__ import annotations

from datetime import date, timedelta
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pytest

from quant_system.research import us_spy_qqq_gld_inverse_volatility as iv


ROOT = Path(__file__).resolve().parents[1]
DEFINITION = ROOT / "research/definitions/us_spy_qqq_gld_inverse_volatility_v1.json"
RUNNER = ROOT / "scripts/run_us_spy_qqq_gld_inverse_volatility_once.py"


def _runner():
    spec = importlib.util.spec_from_file_location("inverse_volatility_runner", RUNNER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rows(days: int = 500) -> tuple[iv.Bar, ...]:
    start = date(2004, 1, 1)
    output = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        for index, symbol in enumerate(iv.SYMBOLS, 1):
            price = 100.0 * math.exp(0.001 * offset + 0.01 * math.sin(offset * index / 4.0))
            output.append(iv.Bar(day, symbol, price, price, price))
    return tuple(output)


def _view(start: date, weights=(0.6, 0.3, 0.1)) -> iv.SplitView:
    dates = (start, start + timedelta(days=1))
    rows = tuple(iv.Bar(day, symbol, price, price, price) for day in dates
                 for symbol, price in zip(iv.SYMBOLS, (100.0, 200.0, 400.0)))
    interval = iv.Interval(start - timedelta(days=1), dates[0], dates[1],
                           tuple(zip(iv.SYMBOLS, weights)), tuple(zip(iv.SYMBOLS, (0.1, 0.2, 0.3))))
    return iv.SplitView(iv.Panel(dates, rows), (interval,))


def test_definition_freezes_method_inference_and_boundaries() -> None:
    value = json.loads(DEFINITION.read_text(encoding="utf-8"))
    assert value["status"] == "DEFINITION_FROZEN_NOT_EXECUTED"
    assert value["strategy"]["volatility_window_common_session_returns"] == 60
    assert value["strategy"]["single_asset_cap"] == 0.6
    assert "redistribute" in value["strategy"]["cap_redistribution"]
    assert len(value["primary_gates"]) == 10
    assert value["inference"]["bootstrap_draws"] == 20_000
    assert all(flag is False for flag in value["boundaries"].values())


def test_capped_weights_redistribute_and_remain_fully_invested() -> None:
    weights = dict(iv.capped_inverse_weights((("SPY", 0.005), ("QQQ", 0.02), ("GLD", 0.04))))
    assert weights == pytest.approx({"SPY": 0.6, "QQQ": 0.8 / 3, "GLD": 0.4 / 3})
    assert math.fsum(weights.values()) == pytest.approx(1.0)
    with pytest.raises(iv.InverseVolatilityError, match="positive and finite"):
        iv.capped_inverse_weights((("SPY", 0.0), ("QQQ", 0.02), ("GLD", 0.04)))


def test_month_end_uses_exact_sixty_returns_and_next_open() -> None:
    panel = iv.prepare_panel(_rows(), date(2005, 5, 14))
    first = iv.build_intervals(panel)[0]
    index, lookup = panel.dates.index(first.decision_date), panel.lookup
    returns = [lookup[(panel.dates[offset], "SPY")].adj_close /
               lookup[(panel.dates[offset - 1], "SPY")].adj_close - 1.0
               for offset in range(index - 59, index + 1)]
    mean = math.fsum(returns) / 60
    expected = math.sqrt(math.fsum((value - mean) ** 2 for value in returns) / 59)
    assert dict(first.volatilities)["SPY"] == pytest.approx(expected)
    assert first.entry_date == panel.dates[index + 1]
    assert (first.decision_date.year, first.decision_date.month) != (first.entry_date.year, first.entry_date.month)


def test_split_requires_decision_entry_and_exit_inside_bounds() -> None:
    panel = iv.prepare_panel(_rows(), date(2005, 5, 14))
    intervals = iv.build_intervals(panel)
    chosen = intervals[2]
    view = iv.select_split(panel, intervals, chosen.decision_date, chosen.exit_date)
    assert view.intervals == (chosen,)
    assert view.panel.dates == tuple(day for day in panel.dates if chosen.entry_date <= day <= chosen.exit_date)


def test_whole_share_cost_residual_and_monthly_turnover_semantics() -> None:
    outcome = iv.evaluate(_view(date(2020, 1, 2)), 100)
    purchase = 237 * 100 + 59 * 200 + 9 * 400
    post_purchase_cash = 40_000 - purchase * 1.01
    assert outcome["whole_share_cash_utilization"] == pytest.approx(purchase / 40_000)
    assert outcome["mean_residual_cash_fraction"] == pytest.approx(post_purchase_cash / 40_000)
    assert outcome["maximum_residual_cash_fraction"] == pytest.approx(post_purchase_cash / 40_000)
    assert outcome["mean_monthly_one_way_turnover"] == pytest.approx(purchase / 40_000)
    assert outcome["cap_binding_month_count"] == 1


def test_combined_outcomes_preserve_inverse_volatility_extras() -> None:
    first = iv.evaluate(_view(date(2020, 1, 2)), 15)
    second = iv.evaluate(_view(date(2021, 1, 2), (0.2, 0.2, 0.6)), 15)
    combined = iv.combine_outcomes((first, second))
    assert combined["mean_target_weights"] == pytest.approx({"SPY": 0.4, "QQQ": 0.25, "GLD": 0.35})
    assert combined["cap_binding_month_count"] == 2
    assert combined["mean_monthly_one_way_turnover"] == pytest.approx(
        (first["mean_monthly_one_way_turnover"] + second["mean_monthly_one_way_turnover"]) / 2
    )
    assert combined["maximum_residual_cash_fraction"] == max(
        first["maximum_residual_cash_fraction"], second["maximum_residual_cash_fraction"]
    )


def _results() -> dict[str, object]:
    metric = {"cagr": 0.10, "annualized_volatility": 0.10, "daily_maximum_drawdown": -0.10,
              "calmar": 1.0, "largest_calendar_year_profit_contribution": 0.2}
    result = {split: {cost: {name: dict(metric) for name in
              ("B1_SPY_BUY_HOLD", "B2_STATIC_EQUAL_WEIGHT_SPY_QQQ_GLD", "B4_INVERSE_VOLATILITY")}
              for cost in ("15", "30")} for split in ("validation", "holdout", "combined")}
    for split in ("validation", "holdout"):
        result[split]["15"]["B2_STATIC_EQUAL_WEIGHT_SPY_QQQ_GLD"]["annualized_volatility"] = 0.2
    result["holdout"]["15"]["B1_SPY_BUY_HOLD"].update({"daily_maximum_drawdown": -0.2, "calmar": 0.5})
    result["holdout"]["15"]["B2_STATIC_EQUAL_WEIGHT_SPY_QQQ_GLD"].update({"daily_maximum_drawdown": -0.2, "calmar": 0.8})
    result["combined"]["15"]["B1_SPY_BUY_HOLD"]["cagr"] = 0.15
    result["combined"]["15"]["B2_STATIC_EQUAL_WEIGHT_SPY_QQQ_GLD"]["calmar"] = 0.8
    result["combined"]["30"]["B2_STATIC_EQUAL_WEIGHT_SPY_QQQ_GLD"]["calmar"] = 0.8
    return result


def test_nullable_metric_is_failed_gate_not_input_blocked() -> None:
    results = _results()
    inference = ({"passed": True},) * 4
    assert iv.adjudicate(results, inference)["status"] == "RETROSPECTIVE_INVERSE_VOLATILITY_PASS_TO_EXTERNAL_REVIEW"
    results["combined"]["30"]["B4_INVERSE_VOLATILITY"]["largest_calendar_year_profit_contribution"] = None
    adjudication = iv.adjudicate(results, inference)
    assert adjudication["status"] == "RETROSPECTIVE_INVERSE_VOLATILITY_FAIL"
    assert adjudication["gates_passed"] == 9


def test_paired_bootstrap_and_holm_are_deterministic() -> None:
    comparator = np.array([0.001 * math.sin(index) for index in range(80)])
    strategy = comparator + np.array([0.0005 + 0.0002 * math.cos(index) for index in range(80)])
    first = iv.paired_sharpe_test(strategy, comparator, draws=50, seed=7)
    second = iv.paired_sharpe_test(strategy, comparator, draws=50, seed=7)
    assert first["raw_p"] == second["raw_p"]
    tests = tuple({"observed_difference": 1.0, "raw_p": 0.001,
                   "_centered": np.linspace(-0.1, 0.1, 101)} for _ in range(4))
    assert all(item["passed"] for item in iv.holm(tests))


def test_runner_dry_run_never_opens_database_or_writes(monkeypatch, tmp_path, capsys) -> None:
    runner = _runner()
    monkeypatch.setattr(runner, "RESULT", tmp_path / "result.json")
    monkeypatch.setattr(runner, "RECEIPT", tmp_path / "run.json")
    monkeypatch.setattr(runner, "query", lambda *_a, **_k: pytest.fail("database opened"))
    monkeypatch.setattr(runner, "sha256_file", lambda *_a, **_k: pytest.fail("database hashed"))
    assert runner.main([]) == 0
    assert json.loads(capsys.readouterr().out)["database_opened"] is False
    assert list(tmp_path.iterdir()) == []


def test_runner_existing_output_rejects_before_identity(monkeypatch, tmp_path) -> None:
    runner = _runner()
    existing = tmp_path / "result.json"
    existing.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(runner, "RESULT", existing)
    monkeypatch.setattr(runner, "RECEIPT", tmp_path / "run.json")
    monkeypatch.setattr(runner, "_code_identity", lambda: pytest.fail("Git inspected"))
    with pytest.raises(runner.InverseVolatilityRunError, match="already exists"):
        runner._run(tmp_path / "never-open.db", "0" * 64)
