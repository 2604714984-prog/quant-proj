from dataclasses import replace
from datetime import datetime, timezone

import pytest

from quant_system.research.experiments import (
    freeze_experiment_manifest,
    persist_experiment_ledger,
    preregister_trial,
    record_holdout_result,
    require_adjusted_holdout_for_candidate,
    verify_experiment_manifest,
)

UTC = timezone.utc


def _preregister(trial_id: str = "trial-001"):
    return preregister_trial(
        (),
        trial_id=trial_id,
        definition_sha256="a" * 64,
        dataset_sha256="b" * 64,
        split_sha256="c" * 64,
        parameters={"holding_days": 5, "threshold": 0.2},
        multiplicity_family_id="family-001",
        preregistered_at=datetime(2026, 7, 22, tzinfo=UTC),
        external_anchor_sha256="f" * 64,
        alpha=0.05,
        family_size=1,
    )


def test_definition_change_cannot_unlock_holdout_twice() -> None:
    events = _preregister()
    events = record_holdout_result(
        events,
        trial_id="trial-001",
        holdout_access_at=datetime(2026, 7, 23, tzinfo=UTC),
        result_sha256="d" * 64,
        result_status="FAILED",
        multiplicity_method="holm",
        raw_pvalue=0.4,
        adjusted_pvalue=0.4,
    )
    with pytest.raises(ValueError, match="preregistered size"):
        preregister_trial(
            events,
            trial_id="trial-002",
            definition_sha256="e" * 64,
            dataset_sha256="b" * 64,
            split_sha256="c" * 64,
            parameters={"holding_days": 20},
            multiplicity_family_id="family-001",
            preregistered_at=datetime(2026, 7, 23, tzinfo=UTC),
            external_anchor_sha256="f" * 64,
            alpha=0.05,
            family_size=1,
        )


def test_deleting_failed_trial_breaks_frozen_manifest() -> None:
    events = _preregister()
    events = record_holdout_result(
        events,
        trial_id="trial-001",
        holdout_access_at=datetime(2026, 7, 23, tzinfo=UTC),
        result_sha256="d" * 64,
        result_status="FAILED",
        multiplicity_method="holm",
        raw_pvalue=0.4,
        adjusted_pvalue=0.4,
    )
    manifest = freeze_experiment_manifest(events)

    with pytest.raises(ValueError, match="manifest is incomplete"):
        verify_experiment_manifest(manifest, events[:1])
    with pytest.raises(ValueError, match="chain"):
        verify_experiment_manifest(manifest, events[1:])


def test_candidate_requires_multiplicity_adjustment() -> None:
    events = _preregister()
    result = record_holdout_result(
        events,
        trial_id="trial-001",
        holdout_access_at=datetime(2026, 7, 23, tzinfo=UTC),
        result_sha256="d" * 64,
        result_status="PASSED",
        multiplicity_method="holm",
        raw_pvalue=0.04,
        adjusted_pvalue=0.04,
    )[-1]
    manifest = freeze_experiment_manifest(events + (result,))
    full_events = events + (result,)
    require_adjusted_holdout_for_candidate(
        result,
        manifest=manifest,
        events=full_events,
    )

    with pytest.raises(ValueError, match="multiplicity_method"):
        replace(result, multiplicity_method=None, adjusted_pvalue=None)


def test_persistent_ledger_detects_deleted_prefix(tmp_path) -> None:
    events = _preregister()
    receipt = persist_experiment_ledger(tmp_path / "experiment-ledger.ndjson", events)
    receipt.verify_current_bytes()
    receipt.path.write_bytes(b"")

    with pytest.raises(ValueError, match="bytes changed"):
        receipt.verify_current_bytes()


def test_candidate_requires_complete_recomputable_multiplicity_family() -> None:
    common = {
        "dataset_sha256": "b" * 64,
        "split_sha256": "c" * 64,
        "multiplicity_family_id": "family-002",
        "external_anchor_sha256": "f" * 64,
        "alpha": 0.05,
        "family_size": 2,
    }
    events = preregister_trial(
        (),
        trial_id="trial-a",
        definition_sha256="a" * 64,
        parameters={"variant": "a"},
        preregistered_at=datetime(2026, 7, 21, tzinfo=UTC),
        **common,
    )
    events = preregister_trial(
        events,
        trial_id="trial-b",
        definition_sha256="e" * 64,
        parameters={"variant": "b"},
        preregistered_at=datetime(2026, 7, 21, 1, tzinfo=UTC),
        **common,
    )
    events = record_holdout_result(
        events,
        trial_id="trial-a",
        holdout_access_at=datetime(2026, 7, 23, tzinfo=UTC),
        result_sha256="1" * 64,
        result_status="PASSED",
        multiplicity_method="holm",
        raw_pvalue=0.04,
        adjusted_pvalue=0.04,
    )
    first_result = events[-1]
    with pytest.raises(ValueError, match="complete multiplicity family"):
        require_adjusted_holdout_for_candidate(
            first_result,
            manifest=freeze_experiment_manifest(events),
            events=events,
        )

    wrongly_adjusted = record_holdout_result(
        events,
        trial_id="trial-b",
        holdout_access_at=datetime(2026, 7, 23, tzinfo=UTC),
        result_sha256="2" * 64,
        result_status="PASSED",
        multiplicity_method="holm",
        raw_pvalue=0.01,
        adjusted_pvalue=0.01,
    )
    with pytest.raises(ValueError, match="not recomputable"):
        require_adjusted_holdout_for_candidate(
            first_result,
            manifest=freeze_experiment_manifest(wrongly_adjusted),
            events=wrongly_adjusted,
        )
