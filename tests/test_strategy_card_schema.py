import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "runbooks/automated_research_factory/strategy_card_schema.json"
FIXTURE_ROOT = ROOT / "tests/fixtures/strategy_cards"
FINAL_STATES = {
    "blocked.json": "BLOCKED",
    "accepted.json": "RESEARCH_EVIDENCE_ACCEPTED",
    "rejected.json": "RESEARCH_EVIDENCE_REJECTED",
}


def _validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _fixture(name: str) -> dict:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(("name", "state"), FINAL_STATES.items())
def test_positive_fixture_for_every_final_state(name, state):
    payload = _fixture(name)
    assert payload["state"] == state
    _validator().validate(payload)


@pytest.mark.parametrize("field", ("question", "statement"))
def test_hypothesis_text_must_be_nonempty(field):
    payload = _fixture("blocked.json")
    payload["hypothesis"][field] = ""
    assert not _validator().is_valid(payload)


@pytest.mark.parametrize("field", ("success_criteria", "failure_criteria"))
def test_hypothesis_criteria_must_be_nonempty(field):
    payload = _fixture("blocked.json")
    payload["hypothesis"][field] = []
    assert not _validator().is_valid(payload)


@pytest.mark.parametrize("missing", ("object_id", "sha256"))
def test_every_ref_requires_object_id_and_digest(missing):
    payload = _fixture("accepted.json")
    payload["model_spec"]["features_ref"].pop(missing)
    assert not _validator().is_valid(payload)


def test_mutable_alias_and_extra_ref_fields_are_rejected():
    payload = _fixture("accepted.json")
    ref = payload["model_spec"]["features_ref"]
    ref["object_id"] = "latest"
    assert not _validator().is_valid(payload)
    payload = _fixture("accepted.json")
    payload["model_spec"]["features_ref"]["path"] = "mutable/latest.json"
    assert not _validator().is_valid(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("object_id", "0" * 40),
        ("object_id", "f" * 64),
        ("object_id", "urn:sha256:" + "a" * 64),
        ("sha256", "0" * 64),
    ),
)
def test_immutable_refs_reject_placeholder_digests(field, value):
    payload = _fixture("accepted.json")
    payload["model_spec"]["features_ref"][field] = value
    assert not _validator().is_valid(payload)


@pytest.mark.parametrize(
    ("fixture", "field"),
    (
        ("accepted.json", "reviewer"),
        ("accepted.json", "reason"),
        ("rejected.json", "reviewer"),
        ("rejected.json", "reason"),
        ("blocked.json", "actor"),
        ("blocked.json", "reason"),
    ),
)
def test_evidence_identity_and_reason_must_not_be_whitespace(fixture, field):
    payload = _fixture(fixture)
    payload["evidence"][field] = "   "
    assert not _validator().is_valid(payload)


@pytest.mark.parametrize(
    "required_field",
    ("verification_receipts", "metrics_ref", "reproducibility_ref", "multiple_testing_ref"),
)
def test_accepted_evidence_requires_complete_verification_contract(required_field):
    payload = _fixture("accepted.json")
    payload["evidence"].pop(required_field)
    assert not _validator().is_valid(payload)


@pytest.mark.parametrize("required_field", ("reviewer", "decided_at", "reason", "failure_codes"))
def test_rejected_evidence_requires_complete_failure_contract(required_field):
    payload = _fixture("rejected.json")
    payload["evidence"].pop(required_field)
    assert not _validator().is_valid(payload)


@pytest.mark.parametrize("required_field", ("prior_state", "actor", "decided_at", "reason"))
def test_blocked_evidence_retains_lifecycle_context(required_field):
    payload = _fixture("blocked.json")
    payload["evidence"].pop(required_field)
    assert not _validator().is_valid(payload)


def test_state_and_evidence_disposition_must_match():
    payload = _fixture("accepted.json")
    payload["state"] = "RESEARCH_EVIDENCE_REJECTED"
    assert not _validator().is_valid(payload)


def test_boundary_flags_remain_false_in_all_fixtures():
    validator = _validator()
    for name in FINAL_STATES:
        payload = _fixture(name)
        for flag in payload["boundary_flags"]:
            mutated = copy.deepcopy(payload)
            mutated["boundary_flags"][flag] = True
            assert not validator.is_valid(mutated), flag
