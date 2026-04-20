
from __future__ import annotations

import logging
import os
from pathlib import Path

from sysforge.sysforge_paths import ensure_home_layout, get_central_log_file


def _current_log_level() -> int:
    if os.environ.get("SYSFORGE_QUIET") == "1":
        return logging.WARNING
    if os.environ.get("SYSFORGE_VERBOSE") == "1":
        return logging.DEBUG
    return logging.INFO