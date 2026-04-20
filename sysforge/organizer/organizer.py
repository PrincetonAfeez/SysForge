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


def choose_destination(
    source: Path, base_dir: Path, relative_folder: Path, conflict_mode: str
) -> tuple[Path | None, str]:
    destination_dir = base_dir / relative_folder
    destination = destination_dir / source.name

    if destination == source:
        return None, "skip"

    if not destination.exists():
        return destination, "move"

    if conflict_mode == "skip":
        return None, "skip"

    if conflict_mode == "overwrite":
        return destination, "overwrite"

    stem = destination.stem
    suffix = destination.suffix
    counter = 1
    while True:
        renamed = destination_dir / f"{stem}_{counter}{suffix}"
        if not renamed.exists():
            return renamed, "rename"
        counter += 1


def perform_move(source: Path, destination: Path, action: str, dry_run: bool) -> Path:
    if dry_run:
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    if action == "overwrite" and destination.exists():
        destination.unlink()
    try:
        shutil.move(str(source), str(destination))
        return destination
    except FileExistsError:
        if action != "move":
            raise
        stem = destination.stem
        suffix = destination.suffix
        counter = 1
        renamed = destination
        while renamed.exists():
            renamed = destination.parent / f"{stem}_{counter}{suffix}"
            counter += 1
        shutil.move(str(source), str(renamed))
        return renamed

def build_log_path(prefix: str = "organizer") -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return get_organizer_log_dir() / f"{prefix}_{timestamp}.json"

def run_organizer(
    target: Path,
    *,
    sort_mode: str,
    rules_path: Path | None,
    dry_run: bool,
    conflict_mode: str,
    include_hidden: bool,
    recursive: bool,
    config_path: Path | None = None,
) -> dict[str, Any]:
    ensure_home_layout()
    if not target.exists() or not target.is_dir():
        raise ValueError(f"Target directory does not exist: {target}")

    rules = load_rules(rules_path, config_path)
    files, initial_messages = iter_candidate_files(target, recursive, include_hidden)

    actions: list[dict[str, Any]] = []
    skipped = len(initial_messages)
    errors = 0
    total_size_processed = 0

    for file_path in files:
        try:
            total_size_processed += file_path.stat().st_size
            relative_folder = resolve_relative_folder(file_path, sort_mode, rules)
            destination, action = choose_destination(
                file_path, target, relative_folder, conflict_mode
            )

            if destination is None:
                skipped += 1
                actions.append(
                    {
                        "source": _normalize_log_path(file_path),
                        "destination": None,
                        "status": "skipped",
                        "strategy_used": action,
                    }
                )
                continue

            final_destination = perform_move(file_path, destination, action, dry_run)
            actions.append(
                {
                    "source": _normalize_log_path(file_path),
                    "destination": _normalize_log_path(final_destination),
                    "status": "planned" if dry_run else "moved",
                    "strategy_used": action,
                }
            )
        except Exception as exc:
            errors += 1
            actions.append(
                {
                    "source": _normalize_log_path(file_path),
                    "destination": None,
                    "status": "error",
                    "error": str(exc),
                }
            )

    moved = sum(1 for item in actions if item["status"] in {"planned", "moved"})
    summary = {
        "moved": moved,
        "skipped": skipped,
        "errors": errors,
        "total_size_processed": total_size_processed,
    }
    log_payload = {
        "timestamp": datetime.now().isoformat(),
        "target": _normalize_log_path(target),
        "mode": sort_mode,
        "dry_run": dry_run,
        "conflict_mode": conflict_mode,
        "messages": initial_messages,
        "moves": actions,
        "summary": summary,
    }
    log_path = build_log_path()
    write_json_file(log_path, log_payload)
    logger.info("Organizer run complete for %s", target)
    return {
        "log_path": log_path,
        "summary": summary,
        "moves": actions,
        "messages": initial_messages,
    }





















def main() -> None:
    app()


if __name__ == "__main__":
    main()
