# Architecture Decision Record

## App 26 — Folder Organizer

**SysForge Group | Document 1 of 5**  
**Status: Accepted**

---

## Title

Use a Typer-based SysForge sub-application with rule-driven file classification, dry-run planning, JSON movement logs, and undo support for folder organization.

---

## Date

2026-05-08

---

## Context

The Folder Organizer is the SysForge utility responsible for taking a messy directory and moving files into predictable subfolders. It belongs to the SysForge toolkit, so it must work both as a standalone command (`sysforge-organizer`) and as part of the unified `sysforge organize` CLI.

The app solves a practical local-automation problem: users often need to clean folders such as Downloads, project scratch directories, exported reports, or mixed media folders. The organizer needs to classify files by common criteria, avoid surprising destructive behavior, provide a preview mode, and leave enough audit information to reverse a recent real run.

The implementation lives in `sysforge/organizer/organizer.py`. It uses the shared SysForge helpers for JSON I/O, hidden-file detection, human-readable sizes, logging, shared config, package default rules, and home-directory layout. This makes the app a good example of the SysForge monorepo design: it is a standalone app, but it deliberately shares infrastructure instead of copying utility code.

---

## Decision Drivers

- Keep the app usable from the command line without requiring a GUI.
- Support realistic folder cleanup workflows: by extension, by modified date, or by file size.
- Avoid destructive behavior by default through rename-on-conflict and optional dry-run planning.
- Preserve operational accountability with JSON movement logs.
- Support undo for the most recent real organizer run.
- Fit into SysForge’s shared state model under `~/.sysforge` or `SYSFORGE_HOME`.
- Keep classification rules editable as JSON rather than hard-coded only in Python.
- Teach file-system automation, pathlib usage, conflict resolution, and CLI state management.
- Maintain a small, readable implementation appropriate for a portfolio utility app.

---

## Options Considered

### Option 1 — Single-file standalone organizer outside SysForge

**Description:** Build the organizer as a separate script with its own local rules, logs, and CLI.

**Pros**
- Simple to distribute as one file.
- No dependency on SysForge package layout.
- Easier to understand as an isolated beginner project.

**Cons**
- Duplicates JSON, logging, and path helpers already present in SysForge.
- Would not participate in the unified `sysforge` command.
- Harder to maintain consistent behavior across the toolkit.
- Undo logs and config paths would not follow the same home-directory convention.

**Decision:** Rejected.

**Reason:** The SysForge portfolio is intentionally demonstrating a shared-package architecture. A standalone script would work, but it would weaken the architectural goal.

---

### Option 2 — Rule-driven organizer inside SysForge

**Description:** Implement the organizer as `sysforge.organizer.organizer`, expose a Typer app, load rules from either the shared config or a provided JSON file, and use shared SysForge helpers for paths and logging.

**Pros**
- Integrates with `sysforge-organizer` and `sysforge organize`.
- Reuses common functionality without copy-pasting.
- Keeps default rules packaged with the project.
- Allows user-provided rules through `--rules` or shared config.
- Makes logs and undo state consistent with the rest of SysForge.

**Cons**
- Slightly more complicated than a one-file script.
- Requires understanding the shared SysForge home layout.
- Depends on the package being installed correctly.

**Decision:** Accepted.

**Reason:** This option best matches the SysForge design goal while keeping the app small enough for a focused utility.

---

### Option 3 — Fully interactive menu-driven organizer

**Description:** Prompt the user for folder path, sort mode, conflict behavior, hidden file handling, and whether to run or preview.

**Pros**
- Friendly for casual users.
- Reduces need to remember command-line flags.

**Cons**
- Harder to script.
- Harder to test.
- Less consistent with SysForge’s other Typer-based tools.
- Not ideal for automation workflows.

**Decision:** Rejected.

**Reason:** Folder organization is a utility operation that benefits from predictable CLI invocation and automation.

---

### Option 4 — Always move files directly with no dry run

**Description:** Keep the tool simple by moving files immediately and relying only on logs or manual cleanup if the result is wrong.

**Pros**
- Less code.
- Faster path from command to visible result.

**Cons**
- Risky for user data.
- Makes classification mistakes harder to catch.
- Poor learning example for safe file-system automation.

**Decision:** Rejected.

**Reason:** A dry-run flag is important for user trust, safety, and professional CLI design.

---

### Option 5 — Use OS-specific shell commands

**Description:** Delegate operations to commands like `mv`, `move`, `find`, or shell globbing.

**Pros**
- Can be concise.
- Familiar to shell users.

**Cons**
- Less portable across Windows, macOS, and Linux.
- Harder to test consistently.
- More fragile around spaces and unusual paths.
- Does not teach Python’s `pathlib` and `shutil` patterns.

**Decision:** Rejected.

**Reason:** The app should be Python-native and cross-platform.

---

## Decision

The Folder Organizer will be implemented as a SysForge Typer sub-application using the following design:

1. Expose `sysforge-organizer` through the package entry point and `sysforge organize` through the unified CLI.
2. Use `pathlib.Path` for all file-system paths.
3. Support three classification modes:
   - `extension`
   - `date`
   - `size`
4. Load rules from:
   - an explicit `--rules` file,
   - a shared config `organizer.rules_file`,
   - or the packaged default `sysforge/data/default_organizer_rules.json`.
5. Skip symlinks.
6. Skip hidden files unless `--include-hidden` is passed.
7. Use conflict strategies:
   - `rename`
   - `skip`
   - `overwrite`
8. Default conflict behavior to `rename`.
9. Support `--dry-run` to plan moves without performing them.
10. Write JSON run logs under the SysForge organizer log directory.
11. Support undo by replaying the latest non-dry-run organizer log in reverse order.
12. Print a compact summary after each run.

---

## Rationale

The selected approach balances safety, usability, and educational value.

The important architectural decision is that organization is not treated as a simple loop that moves files directly. Instead, it is split into smaller responsibilities:

- candidate discovery,
- folder classification,
- conflict resolution,
- move execution,
- logging,
- undo.

This separation makes the behavior easier to test and easier to reason about. For example, `resolve_relative_folder()` can be tested without touching the file system except for date and size cases, while `choose_destination()` can be tested with small temporary files. `run_organizer()` acts as the orchestration layer.

Dry-run support is also a major design decision. A folder organizer can easily create user frustration if it moves files unexpectedly. The dry-run mode allows the user to verify planned destinations first. The log format further improves trust by showing exactly what was moved, skipped, planned, or errored.

The undo design is intentionally simple: it only targets the latest non-dry-run log and restores moved files in reverse order. This is enough to teach stateful recovery without turning the project into a full file-system transaction engine.

---

## Trade-offs Accepted

### JSON logs are useful but not a full transaction system

The app writes movement logs and can undo the latest real run, but it does not guarantee perfect rollback in every real-world scenario. If files are edited, moved again, deleted, or recreated at the original path, undo may skip or fail individual items.

This is acceptable because the project is a portfolio-sized CLI app rather than a backup tool.

---

### Recursive mode can reprocess organized folders

Recursive scans inspect all nested files under the target. If the target already contains organizer-created folders, recursive mode may consider those nested files as candidates too.

This is acceptable because recursive behavior is explicit through `--recursive`, and the tool records actions in logs. A future version could add exclusion rules for generated destination folders.

---

### Rule files are flexible but loosely validated

The organizer expects rule JSON to have meaningful keys such as `extension_categories`, `size_buckets`, and `date_format`, but it does not run a full schema validator before use.

This keeps the app small and readable. Invalid rule values generally fall back to conservative behavior, such as placing unknown extensions under `Other` or treating bad size bucket values as very large.

---

### Undo only uses the latest non-dry-run organizer log

The undo feature does not let the user choose an older log from the CLI.

This keeps the operation simple and reduces ambiguity for a beginner-friendly utility. The JSON logs still preserve enough data for manual inspection.

---

### The app logs file paths

Movement logs include normalized source and destination paths. This is necessary for undo and auditing, but it means logs can reveal local folder structure.

This is acceptable for a local developer tool. Users should avoid sharing organizer logs if paths contain sensitive information.

---

## Consequences

### Positive Consequences

- The app is safe to experiment with because `--dry-run` previews moves.
- The default `rename` strategy avoids overwriting files by accident.
- JSON logs create a clear audit trail.
- Undo support makes the app more operationally mature than a basic file mover.
- Rule-driven design allows behavior to change without editing Python code.
- The same app works through standalone and unified SysForge commands.
- Tests can focus on small units like classification, conflict handling, and real move behavior.

### Negative Consequences

- The app has more moving parts than a simple folder-sorting script.
- JSON logs add persistent side effects to the SysForge home directory.
- Undo can only restore moves if the current file-system state still allows it.
- Users must understand the difference between dry-run and real runs.
- Rule mistakes can still produce unexpected folder names.

### Neutral Consequences

- Typer becomes part of the runtime dependency set.
- Shared SysForge config affects behavior when `organizer.rules_file` is set.
- `SYSFORGE_HOME` can redirect state during testing or local experimentation.

---

## Superseded By

Not superseded.

A future ADR could supersede this one if the organizer gains a transaction database, exclusion patterns, checksum-based rollback, or a richer rule schema.

---

# Technical Design Document

## App 26 — Folder Organizer

**SysForge Group | Document 2 of 5**  
**Status: Accepted**

---

## Purpose & Scope

The Folder Organizer is a command-line utility for organizing files inside a target directory. It can group files by extension category, modification date, or size bucket. It supports dry-run planning, conflict handling, hidden-file filtering, recursive scanning, JSON logs, and undo.

The scope is intentionally local and file-system based. The app does not watch folders continuously, sync files to cloud storage, inspect file contents, or perform duplicate-file detection. It focuses on predictable movement of local files based on metadata.

---

## System Context

The organizer is one application within SysForge, a Python CLI toolkit. It is available in two command contexts:

```bash
sysforge-organizer
```

and:

```bash
sysforge organize
```

The standalone command is wired through the `sysforge-organizer` console script. The unified CLI imports the organizer Typer app and registers it under the `organize` command.

The app interacts with:

- the user’s target directory,
- packaged default organizer rules,
- optional custom rules files,
- optional shared SysForge config,
- the SysForge organizer log directory,
- the central SysForge logger.

---

## Component Breakdown

### `sysforge/organizer/organizer.py`

This is the main implementation module. It contains:

- Typer app object,
- CLI callback,
- undo command,
- rule loading,
- file candidate discovery,
- destination classification,
- conflict resolution,
- move execution,
- run logging,
- undo orchestration,
- summary printing.

Key functions include:

- `load_rules()`
- `iter_candidate_files()`
- `resolve_relative_folder()`
- `choose_destination()`
- `perform_move()`
- `run_organizer()`
- `find_latest_real_log()`
- `undo_last_run()`
- `print_summary()`
- `organize()`
- `undo_command()`
- `main()`

---

### `sysforge/organizer/__init__.py`

This package marker identifies `sysforge.organizer` as a package. It does not currently re-export the organizer API.

---

### `sysforge/data/default_organizer_rules.json`

This is the default rule file used when the user does not provide `--rules` and the shared config does not define `organizer.rules_file`.

It defines:

- extension categories,
- size buckets,
- date folder format.

The default extension categories include common image, document, code, archive, and media extensions. The default size buckets are small, medium, and large. The default date format is `%Y/%m`.

---

### `sysforge/common.py`

The organizer uses common utilities for:

- `human_size()` summary formatting,
- `is_hidden_path()` hidden-file detection,
- `load_json_file()` rule and log loading,
- `write_json_file()` run and undo log writing,
- `print_error()` CLI error handling.

---

### `sysforge/sysforge_paths.py`

The organizer uses path helpers for:

- ensuring the SysForge home layout exists,
- locating the default organizer rules file,
- locating the organizer log directory.

Relevant paths include:

- `~/.sysforge/organizer/logs/`
- package data path for `default_organizer_rules.json`

When `SYSFORGE_HOME` is set, the home directory is redirected.

---

### `sysforge/shared_config.py`

The organizer uses `load_shared_config()` to read shared SysForge settings. If the shared config contains an organizer rules file path, that path can become the default rules source.

---

### `sysforge/logging_utils.py`

The organizer uses a logger named `sysforge.organizer`. Logging is integrated with the central SysForge log system, with verbosity controlled by environment variables set by the unified CLI.

---

### `sysforge/__main__.py`

The unified CLI imports the organizer Typer app and registers it as:

```python
app.add_typer(organizer_app, name="organize")
```

This is why `sysforge organize ...` runs the same app as `sysforge-organizer ...`.

---

## Module Dependency Graph

```text
User
  |
  v
Typer CLI
  |
  +--> sysforge.organizer.organizer
          |
          +--> pathlib.Path
          +--> shutil
          +--> datetime
          +--> typer
          |
          +--> sysforge.common
          |       +--> human_size
          |       +--> is_hidden_path
          |       +--> load_json_file
          |       +--> write_json_file
          |       +--> print_error
          |
          +--> sysforge.shared_config
          |       +--> load_shared_config
          |
          +--> sysforge.sysforge_paths
          |       +--> ensure_home_layout
          |       +--> get_default_organizer_rules_path
          |       +--> get_organizer_log_dir
          |
          +--> sysforge.logging_utils
                  +--> get_logger
```

Unified CLI path:

```text
sysforge.__main__
  |
  +--> imports sysforge.organizer.organizer.app
  |
  +--> registers as "organize"
```

Standalone path:

```text
pyproject.toml
  |
  +--> sysforge-organizer = sysforge.organizer.organizer:main
```

---

## Core Algorithms & Logic

### 1. Rule Loading

`load_rules(rules_path, config_path)` chooses a rule source in this order:

1. Explicit `rules_path` passed from `--rules`.
2. `organizer.rules_file` from shared SysForge config.
3. Packaged default organizer rules.

The selected JSON file is loaded with `load_json_file()` and returned as a dictionary.

---

### 2. Candidate File Discovery

`iter_candidate_files(target, recursive, include_hidden)` returns two lists:

- candidate file paths,
- informational messages about skipped paths.

The function scans either:

```python
target.iterdir()
```

for non-recursive mode, or:

```python
target.rglob("*")
```

for recursive mode.

It skips:

- paths that no longer exist,
- symlinks,
- directories,
- hidden files unless `include_hidden=True`.

Skipped symlinks and hidden files are reported as messages, not treated as fatal errors.

---

### 3. Folder Resolution

`resolve_relative_folder(path, mode, rules)` determines where a file should go relative to the target directory.

#### Extension Mode

For `mode == "extension"`:

1. Read `extension_categories` from the rules.
2. Lowercase the file suffix.
3. If the file has no suffix:
   - use an explicit `""` mapping when present,
   - otherwise use `extension_no_suffix_category`,
   - otherwise use `Other`.
4. If the suffix exists in the map, use that category.
5. Otherwise use `Other`.

Examples:

```text
notes.txt     -> Docs or custom TextFiles
photo.png     -> Images
archive.zip   -> Archives
Makefile      -> Other or configured no-suffix folder
unknown.xyz   -> Other
```

#### Date Mode

For `mode == "date"`:

1. Read file modification time with `path.stat().st_mtime`.
2. Convert it to a local datetime.
3. Format it using `rules["date_format"]` or default `%Y/%m`.
4. Return that formatted path.

Example:

```text
2026/05
```

#### Size Mode

For `mode == "size"`:

1. Calculate file size in megabytes.
2. Read `size_buckets` from rules.
3. Sort buckets by numeric `max_mb`, with `null` buckets last.
4. Return the first bucket whose `max_mb` accepts the file.
5. If no bucket matches, return `Large`.

Example default buckets:

```text
<= 1 MB   -> Small
<= 25 MB  -> Medium
> 25 MB   -> Large
```

---

### 4. Size Bucket Ordering

`_ordered_size_bucket_entries()` exists to avoid relying on JSON object order. It parses each bucket’s `max_mb` value and sorts buckets by numeric size. Buckets with `max_mb: null` are treated as catch-all entries and placed last.

This prevents a bug where a catch-all bucket like `large` could accidentally match everything if it appeared first in the JSON object.

---

### 5. Destination Selection

`choose_destination(source, base_dir, relative_folder, conflict_mode)` determines whether a move should occur and what destination path should be used.

The destination is:

```text
base_dir / relative_folder / source.name
```

If the destination is identical to the source, the file is skipped.

If the destination does not exist, the action is `move`.

If the destination exists, the conflict strategy applies:

- `skip`: no move.
- `overwrite`: move to the destination after deleting the existing file.
- `rename`: generate `stem_1.ext`, `stem_2.ext`, etc. until a free name is found.

---

### 6. Move Execution

`perform_move(source, destination, action, dry_run)` performs the final movement step.

In dry-run mode:

- no directories are created,
- no files are moved,
- the planned destination is returned.

In real mode:

1. Create the destination parent directory.
2. If action is `overwrite`, remove the existing destination file.
3. Move the file with `shutil.move()`.
4. If an unexpected `FileExistsError` occurs during a normal move, retry with a numbered rename.

---

### 7. Organizer Run Orchestration

`run_organizer()` is the core workflow function.

It:

1. Ensures the SysForge home layout exists.
2. Validates that the target exists and is a directory.
3. Loads rules.
4. Discovers candidate files.
5. Initializes counters for moved, skipped, errors, and total bytes.
6. For each file:
   - adds file size to total processed,
   - resolves a relative folder,
   - chooses a destination,
   - skips or moves/plans the file,
   - records an action dictionary.
7. Builds a summary.
8. Writes a JSON log.
9. Returns summary, moves, messages, and log path.

The returned structure is designed for both CLI output and tests.

---

### 8. Run Log Structure

A normal run log contains:

```json
{
  "timestamp": "...",
  "target": "...",
  "mode": "extension",
  "dry_run": false,
  "conflict_mode": "rename",
  "messages": [],
  "moves": [
    {
      "source": "...",
      "destination": "...",
      "status": "moved",
      "strategy_used": "move"
    }
  ],
  "summary": {
    "moved": 1,
    "skipped": 0,
    "errors": 0,
    "total_size_processed": 1234
  }
}
```

Dry-run actions use `status: "planned"`.

Skipped actions use `status: "skipped"`.

Failed actions use `status: "error"`.

---

### 9. Undo Workflow

`undo_last_run()` restores files from the latest non-dry-run log.

It:

1. Ensures the home layout exists.
2. Finds the latest organizer log whose `dry_run` field is false.
3. Reads its `moves` list in reverse order.
4. Ignores moves that were not actually moved.
5. For each moved file:
   - check if destination still exists,
   - check if original source path is free,
   - move destination back to source when safe,
   - record restored/skipped/error status.
6. Write an undo log.
7. Return the undo log path and summary.

The reverse-order replay is important because it reduces the chance of parent/child path conflicts during restoration.

---

## Data Structures

### Rules Dictionary

```python
{
    "extension_categories": {
        ".txt": "Docs",
        ".png": "Images"
    },
    "extension_no_suffix_category": "Other",
    "size_buckets": {
        "small": {"max_mb": 1},
        "medium": {"max_mb": 25},
        "large": {"max_mb": None}
    },
    "date_format": "%Y/%m"
}
```

### Move Action

```python
{
    "source": "/absolute/source/path.txt",
    "destination": "/absolute/destination/path.txt",
    "status": "moved",
    "strategy_used": "move"
}
```

### Summary

```python
{
    "moved": 3,
    "skipped": 1,
    "errors": 0,
    "total_size_processed": 9432
}
```

### Run Result

```python
{
    "log_path": Path("..."),
    "summary": {...},
    "moves": [...],
    "messages": [...]
}
```

### Undo Summary

```python
{
    "restored": 3,
    "skipped": 0,
    "errors": 0
}
```

---

## State Management

The app has no database. Its persistent state is stored in JSON files under the SysForge home directory.

Default state path:

```text
~/.sysforge/organizer/logs/
```

When `SYSFORGE_HOME` is set:

```text
$SYSFORGE_HOME/organizer/logs/
```

State files include:

- organizer run logs,
- organizer undo logs,
- shared SysForge config copied from package defaults on first run.

The target directory itself is also modified during real runs. Those file moves are the most important side effect.

---

## Error Handling Strategy

### CLI-Level Validation

The CLI validates:

- `--by` must be `extension`, `date`, or `size`.
- `--on-conflict` must be `rename`, `skip`, or `overwrite`.
- a target folder is required unless undo is requested.
- the target must exist and be a directory.

Invalid input is routed through `print_error()`, which prints a red Typer error and exits.

---

### Per-File Error Handling

`run_organizer()` wraps each candidate file in a try/except block. A failure for one file:

- increments the error counter,
- adds an action with `status: "error"`,
- records the error message,
- allows the run to continue with remaining files.

This prevents one problematic file from stopping the entire organization run.

---

### Undo Error Handling

Undo treats unsafe restoration conditions as skipped actions:

- destination no longer exists,
- original source path already exists.

Unexpected exceptions during a restore attempt become `error` entries in the undo log.

---

### Hidden and Symlink Handling

Hidden files and symlinks are skipped rather than treated as errors. This is safer because hidden files may represent configuration or system metadata, and symlinks can create surprising movement behavior.

---

## External Dependencies

### Runtime Dependencies

The app uses:

- `typer>=0.12` for CLI construction.
- SysForge shared runtime dependencies inherited from the project package.

The organizer itself primarily uses the Python standard library:

- `pathlib`
- `shutil`
- `datetime`
- `typing`

### Development Dependencies

The SysForge dev workflow includes:

- `pytest`
- `pytest-cov`
- `ruff`
- `mypy`
- type stub packages used by the broader repository.

---

## Concurrency Model

The Folder Organizer is single-threaded and synchronous.

It does not use:

- threads,
- multiprocessing,
- asyncio,
- file locks.

This is appropriate for a local CLI utility. However, concurrent runs against the same target directory are not protected. Two organizer processes running on the same folder could race on destinations and logs.

---

## Known Limitations

1. Undo only targets the latest non-dry-run log.
2. Undo cannot restore a file if the original source path now exists.
3. Undo cannot restore a file if the moved destination has been deleted or moved again.
4. Recursive mode can scan previously organized folders.
5. Rule files are not fully schema-validated.
6. Extension classification only uses suffix, not file content or MIME type.
7. Date classification uses local modified time.
8. Hidden-file detection is platform-dependent.
9. Logs include local absolute paths.
10. No file lock prevents two organizer runs from operating on the same directory at the same time.

---

## Design Patterns Used

### Command Pattern

The Typer CLI exposes user operations as commands and options.

### Strategy Pattern

The `sort_mode` argument selects one of three organization strategies:

- extension,
- date,
- size.

The `conflict_mode` argument selects one of three conflict strategies:

- rename,
- skip,
- overwrite.

### Functional Decomposition

The implementation separates small responsibilities into individual functions. This improves testability.

### Audit Log Pattern

Every run writes a JSON log. The log is both an audit record and the input for undo.

### Safe Preview Pattern

Dry-run mode computes planned moves without changing files.

### Recovery Pattern

Undo replays the latest real log in reverse order to restore moved files when safe.

---

# Interface Design Specification

## App 26 — Folder Organizer

**SysForge Group | Document 3 of 5**  
**Status: Accepted**

---

## Invocation Syntax

### Standalone command

```bash
sysforge-organizer [TARGET] [OPTIONS]
```

### Unified SysForge command

```bash
sysforge organize [TARGET] [OPTIONS]
```

### Undo command forms

```bash
sysforge-organizer --undo
sysforge-organizer undo
sysforge organize --undo
sysforge organize undo
```

---

## Argument Reference Table

| Name | Type | Required | Default | Accepted Values | Description |
|---|---:|---:|---:|---|---|
| `TARGET` | Path | Required unless undoing | `None` | Existing directory | Folder to organize. |
| `--by` | string | Optional | `extension` | `extension`, `date`, `size` | Selects organization mode. |
| `--rules` | Path | Optional | `None` | JSON file path | Custom rules file. |
| `--dry-run` | flag | Optional | `False` | present / absent | Shows planned moves without moving files. |
| `--on-conflict` | string | Optional | `rename` | `rename`, `skip`, `overwrite` | Controls behavior when destination exists. |
| `--include-hidden` | flag | Optional | `False` | present / absent | Includes hidden files in candidate scan. |
| `--recursive` | flag | Optional | `False` | present / absent | Scans nested files under target. |
| `--undo` | flag | Optional | `False` | present / absent | Undo latest non-dry-run organizer log. |
| `--config` | Path | Optional | `None` | JSON file path | Optional shared SysForge config file. |
| `undo` | subcommand | Optional | N/A | N/A | Undo latest non-dry-run organizer log. |
| `--help` | flag | Optional | N/A | present / absent | Show Typer help. |

---

## Input Contract

### Target Directory

When not undoing, `TARGET` must:

- exist,
- be a directory,
- be readable by the process,
- contain files that may be moved.

If `TARGET` is missing or is not a directory, the app exits with an error.

---

### Rule File

A rule file is JSON. The expected structure is:

```json
{
  "extension_categories": {
    ".txt": "Docs",
    ".png": "Images"
  },
  "extension_no_suffix_category": "Other",
  "size_buckets": {
    "small": {"max_mb": 1},
    "medium": {"max_mb": 25},
    "large": {"max_mb": null}
  },
  "date_format": "%Y/%m"
}
```

All keys are optional, but missing sections reduce classification quality.

---

### File Candidates

A file is a candidate when:

- it exists,
- it is not a directory,
- it is not a symlink,
- it is not hidden unless `--include-hidden` is used,
- it is found at the scan depth selected by `--recursive`.

---

## Output Contract

### Normal Run Output

A real run prints:

- skipped symlink/hidden messages if any,
- summary heading,
- moved count,
- skipped count,
- error count,
- total size processed,
- log file path.

Example:

```text
Organizer summary
Moved: 3
Skipped: 1
Errors: 0
Total size processed: 4.2 MB
Log file: /home/user/.sysforge/organizer/logs/organizer_20260508_120000.json
```

---

### Dry-Run Output

Dry-run output includes a planned move section:

```text
Planned moves
/path/Downloads/a.txt -> /path/Downloads/Docs/a.txt

Organizer summary
Moved: 1
Skipped: 0
Errors: 0
Total size processed: 5.0 B
Log file: /home/user/.sysforge/organizer/logs/organizer_20260508_120000.json
```

The summary key is still named `Moved`, but dry-run actions are recorded internally as `planned`.

---

### Undo Output

Undo output prints:

```text
Undo log: /home/user/.sysforge/organizer/logs/organizer_undo_20260508_120500.json
Restored: 3
Skipped: 0
Errors: 0
```

---

## Exit Code Reference

| Exit Code | Meaning |
|---:|---|
| `0` | Operation completed successfully. |
| `1` | Typer/application error, invalid mode, missing target, invalid conflict mode, no undo log, or other `print_error()` failure. |
| `2` | Possible Typer parsing error for malformed command-line invocation. |

The exact exit code may be controlled by Typer for parser-level errors.

---

## Error Output Behavior

Errors are printed through Typer’s styled error path. Examples include:

```text
Please provide a folder to organize.
```

```text
--by must be extension, date, or size.
```

```text
--on-conflict must be rename, skip, or overwrite.
```

```text
Target directory does not exist: /bad/path
```

```text
No organizer log found to undo.
```

Per-file errors are recorded in the JSON log and counted in the summary rather than terminating the whole run.

---

## Environment Variables

| Variable | Used By | Description |
|---|---|---|
| `SYSFORGE_HOME` | SysForge paths | Overrides default `~/.sysforge` state directory. Useful for tests and isolated runs. |
| `SYSFORGE_CONFIG` | Shared config | Allows shared config path override when loaded through shared config helpers. |
| `SYSFORGE_VERBOSE` | Logging | Increases console log verbosity when set by unified CLI. |
| `SYSFORGE_QUIET` | Logging | Reduces console log verbosity when set by unified CLI. |

---

## Configuration Files

### Shared SysForge Config

Default location:

```text
~/.sysforge/sysforge.json
```

Relevant section:

```json
{
  "organizer": {
    "rules_file": "",
    "default_conflict_strategy": "rename"
  }
}
```

The current organizer code uses `organizer.rules_file` when no `--rules` path is supplied. The CLI default for `--on-conflict` is `rename`.

---

### Default Rules File

Packaged default:

```text
sysforge/data/default_organizer_rules.json
```

Includes extension categories, size buckets, and date format.

---

### Run Logs

Default path:

```text
~/.sysforge/organizer/logs/organizer_YYYYMMDD_HHMMSS.json
```

### Undo Logs

Default path:

```text
~/.sysforge/organizer/logs/organizer_undo_YYYYMMDD_HHMMSS.json
```

---

## Side Effects

A real organizer run may:

- create destination subfolders,
- move files,
- overwrite destination files when `--on-conflict overwrite` is used,
- create a SysForge home directory,
- create shared config on first run,
- write an organizer JSON log,
- write central SysForge log messages.

A dry-run may:

- create the SysForge home layout,
- write a dry-run JSON log,
- print planned moves.

Undo may:

- move files back to original paths,
- create parent directories for restored sources,
- write an undo JSON log.

---

## Usage Examples

### Basic Extension Organization

```bash
sysforge-organizer ./Downloads --by extension
```

Expected behavior:

- `.txt`, `.md`, `.pdf`, and similar files move to Docs.
- `.png`, `.jpg`, and similar files move to Images.
- unknown extensions move to Other.
- run log is written.

---

### Dry-Run Extension Organization

```bash
sysforge-organizer ./Downloads --by extension --dry-run
```

Expected behavior:

- no files are moved,
- planned moves are printed,
- a dry-run log is written.

---

### Date-Based Organization

```bash
sysforge-organizer ./Downloads --by date
```

Expected folder pattern with default rules:

```text
./Downloads/2026/05/example.txt
```

---

### Size-Based Organization

```bash
sysforge-organizer ./Downloads --by size
```

Expected default folders:

```text
Small/
Medium/
Large/
```

---

### Recursive Scan

```bash
sysforge-organizer ./Downloads --by extension --recursive
```

Expected behavior:

- files inside subfolders are considered,
- symlinks are skipped,
- hidden files are skipped unless explicitly included.

---

### Include Hidden Files

```bash
sysforge-organizer ./Downloads --include-hidden
```

Expected behavior:

- hidden files are eligible for movement,
- platform-specific hidden detection still applies.

---

### Skip Conflicts

```bash
sysforge-organizer ./Downloads --on-conflict skip
```

Expected behavior:

- files whose destination exists are skipped.

---

### Overwrite Conflicts

```bash
sysforge-organizer ./Downloads --on-conflict overwrite
```

Expected behavior:

- existing destination files may be deleted and replaced.
- this should be used carefully.

---

### Custom Rules File

```bash
sysforge-organizer ./Downloads --rules ./rules.json
```

Example rules:

```json
{
  "extension_categories": {
    ".csv": "Data",
    ".json": "Data",
    ".py": "Python"
  },
  "size_buckets": {
    "tiny": {"max_mb": 0.1},
    "normal": {"max_mb": 10},
    "large": {"max_mb": null}
  },
  "date_format": "%Y-%m"
}
```

---

### Undo Latest Real Run

```bash
sysforge-organizer --undo
```

or:

```bash
sysforge-organizer undo
```

Expected behavior:

- reads the latest non-dry-run organizer log,
- attempts to move files back,
- writes an undo log,
- prints restored/skipped/error counts.

---

### Unified CLI Usage

```bash
sysforge organize ./Downloads --dry-run
```

Equivalent standalone usage:

```bash
sysforge-organizer ./Downloads --dry-run
```

---

### Intentional Failure: Missing Target

```bash
sysforge-organizer ./does-not-exist
```

Expected output:

```text
Target directory does not exist: does-not-exist
```

---

### Intentional Failure: Bad Mode

```bash
sysforge-organizer ./Downloads --by color
```

Expected output:

```text
--by must be extension, date, or size.
```

---

# Runbook

## App 26 — Folder Organizer

**SysForge Group | Document 4 of 5**  
**Status: Accepted**

---

## Prerequisites

- Python 3.11 or newer.
- SysForge installed from the repository.
- Runtime dependencies installed.
- A target folder with files to organize.
- Permission to read and move files in the target folder.
- Permission to write SysForge state under `~/.sysforge` or `SYSFORGE_HOME`.

---

## Installation Procedure

From the SysForge repository root:

```bash
python -m pip install -e .
```

For development and tests:

```bash
python -m pip install -e ".[dev]"
```

Alternative dependency-first flow:

```bash
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps
```

---

## Configuration Steps

### 1. Choose a SysForge Home Directory

Default:

```text
~/.sysforge
```

Optional local testing override:

```bash
export SYSFORGE_HOME=.sysforge-dev
```

Windows Command Prompt:

```cmd
set SYSFORGE_HOME=.sysforge-dev
```

PowerShell:

```powershell
$env:SYSFORGE_HOME = ".sysforge-dev"
```

---

### 2. Review Default Rules

Default rules are packaged at:

```text
sysforge/data/default_organizer_rules.json
```

They classify common extensions into:

- Images,
- Docs,
- Code,
- Archives,
- Media,
- Other.

---

### 3. Optional Custom Rules

Create a custom rules file:

```json
{
  "extension_categories": {
    ".csv": "Data",
    ".json": "Data",
    ".py": "Python"
  },
  "extension_no_suffix_category": "NoExtension",
  "size_buckets": {
    "small": {"max_mb": 5},
    "large": {"max_mb": null}
  },
  "date_format": "%Y/%m"
}
```

Run with:

```bash
sysforge-organizer ./Downloads --rules ./rules.json
```

---

### 4. Optional Shared Config Rule Path

Set `organizer.rules_file` in the shared SysForge config:

```json
{
  "organizer": {
    "rules_file": "/absolute/path/to/rules.json"
  }
}
```

Then run:

```bash
sysforge-organizer ./Downloads
```

---

## Standard Operating Procedures

### SOP 1 — Safe First Run

Always start with a dry run:

```bash
sysforge-organizer ./Downloads --dry-run
```

Review planned destinations. If they look correct, run without `--dry-run`:

```bash
sysforge-organizer ./Downloads
```

---

### SOP 2 — Organize by Extension

```bash
sysforge-organizer ./Downloads --by extension
```

Use when a folder contains mixed file types.

---

### SOP 3 — Organize by Date

```bash
sysforge-organizer ./Downloads --by date
```

Use when the timeline matters, such as exports, reports, or screenshots.

---

### SOP 4 — Organize by Size

```bash
sysforge-organizer ./Downloads --by size
```

Use when separating small notes from large media or archive files.

---

### SOP 5 — Recursive Organization

```bash
sysforge-organizer ./Downloads --recursive --dry-run
```

Use carefully. Recursive mode may include files already inside subfolders.

---

### SOP 6 — Undo Latest Real Run

```bash
sysforge-organizer --undo
```

Use immediately after a real run if the result was not desired.

---

## Health Checks

### Command Availability

```bash
sysforge-organizer --help
```

Expected:

- Typer help appears.
- Options include `--by`, `--rules`, `--dry-run`, `--on-conflict`, `--include-hidden`, `--recursive`, and `--undo`.

---

### Unified CLI Availability

```bash
sysforge organize --help
```

Expected:

- same organizer options appear under the unified CLI.

---

### Dry-Run Check

```bash
mkdir -p /tmp/sysforge-organizer-check
echo hello > /tmp/sysforge-organizer-check/example.txt
sysforge-organizer /tmp/sysforge-organizer-check --dry-run
```

Expected:

- planned move appears,
- original file remains in place,
- a dry-run log is written.

---

### Real Move Check

```bash
sysforge-organizer /tmp/sysforge-organizer-check
```

Expected:

```text
/tmp/sysforge-organizer-check/Docs/example.txt
```

or another folder based on active rules.

---

### Undo Check

```bash
sysforge-organizer --undo
```

Expected:

- file is restored to the original path if no conflicts exist,
- undo log is written.

---

## Expected Output Samples

### Dry Run

```text
Planned moves
/tmp/downloads/a.txt -> /tmp/downloads/Docs/a.txt

Organizer summary
Moved: 1
Skipped: 0
Errors: 0
Total size processed: 6.0 B
Log file: /home/user/.sysforge/organizer/logs/organizer_20260508_101500.json
```

---

### Real Run

```text
Organizer summary
Moved: 1
Skipped: 0
Errors: 0
Total size processed: 6.0 B
Log file: /home/user/.sysforge/organizer/logs/organizer_20260508_101530.json
```

---

### Hidden File Skip

```text
Skipped hidden file: /home/user/Downloads/.env

Organizer summary
Moved: 0
Skipped: 1
Errors: 0
Total size processed: 0.0 B
Log file: /home/user/.sysforge/organizer/logs/organizer_20260508_101600.json
```

---

### Undo

```text
Undo log: /home/user/.sysforge/organizer/logs/organizer_undo_20260508_101700.json
Restored: 1
Skipped: 0
Errors: 0
```

---

## Known Failure Modes

### Failure Mode 1 — Target directory does not exist

**Symptom**

```text
Target directory does not exist: ./missing
```

**Cause**

The target path is missing or is not a directory.

**Resolution**

Create the directory or provide a correct path.

---

### Failure Mode 2 — Bad sort mode

**Symptom**

```text
--by must be extension, date, or size.
```

**Cause**

The `--by` value is invalid.

**Resolution**

Use one of:

```text
extension
date
size
```

---

### Failure Mode 3 — Bad conflict mode

**Symptom**

```text
--on-conflict must be rename, skip, or overwrite.
```

**Cause**

The conflict strategy is invalid.

**Resolution**

Use one of:

```text
rename
skip
overwrite
```

---

### Failure Mode 4 — No undo log exists

**Symptom**

```text
No organizer log found to undo.
```

**Cause**

No non-dry-run organizer log exists in the organizer log directory.

**Resolution**

Run a real organizer operation before using undo.

---

### Failure Mode 5 — Undo skips a file

**Symptom**

Undo summary shows skipped files.

**Cause**

The moved destination no longer exists, or the original path already exists.

**Resolution**

Inspect the undo log for the reason. Restore manually if needed.

---

### Failure Mode 6 — Permission denied

**Symptom**

Run summary shows errors, or the CLI exits with a file-system error.

**Cause**

The process lacks read/write permissions for files, destination folders, or SysForge logs.

**Resolution**

Run from a user account with appropriate permissions or choose a writable target and `SYSFORGE_HOME`.

---

### Failure Mode 7 — Unexpected classification

**Symptom**

Files move into `Other` or unexpected folders.

**Cause**

The extension is not mapped, the file has no suffix, or custom rules are wrong.

**Resolution**

Update the rules file and test with `--dry-run`.

---

## Troubleshooting Decision Tree

```text
Problem: Organizer did not behave as expected
|
+-- Did the command fail immediately?
|   |
|   +-- Yes: Check target path, --by, --on-conflict, and rules file JSON.
|   |
|   +-- No: Continue.
|
+-- Were files moved unexpectedly?
|   |
|   +-- Yes: Run sysforge-organizer --undo immediately.
|   |
|   +-- No: Continue.
|
+-- Were files skipped?
|   |
|   +-- Hidden or symlink messages?
|   |   |
|   |   +-- Yes: Use --include-hidden if appropriate; symlinks are intentionally skipped.
|   |
|   +-- Destination conflicts?
|       |
|       +-- Use --on-conflict rename, skip, or overwrite depending on goal.
|
+-- Did classification look wrong?
|   |
|   +-- Check active rules file.
|   +-- Test with --dry-run.
|   +-- Add extension_no_suffix_category for files without suffix.
|
+-- Did undo not restore everything?
    |
    +-- Inspect undo log.
    +-- Check whether destination files still exist.
    +-- Check whether original source paths are occupied.
```

---

## Dependency Failure Handling

### Typer Missing

If Typer is missing, the CLI will not import correctly.

Resolution:

```bash
python -m pip install -e .
```

or:

```bash
python -m pip install -r requirements.txt
```

---

### Invalid JSON Rules

If the rules file is invalid JSON, `load_json_file()` will raise a JSON decode error.

Resolution:

```bash
python -m json.tool rules.json
```

Fix the JSON syntax, then retry with `--dry-run`.

---

### SysForge Home Not Writable

If the app cannot create `~/.sysforge` or log directories, file writes may fail.

Resolution:

```bash
export SYSFORGE_HOME=/path/to/writable/folder
```

Then retry.

---

## Recovery Procedures

### Recover from Bad Real Run

1. Stop using the folder to avoid creating conflicts.
2. Run:

```bash
sysforge-organizer --undo
```

3. Review restored/skipped/error counts.
4. Inspect the undo log if any files were skipped.
5. Manually restore files that could not be safely moved.

---

### Recover from Bad Rules

1. Do not run a real organization yet.
2. Run with dry-run:

```bash
sysforge-organizer ./Downloads --rules ./rules.json --dry-run
```

3. Fix rules.
4. Repeat until planned moves look correct.
5. Run without `--dry-run`.

---

### Recover from Overwrite Mistake

If files were overwritten, undo may not restore overwritten destination contents because overwrite deletes the existing destination before moving the source.

Recovery options:

- restore from backup,
- recover from version control if applicable,
- inspect organizer logs to identify affected paths.

Recommendation: avoid `--on-conflict overwrite` unless the folder is backed up.

---

## Logging Reference

### Organizer Run Log

Path pattern:

```text
~/.sysforge/organizer/logs/organizer_YYYYMMDD_HHMMSS.json
```

Contains:

- timestamp,
- target,
- mode,
- dry-run flag,
- conflict mode,
- messages,
- moves,
- summary.

### Organizer Undo Log

Path pattern:

```text
~/.sysforge/organizer/logs/organizer_undo_YYYYMMDD_HHMMSS.json
```

Contains:

- timestamp,
- original log path,
- undo actions,
- restored/skipped/error summary.

### Central SysForge Log

Path:

```text
~/.sysforge/logs/sysforge.log
```

Contains app-level log entries from `sysforge.organizer`.

---

## Maintenance Notes

- Keep default rules broad but conservative.
- Add new extension mappings only when they are obvious.
- Prefer `rename` as the safest default conflict strategy.
- Keep undo simple and predictable.
- Avoid adding content-based classification until metadata-based behavior is fully stable.
- Preserve JSON log compatibility if future versions add fields.
- Expand tests around undo, hidden files, symlinks, recursive scans, and conflict strategies.

---

# Lessons Learned

## App 26 — Folder Organizer

**SysForge Group | Document 5 of 5**  
**Status: Accepted**

---

## Project Summary

The Folder Organizer is a practical file-system automation tool in SysForge. It organizes files in a target folder by extension, modified date, or size. It supports dry-run previews, conflict strategies, custom JSON rules, hidden-file filtering, recursive scanning, movement logs, and undo.

This app is a stronger engineering exercise than a simple “move files by extension” script because it handles the risks that appear when code touches a user’s file system. It demonstrates that even a small utility needs careful design around safety, observability, and recovery.

---

## Original Goals vs. Actual Outcome

### Original Goals

- Build a CLI folder organizer.
- Sort files into subfolders.
- Support multiple organization modes.
- Avoid destructive behavior.
- Leave a log of what happened.
- Fit into SysForge’s shared CLI and state model.

### Actual Outcome

The final app meets those goals and adds useful operational details:

- extension/date/size organization,
- dry-run mode,
- rename/skip/overwrite conflict handling,
- symlink and hidden-file safeguards,
- JSON run logs,
- undo from latest real run,
- SysForge shared config support,
- unified CLI integration.

The final result is not just an algorithm exercise. It is a local operations tool with real user-safety considerations.

---

## Technical Decisions That Paid Off

### 1. Separating classification from movement

Keeping `resolve_relative_folder()` separate from `perform_move()` made the app easier to reason about. Classification can be tested without actually moving files. Movement can be tested separately.

This separation also helped the CLI support dry-run mode cleanly.

---

### 2. Using JSON rules

A JSON rules file makes the organizer flexible without requiring code edits. Users can add new extension categories, change date folder formats, and define different size buckets.

This was a good trade-off because the problem domain is naturally configuration-driven.

---

### 3. Supporting dry-run mode

Dry-run mode is one of the most important features. A file organizer can cause real inconvenience if it moves files incorrectly. Previewing planned moves gives the user a chance to catch bad rules or a wrong target directory.

This is a practical lesson: when code changes user data, preview mode is not just nice to have. It is part of responsible design.

---

### 4. Logging every run as JSON

The JSON log is useful for debugging, audit, and undo. It also makes the app’s behavior more transparent.

The log format records status per file, which means a run can partially succeed and still leave enough information to understand what happened.

---

### 5. Undo based on reverse log replay

Undo is intentionally built from the movement log. This creates a simple recovery model:

- if a file was moved,
- and the moved file still exists,
- and the original path is available,
- move it back.

This is not perfect, but it is understandable and reliable enough for the project scope.

---

### 6. Skipping symlinks

Skipping symlinks avoids complicated edge cases. Symlinks can point outside the target directory, create cycles, or represent important environment links. For a beginner-to-intermediate utility, skipping them is the safer choice.

---

### 7. Using SysForge shared paths

Using SysForge’s shared path helpers made logs and config consistent with the other apps. It also made tests easier because `SYSFORGE_HOME` can isolate state.

---

## Technical Decisions That Created Debt

### 1. Rule validation is minimal

The app accepts loosely structured JSON rules. This works for a small tool, but invalid rule data can lead to odd behavior.

A future version should define and validate a formal schema.

---

### 2. Undo only targets the latest real run

This keeps the interface simple, but it limits recovery. If the user wants to undo an older run, they need to inspect logs manually.

A future version could support:

```bash
sysforge-organizer undo --log path/to/log.json
```

---

### 3. Recursive mode has no exclusion rules

Recursive mode can scan folders that were previously created by the organizer. That may be surprising if users run the command repeatedly.

A future version should allow exclude patterns or skip known category folders.

---

### 4. Conflict defaults are only partially config-driven

The shared config includes `default_conflict_strategy`, but the CLI currently defaults `--on-conflict` to `rename` directly. The explicit CLI default is safe, but the config value is not fully used as the dynamic default.

A future version could resolve the default conflict strategy from shared config when the user does not pass `--on-conflict`.

---

### 5. Logs contain absolute paths

Absolute paths are useful for undo but can reveal sensitive folder structure. This is acceptable for a local tool, but users should avoid sharing logs.

A future version could optionally redact home directory prefixes in display output while keeping full paths internally for undo.

---

## What Was Harder Than Expected

### Conflict handling

At first, moving files sounds simple. But destination conflicts introduce several design questions:

- Should existing files be overwritten?
- Should the move be skipped?
- Should a new name be generated?
- What happens if a race creates the destination after planning?

The final design handles normal cases and has a fallback for unexpected `FileExistsError`, but this area is more complex than it first appears.

---

### Undo safety

Undo cannot blindly move files back. It needs to check whether the moved file still exists and whether the original source path is free.

This led to an important lesson: recovery logic often needs as much care as the main operation.

---

### Recursive scans

Recursive scans make a simple file organizer more complex. Without exclusions, recursive mode can include files in folders that may also be destinations.

The app handles recursive scanning, but future versions need more policy around what to skip.

---

### Hidden-file behavior

Hidden-file detection is platform-specific. Dotfiles are simple on Unix-like systems, but Windows hidden attributes require different handling. Using the shared `is_hidden_path()` helper avoided duplicating that logic inside the organizer.

---

## What Was Easier Than Expected

### Using `pathlib`

`pathlib.Path` made path manipulation readable. Expressions like:

```python
base_dir / relative_folder / source.name
```

are much clearer than string concatenation.

---

### JSON logs

JSON was a natural fit for run logs. It supports nested structures, lists of moves, and summary metadata without requiring a database.

---

### Typer CLI structure

Typer made the CLI readable and declarative. Options and arguments are defined close to the function that handles them.

---

### Unit testing classification

Functions like `resolve_relative_folder()` and `choose_destination()` are easy to test because they have clear inputs and outputs.

This reinforced the value of decomposing code before testing.

---

## Python-Specific Learnings

### `pathlib.Path` improves file-system code

Using `Path` objects makes code safer and easier to understand than raw strings.

Important patterns included:

```python
target.iterdir()
target.rglob("*")
path.suffix.lower()
destination.parent.mkdir(parents=True, exist_ok=True)
```

---

### `shutil.move()` is the right abstraction for moves

`shutil.move()` works across directories and file systems. It is more appropriate than trying to use low-level rename behavior everywhere.

---

### `datetime.fromtimestamp()` is useful for date sorting

File modified times are numeric timestamps. Converting them to `datetime` allows easy formatting into folder paths.

---

### Dictionaries are flexible but need validation

JSON-loaded dictionaries are convenient, but they can contain unexpected structures. This app handles some bad values, but a stricter schema would improve confidence.

---

### Exceptions should be scoped carefully

`run_organizer()` catches exceptions per file so that one bad file does not stop the entire run. This is better than wrapping the whole operation in one large try/except.

---

## Architecture Insights

### File-system tools need safety features early

For a tool that changes files, safety is not an advanced feature. It belongs in the first design:

- dry-run,
- logs,
- conflict handling,
- undo,
- skipped symlink behavior.

This app taught that “works on happy path” is not enough for file automation.

---

### Logs can double as recovery state

The movement log is not only for humans. It is also the data source for undo. This is a useful pattern for small systems: an append-like audit record can support later recovery without adding a full database.

---

### Shared infrastructure helps a toolkit feel coherent

Because Organizer uses SysForge shared paths, config, and logging, it behaves like part of a larger system instead of an isolated script.

This supports the broader SysForge architectural goal.

---

### The orchestration function is the center of the design

`run_organizer()` is where the app’s workflow is visible. It ties together rules, candidate files, classification, destination selection, movement, and logging. Keeping this function readable is important because it is the easiest place to understand the full system.

---

## Testing Gaps

Current tests cover important pieces:

- extension folder resolution,
- rename-on-conflict destination selection,
- sorted size buckets,
- no-suffix extension behavior,
- missing target validation,
- real movement by extension,
- isolated SysForge home fixture.

Additional useful tests would include:

1. Dry-run does not move files.
2. Hidden files are skipped by default.
3. `--include-hidden` includes hidden files.
4. Symlinks are skipped.
5. Date mode creates expected folder paths.
6. `overwrite` conflict mode removes destination and moves source.
7. `skip` conflict mode leaves source unchanged.
8. Undo restores a real run.
9. Undo skips safely when original source path exists.
10. Undo skips safely when moved destination is gone.
11. Recursive mode scans nested files.
12. Custom shared config rule path is respected.
13. CLI tests for `--help`, bad `--by`, bad `--on-conflict`, and `--undo`.

---

## Reusable Patterns Identified

### Dry-run before mutation

This pattern can apply to many CLI tools:

1. compute planned changes,
2. display or log them,
3. only mutate when dry-run is false.

---

### JSON action logs

The move action structure could be reused for other tools that modify files:

```json
{
  "source": "...",
  "destination": "...",
  "status": "...",
  "strategy_used": "..."
}
```

---

### Reverse replay undo

If a tool records reversible actions, undo can often process those actions in reverse order.

---

### Rule-driven classification

The same pattern could be used for other apps:

- classify files,
- classify logs,
- classify events,
- classify reports.

Keep policy in JSON and mechanics in Python.

---

### Conflict strategy abstraction

The `rename`, `skip`, and `overwrite` strategy set is reusable anywhere files are written into a destination folder.

---

## If I Built This Again

I would keep:

- Typer,
- `pathlib`,
- dry-run mode,
- JSON logs,
- default packaged rules,
- undo from logs,
- shared SysForge paths.

I would improve:

1. Add a schema for rules.
2. Add CLI option to undo a specific log.
3. Add exclusion patterns.
4. Add a safer confirmation prompt for `overwrite`.
5. Add a `--plan-file` option to save dry-run plans separately.
6. Add a command to print active rules.
7. Add more CLI tests with Typer’s test runner.
8. Support a `--max-files` safety guard for large folders.
9. Add a summary grouped by destination folder.
10. Consider storing relative paths in logs when possible, with an absolute target root.

---

## Open Questions

1. Should recursive mode automatically skip known destination category folders?
2. Should undo support older logs by path?
3. Should the app refuse overwrite unless `--force` is also passed?
4. Should logs store checksums to detect file changes before undo?
5. Should classification support MIME type detection?
6. Should date mode allow created date instead of modified date?
7. Should the app support preview output in JSON for scripting?
8. Should shared config control the default conflict strategy?
9. Should hidden files be included only by explicit glob patterns instead of a broad flag?
10. Should logs redact the user’s home path by default?

---

## Final Reflection

Folder Organizer is a strong example of how a simple automation idea becomes a real engineering exercise once safety and recovery are considered. Moving files is easy; moving files responsibly is the important part.

The project demonstrates practical Python skills: `pathlib`, `shutil`, JSON I/O, CLI parsing, file metadata, per-item error handling, and testable decomposition. It also demonstrates architectural thinking through rule-driven behavior, shared SysForge state, and undo based on movement logs.

The best lesson from this app is that local utility scripts should still be designed with respect for user data. Dry-run mode, conflict handling, and logs are not overengineering here. They are what make the tool trustworthy.
