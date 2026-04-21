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

