# SysForge

SysForge is a Python CLI toolkit that bundles six standalone utility apps plus one integrated dashboard command:

- `sysforge-organizer`: organize files by extension, date, or size
- `sysforge-mdhtml`: build HTML docs from Markdown
- `sysforge-briefing`: generate a daily briefing file
- `sysforge-time`: track work sessions and export timesheets
- `sysforge-config`: inspect and update JSON configs
- `sysforge-health`: log system health snapshots
- `sysforge`: the unified CLI that wraps all of the above


## Project layout

Python package code lives under the `sysforge/` directory (standard `src`-style layout without a `src/` prefix). The repository root holds packaging metadata, CI, and tests.

```text
.
  pyproject.toml
  requirements.txt
  README.md
  tests/
  sysforge/                 (importable package sysforge)
    __init__.py
    __main__.py
    py.typed
    _import_shims.py
    common.py
    logging_utils.py
    reporting.py
    shared_config.py
    sysforge_paths.py
    organizer/
    mdhtml/
    briefing/
    timetracker/
    config/
    monitor/
    data/
```

## Install

```bash
python -m pip install -e .
```

If you prefer installing dependencies from `requirements.txt` first (for example in a container), use:

```bash
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps
```

Windows timezone note:

- If `zoneinfo` cannot find your timezone, install `tzdata` with `python -m pip install tzdata`.

## Shared state

By default, SysForge stores app data under `~/.sysforge/`, including:

- `~/.sysforge/sysforge.json` (shared settings; created on first run from package defaults)
- `~/.sysforge/logs/sysforge.log`
- `~/.sysforge/organizer/logs/*.json`
- `~/.sysforge/docs/build_history.json`
- `~/.sysforge/briefings/`
- `~/.sysforge/time/timesheet.json`
- `~/.sysforge/health/health_log.jsonl`
- `~/.sysforge/reports/`

For local testing, you can point everything at a different home folder:

```bash
set SYSFORGE_HOME=.sysforge-dev
```

## Standalone app examples

### Organizer

```bash
sysforge-organizer ./Downloads --by extension --dry-run
sysforge-organizer ./Downloads --by date --recursive
sysforge-organizer --undo
```

### Markdown builder

```bash
sysforge-mdhtml build notes.md --output output.html
sysforge-mdhtml build ./notes --output ./site --theme dark
```

### Briefing

```bash
sysforge-briefing
sysforge-briefing --format markdown --no-quote
```

### Time tracker

```bash
sysforge-time start "Code review" --project ClientX --tag billable
sysforge-time status
sysforge-time stop
sysforge-time log
sysforge-time report --week
sysforge-time export --csv timesheet.csv
```

### Config manager

```bash
sysforge-config get database.host --file app.json
sysforge-config set database.port 5432 --file app.json
sysforge-config list --file app.json
sysforge-config validate app.json --schema sysforge/data/sysforge.schema.json
sysforge-config diff a.json b.json
sysforge-config init --template web-app --output starter.json
```

### Health monitor

```bash
sysforge-health
sysforge-health --watch --interval 30
```

## Unified CLI walkthrough

```bash
sysforge --version
sysforge organize ./Downloads --dry-run
sysforge docs build ./notes --output ./site
sysforge briefing
sysforge time start "Architecture notes" --project Learning --tag study
sysforge time stop
sysforge config validate ~/.sysforge/sysforge.json --schema sysforge/data/sysforge.schema.json
sysforge health
sysforge report --format markdown
```

## Config notes

The shared config file is `~/.sysforge/sysforge.json`. It includes starter values for:

- `user.name`
- `user.timezone`
- `time.project_rates`
- `health.disk_warning`
- `health.memory_warning`

`sysforge-config validate` reads a JSON Schema file, but only the subset implemented in SysForge (`type`, `properties`, `required`, `default`, numeric `min`/`max`, and `enum`). For full Draft JSON Schema features, use a dedicated validator.

The config manager also supports environment overrides when reading values. Example:

```bash
set APP_DATABASE_HOST=prod-db.internal
sysforge-config get database.host --file app.json
```

## Verification

From the project root (after installing dependencies):

```bash
python -m pip install -e ".[dev]"
python -m ruff format --check .
python -m ruff check .
python -m mypy
python -m compileall -q .
python -m pytest
```

Tests run with **coverage** on the `sysforge` package (see `pyproject.toml`: `pytest-cov`, `--cov-fail-under=63`). CI fails if coverage drops below that threshold.

`compileall` targets the current tree; with an editable install, `python -m compileall sysforge` also works against the installed package path.

## Changelog

All notable changes to this project are documented here.

### [Unreleased]

#### Added

- **pytest-cov**: test runs measure line coverage on `sysforge` and fail below **63%** (configurable via `pyproject.toml`).
- Development tooling: Ruff (lint + format), Mypy, and library stubs (`types-Markdown`, `types-psutil`) in the `dev` optional dependency set; CI runs Ruff and Mypy on every push and PR.
- PEP 561 `py.typed` marker for the `sysforge` package.
- Deprecation shim: `import sysforge.markdown` / `import sysforge.markdown.markdown` still resolve to the Markdown-to-HTML implementation, but emit a `DeprecationWarning` directing callers to `sysforge.mdhtml` (see Migration below).

#### Changed

- **Mypy**: `warn_return_any` is enabled; third-party `ignore_missing_imports` is limited to **pygments** (Typer/Rich use installed types).
- Package layout: application modules now live under a `sysforge/` directory (standard package tree) instead of a flat repository root mapped via `package-dir`.
- Version **0.2.0** with an updated PyPI project description.
- The documentation builder package was renamed from `sysforge.markdown` to `sysforge.mdhtml` so the PyPI `markdown` library is no longer shadowed by a same-named local directory on `sys.path`. CLI entry points (`sysforge-mdhtml`, `sysforge docs`, and so on) are unchanged.

#### Migration

Replace:

```python
from sysforge.markdown.markdown import app
```

with:

```python
from sysforge.mdhtml.markdown import app
```

Until you remove the old import, a one-time `DeprecationWarning` is emitted when the legacy path is first imported in a process.
