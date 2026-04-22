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

def validate_type(value: Any, expected_type: str) -> bool:
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "array":
        return isinstance(value, list)
    return True

def validate_against_schema(
    value: Any,
    schema: dict[str, Any],
    key_path: str = "root",
) -> tuple[list[str], Any]:
    errors: list[str] = []

    expected_type = schema.get("type")
    if expected_type and not validate_type(value, expected_type):
        errors.append(f"{key_path}: expected {expected_type}, got {type(value).__name__}")
        return errors, value

    if expected_type == "object":
        properties = schema.get("properties", {})
        required_keys = schema.get("required", [])

        for required_key in required_keys:
            if required_key not in value:
                errors.append(f"{key_path}.{required_key}: missing required key")

        updated_value = dict(value)
        for child_key, child_schema in properties.items():
            child_path = f"{key_path}.{child_key}"
            if child_key not in updated_value:
                if "default" in child_schema:
                    updated_value[child_key] = child_schema["default"]
                continue
            child_errors, child_value = validate_against_schema(
                updated_value[child_key], child_schema, child_path
            )
            updated_value[child_key] = child_value
            errors.extend(child_errors)
        return errors, updated_value

    if expected_type == "array":
        items_schema = schema.get("items")
        min_items = schema.get("minItems")
        max_items = schema.get("maxItems")
        if min_items is not None and len(value) < min_items:
            errors.append(
                f"{key_path}: array length {len(value)} is less than minItems {min_items}"
            )
        if max_items is not None and len(value) > max_items:
            errors.append(
                f"{key_path}: array length {len(value)} is greater than maxItems {max_items}"
            )
        updated_list: list[Any] = []
        for index, item in enumerate(value):
            child_path = f"{key_path}[{index}]"
            if items_schema is not None:
                child_errors, child_value = validate_against_schema(item, items_schema, child_path)
                errors.extend(child_errors)
                updated_list.append(child_value)
            else:
                updated_list.append(item)
        return errors, updated_list

    if expected_type in {"integer", "number"}:
        minimum = schema.get("min")
        maximum = schema.get("max")
        if minimum is not None and value < minimum:
            errors.append(f"{key_path}: value {value} is smaller than min {minimum}")
        if maximum is not None and value > maximum:
            errors.append(f"{key_path}: value {value} is larger than max {maximum}")

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{key_path}: value {value!r} is not in allowed options {schema['enum']}")

    return errors, value


def diff_configs(left: dict[str, Any], right: dict[str, Any]) -> dict[str, list[str]]:
    left_flat = flatten_dict(left)
    right_flat = flatten_dict(right)
    left_keys = set(left_flat)
    right_keys = set(right_flat)

    added = [f"{key}: {right_flat[key]!r}" for key in sorted(right_keys - left_keys)]
    removed = [f"{key}: {left_flat[key]!r}" for key in sorted(left_keys - right_keys)]
    changed = [
        f"{key}: {left_flat[key]!r} -> {right_flat[key]!r}"
        for key in sorted(left_keys & right_keys)
        if left_flat[key] != right_flat[key]
    ]
    return {"added": added, "removed": removed, "changed": changed}


def template_path_for_name(name: str) -> Path:
    template_path = PACKAGE_ROOT / "config" / "templates" / f"{name}.json"
    if not template_path.exists():
        print_error(f"Template not found: {name}")
    return template_path


@app.command()
def get(
    key: str = typer.Argument(..., help="Dot-notation key, like database.host"),
    file: Path = typer.Option(..., "--file", help="JSON config file"),
) -> None:
    try:
        value = get_nested_value(load_config_file(file), key)
    except FileNotFoundError:
        print_error(f"Config file not found: {file}", exit_code=2)
    except KeyError:
        print_error(f"Key not found: {key}")
    except (ValueError, JSONDecodeError, TypeError, OSError) as exc:
        print_error(str(exc), exit_code=2)

    if isinstance(value, (dict, list)):
        typer.echo(json.dumps(value, indent=2))
    else:
        typer.echo(value)



















def main() -> None:
    app()


if __name__ == "__main__":
    main()
