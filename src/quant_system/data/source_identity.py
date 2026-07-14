"""Immutable provenance primitives shared by offline data adapters."""

from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict
from collections.abc import Iterable
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import re
from typing import Literal
from urllib.parse import urlparse


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ActionType = Literal[
    "split",
    "reverse_split",
    "cash_dividend",
    "special_dividend",
    "symbol_change",
]
_ACTION_TYPES = frozenset(ActionType.__args__)
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
    """One rich, source-revision-bound corporate action observation."""

    subject_id: str
    action_id: str
    action_type: ActionType
    effective_at: datetime
    source: SourceIdentity
    ex_date: date | None = None
    record_date: date | None = None
    pay_date: date | None = None
    split_ratio: Decimal | None = None
    cash_amount: Decimal | None = None
    currency: str | None = None
    unit: str | None = None
    new_subject_id: str | None = None

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
        for field, value in (
            ("ex_date", self.ex_date),
            ("record_date", self.record_date),
            ("pay_date", self.pay_date),
        ):
            if value is not None and type(value) is not date:
                raise SourceIdentityError(f"{field} must be a date")
        ratio = self.split_ratio
        amount = self.cash_amount
        currency = None if self.currency is None else str(self.currency).strip()
        unit = None if self.unit is None else str(self.unit).strip()
        new_subject = None if self.new_subject_id is None else str(self.new_subject_id).strip()
        if action_type in _SPLIT_ACTION_TYPES:
            if (
                any(value is not None for value in (amount, currency, unit, new_subject))
                or ratio is None
            ):
                raise SourceIdentityError("split actions require dates and split_ratio only")
            ratio = require_decimal(ratio, "split_ratio")
            if action_type == "split" and ratio <= 1:
                raise SourceIdentityError("split ratio must be greater than one")
            if action_type == "reverse_split" and not 0 < ratio < 1:
                raise SourceIdentityError("reverse_split ratio must be between zero and one")
            self._require_effective_ex_date()
            self._require_optional_record_pay_order()
        elif action_type in _CASH_ACTION_TYPES:
            if ratio is not None or amount is None or not unit or not currency:
                raise SourceIdentityError("cash actions require cash_amount, currency, and unit")
            amount = require_decimal(amount, "cash_amount")
            if amount <= 0:
                raise SourceIdentityError("cash_amount must be positive")
            if len(currency) != 3 or not currency.isalpha() or not currency.isupper():
                raise SourceIdentityError("currency must be a three-letter uppercase code")
            if new_subject is not None:
                raise SourceIdentityError("cash actions cannot change subject")
            self._require_effective_ex_date()
            if self.record_date is None or self.pay_date is None:
                raise SourceIdentityError("cash actions require ex_date, record_date, and pay_date")
            self._require_optional_record_pay_order()
        else:
            if not new_subject or new_subject == subject_id:
                raise SourceIdentityError("symbol_change requires a distinct new_subject_id")
            if any(
                value is not None
                for value in (
                    self.ex_date,
                    self.record_date,
                    self.pay_date,
                    ratio,
                    amount,
                    currency,
                    unit,
                )
            ):
                raise SourceIdentityError("symbol_change cannot carry distribution or split fields")
        object.__setattr__(self, "split_ratio", ratio)
        object.__setattr__(self, "cash_amount", amount)
        object.__setattr__(self, "currency", currency)
        object.__setattr__(self, "unit", unit)
        object.__setattr__(self, "new_subject_id", new_subject)

    def _require_effective_ex_date(self) -> None:
        if self.ex_date is None or self.effective_at.date() != self.ex_date:
            raise SourceIdentityError("effective_at date must equal ex_date")

    def _require_optional_record_pay_order(self) -> None:
        if (self.record_date is None) != (self.pay_date is None):
            raise SourceIdentityError(
                "record_date and pay_date must be both present or both absent"
            )
        if self.record_date is not None:
            assert self.ex_date is not None and self.pay_date is not None
            if not self.ex_date <= self.record_date <= self.pay_date:
                raise SourceIdentityError(
                    "action dates must satisfy ex_date <= record_date <= pay_date"
                )


def select_corporate_action_revision(
    actions: Iterable[CorporateActionIdentity],
    *,
    as_of: datetime,
) -> CorporateActionIdentity:
    """Select one complete, linear source revision chain at ``as_of``."""

    cutoff = require_aware_utc(as_of, "as_of")
    frozen = tuple(actions)
    if not frozen:
        raise SourceIdentityError("corporate action revision chain is empty")
    identity = (frozen[0].subject_id, frozen[0].action_id, frozen[0].action_type)
    if any((item.subject_id, item.action_id, item.action_type) != identity for item in frozen):
        raise SourceIdentityError(
            "corporate action revisions must share subject, action_id, and type"
        )
    by_revision: dict[str, CorporateActionIdentity] = {}
    successors: dict[str, list[CorporateActionIdentity]] = defaultdict(list)
    roots: list[CorporateActionIdentity] = []
    content_hashes: set[str] = set()
    for item in frozen:
        revision_id = item.source.revision_id
        if revision_id in by_revision:
            raise SourceIdentityError("corporate action revision IDs must be unique")
        if item.source.content_sha256 in content_hashes:
            raise SourceIdentityError("corporate action revision hashes must be unique")
        by_revision[revision_id] = item
        content_hashes.add(item.source.content_sha256)
        prior = item.source.supersedes_revision_id
        if prior is None:
            roots.append(item)
        else:
            successors[prior].append(item)
    if len(roots) != 1:
        raise SourceIdentityError("corporate action must have exactly one root revision")
    for prior, items in successors.items():
        if prior not in by_revision:
            raise SourceIdentityError("corporate action revision chain has a missing parent")
        if len(items) != 1:
            raise SourceIdentityError("corporate action revision chain is branched")

    chain: list[CorporateActionIdentity] = []
    current = roots[0]
    seen: set[str] = set()
    while True:
        revision_id = current.source.revision_id
        if revision_id in seen:
            raise SourceIdentityError("corporate action revision chain contains a cycle")
        seen.add(revision_id)
        chain.append(current)
        children = successors.get(revision_id, ())
        if not children:
            break
        child = children[0]
        if child.source.available_at <= current.source.available_at:
            raise SourceIdentityError("corporate action revision availability must increase")
        current = child
    if len(seen) != len(frozen):
        raise SourceIdentityError("corporate action revisions are not one connected chain")
    eligible = tuple(item for item in chain if item.source.available_at <= cutoff)
    if not eligible:
        raise SourceIdentityError("no corporate action revision was available at as_of")
    return eligible[-1]


__all__ = [
    "CorporateActionIdentity",
    "SourceIdentity",
    "SourceIdentityError",
    "select_corporate_action_revision",
]
