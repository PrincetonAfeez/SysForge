from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import typer

from sysforge.common import (
    human_size,
    is_hidden_path,
    load_json_file,
    print_error,
    write_json_file,
)
from sysforge.logging_utils import get_logger
from sysforge.shared_config import load_shared_config
from sysforge.sysforge_paths import (
    ensure_home_layout,
    get_default_organizer_rules_path,
    get_organizer_log_dir,
)

app = typer.Typer(help="Organize files in a folder based on extension, date, or size.")
logger = get_logger("sysforge.organizer")


def _normalize_log_path(path: Path) -> str:
    try:
        return str(path.resolve(strict=False))
    except OSError:
        return str(path)


def _ordered_size_bucket_entries(
    buckets: dict[str, Any],
) -> list[tuple[str, float | None]]:
    parsed: list[tuple[str, float | None]] = []
    for bucket_name, bucket_data in buckets.items():
        raw = bucket_data.get("max_mb")
        if raw is None:
            parsed.append((bucket_name, None))
            continue
        try:
            parsed.append((bucket_name, float(raw)))
        except (TypeError, ValueError):
            parsed.append((bucket_name, float("inf")))

    def sort_key(entry: tuple[str, float | None]) -> tuple[int, float, str]:
        name, max_mb = entry
        if max_mb is None:
            return (1, float("inf"), name)
        return (0, max_mb, name)

    parsed.sort(key=sort_key)
    return parsed

def load_rules(rules_path: Path | None, config_path: Path | None = None) -> dict[str, Any]:
    config = load_shared_config(config_path)
    if rules_path is None:
        raw_rules = config.get("organizer", {}).get("rules_file", "")
        if raw_rules:
            rules_path = Path(raw_rules)
        else:
            rules_path = get_default_organizer_rules_path()
    return cast(dict[str, Any], load_json_file(rules_path, default={}))


def iter_candidate_files(
    target: Path, recursive: bool, include_hidden: bool
) -> tuple[list[Path], list[str]]:
    messages: list[str] = []
    files: list[Path] = []
    paths = target.rglob("*") if recursive else target.iterdir()

    for path in paths:
        if not path.exists():
            continue
        if path.is_symlink():
            messages.append(f"Skipped symlink: {_normalize_log_path(path)}")
            continue
        if path.is_dir():
            continue
        if not include_hidden and is_hidden_path(path):
            messages.append(f"Skipped hidden file: {_normalize_log_path(path)}")
            continue
        files.append(path)

    return files, messages


def resolve_relative_folder(path: Path, mode: str, rules: dict[str, Any]) -> Path:
    if mode == "extension":
        extension_map = rules.get("extension_categories", {})
        suffix = path.suffix.lower()
        if suffix == "":
            if "" in extension_map:
                category = extension_map[""]
            else:
                category = rules.get("extension_no_suffix_category", "Other")
        else:
            category = extension_map.get(suffix, "Other")
        return Path(str(category))

    if mode == "date":
        modified_at = datetime.fromtimestamp(path.stat().st_mtime)
        date_format = rules.get("date_format", "%Y/%m")
        return Path(modified_at.strftime(date_format))

    if mode == "size":
        size_in_mb = path.stat().st_size / (1024 * 1024)
        buckets = rules.get("size_buckets", {})
        for bucket_name, max_mb in _ordered_size_bucket_entries(buckets):
            if max_mb is None or size_in_mb <= max_mb:
                return Path(bucket_name.title())
        return Path("Large")

    raise ValueError(f"Unknown mode: {mode}")


























def main() -> None:
    app()


if __name__ == "__main__":
    main()
