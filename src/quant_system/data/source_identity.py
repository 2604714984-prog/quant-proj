"""Immutable provenance primitives shared by offline data adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict
from collections.abc import Iterable
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
import os
from pathlib import Path
import stat
from typing import Literal
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


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
_CAPTURE_TOKEN = object()


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


def require_stable_id(value: str, field: str) -> str:
    normalized = str(value).strip()
    if not normalized or any(ord(character) < 32 for character in normalized):
        raise SourceIdentityError(f"{field} must be nonempty and contain no control characters")
    return normalized


def _capture_payload(
    *,
    source_url: str,
    content_sha256: str,
    byte_count: int,
    available_at: datetime,
    retrieved_at: datetime,
    revision_id: str,
    source_family_id: str,
    provider_id: str,
    subject_id: str,
    supersedes_revision_id: str | None,
    publication_evidence_sha256: str,
    url_migration_receipt_sha256: str | None,
) -> bytes:
    payload = {
        "available_at": require_aware_utc(available_at, "available_at").isoformat(),
        "byte_count": byte_count,
        "content_sha256": require_sha256(content_sha256),
        "provider_id": require_stable_id(provider_id, "provider_id"),
        "publication_evidence_sha256": require_sha256(
            publication_evidence_sha256,
            "publication_evidence_sha256",
        ),
        "retrieved_at": require_aware_utc(retrieved_at, "retrieved_at").isoformat(),
        "revision_id": require_stable_id(revision_id, "revision_id"),
        "source_family_id": require_stable_id(source_family_id, "source_family_id"),
        "source_url": require_https_url(source_url),
        "subject_id": require_stable_id(subject_id, "subject_id"),
        "supersedes_revision_id": supersedes_revision_id,
        "url_migration_receipt_sha256": url_migration_receipt_sha256,
        "version": 1,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


@dataclass(frozen=True)
class SourceIdentity:
    """Identity of exact source bytes and when those bytes became usable."""

    source_url: str
    content_sha256: str
    available_at: datetime
    retrieved_at: datetime
    revision_id: str
    source_family_id: str
    provider_id: str
    subject_id: str
    supersedes_revision_id: str | None = None
    capture_receipt_sha256: str | None = None
    capture_byte_count: int | None = None
    publication_evidence_sha256: str | None = None
    url_migration_receipt_sha256: str | None = None
    _capture_token: object | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )

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
        revision_id = require_stable_id(self.revision_id, "revision_id")
        object.__setattr__(
            self,
            "source_family_id",
            require_stable_id(self.source_family_id, "source_family_id"),
        )
        object.__setattr__(self, "provider_id", require_stable_id(self.provider_id, "provider_id"))
        object.__setattr__(self, "subject_id", require_stable_id(self.subject_id, "subject_id"))
        supersedes = self.supersedes_revision_id
        if supersedes is not None:
            supersedes = str(supersedes).strip()
            if not supersedes or supersedes == revision_id:
                raise SourceIdentityError("supersedes_revision_id must name a different revision")
        object.__setattr__(self, "revision_id", revision_id)
        object.__setattr__(self, "supersedes_revision_id", supersedes)
        migration = self.url_migration_receipt_sha256
        if migration is not None:
            migration = require_sha256(migration, "url_migration_receipt_sha256")
        object.__setattr__(self, "url_migration_receipt_sha256", migration)
        capture_fields = (
            self.capture_receipt_sha256,
            self.capture_byte_count,
            self.publication_evidence_sha256,
        )
        if any(value is not None for value in capture_fields):
            if not all(value is not None for value in capture_fields):
                raise SourceIdentityError("trusted capture fields must be supplied together")
            if type(self.capture_byte_count) is not int or self.capture_byte_count < 0:
                raise SourceIdentityError("capture_byte_count must be a nonnegative integer")
            publication_sha = require_sha256(
                self.publication_evidence_sha256,
                "publication_evidence_sha256",
            )
            receipt_sha = require_sha256(self.capture_receipt_sha256, "capture_receipt_sha256")
            expected = hashlib.sha256(
                _capture_payload(
                    source_url=self.source_url,
                    content_sha256=self.content_sha256,
                    byte_count=self.capture_byte_count,
                    available_at=available,
                    retrieved_at=retrieved,
                    revision_id=revision_id,
                    source_family_id=self.source_family_id,
                    provider_id=self.provider_id,
                    subject_id=self.subject_id,
                    supersedes_revision_id=supersedes,
                    publication_evidence_sha256=publication_sha,
                    url_migration_receipt_sha256=migration,
                )
            ).hexdigest()
            if self._capture_token is not _CAPTURE_TOKEN or receipt_sha != expected:
                raise SourceIdentityError(
                    "trusted source identities must come from the capture entrypoint"
                )
            object.__setattr__(self, "capture_receipt_sha256", receipt_sha)
            object.__setattr__(self, "publication_evidence_sha256", publication_sha)
        elif self._capture_token is not None:
            raise SourceIdentityError("capture token cannot be supplied without a complete receipt")

    @property
    def is_trusted_capture(self) -> bool:
        return self._capture_token is _CAPTURE_TOKEN


@dataclass(frozen=True)
class SourceCaptureReceipt:
    """Immutable result of capturing source and publication-evidence bytes."""

    source: SourceIdentity
    byte_count: int
    receipt_sha256: str

    def __post_init__(self) -> None:
        require_trusted_source(self.source)
        if self.byte_count != self.source.capture_byte_count:
            raise SourceIdentityError("capture receipt byte_count mismatch")
        if require_sha256(self.receipt_sha256, "receipt_sha256") != (
            self.source.capture_receipt_sha256
        ):
            raise SourceIdentityError("capture receipt hash mismatch")


def capture_file_digest(path: Path) -> tuple[str, int]:
    candidate = path.expanduser()
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(candidate, flags)
    except OSError as exc:
        raise SourceIdentityError(f"capture path is not a regular file: {candidate}") from exc
    try:
        before = os.fstat(descriptor)
        linked = os.stat(candidate, follow_symlinks=False)
        identity = (before.st_dev, before.st_ino)
        if (
            not stat.S_ISREG(before.st_mode)
            or not stat.S_ISREG(linked.st_mode)
            or before.st_nlink != 1
            or linked.st_nlink != 1
            or identity != (linked.st_dev, linked.st_ino)
        ):
            raise SourceIdentityError("capture path must be a single-link regular file")
        digest = hashlib.sha256()
        byte_count = 0
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
            byte_count += len(chunk)
        after = os.fstat(descriptor)
        linked_after = os.stat(candidate, follow_symlinks=False)
        def signature(item: os.stat_result) -> tuple[int, int, int, int, int, int]:
            return (
                item.st_dev,
                item.st_ino,
                item.st_size,
                item.st_mtime_ns,
                item.st_ctime_ns,
                item.st_nlink,
            )
        if signature(before) != signature(after) or signature(before) != signature(linked_after):
            raise SourceIdentityError("capture path changed while bytes were being read")
        return digest.hexdigest(), byte_count
    except OSError as exc:
        raise SourceIdentityError("capture path changed while bytes were being read") from exc
    finally:
        os.close(descriptor)


def capture_file_bytes(path: Path, *, max_bytes: int = 16 * 1024 * 1024) -> bytes:
    """Read one small immutable file through the same pinned-file boundary."""

    if type(max_bytes) is not int or max_bytes < 1:
        raise ValueError("max_bytes must be a positive integer")
    candidate = path.expanduser()
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(candidate, flags)
    except OSError as exc:
        raise SourceIdentityError(f"capture path is not a regular file: {candidate}") from exc
    try:
        before = os.fstat(descriptor)
        linked = os.stat(candidate, follow_symlinks=False)
        if (
            not stat.S_ISREG(before.st_mode)
            or not stat.S_ISREG(linked.st_mode)
            or before.st_nlink != 1
            or linked.st_nlink != 1
            or (before.st_dev, before.st_ino) != (linked.st_dev, linked.st_ino)
        ):
            raise SourceIdentityError("capture path must be a single-link regular file")
        chunks: list[bytes] = []
        size = 0
        while chunk := os.read(descriptor, min(1024 * 1024, max_bytes + 1 - size)):
            chunks.append(chunk)
            size += len(chunk)
            if size > max_bytes:
                raise SourceIdentityError("capture path exceeds max_bytes")
        after = os.fstat(descriptor)
        linked_after = os.stat(candidate, follow_symlinks=False)
        def signature(item: os.stat_result) -> tuple[int, int, int, int, int, int]:
            return (
                item.st_dev,
                item.st_ino,
                item.st_size,
                item.st_mtime_ns,
                item.st_ctime_ns,
                item.st_nlink,
            )
        if signature(before) != signature(after) or signature(before) != signature(linked_after):
            raise SourceIdentityError("capture path changed while bytes were being read")
        return b"".join(chunks)
    except OSError as exc:
        raise SourceIdentityError("capture path changed while bytes were being read") from exc
    finally:
        os.close(descriptor)


def _build_capture_receipt(
    *,
    content_sha256: str,
    byte_count: int,
    publication_evidence_sha256: str,
    source_url: str,
    available_at: datetime,
    retrieved_at: datetime,
    revision_id: str,
    source_family_id: str,
    provider_id: str,
    subject_id: str,
    supersedes_revision_id: str | None,
    url_migration_receipt_sha256: str | None,
) -> SourceCaptureReceipt:
    payload = _capture_payload(
        source_url=source_url,
        content_sha256=content_sha256,
        byte_count=byte_count,
        available_at=available_at,
        retrieved_at=retrieved_at,
        revision_id=revision_id,
        source_family_id=source_family_id,
        provider_id=provider_id,
        subject_id=subject_id,
        supersedes_revision_id=supersedes_revision_id,
        publication_evidence_sha256=publication_evidence_sha256,
        url_migration_receipt_sha256=url_migration_receipt_sha256,
    )
    receipt_sha = hashlib.sha256(payload).hexdigest()
    source = SourceIdentity(
        source_url=source_url,
        content_sha256=content_sha256,
        available_at=available_at,
        retrieved_at=retrieved_at,
        revision_id=revision_id,
        source_family_id=source_family_id,
        provider_id=provider_id,
        subject_id=subject_id,
        supersedes_revision_id=supersedes_revision_id,
        capture_receipt_sha256=receipt_sha,
        capture_byte_count=byte_count,
        publication_evidence_sha256=publication_evidence_sha256,
        url_migration_receipt_sha256=url_migration_receipt_sha256,
        _capture_token=_CAPTURE_TOKEN,
    )
    return SourceCaptureReceipt(source, byte_count, receipt_sha)


def capture_source_file(
    path: Path,
    *,
    publication_evidence_path: Path,
    source_url: str,
    available_at: datetime,
    retrieved_at: datetime,
    revision_id: str,
    source_family_id: str,
    provider_id: str,
    subject_id: str,
    supersedes_revision_id: str | None = None,
    url_migration_receipt_sha256: str | None = None,
) -> SourceCaptureReceipt:
    """Capture exact local bytes without following links or trusting caller hashes."""

    content_sha, byte_count = capture_file_digest(path)
    publication_sha, _ = capture_file_digest(publication_evidence_path)
    return _build_capture_receipt(
        content_sha256=content_sha,
        byte_count=byte_count,
        publication_evidence_sha256=publication_sha,
        source_url=source_url,
        available_at=available_at,
        retrieved_at=retrieved_at,
        revision_id=revision_id,
        source_family_id=source_family_id,
        provider_id=provider_id,
        subject_id=subject_id,
        supersedes_revision_id=supersedes_revision_id,
        url_migration_receipt_sha256=url_migration_receipt_sha256,
    )


def capture_source_bytes(
    content: bytes,
    *,
    publication_evidence: bytes,
    source_url: str,
    available_at: datetime,
    retrieved_at: datetime,
    revision_id: str,
    source_family_id: str,
    provider_id: str,
    subject_id: str,
    supersedes_revision_id: str | None = None,
    url_migration_receipt_sha256: str | None = None,
) -> SourceCaptureReceipt:
    """Capture response bytes supplied directly by a provider adapter."""

    if type(content) is not bytes or type(publication_evidence) is not bytes:
        raise TypeError("content and publication_evidence must be immutable bytes")
    return _build_capture_receipt(
        content_sha256=hashlib.sha256(content).hexdigest(),
        byte_count=len(content),
        publication_evidence_sha256=hashlib.sha256(publication_evidence).hexdigest(),
        source_url=source_url,
        available_at=available_at,
        retrieved_at=retrieved_at,
        revision_id=revision_id,
        source_family_id=source_family_id,
        provider_id=provider_id,
        subject_id=subject_id,
        supersedes_revision_id=supersedes_revision_id,
        url_migration_receipt_sha256=url_migration_receipt_sha256,
    )


def require_trusted_source(source: SourceIdentity) -> SourceIdentity:
    if not isinstance(source, SourceIdentity) or not source.is_trusted_capture:
        raise SourceIdentityError("candidate-grade source must come from a capture receipt")
    return source


@dataclass(frozen=True)
class CorporateActionIdentity:
    """One rich, source-revision-bound corporate action observation."""

    subject_id: str
    action_id: str
    action_type: ActionType
    effective_at: datetime
    source: SourceIdentity
    exchange_timezone: str
    effective_date: date = field(init=False)
    ex_date: date | None = None
    record_date: date | None = None
    pay_date: date | None = None
    split_ratio: Decimal | None = None
    cash_amount: Decimal | None = None
    currency: str | None = None
    unit: str | None = None
    new_subject_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source, SourceIdentity):
            raise SourceIdentityError("source must be a canonical SourceIdentity")
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
        effective_at = require_aware_utc(self.effective_at, "effective_at")
        timezone_name = str(self.exchange_timezone).strip()
        if not timezone_name:
            raise SourceIdentityError("exchange_timezone is required")
        try:
            exchange_zone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise SourceIdentityError(
                "exchange_timezone must name an installed IANA timezone"
            ) from exc
        object.__setattr__(self, "effective_at", effective_at)
        object.__setattr__(self, "exchange_timezone", timezone_name)
        object.__setattr__(self, "effective_date", effective_at.astimezone(exchange_zone).date())
        for field_name, value in (
            ("ex_date", self.ex_date),
            ("record_date", self.record_date),
            ("pay_date", self.pay_date),
        ):
            if value is not None and type(value) is not date:
                raise SourceIdentityError(f"{field_name} must be a date")
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
        if self.ex_date is None or self.effective_date != self.ex_date:
            raise SourceIdentityError(
                "effective_at local date in exchange_timezone must equal ex_date"
            )

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


def select_source_revision(
    sources: Iterable[SourceIdentity],
    *,
    as_of: datetime,
) -> SourceIdentity:
    """Select the latest available member of one complete linear revision chain."""

    cutoff = require_aware_utc(as_of, "as_of")
    frozen = tuple(sources)
    if not frozen:
        raise SourceIdentityError("source revision chain is empty")
    if any(not isinstance(source, SourceIdentity) for source in frozen):
        raise SourceIdentityError("revision chain must contain only SourceIdentity values")
    semantic_identity = (
        frozen[0].source_family_id,
        frozen[0].provider_id,
        frozen[0].subject_id,
    )
    if any(
        (source.source_family_id, source.provider_id, source.subject_id)
        != semantic_identity
        for source in frozen
    ):
        raise SourceIdentityError(
            "source revisions must share source_family_id, provider_id, and subject_id"
        )
    by_revision: dict[str, SourceIdentity] = {}
    successors: dict[str, list[SourceIdentity]] = defaultdict(list)
    roots: list[SourceIdentity] = []
    content_hashes: set[str] = set()
    for source in frozen:
        revision_id = source.revision_id
        if revision_id in by_revision:
            raise SourceIdentityError("source revision IDs must be unique")
        if source.content_sha256 in content_hashes:
            raise SourceIdentityError("source revision hashes must be unique")
        by_revision[revision_id] = source
        content_hashes.add(source.content_sha256)
        prior = source.supersedes_revision_id
        if prior is None:
            roots.append(source)
        else:
            successors[prior].append(source)
    if len(roots) != 1:
        raise SourceIdentityError("source must have exactly one root revision")
    for prior, items in successors.items():
        if prior not in by_revision:
            raise SourceIdentityError("source revision chain has a missing parent")
        if len(items) != 1:
            raise SourceIdentityError("source revision chain is branched")

    chain: list[SourceIdentity] = []
    current = roots[0]
    seen: set[str] = set()
    while True:
        revision_id = current.revision_id
        if revision_id in seen:
            raise SourceIdentityError("source revision chain contains a cycle")
        seen.add(revision_id)
        chain.append(current)
        children = successors.get(revision_id, ())
        if not children:
            break
        child = children[0]
        if child.available_at <= current.available_at:
            raise SourceIdentityError("source revision availability must increase")
        if (
            child.source_url != current.source_url
            and child.url_migration_receipt_sha256 is None
        ):
            raise SourceIdentityError(
                "source URL changes require an immutable migration receipt"
            )
        current = child
    if len(seen) != len(frozen):
        raise SourceIdentityError("source revisions are not one connected chain")
    eligible = tuple(source for source in chain if source.available_at <= cutoff)
    if not eligible:
        raise SourceIdentityError("no source revision was available at as_of")
    return eligible[-1]


def select_corporate_action_revision(
    actions: Iterable[CorporateActionIdentity],
    *,
    as_of: datetime,
) -> CorporateActionIdentity:
    """Select one complete, linear corporate-action revision at ``as_of``."""

    frozen = tuple(actions)
    if not frozen:
        raise SourceIdentityError("corporate action revision chain is empty")
    identity = (
        frozen[0].subject_id,
        frozen[0].action_id,
        frozen[0].action_type,
        frozen[0].exchange_timezone,
    )
    if any(
        (item.subject_id, item.action_id, item.action_type, item.exchange_timezone) != identity
        for item in frozen
    ):
        raise SourceIdentityError(
            "corporate action revisions must share subject, action_id, type, and timezone"
        )
    selected = select_source_revision((item.source for item in frozen), as_of=as_of)
    return next(item for item in frozen if item.source == selected)


__all__ = [
    "CorporateActionIdentity",
    "SourceCaptureReceipt",
    "SourceIdentity",
    "SourceIdentityError",
    "capture_source_bytes",
    "capture_source_file",
    "capture_file_bytes",
    "capture_file_digest",
    "require_trusted_source",
    "select_corporate_action_revision",
    "select_source_revision",
]
