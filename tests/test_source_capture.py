from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import os
from pathlib import Path

import pytest

import quant_system.data.source_identity as source_module
from quant_system.data import (
    SourceIdentity,
    SourceIdentityError,
    capture_source_file,
    require_trusted_source,
    select_source_revision,
)


UTC = timezone.utc
AVAILABLE = datetime(2026, 7, 22, 20, tzinfo=UTC)
RETRIEVED = AVAILABLE + timedelta(minutes=5)


def _manual_source(
    revision_id: str,
    *,
    available_at: datetime,
    supersedes: str | None = None,
    source_url: str = "https://example.test/data",
) -> SourceIdentity:
    return SourceIdentity(
        source_url=source_url,
        content_sha256=hashlib.sha256(revision_id.encode()).hexdigest(),
        available_at=available_at,
        retrieved_at=available_at + timedelta(minutes=1),
        revision_id=revision_id,
        source_family_id="daily-bars-v1",
        provider_id="example-provider",
        subject_id="SPY",
        supersedes_revision_id=supersedes,
    )


def test_capture_source_file_hashes_bytes_and_publication_evidence(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    publication = tmp_path / "publication.json"
    source.write_bytes(b'{"close": 100.0}\n')
    publication.write_bytes(b'{"published_at": "2026-07-22T20:00:00Z"}\n')

    receipt = capture_source_file(
        source,
        publication_evidence_path=publication,
        source_url="https://example.test/data",
        available_at=AVAILABLE,
        retrieved_at=RETRIEVED,
        revision_id="r1",
        source_family_id="daily-bars-v1",
        provider_id="example-provider",
        subject_id="SPY",
    )

    assert receipt.source.content_sha256 == hashlib.sha256(source.read_bytes()).hexdigest()
    assert receipt.source.publication_evidence_sha256 == hashlib.sha256(
        publication.read_bytes()
    ).hexdigest()
    assert receipt.byte_count == source.stat().st_size
    assert require_trusted_source(receipt.source) is receipt.source
    with pytest.raises(SourceIdentityError, match="capture entrypoint"):
        replace(receipt.source, available_at=AVAILABLE + timedelta(seconds=1))


def test_manual_source_is_experimental_only() -> None:
    with pytest.raises(SourceIdentityError, match="capture receipt"):
        require_trusted_source(_manual_source("r1", available_at=AVAILABLE))


@pytest.mark.parametrize("link_kind", ["symlink", "hardlink"])
def test_capture_rejects_link_aliases(tmp_path: Path, link_kind: str) -> None:
    source = tmp_path / "source.json"
    source.write_bytes(b"source")
    alias = tmp_path / "alias.json"
    if link_kind == "symlink":
        alias.symlink_to(source)
    else:
        os.link(source, alias)
    publication = tmp_path / "publication.json"
    publication.write_bytes(b"publication")

    with pytest.raises(SourceIdentityError, match="regular file"):
        capture_source_file(
            alias,
            publication_evidence_path=publication,
            source_url="https://example.test/data",
            available_at=AVAILABLE,
            retrieved_at=RETRIEVED,
            revision_id="r1",
            source_family_id="daily-bars-v1",
            provider_id="example-provider",
            subject_id="SPY",
        )


def test_capture_rejects_path_replacement(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source.json"
    source.write_bytes(b"source")
    publication = tmp_path / "publication.json"
    publication.write_bytes(b"publication")
    moved = tmp_path / "moved.json"
    replacement = tmp_path / "replacement.json"
    replacement.write_bytes(b"replacement")
    original_inode = source.stat().st_ino
    real_read = source_module.os.read
    replaced = False

    def replacing_read(descriptor: int, size: int) -> bytes:
        nonlocal replaced
        if not replaced and os.fstat(descriptor).st_ino == original_inode:
            replaced = True
            os.replace(source, moved)
            os.replace(replacement, source)
        return real_read(descriptor, size)

    monkeypatch.setattr(source_module.os, "read", replacing_read)
    with pytest.raises(SourceIdentityError, match="changed"):
        capture_source_file(
            source,
            publication_evidence_path=publication,
            source_url="https://example.test/data",
            available_at=AVAILABLE,
            retrieved_at=RETRIEVED,
            revision_id="r1",
            source_family_id="daily-bars-v1",
            provider_id="example-provider",
            subject_id="SPY",
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_family_id", "other-family"),
        ("provider_id", "other-provider"),
        ("subject_id", "QQQ"),
    ],
)
def test_revision_chain_rejects_semantic_drift(field: str, value: str) -> None:
    root = _manual_source("r1", available_at=AVAILABLE)
    child = _manual_source(
        "r2",
        available_at=AVAILABLE + timedelta(days=1),
        supersedes="r1",
    )
    child = replace(child, **{field: value})

    with pytest.raises(SourceIdentityError, match="source_family_id"):
        select_source_revision((root, child), as_of=AVAILABLE + timedelta(days=2))


def test_revision_chain_requires_receipt_for_url_migration() -> None:
    root = _manual_source("r1", available_at=AVAILABLE)
    child = _manual_source(
        "r2",
        available_at=AVAILABLE + timedelta(days=1),
        supersedes="r1",
        source_url="https://mirror.example.test/data",
    )
    with pytest.raises(SourceIdentityError, match="migration receipt"):
        select_source_revision((root, child), as_of=AVAILABLE + timedelta(days=2))

    migrated = replace(child, url_migration_receipt_sha256="c" * 64)
    assert (
        select_source_revision((root, migrated), as_of=AVAILABLE + timedelta(days=2))
        is migrated
    )
