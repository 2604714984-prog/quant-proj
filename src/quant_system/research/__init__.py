"""Outcome-blind research primitives live here."""

from quant_system.research.identity import dataset_identity_sha256
from quant_system.research.splits import purged_embargo_train_mask, walk_forward_masks
from quant_system.research.stats import (
    DeflatedSharpeResult,
    ExpectedMaximumSharpeResult,
    HACMeanResult,
    NullCenteredBootstrapResult,
    PBOResult,
    circular_block_bootstrap_greater_mean_test,
    circular_block_bootstrap_indices,
    circular_block_bootstrap_means,
    deflated_sharpe_ratio,
    expected_maximum_sharpe,
    newey_west_mean_test,
    overlapping_ic_hac_test,
    probabilistic_sharpe_ratio,
    probability_of_backtest_overfitting,
)

__all__ = [
    "DeflatedSharpeResult",
    "ExpectedMaximumSharpeResult",
    "HACMeanResult",
    "NullCenteredBootstrapResult",
    "PBOResult",
    "circular_block_bootstrap_greater_mean_test",
    "circular_block_bootstrap_indices",
    "circular_block_bootstrap_means",
    "dataset_identity_sha256",
    "deflated_sharpe_ratio",
    "expected_maximum_sharpe",
    "newey_west_mean_test",
    "overlapping_ic_hac_test",
    "probabilistic_sharpe_ratio",
    "probability_of_backtest_overfitting",
    "purged_embargo_train_mask",
    "walk_forward_masks",
]
