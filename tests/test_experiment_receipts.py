from dataclasses import replace
from datetime import datetime, timezone

import pytest

from quant_system.research.experiments import (
    freeze_experiment_manifest,
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
        adjusted_pvalue=0.4,
    )
    events = preregister_trial(
        events,
        trial_id="trial-002",
        definition_sha256="e" * 64,
        dataset_sha256="b" * 64,
        split_sha256="c" * 64,
        parameters={"holding_days": 20},
        multiplicity_family_id="family-001",
    )

    with pytest.raises(ValueError, match="already been unlocked"):
        record_holdout_result(
            events,
            trial_id="trial-002",
            holdout_access_at=datetime(2026, 7, 24, tzinfo=UTC),
            result_sha256="f" * 64,
            result_status="PASSED",
            multiplicity_method="holm",
            adjusted_pvalue=0.04,
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
        adjusted_pvalue=0.04,
    )[-1]
    require_adjusted_holdout_for_candidate(result)

    with pytest.raises(ValueError, match="multiplicity_method"):
        replace(result, multiplicity_method=None, adjusted_pvalue=None)
