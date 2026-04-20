from __future__ import annotations

import os
from pathlib import Path
from typing import Any, cast

from sysforge.common import load_json_file
from sysforge.sysforge_paths import (
    ensure_home_layout,
    get_default_config_path,
    get_user_config_path,
)

def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged
