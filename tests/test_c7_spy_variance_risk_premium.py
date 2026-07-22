from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from research.adapters.c7_spy_variance_risk_premium import (
    BOOTSTRAP_BLOCK_LENGTH,
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    HOLDOUT_INTERVALS,
    PROGRAM_ALPHA,
    RESEARCH_ID,
    VALIDATION_INTERVALS,
    InputContractError,
    bootstrap_inference,
    circular_block_bootstrap_indices,
    holdout_decision,
    validation_decision,
)

RUNNER_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts/run_c7_spy_variance_risk_premium_once.py"
)
SPEC = importlib.util.spec_from_file_location("c7_vrp_runner", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)

_VALIDATION_STATES = (
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    0,
    1,
    1,
    0,
    1,
    0,
    0,
    1,
    1,
    1,
    1,
    0,
    1,
    1,
    1,
    0,
    1,
    1,
)
_HOLDOUT_STATES = (
    1,
    1,
    1,
    1,
    1,
    0,
    1,
    1,
    1,
    1,
    0,
    1,
    1,
    1,
    0,
    0,
    1,
    0,
    1,
    1,
    1,
    1,
    0,
    0,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    0,
    1,
    1,
)


def _sha(seed: str) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


def _strict_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()


def _definition() -> dict[str, object]:
    return json.loads(RUNNER.DEFINITION.read_text())


def _month(start: date, offset: int) -> date:
    index = start.year * 12 + start.month - 1 + offset
    return date(index // 12, index % 12 + 1, 1)


def _signal_payload() -> dict[str, object]:
    definition = _definition()
    rows: list[dict[str, object]] = []
    starts = {
        "validation": date(2021, 1, 1),
        "holdout": date(2023, 6, 1),
    }
    for split, states in (
        ("validation", _VALIDATION_STATES),
        ("holdout", _HOLDOUT_STATES),
    ):
        for index, target in enumerate(states):
            signal = _month(starts[split], index)
            execution = signal + timedelta(days=1)
            vix_variance = 0.04 if target else 0.01
            realized_variance = 0.01 if target else 0.02
            premium = vix_variance - realized_variance
            rows.append(
                {
                    "decision_at": datetime.combine(
                        execution,
                        time(9),
                        tzinfo=ZoneInfo("America/New_York"),
                    ).isoformat(),
                    "distribution_action_ids": [],
                    "execution_session": execution.isoformat(),
                    "realized_variance_hex": float.hex(realized_variance),
                    "row_sha256": _sha(f"{split}-row-{index}"),
                    "signal_session": signal.isoformat(),
                    "split_membership": split,
                    "target_weight": float(target),
                    "variance_risk_premium_hex": float.hex(premium),
                    "vix_row_sha256": _sha(f"{split}-vix-{index}"),
                    "vix_variance_hex": float.hex(vix_variance),
                    "weekly_source_point_sha256": [
                        _sha(f"{split}-source-{index}-{offset}")
                        for offset in range(5)
                    ],
                }
            )
    return {
        "definition_sha256": RUNNER.PARENT_PREREGISTRATION_SHA256,
        "research_id": RESEARCH_ID,
        "schema_version": "c7-spy-variance-risk-premium-signal-input-v1",
        "selected_monthly_rows": rows,
        "signal_formula": definition["signal"],
        "source_identities": {
            "holdout_spy_bundle_sha256": RUNNER.HOLDOUT_BUNDLE_SHA256,
            "validation_spy_bundle_sha256": RUNNER.VALIDATION_BUNDLE_SHA256,
            "weekly_vix_input_sha256": RUNNER.WEEKLY_VIX_INPUT_SHA256,
        },
        "support": definition["runtime_materialization"]["accepted_support"],
        "support_status": "PASS_STATE_SUPPORT",
    }


def test_frozen_constants_and_code_identities_are_exact() -> None:
    assert RESEARCH_ID == "C7_SPY_VARIANCE_RISK_PREMIUM_V1"
    assert PROGRAM_ALPHA == 0.00078125
    assert (VALIDATION_INTERVALS, HOLDOUT_INTERVALS) == (28, 36)
    assert (BOOTSTRAP_RESAMPLES, BOOTSTRAP_SEED, BOOTSTRAP_BLOCK_LENGTH) == (
        10_000,
        119_702,
        3,
    )
    assert RUNNER._file_sha256(RUNNER.DEFINITION) == RUNNER.DEFINITION_SHA256
    assert RUNNER._file_sha256(RUNNER.ADAPTER) == RUNNER.ADAPTER_SHA256
    assert RUNNER._core_identity() == (
        RUNNER.CORE_SOURCE_FILE_COUNT,
        RUNNER.CORE_SOURCE_SHA256,
    )
    definition = RUNNER._validate_definition(RUNNER.DEFINITION.read_bytes())
    assert definition["code_identity"]["adapter_sha256"] == RUNNER.ADAPTER_SHA256


def test_validation_passes_only_when_all_three_frozen_gates_pass() -> None:
    decision = validation_decision(
        (0.01,) * VALIDATION_INTERVALS,
        (0.005,) * VALIDATION_INTERVALS,
    )
    assert decision.all_gates_pass is True
    assert dict(decision.gates) == {
        "strategy_terminal_net_wealth_strictly_above_spy": True,
        "arithmetic_mean_paired_monthly_active_return_strictly_positive": True,
        "strategy_maximum_drawdown_no_worse_than_spy": True,
    }

    failure = validation_decision(
        (0.0,) * VALIDATION_INTERVALS,
        (0.01,) * VALIDATION_INTERVALS,
    )
    assert failure.all_gates_pass is False
    assert tuple(dict(failure.gates).values()) == (False, False, True)


@pytest.mark.parametrize(
    "strategy,spy",
    [
        ((0.0,) * (VALIDATION_INTERVALS - 1), (0.0,) * VALIDATION_INTERVALS),
        ((math.nan,) + (0.0,) * 27, (0.0,) * VALIDATION_INTERVALS),
        ((-1.0,) + (0.0,) * 27, (0.0,) * VALIDATION_INTERVALS),
        ([0.0] * VALIDATION_INTERVALS, (0.0,) * VALIDATION_INTERVALS),
    ],
)
def test_inference_rejects_incomplete_nonfinite_or_non_tuple_inputs(
    strategy,
    spy,
) -> None:
    with pytest.raises(InputContractError):
        validation_decision(strategy, spy)


def test_bootstrap_has_literal_golden_paths_and_is_repeatable() -> None:
    paths = circular_block_bootstrap_indices()
    assert len(paths) == 10_000
    assert paths[0] == (
        11,
        12,
        13,
        6,
        7,
        8,
        22,
        23,
        24,
        10,
        11,
        12,
        21,
        22,
        23,
        29,
        30,
        31,
        5,
        6,
        7,
        18,
        19,
        20,
        18,
        19,
        20,
        5,
        6,
        7,
        33,
        34,
        35,
        18,
        19,
        20,
    )
    assert paths == circular_block_bootstrap_indices()


def test_constant_positive_active_return_passes_frozen_holdout_inference() -> None:
    decision = holdout_decision(
        (0.001,) * HOLDOUT_INTERVALS,
        (0.0,) * HOLDOUT_INTERVALS,
    )
    assert decision.all_gates_pass is True
    assert decision.inference.centered_null_one_sided_p == pytest.approx(1 / 10001)
    assert decision.inference.uncentered_type7_lower_bound == pytest.approx(0.001)
    direct = bootstrap_inference((0.001,) * HOLDOUT_INTERVALS)
    assert direct == decision.inference


def test_signal_packet_reproduces_exact_support_and_timing() -> None:
    payload = _signal_payload()
    groups = RUNNER._signal_rows(_strict_bytes(payload), _definition())
    assert len(groups["validation"]) == 29
    assert len(groups["holdout"]) == 37
    assert groups["validation"][0].target_weight == 1.0
    assert groups["validation"][-1].target_weight == 1.0


def test_signal_packet_rejects_support_drift_even_when_row_arithmetic_is_valid() -> None:
    payload = _signal_payload()
    row = payload["selected_monthly_rows"][0]
    row["target_weight"] = 0.0
    row["vix_variance_hex"] = float.hex(0.01)
    row["realized_variance_hex"] = float.hex(0.02)
    row["variance_risk_premium_hex"] = float.hex(0.01 - 0.02)
    with pytest.raises(RUNNER.InputBlockedError, match="accepted support"):
        RUNNER._signal_rows(_strict_bytes(payload), _definition())


def test_signal_packet_rejects_duplicate_identity_and_bad_hex() -> None:
    duplicate = _signal_payload()
    duplicate["selected_monthly_rows"][1]["row_sha256"] = duplicate[
        "selected_monthly_rows"
    ][0]["row_sha256"]
    with pytest.raises(RUNNER.InputBlockedError, match="must be unique"):
        RUNNER._signal_rows(_strict_bytes(duplicate), _definition())

    bad_hex = _signal_payload()
    bad_hex["selected_monthly_rows"][0]["vix_variance_hex"] = "nan"
    with pytest.raises(RUNNER.InputBlockedError, match="variance"):
        RUNNER._signal_rows(_strict_bytes(bad_hex), _definition())


def test_strict_json_rejects_duplicate_keys_and_nonfinite_constants() -> None:
    with pytest.raises(RUNNER.InputBlockedError, match="duplicate JSON key"):
        RUNNER._json(b'{"a":1,"a":2}', "test")
    with pytest.raises(RUNNER.InputBlockedError, match="nonfinite JSON"):
        RUNNER._json(b'{"a":NaN}', "test")


def test_descriptor_bound_capture_rejects_symlink_and_hash_drift(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    source.write_bytes(b"{}")
    source.chmod(0o600)
    digest = hashlib.sha256(b"{}").hexdigest()
    assert RUNNER._capture(source, digest, max_bytes=16) == b"{}"
    with pytest.raises(RUNNER.InputBlockedError, match="SHA-256 mismatch"):
        RUNNER._capture(source, "0" * 64, max_bytes=16)
    link = tmp_path / "link.json"
    link.symlink_to(source)
    with pytest.raises(RUNNER.InputBlockedError, match="cannot open"):
        RUNNER._capture(link, digest, max_bytes=16)


def test_private_publication_is_one_use_and_mode_0600(tmp_path: Path) -> None:
    target = tmp_path / "private" / "record.json"
    digest = RUNNER._publish(target, {"status": "test"})
    assert digest == hashlib.sha256(target.read_bytes()).hexdigest()
    assert target.stat().st_mode & 0o777 == 0o600
    with pytest.raises(RUNNER.InputBlockedError, match="must be absent"):
        RUNNER._publish(target, {"status": "second"})


def test_one_use_targets_must_all_be_absent(tmp_path: Path, monkeypatch) -> None:
    paths = [tmp_path / name for name in ("vc", "vr", "hc", "hr")]
    for name, path in zip(
        ("VALIDATION_CLAIM", "VALIDATION_RESULT", "HOLDOUT_CLAIM", "HOLDOUT_RESULT"),
        paths,
    ):
        monkeypatch.setattr(RUNNER, name, path)
    RUNNER._targets_absent()
    paths[0].write_text("used")
    with pytest.raises(RUNNER.InputBlockedError, match="already exists"):
        RUNNER._targets_absent()


def test_result_record_never_opens_candidate_or_trading_boundaries() -> None:
    record = RUNNER._result_record(
        "validation",
        "RETROSPECTIVE_SECONDARY_VALIDATION_FAIL",
        claim_sha256="a" * 64,
        bundle_sha256="b" * 64,
        decision={"all_gates_pass": False},
    )
    assert record["strategy_candidate_available"] is False
    assert record["rerun_authorized"] is False
    assert record["shadow"] is False
    assert record["paper"] is False
    assert record["broker"] is False
    assert record["live"] is False
