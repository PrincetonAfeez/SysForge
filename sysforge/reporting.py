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
