from __future__ import annotations

import hashlib
import json
from pathlib import Path
import random
import stat

import pytest

from research.adapters.c10_vix20_fear_regime import (
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
from scripts import run_c10_vix20_fear_regime_once as runner


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
    assert PROGRAM_ALPHA == 0.00009765625
    assert BOOTSTRAP_RESAMPLES == 20_000
    assert BOOTSTRAP_BLOCK_MONTHS == 3
    assert BOOTSTRAP_SEED == 1_200_101


def test_definition_is_single_variant_outcome_blind_and_nontrading() -> None:
    record = json.loads(runner.DEFINITION.read_text(encoding="utf-8"))
    assert record["selection_without_outcomes"][
        "price_return_nav_sharpe_or_drawdown_used_for_selection"
    ] is False
    assert record["selection_without_outcomes"]["parameter_grid"] is False
    assert record["selection_without_outcomes"]["variant_count"] == 1
    assert record["program_multiplicity"]["alpha_recycling"] is False
    assert record["source_identities"]["adapter_sha256"] == runner.ADAPTER_SHA256
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
        "strategy_terminal_net_wealth_strictly_above_spy"
    ] is False


@pytest.mark.parametrize(
    "strategy,spy",
    [
        ((0.0,) * (VALIDATION_INTERVALS - 1), (0.0,) * VALIDATION_INTERVALS),
        ((float("nan"),) + (0.0,) * (VALIDATION_INTERVALS - 1), (0.0,) * VALIDATION_INTERVALS),
        ((-1.0,) + (0.0,) * (VALIDATION_INTERVALS - 1), (0.0,) * VALIDATION_INTERVALS),
    ],
)
def test_validation_fails_closed_on_invalid_returns(
    strategy: tuple[float, ...], spy: tuple[float, ...]
) -> None:
    with pytest.raises(InputContractError):
        validation_decision(strategy, spy)


def test_bootstrap_index_sequence_has_a_literal_golden_vector() -> None:
    rng = random.Random(BOOTSTRAP_SEED)
    assert circular_block_indices(8, block_length=3, rng=rng) == (
        4,
        5,
        6,
        4,
        5,
        6,
        1,
        2,
    )
    assert circular_block_indices(8, block_length=3, rng=rng) == (
        4,
        5,
        6,
        3,
        4,
        5,
        1,
        2,
    )


def test_constant_positive_active_holdout_passes_exact_inference() -> None:
    decision = holdout_decision(
        (0.01,) * HOLDOUT_INTERVALS,
        (0.0,) * HOLDOUT_INTERVALS,
    )
    assert decision.all_gates_pass is True
    assert decision.inference.centered_null_one_sided_p == pytest.approx(1 / 20001)
    assert decision.inference.uncentered_lower_bound == pytest.approx(0.01)


def test_signal_packet_reproduces_frozen_support_without_price_access() -> None:
    payload = runner.SIGNAL_INPUT.read_bytes()
    groups = runner._signals(payload)
    assert len(groups["validation"]) == VALIDATION_INTERVALS
    assert len(groups["retrospective_holdout"]) == HOLDOUT_INTERVALS
    assert sum(row.target == 1.0 for row in groups["validation"]) == 11
    assert sum(row.target == 0.0 for row in groups["validation"]) == 17
    assert sum(row.target == 1.0 for row in groups["retrospective_holdout"]) == 30
    assert sum(row.target == 0.0 for row in groups["retrospective_holdout"]) == 4
    lowered = payload.lower()
    for forbidden in (b'"return"', b'"wealth"', b'"nav"', b'"sharpe"', b'"price"'):
        assert forbidden not in lowered


def test_signal_packet_rejects_state_tampering() -> None:
    record = json.loads(runner.SIGNAL_INPUT.read_text(encoding="utf-8"))
    record["signals"][0]["state"] = "CASH" if record["signals"][0]["state"] == "SPY" else "SPY"
    payload = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    with pytest.raises(runner.InputBlockedError, match="signal arithmetic"):
        runner._signals(payload)


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


def test_real_one_use_state_is_pristine_or_terminal_without_holdout() -> None:
    if not runner.VALIDATION_CLAIM.exists():
        assert not runner.VALIDATION_RESULT.exists()
        assert not runner.HOLDOUT_CLAIM.exists()
        assert not runner.HOLDOUT_RESULT.exists()
        return
    assert runner.VALIDATION_RESULT.exists()
    result = json.loads(runner.VALIDATION_RESULT.read_text(encoding="utf-8"))
    assert result["classification"] == "RETROSPECTIVE_SECONDARY_VALIDATION_FAIL"
    assert result["decision"]["all_gates_pass"] is False
    assert not runner.HOLDOUT_CLAIM.exists()
    assert not runner.HOLDOUT_RESULT.exists()
