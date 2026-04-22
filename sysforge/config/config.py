from __future__ import annotations

import json
import os
import shutil
from json import JSONDecodeError
from pathlib import Path
from typing import Any, cast

import typer

from sysforge.common import (
    flatten_dict,
    get_nested_value,
    load_json_file,
    parse_cli_value,
    print_error,
    set_nested_value,
    write_json_file,
)
from sysforge.logging_utils import get_logger
from sysforge.sysforge_paths import PACKAGE_ROOT, ensure_home_layout

app = typer.Typer(help="Manage JSON configuration files.")
logger = get_logger("sysforge.config")


def load_config_file(path: Path, *, apply_env: bool = True) -> dict[str, Any]:
    data = load_json_file(path)
    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a JSON object: {path}")
    return apply_environment_overrides(data) if apply_env else data

def apply_environment_overrides(data: dict[str, Any]) -> dict[str, Any]:
    updated = json.loads(json.dumps(data))
    flattened = flatten_dict(data)
    env_to_paths: dict[str, list[str]] = {}
    for dotted_key in flattened:
        env_key = f"APP_{dotted_key.replace('.', '_').upper()}"
        env_to_paths.setdefault(env_key, []).append(dotted_key)
    for env_key, paths in env_to_paths.items():
        unique = sorted(set(paths))
        if len(unique) > 1:
            logger.warning(
                "Multiple config paths map to the same env var %s: %s "
                "(only one value can be set via the environment)",
                env_key,
                unique,
            )
    for dotted_key in flattened:
        env_key = f"APP_{dotted_key.replace('.', '_').upper()}"
        if env_key in os.environ:
            set_nested_value(updated, dotted_key, parse_cli_value(os.environ[env_key]))
    return cast(dict[str, Any], updated)
























def main() -> None:
    app()


if __name__ == "__main__":
    main()
