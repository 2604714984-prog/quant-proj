from datetime import date, datetime, timedelta, timezone

import pytest

from quant_system.research.identity import dataset_identity_sha256
from quant_system.research.splits import purged_embargo_train_mask, walk_forward_masks


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
    labels = tuple(value + timedelta(days=2) for value in observations)

    train, test = walk_forward_masks(
        observations,
        labels,
        test_start=date(2026, 1, 5),
        test_end=date(2026, 1, 6),
    )

    assert train == (True, True, False, False, False, False, False, False, False, False)
    assert test == (False, False, False, False, True, True, False, False, False, False)
    assert not any(keep and value >= date(2026, 1, 5) for keep, value in zip(train, observations))


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


def _identity(**overrides: object) -> str:
    inputs: dict[str, object] = {
        "dates": (date(2026, 1, 2), date(2026, 1, 5)),
        "frequency": "1d-close",
        "schema": (("symbol", "VARCHAR"), ("close", "DOUBLE")),
        "config_ids": {"universe": "abc123", "costs": "def456"},
        "partition_sha256s": ("0" * 64, "1" * 64),
    }
    inputs.update(overrides)
    return dataset_identity_sha256(**inputs)  # type: ignore[arg-type]


def test_dataset_identity_has_a_fixed_canonical_golden_hash() -> None:
    assert _identity() == "d578923bd9652ad59c8dcccdac463494e1504a062c15cb7e7c285102931b167a"
    assert _identity(config_ids={"costs": "def456", "universe": "abc123"}) == _identity()


@pytest.mark.parametrize(
    "override",
    [
        {"dates": (date(2026, 1, 2), date(2026, 1, 6))},
        {"frequency": "1d-open"},
        {"schema": (("symbol", "VARCHAR"), ("close", "DECIMAL"))},
        {"config_ids": {"universe": "changed", "costs": "def456"}},
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
