from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from sysforge.timetracker import timetracker as tt

UTC = ZoneInfo("UTC")

MIN_CONFIG = {
    "user": {"timezone": "UTC"},
    "time": {"project_rates": {"Acme": 100.0}},
}



@pytest.fixture
def tt_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tt, "load_shared_config", lambda: MIN_CONFIG)

def test_seconds_between() -> None:
    a = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    b = datetime(2026, 1, 1, 11, 30, tzinfo=UTC)
    assert tt.seconds_between(a, b) == 5400

def test_make_entry_id_has_suffix() -> None:
    eid = tt.make_entry_id()
    assert eid.startswith("entry-")
    assert eid.count("-") >= 2

def test_build_entry_billable(tt_config: None) -> None:
    start = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    end = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    entry = tt.build_entry(task="Work", start_time=start, end_time=end, project="Acme", tag="dev")
    assert entry["duration_seconds"] == 3600
    assert entry["billable_rate"] == 100.0
    assert entry["billable_total"] == 100.0

def test_normalize_timesheet_payload_skips_bad(tt_config: None) -> None:
    raw = {
        "active_timer": None,
        "entries": [
            {
                "id": "good",
                "task": "T",
                "start_time": "2026-01-01T10:00:00+00:00",
                "end_time": "2026-01-01T11:00:00+00:00",
                "duration_seconds": 3600,
                "billable_rate": 0,
                "billable_total": 0,
                "project": "P",
                "tag": "g",
            },
            "not-a-dict",
            {"id": "", "task": "x"},
        ],
    }
    out = tt.normalize_timesheet_payload(raw)
    assert len(out["entries"]) == 1
    assert out["entries"][0]["id"] == "good"

def test_normalize_timesheet_payload_skips_bad(tt_config: None) -> None:
    raw = {
        "active_timer": None,
        "entries": [
            {
                "id": "good",
                "task": "T",
                "start_time": "2026-01-01T10:00:00+00:00",
                "end_time": "2026-01-01T11:00:00+00:00",
                "duration_seconds": 3600,
                "billable_rate": 0,
                "billable_total": 0,
                "project": "P",
                "tag": "g",
            },
            "not-a-dict",
            {"id": "", "task": "x"},
        ],
    }
    out = tt.normalize_timesheet_payload(raw)
    assert len(out["entries"]) == 1
    assert out["entries"][0]["id"] == "good"

