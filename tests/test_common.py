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

def test_write_json_file_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    payload = {"a": 1, "nested": {"b": True}}
    write_json_file(path, payload)
    assert load_json_file(path) == payload

def test_write_json_file_atomic(tmp_path: Path) -> None:
    path = tmp_path / "atomic.json"
    write_json_file(path, {"v": 1}, atomic=True)
    assert load_json_file(path) == {"v": 1}
    assert not (tmp_path / "atomic.json.tmp").exists()
