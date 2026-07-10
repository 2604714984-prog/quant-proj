#!/usr/bin/env python3
"""Validate the single execution record used before Luna acceptance."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess


SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_CHECKS = {"git_diff_check", "boundary_scan"}
PYTEST_SUMMARY_RE = re.compile(r"(?<!\d)(\d+)\s+passed\b")
EXECUTION_ROLE_BINDINGS = {
    "executor": {
        "model": "gpt-5.6-luna",
        "callback_status": "LUNA_EXECUTION_COMPLETE",
    },
    "strategy_research_executor": {
        "model": "gpt-5.6-sol",
        "callback_status": "SOL_STRATEGY_RESEARCH_COMPLETE",
    },
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(value: object, field: str, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value) or len(set(value)) == 1:
        raise ValueError(f"{field} has an invalid or placeholder digest")
    return value


def _rooted(root: Path, value: object, field: str) -> Path:
    if not isinstance(value, str) or not value or any(token in value for token in ("<", ">", "path/to")):
        raise ValueError(f"{field} must be a concrete path")
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"{field} escapes workspace_root")
    if not resolved.is_file():
        raise ValueError(f"{field} file does not exist")
    return resolved


def _metadata(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^([A-Z][A-Z0-9_]*):\s*(.+?)\s*$", line)
        if match:
            result[match.group(1)] = match.group(2).strip("` ")
    return result


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode:
        raise ValueError((completed.stderr or completed.stdout).strip() or f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def _command_argv(command: str) -> list[str]:
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        raise ValueError(f"invalid expected command: {command}") from exc
    if not argv:
        raise ValueError("expected command cannot be empty")
    return argv


def _is_python(argv0: str) -> bool:
    return Path(argv0).name.lower().startswith("python")


def _is_within(root: Path, candidate: Path) -> bool:
    return candidate == root or root in candidate.parents


def _validate_check_semantics(check: dict) -> None:
    """Bind reserved check names to validator-owned or repository-owned semantics."""

    name = check["name"]
    argv = _command_argv(check["command"])
    if name == "focused_tests":
        if not (
            Path(argv[0]).is_absolute()
            and _is_python(argv[0])
            and argv[1:4] == ["-I", "-m", "pytest"]
        ):
            raise ValueError(
                "focused_tests must execute an absolute trusted Python with -I -m pytest"
            )
        forbidden = {"--collect-only", "--co"}
        if forbidden.intersection(argv):
            raise ValueError("focused_tests must execute tests, not collection only")
    elif name == "git_diff_check":
        if argv != ["git", "diff", "--check"]:
            raise ValueError("git_diff_check uses the validator-owned command: git diff --check")
    elif name == "boundary_scan":
        if not (
            Path(argv[0]).is_absolute()
            and _is_python(argv[0])
            and len(argv) == 2
            and not argv[1].startswith("-")
        ):
            raise ValueError(
                "boundary_scan must execute exactly one repository-controlled Python script without arguments"
            )
        if not isinstance(check.get("validator_path"), str) or not check["validator_path"].strip():
            raise ValueError("boundary_scan requires validator_path")
        _digest(check.get("validator_sha256"), "boundary_scan.validator_sha256", SHA256_RE)


def _run_expected_command(root: Path, command: str) -> str:
    argv = _command_argv(command)
    completed = subprocess.run(
        argv,
        cwd=root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if completed.returncode:
        output = completed.stdout[-2000:].strip()
        raise ValueError(f"expected command failed ({command}): {output}")
    return completed.stdout


def _validate_focused_test_runtime(root: Path, check: dict) -> None:
    """Require isolated pytest from the bound interpreter's installed site-packages."""

    argv = _command_argv(check["command"])
    interpreter = Path(argv[0])
    if not interpreter.is_file() or not os.access(interpreter, os.X_OK):
        raise ValueError("focused_tests interpreter is unavailable or not executable")
    resolved_interpreter = interpreter.resolve()
    if _is_within(root, resolved_interpreter):
        raise ValueError("focused_tests interpreter must be outside the result worktree")

    shadows = [candidate for candidate in (root / "pytest.py", root / "pytest") if candidate.exists()]
    if shadows:
        raise ValueError("focused_tests worktree contains a pytest shadow module")

    probe = (
        "import json,pathlib,pytest,sys,sysconfig;"
        "p=sysconfig.get_paths();"
        "print(json.dumps({'executable':sys.executable,'pytest_file':pytest.__file__,"
        "'purelib':p.get('purelib'),'platlib':p.get('platlib')}))"
    )
    completed = subprocess.run(
        [str(interpreter), "-I", "-c", probe],
        cwd=root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if completed.returncode:
        raise ValueError(f"focused_tests pytest provenance probe failed: {completed.stdout[-1000:].strip()}")
    try:
        lines = [line for line in completed.stdout.splitlines() if line.strip()]
        provenance = json.loads(lines[-1])
        reported_interpreter = Path(provenance["executable"]).resolve()
        pytest_file = Path(provenance["pytest_file"]).resolve()
        install_roots = {
            Path(provenance[name]).resolve()
            for name in ("purelib", "platlib")
            if provenance.get(name)
        }
    except (IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("focused_tests pytest provenance output is invalid") from exc
    if reported_interpreter != resolved_interpreter:
        raise ValueError("focused_tests interpreter provenance does not match the bound command")
    if not pytest_file.is_file() or _is_within(root, pytest_file):
        raise ValueError("focused_tests pytest module must be installed outside the result worktree")
    if not any(_is_within(install_root, pytest_file) for install_root in install_roots):
        raise ValueError("focused_tests pytest module is not from the interpreter site-packages")


def _validate_boundary_command(root: Path, source_commit: str, check: dict) -> None:
    validator = _rooted(root, check["validator_path"], "boundary_scan.validator_path")
    if _sha256(validator) != check["validator_sha256"]:
        raise ValueError("boundary_scan validator hash does not match")
    relative = validator.relative_to(root).as_posix()
    if _git(root, "ls-tree", "-r", "--name-only", source_commit, "--", relative) != relative:
        raise ValueError("boundary_scan validator must be tracked in the source commit")
    if _git(root, "diff", "--name-only", source_commit, "HEAD", "--", relative):
        raise ValueError("boundary_scan validator must be unchanged from the source commit")
    argv = _command_argv(check["command"])
    if len(argv) != 2:
        raise ValueError("boundary_scan command must not include additional arguments")
    target = Path(argv[1])
    if not target.is_absolute():
        target = root / target
    if target.resolve() != validator:
        raise ValueError("boundary_scan command must execute validator_path directly")


def validate_payload(payload: dict) -> None:
    if payload.get("template_only") is True:
        raise ValueError("template-only gate cannot enter acceptance")
    if payload.get("schema_version") != 1:
        raise ValueError("schema_version must be 1")
    for field in ("task_id", "execution_id", "workspace_root"):
        if not isinstance(payload.get(field), str) or not payload[field].strip():
            raise ValueError(f"{field} is required")
    model_role = payload.get("model_role")
    binding = EXECUTION_ROLE_BINDINGS.get(model_role)
    if binding is None or payload.get("model") != binding["model"]:
        raise ValueError("gate model must exactly match its execution role")
    if payload.get("status") != "GREEN":
        raise ValueError("gate status must be GREEN")

    packet = payload.get("task_packet", {})
    if not isinstance(packet.get("dir"), str) or not packet["dir"].strip():
        raise ValueError("task_packet.dir is required")
    _digest(packet.get("spec_sha256"), "task_packet.spec_sha256", SHA256_RE)

    source = payload.get("source", {})
    result = payload.get("result", {})
    for group_name, group in (("source", source), ("result", result)):
        _digest(group.get("commit"), f"{group_name}.commit", SHA1_RE)
        _digest(group.get("tree"), f"{group_name}.tree", SHA1_RE)
    if not isinstance(payload.get("code_changed"), bool):
        raise ValueError("code_changed must be boolean")

    checks = payload.get("checks")
    if not isinstance(checks, list) or not checks:
        raise ValueError("checks must be a non-empty list")
    names: set[str] = set()
    for check in checks:
        if not isinstance(check, dict) or not isinstance(check.get("name"), str):
            raise ValueError("each check requires a name")
        if check["name"] in names:
            raise ValueError("check names must be unique")
        names.add(check["name"])
        if not isinstance(check.get("command"), str) or not check["command"].strip():
            raise ValueError("each check requires an exact command")
        if check.get("exit_code") != 0:
            raise ValueError(f"check did not pass: {check['name']}")
        _validate_check_semantics(check)
    if not REQUIRED_CHECKS.issubset(names):
        raise ValueError("git_diff_check and boundary_scan are required")
    focused = next((check for check in checks if check["name"] == "focused_tests"), None)
    if focused and (type(focused.get("test_count")) is not int or focused["test_count"] <= 0):
        raise ValueError("focused_tests requires a positive observed test count")
    if payload["code_changed"]:
        if not focused:
            raise ValueError("code changes require a positive focused test count")
    elif source != result:
        raise ValueError("code_changed=false requires identical source and result refs")

    callback = payload.get("callback", {})
    if not isinstance(callback.get("path"), str) or not callback["path"].strip():
        raise ValueError("callback.path is required")
    _digest(callback.get("sha256"), "callback.sha256", SHA256_RE)
    for artifact in payload.get("artifacts", []):
        if not isinstance(artifact, dict) or not artifact.get("path"):
            raise ValueError("every artifact requires a path")
        _digest(artifact.get("sha256"), "artifact.sha256", SHA256_RE)

    push = payload.get("push", {})
    if not isinstance(push.get("required"), bool):
        raise ValueError("push.required must be boolean")
    if push["required"]:
        for field in ("remote", "ref"):
            if not isinstance(push.get(field), str) or not push[field].strip():
                raise ValueError(f"push.{field} is required")
        commit = _digest(push.get("commit"), "push.commit", SHA1_RE)
        if commit != result["commit"]:
            raise ValueError("pushed commit must equal result commit")
    if payload.get("missing_evidence") or payload.get("evidence_conflicts"):
        raise ValueError("green gate cannot contain missing or conflicting evidence")


def validate_file(path: Path, *, execute_commands: bool = True) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("gate must be a JSON object")
    validate_payload(payload)

    workspace = Path(payload["workspace_root"]).resolve()
    if not workspace.is_dir():
        raise ValueError("workspace_root does not exist")
    packet_dir = Path(payload["task_packet"]["dir"]).resolve()
    spec = packet_dir / "spec.md"
    if not spec.is_file() or _sha256(spec) != payload["task_packet"]["spec_sha256"]:
        raise ValueError("task packet spec hash does not match")
    try:
        from scripts.validate_task_packet import validate as validate_packet
    except ModuleNotFoundError:
        from validate_task_packet import validate as validate_packet
    validate_packet(packet_dir)
    facts = _metadata(spec.read_text(encoding="utf-8"))
    if facts.get("TASK_ID") != payload["task_id"]:
        raise ValueError("task id differs from task packet")
    if facts.get("MODEL_ROLE") != payload["model_role"] or facts.get("MODEL") != payload["model"]:
        raise ValueError("gate execution role/model differs from task packet")
    if facts.get("SOURCE_COMMIT") != payload["source"]["commit"] or facts.get("SOURCE_TREE") != payload["source"]["tree"]:
        raise ValueError("source refs differ from task packet")
    commands = _rooted(packet_dir, facts.get("AUTOMATED_GATE_COMMANDS"), "AUTOMATED_GATE_COMMANDS")
    if _sha256(commands) != facts.get("AUTOMATED_GATE_COMMANDS_SHA256"):
        raise ValueError("expected command file hash does not match")
    expected = [line.strip() for line in commands.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if [check["command"] for check in payload["checks"]] != expected:
        raise ValueError("checks must exactly match the task packet commands")

    callback_path = _rooted(packet_dir, payload["callback"]["path"], "callback.path")
    if _sha256(callback_path) != payload["callback"]["sha256"]:
        raise ValueError("callback hash does not match")
    callback = json.loads(callback_path.read_text(encoding="utf-8"))
    callback_status = EXECUTION_ROLE_BINDINGS[payload["model_role"]]["callback_status"]
    if (
        callback.get("task_id") != payload["task_id"]
        or callback.get("execution_id") != payload["execution_id"]
        or callback.get("status") != callback_status
        or callback.get("model") != payload["model"]
        or callback.get("source") != payload["source"]
        or callback.get("result") != payload["result"]
    ):
        raise ValueError("callback does not match the gate")
    for artifact in payload.get("artifacts", []):
        artifact_path = _rooted(workspace, artifact["path"], "artifact.path")
        if _sha256(artifact_path) != artifact["sha256"]:
            raise ValueError(f"artifact hash mismatch: {artifact['path']}")

    source = payload["source"]
    result = payload["result"]
    if _git(workspace, "show", "-s", "--format=%T", source["commit"]) != source["tree"]:
        raise ValueError("source commit/tree mismatch")
    if _git(workspace, "show", "-s", "--format=%T", result["commit"]) != result["tree"]:
        raise ValueError("result commit/tree mismatch")
    if _git(workspace, "rev-parse", "HEAD") != result["commit"]:
        raise ValueError("workspace HEAD must equal result commit")
    if _git(workspace, "status", "--porcelain"):
        raise ValueError("automated gate requires a clean result worktree")
    changed_paths = _git(workspace, "diff", "--name-only", source["commit"], result["commit"])
    if payload["code_changed"]:
        if source == result or not changed_paths:
            raise ValueError("code_changed=true requires a nonempty source-to-result diff")
        completed = subprocess.run(
            ["git", "-C", str(workspace), "merge-base", "--is-ancestor", source["commit"], result["commit"]],
            check=False,
        )
        if completed.returncode:
            raise ValueError("source commit is not an ancestor of result commit")
    elif changed_paths:
        raise ValueError("code_changed=false requires an empty source-to-result diff")
    _git(workspace, "diff", "--check", source["commit"], result["commit"])

    boundary_check = next(check for check in payload["checks"] if check["name"] == "boundary_scan")
    _validate_boundary_command(workspace, source["commit"], boundary_check)
    focused_check = next(
        (check for check in payload["checks"] if check["name"] == "focused_tests"),
        None,
    )
    if focused_check:
        _validate_focused_test_runtime(workspace, focused_check)

    if execute_commands:
        for check in payload["checks"]:
            output = _run_expected_command(workspace, check["command"])
            if check["name"] == "focused_tests":
                counts = [int(value) for value in PYTEST_SUMMARY_RE.findall(output)]
                actual_count = counts[-1] if counts else 0
                if actual_count != check["test_count"]:
                    raise ValueError(
                        "focused_tests test_count differs from the executed pytest summary: "
                        f"claimed {check['test_count']}, observed {actual_count}"
                    )
        if _git(workspace, "status", "--porcelain"):
            raise ValueError("gate commands must leave the result worktree clean")

    push = payload["push"]
    if push["required"]:
        output = _git(workspace, "ls-remote", "--exit-code", push["remote"], push["ref"])
        if [row.split() for row in output.splitlines() if row.strip()] != [[push["commit"], push["ref"]]]:
            raise ValueError("live remote ref differs from the result commit")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    validate_file(args.manifest)
    print("automated gate manifest: GREEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
