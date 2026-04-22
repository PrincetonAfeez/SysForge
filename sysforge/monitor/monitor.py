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

def level_for_percent(percent: float, warning: int, critical: int) -> str:
    if percent >= critical:
        return "CRITICAL"
    if percent >= warning:
        return "WARNING"
    return "INFO"


def determine_levels(snapshot: dict[str, Any], thresholds: dict[str, Any]) -> dict[str, str]:
    cpu_pct = float(snapshot.get("cpu_percent", 0.0) or 0.0)
    mem_raw = snapshot.get("memory")
    mem: dict[str, Any] = mem_raw if isinstance(mem_raw, dict) else {}
    mem_pct = float(mem.get("percent", 0.0) or 0.0)
    levels = {
        "cpu": level_for_percent(
            cpu_pct,
            thresholds.get("cpu_warning", 80),
            thresholds.get("cpu_critical", 95),
        ),
        "memory": level_for_percent(
            mem_pct,
            thresholds.get("memory_warning", 90),
            thresholds.get("memory_critical", 97),
        ),
    }

    worst_disk_level = "INFO"
    disks = snapshot.get("disks")
    if not isinstance(disks, list):
        disks = []
    for disk in disks:
        if not isinstance(disk, dict):
            continue
        disk_pct = float(disk.get("percent", 0.0) or 0.0)
        disk_level = level_for_percent(
            disk_pct,
            thresholds.get("disk_warning", 80),
            thresholds.get("disk_critical", 95),
        )
        if disk_level == "CRITICAL":
            worst_disk_level = "CRITICAL"
            break
        if disk_level == "WARNING":
            worst_disk_level = "WARNING"
    levels["disk"] = worst_disk_level
    return levels

def overall_level(levels: dict[str, str]) -> str:
    if "CRITICAL" in levels.values():
        return "CRITICAL"
    if "WARNING" in levels.values():
        return "WARNING"
    return "INFO"

def rotate_log_file(max_megabytes: int, keep_files: int) -> None:
    log_path = get_health_log_file()
    if not log_path.exists():
        return

    max_bytes = max_megabytes * 1024 * 1024
    if log_path.stat().st_size < max_bytes:
        return

    for index in range(keep_files - 1, 0, -1):
        older = log_path.with_name(f"{log_path.name}.{index}")
        newer = log_path.with_name(f"{log_path.name}.{index + 1}")
        if older.exists():
            if index == keep_files - 1:
                older.unlink()
            else:
                older.replace(newer)

    log_path.replace(log_path.with_name(f"{log_path.name}.1"))


def write_snapshot(snapshot: dict[str, Any], thresholds: dict[str, Any]) -> None:
    rotate_mb = max(1, _coerce_threshold_int(thresholds.get("rotate_mb"), 10))
    keep_files = max(1, min(_coerce_threshold_int(thresholds.get("keep_files"), 5), 50))
    rotate_log_file(rotate_mb, keep_files)
    levels = determine_levels(snapshot, thresholds)
    snapshot["levels"] = levels
    snapshot["overall_level"] = overall_level(levels)
    append_json_line(get_health_log_file(), snapshot)
    write_json_file(get_latest_health_file(), snapshot, atomic=True)


def render_snapshot(snapshot: dict[str, Any]) -> None:
    rich_tools = load_rich_table_tools()
    mem_raw = snapshot.get("memory")
    mem: dict[str, Any] = mem_raw if isinstance(mem_raw, dict) else {}
    disks = snapshot.get("disks")
    if not isinstance(disks, list):
        disks = []
    top_procs = snapshot.get("top_processes")
    if not isinstance(top_procs, list):
        top_procs = []
    if rich_tools is None:
        typer.echo(f"CPU: {snapshot.get('cpu_percent', 0)}%")
        typer.echo(f"Memory: {mem.get('percent', 0)}%")
        typer.echo(f"Processes: {snapshot.get('process_count', 0)}")
        typer.echo(f"Uptime: {format_duration(int(snapshot.get('uptime_seconds', 0) or 0))}")
        typer.echo(f"Status: {snapshot.get('overall_level', 'INFO')}")
        for disk in disks:
            if not isinstance(disk, dict):
                continue
            typer.echo(
                f"{disk.get('mountpoint', '')}: {disk.get('percent', 0)}% used "
                f"({human_size(int(disk.get('free', 0) or 0))} free)"
            )
        return

    Console, Table = rich_tools
    console = Console()
    table = Table(title=f"System Health ({snapshot.get('overall_level', 'INFO')})")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("CPU", f"{snapshot.get('cpu_percent', 0)}%")
    table.add_row("Memory", f"{mem.get('percent', 0)}%")
    table.add_row("Processes", str(snapshot.get("process_count", 0)))
    table.add_row("Uptime", format_duration(int(snapshot.get("uptime_seconds", 0) or 0)))
    if snapshot.get("load_average") is not None:
        table.add_row("Load average", str(snapshot["load_average"]))

    for disk in disks:
        if not isinstance(disk, dict):
            continue
        table.add_row(
            f"Disk {disk.get('mountpoint', '')}",
            f"{disk.get('percent', 0)}% used / {human_size(int(disk.get('free', 0) or 0))} free",
        )

    console.print(table)

    process_table = Table(title="Top Processes")
    process_table.add_column("PID")
    process_table.add_column("Name")
    process_table.add_column("CPU %")
    process_table.add_column("Memory %")
    for process in top_procs:
        if not isinstance(process, dict):
            continue
        process_table.add_row(
            str(process.get("pid", "")),
            str(process.get("name", "")),
            str(process.get("cpu_percent", "")),
            str(process.get("memory_percent", "")),
        )
    console.print(process_table)


def print_transitions(
    previous_levels: dict[str, str] | None, current_levels: dict[str, str]
) -> None:
    if previous_levels is None:
        return
    for metric, level in current_levels.items():
        if previous_levels.get(metric) != level:
            typer.echo(f"{metric.upper()} changed from {previous_levels.get(metric)} to {level}")

def run_monitor(watch: bool, interval: int, config_path: Path | None) -> None:
    ensure_home_layout()
    thresholds = read_thresholds(config_path)
    previous_levels: dict[str, str] | None = None

    try:
        while True:
            snapshot = snapshot_system(thresholds)
            write_snapshot(snapshot, thresholds)
            render_snapshot(snapshot)
            print_transitions(previous_levels, snapshot["levels"])
            previous_levels = snapshot["levels"]
            logger.info("Health snapshot written with status %s", snapshot["overall_level"])

            if not watch:
                return

            time.sleep(interval)
    except KeyboardInterrupt:
        append_json_line(
            get_health_log_file(),
            {
                "timestamp": datetime.now().isoformat(),
                "event": "shutdown",
                "message": "Watch mode interrupted with Ctrl+C",
            },
        )
        typer.echo("Stopped watch mode.")
















def main() -> None:
    app()


if __name__ == "__main__":
    main()
