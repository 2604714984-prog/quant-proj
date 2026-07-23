from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

import pytest

from quant_system.research.identity import (
    build_dataset_manifest,
    capture_dataset_manifest,
    dataset_identity_sha256,
)
from quant_system.research.splits import (
    build_split_manifest,
    evaluate_split,
    purged_embargo_train_mask,
    require_split_evaluation_for_candidate,
    walk_forward_masks,
)


def test_purge_removes_cross_boundary_labels_and_post_test_embargo() -> None:
    observations = tuple(date(2026, 1, day) for day in range(1, 11))
    labels = tuple(value + timedelta(days=2) for value in observations)

    mask = purged_embargo_train_mask(
        observations,
        labels,
        test_start=date(2026, 1, 5),
        test_end=date(2026, 1, 6),
        embargo=timedelta(days=2),
    )

    assert mask == (True, True, False, False, False, False, False, False, True, True)


def test_walk_forward_never_admits_future_observations() -> None:
    observations = tuple(date(2026, 1, day) for day in range(1, 11))
    labels = (
        date(2026, 1, 3),
        date(2026, 1, 4),
        date(2026, 1, 5),
        date(2026, 1, 6),
        date(2026, 1, 6),
        date(2026, 1, 6),
        date(2026, 1, 7),
        date(2026, 1, 8),
        date(2026, 1, 9),
        date(2026, 1, 10),
    )

    train, test = walk_forward_masks(
        observations,
        labels,
        test_start=date(2026, 1, 5),
        test_end=date(2026, 1, 6),
    )

    assert train == (True, True, False, False, False, False, False, False, False, False)
    assert test == (False, False, False, False, True, True, False, False, False, False)
    assert not any(keep and value >= date(2026, 1, 5) for keep, value in zip(train, observations))


def test_walk_forward_excludes_test_labels_crossing_test_end() -> None:
    observations = tuple(date(2026, 1, day) for day in range(1, 8))
    labels = (
        date(2026, 1, 1),
        date(2026, 1, 2),
        date(2026, 1, 3),
        date(2026, 1, 4),
        date(2026, 1, 6),
        date(2026, 1, 7),
        date(2026, 1, 7),
    )

    _, test = walk_forward_masks(
        observations,
        labels,
        test_start=date(2026, 1, 5),
        test_end=date(2026, 1, 6),
    )

    assert test == (False, False, False, False, True, False, False)


def test_split_inputs_fail_closed_on_ambiguous_time_or_labels() -> None:
    aware = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="timezone-aware"):
        purged_embargo_train_mask(
            (datetime(2026, 1, 1), datetime(2026, 1, 2)),
            (datetime(2026, 1, 1), datetime(2026, 1, 2)),
            test_start=datetime(2026, 1, 2),
            test_end=datetime(2026, 1, 2),
        )
    with pytest.raises(ValueError, match="cannot end before"):
        purged_embargo_train_mask(
            (aware, aware + timedelta(days=1)),
            (aware - timedelta(seconds=1), aware + timedelta(days=1)),
            test_start=aware,
            test_end=aware + timedelta(days=1),
        )
    with pytest.raises(ValueError, match="strictly increasing"):
        purged_embargo_train_mask(
            (date(2026, 1, 2), date(2026, 1, 1)),
            (date(2026, 1, 2), date(2026, 1, 1)),
            test_start=date(2026, 1, 2),
            test_end=date(2026, 1, 2),
        )
    with pytest.raises(ValueError, match="whole number of days"):
        purged_embargo_train_mask(
            (date(2026, 1, 1), date(2026, 1, 2)),
            (date(2026, 1, 1), date(2026, 1, 2)),
            test_start=date(2026, 1, 2),
            test_end=date(2026, 1, 2),
            embargo=timedelta(microseconds=1),
        )


def test_panel_split_manifest_flags_five_day_overlap_with_stable_ids() -> None:
    observations = tuple(date(2026, 1, day) for day in range(1, 8))
    labels = tuple(value + timedelta(days=5) for value in observations)
    manifest = build_split_manifest(
        entity_ids=("AAA",) * len(observations),
        observed_at=observations,
        label_end_at=labels,
        fold_ids=("test-1",) * len(observations),
    )

    assert len(manifest.samples) == 7
    assert len({sample.sample_id for sample in manifest.samples}) == 7
    assert len({sample.overlap_group for sample in manifest.samples}) < 7
    with pytest.raises(ValueError, match="overlapping labels"):
        evaluate_split(
            manifest,
            selected_sample_ids=tuple(sample.sample_id for sample in manifest.samples),
            returns=(0.01, -0.02, 0.03, 0.01, -0.01, 0.02, 0.04),
            method="non_overlapping",
        )
    corrected = evaluate_split(
        manifest,
        selected_sample_ids=tuple(sample.sample_id for sample in manifest.samples),
        returns=(0.01, -0.02, 0.03, 0.01, -0.01, 0.02, 0.04),
        method="hac",
        hac_bandwidth=2,
    )
    require_split_evaluation_for_candidate(corrected)
    assert corrected.nominal_n == 7
    assert 1 <= corrected.effective_n <= 7
    assert corrected.standard_error > 0
    assert corrected.hac_bandwidth == 2
    assert len(corrected.returns_sha256) == 64
    assert len(corrected.estimator_sha256) == 64

    bootstrapped = evaluate_split(
        manifest,
        selected_sample_ids=tuple(sample.sample_id for sample in manifest.samples),
        returns=(0.01, -0.02, 0.03, 0.01, -0.01, 0.02, 0.04),
        method="block_bootstrap",
        block_length=3,
        bootstrap_replicates=250,
    )
    require_split_evaluation_for_candidate(bootstrapped)
    assert bootstrapped.block_length == 3
    assert bootstrapped.bootstrap_replicates == 250
    assert bootstrapped.standard_error > 0


def test_same_day_multi_security_panel_has_distinct_stable_sample_ids() -> None:
    observed = date(2026, 1, 5)
    manifest = build_split_manifest(
        entity_ids=("AAA", "BBB"),
        observed_at=(observed, observed),
        label_end_at=(observed + timedelta(days=5),) * 2,
        fold_ids=("test-1", "test-1"),
    )

    assert len({sample.sample_id for sample in manifest.samples}) == 2
    assert len({sample.overlap_group for sample in manifest.samples}) == 1


def _identity(**overrides: object) -> str:
    inputs: dict[str, object] = {
        "dates": (date(2026, 1, 2), date(2026, 1, 5)),
        "frequency": "1d-close",
        "schema": (("symbol", "VARCHAR"), ("close", "DOUBLE")),
        "source_snapshot_sha256s": ("2" * 64, "3" * 64),
        "universe_snapshot_sha256": "4" * 64,
        "feature_code_sha256": "5" * 64,
        "label_code_sha256": "6" * 64,
        "split_manifest_sha256": "7" * 64,
        "calendar_policy_sha256": "8" * 64,
        "action_policy_sha256": "9" * 64,
        "cost_policy_sha256": "a" * 64,
        "partition_sha256s": ("0" * 64, "1" * 64),
    }
    inputs.update(overrides)
    return dataset_identity_sha256(**inputs)  # type: ignore[arg-type]


def test_dataset_identity_has_a_fixed_canonical_golden_hash() -> None:
    assert _identity() == "eafa8bc336bfe583c2c130b7dda3cb4f0447186cc5f25e90d98b8c7f9d41142b"


@pytest.mark.parametrize(
    "override",
    [
        {"dates": (date(2026, 1, 2), date(2026, 1, 6))},
        {"frequency": "1d-open"},
        {"schema": (("symbol", "VARCHAR"), ("close", "DECIMAL"))},
        {"source_snapshot_sha256s": ("b" * 64, "3" * 64)},
        {"universe_snapshot_sha256": "b" * 64},
        {"feature_code_sha256": "b" * 64},
        {"label_code_sha256": "b" * 64},
        {"split_manifest_sha256": "b" * 64},
        {"calendar_policy_sha256": "b" * 64},
        {"action_policy_sha256": "b" * 64},
        {"cost_policy_sha256": "b" * 64},
        {"partition_sha256s": ("0" * 64, "2" * 64)},
    ],
)
def test_dataset_identity_binds_every_required_input(override: dict[str, object]) -> None:
    assert _identity(**override) != _identity()


def test_dataset_identity_rejects_incomplete_or_ambiguous_inputs() -> None:
    with pytest.raises(ValueError, match="chronologically"):
        _identity(dates=(date(2026, 1, 5), date(2026, 1, 2)))
    with pytest.raises(ValueError, match="one hash per date"):
        _identity(partition_sha256s=("0" * 64,))
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        _identity(partition_sha256s=("A" * 64, "1" * 64))
    with pytest.raises(ValueError, match="timezone-aware"):
        _identity(dates=(datetime(2026, 1, 2), datetime(2026, 1, 5)))
    with pytest.raises(ValueError, match="must not be empty"):
        _identity(source_snapshot_sha256s=())


def test_dataset_manifest_exposes_bound_semantic_identities() -> None:
    inputs = {
        "dates": (date(2026, 1, 2), date(2026, 1, 5)),
        "frequency": "1d-close",
        "schema": (("symbol", "VARCHAR"), ("close", "DOUBLE")),
        "source_snapshot_sha256s": ("2" * 64, "3" * 64),
        "universe_snapshot_sha256": "4" * 64,
        "feature_code_sha256": "5" * 64,
        "label_code_sha256": "6" * 64,
        "split_manifest_sha256": "7" * 64,
        "calendar_policy_sha256": "8" * 64,
        "action_policy_sha256": "9" * 64,
        "cost_policy_sha256": "a" * 64,
        "partition_sha256s": ("0" * 64, "1" * 64),
    }
    manifest = build_dataset_manifest(**inputs)
    assert manifest.identity_sha256 == dataset_identity_sha256(**inputs)
    assert manifest.split_manifest_sha256 == "7" * 64
    manifest.verify_identity()
    with pytest.raises(ValueError, match="semantic identity mismatch"):
        replace(manifest, cost_policy_sha256="b" * 64).verify_identity()


def test_captured_dataset_manifest_revalidates_all_semantic_bytes(tmp_path) -> None:
    names = (
        "feature",
        "label",
        "split",
        "calendar",
        "action",
        "cost",
        "partition",
    )
    paths = {}
    for name in names:
        path = tmp_path / f"{name}.json"
        path.write_text(f'{{"identity":"{name}-v1"}}\n', encoding="utf-8")
        paths[name] = path
    manifest = capture_dataset_manifest(
        dates=(date(2026, 1, 2),),
        frequency="1d-close",
        schema=(("symbol", "VARCHAR"), ("close", "DOUBLE")),
        source_snapshot_sha256s=("2" * 64,),
        universe_snapshot_sha256="4" * 64,
        feature_code_path=paths["feature"],
        label_code_path=paths["label"],
        split_manifest_path=paths["split"],
        calendar_policy_path=paths["calendar"],
        action_policy_path=paths["action"],
        cost_policy_path=paths["cost"],
        partition_paths=(paths["partition"],),
    )

    assert manifest.has_captured_semantics is True
    manifest.verify_identity()
    paths["cost"].write_text('{"identity":"cost-v2"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="cost_policy_sha256"):
        manifest.verify_identity()
