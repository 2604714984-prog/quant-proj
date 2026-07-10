#!/usr/bin/env python3
"""Validate the single execution record used before Luna acceptance."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess


SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_CHECKS = {"git_diff_check", "boundary_scan"}


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


def _run_expected_command(root: Path, command: str) -> None:
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        raise ValueError(f"invalid expected command: {command}") from exc
    if not argv:
        raise ValueError("expected command cannot be empty")
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


def validate_payload(payload: dict) -> None:
    if payload.get("template_only") is True:
        raise ValueError("template-only gate cannot enter acceptance")
    if payload.get("schema_version") != 1:
        raise ValueError("schema_version must be 1")
    for field in ("task_id", "execution_id", "workspace_root"):
        if not isinstance(payload.get(field), str) or not payload[field].strip():
            raise ValueError(f"{field} is required")
    if payload.get("model_role") != "executor" or payload.get("model") != "gpt-5.6-luna":
        raise ValueError("gate must be emitted by a Luna executor")
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
    if not REQUIRED_CHECKS.issubset(names):
        raise ValueError("git_diff_check and boundary_scan are required")
    if payload["code_changed"]:
        focused = next((check for check in checks if check["name"] == "focused_tests"), None)
        if not focused or not isinstance(focused.get("test_count"), int) or focused["test_count"] <= 0:
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
    if (
        callback.get("task_id") != payload["task_id"]
        or callback.get("execution_id") != payload["execution_id"]
        or callback.get("status") != "LUNA_EXECUTION_COMPLETE"
        or callback.get("model") != "gpt-5.6-luna"
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

    if execute_commands:
        for check in payload["checks"]:
            _run_expected_command(workspace, check["command"])
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
