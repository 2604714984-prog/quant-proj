from __future__ import annotations

from datetime import date
import importlib.util
import json
from pathlib import Path
import sys

import pytest

from quant_system.research.us_spy_turn_of_month import (
    DailyBar, Episode, SplitView, TurnOfMonthError, adjudicate, bootstrap_lower_bound,
    build_episodes, daily_labels, evaluate, label_metrics, split_view,
)


ROOT = Path(__file__).resolve().parents[1]
DEFINITION = ROOT / "research/definitions/us_spy_classic_turn_of_month_v1.json"
RUNNER_PATH = ROOT / "scripts/run_us_spy_turn_of_month_once.py"
SPEC = importlib.util.spec_from_file_location("tom_runner", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


def _bar(day: date, raw: float = 30.0, adjusted: float | None = None) -> DailyBar:
    return DailyBar(day, raw, raw if adjusted is None else adjusted)


def test_episode_roles_and_cross_split_returns_are_purged_not_relabelled() -> None:
    bars = tuple(
        _bar(day) for day in (
            date(2020, 1, 30), date(2020, 1, 31), date(2020, 2, 3),
            date(2020, 2, 4), date(2020, 2, 5), date(2020, 2, 27),
            date(2020, 2, 28), date(2020, 3, 2), date(2020, 3, 3), date(2020, 3, 4),
        )
    )
    episodes = build_episodes(bars)
    assert episodes[0] == Episode(
        "2020-02", date(2020, 1, 30), date(2020, 1, 31), date(2020, 2, 3),
        date(2020, 2, 4), date(2020, 2, 5),
    )
    view = split_view(bars, episodes, date(2020, 2, 1), date(2020, 2, 29))
    assert view.episodes == ()
    assert view.excluded_return_dates == {
        date(2020, 2, 3), date(2020, 2, 4), date(2020, 2, 5), date(2020, 2, 28)
    }
    terminal_bars = bars[:7]
    terminal = split_view(
        terminal_bars, build_episodes(terminal_bars), date(2020, 1, 1), date(2020, 2, 28),
        terminal_censored_t=date(2020, 2, 28),
    )
    assert date(2020, 2, 28) not in {day for day, _, _ in daily_labels(terminal)}


def test_calendar_gap_duplicate_and_interior_short_month_fail_closed() -> None:
    with pytest.raises(TurnOfMonthError, match="strictly increasing"):
        build_episodes((_bar(date(2020, 1, 2)), _bar(date(2020, 1, 2))))
    with pytest.raises(TurnOfMonthError, match="missing calendar month"):
        build_episodes((
            _bar(date(2020, 1, 30)), _bar(date(2020, 1, 31)),
            _bar(date(2020, 3, 2)), _bar(date(2020, 3, 3)), _bar(date(2020, 3, 4)),
        ))


def test_whole_share_cost_nav_timeline_adjusted_mark_and_drawdown() -> None:
    days = tuple(date(2020, 1, value) for value in range(1, 6))
    adjusted = (30.0, 15.0, 24.0, 27.0, 33.0)
    bars = tuple(_bar(day, 30.0, value) for day, value in zip(days, adjusted))
    episode = Episode("2020-01", *days)
    outcome = evaluate(SplitView(bars, (episode,), frozenset()),
                       "B2_SPY_CLASSIC_TURN_OF_MONTH", 100, 100.0)
    assert outcome["_navs"][0] == pytest.approx(99.1)
    assert outcome["_navs"][-1] == pytest.approx(107.11)
    assert outcome["_exposure"] == (False, True, True, True, True)
    assert outcome["whole_share_cash_utilization"] == pytest.approx(0.9)
    assert outcome["cost_drag"] == pytest.approx(0.0189)
    assert outcome["mean_episode_return"] == pytest.approx(0.0711)
    assert outcome["daily_maximum_drawdown"] < -0.4


def test_zero_share_and_nonfinite_price_fail_closed() -> None:
    view = SplitView(tuple(_bar(date(2020, 1, value), 200.0) for value in range(1, 6)),
                     (Episode("2020-01", *(date(2020, 1, value) for value in range(1, 6))),),
                     frozenset())
    with pytest.raises(TurnOfMonthError, match="afford"):
        evaluate(view, "B2_SPY_CLASSIC_TURN_OF_MONTH", 5, 100.0)
    with pytest.raises(TurnOfMonthError, match="positive and finite"):
        _bar(date(2020, 1, 1), float("nan"))


def test_daily_labels_use_destination_session_and_both_split_endpoints() -> None:
    days = tuple(date(2020, 1, value) for value in range(1, 7))
    bars = tuple(_bar(day, adjusted=30.0 + index) for index, day in enumerate(days))
    episode = Episode("2020-01", *days[:5])
    labelled = daily_labels(SplitView(bars, (episode,), frozenset()))
    assert tuple(flag for _, _, flag in labelled) == (True, True, True, True, False)
    metrics = label_metrics(labelled)
    assert metrics["tom_day_count"] == 4
    assert metrics["non_tom_day_count"] == 1


def test_pcg64_calendar_month_bootstrap_has_literal_nonconstant_golden_value() -> None:
    labelled = (
        (date(2020, 1, 2), 0.01, True), (date(2020, 1, 3), -0.01, False),
        (date(2020, 2, 3), 0.02, True), (date(2020, 2, 4), 0.00, False),
        (date(2020, 3, 2), -0.01, True), (date(2020, 3, 3), 0.01, False),
    )
    assert bootstrap_lower_bound(labelled, draws=8, seed=7) == pytest.approx(-0.006666666666666667)


def _metric(cagr: float, drawdown: float = -0.1, calmar: float = 1.0,
            episode: float = 0.1, year: float = 0.2) -> dict[str, float]:
    return {"cagr": cagr, "daily_maximum_drawdown": drawdown, "calmar": calmar,
            "largest_episode_contribution": episode,
            "largest_calendar_year_contribution": year}


def test_adjudication_separates_input_blocked_and_applies_exact_eight_gates() -> None:
    b1, b2 = _metric(0.05, -0.2, 0.25), _metric(0.06, -0.1, 0.6)
    results = {name: {"5": {"B1_SPY_BUY_HOLD": b1,
                             "B2_SPY_CLASSIC_TURN_OF_MONTH": b2}}
               for name in ("validation", "holdout")}
    results["combined"] = {"15": {"B2_SPY_CLASSIC_TURN_OF_MONTH": _metric(0.03)}}
    labels = {name: {"mean_tom_daily_return": 0.01, "mean_non_tom_daily_return": 0.0}
              for name in ("validation", "holdout")}
    assert adjudicate(results, labels, 0.001)["gates_passed"] == 8
    assert adjudicate(results, labels, 0.001, 1) == {
        "status": "INPUT_BLOCKED", "gates_passed": None, "gates_total": 8
    }


def test_definition_and_runner_are_frozen_and_default_run_is_dry(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    definition = json.loads(DEFINITION.read_text(encoding="utf-8"))
    assert definition["research_id"] == runner.RESEARCH_ID
    assert definition["input_identity"]["required_complete_episode_counts"] == {
        "development": 119, "validation": 95, "retrospective_holdout": 101
    }
    assert tuple(definition["primary_gates"]) == runner.GATE_LABELS
    forged = tmp_path / "definition.json"
    forged.write_bytes(DEFINITION.read_bytes() + b"\n")
    monkeypatch.setattr(runner, "DEFINITION", forged)
    with pytest.raises(runner.TurnOfMonthRunError, match="accepted freeze"):
        runner._validate_definition(definition, definition["input_identity"]["database_sha256"])
    database, replacement = tmp_path / "db", tmp_path / "replacement"
    database.write_bytes(b"first")
    signature = runner._database_signature(database)
    replacement.write_bytes(b"second")
    replacement.replace(database)
    with pytest.raises(runner.TurnOfMonthRunError, match="identity changed"):
        runner._assert_database_signature(database, signature)
    monkeypatch.setattr(runner, "_run", lambda *_: pytest.fail("dry run cannot open outcomes"))
    assert runner.main([]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "DRY_RUN_NO_OUTCOME"
