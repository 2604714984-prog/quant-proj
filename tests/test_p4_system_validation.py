from copy import deepcopy
import json
from pathlib import Path
import socket
import subprocess
import threading

import pytest

from quant_system.markets.common import MarketDataError
from scripts import run_p4_system_validation as p4


@pytest.fixture
def packet() -> tuple[dict, dict]:
    return p4.strict_load(p4.DEFINITION), p4.strict_load(p4.FIXTURE)


@pytest.fixture
def accepted_runtime() -> dict[str, object]:
    return {
        "clean_committed": True,
        "commit": "c" * 40,
        "tree": "d" * 40,
    }


def test_frozen_golden_report_passes_all_thirteen_system_gates(
    accepted_runtime: dict[str, object],
) -> None:
    report = p4.build_report(p4.DEFINITION, p4.FIXTURE, runtime=accepted_runtime)

    assert report["system_validation_status"] == "FORMAL_SYSTEM_VALIDATION_PASS"
    assert report["system_gate_counts"] == {"passed": 13, "total": 13}
    assert set(report["gate_results"]) == set(p4.GATES)
    assert all(report["gate_results"].values())
    assert report["observed_ledger"]["final_nav"] == "100400.087525000"
    assert report["observed_ledger"]["accounting_residual"] == "0.000000000"
    assert report["strategy_gate_counts"] is None
    assert report["strategy_candidate_available"] is False
    assert report["strategy_evidence_eligible"] is False


def test_golden_stage_ledger_covers_actions_blocking_and_settlement(
    accepted_runtime: dict[str, object],
) -> None:
    observed = p4.build_report(
        p4.DEFINITION, p4.FIXTURE, runtime=accepted_runtime
    )["observed_ledger"]
    stages = observed["stages"]

    assert stages[0]["positions"] == {
        "SYN_A": "500.000000000",
        "SYN_B": "500.000000000",
    }
    assert stages[1]["positions"]["SYN_A"] == "1000.000000000"
    assert stages[1]["pending_cash"] == "500.000000000"
    assert stages[3]["settled_cash"] == "500.075025000"
    assert [stages[index]["blocked_delay"] for index in (4, 5, 6)] == [1, 2, 2]
    assert "SYN_A" not in stages[4]["positions"]
    assert stages[6]["pending_cash"] == "49950.012500000"
    assert stages[7]["settled_cash"] == "100400.087525000"
    assert observed["commission_total"] == "74.962475000"
    assert observed["slippage_total"] == "74.950000000"
    assert observed["receipt_count"] == 8


def test_default_validate_only_opens_no_socket_and_writes_no_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_connect(*_args, **_kwargs):
        raise AssertionError("synthetic validation must not open a socket")

    monkeypatch.setattr(socket.socket, "connect", forbidden_connect)
    before = set(p4.RESULT.parent.glob("p4_v2_engine_golden_static_allocation_v1_result*"))
    assert p4.main([]) == 0
    after = set(p4.RESULT.parent.glob("p4_v2_engine_golden_static_allocation_v1_result*"))
    assert after == before


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_strict_json_rejects_nonfinite_constants(tmp_path: Path, constant: str) -> None:
    path = tmp_path / "bad.json"
    path.write_text(f'{{"value": {constant}}}', encoding="utf-8")
    with pytest.raises(p4.ValidationError, match="nonfinite"):
        p4.strict_load(path)


def test_strict_json_rejects_duplicate_keys(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text('{"value": 1, "value": 2}', encoding="utf-8")
    with pytest.raises(p4.ValidationError, match="duplicate JSON key"):
        p4.strict_load(path)


def test_fixture_hash_drift_fails_before_simulation(
    tmp_path: Path,
    packet: tuple[dict, dict],
    accepted_runtime: dict[str, object],
) -> None:
    _definition, fixture = packet
    fixture["stages"][0]["rows"][0]["open_price"] = "100"
    changed = tmp_path / "fixture.json"
    changed.write_text(json.dumps(fixture, sort_keys=True), encoding="utf-8")

    with pytest.raises(p4.ValidationError, match="fixture SHA-256"):
        p4.build_report(p4.DEFINITION, changed, runtime=accepted_runtime)


def test_frozen_schema_rejects_extra_fields(
    tmp_path: Path,
    packet: tuple[dict, dict],
    accepted_runtime: dict[str, object],
) -> None:
    definition, _fixture = packet
    definition["unreviewed_extension"] = True
    changed = tmp_path / "definition.json"
    changed.write_text(json.dumps(definition, sort_keys=True), encoding="utf-8")

    with pytest.raises(p4.ValidationError, match="object keys changed"):
        p4.build_report(changed, p4.FIXTURE, runtime=accepted_runtime)


def test_late_execution_source_fails_closed(packet: tuple[dict, dict]) -> None:
    _definition, fixture = packet
    fixture["stages"][0]["rows"][0]["source_available_at"] = (
        "2026-01-05T14:30:00.000001+00:00"
    )
    with pytest.raises(MarketDataError, match="unavailable at open"):
        p4._simulate(fixture)


def test_missing_status_identity_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    packet: tuple[dict, dict],
) -> None:
    _definition, fixture = packet
    original = p4._statuses

    def missing_one(*args, **kwargs):
        return original(*args, **kwargs)[:-1]

    monkeypatch.setattr(p4, "_statuses", missing_one)
    with pytest.raises(MarketDataError, match="missing effective suspended"):
        p4._simulate(fixture)


def test_duplicate_action_identity_fails_closed(packet: tuple[dict, dict]) -> None:
    _definition, fixture = packet
    actions = fixture["stages"][1]["rows"][0]["corporate_actions"]
    actions.append(deepcopy(actions[0]))
    with pytest.raises(MarketDataError, match="globally unique"):
        p4._simulate(fixture)


def test_replayed_split_identity_on_later_session_fails_once_only(
    packet: tuple[dict, dict],
) -> None:
    _definition, fixture = packet
    replay = deepcopy(fixture["stages"][1]["rows"][0]["corporate_actions"][0])
    replay.update(
        {
            "available_at": "2026-01-06T20:30:00+00:00",
            "effective_at": "2026-01-07T14:30:00+00:00",
            "ex_date": "2026-01-07",
        }
    )
    fixture["stages"][2]["rows"][0]["corporate_actions"] = [replay]
    with pytest.raises(ValueError, match="already been applied"):
        p4._simulate(fixture)


def test_terminal_symbol_must_be_pit_ineligible(packet: tuple[dict, dict]) -> None:
    _definition, fixture = packet
    fixture["stages"][4]["rows"][0]["delisted"] = False
    with pytest.raises(MarketDataError, match="PIT ineligible"):
        p4._simulate(fixture)


def test_stage_chain_is_deterministic_and_sensitive_to_input_identity(
    packet: tuple[dict, dict],
) -> None:
    _definition, fixture = packet
    first = p4._simulate(fixture)
    second = p4._simulate(deepcopy(fixture))
    changed = deepcopy(fixture)
    changed["stages"][0]["rows"][0]["source_available_at"] = (
        "2026-01-05T14:29:59+00:00"
    )
    mutated = p4._simulate(changed)

    assert first == second
    assert first["stage_hashes"] != mutated["stage_hashes"]
    assert len(first["stage_hashes"]) == 8
    assert len(set(first["stage_hashes"])) == 8
    assert len(first["receipt_hashes"]) == 8


def test_execute_runtime_gate_rejects_a_dirty_repository(tmp_path: Path) -> None:
    subprocess.run(("git", "init", "-q", str(tmp_path)), check=True)
    subprocess.run(("git", "-C", str(tmp_path), "config", "user.email", "p4@invalid"), check=True)
    subprocess.run(("git", "-C", str(tmp_path), "config", "user.name", "P4"), check=True)
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("clean\n", encoding="utf-8")
    subprocess.run(("git", "-C", str(tmp_path), "add", "tracked.txt"), check=True)
    subprocess.run(("git", "-C", str(tmp_path), "commit", "-qm", "base"), check=True)
    untracked = tmp_path / "untracked.txt"
    untracked.write_text("untracked\n", encoding="utf-8")

    with pytest.raises(p4.ValidationError, match="clean committed worktree"):
        p4._runtime_identity(tmp_path, require_clean=True)
    untracked.unlink()
    tracked.write_text("dirty\n", encoding="utf-8")

    with pytest.raises(p4.ValidationError, match="clean committed worktree"):
        p4._runtime_identity(tmp_path, require_clean=True)


def test_execute_rejects_external_definition_fixture_or_output_before_git_gate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    definition = tmp_path / "definition.json"
    fixture = tmp_path / "fixture.json"
    definition.write_bytes(p4.DEFINITION.read_bytes())
    fixture.write_bytes(p4.FIXTURE.read_bytes())

    def unexpected_runtime(*_args, **_kwargs):
        raise AssertionError("path rejection must precede the Git runtime gate")

    monkeypatch.setattr(p4, "_runtime_identity", unexpected_runtime)
    with pytest.raises(p4.ValidationError, match="exact frozen definition"):
        p4.main(
            [
                "--execute",
                "--definition",
                str(definition),
                "--fixture",
                str(fixture),
                "--output",
                str(tmp_path / "result.json"),
            ]
        )


def test_atomic_publication_creates_only_result_and_sidecar_then_refuses_overwrite(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    accepted_runtime: dict[str, object],
) -> None:
    report = p4.build_report(p4.DEFINITION, p4.FIXTURE, runtime=accepted_runtime)
    output = tmp_path / "p4_v2_engine_golden_static_allocation_v1_result.json"
    monkeypatch.setattr(p4, "RESULT", output)

    p4._publish(report, output)
    assert {path.name for path in tmp_path.iterdir()} == {
        output.name,
        output.name + ".sha256",
    }
    digest, filename = output.with_suffix(".json.sha256").read_text().split()
    assert filename == output.name
    assert digest == p4.sha256_file(output)
    with pytest.raises(p4.ValidationError, match="may already exist"):
        p4._publish(report, output)


def test_concurrent_publishers_have_exactly_one_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    accepted_runtime: dict[str, object],
) -> None:
    report = p4.build_report(p4.DEFINITION, p4.FIXTURE, runtime=accepted_runtime)
    output = tmp_path / "p4_v2_engine_golden_static_allocation_v1_result.json"
    monkeypatch.setattr(p4, "RESULT", output)
    barrier = threading.Barrier(2)
    outcomes: list[BaseException | None] = []

    def publish() -> None:
        barrier.wait()
        try:
            p4._publish(report, output)
        except BaseException as exc:
            outcomes.append(exc)
        else:
            outcomes.append(None)

    threads = [threading.Thread(target=publish) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert all(not thread.is_alive() for thread in threads)
    assert sum(outcome is None for outcome in outcomes) == 1
    failures = [outcome for outcome in outcomes if outcome is not None]
    assert len(failures) == 1 and isinstance(failures[0], p4.ValidationError)
    assert {path.name for path in tmp_path.iterdir()} == {
        output.name,
        output.name + ".sha256",
    }


def test_second_finalization_failure_removes_final_temp_and_claim_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    accepted_runtime: dict[str, object],
) -> None:
    report = p4.build_report(p4.DEFINITION, p4.FIXTURE, runtime=accepted_runtime)
    original_link = p4.os.link
    calls = {"count": 0}

    def fail_second_link(source, destination) -> None:
        calls["count"] += 1
        if calls["count"] == 2:
            raise OSError("injected second-finalization failure")
        original_link(source, destination)

    monkeypatch.setattr(p4.os, "link", fail_second_link)
    sentinel = tmp_path / "preexisting.txt"
    sentinel.write_text("preserve\n", encoding="utf-8")
    output = tmp_path / "p4_v2_engine_golden_static_allocation_v1_result.json"
    monkeypatch.setattr(p4, "RESULT", output)
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    with pytest.raises(OSError, match="second-finalization"):
        p4._publish(report, output)
    assert {path.name: path.read_bytes() for path in tmp_path.iterdir()} == before

    absent_parent = tmp_path / "new-report-directory"
    second_output = absent_parent / output.name
    monkeypatch.setattr(p4, "RESULT", second_output)
    calls["count"] = 0
    with pytest.raises(OSError, match="second-finalization"):
        p4._publish(report, second_output)
    assert not absent_parent.exists()


def test_result_contract_has_no_strategy_performance_fields(
    accepted_runtime: dict[str, object],
) -> None:
    report = p4.build_report(p4.DEFINITION, p4.FIXTURE, runtime=accepted_runtime)
    serialized = json.dumps(report, sort_keys=True).lower()
    for forbidden in ("sharpe", "cagr", "annual_return", "alpha_estimate"):
        assert forbidden not in serialized
