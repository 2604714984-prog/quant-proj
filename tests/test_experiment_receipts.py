from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import json

import pytest

from quant_system.data import capture_source_bytes, parse_provider_observation
import quant_system.research.experiments as experiment_module
import quant_system.backtest.event_loop as event_loop_module
from quant_system.backtest.event_loop import StaticRebalanceResult, create_stage_plan
from quant_system.research.experiments import (
    capture_family_anchor,
    capture_final_run_receipt,
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


def _anchor(events, tmp_path, *, holdout_id: str = "holdout-001"):
    ledger = persist_experiment_ledger(tmp_path, events)
    family = tuple(
        event
        for event in events
        if event.kind == "PREREGISTERED" and event.holdout_id == holdout_id
    )
    available_at = PREREGISTERED_AT + timedelta(hours=1)
    values = {
        "created_at": available_at.isoformat(),
        "family_size": len(family),
        "frozen_at": PREREGISTERED_AT.isoformat(),
        "holdout_id": holdout_id,
        "ledger_event_count": len(events),
        "ledger_head_sha256": events[-1].event_sha256,
        "multiplicity_family_id": family[0].multiplicity_family_id,
        "parameter_summary_sha256": experiment_module._family_parameter_summary(
            family
        ),
    }
    content = json.dumps(
        {
            "schema": "experiment-anchor-v1",
            "observations": [
                {
                    "kind": "experiment_anchor",
                    "subject_id": holdout_id,
                    "values": values,
                }
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    source_receipt = capture_source_bytes(
        content,
        publication_evidence=b"published anchor",
        source_url="https://example.test/anchor",
        available_at=available_at,
        retrieved_at=available_at + timedelta(minutes=1),
        revision_id="anchor-v1",
        source_family_id="experiment-anchor",
        provider_id="fixture-provider",
        subject_id=holdout_id,
    )
    observation = parse_provider_observation(
        source_receipt,
        content,
        observation_kind="experiment_anchor",
        subject_id=holdout_id,
    )
    return capture_family_anchor(
        events,
        holdout_id=holdout_id,
        ledger_receipt=ledger,
        observation_receipt=observation,
    )


def _evaluation(
    *,
    holdout_id: str = "holdout-001",
    returns=(0.10, 0.11, 0.09, 0.12, 0.08),
):
    count = len(returns)
    observed = tuple(date(2026, 1, 1) + timedelta(days=index) for index in range(count))
    manifest = build_split_manifest(
        entity_ids=tuple(f"S{index}" for index in range(count)),
        observed_at=observed,
        label_end_at=observed,
        fold_ids=("holdout",) * count,
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
        alpha=0.05,
        family_size=family_size,
    )


def _receipt(
    trial_id: str,
    *,
    holdout_id: str = "holdout-001",
    returns=(0.10, 0.11, 0.09, 0.12, 0.08),
):
    _, evaluation = _evaluation(holdout_id=holdout_id, returns=returns)
    stage_plan = create_stage_plan((date(2026, 7, 1),))
    executed = object.__new__(StaticRebalanceResult)
    for name, value in {
        "stage_plan_sha256": stage_plan.plan_sha256,
        "stage_index": 0,
        "stage_session": stage_plan.sessions[0],
        "prior_stage_hash": "0" * 64,
        "stage_hash": "d" * 64,
        "final_nav": 100.0,
        "_token": event_loop_module._RESULT_TOKEN,
    }.items():
        object.__setattr__(executed, name, value)
    final_run_receipt = capture_final_run_receipt(stage_plan, (executed,))
    return capture_holdout_result(
        trial_id=trial_id,
        holdout_id=holdout_id,
        final_run_receipt=final_run_receipt,
        split_evaluation=evaluation,
        holdout_access_at=datetime(2026, 7, 23, tzinfo=UTC),
    )


def test_holdout_family_cannot_extend_after_access(tmp_path) -> None:
    events = _preregister()
    anchor = _anchor(events, tmp_path)
    receipt = _receipt("trial-001", returns=(-0.1, 0.1, -0.1, 0.1, 0.0))
    events = record_holdout_result(
        events,
        receipt=receipt,
        multiplicity_method="holm",
        anchor=anchor,
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


def test_deleting_failed_trial_breaks_frozen_manifest(tmp_path) -> None:
    events = _preregister()
    anchor = _anchor(events, tmp_path)
    events = record_holdout_result(
        events,
        receipt=_receipt("trial-001", returns=(-0.1, 0.1, -0.1, 0.1, 0.0)),
        multiplicity_method="holm",
        anchor=anchor,
    )
    manifest = freeze_experiment_manifest(events)
    with pytest.raises(ValueError, match="manifest is incomplete"):
        verify_experiment_manifest(manifest, events[:1])
    with pytest.raises(ValueError, match="chain"):
        verify_experiment_manifest(manifest, events[1:])


def test_candidate_requires_typed_recomputable_holdout_receipt(tmp_path) -> None:
    events = _preregister()
    anchor = _anchor(events, tmp_path)
    receipt = _receipt("trial-001")
    events = record_holdout_result(
        events,
        receipt=receipt,
        multiplicity_method="holm",
        anchor=anchor,
    )
    result = events[-1]
    require_adjusted_holdout_for_candidate(
        result,
        receipt=receipt,
        manifest=freeze_experiment_manifest(events),
        events=events,
        anchor=anchor,
    )
    with pytest.raises(ValueError, match="not derived|does not bind"):
        require_adjusted_holdout_for_candidate(
            result,
            receipt=replace(receipt, final_stage_hash="e" * 64),
            manifest=freeze_experiment_manifest(events),
            events=events,
            anchor=anchor,
        )


def test_persistent_ledger_detects_deleted_prefix(tmp_path) -> None:
    events = _preregister()
    receipt = persist_experiment_ledger(tmp_path, events)
    receipt.verify_current_bytes()
    receipt.path.write_bytes(b"")
    with pytest.raises(ValueError, match="bytes changed"):
        receipt.verify_current_bytes()


def test_final_run_receipt_requires_complete_ordered_stage_chain() -> None:
    plan = create_stage_plan((date(2026, 7, 1), date(2026, 7, 2)))

    def result(index: int, prior: str, stage_hash: str):
        item = object.__new__(StaticRebalanceResult)
        for name, value in {
            "stage_plan_sha256": plan.plan_sha256,
            "stage_index": index,
            "stage_session": plan.sessions[index],
            "prior_stage_hash": prior,
            "stage_hash": stage_hash,
            "final_nav": 100.0 + index,
            "_token": event_loop_module._RESULT_TOKEN,
        }.items():
            object.__setattr__(item, name, value)
        return item

    first = result(0, "0" * 64, "1" * 64)
    second = result(1, first.stage_hash, "2" * 64)
    receipt = capture_final_run_receipt(plan, (first, second))
    assert receipt.final_stage_hash == second.stage_hash
    with pytest.raises(ValueError, match="one actual result"):
        capture_final_run_receipt(plan, (first,))
    with pytest.raises(ValueError, match="skipped, reordered, or replaced"):
        capture_final_run_receipt(plan, (second, first))


def test_complete_family_is_recorded_atomically_with_computed_holm_values(tmp_path) -> None:
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
    anchor = _anchor(events, tmp_path, holdout_id="holdout-002")
    with pytest.raises(ValueError, match="complete frozen family"):
        record_holdout_result(
            events,
            receipt=_receipt("trial-a", holdout_id="holdout-002"),
            multiplicity_method="holm",
            anchor=anchor,
        )
    receipts = (
        _receipt("trial-a", holdout_id="holdout-002"),
        _receipt(
            "trial-b",
            holdout_id="holdout-002",
            returns=(0.08, 0.10, 0.07, 0.09, 0.08),
        ),
    )
    completed = record_holdout_family_results(
        events,
        receipts=receipts,
        multiplicity_method="holm",
        anchor=anchor,
    )
    results = completed[-2:]
    assert {event.trial_id for event in results} == {"trial-a", "trial-b"}
    assert all(event.adjusted_pvalue is not None for event in results)
