"""Small, explicit helpers for point-in-time research splits."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from dataclasses import field
from datetime import date, datetime, timedelta
import hashlib
import json
import math
import random
import statistics
from typing import Literal, Sequence, TypeAlias


DateLike: TypeAlias = date | datetime
EvaluationMethod = Literal["non_overlapping", "hac", "block_bootstrap"]
_EVALUATION_TOKEN = object()


def _time_text(value: DateLike) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("split datetimes must be timezone-aware")
        return value.isoformat()
    if type(value) is date:
        return value.isoformat()
    raise TypeError("split times must be dates or datetimes")


@dataclass(frozen=True)
class SplitSample:
    sample_id: str
    entity_id: str
    observed_at: DateLike
    label_end_at: DateLike
    fold_id: str
    overlap_group: str


@dataclass(frozen=True)
class SplitManifest:
    samples: tuple[SplitSample, ...]
    manifest_sha256: str


@dataclass(frozen=True)
class SplitEvaluation:
    method: EvaluationMethod
    selected_sample_ids: tuple[str, ...]
    nominal_n: int
    effective_n: float
    overlap_corrected: bool
    manifest_sha256: str
    returns_sha256: str
    estimator_sha256: str
    statistic: float
    standard_error: float
    hac_bandwidth: int | None
    block_length: int | None
    bootstrap_replicates: int | None
    evaluation_sha256: str
    _token: object | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._token is not _EVALUATION_TOKEN:
            raise ValueError("SplitEvaluation must be created by evaluate_split")
        if hashlib.sha256(_evaluation_payload(self)).hexdigest() != self.evaluation_sha256:
            raise ValueError("split evaluation receipt hash mismatch")


def _evaluation_payload(evaluation: SplitEvaluation) -> bytes:
    return json.dumps(
        {
            name: value
            for name, value in evaluation.__dict__.items()
            if name not in {"evaluation_sha256", "_token"}
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def build_split_manifest(
    *,
    entity_ids: Sequence[str],
    observed_at: Sequence[DateLike],
    label_end_at: Sequence[DateLike],
    fold_ids: Sequence[str],
) -> SplitManifest:
    """Build stable panel sample IDs and connected interval-overlap groups."""

    entities = tuple(entity_ids)
    observations = tuple(observed_at)
    labels = tuple(label_end_at)
    folds = tuple(fold_ids)
    count = len(entities)
    if count == 0 or any(len(values) != count for values in (observations, labels, folds)):
        raise ValueError("split manifest columns must have one nonempty common length")
    expected_type = type(observations[0])
    if expected_type not in {date, datetime}:
        raise TypeError("observed_at must contain dates or datetimes")
    rows: list[dict[str, object]] = []
    seen_keys: set[tuple[str, DateLike]] = set()
    for entity, observed, label_end, fold in zip(
        entities,
        observations,
        labels,
        folds,
        strict=True,
    ):
        if not isinstance(entity, str) or not entity.strip():
            raise ValueError("entity_id must be nonempty")
        if not isinstance(fold, str) or not fold.strip():
            raise ValueError("fold_id must be nonempty")
        if type(observed) is not expected_type or type(label_end) is not expected_type:
            raise TypeError("split times must use one consistent temporal type")
        observed_text = _time_text(observed)
        label_text = _time_text(label_end)
        if label_end < observed:
            raise ValueError("label_end_at cannot precede observed_at")
        key = (entity, observed)
        if key in seen_keys:
            raise ValueError("entity_id and observed_at must identify one panel sample")
        seen_keys.add(key)
        sample_id = hashlib.sha256(
            f"{entity}|{observed_text}|{label_text}|{fold}".encode()
        ).hexdigest()
        rows.append(
            {
                "entity": entity,
                "observed": observed,
                "label_end": label_end,
                "fold": fold,
                "sample_id": sample_id,
            }
        )
    overlap_by_sample: dict[str, str] = {}
    by_fold: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_fold[str(row["fold"])].append(row)
    for fold, fold_rows in sorted(by_fold.items()):
        ordered = sorted(
            fold_rows,
            key=lambda row: (row["observed"], row["label_end"], row["sample_id"]),
        )
        group_index = -1
        group_end: DateLike | None = None
        for row in ordered:
            observed = row["observed"]
            label_end = row["label_end"]
            assert isinstance(observed, (date, datetime))
            assert isinstance(label_end, (date, datetime))
            if group_end is None or observed > group_end:
                group_index += 1
                group_end = label_end
            elif label_end > group_end:
                group_end = label_end
            group = hashlib.sha256(f"{fold}|{group_index}".encode()).hexdigest()
            overlap_by_sample[str(row["sample_id"])] = group
    samples = tuple(
        SplitSample(
            sample_id=str(row["sample_id"]),
            entity_id=str(row["entity"]),
            observed_at=row["observed"],  # type: ignore[arg-type]
            label_end_at=row["label_end"],  # type: ignore[arg-type]
            fold_id=str(row["fold"]),
            overlap_group=overlap_by_sample[str(row["sample_id"])],
        )
        for row in sorted(rows, key=lambda item: str(item["sample_id"]))
    )
    payload = tuple(sample.__dict__ for sample in samples)
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=_time_text).encode()
    ).hexdigest()
    return SplitManifest(samples, digest)


def evaluate_split(
    manifest: SplitManifest,
    *,
    selected_sample_ids: Sequence[str],
    returns: Sequence[float],
    method: EvaluationMethod,
    hac_bandwidth: int | None = None,
    block_length: int | None = None,
    bootstrap_replicates: int = 1000,
) -> SplitEvaluation:
    if not isinstance(manifest, SplitManifest):
        raise TypeError("manifest must be a SplitManifest")
    selected = tuple(selected_sample_ids)
    if not selected or len(selected) != len(set(selected)):
        raise ValueError("selected_sample_ids must be nonempty and unique")
    by_id = {sample.sample_id: sample for sample in manifest.samples}
    if not set(selected) <= set(by_id):
        raise ValueError("selected sample is absent from split manifest")
    if method not in {"non_overlapping", "hac", "block_bootstrap"}:
        raise ValueError("unsupported split evaluation method")
    selected_samples = tuple(by_id[sample_id] for sample_id in selected)
    overlapping = any(
        left.fold_id == right.fold_id
        and left.observed_at <= right.label_end_at
        and right.observed_at <= left.label_end_at
        for index, left in enumerate(selected_samples)
        for right in selected_samples[index + 1 :]
    )
    if method == "non_overlapping" and overlapping:
        raise ValueError("non-overlapping evaluation selected overlapping labels")
    frozen_returns = tuple(returns)
    if len(frozen_returns) != len(selected) or len(frozen_returns) < 2 or any(
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
        for value in frozen_returns
    ):
        raise ValueError("returns must provide at least two finite values in selected order")
    values = tuple(float(value) for value in frozen_returns)
    mean = statistics.fmean(values)
    sample_variance = statistics.variance(values)
    estimator = {
        "method": method,
        "version": 1,
        "hac_bandwidth": hac_bandwidth,
        "block_length": block_length,
        "bootstrap_replicates": (
            bootstrap_replicates if method == "block_bootstrap" else None
        ),
    }
    if method == "non_overlapping":
        if hac_bandwidth is not None or block_length is not None:
            raise ValueError("non-overlapping evaluation does not accept correction parameters")
        standard_error = math.sqrt(sample_variance / len(values))
        effective_n = float(len(values))
    elif method == "hac":
        if (
            type(hac_bandwidth) is not int
            or not 1 <= hac_bandwidth < len(values)
            or block_length is not None
        ):
            raise ValueError("HAC requires bandwidth in [1, nominal_n)")
        centered = tuple(value - mean for value in values)
        long_run_variance = math.fsum(value * value for value in centered) / len(values)
        for lag in range(1, hac_bandwidth + 1):
            covariance = math.fsum(
                centered[index] * centered[index - lag]
                for index in range(lag, len(values))
            ) / len(values)
            long_run_variance += 2 * (1 - lag / (hac_bandwidth + 1)) * covariance
        if long_run_variance <= 0 or not math.isfinite(long_run_variance):
            raise ValueError("HAC long-run variance must be positive and finite")
        standard_error = math.sqrt(long_run_variance / len(values))
        effective_n = min(
            float(len(values)),
            max(1.0, sample_variance / (standard_error * standard_error)),
        )
    else:
        if (
            type(block_length) is not int
            or not 2 <= block_length <= len(values)
            or hac_bandwidth is not None
            or type(bootstrap_replicates) is not int
            or bootstrap_replicates < 200
        ):
            raise ValueError(
                "block bootstrap requires block_length in [2, nominal_n] "
                "and at least 200 replicates"
            )
        seed_payload = json.dumps(
            {"returns": values, **estimator},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        generator = random.Random(int(hashlib.sha256(seed_payload).hexdigest(), 16))
        bootstrap_means: list[float] = []
        for _ in range(bootstrap_replicates):
            sample: list[float] = []
            while len(sample) < len(values):
                start = generator.randrange(len(values))
                sample.extend(
                    values[(start + offset) % len(values)]
                    for offset in range(block_length)
                )
            bootstrap_means.append(statistics.fmean(sample[: len(values)]))
        standard_error = statistics.stdev(bootstrap_means)
        if standard_error <= 0 or not math.isfinite(standard_error):
            raise ValueError("block-bootstrap standard error must be positive and finite")
        effective_n = min(
            float(len(values)),
            max(1.0, sample_variance / (standard_error * standard_error)),
        )
    if standard_error <= 0 or not math.isfinite(standard_error):
        raise ValueError("evaluation standard error must be positive and finite")
    returns_sha = hashlib.sha256(
        json.dumps(values, separators=(",", ":")).encode()
    ).hexdigest()
    estimator_sha = hashlib.sha256(
        json.dumps(estimator, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    values_by_field = {
        "method": method,
        "selected_sample_ids": selected,
        "nominal_n": len(selected),
        "effective_n": float(effective_n),
        "overlap_corrected": method in {"hac", "block_bootstrap"} or not overlapping,
        "manifest_sha256": manifest.manifest_sha256,
        "returns_sha256": returns_sha,
        "estimator_sha256": estimator_sha,
        "statistic": mean / standard_error,
        "standard_error": standard_error,
        "hac_bandwidth": hac_bandwidth,
        "block_length": block_length,
        "bootstrap_replicates": (
            bootstrap_replicates if method == "block_bootstrap" else None
        ),
    }
    provisional = object.__new__(SplitEvaluation)
    for name, value in values_by_field.items():
        object.__setattr__(provisional, name, value)
    digest = hashlib.sha256(_evaluation_payload(provisional)).hexdigest()
    return SplitEvaluation(
        **values_by_field,
        evaluation_sha256=digest,
        _token=_EVALUATION_TOKEN,
    )


def require_split_evaluation_for_candidate(evaluation: SplitEvaluation) -> None:
    if not isinstance(evaluation, SplitEvaluation) or not evaluation.overlap_corrected:
        raise ValueError("candidate significance requires overlap correction")


def _validate_time_axis(values: Sequence[DateLike], *, name: str) -> tuple[DateLike, ...]:
    frozen = tuple(values)
    if not frozen:
        raise ValueError(f"{name} must not be empty")
    expected_type = type(frozen[0])
    if expected_type not in (date, datetime):
        raise TypeError(f"{name} must contain only dates or only datetimes")
    if any(type(value) is not expected_type for value in frozen):
        raise TypeError(f"{name} must contain one consistent temporal type")
    if expected_type is datetime:
        for value in frozen:
            assert isinstance(value, datetime)
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} datetimes must be timezone-aware")
    if frozen != tuple(sorted(frozen)) or len(frozen) != len(set(frozen)):
        raise ValueError(f"{name} must be strictly increasing and unique")
    return frozen


def purged_embargo_train_mask(
    observed_at: Sequence[DateLike],
    label_end_at: Sequence[DateLike],
    *,
    test_start: DateLike,
    test_end: DateLike,
    embargo: timedelta = timedelta(0),
) -> tuple[bool, ...]:
    """Return training eligibility without label overlap or post-test leakage.

    An observation is removed when its inclusive information/label interval
    intersects the inclusive test interval. Observations after the test are
    additionally removed through ``test_end + embargo``. This general helper
    supports both walk-forward (use only the pre-test ``True`` values) and
    symmetric cross-validation splits.
    """

    observations = _validate_time_axis(observed_at, name="observed_at")
    labels = tuple(label_end_at)
    if len(labels) != len(observations):
        raise ValueError("label_end_at must have the same length as observed_at")
    if not isinstance(embargo, timedelta):
        raise TypeError("embargo must be a timedelta")
    if timedelta(0) > embargo:
        raise ValueError("embargo must be nonnegative")

    expected_type = type(observations[0])
    if expected_type is date and (embargo.seconds != 0 or embargo.microseconds != 0):
        raise ValueError("date-based embargo must use a whole number of days")
    if type(test_start) is not expected_type or type(test_end) is not expected_type:
        raise TypeError("test bounds must use the same temporal type as observed_at")
    if expected_type is datetime:
        for bound in (test_start, test_end):
            assert isinstance(bound, datetime)
            if bound.tzinfo is None or bound.utcoffset() is None:
                raise ValueError("test bound datetimes must be timezone-aware")
    if test_start > test_end:
        raise ValueError("test_start must not be after test_end")

    for observation, label_end in zip(observations, labels, strict=True):
        if type(label_end) is not expected_type:
            raise TypeError("label_end_at must use the same temporal type as observed_at")
        if expected_type is datetime:
            assert isinstance(label_end, datetime)
            if label_end.tzinfo is None or label_end.utcoffset() is None:
                raise ValueError("label_end_at datetimes must be timezone-aware")
        if label_end < observation:
            raise ValueError("a label cannot end before its observation")

    embargo_end = test_end + embargo
    mask: list[bool] = []
    for observation, label_end in zip(observations, labels, strict=True):
        overlaps_test = observation <= test_end and label_end >= test_start
        inside_post_test_embargo = test_end < observation <= embargo_end
        mask.append(not overlaps_test and not inside_post_test_embargo)
    return tuple(mask)


def walk_forward_masks(
    observed_at: Sequence[DateLike],
    label_end_at: Sequence[DateLike],
    *,
    test_start: DateLike,
    test_end: DateLike,
) -> tuple[tuple[bool, ...], tuple[bool, ...]]:
    """Return strictly historical train and inclusive test masks.

    Future observations are never admitted to the training mask. Labels that
    reach the first test timestamp are purged in full.
    """

    observations = _validate_time_axis(observed_at, name="observed_at")
    labels = tuple(label_end_at)
    general_train = purged_embargo_train_mask(
        observations,
        labels,
        test_start=test_start,
        test_end=test_end,
    )
    train = tuple(keep and value < test_start for keep, value in zip(general_train, observations))
    test = tuple(
        test_start <= value <= test_end and label_end <= test_end
        for value, label_end in zip(observations, labels, strict=True)
    )
    if not any(train):
        raise ValueError("split contains no purged training observations")
    if not any(test):
        raise ValueError("split contains no test observations")
    return train, test
