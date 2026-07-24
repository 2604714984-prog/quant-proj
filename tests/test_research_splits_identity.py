from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import hashlib
import json

import pytest

from quant_system.data import capture_source_bytes
from quant_system.research.identity import (
    build_dataset_manifest,
    capture_dataset_manifest,
    dataset_identity_sha256,
    execute_transformation,
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
from tests.controlled_result_fixtures import controlled_return_fixture


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
    return_artifact, _ = controlled_return_fixture(
        {
            date(2026, 1, 1) + timedelta(days=day): (day % 7 - 2) / 100
            for day in range(40)
        }
    )
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
            return_artifact=return_artifact,
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
        return_artifact=return_artifact,
    )
    require_split_evaluation_for_candidate(corrected)
    assert corrected.nominal_n == 35
    assert 1 <= corrected.effective_n <= 35
    assert corrected.standard_error > 0
    assert corrected.hac_bandwidth == 2
    assert len(corrected.returns_sha256) == 64
    assert len(corrected.estimator_sha256) == 64
    assert corrected.inference_distribution == "hac_asymptotic_normal_min_n_30"
    shorter_manifest = build_split_manifest(
        entity_ids=("AAA",) * len(observations),
        observed_at=observations,
        label_end_at=tuple(value + timedelta(days=4) for value in observations),
        fold_ids=("test-1",) * len(observations),
    )
    shorter = evaluate_split(
        shorter_manifest,
        plan=build_split_evaluation_plan(
            shorter_manifest,
            holdout_id="holdout-shorter-horizon",
            selected_sample_ids=tuple(
                sample.sample_id for sample in shorter_manifest.samples
            ),
            method="hac",
            hac_bandwidth=2,
            preregistered_at=datetime(2025, 12, 31, tzinfo=timezone.utc),
        ),
        return_artifact=return_artifact,
    )
    assert shorter.returns_sha256 != corrected.returns_sha256
    tampered_observation = replace(
        return_artifact.observations[0],
        net_return=return_artifact.observations[0].net_return + 0.5,
    )
    tampered_artifact = replace(
        return_artifact,
        observations=(tampered_observation, *return_artifact.observations[1:]),
    )
    with pytest.raises(ValueError, match="not derived from NAV"):
        evaluate_split(
            manifest,
            plan=hac_plan,
            return_artifact=tampered_artifact,
        )

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
        return_artifact=return_artifact,
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


def test_daily_portfolio_unit_binds_nav_returns_and_rejects_cross_fold_or_small_n() -> None:
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
    return_artifact, _ = controlled_return_fixture(
        {day: 0.01 * (index + 1) for index, day in enumerate(days)},
        contributors=("AAA", "BBB"),
    )
    evaluation = evaluate_split(
        manifest,
        plan=plan,
        return_artifact=return_artifact,
    )
    assert evaluation.evaluation_unit == "daily_portfolio"
    assert evaluation.nominal_n == 5
    assert evaluation.inference_distribution == "student_t_df_4"
    assert 0 <= evaluation.raw_pvalue <= 1
    mismatched_artifact, _ = controlled_return_fixture(
        {day: 0.01 * (index + 1) for index, day in enumerate(days)}
    )
    with pytest.raises(ValueError, match="contributor set"):
        evaluate_split(
            manifest,
            plan=plan,
            return_artifact=mismatched_artifact,
        )

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
            return_artifact=controlled_return_fixture(
                {day: 0.1 for day in days[:2]}
            )[0],
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
            return_artifact=controlled_return_fixture(
                {day: 0.1 for day in days}
            )[0],
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


def test_transformation_receipt_replays_raw_input_to_partition(tmp_path) -> None:
    as_of = datetime(2026, 1, 2, 12, tzinfo=timezone.utc)
    raw_rows = [
        {
            "close": 10.5,
            "feature_available_at": "2026-01-02T10:00:00+00:00",
            "label": 0.02,
            "label_available_at": "2026-01-02T11:00:00+00:00",
            "observed_at": "2026-01-02T10:30:00+00:00",
            "symbol": "AAA",
        }
    ]
    raw_bytes = json.dumps(raw_rows, sort_keys=True, separators=(",", ":")).encode()
    raw_path = tmp_path / "raw.json"
    raw_path.write_bytes(raw_bytes)
    source = capture_source_bytes(
        raw_bytes,
        publication_evidence=b"fixture publication",
        source_url="https://example.test/raw",
        available_at=datetime(2026, 1, 2, 10, tzinfo=timezone.utc),
        retrieved_at=datetime(2026, 1, 2, 10, 1, tzinfo=timezone.utc),
        revision_id="raw-v1",
        source_family_id="raw-family",
        provider_id="fixture-provider",
        subject_id="AAA",
    ).source
    program = tmp_path / "transform-spec.json"
    feature_program = tmp_path / "feature-spec.json"
    label_program = tmp_path / "label-spec.json"
    feature_program.write_text(
        '{"operation":"json_array_to_canonical_jsonl",'
        '"output_fields":["symbol","close","observed_at","feature_available_at"],'
        '"sort_keys":["symbol"],"version":1}',
        encoding="utf-8",
    )
    label_program.write_text(
        '{"operation":"json_array_to_canonical_jsonl",'
        '"output_fields":["symbol","label","label_available_at"],'
        '"sort_keys":["symbol"],"version":1}',
        encoding="utf-8",
    )
    program.write_text(
        '{"keys":["symbol"],"operation":"join_jsonl","version":1}',
        encoding="utf-8",
    )
    config = tmp_path / "transform.json"
    config.write_text('{"version":1}\n', encoding="utf-8")
    output = tmp_path / "partition.jsonl"
    receipt = execute_transformation(
        raw_paths=(raw_path,),
        raw_sources=(source,),
        program_path=program,
        feature_program_path=feature_program,
        label_program_path=label_program,
        config_path=config,
        output_path=output,
        schema=(
            ("symbol", "VARCHAR"),
            ("close", "DOUBLE"),
            ("observed_at", "TIMESTAMP"),
            ("feature_available_at", "TIMESTAMP"),
            ("label", "DOUBLE"),
            ("label_available_at", "TIMESTAMP"),
        ),
        field_metadata=(
            ("symbol", "security_identifier", "NA"),
            ("close", "USD_per_share", "NA"),
            ("observed_at", "instant", "UTC"),
            ("feature_available_at", "instant", "UTC"),
            ("label", "return_fraction", "NA"),
            ("label_available_at", "instant", "UTC"),
        ),
        dataset_as_of=as_of,
        executed_at=as_of,
    )
    assert receipt.row_count == 1
    assert receipt.is_authoritative is False
    assert receipt.feature_program_sha256 == hashlib.sha256(
        feature_program.read_bytes()
    ).hexdigest()
    assert receipt.label_program_sha256 == hashlib.sha256(
        label_program.read_bytes()
    ).hexdigest()
    assert receipt.field_contracts[1] == ("close", "DOUBLE", "USD_per_share", "NA")
    assert receipt.row_pit_enforced is True
    assert receipt.feature_artifact_sha256 != receipt.label_artifact_sha256
    receipt.verify()
    with pytest.raises(ValueError, match="runtime identity changed"):
        replace(receipt, runtime_identity_sha256="f" * 64).verify()
    output.write_text('{"symbol":"TAMPERED"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="output partition bytes changed"):
        receipt.verify()

    late_raw_rows = [
        {
            **raw_rows[0],
            "feature_available_at": "2026-01-02T10:31:00+00:00",
        }
    ]
    late_raw_bytes = json.dumps(
        late_raw_rows, sort_keys=True, separators=(",", ":")
    ).encode()
    late_raw_path = tmp_path / "late-raw.json"
    late_raw_path.write_bytes(late_raw_bytes)
    late_source = capture_source_bytes(
        late_raw_bytes,
        publication_evidence=b"fixture publication",
        source_url="https://example.test/late-raw",
        available_at=datetime(2026, 1, 2, 10, tzinfo=timezone.utc),
        retrieved_at=datetime(2026, 1, 2, 10, 1, tzinfo=timezone.utc),
        revision_id="late-raw-v1",
        source_family_id="raw-family",
        provider_id="fixture-provider",
        subject_id="AAA",
    ).source
    with pytest.raises(ValueError, match="feature evidence is unavailable"):
        execute_transformation(
            raw_paths=(late_raw_path,),
            raw_sources=(late_source,),
            program_path=program,
            feature_program_path=feature_program,
            label_program_path=label_program,
            config_path=config,
            output_path=tmp_path / "late-output.jsonl",
            schema=receipt.schema,
            field_metadata=tuple(
                (name, semantic, unit)
                for name, _, semantic, unit in receipt.field_contracts
            ),
            dataset_as_of=as_of,
            executed_at=as_of,
        )

    for operation in (
        "ctypes_libc_open",
        "mmap_undeclared",
        "proc_read",
        "native_extension",
        "undeclared_database",
    ):
        malicious = tmp_path / f"{operation}.json"
        malicious.write_text(
            json.dumps({"operation": operation, "version": 1}),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="unsupported controlled pure"):
            execute_transformation(
                raw_paths=(raw_path,),
                raw_sources=(source,),
                program_path=program,
                feature_program_path=malicious,
                label_program_path=label_program,
                config_path=config,
                output_path=tmp_path / f"{operation}-output.jsonl",
                schema=receipt.schema,
                field_metadata=tuple(
                    (name, unit, timezone_name)
                    for name, _, unit, timezone_name in receipt.field_contracts
                ),
                dataset_as_of=as_of,
                executed_at=as_of,
            )
