from __future__ import annotations

from datetime import date, timedelta
import importlib.util
import json
import math
from pathlib import Path

import pytest

from quant_system.research import us_spy_qqq_gld_dual_momentum as dm


ROOT = Path(__file__).resolve().parents[1]
DEFINITION = ROOT / "research/definitions/us_spy_qqq_gld_dual_momentum_v1.json"
RUNNER = ROOT / "scripts/run_us_spy_qqq_gld_dual_momentum_once.py"


def _runner():
    spec = importlib.util.spec_from_file_location("dual_momentum_runner", RUNNER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rows(days: int = 620, drifts=(0.002, 0.001, 0.0005)) -> tuple[dm.Bar, ...]:
    start = date(2004, 1, 1)
    output = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        for symbol, drift in zip(dm.SYMBOLS, drifts):
            price = 100.0 * math.exp(drift * offset)
            output.append(dm.Bar(day, symbol, price, price, price))
    return tuple(output)


def _tiny_view(targets=("SPY",), ratio: float = 1.0) -> dm.SplitView:
    start = date(2020, 1, 2)
    dates = tuple(start + timedelta(days=index) for index in range(len(targets) + 1))
    rows = []
    for index, day in enumerate(dates):
        for symbol in dm.SYMBOLS:
            adj = 50.0 * (ratio**index) if symbol == "SPY" else 100.0
            rows.append(dm.Bar(day, symbol, 100.0, adj, adj))
    intervals = tuple(
        dm.Interval(dates[max(index - 1, 0)] - timedelta(days=1), dates[index], dates[index + 1], target, ())
        for index, target in enumerate(targets)
    )
    return dm.SplitView(dm.Panel(dates, tuple(rows)), intervals)


def test_definition_freezes_exact_mechanics_and_boundaries() -> None:
    value = json.loads(DEFINITION.read_text(encoding="utf-8"))
    assert value["duplicate_screen"] == "NO_EXACT_DUPLICATE"
    assert value["input_identity"]["symbols_in_tie_order"] == ["SPY", "QQQ", "GLD"]
    assert value["input_identity"]["database_sha256"] == "e636bb80e300f89e46831e91275c6f2167e370e81a00b21b300e253f6107bee0"
    assert "union" in value["input_identity"]["common_session_rule"]
    assert value["strategy"]["lookback_common_sessions"] == 252
    assert value["costs"] == {"primary_one_way_bps": 15, "stress_one_way_bps": 30, "additional_commission_model": False}
    assert len(value["primary_gates"]) == 8
    assert all(flag is False for flag in value["boundaries"].values())


def test_union_missing_symbol_blocks_before_intersection() -> None:
    rows = list(_rows())
    victim = next(row for row in rows if row.symbol == "QQQ" and row.session_date == date(2004, 3, 1))
    rows.remove(victim)
    with pytest.raises(dm.DualMomentumError, match="union date"):
        dm.prepare_panel(rows, rows[-1].session_date)


@pytest.mark.parametrize("field", ["raw_open", "adj_open", "adj_close"])
def test_duplicate_post_cutoff_and_bad_prices_fail_closed(field: str) -> None:
    rows = list(_rows())
    with pytest.raises(dm.DualMomentumError, match="duplicate"):
        dm.prepare_panel((*rows, rows[0]), rows[-1].session_date)
    with pytest.raises(dm.DualMomentumError, match="post-cutoff"):
        dm.prepare_panel(rows, rows[-4].session_date)
    source = rows[0]
    values = {"raw_open": source.raw_open, "adj_open": source.adj_open, "adj_close": source.adj_close}
    values[field] = float("nan")
    with pytest.raises(dm.DualMomentumError, match="positive and finite"):
        dm.Bar(source.session_date, source.symbol, **values)


def test_exact_252_top_one_tie_order_cash_gate_and_next_open() -> None:
    panel = dm.prepare_panel(_rows(drifts=(0.001, 0.001, 0.0005)), date(2005, 9, 11))
    first = dm.build_intervals(panel)[0]
    lookup = panel.lookup
    index = panel.dates.index(first.decision_date)
    expected = lookup[(first.decision_date, "SPY")].adj_close / lookup[(panel.dates[index - 252], "SPY")].adj_close - 1.0
    assert first.target == "SPY"
    assert dict(first.momentum)["SPY"] == pytest.approx(expected)
    assert first.entry_date == panel.dates[index + 1]
    assert (first.decision_date.year, first.decision_date.month) != (first.entry_date.year, first.entry_date.month)
    declining = dm.prepare_panel(_rows(drifts=(-0.001, -0.002, -0.003)), date(2005, 9, 11))
    assert dm.build_intervals(declining)[0].target == dm.CASH


def test_split_requires_decision_entry_and_exit_inside_same_bounds() -> None:
    panel = dm.prepare_panel(_rows(), date(2005, 9, 11))
    intervals = dm.build_intervals(panel)
    chosen = intervals[2]
    view = dm.select_split(panel, intervals, chosen.decision_date, chosen.exit_date)
    assert view.intervals[0] == chosen
    assert all(chosen.decision_date <= item.decision_date < item.entry_date < item.exit_date <= chosen.exit_date for item in view.intervals)
    assert view.panel.dates[0] == chosen.entry_date
    assert view.panel.dates[-1] == view.intervals[-1].exit_date


def test_cost_floor_adjusted_open_marking_and_single_terminal_sale() -> None:
    result = dm.evaluate(_tiny_view(("SPY",), ratio=2.0), "B3_DUAL_MOMENTUM_CASH", 100)
    assert result["whole_share_cash_utilization"] == pytest.approx(39600 / 40000)
    assert result["cost_drag"] == pytest.approx((396 + 792) / 40000)
    assert result["_navs"][-1] == pytest.approx(4 + 79200 - 792)
    assert result["selection_counts"] == {"SPY": 1, "QQQ": 0, "GLD": 0, "CASH": 0}


def test_same_asset_has_no_rebalance_but_switch_charges_two_sides() -> None:
    same = dm.evaluate(_tiny_view(("SPY", "SPY")), "B3_DUAL_MOMENTUM_CASH", 100)
    switched = dm.evaluate(_tiny_view(("SPY", "QQQ")), "B3_DUAL_MOMENTUM_CASH", 100)
    assert same["state_transition_count"] == 0
    assert same["cost_drag"] == pytest.approx(792 / 40000)
    assert switched["state_transition_count"] == 1
    assert switched["cost_drag"] == pytest.approx(1568 / 40000)
    assert switched["one_way_turnover"] > same["one_way_turnover"]


def test_static_equal_weight_uses_three_independent_unrebalanced_legs() -> None:
    view = _tiny_view(("SPY", "QQQ"))
    result = dm.evaluate(view, "B2_STATIC_EQUAL_WEIGHT_SPY_QQQ_GLD", 100)
    assert result["whole_share_cash_utilization"] == pytest.approx(0.99)
    assert result["one_way_turnover"] == pytest.approx(39600 / 40000 + 39600 / 39604)
    assert result["cost_drag"] == pytest.approx(792 / 40000)
    assert result["_exposure"][-1] is False
    assert "selection_counts" not in result


def _fake(dates, returns, intervals=1, selections=False):
    value = {"_dates": tuple(dates), "_daily_returns": tuple(returns), "_exposure": tuple(True for _ in dates),
             "_month_returns": (math.prod(1 + item for item in returns) - 1,), "_turnover": 0.0,
             "_cost_usd": 0.0, "_utilizations": (), "complete_interval_count": intervals}
    if selections:
        value.update({"selection_counts": {"SPY": intervals, "QQQ": 0, "GLD": 0, "CASH": 0},
                      "state_transition_count": 0})
    return value


def test_combined_chains_split_wealth_peak_and_actual_calendar_days() -> None:
    first = _fake((date(2020, 1, 1), date(2020, 1, 2)), (1.0, -0.25))
    second = _fake((date(2020, 1, 3), date(2020, 1, 11)), (-0.25, 0.0))
    result = dm.combine_outcomes((first, second))
    assert result["cumulative_net_return"] == pytest.approx(0.125)
    assert result["daily_maximum_drawdown"] == pytest.approx(-0.4375)
    assert result["actual_calendar_days"] == 10
    assert result["cagr"] == pytest.approx(1.125 ** (365.25 / 10) - 1)


def test_positive_year_contribution_and_empty_pool_are_fail_closed() -> None:
    positive = dm.combine_outcomes((_fake((date(2020, 1, 1), date(2021, 1, 1)), (0.10, 0.10)),))
    assert positive["largest_calendar_year_profit_contribution"] == pytest.approx(4400 / 8400)
    negative = dm.combine_outcomes((_fake((date(2020, 1, 1), date(2021, 1, 1)), (-0.10, -0.10)),))
    assert negative["largest_calendar_year_profit_contribution"] is None


def test_adjudication_requires_exact_eight_gates() -> None:
    metric = {"cagr": 0.10, "daily_maximum_drawdown": -0.10, "calmar": 1.0,
              "largest_calendar_year_profit_contribution": 0.2}
    results = {split: {cost: {name: dict(metric) for name in ("B1_SPY_BUY_HOLD", "B2_STATIC_EQUAL_WEIGHT_SPY_QQQ_GLD", "B3_DUAL_MOMENTUM_CASH")}
                       for cost in ("15", "30")} for split in ("validation", "holdout", "combined")}
    results["holdout"]["15"]["B1_SPY_BUY_HOLD"]["daily_maximum_drawdown"] = -0.2
    results["holdout"]["15"]["B1_SPY_BUY_HOLD"]["calmar"] = 0.5
    results["holdout"]["15"]["B2_STATIC_EQUAL_WEIGHT_SPY_QQQ_GLD"]["calmar"] = 0.8
    results["combined"]["15"]["B2_STATIC_EQUAL_WEIGHT_SPY_QQQ_GLD"]["calmar"] = 0.8
    result = dm.adjudicate(results)
    assert result["status"] == "RETROSPECTIVE_DUAL_MOMENTUM_PASS_TO_EXTERNAL_REVIEW"
    assert result["gates"] == (True,) * 8
    assert dm.adjudicate(results, 1) == {"status": "INPUT_BLOCKED", "gates_passed": None, "gates_total": 8}


def test_runner_dry_run_never_opens_database_or_writes(monkeypatch, tmp_path, capsys) -> None:
    runner = _runner()
    monkeypatch.setattr(runner, "RESULT", tmp_path / "result.json")
    monkeypatch.setattr(runner, "RECEIPT", tmp_path / "run.json")
    monkeypatch.setattr(runner, "query", lambda *_a, **_k: pytest.fail("database opened"))
    monkeypatch.setattr(runner, "sha256_file", lambda *_a, **_k: pytest.fail("database hashed"))
    assert runner.main([]) == 0
    assert json.loads(capsys.readouterr().out)["database_opened"] is False
    assert list(tmp_path.iterdir()) == []


def test_runner_requires_exact_path_hash_and_exclusive_outputs(tmp_path) -> None:
    runner = _runner()
    with pytest.raises(runner.DualMomentumRunError, match="path or expected"):
        runner.main(["--execute", "--database", str(tmp_path / "wrong.db"),
                     "--expected-database-sha256", "0" * 64])
    target = tmp_path / "once.json"
    runner._exclusive(target, b"{}\n")
    with pytest.raises(runner.DualMomentumRunError, match="exists"):
        runner._exclusive(target, b"{}\n")
    assert target.stat().st_mode & 0o777 == 0o600


def test_runner_existing_result_rejects_before_database_identity(monkeypatch, tmp_path) -> None:
    runner = _runner()
    existing = tmp_path / "result.json"
    existing.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(runner, "RESULT", existing)
    monkeypatch.setattr(runner, "RECEIPT", tmp_path / "run.json")
    monkeypatch.setattr(runner, "_code_identity", lambda: pytest.fail("Git inspected"))
    monkeypatch.setattr(runner, "_signature", lambda *_a: pytest.fail("database inspected"))
    with pytest.raises(runner.DualMomentumRunError, match="already exists"):
        runner._run(tmp_path / "never-open.db", "0" * 64)


@pytest.mark.parametrize("payload,match", [('{"x":1,"x":2}', "duplicate"), ('{"x":NaN}', "nonfinite")])
def test_runner_strict_json_rejects_ambiguous_values(tmp_path, payload: str, match: str) -> None:
    runner = _runner()
    path = tmp_path / "bad.json"
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(runner.DualMomentumRunError, match=match):
        runner._strict_json(path)
