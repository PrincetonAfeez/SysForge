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

def top_processes(
    psutil_module: Any,
    limit: int = 5,
    *,
    cpu_candidate_cap: int = 80,
    max_rss_scan: int = 4000,
    pids: list[int] | None = None,
) -> list[dict[str, Any]]:
    cap = max(limit, min(cpu_candidate_cap, 500))
    all_pids = list(pids) if pids is not None else psutil_module.pids()
    total_pids = len(all_pids)
    if total_pids > max_rss_scan:
        logger.info(
            "RSS ranking uses a random sample of %s of %s processes "
            "(max_rss_scan=%s); top processes are approximate",
            max_rss_scan,
            total_pids,
            max_rss_scan,
        )
        work_pids = random.sample(all_pids, max_rss_scan)
    else:
        work_pids = list(all_pids)

    scored: list[tuple[int, Any]] = []
    for pid in work_pids:
        try:
            proc = psutil_module.Process(pid)
            mem_info = proc.memory_info()
            rss = int(mem_info.rss) if mem_info else 0
            scored.append((rss, proc))
        except (psutil_module.NoSuchProcess, psutil_module.AccessDenied):
            continue

    scored.sort(key=lambda item: item[0], reverse=True)
    candidates = [proc for _, proc in scored[:cap]]

    for proc in candidates:
        try:
            proc.cpu_percent(interval=None)
        except (psutil_module.NoSuchProcess, psutil_module.AccessDenied):
            continue

    time.sleep(0.1)

    processes: list[dict[str, Any]] = []
    for proc in candidates:
        try:
            memory_percent = round(proc.memory_percent(), 2)
            cpu_p = round(proc.cpu_percent(interval=None), 2)
            processes.append(
                {
                    "pid": proc.pid,
                    "name": proc.name() or "unknown",
                    "memory_percent": memory_percent,
                    "cpu_percent": cpu_p,
                }
            )
        except (psutil_module.NoSuchProcess, psutil_module.AccessDenied):
            continue

    processes.sort(key=lambda item: (item["memory_percent"], item["cpu_percent"]), reverse=True)
    return processes[:limit]


def snapshot_system(thresholds: dict[str, Any] | None = None) -> dict[str, Any]:
    th = thresholds if thresholds is not None else read_thresholds()
    psutil = load_psutil()
    all_pids = psutil.pids()
    disks = []
    disk_all = sys.platform != "win32"
    for partition in psutil.disk_partitions(all=disk_all):
        try:
            usage = psutil.disk_usage(partition.mountpoint)
        except PermissionError:
            continue
        disks.append(
            {
                "device": partition.device,
                "mountpoint": partition.mountpoint,
                "percent": usage.percent,
                "free": usage.free,
                "total": usage.total,
            }
        )

    load_average_raw = None
    if hasattr(os, "getloadavg"):
        try:
            load_average_raw = os.getloadavg()
        except OSError:
            load_average_raw = None
    load_average = normalize_load_average(load_average_raw)

    memory = psutil.virtual_memory()
    boot_time = psutil.boot_time()
    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "cpu_percent": psutil.cpu_percent(interval=0.2),
        "memory": {
            "percent": memory.percent,
            "available": memory.available,
        },
        "disks": disks,
        "process_count": len(all_pids),
        "boot_time": datetime.fromtimestamp(boot_time).isoformat(),
        "uptime_seconds": int(time.time() - boot_time),
        "load_average": load_average,
        "platform": {
            "system": sys.platform,
            "load_average_available": load_average is not None,
            "disk_partitions_all": disk_all,
        },
        "top_processes": top_processes(
            psutil,
            limit=5,
            cpu_candidate_cap=int(th.get("top_process_scan", 80)),
            max_rss_scan=int(th.get("max_rss_scan", 4000)),
            pids=all_pids,
        ),
    }
    return snapshot
























def main() -> None:
    app()


if __name__ == "__main__":
    main()
