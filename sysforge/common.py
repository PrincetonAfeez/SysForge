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
