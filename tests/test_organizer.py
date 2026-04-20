from __future__ import annotations

import json
from pathlib import Path

import pytest

from sysforge.organizer.organizer import (
    choose_destination,
    resolve_relative_folder,
    run_organizer,
)

def test_resolve_relative_folder_extension() -> None:
    rules = {"extension_categories": {".txt": "Text"}}
    folder = resolve_relative_folder(Path("notes.txt"), "extension", rules)
    assert folder == Path("Text")

def test_choose_destination_rename_on_conflict(tmp_path: Path) -> None:
    base = tmp_path / "work"
    rel = Path("Cat")
    dest_dir = base / rel
    dest_dir.mkdir(parents=True)
    existing = dest_dir / "file.txt"
    existing.write_text("x", encoding="utf-8")
    source = base / "file.txt"
    source.write_text("y", encoding="utf-8")
    dest, action = choose_destination(source, base, rel, "rename")
    assert dest is not None
    assert dest.name.startswith("file_")
    assert action == "rename"

def test_resolve_relative_folder_size_buckets_sorted(tmp_path: Path) -> None:
    half_mb = tmp_path / "half.bin"
    half_mb.write_bytes(b"0" * (512 * 1024))
    rules = {"size_buckets": {"large": {"max_mb": None}, "small": {"max_mb": 1}}}
    assert resolve_relative_folder(half_mb, "size", rules) == Path("Small")

    big = tmp_path / "big.bin"
    big.write_bytes(b"1" * (2 * 1024 * 1024))
    assert resolve_relative_folder(big, "size", rules) == Path("Large")

def test_resolve_relative_folder_extension_no_suffix_category() -> None:
    rules = {
        "extension_categories": {".txt": "Text"},
        "extension_no_suffix_category": "Scripts",
    }
    assert resolve_relative_folder(Path("Makefile"), "extension", rules) == Path("Scripts")

def test_resolve_relative_folder_extension_empty_explicit() -> None:
    rules = {"extension_categories": {"": "NoExt"}}
    assert resolve_relative_folder(Path("README"), "extension", rules) == Path("NoExt")

def test_run_organizer_missing_target_raises(isolated_sysforge_home: None, tmp_path: Path) -> None:
    rules_path = tmp_path / "rules.json"
    rules_path.write_text("{}", encoding="utf-8")
    missing = tmp_path / "nope"
    with pytest.raises(ValueError, match="Target directory"):
        run_organizer(
            missing,
            sort_mode="extension",
            rules_path=rules_path,
            dry_run=True,
            conflict_mode="rename",
            include_hidden=False,
            recursive=False,
        )


