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





















def main() -> None:
    app()


if __name__ == "__main__":
    main()
