from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import random
import stat
from types import SimpleNamespace

import pytest

from research.adapters import c35_cftc_vix_positioning_risk_rotation as adapter
from research.adapters.c35_cftc_vix_positioning_risk_rotation import (
    BOOTSTRAP_BLOCK_MONTHS,
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    HOLDOUT_INTERVALS,
    PROGRAM_ALPHA,
    VALIDATION_INTERVALS,
    InputContractError,
    circular_block_indices,
    holdout_decision,
    validation_decision,
)
from scripts import run_c35_cftc_vix_positioning_risk_rotation_once as runner


ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_frozen_definition_adapter_and_program_constants_are_exact() -> None:
    assert sha(runner.DEFINITION) == runner.DEFINITION_SHA256
    assert sha(runner.ADAPTER) == runner.ADAPTER_SHA256
    assert runner._core_identity() == (
        runner.CORE_SOURCE_FILE_COUNT,
        runner.CORE_SOURCE_SHA256,
    )
    assert VALIDATION_INTERVALS == 28
    assert HOLDOUT_INTERVALS == 34
    assert PROGRAM_ALPHA == 0.016666666666666666
    assert BOOTSTRAP_RESAMPLES == 100_000
    assert BOOTSTRAP_BLOCK_MONTHS == 3
    assert BOOTSTRAP_SEED == 3_500_101


def test_definition_is_single_variant_outcome_blind_and_nontrading() -> None:
    record = json.loads(runner.DEFINITION.read_text(encoding="utf-8"))
    assert record["selection_without_outcomes"][
        "price_return_nav_sharpe_or_drawdown_used_for_selection"
    ] is False
    assert record["selection_without_outcomes"]["parameter_grid"] is False
    assert record["selection_without_outcomes"]["variant_count"] == 1
    assert record["program_multiplicity"]["alpha_recycling"] is False
    assert record["program_multiplicity"]["epoch3_mechanism_count"] == 3
    assert record["program_multiplicity"]["sole_primary_alpha"] == PROGRAM_ALPHA
    assert record["program_multiplicity"]["lifetime_fwer_claim"] is False
    assert record["source_identities"]["adapter_sha256"] == runner.ADAPTER_SHA256
    assert record["expected_inclusion_rule_sha256"] == runner.INCLUSION_RULE_SHA256
    assert record["terminal_rules"]["rerun"] is False
    assert all(value is False for value in record["boundaries"].values())


def test_validation_requires_all_three_frozen_gates() -> None:
    passing = validation_decision(
        (0.01,) * VALIDATION_INTERVALS,
        (0.005,) * VALIDATION_INTERVALS,
    )
    assert passing.all_gates_pass is True
    assert all(value for _, value in passing.gates)

    failing = validation_decision(
        (0.0,) * VALIDATION_INTERVALS,
        (0.005,) * VALIDATION_INTERVALS,
    )
    assert failing.all_gates_pass is False
    assert dict(failing.gates)[
        "strategy_terminal_net_wealth_strictly_above_50_50_comparator"
    ] is False


@pytest.mark.parametrize(
    "strategy,comparator",
    [
        ((0.0,) * (VALIDATION_INTERVALS - 1), (0.0,) * VALIDATION_INTERVALS),
        ((float("nan"),) + (0.0,) * (VALIDATION_INTERVALS - 1), (0.0,) * VALIDATION_INTERVALS),
        ((-1.0,) + (0.0,) * (VALIDATION_INTERVALS - 1), (0.0,) * VALIDATION_INTERVALS),
    ],
)
def test_validation_fails_closed_on_invalid_returns(
    strategy: tuple[float, ...], comparator: tuple[float, ...]
) -> None:
    with pytest.raises(InputContractError):
        validation_decision(strategy, comparator)


def test_bootstrap_index_sequence_has_a_literal_golden_vector() -> None:
    rng = random.Random(BOOTSTRAP_SEED)
    assert circular_block_indices(8, block_length=3, rng=rng) == (
        6,
        7,
        0,
        7,
        0,
        1,
        4,
        5,
    )
    assert circular_block_indices(8, block_length=3, rng=rng) == (
        6,
        7,
        0,
        7,
        0,
        1,
        3,
        4,
    )


def test_adjacent_nav_returns_use_all_neighboring_pairs_without_strict_zip_bug() -> None:
    assert runner._adjacent_returns([100.0, 110.0, 99.0]) == pytest.approx(
        (0.1, -0.1)
    )
    for bad in (
        [100.0],
        [100.0, float("nan")],
        [100.0, float("inf")],
        [100.0, 0.0],
    ):
        with pytest.raises(runner.InputBlockedError):
            runner._adjacent_returns(bad)


def test_constant_positive_active_holdout_passes_exact_inference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(adapter, "BOOTSTRAP_RESAMPLES", 20_000)
    monkeypatch.setattr(adapter, "PROGRAM_ALPHA", 0.001)
    decision = holdout_decision(
        (0.01,) * HOLDOUT_INTERVALS,
        (0.0,) * HOLDOUT_INTERVALS,
    )
    assert decision.all_gates_pass is True
    assert decision.inference.centered_null_one_sided_p == pytest.approx(1 / 20001)
    assert decision.inference.uncentered_lower_bound == pytest.approx(0.01)


def _month(value: date, offset: int) -> date:
    ordinal = value.year * 12 + value.month - 1 + offset
    return date(ordinal // 12, ordinal % 12 + 1, 1)


def _synthetic_signal_packet() -> bytes:
    def contract(
        report_date: date,
        long_value: int,
        short_value: int,
    ) -> dict:
        identity = {
            "market_and_exchange_name": "VIX FUTURES - CBOE FUTURES EXCHANGE",
            "report_date": report_date.isoformat(),
            "cftc_contract_market_code": runner.CFTC_VIX_CODE,
            "open_interest_all": 1000,
            "leveraged_money_long_all": long_value,
            "leveraged_money_short_all": short_value,
            "futures_only_or_combined": "FutOnly",
            "source_class": (
                "OFFICIAL_CFTC_TFF_FUTURES_ONLY_HISTORICAL_COMPRESSED"
            ),
            "raw_response_sha256": runner.CFTC_RAW_SHA_BY_YEAR[report_date.year],
        }
        return {
            **identity,
            "row_sha256": hashlib.sha256(
                json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        }

    def selection(report_date: date, positive_position: bool) -> dict:
        vix = contract(
            report_date,
            650 if positive_position else 550,
            350 if positive_position else 450,
        )
        vix_ratio = (
            vix["leveraged_money_long_all"] - vix["leveraged_money_short_all"]
        ) / vix["open_interest_all"]
        available_at = datetime.combine(
            report_date + timedelta(days=10), datetime.max.time(), runner.NY
        )
        identity = {
            "report_date": report_date.isoformat(),
            "available_at_conservative": available_at.isoformat(),
            "availability_rule": runner.CFTC_AVAILABILITY_RULE,
            "vix_contract_row_sha256": vix["row_sha256"],
            "vix_leveraged_money_net_pct_oi": vix_ratio,
        }
        return {
            **identity,
            "vix_contract_row": vix,
            "selection_row_sha256": hashlib.sha256(
                json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        }

    rows: list[dict] = []
    state_support: dict[str, dict[str, int]] = {}
    for stage, first, count in (
        ("validation", date(2021, 2, 1), VALIDATION_INTERVALS),
        ("retrospective_holdout", date(2023, 8, 1), HOLDOUT_INTERVALS),
    ):
        targets: list[str] = []
        prior_cutoff = datetime(
            2020 if stage == "validation" else 2023,
            12 if stage == "validation" else 6,
            31 if stage == "validation" else 30,
            20,
            5,
            tzinfo=runner.NY,
        )
        previous = selection(
            date(2020, 12, 15) if stage == "validation" else date(2023, 6, 15),
            False,
        )
        for index in range(count):
            start = _month(first, index)
            end = _month(first, index + 1)
            report_month = _month(start, -1)
            report_date = date(report_month.year, report_month.month, 12)
            current = selection(report_date, index % 2 == 0)
            delta = (
                current["vix_leveraged_money_net_pct_oi"]
                - previous["vix_leveraged_money_net_pct_oi"]
            )
            target = "SPY" if delta > 0.0 else "QQQ"
            targets.append(target)
            decision_at = datetime(
                report_month.year,
                report_month.month,
                28,
                20,
                5,
                tzinfo=runner.NY,
            )
            identity = {
                "stage": stage,
                "holding_start_execution_session": start.isoformat(),
                "holding_end_execution_session": end.isoformat(),
                "decision_at": decision_at.isoformat(),
                "prior_monthly_cutoff": prior_cutoff.isoformat(),
                "previous_report_date": previous["report_date"],
                "current_report_date": current["report_date"],
                "previous_selection_row_sha256": previous[
                    "selection_row_sha256"
                ],
                "current_selection_row_sha256": current["selection_row_sha256"],
                "delta_vix_leveraged_money_net_pct_oi": delta,
                "target_symbol": target,
            }
            rows.append(
                {
                    **identity,
                    "current_selection": current,
                    "previous_selection": previous,
                    "signal_identity_sha256": hashlib.sha256(
                        json.dumps(
                            identity, sort_keys=True, separators=(",", ":")
                        ).encode()
                    ).hexdigest(),
                }
            )
            prior_cutoff = decision_at
            previous = current
        state_support[stage] = {
            "complete_intervals": len(targets),
            "spy_intervals": targets.count("SPY"),
            "qqq_intervals": targets.count("QQQ"),
            "spy_to_qqq": sum(
                left == "SPY" and right == "QQQ"
                for left, right in zip(targets, targets[1:], strict=False)
            ),
            "qqq_to_spy": sum(
                left == "QQQ" and right == "SPY"
                for left, right in zip(targets, targets[1:], strict=False)
            ),
        }
    return json.dumps(
        {
            "schema_version": (
                "c35-cftc-vix-positioning-spy-qqq-input-v1"
            ),
            "research_id": runner.RESEARCH_ID,
            "strategy_outcomes_opened": False,
            "price_values_used_for_signal": False,
            "spy_price_values_used_for_materialization": False,
            "adjusted_prices_used": False,
            "database_opened": False,
            "database_write": False,
            "source_selected_using_performance": False,
            "signal_contract": {
                "vix_contract_code": runner.CFTC_VIX_CODE,
                "target_rule": "delta of VIX leveraged-money net percent of open interest strictly above zero means SPY; equal or below zero means QQQ",
                "threshold": 0.0,
            },
            "signals": rows,
            "state_support": state_support,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def test_synthetic_signal_packet_reproduces_rule_without_price_access() -> None:
    payload = _synthetic_signal_packet()
    groups = runner._signals(payload)
    assert len(groups["validation"]) == VALIDATION_INTERVALS
    assert len(groups["retrospective_holdout"]) == HOLDOUT_INTERVALS
    assert sum(row.target_symbol == "QQQ" for row in groups["validation"]) == 14
    assert sum(row.target_symbol == "SPY" for row in groups["validation"]) == 14
    assert sum(row.target_symbol == "QQQ" for row in groups["retrospective_holdout"]) == 17
    assert sum(row.target_symbol == "SPY" for row in groups["retrospective_holdout"]) == 17
    record = json.loads(payload)
    assert record["strategy_outcomes_opened"] is False
    lowered = payload.lower()
    for forbidden in (
        b'"terminal_wealth"',
        b'"nav"',
        b'"sharpe"',
        b'"strategy_returns"',
        b'"comparator_returns"',
    ):
        assert forbidden not in lowered


def test_signal_packet_rejects_state_tampering() -> None:
    record = json.loads(_synthetic_signal_packet())
    record["signals"][0]["target_symbol"] = "QQQ"
    payload = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    with pytest.raises(runner.InputBlockedError, match="signal arithmetic"):
        runner._signals(payload)


def test_real_input_bytes_are_hash_bound_and_signals_match_frozen_support() -> None:
    assert sha(runner.SIGNAL_INPUT) == runner.SIGNAL_SHA256
    assert sha(runner.INPUT_RECEIPT) == runner.RECEIPT_SHA256
    groups = runner._signals(runner.SIGNAL_INPUT.read_bytes())
    validation = tuple(row.target_symbol for row in groups["validation"])
    holdout = tuple(row.target_symbol for row in groups["retrospective_holdout"])
    assert (validation.count("SPY"), validation.count("QQQ")) == (16, 12)
    assert (holdout.count("SPY"), holdout.count("QQQ")) == (16, 18)


def test_rebalance_binds_two_asset_universe_and_exact_weights(monkeypatch) -> None:
    captured = {}

    def fake(portfolio, calendar, **kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(runner, "run_static_rebalance", fake)
    point = SimpleNamespace(
        calendar=object(),
        signal_session=date(2021, 1, 29),
        decision_at=datetime(2021, 2, 1, 14, 0, tzinfo=timezone.utc),
        executions=("QQQ_INPUT", "SPY_INPUT"),
        revision=None,
        snapshot=object(),
    )
    runner._rebalance(object(), point, {"QQQ": 1.0}, "0" * 64)
    assert captured["execution_inputs"] == ("QQQ_INPUT", "SPY_INPUT")
    assert captured["universe_members"] == ("QQQ", "SPY")
    assert captured["target_weights"](None) == {"QQQ": 1.0}


def test_strict_json_rejects_duplicate_keys_and_nonfinite_values() -> None:
    with pytest.raises(runner.InputBlockedError, match="duplicate JSON key"):
        runner._json(b'{"a":1,"a":2}', "test")
    with pytest.raises(runner.InputBlockedError, match="nonfinite JSON constant"):
        runner._json(b'{"a":NaN}', "test")


def test_private_publication_is_one_use_and_mode_0600(tmp_path: Path) -> None:
    destination = tmp_path / "private" / "result.json"
    value = {"classification": "TEST_ONLY"}
    digest = runner._publish(destination, value)
    assert digest == hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600
    with pytest.raises(runner.InputBlockedError):
        runner._publish(destination, value)


def test_capture_rejects_symlinks(tmp_path: Path) -> None:
    target = tmp_path / "target.json"
    target.write_bytes(b"{}")
    link = tmp_path / "link.json"
    link.symlink_to(target)
    with pytest.raises(runner.InputBlockedError, match="cannot open protected input"):
        runner._capture(link, hashlib.sha256(b"{}").hexdigest(), max_bytes=10)


def test_real_one_use_state_is_pristine_or_mechanically_terminal() -> None:
    if not runner.VALIDATION_CLAIM.exists():
        assert not runner.VALIDATION_RESULT.exists()
        assert not runner.HOLDOUT_CLAIM.exists()
        assert not runner.HOLDOUT_RESULT.exists()
        return
    assert runner.VALIDATION_RESULT.exists()
    result = json.loads(runner.VALIDATION_RESULT.read_text(encoding="utf-8"))
    classification = result["classification"]
    if classification == "RETROSPECTIVE_SECONDARY_VALIDATION_PASS_HOLDOUT_UNLOCKED":
        assert result["decision"]["all_gates_pass"] is True
        assert runner.HOLDOUT_CLAIM.exists() is runner.HOLDOUT_RESULT.exists()
        if runner.HOLDOUT_RESULT.exists():
            holdout = json.loads(runner.HOLDOUT_RESULT.read_text(encoding="utf-8"))
            assert holdout["classification"] in {
                "RETROSPECTIVE_SECONDARY_PASS_PENDING_REVIEW",
                "RETROSPECTIVE_SECONDARY_HOLDOUT_FAIL",
                "INPUT_BLOCKED_CLAIM_CONSUMED",
            }
    else:
        assert classification in {
            "RETROSPECTIVE_SECONDARY_VALIDATION_FAIL",
            "INPUT_BLOCKED_CLAIM_CONSUMED",
        }
        assert not runner.HOLDOUT_CLAIM.exists()
        assert not runner.HOLDOUT_RESULT.exists()
