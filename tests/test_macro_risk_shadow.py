from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from quant_system.research import macro_risk_shadow as shadow


ROOT = Path(__file__).resolve().parents[1]
DEFINITION = ROOT / shadow.DEFINITION_PATH
ZONE = ZoneInfo("Asia/Shanghai")
AS_OF = datetime(2026, 6, 30, 15, 0, tzinfo=ZONE)
DIGEST = hashlib.sha256(b"anonymous-ordered-universe-v1").hexdigest()


def _sessions() -> tuple[date, ...]:
    current = AS_OF.date()
    descending: list[date] = []
    while len(descending) < 121:
        if current.weekday() < 5:
            descending.append(current)
        current -= timedelta(days=1)
    return tuple(reversed(descending))


def _input(*, adverse: bool = False) -> shadow.MacroRiskInput:
    sessions = _sessions()
    if adverse:
        benchmark = tuple(130.0 - 0.5 * index for index in range(121))
        prices = tuple(tuple(100.0 - 0.5 * index for index in range(61)) for _ in range(4))
        amounts = tuple((100.0,) * 20 + (50.0,) for _ in range(4))
        limit_down = (True,) * 4
        suspended = (True,) * 4
    else:
        benchmark = tuple(100.0 + 0.2 * index for index in range(121))
        prices = tuple(tuple(100.0 + 0.5 * index for index in range(61)) for _ in range(4))
        amounts = tuple((100.0,) * 20 + (150.0,) for _ in range(4))
        limit_down = (False,) * 4
        suspended = (False,) * 4
    return shadow.MacroRiskInput(
        AS_OF,
        AS_OF + timedelta(hours=1),
        shadow.SNAPSHOT_ID,
        shadow.DATABASE_SHA256,
        sessions,
        sessions[-61:],
        sessions[-21:],
        sessions[-1],
        4,
        DIGEST,
        DIGEST,
        DIGEST,
        DIGEST,
        benchmark,
        prices,
        amounts,
        limit_down,
        suspended,
    )


def test_definition_freezes_exact_components_alignment_finite_gate_and_boundaries() -> None:
    definition = json.loads(DEFINITION.read_text())
    assert hashlib.sha256(DEFINITION.read_bytes()).hexdigest() == shadow.DEFINITION_SHA256
    assert definition["status"] == "SHADOW_ONLY_NOT_COMPUTED"
    assert definition["input_identity"]["snapshot_id"] == shadow.SNAPSHOT_ID
    assert definition["input_identity"]["database_sha256"] == shadow.DATABASE_SHA256
    assert tuple(
        component["component_id"] for component in definition["components_in_exact_order"]
    ) == shadow.COMPONENTS
    alignment = definition["time_and_alignment_contract"]
    assert alignment["accepted_session_dates"].startswith("exactly 121 strictly increasing")
    assert alignment["as_of"] == "15:00:00 Asia/Shanghai on the final accepted_session_date"
    assert alignment["ordered_universe_digests"].endswith("all four must be identical")
    assert definition["aggregation"]["finite_gate"].startswith("every raw value")
    assert definition["staleness_and_missing_behavior"]["imputation"] == "forbidden"
    assert definition["boundaries"] == {
        "shadow_only": True,
        "position_effect_enabled": False,
        "strategy_selection_enabled": False,
        "order_or_signal_enabled": False,
        "use_as_strategy_gate": False,
        "strategy_candidate_available": False,
        "real_weekly_record_computation_authorized_by_this_artifact": False,
    }


def test_all_low_risk_synthetic_inputs_produce_exact_green_record() -> None:
    result = shadow.compute_shadow(_input())
    assert result.status == "SHADOW_READY"
    assert result.risk_score == 0.0
    assert result.risk_level == "GREEN"
    assert result.confidence == 1.0
    assert tuple(item.component_id for item in result.component_contributions) == shadow.COMPONENTS
    assert all(
        math.isfinite(item.raw_value)
        and item.unit_risk == 0.0
        and item.contribution_points == 0.0
        for item in result.component_contributions
    )
    assert result.stale_components == result.missing_components == ()


def test_adverse_synthetic_inputs_produce_deterministic_red_record() -> None:
    result = shadow.compute_shadow(_input(adverse=True))
    assert result.status == "SHADOW_READY"
    assert result.risk_score == 77.777778
    assert result.risk_level == "RED"
    risks = {item.component_id: item.unit_risk for item in result.component_contributions}
    assert risks == {
        "trend_120": 1.0,
        "realized_volatility_20": 0.0,
        "realized_volatility_60": 0.0,
        "drawdown_120": 1.0,
        "positive_return_breadth_60": 1.0,
        "above_moving_average_breadth_60": 1.0,
        "amount_breadth_20": 1.0,
        "limit_down_share": 1.0,
        "suspension_share": 1.0,
    }


def test_extreme_finite_ratio_overflow_blocks_affected_component() -> None:
    smallest = float.fromhex("0x0.0000000000001p-1022")
    largest = float.fromhex("0x1.fffffffffffffp+1023")
    benchmark = (smallest,) + (1.0,) * 119 + (largest,)
    result = shadow.compute_shadow(replace(_input(), benchmark_closes=benchmark))
    assert result.status == "SHADOW_INPUT_BLOCKED"
    assert "trend_120" in result.missing_components
    assert result.risk_score is result.risk_level is None
    assert result.component_contributions == ()


def test_huge_real_input_conversion_overflow_is_reported_as_missing() -> None:
    benchmark = (10**10000,) + _input().benchmark_closes[1:]
    result = shadow.compute_shadow(replace(_input(), benchmark_closes=benchmark))
    assert result.status == "SHADOW_INPUT_BLOCKED"
    assert result.missing_components == shadow.COMPONENTS[:4]
    assert result.risk_score is result.risk_level is None
    assert result.component_contributions == ()


def test_extreme_finite_cross_section_uses_log_difference_without_ratio_overflow() -> None:
    smallest = float.fromhex("0x0.0000000000001p-1022")
    largest = float.fromhex("0x1.fffffffffffffp+1023")
    extreme = (smallest,) + (1.0,) * 59 + (largest,)
    data = _input()
    result = shadow.compute_shadow(
        replace(data, stock_closes=(extreme, *data.stock_closes[1:]))
    )
    assert result.status == "SHADOW_READY"
    assert all(math.isfinite(item.raw_value) for item in result.component_contributions)


def test_nonfinite_contribution_is_rechecked_before_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(shadow, "_unit_risk", lambda component, value: float("inf"))
    result = shadow.compute_shadow(_input())
    assert result.status == "SHADOW_INPUT_BLOCKED"
    assert result.missing_components == shadow.COMPONENTS
    assert result.component_contributions == ()


def test_eight_calendar_day_staleness_blocks_all_components_without_score() -> None:
    result = shadow.compute_shadow(
        replace(_input(), generated_at=AS_OF + timedelta(days=8))
    )
    assert result.status == "SHADOW_INPUT_BLOCKED"
    assert result.risk_score is result.risk_level is None
    assert result.confidence == 0.0
    assert result.component_contributions == ()
    assert result.stale_components == shadow.COMPONENTS
    assert result.missing_components == ()


def test_stale_and_missing_components_are_both_reported() -> None:
    result = shadow.compute_shadow(
        replace(
            _input(),
            generated_at=AS_OF + timedelta(days=8),
            limit_down_flags=(None, False, False, False),
        )
    )
    assert result.stale_components == shadow.COMPONENTS
    assert result.missing_components == ("limit_down_share",)
    assert result.risk_score is result.risk_level is None


@pytest.mark.parametrize(
    ("change", "missing"),
    (
        (
            {"benchmark_closes": (None,) + _input().benchmark_closes[1:]},
            shadow.COMPONENTS[:4],
        ),
        (
            {
                "stock_closes": (
                    (None,) + _input().stock_closes[0][1:],
                    *_input().stock_closes[1:],
                )
            },
            shadow.COMPONENTS[4:6],
        ),
        (
            {
                "stock_amount_cny": (
                    (0.0,) + _input().stock_amount_cny[0][1:],
                    *_input().stock_amount_cny[1:],
                )
            },
            ("amount_breadth_20",),
        ),
        ({"limit_down_flags": (None, False, False, False)}, ("limit_down_share",)),
    ),
)
def test_missing_component_blocks_whole_record_without_imputation(
    change: dict[str, object], missing: tuple[str, ...]
) -> None:
    result = shadow.compute_shadow(replace(_input(), **change))
    assert result.status == "SHADOW_INPUT_BLOCKED"
    assert result.risk_score is result.risk_level is None
    assert result.confidence == 0.0
    assert result.component_contributions == ()
    assert result.missing_components == missing


def test_sunday_in_accepted_sessions_blocks_all_components() -> None:
    data = _input()
    dates = list(data.accepted_session_dates)
    monday_index = next(index for index, day in enumerate(dates[1:-1], 1) if day.weekday() == 0)
    dates[monday_index] -= timedelta(days=1)
    invalid = tuple(dates)
    result = shadow.compute_shadow(
        replace(
            data,
            accepted_session_dates=invalid,
            stock_price_session_dates=invalid[-61:],
            stock_amount_session_dates=invalid[-21:],
        )
    )
    assert result.status == "SHADOW_INPUT_BLOCKED"
    assert result.missing_components == shadow.COMPONENTS


@pytest.mark.parametrize(
    "change",
    (
        {"as_of": AS_OF.replace(hour=14, minute=59)},
        {"as_of": AS_OF.astimezone(timezone.utc)},
        {"stock_price_session_dates": _sessions()[-62:-1]},
        {"stock_amount_session_dates": _sessions()[-22:-1]},
        {"flag_session_date": _sessions()[-2]},
        {"amount_universe_digest": "1" * 64},
        {"limit_down_universe_digest": "A" * 64},
        {"ordered_universe_count": 5},
        {"snapshot_id": "another-snapshot"},
        {"database_sha256": "0" * 64},
        {"generated_at": AS_OF - timedelta(seconds=1)},
    ),
)
def test_time_pit_digest_count_and_identity_mismatch_block_all_components(
    change: dict[str, object],
) -> None:
    result = shadow.compute_shadow(replace(_input(), **change))
    assert result.status == "SHADOW_INPUT_BLOCKED"
    assert result.missing_components == shadow.COMPONENTS
    assert result.risk_score is result.risk_level is None


def test_duplicate_or_reversed_accepted_date_blocks_all_components() -> None:
    data = _input()
    dates = list(data.accepted_session_dates)
    dates[60] = dates[59]
    result = shadow.compute_shadow(replace(data, accepted_session_dates=tuple(dates)))
    assert result.status == "SHADOW_INPUT_BLOCKED"
    assert result.missing_components == shadow.COMPONENTS


def test_aggregate_serialization_has_no_identifier_or_action_surface() -> None:
    payload = shadow.compute_shadow(_input()).to_dict()
    encoded = json.dumps(payload, sort_keys=True)
    assert ".SH" not in encoded and ".SZ" not in encoded
    assert "symbol" not in encoded and "ranking" not in encoded
    assert payload["position_effect_enabled"] is False
    assert payload["strategy_selection_enabled"] is False
    assert payload["order_or_signal_enabled"] is False
    assert payload["strategy_candidate_available"] is False
    assert payload["input_snapshot_identity"] == {
        "snapshot_id": shadow.SNAPSHOT_ID,
        "database_sha256": shadow.DATABASE_SHA256,
    }


def test_module_has_no_database_network_runner_or_cli_dependency() -> None:
    source = (ROOT / "src/quant_system/research/macro_risk_shadow.py").read_text()
    for forbidden in (
        "import duckdb",
        "import requests",
        "import socket",
        "argparse",
        "subprocess",
    ):
        assert forbidden not in source
