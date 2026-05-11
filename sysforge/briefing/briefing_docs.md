# Architecture Decision Record

## App 22 — Daily Briefing Generator / SysForge Briefing

**SysForge Group | Document 1 of 5**  
**Status: Accepted**  
**Date: 2026-05-08**

---

## Title

Use a shared SysForge CLI package to generate deterministic daily briefing files from local JSON data, shared user configuration, and a lightweight system snapshot.

---

## Context

The Daily Briefing Generator is App 22 in the SysForge toolkit. Unlike the earlier standalone Vault OS apps, this project sits inside a larger monorepo package named `sysforge`. The repository contains several CLI utilities, including file organization, Markdown-to-HTML documentation building, briefings, time tracking, config management, health monitoring, and a unified root CLI.

The briefing app’s job is intentionally narrow: create a daily personal briefing file. It reads a user profile, timezone, mock weather, quotes, mock calendar items, and system details, then writes either a text or Markdown file for the current day. It must work as both its own command, `sysforge-briefing`, and as a subcommand of the unified CLI, `sysforge briefing`.

The main design pressure is not algorithmic complexity. It is integration discipline. The app has to live cleanly inside the SysForge package without duplicating path, config, JSON, logging, or state-management utilities that other SysForge apps already use. This makes the project a good exercise in package architecture, shared infrastructure, and controlled CLI side effects.

---

## Decision Drivers

- Keep the briefing generator small enough to understand as one CLI app.
- Use shared SysForge utilities instead of copying filesystem, JSON, logging, and config code.
- Support both text and Markdown output without creating two separate renderers at the CLI level.
- Avoid network/API scope creep by using local mock weather, quote, and calendar JSON files.
- Keep the app useful when run repeatedly by writing files into a predictable SysForge data directory.
- Allow tests to isolate filesystem effects through `SYSFORGE_HOME`.
- Preserve student-authored architecture by keeping state, formatting, and input normalization explicit.

---

## Options Considered

### Option 1 — Build the briefing generator as a standalone repository

**Rejected.**

This would have been simpler for one app, but it would duplicate path handling, shared config, logging, and install metadata already present in SysForge. It would also weaken the portfolio evidence for monorepo architecture.

### Option 2 — Put all logic directly in the root `sysforge` command

**Rejected.**

The unified CLI should compose apps, not contain every app’s implementation. Keeping briefing logic in `sysforge/briefing/briefing.py` preserves a clear module boundary while still allowing the root CLI to mount it as `sysforge briefing`.

### Option 3 — Use live weather/calendar APIs

**Rejected.**

Live APIs would add credentials, networking, rate limits, nondeterministic tests, and error cases outside the intended scope. The current implementation uses local JSON fixtures to demonstrate the architecture without depending on external services.

### Option 4 — Write only to stdout

**Rejected.**

A daily briefing is most useful as a file that can be saved, viewed later, and tracked in history. The CLI still prints the generated path, but the primary output is a text or Markdown file.

### Option 5 — Use only package defaults with no user-level config

**Rejected.**

Package defaults are useful, but a daily briefing should reflect the user. The app merges package defaults with shared SysForge config and optional briefing-specific config, which lets users control name, timezone, temperature unit, input data files, and output directory.

### Option 6 — Support text and Markdown through one generic template engine

**Rejected for now.**

A template engine would add another dependency and obscure the learning goal. Two direct renderer functions, `build_text_briefing()` and `build_markdown_briefing()`, are more explicit and easier to test.

---

## Decision

Implement the Daily Briefing Generator as the `sysforge.briefing` package inside the SysForge monorepo, with `sysforge/briefing/briefing.py` serving as the main application module. The app will expose a Typer app named `app`, which is installed as `sysforge-briefing` and mounted under the root SysForge CLI as `sysforge briefing`.

The app will:

- Load shared SysForge configuration from `~/.sysforge/sysforge.json` or `SYSFORGE_CONFIG`.
- Load briefing-specific defaults from `sysforge/briefing/data/briefing_config.json`.
- Optionally merge an explicitly provided `--briefing-config` file.
- Load local JSON data for weather, quotes, and calendar items.
- Generate a greeting based on timezone-aware local time.
- Build either text or Markdown content.
- Include optional weather, quote, and calendar sections.
- Include a system snapshot with OS, Python version, uptime, and free disk space.
- Write the briefing to a dated file under `~/.sysforge/briefings/` unless `output_dir` is configured.
- Append a generation record to `briefing_history.json`.

---

## Rationale

The chosen design fits the SysForge architecture because the briefing generator is a normal package submodule, not a special-case script. It uses the same home directory resolution, logging, JSON helpers, and shared configuration conventions as the rest of the toolkit.

Using Typer keeps CLI definitions readable while still producing a professional command-line interface. The command options are direct: output format, optional config path, and section toggles. There is no hidden interactive state.

Using local JSON fixtures keeps the app deterministic enough for portfolio testing. Weather and calendar data are not real integrations; they are controlled input sources used to show file parsing, validation, formatting, and reporting flow.

The renderer split between text and Markdown is intentionally simple. It avoids a premature abstraction while still demonstrating how the same normalized data can produce two output formats.

---

## Trade-offs Accepted

- The app does not fetch live weather or live calendar data.
- The same day’s briefing filename is deterministic, so repeated runs overwrite that day’s briefing file.
- Quote selection uses `random.choice()`, so output can vary unless quote inclusion is disabled or randomness is patched in tests.
- The history file is append-oriented and not designed as a database.
- Config validation is practical rather than schema-driven; unsupported briefing config keys are ignored with a warning.
- System snapshot data is intentionally shallow.
- The app depends on the larger SysForge package environment instead of being a fully independent script.

---

## Consequences

### Positive Consequences

- The app demonstrates real monorepo integration.
- CLI behavior is consistent with the rest of SysForge.
- Tests can isolate state with `SYSFORGE_HOME`.
- JSON data sources are easy to inspect and replace.
- The generated output is useful as an artifact, not just terminal text.
- The app provides a reusable formatting pipeline for future reporting work.

### Negative Consequences

- Running the app creates filesystem state under SysForge home directories.
- Users must understand the difference between package defaults, shared config, and briefing-specific config.
- No live API support means the “weather” and “calendar” sections are simulations unless the user maintains the JSON files.
- The app inherits SysForge’s project-wide dependencies even though the briefing feature itself uses only a subset directly.

---

## Superseded By

Not superseded.

Future superseding decisions could include:

- replacing local JSON weather/calendar files with provider adapters,
- adding a template system for output formats,
- adding collision-safe output naming for multiple daily briefings,
- or promoting briefing generation into a scheduled workflow.

---

# Technical Design Document

## App 22 — Daily Briefing Generator / SysForge Briefing

**SysForge Group | Document 2 of 5**  
**Status: Accepted**

---

## Purpose & Scope

The Daily Briefing Generator creates a dated daily briefing file from local data and system information. It supports two output formats: plain text and Markdown.

In scope:

- command-line briefing generation,
- shared SysForge config integration,
- optional briefing-specific config files,
- weather section from local JSON,
- random quote section from local JSON,
- calendar section from local JSON,
- system snapshot section,
- text and Markdown rendering,
- output file writing,
- generation history tracking,
- testable helper functions for sanitization, formatting, data normalization, and end-to-end generation.

Out of scope:

- live weather APIs,
- live calendar APIs,
- email delivery,
- scheduled background execution,
- multi-user server mode,
- database persistence,
- PDF generation,
- authentication,
- concurrent write coordination beyond atomic JSON history writing.

---

## System Context

```text
User
  |
  | sysforge-briefing / sysforge briefing
  v
Typer CLI callback
  |
  v
briefing.generate_briefing()
  |
  +--> shared SysForge config
  +--> briefing-specific config
  +--> local weather / quote / calendar JSON
  +--> system snapshot
  |
  v
Renderer: text or Markdown
  |
  v
Daily briefing file + briefing_history.json
```

The briefing app is one sub-application in the SysForge toolkit. The root `sysforge` CLI mounts `sysforge.briefing.briefing.app` as the `briefing` subcommand. The package metadata also exposes the same Typer app through the `sysforge-briefing` console script.

---

## Component Breakdown

### `sysforge/briefing/briefing.py`

Main app module. It contains:

- the Typer app object,
- config normalization,
- mock data loading,
- greeting selection,
- weather/quote/calendar selection,
- system snapshot collection,
- text and Markdown rendering,
- output writing,
- history append logic,
- CLI callback and `main()` wrapper.

This is the only briefing-specific Python module with substantial logic.

### `sysforge/briefing/data/briefing_config.json`

Default briefing config. It provides starter values for:

- name,
- timezone,
- temperature unit,
- weather file,
- quotes file,
- calendar file,
- output directory.

### `sysforge/briefing/data/weather.json`

Local weather fixture. It contains:

- a `default` weather object,
- optional date-specific overrides under `days`.

### `sysforge/briefing/data/quotes.json`

Local list of quote strings. One quote is selected randomly when the quote section is enabled.

### `sysforge/briefing/data/calendar.json`

Local calendar fixture. Each valid item has:

- `date`,
- `time`,
- `title`.

Rows without a date are ignored during normalization.

### `sysforge/common.py`

Shared utility module used by the briefing app for:

- JSON loading,
- JSON writing,
- text file writing,
- duration formatting,
- error printing through Typer.

### `sysforge/shared_config.py`

Loads SysForge-wide configuration. It supports:

- default package config,
- user config under SysForge home,
- optional `SYSFORGE_CONFIG`,
- recursive dictionary merge through `deep_merge()`.

### `sysforge/sysforge_paths.py`

Central path authority. The briefing app uses it to find:

- SysForge home,
- default briefing output directory,
- briefing history file,
- package briefing data directory.

It also creates the SysForge home layout on demand.

### `sysforge/logging_utils.py`

Creates named loggers and central file logging under SysForge’s log directory. The briefing app uses `get_logger("sysforge.briefing")`.

### `sysforge/__main__.py`

Unified root CLI. It mounts the briefing Typer app with:

```python
app.add_typer(briefing_app, name="briefing")
```

### `tests/test_briefing.py`

Briefing-specific test coverage. It verifies sanitization, mock data loading, weather selection, calendar sorting, temperature conversion, disk-root fallback, text/Markdown rendering, config normalization, bad format rejection, payload normalization, Markdown quote wrapping, and an end-to-end Markdown generation path.

### `tests/conftest.py`

Defines `isolated_sysforge_home`, which redirects SysForge side effects into a temporary directory through `SYSFORGE_HOME`.

---

## Module Dependency Graph

```text
sysforge.__main__
  └── sysforge.briefing.briefing.app

sysforge.briefing.briefing
  ├── typer
  ├── zoneinfo.ZoneInfo
  ├── sysforge.common
  │     ├── load_json_file
  │     ├── write_json_file
  │     ├── write_text_file
  │     ├── format_duration
  │     └── print_error
  ├── sysforge.logging_utils.get_logger
  ├── sysforge.shared_config
  │     ├── deep_merge
  │     └── load_shared_config
  └── sysforge.sysforge_paths
        ├── ensure_home_layout
        ├── get_briefing_data_dir
        ├── get_briefing_history_file
        └── get_briefings_dir
```

The dependency direction is important. The briefing app depends on shared SysForge utilities. Shared utilities do not depend on the briefing app.

---

## Core Algorithms & Logic

### 1. Config Loading and Normalization

`load_briefing_config()` starts with shared SysForge config and package briefing defaults. It can also merge an explicit `--briefing-config` file.

The effective config is normalized by `normalize_briefing_config()`:

1. Unknown briefing-specific keys are ignored and logged.
2. Timezone is validated through `ZoneInfo`.
3. Temperature unit is normalized to `F` or `C`; invalid values fall back to `F`.
4. data file settings are converted to strings.
5. `output_dir` is converted to a string when provided.

The user name and timezone can come from shared SysForge config. This means the briefing app participates in the larger toolkit’s user-profile behavior rather than owning a completely separate identity system.

### 2. Mock Data Loading

`load_mock_data()` resolves three data filenames:

- weather file,
- quotes file,
- calendar file.

It loads those JSON files from the selected data directory and then normalizes their shapes.

Weather is normalized to:

```python
{
    "default": dict,
    "days": dict,
}
```

Quotes are normalized to a list of strings.

Calendar items are normalized to a list of dictionaries with string `date`, `time`, and `title`, skipping malformed rows and rows without `date`.

### 3. Date and Greeting Selection

`generate_briefing()` creates a timezone-aware `now` using the configured timezone and `_zoned_now()`.

The date key is:

```python
day_key = now.date().isoformat()
```

`greeting_for_hour()` selects:

- “Good morning” before noon,
- “Good afternoon” before 6 PM,
- “Good evening” otherwise.

### 4. Weather Selection

`pick_weather()` checks whether a date-specific weather record exists under `weather["days"][day_key]`. If not, it falls back to `weather["default"]`.

Temperature values are formatted by `_format_temperature_value()`.

Important behavior:

- `None` and `"n/a"` render as `n/a`.
- numeric values are interpreted as Fahrenheit input.
- when the configured unit is Celsius, Fahrenheit is converted to Celsius.
- non-numeric strings are sanitized and rendered as text.

### 5. Quote Selection

`pick_quote()` uses `random.choice()` when quotes are available. It sanitizes the selected quote with `_sanitize_quote_text()`.

Sanitization behavior:

- normalizes CRLF/CR to LF,
- preserves paragraph breaks,
- removes non-printable characters,
- collapses internal whitespace within paragraphs,
- returns a fallback message when there are no usable quotes.

### 6. Calendar Selection

`calendar_items_for_day()` filters normalized calendar items to the current day and sorts them by the `time` field.

This supports predictable output ordering even when the input file is not already sorted.

### 7. System Snapshot

`get_system_snapshot()` collects:

- operating system string,
- Python version,
- uptime,
- free disk bytes,
- disk root used for disk measurement.

It attempts to load `psutil` dynamically. If `psutil` is unavailable, uptime becomes `0h 00m` instead of failing the whole command.

Disk usage is collected with `shutil.disk_usage()`. `_resolve_disk_usage_root()` walks upward from the intended output directory until it finds an existing directory, reducing failures when a configured output directory has not been created yet.

### 8. Rendering

The app has two renderer functions.

`build_text_briefing()` produces plain text with headings such as:

```text
Weather
Quote
Today's calendar
System snapshot
```

`build_markdown_briefing()` produces Markdown with headings such as:

```markdown
## Weather
## Quote
## Today's calendar
## System snapshot
```

Both renderers accept the same normalized input set. Optional sections are skipped by passing `None` for weather, quote, or calendar items.

### 9. File Writing

`generate_briefing()` writes to:

```text
briefing_YYYY-MM-DD.txt
```

or:

```text
briefing_YYYY-MM-DD.md
```

The output directory comes from config `output_dir` if set; otherwise it defaults to the SysForge briefing directory under SysForge home.

### 10. History Append

`append_briefing_history()` loads `briefing_history.json`, appends a record, and writes it back atomically.

A history record contains:

```json
{
  "timestamp": "...",
  "output_file": "...",
  "format": "text|markdown"
}
```

---

## Data Structures

### Briefing Config

```json
{
  "name": "Princeton",
  "timezone": "America/Los_Angeles",
  "temperature_unit": "F",
  "weather_file": "weather.json",
  "quotes_file": "quotes.json",
  "calendar_file": "calendar.json",
  "output_dir": ""
}
```

### Weather Data

```json
{
  "default": {
    "temp": 63,
    "condition": "Partly cloudy",
    "high": 68,
    "low": 55
  },
  "days": {
    "YYYY-MM-DD": {
      "temp": 64,
      "condition": "Sunny with light clouds",
      "high": 70,
      "low": 54
    }
  }
}
```

### Quote Data

```json
[
  "Small steps still move the system forward.",
  "Consistency is often more powerful than intensity."
]
```

### Calendar Data

```json
[
  {
    "date": "2026-04-19",
    "time": "09:00",
    "title": "Review SysForge architecture notes"
  }
]
```

### System Snapshot

```python
{
    "os": str,
    "python_version": str,
    "uptime": str,
    "free_disk": int,
    "disk_root": str,
}
```

---

## State Management

The app is not stateless. It creates and updates files.

### Package Data State

Default mock inputs live under:

```text
sysforge/briefing/data/
```

These are read-only package defaults from the perspective of normal CLI operation.

### User State

By default, SysForge uses:

```text
~/.sysforge/
```

The briefing app writes under:

```text
~/.sysforge/briefings/
```

It also appends to:

```text
~/.sysforge/briefings/briefing_history.json
```

### Environment-Scoped State

`SYSFORGE_HOME` can redirect all SysForge data to a different directory. Tests use this to avoid writing into the developer’s real home folder.

`SYSFORGE_CONFIG` can point shared config loading at a specific config file.

### In-Memory State

Generation is mostly functional within a single call. Intermediate values include:

- normalized config,
- loaded data payloads,
- selected weather,
- selected quote,
- selected calendar items,
- system snapshot,
- rendered content.

There is no long-running daemon or persistent Python object required.

---

## Error Handling Strategy

### CLI-Level Validation

The Typer callback validates `--format`. Invalid format prints a red error message and exits.

`generate_briefing()` also validates output format directly and raises `ValueError` when called with an invalid value. This makes the core function safer for tests and library-style use.

### Config Validation

`normalize_briefing_config()` validates timezone by trying to construct `ZoneInfo`. Invalid timezones raise `ValueError`.

Temperature unit is forgiving: invalid unit values fall back to Fahrenheit.

Unknown config keys are ignored and logged instead of failing the command.

### Missing Briefing Config

If `--briefing-config` points to a missing file, the CLI prints an error and exits.

### JSON Loading

`load_json_file()` raises JSON errors if existing files contain invalid JSON. Missing files return the provided defaults when a default is supplied.

### System Snapshot Degradation

If `psutil` is missing, uptime is reported as `0h 00m` instead of stopping the briefing.

If disk usage fails for the selected root, the app falls back to `Path.home()`.

### Data Sanitization

User-facing strings are sanitized before rendering to keep output one-line where needed and to remove non-printable characters.

---

## External Dependencies

The SysForge package declares these runtime dependencies:

| Dependency | Used By Briefing? | Purpose |
|---|---:|---|
| `typer>=0.12` | Yes | CLI framework. |
| `psutil>=5.9` | Optional path in briefing | Uptime calculation when available. |
| `rich>=13.7` | Indirect / project-wide | Shared CLI presentation dependency in SysForge. |
| `markdown>=3.6` | No direct briefing use | Used by the Markdown-to-HTML app in the same package. |
| `pygments>=2.18` | No direct briefing use | Used by documentation rendering features in the same package. |

Development dependencies include pytest, pytest-cov, Ruff, Mypy, and type stubs.

---

## Concurrency Model

The briefing generator is synchronous and single-process.

There is no threading, multiprocessing, async IO, file locking, or background scheduling.

Concurrency risks are limited to simultaneous CLI runs writing the same daily output file or history file. The history write uses the shared JSON atomic-write helper, but the read-modify-write append pattern is not a full multi-process transaction.

---

## Known Limitations

- No live weather provider.
- No live calendar provider.
- No email, Slack, or notification delivery.
- No scheduled execution.
- Same-day output file names are overwritten on repeated runs.
- Quote selection is random unless patched or disabled.
- History is append-only and not query-optimized.
- The briefing config is validated manually rather than with a full schema.
- Calendar times are sorted as strings, which works for zero-padded `HH:MM` values but is not a full temporal parser.
- Output templates are hardcoded in Python functions.
- The app is part of SysForge, so installing only the briefing tool without other SysForge dependencies is not the current package model.

---

## Design Patterns Used

### Facade

`generate_briefing()` acts as a facade over config loading, data loading, selection, snapshotting, rendering, writing, and history tracking.

### Pipeline

The app follows a pipeline:

```text
config → data normalization → section selection → system snapshot → rendering → file write → history append
```

### Adapter

`load_mock_data()` adapts JSON files into predictable in-memory structures.

### Strategy-like Rendering

The text and Markdown renderers are separate functions selected by `output_format`.

### Shared Infrastructure

Path, config, JSON, and logging behavior are delegated to SysForge-wide modules rather than copied into the briefing app.

---

# Interface Design Specification

## App 22 — Daily Briefing Generator / SysForge Briefing

**SysForge Group | Document 3 of 5**  
**Status: Accepted**

---

## Invocation Syntax

### Standalone Console Script

```bash
sysforge-briefing [OPTIONS]
```

### Unified SysForge CLI

```bash
sysforge briefing [OPTIONS]
```

### Python Module / Direct Package Use

The package exposes `sysforge.briefing.briefing.generate_briefing()` for direct Python calls, but the supported user interface is the CLI.

---

## Argument Reference Table

| Name | Type | Required | Default | Accepted Values | Description |
|---|---|---:|---|---|---|
| `--format` | string | No | Shared config `briefing.output_format`, usually `text` | `text`, `markdown` | Selects output format. Produces `.txt` or `.md`. |
| `--briefing-config` | path | No | None | Existing JSON file path | Optional briefing-specific config. Its parent directory is also used as the input data directory for weather, quotes, and calendar files. |
| `--no-weather` | flag | No | `False` | present / absent | Skips the weather section. |
| `--no-quote` | flag | No | `False` | present / absent | Skips the quote section. |
| `--no-calendar` | flag | No | `False` | present / absent | Skips the calendar section. |

The unified root command also supports root-level SysForge options such as `--verbose`, `--quiet`, `--config`, and `--version` before the `briefing` subcommand.

---

## Input Contract

### Shared Config Input

The app loads SysForge shared config from the default user config path, or from `SYSFORGE_CONFIG` when set. Relevant shared fields are:

```json
{
  "user": {
    "name": "Princeton",
    "timezone": "America/Los_Angeles"
  },
  "briefing": {
    "config_file": "",
    "output_format": "text"
  }
}
```

`user.name` and `user.timezone` can override briefing defaults.

### Briefing Config Input

A briefing config JSON object may include:

```json
{
  "name": "Princeton",
  "timezone": "America/Los_Angeles",
  "temperature_unit": "F",
  "weather_file": "weather.json",
  "quotes_file": "quotes.json",
  "calendar_file": "calendar.json",
  "output_dir": ""
}
```

Accepted keys:

- `name`
- `timezone`
- `temperature_unit`
- `weather_file`
- `quotes_file`
- `calendar_file`
- `output_dir`

Unknown keys are ignored and logged.

### Weather File Input

Expected shape:

```json
{
  "default": {
    "temp": 63,
    "condition": "Partly cloudy",
    "high": 68,
    "low": 55
  },
  "days": {
    "2026-04-19": {
      "temp": 64,
      "condition": "Sunny with light clouds",
      "high": 70,
      "low": 54
    }
  }
}
```

If malformed, the payload is normalized to empty default/day dictionaries.

### Quotes File Input

Expected shape:

```json
[
  "Small steps still move the system forward.",
  "Consistency is often more powerful than intensity."
]
```

Non-list payloads normalize to an empty quote list.

### Calendar File Input

Expected shape:

```json
[
  {
    "date": "2026-04-19",
    "time": "09:00",
    "title": "Review SysForge architecture notes"
  }
]
```

Rows without `date` are skipped. Missing `time` becomes an empty string. Missing `title` becomes `Untitled`.

---

## Output Contract

### Terminal Output

On success, the CLI prints:

```text
Briefing written to <path>
```

### File Output

For text output:

```text
briefing_YYYY-MM-DD.txt
```

For Markdown output:

```text
briefing_YYYY-MM-DD.md
```

Default output directory:

```text
~/.sysforge/briefings/
```

When config `output_dir` is set, that directory is used instead.

### History Output

The app appends a JSON object to:

```text
~/.sysforge/briefings/briefing_history.json
```

Each record includes:

- timestamp,
- output file path,
- format.

---

## Exit Code Reference

| Exit Code | Meaning |
|---:|---|
| `0` | Briefing generated successfully. |
| `1` | CLI validation or app validation failure, such as invalid format, invalid timezone, or missing explicit briefing config. |
| Typer-generated nonzero | Typer may return nonzero status for malformed command-line usage. |

---

## Error Output Behavior

Errors are printed through the shared `print_error()` helper, which uses Typer styling and writes to stderr.

Examples:

```text
--format must be text or markdown.
```

```text
Invalid briefing timezone: 'Not/A/Zone'
```

```text
Briefing config not found: ./missing.json
```

---

## Environment Variables

| Variable | Purpose |
|---|---|
| `SYSFORGE_HOME` | Overrides the default `~/.sysforge` home directory. Useful for testing and isolated runs. |
| `SYSFORGE_CONFIG` | Points shared config loading at a specific config file. |
| `SYSFORGE_VERBOSE` | Enables more verbose logging when set by the root CLI. |
| `SYSFORGE_QUIET` | Reduces console logging when set by the root CLI. |

---

## Configuration Files

### Shared Config

Default package file:

```text
sysforge/data/sysforge.json
```

Default user copy:

```text
~/.sysforge/sysforge.json
```

### Briefing Defaults

Package file:

```text
sysforge/briefing/data/briefing_config.json
```

### Optional User Briefing Config

Supplied by:

```bash
sysforge-briefing --briefing-config ./profile/briefing_config.json
```

When this is used, weather, quotes, and calendar filenames are resolved relative to the config file’s parent directory.

---

## Side Effects

The app may:

- create the SysForge home layout,
- create `~/.sysforge/briefings/`,
- write or overwrite a dated briefing file,
- append to `briefing_history.json`,
- create or update central log files under `~/.sysforge/logs/`,
- read shared and briefing-specific config files,
- read local JSON weather, quote, and calendar files.

It does not:

- call network APIs,
- send email,
- create background tasks,
- modify source package data files,
- persist secrets.

---

## Usage Examples

### Basic Example

```bash
sysforge-briefing
```

Expected result:

```text
Briefing written to /Users/<you>/.sysforge/briefings/briefing_2026-05-08.txt
```

### Markdown Output

```bash
sysforge-briefing --format markdown
```

Expected result:

```text
Briefing written to /Users/<you>/.sysforge/briefings/briefing_2026-05-08.md
```

### Skip Quote Section

```bash
sysforge-briefing --format markdown --no-quote
```

### Skip Weather and Calendar

```bash
sysforge-briefing --no-weather --no-calendar
```

### Use a Custom Briefing Profile

```bash
sysforge-briefing --briefing-config ./daily-profile/briefing_config.json --format markdown
```

The app expects the profile directory to contain any filenames referenced by the config, such as:

```text
daily-profile/weather.json
daily-profile/quotes.json
daily-profile/calendar.json
```

### Use the Unified CLI

```bash
sysforge briefing --format markdown --no-quote
```

### Isolated Local Run

```bash
SYSFORGE_HOME=.sysforge-dev sysforge-briefing --format markdown
```

### Intentional Failure: Invalid Format

```bash
sysforge-briefing --format pdf
```

Expected result:

```text
--format must be text or markdown.
```

### Intentional Failure: Missing Config

```bash
sysforge-briefing --briefing-config ./missing.json
```

Expected result:

```text
Briefing config not found: missing.json
```

---

# Runbook

## App 22 — Daily Briefing Generator / SysForge Briefing

**SysForge Group | Document 4 of 5**  
**Status: Accepted**

---

## Prerequisites

- Python 3.11 or newer.
- A shell with access to the project root.
- Ability to install Python packages.
- Runtime dependencies from SysForge package metadata.
- On Windows, `tzdata` may be needed if `zoneinfo` cannot find the configured timezone.

---

## Installation Procedure

### Development Install

From the SysForge repository root:

```bash
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows
python -m pip install -e ".[dev]"
```

### Runtime Install

```bash
python -m pip install -e .
```

### Requirements File Install

```bash
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps
```

---

## Configuration Steps

### 1. Choose a SysForge Home Directory

Default:

```text
~/.sysforge/
```

For a local sandbox:

```bash
export SYSFORGE_HOME=.sysforge-dev
```

Windows PowerShell:

```powershell
$env:SYSFORGE_HOME = ".sysforge-dev"
```

### 2. Review Shared Config

On first run, SysForge copies default config into:

```text
~/.sysforge/sysforge.json
```

Relevant defaults:

```json
{
  "user": {
    "name": "Princeton",
    "timezone": "America/Los_Angeles"
  },
  "briefing": {
    "config_file": "",
    "output_format": "text"
  }
}
```

### 3. Optional Briefing-Specific Config

Create a profile directory:

```text
briefing-profile/
  briefing_config.json
  weather.json
  quotes.json
  calendar.json
```

Example `briefing_config.json`:

```json
{
  "timezone": "America/Los_Angeles",
  "temperature_unit": "F",
  "weather_file": "weather.json",
  "quotes_file": "quotes.json",
  "calendar_file": "calendar.json",
  "output_dir": "./briefings_out"
}
```

Run:

```bash
sysforge-briefing --briefing-config briefing-profile/briefing_config.json
```

---

## Standard Operating Procedures

### Generate Default Text Briefing

```bash
sysforge-briefing
```

### Generate Markdown Briefing

```bash
sysforge-briefing --format markdown
```

### Generate Briefing Without Weather

```bash
sysforge-briefing --no-weather
```

### Generate Briefing Without Quote

```bash
sysforge-briefing --no-quote
```

### Generate Briefing Without Calendar

```bash
sysforge-briefing --no-calendar
```

### Generate Through Unified CLI

```bash
sysforge briefing --format markdown
```

### Inspect Output Directory

```bash
ls ~/.sysforge/briefings
```

### Inspect History

```bash
cat ~/.sysforge/briefings/briefing_history.json
```

---

## Health Checks

### CLI Import Check

```bash
python -c "from sysforge.briefing.briefing import generate_briefing; print('ok')"
```

### Console Script Check

```bash
sysforge-briefing --help
```

### Unified CLI Check

```bash
sysforge briefing --help
```

### Isolated End-to-End Check

```bash
SYSFORGE_HOME=.sysforge-dev sysforge-briefing --format markdown --no-weather --no-calendar
```

Then confirm:

```bash
ls .sysforge-dev/briefings
```

### Test Suite Check

```bash
python -m pytest tests/test_briefing.py
```

Full project verification:

```bash
python -m ruff format --check .
python -m ruff check .
python -m mypy
python -m compileall -q .
python -m pytest
```

---

## Expected Output Samples

### Plain Text Shape

```text
Good morning, Princeton

Date: Friday, 2026-05-08
Time: 09:15 AM PDT

Weather
  Condition: Partly cloudy
  Current: 63 °F
  High / Low: 68 / 55 °F

Quote
  Small steps still move the system forward.

Today's calendar
  No calendar items today.

System snapshot
  OS: macOS-...
  Python: 3.11.9
  Uptime: 12h 04m
  Free disk (/Users/princeton): 150.21 GB
```

### Markdown Shape

```markdown
# Good morning, Princeton

- Date: Friday, 2026-05-08
- Time: 09:15 AM PDT

## Weather
- Condition: Partly cloudy
- Current: 63 °F
- High / Low: 68 / 55 °F

## Quote
> Small steps still move the system forward.

## Today's calendar
- No calendar items today.

## System snapshot
- OS: macOS-...
- Python: 3.11.9
- Uptime: 12h 04m
- Free disk (/Users/princeton): 150.21 GB
```

### Terminal Success

```text
Briefing written to /Users/princeton/.sysforge/briefings/briefing_2026-05-08.md
```

---

## Known Failure Modes

### Invalid Output Format

Symptom:

```text
--format must be text or markdown.
```

Cause: unsupported `--format` value.

Resolution:

```bash
sysforge-briefing --format text
sysforge-briefing --format markdown
```

### Missing Explicit Briefing Config

Symptom:

```text
Briefing config not found: ./profile/briefing_config.json
```

Cause: `--briefing-config` path does not exist.

Resolution: create the config file or correct the path.

### Invalid Timezone

Symptom:

```text
Invalid briefing timezone: 'Not/A/Zone'
```

Cause: timezone is not valid for `zoneinfo.ZoneInfo`.

Resolution: use a valid IANA timezone such as `UTC` or `America/Los_Angeles`.

### Invalid JSON

Symptom: JSON decoding error from the file loader.

Cause: malformed weather, quote, calendar, or config JSON.

Resolution:

```bash
python -m json.tool path/to/file.json
```

Fix the JSON and rerun.

### No Uptime Data

Symptom:

```text
Uptime: 0h 00m
```

Cause: `psutil` is unavailable.

Resolution: install SysForge runtime dependencies or accept degraded system snapshot behavior.

### Unexpected Empty Sections

Symptom: no weather values, no quote, or no calendar items.

Possible causes:

- section disabled with `--no-weather`, `--no-quote`, or `--no-calendar`,
- wrong data directory,
- malformed JSON normalized to empty data,
- date-specific calendar records do not match today’s date.

---

## Troubleshooting Decision Tree

```text
Briefing failed?
  |
  +-- Did the command print an invalid format error?
  |     +-- Use --format text or --format markdown.
  |
  +-- Did it complain about briefing config not found?
  |     +-- Check --briefing-config path.
  |
  +-- Did it complain about timezone?
  |     +-- Replace timezone with a valid IANA timezone.
  |
  +-- Did it crash while loading JSON?
  |     +-- Run python -m json.tool on config/weather/quotes/calendar files.
  |
  +-- Did it write a file but content is missing sections?
  |     +-- Check --no-* flags and input data file names.
  |
  +-- Did it write to an unexpected location?
        +-- Check SYSFORGE_HOME and config output_dir.
```

---

## Dependency Failure Handling

### Typer Missing

The CLI will not import. Reinstall SysForge dependencies:

```bash
python -m pip install -e .
```

or:

```bash
python -m pip install -r requirements.txt
```

### psutil Missing

The app degrades gracefully for uptime. If full uptime is desired:

```bash
python -m pip install psutil
```

### zoneinfo Data Missing on Windows

Install timezone data:

```bash
python -m pip install tzdata
```

---

## Recovery Procedures

### Recover From Bad User Config

Move the broken file aside:

```bash
mv ~/.sysforge/sysforge.json ~/.sysforge/sysforge.json.bak
sysforge-briefing
```

SysForge can recreate the default config from package data.

### Recover From Bad Briefing History

If `briefing_history.json` is malformed:

```bash
mv ~/.sysforge/briefings/briefing_history.json ~/.sysforge/briefings/briefing_history.bad.json
sysforge-briefing
```

The app will create a new history list on the next successful generation path if the loader receives default behavior. If the malformed file exists and breaks JSON parsing, removing or repairing it is required.

### Recover From Wrong Output Directory

Check effective config:

- shared `~/.sysforge/sysforge.json`,
- explicit `--briefing-config`,
- `output_dir` in briefing config,
- `SYSFORGE_HOME`.

Then rerun with an explicit profile:

```bash
sysforge-briefing --briefing-config ./profile/briefing_config.json
```

---

## Logging Reference

The briefing app uses logger name:

```text
sysforge.briefing
```

Central log file:

```text
~/.sysforge/logs/sysforge.log
```

Root CLI flags can affect console logging:

```bash
sysforge --verbose briefing
sysforge --quiet briefing
```

`--verbose` sets `SYSFORGE_VERBOSE=1`. `--quiet` sets `SYSFORGE_QUIET=1`.

---

## Maintenance Notes

- Keep briefing data JSON small and human-editable.
- Use valid IANA timezones.
- Prefer zero-padded calendar times such as `09:00` so string sorting is correct.
- Treat weather/calendar files as mock data, not authoritative external integrations.
- When adding a new output format, add a renderer and update format validation.
- When adding new config keys, update `_ALLOWED_BRIEFING_CONFIG_KEYS` and tests.
- Keep filesystem side effects isolated in tests with `SYSFORGE_HOME`.

---

# Lessons Learned

## App 22 — Daily Briefing Generator / SysForge Briefing

**SysForge Group | Document 5 of 5**  
**Status: Accepted**

---

## Project Summary

The Daily Briefing Generator turns a small set of local inputs into a daily briefing file. It reads user/profile settings, mock weather, quotes, calendar data, and system information, then produces either a text or Markdown file with a predictable name.

The important part of this project is not that it prints a greeting. The important part is that it works as a real sub-application inside SysForge. It shares path rules, config loading, logging, package metadata, root CLI wiring, and test isolation with the rest of the toolkit.

This app shows a shift from isolated scripts toward a coherent CLI product.

---

## Original Goals vs. Actual Outcome

### Original Goals

- Generate a daily briefing.
- Include weather, quote, calendar, and system information.
- Support text and Markdown output.
- Keep inputs simple and local.
- Make the tool usable through the command line.

### Actual Outcome

The final result does all of that, but it also became a good example of shared architecture. It is wired into SysForge as both a standalone command and a unified subcommand. It uses shared config and SysForge home paths instead of inventing its own per-app storage rules.

The output is simple, but the integration is meaningful.

---

## Technical Decisions That Paid Off

### Keeping Data Local

Using local JSON for weather, quotes, and calendar items kept the app testable. There are no network calls, credentials, rate limits, or API failures in the core path.

This made it easier to focus on normalization, formatting, config behavior, and file output.

### Using SysForge Shared Paths

The app does not decide on its own where state should live. It uses SysForge path helpers. This makes the app consistent with the rest of the monorepo.

The same `SYSFORGE_HOME` override works across SysForge apps, which is especially useful for tests and demos.

### Splitting Text and Markdown Rendering

Separate renderer functions kept output logic understandable. The app does not need a template engine yet. Direct Python formatting was enough for the scope.

### Normalizing Input Payloads

The normalization helpers make the app more forgiving. Bad weather payloads, bad quote payloads, and malformed calendar rows do not automatically destroy the whole generation flow.

### Testing Helper Functions

The tests cover smaller functions instead of only running the CLI. That makes issues easier to locate. Sanitization, date filtering, temperature conversion, config normalization, and Markdown wrapping are all individually testable.

---

## Technical Decisions That Created Debt

### Same-Day File Overwrite

The output filename is based only on date and format. Running the command twice in a day overwrites the previous file.

This is acceptable for a simple daily briefing, but future versions may need timestamps or a `--no-overwrite` flag.

### Random Quote Selection

Random quote selection is pleasant for a user, but it makes output less deterministic. Tests avoid this where needed, but a production version might want a seeded quote-of-the-day calculation.

### Hardcoded Renderers

The text and Markdown renderers are readable, but adding HTML, JSON, or PDF would increase duplication. At that point, a light template abstraction might become worthwhile.

### Calendar Time Sorting as Strings

Sorting calendar items by `time` string works when values use `HH:MM`. It is not a full time parser and could behave poorly with inconsistent input.

### Limited History Model

`briefing_history.json` is useful, but it is not queryable in a sophisticated way. It is also not a concurrency-safe database.

---

## What Was Harder Than Expected

### Config Precedence

The app has three possible layers of config:

1. package briefing defaults,
2. shared SysForge config,
3. optional briefing-specific config.

This is more realistic than a single JSON file, but it requires care. A user may expect `name` and `timezone` to come from one place, while the app intentionally lets shared config win for profile values.

### Filesystem Side Effects

A CLI that writes files needs careful test isolation. Without `SYSFORGE_HOME`, tests could accidentally write into a real home directory.

### Making Output Safe

Briefing text is user-facing. Sanitizing control characters and collapsing whitespace prevents weird config or JSON content from producing messy output.

### Optional System Data

System snapshot data is helpful, but platform details vary. The app had to avoid becoming fragile when disk paths do not exist or `psutil` is missing.

---

## What Was Easier Than Expected

### Typer Integration

Typer made the CLI callback concise. The options map cleanly to the app’s actual behavior.

### Markdown Rendering

The Markdown output did not require a full Markdown library because the app is producing Markdown text, not converting it to HTML.

### Shared SysForge Infrastructure

Once shared path, config, JSON, and logging modules existed, the briefing app could focus on its domain logic instead of rewriting utilities.

---

## Python-Specific Learnings

### `zoneinfo.ZoneInfo`

Using `ZoneInfo` gives timezone-aware briefing dates without pulling in a third-party dependency. It also forces config validation to happen early.

### `pathlib.Path`

`Path` makes config-driven file behavior easier to read, especially when resolving output directories and profile-relative data files.

### `textwrap.wrap`

Text wrapping is useful for both plain text quote indentation and Markdown blockquote formatting.

### `shutil.disk_usage`

The standard library can provide useful system information without needing a monitoring library for everything.

### Optional Imports

`load_psutil()` shows a good pattern for optional enhancement: try to import, degrade gracefully if missing.

### Type Hints With `Any`

JSON-heavy code often needs `Any`, but the app narrows shapes through normalization functions. That is better than letting raw JSON flow through all renderers unchecked.

---

## Architecture Insights

### Shared Infrastructure Matters

The app is small, but the architecture matters because it participates in SysForge. Shared paths and config make the tool feel like part of a suite instead of a random script.

### A Small Facade Can Keep a CLI Clean

`generate_briefing()` is the right boundary. The CLI collects options; the function performs the actual workflow. This makes tests easier and keeps CLI code from becoming the whole application.

### Local Data Can Still Exercise Real Design

Even without live APIs, the app handles real concerns:

- data shape validation,
- config merging,
- timezone-aware dates,
- output formats,
- filesystem writes,
- history tracking,
- logging.

That is enough to demonstrate architecture without overbuilding.

### Monorepo Apps Need Clear Boundaries

The briefing app imports shared utilities but does not reach into unrelated apps. That keeps the SysForge monorepo organized.

---

## Testing Gaps

The tests cover a strong set of helper functions and an end-to-end Markdown generation path. Remaining gaps include:

- direct CLI invocation through Typer runner,
- history behavior when the existing history file is corrupt,
- repeated same-day generation behavior,
- explicit shared config precedence tests,
- `--no-weather`, `--no-quote`, and `--no-calendar` integration tests,
- behavior when weather, quotes, or calendar files are missing,
- behavior when `psutil` is absent,
- concurrent generation attempts,
- Windows-specific timezone behavior.

These gaps are acceptable for the current scope but worth addressing if the app becomes a daily-use tool.

---

## Reusable Patterns Identified

### Normalize Before Rendering

Raw JSON should not be rendered directly. Normalize it first.

### Separate CLI From Workflow

Keep CLI parsing in the Typer callback and workflow logic in a callable function.

### Use Package Defaults, Then User Overrides

Package defaults make the app work immediately. User overrides make it personal.

### Use Environment Variables for Test Isolation

`SYSFORGE_HOME` is a simple but powerful way to avoid writing to real user state in tests.

### Graceful Degradation for Optional System Features

If uptime is unavailable, the briefing should still generate.

---

## If I Built This Again

I would keep the shared SysForge integration, but I would consider adding:

- a deterministic quote-of-the-day option,
- `--output` to override a single output file path,
- `--no-overwrite` to prevent replacing the same day’s briefing,
- a `preview` mode that prints the briefing without writing files,
- stricter calendar time parsing,
- schema validation for briefing config,
- live provider interfaces for weather/calendar as optional plugins,
- structured JSON output for automation,
- tests for all CLI flags using a Typer test runner.

---

## Open Questions

- Should repeated runs overwrite a daily file or create timestamped versions?
- Should quote selection be random or deterministic by date?
- Should the briefing app eventually support real APIs?
- Should history be queryable from the CLI?
- Should Markdown output be converted to HTML by piping into the SysForge Markdown builder?
- Should the app support scheduled generation, or should scheduling remain external to SysForge?
- Should config validation move to the SysForge config/schema system?

---

## Constitution Alignment

The app aligns well with the portfolio Constitution:

- It is appropriately scoped for a focused CLI app.
- It uses Python fundamentals, package structure, functions, filesystem IO, JSON parsing, and timezone-aware dates.
- It shows meaningful architecture through shared SysForge utilities.
- It avoids scope creep by using local data instead of live APIs.
- It includes verification through focused tests and end-to-end file generation.
- It documents trade-offs honestly, especially around mocked data, same-day overwrites, random quote selection, and limited history persistence.

The strongest engineering evidence is not complexity. It is the way the app fits into a larger toolkit without losing its own clear responsibility.
