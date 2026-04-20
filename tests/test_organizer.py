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

