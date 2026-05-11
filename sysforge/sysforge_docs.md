# Architecture Decision Record

## App 28 — SysForge Integrated CLI Toolkit

**SysForge Group | Document 1 of 5**  
**Status: Accepted**

## Title

Unify six standalone SysForge utility applications behind one Typer-based command surface and one daily reporting command.

## Date

2026-05-08

## Context

SysForge began as a collection of standalone command-line utilities: Folder Organizer, Markdown-to-HTML Generator, Daily Briefing Generator, Time Tracker, Configuration Manager, and System Health Monitor. Each app solves a different operations or productivity problem, but they all share similar needs:

- predictable command-line invocation,
- a shared home directory for user state,
- JSON-based persistence,
- a central logging model,
- shared configuration,
- consistent installation through one Python package,
- and a way to summarize activity across the toolkit.

The integrated SysForge app addresses that cross-cutting layer. Instead of forcing users to remember six unrelated entry points, the `sysforge` command acts as the unified command surface. It exposes subcommands for the individual apps and adds a dashboard-style `report` command that reads the files created by those apps and writes a daily report.

This app is different from the previous six SysForge utilities. It does not primarily perform one domain operation. Its job is orchestration. It imports the Typer applications owned by the subpackages, wires them into one parent Typer application, configures shared runtime behavior, validates global options, initializes the SysForge home layout, and delegates work to the correct subcommand.

The educational goal is to demonstrate package-level architecture: entry-point design, shared configuration, command composition, module boundaries, compatibility handling, and cross-application reporting.

## Decision Drivers

- **CLI consistency:** Users should be able to run both standalone tools and one integrated `sysforge` command.
- **Low ceremony:** The unified CLI should be thin, not a second implementation of every feature.
- **Single package identity:** SysForge should install as one project with multiple console scripts.
- **Shared operational state:** All apps should agree on `~/.sysforge` or `SYSFORGE_HOME`.
- **Centralized logging:** Global verbosity and quiet flags should influence all SysForge loggers.
- **Dashboard value:** The integrated command should do something useful beyond wrapping subcommands.
- **Maintainability:** New sub-apps should be attachable without rewriting existing app logic.
- **Learning value:** The app should show how a CLI suite can scale from single-purpose scripts into a package toolkit.

## Options Considered

### Option 1 — Keep only standalone console scripts

**Description:** Ship `sysforge-organizer`, `sysforge-mdhtml`, `sysforge-briefing`, `sysforge-time`, `sysforge-config`, and `sysforge-health`, but no top-level `sysforge` command.

**Pros**

- Very simple packaging.
- Each app remains isolated.
- No parent router or command composition needed.

**Cons**

- Poor toolkit experience.
- No single place for global `--config`, `--verbose`, or `--quiet`.
- No natural place for a daily dashboard/report command.
- Users must remember several command names.
- The package feels like unrelated utilities rather than one system.

**Decision:** Rejected.

### Option 2 — Merge every feature into one large CLI module

**Description:** Put all command handlers into `sysforge/__main__.py`.

**Pros**

- One file shows the whole command surface.
- No need to import sub-app Typer objects.
- Global state would be easy to see.

**Cons**

- Creates a large, fragile module.
- Breaks separation of concerns.
- Makes individual apps harder to test.
- Increases merge conflicts as the suite grows.
- Re-implements work already done in subpackages.

**Decision:** Rejected.

### Option 3 — Use Typer sub-application composition

**Description:** Keep each utility in its own package, expose an `app` object from each, and attach those apps to the root `sysforge` Typer application with `add_typer()`.

**Pros**

- Preserves modularity.
- Keeps standalone entry points and unified entry point aligned.
- Lets the root command handle global concerns.
- Makes sub-app ownership clear.
- Scales naturally as new apps are added.

**Cons**

- Import-time failures in a sub-app can affect the unified CLI.
- The root command still needs to know every app it registers.
- Shared behavior must be coordinated through utilities rather than hidden globals.

**Decision:** Accepted.

### Option 4 — Implement the dashboard as a separate standalone script

**Description:** Create a separate command, such as `sysforge-report`, that only builds the daily report.

**Pros**

- Keeps the root CLI focused on routing.
- Dashboard can evolve independently.
- Simple mental model for reporting code.

**Cons**

- Adds another command name to remember.
- Hides the dashboard from the unified toolkit surface.
- Does not reinforce the root CLI as the central entry point.

**Decision:** Rejected.

### Option 5 — Implement the dashboard as `sysforge report`

**Description:** Add a first-class `report` command to the root CLI that reads shared app artifacts and writes a daily report.

**Pros**

- Makes the integrated command useful.
- Creates a cross-application feature that only the toolkit can provide.
- Keeps report generation close to the root command but in a separate module.
- Supports text, Markdown, and HTML output.

**Cons**

- Reporting depends on conventions from all sub-apps.
- Missing or malformed app data can affect the dashboard.
- As more apps are added, the report module can grow.

**Decision:** Accepted.

## Decision

SysForge will be implemented as a single Python package with multiple console scripts. The root console script, `sysforge`, will use Typer to compose the six standalone sub-apps and expose a dashboard-style `report` command.

The root command will:

1. define a top-level Typer app,
2. register global options for verbosity, quiet mode, shared config, and version,
3. initialize the SysForge home layout,
4. initialize shared loggers,
5. register sub-apps with names such as `organize`, `docs`, `briefing`, `time`, `config`, and `health`,
6. expose a root `report` command,
7. delegate report content generation to `sysforge.reporting.build_daily_report()`.

The `reporting.py` module will collect activity from known SysForge state files:

- organizer JSON logs,
- Markdown build history,
- briefing history,
- time tracker timesheet,
- latest health monitor snapshot.

It will render the report as text, Markdown, or HTML and write the output under the reports directory in the SysForge home.

## Rationale

A CLI toolkit needs two architectural layers. The first layer is the domain layer: each utility performs its own focused job. The second layer is the orchestration layer: it presents the tools as one coherent package. SysForge’s integrated command is that second layer.

Typer sub-application composition fits this problem well. It allows each utility to keep its own command definitions while the root command serves as a router. This avoids duplicating every option and command in the root module. It also preserves standalone scripts for users who prefer direct commands.

The `report` command is the strongest justification for the integrated app. A single sub-app cannot summarize the whole toolkit; only the integrated command has a reason to read across all app histories. By keeping report rendering in `reporting.py`, the root command remains clean and the dashboard logic remains testable.

Shared configuration and shared paths reduce accidental divergence. Every tool can write to its own area under the same SysForge home, while the report command knows where to look. The use of `SYSFORGE_HOME` gives a practical test and development override.

## Trade-offs Accepted

### Root imports can expose sub-app failures early

Because the root CLI imports each sub-app’s Typer app, a syntax error or missing runtime dependency in one sub-app can affect the root command. This is acceptable for this project because the package is intended to be installed and tested as a unit.

### Report logic depends on file conventions

The dashboard reads files created by other apps. If an app changes its log format, the report module may need an update. This coupling is intentional but should be kept visible.

### Dashboard is a daily summary, not a full analytics engine

The report command summarizes current-day activity and latest health data. It does not implement long-term analytics, charts, filtering by arbitrary date ranges, or a persistent index.

### Global flags use environment variables internally

The root command maps `--verbose`, `--quiet`, and `--config` into environment variables used by shared helpers. This is simple and effective, but it means command behavior depends partly on process environment.

### Compatibility shim adds advanced import behavior

The package installs a compatibility import hook so old `sysforge.markdown` imports continue to route to `sysforge.mdhtml`. This protects users during a rename but introduces a more advanced Python mechanism than most beginner CLI projects need.

## Consequences

### Positive Consequences

- Users can run one command, `sysforge`, to access the full toolkit.
- Standalone scripts remain available.
- The root CLI demonstrates scalable command composition.
- The report command provides cross-app value.
- Shared configuration, paths, and logging are centralized.
- The package has a stronger identity than a folder of scripts.
- The design supports future subcommands with minimal disruption.

### Negative Consequences

- The root command imports many modules, increasing startup coupling.
- The report command must understand several file formats.
- Adding new apps requires explicit root CLI registration.
- Shared state can become cluttered if not documented and maintained.
- Missing optional activity data must be handled gracefully.

## Superseded By

Not currently superseded.

Potential future replacements:

- a plugin registry that discovers subcommands dynamically,
- a web dashboard that reads the same state files,
- a richer reporting engine with date ranges and structured metrics,
- a separate `sysforge report` package if reporting grows beyond the root module.

---

# Technical Design Document

## App 28 — SysForge Integrated CLI Toolkit

**SysForge Group | Document 2 of 5**  
**Status: Accepted**

## Purpose & Scope

The SysForge integrated CLI toolkit provides one command surface for the full SysForge package. It wraps six standalone utilities and adds a daily report command.

In scope:

- expose the root `sysforge` command,
- expose `--version`,
- support global `--verbose`, `--quiet`, and `--config`,
- initialize the SysForge home directory,
- initialize logging for root and sub-app loggers,
- register six sub-app Typer applications,
- provide a dashboard-style `report` command,
- support report output in text, Markdown, and HTML,
- write reports under the shared reports directory,
- load shared configuration and state files.

Out of scope:

- re-implementing sub-app internals,
- interactive dashboard UI,
- remote synchronization,
- daemon/service mode,
- authentication or multi-user permissions,
- long-term analytics,
- automatic discovery of third-party plugins.

## System Context

SysForge is installed as one Python package. The package exposes multiple console scripts:

- `sysforge`
- `sysforge-organizer`
- `sysforge-mdhtml`
- `sysforge-briefing`
- `sysforge-time`
- `sysforge-config`
- `sysforge-health`

The integrated app is the `sysforge` script. It imports the same Typer app objects used by the standalone utilities and mounts them as subcommands. This keeps the root command consistent with the standalone commands.

The root app also owns the `report` command, which reads data from shared state locations:

```text
~/.sysforge/
  sysforge.json
  logs/
    sysforge.log
  organizer/
    logs/
      organizer_*.json
  docs/
    build_history.json
  briefings/
    briefing_history.json
  time/
    timesheet.json
  health/
    latest_snapshot.json
    health_log.jsonl
  reports/
    sysforge_report_YYYY-MM-DD.txt
    sysforge_report_YYYY-MM-DD.md
    sysforge_report_YYYY-MM-DD.html
```

The base directory can be overridden with `SYSFORGE_HOME`.

## Component Breakdown

### `sysforge/__main__.py`

Primary root CLI module.

Responsibilities:

- create the root Typer app,
- define global callback options,
- expose version callback,
- initialize shared home layout,
- initialize loggers,
- mount sub-apps,
- define the `report` command,
- call `build_daily_report()`.

Key design features:

- `app = typer.Typer(...)`
- `version_callback()`
- `root()` callback with global flags
- `report()` command
- `app.add_typer(...)` calls for all sub-apps
- `main()` entry point

### `sysforge/reporting.py`

Cross-app reporting module.

Responsibilities:

- load organizer activity for the current day,
- load Markdown build activity for the current day,
- load briefing activity for the current day,
- load time tracking activity for the current day,
- load latest health snapshot,
- render text report,
- render Markdown report,
- render HTML report,
- write report file to the reports directory.

Important functions:

- `_load_today_organizer_data(today)`
- `_load_today_docs_data(today)`
- `_load_today_briefing_data(today)`
- `_load_today_time_data(today)`
- `_load_health_data()`
- `_render_text(today, report_data)`
- `_render_markdown(today, report_data)`
- `_render_html(today, report_data)`
- `build_daily_report(output_format="text")`

### `sysforge/__init__.py`

Package identity module.

Responsibilities:

- define `__version__`,
- expose package metadata through `__all__`,
- install compatibility import shim for deprecated Markdown package path.

### `sysforge/_import_shims.py`

Compatibility module.

Responsibilities:

- provide a meta-path finder for deprecated `sysforge.markdown` imports,
- route old imports to `sysforge.mdhtml`,
- emit a `DeprecationWarning` once.

This module is not part of the user-facing CLI contract, but it is important for package migration safety.

### `sysforge/common.py`

Shared utility module.

Relevant responsibilities for integrated SysForge:

- JSON file reading,
- text file writing,
- human-readable byte sizes,
- duration formatting,
- typed CLI value parsing,
- common error printing through Typer,
- filesystem parent creation.

### `sysforge/sysforge_paths.py`

Shared path module.

Responsibilities:

- compute package root,
- compute SysForge home directory,
- honor `SYSFORGE_HOME`,
- expose state-file paths,
- expose report directory path,
- create home directory layout,
- seed user config from default config.

### `sysforge/shared_config.py`

Shared configuration module.

Responsibilities:

- load default package config,
- load user config or `SYSFORGE_CONFIG`,
- deep-merge user overrides over defaults,
- ensure layout before loading config.

### `sysforge/logging_utils.py`

Shared logging module.

Responsibilities:

- configure loggers,
- write to central `sysforge.log`,
- adjust console log level using `SYSFORGE_VERBOSE` and `SYSFORGE_QUIET`,
- prevent duplicate logger setup.

### Sub-app packages

Mounted into the root Typer app:

- `sysforge.organizer.organizer`
- `sysforge.mdhtml.markdown`
- `sysforge.briefing.briefing`
- `sysforge.timetracker.timetracker`
- `sysforge.config.config`
- `sysforge.monitor.monitor`

The root app does not duplicate their logic. It imports their `app` objects and attaches them under root command names.

## Module Dependency Graph

```text
pyproject.toml
  └── console script: sysforge = sysforge.__main__:main

sysforge.__main__
  ├── sysforge.__version__
  ├── sysforge.logging_utils.get_logger
  ├── sysforge.shared_config.load_shared_config
  ├── sysforge.sysforge_paths.ensure_home_layout
  ├── sysforge.reporting.build_daily_report
  ├── sysforge.organizer.organizer.app
  ├── sysforge.mdhtml.markdown.app
  ├── sysforge.briefing.briefing.app
  ├── sysforge.timetracker.timetracker.app
  ├── sysforge.config.config.app
  └── sysforge.monitor.monitor.app

sysforge.reporting
  ├── markdown
  ├── sysforge.common
  ├── sysforge.shared_config
  └── sysforge.sysforge_paths

sysforge.shared_config
  ├── os.environ
  ├── sysforge.common.load_json_file
  └── sysforge.sysforge_paths

sysforge.logging_utils
  ├── logging
  ├── os.environ
  └── sysforge.sysforge_paths
```

## Core Algorithms & Logic

## Root CLI Startup Flow

```text
user runs sysforge ...
  ↓
pyproject console script calls sysforge.__main__:main
  ↓
Typer parses root command
  ↓
root callback handles global options
  ↓
validate --verbose/--quiet conflict
  ↓
set or clear SYSFORGE_VERBOSE / SYSFORGE_QUIET
  ↓
set SYSFORGE_CONFIG if --config was provided
  ↓
ensure ~/.sysforge layout exists
  ↓
initialize known loggers
  ↓
dispatch to selected subcommand
```

The root callback is invoked before subcommands. This gives every sub-app a consistent environment.

## Version Flow

```text
sysforge --version
  ↓
version_callback(True)
  ↓
print __version__
  ↓
raise typer.Exit()
```

The version is defined in `sysforge/__init__.py`.

## Report Command Flow

```text
sysforge report --format markdown
  ↓
load shared config
  ↓
choose output format
  ↓
validate format is text, markdown, or html
  ↓
build_daily_report(chosen_format)
  ↓
load today's organizer data
  ↓
load today's docs build data
  ↓
load today's briefing data
  ↓
load today's time data
  ↓
load latest health snapshot
  ↓
render selected format
  ↓
write report under ~/.sysforge/reports/
  ↓
print report body
  ↓
print saved path
```

## Organizer Data Aggregation

The report module scans organizer JSON logs. It includes only logs whose timestamp starts with the current date. For those logs, it accumulates:

- number of runs,
- moved files,
- skipped files,
- errors,
- total bytes processed.

This is a lightweight event-log aggregation model. It does not need a database because organizer runs already create structured JSON files.

## Documentation Build Aggregation

The report module reads `build_history.json` from the docs directory. It filters entries for the current date and sums `files_built`.

## Briefing Aggregation

The report module reads `briefing_history.json`. It counts current-day runs and reports the latest output file for the day.

## Time Tracking Aggregation

The report module reads `timesheet.json`. It includes entries whose `start_time` begins with the current date. It sums:

- `duration_seconds`,
- `billable_total`.

It also reports the active task name if an active timer exists.

## Health Snapshot Aggregation

The report module reads `latest_snapshot.json`. Unlike the other sections, this is not filtered by today. It reports the latest known health state:

- CPU percent,
- memory percent,
- disk count,
- process count,
- overall status.

If no snapshot exists, the report displays `"No health data yet"`.

## Rendering Strategy

The report module has three renderers:

### Text Renderer

Produces plain terminal-friendly output.

### Markdown Renderer

Produces headings and bullet lists.

### HTML Renderer

Uses Markdown rendering first, then wraps the generated HTML body in a basic complete HTML document with inline CSS.

This approach avoids maintaining separate HTML content logic for every report section.

## Data Structures

## Root CLI Configuration

The root callback uses simple option values:

```python
verbose: bool
quiet: bool
config: Path | None
version: bool
```

These values affect environment variables and shared config loading.

## Report Data Shape

The report module builds one nested dictionary:

```python
{
    "organizer": {
        "runs": int,
        "moved": int,
        "skipped": int,
        "errors": int,
        "bytes": int,
    },
    "docs": {
        "runs": int,
        "files_built": int,
    },
    "briefing": {
        "runs": int,
        "latest_file": str,
    },
    "time": {
        "duration": str,
        "billable_total": float,
        "active_task": str | None,
    },
    "health": {
        "cpu_percent": float | None,
        "memory_percent": float | None,
        "disk_count": int,
        "process_count": int | None,
        "status": str,
    },
}
```

This shape is intentionally simple because it feeds three renderers.

## Shared Config Shape

The default config includes sections for:

- user,
- organizer,
- markdown,
- briefing,
- time,
- health,
- report.

The integrated app mainly reads the `report.default_format` value and uses the rest indirectly through sub-apps.

## Shared Directory Layout

`sysforge_paths.py` provides a function for every important location rather than scattering path strings throughout modules.

Examples:

- `get_home_dir()`
- `get_user_config_path()`
- `get_reports_dir()`
- `get_timesheet_file()`
- `get_latest_health_file()`
- `get_docs_history_file()`

## State Management

The root CLI itself is mostly stateless. It uses environment variables and path initialization as process-level setup.

Persistent state lives in the shared home directory:

- config file,
- logs,
- run histories,
- timesheet,
- health snapshot,
- reports.

The dashboard does not mutate sub-app state. It only reads it and writes a report file.

State ownership:

| State | Owner | Reader |
|---|---|---|
| Organizer logs | Folder Organizer | Reporting |
| Docs build history | Markdown-to-HTML Generator | Reporting |
| Briefing history | Daily Briefing Generator | Reporting |
| Timesheet | Time Tracker | Reporting |
| Latest health snapshot | System Health Monitor | Reporting |
| Shared config | Shared config module | Root CLI, reporting, sub-apps |
| Central log | Logging utility | All SysForge apps |

## Error Handling Strategy

## Root CLI Errors

The root callback explicitly handles only one validation rule:

- `--verbose` and `--quiet` cannot both be selected.

If both flags are present, the CLI prints an error and exits with code 1.

The `report` command validates output format:

- accepted values: `text`, `markdown`, `html`.

Invalid format exits with code 1.

## Subcommand Errors

Subcommands own their own validation and error handling. The root app does not catch and rewrite every sub-app exception. This preserves each utility’s existing behavior.

## Missing Report Input Files

The reporting module uses default values when history files do not exist. This lets a fresh SysForge installation still generate a report.

Examples:

- no organizer logs means zero runs,
- no docs history means zero builds,
- no briefing history means no briefing today,
- no timesheet means zero time,
- no health snapshot means "No health data yet."

## Malformed Report Input Files

Malformed JSON can still raise errors because `load_json_file()` uses `json.load()`. The report command is resilient to missing files, but not designed as a full corruption-recovery tool.

This is an accepted limitation. Corrupted files should be fixed by the owning app or by user recovery procedures.

## Logging

The root CLI initializes loggers for all known SysForge app names. The logging utility:

- writes DEBUG-level logs to the central log file,
- writes console logs according to current verbosity settings,
- avoids duplicate handler setup.

## External Dependencies

Runtime dependencies are declared in package metadata and requirements.

| Dependency | Used For |
|---|---|
| `typer>=0.12` | CLI framework |
| `markdown>=3.6` | HTML report rendering and Markdown builder |
| `pygments>=2.18` | Code highlighting in Markdown builder |
| `psutil>=5.9` | System health monitor |
| `rich>=13.7` | Health monitor table rendering |

The integrated CLI depends directly on Typer. The dashboard HTML renderer depends on Markdown. Other dependencies are imported through mounted sub-apps.

Development dependencies include pytest, pytest-cov, Ruff, Mypy, and typing stubs.

## Concurrency Model

SysForge uses a synchronous command-line model.

There is no threading, multiprocessing, async IO, background scheduler, or daemon process in the integrated app.

Concurrency considerations:

- two SysForge processes can write to shared state at the same time,
- report generation can read while a sub-app is writing,
- no file locking is implemented,
- atomic writes exist in some shared helpers and sub-apps, but not all report input files are transactionally coordinated.

For the portfolio scope, this is acceptable. The app is intended for local CLI usage, not multi-user concurrent operation.

## Known Limitations

- The root CLI imports every sub-app at startup.
- The report command is tied to known file names and schemas.
- Report date is always today; arbitrary historical report dates are not supported.
- Health data is latest snapshot, not necessarily today.
- Report rendering is intentionally simple.
- Corrupted JSON files can still fail report generation.
- There is no plugin discovery.
- Global config is process/environment based, not an explicit object passed everywhere.
- The root app does not provide a GUI or long-running dashboard server.
- Some sub-apps can be more deeply tested than the integrated root CLI itself.

## Design Patterns Used

### Command Router

The root Typer app routes commands to mounted sub-app Typer apps.

### Facade

`sysforge` is a facade over several utility applications.

### Shared Kernel

Common utilities, paths, logging, and config form a small shared kernel used across the package.

### Adapter

The compatibility import shim adapts old `sysforge.markdown` import paths to the new `sysforge.mdhtml` package.

### Aggregator

The report command aggregates structured artifacts from several sub-apps.

### Template Method Style Rendering

The report module builds one shared data dictionary and passes it through one of several renderer functions.

### File-Based Persistence

The system uses JSON, JSONL, Markdown, text, HTML, and CSV files rather than a database.

---

# Interface Design Specification

## App 28 — SysForge Integrated CLI Toolkit

**SysForge Group | Document 3 of 5**  
**Status: Accepted**

## Invocation Syntax

### Root CLI

```bash
sysforge [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS]
python -m sysforge [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS]
```

### Version

```bash
sysforge --version
```

### Dashboard Report

```bash
sysforge report [--format text|markdown|html]
```

### Mounted Subcommands

```bash
sysforge organize [OPTIONS]
sysforge docs [OPTIONS]
sysforge briefing [OPTIONS]
sysforge time COMMAND [OPTIONS]
sysforge config COMMAND [OPTIONS]
sysforge health [OPTIONS]
```

The root CLI also supports standalone scripts for each sub-app:

```bash
sysforge-organizer
sysforge-mdhtml
sysforge-briefing
sysforge-time
sysforge-config
sysforge-health
```

## Argument Reference Table — Global Options

| Name | Type | Required | Default | Accepted Values | Description |
|---|---:|---:|---:|---|---|
| `--verbose` | boolean flag | No | `False` | present/absent | Enables extra console logging by setting `SYSFORGE_VERBOSE=1`. |
| `--quiet` | boolean flag | No | `False` | present/absent | Reduces console logging by setting `SYSFORGE_QUIET=1`. |
| `--config` | path | No | `None` | filesystem path | Sets `SYSFORGE_CONFIG` for shared config loading. |
| `--version` | boolean flag | No | `False` | present/absent | Prints package version and exits. |
| `--help` | boolean flag | No | `False` | present/absent | Shows Typer-generated help. |

## Argument Reference Table — Root Commands

| Command | Type | Required | Default | Accepted Values | Description |
|---|---:|---:|---:|---|---|
| `organize` | subcommand group | No | N/A | Typer sub-app | Runs Folder Organizer through the unified CLI. |
| `docs` | subcommand group | No | N/A | Typer sub-app | Runs Markdown-to-HTML Generator through the unified CLI. |
| `briefing` | subcommand group | No | N/A | Typer sub-app | Runs Daily Briefing Generator through the unified CLI. |
| `time` | subcommand group | No | N/A | Typer sub-app | Runs Time Tracker through the unified CLI. |
| `config` | subcommand group | No | N/A | Typer sub-app | Runs Configuration Manager through the unified CLI. |
| `health` | subcommand group | No | N/A | Typer sub-app | Runs System Health Monitor through the unified CLI. |
| `report` | command | No | N/A | `--format` option | Builds a cross-app daily report. |

## Argument Reference Table — `sysforge report`

| Name | Type | Required | Default | Accepted Values | Description |
|---|---:|---:|---:|---|---|
| `--format` | string | No | config value or `text` | `text`, `markdown`, `html` | Selects report output format. |

## Input Contract

## Root CLI Input

The root CLI expects:

- a valid command name,
- valid global option combinations,
- a readable config file if `--config` is provided,
- installed package dependencies,
- a writable SysForge home directory.

## Report Command Input

The report command reads current state from the SysForge home directory. Missing files are acceptable and treated as empty data.

Expected files when present:

| File | Expected Shape |
|---|---|
| `organizer/logs/*.json` | JSON object with timestamp and summary |
| `docs/build_history.json` | JSON list of build history objects |
| `briefings/briefing_history.json` | JSON list of briefing history objects |
| `time/timesheet.json` | JSON object with entries and active timer |
| `health/latest_snapshot.json` | JSON object with latest system health fields |
| `sysforge.json` | JSON object with shared config |

## Output Contract

## Root CLI Output

Root output depends on command.

Examples:

- `--version` prints the version string.
- invalid global flags print an error.
- subcommands print their own output.
- `report` prints the report body and the saved path.

## Report Output

### Text

A plain text report beginning with:

```text
SysForge Daily Report - YYYY-MM-DD
```

### Markdown

A Markdown report beginning with:

```markdown
# SysForge Daily Report (YYYY-MM-DD)
```

### HTML

A complete HTML document with:

- doctype,
- `html` tag,
- `head`,
- inline CSS,
- `article.sysforge-report`,
- Markdown-rendered body.

## Exit Code Reference

| Scenario | Expected Exit Code |
|---|---:|
| `sysforge --version` | 0 |
| valid subcommand | 0 if subcommand succeeds |
| valid report generation | 0 |
| `--verbose` and `--quiet` used together | 1 |
| invalid report format | 1 |
| subcommand validation failure | controlled by subcommand |
| unhandled corrupted JSON or IO failure | non-zero Python/Typer failure |

## Error Output Behavior

- Global option conflicts are printed to stderr using Typer styling.
- Invalid report formats are printed to stderr.
- Sub-app error behavior is owned by each mounted app.
- Missing report data is not treated as an error.
- Corrupted JSON may raise through shared JSON loading.

## Environment Variables

| Variable | Purpose |
|---|---|
| `SYSFORGE_HOME` | Overrides the default `~/.sysforge` home directory. |
| `SYSFORGE_CONFIG` | Overrides shared config path. Can be set by root `--config`. |
| `SYSFORGE_VERBOSE` | Enables verbose console logging. Can be set by root `--verbose`. |
| `SYSFORGE_QUIET` | Reduces console logging. Can be set by root `--quiet`. |

## Configuration Files

### Shared User Config

Default path:

```text
~/.sysforge/sysforge.json
```

Seeded from package default config on first layout initialization.

### Default Package Config

Stored inside package data:

```text
sysforge/data/sysforge.json
```

Relevant fields:

```json
{
  "user": {
    "name": "Princeton",
    "timezone": "America/Los_Angeles"
  },
  "organizer": {
    "rules_file": "",
    "default_conflict_strategy": "rename"
  },
  "markdown": {
    "theme": "light"
  },
  "briefing": {
    "config_file": "",
    "output_format": "text"
  },
  "time": {
    "project_rates": {
      "ClientX": 125,
      "Learning": 0,
      "Internal": 85
    }
  },
  "report": {
    "default_format": "text"
  }
}
```

## Side Effects

The integrated CLI may create or update:

```text
~/.sysforge/
~/.sysforge/sysforge.json
~/.sysforge/logs/sysforge.log
~/.sysforge/reports/sysforge_report_YYYY-MM-DD.txt
~/.sysforge/reports/sysforge_report_YYYY-MM-DD.md
~/.sysforge/reports/sysforge_report_YYYY-MM-DD.html
```

Mounted subcommands may create their own app-specific state.

## Usage Examples

## Basic Example — Show Version

```bash
sysforge --version
```

Expected behavior:

```text
0.2.0
```

## Basic Example — Run a Mounted Subcommand

```bash
sysforge health
```

Expected behavior:

- initializes shared layout,
- runs the health monitor Typer app,
- writes health state through the health app.

## Advanced Example — Build Markdown Site Through Unified CLI

```bash
sysforge docs build ./notes --output ./site --theme dark
```

Expected behavior:

- root callback handles shared setup,
- `docs` subcommand delegates to Markdown-to-HTML Generator,
- output files are created by the docs app.

## Advanced Example — Use Alternate SysForge Home

```bash
SYSFORGE_HOME=.sysforge-dev sysforge report --format markdown
```

Expected behavior:

- report reads from `.sysforge-dev`,
- report writes to `.sysforge-dev/reports/`.

## Advanced Example — Use Explicit Config

```bash
sysforge --config ./dev-sysforge.json report --format html
```

Expected behavior:

- root CLI sets `SYSFORGE_CONFIG`,
- shared config loading uses the provided file,
- report is rendered as HTML.

## Edge Case — Fresh Install Report

```bash
sysforge report
```

Expected behavior on a new install:

- creates home layout,
- reads empty defaults for missing histories,
- prints a valid report with zero activity,
- writes a report file.

## Intentional Failure — Conflicting Log Flags

```bash
sysforge --verbose --quiet report
```

Expected behavior:

```text
Choose either --verbose or --quiet, not both.
```

Exit code: 1.

## Intentional Failure — Invalid Report Format

```bash
sysforge report --format pdf
```

Expected behavior:

```text
--format must be text, markdown, or html.
```

Exit code: 1.

---

# Runbook

## App 28 — SysForge Integrated CLI Toolkit

**SysForge Group | Document 4 of 5**  
**Status: Accepted**

## Prerequisites

- Python 3.11 or newer.
- Local shell access.
- Write access to the selected SysForge home directory.
- Runtime dependencies installed:
  - Typer,
  - Markdown,
  - Pygments,
  - psutil,
  - Rich.
- For development:
  - pytest,
  - pytest-cov,
  - Ruff,
  - Mypy,
  - type stubs.

## Installation Procedure

## Editable Development Install

```bash
python -m pip install -e ".[dev]"
```

## Runtime Dependency Install Followed by Editable Package

```bash
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps
```

## Verify Console Scripts

```bash
sysforge --version
sysforge --help
sysforge report --format text
```

## Configuration Steps

## Use Default Home Directory

No action required.

Default:

```text
~/.sysforge
```

## Use Isolated Development Home

Linux/macOS:

```bash
export SYSFORGE_HOME=.sysforge-dev
```

Windows PowerShell:

```powershell
$env:SYSFORGE_HOME = ".sysforge-dev"
```

Windows Command Prompt:

```cmd
set SYSFORGE_HOME=.sysforge-dev
```

## Use Explicit Shared Config

```bash
sysforge --config ./sysforge-dev.json report
```

The config file should be a JSON object.

## Standard Operating Procedures

## SOP 1 — Run the Unified CLI Help

```bash
sysforge --help
```

Use this to verify the root command is installed and subcommands are registered.

## SOP 2 — Run a Sub-App Through the Root CLI

```bash
sysforge health
```

This confirms the root CLI can dispatch to a mounted sub-app.

## SOP 3 — Generate a Daily Text Report

```bash
sysforge report
```

or:

```bash
sysforge report --format text
```

Expected output:

- report printed to terminal,
- saved report file path printed after the body.

## SOP 4 — Generate a Markdown Report

```bash
sysforge report --format markdown
```

Expected file:

```text
~/.sysforge/reports/sysforge_report_YYYY-MM-DD.md
```

## SOP 5 — Generate an HTML Report

```bash
sysforge report --format html
```

Expected file:

```text
~/.sysforge/reports/sysforge_report_YYYY-MM-DD.html
```

## SOP 6 — Run Full Verification Suite

```bash
python -m ruff format --check .
python -m ruff check .
python -m mypy
python -m compileall -q .
python -m pytest
```

## Health Checks

## CLI Health

```bash
sysforge --version
```

Expected:

```text
0.2.0
```

## Root Command Health

```bash
sysforge --help
```

Expected:

- shows root help,
- includes subcommands,
- includes global options.

## Report Health

```bash
SYSFORGE_HOME=.sysforge-healthcheck sysforge report --format text
```

Expected:

- no crash on empty state,
- report saved under `.sysforge-healthcheck/reports`.

## Shared Layout Health

Check that directories exist:

```text
~/.sysforge/
~/.sysforge/logs/
~/.sysforge/reports/
```

## Logging Health

Check central log:

```text
~/.sysforge/logs/sysforge.log
```

It should exist after commands that initialize logging.

## Expected Output Samples

## Empty Text Report

```text
SysForge Daily Report - 2026-05-08

Files organized
  Runs: 0
  Moved: 0
  Skipped: 0
  Errors: 0
  Data touched: 0.0 B

Documentation builds
  Runs: 0
  HTML files built: 0

Briefings
  Runs today: 0
  Latest file: No briefing today

Time tracked
  Total today: 0h 00m
  Billable total: $0.00
  Active task: None

System health
  Status: No health data yet
  CPU: n/a
  Memory: n/a
  Processes: n/a
```

## Markdown Report Header

```markdown
# SysForge Daily Report (2026-05-08)
```

## Saved Report Message

```text
Saved report to /home/user/.sysforge/reports/sysforge_report_2026-05-08.txt
```

## Known Failure Modes

## Failure Mode 1 — `sysforge` Command Not Found

Cause:

- package not installed,
- virtual environment not activated,
- scripts directory not on PATH.

Recovery:

```bash
python -m pip install -e .
python -m sysforge --help
```

## Failure Mode 2 — Missing Runtime Dependency

Cause:

- requirements not installed,
- partial environment.

Recovery:

```bash
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps
```

## Failure Mode 3 — Conflicting Verbosity Flags

Command:

```bash
sysforge --verbose --quiet report
```

Cause:

- incompatible global options.

Recovery:

Use only one:

```bash
sysforge --verbose report
```

or:

```bash
sysforge --quiet report
```

## Failure Mode 4 — Invalid Report Format

Command:

```bash
sysforge report --format pdf
```

Recovery:

```bash
sysforge report --format text
sysforge report --format markdown
sysforge report --format html
```

## Failure Mode 5 — Corrupted JSON State File

Symptoms:

- report command crashes with JSON decode error.

Likely files:

- timesheet,
- build history,
- briefing history,
- organizer logs,
- latest health snapshot.

Recovery:

1. Identify the file from traceback.
2. Back up the file.
3. Validate or repair JSON.
4. Rerun the report command.

## Failure Mode 6 — Permission Denied in SysForge Home

Cause:

- home directory not writable,
- stale file permissions,
- protected location used as `SYSFORGE_HOME`.

Recovery:

```bash
SYSFORGE_HOME=.sysforge-dev sysforge report
```

If this works, fix permissions on the original home directory.

## Troubleshooting Decision Tree

```text
Start
 |
 |-- Does `sysforge --version` work?
 |      |-- No → reinstall package or activate virtual environment
 |      `-- Yes
 |
 |-- Does `sysforge --help` show subcommands?
 |      |-- No → inspect package install and import errors
 |      `-- Yes
 |
 |-- Does `sysforge report` run?
 |      |-- No
 |      |    |-- Invalid format? → use text/markdown/html
 |      |    |-- JSON error? → repair state file
 |      |    |-- Permission error? → check SYSFORGE_HOME
 |      |    `-- Dependency error? → reinstall requirements
 |      `-- Yes
 |
 |-- Is report missing expected data?
 |      |-- Organizer missing → run organizer first
 |      |-- Docs missing → run docs build first
 |      |-- Briefing missing → run briefing first
 |      |-- Time missing → add or stop time entries
 |      |-- Health missing → run health first
 |      `-- Data exists but date mismatch → report only includes today's activity
```

## Dependency Failure Handling

## Typer Failure

Impact:

- all CLI commands fail.

Recovery:

```bash
python -m pip install "typer>=0.12"
```

## Markdown Failure

Impact:

- HTML report rendering can fail.

Recovery:

```bash
python -m pip install "markdown>=3.6"
```

## psutil Failure

Impact:

- health subcommand fails,
- report can still run if no health command is invoked, but latest health may be absent.

Recovery:

```bash
python -m pip install "psutil>=5.9"
```

## Rich Failure

Impact:

- health rendering may fall back or fail depending on health code path.

Recovery:

```bash
python -m pip install "rich>=13.7"
```

## Recovery Procedures

## Recover from Bad User Config

1. Move current config aside:

```bash
mv ~/.sysforge/sysforge.json ~/.sysforge/sysforge.json.bak
```

2. Re-run:

```bash
sysforge report
```

3. SysForge layout initialization should reseed default config if package default exists.

## Recover from Bad Report Output

1. Delete generated report file.
2. Fix source state data.
3. Regenerate:

```bash
sysforge report --format text
```

## Recover from Broken Home Directory During Testing

Use a clean home:

```bash
SYSFORGE_HOME=.sysforge-clean sysforge report
```

## Recover from Sub-App Import Failure

Because root CLI imports sub-apps at startup, a broken sub-app can affect the whole root command.

Procedure:

1. Run Python import check:

```bash
python -m compileall -q sysforge
```

2. Run tests:

```bash
python -m pytest
```

3. Fix the broken sub-app module.
4. Re-run:

```bash
sysforge --help
```

## Logging Reference

## Central Log File

```text
~/.sysforge/logs/sysforge.log
```

## Verbose Logging

```bash
sysforge --verbose report
```

## Quiet Logging

```bash
sysforge --quiet report
```

## Logger Names Initialized by Root CLI

- `sysforge`
- `sysforge.organizer`
- `sysforge.mdhtml`
- `sysforge.briefing`
- `sysforge.timetracker`
- `sysforge.config`
- `sysforge.monitor`

## Maintenance Notes

- Keep root `app.add_typer()` registrations aligned with package scripts.
- Add new apps to the root CLI intentionally.
- Update `reporting.py` whenever a sub-app state file format changes.
- Keep shared path functions authoritative; do not hard-code `~/.sysforge` in new modules.
- Keep package version in sync with release metadata.
- Maintain tests for report generation because report logic crosses app boundaries.
- Keep compatibility shims documented and eventually remove them when no longer needed.
- Avoid expanding `__main__.py` into a large business-logic module.

---

# Lessons Learned

## App 28 — SysForge Integrated CLI Toolkit

**SysForge Group | Document 5 of 5**  
**Status: Accepted**

## Project Summary

The integrated SysForge CLI turns a set of standalone utilities into one toolkit. It provides the `sysforge` command, registers six sub-apps, applies global runtime settings, initializes shared state, and generates a daily report from the data those sub-apps produce.

This app is the architectural capstone of the SysForge group. The previous utilities prove individual command-line and persistence skills. App 28 proves package composition skills.

## Original Goals vs. Actual Outcome

## Original Goals

- Bundle six utilities behind one command.
- Keep standalone commands available.
- Provide shared config and state conventions.
- Add a dashboard-style summary command.
- Preserve clean module separation.
- Make the project feel like a real developer toolkit.

## Actual Outcome

The final design meets the main goals. The root CLI is thin and uses Typer composition rather than duplicating subcommand logic. The `report` command reads from several app state files and creates a useful cross-app summary. Shared paths, config, and logging make the suite feel coherent.

The implementation also includes migration support for the Markdown package rename, which shows real package-maintenance thinking.

## Technical Decisions That Paid Off

## Typer Sub-App Composition

Using `app.add_typer()` is the most important architectural choice. It lets every utility keep its own command structure while still participating in the root CLI.

This avoided the common mistake of rewriting all commands in one huge main file.

## Shared Path Module

Centralizing paths in `sysforge_paths.py` made the report command possible. Without consistent paths, the dashboard would need brittle assumptions.

The `SYSFORGE_HOME` override also made testing safer.

## Shared Config Loader

The shared config loader gave the root CLI and sub-apps a common configuration source. Deep merging defaults with user config is more realistic than requiring every config file to contain every key.

## Central Logging Utility

Root-level verbosity and quiet flags are useful because they affect the broader toolkit. Central logger initialization is a good first step toward consistent operations.

## Dashboard as a Root Command

The `report` command belongs at the root because it summarizes the whole system. It gives App 28 its own identity rather than making it only a router.

## Simple File-Based State

JSON, JSONL, text, Markdown, HTML, and CSV are appropriate for a local CLI portfolio project. A database would have been overbuilt for this stage.

## Compatibility Import Shim

The shim for `sysforge.markdown` demonstrates awareness of migration and backward compatibility. It is more advanced than necessary for a toy app, but appropriate for a toolkit that has changed package layout.

## Technical Decisions That Created Debt

## Root CLI Imports Every Sub-App

The root command imports all sub-apps immediately. This is easy to understand, but it means a broken optional area can break the main command.

A future design could lazy-load subcommands or use a plugin registry.

## Report Logic Knows Every State Format

`reporting.py` reads files produced by multiple apps. This is useful, but it creates coupling. If the organizer changes its summary field names, the report must change too.

A future design might define a small report-provider interface for each app.

## Environment Variables as Internal State

Mapping global flags to environment variables is convenient. It also makes behavior depend on mutable process state. Passing a runtime context object would be cleaner for a larger system.

## Limited Report Querying

The report command only builds a daily report for the current date. It does not support `--date`, `--from`, or `--to`.

## Minimal Corruption Recovery

Missing files are handled well, but malformed JSON can still fail report generation. A more robust version would quarantine bad files or show partial reports.

## What Was Harder Than Expected

## Cross-App Boundaries

The hardest part is deciding how much the root app should know about sub-apps. Too little knowledge makes reporting impossible. Too much knowledge turns the root into a second implementation of every utility.

The chosen design keeps command execution delegated, but reporting reads state directly.

## Shared State Design

Once several apps share a home directory, naming conventions matter. Every file path becomes part of an internal contract.

## Keeping the Root Thin

It is tempting to add more logic to `__main__.py` because it is the first file users touch. The better design is to keep root routing there and put business logic in modules such as `reporting.py`.

## Report Rendering in Multiple Formats

Text, Markdown, and HTML share the same data but require different output conventions. Building a common report data object first made this manageable.

## What Was Easier Than Expected

## Mounting Typer Apps

Typer made composition straightforward. Once each sub-app exposed an `app`, the root CLI could mount it without special routing code.

## Shared File-Based Reporting

Because sub-apps already wrote JSON state and history, reporting did not need invasive changes to the sub-apps.

## Version Command

Using a callback for `--version` is a clean Typer pattern and kept version behavior separate from normal command execution.

## Python-Specific Learnings

## `__main__.py` as a Package Entry Point

The root command shows how a package can be executable through both console scripts and `python -m sysforge`.

## Import-Time Side Effects Need Care

Installing the Markdown alias finder in `__init__.py` is powerful, but import hooks are advanced. They should be used carefully and documented clearly.

## `pathlib.Path` Improves CLI Code

Paths are easier to pass between Typer, shared helpers, and file operations when represented as `Path` objects.

## `os.environ` Works but Can Spread

Environment variables are a simple cross-module communication mechanism, but overuse can hide dependencies.

## Small Shared Helpers Matter

Functions like `format_duration()`, `human_size()`, `write_text_file()`, and `load_json_file()` make the report module more readable.

## Architecture Insights

## A Toolkit Needs a Shell

Six working apps are useful, but a toolkit needs a shell around them. The root command creates that shell.

## Integration Apps Are Mostly About Contracts

App 28 depends on contracts:

- sub-apps expose Typer apps,
- shared paths return stable locations,
- state files have expected shapes,
- config loading follows a predictable merge order,
- logs use shared logger names.

The integrated app is less about complex algorithms and more about holding these contracts together.

## Reporting Reveals Architecture Quality

A daily report can only exist if apps record useful state. Building the report exposed which sub-apps had clear histories and which data was only implicit.

## Root Commands Should Delegate

The root CLI should be a coordinator, not an owner of every feature. Delegation kept the design maintainable.

## Testing Gaps

## Current Coverage Strengths

The reporting module has tests that seed today’s artifacts and verify text report generation. HTML rendering is tested to ensure Markdown is rendered into real HTML rather than escaped as preformatted text.

Other sub-app tests provide indirect confidence because the root CLI mounts their app objects.

## Remaining Gaps

- Root CLI global flag behavior could use direct CLI tests.
- `--version` callback could be tested explicitly.
- `--verbose` and `--quiet` conflict could be tested.
- `--config` behavior could be tested at root level.
- Root subcommand registration could be tested with `sysforge --help`.
- Report behavior with corrupted JSON could be tested.
- HTML and Markdown report file writing could be tested more fully.
- Compatibility import shim could be tested directly.

## Reusable Patterns Identified

## Root Typer App Pattern

```python
app = typer.Typer(...)
app.add_typer(sub_app, name="subcommand")
```

Useful for any future multi-tool CLI suite.

## Shared Home Directory Pattern

A single state root with app-specific subfolders is reusable across local tooling projects.

## Report Aggregator Pattern

Collect state from several simple file stores, normalize into one dictionary, then render in multiple formats.

## Config Merge Pattern

Load package defaults, then deep-merge user overrides.

## Logger Setup Pattern

Central file logger plus configurable console handler.

## Compatibility Shim Pattern

Use import hooks only when migration safety is worth the complexity.

## If I Built This Again

I would keep the same broad structure but improve several details:

1. Add a root CLI test file.
2. Add `sysforge report --date YYYY-MM-DD`.
3. Add a report-provider function per app, such as `get_report_data(today)`.
4. Lazy-load subcommands to reduce startup coupling.
5. Add a structured runtime context object instead of relying on environment variables.
6. Add JSON corruption handling in report generation.
7. Add a plugin registry or app manifest.
8. Include a machine-readable report JSON format.
9. Add more explicit documentation of the shared state contract.
10. Add a cleanup or doctor command for validating the SysForge home directory.

## Open Questions

- Should reporting remain centralized, or should each app provide its own report fragment?
- Should the root CLI support plugin discovery?
- Should SysForge eventually use SQLite for structured history?
- Should `report` include a date-range option?
- Should the root command continue importing all sub-apps eagerly?
- Should config be passed as a context object instead of environment variables?
- Should compatibility shims have a planned removal date?
- Should the report command include health data only if it was captured today?
- Should reports include links to generated HTML docs and briefing files?
- Should `sysforge doctor` be added to validate installation and state?

## Final Reflection

This app shows the transition from writing scripts to designing a toolkit. The individual SysForge utilities demonstrate practical Python CLI skills. The integrated command demonstrates architecture: composition, shared contracts, package identity, reporting, configuration, logging, and migration support.

The most important lesson is that integration work is real engineering work. It does not always introduce new algorithms, but it introduces coordination problems. SysForge solves those coordination problems with a clear root CLI, shared paths, shared config, shared logging, and a dashboard command that proves the apps can work together as one system.
