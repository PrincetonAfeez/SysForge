from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from sysforge.monitor import monitor as monitor_mod


def _default_thresholds() -> dict:
    return {
        "cpu_warning": 80,
        "cpu_critical": 95,
        "memory_warning": 90,
        "memory_critical": 97,
        "disk_warning": 80,
        "disk_critical": 95,
        "rotate_mb": 10,
        "keep_files": 5,
        "top_process_scan": 80,
        "max_rss_scan": 4000,
    }

def test_coerce_threshold_int() -> None:
    assert monitor_mod._coerce_threshold_int(None, 10) == 10
    assert monitor_mod._coerce_threshold_int(42, 10) == 42
    assert monitor_mod._coerce_threshold_int("75", 10) == 75
    assert monitor_mod._coerce_threshold_int("3.2", 10) == 3
    assert monitor_mod._coerce_threshold_int(True, 10) == 10
    assert monitor_mod._coerce_threshold_int("nope", 10) == 10


def test_level_for_percent() -> None:
    assert monitor_mod.level_for_percent(50, 80, 95) == "INFO"
    assert monitor_mod.level_for_percent(85, 80, 95) == "WARNING"
    assert monitor_mod.level_for_percent(96, 80, 95) == "CRITICAL"


def test_overall_level() -> None:
    assert monitor_mod.overall_level({"a": "INFO", "b": "WARNING"}) == "WARNING"
    assert monitor_mod.overall_level({"a": "CRITICAL", "b": "WARNING"}) == "CRITICAL"
    assert monitor_mod.overall_level({"a": "INFO"}) == "INFO"


def test_determine_levels_tolerates_partial_snapshot() -> None:
    th = _default_thresholds()
    snap = {
        "cpu_percent": 10.0,
        "memory": {"percent": 20.0},
        "disks": [{"percent": 30}],
    }
    levels = monitor_mod.determine_levels(snap, th)
    assert set(levels.keys()) == {"cpu", "memory", "disk"}
    assert all(v == "INFO" for v in levels.values())

def test_determine_levels_cpu_warning_and_critical() -> None:
    th = _default_thresholds()
    assert (
        monitor_mod.determine_levels(
            {"cpu_percent": 85.0, "memory": {"percent": 10}, "disks": []},
            th,
        )["cpu"]
        == "WARNING"
    )
    assert (
        monitor_mod.determine_levels(
            {"cpu_percent": 96.0, "memory": {"percent": 10}, "disks": []},
            th,
        )["cpu"]
        == "CRITICAL"
    )

def test_determine_levels_memory_warning_and_critical() -> None:
    th = _default_thresholds()
    assert (
        monitor_mod.determine_levels(
            {"cpu_percent": 10.0, "memory": {"percent": 92.0}, "disks": []},
            th,
        )["memory"]
        == "WARNING"
    )
    assert (
        monitor_mod.determine_levels(
            {"cpu_percent": 10.0, "memory": {"percent": 98.0}, "disks": []},
            th,
        )["memory"]
        == "CRITICAL"
    )


def test_determine_levels_disk_worst_mount_wins() -> None:
    th = _default_thresholds()
    assert (
        monitor_mod.determine_levels(
            {
                "cpu_percent": 10.0,
                "memory": {"percent": 10.0},
                "disks": [{"percent": 50.0}, {"percent": 85.0}],
            },
            th,
        )["disk"]
        == "WARNING"
    )
    assert (
        monitor_mod.determine_levels(
            {
                "cpu_percent": 10.0,
                "memory": {"percent": 10.0},
                "disks": [{"percent": 85.0}, {"percent": 96.0}],
            },
            th,
        )["disk"]
        == "CRITICAL"
    )

