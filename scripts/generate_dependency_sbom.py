#!/usr/bin/env python3
"""Generate a deterministic CycloneDX SBOM from a hash-locked requirements file."""

from __future__ import annotations

import argparse
import hashlib
from importlib import metadata
import json
from pathlib import Path
import re


LOCK_LINE = re.compile(r"^([A-Za-z0-9_.-]+)==([^\\\s]+)\s*(?:\\)?$")
DENIED_LICENSE_MARKERS = ("AGPL", "SSPL", "BUSINESS SOURCE", "PROPRIETARY")


def canonical_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_lock(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if raw_line.startswith((" ", "#", "--")) or not raw_line:
            continue
        match = LOCK_LINE.fullmatch(raw_line)
        if match is None:
            raise ValueError(f"unsupported unlocked requirement line: {raw_line!r}")
        name = canonical_name(match.group(1))
        version = match.group(2)
        if name in result:
            raise ValueError(f"duplicate locked distribution: {name}")
        result[name] = version
    if not result:
        raise ValueError("requirements lock contains no distributions")
    return result


def _classifier_license(classifier: str) -> str | None:
    mapping = {
        "License :: OSI Approved :: Apache Software License": "Apache-2.0",
        "License :: OSI Approved :: BSD License": "BSD-3-Clause",
        "License :: OSI Approved :: ISC License (ISCL)": "ISC",
        "License :: OSI Approved :: MIT License": "MIT",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
        "License :: OSI Approved :: Python Software Foundation License": "PSF-2.0",
    }
    return mapping.get(classifier)


def distribution_license(dist: metadata.Distribution) -> str:
    expression = str(dist.metadata.get("License-Expression") or "").strip()
    if expression:
        result = expression
    else:
        classifiers = [
            _classifier_license(value)
            for value in dist.metadata.get_all("Classifier", [])
            if value.startswith("License ::")
        ]
        normalized = sorted({value for value in classifiers if value})
        raw = str(dist.metadata.get("License") or "").strip()
        if normalized:
            result = " OR ".join(normalized)
        elif raw and len(raw) <= 120 and "\n" not in raw:
            result = raw
        else:
            raise ValueError(f"license is not machine-reported for {dist.metadata['Name']}")
    upper = result.upper()
    if any(marker in upper for marker in DENIED_LICENSE_MARKERS):
        raise ValueError(f"denied license for {dist.metadata['Name']}: {result}")
    return result


def build_sbom(
    *,
    lock_path: Path,
    repository: str,
    commit: str,
    tree: str,
) -> dict[str, object]:
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise ValueError("commit must be a full lowercase Git object ID")
    if re.fullmatch(r"[0-9a-f]{40}", tree) is None:
        raise ValueError("tree must be a full lowercase Git object ID")
    locked = parse_lock(lock_path)
    installed = {
        canonical_name(dist.metadata["Name"]): dist for dist in metadata.distributions()
    }
    components: list[dict[str, object]] = []
    for name, version in sorted(locked.items()):
        dist = installed.get(name)
        if dist is None:
            raise ValueError(f"locked distribution is not installed: {name}=={version}")
        if dist.version != version:
            raise ValueError(
                f"installed version drift for {name}: {dist.version!r} != {version!r}"
            )
        components.append(
            {
                "type": "library",
                "name": name,
                "version": version,
                "purl": f"pkg:pypi/{name}@{version}",
                "licenses": [{"expression": distribution_license(dist)}],
            }
        )
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": (
            "urn:uuid:"
            + hashlib.sha256(
                f"{repository}|{commit}|{tree}|{sha256_file(lock_path)}".encode()
            ).hexdigest()[:32]
        ),
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": repository,
                "version": commit,
                "properties": [
                    {"name": "git.commit", "value": commit},
                    {"name": "git.tree", "value": tree},
                    {"name": "requirements.lock.sha256", "value": sha256_file(lock_path)},
                ],
            }
        },
        "components": components,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--tree", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build_sbom(
        lock_path=args.lock,
        repository=args.repository,
        commit=args.commit,
        tree=args.tree,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"SBOM VALID: repository={args.repository}; components={len(payload['components'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
