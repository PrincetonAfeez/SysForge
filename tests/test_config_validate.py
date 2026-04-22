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
