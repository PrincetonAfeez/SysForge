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


def test_format_temperature_value() -> None:
    assert briefing_mod._format_temperature_value(32, "C") == "0"
    assert briefing_mod._format_temperature_value(50, "F") == "50"
    assert briefing_mod._format_temperature_value("n/a", "F") == "n/a"

def test_resolve_disk_usage_root(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b" / "c"
    assert briefing_mod._resolve_disk_usage_root(nested) == tmp_path.resolve()

def test_build_text_briefing_temperature_unit() -> None:
    now = datetime(2026, 1, 1, 12, 0, tzinfo=ZoneInfo("UTC"))
    snap = {
        "os": "test-os",
        "python_version": "3.14",
        "uptime": "0h 00m",
        "free_disk": 10 * 1024**3,
        "disk_root": "/tmp",
    }
    text = briefing_mod.build_text_briefing(
        greeting="Hi",
        now=now,
        weather={"condition": "OK", "temp": 32, "high": 50, "low": 40},
        quote=None,
        calendar_items=None,
        system_snapshot=snap,
        temperature_unit="C",
    )
    assert "°C" in text
    assert "Current: 0 °C" in text

