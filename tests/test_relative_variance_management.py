from __future__ import annotations

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
    binding = frozen["shared_execution_binding"]
    assert binding["base_commit"] == "1713f8ea2051ebee8f516c9a7830e4e2d7c8bcdb"
    assert set(binding["modules_sha256"]) == {
        "quant_system.backtest.event_loop",
        "quant_system.backtest.portfolio",
        "quant_system.backtest.blocked_orders",
        "quant_system.backtest.capacity",
        "quant_system.backtest.permanent_portfolio",
        "quant_system.markets.a_share",
    }
    assert binding["modules_sha256"]["quant_system.backtest.permanent_portfolio"] == (
        "11874465320c71218e89bad9bdf6ad543aa74dd3335a7571cc8ca2cc97ac6ffe"
    )
    assert "pre-current-rebalance NAV" in binding["monthly_return"]
    assert "residual or blocked terminal holding invalid" in binding["terminal_interval"]
    assert frozen["input_identity"]["available_at"] == "UNKNOWN_NOT_PIT_QUALIFIED"
    assert frozen["mechanism"]["one_way_cost_bps"] == 50
    assert "roundtrip_friction" not in frozen["mechanism"]


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


def test_monthly_metrics_and_centered_bootstrap_truncate_exact_n(monkeypatch) -> None:
    assert rvm.annualized_net((0.01,) * 12) == pytest.approx(1.01**12 - 1)
    assert rvm.annualized_volatility((0.01, 0.03)) == pytest.approx(0.02 * math.sqrt(6))
    observed: dict[str, int] = {}

    def starts(size: int, *, draws: int, seed: int):
        observed.update(size=size, draws=draws, seed=seed)
        return ((0, 3),)

    monkeypatch.setattr(rvm, "circular_block_start_indices", starts)
    result = rvm.centered_bootstrap(
        (0.01, -0.02, 0.03, 0.04, -0.01), seed=20260731, draws=1, alpha=0.2
    )
    assert observed == {"size": 5, "draws": 1, "seed": 20260731}
    assert result == pytest.approx((0.01, 0.5, 0.01))


def _audits(selected: int = 30) -> tuple[preflight.IntervalAudit, ...]:
    rows = []
    for split, start, count in (
        ("development_2020_2021", date(2020, 1, 1), 23),
        ("validation_2022_2023", date(2022, 1, 1), 23),
        ("holdout_2024_2026h1", date(2024, 1, 1), 29),
    ):
        rows.extend(
            preflight.IntervalAudit(start + timedelta(days=index), split, selected, 40, 7)
            for index in range(count)
        )
    return tuple(rows)


def test_report_is_aggregate_only_candidate_exclusions_allowed_and_precedence() -> None:
    report = preflight._report(_audits())
    assert report["status"] == "PREFLIGHT_PASS"
    assert report["candidate_excluded_counts"]["validation_2022_2023"] == 23 * 7
    assert report["holding_returns_opened"] is False
    assert report["strategy_candidate_available"] is False
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
    )
    assert preflight._report(variance_blocked)["status"] == "INPUT_BLOCKED"


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
    with pytest.raises(preflight.PreflightError, match="duplicate"):
        preflight._strict_json(b'{"x":1,"x":2}', "probe")
