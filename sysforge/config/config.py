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



























def main() -> None:
    app()


if __name__ == "__main__":
    main()
