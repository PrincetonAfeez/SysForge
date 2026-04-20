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

def test_deep_merge_replaces_non_dict_values() -> None:
    assert deep_merge({"a": {"b": 1}}, {"a": 2}) == {"a": 2}


def test_load_shared_config_merges_user_over_defaults(
    isolated_sysforge_home: None, tmp_path: Path
) -> None:
    from sysforge.sysforge_paths import ensure_home_layout, get_user_config_path

    ensure_home_layout()
    user_path = get_user_config_path()
    user_path.write_text(
        '{"user": {"name": "Tester"}, "report": {"default_format": "markdown"}}',
        encoding="utf-8",
    )
    cfg = load_shared_config()
    assert cfg["user"]["name"] == "Tester"
    assert cfg["report"]["default_format"] == "markdown"
