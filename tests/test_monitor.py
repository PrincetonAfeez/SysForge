from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from sysforge.monitor import monitor as monitor_mod


def _default_thresholds() -> dict:
    return {
        "cpu_warning": 80,
        "cpu_critical": 95,
        "memory_warning": 90,
        "memory_critical": 97,
        "disk_warning": 80,
        "disk_critical": 95,
        "rotate_mb": 10,
        "keep_files": 5,
        "top_process_scan": 80,
        "max_rss_scan": 4000,
    }

