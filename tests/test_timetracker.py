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
