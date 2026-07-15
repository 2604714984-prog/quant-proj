from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from quant_system.backtest import CapacityObservation, ExecutionInput
from quant_system.data import AcceptedSession, AcceptedSessionCalendar, SourceIdentity
from quant_system.markets.universe import StatusEvidence
from quant_system.research import relative_strength as rs


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "research/definitions/a_share_relative_strength_medium_term_momentum_code_v1.json"
UTC = timezone.utc


def _source(label: str, available_at: datetime | None = None) -> SourceIdentity:
    available = available_at or datetime(2000, 1, 1, tzinfo=UTC)
    return SourceIdentity(
        f"https://example.test/{label}",
        hashlib.sha256(label.encode()).hexdigest(),
        available,
        available + timedelta(minutes=1),
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


def _signal_fixture() -> tuple[tuple[rs.SignalBar, ...], AcceptedSessionCalendar]:
    start = date(2025, 1, 1)
    dates = tuple(start + timedelta(days=offset) for offset in range(120)) + (
        date(2025, 5, 31),
        date(2025, 6, 1),
    )
    calendar = _calendar(dates)
    source = _source("signals")
    rows: list[rs.SignalBar] = []
    for index, day in enumerate(dates):
        rows.append(
            rs.SignalBar(
                day,
                rs.BENCHMARK_SYMBOL,
                math.exp(0.0001 * index),
                1_000_000_000.0,
                1_000 + index,
                True,
                False,
                False,
                False,
                "ETF",
                "SSE_MAIN",
                source,
            )
        )
        for symbol_index in range(500):
            symbol = f"{symbol_index:06d}.SZ"
            drift = 0.0003 + symbol_index * 0.000001
            amplitude = 0.00002 if symbol_index < 250 else 0.00020
            tri = math.exp(drift * index + amplitude * math.sin(index * 0.7))
            rows.append(
                rs.SignalBar(
                    day,
                    symbol,
                    tri,
                    25_000_000.0,
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
    return tuple(rows), calendar


@pytest.fixture(scope="module")
def signal_data() -> tuple[tuple[rs.SignalBar, ...], AcceptedSessionCalendar]:
    return _signal_fixture()


def _decision_times() -> dict[date, datetime]:
    zone = ZoneInfo("Asia/Shanghai")
    return {date(2025, 5, 31): datetime(2025, 5, 31, 15, 30, tzinfo=zone)}


@pytest.fixture(scope="module")
def targets(
    signal_data: tuple[tuple[rs.SignalBar, ...], AcceptedSessionCalendar],
) -> tuple[rs.RelativeStrengthTarget, ...]:
    rows, calendar = signal_data
    return rs.build_monthly_targets(
        rows, calendar, decision_at_by_session=_decision_times()
    )


def test_contract_hashes_variants_and_source_identity_are_exact() -> None:
    assert hashlib.sha256((ROOT / rs.DEFINITION_PATH).read_bytes()).hexdigest() == (
        rs.DEFINITION_SHA256
    )


def test_code_manifest_binds_exact_two_implementation_files_and_no_execution() -> None:
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["accepted_source"] == {
        "commit": rs.ACCEPTED_SOURCE_COMMIT,
        "tree": rs.ACCEPTED_SOURCE_TREE,
        "preregistration_path": str(rs.DEFINITION_PATH),
        "preregistration_sha256": rs.DEFINITION_SHA256,
        "data_qualification_path": str(rs.QUALIFICATION_PATH),
        "data_qualification_sha256": rs.QUALIFICATION_SHA256,
    }
    assert tuple(item["path"] for item in manifest["scope"]) == (
        "src/quant_system/research/relative_strength.py",
        "tests/test_relative_strength_cleanroom.py",
    )
    for item in manifest["scope"]:
        assert hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest() == item["sha256"]
    assert manifest["reuse"]["new_runner_or_dsl_or_registry"] is False
    assert manifest["boundary"]["real_data_or_outcome_access"] is False
    assert manifest["boundary"]["strategy_candidate_available"] is False
    assert hashlib.sha256((ROOT / rs.QUALIFICATION_PATH).read_bytes()).hexdigest() == (
        rs.QUALIFICATION_SHA256
    )
    assert rs.ACCEPTED_SOURCE_COMMIT == "7160d07459fa0514f48beca00f34278ffa13c98c"
    assert rs.ACCEPTED_SOURCE_TREE == "758fa2b2bb836a0c5cfbf9763d4973f202f117c6"
    assert tuple((item.variant_id, item.lookback_sessions, item.volatility_filter_enabled)
                 for item in rs.VARIANTS) == (
        ("RS60_BASE", 60, False),
        ("RS60_VOL20_MEDIAN", 60, True),
        ("RS120_BASE", 120, False),
        ("RS120_VOL20_MEDIAN", 120, True),
    )


def test_month_end_targets_freeze_signal_rank_filter_timing_and_selection(
    targets: tuple[rs.RelativeStrengthTarget, ...],
    signal_data: tuple[tuple[rs.SignalBar, ...], AcceptedSessionCalendar],
) -> None:
    assert len(targets) == 4
    assert tuple(target.variant_id for target in targets) == tuple(
        item.variant_id for item in rs.VARIANTS
    )
    for target in targets:
        assert target.decision_date == date(2025, 5, 31)
        assert target.execution_date == date(2025, 6, 1)
        local_decision = target.decision_at.astimezone(ZoneInfo("Asia/Shanghai"))
        assert local_decision.hour == 15 and local_decision.minute == 30
        assert target.base_eligible_count == 500
        assert len(target.selected_symbols) == rs.MAX_POSITIONS
        assert target.target_weights == tuple(
            (symbol, 1.0 / 15.0) for symbol in target.selected_symbols
        )
        strengths = tuple(value for _, value in target.selected_relative_strength)
        assert strengths == tuple(sorted(strengths, reverse=True))
        assert all(value > 0.0 for value in strengths)
    by_id = {target.variant_id: target for target in targets}
    assert by_id["RS60_VOL20_MEDIAN"].ranked_candidate_count < 500
    assert by_id["RS120_VOL20_MEDIAN"].ranked_candidate_count < 500
    assert by_id["RS60_BASE"].selected_symbols[0] == "000499.SZ"
    assert by_id["RS120_BASE"].selected_symbols[0] == "000499.SZ"
    rows, _ = signal_data
    by_symbol: dict[str, list[rs.SignalBar]] = {}
    for row in rows:
        if row.symbol != rs.BENCHMARK_SYMBOL:
            by_symbol.setdefault(row.symbol, []).append(row)
    volatilities = []
    for history in by_symbol.values():
        returns = tuple(
            history[index].total_return_index / history[index - 1].total_return_index - 1.0
            for index in range(len(history) - 21, len(history) - 1)
        )
        mean = math.fsum(returns) / 20.0
        volatilities.append(math.sqrt(math.fsum((value - mean) ** 2 for value in returns) / 19.0))
    ordered_volatility = sorted(volatilities)
    expected_median = math.fsum(ordered_volatility[249:251]) / 2.0
    assert targets[0].volatility_median == pytest.approx(expected_median)


def test_duplicate_key_late_history_and_wrong_cutoff_fail_closed(
    signal_data: tuple[tuple[rs.SignalBar, ...], AcceptedSessionCalendar],
) -> None:
    rows, calendar = signal_data
    with pytest.raises(rs.RelativeStrengthContractError, match="duplicate"):
        rs.build_monthly_targets(
            rows + (rows[0],), calendar, decision_at_by_session=_decision_times()
        )

    changed = list(rows)
    index = next(
        offset
        for offset, row in enumerate(changed)
        if row.symbol == "000000.SZ" and row.session_date == date(2025, 5, 31)
    )
    row = changed[index]
    changed[index] = rs.SignalBar(
        row.session_date,
        row.symbol,
        row.total_return_index,
        row.amount_cny,
        row.accepted_sessions_since_listing,
        row.listed,
        row.delisted,
        row.is_st,
        row.is_suspended,
        row.security_type,
        row.board,
        _source("late", datetime(2025, 6, 1, 0, tzinfo=UTC)),
    )
    with pytest.raises(rs.RelativeStrengthContractError, match="fewer than 500"):
        rs.build_monthly_targets(
            tuple(changed), calendar, decision_at_by_session=_decision_times()
        )
    wrong = {date(2025, 5, 31): datetime(2025, 5, 31, 15, 29, tzinfo=ZoneInfo("Asia/Shanghai"))}
    with pytest.raises(rs.RelativeStrengthContractError, match="close plus 30"):
        rs.build_monthly_targets(rows, calendar, decision_at_by_session=wrong)


def test_residual_allocation_reserves_trapped_slot_and_never_uses_alphabetical_fallback() -> None:
    ranked = tuple(f"RANK-{index:02d}" for index in range(20))
    trapped = {"AAA-TRAPPED": 40_000.0}
    before = dict(trapped)
    allocation = rs.residual_target_weights(ranked, trapped, nav=400_000.0)
    assert trapped == before
    assert allocation.trapped_symbols == ("AAA-TRAPPED",)
    assert allocation.admitted_symbols == ranked[:14]
    assert "RANK-14" not in dict(allocation.target_weights)
    assert math.fsum(dict(allocation.target_weights).values()) == pytest.approx(0.9)
    assert allocation.residual_investable_nav == 360_000.0
    with pytest.raises(rs.RelativeStrengthContractError, match="disjoint"):
        rs.residual_target_weights(ranked, {"RANK-00": 1.0}, nav=400_000.0)
    with pytest.raises(rs.RelativeStrengthContractError, match="within NAV"):
        rs.residual_target_weights(ranked, {"TRAPPED": 400_001.0}, nav=400_000.0)
    for invalid in (float("nan"), float("inf"), float("-inf"), -1.0):
        values = {"BAD": invalid, "GOOD": 100.0}
        unchanged = dict(values)
        with pytest.raises(rs.RelativeStrengthContractError, match="trapped mark|nonnegative"):
            rs.residual_target_weights(ranked, values, nav=400_000.0)
        assert values == unchanged


def _statuses(symbol: str) -> tuple[StatusEvidence, ...]:
    return tuple(
        StatusEvidence(
            f"{symbol}-{kind}",
            symbol,
            kind,
            value,
            date(2000, 1, 1),
            None,
            "Asia/Shanghai",
            _source(f"status-{symbol}-{kind}"),
        )
        for kind, value in (
            ("listed", True),
            ("delisted", False),
            ("st", False),
            ("suspended", False),
        )
    )


def test_existing_event_loop_applies_board_lot_capacity_cost_and_frozen_slippage() -> None:
    days = (date(2026, 6, 29), date(2026, 6, 30))
    calendar = _calendar(days)
    signal = calendar.session_on(days[0], as_of=datetime(2026, 6, 29, 8, tzinfo=UTC))
    execution = calendar.next_session(days[0], as_of=signal.close_at + timedelta(minutes=30))
    inputs = []
    weights = {}
    for index in range(15):
        symbol = f"{index:06d}.SZ"
        weights[symbol] = 1.0 / 15.0
        capacity = CapacityObservation(
            symbol,
            signal,
            10_000_000.0,
            1_000_000_000.0,
            "CNY",
            _source(f"capacity-{symbol}", signal.close_at),
        )
        inputs.append(
            ExecutionInput(
                symbol,
                "a_share",
                10.0,
                "CNY",
                _source(f"open-{symbol}", execution.open_at),
                _statuses(symbol),
                capacity=capacity,
            )
        )
    result = rs.run_frozen_static_rebalance(
        rs.new_strategy_portfolio(),
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at + timedelta(minutes=30),
        execution_inputs=tuple(inputs),
        target_weights=weights,
        slippage_bps=50.0,
    )
    buys = tuple(receipt for receipt in result.receipts if receipt.side == "buy")
    assert len(result.portfolio.positions) == 15
    assert len(buys) == 15
    assert all(receipt.filled_shares % 100 == 0 for receipt in buys)
    assert all(receipt.price == pytest.approx(10.05) for receipt in buys)
    assert all(receipt.commission >= 5.0 for receipt in buys)
    with pytest.raises(rs.RelativeStrengthContractError, match="20 or 50"):
        rs.run_frozen_static_rebalance(
            rs.new_strategy_portfolio(),
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at + timedelta(minutes=30),
            execution_inputs=tuple(inputs),
            target_weights=weights,
            slippage_bps=30.0,
        )


def test_whole_label_split_purge_and_embargo_fail_closed() -> None:
    kept = rs.MonthlyObservation(
        "RS60_BASE",
        date(2022, 1, 28),
        date(2022, 1, 31),
        date(2022, 2, 28),
        0.02,
        0.01,
    )
    crossed = rs.MonthlyObservation(
        "RS60_BASE",
        date(2021, 12, 30),
        date(2021, 12, 31),
        date(2022, 1, 31),
        0.02,
        0.01,
    )
    assigned, purged = rs.assign_and_purge_monthly_observations((crossed, kept))
    assert purged == 1
    assert len(assigned) == 1
    assert assigned[0].split_id == "validation_2022_2023"
    pre_split_signal = rs.MonthlyObservation(
        "RS60_BASE",
        date(2021, 12, 31),
        date(2022, 1, 3),
        date(2022, 2, 1),
        0.02,
        0.01,
    )
    pre_split_assigned, pre_split_purged = rs.assign_and_purge_monthly_observations(
        (pre_split_signal,)
    )
    assert pre_split_purged == 0
    assert pre_split_assigned[0].split_id == "validation_2022_2023"
    embargo = rs.MonthlyObservation(
        "RS60_BASE",
        date(2026, 7, 28),
        date(2026, 7, 29),
        date(2026, 8, 29),
        0.02,
        0.01,
    )
    with pytest.raises(rs.RelativeStrengthContractError, match="embargo"):
        rs.assign_and_purge_monthly_observations((embargo,))


def _next_month(value: date) -> date:
    year = value.year + (value.month == 12)
    month = 1 if value.month == 12 else value.month + 1
    return date(year, month, value.day)


def _twelve_groups() -> tuple[
    tuple[rs.AssignedObservation, ...], tuple[rs.GatedDecisionLedger, ...]
]:
    observations: list[rs.AssignedObservation] = []
    ledgers: list[rs.GatedDecisionLedger] = []
    for variant in rs.VARIANTS:
        for split_id in rs.GATED_SPLITS:
            split = next(item for item in rs.SPLITS if item.split_id == split_id)
            entry = date(split.start.year, split.start.month, 3)
            decisions: list[rs.DecisionAudit] = []
            index = 0
            while (entry.year, entry.month) != (split.end.year, split.end.month):
                exit_date = _next_month(entry)
                signal = entry - timedelta(days=3)
                active = 0.01 + 0.001 * math.sin(index + variant.order)
                observations.append(
                    rs.AssignedObservation(
                        variant.variant_id,
                        split_id,
                        signal,
                        entry,
                        exit_date,
                        0.015 + active,
                        0.015,
                    )
                )
                decisions.append(rs.DecisionAudit(signal, entry, exit_date, True))
                entry = exit_date
                index += 1
            ledgers.append(
                rs.GatedDecisionLedger(
                    variant.variant_id,
                    split_id,
                    split.start,
                    split.end,
                    tuple(decisions),
                )
            )
    return tuple(observations), tuple(ledgers)


def test_exact_twelve_test_bonferroni_family_and_deterministic_report() -> None:
    observations, ledgers = _twelve_groups()
    results = rs.evaluate_twelve_tests(observations, decision_ledgers=ledgers)
    assert len(results) == 12
    assert tuple((item.variant_id, item.split_id) for item in results) == tuple(
        (variant.variant_id, split_id)
        for variant in rs.VARIANTS
        for split_id in rs.GATED_SPLITS
    )
    assert results[0].seed == 20_260_816
    assert results[-1].seed == 20_261_118
    expected_sizes = {
        "validation_2022_2023": 23,
        "retrospective_holdout_2024_2026h1": 29,
        "prospective_forward_2027_2029": 35,
    }
    assert all(item.sample_size == expected_sizes[item.split_id] for item in results)
    assert all(len(item.gates) == 6 and all(passed for _, passed in item.gates) for item in results)
    report_a = rs.build_synthetic_diagnostic(observations, decision_ledgers=ledgers)
    report_b = rs.build_synthetic_diagnostic(observations, decision_ledgers=ledgers)
    assert rs.canonical_report_bytes(report_a) == rs.canonical_report_bytes(report_b)
    assert report_a["test_family_size"] == 12
    assert report_a["gate_counts"] == {"passed": 72, "total": 72}
    assert report_a["strategy_candidate_available"] is False
    assert report_a["status"] == "SYNTHETIC_DIAGNOSTIC_NOT_STRATEGY_EVIDENCE"


def test_pcg64_three_month_bootstrap_has_fixed_nonconstant_golden_output() -> None:
    observed, p_value, lower = rs._pcg64_bootstrap(
        (0.01, -0.02, 0.03, 0.04, -0.01, 0.02), seed=20_260_816
    )
    assert observed == pytest.approx(0.011666666666666665)
    assert p_value == pytest.approx(9.999000099990002e-05)
    assert lower == pytest.approx(0.003333333333333334)


def test_inference_requires_exact_complete_ordered_monthly_decision_ledger() -> None:
    observations, ledgers = _twelve_groups()
    with pytest.raises(rs.RelativeStrengthContractError, match="complete ordered"):
        rs.evaluate_twelve_tests(observations[:-1], decision_ledgers=ledgers)
    with pytest.raises(rs.RelativeStrengthContractError, match="complete ordered"):
        rs.evaluate_twelve_tests(tuple(reversed(observations)), decision_ledgers=ledgers)
    with pytest.raises(rs.RelativeStrengthContractError, match="exact ordered 12"):
        rs.evaluate_twelve_tests(observations, decision_ledgers=tuple(reversed(ledgers)))

    first = ledgers[0]
    with pytest.raises(rs.RelativeStrengthContractError, match="declared split bounds"):
        rs.GatedDecisionLedger(
            first.variant_id,
            first.split_id,
            first.declared_start + timedelta(days=1),
            first.declared_end,
            first.decisions,
        )
    invalid_first = rs.DecisionAudit(
        first.decisions[0].signal_date,
        first.decisions[0].entry_date,
        first.decisions[0].exit_date,
        False,
        "missing accepted close mark",
    )
    invalid_ledger = rs.GatedDecisionLedger(
        first.variant_id,
        first.split_id,
        first.declared_start,
        first.declared_end,
        (invalid_first, *first.decisions[1:]),
    )
    with pytest.raises(rs.RelativeStrengthContractError, match="missing or invalid"):
        rs.evaluate_twelve_tests(
            observations, decision_ledgers=(invalid_ledger, *ledgers[1:])
        )

    second = first.decisions[1]
    overlapping_second = rs.DecisionAudit(
        second.signal_date - timedelta(days=1),
        second.entry_date - timedelta(days=1),
        second.exit_date - timedelta(days=1),
        True,
    )
    with pytest.raises(rs.RelativeStrengthContractError, match="complete and non-overlapping"):
        rs.GatedDecisionLedger(
            first.variant_id,
            first.split_id,
            first.declared_start,
            first.declared_end,
            (first.decisions[0], overlapping_second, *first.decisions[2:]),
        )


def test_mislabeled_and_out_of_contract_observations_fail_before_inference() -> None:
    with pytest.raises(rs.RelativeStrengthContractError, match="declared split"):
        rs.AssignedObservation(
            "RS60_BASE",
            "validation_2022_2023",
            date(2034, 12, 31),
            date(2035, 1, 3),
            date(2035, 2, 3),
            0.02,
            0.01,
        )
    with pytest.raises(rs.RelativeStrengthContractError, match="declared split"):
        rs.AssignedObservation(
            "RS60_BASE",
            "retrospective_holdout_2024_2026h1",
            date(2021, 12, 31),
            date(2022, 1, 3),
            date(2022, 2, 3),
            0.02,
            0.01,
        )


def test_nonfinite_report_fails_closed() -> None:
    with pytest.raises(rs.RelativeStrengthContractError, match="canonical"):
        rs.canonical_report_bytes({"bad": float("nan")})


def _accepted_manifest() -> dict[str, object]:
    return {
        "status": "ACCEPTED_STRICT_PIT_MANIFEST",
        "research_id": rs.RESEARCH_ID,
        "preregistration_sha256": rs.DEFINITION_SHA256,
        "data_qualification_sha256": rs.QUALIFICATION_SHA256,
        "strict_pit_execution_eligible": True,
        "strategy_outcomes_opened": False,
        "dataset_identity_sha256": "1" * 64,
        "calendar_identity_sha256": "2" * 64,
        "parser_identity_sha256": "3" * 64,
        "corporate_action_identity_sha256": "4" * 64,
    }


def test_formal_manifest_binding_is_exact_and_synthetic_path_is_structurally_separate(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "manifest.json"
    raw = json.dumps(_accepted_manifest(), sort_keys=True).encode()
    manifest_path.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    evidence = rs.load_formal_evidence(
        ROOT,
        data_manifest_path=manifest_path,
        expected_data_manifest_sha256=digest,
    )
    assert evidence.data_manifest_sha256 == digest
    assert evidence.dataset_identity_sha256 == "1" * 64
    observations, ledgers = _twelve_groups()
    assert "FormalEvidence" not in rs.build_synthetic_diagnostic(
        observations, decision_ledgers=ledgers
    )

    forged = _accepted_manifest()
    forged["preregistration_sha256"] = "0" * 64
    forged_raw = json.dumps(forged, sort_keys=True).encode()
    manifest_path.write_bytes(forged_raw)
    with pytest.raises(rs.RelativeStrengthContractError, match="not accepted"):
        rs.load_formal_evidence(
            ROOT,
            data_manifest_path=manifest_path,
            expected_data_manifest_sha256=hashlib.sha256(forged_raw).hexdigest(),
        )
    link = tmp_path / "manifest-link.json"
    link.symlink_to(manifest_path)
    with pytest.raises(rs.RelativeStrengthContractError, match="cannot open"):
        rs.load_formal_evidence(
            ROOT,
            data_manifest_path=link,
            expected_data_manifest_sha256=hashlib.sha256(forged_raw).hexdigest(),
        )
