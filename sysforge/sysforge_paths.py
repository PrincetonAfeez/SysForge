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
