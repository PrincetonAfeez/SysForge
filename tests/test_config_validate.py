from __future__ import annotations

import json
from pathlib import Path

import pytest

from sysforge.common import write_json_file
from sysforge.config.config import (
    apply_environment_overrides,
    diff_configs,
    load_config_file,
    validate_against_schema,
)


def test_validate_object_required_and_defaults() -> None:
    schema: dict = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "count": {"type": "integer", "default": 0},
        },
        "required": ["name"],
    }
    errors, _ = validate_against_schema({}, schema)
    assert errors

    errors, merged = validate_against_schema({"name": "ok"}, schema)
    assert not errors
    assert merged["name"] == "ok"
    assert merged["count"] == 0

def test_validate_min_max_enum() -> None:
    schema = {"type": "integer", "min": 1, "max": 3, "enum": [1, 2, 3]}
    errors, _ = validate_against_schema(0, schema)
    assert any("min" in e for e in errors)

    errors, _ = validate_against_schema(5, schema)
    assert any("max" in e for e in errors)

    errors, _ = validate_against_schema(2, schema)
    assert not errors

def test_validate_type_mismatch() -> None:
    schema = {"type": "string"}
    errors, _ = validate_against_schema(99, schema)
    assert errors


def test_validate_array_items_and_length() -> None:
    schema = {
        "type": "array",
        "items": {"type": "integer", "min": 1, "max": 10},
        "minItems": 2,
        "maxItems": 3,
    }
    errors, _ = validate_against_schema([1], schema)
    assert any("minItems" in e for e in errors)

    errors, _ = validate_against_schema([1, 2, 3, 4], schema)
    assert any("maxItems" in e for e in errors)

    errors, merged = validate_against_schema([2, 5], schema)
    assert not errors
    assert merged == [2, 5]


def test_diff_configs() -> None:
    left = {"app": {"name": "a"}, "x": 1}
    right = {"app": {"name": "b"}, "y": 2}
    diff = diff_configs(left, right)
    assert any("app.name" in line for line in diff["changed"])
    assert any("x" in line for line in diff["removed"]) or any("x" in r for r in diff["removed"])


def test_apply_environment_duplicate_path_mapping() -> None:
    data = {"a": {"b": 1}, "a_b": 2}
    out = apply_environment_overrides(data)
    assert isinstance(out, dict)
    assert out["a"]["b"] == 1 and out["a_b"] == 2


def test_load_config_file_requires_object(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("[1,2]", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON object"):
        load_config_file(path, apply_env=False)
