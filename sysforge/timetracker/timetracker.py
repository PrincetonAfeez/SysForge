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


def seconds_between(start_time: datetime, end_time: datetime) -> int:
    return int((end_time - start_time).total_seconds())


def build_entry(
    *,
    task: str,
    start_time: datetime,
    end_time: datetime,
    project: str | None,
    tag: str | None,
) -> dict[str, Any]:
    duration_seconds = seconds_between(start_time, end_time)
    rate = project_rate(project)
    hours = duration_seconds / 3600
    return {
        "id": make_entry_id(),
        "task": task,
        "project": project or "Unassigned",
        "tag": tag or "general",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": duration_seconds,
        "billable_rate": rate,
        "billable_total": round(rate * hours, 2),
    }


def parse_entry_datetime(value: str) -> datetime:
    return parse_local_datetime(value, active_timezone())


def todays_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    today_key = now_in_timezone().date().isoformat()
    return [entry for entry in entries if entry.get("start_time", "").startswith(today_key)]

def _entry_start_datetime(entry: dict[str, Any], tz: tzinfo) -> datetime | None:
    raw = entry.get("start_time")
    if not isinstance(raw, str):
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=tz)
    return parsed.astimezone(tz)

def period_entries(entries: list[dict[str, Any]], period: str) -> list[dict[str, Any]]:
    now = now_in_timezone()
    if period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start = now - timedelta(days=7)
    tz = now.tzinfo or ZoneInfo("UTC")
    filtered: list[dict[str, Any]] = []
    for entry in entries:
        parsed_start = _entry_start_datetime(entry, tz)
        if parsed_start is None:
            continue
        if parsed_start >= start:
            filtered.append(entry)
    return filtered


def report_lines(entries: list[dict[str, Any]]) -> list[str]:
    totals_by_project: dict[str, int] = {}
    totals_by_tag: dict[str, int] = {}
    billable_total = 0.0

    for entry in entries:
        project = str(entry.get("project", "Unassigned"))
        tag = str(entry.get("tag", "general"))
        duration = int(entry.get("duration_seconds", 0) or 0)
        totals_by_project[project] = totals_by_project.get(project, 0) + duration
        totals_by_tag[tag] = totals_by_tag.get(tag, 0) + duration
        try:
            billable_total += float(entry.get("billable_total", 0.0) or 0.0)
        except (TypeError, ValueError):
            billable_total += 0.0

    lines = ["Totals by project"]
    for project, seconds in sorted(totals_by_project.items()):
        lines.append(f"  {project}: {format_duration(seconds)}")

    lines.append("")
    lines.append("Totals by tag")
    for tag, seconds in sorted(totals_by_tag.items()):
        lines.append(f"  {tag}: {format_duration(seconds)}")

    lines.append("")
    lines.append(f"Billable total: ${billable_total:.2f}")
    return lines

@app.command()
def start(
    task: str = typer.Argument(..., help="Task name"),
    project: str | None = typer.Option(None, "--project", help="Optional project name"),
    tag: str | None = typer.Option(None, "--tag", help="Optional tag"),
) -> None:
    data = load_timesheet()
    if data.get("active_timer"):
        print_error("A timer is already running. Stop it before starting a new one.")

    timer = {
        "task": task,
        "project": project or "Unassigned",
        "tag": tag or "general",
        "start_time": now_in_timezone().isoformat(),
    }
    data["active_timer"] = timer
    save_timesheet(data)
    logger.info("Started timer for %s", task)
    typer.echo(f"Started timer: {task}")

@app.command()
def stop() -> None:
    data = load_timesheet()
    active_timer = data.get("active_timer")
    if not active_timer:
        print_error("No timer is currently running.")

    start_raw = active_timer.get("start_time")
    if not isinstance(start_raw, str):
        print_error("Active timer is missing a valid start_time.")
    try:
        start_time = datetime.fromisoformat(start_raw)
    except ValueError:
        print_error("Active timer has an invalid start_time.")
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=ZoneInfo(active_timezone()))
    else:
        start_time = start_time.astimezone(ZoneInfo(active_timezone()))
    end_time = now_in_timezone()
    entry = build_entry(
        task=str(active_timer.get("task", "Untitled")),
        start_time=start_time,
        end_time=end_time,
        project=active_timer.get("project"),
        tag=active_timer.get("tag"),
    )
    data.setdefault("entries", []).append(entry)
    data["active_timer"] = None
    save_timesheet(data)

    typer.echo(f"Stopped timer: {entry['task']}")
    typer.echo(f"Duration: {format_duration(entry['duration_seconds'])}")
    if entry["duration_seconds"] > 8 * 3600:
        typer.echo("Warning: this timer ran for more than 8 hours.")

@app.command()
def status() -> None:
    data = load_timesheet()
    active_timer = data.get("active_timer")
    if not active_timer:
        typer.echo("No timer is running.")
        return

    start_raw = active_timer.get("start_time")
    if not isinstance(start_raw, str):
        typer.echo("Active timer is missing a valid start_time.")
        raise typer.Exit(code=1)
    try:
        start_time = datetime.fromisoformat(start_raw)
    except ValueError:
        typer.echo("Active timer has an invalid start_time.")
        raise typer.Exit(code=1)
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=ZoneInfo(active_timezone()))
    else:
        start_time = start_time.astimezone(ZoneInfo(active_timezone()))
    elapsed = seconds_between(start_time, now_in_timezone())
    typer.echo(f"Active task: {active_timer.get('task', 'Untitled')}")
    typer.echo(f"Project: {active_timer.get('project', 'Unassigned')}")
    typer.echo(f"Tag: {active_timer.get('tag', 'general')}")
    typer.echo(f"Elapsed: {format_duration(elapsed)}")
    if elapsed > 8 * 3600:
        typer.echo("Warning: this timer has been running for more than 8 hours.")


@app.command()
def log() -> None:
    entries = todays_entries(load_timesheet().get("entries", []))
    if not entries:
        typer.echo("No entries for today.")
        return

    for entry in entries:
        try:
            start_time = datetime.fromisoformat(str(entry.get("start_time", ""))).strftime("%H:%M")
            end_time = datetime.fromisoformat(str(entry.get("end_time", ""))).strftime("%H:%M")
        except ValueError:
            continue
        duration = int(entry.get("duration_seconds", 0) or 0)
        typer.echo(
            f"{entry.get('id', '')} | {entry.get('task', '')} | {start_time}-{end_time} | "
            f"{format_duration(duration)} | {entry.get('project', '')} | {entry.get('tag', '')}"
        )

@app.command()
def report(
    week: bool = typer.Option(False, "--week", help="Report on the last 7 days."),
    month: bool = typer.Option(False, "--month", help="Report on the current month."),
) -> None:
    if week and month:
        print_error("Choose either --week or --month, not both.")

    period = "month" if month else "week"
    entries = period_entries(load_timesheet().get("entries", []), period)
    typer.echo(f"Time report for {period}")
    typer.echo(f"Entries counted: {len(entries)}")
    typer.echo("")
    for line in report_lines(entries):
        typer.echo(line)

@app.command()
def export(
    csv: Path = typer.Option(..., "--csv", help="CSV file path"),
) -> None:
    entries = load_timesheet().get("entries", [])
    rows = [
        {
            "id": entry.get("id", ""),
            "task": entry.get("task", ""),
            "project": entry.get("project", ""),
            "tag": entry.get("tag", ""),
            "start_time": entry.get("start_time", ""),
            "end_time": entry.get("end_time", ""),
            "duration_seconds": entry.get("duration_seconds", 0),
            "billable_rate": entry.get("billable_rate", 0.0),
            "billable_total": entry.get("billable_total", 0.0),
        }
        for entry in entries
    ]
    append_csv_rows(
        csv,
        rows,
        [
            "id",
            "task",
            "project",
            "tag",
            "start_time",
            "end_time",
            "duration_seconds",
            "billable_rate",
            "billable_total",
        ],
    )
    typer.echo(f"Exported {len(rows)} entries to {csv}")

@app.command()
def add(
    task: str = typer.Argument(..., help="Task name"),
    start: str = typer.Option(..., "--start", help="Start time like 2026-04-19 09:00"),
    end: str = typer.Option(..., "--end", help="End time like 2026-04-19 10:30"),
    project: str | None = typer.Option(None, "--project", help="Optional project name"),
    tag: str | None = typer.Option(None, "--tag", help="Optional tag"),
) -> None:
    start_time = parse_entry_datetime(start)
    end_time = parse_entry_datetime(end)
    if end_time <= start_time:
        print_error("--end must be after --start.")

    data = load_timesheet()
    entry = build_entry(
        task=task, start_time=start_time, end_time=end_time, project=project, tag=tag
    )
    data.setdefault("entries", []).append(entry)
    save_timesheet(data)
    typer.echo(f"Added entry {entry['id']}")


@app.command()
def delete(
    entry_id: str = typer.Argument(..., help="Entry ID to remove"),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation prompt"),
) -> None:
    data = load_timesheet()
    entries = data.get("entries", [])
    match = next((entry for entry in entries if str(entry.get("id", "")) == entry_id), None)
    if match is None:
        print_error(f"Entry not found: {entry_id}")

    if not yes:
        confirmed = typer.confirm(f"Delete entry {entry_id}?")
        if not confirmed:
            typer.echo("Delete canceled.")
            raise typer.Exit(code=0)

    data["entries"] = [entry for entry in entries if str(entry.get("id", "")) != entry_id]
    save_timesheet(data)
    typer.echo(f"Deleted entry {entry_id}")





















def main() -> None:
    app()


if __name__ == "__main__":
    main()
