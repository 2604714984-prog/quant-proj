from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

import scripts.run_us_spy_h15_10y3m_state_once as RUNNER
import research.adapters.us_spy_h15_10y3m_state as ADAPTER
from research.adapters.us_spy_h15_10y3m_state import (
    InputContractError,
    RateObservation,
    cohort_returns,
    inference_decision,
    paired_stationary_bootstrap_lower_bounds,
    screen_decision,
    stationary_bootstrap_indices,
    target_weight,
)


ROOT = Path(__file__).resolve().parents[1]


def _observation(
    series_id: str,
    value: float,
    *,
    observation_date: date = date(2021, 6, 29),
    available_at: datetime = datetime(2021, 6, 30, tzinfo=timezone.utc),
) -> RateObservation:
    return RateObservation(
        series_id,
        observation_date,
        value,
        available_at,
        "1" * 64 if series_id == "DGS10" else "2" * 64,
    )


def test_target_weight_uses_the_fixed_zero_threshold_and_equality_is_cash() -> None:
    decision_at = datetime(2021, 6, 30, 23, tzinfo=timezone.utc)
    assert target_weight(
        _observation("DGS10", 1.5),
        _observation("DGS3MO", 0.25),
        decision_at=decision_at,
    ) == 1.0
    assert target_weight(
        _observation("DGS10", 0.25),
        _observation("DGS3MO", 0.25),
        decision_at=decision_at,
    ) == 0.0
    assert target_weight(
        _observation("DGS10", 0.1),
        _observation("DGS3MO", 0.25),
        decision_at=decision_at,
    ) == 0.0


@pytest.mark.parametrize(
    ("ten_year", "three_month", "decision_at"),
    [
        (
            _observation("DGS10", 1.0),
            _observation("DGS3MO", 0.5, observation_date=date(2021, 6, 28)),
            datetime(2021, 6, 30, 23, tzinfo=timezone.utc),
        ),
        (
            _observation(
                "DGS10",
                1.0,
                available_at=datetime(2021, 7, 1, tzinfo=timezone.utc),
            ),
            _observation("DGS3MO", 0.5),
            datetime(2021, 6, 30, 23, tzinfo=timezone.utc),
        ),
        (
            _observation("DGS10", 1.0, observation_date=date(2021, 6, 20)),
            _observation("DGS3MO", 0.5, observation_date=date(2021, 6, 20)),
            datetime(2021, 6, 30, 23, tzinfo=timezone.utc),
        ),
    ],
)
def test_target_weight_fails_closed_on_mismatch_lateness_or_staleness(
    ten_year: RateObservation,
    three_month: RateObservation,
    decision_at: datetime,
) -> None:
    with pytest.raises(InputContractError):
        target_weight(ten_year, three_month, decision_at=decision_at)


def test_rate_observation_rejects_nonfinite_values_and_bad_hashes() -> None:
    with pytest.raises(InputContractError):
        _observation("DGS10", float("nan"))
    with pytest.raises(InputContractError):
        RateObservation(
            "DGS10",
            date(2021, 6, 29),
            1.0,
            datetime(2021, 6, 30, tzinfo=timezone.utc),
            "bad",
        )


def test_screen_decision_requires_exactly_45_complete_cohorts() -> None:
    def nav_path(first: float, second: float) -> tuple[float, ...]:
        navs = [40_000.0]
        for index in range(45):
            navs.append(navs[-1] * (1.0 + (first if index % 2 else second)))
        return tuple(navs)

    benchmark = nav_path(0.01, 0.005)
    strategy = nav_path(0.008, 0.003)
    decision = screen_decision(strategy, benchmark)
    assert decision.observed_cohorts == 45
    assert tuple(name for name, _ in decision.gates) == (
        "sharpe_difference_positive",
        "strategy_compounded_net_return_positive",
        "strategy_annualized_volatility_lower",
        "strategy_maximum_drawdown_better",
    )
    assert not decision.all_gates_pass

    with pytest.raises(InputContractError):
        cohort_returns(strategy[:-1])


def test_all_cash_path_is_a_terminal_screen_fail_not_an_undefined_metric() -> None:
    strategy = (40_000.0,) * 46
    benchmark = tuple(
        40_000.0 * (1.01 if index % 2 else 1.0) for index in range(46)
    )
    decision = screen_decision(strategy, benchmark)
    assert decision.strategy.monthly_sample_stdev == 0.0
    assert decision.strategy.sharpe == 0.0
    assert decision.strategy.compounded_net_return == 0.0
    assert decision.all_gates_pass is False


def test_nonzero_near_constant_path_fails_closed_instead_of_inflating_sharpe() -> None:
    near_constant = tuple(40_000.0 * (1.01**index) for index in range(46))
    with pytest.raises(InputContractError, match="nonzero constant returns"):
        screen_decision(near_constant, near_constant)


def _navs(returns: tuple[float, ...]) -> tuple[float, ...]:
    navs = [40_000.0]
    for value in returns:
        navs.append(navs[-1] * (1.0 + value))
    return tuple(navs)


def test_inference_stationary_bootstrap_has_a_literal_golden_path() -> None:
    assert stationary_bootstrap_indices(8)[:5] == (
        (6, 7, 0, 5, 6, 7, 0, 1),
        (0, 1, 2, 3, 4, 5, 6, 4),
        (6, 7, 0, 1, 2, 3, 4, 5),
        (7, 0, 1, 0, 1, 2, 2, 3),
        (2, 3, 4, 5, 0, 1, 2, 3),
    )

    production_paths = stationary_bootstrap_indices()
    assert len(production_paths) == 10_000
    assert all(len(path) == 53 and min(path) >= 0 and max(path) <= 52 for path in production_paths)
    payload = json.dumps(production_paths, separators=(",", ":")).encode()
    assert hashlib.sha256(payload).hexdigest() == (
        "4d7ef3071cec0da43f827a0428bde2e411243ac7c393553705f672fcb6e15398"
    )


def test_inference_requires_unlock_and_exactly_53_paired_cohorts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    strategy_returns = tuple(0.01 + 0.001 * (index % 5) for index in range(53))
    benchmark_returns = tuple(0.006 + 0.002 * (index % 7) for index in range(53))
    with pytest.raises(InputContractError, match="locked"):
        inference_decision(
            _navs(strategy_returns),
            _navs(benchmark_returns),
            screen_a_unlocked=False,
        )
    with pytest.raises(InputContractError, match="no monthly cohort"):
        inference_decision(
            _navs(strategy_returns[:-1]),
            _navs(benchmark_returns[:-1]),
            screen_a_unlocked=True,
        )

    monkeypatch.setattr(
        ADAPTER,
        "paired_stationary_bootstrap_lower_bounds",
        lambda strategy, benchmark: (0.2, 0.1),
    )
    decision = inference_decision(
        _navs(strategy_returns),
        _navs(benchmark_returns),
        screen_a_unlocked=True,
    )
    assert decision.observed_cohorts == 53
    assert decision.all_gates_pass is True
    assert dict(decision.gates) == {
        "local_lower_bound_positive": True,
        "program_lower_bound_positive": True,
    }


@pytest.mark.parametrize(
    ("bounds", "expected"),
    [
        ((0.0, 0.01), False),
        ((-0.01, 0.01), False),
        ((0.2, -0.01), False),
        ((0.2, 0.0), False),
        ((0.2, 0.01), True),
    ],
)
def test_inference_requires_both_strictly_positive_bounds(
    monkeypatch: pytest.MonkeyPatch,
    bounds: tuple[float, float],
    expected: bool,
) -> None:
    strategy = tuple(0.01 + 0.001 * (index % 5) for index in range(53))
    benchmark = tuple(0.006 + 0.002 * (index % 7) for index in range(53))
    monkeypatch.setattr(
        ADAPTER,
        "paired_stationary_bootstrap_lower_bounds",
        lambda left, right: bounds,
    )
    decision = inference_decision(
        _navs(strategy), _navs(benchmark), screen_a_unlocked=True
    )
    assert decision.all_gates_pass is expected


def test_inference_bootstrap_fails_closed_on_zero_variance_or_invalid_replicate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    benchmark = tuple(0.01 if index % 2 else -0.01 for index in range(53))
    with pytest.raises(InputContractError, match="zero standard deviation"):
        paired_stationary_bootstrap_lower_bounds((0.0,) * 53, benchmark)

    strategy = tuple(0.02 if index % 2 else -0.01 for index in range(53))
    monkeypatch.setattr(
        ADAPTER,
        "stationary_bootstrap_indices",
        lambda sample_size=53: ((0,) * 53,),
    )
    with pytest.raises(InputContractError, match="invalid bootstrap replicate"):
        paired_stationary_bootstrap_lower_bounds(strategy, benchmark)


def test_inference_quantiles_use_frozen_linear_interpolation() -> None:
    ordered = [0.0, 1.0, 2.0, 3.0]
    assert ADAPTER._linear_quantile(ordered, 0.05) == pytest.approx(0.15)
    assert ADAPTER._linear_quantile(ordered, 0.015) == pytest.approx(0.045)


def test_target_weight_rejects_observation_after_local_decision_date() -> None:
    decision_at = datetime(2021, 6, 30, 23, tzinfo=timezone.utc)
    future_date = decision_at.date() + timedelta(days=1)
    with pytest.raises(InputContractError):
        target_weight(
            _observation("DGS10", 1.0, observation_date=future_date),
            _observation("DGS3MO", 0.5, observation_date=future_date),
            decision_at=decision_at,
        )


def test_definition_freezes_the_outcome_blind_data_amendment_and_inputs() -> None:
    path = ROOT / "research" / "definitions" / "us_spy_h15_10y3m_state_v1.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["status"] == "PREREGISTERED_NOT_EXECUTED"
    assert record["data_boundary_amendment"] == {
        "original_contemplated_start": "2010-01-01",
        "amended_qualified_start": "2018-01-02",
        "reason": "the exact qualified shared SPY execution input begins in 2018",
        "m119_03_outcomes_read_before_amendment": False,
        "m119_01_aggregate_outcomes_used_for_date_choice": False,
        "amendment_interpretation": (
            "outcome-blind data-feasibility amendment, not preservation of an unchanged "
            "2010 design"
        ),
    }
    assert record["program_multiplicity"]["current_program_alpha"] == 0.015
    assert record["input_identities"]["shared_spy_bundle_sha256"] == (
        "fcf4b487b1b798c6afcfc774339d2066a45238431253e27b14ed5d1a4cc369c9"
    )
    assert record["input_identities"]["h15_signal_input_sha256"] == (
        "998e25841870582b56592ba03fb61ca278b51a9f8141e06e4601c6fde886d1c2"
    )
    assert record["input_identities"]["h15_selection_query_sha256"] == (
        "a80b052fd13e688e90937d5fedac9b70d363e01cd6a3a057e42807bf522b65ab"
    )
    assert record["input_identities"]["h15_selection_proof"] == {
        "algorithm_id": "ALFRED_H15_LATEST_COMMON_ELIGIBLE_OBSERVATION_V1",
        "decisions_verified": 45,
        "mismatch_count": 0,
        "later_eligible_common_count": 0,
    }
    assert record["input_identities"]["shared_core_source_sha256"] == (
        "46ae2fe342a40034b9caacb6cc48a182947a49da9d874de31a1fdb60be0b9a80"
    )
    assert record["screen_a"]["required_complete_cohorts"] == 45
    assert record["inference_b_if_unlocked"]["locked_before_screen_a_pass"] is True
    assert record["boundaries"]["outcome_accessed"] is False
    assert record["strategy_candidate_available"] is False


def test_inference_definition_freezes_exact_inputs_statistics_and_terminal_rules() -> None:
    path = ROOT / "research" / "definitions" / "us_spy_h15_10y3m_state_v1.json"
    payload = path.read_bytes()
    assert hashlib.sha256(payload).hexdigest() == RUNNER.INFERENCE_B_DEFINITION_SHA256
    RUNNER._require_inference_contract(
        payload,
        hashlib.sha256((ROOT / "research/adapters/us_spy_h15_10y3m_state.py").read_bytes()).hexdigest(),
    )
    record = json.loads(payload)
    freeze = record["inference_b_execution_freeze"]
    assert freeze["stage_contract"]["required_complete_cohorts"] == 53
    assert freeze["stage_contract"]["terminal_exit_month"] == "2026-06"
    assert freeze["bootstrap_contract"]["program_alpha"] == 0.015
    assert freeze["terminal_rules"]["rerun_after_any_claim"] is False
    assert record["strategy_candidate_available"] is False


def test_inference_runner_ignores_environment_data_root_redirect(
    tmp_path: Path,
) -> None:
    redirected = tmp_path / "alternate-data-root"
    redirected.mkdir()
    environment = os.environ.copy()
    environment["QUANT_DATA_ROOT"] = str(redirected)
    environment["QUANT_PROJECT_ROOT"] = str(tmp_path / "alternate-project")
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import scripts.run_us_spy_h15_10y3m_state_once as runner; "
                "print(runner.DATA_ROOT)"
            ),
        ],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    assert Path(completed.stdout.strip()) == ROOT.parent / "quant-data"
    assert Path(completed.stdout.strip()) != redirected


def _month_sequence(
    start_year: int,
    start_month: int,
    count: int,
) -> tuple[tuple[int, int], ...]:
    months = []
    year, month = start_year, start_month
    for _ in range(count):
        months.append((year, month))
        month += 1
        if month == 13:
            year += 1
            month = 1
    return tuple(months)


def test_runner_maps_exactly_45_h15_rows_without_substitution() -> None:
    rows = []
    points = []
    for year, month in _month_sequence(2018, 2, 45):
        signal_session = date(year, month, 28)
        decision_at = datetime(year, month, 28, 20, 5, tzinfo=timezone.utc)
        observation_date = signal_session - timedelta(days=1)
        points.append(SimpleNamespace(signal_session=signal_session, decision_at=decision_at))
        rows.append(
            {
                "decision_at": decision_at.isoformat(),
                "signal_month": signal_session.isoformat()[:7],
                "selected_observation_date": observation_date.isoformat(),
                "staleness_days": 1,
                "DGS10": {
                    "value_percent": 1.5,
                    "available_at": decision_at.isoformat(),
                    "row_sha": "1" * 64,
                },
                "DGS3MO": {
                    "value_percent": 0.5,
                    "available_at": decision_at.isoformat(),
                    "row_sha": "2" * 64,
                },
            }
        )
    terminal = SimpleNamespace(
        signal_session=date(2021, 11, 30),
        decision_at=datetime(2021, 11, 30, 20, 5, tzinfo=timezone.utc),
    )
    record = {
        "schema_version": "us-spy-h15-10y3m-state-v1",
        "stage": "validation_input",
        "source_table": "us_macro_research.alfred_h15_yield_observations_research",
        "source_class": "OFFICIAL_ALFRED_H15",
        "spy_bundle_sha256": RUNNER.BASE_BUNDLE_SHA256,
        "row_count": 45,
        "response_set_sha256": (
            "338a8da0720f16045cd3325a5dc07241292c149e836bce1149af3de8bb97cc14"
        ),
        "db_postwrite_sha256": (
            "4e7bd0792241087c7c4da05de32b75a7450baa1dda0342a326ef4c02aa42a92e"
        ),
        "raw_response_sha256": {
            "DGS10": "b59608fa97f00d945292ea77472079d419eee582b0a5ee5af4a2dfa3f5a2f55c",
            "DGS3MO": "6ec27c0460be9365e3648d3f1ed10e4af685aaf232065c1ae19d67cd70766fcf",
        },
        "selection_proof": {
            "algorithm_id": "ALFRED_H15_LATEST_COMMON_ELIGIBLE_OBSERVATION_V1",
            "query_sha256": RUNNER.H15_SELECTION_QUERY_SHA256,
            "replayed_db_sha256": (
                "4e7bd0792241087c7c4da05de32b75a7450baa1dda0342a326ef4c02aa42a92e"
            ),
            "decisions_verified": 45,
            "mismatch_count": 0,
            "later_eligible_common_count": 0,
        },
        "rows": rows,
    }
    payload = json.dumps(record, separators=(",", ":")).encode()

    assert RUNNER._load_h15(payload, tuple(points) + (terminal,)) == (1.0,) * 45
    record["rows"][0]["decision_at"] = terminal.decision_at.isoformat()
    with pytest.raises(RUNNER.InputBlockedError, match="decision mapping"):
        RUNNER._load_h15(
            json.dumps(record, separators=(",", ":")).encode(),
            tuple(points) + (terminal,),
        )


def test_inference_h15_maps_exactly_53_rows_and_rejects_month_drift() -> None:
    rows = []
    points = []
    for year, month in _month_sequence(2021, 12, 53):
        signal_session = date(year, month, 28)
        decision_at = datetime(year, month, 28, 20, 5, tzinfo=timezone.utc)
        observation_date = signal_session - timedelta(days=1)
        points.append(SimpleNamespace(signal_session=signal_session, decision_at=decision_at))
        rows.append(
            {
                "decision_at": decision_at.isoformat(),
                "signal_month": signal_session.isoformat()[:7],
                "selected_observation_date": observation_date.isoformat(),
                "staleness_days": 1,
                "DGS10": {
                    "value_percent": 1.5,
                    "available_at": decision_at.isoformat(),
                    "row_sha": "1" * 64,
                },
                "DGS3MO": {
                    "value_percent": 0.5,
                    "available_at": decision_at.isoformat(),
                    "row_sha": "2" * 64,
                },
            }
        )
    terminal = SimpleNamespace(
        signal_session=date(2026, 5, 29),
        decision_at=datetime(2026, 5, 29, 20, 5, tzinfo=timezone.utc),
    )
    record = {
        "schema_version": "us-spy-h15-10y3m-state-inference-b-v1",
        "stage": "inference_b_input",
        "source_table": "us_macro_research.alfred_h15_yield_observations_research",
        "source_class": "OFFICIAL_ALFRED_H15",
        "runtime_bundle_sha256": RUNNER.INFERENCE_B_BUNDLE_SHA256,
        "row_count": 53,
        "response_set_sha256": (
            "338a8da0720f16045cd3325a5dc07241292c149e836bce1149af3de8bb97cc14"
        ),
        "db_postwrite_sha256": RUNNER.INFERENCE_B_DATABASE_SHA256,
        "raw_response_sha256": {
            "DGS10": "b59608fa97f00d945292ea77472079d419eee582b0a5ee5af4a2dfa3f5a2f55c",
            "DGS3MO": "6ec27c0460be9365e3648d3f1ed10e4af685aaf232065c1ae19d67cd70766fcf",
        },
        "selection_proof": {
            "algorithm_id": "ALFRED_H15_LATEST_COMMON_ELIGIBLE_OBSERVATION_V1",
            "query_sha256": RUNNER.INFERENCE_B_H15_SELECTION_QUERY_SHA256,
            "replayed_db_sha256": RUNNER.INFERENCE_B_DATABASE_SHA256,
            "decisions_verified": 53,
            "mismatch_count": 0,
            "later_eligible_common_count": 0,
        },
        "rows": rows,
    }
    payload = json.dumps(record, separators=(",", ":")).encode()
    kwargs = {
        "schema_version": "us-spy-h15-10y3m-state-inference-b-v1",
        "stage": "inference_b_input",
        "spy_bundle_sha256": RUNNER.INFERENCE_B_BUNDLE_SHA256,
        "row_count": 53,
        "selection_query_sha256": RUNNER.INFERENCE_B_H15_SELECTION_QUERY_SHA256,
        "database_sha256": RUNNER.INFERENCE_B_DATABASE_SHA256,
        "bundle_hash_field": "runtime_bundle_sha256",
    }
    assert RUNNER._load_h15(payload, tuple(points) + (terminal,), **kwargs) == (1.0,) * 53
    record["rows"][1]["signal_month"] = "2022-02"
    with pytest.raises(RUNNER.InputBlockedError, match="signal month mismatch"):
        RUNNER._load_h15(
            json.dumps(record, separators=(",", ":")).encode(),
            tuple(points) + (terminal,),
            **kwargs,
        )


def test_inference_schedule_requires_exact_signal_decision_and_next_open() -> None:
    class Calendar:
        def __init__(self, signal: date, execution: date) -> None:
            self.session_dates = (signal, execution)
            self.execution = execution

        def next_session(self, after: date, *, as_of: datetime) -> SimpleNamespace:
            assert after == self.session_dates[0]
            assert as_of.tzinfo is not None
            return SimpleNamespace(session_date=self.execution)

    timezone_new_york = ZoneInfo("America/New_York")
    points = []
    for index, (year, month) in enumerate(RUNNER.INFERENCE_SIGNAL_MONTHS):
        signal = date(year, month, 28)
        entry_year, entry_month = (
            RUNNER.INFERENCE_ENTRY_MONTHS[index]
            if index < 53
            else (2026, 6)
        )
        execution = date(entry_year, entry_month, 1)
        points.append(
            SimpleNamespace(
                signal_session=signal,
                decision_at=datetime.combine(signal, time(20, 5), timezone_new_york),
                execution_session=execution,
                terminal_exit=index == 53,
                calendar=Calendar(signal, execution),
            )
        )
    frozen = tuple(points)
    RUNNER._require_stage_schedule(
        frozen,
        entry_months=RUNNER.INFERENCE_ENTRY_MONTHS,
        signal_months=RUNNER.INFERENCE_SIGNAL_MONTHS,
        terminal_month=(2026, 6),
    )
    frozen[0].decision_at = datetime.combine(
        frozen[0].signal_session,
        time(20, 6),
        timezone_new_york,
    )
    with pytest.raises(RUNNER.InputBlockedError, match="20:05 ET"):
        RUNNER._require_stage_schedule(
            frozen,
            entry_months=RUNNER.INFERENCE_ENTRY_MONTHS,
            signal_months=RUNNER.INFERENCE_SIGNAL_MONTHS,
            terminal_month=(2026, 6),
        )
    frozen[0].decision_at = datetime.combine(
        frozen[0].signal_session,
        time(20, 5),
        timezone_new_york,
    )
    frozen[0].calendar.session_dates = (
        frozen[0].signal_session,
        frozen[0].signal_session + timedelta(days=1),
        frozen[0].execution_session,
    )
    with pytest.raises(RUNNER.InputBlockedError, match="final accepted session"):
        RUNNER._require_stage_schedule(
            frozen,
            entry_months=RUNNER.INFERENCE_ENTRY_MONTHS,
            signal_months=RUNNER.INFERENCE_SIGNAL_MONTHS,
            terminal_month=(2026, 6),
        )


def test_runner_simulation_keeps_monthly_boundaries_and_stage_chains(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakePortfolio:
        def __init__(self, label: str) -> None:
            self.label = label

        def nav(self, marks: dict[str, float]) -> float:
            return 40_000.0 + marks["SPY"]

    created = []

    def portfolio_factory(capital: float) -> FakePortfolio:
        assert capital == 40_000.0
        label = "strategy" if not created else "benchmark"
        portfolio = FakePortfolio(label)
        created.append(portfolio)
        return portfolio

    calls: list[tuple[str, float | None, str]] = []

    def rebalance(portfolio, point, target, prior_stage_hash, *unused):
        calls.append((portfolio.label, target, prior_stage_hash))
        stage_hash = hashlib.sha256(
            f"{portfolio.label}|{len(calls)}|{prior_stage_hash}".encode()
        ).hexdigest()
        return SimpleNamespace(
            portfolio=portfolio,
            final_nav=40_000.0 + len(calls),
            stage_hash=stage_hash,
        )

    sessions = tuple(date(2018, 3, 1) + timedelta(days=index) for index in range(46))
    points = tuple(
        SimpleNamespace(
            execution_session=session,
            terminal_exit=index == 45,
            execution_input=SimpleNamespace(open_price=100.0 + index),
        )
        for index, session in enumerate(sessions)
    )
    monkeypatch.setattr(RUNNER.Portfolio, "us", staticmethod(portfolio_factory))
    monkeypatch.setattr(RUNNER, "_apply_actions", lambda *args: None)
    monkeypatch.setattr(RUNNER, "_rebalance", rebalance)

    strategy_navs, benchmark_navs, strategy_hashes, benchmark_hashes = RUNNER._simulate(
        points,
        sessions,
        (),
        (1.0,) * 45,
        "3" * 64,
        "4" * 64,
    )

    assert len(strategy_navs) == len(benchmark_navs) == 46
    assert strategy_navs[0] == benchmark_navs[0] == 40_000.0
    assert len(strategy_hashes) == 46
    assert len(benchmark_hashes) == 2
    assert calls[0] == ("strategy", 1.0, "0" * 64)
    assert calls[1] == ("benchmark", 1.0, "0" * 64)
    assert calls[-2][1] is None and calls[-1][1] is None
    assert calls[-1][2] == benchmark_hashes[0]


def test_inference_unlock_recomputes_screen_a_before_any_new_outcome(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    strategy_returns = tuple(0.012 + 0.002 * ((index % 5) - 2) for index in range(45))
    benchmark_returns = tuple(
        0.01 + 0.04 * (1 if index % 2 else -1) for index in range(45)
    )
    strategy_navs = _navs(strategy_returns)
    benchmark_navs = _navs(benchmark_returns)
    decision = screen_decision(strategy_navs, benchmark_navs)
    assert decision.all_gates_pass
    public = tmp_path / "public.json"
    public.write_bytes(b'{"screen_a":"pass"}')
    monkeypatch.setattr(RUNNER, "SCREEN_A_PUBLIC_REPORT", public)
    monkeypatch.setattr(
        RUNNER, "SCREEN_A_PUBLIC_REPORT_SHA256", hashlib.sha256(public.read_bytes()).hexdigest()
    )
    record = {
        "schema_version": "us-spy-h15-10y3m-state-screen-a-private-result-v1",
        "research_id": "US_SPY_H15_10Y3M_STATE_V1",
        "mechanism_id": RUNNER.MECHANISM_ID,
        "program_family_id": RUNNER.PROGRAM_FAMILY_ID,
        "program_alpha": RUNNER.PROGRAM_ALPHA,
        "stage": "RETROSPECTIVE_SECONDARY_SCREEN_A",
        "classification": "RETROSPECTIVE_SECONDARY_SCREEN_A_PASS_INFERENCE_B_UNLOCKED",
        "observed_cohorts": 45,
        "gates": dict(decision.gates),
        "strategy_metrics_hex": {
            key: float(value).hex() for key, value in vars(decision.strategy).items()
        },
        "benchmark_metrics_hex": {
            key: float(value).hex() for key, value in vars(decision.benchmark).items()
        },
        "sharpe_difference_hex": float(decision.sharpe_difference).hex(),
        "strategy_boundary_navs_hex": [float(value).hex() for value in strategy_navs],
        "benchmark_boundary_navs_hex": [float(value).hex() for value in benchmark_navs],
        "identity": {
            "definition_sha256": RUNNER.SCREEN_A_DEFINITION_SHA256,
            "adapter_sha256": RUNNER.SCREEN_A_ADAPTER_SHA256,
            "runner_sha256": RUNNER.SCREEN_A_RUNNER_SHA256,
            "base_bundle_sha256": RUNNER.BASE_BUNDLE_SHA256,
            "h15_input_sha256": RUNNER.H15_INPUT_SHA256,
            "core_commit": RUNNER.CORE_COMMIT,
            "core_tree": RUNNER.CORE_TREE,
            "core_source_sha256": RUNNER.CORE_SOURCE_SHA256,
            "claim_sha256": RUNNER.SCREEN_A_CLAIM_SHA256,
        },
        "one_use_execution_consumed": True,
        "rerun_authorized": False,
        "inference_b_opened": False,
        "strategy_candidate_available": False,
        "shadow": False,
        "paper": False,
        "broker": False,
        "live": False,
    }
    payload = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    RUNNER._require_screen_a_unlocked(payload)
    record["strategy_boundary_navs_hex"][-1] = float(1.0).hex()
    with pytest.raises(RUNNER.InputBlockedError):
        RUNNER._require_screen_a_unlocked(
            json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
        )


def _prepare_inference_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[tuple[str, str], dict[str, Path]]:
    tmp_path.chmod(0o700)
    adapter = tmp_path / "adapter.py"
    runner = tmp_path / "runner.py"
    adapter.write_bytes(b"adapter")
    runner.write_bytes(b"runner")
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    paths = {
        "screen": tmp_path / "screen.json",
        "bundle": tmp_path / "bundle.json",
        "h15": tmp_path / "h15.json",
        "claim": private / "claim.json",
        "result": private / "result.json",
    }
    monkeypatch.setattr(RUNNER, "ADAPTER", adapter)
    monkeypatch.setattr(RUNNER, "RUNNER", runner)
    monkeypatch.setattr(RUNNER, "SCREEN_A_PRIVATE_RESULT", paths["screen"])
    monkeypatch.setattr(RUNNER, "INFERENCE_B_BUNDLE", paths["bundle"])
    monkeypatch.setattr(RUNNER, "INFERENCE_B_H15", paths["h15"])
    monkeypatch.setattr(RUNNER, "INFERENCE_B_CLAIM", paths["claim"])
    monkeypatch.setattr(RUNNER, "INFERENCE_B_RESULT", paths["result"])
    contract = json.loads(
        (ROOT / "research/definitions/us_spy_h15_10y3m_state_v1.json").read_text(
            encoding="utf-8"
        )
    )
    freeze = contract["inference_b_execution_freeze"]
    adapter_sha256 = hashlib.sha256(adapter.read_bytes()).hexdigest()
    freeze["implementation"]["adapter_sha256"] = adapter_sha256
    inference_definition = tmp_path / "inference.json"
    inference_definition.write_text(
        json.dumps(contract, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    monkeypatch.setattr(RUNNER, "DEFINITION", inference_definition)
    monkeypatch.setattr(
        RUNNER,
        "INFERENCE_B_DEFINITION_SHA256",
        hashlib.sha256(inference_definition.read_bytes()).hexdigest(),
    )
    monkeypatch.setattr(RUNNER, "_require_core_identity", lambda: None)
    return (
        adapter_sha256,
        hashlib.sha256(runner.read_bytes()).hexdigest(),
    ), paths


def test_inference_runner_claim_is_consumed_before_fixed_capture_sequence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected, paths = _prepare_inference_runner(tmp_path, monkeypatch)
    captures = []

    def fail_on_h15(path: Path, *args, **kwargs) -> bytes:
        assert paths["claim"].exists()
        captures.append(path)
        if path == paths["h15"]:
            raise RUNNER.InputBlockedError("synthetic capture stop")
        return b"synthetic"

    monkeypatch.setattr(RUNNER, "_capture", fail_on_h15)
    monkeypatch.setattr(RUNNER, "_require_screen_a_unlocked", lambda payload: None)
    with pytest.raises(RUNNER.InputBlockedError, match="identity mismatch"):
        RUNNER._run_inference_once(("0" * 64, expected[1]))
    assert not paths["claim"].exists()

    with pytest.raises(RUNNER.InputBlockedError, match="synthetic capture stop"):
        RUNNER._run_inference_once(expected)
    assert captures == [paths["screen"], paths["bundle"], paths["h15"]]
    assert paths["claim"].stat().st_mode & 0o777 == 0o600
    blocked = json.loads(paths["result"].read_text(encoding="utf-8"))
    assert blocked["classification"] == "INPUT_BLOCKED"
    assert blocked["inference_attempt_consumed"] is True
    assert blocked["inference_outcome_opened"] is True
    assert blocked["rerun_authorized"] is False
    assert blocked["strategy_candidate_available"] is False
    with pytest.raises(RUNNER.InputBlockedError, match="must be absent"):
        RUNNER._run_inference_once(expected)
    assert captures == [paths["screen"], paths["bundle"], paths["h15"]]


@pytest.mark.parametrize(
    ("passes", "classification"),
    [
        (True, "RETROSPECTIVE_SECONDARY_PASS_PENDING_EXTERNAL_REVIEW"),
        (False, "RETROSPECTIVE_SECONDARY_INFERENCE_B_FAIL"),
    ],
)
def test_inference_runner_publishes_only_private_aggregate_terminal_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    passes: bool,
    classification: str,
) -> None:
    expected, paths = _prepare_inference_runner(tmp_path, monkeypatch)
    monkeypatch.setattr(RUNNER, "_capture", lambda *args, **kwargs: b"synthetic")
    monkeypatch.setattr(RUNNER, "_require_screen_a_unlocked", lambda payload: None)
    monkeypatch.setattr(
        RUNNER,
        "_load_bundle",
        lambda payload, **kwargs: (
            object(),
            (object(),) * 54,
            (date(2022, 1, 1),) * 1106,
            (),
        ),
    )
    monkeypatch.setattr(
        RUNNER,
        "_load_h15",
        lambda payload, points, **kwargs: (1.0,) * 53,
    )
    navs = tuple(40_000.0 + index for index in range(54))
    def simulate_with_frozen_definition(*args):
        assert args[-2] == RUNNER.INFERENCE_B_DEFINITION_SHA256
        return navs, navs, ("1" * 64,) * 54, ("2" * 64,) * 2

    monkeypatch.setattr(RUNNER, "_simulate", simulate_with_frozen_definition)
    metrics = SimpleNamespace(
        monthly_arithmetic_mean=0.01,
        monthly_sample_stdev=0.02,
        sharpe=0.5,
        annualized_volatility=0.07,
        compounded_net_return=0.1,
        maximum_drawdown=-0.05,
    )
    decision = SimpleNamespace(
        all_gates_pass=passes,
        observed_cohorts=53,
        gates=(
            ("local_lower_bound_positive", passes),
            ("program_lower_bound_positive", passes),
        ),
        strategy=metrics,
        benchmark=metrics,
        observed_sharpe_difference=0.1,
        local_lower_bound=0.02 if passes else -0.01,
        program_lower_bound=0.01 if passes else -0.02,
    )
    monkeypatch.setattr(RUNNER, "inference_decision", lambda *args, **kwargs: decision)

    RUNNER._run_inference_once(expected)
    published = json.loads(paths["result"].read_text(encoding="utf-8"))
    assert published["classification"] == classification
    assert published["strategy_candidate_available"] is False
    assert published["inference_outcome_opened"] is True
    assert published["rerun_authorized"] is False
    assert published["observed_cohorts"] == 53
    assert len(published["strategy_boundary_navs_hex"]) == 54
    text = paths["result"].read_text(encoding="utf-8")
    assert "raw_open" not in text
    assert "value_percent" not in text
    assert "selected_observation_date" not in text
    assert paths["claim"].stat().st_mode & 0o777 == 0o600


def test_invalid_inference_statistic_is_terminal_fail_not_input_blocked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected, paths = _prepare_inference_runner(tmp_path, monkeypatch)
    monkeypatch.setattr(RUNNER, "_capture", lambda *args, **kwargs: b"synthetic")
    monkeypatch.setattr(RUNNER, "_require_screen_a_unlocked", lambda payload: None)
    monkeypatch.setattr(
        RUNNER,
        "_load_bundle",
        lambda payload, **kwargs: (
            object(),
            (object(),) * 54,
            (date(2022, 1, 1),) * 1106,
            (),
        ),
    )
    monkeypatch.setattr(
        RUNNER,
        "_load_h15",
        lambda payload, points, **kwargs: (1.0,) * 53,
    )
    navs = tuple(40_000.0 + index for index in range(54))
    monkeypatch.setattr(
        RUNNER,
        "_simulate",
        lambda *args: (navs, navs, ("1" * 64,) * 54, ("2" * 64,) * 2),
    )

    def invalid(*args, **kwargs):
        raise InputContractError("zero standard deviation")

    monkeypatch.setattr(RUNNER, "inference_decision", invalid)
    RUNNER._run_inference_once(expected)
    published = json.loads(paths["result"].read_text(encoding="utf-8"))
    assert published["classification"] == "RETROSPECTIVE_SECONDARY_INFERENCE_B_FAIL"
    assert published["inference_failure_reason"] == (
        "FAIL_CLOSED_INVALID_INFERENCE_STATISTIC"
    )
    assert published["rerun_authorized"] is False


def test_runner_capture_and_json_fail_closed_on_identity_or_parser_drift(
    tmp_path: Path,
) -> None:
    tmp_path.chmod(0o700)
    path = tmp_path / "input.json"
    payload = b'{"fixed":true}'
    path.write_bytes(payload)
    path.chmod(0o600)
    assert RUNNER._capture(path, hashlib.sha256(payload).hexdigest(), max_bytes=1024) == payload
    with pytest.raises(RUNNER.InputBlockedError, match="SHA-256 mismatch"):
        RUNNER._capture(path, "0" * 64, max_bytes=1024)
    with pytest.raises(RUNNER.InputBlockedError, match="duplicate JSON key"):
        RUNNER._json(b'{"stage":1,"stage":2}', "synthetic")
    with pytest.raises(RUNNER.InputBlockedError, match="nonfinite JSON constant"):
        RUNNER._json(b'{"value":NaN}', "synthetic")


def test_runner_rejects_shared_core_drift_before_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        RUNNER,
        "_core_source_identity",
        lambda: (RUNNER.CORE_SOURCE_FILE_COUNT, "0" * 64),
    )
    with pytest.raises(RUNNER.InputBlockedError, match="shared-core source bytes"):
        RUNNER._require_core_identity()


def test_runner_rejects_symlinked_private_result_parent(tmp_path: Path) -> None:
    real_parent = tmp_path / "private"
    real_parent.mkdir(mode=0o700)
    linked_parent = tmp_path / "linked"
    linked_parent.symlink_to(real_parent, target_is_directory=True)
    with pytest.raises(RUNNER.InputBlockedError, match="owner-private directory"):
        RUNNER._target(linked_parent / "result.json")
