"""Tests for the reporting module."""

from __future__ import annotations

from datetime import datetime

from sysforge.common import write_json_file
from sysforge.reporting import _render_html, build_daily_report
from sysforge.sysforge_paths import (
    get_briefings_dir,
    get_docs_dir,
    get_latest_health_file,
    get_organizer_log_dir,
    get_reports_dir,
    get_timesheet_file,
)


def _seed_today_artifacts(today: str) -> None:
    organizer_dir = get_organizer_log_dir()
    organizer_dir.mkdir(parents=True, exist_ok=True)
    log_path = organizer_dir / "organizer_test.json"
    write_json_file(
        log_path,
        {
            "timestamp": f"{today}T10:00:00",
            "summary": {
                "moved": 2,
                "skipped": 1,
                "errors": 0,
                "total_size_processed": 1024,
            },
        },
    )

    docs_history = get_docs_dir() / "build_history.json"
    write_json_file(
        docs_history,
        [{"timestamp": f"{today}T11:00:00", "files_built": 3}],
    )

    briefing_dir = get_briefings_dir()
    briefing_dir.mkdir(parents=True, exist_ok=True)
    briefing_history = briefing_dir / "briefing_history.json"
    write_json_file(
        briefing_history,
        [{"timestamp": f"{today}T09:00:00", "output_file": str(briefing_dir / "b.md")}],
    )

    timesheet = get_timesheet_file()
    timesheet.parent.mkdir(parents=True, exist_ok=True)
    write_json_file(
        timesheet,
        {
            "entries": [
                {
                    "start_time": f"{today}T08:00:00",
                    "duration_seconds": 3600,
                    "billable_total": 10.5,
                }
            ],
            "active_timer": None,
        },
    )

    latest_health = get_latest_health_file()
    latest_health.parent.mkdir(parents=True, exist_ok=True)
    write_json_file(
        latest_health,
        {
            "cpu_percent": 12.5,
            "memory": {"percent": 44.0},
            "disks": [{"mount": "/"}],
            "process_count": 200,
            "overall_level": "INFO",
        },
    )


def test_build_daily_report_text(isolated_sysforge_home: None) -> None:
    today = datetime.now().date().isoformat()
    _seed_today_artifacts(today)

    body, path = build_daily_report("text")
    assert "SysForge Daily Report" in body
    assert today in body
    assert path.suffix == ".txt"
    assert path.parent == get_reports_dir()
    assert path.read_text(encoding="utf-8") == body


def test_render_html_uses_markdown_not_pre_escape() -> None:
    from datetime import date

    sample = {
        "organizer": {"runs": 0, "moved": 0, "skipped": 0, "errors": 0, "bytes": 0},
        "docs": {"runs": 0, "files_built": 0},
        "briefing": {"runs": 0, "latest_file": "n/a"},
        "time": {"duration": "0h 00m", "billable_total": 0.0, "active_task": None},
        "health": {"status": "ok"},
    }
    html = _render_html(date(2026, 1, 2), sample)
    assert "<h1" in html
    assert "<pre>" not in html
    assert "SysForge Daily Report (2026-01-02)" in html
