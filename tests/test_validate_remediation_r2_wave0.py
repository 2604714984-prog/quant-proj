from __future__ import annotations

from copy import deepcopy

import pytest

from scripts import validate_remediation_r2_wave0 as validator


def test_current_wave0_contract_is_valid_before_backup() -> None:
    validator.validate(require_backup=False)


def test_candidate_promotion_is_rejected() -> None:
    value = validator.load_json(validator.BASELINE)
    value["strategy_candidate_available"] = True
    with pytest.raises(validator.ContractError, match="candidate_flag_must_be_false"):
        validator.validate_baseline(value)


def test_dirty_live_checkout_is_rejected() -> None:
    value = validator.load_json(validator.BASELINE)
    value["live_checkouts"][0]["dirty_entries"] = 1
    with pytest.raises(validator.ContractError, match="live_checkout_not_clean"):
        validator.validate_baseline(value)


def test_closed_finding_without_external_evidence_is_rejected() -> None:
    value = validator.load_json(validator.MATRIX)
    value["findings"][0]["status"] = "CLOSED"
    with pytest.raises(validator.ContractError, match="finding_closed_without_evidence"):
        validator.validate_matrix(value)


def test_publisher_enabled_is_rejected() -> None:
    import yaml

    value = yaml.safe_load(validator.REGISTRY.read_text(encoding="utf-8"))
    changed = deepcopy(value)
    changed["central_database"]["publisher_enabled"] = True
    with pytest.raises(validator.ContractError, match="publisher_must_be_disabled"):
        validator.validate_registry(changed)


def test_human_gate_must_match_durable_record() -> None:
    record = validator.load_json(validator.HG_RECORD)
    changed = deepcopy(record)
    changed["backup_path"] = "/tmp/drift.duckdb"
    with pytest.raises(validator.ContractError, match="durable_record_mismatch"):
        validator.validate_hg(changed, validator.read_decisions())
