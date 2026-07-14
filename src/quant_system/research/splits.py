"""Small, explicit helpers for point-in-time research splits."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Sequence, TypeAlias


DateLike: TypeAlias = date | datetime


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
    if expected_type is date and embargo.seconds != 0:
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
    general_train = purged_embargo_train_mask(
        observations,
        label_end_at,
        test_start=test_start,
        test_end=test_end,
    )
    train = tuple(keep and value < test_start for keep, value in zip(general_train, observations))
    test = tuple(test_start <= value <= test_end for value in observations)
    if not any(train):
        raise ValueError("split contains no purged training observations")
    if not any(test):
        raise ValueError("split contains no test observations")
    return train, test
