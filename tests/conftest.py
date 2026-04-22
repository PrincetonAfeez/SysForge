"""Configuration for pytest."""

from __future__ import annotations

import pytest


@pytest.fixture
def isolated_sysforge_home(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Use a temp directory instead of ~/.sysforge for filesystem side effects."""
    monkeypatch.setenv("SYSFORGE_HOME", str(tmp_path / "sysforge_home"))
