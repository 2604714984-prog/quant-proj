from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

import pytest

from quant_system.data import capture_source_bytes
from quant_system.research.experiments import (
    capture_holdout_result,
    freeze_experiment_manifest,
    persist_experiment_ledger,
    preregister_trial,
    record_holdout_family_results,
    record_holdout_result,
    require_adjusted_holdout_for_candidate,
    verify_experiment_manifest,
)
from quant_system.research.splits import (
    build_split_evaluation_plan,
    build_split_manifest,
    evaluate_split,
)

UTC = timezone.utc
PREREGISTERED_AT = datetime(2026, 7, 22, tzinfo=UTC)


def _anchor():
    return capture_source_bytes(
        b"external preregistration anchor",
        publication_evidence=b"published anchor",
        source_url="https://example.test/anchor",
        available_at=PREREGISTERED_AT - timedelta(days=1),
        retrieved_at=PREREGISTERED_AT - timedelta(hours=23),
        revision_id="anchor-v1",
        source_family_id="experiment-anchor",
        provider_id="fixture-provider",
        subject_id="holdout-001",
    ).source


def _evaluation(*, holdout_id: str = "holdout-001", returns=(0.10, 0.11)):
    manifest = build_split_manifest(
        entity_ids=("AAA", "BBB"),
        observed_at=(date(2026, 1, 1), date(2026, 1, 2)),
        label_end_at=(date(2026, 1, 1), date(2026, 1, 2)),
        fold_ids=("holdout", "holdout"),
    )
    plan = build_split_evaluation_plan(
        manifest,
        holdout_id=holdout_id,
        selected_sample_ids=tuple(sample.sample_id for sample in manifest.samples),
        method="non_overlapping",
        preregistered_at=PREREGISTERED_AT,
    )
    evaluation = evaluate_split(
        manifest,
        plan=plan,
        returns_by_sample={
            sample.sample_id: value
            for sample, value in zip(manifest.samples, returns, strict=True)
        },
    )
    return plan, evaluation


def _preregister(
    trial_id: str = "trial-001",
    *,
    events=(),
    family_id: str = "family-001",
    holdout_id: str = "holdout-001",
    family_size: int = 1,
    definition_sha256: str = "a" * 64,
):
    plan, _ = _evaluation(holdout_id=holdout_id)
    return preregister_trial(
        events,
        trial_id=trial_id,
        definition_sha256=definition_sha256,
        dataset_sha256="b" * 64,
        split_sha256=plan.manifest_sha256,
        stage_plan_sha256="9" * 64,
        split_evaluation_plan=plan,
        candidate_run_config_sha256="8" * 64,
        parameters={"holding_days": 5, "threshold": 0.2},
        multiplicity_family_id=family_id,
        holdout_id=holdout_id,
        preregistered_at=PREREGISTERED_AT,
        external_anchor=_anchor(),
        alpha=0.05,
        family_size=family_size,
    )


def _receipt(trial_id: str, *, holdout_id: str = "holdout-001", returns=(0.10, 0.11)):
    _, evaluation = _evaluation(holdout_id=holdout_id, returns=returns)
    return capture_holdout_result(
        trial_id=trial_id,
        holdout_id=holdout_id,
        final_stage_hash="d" * 64,
        split_evaluation=evaluation,
        holdout_access_at=datetime(2026, 7, 23, tzinfo=UTC),
    )


def test_holdout_family_cannot_extend_after_access() -> None:
    events = _preregister()
    receipt = _receipt("trial-001", returns=(-0.1, 0.1))
    events = record_holdout_result(
        events,
        receipt=receipt,
        multiplicity_method="holm",
    )
    with pytest.raises(ValueError, match="cannot be extended"):
        _preregister(
            "trial-002",
            events=events,
            definition_sha256="e" * 64,
        )


def test_same_dataset_split_cannot_be_relabelled_as_a_new_holdout_family() -> None:
    events = _preregister()
    with pytest.raises(ValueError, match="one holdout family"):
        _preregister(
            "trial-002",
            events=events,
            family_id="family-002",
            holdout_id="holdout-002",
            definition_sha256="e" * 64,
        )


def test_deleting_failed_trial_breaks_frozen_manifest() -> None:
    events = _preregister()
    events = record_holdout_result(
        events,
        receipt=_receipt("trial-001", returns=(-0.1, 0.1)),
        multiplicity_method="holm",
    )
    manifest = freeze_experiment_manifest(events)
    with pytest.raises(ValueError, match="manifest is incomplete"):
        verify_experiment_manifest(manifest, events[:1])
    with pytest.raises(ValueError, match="chain"):
        verify_experiment_manifest(manifest, events[1:])


def test_candidate_requires_typed_recomputable_holdout_receipt() -> None:
    events = _preregister()
    receipt = _receipt("trial-001")
    events = record_holdout_result(
        events,
        receipt=receipt,
        multiplicity_method="holm",
    )
    result = events[-1]
    require_adjusted_holdout_for_candidate(
        result,
        receipt=receipt,
        manifest=freeze_experiment_manifest(events),
        events=events,
    )
    with pytest.raises(ValueError, match="not derived|does not bind"):
        require_adjusted_holdout_for_candidate(
            result,
            receipt=replace(receipt, final_stage_hash="e" * 64),
            manifest=freeze_experiment_manifest(events),
            events=events,
        )


def test_persistent_ledger_detects_deleted_prefix(tmp_path) -> None:
    events = _preregister()
    receipt = persist_experiment_ledger(tmp_path / "experiment-ledger.ndjson", events)
    receipt.verify_current_bytes()
    receipt.path.write_bytes(b"")
    with pytest.raises(ValueError, match="bytes changed"):
        receipt.verify_current_bytes()


def test_complete_family_is_recorded_atomically_with_computed_holm_values() -> None:
    events = _preregister(
        "trial-a",
        family_id="family-002",
        holdout_id="holdout-002",
        family_size=2,
    )
    events = _preregister(
        "trial-b",
        events=events,
        family_id="family-002",
        holdout_id="holdout-002",
        family_size=2,
        definition_sha256="e" * 64,
    )
    with pytest.raises(ValueError, match="complete frozen family"):
        record_holdout_result(
            events,
            receipt=_receipt("trial-a", holdout_id="holdout-002"),
            multiplicity_method="holm",
        )
    receipts = (
        _receipt("trial-a", holdout_id="holdout-002"),
        _receipt("trial-b", holdout_id="holdout-002", returns=(0.08, 0.10)),
    )
    completed = record_holdout_family_results(
        events,
        receipts=receipts,
        multiplicity_method="holm",
    )
    results = completed[-2:]
    assert {event.trial_id for event in results} == {"trial-a", "trial-b"}
    assert all(event.adjusted_pvalue is not None for event in results)
