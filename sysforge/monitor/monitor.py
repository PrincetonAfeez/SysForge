from __future__ import annotations

import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import typer

from sysforge.common import (
    append_json_line,
    format_duration,
    human_size,
    print_error,
    write_json_file,
)
from sysforge.config.config import load_config_file
from sysforge.logging_utils import get_logger
from sysforge.shared_config import load_shared_config
from sysforge.sysforge_paths import (
    ensure_home_layout,
    get_health_log_file,
    get_latest_health_file,
)

app = typer.Typer(help="Check CPU, memory, disks, and uptime.")
logger = get_logger("sysforge.monitor")



















def main() -> None:
    app()


if __name__ == "__main__":
    main()
