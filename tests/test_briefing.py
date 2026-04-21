from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from sysforge.briefing import briefing as briefing_mod


def test_sanitize_single_line() -> None:
    assert briefing_mod._sanitize_single_line("  a\nb\tc  ") == "a b c"
    assert briefing_mod._sanitize_single_line("x\x00y") == "x y"

def test_load_mock_data_default_filenames(tmp_path: Path) -> None:
    data = tmp_path / "d"
    data.mkdir()
    (data / "weather.json").write_text("{}", encoding="utf-8")
    (data / "quotes.json").write_text("[]", encoding="utf-8")
    (data / "calendar.json").write_text("[]", encoding="utf-8")
    loaded = briefing_mod.load_mock_data({}, data)
    assert loaded["weather"] == {"default": {}, "days": {}}
    assert loaded["quotes"] == []
    assert loaded["calendar"] == []

def test_pick_weather() -> None:
    weather = {"default": {"temp": 1}, "days": {"2026-01-02": {"temp": 2}}}
    assert briefing_mod.pick_weather(weather, "2026-01-02")["temp"] == 2
    assert briefing_mod.pick_weather(weather, "2099-01-01")["temp"] == 1


def test_calendar_items_for_day() -> None:
    items = [
        {"date": "2026-01-01", "time": "10:00", "title": "A"},
        {"date": "2026-01-01", "time": "09:00", "title": "B"},
        {"date": "2026-01-02", "time": "08:00", "title": "C"},
    ]
    day = briefing_mod.calendar_items_for_day(items, "2026-01-01")
    assert [i["title"] for i in day] == ["B", "A"]
