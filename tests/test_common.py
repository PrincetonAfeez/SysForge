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

def test_load_json_file_missing_no_default(tmp_path: Path) -> None:
    missing = tmp_path / "nope.json"
    with pytest.raises(FileNotFoundError):
        load_json_file(missing)

def test_load_json_file_missing_with_default(tmp_path: Path) -> None:
    missing = tmp_path / "nope.json"
    assert load_json_file(missing, default={"k": 1}) == {"k": 1}

