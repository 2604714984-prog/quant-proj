"""Immutable provenance primitives shared by offline data adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import re
from urllib.parse import urlparse


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ACTION_TYPES = frozenset(
    {
        "split",
        "reverse_split",
        "cash_dividend",
        "special_dividend",
        "symbol_change",
        "merger",
        "delisting",
        "trading_halt",
    }
)
_CASH_ACTION_TYPES = frozenset({"cash_dividend", "special_dividend"})
_SPLIT_ACTION_TYPES = frozenset({"split", "reverse_split"})


class SourceIdentityError(ValueError):
    """Raised when source provenance is missing or internally inconsistent."""


def require_aware_utc(value: datetime, field: str) -> datetime:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise SourceIdentityError(f"{field} must be a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def require_sha256(value: str, field: str = "content_sha256") -> str:
    digest = str(value).strip().lower()
    if _SHA256_RE.fullmatch(digest) is None:
        raise SourceIdentityError(f"{field} must be a lowercase SHA-256 digest")
    return digest


def require_https_url(value: str, field: str = "source_url") -> str:
    url = str(value).strip()
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise SourceIdentityError(f"{field} must be an HTTPS URL without credentials or a fragment")
    return url


def require_decimal(value: object, field: str) -> Decimal:
    if isinstance(value, bool):
        raise SourceIdentityError(f"{field} must be finite")
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise SourceIdentityError(f"{field} must be finite") from exc
    if not parsed.is_finite():
        raise SourceIdentityError(f"{field} must be finite")
    return parsed


@dataclass(frozen=True)
class SourceIdentity:
    """Identity of exact source bytes and when those bytes became usable."""

    source_url: str
    content_sha256: str
    available_at: datetime
    retrieved_at: datetime
    revision_id: str
    supersedes_revision_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_url", require_https_url(self.source_url))
        object.__setattr__(
            self,
            "content_sha256",
            require_sha256(self.content_sha256),
        )
        available = require_aware_utc(self.available_at, "available_at")
        retrieved = require_aware_utc(self.retrieved_at, "retrieved_at")
        if retrieved < available:
            raise SourceIdentityError("retrieved_at cannot precede available_at")
        object.__setattr__(self, "available_at", available)
        object.__setattr__(self, "retrieved_at", retrieved)
        revision_id = str(self.revision_id).strip()
        if not revision_id:
            raise SourceIdentityError("revision_id is required")
        supersedes = self.supersedes_revision_id
        if supersedes is not None:
            supersedes = str(supersedes).strip()
            if not supersedes or supersedes == revision_id:
                raise SourceIdentityError("supersedes_revision_id must name a different revision")
        object.__setattr__(self, "revision_id", revision_id)
        object.__setattr__(self, "supersedes_revision_id", supersedes)


@dataclass(frozen=True)
class CorporateActionIdentity:
    """A source-bound corporate action; values are present only when applicable."""

    subject_id: str
    action_id: str
    action_type: str
    effective_at: datetime
    source: SourceIdentity
    split_ratio: Decimal | None = None
    cash_amount: Decimal | None = None
    unit: str | None = None

    def __post_init__(self) -> None:
        subject_id = str(self.subject_id).strip()
        action_id = str(self.action_id).strip()
        action_type = str(self.action_type).strip().lower()
        if not subject_id or not action_id:
            raise SourceIdentityError("subject_id and action_id are required")
        if action_type not in _ACTION_TYPES:
            raise SourceIdentityError(f"unsupported corporate action: {action_type!r}")
        object.__setattr__(self, "subject_id", subject_id)
        object.__setattr__(self, "action_id", action_id)
        object.__setattr__(self, "action_type", action_type)
        object.__setattr__(
            self,
            "effective_at",
            require_aware_utc(self.effective_at, "effective_at"),
        )

        ratio = self.split_ratio
        amount = self.cash_amount
        unit = None if self.unit is None else str(self.unit).strip()
        if action_type in _SPLIT_ACTION_TYPES:
            if amount is not None or unit is not None or ratio is None:
                raise SourceIdentityError("split actions require only a positive split_ratio")
            ratio = require_decimal(ratio, "split_ratio")
            if ratio <= 0:
                raise SourceIdentityError("split_ratio must be positive")
        elif action_type in _CASH_ACTION_TYPES:
            if ratio is not None or amount is None or not unit:
                raise SourceIdentityError(
                    "cash actions require cash_amount and unit, but no split_ratio"
                )
            amount = require_decimal(amount, "cash_amount")
            if amount < 0:
                raise SourceIdentityError("cash_amount must be nonnegative")
        elif ratio is not None or amount is not None or unit is not None:
            raise SourceIdentityError("non-financial actions cannot carry ratio, amount, or unit")
        object.__setattr__(self, "split_ratio", ratio)
        object.__setattr__(self, "cash_amount", amount)
        object.__setattr__(self, "unit", unit)


__all__ = [
    "CorporateActionIdentity",
    "SourceIdentity",
    "SourceIdentityError",
]
