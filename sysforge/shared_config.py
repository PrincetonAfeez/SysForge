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


def load_shared_config(config_path: Path | None = None) -> dict[str, Any]:
    ensure_home_layout()
    default_config = cast(dict[str, Any], load_json_file(get_default_config_path(), default={}))

    if config_path is None:
        env_path = os.environ.get("SYSFORGE_CONFIG")
        if env_path:
            config_path = Path(env_path)
        else:
            config_path = get_user_config_path()

    if not config_path.exists():
        return default_config

    user_config = cast(dict[str, Any], load_json_file(config_path, default={}))
    return deep_merge(default_config, user_config)
