"""Effective-dated security-universe predicate over accepted PIT identities."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from quant_system.data import (
    AcceptedSession,
    CalendarIdentity,
    SourceIdentity,
    TypedObservationReceipt,
    calendar_identity_sha256,
    capture_file_bytes,
    capture_file_digest,
    require_trusted_source,
    select_source_revision,
)
from quant_system.data.source_identity import require_sha256

from .common import (
    MarketDataError,
    require_aware_datetime,
    require_date,
    require_nonempty_text,
)

StatusKind = Literal["listed", "delisted", "st", "suspended"]
UniverseMarket = Literal["a_share", "us"]
ALL_STATUS_KINDS: tuple[StatusKind, ...] = (
    "listed",
    "delisted",
    "st",
    "suspended",
)
US_REQUIRED_STATUS_KINDS: tuple[StatusKind, ...] = (
    "listed",
    "delisted",
)
_UNIVERSE_MATERIALIZATION_TOKEN = object()


@dataclass(frozen=True)
class StatusEvidence:
    status_id: str
    symbol: str
    kind: StatusKind
    value: bool
    effective_from: date
    effective_to: date | None
    exchange_timezone: str
    source: SourceIdentity
    observation_receipt: TypedObservationReceipt | None = None

    def __post_init__(self) -> None:
        require_nonempty_text(self.status_id, "status_id")
        require_nonempty_text(self.symbol, "symbol")
        if self.kind not in ALL_STATUS_KINDS:
            raise MarketDataError(f"unsupported status kind: {self.kind!r}")
        if type(self.value) is not bool:
            raise MarketDataError("status value must be boolean")
        require_date(self.effective_from, "effective_from")
        if self.effective_to is not None:
            require_date(self.effective_to, "effective_to")
            if self.effective_to <= self.effective_from:
                raise MarketDataError("effective_to must be later than effective_from")
        timezone_name = require_nonempty_text(self.exchange_timezone, "exchange_timezone")
        try:
            ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise MarketDataError("exchange_timezone must be an installed IANA timezone") from exc
        if not isinstance(self.source, SourceIdentity):
            raise MarketDataError("source must be a canonical SourceIdentity")

    def effective_on(self, session: date) -> bool:
        return self.effective_from <= session and (
            self.effective_to is None or session < self.effective_to
        )


@dataclass(frozen=True)
class UniverseDecision:
    eligible: bool
    reasons: tuple[str, ...]
    evidence: tuple[tuple[StatusKind, str, SourceIdentity], ...]


@dataclass(frozen=True)
class UniverseSnapshotIdentity:
    """Immutable identity of the complete candidate set for one decision session."""

    market: UniverseMarket
    exchange_id: str
    effective_session: date
    member_count: int
    ordered_members_sha256: str
    lifecycle_coverage_sha256: str
    inclusion_rule_sha256: str
    calendar_identity_sha256: str
    source_identity: SourceIdentity
    source_partition_sha256: str | None = None
    materialization_sha256: str | None = None
    observation_receipt: TypedObservationReceipt | None = None

    def __post_init__(self) -> None:
        if self.market not in {"a_share", "us"}:
            raise MarketDataError("universe market must be a_share or us")
        object.__setattr__(
            self,
            "exchange_id",
            require_nonempty_text(self.exchange_id, "exchange_id"),
        )
        require_date(self.effective_session, "effective_session")
        if type(self.member_count) is not int or self.member_count < 1:
            raise MarketDataError("member_count must be a positive integer")
        for field_name in (
            "ordered_members_sha256",
            "lifecycle_coverage_sha256",
            "inclusion_rule_sha256",
            "calendar_identity_sha256",
        ):
            try:
                digest = require_sha256(getattr(self, field_name), field_name)
            except ValueError as exc:
                raise MarketDataError(str(exc)) from exc
            object.__setattr__(self, field_name, digest)
        if not isinstance(self.source_identity, SourceIdentity):
            raise MarketDataError("universe source_identity must be a SourceIdentity")
        materialization_fields = (
            self.source_partition_sha256,
            self.materialization_sha256,
        )
        if any(value is not None for value in materialization_fields):
            if not all(value is not None for value in materialization_fields):
                raise MarketDataError(
                    "source_partition_sha256 and materialization_sha256 must be supplied together"
                )
            for field_name in ("source_partition_sha256", "materialization_sha256"):
                try:
                    digest = require_sha256(getattr(self, field_name), field_name)
                except ValueError as exc:
                    raise MarketDataError(str(exc)) from exc
                object.__setattr__(self, field_name, digest)


@dataclass(frozen=True)
class UniverseMaterializationEntry:
    """One explicit inclusion or exclusion from the complete source partition."""

    symbol: str
    included: bool
    exclusion_reason: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", require_nonempty_text(self.symbol, "symbol"))
        if type(self.included) is not bool:
            raise MarketDataError("included must be boolean")
        if self.included:
            if self.exclusion_reason is not None:
                raise MarketDataError("included symbols cannot have an exclusion reason")
        else:
            object.__setattr__(
                self,
                "exclusion_reason",
                require_nonempty_text(self.exclusion_reason, "exclusion_reason"),
            )


@dataclass(frozen=True)
class UniverseMaterialization:
    """Captured complete-partition materialization accepted by the candidate API."""

    entries: tuple[UniverseMaterializationEntry, ...]
    snapshot: UniverseSnapshotIdentity
    source_partition_sha256: str
    inclusion_rule_sha256: str
    source_lifecycle_coverage_sha256: str
    materialization_sha256: str
    _source_partition_path: Path = field(repr=False, compare=False, hash=False)
    _inclusion_rule_path: Path = field(repr=False, compare=False, hash=False)
    _materialization_token: object | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if self._materialization_token is not _UNIVERSE_MATERIALIZATION_TOKEN:
            raise MarketDataError(
                "UniverseMaterialization must come from materialize_universe_partition"
            )
        if not self.entries or tuple(sorted(entry.symbol for entry in self.entries)) != tuple(
            entry.symbol for entry in self.entries
        ):
            raise MarketDataError("materialization entries must be nonempty and sorted")
        if len({entry.symbol for entry in self.entries}) != len(self.entries):
            raise MarketDataError("materialization entries must be unique")
        require_sha256(self.source_partition_sha256, "source_partition_sha256")
        require_sha256(self.inclusion_rule_sha256, "inclusion_rule_sha256")
        require_sha256(
            self.source_lifecycle_coverage_sha256,
            "source_lifecycle_coverage_sha256",
        )
        require_sha256(self.materialization_sha256, "materialization_sha256")
        if self.snapshot.source_partition_sha256 != self.source_partition_sha256:
            raise MarketDataError("snapshot source partition identity mismatch")
        if self.snapshot.inclusion_rule_sha256 != self.inclusion_rule_sha256:
            raise MarketDataError("snapshot inclusion rule identity mismatch")
        if self.snapshot.materialization_sha256 != self.materialization_sha256:
            raise MarketDataError("snapshot materialization identity mismatch")
        expected = hashlib.sha256(_materialization_payload(self)).hexdigest()
        if expected != self.materialization_sha256:
            raise MarketDataError("materialization receipt does not match its contents")

    @property
    def members(self) -> tuple[str, ...]:
        return tuple(entry.symbol for entry in self.entries if entry.included)

    def verify_current_bytes(self) -> None:
        if capture_file_digest(self._source_partition_path)[0] != self.source_partition_sha256:
            raise MarketDataError("source partition no longer matches captured bytes")
        if capture_file_digest(self._inclusion_rule_path)[0] != self.inclusion_rule_sha256:
            raise MarketDataError("inclusion rule no longer matches captured bytes")


def _materialization_payload(materialization: UniverseMaterialization) -> bytes:
    payload = {
        "calendar_identity_sha256": materialization.snapshot.calendar_identity_sha256,
        "effective_session": materialization.snapshot.effective_session.isoformat(),
        "entries": tuple(
            {
                "exclusion_reason": entry.exclusion_reason,
                "included": entry.included,
                "symbol": entry.symbol,
            }
            for entry in materialization.entries
        ),
        "inclusion_rule_sha256": materialization.inclusion_rule_sha256,
        "lifecycle_coverage_sha256": materialization.source_lifecycle_coverage_sha256,
        "market": materialization.snapshot.market,
        "source_capture_receipt_sha256": (
            materialization.snapshot.source_identity.capture_receipt_sha256
        ),
        "source_partition_sha256": materialization.source_partition_sha256,
        "version": 1,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def materialize_universe_partition(
    partition_path: Path,
    *,
    source_identity: SourceIdentity,
    symbol_field: str,
    records_by_symbol: Mapping[str, tuple[StatusEvidence, ...]],
    inclusion_rule_path: Path,
    market: UniverseMarket,
    calendar_identity: CalendarIdentity,
    session: AcceptedSession,
    decision_at: datetime,
) -> UniverseMaterialization:
    """Execute one frozen lifecycle rule across a complete captured partition."""

    cutoff = require_aware_datetime(decision_at, "decision_at")
    if not isinstance(calendar_identity, CalendarIdentity):
        raise MarketDataError("calendar_identity must be a CalendarIdentity")
    if not isinstance(session, AcceptedSession):
        raise MarketDataError("session must be an AcceptedSession")
    try:
        require_trusted_source(source_identity)
    except ValueError as exc:
        raise MarketDataError("universe partition requires a trusted source capture") from exc
    if source_identity.available_at > cutoff:
        raise MarketDataError("universe partition was unavailable at decision_at")
    field_name = require_nonempty_text(symbol_field, "symbol_field")
    raw = capture_file_bytes(partition_path)
    source_sha = hashlib.sha256(raw).hexdigest()
    if source_sha != source_identity.content_sha256:
        raise MarketDataError("source partition bytes do not match source identity")
    if len(raw) != source_identity.capture_byte_count:
        raise MarketDataError("source partition byte count does not match capture receipt")
    try:
        decoded = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MarketDataError("source partition must be UTF-8 JSON") from exc
    if not isinstance(decoded, list) or not decoded:
        raise MarketDataError("source partition must be a nonempty JSON array")
    symbols: list[str] = []
    for row in decoded:
        if not isinstance(row, dict) or field_name not in row:
            raise MarketDataError("every source partition row must contain symbol_field")
        symbols.append(require_nonempty_text(row[field_name], "source symbol"))
    source_symbols = tuple(sorted(symbols))
    if len(set(source_symbols)) != len(source_symbols):
        raise MarketDataError("source partition symbols must be unique")
    if tuple(sorted(records_by_symbol)) != source_symbols:
        raise MarketDataError("lifecycle records must cover every source partition symbol")
    rule_bytes = capture_file_bytes(inclusion_rule_path)
    try:
        rule = json.loads(rule_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MarketDataError("inclusion rule must be UTF-8 JSON") from exc
    if rule != {"include": "lifecycle_eligible", "version": 1}:
        raise MarketDataError("unsupported controlled universe inclusion rule")
    evaluated: dict[str, UniverseDecision] = {}
    for symbol in source_symbols:
        evaluated[symbol] = evaluate_universe(
            symbol,
            session,
            cutoff,
            records_by_symbol[symbol],
            market=market,
        )
    entries = tuple(
        UniverseMaterializationEntry(
            symbol,
            evaluated[symbol].eligible,
            None if evaluated[symbol].eligible else ",".join(evaluated[symbol].reasons),
        )
        for symbol in source_symbols
    )
    members = tuple(entry.symbol for entry in entries if entry.included)
    if not members:
        raise MarketDataError("materialized universe must include at least one symbol")
    lifecycle_sha = lifecycle_coverage_sha256(
        source_symbols,
        session,
        cutoff,
        records_by_symbol,
        market=market,
    )
    rule_sha = hashlib.sha256(rule_bytes).hexdigest()
    provisional = object.__new__(UniverseMaterialization)
    provisional_values = {
        "entries": entries,
        "source_partition_sha256": source_sha,
        "inclusion_rule_sha256": rule_sha,
        "source_lifecycle_coverage_sha256": lifecycle_sha,
    }
    snapshot = UniverseSnapshotIdentity(
        market=market,
        exchange_id=calendar_identity.exchange_id,
        effective_session=session.session_date,
        member_count=len(members),
        ordered_members_sha256=ordered_members_sha256(members),
        lifecycle_coverage_sha256=lifecycle_coverage_sha256(
            members,
            session,
            cutoff,
            {symbol: records_by_symbol[symbol] for symbol in members},
            market=market,
        ),
        inclusion_rule_sha256=rule_sha,
        calendar_identity_sha256=calendar_identity_sha256(calendar_identity),
        source_identity=source_identity,
        source_partition_sha256=source_sha,
        materialization_sha256="0" * 64,
    )
    object.__setattr__(provisional, "snapshot", snapshot)
    for field_name, value in provisional_values.items():
        object.__setattr__(provisional, field_name, value)
    materialization_sha = hashlib.sha256(_materialization_payload(provisional)).hexdigest()
    snapshot = replace(snapshot, materialization_sha256=materialization_sha)
    return UniverseMaterialization(
        entries=entries,
        snapshot=snapshot,
        source_partition_sha256=source_sha,
        inclusion_rule_sha256=rule_sha,
        source_lifecycle_coverage_sha256=lifecycle_sha,
        materialization_sha256=materialization_sha,
        _source_partition_path=partition_path,
        _inclusion_rule_path=inclusion_rule_path,
        _materialization_token=_UNIVERSE_MATERIALIZATION_TOKEN,
    )


def ordered_members_sha256(members: tuple[str, ...]) -> str:
    """Hash one strictly sorted, unique candidate-member tuple."""

    frozen = _members(members)
    encoded = json.dumps(
        frozen,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def lifecycle_coverage_sha256(
    members: tuple[str, ...],
    session: AcceptedSession,
    decision_at: datetime,
    records_by_symbol: Mapping[str, tuple[StatusEvidence, ...]],
    *,
    market: UniverseMarket,
) -> str:
    """Hash selected PIT lifecycle records for the accepted candidate members."""

    frozen = _members(members)
    cutoff = require_aware_datetime(decision_at, "decision_at")
    required_kinds = _required_status_kinds(market)
    selected: list[dict[str, object]] = []
    for symbol in frozen:
        if symbol not in records_by_symbol:
            raise MarketDataError("every universe member requires lifecycle records")
        records = tuple(records_by_symbol[symbol])
        if any(
            not isinstance(record, StatusEvidence) or record.symbol != symbol
            for record in records
        ):
            raise MarketDataError("lifecycle records must match their universe member")
        chosen = _select_status_records(
            symbol,
            session,
            cutoff,
            records,
            required_kinds=required_kinds,
        )
        for kind in required_kinds:
            record = chosen[kind]
            selected.append(
                {
                    "status_id": record.status_id,
                    "symbol": record.symbol,
                    "kind": record.kind,
                    "value": record.value,
                    "effective_from": record.effective_from.isoformat(),
                    "effective_to": (
                        None if record.effective_to is None else record.effective_to.isoformat()
                    ),
                    "exchange_timezone": record.exchange_timezone,
                    "source": _source_payload(record.source),
                }
            )
    payload = {
        "market": market,
        "required_status_kinds": required_kinds,
        "selected_records": selected,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def validate_universe_snapshot(
    identity: UniverseSnapshotIdentity,
    *,
    market: UniverseMarket,
    calendar_identity: CalendarIdentity,
    session: AcceptedSession,
    decision_at: datetime,
    members: tuple[str, ...],
    records_by_symbol: Mapping[str, tuple[StatusEvidence, ...]],
) -> None:
    """Fail closed unless runtime candidates equal the accepted PIT snapshot."""

    if not isinstance(identity, UniverseSnapshotIdentity):
        raise MarketDataError("universe_snapshot must be a UniverseSnapshotIdentity")
    cutoff = require_aware_datetime(decision_at, "decision_at")
    frozen = _members(members)
    if identity.market != market or identity.exchange_id != calendar_identity.exchange_id:
        raise MarketDataError("universe snapshot market or exchange mismatch")
    if identity.calendar_identity_sha256 != calendar_identity_sha256(calendar_identity):
        raise MarketDataError("universe snapshot calendar identity mismatch")
    if identity.effective_session != session.session_date:
        raise MarketDataError("universe snapshot effective_session mismatch")
    if identity.source_identity.available_at > cutoff:
        raise MarketDataError("universe snapshot was unavailable at decision_at")
    if identity.member_count != len(frozen):
        raise MarketDataError("universe snapshot member_count mismatch")
    if identity.ordered_members_sha256 != ordered_members_sha256(frozen):
        raise MarketDataError("universe snapshot ordered_members_sha256 mismatch")
    candidate_records = {symbol: records_by_symbol[symbol] for symbol in frozen}
    lifecycle_hash = lifecycle_coverage_sha256(
        frozen,
        session,
        cutoff,
        candidate_records,
        market=market,
    )
    if identity.lifecycle_coverage_sha256 != lifecycle_hash:
        raise MarketDataError("universe snapshot lifecycle_coverage_sha256 mismatch")


def evaluate_universe(
    symbol: str,
    session: AcceptedSession,
    decision_at: datetime,
    records: tuple[StatusEvidence, ...] | list[StatusEvidence],
    *,
    market: UniverseMarket,
) -> UniverseDecision:
    """Evaluate a symbol from one complete, nonoverlapping PIT status set."""

    symbol = require_nonempty_text(symbol, "symbol")
    if not isinstance(session, AcceptedSession):
        raise MarketDataError("session must be an AcceptedSession")
    cutoff = require_aware_datetime(decision_at, "decision_at")
    if cutoff >= session.open_at:
        raise MarketDataError("decision_at cannot follow or equal the accepted-session open")
    if session.source.available_at > cutoff:
        raise MarketDataError("accepted-session source was unavailable at decision_at")
    frozen = tuple(records)
    required_kinds = _required_status_kinds(market)
    selected = _select_status_records(
        symbol,
        session,
        cutoff,
        frozen,
        required_kinds=required_kinds,
    )

    reasons: list[str] = []
    if not selected["listed"].value:
        reasons.append("not_listed")
    if selected["delisted"].value:
        reasons.append("delisted")
    if "st" in selected and selected["st"].value:
        reasons.append("st")
    if "suspended" in selected and selected["suspended"].value:
        reasons.append("suspended")
    evidence = tuple(
        (kind, selected[kind].status_id, selected[kind].source)
        for kind in required_kinds
    )
    return UniverseDecision(not reasons, tuple(reasons), evidence)


def _select_status_records(
    symbol: str,
    session: AcceptedSession,
    cutoff: datetime,
    frozen: tuple[StatusEvidence, ...],
    *,
    required_kinds: tuple[StatusKind, ...],
) -> dict[StatusKind, StatusEvidence]:
    if any(not isinstance(record, StatusEvidence) for record in frozen):
        raise MarketDataError("records must contain only StatusEvidence values")
    supplied_kinds = {
        record.kind for record in frozen if record.symbol == symbol
    }
    if supplied_kinds - set(required_kinds):
        raise MarketDataError(
            "status records must contain exactly the market-required kinds"
        )
    if any(record.source.available_at > cutoff for record in frozen):
        raise MarketDataError(
            "status records include future evidence unavailable at decision_at"
        )
    global_identities: dict[str, list[StatusEvidence]] = defaultdict(list)
    for record in frozen:
        global_identities[record.status_id].append(record)
    for revisions in global_identities.values():
        identities = {
            (record.symbol, record.kind, record.exchange_timezone)
            for record in revisions
        }
        if len(identities) != 1:
            raise MarketDataError(
                "status revisions must share symbol, kind, and exchange_timezone"
            )

    selected: dict[StatusKind, StatusEvidence] = {}
    for kind in required_kinds:
        candidates = tuple(
            record
            for record in frozen
            if record.symbol == symbol
            and record.kind == kind
        )
        by_status_id: dict[str, list[StatusEvidence]] = defaultdict(list)
        for record in candidates:
            by_status_id[record.status_id].append(record)
        matches: list[StatusEvidence] = []
        for revisions in by_status_id.values():
            if len({record.exchange_timezone for record in revisions}) != 1:
                raise MarketDataError(f"{kind} revisions cannot mix exchange timezones")
            if all(record.source.available_at > cutoff for record in revisions):
                continue
            selected_source = select_source_revision(
                (record.source for record in revisions),
                as_of=cutoff,
            )
            selected_record = next(
                record for record in revisions if record.source == selected_source
            )
            if selected_record.effective_on(session.session_date):
                if selected_record.exchange_timezone != session.exchange_timezone:
                    raise MarketDataError(
                        f"effective {kind} evidence uses a different exchange timezone"
                    )
                matches.append(selected_record)
        if not matches:
            raise MarketDataError(
                f"missing effective {kind} identity available by decision_at"
            )
        if len(matches) != 1:
            raise MarketDataError(f"overlapping effective {kind} identities")
        selected[kind] = matches[0]

    return selected


def _required_status_kinds(market: UniverseMarket) -> tuple[StatusKind, ...]:
    if market == "a_share":
        return ALL_STATUS_KINDS
    if market == "us":
        return US_REQUIRED_STATUS_KINDS
    raise MarketDataError("universe market must be a_share or us")


def _members(members: tuple[str, ...]) -> tuple[str, ...]:
    if type(members) is not tuple or not members:
        raise MarketDataError("universe_members must be a nonempty immutable tuple")
    if any(not isinstance(symbol, str) or not symbol.strip() for symbol in members):
        raise MarketDataError("universe members must be nonempty strings")
    if any(any(ord(character) < 32 for character in symbol) for symbol in members):
        raise MarketDataError("universe members cannot contain C0 control characters")
    if members != tuple(sorted(set(members))):
        raise MarketDataError("universe_members must be sorted and unique")
    return members


def _source_payload(source: SourceIdentity) -> dict[str, object]:
    return {
        "source_url": source.source_url,
        "content_sha256": source.content_sha256,
        "available_at": source.available_at.isoformat(),
        "retrieved_at": source.retrieved_at.isoformat(),
        "revision_id": source.revision_id,
        "source_family_id": source.source_family_id,
        "provider_id": source.provider_id,
        "subject_id": source.subject_id,
        "supersedes_revision_id": source.supersedes_revision_id,
        "capture_receipt_sha256": source.capture_receipt_sha256,
        "publication_evidence_sha256": source.publication_evidence_sha256,
        "url_migration_receipt_sha256": source.url_migration_receipt_sha256,
    }
