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

def _normalize_entry(raw: Any, zone: ZoneInfo) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    entry_id = raw.get("id")
    if entry_id is None or str(entry_id).strip() == "":
        return None
    start_raw = raw.get("start_time")
    end_raw = raw.get("end_time")
    if not isinstance(start_raw, str) or not isinstance(end_raw, str):
        return None
    try:
        start = datetime.fromisoformat(start_raw)
        end = datetime.fromisoformat(end_raw)
    except ValueError:
        return None
    if start.tzinfo is None:
        start = start.replace(tzinfo=zone)
    else:
        start = start.astimezone(zone)
    if end.tzinfo is None:
        end = end.replace(tzinfo=zone)
    else:
        end = end.astimezone(zone)
    if _intish(raw.get("duration_seconds")):
        duration = max(int(raw["duration_seconds"]), 0)
    else:
        duration = max(seconds_between(start, end), 0)
    task = str(raw.get("task", "")).strip() or "Untitled"
    project = str(raw.get("project") or "Unassigned") or "Unassigned"
    tag = str(raw.get("tag") or "general") or "general"
    try:
        rate = float(raw.get("billable_rate", 0) or 0.0)
    except (TypeError, ValueError):
        rate = 0.0
    hours = duration / 3600.0
    raw_total = raw.get("billable_total")
    try:
        billable_total = (
            round(float(raw_total), 2) if raw_total is not None else round(rate * hours, 2)
        )
    except (TypeError, ValueError):
        billable_total = round(rate * hours, 2)
    return {
        "id": str(entry_id),
        "task": task,
        "project": project,
        "tag": tag,
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "duration_seconds": duration,
        "billable_rate": rate,
        "billable_total": billable_total,
    }

def normalize_timesheet_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"active_timer": None, "entries": []}
    zone = ZoneInfo(active_timezone())
    raw_entries = payload.get("entries", [])
    if not isinstance(raw_entries, list):
        raw_entries = []
    entries: list[dict[str, Any]] = []
    for item in raw_entries:
        normalized = _normalize_entry(item, zone)
        if normalized is not None:
            entries.append(normalized)
        elif item not in (None, {}):
            logger.warning("Skipping invalid timesheet entry: %r", item)
    active = _normalize_active_timer(payload.get("active_timer"))
    result = dict(payload)
    result["entries"] = entries
    result["active_timer"] = active
    return result

























def main() -> None:
    app()


if __name__ == "__main__":
    main()
