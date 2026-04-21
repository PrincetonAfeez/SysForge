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


def _sanitize_quote_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs: list[str] = []
    for para in text.split("\n\n"):
        cleaned = "".join(ch if ch.isprintable() or ch in "\t" else " " for ch in para)
        collapsed = " ".join(cleaned.split())
        if collapsed:
            paragraphs.append(collapsed)
    return "\n\n".join(paragraphs)


def normalize_briefing_config(config: dict[str, Any]) -> dict[str, Any]:
    unknown = sorted(k for k in config if k not in _ALLOWED_BRIEFING_CONFIG_KEYS)
    for key in unknown:
        logger.warning("Ignoring unknown briefing config key: %s", key)
    cleaned: dict[str, Any] = {k: config[k] for k in config if k in _ALLOWED_BRIEFING_CONFIG_KEYS}
    tz_name = str(cleaned.get("timezone", "UTC"))
    try:
        ZoneInfo(tz_name)
    except Exception as exc:
        raise ValueError(f"Invalid briefing timezone: {tz_name!r}") from exc
    unit = str(cleaned.get("temperature_unit", "F")).upper()
    cleaned["temperature_unit"] = unit if unit in {"F", "C"} else "F"
    for file_key in ("weather_file", "quotes_file", "calendar_file"):
        if file_key in cleaned and cleaned[file_key] is not None:
            cleaned[file_key] = str(cleaned[file_key])
    if "output_dir" in cleaned and cleaned["output_dir"] is not None:
        cleaned["output_dir"] = str(cleaned["output_dir"])
    return cleaned

def _normalize_weather_payload(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {"default": {}, "days": {}}
    default = data.get("default")
    days = data.get("days")
    if not isinstance(default, dict):
        default = {}
    if not isinstance(days, dict):
        days = {}
    return {"default": default, "days": days}

