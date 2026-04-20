from __future__ import annotations

from pathlib import Path

import pytest

from sysforge.mdhtml import markdown as mdhtml

def test_parse_frontmatter_none() -> None:
    fm, body = mdhtml.parse_frontmatter("Hello\n", Path("x.md"))
    assert fm == {}
    assert body == "Hello\n"

def test_parse_frontmatter_basic(tmp_path: Path) -> None:
    src = tmp_path / "a.md"
    text = "---\ntitle: Hello\ndate: 2024-01-01\n---\nBody here\n"
    fm, body = mdhtml.parse_frontmatter(text, src)
    assert fm == {"title": "Hello", "date": "2024-01-01"}
    assert body == "Body here"

def test_parse_frontmatter_skips_blank_and_comments(tmp_path: Path) -> None:
    src = tmp_path / "a.md"
    text = "---\n\n# ignored in fm\ntitle: 'Quoted'\n\n---\nOK\n"
    fm, body = mdhtml.parse_frontmatter(text, src)
    assert fm["title"] == "Quoted"
    assert body == "OK"


def test_parse_frontmatter_continuation(tmp_path: Path) -> None:
    src = tmp_path / "a.md"
    text = "---\nsummary: first line\n second line\n---\nX\n"
    fm, body = mdhtml.parse_frontmatter(text, src)
    assert fm["summary"] == "first line\n second line"
    assert body == "X"
