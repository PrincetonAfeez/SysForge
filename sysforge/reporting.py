""" Daily reporting system """

from __future__ import annotations

from datetime import date, datetime
from html import escape
from pathlib import Path
from typing import Any

import markdown

from sysforge.common import format_duration, human_size, load_json_file, write_text_file
from sysforge.shared_config import load_shared_config
from sysforge.sysforge_paths import (
    get_briefing_history_file,
    get_docs_history_file,
    get_latest_health_file,
    get_organizer_log_dir,
    get_reports_dir,
    get_timesheet_file,
)


def _load_today_organizer_data(today: date) -> dict[str, Any]:
    log_dir = get_organizer_log_dir()
    summary = {"runs": 0, "moved": 0, "skipped": 0, "errors": 0, "bytes": 0}
    if not log_dir.exists():
        return summary

    for log_file in sorted(log_dir.glob("*.json")):
        log_data = load_json_file(log_file, default={})
        timestamp = log_data.get("timestamp", "")
        if not timestamp.startswith(today.isoformat()):
            continue
        file_summary = log_data.get("summary", {})
        summary["runs"] += 1
        summary["moved"] += file_summary.get("moved", 0)
        summary["skipped"] += file_summary.get("skipped", 0)
        summary["errors"] += file_summary.get("errors", 0)
        summary["bytes"] += file_summary.get("total_size_processed", 0)

    return summary


def _load_today_docs_data(today: date) -> dict[str, Any]:
    history = load_json_file(get_docs_history_file(), default=[])
    runs = [item for item in history if item.get("timestamp", "").startswith(today.isoformat())]
    file_count = sum(item.get("files_built", 0) for item in runs)
    return {"runs": len(runs), "files_built": file_count}


def _load_today_briefing_data(today: date) -> dict[str, Any]:
    history = load_json_file(get_briefing_history_file(), default=[])
    today_runs = [
        item for item in history if item.get("timestamp", "").startswith(today.isoformat())
    ]
    latest = today_runs[-1] if today_runs else None
    return {
        "runs": len(today_runs),
        "latest_file": latest.get("output_file") if latest else "No briefing today",
    }


def _load_today_time_data(today: date) -> dict[str, Any]:
    data = load_json_file(get_timesheet_file(), default={"entries": [], "active_timer": None})
    total_seconds = 0
    total_billable = 0.0
    for entry in data.get("entries", []):
        start_time = entry.get("start_time", "")
        if start_time.startswith(today.isoformat()):
            total_seconds += entry.get("duration_seconds", 0)
            total_billable += entry.get("billable_total", 0.0)

    active_timer = data.get("active_timer")
    return {
        "duration": format_duration(total_seconds),
        "billable_total": round(total_billable, 2),
        "active_task": active_timer.get("task") if active_timer else None,
    }


def _load_health_data() -> dict[str, Any]:
    latest_path = get_latest_health_file()
    if not latest_path.exists():
        return {"status": "No health data yet"}
    snapshot = load_json_file(latest_path, default={})
    return {
        "cpu_percent": snapshot.get("cpu_percent"),
        "memory_percent": snapshot.get("memory", {}).get("percent"),
        "disk_count": len(snapshot.get("disks", [])),
        "process_count": snapshot.get("process_count"),
        "status": snapshot.get("overall_level", "INFO"),
    }


def _render_text(today: date, report_data: dict[str, Any]) -> str:
    organizer = report_data["organizer"]
    docs = report_data["docs"]
    briefing = report_data["briefing"]
    time_data = report_data["time"]
    health = report_data["health"]

    lines = [
        f"SysForge Daily Report - {today.isoformat()}",
        "",
        "Files organized",
        f"  Runs: {organizer['runs']}",
        f"  Moved: {organizer['moved']}",
        f"  Skipped: {organizer['skipped']}",
        f"  Errors: {organizer['errors']}",
        f"  Data touched: {human_size(organizer['bytes'])}",
        "",
        "Documentation builds",
        f"  Runs: {docs['runs']}",
        f"  HTML files built: {docs['files_built']}",
        "",
        "Briefings",
        f"  Runs today: {briefing['runs']}",
        f"  Latest file: {briefing['latest_file']}",
        "",
        "Time tracked",
        f"  Total today: {time_data['duration']}",
        f"  Billable total: ${time_data['billable_total']:.2f}",
        f"  Active task: {time_data['active_task'] or 'None'}",
        "",
        "System health",
        f"  Status: {health['status']}",
        f"  CPU: {health.get('cpu_percent', 'n/a')}",
        f"  Memory: {health.get('memory_percent', 'n/a')}",
        f"  Processes: {health.get('process_count', 'n/a')}",
    ]
    return "\n".join(lines)


def _render_markdown(today: date, report_data: dict[str, Any]) -> str:
    organizer = report_data["organizer"]
    docs = report_data["docs"]
    briefing = report_data["briefing"]
    time_data = report_data["time"]
    health = report_data["health"]

    return "\n".join(
        [
            f"# SysForge Daily Report ({today.isoformat()})",
            "",
            "## Files organized",
            f"- Runs: {organizer['runs']}",
            f"- Moved: {organizer['moved']}",
            f"- Skipped: {organizer['skipped']}",
            f"- Errors: {organizer['errors']}",
            f"- Data touched: {human_size(organizer['bytes'])}",
            "",
            "## Documentation builds",
            f"- Runs: {docs['runs']}",
            f"- HTML files built: {docs['files_built']}",
            "",
            "## Briefings",
            f"- Runs today: {briefing['runs']}",
            f"- Latest file: `{briefing['latest_file']}`",
            "",
            "## Time tracked",
            f"- Total today: {time_data['duration']}",
            f"- Billable total: ${time_data['billable_total']:.2f}",
            f"- Active task: {time_data['active_task'] or 'None'}",
            "",
            "## System health",
            f"- Status: {health['status']}",
            f"- CPU: {health.get('cpu_percent', 'n/a')}",
            f"- Memory: {health.get('memory_percent', 'n/a')}",
            f"- Processes: {health.get('process_count', 'n/a')}",
        ]
    )


def _render_html(today: date, report_data: dict[str, Any]) -> str:
    markdown_version = _render_markdown(today, report_data)
    body_html = markdown.markdown(
        markdown_version,
        extensions=["extra"],
        output_format="html",
    )
    title = escape(f"SysForge Daily Report - {today.isoformat()}")
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        f"  <title>{title}</title>\n"
        "  <style>"
        "body{font-family:Arial,sans-serif;max-width:900px;margin:2rem auto;line-height:1.6;}"
        "pre,code{background:#f5f5f5;padding:0.2rem 0.4rem;border-radius:4px;}"
        "pre{padding:1rem;white-space:pre-wrap;}"
        "table{border-collapse:collapse;width:100%;}"
        "th,td{border:1px solid #ddd;padding:0.4rem 0.6rem;text-align:left;}"
        "</style>\n"
        "</head>\n"
        "<body>\n"
        f'  <article class="sysforge-report">{body_html}</article>\n'
        "</body>\n"
        "</html>\n"
    )


def build_daily_report(output_format: str = "text") -> tuple[str, Path]:
    today = datetime.now().date()
    load_shared_config()

    report_data = {
        "organizer": _load_today_organizer_data(today),
        "docs": _load_today_docs_data(today),
        "briefing": _load_today_briefing_data(today),
        "time": _load_today_time_data(today),
        "health": _load_health_data(),
    }

    if output_format == "markdown":
        body = _render_markdown(today, report_data)
        path = get_reports_dir() / f"sysforge_report_{today.isoformat()}.md"
    elif output_format == "html":
        body = _render_html(today, report_data)
        path = get_reports_dir() / f"sysforge_report_{today.isoformat()}.html"
    else:
        body = _render_text(today, report_data)
        path = get_reports_dir() / f"sysforge_report_{today.isoformat()}.txt"

    write_text_file(path, body)
    return body, path
