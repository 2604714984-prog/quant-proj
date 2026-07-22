from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.run_us_spy_h15_10y3m_state_once as RUNNER
from research.adapters.us_spy_h15_10y3m_state import (
    InputContractError,
    RateObservation,
    cohort_returns,
    screen_decision,
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


def test_runner_claim_is_consumed_before_any_input_capture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path.chmod(0o700)
    definition = tmp_path / "definition.json"
    adapter = tmp_path / "adapter.py"
    runner = tmp_path / "runner.py"
    definition.write_text('{"status":"PREREGISTERED_NOT_EXECUTED"}', encoding="utf-8")
    adapter.write_bytes(b"adapter")
    runner.write_bytes(b"runner")
    monkeypatch.setattr(RUNNER, "DEFINITION", definition)
    monkeypatch.setattr(RUNNER, "ADAPTER", adapter)
    monkeypatch.setattr(RUNNER, "RUNNER", runner)
    claim = tmp_path / "claim.json"
    result = tmp_path / "result.json"
    captures = []

    def fail_capture(*args, **kwargs):
        assert claim.exists()
        captures.append(args[0])
        raise RUNNER.InputBlockedError("synthetic capture stop")

    monkeypatch.setattr(RUNNER, "_capture", fail_capture)
    expected = tuple(
        hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (definition, adapter, runner)
    )
    mismatch_claim = tmp_path / "mismatch-claim.json"
    with pytest.raises(RUNNER.InputBlockedError, match="identity mismatch"):
        RUNNER._run_once(
            tmp_path / "bundle.json",
            tmp_path / "h15.json",
            mismatch_claim,
            tmp_path / "mismatch-result.json",
            ("0" * 64, expected[1], expected[2]),
        )
    assert not mismatch_claim.exists()

    with pytest.raises(RUNNER.InputBlockedError, match="synthetic capture stop"):
        RUNNER._run_once(
            tmp_path / "bundle.json",
            tmp_path / "h15.json",
            claim,
            result,
            expected,
        )
    assert captures == [tmp_path / "bundle.json"]
    assert claim.stat().st_mode & 0o777 == 0o600
    blocked = json.loads(result.read_text(encoding="utf-8"))
    assert blocked["classification"] == "INPUT_BLOCKED"
    assert blocked["error_type"] == "InputBlockedError"
    assert blocked["strategy_candidate_available"] is False
    with pytest.raises(RUNNER.InputBlockedError, match="must be absent"):
        RUNNER._run_once(
            tmp_path / "bundle.json",
            tmp_path / "h15.json",
            claim,
            result,
            expected,
        )
    assert captures == [tmp_path / "bundle.json"]


def test_runner_publishes_only_private_aggregate_terminal_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path.chmod(0o700)
    definition = tmp_path / "definition.json"
    adapter = tmp_path / "adapter.py"
    runner = tmp_path / "runner.py"
    definition.write_text('{"status":"PREREGISTERED_NOT_EXECUTED"}', encoding="utf-8")
    adapter.write_bytes(b"adapter")
    runner.write_bytes(b"runner")
    monkeypatch.setattr(RUNNER, "DEFINITION", definition)
    monkeypatch.setattr(RUNNER, "ADAPTER", adapter)
    monkeypatch.setattr(RUNNER, "RUNNER", runner)
    monkeypatch.setattr(RUNNER, "_capture", lambda *args, **kwargs: b"synthetic")
    monkeypatch.setattr(
        RUNNER,
        "_load_bundle",
        lambda payload: (object(), (object(),) * 46, (), ()),
    )
    monkeypatch.setattr(RUNNER, "_load_h15", lambda payload, points: (1.0,) * 45)
    navs = tuple(40_000.0 + index for index in range(46))
    monkeypatch.setattr(
        RUNNER,
        "_simulate",
        lambda *args: (navs, navs, ("1" * 64,) * 46, ("2" * 64,) * 2),
    )
    metrics = SimpleNamespace(
        monthly_arithmetic_mean=0.01,
        monthly_sample_stdev=0.02,
        sharpe=0.5,
        annualized_volatility=0.07,
        compounded_net_return=0.1,
        maximum_drawdown=-0.05,
    )
    decision = SimpleNamespace(
        all_gates_pass=False,
        observed_cohorts=45,
        gates=(
            ("sharpe_difference_positive", False),
            ("strategy_compounded_net_return_positive", True),
            ("strategy_annualized_volatility_lower", True),
            ("strategy_maximum_drawdown_better", True),
        ),
        strategy=metrics,
        benchmark=metrics,
        sharpe_difference=-0.1,
    )
    monkeypatch.setattr(RUNNER, "screen_decision", lambda *args: decision)
    expected = tuple(
        hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (definition, adapter, runner)
    )
    claim = tmp_path / "claim.json"
    result = tmp_path / "result.json"

    RUNNER._run_once(
        tmp_path / "bundle.json",
        tmp_path / "h15.json",
        claim,
        result,
        expected,
    )
    published = json.loads(result.read_text(encoding="utf-8"))
    assert published["classification"] == "RETROSPECTIVE_SECONDARY_SCREEN_A_FAIL"
    assert published["strategy_candidate_available"] is False
    assert published["inference_b_opened"] is False
    assert published["rerun_authorized"] is False
    assert published["observed_cohorts"] == 45
    assert "raw_open" not in result.read_text(encoding="utf-8")
    assert "value_percent" not in result.read_text(encoding="utf-8")
    assert claim.stat().st_mode & 0o777 == 0o600


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
