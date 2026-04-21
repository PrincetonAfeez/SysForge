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

def _normalize_quotes_payload(data: Any) -> list[str]:
    if not isinstance(data, list):
        return []
    return [str(item) for item in data]

def _normalize_calendar_payload(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, list):
        return []
    items: list[dict[str, Any]] = []
    for raw in data:
        if not isinstance(raw, dict):
            continue
        if raw.get("date") is None:
            continue
        items.append(
            {
                "date": str(raw.get("date")),
                "time": str(raw.get("time", "")),
                "title": str(raw.get("title", "Untitled")),
            }
        )
    return items


def _markdown_quote_block(quote: str, wrap_width: int = 88) -> list[str]:
    quote = quote.strip()
    if not quote:
        return ["> _(empty quote)_", ""]
    paragraphs = [p.strip() for p in quote.split("\n\n") if p.strip()]
    lines_out: list[str] = []
    for para in paragraphs:
        wrapped = textwrap.wrap(
            para, width=wrap_width, break_long_words=True, break_on_hyphens=True
        )
        if not wrapped:
            wrapped = [para]
        for segment in wrapped:
            lines_out.append(f"> {segment}")
        lines_out.append(">")
    while lines_out and lines_out[-1].strip() == ">":
        lines_out.pop()
    return lines_out

def load_psutil() -> Any:
    try:
        import psutil

        return psutil
    except ModuleNotFoundError:
        return None

def load_briefing_config(
    briefing_config_path: Path | None = None,
) -> tuple[dict[str, Any], Path]:
    shared_config = load_shared_config()
    data_dir = get_briefing_data_dir()
    base_config = load_json_file(data_dir / "briefing_config.json", default={})

    if briefing_config_path is not None:
        if not briefing_config_path.exists():
            print_error(f"Briefing config not found: {briefing_config_path}")
        data_dir = briefing_config_path.parent
        file_config = load_json_file(briefing_config_path, default={})
        config = deep_merge(base_config, file_config)
    else:
        config_path_from_shared = shared_config.get("briefing", {}).get("config_file", "")
        if config_path_from_shared:
            config_path = Path(config_path_from_shared)
            if config_path.exists():
                data_dir = config_path.parent
                config = deep_merge(base_config, load_json_file(config_path, default={}))
            else:
                config = base_config
        else:
            config = base_config

    raw_name = shared_config.get("user", {}).get("name", config.get("name", "Developer"))
    config["name"] = _sanitize_single_line(str(raw_name)) or "Developer"
    config["timezone"] = shared_config.get("user", {}).get(
        "timezone", config.get("timezone", "UTC")
    )
    return normalize_briefing_config(config), data_dir

def load_mock_data(config: dict[str, Any], data_dir: Path) -> dict[str, Any]:
    weather_name = str(config.get("weather_file") or _DEFAULT_DATA_FILENAMES["weather_file"])
    quotes_name = str(config.get("quotes_file") or _DEFAULT_DATA_FILENAMES["quotes_file"])
    calendar_name = str(config.get("calendar_file") or _DEFAULT_DATA_FILENAMES["calendar_file"])
    weather = _normalize_weather_payload(load_json_file(data_dir / weather_name, default={}))
    quotes = _normalize_quotes_payload(load_json_file(data_dir / quotes_name, default=[]))
    calendar = _normalize_calendar_payload(load_json_file(data_dir / calendar_name, default=[]))
    return {"weather": weather, "quotes": quotes, "calendar": calendar}

def greeting_for_hour(hour: int, name: str) -> str:
    if hour < 12:
        return f"Good morning, {name}"
    if hour < 18:
        return f"Good afternoon, {name}"
    return f"Good evening, {name}"

def pick_weather(weather_data: dict[str, Any], day_key: str) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        weather_data.get("days", {}).get(day_key, weather_data.get("default", {})),
    )

def pick_quote(quotes: list[str]) -> str:
    if not quotes:
        return "No quote available today."
    raw = random.choice(quotes)
    cleaned = _sanitize_quote_text(str(raw))
    return cleaned or "No quote available today."

def calendar_items_for_day(
    calendar_items: list[dict[str, Any]], day_key: str
) -> list[dict[str, Any]]:
    items = [item for item in calendar_items if item.get("date") == day_key]
    return sorted(items, key=lambda item: item.get("time", ""))

def _resolve_disk_usage_root(preferred: Path) -> Path:
    try:
        current = preferred.expanduser().resolve(strict=False)
    except OSError:
        current = preferred.expanduser()
    for _ in range(128):
        try:
            if current.exists() and current.is_dir():
                return current
        except OSError:
            pass
        parent = current.parent
        if parent == current:
            break
        current = parent
    return Path.home()

def get_system_snapshot(disk_root: Path | None = None) -> dict[str, Any]:
    psutil = load_psutil()
    root = disk_root if disk_root is not None else Path.home()
    try:
        free_disk = shutil.disk_usage(root).free
    except OSError:
        free_disk = shutil.disk_usage(Path.home()).free

    uptime_seconds = 0
    if psutil is not None:
        uptime_seconds = int(time.time() - psutil.boot_time())

    return {
        "os": platform.platform(),
        "python_version": sys.version.split()[0],
        "uptime": format_duration(uptime_seconds),
        "free_disk": free_disk,
        "disk_root": str(root),
    }

def _format_temperature_value(value: Any, unit: str) -> str:
    if value is None or value == "n/a":
        return "n/a"
    try:
        fahrenheit = float(value)
    except (TypeError, ValueError):
        return _sanitize_single_line(str(value))
    unit_u = unit.upper()
    if unit_u == "C":
        celsius = (fahrenheit - 32.0) * 5.0 / 9.0
        text = f"{celsius:.1f}".rstrip("0").rstrip(".")
        return text or "0"
    text = f"{fahrenheit:.1f}".rstrip("0").rstrip(".") if fahrenheit % 1 else str(int(fahrenheit))
    return text


def _temperature_unit_label(unit: str) -> str:
    return "C" if unit.upper() == "C" else "F"

def build_text_briefing(
    *,
    greeting: str,
    now: datetime,
    weather: dict[str, Any] | None,
    quote: str | None,
    calendar_items: list[dict[str, Any]] | None,
    system_snapshot: dict[str, Any],
    temperature_unit: str = "F",
) -> str:
    lines = [
        greeting,
        "",
        f"Date: {now.strftime('%A, %Y-%m-%d')}",
        f"Time: {now.strftime('%I:%M %p %Z')}",
        "",
    ]

    if weather is not None:
        unit_l = _temperature_unit_label(temperature_unit)
        cond = _sanitize_single_line(str(weather.get("condition", "Unknown")))
        cur = _format_temperature_value(weather.get("temp"), temperature_unit)
        hi = _format_temperature_value(weather.get("high"), temperature_unit)
        lo = _format_temperature_value(weather.get("low"), temperature_unit)
        lines.extend(
            [
                "Weather",
                f"  Condition: {cond}",
                f"  Current: {cur} °{unit_l}",
                f"  High / Low: {hi} / {lo} °{unit_l}",
                "",
            ]
        )

    if quote is not None:
        lines.append("Quote")
        for para in quote.split("\n\n"):
            wrapped = textwrap.wrap(para, width=88, break_long_words=True, break_on_hyphens=True)
            if not wrapped and para.strip():
                wrapped = [para.strip()]
            for idx, segment in enumerate(wrapped or [""]):
                prefix = "  " if idx == 0 else "    "
                lines.append(f"{prefix}{segment}")
        lines.append("")

    if calendar_items is not None:
        lines.append("Today's calendar")
        if calendar_items:
            for item in calendar_items:
                t = _sanitize_single_line(str(item.get("time", "??:??")))
                title = _sanitize_single_line(str(item.get("title", "Untitled")))
                lines.append(f"  {t} - {title}")
        else:
            lines.append("  No calendar items today.")
        lines.append("")

    free_gb = round(system_snapshot["free_disk"] / (1024**3), 2)
    disk_root = system_snapshot["disk_root"]
    lines.extend(
        [
            "System snapshot",
            f"  OS: {system_snapshot['os']}",
            f"  Python: {system_snapshot['python_version']}",
            f"  Uptime: {system_snapshot['uptime']}",
            f"  Free disk ({disk_root}): {free_gb} GB",
        ]
    )
    return "\n".join(lines)
