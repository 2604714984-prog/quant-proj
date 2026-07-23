from __future__ import annotations

from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(
    0,
    str(
        REPO_ROOT
        / "research/archive/us_qqq_disclosed_top50_equal_weight_v1/scripts"
    ),
)

import complete_us_qqq_atvi_identity_v1 as completion  # noqa: E402


def test_sec_cover_page_identity_text_passes() -> None:
    completion._validate_source(
        b"<html>Activision Blizzard, Inc. ATVI Nasdaq Global Select Market</html>"
    )


def test_missing_trading_symbol_fails_closed() -> None:
    with pytest.raises(completion.CompletionError, match="missing"):
        completion._validate_source(
            b"<html>Activision Blizzard, Inc. Nasdaq Global Select Market</html>"
        )
