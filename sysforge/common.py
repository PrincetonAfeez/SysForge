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
