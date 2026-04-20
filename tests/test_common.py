from __future__ import annotations

import sys
from pathlib import Path

import pytest

from sysforge.common import (
    flatten_dict,
    format_duration,
    get_nested_value,
    human_size,
    is_hidden_path,
    load_json_file,
    parse_cli_value,
    set_nested_value,
    write_json_file,
)

