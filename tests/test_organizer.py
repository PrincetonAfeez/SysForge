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


