from __future__ import annotations

import ast
import importlib.util
import json
import math
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parents[1]
ADAPTER_PATH = ROOT / "research" / "adapters" / "us_spy_volatility_managed.py"
REPORT_PATH = ROOT / "research" / "reports" / "us_spy_volatility_managed_exposure_v1.json"
NY = ZoneInfo("America/New_York")
SOURCE_HASH = "a" * 64
OFFICIAL_HASH = "b" * 64

SPEC = importlib.util.spec_from_file_location("us_spy_volatility_managed", ADAPTER_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _synthetic_closes(first: date = date(2024, 1, 2)) -> tuple[object, ...]:
    observations = []
    for index in range(22):
        session = first + timedelta(days=index)
        close_at = datetime.combine(session, datetime.min.time(), NY).replace(hour=16)
        available_at = close_at + timedelta(minutes=1)
        raw_close = 100.0 + index * 0.4 + (index % 4) * 0.15
        observations.append(
            MODULE.CloseObservation(
                session_date=session,
                close_at=close_at,
                available_at=available_at,
                raw_close=raw_close,
                source_sha256=SOURCE_HASH,
            )
        )
    return tuple(observations)


def _decision_at(closes: tuple[object, ...]) -> datetime:
    return datetime.combine(closes[-1].session_date, datetime.min.time(), NY).replace(
        hour=20,
        minute=5,
    )


def _distribution(ex_date: date, *, official: float = 1.636431, tiingo: float = 1.633485):
    return MODULE.CashDistribution(
        ex_date=ex_date,
        record_date=ex_date + timedelta(days=1),
        payment_date=ex_date + timedelta(days=7),
        information_available_at=datetime.combine(ex_date, datetime.min.time(), NY).replace(
            hour=9,
            minute=30,
        ),
        official_amount=official,
        currency="USD",
        amount_unit="PER_SHARE",
        tiingo_comparison_amount=tiingo,
        source_sha256=OFFICIAL_HASH,
    )


def test_preregistration_freezes_qualified_but_unexecuted_state() -> None:
    record = json.loads(REPORT_PATH.read_text(encoding="utf-8"))

    assert record["research_id"] == "US_SPY_VOLATILITY_MANAGED_EXPOSURE_V1"
    assert record["status"] == "PREREGISTERED_NOT_EXECUTED"
    evidence = record["input_qualification_evidence"]
    assert (
        evidence["qualification_status"]
        == "INPUT_QUALIFIED_RETROSPECTIVE_RESEARCH_GRADE_PENDING_SHARED_P0"
    )
    assert evidence["tiingo_raw_eod"]["rows"] == 2134
    assert evidence["tiingo_raw_eod"]["raw_open_nonnull"] == 2134
    assert evidence["tiingo_raw_eod"]["raw_close_nonnull"] == 2134
    assert evidence["tiingo_raw_eod"]["row_hash_nonnull"] == 2134
    assert evidence["tiingo_raw_eod"]["row_hash_unique"] == 2134
    assert evidence["xnys_calendar"]["exact_date_parity"] is True
    distributions = evidence["official_state_street_distributions"]
    assert distributions["events"] == 34
    comparison = distributions["tiingo_amount_comparison"]
    assert comparison["exact_matches"] == 26
    assert comparison["rounding_differences"] == 7
    assert comparison["material_conflicts"] == 1
    assert comparison["material_conflict"] == {
        "ex_date": "2021-12-17",
        "official_amount": 1.636431,
        "tiingo_amount": 1.633485,
        "difference_official_minus_tiingo": 0.002946,
    }
    assert distributions["tiingo_amount_comparison"]["resolution"].startswith(
        "official State Street value controls"
    )
    assert evidence["external_acceptance_claimed"] is False
    assert record["strategy_candidate_available"] is False
    assert record["adjudication"]["outcome_accessed"] is False
    frozen = record["outcome_blind_frozen_specification"]
    assert frozen["instrument_selection"].startswith("fixed before outcome access")
    assert frozen["splits"]["validation_entry_cohorts"]["required_count"] == 45
    assert frozen["splits"]["purged_entry_cohort"] == "2021-12"
    assert frozen["splits"]["retrospective_holdout_entry_cohorts"]["required_count"] == 53
    assert frozen["splits"]["holdout_access_rule"].startswith("open exactly once")
    inference = frozen["holdout_primary_inference"]
    assert inference["resamples"] == 10_000
    assert inference["seed"] == 4601
    assert inference["expected_block_length_months"] == 6
    assert inference["restart_probability"] == "1/6"
    assert inference["quantile"] == "linear-interpolated 5th percentile"
    assert frozen["portfolio"]["one_way_slippage_bps"] == 10
    assert frozen["portfolio"]["commission_rate"] == 0.0
    assert evidence["database_snapshot"]["sha256_before"] == (
        "f7d35377a9c66e2b0ffd7d0201a6e3954a79df25b3e0b8f36904df1cfef1eeb0"
    )
    assert evidence["database_snapshot"]["sha256_before"] == evidence[
        "database_snapshot"
    ]["sha256_after"]
    serialized = REPORT_PATH.read_text(encoding="utf-8")
    assert "current_input_identity_permanently_forbidden_for_outcome_execution" not in serialized
    assert '"decisive_blockers"' not in serialized


def test_total_return_signal_uses_official_amount_not_tiingo_comparison() -> None:
    closes = _synthetic_closes()
    action_index = 10
    action = _distribution(closes[action_index].session_date)

    returns = MODULE.total_return_log_returns(
        closes,
        distributions=(action,),
        decision_at=_decision_at(closes),
    )

    expected = math.log(
        (closes[action_index].raw_close + action.official_amount)
        / closes[action_index - 1].raw_close
    )
    comparison_based = math.log(
        (closes[action_index].raw_close + action.tiingo_comparison_amount)
        / closes[action_index - 1].raw_close
    )
    assert len(returns) == 21
    assert returns[action_index - 1] == pytest.approx(expected)
    assert returns[action_index - 1] != pytest.approx(comparison_based, abs=1e-9)


def test_raw_close_must_be_available_by_the_frozen_decision() -> None:
    closes = list(_synthetic_closes())
    decision_at = _decision_at(tuple(closes))
    final = closes[-1]
    closes[-1] = MODULE.CloseObservation(
        session_date=final.session_date,
        close_at=final.close_at,
        available_at=decision_at + timedelta(microseconds=1),
        raw_close=final.raw_close,
        source_sha256=final.source_sha256,
    )

    with pytest.raises(MODULE.InputContractError, match="available by decision_at"):
        MODULE.total_return_log_returns(tuple(closes), decision_at=decision_at)


def test_decision_time_is_exact_and_latest_close_matches_decision_session() -> None:
    closes = _synthetic_closes()
    with pytest.raises(MODULE.InputContractError, match="20:05"):
        MODULE.total_return_log_returns(
            closes,
            decision_at=_decision_at(closes) + timedelta(microseconds=1),
        )


@pytest.mark.parametrize("first", [date(2024, 1, 2), date(2024, 7, 1)])
def test_decision_time_contract_works_in_standard_and_daylight_time(first: date) -> None:
    closes = _synthetic_closes(first)
    returns = MODULE.total_return_log_returns(closes, decision_at=_decision_at(closes))
    assert len(returns) == 21

    with pytest.raises(MODULE.InputContractError, match="decision session"):
        MODULE.total_return_log_returns(
            closes,
            decision_at=_decision_at(closes) + timedelta(days=1),
        )


def test_distribution_information_entitlement_and_cash_credit_are_distinct() -> None:
    closes = _synthetic_closes()
    action = _distribution(closes[8].session_date)
    entitlement = MODULE.distribution_entitlement(action, 17)

    assert action.information_available_at.hour == 9
    assert action.information_available_at.minute == 30
    assert entitlement.ex_date == action.ex_date
    assert entitlement.entitled_shares == 17
    assert MODULE.cash_credit_on(entitlement, action.ex_date) == 0.0
    assert MODULE.cash_credit_on(entitlement, action.record_date) == 0.0
    assert MODULE.cash_credit_on(entitlement, action.payment_date) == pytest.approx(
        17 * action.official_amount
    )
    assert MODULE.cash_credit_on(entitlement, action.payment_date + timedelta(days=1)) == 0.0


def test_distribution_availability_must_equal_ex_date_open() -> None:
    ex_date = date(2024, 1, 10)
    with pytest.raises(MODULE.InputContractError, match="ex-date XNYS open"):
        MODULE.CashDistribution(
            ex_date=ex_date,
            record_date=ex_date + timedelta(days=1),
            payment_date=ex_date + timedelta(days=7),
            information_available_at=datetime.combine(
                ex_date,
                datetime.min.time(),
                NY,
            ).replace(hour=9, minute=31),
            official_amount=1.0,
            currency="USD",
            amount_unit="PER_SHARE",
            source_sha256=OFFICIAL_HASH,
        )


@pytest.mark.parametrize(
    ("currency", "amount_unit", "message"),
    [("EUR", "PER_SHARE", "currency"), ("USD", "CENTS_PER_SHARE", "amount_unit")],
)
def test_distribution_currency_and_unit_are_exact(
    currency: str,
    amount_unit: str,
    message: str,
) -> None:
    ex_date = date(2024, 1, 10)
    with pytest.raises(MODULE.InputContractError, match=message):
        MODULE.CashDistribution(
            ex_date=ex_date,
            record_date=ex_date + timedelta(days=1),
            payment_date=ex_date + timedelta(days=7),
            information_available_at=datetime.combine(
                ex_date,
                datetime.min.time(),
                NY,
            ).replace(hour=9, minute=30),
            official_amount=1.0,
            currency=currency,
            amount_unit=amount_unit,
            source_sha256=OFFICIAL_HASH,
        )


def test_nonfinite_inputs_and_zero_volatility_fail_closed() -> None:
    closes = _synthetic_closes()
    with pytest.raises(MODULE.InputContractError, match="finite"):
        MODULE.CloseObservation(
            session_date=closes[0].session_date,
            close_at=closes[0].close_at,
            available_at=closes[0].available_at,
            raw_close=float("nan"),
            source_sha256=SOURCE_HASH,
        )
    with pytest.raises(MODULE.InputContractError, match="finite and positive"):
        MODULE.annualized_realized_volatility((0.0,) * 21)
    with pytest.raises(MODULE.InputContractError, match="finite"):
        MODULE.target_weight(float("inf"))
    with pytest.raises(MODULE.InputContractError, match="not boolean"):
        _distribution(closes[8].session_date, official=True)
    assert MODULE.target_weight(0.05) == 1.0
    assert MODULE.target_weight(0.20) == pytest.approx(0.5)


def test_rebalance_is_whole_share_unlevered_and_independent_of_execution_open() -> None:
    closes = _synthetic_closes()
    decision_at = _decision_at(closes)
    request = MODULE.form_monthly_rebalance(40_000.0, closes, decision_at=decision_at)

    assert 0.0 < request.target_weight <= 1.0
    assert request.sizing_price == closes[-1].raw_close
    assert request.requested_shares == math.floor(
        40_000.0 * request.target_weight / closes[-1].raw_close
    )

    execution_date = closes[-1].session_date + timedelta(days=1)
    low_open = MODULE.observe_execution_fill(
        request,
        execution_session_date=execution_date,
        raw_open=10.0,
        source_sha256=SOURCE_HASH,
    )
    high_open = MODULE.observe_execution_fill(
        request,
        execution_session_date=execution_date,
        raw_open=500.0,
        source_sha256=SOURCE_HASH,
    )
    assert low_open.requested_shares == high_open.requested_shares == request.requested_shares


def test_duplicate_or_mixed_same_session_actions_fail_closed() -> None:
    closes = _synthetic_closes()
    ex_date = closes[9].session_date
    first = _distribution(ex_date)
    second = _distribution(ex_date, official=1.0, tiingo=1.0)
    split = MODULE.SplitEvent(
        ex_date=ex_date,
        information_available_at=first.information_available_at,
        factor=2.0,
        source_sha256=OFFICIAL_HASH,
    )
    second_split = MODULE.SplitEvent(
        ex_date=ex_date,
        information_available_at=first.information_available_at,
        factor=3.0,
        source_sha256=OFFICIAL_HASH,
    )

    with pytest.raises(MODULE.InputContractError, match="multiple ordinary actions"):
        MODULE.total_return_log_returns(
            closes,
            distributions=(first, second),
            decision_at=_decision_at(closes),
        )
    with pytest.raises(MODULE.InputContractError, match="multiple ordinary actions"):
        MODULE.total_return_log_returns(
            closes,
            distributions=(first,),
            splits=(split,),
            decision_at=_decision_at(closes),
        )
    with pytest.raises(MODULE.InputContractError, match="multiple ordinary actions"):
        MODULE.total_return_log_returns(
            closes,
            splits=(split, second_split),
            decision_at=_decision_at(closes),
        )


def test_split_factor_is_applied_once_and_window_external_actions_are_rejected() -> None:
    closes = _synthetic_closes()
    action_index = 11
    ex_date = closes[action_index].session_date
    available_at = datetime.combine(ex_date, datetime.min.time(), NY).replace(
        hour=9,
        minute=30,
    )
    split = MODULE.SplitEvent(
        ex_date=ex_date,
        information_available_at=available_at,
        factor=2.0,
        source_sha256=OFFICIAL_HASH,
    )

    returns = MODULE.total_return_log_returns(
        closes,
        splits=(split,),
        decision_at=_decision_at(closes),
    )
    expected = math.log(
        2.0 * closes[action_index].raw_close / closes[action_index - 1].raw_close
    )
    assert returns[action_index - 1] == pytest.approx(expected)
    assert returns[action_index] == pytest.approx(
        math.log(closes[action_index + 1].raw_close / closes[action_index].raw_close)
    )

    outside = MODULE.SplitEvent(
        ex_date=closes[0].session_date,
        information_available_at=datetime.combine(
            closes[0].session_date,
            datetime.min.time(),
            NY,
        ).replace(hour=9, minute=30),
        factor=2.0,
        source_sha256=OFFICIAL_HASH,
    )
    with pytest.raises(MODULE.InputContractError, match="return-period session"):
        MODULE.total_return_log_returns(
            closes,
            splits=(outside,),
            decision_at=_decision_at(closes),
        )


def test_public_result_records_reject_forged_values() -> None:
    decision_at = datetime(2024, 1, 31, 20, 5, tzinfo=NY)
    with pytest.raises(MODULE.InputContractError, match="cannot exceed one"):
        MODULE.RebalanceRequest(decision_at, 2.0, 1, 100.0, 0.05)
    with pytest.raises(MODULE.InputContractError, match="requested_shares"):
        MODULE.ExecutionFillObservation(date(2024, 2, 1), 100.0, -7, SOURCE_HASH)
    with pytest.raises(MODULE.InputContractError, match="total_cash"):
        MODULE.DistributionEntitlement(
            date(2024, 1, 10),
            date(2024, 1, 17),
            10,
            1.0,
            float("inf"),
            OFFICIAL_HASH,
        )


def test_adapter_has_no_io_database_or_network_surface() -> None:
    tree = ast.parse(ADAPTER_PATH.read_text(encoding="utf-8"))
    imported_roots: set[str] = set()
    called_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            called_names.add(node.func.id)

    assert imported_roots <= {
        "__future__",
        "dataclasses",
        "datetime",
        "math",
        "re",
        "statistics",
        "zoneinfo",
    }
    assert not ({"open", "exec", "eval", "compile"} & called_names)
