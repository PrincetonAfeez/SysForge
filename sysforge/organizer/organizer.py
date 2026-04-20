from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import typer

from sysforge.common import (
    human_size,
    is_hidden_path,
    load_json_file,
    print_error,
    write_json_file,
)
from sysforge.logging_utils import get_logger
from sysforge.shared_config import load_shared_config
from sysforge.sysforge_paths import (
    ensure_home_layout,
    get_default_organizer_rules_path,
    get_organizer_log_dir,
)

app = typer.Typer(help="Organize files in a folder based on extension, date, or size.")
logger = get_logger("sysforge.organizer")






























def main() -> None:
    app()


if __name__ == "__main__":
    main()
