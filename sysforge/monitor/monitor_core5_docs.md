# Architecture Decision Record

## App 25 — System Health Monitor

**SysForge Group | Document 1 of 5**  
**Status: Accepted**  
**Date: 2026-05-08**

---

## 1. Context

The System Health Monitor is the SysForge application responsible for collecting local machine health snapshots from the command line. It reports CPU usage, memory usage, disk usage, process count, uptime, load average when available, and top processes. It can run once or continuously in watch mode, and it persists health data under the shared SysForge home directory.

Unlike earlier single-purpose CLI projects, this app lives inside the larger SysForge toolkit. That means its architecture must satisfy two different roles:

1. Act as a standalone utility through the `sysforge-health` entry point.
2. Act as a subcommand inside the unified `sysforge health` command.

The implementation also has to coordinate several shared SysForge concerns: shared configuration loading, filesystem layout creation, central logging, JSONL health history, latest snapshot persistence, and optional rich terminal rendering.

The main architectural question was how much monitoring behavior should be embedded directly in the CLI command versus separated into reusable functions that could be tested independently.

---

## 2. Decision Drivers

- **Operational usefulness:** the monitor should produce a clear health snapshot with useful metrics, not just print raw psutil objects.
- **Reusable internal API:** threshold calculation, snapshot collection, rendering, log rotation, and watch-mode control should be callable independently.
- **SysForge integration:** the app should share the same home directory, configuration file, logger, and CLI framework as the rest of SysForge.
- **CLI simplicity:** the user-facing interface should remain small: run once by default, optionally watch continuously, optionally override config.
- **Persistence:** every health check should be written to a history log and a latest-snapshot file for downstream reporting.
- **Cross-platform tolerance:** load average and disk partition behavior vary by operating system, so the app should include platform-aware fallbacks.
- **Testability:** system-level code is hard to test unless psutil, time, and filesystem behavior are isolated behind functions.
- **Portfolio value:** this project should show growth into system monitoring, dependency integration, thresholds, structured logs, and CLI operations.

---

## 3. Options Considered

### Option A — Print psutil metrics directly from the Typer callback

**Description:** The CLI command would call psutil functions, print results, and exit.

**Pros**

- Very small implementation.
- Easy to understand for a first monitoring script.
- Minimal internal structure.

**Cons**

- Hard to test without invoking the whole CLI.
- No reusable snapshot object.
- Hard to persist structured history.
- No clean path to watch mode or reporting integration.
- Business logic and presentation would be mixed together.

**Decision:** Rejected.

---

### Option B — Create a full daemon or background service

**Description:** The monitor would run as a long-lived background process, collecting health snapshots on a schedule and managing its own lifecycle.

**Pros**

- Closer to production monitoring systems.
- Could support continuous collection without a terminal session.
- Could eventually integrate with alerts or dashboards.

**Cons**

- Too large for the project scope.
- Requires process supervision, installation steps, permissions, logs, and service recovery behavior.
- Adds OS-specific complexity.
- Would obscure the learning objective behind operational mechanics.

**Decision:** Rejected for this project.

---

### Option C — Structured one-shot monitor with optional foreground watch mode

**Description:** Build reusable functions for threshold loading, snapshot collection, level determination, persistence, rendering, and watch-mode looping. The CLI runs one snapshot by default and enters a foreground loop only when `--watch` is provided.

**Pros**

- Keeps the app small enough for the portfolio scope.
- Supports both one-shot and repeated monitoring.
- Makes core logic testable without requiring real system state.
- Produces persistent JSON records for later reporting.
- Fits the SysForge command model.

**Cons**

- Not a background service.
- Watch mode stops when the terminal is closed.
- Uses local files rather than a real metrics database.
- psutil behavior still depends on the host OS.

**Decision:** Accepted.

---

## 4. Decision

The System Health Monitor will be implemented as a Typer-based SysForge app centered on reusable monitoring functions. The accepted architecture is:

- `sysforge.monitor.monitor` owns the health-monitoring application.
- `sysforge-health` runs the monitor as a standalone console script.
- `sysforge health` runs the same Typer app through the unified SysForge CLI.
- `snapshot_system()` gathers CPU, memory, disk, uptime, load average, process count, and top-process data.
- `read_thresholds()` loads warning/critical thresholds from shared SysForge config or an explicit config file.
- `determine_levels()` converts raw percentages into `INFO`, `WARNING`, and `CRITICAL` levels.
- `overall_level()` computes the worst overall status.
- `write_snapshot()` appends JSONL history and writes the latest snapshot JSON.
- `rotate_log_file()` rotates the health JSONL file when it exceeds a configured size.
- `render_snapshot()` displays either Rich tables or plain text depending on dependency availability.
- `run_monitor()` coordinates one-shot and watch-mode execution.

---

## 5. Rationale

The accepted design keeps the monitor operationally useful while remaining appropriately scoped. It avoids turning the project into a full daemon but still demonstrates important system-programming ideas: dependency loading, configuration, thresholds, structured logs, error handling, filesystem side effects, and terminal rendering.

The most important design choice is the structured snapshot dictionary. Rather than letting the CLI print psutil values immediately, the app first builds a dictionary containing the machine state. That dictionary can then be rendered to the terminal, written to JSONL, saved as the latest snapshot, and tested through unit tests.

Separating threshold logic from snapshot collection also improves maintainability. CPU, memory, and disk warning levels are not hard-coded in the rendering layer. They are loaded from config and normalized through `_coerce_threshold_int()`. This gives the project a realistic operational feel without requiring a database or remote monitoring service.

The app also uses dependency tolerance in two places. `load_psutil()` gives a clear CLI error if psutil is missing. `load_rich_table_tools()` returns `None` when Rich is unavailable, allowing the app to fall back to plain text rendering. This is a practical CLI design pattern: optional presentation upgrades should not break the core monitoring behavior.

---

## 6. Trade-offs Accepted

### 6.1 Local JSONL history instead of metrics storage

The monitor writes snapshots to a local `health_log.jsonl` file instead of a time-series database.

**Accepted because:** the project is a local CLI utility, not a production observability platform.

**Cost:** querying history and generating long-term trends is limited.

---

### 6.2 Foreground watch mode instead of a daemon

The `--watch` mode loops inside the foreground CLI process.

**Accepted because:** it is easy to reason about, easy to stop with Ctrl+C, and appropriate for a portfolio app.

**Cost:** it is not suitable for unattended background monitoring without external scheduling.

---

### 6.3 Dictionary snapshots instead of dataclasses

The app represents snapshots as dictionaries rather than custom dataclasses.

**Accepted because:** JSON serialization is direct and the snapshot structure is naturally record-like.

**Cost:** field names are not enforced by Python types, so defensive checks are needed in rendering and level calculation.

---

### 6.4 Approximate top-process ranking under high process counts

When there are many processes, top-process ranking may use a random sample for RSS scanning.

**Accepted because:** scanning every process can be expensive on busy systems.

**Cost:** top-process results are approximate when sampling is used.

---

### 6.5 Platform-aware but not platform-identical behavior

The app handles load-average availability and disk-partition flags differently by platform.

**Accepted because:** operating systems expose health metrics differently.

**Cost:** snapshot contents can differ between Linux, macOS, and Windows.

---

## 7. Consequences

### Positive Consequences

- The CLI remains simple while the internals are modular.
- Threshold logic is testable independently from psutil.
- Snapshot persistence creates a usable audit trail.
- The latest-snapshot file gives other SysForge tools a simple integration point.
- Rich rendering improves usability when installed, while plain output keeps the monitor usable without Rich.
- Watch mode gives immediate operational feedback without requiring a daemon.
- Tests can mock psutil, time, logging paths, and CLI invocation.

### Negative Consequences

- The app depends on psutil for meaningful operation.
- The JSON snapshot schema is implicit rather than formally versioned.
- Watch mode is synchronous and blocks the terminal.
- There is no alert notification channel beyond terminal output and persisted status.
- Log rotation is simple filename rotation, not a full logging subsystem.
- Random sampling for process ranking can produce slightly different results between runs.

---

## 8. Superseded By

None. This ADR is the current accepted design for App 25.

---

## 9. Constitution Alignment

This project fits the roadmap standard because it is scoped as a local CLI utility, uses an understandable modular design, keeps side effects explicit, has behavior-focused tests, and documents its operational limits. It also shows a clear progression from simple data-processing apps into system monitoring and shared-toolkit integration.

---

# Technical Design Document

## App 25 — System Health Monitor

**SysForge Group | Document 2 of 5**  
**Status: Accepted**  
**Date: 2026-05-08**

---

## 1. Purpose & Scope

The System Health Monitor collects and displays local machine health information from the command line. It is part of the SysForge toolkit and can be invoked either as a standalone app or through the unified SysForge CLI.

The app is responsible for:

- Loading health thresholds from SysForge configuration.
- Collecting CPU, memory, disk, process, uptime, and load-average metrics.
- Ranking top processes by memory and CPU signals.
- Assigning `INFO`, `WARNING`, or `CRITICAL` levels to CPU, memory, and disk usage.
- Computing an overall health level.
- Rendering the snapshot to the terminal.
- Writing structured health history as JSON Lines.
- Writing the latest snapshot as JSON.
- Rotating the health log file when it grows past a configured size.
- Running once by default or continuously in watch mode.

The app is not responsible for:

- Remote monitoring.
- Alert delivery through email, Slack, webhooks, or SMS.
- Background service installation.
- Long-term metrics aggregation.
- Graphing historical data.
- Full process inspection beyond a top-process summary.

---

## 2. System Context

```text
User
  |
  | sysforge-health
  | sysforge health
  v
Typer CLI callback
  |
  v
run_monitor()
  |
  +--> read_thresholds()
  |      |
  |      +--> load_shared_config() or load_config_file()
  |
  +--> snapshot_system()
  |      |
  |      +--> psutil.cpu_percent()
  |      +--> psutil.virtual_memory()
  |      +--> psutil.disk_partitions()
  |      +--> psutil.disk_usage()
  |      +--> psutil.boot_time()
  |      +--> psutil.pids()
  |      +--> top_processes()
  |
  +--> write_snapshot()
  |      |
  |      +--> determine_levels()
  |      +--> overall_level()
  |      +--> append_json_line(health_log.jsonl)
  |      +--> write_json_file(latest_snapshot.json)
  |
  +--> render_snapshot()
  |      |
  |      +--> Rich table output or plain text output
  |
  +--> print_transitions()
```

The monitor is a local host utility. It does not call a network API. Its main external dependency is `psutil`, and its main persistent side effects are files inside the SysForge home directory.

---

## 3. Component Breakdown

### 3.1 `sysforge.monitor.monitor`

Primary implementation module.

Responsibilities:

- Defines the Typer app.
- Loads optional dependencies.
- Reads thresholds.
- Collects health snapshots.
- Determines warning/critical levels.
- Rotates health logs.
- Writes snapshot history.
- Renders output.
- Runs one-shot and watch modes.

Key public functions:

- `read_thresholds(config_path=None)`
- `snapshot_system(thresholds=None)`
- `level_for_percent(percent, warning, critical)`
- `determine_levels(snapshot, thresholds)`
- `overall_level(levels)`
- `write_snapshot(snapshot, thresholds)`
- `render_snapshot(snapshot)`
- `run_monitor(watch, interval, config_path)`
- `main()`

---

### 3.2 `sysforge.monitor.__init__`

Package export layer.

Exports:

- `app`
- `main`
- `read_thresholds`
- `snapshot_system`

This lets other code import monitor functionality from `sysforge.monitor` without reaching directly into `monitor.py`.

---

### 3.3 `sysforge.common`

Shared utility dependency.

The monitor uses:

- `append_json_line()` for JSONL history.
- `format_duration()` for uptime display.
- `human_size()` for disk free-space display.
- `print_error()` for CLI error handling.
- `write_json_file()` for latest-snapshot persistence.

---

### 3.4 `sysforge.sysforge_paths`

Shared path management dependency.

The monitor uses:

- `ensure_home_layout()` to create SysForge state directories.
- `get_health_log_file()` for `health_log.jsonl`.
- `get_latest_health_file()` for `latest_snapshot.json`.

The default location is under `~/.sysforge/health/`, unless `SYSFORGE_HOME` overrides the SysForge home directory.

---

### 3.5 `sysforge.shared_config`

Shared configuration dependency.

The monitor uses `load_shared_config()` when no explicit config file is provided.

The default SysForge config contains health keys for CPU, memory, disk, log rotation, and process-scanning behavior.

---

### 3.6 `sysforge.config.config`

Explicit config-file dependency.

When the user passes `--config PATH`, the monitor reads that config with `load_config_file(path, apply_env=False)`. This allows a separate health config file to override thresholds without using the shared SysForge config.

---

### 3.7 `sysforge.logging_utils`

Central logging dependency.

The monitor obtains a logger named `sysforge.monitor`. SysForge logging writes to the central log file and respects `SYSFORGE_VERBOSE` and `SYSFORGE_QUIET` environment behavior configured by the root CLI.

---

### 3.8 `sysforge.__main__`

Unified CLI integration.

The root SysForge CLI imports the monitor Typer app and mounts it as the `health` subcommand. This gives the app two invocation paths:

```bash
sysforge-health
sysforge health
```

---

## 4. Module Dependency Graph

```text
sysforge.monitor.monitor
  ├── os, random, sys, time, datetime, pathlib, typing
  ├── typer
  ├── psutil                         (loaded dynamically)
  ├── rich.console / rich.table       (loaded dynamically)
  ├── sysforge.common
  │     ├── append_json_line
  │     ├── format_duration
  │     ├── human_size
  │     ├── print_error
  │     └── write_json_file
  ├── sysforge.config.config
  │     └── load_config_file
  ├── sysforge.logging_utils
  │     └── get_logger
  ├── sysforge.shared_config
  │     └── load_shared_config
  └── sysforge.sysforge_paths
        ├── ensure_home_layout
        ├── get_health_log_file
        └── get_latest_health_file
```

---

## 5. Core Algorithms & Logic

### 5.1 Threshold Loading

`read_thresholds()` loads threshold values from either:

1. An explicit config file passed with `--config`, or
2. The shared SysForge config.

It then normalizes values through `_coerce_threshold_int()`.

Default thresholds:

| Key | Default | Meaning |
|---|---:|---|
| `cpu_warning` | 80 | CPU percent that becomes warning |
| `cpu_critical` | 95 | CPU percent that becomes critical |
| `memory_warning` | 90 | Memory percent that becomes warning |
| `memory_critical` | 97 | Memory percent that becomes critical |
| `disk_warning` | 80 | Disk percent that becomes warning |
| `disk_critical` | 95 | Disk percent that becomes critical |
| `rotate_mb` | 10 | Health log rotation size in MB |
| `keep_files` | 5 | Number of rotated JSONL files to keep |
| `top_process_scan` | 80 | Number of candidate processes for CPU sampling |
| `max_rss_scan` | 4000 | Maximum process count to scan for RSS before sampling |

Special normalization rules:

- Boolean values are rejected and replaced with defaults.
- Float values are rounded to integers.
- Numeric strings are accepted.
- Invalid strings fall back to defaults.
- `keep_files` is clamped between 1 and 50.
- `top_process_scan` is clamped between 20 and 500.
- `max_rss_scan` is clamped between 200 and 50,000.

---

### 5.2 Snapshot Collection

`snapshot_system()` collects a structured snapshot:

```python
{
    "timestamp": "...",
    "cpu_percent": ...,
    "memory": {
        "percent": ...,
        "available": ...,
    },
    "disks": [...],
    "process_count": ...,
    "boot_time": "...",
    "uptime_seconds": ...,
    "load_average": ...,
    "platform": {...},
    "top_processes": [...],
}
```

Main steps:

1. Load thresholds if not provided.
2. Load `psutil` dynamically.
3. Call `psutil.pids()` once and reuse the result.
4. Collect disk partition usage.
5. Read load average if `os.getloadavg()` is available.
6. Collect virtual memory usage.
7. Calculate uptime from boot time.
8. Rank top processes using `top_processes()`.
9. Return a JSON-serializable dictionary.

---

### 5.3 Disk Collection

The monitor calls `psutil.disk_partitions(all=disk_all)`.

- On Windows, `disk_all` is `False`.
- On non-Windows platforms, `disk_all` is `True`.

Each successful disk entry stores:

- `device`
- `mountpoint`
- `percent`
- `free`
- `total`

Partitions that raise `PermissionError` during `disk_usage()` are skipped.

---

### 5.4 Load Average Normalization

`normalize_load_average()` accepts only three-value list or tuple inputs and converts them to floats.

Valid example:

```python
(1.5, 2.0, 3.25) -> [1.5, 2.0, 3.25]
```

Invalid inputs return `None`.

This avoids assuming that every platform supports Unix-style load averages.

---

### 5.5 Top Process Ranking

`top_processes()` ranks processes primarily by memory percentage and secondarily by CPU percentage.

Process ranking steps:

1. Get PID list from caller or from `psutil.pids()`.
2. If process count exceeds `max_rss_scan`, randomly sample `max_rss_scan` PIDs.
3. For each PID, instantiate `psutil.Process(pid)`.
4. Read RSS memory from `memory_info()`.
5. Sort processes by RSS descending.
6. Keep a candidate set of size `cpu_candidate_cap`.
7. Prime CPU percent with `cpu_percent(interval=None)`.
8. Sleep briefly.
9. Read CPU percent and memory percent.
10. Sort by `(memory_percent, cpu_percent)` descending.
11. Return the top `limit` process dictionaries.

The returned process record contains:

```python
{
    "pid": 123,
    "name": "python",
    "memory_percent": 1.25,
    "cpu_percent": 4.5,
}
```

The function catches `NoSuchProcess` and `AccessDenied` so transient process exits or permission problems do not crash the monitor.

---

### 5.6 Level Determination

`level_for_percent()` maps a numeric percent into a level:

```text
percent >= critical threshold  -> CRITICAL
percent >= warning threshold   -> WARNING
otherwise                      -> INFO
```

`determine_levels()` applies this to:

- CPU usage.
- Memory usage.
- Disk usage.

For disks, the worst disk level across all disk entries wins.

`overall_level()` then chooses the highest severity across CPU, memory, and disk:

```text
Any CRITICAL -> CRITICAL
Else any WARNING -> WARNING
Else INFO
```

---

### 5.7 Snapshot Persistence

`write_snapshot()` performs the persistence workflow:

1. Normalize rotation settings.
2. Rotate the health log if needed.
3. Determine levels.
4. Add `levels` to the snapshot dictionary.
5. Add `overall_level` to the snapshot dictionary.
6. Append the full snapshot to `health_log.jsonl`.
7. Write the full snapshot to `latest_snapshot.json` atomically.

This design creates both historical and current-state views.

---

### 5.8 Log Rotation

`rotate_log_file()` checks the health JSONL file size.

If the file is smaller than `rotate_mb`, no rotation happens.

If the file is at or above the threshold:

1. Older rotated files are shifted upward.
2. The oldest file beyond the retention limit is deleted.
3. The active `health_log.jsonl` becomes `health_log.jsonl.1`.
4. The next snapshot creates a new active log file.

---

### 5.9 Rendering

`render_snapshot()` supports two output paths.

If Rich is installed:

- Render a `System Health` table.
- Render a `Top Processes` table.

If Rich is unavailable:

- Print plain text metrics with `typer.echo()`.
- Include CPU, memory, process count, uptime, status, and disk usage.

This keeps the core utility usable even when presentation dependencies are missing.

---

### 5.10 Watch Mode

`run_monitor()` coordinates repeated monitoring.

One-shot mode:

```text
snapshot -> write -> render -> return
```

Watch mode:

```text
while True:
    snapshot
    write
    render
    print level transitions
    sleep interval
```

Ctrl+C behavior:

- Appends a shutdown event to the health log.
- Prints `Stopped watch mode.`
- Exits cleanly.

---

## 6. Data Structures

### 6.1 Threshold Dictionary

```python
{
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
```

### 6.2 Snapshot Dictionary

```python
{
    "timestamp": str,
    "cpu_percent": float,
    "memory": dict,
    "disks": list[dict],
    "process_count": int,
    "boot_time": str,
    "uptime_seconds": int,
    "load_average": list[float] | None,
    "platform": dict,
    "top_processes": list[dict],
    "levels": dict[str, str],
    "overall_level": str,
}
```

### 6.3 Disk Dictionary

```python
{
    "device": str,
    "mountpoint": str,
    "percent": float,
    "free": int,
    "total": int,
}
```

### 6.4 Process Dictionary

```python
{
    "pid": int,
    "name": str,
    "memory_percent": float,
    "cpu_percent": float,
}
```

### 6.5 Levels Dictionary

```python
{
    "cpu": "INFO" | "WARNING" | "CRITICAL",
    "memory": "INFO" | "WARNING" | "CRITICAL",
    "disk": "INFO" | "WARNING" | "CRITICAL",
}
```

---

## 7. State Management

The monitor maintains no long-lived in-memory state outside a single run. State is persisted to the filesystem:

| State | Location | Purpose |
|---|---|---|
| Shared config | `~/.sysforge/sysforge.json` or `SYSFORGE_CONFIG` | Default health thresholds |
| Health history | `~/.sysforge/health/health_log.jsonl` | Append-only snapshot history |
| Latest snapshot | `~/.sysforge/health/latest_snapshot.json` | Most recent monitor result |
| Central log | `~/.sysforge/logs/sysforge.log` | SysForge logger output |

`SYSFORGE_HOME` can redirect all of this state to another directory.

---

## 8. Error Handling Strategy

### 8.1 Missing psutil

`load_psutil()` raises a Typer exit through `print_error()` with exit code 2 if psutil is missing.

### 8.2 Missing Rich

`load_rich_table_tools()` returns `None` if Rich is missing. Rendering then falls back to plain text.

### 8.3 Bad interval

The CLI rejects intervals less than 1 second.

### 8.4 Disk permission errors

Partitions that raise `PermissionError` are skipped instead of failing the entire snapshot.

### 8.5 Process race conditions

`top_processes()` catches process disappearance and access-denied errors.

### 8.6 Keyboard interrupt

Watch mode catches Ctrl+C, writes a shutdown event to the health log, and prints a stop message.

### 8.7 Invalid config values

Threshold values are coerced where possible and defaulted when invalid.

---

## 9. External Dependencies

| Dependency | Runtime or Dev | Purpose |
|---|---|---|
| `typer>=0.12` | Runtime | CLI command framework |
| `psutil>=5.9` | Runtime | CPU, memory, disk, process, and boot-time metrics |
| `rich>=13.7` | Runtime | Optional table rendering |
| `pytest>=8.0` | Dev | Unit tests |
| `pytest-cov>=5.0` | Dev | Coverage enforcement |
| `ruff>=0.8` | Dev | Linting and formatting |
| `mypy>=1.13` | Dev | Type checking |

The monitor cannot collect real system metrics without psutil. Rich is treated as a presentation enhancement rather than a hard rendering requirement.

---

## 10. Concurrency Model

The monitor is synchronous.

- One-shot mode runs a single sequence and exits.
- Watch mode uses a blocking `while True` loop and `time.sleep(interval)`.
- There are no threads, subprocesses, async tasks, queues, sockets, or background workers.

This is intentional because the app is a local CLI utility, not a service.

---

## 11. Known Limitations

- Watch mode is foreground-only.
- No notifications are sent when health becomes warning or critical.
- JSONL history has no formal schema version.
- Process ranking can be approximate when random sampling is used.
- Metrics depend on psutil behavior and OS permissions.
- Load average may be unavailable on some platforms.
- Disk partition reporting differs between Windows and non-Windows systems.
- Log rotation is simple local file rotation.
- The monitor does not calculate trends, moving averages, or historical summaries.

---

## 12. Design Patterns Used

| Pattern | Use in App |
|---|---|
| Facade | `run_monitor()` coordinates the monitoring workflow |
| Strategy-like rendering | Rich output vs plain output based on dependency availability |
| Snapshot record | System state is captured as a structured dictionary |
| Threshold evaluation | Raw metrics are separated from severity classification |
| Adapter | psutil data is converted into JSON-serializable dictionaries |
| Dependency boundary | psutil and Rich are loaded through helper functions |
| Append-only log | Health history is written as JSON Lines |
| Latest-state cache | Most recent snapshot is written separately for quick access |

---

# Interface Design Specification

## App 25 — System Health Monitor

**SysForge Group | Document 3 of 5**  
**Status: Accepted**  
**Date: 2026-05-08**

---

## 1. Invocation Syntax

### Standalone command

```bash
sysforge-health [OPTIONS]
```

### Unified SysForge command

```bash
sysforge health [OPTIONS]
```

### Python module / function path

The package script entry point maps to:

```text
sysforge.monitor.monitor:main
```

---

## 2. Command Reference

The monitor uses a Typer callback with no required subcommands. Running the command directly performs one health check.

```bash
sysforge-health
```

---

## 3. Argument Reference Table

| Name | Type | Required | Default | Valid Values | Description |
|---|---|---:|---|---|---|
| `--watch` | boolean flag | No | `False` | present / absent | Keep collecting snapshots until Ctrl+C. |
| `--interval` | integer | No | `30` | `>= 1` | Seconds between readings in watch mode. |
| `--config` | path | No | `None` | Path to JSON object config | Optional config file for health thresholds. |
| `--help` | boolean flag | No | n/a | present / absent | Show help text and exit. |

---

## 4. Input Contract

### 4.1 Default Invocation

When called with no options, the app:

1. Ensures SysForge home layout exists.
2. Loads thresholds from shared config.
3. Collects one health snapshot.
4. Persists history and latest snapshot.
5. Renders the snapshot.
6. Exits.

### 4.2 Watch Mode

When `--watch` is supplied:

- The monitor repeats until Ctrl+C.
- `--interval` controls the sleep time between snapshots.
- Each iteration writes to history and latest snapshot.
- Level transitions are printed after the first iteration when a metric changes state.

### 4.3 Config File

`--config PATH` must point to a JSON object. The monitor reads the `health` object from that file.

Example:

```json
{
  "health": {
    "cpu_warning": 75,
    "cpu_critical": 90,
    "memory_warning": 85,
    "memory_critical": 95,
    "disk_warning": 80,
    "disk_critical": 95,
    "rotate_mb": 10,
    "keep_files": 5,
    "top_process_scan": 100,
    "max_rss_scan": 3000
  }
}
```

Invalid threshold values fall back to defaults rather than crashing the monitor.

---

## 5. Output Contract

### 5.1 Terminal Output with Rich Available

The app prints a Rich table titled with the overall status:

```text
System Health (INFO)
```

The table includes:

- CPU percent.
- Memory percent.
- Process count.
- Uptime.
- Load average when available.
- Disk usage rows.

It also prints a `Top Processes` table with:

- PID.
- Name.
- CPU percent.
- Memory percent.

### 5.2 Terminal Output without Rich

The app prints plain text similar to:

```text
CPU: 7.5%
Memory: 8.0%
Processes: 200
Uptime: 1h 00m
Status: INFO
/data: 12% used (4.0 KB free)
```

### 5.3 JSONL History Output

The app appends one JSON object per snapshot to:

```text
~/.sysforge/health/health_log.jsonl
```

Each line is an independent JSON record.

### 5.4 Latest Snapshot Output

The app writes the current snapshot to:

```text
~/.sysforge/health/latest_snapshot.json
```

This file is overwritten on each run.

### 5.5 Watch Shutdown Output

On Ctrl+C in watch mode, the app prints:

```text
Stopped watch mode.
```

It also appends a shutdown event to the health JSONL log.

---

## 6. Exit Code Reference

| Scenario | Exit Code | Notes |
|---|---:|---|
| Successful one-shot run | 0 | Normal Typer completion |
| Successful watch-mode stop with Ctrl+C | 0 | Handled interrupt |
| Invalid `--interval` | non-zero | Typer exit through `print_error()` |
| Missing psutil | 2 | Dependency error |
| Invalid config file | non-zero | Raised through config loading path |
| Typer argument parsing error | non-zero | Standard Typer behavior |

---

## 7. Error Output Behavior

- `print_error()` writes colored error text to stderr through Typer.
- Missing psutil produces a dependency-install message.
- Bad interval produces a direct validation message.
- Permission errors on individual disks are skipped silently.
- Process access errors are skipped silently.

---

## 8. Environment Variables

| Variable | Used By | Effect |
|---|---|---|
| `SYSFORGE_HOME` | SysForge paths | Overrides default `~/.sysforge` state directory. |
| `SYSFORGE_CONFIG` | Shared config loader | Overrides shared SysForge config path. |
| `SYSFORGE_VERBOSE` | Logging utility | Enables more console logging. |
| `SYSFORGE_QUIET` | Logging utility | Reduces console logging. |

---

## 9. Configuration Files

### 9.1 Shared SysForge Config

Default path:

```text
~/.sysforge/sysforge.json
```

The health section contains default monitor thresholds.

### 9.2 Explicit Health Config

Passed through:

```bash
sysforge-health --config health.json
```

When present, this path is read instead of the shared SysForge config for thresholds.

---

## 10. Side Effects

| Side Effect | Path | Condition |
|---|---|---|
| Create SysForge home layout | `~/.sysforge/` or `SYSFORGE_HOME` | Every run |
| Append health history | `health/health_log.jsonl` | Every snapshot |
| Write latest snapshot | `health/latest_snapshot.json` | Every snapshot |
| Rotate health log | `health/health_log.jsonl.N` | When log exceeds configured size |
| Write central logs | `logs/sysforge.log` | Logger initialization and monitor operations |
| Append shutdown event | `health/health_log.jsonl` | Ctrl+C in watch mode |

---

## 11. Usage Examples

### 11.1 Basic one-shot health check

```bash
sysforge-health
```

Expected behavior:

- Collects one snapshot.
- Prints system health.
- Writes `health_log.jsonl` and `latest_snapshot.json`.

---

### 11.2 Unified CLI invocation

```bash
sysforge health
```

Expected behavior:

- Runs the same monitor app through the unified SysForge CLI.

---

### 11.3 Watch mode every five seconds

```bash
sysforge-health --watch --interval 5
```

Expected behavior:

- Repeats until Ctrl+C.
- Prints transitions such as `CPU changed from INFO to WARNING` when levels change.

---

### 11.4 Custom threshold config

```bash
sysforge-health --config ./health_config.json
```

Expected behavior:

- Loads thresholds from `health_config.json`.
- Collects and persists one snapshot.

---

### 11.5 Intentional failure: bad interval

```bash
sysforge-health --interval 0
```

Expected behavior:

- Command exits non-zero.
- Error explains that interval must be at least 1 second.

---

### 11.6 Isolated development state

```bash
SYSFORGE_HOME=.sysforge-dev sysforge-health
```

Expected behavior:

- Writes monitor state under `.sysforge-dev/` instead of the user home directory.

---

# Runbook

## App 25 — System Health Monitor

**SysForge Group | Document 4 of 5**  
**Status: Accepted**  
**Date: 2026-05-08**

---

## 1. Prerequisites

- Python 3.11 or newer.
- SysForge installed from the project root.
- Runtime dependencies installed:
  - Typer.
  - psutil.
  - Rich.
- Write permission to the SysForge home directory.

Recommended development install:

```bash
python -m pip install -e ".[dev]"
```

Runtime-only style install:

```bash
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps
```

---

## 2. Installation Procedure

From the SysForge repository root:

```bash
python -m pip install -e .
```

Verify the console script exists:

```bash
sysforge-health --help
```

Verify unified CLI access:

```bash
sysforge health --help
```

---

## 3. Configuration Steps

### 3.1 Default configuration

On first run, SysForge creates a shared config under the SysForge home directory when package defaults are available.

Default location:

```text
~/.sysforge/sysforge.json
```

Default health thresholds include CPU, memory, disk, log rotation, and process-scanning settings.

### 3.2 Isolated testing configuration

For local experiments, redirect SysForge home:

```bash
export SYSFORGE_HOME=.sysforge-dev
```

On Windows Command Prompt:

```bat
set SYSFORGE_HOME=.sysforge-dev
```

### 3.3 Custom monitor config

Create a file such as `health_config.json`:

```json
{
  "health": {
    "cpu_warning": 70,
    "cpu_critical": 90,
    "memory_warning": 85,
    "memory_critical": 95,
    "disk_warning": 80,
    "disk_critical": 95,
    "rotate_mb": 10,
    "keep_files": 5
  }
}
```

Run:

```bash
sysforge-health --config health_config.json
```

---

## 4. Standard Operating Procedures

### 4.1 Run a one-shot health check

```bash
sysforge-health
```

Use this when you want a single current snapshot.

### 4.2 Run in watch mode

```bash
sysforge-health --watch --interval 30
```

Use this when you want repeated foreground updates.

Stop with Ctrl+C.

### 4.3 Run through unified SysForge CLI

```bash
sysforge health
```

Use this when working from the main SysForge command.

### 4.4 Inspect latest snapshot

```bash
cat ~/.sysforge/health/latest_snapshot.json
```

### 4.5 Inspect health history

```bash
tail ~/.sysforge/health/health_log.jsonl
```

### 4.6 Use isolated output directory

```bash
SYSFORGE_HOME=.sysforge-dev sysforge-health
```

Then inspect:

```text
.sysforge-dev/health/latest_snapshot.json
.sysforge-dev/health/health_log.jsonl
```

---

## 5. Health Checks

### 5.1 CLI help check

```bash
sysforge-health --help
```

Expected:

- Command shows options including `--watch`, `--interval`, and `--config`.

### 5.2 One-shot execution check

```bash
sysforge-health
```

Expected:

- CPU, memory, process count, uptime, and disk information are printed.
- Files are written under SysForge health state.

### 5.3 Latest snapshot check

```bash
test -f ~/.sysforge/health/latest_snapshot.json
```

Expected:

- File exists after a successful run.

### 5.4 History check

```bash
test -f ~/.sysforge/health/health_log.jsonl
```

Expected:

- File exists and contains at least one JSON line.

### 5.5 Watch-mode check

```bash
sysforge-health --watch --interval 1
```

Expected:

- Repeated snapshots are produced.
- Ctrl+C stops the loop and writes a shutdown event.

---

## 6. Expected Output Samples

### 6.1 Plain fallback output

```text
CPU: 7.5%
Memory: 8.0%
Processes: 200
Uptime: 1h 00m
Status: INFO
/data: 12% used (4.0 KB free)
```

### 6.2 Level transition output

```text
CPU changed from INFO to WARNING
MEMORY changed from INFO to CRITICAL
```

### 6.3 Latest snapshot fields

```json
{
  "timestamp": "2026-05-08T12:00:00.000000",
  "cpu_percent": 12.5,
  "memory": {
    "percent": 33.0,
    "available": 500
  },
  "disks": [],
  "process_count": 3,
  "levels": {
    "cpu": "INFO",
    "memory": "INFO",
    "disk": "INFO"
  },
  "overall_level": "INFO"
}
```

---

## 7. Known Failure Modes

| Failure Mode | Symptom | Likely Cause | Recovery |
|---|---|---|---|
| Missing psutil | Error says psutil is required | Dependencies not installed | Run `python -m pip install -e .` |
| Bad interval | Non-zero exit | `--interval` less than 1 | Use `--interval 1` or higher |
| Config file missing | CLI error | Bad `--config` path | Fix path or remove option |
| Config is not JSON object | CLI error | Config contains array/scalar | Replace with JSON object |
| Permission denied on SysForge home | Write failure | No permission to state directory | Set `SYSFORGE_HOME` to writable directory |
| Some disks missing | Disk not shown | Permission or OS behavior | Check OS permissions; expected on some systems |
| Top process list seems approximate | Process ranking varies | Sampling under high process count | Increase `max_rss_scan` if needed |
| Rich table not shown | Plain text output | Rich unavailable | Install dependencies or accept fallback |

---

## 8. Troubleshooting Decision Tree

```text
Start
 |
 |-- Does `sysforge-health --help` work?
 |     |-- No -> reinstall SysForge / check entry points
 |     |-- Yes
 |
 |-- Does `sysforge-health` fail immediately?
 |     |-- Missing psutil -> install project dependencies
 |     |-- Bad config -> validate JSON file
 |     |-- Permission error -> set SYSFORGE_HOME to writable path
 |     |-- Other -> run with unified CLI or inspect traceback
 |
 |-- Is no latest snapshot written?
 |     |-- Check ~/.sysforge/health/
 |     |-- Check SYSFORGE_HOME override
 |     |-- Check write permissions
 |
 |-- Is status unexpectedly WARNING/CRITICAL?
 |     |-- Inspect thresholds in sysforge.json
 |     |-- Check CPU/memory/disk percentages
 |     |-- Run with custom config to verify threshold behavior
 |
 |-- Does watch mode not repeat?
 |     |-- Confirm --watch was supplied
 |     |-- Confirm interval is >= 1
 |     |-- Check for Ctrl+C or terminal closure
```

---

## 9. Dependency Failure Handling

### 9.1 psutil

psutil is required. If it is missing, the app exits with an installation message.

Recovery:

```bash
python -m pip install -e .
```

### 9.2 Rich

Rich is optional for rendering. If missing, the app falls back to plain output.

Recovery if Rich output is desired:

```bash
python -m pip install rich
```

### 9.3 Typer

Typer is required for the CLI entry point.

Recovery:

```bash
python -m pip install -e .
```

---

## 10. Recovery Procedures

### 10.1 Reset monitor state

```bash
rm ~/.sysforge/health/latest_snapshot.json
rm ~/.sysforge/health/health_log.jsonl
```

Then rerun:

```bash
sysforge-health
```

### 10.2 Use a clean temporary state directory

```bash
SYSFORGE_HOME=$(mktemp -d) sysforge-health
```

### 10.3 Recover from oversized logs

If log rotation is not enough:

```bash
mv ~/.sysforge/health/health_log.jsonl ~/.sysforge/health/health_log.manual-backup.jsonl
sysforge-health
```

### 10.4 Recover from bad threshold config

Move the custom config out of the way or use the shared defaults:

```bash
sysforge-health
```

Instead of:

```bash
sysforge-health --config bad_health.json
```

---

## 11. Logging Reference

### 11.1 Central SysForge log

```text
~/.sysforge/logs/sysforge.log
```

The monitor logger name is:

```text
sysforge.monitor
```

### 11.2 Health history log

```text
~/.sysforge/health/health_log.jsonl
```

Each line is one JSON object.

### 11.3 Latest snapshot

```text
~/.sysforge/health/latest_snapshot.json
```

This is the current state cache.

### 11.4 Watch shutdown event

When Ctrl+C interrupts watch mode, a JSON event is appended to the health log:

```json
{
  "timestamp": "...",
  "event": "shutdown",
  "message": "Watch mode interrupted with Ctrl+C"
}
```

---

## 12. Maintenance Notes

- Keep snapshot keys stable if other SysForge tools begin reading `latest_snapshot.json`.
- Add a schema version before changing JSON output format.
- Consider deterministic process ranking for testability if process sampling behavior grows more important.
- Keep threshold defaults aligned with `sysforge/data/sysforge.json`.
- Avoid hiding psutil errors too aggressively; permission errors are normal, but dependency errors should be explicit.
- Consider adding a `--json` terminal output mode if this app becomes part of scripts.
- Consider reporting historical trends in a future SysForge dashboard.

---

# Lessons Learned

## App 25 — System Health Monitor

**SysForge Group | Document 5 of 5**  
**Status: Accepted**  
**Date: 2026-05-08**

---

## 1. Project Summary

The System Health Monitor is a local observability utility for SysForge. It collects CPU, memory, disk, uptime, process, and load-average data, renders that data to the terminal, and persists it as structured JSON.

This project is a step up from simpler CLI apps because the data comes from the host operating system rather than from static files or direct user input. That introduces real-world concerns: permissions, platform differences, optional dependencies, noisy metrics, processes disappearing while they are being inspected, and long-running watch behavior.

The project is still intentionally scoped as a learning app. It is not a full monitoring daemon or alerting platform. Its value is in showing how a CLI can collect system data, classify it, persist it, and present it cleanly.

---

## 2. Original Goals vs. Actual Outcome

### Original Goals

- Build a CLI health monitor.
- Report CPU, memory, disk, uptime, and process information.
- Support threshold-based warning levels.
- Write logs for later review.
- Integrate with SysForge shared config and filesystem layout.

### Actual Outcome

The final app met those goals and added several useful engineering details:

- One-shot and watch modes.
- Configurable thresholds.
- JSONL history.
- Latest-snapshot JSON file.
- Log rotation.
- Rich-table rendering with plain-text fallback.
- Top-process ranking.
- Platform metadata in the snapshot.
- Tests for threshold coercion, level calculation, CLI options, snapshot shape, rotation, rendering fallback, and package exports.

The biggest improvement over a basic script is that the monitor produces structured records instead of only printing text.

---

## 3. Technical Decisions That Paid Off

### 3.1 Separating snapshot collection from rendering

`snapshot_system()` does not print. It returns a dictionary.

That made it possible to:

- Test snapshot shape.
- Persist the same data that is displayed.
- Add levels after collection.
- Reuse snapshots in future reports.

This was the most important design decision.

---

### 3.2 Using thresholds as config-driven data

Thresholds are not scattered across rendering logic. They are loaded through `read_thresholds()` and normalized before use.

That made warnings and critical levels easier to reason about and easier to test.

---

### 3.3 Treating Rich as optional rendering

The app can produce plain text if Rich is unavailable.

This is a useful CLI pattern: presentation should improve the experience, but it should not be the only way to get usable output.

---

### 3.4 Handling process races defensively

Processes can disappear or become inaccessible between listing PIDs and reading process details. Catching `NoSuchProcess` and `AccessDenied` keeps the monitor from failing during normal OS behavior.

---

### 3.5 Writing both history and latest state

JSONL history and latest JSON solve different problems:

- JSONL gives an append-only timeline.
- Latest JSON gives quick current status.

This is a practical pattern for small local monitoring tools.

---

## 4. Technical Decisions That Created Debt

### 4.1 Dictionary snapshots instead of typed models

Dictionaries made JSON output easy, but they also mean field names are implicit.

This created the need for defensive checks like:

- Is `memory` actually a dictionary?
- Is `disks` actually a list?
- Is each disk entry a dictionary?

A future version could introduce dataclasses or typed dictionaries.

---

### 4.2 No explicit snapshot schema version

The JSON output has a structure, but no `schema_version` field.

That is acceptable for a portfolio app, but it becomes a problem if other SysForge tools rely on these files long term.

---

### 4.3 Watch mode is synchronous

The synchronous loop is simple and readable, but it blocks the terminal and cannot easily coordinate multiple output channels.

For this app, that is acceptable. For a production monitor, it would be limiting.

---

### 4.4 Top-process sampling is approximate

Sampling prevents expensive scans on hosts with many processes, but it means the reported top processes can be approximate.

The implementation logs that this is approximate, but the user-facing CLI does not deeply explain it.

---

## 5. What Was Harder Than Expected

### 5.1 System metrics are not as stable as normal data

Unlike reading a JSON file, OS processes can change while the program is running. A process can disappear between `pids()` and `Process(pid)`. Permissions can block metrics. Disk partitions can be visible but not readable.

The app needed defensive programming to avoid crashing on normal system behavior.

---

### 5.2 Cross-platform behavior matters

Load average is not universally available. Disk partition behavior differs between Windows and non-Windows platforms. This forced the app to describe platform behavior explicitly in the snapshot.

---

### 5.3 Top-process ranking is more subtle than expected

CPU percent readings often require a priming call and a small delay. Memory ranking is easier, but CPU and memory together require a two-phase collection approach.

---

### 5.4 Persistence has operational consequences

Writing a JSONL file every time is simple, but it creates growth over time. Adding rotation was a useful reminder that even small CLI tools need basic maintenance behavior when they write logs.

---

## 6. What Was Easier Than Expected

### 6.1 Threshold classification

Mapping percentages to `INFO`, `WARNING`, and `CRITICAL` was straightforward once it was separated from collection and rendering.

### 6.2 Typer callback design

A callback with `invoke_without_command=True` fit this app well because the command itself is the operation. No subcommands were necessary.

### 6.3 Testing pure helper functions

Functions like `_coerce_threshold_int()`, `level_for_percent()`, `overall_level()`, `normalize_load_average()`, and `determine_levels()` are easy to test because they do not touch real system state.

---

## 7. Python-Specific Learnings

### 7.1 Dynamic imports are useful for CLI dependency messages

Loading psutil through `load_psutil()` makes it possible to give a clear CLI error instead of a raw import traceback.

### 7.2 Typer exits are different from normal return values

`print_error()` raises a Typer exit. This is useful for CLI UX, but it means error paths need to be tested through the CLI runner or expected as exits.

### 7.3 JSONL is a good local logging format

Appending one JSON object per line is simple, durable, and easy to inspect with command-line tools.

### 7.4 Type checks matter with dictionaries

When using dictionaries for externalized records, runtime type checks are important. The render function should not assume every loaded or constructed snapshot is perfectly shaped.

### 7.5 Monkeypatching is powerful for system tests

Tests can replace psutil, time, log paths, and `run_monitor()` so the monitor can be verified without relying on the actual host environment.

---

## 8. Architecture Insights

### 8.1 Monitoring is a pipeline

The app follows a pipeline:

```text
config -> collect -> classify -> persist -> render -> repeat optionally
```

This makes the architecture easier to understand than a single large CLI function.

### 8.2 Local state should be centralized

Using SysForge path helpers keeps monitor files in the same home layout as the rest of the toolkit. That is better than having each app invent its own state directory.

### 8.3 Severity should be separate from metrics

Raw CPU percent and severity level are different concepts. Keeping them separate makes the output more flexible.

### 8.4 Optional formatting should not own the domain model

Rich tables are useful, but the snapshot dictionary is the real product of the monitor. This keeps the app from being locked into one presentation layer.

---

## 9. Testing Gaps

The existing tests cover many important behaviors, including:

- Threshold coercion.
- Level calculation.
- Overall status calculation.
- Partial snapshots.
- Disk worst-level selection.
- Transition printing.
- Threshold loading.
- Log rotation.
- Load-average normalization.
- Process sampling.
- CLI option forwarding.
- Bad interval rejection.
- Snapshot shape with mocked psutil.
- Snapshot persistence behavior.
- Plain rendering fallback.
- Package re-exports.

Remaining gaps:

- End-to-end execution against real psutil is not documented as having been run here.
- Rich table rendering is less deeply asserted than plain fallback rendering.
- JSONL rotation behavior could be tested across multiple rotated files.
- Watch mode Ctrl+C behavior could be tested more directly.
- No test asserts the exact latest-snapshot file contents on disk after a real run.
- No schema validation exists for snapshot JSON.

---

## 10. Reusable Patterns Identified

- **Config coercion helpers:** normalize values before using them in logic.
- **Snapshot dictionaries:** collect operational state before rendering or persisting.
- **Severity mapping:** keep threshold classification separate from collection.
- **Optional dependency fallback:** use richer output when available, but keep plain output working.
- **JSONL history:** append structured records for local audit trails.
- **Latest-state cache:** write a single JSON file for the current state.
- **Foreground watch loop:** simple recurring CLI behavior without daemon complexity.
- **Path helpers:** centralize filesystem layout across a toolkit.

---

## 11. If I Built This Again

If I rebuilt this app, I would keep the same general structure but improve several areas:

1. Add a `schema_version` field to each snapshot.
2. Introduce `TypedDict` or dataclasses for snapshot records.
3. Add a `--json` option to print the snapshot directly to stdout.
4. Add a `--no-write` option for dry-run display without persistence.
5. Add a `--once` option only if future subcommands make default behavior less obvious.
6. Add summary commands for recent history.
7. Add alert hooks for warning and critical transitions.
8. Add better explanations when top-process sampling is approximate.
9. Add tests for real temporary filesystem writes through the full CLI.
10. Add documentation for platform-specific metric differences.

---

## 12. Open Questions

- Should the monitor eventually send notifications when levels change?
- Should snapshot JSON have a formal schema file?
- Should watch mode support a maximum iteration count for scripting and tests?
- Should process ranking be based on memory, CPU, or a combined score?
- Should log rotation be shared across SysForge apps instead of implemented locally here?
- Should latest snapshot be consumed by the SysForge report command?
- Should disk thresholds support per-mount overrides?
- Should the app expose historical summaries like average CPU, peak memory, or disk trend?

---

## 13. Final Reflection

The System Health Monitor is a strong portfolio app because it moves beyond static input/output and interacts with the host operating system. It demonstrates practical engineering concerns: dependency boundaries, system permissions, platform variability, structured logs, thresholds, persistence, and CLI feedback.

The project is not production monitoring software, and it does not pretend to be. Its strength is that it takes a realistic systems problem and solves it at the right scale for a learner-built CLI toolkit.
