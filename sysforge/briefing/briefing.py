from __future__ import annotations

import platform
import random
import shutil
import sys
import textwrap
import time
from datetime import datetime, tzinfo
from pathlib import Path
from typing import Any, cast
from zoneinfo import ZoneInfo

import typer

from sysforge.common import (
    format_duration,
    load_json_file,
    print_error,
    write_json_file,
    write_text_file,
)
from sysforge.logging_utils import get_logger
from sysforge.shared_config import deep_merge, load_shared_config
from sysforge.sysforge_paths import (
    ensure_home_layout,
    get_briefing_data_dir,
    get_briefing_history_file,
    get_briefings_dir,
)

app = typer.Typer(help="Build a daily personal briefing file.")
logger = get_logger("sysforge.briefing")


def _zoned_now(tz: tzinfo) -> datetime:
    return datetime.now(tz)


_DEFAULT_DATA_FILENAMES = {
    "weather_file": "weather.json",
    "quotes_file": "quotes.json",
    "calendar_file": "calendar.json",
}

_ALLOWED_BRIEFING_CONFIG_KEYS = frozenset(
    {
        "name",
        "timezone",
        "temperature_unit",
        "weather_file",
        "quotes_file",
        "calendar_file",
        "output_dir",
    }
)


def _sanitize_single_line(text: str) -> str:
    cleaned = "".join(ch if ch.isprintable() or ch in "\t" else " " for ch in text)
    return " ".join(cleaned.split())
