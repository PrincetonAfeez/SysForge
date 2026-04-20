from __future__ import annotations

import csv
import ctypes
import json
import os
import shutil
import stat
import sys
from ctypes import wintypes
from datetime import datetime
from pathlib import Path
from typing import Any, NoReturn

import typer

def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

def load_json_file(path: Path, default: Any = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(f"File not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)

def write_json_file(
    path: Path,
    data: Any,
    *,
    atomic: bool = False,
    backup: bool = False,
) -> None:
    ensure_parent(path)
    if backup and path.exists():
        backup_path = path.with_suffix(f"{path.suffix}.bak")
        shutil.copy2(path, backup_path)

    payload = json.dumps(data, indent=2, ensure_ascii=True)
    if atomic:
        temp_path = path.with_suffix(f"{path.suffix}.tmp")
        temp_path.write_text(payload, encoding="utf-8")
        os.replace(temp_path, path)
    else:
        path.write_text(payload, encoding="utf-8")

def write_text_file(path: Path, text: str) -> None:
    ensure_parent(path)
    path.write_text(text, encoding="utf-8")


def append_json_line(path: Path, payload: dict[str, Any]) -> None:
    ensure_parent(path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True))
        handle.write("\n")

def append_csv_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def is_hidden_path(path: Path) -> bool:
    if path.name.startswith("."):
        return True
    if sys.platform != "win32":
        return False
    hidden_flag = getattr(stat, "FILE_ATTRIBUTE_HIDDEN", 2)
    try:
        st = path.stat(follow_symlinks=False)
    except OSError:
        return False
    attrs = getattr(st, "st_file_attributes", None)
    if attrs is not None:
        return bool(attrs & hidden_flag)
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    get_attrs = kernel32.GetFileAttributesW
    get_attrs.argtypes = [wintypes.LPCWSTR]
    get_attrs.restype = wintypes.DWORD
    raw = get_attrs(os.fsdecode(path))
    invalid = 0xFFFFFFFF
    if raw == invalid:
        return False
    return bool(raw & hidden_flag)

def human_size(size_in_bytes: int) -> str:
    value = float(size_in_bytes)
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    while value >= 1024 and unit_index < len(units) - 1:
        value /= 1024
        unit_index += 1
    return f"{value:.1f} {units[unit_index]}"

def format_duration(duration_seconds: int) -> str:
    hours, remainder = divmod(max(duration_seconds, 0), 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours}h {minutes:02d}m"

def flatten_dict(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for key, value in data.items():
        dotted = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flattened.update(flatten_dict(value, dotted))
        else:
            flattened[dotted] = value
    return flattened

def get_nested_value(data: dict[str, Any], dotted_key: str) -> Any:
    current: Any = data
    for part in dotted_key.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(dotted_key)
        current = current[part]
    return current

def set_nested_value(data: dict[str, Any], dotted_key: str, value: Any) -> None:
    current = data
    parts = dotted_key.split(".")
    for part in parts[:-1]:
        current = current.setdefault(part, {})
        if not isinstance(current, dict):
            raise ValueError(f"Cannot set nested value under non-object key: {part}")
    current[parts[-1]] = value

def parse_cli_value(raw_value: str) -> Any:
    lowered = raw_value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "null":
        return None

    try:
        return int(raw_value)
    except ValueError:
        pass

    try:
        return float(raw_value)
    except ValueError:
        pass

    if raw_value.startswith("{") or raw_value.startswith("["):
        try:
            return json.loads(raw_value)
        except json.JSONDecodeError:
            return raw_value

    return raw_value

def parse_local_datetime(raw_value: str, timezone_name: str | None = None) -> datetime:
    from zoneinfo import ZoneInfo

    timezone = None
    if timezone_name:
        timezone = ZoneInfo(timezone_name)

    formats = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H:%M:%S",
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(raw_value, fmt)
            return parsed.replace(tzinfo=timezone)
        except ValueError:
            continue

    parsed = datetime.fromisoformat(raw_value)
    if parsed.tzinfo is None and timezone is not None:
        parsed = parsed.replace(tzinfo=timezone)
    return parsed

def print_error(message: str, exit_code: int = 1) -> NoReturn:
    typer.secho(message, fg=typer.colors.RED, err=True)
    raise typer.Exit(code=exit_code)
