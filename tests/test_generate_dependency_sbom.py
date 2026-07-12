from __future__ import annotations

from pathlib import Path

import pytest

from scripts.generate_dependency_sbom import canonical_name, parse_lock


def test_parse_lock_requires_exact_unique_pins(tmp_path: Path) -> None:
    lock = tmp_path / "requirements.lock"
    lock.write_text(
        "Example_Pkg==1.2.3 \\\n"
        "    --hash=sha256:" + "a" * 64 + "\n",
        encoding="utf-8",
    )
    assert parse_lock(lock) == {"example-pkg": "1.2.3"}


@pytest.mark.parametrize(
    "line",
    ["example>=1.0\n", "example\n", "example==1\nexample==1\n"],
)
def test_parse_lock_fails_closed_on_unlocked_or_duplicate_lines(
    tmp_path: Path,
    line: str,
) -> None:
    lock = tmp_path / "requirements.lock"
    lock.write_text(line, encoding="utf-8")
    with pytest.raises(ValueError):
        parse_lock(lock)


def test_canonical_name_matches_python_distribution_rules() -> None:
    assert canonical_name("Some_Package.Name") == "some-package-name"
