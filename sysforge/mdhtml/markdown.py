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


















def main() -> None:
    app()


if __name__ == "__main__":
    main()
