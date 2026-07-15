"""Outcome-blind research primitives live here."""

from quant_system.research.identity import dataset_identity_sha256
from quant_system.research.splits import purged_embargo_train_mask, walk_forward_masks

__all__ = [
    "dataset_identity_sha256",
    "purged_embargo_train_mask",
    "walk_forward_masks",
]
