from __future__ import annotations

import os
import shutil
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent

def get_home_dir() -> Path:
    override = os.environ.get("SYSFORGE_HOME")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".sysforge"

def get_logs_dir() -> Path:
    return get_home_dir() / "logs"

def get_central_log_file() -> Path:
    return get_logs_dir() / "sysforge.log"

def get_organizer_log_dir() -> Path:
    return get_home_dir() / "organizer" / "logs"

def get_docs_dir() -> Path:
    return get_home_dir() / "docs"

def get_docs_history_file() -> Path:
    return get_docs_dir() / "build_history.json"

def get_briefings_dir() -> Path:
    return get_home_dir() / "briefings"

def get_briefing_history_file() -> Path:
    return get_briefings_dir() / "briefing_history.json"

def get_time_dir() -> Path:
    return get_home_dir() / "time"

def get_timesheet_file() -> Path:
    return get_time_dir() / "timesheet.json"


def get_health_dir() -> Path:
    return get_home_dir() / "health"


def get_health_log_file() -> Path:
    return get_health_dir() / "health_log.jsonl"

def get_latest_health_file() -> Path:
    return get_health_dir() / "latest_snapshot.json"

def get_reports_dir() -> Path:
    return get_home_dir() / "reports"

def get_backups_dir() -> Path:
    return get_home_dir() / "backups"

def get_user_config_path() -> Path:
    return get_home_dir() / "sysforge.json"

def get_default_config_path() -> Path:
    return PACKAGE_ROOT / "data" / "sysforge.json"

def get_default_schema_path() -> Path:
    return PACKAGE_ROOT / "data" / "sysforge.schema.json"

def get_default_organizer_rules_path() -> Path:
    return PACKAGE_ROOT / "data" / "default_organizer_rules.json"

def get_markdown_template_path() -> Path:
    return PACKAGE_ROOT / "mdhtml" / "template.html"

def get_theme_path(theme_name: str) -> Path:
    return PACKAGE_ROOT / "mdhtml" / "themes" / f"{theme_name}.css"

def get_briefing_data_dir() -> Path:
    return PACKAGE_ROOT / "briefing" / "data"

def ensure_home_layout() -> None:
    directories = [
        get_home_dir(),
        get_logs_dir(),
        get_organizer_log_dir(),
        get_docs_dir(),
        get_briefings_dir(),
        get_time_dir(),
        get_health_dir(),
        get_reports_dir(),
        get_backups_dir(),
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    default_config = get_default_config_path()
    user_config = get_user_config_path()
    if default_config.exists() and not user_config.exists():
        shutil.copy2(default_config, user_config)
