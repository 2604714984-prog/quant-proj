from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json

import pytest

from quant_system.data.sec_edgar import (
    FilingIdentity,
    SecEdgarDataError,
    adjust_share_fact_for_splits,
    build_pit_ratios,
    normalize_companyfacts_payload,
    select_facts_as_of,
)
from quant_system.data.source_identity import (
    CorporateActionIdentity,
    SourceIdentity,
    SourceIdentityError,
    select_corporate_action_revision,
)


CIK = "0000000001"
ORIGINAL = "0000000001-24-000001"
AMENDMENT = "0000000001-24-000002"
UTC = timezone.utc


def _source(
    url: str,
    content: bytes,
    available_at: datetime,
    retrieved_at: datetime,
    revision_id: str,
    supersedes_revision_id: str | None = None,
) -> SourceIdentity:
    return SourceIdentity(
        source_url=url,
        content_sha256=hashlib.sha256(content).hexdigest(),
        available_at=available_at,
        retrieved_at=retrieved_at,
        revision_id=revision_id,
        supersedes_revision_id=supersedes_revision_id,
    )


def _filings() -> tuple[FilingIdentity, FilingIdentity]:
    accepted_original = datetime(2024, 2, 15, 22, tzinfo=UTC)
    accepted_amendment = datetime(2024, 4, 15, 20, 30, tzinfo=UTC)
    retrieved = datetime(2024, 7, 1, 12, tzinfo=UTC)
    original = FilingIdentity(
        cik=CIK,
        accession=ORIGINAL,
        form="10-K",
        filed=date(2024, 2, 15),
        acceptance_utc=accepted_original,
        retrieved_at=retrieved,
        revision=1,
        source=_source(
            f"https://www.sec.gov/Archives/edgar/data/1/{ORIGINAL.replace('-', '')}/facts.json",
            b"original-filing",
            accepted_original,
            retrieved,
            ORIGINAL,
        ),
    )
    amendment = FilingIdentity(
        cik=CIK,
        accession=AMENDMENT,
        form="10-K/A",
        filed=date(2024, 4, 15),
        acceptance_utc=accepted_amendment,
        retrieved_at=retrieved,
        revision=2,
        supersedes_accession=ORIGINAL,
        source=_source(
            f"https://www.sec.gov/Archives/edgar/data/1/{AMENDMENT.replace('-', '')}/facts.json",
            b"amended-filing",
            accepted_amendment,
            retrieved,
            AMENDMENT,
            ORIGINAL,
        ),
    )
    return original, amendment


def _branched_amendment(original: FilingIdentity) -> FilingIdentity:
    accession = "0000000001-24-000003"
    accepted = datetime(2024, 5, 15, 20, 30, tzinfo=UTC)
    return FilingIdentity(
        cik=CIK,
        accession=accession,
        form="10-K/A",
        filed=date(2024, 5, 15),
        acceptance_utc=accepted,
        retrieved_at=original.retrieved_at,
        revision=2,
        supersedes_accession=ORIGINAL,
        source=_source(
            f"https://www.sec.gov/Archives/edgar/data/1/{accession.replace('-', '')}/facts.json",
            b"branched-amendment",
            accepted,
            original.retrieved_at,
            accession,
            ORIGINAL,
        ),
    )


def _payload() -> bytes:
    observations = {
        "Revenue": [
            ("50", ORIGINAL, "10-K", "2024-02-15"),
            ("60", AMENDMENT, "10-K/A", "2024-04-15"),
        ],
        "Assets": [
            ("100", ORIGINAL, "10-K", "2024-02-15"),
            ("600", AMENDMENT, "10-K/A", "2024-04-15"),
        ],
        "Shares": [
            ("10", ORIGINAL, "10-K", "2024-02-15"),
            ("10", AMENDMENT, "10-K/A", "2024-04-15"),
        ],
    }
    facts: dict[str, object] = {}
    for concept, rows in observations.items():
        unit = "shares" if concept == "Shares" else "USD"
        facts[concept] = {
            "units": {
                unit: [
                    {
                        "start": "2023-01-01",
                        "end": "2023-12-31",
                        "val": value,
                        "accn": accession,
                        "fy": 2023,
                        "fp": "FY",
                        "form": form,
                        "filed": filed,
                    }
                    for value, accession, form, filed in rows
                ]
            }
        }
    return json.dumps(
        {"cik": 1, "entityName": "Example Corp", "facts": {"us-gaap": facts}},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def _snapshot():
    raw = _payload()
    retrieved = datetime(2024, 7, 1, 12, tzinfo=UTC)
    source = _source(
        f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json",
        raw,
        retrieved,
        retrieved,
        "companyfacts-20240701",
    )
    return normalize_companyfacts_payload(
        raw,
        snapshot_source=source,
        filing_identities=_filings(),
        expected_cik=CIK,
    )


def test_companyfacts_normalization_preserves_filing_identity_and_is_immutable() -> None:
    snapshot = _snapshot()

    assert snapshot.cik == CIK
    assert len(snapshot.facts) == 6
    amendment = next(
        fact for fact in snapshot.facts if fact.concept == "Revenue" and fact.revision == 2
    )
    assert amendment.accession == AMENDMENT
    assert amendment.form == "10-K/A"
    assert amendment.acceptance_utc == datetime(2024, 4, 15, 20, 30, tzinfo=UTC)
    assert amendment.content_sha256 == hashlib.sha256(b"amended-filing").hexdigest()
    assert not hasattr(snapshot, "raw_bytes")
    with pytest.raises(FrozenInstanceError):
        amendment.value = Decimal("999")  # type: ignore[misc]


def test_as_of_selection_switches_only_at_timezone_aware_acceptance() -> None:
    facts = _snapshot().facts
    before = select_facts_as_of(
        facts,
        as_of=datetime(2024, 4, 15, 20, 29, 59, tzinfo=UTC),
    )
    after = select_facts_as_of(
        facts,
        as_of=datetime(2024, 4, 15, 20, 30, tzinfo=UTC),
    )

    assert {fact.revision for fact in before} == {1}
    assert {fact.revision for fact in after} == {2}
    with pytest.raises(SourceIdentityError, match="timezone-aware"):
        select_facts_as_of(facts, as_of=datetime(2024, 4, 15, 20, 30))


def test_pit_ratio_does_not_use_later_denominator_revision() -> None:
    facts = _snapshot().facts
    ratios = build_pit_ratios(
        (fact for fact in facts if fact.concept == "Revenue"),
        (fact for fact in facts if fact.concept == "Assets"),
    )

    assert [(ratio.value, ratio.denominator_revision) for ratio in ratios] == [
        (Decimal("0.5"), 1),
        (Decimal("0.1"), 2),
    ]
    assert all(ratio.unit == "1" for ratio in ratios)
    assert all(ratio.numerator_unit == "USD" for ratio in ratios)
    assert all(ratio.denominator_unit == "USD" for ratio in ratios)


def test_pit_ratio_fails_closed_on_units_missing_period_and_zero() -> None:
    facts = _snapshot().facts
    numerator = next(fact for fact in facts if fact.concept == "Revenue" and fact.revision == 1)
    denominator = next(fact for fact in facts if fact.concept == "Assets" and fact.revision == 1)
    with pytest.raises(SecEdgarDataError, match="units"):
        build_pit_ratios((numerator,), (replace(denominator, unit="EUR"),))
    with pytest.raises(SecEdgarDataError, match="period"):
        build_pit_ratios(
            (numerator,),
            (
                replace(
                    denominator,
                    start=date(2022, 1, 1),
                    end=date(2022, 12, 31),
                ),
            ),
        )
    with pytest.raises(SecEdgarDataError, match="zero"):
        build_pit_ratios((numerator,), (replace(denominator, value=Decimal("0")),))
    instant_denominator = replace(denominator, start=None)
    instant_ratio = build_pit_ratios((numerator,), (instant_denominator,))[0]
    assert instant_ratio.value == Decimal("0.5")
    assert instant_ratio.unit == "1"


@pytest.mark.parametrize("branch_side", ["numerator", "denominator"])
def test_pit_ratio_rejects_branched_input_graphs(branch_side: str) -> None:
    facts = _snapshot().facts
    original, _amendment = _filings()
    branch = _branched_amendment(original)
    numerators = tuple(fact for fact in facts if fact.concept == "Revenue")
    denominators = tuple(fact for fact in facts if fact.concept == "Assets")
    if branch_side == "numerator":
        numerators = (
            *numerators,
            replace(numerators[0], filing=branch, value=Decimal("58")),
        )
    else:
        denominators = (
            *denominators,
            replace(denominators[0], filing=branch, value=Decimal("580")),
        )

    with pytest.raises(SecEdgarDataError, match="globally branched"):
        build_pit_ratios(numerators, denominators)


def test_pit_ratio_rejects_branch_split_across_numerator_and_denominator() -> None:
    facts = _snapshot().facts
    original, _amendment = _filings()
    branch = _branched_amendment(original)
    revenues = tuple(fact for fact in facts if fact.concept == "Revenue")
    original_asset = next(fact for fact in facts if fact.concept == "Assets" and fact.revision == 1)
    branched_asset = replace(original_asset, filing=branch, value=Decimal("580"))

    with pytest.raises(SecEdgarDataError, match="globally branched"):
        build_pit_ratios(revenues, (original_asset, branched_asset))


def test_companyfacts_rejects_hash_url_missing_identity_and_duplicate_json() -> None:
    raw = _payload()
    retrieved = datetime(2024, 7, 1, 12, tzinfo=UTC)
    good_source = _source(
        f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json",
        raw,
        retrieved,
        retrieved,
        "snapshot",
    )
    with pytest.raises(SecEdgarDataError, match="SHA-256"):
        normalize_companyfacts_payload(
            raw + b" ",
            snapshot_source=good_source,
            filing_identities=_filings(),
        )
    wrong_url_source = replace(
        good_source,
        source_url="https://data.sec.gov/api/xbrl/companyfacts/CIK0000000002.json",
    )
    with pytest.raises(SecEdgarDataError, match="canonical SEC Company Facts"):
        normalize_companyfacts_payload(
            raw,
            snapshot_source=wrong_url_source,
            filing_identities=_filings(),
        )
    with pytest.raises(SecEdgarDataError, match="accepted filing identity"):
        normalize_companyfacts_payload(
            raw,
            snapshot_source=good_source,
            filing_identities=(_filings()[0],),
        )

    duplicate = b'{"cik":1,"cik":1,"entityName":"X","facts":{}}'
    duplicate_source = _source(
        f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json",
        duplicate,
        retrieved,
        retrieved,
        "duplicate",
    )
    with pytest.raises(SecEdgarDataError, match="duplicate JSON key"):
        normalize_companyfacts_payload(
            duplicate,
            snapshot_source=duplicate_source,
            filing_identities=_filings(),
        )


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_companyfacts_rejects_nonfinite_json_constants(constant: str) -> None:
    raw = _payload().replace(b'"val":"50"', f'"val":{constant}'.encode(), 1)
    retrieved = datetime(2024, 7, 1, 12, tzinfo=UTC)
    source = _source(
        f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json",
        raw,
        retrieved,
        retrieved,
        f"nonfinite-{constant}",
    )
    with pytest.raises(SecEdgarDataError, match="non-finite JSON constant"):
        normalize_companyfacts_payload(
            raw,
            snapshot_source=source,
            filing_identities=_filings(),
        )


def test_snapshot_available_at_cannot_precede_any_contained_filing() -> None:
    raw = _payload()
    source = _source(
        f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json",
        raw,
        datetime(2024, 3, 1, tzinfo=UTC),
        datetime(2024, 7, 1, 12, tzinfo=UTC),
        "premature-snapshot",
    )
    with pytest.raises(SecEdgarDataError, match="contained filing acceptance"):
        normalize_companyfacts_payload(
            raw,
            snapshot_source=source,
            filing_identities=_filings(),
        )
    snapshot = _snapshot()
    with pytest.raises(SecEdgarDataError, match="contained filing acceptance"):
        replace(
            snapshot,
            source=replace(
                snapshot.source,
                available_at=datetime(2024, 3, 1, tzinfo=UTC),
            ),
        )


def test_unreferenced_later_filing_does_not_change_snapshot_availability() -> None:
    raw = _payload()
    snapshot_time = datetime(2024, 7, 1, 12, tzinfo=UTC)
    source = _source(
        f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json",
        raw,
        snapshot_time,
        snapshot_time,
        "snapshot-with-extra-registry-identity",
    )
    accession = "0000000001-24-000004"
    accepted = datetime(2024, 8, 1, 20, tzinfo=UTC)
    retrieved = datetime(2024, 8, 2, tzinfo=UTC)
    unreferenced = FilingIdentity(
        cik=CIK,
        accession=accession,
        form="8-K",
        filed=date(2024, 8, 1),
        acceptance_utc=accepted,
        retrieved_at=retrieved,
        revision=1,
        source=_source(
            f"https://www.sec.gov/Archives/edgar/data/1/{accession.replace('-', '')}/filing.htm",
            b"unreferenced-filing",
            accepted,
            retrieved,
            accession,
        ),
    )

    snapshot = normalize_companyfacts_payload(
        raw,
        snapshot_source=source,
        filing_identities=(*_filings(), unreferenced),
    )

    assert len(snapshot.facts) == 6


def test_filing_identity_rejects_naive_availability_bad_archive_and_broken_chain() -> None:
    original, amendment = _filings()
    with pytest.raises(SourceIdentityError, match="timezone-aware"):
        replace(original.source, available_at=datetime(2024, 2, 15, 22))
    with pytest.raises(SecEdgarDataError, match="canonical SEC archive"):
        replace(
            original,
            source=replace(original.source, source_url="https://example.com/facts.json"),
        )
    with pytest.raises(SecEdgarDataError, match="canonical SEC archive"):
        replace(
            original,
            source=replace(
                original.source,
                source_url=f"{original.source.source_url}?download=1",
            ),
        )
    with pytest.raises(SecEdgarDataError, match="missing filing"):
        raw = _payload()
        retrieved = datetime(2024, 7, 1, 12, tzinfo=UTC)
        normalize_companyfacts_payload(
            raw,
            snapshot_source=_source(
                f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json",
                raw,
                retrieved,
                retrieved,
                "snapshot",
            ),
            filing_identities=(amendment,),
        )


def test_equal_acceptance_or_nonfinite_fact_is_rejected() -> None:
    original, _amendment = _filings()
    competing_accession = "0000000001-24-000003"
    competing = FilingIdentity(
        cik=CIK,
        accession=competing_accession,
        form="10-K",
        filed=original.filed,
        acceptance_utc=original.acceptance_utc,
        retrieved_at=original.retrieved_at,
        revision=1,
        source=_source(
            f"https://www.sec.gov/Archives/edgar/data/1/{competing_accession.replace('-', '')}/facts.json",
            b"competing",
            original.acceptance_utc,
            original.retrieved_at,
            competing_accession,
        ),
    )
    revenue = next(
        fact for fact in _snapshot().facts if fact.concept == "Revenue" and fact.revision == 1
    )
    with pytest.raises(SecEdgarDataError, match="equal-time"):
        select_facts_as_of(
            (revenue, replace(revenue, filing=competing, value=Decimal("55"))),
            as_of=original.acceptance_utc,
        )
    with pytest.raises(SourceIdentityError, match="finite"):
        replace(revenue, value=Decimal("NaN"))


def test_later_original_comparative_fact_is_selected_without_amendment_chain() -> None:
    revenue = next(
        fact for fact in _snapshot().facts if fact.concept == "Revenue" and fact.revision == 1
    )
    accession = "0000000001-25-000001"
    accepted = datetime(2025, 2, 14, 22, tzinfo=UTC)
    retrieved = datetime(2025, 2, 15, tzinfo=UTC)
    later_original = FilingIdentity(
        cik=CIK,
        accession=accession,
        form="10-K",
        filed=date(2025, 2, 14),
        acceptance_utc=accepted,
        retrieved_at=retrieved,
        revision=1,
        source=_source(
            f"https://www.sec.gov/Archives/edgar/data/1/{accession.replace('-', '')}/facts.json",
            b"later-comparative-filing",
            accepted,
            retrieved,
            accession,
        ),
    )
    comparative = replace(revenue, filing=later_original, value=Decimal("52"))

    selected = select_facts_as_of((revenue, comparative), as_of=accepted)

    assert selected == (comparative,)


def test_globally_branched_filing_chain_is_rejected() -> None:
    original, amendment = _filings()
    branch = _branched_amendment(original)
    raw = _payload()
    snapshot_source = _source(
        f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json",
        raw,
        original.retrieved_at,
        original.retrieved_at,
        "branched-snapshot",
    )
    with pytest.raises(SecEdgarDataError, match="globally branched"):
        normalize_companyfacts_payload(
            raw,
            snapshot_source=snapshot_source,
            filing_identities=(original, amendment, branch),
        )

    revenues = tuple(fact for fact in _snapshot().facts if fact.concept == "Revenue")
    with pytest.raises(SecEdgarDataError, match="globally branched"):
        select_facts_as_of(
            (*revenues, replace(revenues[0], filing=branch, value=Decimal("58"))),
            as_of=branch.acceptance_utc,
        )


def test_split_adjustment_uses_latest_known_source_revision() -> None:
    shares = next(
        fact for fact in _snapshot().facts if fact.concept == "Shares" and fact.revision == 1
    )
    available = datetime(2024, 5, 1, 12, tzinfo=UTC)
    effective = datetime(2024, 6, 1, 13, 30, tzinfo=UTC)
    retrieved = datetime(2024, 7, 1, 12, tzinfo=UTC)
    event = CorporateActionIdentity(
        subject_id=CIK,
        action_id="split-20240601",
        action_type="split",
        effective_at=effective,
        source=_source(
            "https://www.sec.gov/Archives/edgar/data/1/000000000124000001/split.htm",
            b"split",
            available,
            retrieved,
            "split-v1",
        ),
        exchange_timezone="America/New_York",
        ex_date=date(2024, 6, 1),
        split_ratio=Decimal("2"),
    )

    assert adjust_share_fact_for_splits(
        shares,
        as_of=datetime(2024, 5, 31, 23, tzinfo=UTC),
        split_events=(event,),
    ) == Decimal("10")
    assert adjust_share_fact_for_splits(
        shares,
        as_of=datetime(2024, 6, 2, tzinfo=UTC),
        split_events=(event,),
    ) == Decimal("20")
    late_identity = replace(
        event,
        source=replace(
            event.source,
            available_at=datetime(2024, 6, 3, tzinfo=UTC),
        ),
    )
    assert adjust_share_fact_for_splits(
        shares,
        as_of=datetime(2024, 6, 2, tzinfo=UTC),
        split_events=(late_identity,),
    ) == Decimal("10")

    revised = replace(
        event,
        split_ratio=Decimal("3"),
        source=_source(
            event.source.source_url,
            b"split-revised",
            datetime(2024, 6, 2, 12, tzinfo=UTC),
            retrieved,
            "split-v2",
            "split-v1",
        ),
    )
    assert (
        select_corporate_action_revision(
            (event, revised),
            as_of=datetime(2024, 6, 2, 11, 59, tzinfo=UTC),
        )
        == event
    )
    assert (
        select_corporate_action_revision(
            (event, revised),
            as_of=datetime(2024, 6, 2, 12, tzinfo=UTC),
        )
        == revised
    )
    assert adjust_share_fact_for_splits(
        shares,
        as_of=datetime(2024, 6, 2, 11, 59, tzinfo=UTC),
        split_events=(event, revised),
    ) == Decimal("20")
    assert adjust_share_fact_for_splits(
        shares,
        as_of=datetime(2024, 6, 2, 12, tzinfo=UTC),
        split_events=(event, revised),
    ) == Decimal("30")
    with pytest.raises(SourceIdentityError, match="timezone"):
        select_corporate_action_revision(
            (event, replace(revised, exchange_timezone="UTC")),
            as_of=datetime(2024, 6, 2, 12, tzinfo=UTC),
        )

    branch = replace(
        revised,
        split_ratio=Decimal("4"),
        source=_source(
            event.source.source_url,
            b"split-branch",
            datetime(2024, 6, 2, 13, tzinfo=UTC),
            retrieved,
            "split-v2-branch",
            "split-v1",
        ),
    )
    with pytest.raises(SecEdgarDataError, match="source revision chain"):
        adjust_share_fact_for_splits(
            shares,
            as_of=datetime(2024, 6, 3, tzinfo=UTC),
            split_events=(event, revised, branch),
        )


def test_split_boundary_uses_exchange_local_effective_date() -> None:
    shares = next(
        fact for fact in _snapshot().facts if fact.concept == "Shares" and fact.revision == 1
    )
    source = _source(
        "https://www.sec.gov/Archives/edgar/data/1/000000000124000001/cn-split.htm",
        b"cn-split",
        datetime(2024, 5, 31, 12, tzinfo=UTC),
        datetime(2024, 6, 2, tzinfo=UTC),
        "cn-split-v1",
    )
    event = CorporateActionIdentity(
        subject_id=CIK,
        action_id="split-20240601-cn",
        action_type="split",
        effective_at=datetime(2024, 5, 31, 16, 30, tzinfo=UTC),
        source=source,
        exchange_timezone="Asia/Shanghai",
        ex_date=date(2024, 6, 1),
        split_ratio=Decimal("2"),
    )

    assert event.effective_at.date() == date(2024, 5, 31)
    assert event.effective_date == date(2024, 6, 1)
    assert adjust_share_fact_for_splits(
        replace(shares, start=None, end=date(2024, 5, 31)),
        as_of=datetime(2024, 6, 2, tzinfo=UTC),
        split_events=(event,),
    ) == Decimal("20")
    assert adjust_share_fact_for_splits(
        replace(shares, start=None, end=date(2024, 6, 1)),
        as_of=datetime(2024, 6, 2, tzinfo=UTC),
        split_events=(event,),
    ) == Decimal("10")
    with pytest.raises(SourceIdentityError, match="local date"):
        replace(event, ex_date=date(2024, 5, 31))


def test_corporate_action_rejects_invalid_exchange_timezone() -> None:
    available = datetime(2024, 5, 1, tzinfo=UTC)
    source = _source(
        "https://www.sec.gov/Archives/edgar/data/1/000000000124000001/split.htm",
        b"invalid-timezone",
        available,
        available,
        "invalid-timezone-v1",
    )
    with pytest.raises(SourceIdentityError, match="IANA timezone"):
        CorporateActionIdentity(
            subject_id=CIK,
            action_id="invalid-timezone",
            action_type="split",
            effective_at=available,
            source=source,
            exchange_timezone="Not/A_Timezone",
            ex_date=date(2024, 5, 1),
            split_ratio=Decimal("2"),
        )


def test_corporate_action_identity_rejects_ambiguous_value_shapes() -> None:
    available = datetime(2024, 5, 1, tzinfo=UTC)
    source = _source(
        "https://www.sec.gov/Archives/edgar/data/1/000000000124000001/action.htm",
        b"action",
        available,
        available,
        "action-v1",
    )
    with pytest.raises(SourceIdentityError, match="split actions"):
        CorporateActionIdentity(
            subject_id=CIK,
            action_id="split",
            action_type="split",
            effective_at=available,
            source=source,
            exchange_timezone="UTC",
            ex_date=date(2024, 5, 1),
            split_ratio=Decimal("2"),
            cash_amount=Decimal("1"),
        )
    with pytest.raises(SourceIdentityError, match="cash_amount, currency, and unit"):
        CorporateActionIdentity(
            subject_id=CIK,
            action_id="dividend",
            action_type="cash_dividend",
            effective_at=available,
            source=source,
            exchange_timezone="UTC",
            cash_amount=Decimal("1"),
        )
    with pytest.raises(SourceIdentityError, match="unsupported corporate action"):
        CorporateActionIdentity(
            subject_id=CIK,
            action_id="merger",
            action_type="merger",  # type: ignore[arg-type]
            effective_at=available,
            source=source,
            exchange_timezone="UTC",
        )


def test_corporate_action_fields_are_action_specific() -> None:
    available = datetime(2024, 5, 1, tzinfo=UTC)
    source = _source(
        "https://www.sec.gov/Archives/edgar/data/1/000000000124000001/action.htm",
        b"cash-action",
        available,
        available,
        "cash-v1",
    )
    cash = CorporateActionIdentity(
        subject_id=CIK,
        action_id="cash-20240501",
        action_type="cash_dividend",
        effective_at=available,
        source=source,
        exchange_timezone="UTC",
        ex_date=date(2024, 5, 1),
        record_date=date(2024, 5, 2),
        pay_date=date(2024, 5, 10),
        cash_amount=Decimal("1.25"),
        currency="USD",
        unit="USD/share",
    )
    symbol_change = CorporateActionIdentity(
        subject_id=CIK,
        action_id="symbol-20240501",
        action_type="symbol_change",
        effective_at=available,
        source=replace(
            source,
            content_sha256=hashlib.sha256(b"symbol-change").hexdigest(),
            revision_id="symbol-v1",
        ),
        exchange_timezone="UTC",
        new_subject_id="NEW-SUBJECT",
    )

    assert (cash.ex_date, cash.record_date, cash.pay_date) == (
        date(2024, 5, 1),
        date(2024, 5, 2),
        date(2024, 5, 10),
    )
    assert cash.currency == "USD"
    assert cash.unit == "USD/share"
    assert symbol_change.new_subject_id == "NEW-SUBJECT"
