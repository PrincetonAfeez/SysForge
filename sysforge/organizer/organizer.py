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




























def main() -> None:
    app()


if __name__ == "__main__":
    main()
