"""Offline-first SEC Company Facts point-in-time primitives.

The module deliberately has no network client.  Callers supply hash-pinned raw
Company Facts bytes plus independently obtained filing identities, including the
SEC acceptance timestamp that is absent from the Company Facts response.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
import re
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from .source_identity import (
    CorporateActionIdentity,
    SourceIdentity,
    require_aware_utc,
    require_decimal,
    select_corporate_action_revision,
)


_ACCESSION_RE = re.compile(r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$")
_COMPANY_FACTS_PATH_RE = re.compile(r"^/api/xbrl/companyfacts/CIK([0-9]{10})\.json$")
_SEC_ARCHIVE_HOSTS = frozenset({"sec.gov", "www.sec.gov"})
_NEW_YORK = ZoneInfo("America/New_York")


class SecEdgarDataError(ValueError):
    """Raised when SEC input identity or PIT semantics are incomplete."""


def _normalize_cik(value: object) -> str:
    text = str(value).strip()
    if not text.isdigit() or len(text) > 10:
        raise SecEdgarDataError("CIK must contain at most ten digits")
    return text.zfill(10)


def _parse_date(value: object, field: str, *, optional: bool = False) -> date | None:
    if optional and value in (None, ""):
        return None
    if type(value) is date:
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise SecEdgarDataError(f"invalid {field}") from exc


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SecEdgarDataError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite_constant(value: str) -> None:
    raise SecEdgarDataError(f"non-finite JSON constant is not allowed: {value}")


def _require_archive_url(url: str, cik: str, accession: str) -> None:
    parsed = urlparse(url)
    prefix = f"/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/"
    if (
        parsed.hostname not in _SEC_ARCHIVE_HOSTS
        or not parsed.path.startswith(prefix)
        or parsed.query
    ):
        raise SecEdgarDataError(
            "filing source_url must be a canonical SEC archive URL for its CIK/accession"
        )


@dataclass(frozen=True)
class FilingIdentity:
    """Immutable identity of one original or amended SEC filing."""

    cik: str
    accession: str
    form: str
    filed: date
    acceptance_utc: datetime
    retrieved_at: datetime
    revision: int
    source: SourceIdentity
    supersedes_accession: str | None = None

    def __post_init__(self) -> None:
        cik = _normalize_cik(self.cik)
        accession = str(self.accession).strip()
        form = str(self.form).strip().upper()
        if _ACCESSION_RE.fullmatch(accession) is None:
            raise SecEdgarDataError("accession must use SEC 10-2-6 format")
        if not form:
            raise SecEdgarDataError("form is required")
        if type(self.filed) is not date:
            raise SecEdgarDataError("filed must be a date")
        acceptance = require_aware_utc(self.acceptance_utc, "acceptance_utc")
        retrieved = require_aware_utc(self.retrieved_at, "retrieved_at")
        if acceptance.astimezone(_NEW_YORK).date() != self.filed:
            raise SecEdgarDataError("acceptance_utc must map to filed in America/New_York")
        if retrieved < acceptance:
            raise SecEdgarDataError("retrieved_at cannot precede acceptance_utc")
        if type(self.revision) is not int or self.revision < 1:
            raise SecEdgarDataError("revision must be a positive integer")
        supersedes = self.supersedes_accession
        if supersedes is not None:
            supersedes = str(supersedes).strip()
            if _ACCESSION_RE.fullmatch(supersedes) is None or supersedes == accession:
                raise SecEdgarDataError("supersedes_accession is invalid")
        if (self.revision == 1) != (supersedes is None):
            raise SecEdgarDataError(
                "revision 1 must be original; later revisions must name superseded filing"
            )
        if (self.revision > 1) != form.endswith("/A"):
            raise SecEdgarDataError("later revisions must use an amended form")
        if self.source.available_at != acceptance or self.source.retrieved_at != retrieved:
            raise SecEdgarDataError(
                "filing source availability/retrieval must equal filing timestamps"
            )
        if self.source.revision_id != accession:
            raise SecEdgarDataError("filing source revision_id must equal accession")
        if self.source.supersedes_revision_id != supersedes:
            raise SecEdgarDataError("filing source supersession must equal supersedes_accession")
        _require_archive_url(self.source.source_url, cik, accession)
        object.__setattr__(self, "cik", cik)
        object.__setattr__(self, "accession", accession)
        object.__setattr__(self, "form", form)
        object.__setattr__(self, "acceptance_utc", acceptance)
        object.__setattr__(self, "retrieved_at", retrieved)
        object.__setattr__(self, "supersedes_accession", supersedes)

    @property
    def base_form(self) -> str:
        return self.form.removesuffix("/A")


@dataclass(frozen=True)
class SecFact:
    """One exact fact observation bound to an immutable filing identity."""

    filing: FilingIdentity
    entity_name: str
    taxonomy: str
    concept: str
    unit: str
    value: Decimal
    start: date | None
    end: date
    fiscal_year: int | None = None
    fiscal_period: str | None = None
    frame: str | None = None

    def __post_init__(self) -> None:
        entity_name = str(self.entity_name).strip()
        taxonomy = str(self.taxonomy).strip()
        concept = str(self.concept).strip()
        unit = str(self.unit).strip()
        if not entity_name or not taxonomy or not concept or not unit:
            raise SecEdgarDataError("entity_name, taxonomy, concept, and unit are required")
        value = require_decimal(self.value, "fact value")
        if type(self.end) is not date or (self.start is not None and type(self.start) is not date):
            raise SecEdgarDataError("fact period dates must be dates")
        if self.start is not None and self.start > self.end:
            raise SecEdgarDataError("fact start cannot follow end")
        if self.fiscal_year is not None and (
            type(self.fiscal_year) is not int or self.fiscal_year < 1900
        ):
            raise SecEdgarDataError("fiscal_year is invalid")
        fiscal_period = (
            None if self.fiscal_period in (None, "") else str(self.fiscal_period).strip().upper()
        )
        frame = None if self.frame in (None, "") else str(self.frame).strip()
        object.__setattr__(self, "entity_name", entity_name)
        object.__setattr__(self, "taxonomy", taxonomy)
        object.__setattr__(self, "concept", concept)
        object.__setattr__(self, "unit", unit)
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "fiscal_period", fiscal_period)
        object.__setattr__(self, "frame", frame)

    @property
    def cik(self) -> str:
        return self.filing.cik

    @property
    def accession(self) -> str:
        return self.filing.accession

    @property
    def form(self) -> str:
        return self.filing.form

    @property
    def filed(self) -> date:
        return self.filing.filed

    @property
    def acceptance_utc(self) -> datetime:
        return self.filing.acceptance_utc

    @property
    def retrieved_at(self) -> datetime:
        return self.filing.retrieved_at

    @property
    def source_url(self) -> str:
        return self.filing.source.source_url

    @property
    def content_sha256(self) -> str:
        return self.filing.source.content_sha256

    @property
    def revision(self) -> int:
        return self.filing.revision

    @property
    def period_identity(self) -> tuple[object, ...]:
        return (
            self.cik,
            self.taxonomy,
            self.concept,
            self.unit,
            self.start,
            self.end,
            self.filing.base_form,
        )


@dataclass(frozen=True)
class CompanyFactsSnapshot:
    cik: str
    entity_name: str
    source: SourceIdentity
    facts: tuple[SecFact, ...]

    def __post_init__(self) -> None:
        cik = _normalize_cik(self.cik)
        entity_name = str(self.entity_name).strip()
        facts = tuple(self.facts)
        if not entity_name or not facts:
            raise SecEdgarDataError("snapshot entity_name and facts are required")
        if any(fact.cik != cik or fact.entity_name != entity_name for fact in facts):
            raise SecEdgarDataError("snapshot facts must match its CIK and entity_name")
        if self.source.available_at < max(fact.acceptance_utc for fact in facts):
            raise SecEdgarDataError(
                "snapshot available_at cannot precede a contained filing acceptance"
            )
        object.__setattr__(self, "cik", cik)
        object.__setattr__(self, "entity_name", entity_name)
        object.__setattr__(self, "facts", facts)


@dataclass(frozen=True)
class PointInTimeRatio:
    accepted_at: datetime
    period_start: date | None
    period_end: date
    value: Decimal
    numerator_accession: str
    denominator_accession: str
    numerator_revision: int
    denominator_revision: int
    numerator_unit: str
    denominator_unit: str
    unit: str = field(default="1", init=False)


def _validate_filing_chain(
    filings: Sequence[FilingIdentity], cik: str
) -> dict[str, FilingIdentity]:
    by_accession: dict[str, FilingIdentity] = {}
    successors: dict[str, list[FilingIdentity]] = defaultdict(list)
    for filing in filings:
        if filing.cik != cik:
            raise SecEdgarDataError("all filing identities must match the payload CIK")
        if filing.accession in by_accession:
            raise SecEdgarDataError("filing accessions must be unique")
        by_accession[filing.accession] = filing
    for filing in filings:
        if filing.revision == 1:
            continue
        prior = by_accession.get(filing.supersedes_accession or "")
        if prior is None:
            raise SecEdgarDataError("revision chain references a missing filing")
        if (
            prior.revision != filing.revision - 1
            or prior.base_form != filing.base_form
            or prior.acceptance_utc >= filing.acceptance_utc
        ):
            raise SecEdgarDataError("revision chain is not monotonic and unambiguous")
        assert filing.supersedes_accession is not None
        successors[filing.supersedes_accession].append(filing)
    if any(len(children) > 1 for children in successors.values()):
        raise SecEdgarDataError("revision chain is globally branched")
    return by_accession


def _validate_observed_filing_relationships(facts: Iterable[SecFact]) -> None:
    """Reject branching in a fact subset without requiring omitted parent facts."""

    filings: dict[tuple[str, str], FilingIdentity] = {}
    successors: dict[tuple[str, str], set[str]] = defaultdict(set)
    for fact in facts:
        key = (fact.cik, fact.accession)
        existing = filings.setdefault(key, fact.filing)
        if existing != fact.filing:
            raise SecEdgarDataError("one filing accession has conflicting identities")
        parent = fact.filing.supersedes_accession
        if parent is not None:
            successors[(fact.cik, parent)].add(fact.accession)
    if any(len(children) > 1 for children in successors.values()):
        raise SecEdgarDataError("revision chain is globally branched")
    for (cik, _accession), filing in filings.items():
        parent_accession = filing.supersedes_accession
        if parent_accession is None:
            continue
        parent = filings.get((cik, parent_accession))
        if parent is not None and (
            parent.revision != filing.revision - 1
            or parent.base_form != filing.base_form
            or parent.acceptance_utc >= filing.acceptance_utc
        ):
            raise SecEdgarDataError("revision chain is not monotonic and unambiguous")


def normalize_companyfacts_payload(
    raw_bytes: bytes,
    *,
    snapshot_source: SourceIdentity,
    filing_identities: Sequence[FilingIdentity],
    expected_cik: str | None = None,
) -> CompanyFactsSnapshot:
    """Normalize hash-pinned SEC Company Facts bytes without I/O or network access."""

    if not isinstance(raw_bytes, bytes) or not raw_bytes:
        raise SecEdgarDataError("raw Company Facts bytes are required")
    if hashlib.sha256(raw_bytes).hexdigest() != snapshot_source.content_sha256:
        raise SecEdgarDataError("Company Facts content SHA-256 mismatch")
    try:
        payload = json.loads(
            raw_bytes,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_nonfinite_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SecEdgarDataError("Company Facts payload is not valid strict JSON") from exc
    if not isinstance(payload, Mapping):
        raise SecEdgarDataError("Company Facts root must be an object")
    cik = _normalize_cik(payload.get("cik"))
    if expected_cik is not None and cik != _normalize_cik(expected_cik):
        raise SecEdgarDataError("payload CIK does not match expected_cik")
    entity_name = str(payload.get("entityName", "")).strip()
    if not entity_name:
        raise SecEdgarDataError("entityName is required")
    parsed_snapshot_url = urlparse(snapshot_source.source_url)
    match = _COMPANY_FACTS_PATH_RE.fullmatch(parsed_snapshot_url.path)
    if (
        parsed_snapshot_url.hostname != "data.sec.gov"
        or match is None
        or match.group(1) != cik
        or parsed_snapshot_url.query
    ):
        raise SecEdgarDataError(
            "snapshot source_url must be the canonical SEC Company Facts URL for its CIK"
        )
    filings = _validate_filing_chain(tuple(filing_identities), cik)
    if not filings:
        raise SecEdgarDataError("filing identities are required")

    facts_root = payload.get("facts")
    if not isinstance(facts_root, Mapping) or not facts_root:
        raise SecEdgarDataError("facts must be a non-empty object")
    facts: list[SecFact] = []
    seen: set[tuple[object, ...]] = set()
    for taxonomy, concepts in facts_root.items():
        if not str(taxonomy).strip() or not isinstance(concepts, Mapping):
            raise SecEdgarDataError("taxonomy entries must be named objects")
        for concept, concept_data in concepts.items():
            if not str(concept).strip() or not isinstance(concept_data, Mapping):
                raise SecEdgarDataError("concept entries must be named objects")
            units = concept_data.get("units")
            if not isinstance(units, Mapping) or not units:
                raise SecEdgarDataError("concept units must be a non-empty object")
            for unit, observations in units.items():
                if not str(unit).strip() or not isinstance(observations, list) or not observations:
                    raise SecEdgarDataError("unit observations must be a non-empty list")
                for observation in observations:
                    if not isinstance(observation, Mapping):
                        raise SecEdgarDataError("fact observation must be an object")
                    accession = str(observation.get("accn", "")).strip()
                    filing = filings.get(accession)
                    if filing is None:
                        raise SecEdgarDataError(
                            "every observation requires an accepted filing identity"
                        )
                    form = str(observation.get("form", "")).strip().upper()
                    filed = _parse_date(observation.get("filed"), "filed")
                    if form != filing.form or filed != filing.filed:
                        raise SecEdgarDataError(
                            "observation form/filed does not match its filing identity"
                        )
                    start = _parse_date(observation.get("start"), "start", optional=True)
                    end = _parse_date(observation.get("end"), "end")
                    assert end is not None
                    duplicate_key = (
                        str(taxonomy),
                        str(concept),
                        str(unit),
                        start,
                        end,
                        accession,
                    )
                    if duplicate_key in seen:
                        raise SecEdgarDataError("duplicate fact observation is ambiguous")
                    seen.add(duplicate_key)
                    fiscal_year_raw = observation.get("fy")
                    if fiscal_year_raw in (None, ""):
                        fiscal_year = None
                    elif type(fiscal_year_raw) is int:
                        fiscal_year = fiscal_year_raw
                    else:
                        raise SecEdgarDataError("fiscal year must be an integer")
                    facts.append(
                        SecFact(
                            filing=filing,
                            entity_name=entity_name,
                            taxonomy=str(taxonomy),
                            concept=str(concept),
                            unit=str(unit),
                            value=require_decimal(observation.get("val"), "fact value"),
                            start=start,
                            end=end,
                            fiscal_year=fiscal_year,
                            fiscal_period=observation.get("fp"),
                            frame=observation.get("frame"),
                        )
                    )
    if not facts:
        raise SecEdgarDataError("payload contains no fact observations")
    facts.sort(
        key=lambda fact: (
            fact.taxonomy,
            fact.concept,
            fact.unit,
            fact.end,
            fact.acceptance_utc,
            fact.revision,
        )
    )
    return CompanyFactsSnapshot(
        cik=cik,
        entity_name=entity_name,
        source=snapshot_source,
        facts=tuple(facts),
    )


def select_facts_as_of(
    facts: Iterable[SecFact],
    *,
    as_of: datetime,
) -> tuple[SecFact, ...]:
    """Return the latest unambiguous accepted revision for each economic period."""

    cutoff = require_aware_utc(as_of, "as_of")
    frozen = tuple(facts)
    _validate_observed_filing_relationships(frozen)
    grouped: dict[tuple[object, ...], list[SecFact]] = defaultdict(list)
    for fact in frozen:
        if fact.acceptance_utc <= cutoff:
            grouped[fact.period_identity].append(fact)
    selected: list[SecFact] = []
    for period, revisions in grouped.items():
        ordered = sorted(revisions, key=lambda item: (item.acceptance_utc, item.accession))
        for earlier, later in zip(ordered, ordered[1:]):
            if earlier.acceptance_utc == later.acceptance_utc:
                raise SecEdgarDataError(f"ambiguous equal-time revisions for period {period}")
        selected.append(ordered[-1])
    return tuple(
        sorted(
            selected,
            key=lambda fact: (fact.end, fact.taxonomy, fact.concept, fact.unit),
        )
    )


def build_pit_ratios(
    numerator_facts: Iterable[SecFact],
    denominator_facts: Iterable[SecFact],
) -> tuple[PointInTimeRatio, ...]:
    """Build filing-time ratios without using denominator revisions from the future."""

    numerators = tuple(numerator_facts)
    denominators = tuple(denominator_facts)
    _validate_observed_filing_relationships((*numerators, *denominators))
    if len({fact.concept for fact in numerators}) != 1:
        raise SecEdgarDataError("numerator facts must contain exactly one concept")
    if len({fact.concept for fact in denominators}) != 1:
        raise SecEdgarDataError("denominator facts must contain exactly one concept")
    results: list[PointInTimeRatio] = []
    for numerator in sorted(numerators, key=lambda fact: fact.acceptance_utc):
        period_candidates = tuple(
            fact
            for fact in denominators
            if fact.cik == numerator.cik
            and (
                fact.start is None
                or (numerator.start is not None and fact.start == numerator.start)
            )
            and fact.end == numerator.end
            and fact.filing.base_form == numerator.filing.base_form
        )
        if not period_candidates:
            raise SecEdgarDataError("ratio denominator period is missing")
        same_unit = tuple(fact for fact in period_candidates if fact.unit == numerator.unit)
        if not same_unit:
            raise SecEdgarDataError("ratio units do not match exactly")
        eligible = select_facts_as_of(same_unit, as_of=numerator.acceptance_utc)
        if len(eligible) != 1:
            raise SecEdgarDataError("ratio denominator is unavailable or ambiguous")
        denominator = eligible[0]
        if denominator.value == 0:
            raise SecEdgarDataError("ratio denominator cannot be zero")
        value = numerator.value / denominator.value
        if not value.is_finite():
            raise SecEdgarDataError("ratio result must be finite")
        results.append(
            PointInTimeRatio(
                accepted_at=numerator.acceptance_utc,
                period_start=numerator.start,
                period_end=numerator.end,
                value=value,
                numerator_accession=numerator.accession,
                denominator_accession=denominator.accession,
                numerator_revision=numerator.revision,
                denominator_revision=denominator.revision,
                numerator_unit=numerator.unit,
                denominator_unit=denominator.unit,
            )
        )
    return tuple(results)


def adjust_share_fact_for_splits(
    fact: SecFact,
    *,
    as_of: datetime,
    split_events: Iterable[CorporateActionIdentity],
) -> Decimal:
    """Translate an accepted share fact onto the known split basis at ``as_of``."""

    cutoff = require_aware_utc(as_of, "as_of")
    if fact.unit.lower() not in {"share", "shares"}:
        raise SecEdgarDataError("split adjustment requires a shares unit")
    if fact.value < 0:
        raise SecEdgarDataError("share fact cannot be negative")
    if fact.acceptance_utc > cutoff:
        raise SecEdgarDataError("share fact was not accepted at as_of")
    by_action_id: dict[str, list[CorporateActionIdentity]] = defaultdict(list)
    for event in split_events:
        if event.action_type not in {"split", "reverse_split"}:
            raise SecEdgarDataError("split_events may contain only split actions")
        if event.subject_id != fact.cik:
            raise SecEdgarDataError("split subject_id must match fact CIK")
        by_action_id[event.action_id].append(event)
    selected_events: list[CorporateActionIdentity] = []
    for revisions in by_action_id.values():
        if not any(event.source.available_at <= cutoff for event in revisions):
            continue
        try:
            event = select_corporate_action_revision(revisions, as_of=cutoff)
        except ValueError as exc:
            raise SecEdgarDataError("invalid split source revision chain") from exc
        if event.effective_at > cutoff:
            continue
        if event.effective_date <= fact.end:
            continue
        selected_events.append(event)
    adjusted = fact.value
    for event in sorted(
        selected_events,
        key=lambda item: (item.effective_at, item.action_id),
    ):
        assert event.split_ratio is not None
        adjusted *= event.split_ratio
    if not adjusted.is_finite():
        raise SecEdgarDataError("split-adjusted value must be finite")
    return adjusted


__all__ = [
    "CompanyFactsSnapshot",
    "FilingIdentity",
    "PointInTimeRatio",
    "SecEdgarDataError",
    "SecFact",
    "adjust_share_fact_for_splits",
    "build_pit_ratios",
    "normalize_companyfacts_payload",
    "select_facts_as_of",
]
