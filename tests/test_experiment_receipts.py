from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import hashlib
import json

import pytest

from quant_system.data import capture_source_bytes, parse_provider_observation
import quant_system.research.experiments as experiment_module
from quant_system.research.experiments import (
    TrialRunReceipt,
    capture_family_anchor,
    capture_family_contract,
    capture_holdout_result,
    capture_trial_config,
    freeze_experiment_manifest,
    load_experiment_ledger,
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
from tests.controlled_result_fixtures import controlled_return_fixture

UTC = timezone.utc
PREREGISTERED_AT = datetime(2026, 7, 22, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _bind_experiment_data_root(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("QUANT_DATA_ROOT", str(tmp_path / "quant-data"))
    monkeypatch.setenv("QUANT_PROJECT_ID", "quant-proj-test")
    monkeypatch.setenv(
        "QUANT_EXPERIMENT_OWNER_ROOT",
        str(tmp_path / "experiment-owner"),
    )


def _anchor(events, tmp_path, *, holdout_id: str = "holdout-001"):
    ledger = persist_experiment_ledger(events)
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
    return_artifact, final_run_receipt = controlled_return_fixture(
        dict(zip(observed, returns, strict=True)),
        contributors_by_session={
            session: (f"S{index}",)
            for index, session in enumerate(observed)
        },
    )
    evaluation = evaluate_split(
        manifest,
        plan=plan,
        return_artifact=return_artifact,
    )
    return plan, evaluation, final_run_receipt


def _preregister(
    trial_id: str = "trial-001",
    *,
    events=(),
    family_id: str = "family-001",
    holdout_id: str = "holdout-001",
    family_size: int = 1,
    definition_sha256: str = "a" * 64,
):
    plan, _, final_run_receipt = _evaluation(holdout_id=holdout_id)
    family_contract = capture_family_contract(
        multiplicity_family_id=family_id,
        holdout_id=holdout_id,
        dataset_sha256="b" * 64,
        split_sha256=plan.manifest_sha256,
        stage_plan_sha256=final_run_receipt.stage_plan_sha256,
        split_evaluation_plan_sha256=plan.plan_sha256,
        cost_assumptions_sha256="c" * 64,
        alpha=0.05,
        family_size=family_size,
    )
    trial_config = _trial_config(
        plan,
        final_run_receipt,
        trial_id=trial_id,
        definition_sha256=definition_sha256,
    )
    return preregister_trial(
        events,
        family_contract=family_contract,
        trial_config=trial_config,
        split_evaluation_plan=plan,
        preregistered_at=PREREGISTERED_AT,
    )


def _trial_config(plan, final_run_receipt, *, trial_id, definition_sha256):
    return capture_trial_config(
        trial_id=trial_id,
        definition_sha256=definition_sha256,
        dataset_sha256="b" * 64,
        split_sha256=plan.manifest_sha256,
        stage_plan_sha256=final_run_receipt.stage_plan_sha256,
        split_evaluation_plan_sha256=plan.plan_sha256,
        ordered_decision_artifact_sha256s=tuple(
            hashlib.sha256(f"{trial_id}|decision|{index}".encode()).hexdigest()
            for index in range(final_run_receipt.stage_count)
        ),
        ordered_universe_materialization_sha256s=tuple(
            hashlib.sha256(f"universe|{index}".encode()).hexdigest()
            for index in range(final_run_receipt.stage_count)
        ),
        cost_assumptions_sha256="c" * 64,
        max_positions=None,
        parameters={"holding_days": 5, "threshold": 0.2},
    )


def _receipt(
    trial_id: str,
    *,
    holdout_id: str = "holdout-001",
    returns=(0.10, 0.11, 0.09, 0.12, 0.08),
    definition_sha256: str = "a" * 64,
):
    plan, evaluation, final_run_receipt = _evaluation(
        holdout_id=holdout_id,
        returns=returns,
    )
    trial_config = _trial_config(
        plan,
        final_run_receipt,
        trial_id=trial_id,
        definition_sha256=definition_sha256,
    )
    trial_run = _synthetic_trial_run(
        trial_id,
        final_run_receipt,
        evaluation,
        trial_config_sha256=trial_config.config_sha256,
    )
    return capture_holdout_result(
        trial_id=trial_id,
        holdout_id=holdout_id,
        trial_run_receipt=trial_run,
        final_run_receipt=final_run_receipt,
        split_evaluation=evaluation,
        holdout_access_at=datetime(2026, 7, 23, tzinfo=UTC),
    )


def _synthetic_trial_run(
    trial_id,
    final_run_receipt,
    evaluation,
    *,
    trial_config_sha256="8" * 64,
):
    values = {
        "trial_id": trial_id,
        "trial_config_sha256": trial_config_sha256,
        "ordered_stage_receipt_sha256s": (
            final_run_receipt.ordered_stage_receipt_sha256s
        ),
        "final_run_receipt_sha256": final_run_receipt.receipt_sha256,
        "return_artifact_sha256": evaluation.return_artifact_sha256,
        "split_evaluation_sha256": evaluation.evaluation_sha256,
    }
    provisional = object.__new__(TrialRunReceipt)
    for name, value in values.items():
        object.__setattr__(provisional, name, value)
    return TrialRunReceipt(
        **values,
        receipt_sha256=hashlib.sha256(
            experiment_module._trial_run_payload(provisional)
        ).hexdigest(),
    )


def test_holdout_receipt_rejects_returns_from_another_final_run() -> None:
    _, evaluation, _ = _evaluation()
    _, _, other_final_run = _evaluation(
        returns=(0.02, 0.03, 0.01, 0.04, 0.02),
    )

    with pytest.raises(ValueError, match="derive from this FinalRunReceipt"):
        capture_holdout_result(
            trial_id="trial-001",
            holdout_id="holdout-001",
            trial_run_receipt=_synthetic_trial_run(
                "trial-001",
                other_final_run,
                evaluation,
            ),
            final_run_receipt=other_final_run,
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


def test_persistent_ledger_detects_deleted_prefix(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = _preregister()
    receipt = persist_experiment_ledger(events)
    receipt.verify_current_bytes()
    monkeypatch.setenv("QUANT_DATA_ROOT", str(tmp_path / "other-data-root"))
    receipt.verify_current_bytes()
    monkeypatch.setenv(
        "QUANT_EXPERIMENT_OWNER_ROOT",
        str(tmp_path / "other-owner"),
    )
    with pytest.raises(ValueError, match="project owner"):
        receipt.verify_current_bytes()
    monkeypatch.setenv(
        "QUANT_EXPERIMENT_OWNER_ROOT",
        str(tmp_path / "experiment-owner"),
    )
    receipt.path.write_bytes(b"")
    with pytest.raises(ValueError, match="bytes changed|complete NDJSON"):
        receipt.verify_current_bytes()


def test_persistent_ledger_requires_explicit_data_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("QUANT_PROJECT_ID", raising=False)
    with pytest.raises(ValueError, match="QUANT_PROJECT_ID"):
        persist_experiment_ledger(_preregister())


def test_persistent_ledger_restores_full_events_and_appends_in_new_process() -> None:
    first = _preregister("trial-a", family_size=2)
    persist_experiment_ledger(first)
    restored = load_experiment_ledger()
    assert restored == first
    completed = _preregister(
        "trial-b",
        events=restored,
        family_size=2,
        definition_sha256="e" * 64,
    )
    persist_experiment_ledger(completed)
    assert load_experiment_ledger() == completed


def test_final_run_receipt_requires_complete_ordered_stage_chain() -> None:
    _, receipt = controlled_return_fixture(
        {
            date(2026, 7, 1): 0.01,
            date(2026, 7, 2): 0.02,
        }
    )
    assert receipt.stage_count == 2
    assert receipt.final_stage_hash == receipt.ordered_stage_hashes[-1]
    assert receipt.ordered_portfolio_transitions[0][1] == (
        receipt.ordered_portfolio_transitions[1][0]
    )
    with pytest.raises(ValueError, match="does not end at its final stage"):
        replace(
            receipt,
            ordered_stage_hashes=tuple(reversed(receipt.ordered_stage_hashes)),
        )
    with pytest.raises(ValueError, match="discontinuous"):
        replace(
            receipt,
            ordered_portfolio_transitions=(
                receipt.ordered_portfolio_transitions[0],
                ("f" * 64, receipt.ordered_portfolio_transitions[1][1]),
            ),
        )


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
            definition_sha256="e" * 64,
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
