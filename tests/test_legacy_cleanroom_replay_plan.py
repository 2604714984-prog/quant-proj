from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = (
    ROOT
    / "research"
    / "definitions"
    / "legacy_rejected_strategy_cleanroom_replay_plan_v1.json"
)
FAMILY_PATH = (
    ROOT
    / "research"
    / "definitions"
    / "legacy_a_share_family_replay_scope_v1.json"
)


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha_fields(value: object) -> list[tuple[str, object]]:
    fields: list[tuple[str, object]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key.endswith("sha256"):
                fields.append((key, item))
            fields.extend(_sha_fields(item))
    elif isinstance(value, list):
        for item in value:
            fields.extend(_sha_fields(item))
    return fields


def test_cleanroom_plan_pins_family_scope_and_forbids_legacy_code() -> None:
    plan = _load(PLAN_PATH)
    family = _load(FAMILY_PATH)

    assert plan["source_contract"]["family_scope"]["sha256"] == _sha256(
        FAMILY_PATH
    )
    assert plan["source_contract"]["legacy_strategy_python_inspected"] is False
    assert (
        plan["source_contract"]["legacy_strategy_python_or_functions_may_be_reused"]
        is False
    )
    assert plan["hard_boundaries"]["no_legacy_strategy_code_or_functions"] is True
    assert plan["strategy_candidate_available"] is False
    assert family["strategy_candidate_available"] is False
    assert ".py" not in PLAN_PATH.read_text(encoding="utf-8")
    assert ".py" not in FAMILY_PATH.read_text(encoding="utf-8")


def test_family_scope_is_complete_and_fail_closed() -> None:
    family = _load(FAMILY_PATH)
    entries = family["entries"]
    by_id = {entry["id"]: entry for entry in entries}

    assert len(entries) == 29
    assert set(by_id) == {f"A_FAMILY_{number}" for number in range(40, 69)}
    assert sum(
        entry["disposition"] == "METHOD_CORRECT_RECOMPUTE" for entry in entries
    ) == 26
    assert sum(entry["disposition"] == "FIRST_BATCH_REPLAY" for entry in entries) == 2
    assert sum(entry["disposition"] == "EXCLUDE_NOT_EXECUTED" for entry in entries) == 1

    assert by_id["A_FAMILY_66"]["status"] == "rejected"
    assert by_id["A_FAMILY_67"]["status"] == "rejected"
    assert by_id["A_FAMILY_68"]["status"] == "blocked-on-data"
    assert by_id["A_FAMILY_68"]["result"] is None

    for entry in entries:
        packet_path, packet_hash = entry["packet"]
        assert packet_path.startswith("reports/planning/")
        assert len(packet_hash) == 64
        int(packet_hash, 16)
        if entry["result"] is not None:
            result_path, result_hash = entry["result"]
            assert result_path.startswith("reports/planning/")
            assert len(result_hash) == 64
            int(result_hash, 16)


def test_replay_batches_preserve_controlling_negative_lineage() -> None:
    plan = _load(PLAN_PATH)

    assert plan["batch_0_completed_us_migration_replay"]["strategy_ids"] == [
        "US31",
        "US36",
        "US41",
        "US46",
    ]
    assert (
        plan["batch_0_completed_us_migration_replay"]["v2_status"]
        == "REPLAY_COMPLETE_HEADLINES_NOT_REPRODUCED"
    )
    assert plan["batch_0_completed_us_migration_replay"]["strict_pit_eligible"] is False
    assert (
        plan["batch_0_completed_us_migration_replay"][
            "satisfies_new_cleanroom_requirement"
        ]
        is False
    )
    assert plan["batch_0_completed_us_migration_replay"]["cleanroom_replay_required"] is True
    assert plan["batch_1_cleanroom_us_four"]["strategy_ids"] == [
        "US31",
        "US36",
        "US41",
        "US46",
    ]
    assert (
        plan["batch_1_cleanroom_us_four"][
            "legacy_implementation_or_function_access_allowed"
        ]
        is False
    )
    assert [entry["strategy_id"] for entry in plan["batch_2_first_a_share_cleanroom_implementations"]] == [
        "A_FAMILY_66",
        "A_FAMILY_67",
    ]
    assert sum(plan["batch_5_non_family_spec_decomposition"]["groups"].values()) == 35
    assert "A_FAMILY_68" in plan["excluded_not_executed_or_noncontrolling"]
    assert (
        plan["batch_6_us_adaptive_quality"]["historical_decision"]
        == "FINAL_BINARY_REJECT_BENCHMARK_ONLY_DO_NOT_RETRY_CURRENT_CONFIGURATION"
    )
    assert len(plan["additional_us_noncontrolling_inventory"]) == 6
    assert plan["hard_boundaries"]["no_rejected_strategy_resurrection"] is True


def test_plan_hashes_are_well_formed_and_chan_sources_are_exact() -> None:
    plan = _load(PLAN_PATH)

    for key, value in _sha_fields(plan):
        assert isinstance(value, str), key
        assert re.fullmatch(r"[0-9a-f]{64}", value), (key, value)

    for _, text_hash in plan["batch_0_completed_us_migration_replay"]["text_specs"]:
        assert re.fullmatch(r"[0-9a-f]{64}", text_hash)

    chan = {entry["strategy_id"]: entry for entry in plan["batch_3_event_mechanism_only"]}
    assert chan["CHAN_CF_H1_PIT_CSI300_REPLICATION"]["packet_sha256"] == (
        "516e3d12addc1783ac358cf08c5817a63316b13b7718133ba0598cd4b319d05f"
    )
    assert chan["CHAN_CF_H1_PIT_CSI300_REPLICATION"]["result_sha256"] == (
        "2e0a25b0060465959779cef8ee6e01088be27faf1cae670a64be518e5690bd52"
    )
    assert chan["CHAN_TIER2_PIT_CSI300_REPLICATION"]["packet_sha256"] == (
        "ec99074e9bd0ab90212222298a57c8cbff3b6314dceac99a3ff1551208dcd52e"
    )
    assert chan["CHAN_TIER2_PIT_CSI300_REPLICATION"]["result_sha256"] == (
        "7bdc76e4ae03b2d0bea1bdab1c12ef5c06365921c39e715ac3a664cc27c91ac2"
    )
