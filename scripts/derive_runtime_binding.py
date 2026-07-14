#!/usr/bin/env python3
"""Derive active high-risk runtime binding from Python AST instead of matrix claims."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any


class RuntimeBindingError(ValueError):
    """Raised when a sensitive active runtime path is missing or differs."""


def _module_for(root: Path, path: Path) -> str:
    relative = path.relative_to(root).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _imports(tree: ast.AST) -> set[str]:
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module)
    return result


def _call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _conditional_returns(function: ast.AST) -> list[list[str]]:
    result: list[list[str]] = []
    for node in ast.walk(function):
        if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
            continue
        test = node.test
        if (
            isinstance(test.left, ast.Name)
            and len(test.ops) == 1
            and isinstance(test.ops[0], ast.Eq)
            and len(test.comparators) == 1
            and isinstance(test.comparators[0], ast.Constant)
            and isinstance(test.comparators[0].value, str)
        ):
            for body_node in node.body:
                if isinstance(body_node, ast.Return) and isinstance(body_node.value, ast.Call):
                    call = _call_name(body_node.value)
                    if call:
                        result.append([test.left.id, test.comparators[0].value, call])
    return result


def derive(source_root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    module_imports: dict[str, set[str]] = {}
    definitions: dict[str, set[str]] = {}
    cli_sensitive: set[str] = set()
    function_calls: dict[str, list[str]] = {}
    return_calls: dict[str, list[str]] = {}
    conditional_returns: dict[str, list[list[str]]] = {}
    sensitive = set(contract["sensitive_modules"])
    for path in sorted((source_root / "usq").rglob("*.py")):
        module = _module_for(source_root, path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        module_imports[module] = _imports(tree)
        definitions[module] = {
            node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        }
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                key = f"{module}.{node.name}"
                function_calls[key] = sorted(
                    {
                        name
                        for item in ast.walk(node)
                        if isinstance(item, ast.Call)
                        for name in [_call_name(item)]
                        if name is not None
                    }
                )
                return_calls[key] = sorted(
                    {
                        name
                        for item in ast.walk(node)
                        if isinstance(item, ast.Return) and isinstance(item.value, ast.Call)
                        for name in [_call_name(item.value)]
                        if name is not None
                    }
                )
                conditional_returns[key] = sorted(_conditional_returns(node))
        if module == "usq.cli":
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if _imports(node) & sensitive:
                        cli_sensitive.add(node.name)
    edges = sorted(
        [source, target]
        for source, imports in module_imports.items()
        for target in imports
        if target in sensitive
    )
    required_definition_modules = {item[0] for item in contract["required_definitions"]}
    required_function_keys = {
        f"{module}.{function}"
        for module, function, _call in contract["required_function_calls"]
    }
    required_return_keys = {
        f"{module}.{function}"
        for module, function, _call in contract["required_return_calls"]
    }
    required_conditional_keys = {
        f"{module}.{function}"
        for module, function, _variable, _value, _call
        in contract["required_conditional_return_calls"]
    }
    return {
        "cli_sensitive_functions": sorted(cli_sensitive),
        "sensitive_module_edges": edges,
        "definitions": {
            module: sorted(definitions[module]) for module in sorted(required_definition_modules)
        },
        "function_calls": {
            key: function_calls.get(key, []) for key in sorted(required_function_keys)
        },
        "return_calls": {
            key: return_calls.get(key, []) for key in sorted(required_return_keys)
        },
        "conditional_return_calls": {
            key: conditional_returns.get(key, []) for key in sorted(required_conditional_keys)
        },
    }


def validate(source_root: Path, contract: dict[str, Any], *, require_git: bool = True) -> dict[str, Any]:
    expected_keys = {
        "schema_version", "repository", "commit", "sensitive_modules",
        "expected_cli_functions", "required_module_edges", "required_definitions",
        "required_function_calls", "required_return_calls",
        "required_conditional_return_calls",
        "strategy_candidate_available",
    }
    if set(contract) != expected_keys or contract["schema_version"] != "runtime-binding-contract-v1":
        raise RuntimeBindingError("runtime contract shape differs")
    if contract["strategy_candidate_available"] is not False:
        raise RuntimeBindingError("candidate boundary differs")
    if require_git:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=source_root, check=True, capture_output=True, text=True
        ).stdout.strip()
        if head != contract["commit"]:
            raise RuntimeBindingError("source checkout HEAD differs from pinned contract")
        dirty = subprocess.run(
            ["git", "status", "--porcelain=v1"],
            cwd=source_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        if dirty:
            raise RuntimeBindingError("source checkout is dirty")
    derived = derive(source_root, contract)
    if derived["cli_sensitive_functions"] != sorted(contract["expected_cli_functions"]):
        raise RuntimeBindingError("active sensitive CLI function set differs")
    edge_set = {tuple(item) for item in derived["sensitive_module_edges"]}
    expected_edge_set = {tuple(item) for item in contract["required_module_edges"]}
    if edge_set != expected_edge_set:
        raise RuntimeBindingError(
            "executable sensitive import edge set differs: "
            f"missing={sorted(expected_edge_set - edge_set)}, "
            f"unexpected={sorted(edge_set - expected_edge_set)}"
        )
    for module, name in contract["required_definitions"]:
        if name not in derived["definitions"].get(module, []):
            raise RuntimeBindingError(f"required active definition missing: {module}.{name}")
    for module, function, call in contract["required_function_calls"]:
        if call not in derived["function_calls"].get(f"{module}.{function}", []):
            raise RuntimeBindingError(f"required function call missing: {module}.{function}->{call}")
    for module, function, call in contract["required_return_calls"]:
        if call not in derived["return_calls"].get(f"{module}.{function}", []):
            raise RuntimeBindingError(f"required return call missing: {module}.{function}->{call}")
    for module, function, variable, value, call in contract["required_conditional_return_calls"]:
        proof = [variable, value, call]
        if proof not in derived["conditional_return_calls"].get(f"{module}.{function}", []):
            raise RuntimeBindingError(
                f"required conditional return missing: {module}.{function}:{variable}={value}->{call}"
            )
    return derived


def evidence_projection(derived: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    call_requirements: dict[str, set[str]] = {}
    for module, function, call in contract["required_function_calls"]:
        call_requirements.setdefault(f"{module}.{function}", set()).add(call)
    definition_requirements: dict[str, set[str]] = {}
    for module, name in contract["required_definitions"]:
        definition_requirements.setdefault(module, set()).add(name)
    return {
        "cli_sensitive_functions": derived["cli_sensitive_functions"],
        "sensitive_module_edges": derived["sensitive_module_edges"],
        "definitions": {
            module: sorted(definition_requirements[module])
            for module in sorted(definition_requirements)
        },
        "function_calls": {
            key: sorted(call_requirements[key]) for key in sorted(call_requirements)
        },
        "return_calls": {
            f"{module}.{function}": [call]
            for module, function, call in contract["required_return_calls"]
        },
        "conditional_return_calls": {
            f"{module}.{function}": [[variable, value, call]]
            for module, function, variable, value, call
            in contract["required_conditional_return_calls"]
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    derived = validate(args.source_repo.resolve(), contract)
    result = {
        "schema_version": "runtime-binding-result-v1",
        "source_commit": contract["commit"],
        "contract_sha256": hashlib.sha256(args.contract.read_bytes()).hexdigest(),
        "derived": evidence_projection(derived, contract),
        "strategy_candidate_available": False,
    }
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
