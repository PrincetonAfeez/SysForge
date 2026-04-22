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

def test_determine_levels_skips_bad_disk_entries() -> None:
    th = _default_thresholds()
    levels = monitor_mod.determine_levels(
        {
            "cpu_percent": 0,
            "memory": {"percent": 0},
            "disks": ["not-a-dict", {"percent": 10}],
        },
        th,
    )
    assert levels["disk"] == "INFO"

def test_print_transitions_emits_on_change(capsys: pytest.CaptureFixture[str]) -> None:
    monitor_mod.print_transitions(
        {"cpu": "INFO", "memory": "INFO"},
        {"cpu": "WARNING", "memory": "INFO"},
    )
    out = capsys.readouterr().out
    assert "CPU" in out and "WARNING" in out


def test_print_transitions_none_previous_is_silent(
    capsys: pytest.CaptureFixture[str],
) -> None:
    monitor_mod.print_transitions(None, {"cpu": "WARNING"})
    assert capsys.readouterr().out == ""


def test_read_thresholds_coerces_strings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        monitor_mod,
        "load_shared_config",
        lambda: {
            "health": {
                "cpu_warning": "70",
                "keep_files": "3",
                "top_process_scan": "100",
                "max_rss_scan": "3000",
            }
        },
    )
    th = monitor_mod.read_thresholds()
    assert th["cpu_warning"] == 70
    assert th["keep_files"] == 3
    assert th["top_process_scan"] == 100
    assert th["max_rss_scan"] == 3000

def test_read_thresholds_non_object_health(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(monitor_mod, "load_shared_config", lambda: {"health": "bad"})
    th = monitor_mod.read_thresholds()
    assert th["cpu_warning"] == 80

def test_rotate_log_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log = tmp_path / "health.jsonl"
    monkeypatch.setattr(monitor_mod, "get_health_log_file", lambda: log)
    log.write_bytes(b"0" * (2 * 1024 * 1024))
    monitor_mod.rotate_log_file(1, 5)
    assert log.with_name("health.jsonl.1").exists()


def test_normalize_load_average() -> None:
    assert monitor_mod.normalize_load_average(None) is None
    assert monitor_mod.normalize_load_average((1.5, 2.0, 3.25)) == [1.5, 2.0, 3.25]
    assert monitor_mod.normalize_load_average([0.1, 0.2, 0.3]) == [0.1, 0.2, 0.3]
    assert monitor_mod.normalize_load_average((1, 2)) is None
    assert monitor_mod.normalize_load_average("nope") is None

def test_top_processes_samples_when_many_pids(monkeypatch: pytest.MonkeyPatch) -> None:
    process_calls: list[int] = []

    class _Mem:
        def __init__(self, rss: int) -> None:
            self.rss = rss

    class FakeProc:
        def __init__(self, pid: int) -> None:
            self.pid = pid

        def memory_info(self) -> _Mem:
            return _Mem(self.pid * 1000)

        def cpu_percent(self, interval: object = None) -> float:
            return 0.1

        def memory_percent(self) -> float:
            return 0.2

        def name(self) -> str:
            return "fake"

    class FakePsutil:
        NoSuchProcess = Exception
        AccessDenied = Exception

        def pids(self) -> list[int]:
            return list(range(500))

        def Process(self, pid: int) -> FakeProc:
            process_calls.append(pid)
            return FakeProc(pid)

    monkeypatch.setattr(monitor_mod.time, "sleep", lambda _s: None)
    out = monitor_mod.top_processes(
        FakePsutil(),
        limit=3,
        cpu_candidate_cap=10,
        max_rss_scan=20,
    )
    assert len(process_calls) == 20
    assert len(out) <= 3
    assert all(isinstance(p["pid"], int) for p in out)
