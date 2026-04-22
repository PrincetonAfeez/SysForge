from __future__ import annotations

import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import typer

from sysforge.common import (
    append_json_line,
    format_duration,
    human_size,
    print_error,
    write_json_file,
)
from sysforge.config.config import load_config_file
from sysforge.logging_utils import get_logger
from sysforge.shared_config import load_shared_config
from sysforge.sysforge_paths import (
    ensure_home_layout,
    get_health_log_file,
    get_latest_health_file,
)

app = typer.Typer(help="Check CPU, memory, disks, and uptime.")
logger = get_logger("sysforge.monitor")


def _coerce_threshold_int(value: Any, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(round(value))
    if isinstance(value, str):
        try:
            return int(float(value.strip()))
        except ValueError:
            return default
    return default

def load_psutil() -> Any:
    try:
        import psutil

        return psutil
    except ModuleNotFoundError:
        print_error("psutil is required. Run `pip install -e .` first.", exit_code=2)


def normalize_load_average(raw: Any) -> list[float] | None:
    if raw is None:
        return None
    if isinstance(raw, (list, tuple)) and len(raw) == 3:
        try:
            return [float(raw[0]), float(raw[1]), float(raw[2])]
        except (TypeError, ValueError):
            return None
    return None


def load_rich_table_tools() -> Any:
    try:
        from rich.console import Console
        from rich.table import Table

        return Console, Table
    except ModuleNotFoundError:
        return None

def read_thresholds(config_path: Path | None = None) -> dict[str, Any]:
    if config_path is not None:
        config = load_config_file(config_path, apply_env=False)
    else:
        config = load_shared_config()
    raw = config.get("health", {})
    if not isinstance(raw, dict):
        raw = {}
    return {
        "cpu_warning": _coerce_threshold_int(raw.get("cpu_warning"), 80),
        "cpu_critical": _coerce_threshold_int(raw.get("cpu_critical"), 95),
        "memory_warning": _coerce_threshold_int(raw.get("memory_warning"), 90),
        "memory_critical": _coerce_threshold_int(raw.get("memory_critical"), 97),
        "disk_warning": _coerce_threshold_int(raw.get("disk_warning"), 80),
        "disk_critical": _coerce_threshold_int(raw.get("disk_critical"), 95),
        "rotate_mb": _coerce_threshold_int(raw.get("rotate_mb"), 10),
        "keep_files": max(1, min(_coerce_threshold_int(raw.get("keep_files"), 5), 50)),
        "top_process_scan": max(
            20, min(_coerce_threshold_int(raw.get("top_process_scan"), 80), 500)
        ),
        "max_rss_scan": max(200, min(_coerce_threshold_int(raw.get("max_rss_scan"), 4000), 50_000)),
    }















def main() -> None:
    app()


if __name__ == "__main__":
    main()
