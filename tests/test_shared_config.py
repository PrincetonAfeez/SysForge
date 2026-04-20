from __future__ import annotations

from pathlib import Path

from sysforge.shared_config import deep_merge, load_shared_config

def test_deep_merge_nested_dicts() -> None:
    base = {"a": 1, "nested": {"x": 1, "y": 2}}
    override = {"nested": {"y": 9, "z": 3}, "b": 2}
    assert deep_merge(base, override) == {
        "a": 1,
        "b": 2,
        "nested": {"x": 1, "y": 9, "z": 3},
    }

