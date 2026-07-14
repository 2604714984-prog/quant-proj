#!/usr/bin/env python3
"""Run a gate once and bind immutable command logs into an attestation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re

try:
    from scripts.validate_automated_gate_manifest import (
        EXECUTION_ATTESTED,
        TASK_UUID_RE,
        _git,
        environment_identity,
        execute_command_evidence,
        validate_file,
    )
except ModuleNotFoundError:
    from validate_automated_gate_manifest import (
        EXECUTION_ATTESTED,
        TASK_UUID_RE,
        _git,
        environment_identity,
        execute_command_evidence,
        validate_file,
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _inside(root: Path, path: Path) -> bool:
    return path == root or root in path.parents


def _write_new_private(path: Path, payload: bytes) -> None:
    if path.exists() or not path.parent.is_dir():
        raise ValueError(f"attestation output must be a new file: {path}")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(payload)
            handle.flush()
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def create_attestation(
    gate_path: Path,
    *,
    execution_task_id: str,
    reasoning_effort: str,
    dependency_lock: Path,
    output_path: Path,
) -> Path:
    if TASK_UUID_RE.fullmatch(execution_task_id) is None:
        raise ValueError("execution_task_id must be a concrete task UUID")
    if reasoning_effort not in {"medium", "high"}:
        raise ValueError("reasoning_effort must be medium or high")
    gate_path = gate_path.resolve()
    payload = json.loads(gate_path.read_text(encoding="utf-8"))
    if payload.get("execution_attestation") is not None:
        raise ValueError("gate already contains an execution attestation")
    if validate_file(gate_path, execute_commands=False) != "MANIFEST_VALID":
        raise ValueError("gate structure is not MANIFEST_VALID")
    workspace = Path(payload["workspace_root"]).resolve()
    packet_dir = Path(payload["task_packet"]["dir"]).resolve()
    output_path = output_path.resolve()
    if not _inside(packet_dir, output_path):
        raise ValueError("execution attestation must be inside the task packet")
    dependency_lock = dependency_lock.resolve()
    if not _inside(workspace, dependency_lock) or not dependency_lock.is_file():
        raise ValueError("dependency lock must be a workspace file")
    relative_lock = dependency_lock.relative_to(workspace).as_posix()
    if _git(
        workspace,
        "ls-tree",
        "-r",
        "--name-only",
        payload["result"]["commit"],
        "--",
        relative_lock,
    ) != relative_lock:
        raise ValueError("dependency lock must be tracked by the result commit")

    log_dir = output_path.parent / f"{output_path.stem}_logs"
    if log_dir.exists():
        raise ValueError("execution log directory already exists")
    log_dir.mkdir(mode=0o700)
    os.chmod(log_dir, 0o700)
    check_records = []
    try:
        for index, check in enumerate(payload["checks"]):
            evidence, stdout, stderr = execute_command_evidence(workspace, check)
            if evidence["exit_code"] != check["exit_code"]:
                raise ValueError(f"attested command failed: {check['name']}")
            if check["name"] == "focused_tests" and evidence["test_count"] != check["test_count"]:
                raise ValueError(
                    "attested focused test count differs from the manifest"
                )
            safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", check["name"])
            stdout_path = log_dir / f"{index:02d}_{safe_name}.stdout.log"
            stderr_path = log_dir / f"{index:02d}_{safe_name}.stderr.log"
            _write_new_private(stdout_path, stdout)
            _write_new_private(stderr_path, stderr)
            evidence["stdout_log"] = {
                "path": stdout_path.relative_to(packet_dir).as_posix(),
                "sha256": _sha256(stdout_path),
            }
            evidence["stderr_log"] = {
                "path": stderr_path.relative_to(packet_dir).as_posix(),
                "sha256": _sha256(stderr_path),
            }
            check_records.append(evidence)
        if _git(workspace, "status", "--porcelain"):
            raise ValueError("attested commands left the result worktree dirty")
        attestation = {
            "checks": check_records,
            "dependency_lock": {
                "path": relative_lock,
                "sha256": _sha256(dependency_lock),
            },
            "environment": environment_identity(),
            "execution_id": payload["execution_id"],
            "execution_task_id": execution_task_id,
            "executor_identity": {
                "model": payload["model"],
                "reasoning_effort": reasoning_effort,
                "role": payload["model_role"],
                "task_id": execution_task_id,
            },
            "model": payload["model"],
            "model_role": payload["model_role"],
            "result": payload["result"],
            "schema_version": 1,
            "source": payload["source"],
            "status": EXECUTION_ATTESTED,
            "task_id": payload["task_id"],
            "workspace_root": str(workspace),
        }
        _write_new_private(
            output_path,
            (json.dumps(attestation, indent=2, sort_keys=True) + "\n").encode(
                "utf-8"
            ),
        )
    except Exception:
        # Failed attempts are not execution evidence. Preserve no partial logs.
        for candidate in sorted(log_dir.glob("*")):
            candidate.unlink(missing_ok=True)
        log_dir.rmdir()
        raise

    payload["evidence_state"] = EXECUTION_ATTESTED
    payload["execution_attestation"] = {
        "path": output_path.relative_to(packet_dir).as_posix(),
        "sha256": _sha256(output_path),
    }
    temporary_gate = gate_path.with_name(f".{gate_path.name}.{os.getpid()}.tmp")
    _write_new_private(
        temporary_gate,
        (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    os.replace(temporary_gate, gate_path)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("gate", type=Path)
    parser.add_argument("--execution-task-id", required=True)
    parser.add_argument("--reasoning-effort", choices=("medium", "high"), required=True)
    parser.add_argument("--dependency-lock", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = create_attestation(
        args.gate,
        execution_task_id=args.execution_task_id,
        reasoning_effort=args.reasoning_effort,
        dependency_lock=args.dependency_lock,
        output_path=args.output,
    )
    print(f"execution attestation: {EXECUTION_ATTESTED}; sha256={_sha256(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
