from __future__ import annotations

import importlib
import os
import re
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, cast

import typer

from sysforge.common import (
    load_json_file,
    print_error,
    write_json_file,
    write_text_file,
)
from sysforge.logging_utils import get_logger
from sysforge.shared_config import load_shared_config
from sysforge.sysforge_paths import (
    ensure_home_layout,
    get_docs_history_file,
    get_markdown_template_path,
    get_theme_path,
)

app = typer.Typer(help="Convert Markdown files into styled HTML.")
logger = get_logger("sysforge.mdhtml")
IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\(\s*([^)]+?)\s*\)")


def _parse_markdown_image_target(raw: str) -> str | None:
    inner = raw.strip()
    if not inner or inner.lower().startswith("data:"):
        return None
    if inner.startswith("<"):
        end = inner.find(">")
        inner = inner[1:end].strip() if end != -1 else inner[1:].strip()
    else:
        inner = inner.split(None, 1)[0].strip()
    inner = inner.strip("\"'")
    return inner or None

def _replace_placeholder_once(template: str, key: str, value: str) -> str:
    marker = f"{{{{{key}}}}}"
    if marker not in template:
        raise ValueError(f"Template is missing placeholder: {marker}")
    before, sep, after = template.partition(marker)
    return before + value + after

def _apply_html_template(
    template: str,
    *,
    theme_css: str,
    pygments_css: str,
    title: str,
    generated_at: str,
    content: str,
) -> str:

    result = template
    result = _replace_placeholder_once(result, "theme_css", theme_css)
    result = _replace_placeholder_once(result, "pygments_css", pygments_css)
    result = _replace_placeholder_once(result, "title", title)
    result = _replace_placeholder_once(result, "generated_at", generated_at)
    result = _replace_placeholder_once(result, "content", content)
    return result

def load_markdown_dependency() -> Any:
    try:
        return importlib.import_module("markdown")
    except ModuleNotFoundError:
        print_error(
            "The markdown package is not installed. Run `pip install -e .` first.",
            exit_code=2,
        )


def load_pygments_formatter() -> Any:
    try:
        pygments_module = importlib.import_module("pygments.formatters")
        return pygments_module.HtmlFormatter
    except ModuleNotFoundError:
        print_error("Pygments is not installed. Run `pip install -e .` first.", exit_code=2)

def _strip_optional_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value

def parse_frontmatter(raw_text: str, source: Path) -> tuple[dict[str, str], str]:
    if not raw_text.startswith("---\n"):
        return {}, raw_text

    lines = raw_text.splitlines()
    frontmatter: dict[str, str] = {}
    last_key: str | None = None

    for line_number in range(1, len(lines)):
        line = lines[line_number]
        stripped = line.strip()
        if stripped == "---":
            body = "\n".join(lines[line_number + 1 :])
            return frontmatter, body
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in line:
            if last_key is None:
                raise ValueError(f"{source}: invalid frontmatter line {line_number + 1}")
            frontmatter[last_key] = f"{frontmatter[last_key]}\n{line.rstrip()}"
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = _strip_optional_quotes(value.strip())
        frontmatter[key] = value
        last_key = key

    raise ValueError(f"{source}: frontmatter was opened but not closed")

def guess_title(frontmatter: dict[str, str], body: str, source: Path) -> str:
    title = frontmatter.get("title", "").strip()
    if title:
        return title
    for line in body.splitlines():
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return source.stem.replace("_", " ").title()

def load_template(template_path: Path | None) -> str:
    if template_path is None:
        template_path = get_markdown_template_path()
    return template_path.read_text(encoding="utf-8")

def load_theme_css(theme_name: str) -> str:
    theme_path = get_theme_path(theme_name)
    if not theme_path.exists():
        print_error(f"Theme not found: {theme_name}")
    return theme_path.read_text(encoding="utf-8")

def build_pygments_css() -> str:
    formatter_class = load_pygments_formatter()
    return cast(str, formatter_class().get_style_defs(".codehilite"))











def main() -> None:
    app()


if __name__ == "__main__":
    main()
