from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from scripts.validate_remediation_checksums import validate


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path) -> Path:
    artifact = tmp_path / "reports/remediation/FINAL_CONTROLLER_ROOT.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("{}\n", encoding="utf-8")
    checksums = tmp_path / "reports/remediation/CHECKSUMS.sha256"
    checksums.write_text(
        f"{_digest(artifact)}  reports/remediation/FINAL_CONTROLLER_ROOT.json\n",
        encoding="utf-8",
    )
    return checksums


def test_checksum_chain_validates(tmp_path: Path) -> None:
    assert validate(_fixture(tmp_path), repository_root=tmp_path) == 1


@pytest.mark.parametrize("mutation", ["digest", "traversal", "duplicate", "self"])
def test_checksum_chain_mutations_fail_closed(tmp_path: Path, mutation: str) -> None:
    checksums = _fixture(tmp_path)
    line = checksums.read_text(encoding="utf-8").strip()
    if mutation == "digest":
        payload = "f" * 64 + line[64:] + "\n"
    elif mutation == "traversal":
        payload = "f" * 64 + "  ../outside.json\n"
    elif mutation == "duplicate":
        payload = line + "\n" + line + "\n"
    else:
        payload = line + "\n" + "f" * 64 + "  reports/remediation/CHECKSUMS.sha256\n"
    checksums.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError):
        validate(checksums, repository_root=tmp_path)
