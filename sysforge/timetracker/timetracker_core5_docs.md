# Architecture Decision Record

## App 27 — Time Tracker

**SysForge Group | Document 1 of 5**  
**Status: Accepted**

## Title

Use a local JSON-backed Typer CLI for task timing, manual time entry, reporting, and CSV export.

## Date

2026-05-09

## Context

The Time Tracker is one of the SysForge utility applications. SysForge is packaged as a Python 3.11+ developer operations toolkit with standalone console scripts and one unified CLI. The root README presents `sysforge-time` as the standalone command for starting, stopping, viewing, reporting, and exporting work sessions, and the package metadata wires `sysforge-time` to `sysforge.timetracker.timetracker:main` while also mounting the same Typer app under the unified `sysforge time` command.

The application needed to remain small enough for the SysForge roadmap while demonstrating stateful CLI design. Unlike purely transformational tools, a time tracker must preserve state across invocations. It has to remember whether a timer is currently active, store completed sessions, support manual entry correction, summarize work by project and tag, and export records for spreadsheet use. The implementation chooses a single JSON file under the shared SysForge home directory rather than a database or external service.

The central implementation lives in `sysforge/timetracker/timetracker.py`. It defines functions for active timezone lookup, JSON loading/saving, payload normalization, entry construction, date filtering, reporting, and Typer commands for `start`, `stop`, `status`, `log`, `report`, `export`, `add`, and `delete`. The shared path layer resolves the timesheet file to `~/.sysforge/time/timesheet.json` unless `SYSFORGE_HOME` redirects the state directory. The default SysForge config includes `user.timezone` and `time.project_rates`, which the tracker uses for timezone-aware timestamps and billable totals.

## Decision Drivers

- Preserve completed work sessions between command invocations.
- Keep state readable and inspectable for a student portfolio project.
- Avoid database setup and external accounts.
- Use the same Typer-based CLI style as the rest of SysForge.
- Support both automatic timers and manual backfilled entries.
- Normalize corrupted or partially invalid stored data rather than crashing where possible.
- Integrate with shared SysForge configuration for timezone and project rates.
- Provide a simple CSV export path for downstream spreadsheet/reporting use.
- Keep behavior easy to verify with pytest and temporary `SYSFORGE_HOME` isolation.

## Options Considered

### Option 1 — Stateless CLI that only prints elapsed time

**Summary:** Accept `--start` and `--end` values, calculate duration, and print results without persistent state.

**Pros**

- Very simple implementation.
- No file persistence or data migration concerns.
- Low risk of corrupting stored state.

**Cons**

- Does not support a real active timer.
- Cannot produce historical reports.
- Cannot export prior sessions.
- Does not meet the app’s state-management learning goal.

**Decision:** Rejected. It would be too shallow for the SysForge roadmap and would not justify a dedicated Time Tracker application.

### Option 2 — SQLite-backed time tracking

**Summary:** Store timers and entries in a local SQLite database.

**Pros**

- Better for long-term querying, indexing, and schema constraints.
- Stronger transactional semantics than a plain JSON file.
- Natural fit for report queries once the dataset grows.

**Cons**

- Adds schema/migration design that is not necessary at this size.
- Makes manual inspection harder for a beginner portfolio project.
- Requires a larger testing surface.
- More complex recovery story for corrupted state.

**Decision:** Rejected for this version. SQLite would be a strong future upgrade, but JSON fits the educational scope better.

### Option 3 — One JSON file containing active timer and completed entries

**Summary:** Store `active_timer`, `entries`, and `updated_at` in one JSON document.

**Pros**

- Easy to inspect, edit, back up, and test.
- Matches the local-first nature of SysForge.
- Supports atomic writes through shared `write_json_file` helper.
- Small enough for a CLI portfolio app but still demonstrates persistence.
- Works well with temporary test directories through `SYSFORGE_HOME`.

**Cons**

- No built-in locking for concurrent CLI invocations.
- Reports require loading the whole file.
- Corrupted JSON can block normal use until repaired.
- Schema evolution must be handled manually.

**Decision:** Accepted.

### Option 4 — Separate active-timer file and entries file

**Summary:** Store the currently running timer and completed entries in separate JSON files.

**Pros**

- Reduces risk that editing one area damages the other.
- Could make active timer checks faster.
- Clearer separation between transient and historical state.

**Cons**

- More file paths and failure modes.
- A stop operation must coordinate two files.
- Harder to explain and back up as a single timesheet artifact.

**Decision:** Rejected for now. One JSON file is simpler and sufficient.

## Decision

The Time Tracker stores a single JSON timesheet containing an `active_timer` object and a list of completed `entries`. The file is resolved through the shared SysForge path helper as `~/.sysforge/time/timesheet.json`, with `SYSFORGE_HOME` available for local testing or isolated runs.

The CLI is implemented with Typer and exposed in two ways:

- `sysforge-time ...` as a standalone app.
- `sysforge time ...` as a subcommand of the unified SysForge CLI.

The accepted command surface is:

- `start` — create an active timer.
- `stop` — convert the active timer into a completed entry.
- `status` — show the active timer and elapsed duration.
- `log` — show entries that started today.
- `report` — summarize recent time by project and tag.
- `export` — write completed entries to CSV.
- `add` — manually add a completed entry.
- `delete` — remove a completed entry by ID with confirmation unless `--yes` is passed.

The application reads shared SysForge config for timezone and project billing rates. It normalizes stored payloads when loading, skipping invalid entries and clearing invalid active timers. Completed entry IDs include a timestamp and random hex suffix to reduce collisions.

## Rationale

A local JSON state file is the right level of persistence for this app. It provides enough complexity to show state management, validation, normalization, and reporting without forcing the project into database design. The main teaching value is not relational modeling; it is coordinating CLI commands around durable local state.

The one-file structure also makes the app easy to reason about. There is exactly one active timer slot. A running timer is not an entry yet. When `stop` succeeds, the active timer is converted into a full entry, appended to `entries`, and cleared from `active_timer`. This creates a clean lifecycle and prevents overlapping timers.

Typer is consistent with the rest of SysForge. It supports readable command definitions, help text, typed `Path` options, confirmation prompts, and root integration through `sysforge.__main__`. The same Typer `app` object can be used both for the standalone command and the unified CLI.

Billable totals are computed at entry creation time rather than dynamically at report time. This is intentional. If a project’s hourly rate changes later, older entries retain the rate that was true when the work was recorded. That behavior is more realistic for timekeeping than recalculating history against the current config.

Payload normalization is also a valuable design choice. Local JSON files can be edited by hand, interrupted during development, or copied between machines. The code accepts that stored data may not always be pristine. It filters invalid entries, normalizes naive datetimes into the active timezone, and recalculates missing/invalid duration or billable totals where possible.

## Trade-offs Accepted

- JSON storage is simple but not robust for concurrent writes.
- The full timesheet is read and written on each state-changing operation.
- There is no entry editing command; correction currently means delete plus add.
- Reports cover only fixed week/month windows rather than arbitrary date ranges.
- CSV export is flat and does not include derived summary rows.
- Timezone behavior depends on valid `zoneinfo` data being available.
- Active timers are not protected by file locks.
- Billable rates are copied into entries at creation time, so updating config does not retroactively update past records.

## Consequences

### Positive Consequences

- The app demonstrates persistent CLI state clearly.
- Users can inspect and back up their timesheet file directly.
- Testing can redirect all state through `SYSFORGE_HOME`.
- The app integrates naturally with SysForge shared config.
- Manual `add` makes the system usable even when the user forgot to start a timer.
- CSV export gives the app an obvious bridge to spreadsheets and invoicing.
- Payload normalization makes the app more tolerant of imperfect local state.

### Negative Consequences

- Corrupted JSON syntax still requires manual repair before loading can work.
- A second process can race with the first if commands run simultaneously.
- Large timesheets could become inefficient because the whole JSON file is loaded.
- The report engine is simple and not suited to complex billing periods.
- Delete operations remove entries rather than archiving tombstones.

## Superseded By

Not superseded. Future versions could introduce SQLite storage, explicit file locking, arbitrary date-range reporting, entry editing, and richer export formats.

---

# Technical Design Document

## App 27 — Time Tracker

**SysForge Group | Document 2 of 5**

## Purpose & Scope

The Time Tracker records work sessions for a developer using a local command-line interface. It supports starting and stopping a timer, checking timer status, logging today’s work, generating week or month reports, exporting entries to CSV, manually adding historical sessions, and deleting entries.

The app is part of the SysForge package. It is intentionally local-first and file-backed. It does not sync with a server, manage teams, integrate with calendars, or perform invoice generation. Its purpose is to teach and demonstrate local state management, CLI command design, timestamp handling, normalization of persisted data, and simple reporting.

## System Context

```text
User
  |
  | sysforge-time start/stop/status/log/report/export/add/delete
  | sysforge time start/stop/status/log/report/export/add/delete
  v
Typer CLI: sysforge.timetracker.timetracker.app
  |
  +-- Shared config: user.timezone, time.project_rates
  +-- Shared paths: ~/.sysforge/time/timesheet.json
  +-- Shared utilities: JSON load/write, CSV write, duration formatting, datetime parsing
  +-- Shared logging: ~/.sysforge/logs/sysforge.log
  v
Local files
  +-- timesheet.json
  +-- optional exported CSV files
```

The application is not a daemon. It runs, performs one operation, writes state if needed, prints output, and exits.

## Component Breakdown

### `sysforge/timetracker/timetracker.py`

Primary implementation module.

Responsibilities:

- Define the Typer app.
- Resolve active timezone from shared config.
- Load and save the timesheet JSON file.
- Normalize active timer and entry payloads.
- Generate entry IDs.
- Build completed entries.
- Compute durations and billable totals.
- Filter entries for today, week, or month.
- Generate report lines.
- Implement CLI commands.

Important functions:

- `active_timezone()`
- `now_in_timezone()`
- `load_timesheet()`
- `save_timesheet()`
- `project_rate()`
- `make_entry_id()`
- `normalize_timesheet_payload()`
- `seconds_between()`
- `build_entry()`
- `parse_entry_datetime()`
- `todays_entries()`
- `period_entries()`
- `report_lines()`
- command handlers: `start`, `stop`, `status`, `log`, `report`, `export`, `add`, `delete`

### `sysforge/timetracker/__init__.py`

Package marker for the time tracker package. It does not re-export the public API beyond documenting that this is the Time Tracker package.

### `sysforge/sysforge_paths.py`

Shared path utility module.

Relevant responsibility:

- `get_timesheet_file()` returns the persistent timesheet location.
- `ensure_home_layout()` creates the shared SysForge directory structure.
- `get_home_dir()` honors the `SYSFORGE_HOME` environment override.

### `sysforge/shared_config.py`

Shared config loader.

Relevant responsibility:

- Loads packaged default config and merges it with user config.
- Honors `SYSFORGE_CONFIG` when set.
- Provides `user.timezone` and `time.project_rates` to the time tracker.

### `sysforge/common.py`

Shared utility module.

Relevant functions:

- `load_json_file()` for reading JSON with a default.
- `write_json_file()` for JSON writing, including atomic writes.
- `append_csv_rows()` for CSV export.
- `format_duration()` for readable hour/minute display.
- `parse_local_datetime()` for manual entry timestamps.
- `print_error()` for consistent CLI error exits.

### `sysforge/logging_utils.py`

Shared logging helper.

Relevant responsibility:

- Creates a central SysForge logger.
- Supports quiet/verbose environment behavior.
- Writes logs under the shared SysForge log directory.

### `sysforge/__main__.py`

Unified SysForge CLI.

Relevant responsibility:

- Imports the time tracker Typer app and mounts it under `sysforge time`.
- Also wires global `--verbose`, `--quiet`, `--config`, and `--version` behavior.

## Module Dependency Graph

```text
sysforge.timetracker.timetracker
  ├── datetime, timedelta, ZoneInfo, secrets, pathlib, typing
  ├── typer
  ├── sysforge.common
  │     ├── append_csv_rows
  │     ├── format_duration
  │     ├── load_json_file
  │     ├── parse_local_datetime
  │     ├── print_error
  │     └── write_json_file
  ├── sysforge.logging_utils.get_logger
  ├── sysforge.shared_config.load_shared_config
  └── sysforge.sysforge_paths
        ├── ensure_home_layout
        └── get_timesheet_file

sysforge.__main__
  └── imports sysforge.timetracker.timetracker.app as time_app
```

## Core Data Model

### Timesheet Payload

```json
{
  "active_timer": null,
  "entries": [],
  "updated_at": "2026-05-09T12:00:00.000000"
}
```

### Active Timer

```json
{
  "task": "Code review",
  "project": "ClientX",
  "tag": "billable",
  "start_time": "2026-05-09T09:00:00-07:00"
}
```

The active timer is intentionally incomplete. It has no end time, duration, rate, total, or ID. Those fields are created when the timer is stopped.

### Completed Entry

```json
{
  "id": "entry-20260509103022-a1b2c3d4",
  "task": "Code review",
  "project": "ClientX",
  "tag": "billable",
  "start_time": "2026-05-09T09:00:00-07:00",
  "end_time": "2026-05-09T10:30:00-07:00",
  "duration_seconds": 5400,
  "billable_rate": 125.0,
  "billable_total": 187.5
}
```

## Core Algorithms & Logic

### Loading the Timesheet

1. Ensure the SysForge home layout exists.
2. Read `get_timesheet_file()` with a default payload of `{"active_timer": None, "entries": []}`.
3. Pass the raw payload through `normalize_timesheet_payload()`.
4. Return the normalized payload.

The normalization step is central. It prevents the rest of the code from having to handle every possible malformed entry shape.

### Saving the Timesheet

1. Normalize the payload again.
2. Add or update the `updated_at` timestamp.
3. Write the payload to the timesheet path using `write_json_file(..., atomic=True)`.

Atomic writing reduces the chance of partial files during normal operation.

### Starting a Timer

1. Load the timesheet.
2. If `active_timer` already exists, fail with a CLI error.
3. Build a timer object using the task, project, tag, and current timezone-aware timestamp.
4. Store the timer under `active_timer`.
5. Save the timesheet.
6. Print confirmation.

This enforces a single active timer model.

### Stopping a Timer

1. Load the timesheet.
2. Require an active timer.
3. Parse and normalize the active timer start time.
4. Capture the current time as the end time.
5. Build a completed entry.
6. Append the entry to `entries`.
7. Clear `active_timer`.
8. Save the timesheet.
9. Print the stopped task and formatted duration.
10. If duration is longer than eight hours, print a warning.

### Building an Entry

1. Compute `duration_seconds = end_time - start_time`.
2. Resolve the project’s billing rate from shared config.
3. Convert seconds to hours.
4. Compute `billable_total = round(rate * hours, 2)`.
5. Generate an entry ID with timestamp plus random suffix.
6. Return a dictionary suitable for JSON persistence.

### Manual Add

1. Parse `--start` and `--end` using shared local datetime parsing and active timezone.
2. Require end time to be after start time.
3. Build a completed entry.
4. Append it to `entries`.
5. Save the timesheet.
6. Print the new entry ID.

Manual add is essential because real users forget to start timers.

### Today’s Log

1. Load completed entries.
2. Compute today’s date key from `now_in_timezone()`.
3. Select entries whose `start_time` begins with today’s ISO date.
4. Print each entry with ID, task, start/end times, duration, project, and tag.

### Week/Month Report

1. Load completed entries.
2. Determine the report period:
   - `--month`: current month starting from day 1.
   - default or `--week`: last seven days.
3. Filter entries by parsed start datetime.
4. Aggregate duration by project.
5. Aggregate duration by tag.
6. Sum billable totals.
7. Print the report.

### CSV Export

1. Load completed entries.
2. Project entries into flat row dictionaries.
3. Write rows with fixed fieldnames using `append_csv_rows()`.
4. Print export count and destination path.

### Delete Entry

1. Load completed entries.
2. Find the entry by ID.
3. If not found, exit with error.
4. Ask for confirmation unless `--yes` is supplied.
5. Remove the matching entry.
6. Save the timesheet.
7. Print confirmation.

## Data Structures

### Dictionaries

The app uses dictionaries rather than dataclasses for persisted records. This keeps JSON serialization straightforward and avoids mapping layers.

### Lists

Completed entries are stored in a list under `entries`. This preserves insertion order and keeps the storage format easy to read.

### ISO-8601 Strings

Timestamps are serialized as ISO strings. This is human-readable and compatible with `datetime.fromisoformat()`.

### Configuration Dictionaries

Shared config is loaded as nested dictionaries. Time tracker uses:

- `user.timezone`
- `time.project_rates`

## State Management

The application has one persistent state file:

```text
~/.sysforge/time/timesheet.json
```

When `SYSFORGE_HOME` is set, this becomes:

```text
$SYSFORGE_HOME/time/timesheet.json
```

State transitions:

```text
No active timer
  └── start -> active_timer exists

Active timer exists
  ├── status -> active_timer unchanged
  └── stop -> active_timer cleared, completed entry appended

Completed entries
  ├── log/report/export -> read-only
  ├── add -> append entry
  └── delete -> remove entry
```

## Error Handling Strategy

### User-Facing CLI Errors

The app uses `print_error()` for common invalid operations:

- Starting a timer while one is already active.
- Stopping when no timer is running.
- Invalid active timer start time.
- Using both `--week` and `--month` on report.
- Adding a manual entry where `--end` is not after `--start`.
- Deleting a missing entry.

`print_error()` prints to stderr and raises `typer.Exit`.

### Defensive Persistence Handling

The app normalizes loaded JSON:

- Non-dictionary payloads become an empty default structure.
- Invalid active timers are cleared.
- Invalid entries are skipped.
- Naive datetimes are assigned the active timezone.
- A missing or invalid duration is recalculated from start/end.
- A missing or invalid billable total is recalculated from rate and duration.

### Limits

If the JSON file exists but contains invalid JSON syntax, `load_json_file()` will raise a JSON decode error. The current app does not implement an automatic recovery file or backup for that case.

## External Dependencies

### Runtime Dependencies

| Dependency | Source | Purpose |
|---|---|---|
| Typer | `typer>=0.12` | CLI commands, options, prompts, exits |
| Rich | `rich>=13.7` | Installed as SysForge dependency, not central in this module |
| psutil | `psutil>=5.9` | Used by other SysForge apps, not directly by Time Tracker |
| Markdown | `markdown>=3.6` | Used by docs builder, not Time Tracker |
| Pygments | `pygments>=2.18` | Used by docs builder, not Time Tracker |

### Standard Library Usage

| Module | Purpose |
|---|---|
| `datetime` | Timestamps, durations, period filtering |
| `zoneinfo` | Timezone-aware local times |
| `secrets` | Random entry ID suffixes |
| `pathlib` | File paths |
| `typing` | Type annotations |

## Concurrency Model

The app is single-process and command-oriented. There are no threads, async tasks, or background schedulers. Each CLI invocation reads state, optionally mutates it, writes it, and exits.

Concurrency limitations:

- No file lock prevents two `start` or `stop` commands from racing.
- Atomic writes reduce partial-file risk but do not solve read-modify-write races.
- A future version should add lock files or a SQLite backend if concurrent usage matters.

## Known Limitations

- No command edits an existing entry in place.
- No arbitrary date-range report.
- No invoice generation.
- No overlapping timer support.
- No pause/resume support.
- No multi-user model.
- No synchronization between machines.
- No automatic recovery from invalid JSON syntax.
- No file locking.
- Delete permanently removes entries from the JSON file.
- Today’s log filters by ISO date prefix, so it depends on normalized timestamp strings.

## Design Patterns Used

### Command Pattern

Each Typer command maps to one operation: start, stop, status, log, report, export, add, delete.

### Repository-Like File Store

`load_timesheet()` and `save_timesheet()` isolate the persistence boundary.

### Normalization Pipeline

Raw JSON is passed through a normalization layer before command logic uses it.

### Shared Configuration Pattern

The app reads shared SysForge config rather than defining a separate time-tracker-specific config file.

### Local-First Utility Pattern

All state lives on the local filesystem and is user-inspectable.

---

# Interface Design Specification

## App 27 — Time Tracker

**SysForge Group | Document 3 of 5**

## Invocation Syntax

### Standalone Command

```bash
sysforge-time COMMAND [OPTIONS]
```

### Unified SysForge Command

```bash
sysforge time COMMAND [OPTIONS]
```

### Development Invocation

```bash
python -m sysforge.timetracker.timetracker COMMAND [OPTIONS]
```

## Command Summary

| Command | Purpose |
|---|---|
| `start` | Start a new active timer |
| `stop` | Stop the active timer and create a completed entry |
| `status` | Show the currently active timer |
| `log` | Show entries for today |
| `report` | Show week or month totals |
| `export` | Export completed entries to CSV |
| `add` | Add a completed entry manually |
| `delete` | Delete a completed entry by ID |

## Argument Reference Tables

### `start`

```bash
sysforge-time start TASK [--project PROJECT] [--tag TAG]
```

| Name | Type | Required | Default | Accepted Values | Description |
|---|---:|---:|---|---|---|
| `TASK` | string | Yes | none | Non-empty task text | Task name to track |
| `--project` | string | No | `Unassigned` | Any string | Project name used for reporting and billing rate lookup |
| `--tag` | string | No | `general` | Any string | Tag used for reporting |

### `stop`

```bash
sysforge-time stop
```

No command-specific arguments.

### `status`

```bash
sysforge-time status
```

No command-specific arguments.

### `log`

```bash
sysforge-time log
```

No command-specific arguments.

### `report`

```bash
sysforge-time report [--week | --month]
```

| Name | Type | Required | Default | Accepted Values | Description |
|---|---:|---:|---|---|---|
| `--week` | boolean flag | No | False | present/absent | Report on last seven days |
| `--month` | boolean flag | No | False | present/absent | Report on current month |

Rules:

- If neither flag is provided, week is used.
- `--week` and `--month` cannot be used together.

### `export`

```bash
sysforge-time export --csv PATH
```

| Name | Type | Required | Default | Accepted Values | Description |
|---|---:|---:|---|---|---|
| `--csv` | path | Yes | none | Writable file path | Output CSV destination |

### `add`

```bash
sysforge-time add TASK --start START --end END [--project PROJECT] [--tag TAG]
```

| Name | Type | Required | Default | Accepted Values | Description |
|---|---:|---:|---|---|---|
| `TASK` | string | Yes | none | Any non-empty task text | Task name |
| `--start` | datetime string | Yes | none | `YYYY-MM-DD HH:MM`, `YYYY-MM-DDTHH:MM`, or ISO datetime variants | Entry start time |
| `--end` | datetime string | Yes | none | Same as `--start`; must be after start | Entry end time |
| `--project` | string | No | `Unassigned` | Any string | Project name |
| `--tag` | string | No | `general` | Any string | Entry tag |

### `delete`

```bash
sysforge-time delete ENTRY_ID [--yes]
```

| Name | Type | Required | Default | Accepted Values | Description |
|---|---:|---:|---|---|---|
| `ENTRY_ID` | string | Yes | none | Existing entry ID | Completed entry to remove |
| `--yes` | boolean flag | No | False | present/absent | Skip confirmation prompt |

## Input Contract

### Timesheet File

The timesheet file should contain a JSON object. Expected top-level keys:

| Key | Type | Required | Description |
|---|---|---:|---|
| `active_timer` | object or null | No | Currently running timer |
| `entries` | list | No | Completed entries |
| `updated_at` | string | No | Last save timestamp |

If keys are missing, the app fills defaults during normalization.

### Active Timer Contract

| Key | Type | Required | Description |
|---|---|---:|---|
| `task` | string | Yes | Task name |
| `project` | string | No | Project name |
| `tag` | string | No | Tag name |
| `start_time` | ISO datetime string | Yes | Timer start timestamp |

### Completed Entry Contract

| Key | Type | Required | Description |
|---|---|---:|---|
| `id` | string | Yes | Entry identifier |
| `task` | string | Yes | Task name |
| `project` | string | No | Project name |
| `tag` | string | No | Tag |
| `start_time` | ISO datetime string | Yes | Start timestamp |
| `end_time` | ISO datetime string | Yes | End timestamp |
| `duration_seconds` | integer | No | Duration; recalculated if missing/invalid |
| `billable_rate` | number | No | Hourly project rate |
| `billable_total` | number | No | Billable amount |

## Output Contract

### `start`

Success output:

```text
Started timer: Code review
```

### `stop`

Success output:

```text
Stopped timer: Code review
Duration: 1h 30m
```

Long timer warning:

```text
Warning: this timer ran for more than 8 hours.
```

### `status`

No active timer:

```text
No timer is running.
```

Active timer:

```text
Active task: Code review
Project: ClientX
Tag: billable
Elapsed: 1h 30m
```

### `log`

No entries:

```text
No entries for today.
```

Entries:

```text
entry-20260509090000-a1b2c3d4 | Code review | 09:00-10:30 | 1h 30m | ClientX | billable
```

### `report`

```text
Time report for week
Entries counted: 2

Totals by project
  ClientX: 3h 00m
  Learning: 1h 00m

Totals by tag
  billable: 3h 00m
  study: 1h 00m

Billable total: $375.00
```

### `export`

```text
Exported 2 entries to timesheet.csv
```

### `add`

```text
Added entry entry-20260509120000-a1b2c3d4
```

### `delete`

```text
Deleted entry entry-20260509120000-a1b2c3d4
```

## CSV Output Contract

CSV columns:

| Column | Description |
|---|---|
| `id` | Entry ID |
| `task` | Task name |
| `project` | Project name |
| `tag` | Tag |
| `start_time` | ISO start timestamp |
| `end_time` | ISO end timestamp |
| `duration_seconds` | Integer duration |
| `billable_rate` | Hourly rate |
| `billable_total` | Rounded billable amount |

## Exit Code Reference

| Scenario | Expected Exit |
|---|---:|
| Successful command | 0 |
| User-facing validation error | 1 |
| Confirmation canceled during delete | 0 |
| Invalid command syntax from Typer | non-zero |
| Missing required option | non-zero |
| File/JSON failure bubbling from helpers | non-zero |

## Error Output Behavior

Common error messages:

```text
A timer is already running. Stop it before starting a new one.
No timer is currently running.
Active timer has an invalid start_time.
Choose either --week or --month, not both.
--end must be after --start.
Entry not found: <entry_id>
```

Errors emitted through `print_error()` are printed in Typer’s error flow and exit non-zero.

## Environment Variables

| Variable | Required | Description |
|---|---:|---|
| `SYSFORGE_HOME` | No | Overrides the default `~/.sysforge` state directory |
| `SYSFORGE_CONFIG` | No | Overrides the shared SysForge config path |
| `SYSFORGE_VERBOSE` | No | Set by unified CLI for more logging |
| `SYSFORGE_QUIET` | No | Set by unified CLI for quieter logging |

## Configuration Files

### Shared SysForge Config

Default location:

```text
~/.sysforge/sysforge.json
```

Relevant keys:

```json
{
  "user": {
    "timezone": "America/Los_Angeles"
  },
  "time": {
    "project_rates": {
      "ClientX": 125,
      "Learning": 0,
      "Internal": 85
    }
  }
}
```

### Timesheet File

Default location:

```text
~/.sysforge/time/timesheet.json
```

## Side Effects

| Command | Side Effects |
|---|---|
| `start` | Creates or updates timesheet file with active timer |
| `stop` | Appends completed entry and clears active timer |
| `status` | Reads timesheet only |
| `log` | Reads timesheet only |
| `report` | Reads timesheet only |
| `export` | Writes CSV file |
| `add` | Appends completed entry |
| `delete` | Removes completed entry after confirmation or `--yes` |

## Usage Examples

### Basic Start/Stop Flow

```bash
sysforge-time start "Code review" --project ClientX --tag billable
sysforge-time status
sysforge-time stop
```

### Manual Entry

```bash
sysforge-time add "Architecture notes" \
  --start "2026-05-09 09:00" \
  --end "2026-05-09 10:30" \
  --project Learning \
  --tag study
```

### Weekly Report

```bash
sysforge-time report --week
```

### Monthly Report

```bash
sysforge-time report --month
```

### CSV Export

```bash
sysforge-time export --csv timesheet.csv
```

### Unified CLI Use

```bash
sysforge time start "Bug triage" --project Internal --tag ops
sysforge time stop
sysforge time report --week
```

### Intentional Failure: Starting Twice

```bash
sysforge-time start "Task A"
sysforge-time start "Task B"
```

Expected result:

```text
A timer is already running. Stop it before starting a new one.
```

### Intentional Failure: Bad Manual Time Range

```bash
sysforge-time add "Bad entry" --start "2026-05-09 10:00" --end "2026-05-09 09:00"
```

Expected result:

```text
--end must be after --start.
```

---

# Runbook

## App 27 — Time Tracker

**SysForge Group | Document 4 of 5**

## Prerequisites

- Python 3.11 or newer.
- SysForge installed from the repository.
- Runtime dependencies installed, especially Typer.
- A writable SysForge state directory.
- Valid timezone data for the configured timezone.

## Installation Procedure

From the SysForge repository root:

```bash
python -m pip install -e .
```

For development and testing:

```bash
python -m pip install -e ".[dev]"
```

Alternative dependency-first install:

```bash
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps
```

## Configuration Steps

### 1. Choose State Directory

Default:

```text
~/.sysforge
```

Development override:

```bash
export SYSFORGE_HOME=.sysforge-dev
```

Windows PowerShell:

```powershell
$env:SYSFORGE_HOME = ".sysforge-dev"
```

### 2. Confirm Shared Config

The first run creates the SysForge home layout and copies default config when available.

Relevant default config values:

```json
{
  "user": {
    "timezone": "America/Los_Angeles"
  },
  "time": {
    "project_rates": {
      "ClientX": 125,
      "Learning": 0,
      "Internal": 85
    }
  }
}
```

### 3. Customize Project Rates

Edit:

```text
~/.sysforge/sysforge.json
```

Example:

```json
{
  "time": {
    "project_rates": {
      "ClientX": 125,
      "Internal": 85,
      "Learning": 0,
      "NewClient": 150
    }
  }
}
```

## Standard Operating Procedures

### Start a Timer

```bash
sysforge-time start "Implement parser" --project ClientX --tag billable
```

Expected:

```text
Started timer: Implement parser
```

### Check Current Timer

```bash
sysforge-time status
```

Expected:

```text
Active task: Implement parser
Project: ClientX
Tag: billable
Elapsed: 0h 25m
```

### Stop a Timer

```bash
sysforge-time stop
```

Expected:

```text
Stopped timer: Implement parser
Duration: 0h 25m
```

### Add Missed Time

```bash
sysforge-time add "Planning notes" --start "2026-05-09 08:00" --end "2026-05-09 08:45" --project Internal --tag planning
```

### View Today’s Log

```bash
sysforge-time log
```

### Generate Weekly Report

```bash
sysforge-time report --week
```

### Export CSV

```bash
sysforge-time export --csv timesheet.csv
```

### Delete an Entry

```bash
sysforge-time delete entry-20260509080000-a1b2c3d4
```

Skip confirmation:

```bash
sysforge-time delete entry-20260509080000-a1b2c3d4 --yes
```

## Health Checks

### Command Availability

```bash
sysforge-time --help
sysforge time --help
```

### State Directory Check

```bash
ls ~/.sysforge/time
```

Expected file after use:

```text
timesheet.json
```

### Timesheet JSON Check

```bash
python -m json.tool ~/.sysforge/time/timesheet.json
```

### Active Timer Check

```bash
sysforge-time status
```

### Report Check

```bash
sysforge-time report --week
```

### CSV Export Check

```bash
sysforge-time export --csv /tmp/timesheet.csv
```

## Expected Output Samples

### No Timer Running

```text
No timer is running.
```

### Empty Today Log

```text
No entries for today.
```

### Report with No Entries

```text
Time report for week
Entries counted: 0

Totals by project

Totals by tag

Billable total: $0.00
```

### CSV Export

```text
Exported 3 entries to timesheet.csv
```

## Known Failure Modes

| Failure Mode | Symptom | Likely Cause | Recovery |
|---|---|---|---|
| Timer already running | Cannot start a new timer | `active_timer` exists | Run `status`, then `stop`, or repair JSON if stale |
| No active timer | `stop` fails | Nothing is running | Use `add` to enter missed time manually |
| Bad manual range | `--end must be after --start` | End time before or equal to start | Correct input timestamps |
| Invalid active start time | Status/stop reports invalid active timer | Hand-edited JSON or corrupted state | Edit or clear `active_timer` in timesheet file |
| Invalid JSON syntax | Load command crashes or exits non-zero | Broken timesheet file | Restore backup or repair JSON manually |
| Wrong timezone | Times appear offset | `user.timezone` config value is wrong | Update shared config |
| Missing timezone data | ZoneInfo error on some systems | OS/Python lacks timezone database | Install `tzdata` if needed |
| Duplicate billing rate assumptions | Billable totals differ from expected | Project rate missing or changed | Add project rate before entry creation or manually adjust JSON |

## Troubleshooting Decision Tree

```text
Command failed?
  |
  +-- Is the command syntax valid?
  |     |
  |     +-- No -> Run sysforge-time COMMAND --help
  |     +-- Yes
  |
  +-- Is the timesheet JSON valid?
  |     |
  |     +-- No -> Repair ~/.sysforge/time/timesheet.json
  |     +-- Yes
  |
  +-- Is the problem with active timer state?
  |     |
  |     +-- start says timer exists -> run status, then stop or clear stale active_timer
  |     +-- stop says no timer -> use add for missed time
  |     +-- status says invalid start_time -> repair active_timer
  |
  +-- Is the problem with reports or billing?
  |     |
  |     +-- Check user.timezone
  |     +-- Check time.project_rates
  |     +-- Confirm entry start_time is in report period
  |
  +-- Is the problem with CSV export?
        |
        +-- Confirm output directory exists or is writable
        +-- Try exporting to a simple local path
```

## Dependency Failure Handling

### Typer Missing

Symptom:

```text
ModuleNotFoundError: No module named 'typer'
```

Recovery:

```bash
python -m pip install -e .
```

### Timezone Data Missing

Symptom may include failure from `ZoneInfo` for a configured timezone.

Recovery:

```bash
python -m pip install tzdata
```

Or set timezone to `UTC` in SysForge config.

## Recovery Procedures

### Clear a Stale Active Timer

1. Open the timesheet file:

```bash
$EDITOR ~/.sysforge/time/timesheet.json
```

2. Set:

```json
"active_timer": null
```

3. Validate JSON:

```bash
python -m json.tool ~/.sysforge/time/timesheet.json
```

4. Add missed work manually if needed:

```bash
sysforge-time add "Recovered work" --start "2026-05-09 09:00" --end "2026-05-09 10:00"
```

### Repair Invalid JSON

1. Back up the file.
2. Run `python -m json.tool` to find syntax errors.
3. Fix commas, brackets, quotes, or malformed objects.
4. Re-run `sysforge-time status`.

### Rebuild Empty Timesheet

If the file is unrecoverable:

```json
{
  "active_timer": null,
  "entries": []
}
```

Save as:

```text
~/.sysforge/time/timesheet.json
```

## Logging Reference

The time tracker obtains a logger named:

```text
sysforge.timetracker
```

The shared logging utility writes through the central SysForge log configuration, normally under:

```text
~/.sysforge/logs/sysforge.log
```

Logged actions include timer starts and other implementation-level events.

## Maintenance Notes

- Keep `timesheet.json` small enough for whole-file reads and writes.
- Back up `~/.sysforge/time/timesheet.json` if it becomes important billing data.
- Prefer `add` over hand-editing JSON for ordinary corrections.
- Use `delete --yes` carefully because entries are removed, not archived.
- Add file locking before recommending this app for concurrent shell usage.
- Consider SQLite if entries grow into thousands or reporting becomes more complex.
- Keep tests running under isolated `SYSFORGE_HOME` to avoid modifying real user data.

---

# Lessons Learned

## App 27 — Time Tracker

**SysForge Group | Document 5 of 5**

## Project Summary

The Time Tracker is a local CLI app for recording work sessions. It supports both live timers and manual entries, stores data in a shared SysForge timesheet file, generates simple reports, and exports completed work to CSV.

This app is more stateful than many earlier CLI utilities. It has to remember what happened before the current command. That makes it a useful project for learning how persistence changes program design. A command like `start` is not just input/output; it changes future behavior by creating an active timer. A command like `stop` has to validate state, transform that state, append history, and clear the active slot.

## Original Goals vs. Actual Outcome

### Original Goals

- Build a CLI time tracker.
- Support start, stop, status, report, and export flows.
- Use the SysForge shared config and state directories.
- Keep persistence understandable.
- Practice timestamp and duration handling.

### Actual Outcome

The final app meets those goals and adds useful robustness:

- Manual `add` supports missed sessions.
- `delete` supports corrections.
- Stored payloads are normalized on load.
- Billing rates are read from shared config.
- Week/month reporting is implemented.
- CSV export is available.
- Tests verify core calculations, normalization, filtering, and load/save behavior.

## Technical Decisions That Paid Off

### One Timesheet File

Using one JSON file kept the state model easy to understand. There is one place to inspect when debugging:

```text
~/.sysforge/time/timesheet.json
```

That matters for a student portfolio project. The goal is not to hide state behind a database; it is to show state clearly.

### Active Timer Separate from Entries

Keeping `active_timer` separate from completed `entries` paid off. It makes the lifecycle obvious:

```text
start -> active_timer
stop -> entry + active_timer cleared
```

This prevents half-complete entries from living in the same list as completed sessions.

### Shared Config Integration

Using shared config for timezone and project rates made the app feel like part of SysForge rather than an isolated script. It also created a realistic dependency between tools: the config manager can update values that the time tracker uses.

### Payload Normalization

The normalization layer is one of the strongest parts of the design. It recognizes that local JSON may be imperfect and attempts to recover useful entries instead of trusting every field blindly.

### Manual Entry Support

A timer app without manual entry support is frustrating. The `add` command makes the app more realistic because people forget to start timers.

### CSV Export

CSV export provides a simple integration point. It does not require building invoice features or spreadsheet logic inside the app.

## Technical Decisions That Created Debt

### Dictionary-Based Data Model

Dictionaries made JSON easy, but they spread field names throughout the code. A future version might benefit from dataclasses or typed models for entries and active timers.

### No File Locking

The app assumes one command at a time. That is fine for a personal CLI, but it is still a real limitation. Two shells running commands together could overwrite each other’s changes.

### Limited Reporting Options

Week and month reports are useful but not enough for all users. Arbitrary date ranges would make the report command more flexible.

### Delete Instead of Archive

Deleting entries permanently is simple, but not ideal for auditability. A better time tracker might mark entries as deleted or keep a change log.

### Billable Rate Snapshot Has Trade-offs

Storing billable totals at entry creation is realistic, but it means rate mistakes need manual correction. If a user starts with the wrong config, the app will not automatically fix old entries later.

## What Was Harder Than Expected

### Timezone Handling

Timezone handling is harder than just calling `datetime.now()`. The app has to decide what to do with naive datetimes, config timezones, parsed manual entries, and report windows.

### Corrupt State Handling

Once state is persisted locally, the code must decide how tolerant to be. Skipping invalid entries and clearing invalid timers is helpful, but invalid JSON syntax still cannot be recovered automatically.

### Report Filtering

Filtering by week or month sounds simple, but it depends on parsing start timestamps correctly and comparing them in the active timezone.

### Billing Calculations

Billing totals require connecting duration, project name, config rates, rounding, and missing-rate behavior. It is not complicated math, but it is easy to get inconsistent if not centralized.

## What Was Easier Than Expected

### CSV Export

Once entries were dictionaries, CSV export was straightforward. The shared `append_csv_rows()` helper kept this command small.

### Typer Command Structure

Typer made command definitions readable. Each command could focus on one operation without much manual argument parsing.

### Default State Creation

The shared SysForge path utilities handled directory creation, so the time tracker did not need to reinvent home-directory setup.

## Python-Specific Learnings

### `datetime.fromisoformat()` Is Useful but Not Enough

It parses stored timestamps well, but the app still has to normalize timezone-aware and naive values.

### `ZoneInfo` Makes Timezones Practical

Using `ZoneInfo(active_timezone())` keeps timestamps aligned with user config without adding a third-party timezone dependency.

### `secrets.token_hex()` Is a Simple ID Suffix

A timestamp alone could collide if entries are created quickly. Adding a random suffix makes IDs safer without building a full ID service.

### JSON Needs Shape Validation

Loading JSON is not the same as loading valid application data. The app needs explicit normalization to protect command logic.

### Small Helpers Matter

Functions like `seconds_between()`, `build_entry()`, and `report_lines()` make the command handlers easier to read and easier to test.

## Architecture Insights

### State Changes Should Be Centralized

The app is easier to understand because loading and saving state go through `load_timesheet()` and `save_timesheet()`. Commands do not directly open the JSON file.

### CLI Apps Still Need Domain Rules

Even though this is a command-line app, it has domain rules:

- Only one timer can run at a time.
- End time must be after start time.
- An active timer is not a completed entry.
- Billing uses project rate at entry creation.
- Invalid entries should not break all reports.

### Local Files Are an Interface

The JSON file is not just implementation detail. Users may inspect or edit it. That means the structure should be readable, stable, and recoverable.

### Shared Platform Code Reduces Repetition

SysForge’s shared path, config, logging, JSON, CSV, and duration helpers make this app smaller and more consistent with the rest of the toolkit.

## Testing Gaps

The existing tests cover important core behavior:

- Duration calculation.
- Entry ID shape.
- Billable entry construction.
- Timesheet normalization.
- Period filtering.
- Report line tolerance.
- Load/save roundtrip.

Remaining gaps:

- CLI integration tests for every Typer command.
- Start/stop full lifecycle with a fake clock.
- Delete confirmation paths.
- CSV export file contents.
- Invalid JSON syntax recovery behavior.
- Long timer warning behavior.
- Timezone edge cases around midnight and daylight saving transitions.
- Concurrent command behavior.

## Reusable Patterns Identified

### Local JSON Store Pattern

```text
load -> normalize -> mutate -> save atomically
```

This pattern applies to many beginner-to-intermediate CLI apps.

### Active Record Slot Pattern

Using a single `active_timer` slot is a reusable pattern for apps that have one in-progress operation.

### Report Aggregation Pattern

The `report_lines()` approach can be reused for other grouped summaries: collect totals by key, sort keys, format output.

### Manual Correction Command Pattern

The pair of `add` and `delete` gives users a basic correction workflow without requiring a complex edit command.

### Config-Driven Calculation Pattern

Project rates show how config can influence business logic while keeping the app local.

## If I Built This Again

I would keep the same overall architecture but improve several areas:

1. Add dataclasses or typed models for `ActiveTimer` and `TimeEntry`.
2. Add a file lock around read-modify-write operations.
3. Add `edit` command for correcting task, project, tag, and times.
4. Add `report --from YYYY-MM-DD --to YYYY-MM-DD`.
5. Add `pause` and `resume` if the app is meant for daily use.
6. Add an archive or audit trail for deleted entries.
7. Add a recovery command for invalid or stale active timers.
8. Add richer tests around CLI behavior.
9. Add JSON schema validation for the timesheet file.
10. Consider SQLite if the app grows beyond personal use.

## Open Questions

- Should project rates be copied into entries forever, or should reports optionally recalculate with current rates?
- Should deleting an entry create a tombstone for audit purposes?
- Should manual entries allow notes?
- Should reports include daily breakdowns?
- Should active timers survive timezone config changes?
- Should `log` show today based on entry start time, end time, or overlap with the current day?
- Should CSV export support only filtered periods instead of all entries?
- Should the app warn when a timer has been active across multiple days?

## Final Reflection

This project is a strong example of how state changes the architecture of a CLI app. A stateless script can be mostly a function from input to output. A time tracker is different. It has memory, lifecycle rules, recovery concerns, and reporting expectations.

The most important design lesson is that persistence should be treated as part of the system contract. The timesheet file must be understandable, normalized, and protected as much as the project scope allows. Even in a small app, the difference between “it writes JSON” and “it manages state responsibly” is significant.

The Time Tracker fits the SysForge group well because it combines shared configuration, shared filesystem layout, user-facing CLI commands, and durable local state into one practical utility.
