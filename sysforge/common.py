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


