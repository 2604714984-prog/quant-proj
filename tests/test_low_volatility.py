from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from quant_system.data import AcceptedSession, AcceptedSessionCalendar, SourceIdentity
from quant_system.research import low_volatility as lv


ROOT = Path(__file__).resolve().parents[1]
DEFINITION = ROOT / "research/definitions/a_share_defensive_low_volatility_v1.json"
UTC = timezone.utc


def _source(label: str, available_at: datetime | None = None) -> SourceIdentity:
    available = available_at or datetime(2000, 1, 1, tzinfo=UTC)
    return SourceIdentity(
        f"https://example.test/{label}",
        hashlib.sha256(label.encode()).hexdigest(),
        available,
        max(available, datetime(2024, 6, 1, tzinfo=UTC)),
        label,
    )


def _calendar(dates: tuple[date, ...]) -> AcceptedSessionCalendar:
    zone = ZoneInfo("Asia/Shanghai")
    source = _source("calendar")
    return AcceptedSessionCalendar(
        tuple(
            AcceptedSession(
                day,
                datetime.combine(day, time(9, 30), zone),
                datetime.combine(day, time(15), zone),
                source,
                "Asia/Shanghai",
            )
            for day in dates
        )
    )


def _fixture() -> tuple[
    tuple[lv.SignalBar, ...],
    AcceptedSessionCalendar,
    dict[date, datetime],
    tuple[lv.ExecutionRow, ...],
]:
    dates = tuple(date(2024, 1, 1) + timedelta(days=index) for index in range(122))
    calendar = _calendar(dates)
    decision = dates[-2]
    decision_at = calendar.session_on(
        decision, as_of=datetime(2024, 1, 1, tzinfo=UTC)
    ).close_at + timedelta(minutes=30)
    source = _source("signals")
    rows: list[lv.SignalBar] = []
    for symbol_index in range(20):
        symbol = f"{symbol_index:06d}.SZ"
        tri = 100.0
        amplitude = (symbol_index + 1) * 0.0001
        for index, day in enumerate(dates[:-1]):
            if index:
                tri *= 1.0 + 0.0002 + amplitude * (-1.0 if index % 2 else 1.0)
            rows.append(
                lv.SignalBar(
                    day,
                    symbol,
                    tri,
                    25_000_000.0,
                    "CNY",
                    300 + index,
                    True,
                    False,
                    False,
                    False,
                    "COMMON_A",
                    "SZSE_MAIN",
                    source,
                )
            )
    execution = tuple(
        lv.ExecutionRow(
            dates[-1],
            f"{index:06d}.SZ",
            10.0,
            "CNY",
            "SHARES",
            _source(f"execution-{index}"),
        )
        for index in range(20)
    )
    return tuple(rows), calendar, {decision: decision_at}, execution


def _health(**changes: object) -> lv.PreflightHealth:
    values = {
        "benchmark_symbol": lv.BENCHMARK_SYMBOL,
        "benchmark_initial_entry_filled": True,
        "benchmark_invested_ratio": 0.99,
        "capacity_rejection_ratio": 0.01,
        "unexpected_exception_count": 0,
        "currency_unit": "CNY",
        "position_unit": "SHARES",
    }
    values.update(changes)
    return lv.PreflightHealth(**values)  # type: ignore[arg-type]


def test_definition_freezes_variants_splits_inference_and_boundaries() -> None:
    definition = json.loads(DEFINITION.read_text())

    assert lv.DEFINITION_PATH == Path("research/definitions/a_share_defensive_low_volatility_v1.json")
    assert hashlib.sha256(DEFINITION.read_bytes()).hexdigest() == lv.DEFINITION_SHA256
    assert definition["status"] == "PREREGISTERED_NOT_EXECUTED"
    assert definition["capital_and_execution"]["benchmark"] == "510300.SH"
    assert tuple(item["variant_id"] for item in definition["variants_in_exact_order"]) == (
        "LV60",
        "LV120",
        "DSV60",
        "DSV120",
    )
    assert definition["historical_test_family"] == {
        "family_size": 8,
        "order": "variant order 1..4, then validation_2022_2023 followed by retrospective_holdout_2024_2026h1",
        "family_alpha": 0.05,
        "bonferroni_alpha_per_test": 0.00625,
        "bootstrap": {
            "series": "chronologically ordered complete monthly strategy net returns",
            "method": "circular block bootstrap",
            "block_length_months": 3,
            "draws": 10000,
            "seed": 20260717,
            "lower_bound": "linear quantile at 0.00625 of bootstrap mean monthly net returns",
        },
    }
    assert len(definition["gates_per_variant_and_historical_split"]) == 8
    assert definition["execution"] == {
        "real_data_authorized": False,
        "outcome_access_authorized": False,
        "network_authorized": False,
        "database_write_authorized": False,
        "execution_authorized": False,
        "prospective_outcomes_opened": False,
        "gate_counts": None,
        "strategy_candidate_available": False,
    }


def test_score_formulas_are_exact_and_annualized() -> None:
    alternating = tuple(0.01 if index % 2 else -0.02 for index in range(120))
    lv60 = next(item for item in lv.VARIANTS if item.variant_id == "LV60")
    dsv60 = next(item for item in lv.VARIANTS if item.variant_id == "DSV60")
    values = alternating[-60:]
    mean = math.fsum(values) / 60
    expected_lv = math.sqrt(math.fsum((x - mean) ** 2 for x in values) / 59) * math.sqrt(252)
    expected_dsv = math.sqrt(math.fsum(min(x, 0) ** 2 for x in values) / 60) * math.sqrt(252)

    assert lv._score(alternating, lv60) == pytest.approx(expected_lv)
    assert lv._score(alternating, dsv60) == pytest.approx(expected_dsv)


def test_targets_use_exact_order_ascending_score_symbol_and_equal_weights() -> None:
    rows, calendar, decisions, execution = _fixture()
    targets = lv.build_monthly_targets(
        rows,
        calendar,
        decision_at_by_session=decisions,
        execution_rows=execution,
    )

    assert tuple(item.variant_id for item in targets) == (
        "LV60",
        "LV120",
        "DSV60",
        "DSV120",
    )
    assert all(item.eligible_count == 20 and item.candidate_count == 20 for item in targets)
    assert all(item.selected_symbols == tuple(f"{i:06d}.SZ" for i in range(15)) for item in targets)
    assert all(
        item.selected_scores == tuple(sorted(item.selected_scores, key=lambda x: (x[1], x[0])))
        for item in targets
    )
    assert all(item.target_weights == tuple((symbol, 1 / 15) for symbol in item.selected_symbols) for item in targets)


def test_preflight_is_aggregate_only_deterministic_and_candidate_false() -> None:
    rows, calendar, decisions, execution = _fixture()
    first = lv.build_preflight_report(
        rows,
        calendar,
        decision_at_by_session=decisions,
        execution_rows=execution,
        health=_health(),
    )
    second = lv.build_preflight_report(
        rows[::-1],
        calendar,
        decision_at_by_session=decisions,
        execution_rows=execution[::-1],
        health=_health(),
    )

    assert first == second
    assert first["status"] == "PREFLIGHT_PASS"
    assert first["decision_date_count"] == 1
    assert first["min_eligible_count"] == first["max_eligible_count"] == 20
    assert first["min_candidate_count"] == first["max_candidate_count"] == 20
    assert first["decision_invalid_count"] == 0
    assert first["benchmark_initial_entry_filled"] is True
    assert first["currency_unit"] == "CNY" and first["position_unit"] == "SHARES"
    assert first["strategy_candidate_available"] is False
    definition = json.loads(DEFINITION.read_text())
    assert set(first) == set(definition["preflight"]["allowed_fields"])
    forbidden = ("symbol", "return", "nav", "sharpe", "gate")
    assert not any(token in key.lower() for key in first for token in forbidden)


def test_missing_selected_execution_blocks_without_replacement() -> None:
    rows, calendar, decisions, execution = _fixture()
    missing = tuple(row for row in execution if row.symbol != "000000.SZ")

    assert lv.build_monthly_targets(
        rows,
        calendar,
        decision_at_by_session=decisions,
        execution_rows=missing,
    ) == ()
    report = lv.build_preflight_report(
        rows,
        calendar,
        decision_at_by_session=decisions,
        execution_rows=missing,
        health=_health(),
    )
    assert report["status"] == "PREFLIGHT_BLOCKED"
    assert report["decision_invalid_count"] == 4


def test_benchmark_fill_and_unexpected_exceptions_hard_block() -> None:
    rows, calendar, decisions, execution = _fixture()
    with pytest.raises(lv.LowVolatilityContractError, match="benchmark initial entry"):
        lv.build_preflight_report(
            rows,
            calendar,
            decision_at_by_session=decisions,
            execution_rows=execution,
            health=_health(benchmark_initial_entry_filled=False),
        )
    with pytest.raises(lv.LowVolatilityContractError, match="must be zero"):
        lv.build_preflight_report(
            rows,
            calendar,
            decision_at_by_session=decisions,
            execution_rows=execution,
            health=_health(unexpected_exception_count=1),
        )
    with pytest.raises(lv.LowVolatilityContractError, match="benchmark identity"):
        _health(benchmark_symbol="159919.SZ")
    forged = _health()
    object.__setattr__(forged, "currency_unit", "USD")
    with pytest.raises(lv.LowVolatilityContractError, match="CNY and SHARES"):
        lv.build_preflight_report(
            rows,
            calendar,
            decision_at_by_session=decisions,
            execution_rows=execution,
            health=forged,
        )


def test_units_duplicates_nonfinite_and_timing_fail_closed() -> None:
    rows, calendar, decisions, execution = _fixture()
    with pytest.raises(lv.LowVolatilityContractError, match="CNY"):
        replace(rows[0], amount_unit="USD")
    with pytest.raises(lv.LowVolatilityContractError, match="CNY and SHARES"):
        replace(execution[0], position_unit="LOTS")
    with pytest.raises(lv.LowVolatilityContractError, match="positive finite"):
        replace(rows[0], total_return_index=float("nan"))
    with pytest.raises(lv.LowVolatilityContractError, match="date and symbol"):
        replace(rows[0], symbol=7)  # type: ignore[arg-type]
    with pytest.raises(lv.LowVolatilityContractError, match="duplicate signal"):
        lv.build_monthly_targets(
            (*rows, rows[0]),
            calendar,
            decision_at_by_session=decisions,
            execution_rows=execution,
        )
    decision_date = next(iter(decisions))
    close_at = calendar.session_on(decision_date, as_of=decisions[decision_date]).close_at
    with pytest.raises(lv.LowVolatilityContractError, match="after D close"):
        lv.build_monthly_targets(
            rows,
            calendar,
            decision_at_by_session={decision_date: close_at},
            execution_rows=execution,
        )


def test_call_time_revalidation_and_late_execution_identity_fail_closed() -> None:
    rows, calendar, decisions, execution = _fixture()
    forged = rows[0]
    object.__setattr__(forged, "amount_unit", "USD")
    with pytest.raises(lv.LowVolatilityContractError, match="CNY"):
        lv.build_monthly_targets(
            rows,
            calendar,
            decision_at_by_session=decisions,
            execution_rows=execution,
        )

    rows, calendar, decisions, execution = _fixture()
    execution_session = calendar.session_on(
        execution[0].execution_date,
        as_of=next(iter(decisions.values())),
    )
    late = replace(
        execution[0],
        source=_source("late-execution", execution_session.open_at + timedelta(minutes=1)),
    )
    assert lv.build_monthly_targets(
        rows,
        calendar,
        decision_at_by_session=decisions,
        execution_rows=(late, *execution[1:]),
    ) == ()


def test_each_variant_uses_only_its_frozen_lookback() -> None:
    rows, calendar, decisions, execution = _fixture()
    early_day = calendar.session_dates[0]
    missing_only_from_120 = tuple(
        row for row in rows if not (row.symbol == "000000.SZ" and row.session_date == early_day)
    )
    targets = lv.build_monthly_targets(
        missing_only_from_120,
        calendar,
        decision_at_by_session=decisions,
        execution_rows=execution,
    )
    selected = {target.variant_id: target.selected_symbols for target in targets}
    assert "000000.SZ" in selected["LV60"]
    assert "000000.SZ" in selected["DSV60"]
    assert "000000.SZ" not in selected["LV120"]
    assert "000000.SZ" not in selected["DSV120"]


def test_forged_nested_source_and_symbol_are_revalidated_at_call_time() -> None:
    rows, calendar, decisions, execution = _fixture()
    object.__setattr__(rows[0].source, "source_url", "http://invalid.test/source")
    with pytest.raises(ValueError, match="HTTPS URL"):
        lv.build_monthly_targets(
            rows,
            calendar,
            decision_at_by_session=decisions,
            execution_rows=execution,
        )
    rows, calendar, decisions, execution = _fixture()
    object.__setattr__(rows[0], "symbol", "QQQ")
    with pytest.raises(lv.LowVolatilityContractError, match="symbol"):
        lv.build_monthly_targets(
            rows,
            calendar,
            decision_at_by_session=decisions,
            execution_rows=execution,
        )


def test_forged_calendar_source_is_revalidated_at_call_time() -> None:
    rows, calendar, decisions, execution = _fixture()
    object.__setattr__(
        calendar._sessions[0].source,  # noqa: SLF001 - deliberate adversarial mutation
        "source_url",
        "http://invalid.test/calendar",
    )
    with pytest.raises(ValueError, match="HTTPS URL"):
        lv.build_monthly_targets(
            rows,
            calendar,
            decision_at_by_session=decisions,
            execution_rows=execution,
        )


def test_status_liquidity_and_history_gaps_never_impute() -> None:
    rows, calendar, decisions, execution = _fixture()
    decision_date = next(iter(decisions))
    changed = tuple(
        replace(row, is_st=True)
        if row.symbol == "000000.SZ" and row.session_date == decision_date
        else row
        for row in rows
    )
    targets = lv.build_monthly_targets(
        changed,
        calendar,
        decision_at_by_session=decisions,
        execution_rows=execution,
    )
    assert all("000000.SZ" not in target.selected_symbols for target in targets)

    missing_history = tuple(
        row
        for row in rows
        if not (
            row.symbol == "000001.SZ"
            and row.session_date == calendar.session_dates[-10]
        )
    )
    targets = lv.build_monthly_targets(
        missing_history,
        calendar,
        decision_at_by_session=decisions,
        execution_rows=execution,
    )
    assert all("000001.SZ" not in target.selected_symbols for target in targets)
