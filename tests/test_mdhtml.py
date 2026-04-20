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

def test_parse_frontmatter_invalid_line(tmp_path: Path) -> None:
    src = tmp_path / "a.md"
    text = "---\nno colon line\n---\n"
    with pytest.raises(ValueError, match="invalid frontmatter"):
        mdhtml.parse_frontmatter(text, src)


def test_collect_markdown_files_case_insensitive(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    (root / "a.md").write_text("a", encoding="utf-8")
    (root / "b.MD").write_text("b", encoding="utf-8")
    (root / "c.txt").write_text("c", encoding="utf-8")
    found = mdhtml.collect_markdown_files(root)
    assert {p.name for p in found} == {"a.md", "b.MD"}

def test_parse_markdown_image_target() -> None:
    assert mdhtml._parse_markdown_image_target("  ./x.png  ") == "./x.png"
    assert mdhtml._parse_markdown_image_target("<img/foo.png>") == "img/foo.png"
    assert mdhtml._parse_markdown_image_target('x.png "title"') == "x.png"
    assert mdhtml._parse_markdown_image_target("https://ex/a.png") == "https://ex/a.png"
    assert mdhtml._parse_markdown_image_target("data:image/png;base64,xx") is None


def test_index_href_for_output_relative(tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    f = out / "sub" / "a.html"
    f.parent.mkdir(parents=True)
    f.write_text("x", encoding="utf-8")
    href = mdhtml._index_href_for_output(f, out)
    assert href.replace("\\", "/") == "sub/a.html"

def test_render_template_order_preserves_body_literals(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    tpl = tmp_path / "t.html"
    tpl.write_text(
        "T={{theme_css}}|P={{pygments_css}}|TI={{title}}|G={{generated_at}}|C={{content}}",
        encoding="utf-8",
    )
    monkeypatch.setattr(mdhtml, "load_theme_css", lambda _name: "THEME")
    monkeypatch.setattr(mdhtml, "build_pygments_css", lambda: "PYG")

    html = mdhtml.render_html_document(
        "BODY_{{theme_css}}_END",
        title="T",
        generated_at="G",
        template_path=tpl,
        theme_name="light",
    )
    assert "BODY_{{theme_css}}_END" in html
    assert "THEME" in html and "PYG" in html
