from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

import pytest

from quant_system.research.identity import (
    build_dataset_manifest,
    capture_dataset_manifest,
    dataset_identity_sha256,
)
from quant_system.research.splits import (
    SplitManifest,
    build_split_manifest,
    build_split_evaluation_plan,
    evaluate_split,
    load_split_manifest,
    purged_embargo_train_mask,
    require_split_evaluation_for_candidate,
    walk_forward_masks,
    serialize_split_manifest,
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
    observations = tuple(date(2026, 1, 1) + timedelta(days=day) for day in range(35))
    labels = tuple(value + timedelta(days=5) for value in observations)
    manifest = build_split_manifest(
        entity_ids=("AAA",) * len(observations),
        observed_at=observations,
        label_end_at=labels,
        fold_ids=("test-1",) * len(observations),
    )

    selected = tuple(sample.sample_id for sample in manifest.samples)
    returns = tuple((day % 7 - 2) / 100 for day in range(35))
    returns_by_sample = dict(zip(selected, returns, strict=True))
    assert len(manifest.samples) == 35
    assert len({sample.sample_id for sample in manifest.samples}) == 35
    assert len({sample.overlap_group for sample in manifest.samples}) < 35
    with pytest.raises(ValueError, match="overlapping labels"):
        evaluate_split(
            manifest,
            plan=build_split_evaluation_plan(
                manifest,
                holdout_id="holdout-1",
                selected_sample_ids=selected,
                method="non_overlapping",
                preregistered_at=datetime(2025, 12, 31, tzinfo=timezone.utc),
            ),
            returns_by_sample=returns_by_sample,
        )
    hac_plan = build_split_evaluation_plan(
        manifest,
        holdout_id="holdout-1",
        selected_sample_ids=tuple(reversed(selected)),
        method="hac",
        hac_bandwidth=2,
        preregistered_at=datetime(2025, 12, 31, tzinfo=timezone.utc),
    )
    corrected = evaluate_split(
        manifest,
        plan=hac_plan,
        returns_by_sample=returns_by_sample,
    )
    require_split_evaluation_for_candidate(corrected)
    assert corrected.nominal_n == 35
    assert 1 <= corrected.effective_n <= 35
    assert corrected.standard_error > 0
    assert corrected.hac_bandwidth == 2
    assert len(corrected.returns_sha256) == 64
    assert len(corrected.estimator_sha256) == 64
    assert corrected.inference_distribution == "hac_asymptotic_normal_min_n_30"

    bootstrapped = evaluate_split(
        manifest,
        plan=build_split_evaluation_plan(
            manifest,
            holdout_id="holdout-1",
            selected_sample_ids=selected,
            method="block_bootstrap",
            block_length=3,
            bootstrap_replicates=250,
            preregistered_at=datetime(2025, 12, 31, tzinfo=timezone.utc),
        ),
        returns_by_sample=returns_by_sample,
    )
    require_split_evaluation_for_candidate(bootstrapped)
    assert bootstrapped.block_length == 3
    assert bootstrapped.bootstrap_replicates == 250
    assert bootstrapped.standard_error > 0
    assert bootstrapped.inference_distribution == "centered_moving_block_empirical"
    assert 0 < bootstrapped.raw_pvalue <= 1

    loaded = load_split_manifest(serialize_split_manifest(manifest))
    assert loaded == manifest
    with pytest.raises(ValueError, match="controlled builder"):
        SplitManifest(manifest.samples, manifest.manifest_sha256)


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


def test_daily_portfolio_unit_aggregates_panel_and_rejects_cross_fold_or_small_n() -> None:
    days = tuple(date(2026, 2, 1) + timedelta(days=index) for index in range(5))
    entities = tuple(entity for day in days for entity in ("AAA", "BBB"))
    observed = tuple(day for day in days for _ in range(2))
    manifest = build_split_manifest(
        entity_ids=entities,
        observed_at=observed,
        label_end_at=observed,
        fold_ids=("holdout",) * len(observed),
    )
    plan = build_split_evaluation_plan(
        manifest,
        holdout_id="panel-holdout",
        selected_sample_ids=tuple(reversed([sample.sample_id for sample in manifest.samples])),
        method="non_overlapping",
        preregistered_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    returns = {
        sample.sample_id: (
            0.01 * (days.index(sample.observed_at) + 1)
            + (0.0 if sample.entity_id == "AAA" else 0.01)
        )
        for sample in manifest.samples
    }
    evaluation = evaluate_split(manifest, plan=plan, returns_by_sample=returns)
    assert evaluation.evaluation_unit == "daily_portfolio"
    assert evaluation.nominal_n == 5
    assert evaluation.inference_distribution == "student_t_df_4"
    assert 0 <= evaluation.raw_pvalue <= 1

    too_small = build_split_manifest(
        entity_ids=("AAA", "AAA"),
        observed_at=days[:2],
        label_end_at=days[:2],
        fold_ids=("holdout", "holdout"),
    )
    with pytest.raises(ValueError, match="at least 5 daily portfolio returns"):
        evaluate_split(
            too_small,
            plan=build_split_evaluation_plan(
                too_small,
                holdout_id="small",
                selected_sample_ids=tuple(
                    sample.sample_id for sample in too_small.samples
                ),
                method="non_overlapping",
                preregistered_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            ),
            returns_by_sample={sample.sample_id: 0.1 for sample in too_small.samples},
        )

    mixed = build_split_manifest(
        entity_ids=("AAA",) * 5,
        observed_at=days,
        label_end_at=days,
        fold_ids=("one", "one", "two", "two", "two"),
    )
    with pytest.raises(ValueError, match="cannot mix fold IDs"):
        evaluate_split(
            mixed,
            plan=build_split_evaluation_plan(
                mixed,
                holdout_id="mixed",
                selected_sample_ids=tuple(sample.sample_id for sample in mixed.samples),
                method="non_overlapping",
                preregistered_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            ),
            returns_by_sample={sample.sample_id: 0.1 for sample in mixed.samples},
        )


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
    split_receipt = build_split_manifest(
        entity_ids=("AAA",),
        observed_at=(date(2026, 1, 2),),
        label_end_at=(date(2026, 1, 2),),
        fold_ids=("test",),
    )
    paths["split"].write_bytes(serialize_split_manifest(split_receipt))
    manifest = capture_dataset_manifest(
        dates=(date(2026, 1, 2),),
        frequency="1d-close",
        schema=(("symbol", "VARCHAR"), ("close", "DOUBLE")),
        source_snapshot_sha256s=("2" * 64,),
        universe_snapshot_sha256="4" * 64,
        feature_code_path=paths["feature"],
        label_code_path=paths["label"],
        split_manifest_path=paths["split"],
        split_manifest_receipt=split_receipt,
        calendar_policy_path=paths["calendar"],
        action_policy_path=paths["action"],
        cost_policy_path=paths["cost"],
        partition_paths=(paths["partition"],),
    )

    assert manifest.has_captured_semantics is True
    assert manifest.has_verified_split_manifest is True
    manifest.verify_identity()
    paths["cost"].write_text('{"identity":"cost-v2"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="cost_policy_sha256"):
        manifest.verify_identity()
