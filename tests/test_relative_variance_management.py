from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
import hashlib
import json
import math
from pathlib import Path

import pytest

from quant_system.research import relative_variance_management as rvm
from scripts import run_a_share_relative_variance_management_preflight as preflight

ROOT = Path(__file__).resolve().parents[1]
DEFINITION = ROOT / "research/definitions/a_share_relative_variance_managed_liquid_equity_v1.json"
MODULE = ROOT / "src/quant_system/research/relative_variance_management.py"
ALLOWED_CANDIDATE_EXCLUSIONS = [
    "ts_code fails the frozen exchange-aware ordinary-A regex or board is not Main, ChiNext, or STAR",
    "list_date is missing, malformed, or later than the decision date",
    "fewer than 274 accepted sessions exist from list_date through the decision date",
    "the 274-session row identity has a duplicate key, wrong snapshot, non-accepted quality, synthetic row, or invalid row_hash",
    "the consecutive 274-session qfq_close window is incomplete, nonfinite, or nonpositive",
    "the consecutive 20-session amount window is incomplete, nonfinite, or negative",
]
FORBIDDEN_ADDITIONAL_FILTERS = [
    "ST or other name-status filters",
    "suspension or price-limit filters",
    "volatility filters",
    "momentum filters",
    "industry filters",
    "market-cap filters",
    "future listing, delisting, or security-status filters",
    "quality filters beyond the frozen snapshot and row-identity checks",
    "result-derived or discretionary filters",
]


def _stock(
    index: int, amount: float, closes: tuple[float, ...] | None = None
) -> rvm.QualifiedStock:
    return rvm.QualifiedStock(
        f"opaque-{index:03d}",
        rvm.BOARD_LABELS[index % 3],
        274,
        (amount,) * 20,
        closes or tuple(100.0 + day for day in range(274)),
    )


def _capital_rows(*, expensive_first: bool = False) -> tuple[rvm.CapitalFormationRow, ...]:
    return tuple(
        rvm.CapitalFormationRow(
            symbol=f"opaque-{index:03d}",
            raw_open=200.0 if expensive_first and index == 0 else 10.0,
            prior_volume_shares=1_000_000.0,
            prior_amount_cny=10_000_000.0,
            is_suspended=False,
            is_st=False,
            up_limit=220.0 if expensive_first and index == 0 else 11.0,
            down_limit=180.0 if expensive_first and index == 0 else 9.0,
            list_status="L",
        )
        for index in range(30)
    )


def test_definition_is_frozen_one_variant_negative_prior_and_closed() -> None:
    raw = DEFINITION.read_bytes()
    frozen = json.loads(raw)
    assert hashlib.sha256(raw).hexdigest() == rvm.DEFINITION_SHA256
    assert frozen["research_id"] == rvm.RESEARCH_ID
    assert frozen["mechanism"]["variant_count"] == 1
    assert frozen["economic_prior"]["direction"] == "negative_prior_requires_strict_validation"
    assert "cross-sectional" in frozen["economic_prior"]["distinction"]
    assert any("2020.04.015" in source for source in frozen["economic_prior"]["sources"])
    inference = frozen["validation_inference"]
    assert inference["seeds"] == {
        "validation": 20260731,
        "holdout": 20260801,
        "forward_closed": 20260802,
    }
    assert (inference["block_length_months"], inference["draws"], inference["one_sided_alpha"]) == (
        3,
        10000,
        1 / 60,
    )
    assert "truncate to N" in inference["bootstrap"]
    assert "/ 10001" in inference["p_value"]
    assert "without recycling" in inference["alpha_policy"]
    assert len(frozen["strict_gates"]) == 6
    assert frozen["retained_interval_counts"] == {
        "development_2020_2021": 23,
        "validation_2022_2023": 23,
        "holdout_2024_2026h1": 29,
    }
    exclusions = frozen["universe"]["candidate_exclusions"]
    assert exclusions == {
        "exhaustive": True,
        "allowed_before_ranking": ALLOWED_CANDIDATE_EXCLUSIONS,
        "forbidden_additional_filters": FORBIDDEN_ADDITIONAL_FILTERS,
        "reporting": "aggregate excluded counts only",
        "post_top_30_replacement": False,
    }
    assert "shared_execution_binding" not in frozen
    representation = frozen["historical_return_representation"]
    assert representation["classification"] == (
        "RETROSPECTIVE_SECONDARY_QFQ_ECONOMIC_SCREEN_NOT_ACCOUNT_EVIDENCE"
    )
    assert representation["single_representation_only"] is True
    assert representation["holding_period_prices"].endswith(
        "next scheduled rebalance accepted-session open"
    )
    assert representation["turnover"].startswith("sum(abs(target_stock_weight")
    assert representation["cost"] == (
        "0.005 times turnover; first entry from cash and terminal split liquidation to cash are included"
    )
    assert representation["cash_return"] == 0.0
    assert representation["account_level_event_loop_claim"] is False
    assert representation["strict_pit_claim"] is False
    assert representation["candidate_eligibility"] is False
    assert representation["allowed_validation_results"] == [
        "VALIDATION_PASS_TO_EXTERNAL_REVIEW",
        "VALIDATION_FAIL",
    ]
    assert representation["input_blocked_rule"] == "INPUT_BLOCKED creates no strategy result"
    assert inference["dependency"] == (
        "quant_system.research.relative_variance_management._circular_block_start_indices"
    )
    assert b"permanent_portfolio" not in raw
    assert b"permanent_portfolio" not in MODULE.read_bytes()
    assert frozen["input_identity"]["available_at"] == "UNKNOWN_NOT_PIT_QUALIFIED"
    assert frozen["mechanism"]["one_way_cost_bps"] == 50
    assert "roundtrip_friction" not in frozen["mechanism"]
    capital = frozen["capital_feasibility"]
    assert capital["historical_initial_cash_cny"] == 400_000
    assert capital["intended_pilot_scale_ceiling_cny_planning_only"] == 400_000
    assert (capital["basket_size"], capital["lot_size_shares"]) == (30, 100)
    assert capital["target_shares"] == (
        "100*floor(400000*target_weight/(100*raw_open))"
    )
    assert capital["interval_gate"] == {
        "comparator_filled_positions": 30,
        "comparator_invested_ratio_minimum": 0.9,
        "managed_filled_positions_minimum": 24,
        "managed_invested_ratio_minimum": (
            "max(0.80*intended_exposure,intended_exposure-0.10)"
        ),
    }
    assert capital["failure_status"] == "LIVE_FEASIBILITY_FAIL_NO_OUTCOME"
    assert capital["historical_outcome_authorized"] is False
    assert frozen["preflight"]["status_precedence"].endswith(
        "CAPITAL_FEASIBILITY_PASS_NO_OUTCOME"
    )


def test_selection_is_exact_thirty_median_amount_then_opaque_id() -> None:
    rows = [_stock(index, 100.0 - index) for index in range(31)]
    basket = rvm.select_basket(tuple(reversed(rows)))
    assert len(basket) == 30
    assert tuple(row.symbol for row in basket) == tuple(
        f"opaque-{index:03d}" for index in range(30)
    )
    tied = [_stock(index, 1.0) for index in reversed(range(30))]
    assert tuple(row.symbol for row in rvm.select_basket(tied)) == tuple(
        sorted(row.symbol for row in tied)
    )


@pytest.mark.parametrize(
    "change",
    (
        {"accepted_session_count": 273},
        {"trailing_amounts_cny": (1.0,) * 19},
        {"trailing_amounts_cny": (math.nan,) * 20},
        {"qfq_closes": (1.0,) * 273},
        {"qfq_closes": (1.0,) * 273 + (0.0,)},
    ),
)
def test_candidate_identity_fails_closed(change: dict[str, object]) -> None:
    values = {
        "symbol": "opaque",
        "board": "Main",
        "accepted_session_count": 274,
        "trailing_amounts_cny": (1.0,) * 20,
        "qfq_closes": (1.0,) * 274,
    }
    values.update(change)
    with pytest.raises(rvm.RelativeVarianceContractError):
        rvm.QualifiedStock(**values)  # type: ignore[arg-type]


def test_exact_daily_basket_variance_and_capped_exposure() -> None:
    closes = tuple(100.0 * (1.01**day) for day in range(274))
    basket = tuple(_stock(index, 1.0, closes) for index in range(30))
    returns = rvm.basket_daily_returns(basket)
    assert len(returns) == 273
    assert returns == pytest.approx((0.01,) * 273)
    baseline, current, exposure = rvm.variance_exposure(returns)
    assert baseline == pytest.approx(0.0001)
    assert current == pytest.approx(0.0001)
    assert exposure == pytest.approx(1.0)
    shock = (0.01,) * 252 + (0.02,) * 21
    assert rvm.variance_exposure(shock)[2] == pytest.approx(0.25)
    with pytest.raises(rvm.RelativeVarianceContractError, match="variance"):
        rvm.variance_exposure((0.0,) * 273)


def test_capital_feasibility_uses_raw_open_lots_cash_commission_and_exact_gate() -> None:
    audit = rvm.capital_interval_feasibility(_capital_rows(), intended_exposure=0.5)
    assert audit.gate_pass is True
    assert audit.managed.minimum_faithful_capital_cny == pytest.approx(60_000.0)
    assert audit.managed.target_nonzero_positions == 30
    assert audit.managed.filled_positions == 30
    assert audit.managed.invested_ratio == pytest.approx(0.45)
    assert audit.managed.total_commission_drag_bps == pytest.approx(3.75)
    assert audit.managed.minimum_commission_drag_bps == pytest.approx(2.4)
    assert audit.comparator.minimum_faithful_capital_cny == pytest.approx(30_000.0)
    assert audit.comparator.filled_positions == 30
    assert audit.comparator.invested_ratio == pytest.approx(0.975)
    assert audit.comparator.minimum_commission_drag_bps == pytest.approx(0.825)


def test_capital_feasibility_fails_expensive_target_without_replacement() -> None:
    audit = rvm.capital_interval_feasibility(
        _capital_rows(expensive_first=True), intended_exposure=0.5
    )
    assert audit.gate_pass is False
    assert audit.managed.minimum_faithful_capital_cny == pytest.approx(1_200_000.0)
    assert audit.managed.target_nonzero_positions == 29
    assert audit.comparator.target_nonzero_positions == 29
    assert audit.managed.filled_positions == 29
    assert audit.comparator.filled_positions == 29


def test_capital_market_rejection_precedes_capacity_and_rows_fail_closed() -> None:
    rows = list(_capital_rows())
    rows[0] = replace(rows[0], raw_open=11.0)
    rows[1] = replace(rows[1], prior_volume_shares=100.0, prior_amount_cny=1_000.0)
    audit = rvm.capital_interval_feasibility(tuple(reversed(rows)), intended_exposure=1.0)
    assert audit.managed.market_rule_rejection_count == 1
    assert audit.managed.capacity_rejection_count == 1
    assert audit.managed.filled_positions == 28
    assert audit.gate_pass is False
    with pytest.raises(rvm.RelativeVarianceContractError, match="30 unique"):
        rvm.capital_interval_feasibility(rows[:-1], intended_exposure=1.0)
    with pytest.raises(rvm.RelativeVarianceContractError, match="raw open"):
        replace(rows[2], raw_open=math.nan)
    with pytest.raises(rvm.RelativeVarianceContractError, match="prior volume"):
        replace(rows[2], prior_volume_shares=1.5)


def test_private_pcg64_start_sequence_is_frozen_by_golden_vector() -> None:
    assert rvm._circular_block_start_indices(5, draws=3, seed=123) == (
        (0, 3),
        (2, 0),
        (4, 1),
    )


@pytest.mark.parametrize(
    ("sample_size", "draws", "seed"),
    ((2, 1, 0), (5, 0, 0), (5, 1, -1), (True, 1, 0), (5, True, 0), (5, 1, True)),
)
def test_private_pcg64_start_sequence_rejects_invalid_inputs(
    sample_size: object, draws: object, seed: object
) -> None:
    with pytest.raises(rvm.RelativeVarianceContractError, match="bootstrap index"):
        rvm._circular_block_start_indices(  # type: ignore[arg-type]
            sample_size, draws=draws, seed=seed
        )


def test_monthly_metrics_and_centered_bootstrap_wrap_and_truncate_exact_n(monkeypatch) -> None:
    assert rvm.annualized_net((0.01,) * 12) == pytest.approx(1.01**12 - 1)
    assert rvm.annualized_volatility((0.01, 0.03)) == pytest.approx(0.02 * math.sqrt(6))
    observed: dict[str, int] = {}

    def starts(size: int, *, draws: int, seed: int):
        observed.update(size=size, draws=draws, seed=seed)
        return ((0, 3),)

    monkeypatch.setattr(rvm, "_circular_block_start_indices", starts)
    result = rvm.centered_bootstrap(
        (0.01, -0.02, 0.03, 0.04, -0.01), seed=20260731, draws=1, alpha=0.2
    )
    assert observed == {"size": 5, "draws": 1, "seed": 20260731}
    assert result == pytest.approx((0.01, 0.5, 0.01))


def _audits(selected: int = 30) -> tuple[preflight.IntervalAudit, ...]:
    rows = []
    capital = rvm.capital_interval_feasibility(_capital_rows(), intended_exposure=1.0)
    for split, start, count in (
        ("development_2020_2021", date(2020, 1, 1), 23),
        ("validation_2022_2023", date(2022, 1, 1), 23),
        ("holdout_2024_2026h1", date(2024, 1, 1), 29),
    ):
        rows.extend(
            preflight.IntervalAudit(
                start + timedelta(days=index), split, selected, 40, 7, capital=capital
            )
            for index in range(count)
        )
    return tuple(rows)


def test_report_is_aggregate_only_candidate_exclusions_allowed_and_precedence() -> None:
    report = preflight._report(_audits())
    assert report["status"] == "CAPITAL_FEASIBILITY_PASS_NO_OUTCOME"
    assert report["candidate_excluded_counts"]["validation_2022_2023"] == 23 * 7
    assert report["holding_returns_opened"] is False
    assert report["strategy_candidate_available"] is False
    assert report["historical_outcome_authorized"] is False
    assert report["invalid_capital_interval_count"] == 0
    assert report["minimum_nonzero_comparator_positions"] == 30
    assert report["minimum_comparator_invested_ratio"] == pytest.approx(0.975)
    assert set(report).isdisjoint({"symbols", "rankings", "returns", "exposures", "pairs"})
    assert preflight._report(_audits(29))["status"] == "STRUCTURAL_FAIL"
    assert preflight._report(_audits()[:-1])["status"] == "STRUCTURAL_FAIL"
    assert preflight._report(_audits(29), input_failure_count=1)["status"] == "INPUT_BLOCKED"
    variance_blocked = list(_audits())
    variance_blocked[0] = preflight.IntervalAudit(
        variance_blocked[0].decision_date,
        variance_blocked[0].split_id,
        30,
        40,
        7,
        invalid_variance_count=1,
        capital=variance_blocked[0].capital,
    )
    assert preflight._report(variance_blocked)["status"] == "INPUT_BLOCKED"
    live_fail = list(_audits())
    live_fail[0] = replace(
        live_fail[0],
        capital=rvm.capital_interval_feasibility(
            _capital_rows(expensive_first=True), intended_exposure=0.5
        ),
    )
    failed_report = preflight._report(live_fail)
    assert failed_report["status"] == "LIVE_FEASIBILITY_FAIL_NO_OUTCOME"
    assert failed_report["invalid_capital_interval_count"] == 1


def test_default_is_dry_run_without_database(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        preflight, "run_read_only_preflight", lambda *_: pytest.fail("database opened")
    )
    assert preflight.main([]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report == {
        "database_opened": False,
        "holding_returns_opened": False,
        "status": "DRY_RUN",
        "strategy_candidate_available": False,
    }


def test_scan_is_parameter_bound_identity_only_and_has_no_identifier_output() -> None:
    assert preflight.SCAN_SQL.count("?") == 11
    assert rvm.SNAPSHOT_ID not in preflight.SCAN_SQL
    assert "qfq_close /" not in preflight.SCAN_SQL
    assert "lead(qfq_close" not in preflight.SCAN_SQL
    assert "lead(first_d) OVER(ORDER BY d) entry_d" in preflight.SCAN_SQL
    assert "excluded_count" in preflight.SCAN_SQL
    assert "baseline_variance" in preflight.SCAN_SQL
    assert "invalid_execution_panel_count" in preflight.SCAN_SQL
    assert "capital_payload AS" in preflight.SCAN_SQL
    assert "e.open exec_open" in preflight.SCAN_SQL
    assert "p.vol prior_vol" in preflight.SCAN_SQL
    assert "least(1.0,v.baseline_variance/v.current_variance) exposure" in preflight.SCAN_SQL
    assert "lead(d) OVER(ORDER BY d) next_d" in preflight.SCAN_SQL
    assert "entry_d exec_d,d prior_d" in preflight.SCAN_SQL
    assert "exit_d,next_d" in preflight.SCAN_SQL
    assert "e.open" in preflight.SCAN_SQL and "e.qfq_open" in preflight.SCAN_SQL
    assert "p.vol" in preflight.SCAN_SQL and "e.up_limit" in preflight.SCAN_SQL
    assert (
        "regexp_full_match(list_date,'[0-9]{8}')" in preflight.SCAN_SQL
        and "m.list_date<=s.d" in preflight.SCAN_SQL
    )
    assert (
        "row_number() OVER(PARTITION BY d ORDER BY med_amount DESC,ts_code)" in preflight.SCAN_SQL
    )
    qualified = preflight.SCAN_SQL.split("), qualified AS (", 1)[1].split(
        "), ranked AS (", 1
    )[0]
    assert all(
        forbidden not in qualified.lower()
        for forbidden in (
            "is_st",
            "is_suspended",
            "up_limit",
            "down_limit",
            "total_mv",
            "industry",
            "momentum",
            "volatility",
        )
    )
    with pytest.raises(preflight.PreflightError, match="duplicate"):
        preflight._strict_json(b'{"x":1,"x":2}', "probe")
