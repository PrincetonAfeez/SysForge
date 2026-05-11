# Architecture Decision Record

## App 23 — Configuration Manager

**SysForge Group | Document 1 of 5**  
**Status: Accepted**

## Title

Adopt a JSON-first configuration manager with dot-notation access, environment overrides, schema-subset validation, diffing, and template initialization.

## Date

2026-05-08

## Context

The Configuration Manager is App 23 in the SysForge toolkit. Unlike earlier single-purpose projects, this app lives inside a larger shared package and is exposed both as a standalone console command and as part of the unified SysForge CLI. Its job is to inspect, update, validate, compare, and initialize JSON configuration files used by small developer tools.

The problem is intentionally scoped: it is not a full production configuration platform, not a full JSON Schema validator, and not a secrets manager. It is a practical CLI utility for working with JSON files in a predictable way. The core value is in learning how to safely manipulate nested configuration data, apply environment-variable overrides, validate a constrained schema model, and integrate a small app into a multi-command package without duplicating shared helpers.

The implementation is centered in `sysforge/config/config.py`, with support functions imported from SysForge shared modules. The app uses Typer for the command surface, JSON files for data, dotted keys for nested values, and packaged templates for starter configuration files.

## Decision Drivers

- Keep runtime behavior understandable and inspectable.
- Use JSON as the configuration format because it is simple, standard, and available through Python's standard library.
- Support common operations: get, set, list, validate, diff, and init.
- Avoid copying shared SysForge utilities into this app.
- Preserve scope discipline by implementing a documented subset of schema validation instead of full JSON Schema.
- Make writes safer through atomic updates and backup files where appropriate.
- Support CLI automation by returning meaningful exit codes on failures.
- Demonstrate architecture growth from standalone apps into a shared-package CLI toolkit.

## Options Considered

### Option 1 — Treat configuration as plain text

**Chosen:** No.

This would have allowed simple search-and-replace operations, but it would be unsafe for nested structures and would not preserve JSON semantics. It would also make validation and diffing much harder.

### Option 2 — Use JSON plus dotted-key helpers

**Chosen:** Yes.

JSON is available in the standard library, and dotted keys such as `database.host` make nested values easy to address from a CLI. This keeps the app practical without adding a database, parser generator, or third-party configuration system.

### Option 3 — Use a full JSON Schema dependency

**Chosen:** No.

A full schema validator would be more complete, but it would also hide the learning value. The project already uses a third-party CLI framework, so keeping validation logic local helps demonstrate recursion, type checks, default injection, numeric bounds, enum checks, and array item validation.

### Option 4 — Implement a schema subset directly

**Chosen:** Yes.

The app implements enough schema behavior for beginner-to-intermediate configuration validation: `type`, `properties`, `required`, `default`, numeric `min`/`max`, `enum`, array `items`, `minItems`, and `maxItems`. This is intentionally smaller than Draft JSON Schema.

### Option 5 — Make every command use the shared SysForge config only

**Chosen:** No.

The tool is more useful if it can operate on any JSON file passed with `--file` or positional arguments. Shared SysForge configuration still matters for the unified CLI and package layout, but the app itself should remain general-purpose.

### Option 6 — Let environment variables override dotted config paths

**Chosen:** Yes.

Environment overrides are a realistic configuration-management feature. Mapping `database.host` to `APP_DATABASE_HOST` makes the behavior deterministic and easy to document. It also shows the difference between loaded configuration and persisted configuration.

### Option 7 — Write directly to the target file

**Chosen:** No.

Direct writes are simpler, but a CLI that edits config files should reduce corruption risk. The app uses shared JSON-writing helpers with atomic writes and, for `set`, backups.

### Option 8 — Copy config helpers into the app package

**Chosen:** No.

SysForge is a multi-app monorepo. Reusing `common.py`, `logging_utils.py`, and `sysforge_paths.py` is a better architectural choice than duplicating helpers. This aligns with the roadmap's shared-core expectation.

## Decision

Build the Configuration Manager as a Typer-based SysForge subpackage with six primary commands:

- `get` for reading a dotted key from a JSON object.
- `set` for writing a parsed CLI value to a dotted key.
- `list` for flattening and printing all keys.
- `validate` for schema-subset validation and optional default writing.
- `diff` for comparing flattened key/value pairs between two JSON files.
- `init` for copying a packaged template to a chosen output path.

Use shared SysForge utility functions for JSON IO, dotted-key lookup, dotted-key mutation, value parsing, logging, and home-layout setup. Use a packaged template directory under `sysforge/config/templates/` and expose the app through both `sysforge-config` and the unified `sysforge config` command.

## Rationale

This design matches the project's learning goals well. The app has a clear user-facing purpose, but the interesting work is architectural: nested data traversal, recursive validation, CLI boundary handling, safe file writes, environment-derived overrides, and integration into a larger toolkit.

The dotted-key model is a strong fit for CLI usage. Users can type `database.host` more easily than a JSON Pointer or a Python expression. The flattened view also makes `list` and `diff` straightforward.

The schema-subset decision is especially important. It keeps the app honest about what it validates while still showing real recursive algorithm design. It also prevents the project from becoming a wrapper around a third-party schema library.

## Trade-offs Accepted

- The validator does not implement the full JSON Schema specification.
- Environment overrides use a fixed `APP_` prefix and may collide when different dotted paths normalize to the same environment variable name.
- The app assumes JSON object roots for configuration files; non-object JSON roots are rejected.
- `set` creates missing parent dictionaries, but it cannot set under an existing scalar value.
- `diff` compares flattened values rather than producing a structural patch.
- Template discovery is name-based and limited to packaged templates.
- The app handles configuration values, not encrypted secrets.

## Consequences

### Positive consequences

- The command set is small but useful.
- The implementation demonstrates recursion, nested mutation, data normalization, validation, and CLI error handling.
- Shared utilities reduce duplication across SysForge apps.
- The app can be tested through pure functions and CLI-level behavior.
- Atomic writes and backups make file editing safer than naïve overwrites.

### Negative consequences

- Users familiar with full JSON Schema may expect unsupported keywords to work.
- Environment override behavior must be clearly documented to avoid confusion.
- Because the tool works on arbitrary JSON files, it cannot know which keys are semantically meaningful without a schema.
- A template catalog would be easier to browse if there were a command that listed available templates.

## Superseded By

Not superseded.

## Constitution Alignment

This project fits the roadmap's medium-complexity stage. It is still a focused CLI app, but it shows growth beyond basic parsing by using a shared package structure, reusable utilities, nested state manipulation, validation rules, file safety, and integration into a multi-command toolkit. It is appropriate in scope as long as the documentation stays clear that the schema validator is intentionally partial.

---

# Technical Design Document

## App 23 — Configuration Manager

**SysForge Group | Document 2 of 5**  
**Status: Accepted**

## Purpose & Scope

The Configuration Manager is a JSON configuration utility inside the SysForge package. It provides a CLI for reading, writing, listing, validating, diffing, and initializing configuration files.

The app is in scope for:

- JSON object configuration files.
- Dot-notation access to nested values.
- Environment variable overrides while reading config files.
- Basic schema-subset validation.
- Applying schema defaults in memory, and optionally writing them back.
- Comparing two config files by flattened key/value pairs.
- Copying a packaged template into a new config file.
- Safe file writes through atomic updates and backups.

The app is out of scope for:

- Full JSON Schema validation.
- YAML, TOML, INI, XML, or HCL support.
- Secret encryption or secret redaction.
- Multi-user config management.
- Remote config stores.
- Transactional editing across multiple files.
- Interactive editing in a text UI.

## System Context

The Configuration Manager is one app inside the broader SysForge toolkit.

```text
User / shell
  |
  | sysforge-config ...
  | sysforge config ...
  v
sysforge.config.config Typer app
  |
  +-- sysforge.common
  |     - load_json_file
  |     - write_json_file
  |     - flatten_dict
  |     - get_nested_value
  |     - set_nested_value
  |     - parse_cli_value
  |     - print_error
  |
  +-- sysforge.logging_utils
  |     - get_logger("sysforge.config")
  |
  +-- sysforge.sysforge_paths
  |     - ensure_home_layout
  |     - PACKAGE_ROOT
  |
  +-- packaged templates
  |     - sysforge/config/templates/web-app.json
  |
  +-- target JSON config files
```

The root SysForge CLI imports the config Typer app and mounts it under the `config` subcommand. The packaging metadata also exposes a standalone `sysforge-config` console script.

## Component Breakdown

### `sysforge/config/config.py`

Primary implementation module. It defines:

- The Typer app object.
- Config loading and environment override logic.
- Schema validation functions.
- Diffing helpers.
- Template lookup.
- CLI command handlers.

### `sysforge/config/__init__.py`

Package marker for the config subpackage. It keeps the package importable without adding public API exports.

### `sysforge/config/templates/web-app.json`

Packaged starter template. It contains a sample web-app structure with `app`, `database`, and `features` sections.

### `sysforge/common.py`

Shared utility module used by this app. The important functions for Config Manager are:

- `load_json_file(path)`
- `write_json_file(path, data, atomic=True, backup=True)`
- `flatten_dict(data)`
- `get_nested_value(data, dotted_key)`
- `set_nested_value(data, dotted_key, value)`
- `parse_cli_value(raw_value)`
- `print_error(message, exit_code)`

### `sysforge/logging_utils.py`

Creates a central SysForge logger. The config app uses this to log write and initialization operations.

### `sysforge/sysforge_paths.py`

Defines package and home-layout paths. The config app uses `PACKAGE_ROOT` for template lookup and `ensure_home_layout()` before writing or initializing files.

### Root CLI integration

`sysforge.__main__` imports the config Typer app and mounts it under `sysforge config`. Packaging metadata exposes `sysforge-config` as a standalone entry point.

## Module Dependency Graph

```text
sysforge.config.config
  ├── json
  ├── os
  ├── shutil
  ├── pathlib.Path
  ├── typer
  ├── sysforge.common
  │     ├── json
  │     ├── os
  │     ├── shutil
  │     └── pathlib.Path
  ├── sysforge.logging_utils
  │     ├── logging
  │     └── sysforge.sysforge_paths
  └── sysforge.sysforge_paths
        ├── os
        ├── shutil
        └── pathlib.Path
```

No config-specific third-party dependency exists beyond Typer, which is already part of SysForge's runtime dependency set.

## Core Algorithms & Logic

### Config file loading

`load_config_file(path, apply_env=True)` performs three steps:

1. Load JSON from disk using the shared `load_json_file()` helper.
2. Require the root JSON value to be a dictionary.
3. Optionally apply environment-variable overrides.

If the root is not a JSON object, the function raises a `ValueError`. This keeps dotted-key behavior predictable.

### Environment override mapping

`apply_environment_overrides(data)`:

1. Deep-copies the data using JSON serialization and deserialization.
2. Flattens the original dictionary into dotted keys.
3. Converts each dotted key to an environment variable name:

```text
database.host -> APP_DATABASE_HOST
database.port -> APP_DATABASE_PORT
app.debug     -> APP_APP_DEBUG
```

4. Warns when multiple dotted paths map to the same environment variable.
5. If the environment variable is present, parses the value with `parse_cli_value()`.
6. Writes the parsed value into the copied structure with `set_nested_value()`.

This means environment variables affect reads, but they do not automatically mutate the file on disk.

### CLI value parsing

The shared parser converts strings into common JSON-compatible values:

- `true` / `false` -> booleans
- `null` -> `None`
- integer-looking text -> `int`
- float-looking text -> `float`
- JSON object/list-looking text -> parsed JSON when valid
- anything else -> string

This is important for the `set` command because CLI arguments are strings by default.

### Dot-notation lookup

`get_nested_value(data, dotted_key)` walks through the dictionary one key segment at a time. If any segment is missing or the current value is not a dictionary, it raises `KeyError`.

Example:

```text
key: database.host
path: data["database"]["host"]
```

### Dot-notation mutation

`set_nested_value(data, dotted_key, value)` walks through every segment except the final segment, creating dictionaries where needed. If a path tries to descend under a scalar value, it raises `ValueError`.

Example:

```text
set database.pool_size 10
```

can create or update:

```json
{
  "database": {
    "pool_size": 10
  }
}
```

but cannot set `database.host.name` if `database.host` is currently a string.

### Flattened listing

`list` loads the JSON object, flattens it into dotted keys, sorts the keys, and prints each key/value pair.

Example output shape:

```text
app.debug = True
database.host = 'localhost'
database.port = 5432
```

### Schema-subset validation

`validate_against_schema(value, schema, key_path="root")` is recursive.

Supported schema features:

- `type`: object, string, integer, number, boolean, array
- `properties`: object child schemas
- `required`: required object keys
- `default`: default value for missing child properties
- `min` / `max`: numeric bounds
- `enum`: allowed values
- `items`: array item schema
- `minItems` / `maxItems`: array length checks

Object validation:

1. Check object type.
2. Check required keys.
3. Copy the current object.
4. For each declared property:
   - If missing and a default exists, add the default.
   - If present, recursively validate and normalize it.
5. Return `(errors, updated_object)`.

Array validation:

1. Check array type.
2. Check length bounds.
3. Recursively validate each item if an `items` schema is present.
4. Return `(errors, updated_list)`.

Numeric validation:

1. Check `min` and `max` when present.
2. Add errors when bounds are violated.

Enum validation:

1. Check that the value appears in the schema's `enum` list.

The validator stops early after a type mismatch because deeper checks would be misleading on the wrong value type.

### Default application

Defaults are applied in memory during validation. The CLI prints a message when the validated data differs from the input data. If the user passes `--write-defaults`, the updated value is written back to the config file.

This separates validation from mutation unless the user explicitly requests persistence.

### Diffing

`diff_configs(left, right)`:

1. Flattens both config dictionaries.
2. Calculates keys added in the right file.
3. Calculates keys removed from the right file.
4. Calculates keys whose values changed.
5. Returns three sorted lists: `added`, `removed`, and `changed`.

The CLI prints each section even when empty.

### Template initialization

`template_path_for_name(name)` builds a path under:

```text
sysforge/config/templates/{name}.json
```

If the template does not exist, it calls `print_error()`, which exits the CLI. `init` copies the template to the requested output path.

## Data Structures

### Configuration object

Runtime type:

```python
dict[str, Any]
```

This represents the loaded JSON configuration root.

### Flattened configuration

Runtime type:

```python
dict[str, Any]
```

Keys are dotted paths. Values are leaf values.

### Schema object

Runtime type:

```python
dict[str, Any]
```

This is a limited schema representation. It is intentionally not modeled as a class because the schema is small and directly mirrors JSON.

### Validation return value

Runtime type:

```python
tuple[list[str], Any]
```

The first element is a list of human-readable errors. The second element is the validated or default-augmented value.

### Diff result

Runtime type:

```python
dict[str, list[str]]
```

Shape:

```python
{
    "added": [...],
    "removed": [...],
    "changed": [...],
}
```

## State Management

The app has no long-running state. Each CLI invocation:

1. Loads one or more JSON files.
2. Performs the requested operation.
3. Writes a file only for `set`, `validate --write-defaults`, or `init`.
4. Exits.

Persistent state lives in user-specified JSON config files. SysForge shared home state may also be created by `ensure_home_layout()` when writing or initializing.

Environment overrides are process-level state. They affect loaded values only when `apply_env=True`.

## Error Handling Strategy

### User-facing command errors

The CLI catches common issues and calls `print_error()`, which prints a red error message to stderr and exits with a Typer exit code.

Examples:

- Missing config file -> exit code 2 in read/validate/diff commands.
- Missing dotted key -> exit code 1.
- Invalid JSON -> exit code 2.
- Invalid type or unsupported path mutation -> exit code 1 or 2 depending on command.
- Missing template -> exit code 1.

### Validation errors

Schema validation errors are printed line by line, then the command exits with code 1.

### File operation errors

`OSError` and `shutil.Error` are caught in file-writing and template-copying contexts and reported as operational failures.

### Logging

Successful `set` and `init` operations are logged through the `sysforge.config` logger. SysForge's logging utility writes to the central log file and console handlers according to environment flags.

## External Dependencies

### Runtime dependencies

SysForge runtime dependencies include:

| Dependency | Use in this app |
|---|---|
| `typer>=0.12` | CLI command definition and execution |
| `rich>=13.7` | Indirectly used by Typer for console rendering |
| `markdown>=3.6` | SysForge-wide dependency, not used directly by config app |
| `pygments>=2.18` | SysForge-wide dependency, not used directly by config app |
| `psutil>=5.9` | SysForge-wide dependency, not used directly by config app |

The app's own data handling uses Python standard-library modules such as `json`, `os`, `shutil`, and `pathlib`.

### Development dependencies

SysForge dev tooling includes pytest, pytest-cov, Ruff, Mypy, and type stubs. The project README documents a verification workflow using formatting, linting, type checking, compileall, and pytest.

## Concurrency Model

The Configuration Manager is single-process and synchronous. It does not use threads, async IO, multiprocessing, or background jobs.

Atomic writes reduce partial-write risk, but the app does not implement file locks. Two simultaneous writes to the same config file could still race.

## Design Patterns Used

### Command pattern

Each Typer command represents a discrete operation.

### Adapter-like shared helper use

The app delegates JSON IO, nested-key handling, and CLI value parsing to shared SysForge helpers instead of implementing all details locally.

### Recursive validation

The schema validator uses recursive traversal for nested objects and arrays.

### Snapshot diff

Diffing is implemented by flattening both input files into comparable snapshots.

### Template method by file copy

`init` uses a simple template-copy pattern: select packaged template, copy to output path, and report success.

## Known Limitations

- Schema validation is intentionally partial.
- There is no `templates list` command.
- There is no delete/unset command for config keys.
- There is no rename command for keys.
- There is no merge command beyond schema default application.
- Environment overrides are read-time only and are not automatically persisted.
- Environment override collisions are only logged as warnings.
- Atomic writes do not include cross-process file locking.
- The app does not redact sensitive values in `list` or `diff`.
- The app only supports JSON object roots.

---

# Interface Design Specification

## App 23 — Configuration Manager

**SysForge Group | Document 3 of 5**  
**Status: Accepted**

## Invocation Syntax

The Configuration Manager can be invoked through either the standalone command or the unified SysForge command.

```bash
sysforge-config <command> [options]
```

or:

```bash
sysforge config <command> [options]
```

The standalone entry point is mapped to `sysforge.config.config:main`. The unified CLI mounts the same Typer app under the `config` command.

## Command Summary

| Command | Purpose |
|---|---|
| `get` | Read one dotted key from a JSON config file |
| `set` | Write one dotted key/value pair to a JSON config file |
| `list` | Print flattened key/value pairs |
| `validate` | Validate a config against the supported schema subset |
| `diff` | Compare two config files by flattened keys |
| `init` | Copy a packaged template to a new config file |

## Argument Reference

### Global interface

There is no config-app-specific global option. Global SysForge options such as `--verbose`, `--quiet`, `--config`, and `--version` belong to the root `sysforge` command, not the standalone `sysforge-config` command.

### `get`

```bash
sysforge-config get KEY --file CONFIG_FILE
```

| Name | Type | Required | Default | Accepted values | Description |
|---|---:|---:|---:|---|---|
| `key` | string | yes | none | dotted key | Nested key to read, such as `database.host` |
| `--file` | path | yes | none | JSON file path | Config file to load |

### `set`

```bash
sysforge-config set KEY VALUE --file CONFIG_FILE
```

| Name | Type | Required | Default | Accepted values | Description |
|---|---:|---:|---:|---|---|
| `key` | string | yes | none | dotted key | Nested key to update |
| `value` | string parsed to JSON-like value | yes | none | strings, numbers, booleans, null, JSON objects/lists | Value to write |
| `--file` | path | yes | none | JSON file path | Config file to update or create |

### `list`

```bash
sysforge-config list --file CONFIG_FILE
```

| Name | Type | Required | Default | Accepted values | Description |
|---|---:|---:|---:|---|---|
| `--file` | path | yes | none | JSON file path | Config file to flatten and print |

### `validate`

```bash
sysforge-config validate CONFIG_FILE --schema SCHEMA_FILE [--write-defaults]
```

| Name | Type | Required | Default | Accepted values | Description |
|---|---:|---:|---:|---|---|
| `file` | path | yes | none | JSON config file | Config file to validate |
| `--schema` | path | yes | none | JSON schema-subset file | Schema file to validate against |
| `--write-defaults` | boolean flag | no | false | present / absent | Persist default-augmented config after successful validation |

### `diff`

```bash
sysforge-config diff LEFT_FILE RIGHT_FILE
```

| Name | Type | Required | Default | Accepted values | Description |
|---|---:|---:|---:|---|---|
| `left_file` | path | yes | none | JSON config file | Baseline file |
| `right_file` | path | yes | none | JSON config file | Comparison file |

### `init`

```bash
sysforge-config init --template TEMPLATE --output OUTPUT_FILE
```

| Name | Type | Required | Default | Accepted values | Description |
|---|---:|---:|---:|---|---|
| `--template` | string | yes | none | packaged template name | Template name under `sysforge/config/templates` without `.json` |
| `--output` | path | no | `app.json` | output file path | Destination file to create |

## Input Contract

### Config files

- Must be valid JSON.
- Must contain a JSON object at the root for commands that load config files.
- Can contain nested objects, arrays, strings, booleans, numbers, and nulls.

### Dotted keys

- Use period separators.
- Each path segment represents a JSON object key.
- Example: `database.host` means `config["database"]["host"]`.

### CLI values

`set` parses values into JSON-like types:

| Raw CLI value | Parsed value |
|---|---|
| `true` | `True` |
| `false` | `False` |
| `null` | `None` |
| `5432` | integer |
| `3.14` | float |
| `{"a":1}` | object |
| `[1,2]` | array |
| `localhost` | string |

### Schema files

Schema files must be JSON objects. Supported keywords include:

- `type`
- `properties`
- `required`
- `default`
- `min`
- `max`
- `enum`
- `items`
- `minItems`
- `maxItems`

Unsupported schema keywords are ignored because the validator only checks the subset it understands.

### Environment overrides

When loading with environment overrides enabled, flattened keys map to environment variables using this shape:

```text
APP_<DOTTED_KEY_WITH_DOTS_AS_UNDERSCORES_UPPERCASED>
```

Examples:

```text
database.host -> APP_DATABASE_HOST
app.debug     -> APP_APP_DEBUG
```

The `get` and `list` commands apply environment overrides. The `set`, `validate`, and `diff` paths disable overrides where persisted-file accuracy matters.

## Output Contract

### `get`

- Prints the resolved value.
- Dictionaries and lists are printed as pretty JSON.
- Scalars are printed directly.

Example:

```text
localhost
```

### `set`

Prints a confirmation:

```text
Updated database.port in app.json
```

Also writes the updated JSON file and creates a backup when the file already exists.

### `list`

Prints sorted flattened keys:

```text
app.debug = True
app.name = 'sample-web-app'
database.host = 'localhost'
database.port = 5432
features.reports = False
features.signup = True
```

### `validate`

On success:

```text
Validation passed.
```

If defaults were applied in memory:

```text
Defaults were applied in memory during validation.
```

If `--write-defaults` is passed:

```text
Wrote merged config to app.json
```

On validation failure, prints one error per line:

```text
root.database.port: expected integer, got str
root.mode: value 'devv' is not in allowed options ['dev', 'prod']
```

### `diff`

Always prints `ADDED`, `REMOVED`, and `CHANGED` sections.

Example:

```text
ADDED
- database.pool_size: 10
REMOVED
- features.reports: False
CHANGED
- database.host: 'localhost' -> 'prod-db.internal'
```

### `init`

Prints:

```text
Created starter.json
```

## Exit Code Reference

| Exit code | Meaning |
|---:|---|
| 0 | Command completed successfully |
| 1 | User-level error, validation failure, missing key, invalid mutation, missing template |
| 2 | File-level or parse-level error, such as missing input file or invalid JSON |

Some exact exit behavior is controlled by Typer and the shared `print_error()` helper.

## Error Output Behavior

Errors are printed to stderr using Typer's colored output. Examples include:

```text
Config file not found: app.json
```

```text
Key not found: database.password
```

```text
Template not found: unknown-template
```

Validation errors are printed to stdout before exiting with code 1 because they are report content rather than a single operational exception.

## Environment Variables

| Variable | Description |
|---|---|
| `APP_<KEY>` | Overrides flattened config keys during read operations |
| `SYSFORGE_HOME` | Changes where SysForge stores shared home state and logs |
| `SYSFORGE_CONFIG` | Used by root shared config loading when running through `sysforge` |
| `SYSFORGE_VERBOSE=1` | Enables more verbose logging through the root CLI |
| `SYSFORGE_QUIET=1` | Reduces console logging through the root CLI |

## Configuration Files

The app operates on user-provided JSON config files. It also ships packaged templates under:

```text
sysforge/config/templates/
```

Known packaged template:

```text
web-app.json
```

The `web-app` template includes:

- `app.name`
- `app.debug`
- `database.host`
- `database.port`
- `database.pool_size`
- `features.signup`
- `features.reports`

## Side Effects

| Command | Side effects |
|---|---|
| `get` | Reads config file; may use environment overrides; no file writes |
| `set` | Writes config file atomically and creates backup when applicable |
| `list` | Reads config file; may use environment overrides; no file writes |
| `validate` | Reads config and schema; writes config only with `--write-defaults` |
| `diff` | Reads two config files; no file writes |
| `init` | Copies a packaged template to output path |

Additional SysForge side effects may include creation of the shared home directory and logs.

## Usage Examples

### Basic example — initialize a template

```bash
sysforge-config init --template web-app --output starter.json
```

Expected output:

```text
Created starter.json
```

### Basic example — read a value

```bash
sysforge-config get database.host --file starter.json
```

Expected output:

```text
localhost
```

### Advanced example — set typed values

```bash
sysforge-config set database.port 5433 --file starter.json
sysforge-config set app.debug false --file starter.json
sysforge-config set features.reports true --file starter.json
```

Expected behavior:

- `database.port` becomes an integer.
- `app.debug` becomes a boolean false.
- `features.reports` becomes a boolean true.

### Advanced example — validate with defaults

```bash
sysforge-config validate starter.json --schema sysforge/data/sysforge.schema.json --write-defaults
```

Expected success output:

```text
Validation passed.
```

If defaults are added:

```text
Defaults were applied in memory during validation.
Wrote merged config to starter.json
```

### Edge case — environment override

```bash
export APP_DATABASE_HOST=prod-db.internal
sysforge-config get database.host --file starter.json
```

Expected output:

```text
prod-db.internal
```

The file is not rewritten by this command.

### Edge case — diff two files

```bash
sysforge-config diff starter.json prod.json
```

Expected output shape:

```text
ADDED
- ...
REMOVED
- ...
CHANGED
- ...
```

### Intentional failure — missing key

```bash
sysforge-config get database.password --file starter.json
```

Expected behavior:

```text
Key not found: database.password
```

Exit code: 1.

### Intentional failure — invalid schema result

```bash
sysforge-config validate bad.json --schema schema.json
```

Expected output shape:

```text
root.database.port: expected integer, got str
```

Exit code: 1.

---

# Runbook

## App 23 — Configuration Manager

**SysForge Group | Document 4 of 5**  
**Status: Accepted**

## Prerequisites

- Python 3.11 or newer.
- SysForge installed from the repository.
- Runtime dependencies installed, especially Typer.
- A valid JSON config file for `get`, `set`, `list`, `validate`, and `diff` workflows.
- A valid schema-subset JSON file for validation workflows.

## Installation Procedure

From the SysForge repository root:

```bash
python -m pip install -e .
```

For development tooling:

```bash
python -m pip install -e ".[dev]"
```

Or install requirements first:

```bash
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps
```

Confirm the CLI is available:

```bash
sysforge-config --help
sysforge config --help
```

## Configuration Steps

### 1. Choose a workspace

For normal use, operate from the project directory containing your JSON config files.

For isolated testing, set:

```bash
export SYSFORGE_HOME=.sysforge-dev
```

On Windows PowerShell:

```powershell
$env:SYSFORGE_HOME = ".sysforge-dev"
```

### 2. Initialize a starter config

```bash
sysforge-config init --template web-app --output app.json
```

### 3. Inspect values

```bash
sysforge-config list --file app.json
sysforge-config get database.host --file app.json
```

### 4. Update values

```bash
sysforge-config set database.host prod-db.internal --file app.json
sysforge-config set database.port 5432 --file app.json
sysforge-config set app.debug false --file app.json
```

### 5. Validate with a schema

```bash
sysforge-config validate app.json --schema sysforge/data/sysforge.schema.json
```

## Standard Operating Procedures

### Read a configuration key

```bash
sysforge-config get database.host --file app.json
```

Use this when scripts need one value from a nested config file.

### Set a configuration key

```bash
sysforge-config set database.pool_size 10 --file app.json
```

The value is parsed before being written. Use quotes around values that might be interpreted as numbers or booleans when you need a string.

### List every leaf value

```bash
sysforge-config list --file app.json
```

Use this before and after changes to verify the config shape.

### Validate a config file

```bash
sysforge-config validate app.json --schema schema.json
```

Use this in CI or before running another app that depends on the config.

### Write schema defaults

```bash
sysforge-config validate app.json --schema schema.json --write-defaults
```

Use this when you intentionally want missing default values added to the file.

### Compare two configs

```bash
sysforge-config diff dev.json prod.json
```

Use this to review environment differences.

### Create a new config from a template

```bash
sysforge-config init --template web-app --output starter.json
```

## Health Checks

### CLI import check

```bash
python -m compileall -q sysforge/config
```

Expected result: no output and exit code 0.

### Help command check

```bash
sysforge-config --help
```

Expected result: Typer help output listing commands.

### Template check

```bash
sysforge-config init --template web-app --output /tmp/sysforge_config_check.json
```

Expected result:

```text
Created /tmp/sysforge_config_check.json
```

### Read/write check

```bash
sysforge-config set database.host localhost --file /tmp/sysforge_config_check.json
sysforge-config get database.host --file /tmp/sysforge_config_check.json
```

Expected result:

```text
localhost
```

### Test suite check

From the repository root:

```bash
python -m pytest
```

The project config runs pytest with coverage over the `sysforge` package and a coverage threshold.

## Expected Output Samples

### `list`

```text
app.debug = True
app.name = 'sample-web-app'
database.host = 'localhost'
database.pool_size = 5
database.port = 5432
features.reports = False
features.signup = True
```

### `validate`

```text
Validation passed.
```

### `diff`

```text
ADDED
- database.pool_size: 10
REMOVED
- features.reports: False
CHANGED
- database.host: 'localhost' -> 'prod-db.internal'
```

### `set`

```text
Updated database.port in app.json
```

## Known Failure Modes

### Missing config file

Symptom:

```text
Config file not found: app.json
```

Cause: Path is wrong or file has not been created.

Recovery: Run `init`, create the file manually, or pass the correct `--file` path.

### Invalid JSON

Symptom:

```text
Expecting property name enclosed in double quotes
```

Cause: JSON syntax error.

Recovery: Fix the JSON syntax and retry.

### Root is not an object

Symptom:

```text
Config file must contain a JSON object
```

Cause: File contains a JSON array, string, number, or boolean at the root.

Recovery: Wrap settings inside an object.

### Missing key

Symptom:

```text
Key not found: database.password
```

Cause: Dotted path does not exist.

Recovery: Use `list` to inspect available keys, or use `set` to create the key.

### Cannot set under scalar

Symptom:

```text
Cannot set nested value under non-object key: host
```

Cause: A parent path segment is a scalar, not a dictionary.

Recovery: Restructure the config object before setting nested keys.

### Template not found

Symptom:

```text
Template not found: api-service
```

Cause: Template name does not exist under the packaged templates directory.

Recovery: Use `web-app` or add a packaged template.

### Schema validation failure

Symptom:

```text
root.database.port: expected integer, got str
```

Cause: Config value does not match schema subset.

Recovery: Update the config value or schema.

### Unexpected environment override

Symptom: `get` or `list` shows a value that is not in the file.

Cause: Matching `APP_...` environment variable is set.

Recovery: Unset the environment variable or run commands that disable env overlays where appropriate.

## Troubleshooting Decision Tree

```text
Command failed?
  |
  +-- Was the command syntax valid?
  |     |
  |     +-- No -> Run --help and correct command shape.
  |     +-- Yes
  |
  +-- Does the input file exist?
  |     |
  |     +-- No -> Create it, run init, or fix --file path.
  |     +-- Yes
  |
  +-- Is the JSON valid?
  |     |
  |     +-- No -> Fix JSON syntax.
  |     +-- Yes
  |
  +-- Is the root a JSON object?
  |     |
  |     +-- No -> Change root to an object.
  |     +-- Yes
  |
  +-- Is the dotted key valid?
  |     |
  |     +-- No -> Run list and inspect available keys.
  |     +-- Yes
  |
  +-- Is a schema involved?
        |
        +-- Yes -> Read validation errors and update config/schema.
        +-- No -> Check environment variables, file permissions, and paths.
```

## Dependency Failure Handling

### Typer unavailable

Symptom:

```text
ModuleNotFoundError: No module named 'typer'
```

Recovery:

```bash
python -m pip install -e .
```

or:

```bash
python -m pip install -r requirements.txt
```

### JSON file permission error

Symptom: Permission denied while reading or writing.

Recovery:

- Check file ownership.
- Check directory permissions.
- Try writing to a different path.
- Avoid editing system-owned config files without appropriate permissions.

### Packaged template missing

Symptom: `Template not found` for a known template.

Recovery:

- Confirm editable install points at the correct checkout.
- Reinstall the package.
- Confirm template exists under `sysforge/config/templates/`.

## Recovery Procedures

### Restore from backup after a bad `set`

`set` writes with backup enabled. If the original file existed, a backup with a `.bak` suffix may be present.

```bash
cp app.json.bak app.json
```

On Windows PowerShell:

```powershell
Copy-Item app.json.bak app.json
```

### Rebuild a config from template

```bash
sysforge-config init --template web-app --output app.new.json
```

Then manually copy values from the old file.

### Remove environment overrides

Unix-like shells:

```bash
unset APP_DATABASE_HOST
unset APP_DATABASE_PORT
```

PowerShell:

```powershell
Remove-Item Env:APP_DATABASE_HOST
Remove-Item Env:APP_DATABASE_PORT
```

### Validate before writing defaults

Always run without `--write-defaults` first:

```bash
sysforge-config validate app.json --schema schema.json
```

Then run with writing enabled only if the result is acceptable:

```bash
sysforge-config validate app.json --schema schema.json --write-defaults
```

## Logging Reference

The config app uses the `sysforge.config` logger. Logs are written through the shared SysForge logging utility.

Default log location:

```text
~/.sysforge/logs/sysforge.log
```

If `SYSFORGE_HOME` is set:

```text
$SYSFORGE_HOME/logs/sysforge.log
```

Logged events include successful key updates and template initialization.

## Maintenance Notes

- Keep the schema subset clearly documented.
- Add tests before expanding schema behavior.
- Add a template-list command if the template catalog grows.
- Consider a delete/unset command as the next small feature.
- Consider masking keys that contain `password`, `token`, or `secret` in `list` and `diff` output.
- Avoid introducing full JSON Schema behavior unless the project explicitly chooses to depend on a schema library.
- Keep shared helpers in `sysforge.common` rather than duplicating dotted-key logic.

---

# Lessons Learned

## App 23 — Configuration Manager

**SysForge Group | Document 5 of 5**  
**Status: Accepted**

## Project Summary

The Configuration Manager is a JSON-focused CLI for managing small configuration files. It supports reading dotted keys, setting nested values, listing flattened keys, validating against a limited schema subset, diffing two configs, and initializing a new config from a packaged template.

The project is important because it moves beyond a simple single-file script. It shows how a tool can live inside a larger package, reuse shared helpers, expose both standalone and unified CLI entry points, and provide safer file operations.

## Original Goals vs. Actual Outcome

### Original goals

- Build a CLI for common JSON configuration tasks.
- Use dotted keys for nested config access.
- Support config initialization from templates.
- Add validation so config files can be checked before use.
- Keep the tool small enough for a portfolio app.

### Actual outcome

The app met those goals and added useful engineering details:

- Environment-variable overrides for read-time config values.
- Atomic writes and backups through shared helpers.
- Recursive schema validation with default application.
- Flattened diff output for config comparisons.
- Integration into both `sysforge-config` and `sysforge config`.

The result feels like a real utility while staying smaller than a production configuration platform.

## Technical Decisions That Paid Off

### Using dotted keys

Dotted keys made the CLI much easier to use. `database.host` is readable and maps naturally to JSON objects. It also gave the implementation a clear reason to use shared nested lookup and mutation helpers.

### Reusing shared SysForge helpers

The app benefits from the existing SysForge core. JSON loading, JSON writing, nested paths, CLI value parsing, and error printing are shared instead of duplicated. That makes the config app smaller and shows good monorepo discipline.

### Keeping schema validation intentionally limited

A limited validator was a good learning choice. It forced the implementation to handle recursion, defaults, arrays, types, enums, and numeric bounds directly. It also kept the project from becoming a wrapper around a third-party package.

### Separating validation from mutation

Validation applies defaults in memory, but the file is only changed when `--write-defaults` is passed. That is a good CLI safety rule because users can preview changes before committing them.

### Using flattened diffs

Flattening both configs into dotted keys makes diff output simple and understandable. It avoids needing a complicated tree-diff algorithm.

## Technical Decisions That Created Debt

### Environment override collisions

The `APP_` mapping is simple, but different dotted paths can collapse to the same variable name. The app logs a warning, but it cannot fully resolve the ambiguity.

### No template discovery command

The `init` command works if the user knows the template name. As soon as more templates exist, users will need a way to list them.

### No delete/unset command

The app can set values but cannot remove them. That limits its usefulness for full config lifecycle management.

### No secret redaction

`list` and `diff` print values directly. That is fine for non-secret config, but risky if users store tokens or passwords in JSON files.

### Partial schema support can surprise users

The validator supports only a subset. Users may assume full JSON Schema keywords work unless documentation is explicit.

## What Was Harder Than Expected

### Safe mutation is harder than reading

Reading a dotted key is straightforward. Writing one is trickier because the app must decide whether to create missing objects, reject scalar parents, parse values correctly, and avoid corrupting the target file.

### Validation needs clear error paths

Recursive schema validation is not just checking values. It also needs to produce useful paths like `root.database.port`. Without those paths, errors are hard to fix.

### Defaults introduce mutation pressure

Applying defaults is helpful, but it creates a design question: should validation write to disk? The final design made this explicit with `--write-defaults`.

### Environment overrides are subtle

An environment override can make a value appear different from what the file contains. That is useful but can confuse debugging. The docs and runbook need to explain it clearly.

## What Was Easier Than Expected

### Flattened listing and diffing

Once `flatten_dict()` existed, both `list` and `diff` became simple. This shows how a good shared helper can unlock multiple features.

### Template initialization

Copying a packaged JSON file is a simple but useful feature. It gives the app an onboarding workflow without requiring an interactive wizard.

### Typer command structure

Typer made the command surface readable. Each command maps cleanly to one function, which keeps the module approachable.

## Python-Specific Learnings

### `pathlib.Path` improves CLI file handling

Using `Path` objects avoids constant string/path conversions and keeps filesystem code clear.

### JSON round-tripping can deep-copy simple data

The environment override function uses JSON serialization/deserialization to create a copy of config data. This is practical because config data is already JSON-compatible.

### Booleans require care in type validation

In Python, `bool` is a subclass of `int`. The validator correctly excludes booleans when checking `integer` and `number` types.

### Exceptions should be translated at the CLI boundary

Internal helpers raise normal exceptions like `KeyError`, `ValueError`, or `FileNotFoundError`. CLI commands catch these and convert them into user-readable messages and exit codes.

### Recursive functions need good base cases

The validator has separate handling for objects, arrays, numbers, and enums. Early return on type mismatch keeps later checks from producing confusing errors.

## Architecture Insights

### A shared utility layer is valuable in a multi-app package

This app demonstrates why SysForge has common helpers. Without `common.py`, every app would need its own JSON loading, file writing, and error handling. Reuse reduces code size and makes behavior consistent.

### CLI tools should separate read behavior from write behavior

`get`, `list`, and `diff` are read-oriented. `set`, `validate --write-defaults`, and `init` are write-oriented. Keeping that boundary clear makes the app safer.

### Small schema validators must be honest

The validator is useful because it is limited and documented. Pretending to support all JSON Schema would be misleading. A small tool is acceptable when its boundaries are explicit.

### File safety is an architectural feature

Atomic writes and backups are not glamorous, but they matter. A config tool that corrupts files is worse than no tool at all.

## Testing Gaps

The shared helper tests cover important functions such as JSON round-tripping, atomic writes, CLI value parsing, flattening, nested lookup, and nested mutation. For the config app itself, the most important future tests would be:

- CLI `get` success and missing-key failure.
- CLI `set` typed value parsing and backup creation.
- CLI `list` with environment overrides.
- Schema validation with nested defaults.
- Schema validation with arrays and item schemas.
- `validate --write-defaults` write behavior.
- `diff` output for added, removed, and changed keys.
- `init` success and missing-template failure.
- Environment override collision warning behavior.

I did not execute the tests while creating this documentation.

## Reusable Patterns Identified

### Dotted-key access

Useful for future apps that need CLI access to nested dictionaries.

### Flatten-then-compare

Useful for diffing nested data structures without building a full tree diff.

### Validate-and-return-updated-data

Useful for functions that need to report errors and also apply safe normalization/defaults.

### Explicit write flag

Useful for any command where validation or analysis could optionally modify a file.

### Packaged template initialization

Useful for onboarding users into config-heavy apps.

### Shared file IO helpers

Useful across SysForge for consistent atomic writes, backups, and JSON formatting.

## If I Built This Again

I would keep the current core but add a few carefully scoped improvements:

1. Add `templates` or `init --list` to show available templates.
2. Add `unset KEY --file app.json` for deleting values.
3. Add optional secret redaction in `list` and `diff`.
4. Add a `--no-env` flag for `get` and `list` so users can compare raw file values against overridden values.
5. Add a `--json` output mode for `diff` so scripts can consume the result.
6. Add more explicit documentation for the supported schema subset.
7. Add a command that prints the environment variable name for a dotted key.
8. Consider file locking if concurrent writes become a concern.

## Open Questions

- Should environment overrides be opt-in instead of default for `get` and `list`?
- Should `set` support deleting keys with a special value, or should deletion be a separate command?
- Should the app support JSON Pointer in addition to dotted keys?
- Should secret-like keys be redacted automatically?
- Should templates be user-extensible from `~/.sysforge/config/templates`?
- Should validation support more JSON Schema keywords, or should the app intentionally stop at the current subset?
- Should the app support TOML now that Python has `tomllib` for reading?
- Should `diff` distinguish type changes more explicitly?

## Final Reflection

The Configuration Manager is a strong portfolio app because it solves a realistic problem and shows several engineering skills at once: CLI design, nested data manipulation, validation, safer writes, environment overrides, templates, and shared package integration. Its biggest strength is that it remains understandable. Its biggest limitation is that the validator and template system are intentionally small. That tradeoff is acceptable for App 23 because the project is still focused on learning and scope control rather than replacing mature configuration platforms.
