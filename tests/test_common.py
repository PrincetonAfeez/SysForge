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

def test_parse_cli_value() -> None:
    assert parse_cli_value("true") is True
    assert parse_cli_value("FALSE") is False
    assert parse_cli_value("null") is None
    assert parse_cli_value("42") == 42
    assert parse_cli_value("3.5") == 3.5
    assert parse_cli_value('{"a":1}') == {"a": 1}
    assert parse_cli_value("plain") == "plain"

def test_flatten_and_nested_roundtrip() -> None:
    data = {"app": {"db": {"host": "localhost"}}}
    flat = flatten_dict(data)
    assert flat == {"app.db.host": "localhost"}
    assert get_nested_value(data, "app.db.host") == "localhost"
    set_nested_value(data, "app.db.port", 5432)
    assert data["app"]["db"]["port"] == 5432

def test_set_nested_value_rejects_non_object_path() -> None:
    data: dict = {"a": "scalar"}
    with pytest.raises(ValueError):
        set_nested_value(data, "a.b", 1)

