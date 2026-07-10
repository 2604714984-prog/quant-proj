import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from scripts.validate_automated_gate_manifest import validate_file, validate_payload


SHA1 = "0123456789abcdef0123456789abcdef01234567"
SHA256 = "0123456789abcdef" * 4
CALLBACK_ID = "019f4ca0-2054-77e3-9559-7005c0f9b565"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(root: Path, *args: str) -> str:
    return subprocess.check_output(args, cwd=root, text=True).strip()


def _payload() -> dict:
    return {
        "schema_version": 1,
        "task_id": "TASK-1",
        "execution_id": "EXEC-1",
        "model_role": "executor",
        "model": "gpt-5.6-luna",
        "status": "GREEN",
        "workspace_root": "/tmp/worktree",
        "task_packet": {"dir": "/tmp/packet", "spec_sha256": SHA256},
        "source": {"commit": SHA1, "tree": SHA1},
        "result": {"commit": SHA1, "tree": SHA1},
        "code_changed": True,
        "checks": [
            {"name": "focused_tests", "command": "pytest", "exit_code": 0, "test_count": 1},
            {"name": "git_diff_check", "command": "git diff --check", "exit_code": 0},
            {"name": "boundary_scan", "command": "safety", "exit_code": 0},
        ],
        "callback": {"path": "callback.json", "sha256": SHA256},
        "artifacts": [{"path": "artifact.bin", "sha256": SHA256}],
        "push": {"required": False},
        "missing_evidence": [],
        "evidence_conflicts": [],
    }


def _real_gate(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    tracked = repo / "tracked.txt"
    tracked.write_text("source\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "source"], cwd=repo, check=True)
    source_commit = _run(repo, "git", "rev-parse", "HEAD")
    source_tree = _run(repo, "git", "rev-parse", "HEAD^{tree}")
    tracked.write_text("result\n", encoding="utf-8")
    artifact = repo / "artifact.bin"
    artifact.write_bytes(b"artifact")
    subprocess.run(["git", "add", "tracked.txt", "artifact.bin"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "result"], cwd=repo, check=True)
    result_commit = _run(repo, "git", "rev-parse", "HEAD")
    result_tree = _run(repo, "git", "rev-parse", "HEAD^{tree}")

    packet = tmp_path / "packet"
    packet.mkdir()
    commands = packet / "gate_commands.txt"
    commands.write_text(
        "python3 -c \"print('focused')\"\ngit diff --check\npython3 -c \"print('boundary')\"\n",
        encoding="utf-8",
    )
    delta = packet / "context_delta.md"
    delta.write_text("bounded delta", encoding="utf-8")
    spec = packet / "spec.md"
    spec.write_text(
        f"""TASK_ID: TASK-1
STATUS: BACKLOG
TARGET_PROJECT: test
RECOMMENDED_AGENT: codex_dev
MODEL_ROLE: executor
MODEL: gpt-5.6-luna
REASONING_EFFORT: medium
SOURCE_COMMIT: {source_commit}
SOURCE_TREE: {source_tree}
AUTOMATED_GATE_COMMANDS: gate_commands.txt
AUTOMATED_GATE_COMMANDS_SHA256: {_digest(commands)}
CALLBACK_TARGET: {CALLBACK_ID}
ACCEPTANCE_ROLE: codex_acceptance
CONTEXT_DELTA: context_delta.md
CONTEXT_DELTA_SHA256: {_digest(delta)}
""",
        encoding="utf-8",
    )
    (packet / "handoff.md").write_text("handoff", encoding="utf-8")
    (packet / "human_gate.md").write_text("not required", encoding="utf-8")

    callback = packet / "callback.json"
    callback.write_text(
        json.dumps(
            {
                "task_id": "TASK-1",
                "execution_id": "EXEC-1",
                "status": "LUNA_EXECUTION_COMPLETE",
                "model": "gpt-5.6-luna",
                "source": {"commit": source_commit, "tree": source_tree},
                "result": {"commit": result_commit, "tree": result_tree},
            }
        ),
        encoding="utf-8",
    )
    payload = _payload()
    payload.update(
        workspace_root=str(repo),
        task_packet={"dir": str(packet), "spec_sha256": _digest(spec)},
        source={"commit": source_commit, "tree": source_tree},
        result={"commit": result_commit, "tree": result_tree},
        callback={"path": "callback.json", "sha256": _digest(callback)},
        artifacts=[{"path": "artifact.bin", "sha256": _digest(artifact)}],
    )
    payload["checks"] = [
        {"name": "focused_tests", "command": "python3 -c \"print('focused')\"", "exit_code": 0, "test_count": 1},
        {"name": "git_diff_check", "command": "git diff --check", "exit_code": 0},
        {"name": "boundary_scan", "command": "python3 -c \"print('boundary')\"", "exit_code": 0},
    ]
    manifest = tmp_path / "gate.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    return manifest


def _convert_to_strategy_gate(manifest: Path) -> None:
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    packet = Path(payload["task_packet"]["dir"])
    spec = packet / "spec.md"
    spec_payload = spec.read_text(encoding="utf-8")
    spec_payload = spec_payload.replace("TARGET_PROJECT: test", "TARGET_PROJECT: strategy_work")
    spec_payload = spec_payload.replace("RECOMMENDED_AGENT: codex_dev", "RECOMMENDED_AGENT: strategy_research_executor")
    spec_payload = spec_payload.replace("MODEL_ROLE: executor", "MODEL_ROLE: strategy_research_executor")
    spec_payload = spec_payload.replace("MODEL: gpt-5.6-luna", "MODEL: gpt-5.6-sol")
    spec_payload = spec_payload.replace("REASONING_EFFORT: medium", "REASONING_EFFORT: high")
    spec_payload = spec_payload.replace(
        f"CALLBACK_TARGET: {CALLBACK_ID}",
        "CALLBACK_TARGET: 019f4c70-cac3-7211-8e04-47b8b51c819e",
    )
    spec_payload = spec_payload.replace(
        "CONTEXT_DELTA: context_delta.md",
        "EXECUTION_THREAD_ID: 019f3881-5293-74a1-8535-814bd83c8681\n"
        "EXECUTION_THREAD_TITLE: Strategy Work — Sol Research\n"
        "CONTEXT_DELTA: context_delta.md",
    )
    spec.write_text(spec_payload, encoding="utf-8")
    payload["task_packet"]["spec_sha256"] = _digest(spec)
    payload["model_role"] = "strategy_research_executor"
    payload["model"] = "gpt-5.6-sol"
    callback = packet / payload["callback"]["path"]
    callback_payload = json.loads(callback.read_text(encoding="utf-8"))
    callback_payload["status"] = "SOL_STRATEGY_RESEARCH_COMPLETE"
    callback_payload["model"] = "gpt-5.6-sol"
    callback.write_text(json.dumps(callback_payload), encoding="utf-8")
    payload["callback"]["sha256"] = _digest(callback)
    manifest.write_text(json.dumps(payload), encoding="utf-8")


def _claim_reserved_strategy_thread(manifest: Path, agent: str) -> None:
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    spec = Path(payload["task_packet"]["dir"]) / "spec.md"
    spec_payload = spec.read_text(encoding="utf-8")
    if agent == "luna_dispatcher":
        spec_payload = spec_payload.replace("RECOMMENDED_AGENT: codex_dev", "RECOMMENDED_AGENT: luna_dispatcher")
        spec_payload = spec_payload.replace("MODEL_ROLE: executor", "MODEL_ROLE: dispatcher")
    spec_payload = spec_payload.replace(
        "CONTEXT_DELTA: context_delta.md",
        "EXECUTION_THREAD_ID: 019f3881-5293-74a1-8535-814bd83c8681\n"
        "EXECUTION_THREAD_TITLE: Strategy Work — Sol Research\n"
        "CONTEXT_DELTA: context_delta.md",
    )
    spec.write_text(spec_payload, encoding="utf-8")
    payload["task_packet"]["spec_sha256"] = _digest(spec)
    manifest.write_text(json.dumps(payload), encoding="utf-8")


def test_green_payload_passes():
    validate_payload(_payload())


def test_strategy_gate_requires_exact_sol_role_model_pair():
    payload = _payload()
    payload["model_role"] = "strategy_research_executor"
    payload["model"] = "gpt-5.6-sol"
    validate_payload(payload)
    payload["model"] = "gpt-5.6-luna"
    with pytest.raises(ValueError, match="exactly match its execution role"):
        validate_payload(payload)


def test_failed_or_missing_check_is_rejected():
    payload = _payload()
    payload["checks"][0]["exit_code"] = 1
    with pytest.raises(ValueError, match="did not pass"):
        validate_payload(payload)
    payload = _payload()
    payload["checks"] = [check for check in payload["checks"] if check["name"] != "focused_tests"]
    with pytest.raises(ValueError, match="positive focused"):
        validate_payload(payload)


def test_gate_binds_packet_callback_artifacts_and_real_git(tmp_path):
    manifest = _real_gate(tmp_path)
    validate_file(manifest)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["result"]["tree"] = payload["source"]["tree"]
    callback = Path(payload["task_packet"]["dir"]) / payload["callback"]["path"]
    callback_payload = json.loads(callback.read_text(encoding="utf-8"))
    callback_payload["result"]["tree"] = payload["source"]["tree"]
    callback.write_text(json.dumps(callback_payload), encoding="utf-8")
    payload["callback"]["sha256"] = _digest(callback)
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="result commit/tree mismatch"):
        validate_file(manifest)


def test_strategy_gate_binds_sol_role_to_strategy_packet(tmp_path):
    manifest = _real_gate(tmp_path)
    _convert_to_strategy_gate(manifest)
    validate_file(manifest)


def test_gate_role_cannot_differ_from_packet(tmp_path):
    manifest = _real_gate(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["model_role"] = "strategy_research_executor"
    payload["model"] = "gpt-5.6-sol"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="role/model differs from task packet"):
        validate_file(manifest)


@pytest.mark.parametrize("agent", ("codex_dev", "luna_dispatcher"))
def test_full_gate_rejects_non_strategy_reserved_thread_claim(tmp_path, agent):
    manifest = _real_gate(tmp_path)
    _claim_reserved_strategy_thread(manifest, agent)
    with pytest.raises(ValueError, match="strategy thread metadata is reserved"):
        validate_file(manifest)


def test_command_drift_is_rejected(tmp_path):
    manifest = _real_gate(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["checks"][0]["command"] = "pytest -k different"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="exactly match"):
        validate_file(manifest)


def test_dirty_result_worktree_is_rejected(tmp_path):
    manifest = _real_gate(tmp_path)
    repo = Path(json.loads(manifest.read_text(encoding="utf-8"))["workspace_root"])
    (repo / "untracked.txt").write_text("drift", encoding="utf-8")
    with pytest.raises(ValueError, match="clean result worktree"):
        validate_file(manifest)


def test_code_changed_false_requires_identical_refs():
    payload = _payload()
    payload["code_changed"] = False
    payload["result"]["commit"] = "fedcba9876543210fedcba9876543210fedcba98"
    with pytest.raises(ValueError, match="identical source and result"):
        validate_payload(payload)


def test_template_is_rejected():
    template = Path(__file__).resolve().parents[1] / "reports/workspace_dispatch/templates/automated_gate_manifest_template.json"
    with pytest.raises(ValueError, match="template-only"):
        validate_payload(json.loads(template.read_text(encoding="utf-8")))
