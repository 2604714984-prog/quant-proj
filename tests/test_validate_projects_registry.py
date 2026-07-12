import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("registry_validator", ROOT / "scripts" / "validate_projects_registry.py")
validator = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(validator)


def _write_registry(tmp_path, payload):
    path = tmp_path / "projects.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return path


def _portable_git_registry(tmp_path, payload, monkeypatch):
    truth = {}
    by_path = {}
    for name, facts in payload["projects"].items():
        path = tmp_path / name
        path.mkdir(exist_ok=True)
        facts["path"] = str(path)
        truth[name] = {"commit": facts["commit"], "tree": facts["tree"]}
        by_path[str(path)] = name

    def fake_run(command, **kwargs):
        del kwargs
        name = by_path[command[2]]
        if command[3:5] == ["cat-file", "-t"]:
            return SimpleNamespace(returncode=0, stdout="commit\n")
        if command[3] == "rev-parse":
            target = command[4]
            if target == "HEAD":
                value = truth[name]["commit"]
            elif target.endswith("^{tree}"):
                value = truth[name]["tree"]
            elif target.endswith("~1"):
                value = "f" * 40
            else:
                value = truth[name]["commit"]
            return SimpleNamespace(returncode=0, stdout=value + "\n")
        raise AssertionError(command)

    monkeypatch.setattr(validator.subprocess, "run", fake_run)


def test_registry_requires_us_stock_30w(monkeypatch, tmp_path):
    payload = validator.load_registry()
    payload["projects"].pop("us_stock_30w")
    monkeypatch.setattr(validator, "REGISTRY", _write_registry(tmp_path, payload))
    with pytest.raises(ValueError, match="us_stock_30w"):
        validator.validate(verify_local_git=False)


def test_registry_rejects_unsafe_boundary_before_commit_check(monkeypatch, tmp_path):
    payload = validator.load_registry()
    payload["boundaries"]["daily_signal_push"] = True
    payload["projects"]["us_stock_monitor"]["commit"] = "not-a-commit"
    monkeypatch.setattr(validator, "REGISTRY", _write_registry(tmp_path, payload))
    with pytest.raises(ValueError, match="daily_signal_push"):
        validator.validate(verify_local_git=False)


def test_remote_authoritative_tree_is_verified(monkeypatch, tmp_path):
    payload = validator.load_registry()
    _portable_git_registry(tmp_path, payload, monkeypatch)
    payload["projects"]["quant_research_lab"]["tree"] = "0" * 40
    monkeypatch.setattr(validator, "REGISTRY", _write_registry(tmp_path, payload))
    with pytest.raises(ValueError, match="pinned tree mismatch"):
        validator.validate(verify_local_git=True)


def test_remote_authoritative_local_tracking_ref_is_verified(monkeypatch, tmp_path):
    payload = validator.load_registry()
    _portable_git_registry(tmp_path, payload, monkeypatch)
    payload["projects"]["quant_research_lab"]["upstream_ref"] = "origin/master~1"
    monkeypatch.setattr(validator, "REGISTRY", _write_registry(tmp_path, payload))
    with pytest.raises(ValueError, match="remote-tracking ref mismatch"):
        validator.validate(verify_local_git=True)
