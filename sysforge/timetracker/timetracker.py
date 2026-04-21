from __future__ import annotations

import secrets
from datetime import datetime, timedelta, tzinfo
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import typer

from sysforge.common import (
    append_csv_rows,
    format_duration,
    load_json_file,
    parse_local_datetime,
    print_error,
    write_json_file,
)
from sysforge.logging_utils import get_logger
from sysforge.shared_config import load_shared_config
from sysforge.sysforge_paths import ensure_home_layout, get_timesheet_file

app = typer.Typer(help="Track work sessions and export time reports.")
logger = get_logger("sysforge.timetracker")





















def main() -> None:
    app()


if __name__ == "__main__":
    main()
