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


def active_timezone() -> str:
    config = load_shared_config()
    raw = config.get("user", {}).get("timezone", "UTC")
    return raw if isinstance(raw, str) else "UTC"

def now_in_timezone() -> datetime:
    return datetime.now(ZoneInfo(active_timezone()))

def load_timesheet() -> dict[str, Any]:
    ensure_home_layout()
    raw = load_json_file(get_timesheet_file(), default={"active_timer": None, "entries": []})
    return normalize_timesheet_payload(raw)

def save_timesheet(payload: dict[str, Any]) -> None:
    normalized = normalize_timesheet_payload(payload)
    normalized["updated_at"] = datetime.now().isoformat()
    write_json_file(get_timesheet_file(), normalized, atomic=True)

def project_rate(project_name: str | None) -> float:
    if not project_name:
        return 0.0
    config = load_shared_config()
    return float(config.get("time", {}).get("project_rates", {}).get(project_name, 0))

def make_entry_id() -> str:
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"entry-{stamp}-{secrets.token_hex(4)}"

def _intish(value: Any) -> bool:
    try:
        int(value)
        return True
    except (TypeError, ValueError):
        return False

def _normalize_active_timer(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    task = str(raw.get("task", "")).strip()
    start_raw = raw.get("start_time")
    if not task or not isinstance(start_raw, str):
        return None
    try:
        datetime.fromisoformat(start_raw)
    except ValueError:
        logger.warning("Clearing active_timer: invalid start_time %r", start_raw)
        return None
    return {
        "task": task,
        "project": str(raw.get("project") or "Unassigned"),
        "tag": str(raw.get("tag") or "general"),
        "start_time": start_raw,
    }














def main() -> None:
    app()


if __name__ == "__main__":
    main()
