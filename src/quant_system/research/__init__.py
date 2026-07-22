"""Outcome-blind research primitives live here."""

from quant_system.research.identity import (
    DatasetManifest,
    build_dataset_manifest,
    dataset_identity_sha256,
)
from quant_system.research.experiments import (
    ExperimentEvent,
    ExperimentManifest,
    freeze_experiment_manifest,
    preregister_trial,
    record_holdout_result,
    require_adjusted_holdout_for_candidate,
    verify_experiment_manifest,
)
from quant_system.research.splits import (
    SplitEvaluation,
    SplitManifest,
    SplitSample,
    build_split_manifest,
    evaluate_split,
    purged_embargo_train_mask,
    require_split_evaluation_for_candidate,
    walk_forward_masks,
)

__all__ = [
    "dataset_identity_sha256",
    "build_dataset_manifest",
    "DatasetManifest",
    "ExperimentEvent",
    "ExperimentManifest",
    "SplitEvaluation",
    "SplitManifest",
    "SplitSample",
    "build_split_manifest",
    "evaluate_split",
    "freeze_experiment_manifest",
    "preregister_trial",
    "purged_embargo_train_mask",
    "record_holdout_result",
    "require_adjusted_holdout_for_candidate",
    "require_split_evaluation_for_candidate",
    "verify_experiment_manifest",
    "walk_forward_masks",
]
