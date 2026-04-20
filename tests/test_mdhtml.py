from __future__ import annotations

from pathlib import Path

import pytest

from sysforge.mdhtml import markdown as mdhtml

def test_parse_frontmatter_none() -> None:
    fm, body = mdhtml.parse_frontmatter("Hello\n", Path("x.md"))
    assert fm == {}
    assert body == "Hello\n"

