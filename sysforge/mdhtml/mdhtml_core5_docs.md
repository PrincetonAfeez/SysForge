# Architecture Decision Record

## App 24 — Markdown-to-HTML Generator

**SysForge Group | Document 1 of 5**  
**Status: Accepted**  
**Date: 2026-05-08**

---

## 1. Title

Adopt a packaged Typer-based Markdown-to-HTML builder with template-driven rendering, theme assets, build history, and shared SysForge filesystem conventions.

---

## 2. Context

The Markdown-to-HTML Generator is one of the standalone utilities inside the SysForge toolkit. SysForge packages several developer-operations commands under one importable `sysforge` package, while also exposing standalone console scripts such as `sysforge-mdhtml` and a unified command surface such as `sysforge docs build`.

This application converts one Markdown file, or a directory tree of Markdown files, into styled HTML output. It also supports a small static-site mode by building an `index.html` page when a directory is processed. The app must balance several concerns:

- The tool should be simple enough for a CLI portfolio project.
- It should support useful documentation-builder features: frontmatter titles, tables, fenced code, syntax highlighting, themes, templates, and relative image copying.
- It should integrate with SysForge shared state rather than creating a separate configuration and logging system.
- It should avoid the earlier package-name conflict where a local `markdown` package shadowed the third-party `markdown` dependency.
- It should be testable through function-level units, not only through manual CLI runs.

---

## 3. Decision Drivers

| Driver | Why it matters |
|---|---|
| CLI usability | The app should be usable from both `sysforge-mdhtml` and the unified `sysforge docs` command. |
| Maintainability | Markdown parsing, template application, file collection, image copying, and history logging should be separate functions. |
| Portfolio progression | This project demonstrates third-party integration, filesystem traversal, rendering pipelines, static assets, and package-layout decisions. |
| Safety | Template placeholders should be validated, title fields escaped, and relative image paths handled conservatively. |
| SysForge integration | The app should reuse shared config, logging, path helpers, and JSON/text writers rather than duplicating infrastructure. |
| Scope discipline | The project should produce static HTML without attempting to become a full static-site generator. |

---

## 4. Options Considered

### Option A — Write a Markdown parser manually

**Description:** Implement Markdown parsing with custom string processing and regular expressions.

**Pros**

- No runtime dependency on the `markdown` package.
- More educational exposure to parsing.

**Cons**

- Too much scope for a small CLI utility.
- Hard to correctly implement tables, fenced code, headings, blockquotes, and code highlighting.
- Would distract from the architecture goal of building a document pipeline.

**Decision:** Rejected.

---

### Option B — Use the third-party `markdown` package and wrap it with SysForge-specific logic

**Description:** Delegate Markdown-to-HTML conversion to the established `markdown` package, then add frontmatter parsing, templates, CSS themes, image copying, history logging, and CLI behavior around it.

**Pros**

- Keeps parsing behavior realistic and maintainable.
- Allows focus on app architecture rather than reimplementing Markdown.
- Supports useful extensions such as fenced code, tables, TOC, and codehilite.
- Works naturally with Pygments-generated CSS for code blocks.

**Cons**

- Requires runtime dependencies beyond the standard library.
- The project must avoid naming collisions with the dependency.
- The dependency may produce HTML that requires additional sanitization if used with untrusted Markdown.

**Decision:** Chosen.

---

### Option C — Use an external static-site generator

**Description:** Invoke or wrap a full static-site generator such as MkDocs, Pelican, or Sphinx.

**Pros**

- Feature-rich output with mature navigation and themes.
- Less custom code required.

**Cons**

- Too heavyweight for this app’s learning target.
- Reduces ownership of the rendering pipeline.
- Adds a large dependency and configuration surface.

**Decision:** Rejected.

---

### Option D — Only support one file at a time

**Description:** Convert a single Markdown file to a single HTML file.

**Pros**

- Simpler output mapping.
- Fewer edge cases.

**Cons**

- Less useful as a documentation utility.
- No opportunity to demonstrate recursive file collection, relative output paths, or index generation.

**Decision:** Rejected.

---

### Option E — Support files and directories with an index page for directory builds

**Description:** If the source is a file, convert it to one HTML file. If the source is a directory, collect all `.md` files recursively, preserve relative layout, convert each file, then generate an `index.html` page linking to the outputs.

**Pros**

- Useful enough for a local documentation site.
- Exercises path mapping and relative-link thinking.
- Still small enough for a portfolio app.

**Cons**

- Does not include advanced site features such as navigation trees, search, tags, or watch mode.
- Needs history and error reporting so partial builds are understandable.

**Decision:** Chosen.

---

## 5. Decision

The Markdown-to-HTML Generator will be implemented as the `sysforge.mdhtml` package, with the main command and application logic in `sysforge/mdhtml/markdown.py`.

The app will:

1. Expose a Typer app called `app`.
2. Provide a `build` command.
3. Support the standalone `sysforge-mdhtml` entry point.
4. Also mount under the unified `sysforge docs` command.
5. Accept a Markdown file or directory as input.
6. Accept an output file or directory through `--output`.
7. Support `--theme light|dark` with shared-config fallback.
8. Support an optional `--template` path.
9. Parse simple YAML-like frontmatter for title/date metadata.
10. Guess document titles from frontmatter, first Markdown heading, or filename.
11. Convert Markdown through the third-party `markdown` package.
12. Use extensions for fenced code, tables, table of contents, and code highlighting.
13. Generate Pygments CSS dynamically.
14. Embed packaged light/dark CSS and template placeholders.
15. Copy local relative images from the source tree into the output tree.
16. Build an index page for directory builds.
17. Append build metadata to SysForge’s shared docs history file.

---

## 6. Rationale

The chosen design is appropriate because the app’s goal is not to prove that Markdown syntax can be reimplemented from scratch. The more valuable learning target is to create a small, realistic rendering pipeline:

```text
source path
  -> collect markdown files
  -> read raw text
  -> parse optional frontmatter
  -> choose title
  -> convert Markdown body to HTML
  -> load template
  -> load theme CSS
  -> generate Pygments CSS
  -> inject placeholders
  -> write output HTML
  -> copy local image assets
  -> optionally generate index.html
  -> append build history
```

This structure is stronger than a one-function converter because every stage has a clear responsibility. The tests also validate several small components directly, including frontmatter parsing, Markdown file collection, image target parsing, template placeholder replacement behavior, relative index links, and title guessing.

The package rename from `sysforge.markdown` to `sysforge.mdhtml` is also an important architecture decision. The app depends on a third-party package named `markdown`, so using the same local package name would create import ambiguity. Renaming the local package avoids shadowing and makes the dependency relationship clearer.

---

## 7. Trade-offs Accepted

| Trade-off | Accepted consequence |
|---|---|
| Use third-party `markdown` and Pygments | Runtime depends on installed packages listed in SysForge metadata. |
| Minimal frontmatter parser | Supports basic key/value metadata, but not full YAML semantics. |
| Embedded CSS in HTML output | Output files are self-contained for styling, but repeated CSS increases file size. |
| Continue on per-file build errors | Directory builds can produce partial output; the CLI exits nonzero if errors exist. |
| Copy only local relative images | Remote images and data URLs are intentionally ignored for copying. |
| No HTML sanitization layer | Trusted local Markdown is assumed; untrusted Markdown is out of scope. |
| History stored as JSON in SysForge home | Useful for audit/reporting, but not designed for high-volume build telemetry. |

---

## 8. Consequences

### Positive consequences

- The app has a clean rendering pipeline with separately testable stages.
- The CLI is consistent with other SysForge apps because it uses Typer and shared helpers.
- The implementation supports both single-file and folder-based documentation workflows.
- Packaged templates and themes make output predictable without requiring external assets.
- Build history creates a durable operational record under the SysForge home directory.
- The renamed `mdhtml` package avoids shadowing the third-party `markdown` package.

### Negative consequences

- The app is no longer standard-library-only.
- Output HTML inherits behavior from the Markdown library and should not be treated as sanitized content for hostile input.
- The frontmatter parser may surprise users expecting full YAML support.
- Directory builds create an index page even if zero files are built, which is useful but may hide empty input unless users inspect the summary.
- The app does not rewrite Markdown links between generated pages.

---

## 9. Superseded By

Not superseded.

Future superseding decisions could include:

- A richer static-site manifest model.
- Full YAML frontmatter via a dedicated parser.
- Link rewriting between generated Markdown pages.
- Configurable Markdown extensions.
- A watch mode for live rebuilds.
- Optional HTML sanitization for untrusted content.

---

# Technical Design Document

## App 24 — Markdown-to-HTML Generator

**SysForge Group | Document 2 of 5**

---

## 1. Purpose & Scope

The Markdown-to-HTML Generator converts Markdown documents into styled HTML pages. It is part of SysForge, a multi-tool CLI package that includes file organization, Markdown documentation building, briefings, time tracking, configuration management, health monitoring, and a unified CLI wrapper.

The app supports:

- Single Markdown file conversion.
- Recursive directory conversion.
- `index.html` generation for directory builds.
- Optional frontmatter parsing.
- Title guessing.
- Packaged HTML template rendering.
- Light and dark themes.
- Pygments code highlighting CSS.
- Relative image copying.
- Build-history persistence.
- Standalone and unified CLI entry points.

The app does not attempt to provide:

- Full static-site navigation.
- Markdown link rewriting.
- Search indexing.
- Full YAML frontmatter.
- HTML sanitization for untrusted input.
- HTTP serving or watch mode.

---

## 2. System Context

```text
User
  |
  | sysforge-mdhtml build notes.md --output output.html
  | sysforge-mdhtml build ./docs --output ./site --theme dark
  | sysforge docs build ./docs --output ./site
  v
Typer CLI
  |
  v
build_site()
  |
  +--> collect_markdown_files()
  +--> convert_markdown_file()
  |      +--> parse_frontmatter()
  |      +--> guess_title()
  |      +--> markdown.markdown(...)
  |      +--> render_html_document()
  |      |      +--> load_template()
  |      |      +--> load_theme_css()
  |      |      +--> build_pygments_css()
  |      +--> write_text_file()
  |      +--> copy_relative_images()
  |
  +--> build_index_page()      (directory builds only)
  +--> append_build_history()
  v
HTML output files + ~/.sysforge/docs/build_history.json
```

The app interacts with local filesystem paths only. It reads Markdown, theme/template assets, and optional shared configuration, then writes HTML output and a JSON build-history entry.

---

## 3. Component Breakdown

### `sysforge/mdhtml/markdown.py`

Primary implementation module.

Responsibilities:

- Define the Typer app.
- Parse and validate build command arguments.
- Load third-party dependencies dynamically.
- Parse optional frontmatter.
- Guess page titles.
- Load HTML templates and CSS themes.
- Convert Markdown to HTML.
- Copy local images.
- Build site index pages.
- Append build history.
- Return structured build results.

Important objects and functions:

| Name | Responsibility |
|---|---|
| `app` | Typer application for the Markdown builder. |
| `IMAGE_PATTERN` | Regex for finding Markdown image targets. |
| `_parse_markdown_image_target()` | Extracts the actual image path from Markdown image syntax. |
| `_replace_placeholder_once()` | Ensures a template contains a required placeholder and replaces one occurrence. |
| `_apply_html_template()` | Injects theme CSS, Pygments CSS, title, timestamp, and content into the template. |
| `load_markdown_dependency()` | Imports third-party `markdown` and exits with a CLI error if missing. |
| `load_pygments_formatter()` | Imports Pygments formatter class and exits with a CLI error if missing. |
| `parse_frontmatter()` | Parses a simple `---` frontmatter block. |
| `guess_title()` | Chooses title from frontmatter, first heading, or filename. |
| `load_template()` | Reads either a custom template or packaged template. |
| `load_theme_css()` | Reads packaged light/dark theme CSS. |
| `build_pygments_css()` | Generates `.codehilite` CSS. |
| `render_html_document()` | Produces final HTML document. |
| `copy_relative_images()` | Copies local image assets referenced by Markdown image syntax. |
| `collect_markdown_files()` | Recursively collects `.md` files with case-insensitive suffix handling. |
| `convert_markdown_file()` | Converts one source file to one destination file. |
| `build_index_page()` | Creates `index.html` for directory builds. |
| `append_build_history()` | Appends build metadata to shared docs history. |
| `build_site()` | Orchestrates file or directory builds. |
| `build()` | CLI command implementation. |
| `main()` | Console script entry point. |

---

### `sysforge/mdhtml/template.html`

Packaged HTML wrapper used by default.

Required placeholders:

- `{{title}}`
- `{{theme_css}}`
- `{{pygments_css}}`
- `{{generated_at}}`
- `{{content}}`

If a custom template is supplied and does not include one of these placeholders, rendering fails with a `ValueError`.

---

### `sysforge/mdhtml/themes/light.css`

Packaged light theme.

Responsibilities:

- Set readable page typography.
- Style code blocks, blockquotes, tables, links, and page container.
- Provide a warm light documentation appearance.

---

### `sysforge/mdhtml/themes/dark.css`

Packaged dark theme.

Responsibilities:

- Provide dark background and high-contrast text.
- Style code blocks, blockquotes, tables, links, and page container.
- Match the same semantic CSS classes as the light theme.

---

### `sysforge/mdhtml/__init__.py`

Package marker and documentation string.

Important architectural note:

The package is named `mdhtml`, not `markdown`, to avoid shadowing the third-party `markdown` library used at runtime.

---

### Shared SysForge utilities

| Module | Used for |
|---|---|
| `sysforge.common` | JSON/text writes, JSON loads, CLI error handling. |
| `sysforge.logging_utils` | Central logger setup and log-level handling. |
| `sysforge.shared_config` | Shared config loading and default theme lookup. |
| `sysforge.sysforge_paths` | SysForge home layout, docs history path, template path, theme path. |
| `sysforge.__main__` | Unified CLI mounting under `sysforge docs`. |

---

## 4. Module Dependency Graph

```text
sysforge.__main__
  └── sysforge.mdhtml.markdown.app

sysforge.mdhtml.markdown
  ├── importlib
  ├── os
  ├── re
  ├── datetime
  ├── html.escape
  ├── pathlib.Path
  ├── typer
  ├── third-party markdown       (loaded dynamically)
  ├── third-party pygments       (loaded dynamically)
  ├── sysforge.common
  ├── sysforge.logging_utils
  ├── sysforge.shared_config
  └── sysforge.sysforge_paths

sysforge.sysforge_paths
  └── packaged mdhtml/template.html
  └── packaged mdhtml/themes/*.css
```

---

## 5. Core Algorithms & Logic

### 5.1 Frontmatter parsing

`parse_frontmatter(raw_text, source)` detects frontmatter only when the file starts with `---\n`.

Algorithm:

1. If the text does not start with `---\n`, return empty metadata and the original text.
2. Split the file into lines.
3. Iterate until the closing `---` line.
4. Ignore blank lines and comment lines inside frontmatter.
5. Parse lines containing `:` into key/value strings.
6. Strip optional matching quotes from values.
7. Treat lines without `:` as continuations only if a prior key exists.
8. Raise `ValueError` if a malformed frontmatter line appears before any key.
9. Raise `ValueError` if frontmatter is never closed.
10. Return metadata dictionary and remaining Markdown body.

This is intentionally not a complete YAML parser.

---

### 5.2 Title guessing

`guess_title(frontmatter, body, source)` uses fallback order:

1. Nonblank `title` from frontmatter.
2. First Markdown heading line beginning with `#`.
3. Source filename stem, with underscores replaced by spaces and title-cased.

---

### 5.3 Markdown conversion

`convert_markdown_file()` reads one Markdown file and calls:

```python
markdown_module.markdown(
    markdown_body,
    extensions=["fenced_code", "tables", "toc", "codehilite"],
)
```

This produces HTML body content with support for:

- Fenced code blocks.
- Tables.
- Heading table-of-contents behavior.
- Pygments-compatible code highlighting classes.

---

### 5.4 Template rendering

`render_html_document()` loads a template, loads theme CSS, generates Pygments CSS, escapes title/timestamp, and calls `_apply_html_template()`.

Template application is strict:

1. Replace `{{theme_css}}` once.
2. Replace `{{pygments_css}}` once.
3. Replace `{{title}}` once.
4. Replace `{{generated_at}}` once.
5. Replace `{{content}}` once.

The “replace once” behavior avoids accidentally replacing placeholder-looking text inside rendered Markdown content.

---

### 5.5 Image copying

`copy_relative_images()` scans Markdown text with `IMAGE_PATTERN`.

For each image reference:

1. Parse the path target.
2. Ignore empty values.
3. Ignore data URLs.
4. Ignore HTTP and HTTPS URLs.
5. Resolve the referenced file relative to the source file’s directory.
6. Skip missing or non-file paths.
7. Copy bytes into the destination output directory, preserving the relative image path.

This keeps local image references working for generated HTML without downloading remote assets.

---

### 5.6 Directory build mapping

When the source path is a directory:

1. Recursively collect Markdown files using `collect_markdown_files()`.
2. Sort them case-insensitively by path string.
3. For each Markdown file, compute its relative path from source.
4. Replace `.md` with `.html`.
5. Write to `output / relative_path`.
6. Build an `index.html` page containing generated page links.

---

### 5.7 History writing

`append_build_history()` appends a JSON object to the SysForge docs history file.

Stored fields include:

- `timestamp`
- `input_path`
- `output_path`
- `theme`
- `files_built`
- `errors`

Writes use the shared `write_json_file(..., atomic=True)` helper.

---

## 6. Data Structures

| Structure | Type | Purpose |
|---|---|---|
| `frontmatter` | `dict[str, str]` | Stores parsed metadata such as title/date. |
| `built_files` | `list[dict[str, Any]]` | Stores conversion records for all generated files. |
| `errors` | `list[str]` | Stores per-file build failures. |
| build record | `dict[str, Any]` | Contains `source`, `output`, `title`, and `date`. |
| history payload | `dict[str, Any]` | Build metadata persisted to docs history. |
| theme CSS | `str` | Packaged CSS injected into output HTML. |
| template | `str` | HTML skeleton with required placeholders. |

---

## 7. State Management

The app does not maintain long-lived in-memory state between CLI executions.

Persistent state includes:

- Generated HTML output files.
- Copied relative image files.
- Directory index files.
- SysForge docs history JSON under `~/.sysforge/docs/build_history.json` by default.
- Central SysForge log output under `~/.sysforge/logs/sysforge.log`.

The app also reads shared configuration from SysForge’s config system. The relevant default value is `markdown.theme`, which defaults to `light`.

For tests or isolated runs, `SYSFORGE_HOME` can redirect SysForge state away from the real user home directory.

---

## 8. Error Handling Strategy

| Error case | Handling |
|---|---|
| Missing Markdown source path | `print_error()` exits with a CLI error. |
| Invalid theme | CLI rejects anything except `light` or `dark`. |
| Missing theme file | `load_theme_css()` exits through `print_error()`. |
| Missing `markdown` dependency | `load_markdown_dependency()` exits with setup guidance. |
| Missing Pygments dependency | `load_pygments_formatter()` exits with setup guidance. |
| Invalid frontmatter | Conversion of that file records an error during build. |
| Template missing placeholder | Conversion records an error through raised `ValueError`. |
| Directory build with some failures | Built files are still written; CLI exits code 1 after printing errors. |
| Keyboard interrupt / system exit | Re-raised, not swallowed as a normal file error. |

The design separates fatal CLI setup errors from per-file conversion errors. Directory builds therefore degrade gracefully when one file fails.

---

## 9. External Dependencies

| Dependency | Role |
|---|---|
| `typer>=0.12` | CLI framework. |
| `markdown>=3.6` | Markdown-to-HTML conversion. |
| `pygments>=2.18` | Syntax-highlighting CSS for `codehilite`. |
| `rich>=13.7` | SysForge dependency; used elsewhere and compatible with Typer CLI output. |
| `psutil>=5.9` | SysForge runtime dependency for health monitoring, not directly used by mdhtml. |
| `pytest>=8.0` | Test runner in the dev dependency group. |
| `pytest-cov>=5.0` | Coverage enforcement. |
| `ruff>=0.8` | Lint and format checks. |
| `mypy>=1.13` | Static typing checks. |

---

## 10. Concurrency Model

The Markdown-to-HTML Generator is synchronous and single-process.

There is no:

- Thread pool.
- Async IO.
- Parallel conversion.
- Watch mode.
- Background server.

This keeps build order predictable and error handling straightforward.

---

## 11. Known Limitations

- The frontmatter parser is not full YAML.
- HTML output is not sanitized for untrusted Markdown input.
- Markdown links between pages are not rewritten from `.md` to `.html`.
- Remote images are not downloaded or cached.
- Data URLs are intentionally skipped during image copying.
- Only packaged `light` and `dark` theme names are accepted through the standard CLI.
- Template placeholders must be present exactly as expected.
- Build history can grow over time without rotation.
- The app does not provide an incremental-build cache.

---

## 12. Design Patterns Used

| Pattern | Where it appears |
|---|---|
| Pipeline | Source collection → parsing → conversion → rendering → writing → history. |
| Adapter | The app wraps the `markdown` library behind SysForge-specific behavior. |
| Template Method style | HTML wrapper uses a fixed set of placeholders. |
| Strategy-lite | Theme selection swaps CSS while leaving rendering logic unchanged. |
| Facade | `build_site()` exposes one orchestration function around many smaller helpers. |
| Shared infrastructure | Common logging, config, path, and file-writing helpers are reused across apps. |

---

# Interface Design Specification

## App 24 — Markdown-to-HTML Generator

**SysForge Group | Document 3 of 5**

---

## 1. Invocation Syntax

### Standalone command

```bash
sysforge-mdhtml build SOURCE --output OUTPUT [--theme light|dark] [--template TEMPLATE]
```

### Unified SysForge command

```bash
sysforge docs build SOURCE --output OUTPUT [--theme light|dark] [--template TEMPLATE]
```

### Python module/function entry

The package metadata exposes:

```text
sysforge-mdhtml = sysforge.mdhtml.markdown:main
```

The unified CLI mounts the Typer app under:

```text
sysforge docs
```

---

## 2. Command Reference

### `build`

Converts Markdown files into HTML.

```bash
sysforge-mdhtml build notes.md --output notes.html
sysforge-mdhtml build ./docs --output ./site --theme dark
```

---

## 3. Argument Reference Table

| Name | Type | Required | Default | Accepted values | Description |
|---|---:|---:|---|---|---|
| `source` | Path | Yes | None | Markdown file or directory | Input Markdown file or folder. |
| `--output` | Path | Yes | None | File or directory path | Output HTML file for file input, or output directory for directory input. |
| `--theme` | String | No | Shared config `markdown.theme`, then `light` | `light`, `dark` | CSS theme to embed in generated HTML. |
| `--template` | Path | No | Packaged template | Existing HTML template path | Custom template with required placeholders. |

---

## 4. Input Contract

### Markdown file input

- Source must exist.
- Source may be any file path, but intended usage is `.md`.
- File is read as UTF-8.
- Optional frontmatter is recognized only if the file starts with `---\n`.

### Markdown directory input

- Source directory must exist.
- All files under the directory with suffix `.md` are collected recursively.
- Suffix matching is case-insensitive.
- Relative directory structure is preserved in the output directory.

### Template input

A custom template must include exactly usable placeholders:

```text
{{theme_css}}
{{pygments_css}}
{{title}}
{{generated_at}}
{{content}}
```

Missing placeholders produce a conversion error.

### Image references

Recognized Markdown syntax:

```markdown
![Alt text](images/example.png)
![Alt text](<images/example.png>)
![Alt text](images/example.png "optional title")
```

The app copies local relative images if they exist. It does not copy:

- Missing files.
- Directories.
- HTTP URLs.
- HTTPS URLs.
- Data URLs.

---

## 5. Output Contract

### Single-file build

If `source` is a file:

- If `--output` ends in `.html`, output is written directly to that path.
- Otherwise, output is treated as a directory and the file is written as `<source_stem>.html`.

Example:

```bash
sysforge-mdhtml build notes.md --output site
```

Produces:

```text
site/notes.html
```

### Directory build

If `source` is a directory:

- Each Markdown file becomes a corresponding `.html` file under the output directory.
- An `index.html` page is generated in the output directory.
- Build history is updated.

Example:

```text
source docs/guide/intro.md
output site/guide/intro.html
```

### CLI success output

On success:

```text
Built 1 HTML file(s).
notes.md -> output.html
```

### CLI partial-failure output

If some files fail:

```text
Built 2 HTML file(s).

Errors
- docs/bad.md: frontmatter was opened but not closed
```

The command exits nonzero after printing errors.

---

## 6. Exit Code Reference

| Exit code | Meaning |
|---:|---|
| `0` | Build succeeded with no recorded errors. |
| `1` | Build completed with one or more file conversion errors, or a normal CLI validation error occurred. |
| `2` | Dependency/setup error may be raised through shared CLI error handling, such as missing third-party package. |

Typer and `print_error()` handle exits by raising `typer.Exit`.

---

## 7. Error Output Behavior

- User-facing fatal errors are printed in red to stderr by `print_error()`.
- Per-file conversion errors are collected as strings and printed under an `Errors` section.
- Missing optional images are skipped silently.
- Invalid theme names are rejected before building.
- Missing template placeholders fail the file conversion.

---

## 8. Environment Variables

| Variable | Effect |
|---|---|
| `SYSFORGE_HOME` | Overrides the default `~/.sysforge` state directory. Useful for tests and isolated runs. |
| `SYSFORGE_CONFIG` | Overrides shared config path used by SysForge. |
| `SYSFORGE_VERBOSE=1` | Increases console logging level through shared logging. |
| `SYSFORGE_QUIET=1` | Reduces console logging level through shared logging. |

---

## 9. Configuration Files

### Shared SysForge config

Default path:

```text
~/.sysforge/sysforge.json
```

Relevant key:

```json
{
  "markdown": {
    "theme": "light"
  }
}
```

If `--theme` is omitted, the app uses this shared config value.

### Packaged template

```text
sysforge/mdhtml/template.html
```

### Packaged themes

```text
sysforge/mdhtml/themes/light.css
sysforge/mdhtml/themes/dark.css
```

### Build history

```text
~/.sysforge/docs/build_history.json
```

---

## 10. Side Effects

| Side effect | Description |
|---|---|
| Writes HTML files | Generated from Markdown input. |
| Writes `index.html` | Directory builds create a generated page index. |
| Copies local image files | Relative image references are copied beside HTML output. |
| Creates SysForge directories | `ensure_home_layout()` creates shared state directories. |
| Writes build history | JSON entry appended to docs history. |
| Writes logs | Shared logger writes to central SysForge log file. |

---

## 11. Usage Examples

### Basic single-file build

```bash
sysforge-mdhtml build README.md --output README.html
```

Expected outcome:

```text
Built 1 HTML file(s).
README.md -> README.html
```

---

### Directory build with dark theme

```bash
sysforge-mdhtml build ./docs --output ./site --theme dark
```

Expected outcome:

```text
site/index.html
site/<converted pages>.html
```

---

### Unified CLI usage

```bash
sysforge docs build ./docs --output ./site
```

Uses shared SysForge setup and default theme configuration.

---

### Custom template

```bash
sysforge-mdhtml build notes.md --output notes.html --template ./template.html
```

The custom template must include all required placeholders.

---

### Intentional failure: invalid theme

```bash
sysforge-mdhtml build notes.md --output notes.html --theme neon
```

Expected behavior:

```text
--theme must be light or dark.
```

---

### Intentional failure: missing source

```bash
sysforge-mdhtml build missing.md --output output.html
```

Expected behavior:

```text
Source path not found: missing.md
```

---

# Runbook

## App 24 — Markdown-to-HTML Generator

**SysForge Group | Document 4 of 5**

---

## 1. Prerequisites

- Python 3.11 or newer.
- SysForge repository cloned locally.
- Runtime dependencies installed:
  - Typer
  - Markdown
  - Pygments
  - Rich
  - Psutil
- Write access to the selected output directory.
- Write access to the SysForge home directory, or set `SYSFORGE_HOME` to a writable path.

---

## 2. Installation Procedure

From the repository root:

```bash
python -m pip install -e .
```

For development and verification:

```bash
python -m pip install -e ".[dev]"
```

Alternative install flow:

```bash
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps
```

---

## 3. Configuration Steps

### Use default shared state

No setup required. SysForge uses:

```text
~/.sysforge/
```

### Use isolated state for development

macOS/Linux:

```bash
export SYSFORGE_HOME=.sysforge-dev
```

Windows PowerShell:

```powershell
$env:SYSFORGE_HOME = ".sysforge-dev"
```

Windows CMD:

```cmd
set SYSFORGE_HOME=.sysforge-dev
```

### Set default theme

Edit the shared config file:

```json
{
  "markdown": {
    "theme": "light"
  }
}
```

Use `--theme dark` or `--theme light` to override the config for one run.

---

## 4. Standard Operating Procedures

### Convert one file

```bash
sysforge-mdhtml build notes.md --output notes.html
```

### Convert one file into an output directory

```bash
sysforge-mdhtml build notes.md --output ./site
```

Expected output:

```text
site/notes.html
```

### Convert a directory

```bash
sysforge-mdhtml build ./docs --output ./site
```

Expected output:

```text
site/index.html
site/<converted pages>.html
```

### Use dark theme

```bash
sysforge-mdhtml build ./docs --output ./site --theme dark
```

### Use custom template

```bash
sysforge-mdhtml build notes.md --output notes.html --template ./template.html
```

### Run through unified CLI

```bash
sysforge docs build ./docs --output ./site
```

---

## 5. Health Checks

### Check CLI availability

```bash
sysforge-mdhtml --help
```

### Check unified CLI availability

```bash
sysforge docs --help
```

### Check conversion path

```bash
echo "# Smoke Test" > smoke.md
sysforge-mdhtml build smoke.md --output smoke.html
```

Confirm:

- `smoke.html` exists.
- The file contains an `<html>` document.
- The title appears in the output.
- The command reports one built file.

### Check docs history

Look for:

```text
~/.sysforge/docs/build_history.json
```

or under the configured `SYSFORGE_HOME`.

---

## 6. Expected Output Samples

### Successful file build

```text
Built 1 HTML file(s).
notes.md -> notes.html
```

### Successful directory build

```text
Built 3 HTML file(s).
docs/a.md -> site/a.html
docs/guide/b.md -> site/guide/b.html
docs/reference/c.md -> site/reference/c.html
```

### Partial failure

```text
Built 2 HTML file(s).

Errors
- docs/broken.md: frontmatter was opened but not closed
```

---

## 7. Known Failure Modes

| Symptom | Likely cause | Recovery |
|---|---|---|
| `Source path not found` | Wrong source path | Correct the path and rerun. |
| `--theme must be light or dark` | Invalid theme argument | Use `light` or `dark`. |
| `Theme not found` | Packaged theme missing or bad code path | Reinstall package or verify package data. |
| `Template is missing placeholder` | Custom template lacks required marker | Add missing `{{...}}` placeholder. |
| `markdown package is not installed` | Runtime dependency missing | Run `python -m pip install -e .`. |
| `Pygments is not installed` | Runtime dependency missing | Run `python -m pip install -e .`. |
| Images missing in output | Image reference is remote, data URL, missing, or not a local file | Use local relative images or copy assets manually. |
| No Markdown files built | Directory contains no `.md` files | Add Markdown files or choose the correct directory. |

---

## 8. Troubleshooting Decision Tree

```text
Command fails?
  |
  +-- Is the source path correct?
  |     +-- No: correct source path.
  |     +-- Yes:
  |
  +-- Is the theme valid?
  |     +-- No: use light or dark.
  |     +-- Yes:
  |
  +-- Are dependencies installed?
  |     +-- No: python -m pip install -e .
  |     +-- Yes:
  |
  +-- Using a custom template?
  |     +-- Yes: verify all placeholders exist.
  |     +-- No:
  |
  +-- Directory build partially failed?
        +-- Inspect Errors section.
        +-- Fix malformed Markdown/frontmatter/template issue.
        +-- Rerun.
```

---

## 9. Dependency Failure Handling

### Missing `markdown`

Install the package in editable mode:

```bash
python -m pip install -e .
```

### Missing `pygments`

Install the package in editable mode:

```bash
python -m pip install -e .
```

### Dev tools missing

Install dev extras:

```bash
python -m pip install -e ".[dev]"
```

---

## 10. Recovery Procedures

### Recover from bad output

1. Delete the generated output directory or file.
2. Fix source Markdown or template.
3. Rerun the build command.

### Recover from bad SysForge state

Use an isolated home:

```bash
export SYSFORGE_HOME=.sysforge-clean
```

Then rerun the command.

### Recover from growing history

The app does not rotate docs history automatically. To reset history:

1. Back up `~/.sysforge/docs/build_history.json`.
2. Delete or truncate the file.
3. Rerun builds as needed.

---

## 11. Logging Reference

The app uses the shared logger name:

```text
sysforge.mdhtml
```

Log destination:

```text
~/.sysforge/logs/sysforge.log
```

Environment controls:

```bash
SYSFORGE_VERBOSE=1
SYSFORGE_QUIET=1
```

---

## 12. Maintenance Notes

- Keep template placeholders stable unless the renderer is updated at the same time.
- Add tests before changing frontmatter syntax.
- Add tests before changing image-copy behavior.
- Avoid reintroducing a local `sysforge.markdown` implementation that shadows the third-party `markdown` dependency.
- If adding more themes, update CLI validation and package data.
- If adding more Markdown extensions, document the dependency and output implications.

---

# Lessons Learned

## App 24 — Markdown-to-HTML Generator

**SysForge Group | Document 5 of 5**

---

## 1. Project Summary

The Markdown-to-HTML Generator is a documentation-build utility inside SysForge. It converts Markdown files into styled HTML documents, supports single-file and directory builds, generates an index page for directory builds, copies relative images, embeds theme and syntax-highlight CSS, and records build history in shared SysForge state.

This app represents a clear step up from smaller CLI exercises because it combines:

- Third-party package integration.
- Filesystem traversal.
- Template rendering.
- Static asset handling.
- CLI argument design.
- Shared configuration.
- Shared logging.
- Persistent build history.
- Package naming and dependency-shadowing concerns.

---

## 2. Original Goals vs. Actual Outcome

### Original goals

- Convert Markdown files to HTML.
- Provide a CLI interface.
- Support useful documentation output.
- Reuse SysForge shared infrastructure.

### Actual outcome

The final app does more than a minimal converter. It includes:

- Frontmatter parsing.
- Title guessing.
- Markdown extensions for code blocks, tables, TOC, and code highlighting.
- Packaged light/dark themes.
- Packaged HTML template.
- Custom template support.
- Directory builds with index generation.
- Relative image copying.
- Build-history persistence.
- Integration with both standalone and unified SysForge CLIs.

The outcome is still appropriately scoped because the app stops short of becoming a full static-site generator.

---

## 3. Technical Decisions That Paid Off

### Renaming the local package to `mdhtml`

This was one of the most important design decisions. Since the app imports the third-party `markdown` package, naming the local package `sysforge.markdown` created a shadowing risk. The `mdhtml` name makes the package purpose clear while avoiding import conflicts.

### Splitting rendering into small functions

Functions such as `parse_frontmatter()`, `guess_title()`, `collect_markdown_files()`, `render_html_document()`, and `copy_relative_images()` make the app testable without needing to run the entire CLI.

### Strict template placeholders

Failing fast when placeholders are missing prevents silently broken HTML output.

### Copying relative images

This makes generated HTML more useful for real documentation folders without adding remote download logic.

### Shared SysForge paths and history

Build history under `~/.sysforge/docs/build_history.json` makes the app feel integrated into the toolkit instead of isolated.

---

## 4. Technical Decisions That Created Debt

### Minimal frontmatter parser

The parser is useful for simple metadata, but it is not YAML. If users try arrays, nested objects, or multiline YAML blocks, behavior may not match expectations.

### No HTML sanitization

The app assumes trusted local Markdown. That is acceptable for a developer utility, but it should be documented clearly.

### Hardcoded Markdown extensions

The extension list is useful, but not configurable. Users cannot currently turn extensions on/off through config.

### Theme validation is fixed

Only `light` and `dark` are accepted by the CLI. Adding more themes requires code changes.

### No link rewriting

Markdown links pointing to `.md` files are not automatically rewritten to `.html`, which limits larger documentation-site workflows.

---

## 5. What Was Harder Than Expected

### Template replacement order

It was important that placeholder replacement not accidentally modify placeholder-looking text inside the generated body content. The test for preserving body literals shows awareness of this issue.

### Image target parsing

Markdown image syntax can include angle brackets, titles, quoted values, remote URLs, and data URLs. The app handles a useful subset without trying to parse every Markdown edge case.

### File vs. directory output semantics

The logic must treat output differently depending on whether the input is a file or directory, and whether the output path ends with `.html`.

### Packaging static assets

Themes and templates only work reliably if package data is included correctly in `pyproject.toml`.

---

## 6. What Was Easier Than Expected

### Using the `markdown` package

Delegating Markdown parsing avoided a large amount of scope and let the app focus on orchestration.

### Theme switching

Because the template uses CSS placeholders, switching between light and dark themes is straightforward.

### Index generation

The index page is intentionally simple: a sorted list of generated pages. This provides value without becoming a navigation framework.

---

## 7. Python-Specific Learnings

- Dynamic imports through `importlib.import_module()` can provide cleaner setup errors for optional or external dependencies.
- `pathlib.Path` makes recursive traversal, relative paths, suffix changes, and filesystem writes easier to reason about.
- `html.escape()` should be applied to metadata inserted into templates.
- `re` is useful for targeted extraction, but Markdown parsing should not be overdone with regex.
- `typer.Exit` provides clear CLI exit behavior.
- Returning structured dictionaries from build functions makes CLI output and tests easier.
- Package data must be explicitly declared when templates and themes are part of the installed package.

---

## 8. Architecture Insights

### A converter is really a pipeline

The app is not just “read Markdown, write HTML.” It has stages that each deserve a boundary:

- Read input.
- Extract metadata.
- Convert content.
- Apply layout.
- Handle assets.
- Persist outputs.
- Record history.

Once this pipeline is explicit, the code becomes easier to test and extend.

### Shared infrastructure matters in a toolkit

Using shared path, config, logging, and file helpers makes SysForge feel consistent. This is a step toward system design, not just standalone scripting.

### Naming can be architecture

The `mdhtml` package name is not cosmetic. It prevents dependency shadowing and makes import behavior more reliable.

---

## 9. Testing Gaps

Current tests cover important units such as:

- Frontmatter parsing.
- Blank/comment handling inside frontmatter.
- Continuation lines.
- Invalid frontmatter errors.
- Case-insensitive `.md` collection.
- Markdown image target parsing.
- Relative index href calculation.
- Template replacement order.
- Title guessing fallback.

Gaps that remain:

- End-to-end CLI invocation through Typer runner.
- Full single-file build integration test.
- Full directory build integration test with generated index.
- Image copying integration test.
- Custom template failure test.
- Missing dependency behavior test.
- Shared config theme fallback test.
- Build history append behavior test.
- Invalid theme CLI test.
- Link rewriting behavior is not implemented or tested.

---

## 10. Reusable Patterns Identified

- `build_site()` as an orchestrator around smaller pure-ish helper functions.
- Strict template placeholder validation.
- Shared package assets for default themes/templates.
- `SYSFORGE_HOME` for isolated test state.
- History append files for user-visible audit trails.
- Dynamic dependency loading with user-friendly error messages.
- Returning structured build summaries rather than only printing text.

---

## 11. If I Built This Again

I would consider:

1. Adding an end-to-end test that builds a small docs folder.
2. Adding `.md` link rewriting for internal page links.
3. Supporting a `--clean` flag to remove stale output files.
4. Supporting configurable Markdown extensions.
5. Supporting extra CSS through config.
6. Adding an optional sanitized mode for untrusted Markdown.
7. Adding theme discovery rather than hardcoding `light` and `dark`.
8. Adding a watch mode only after the static build path is fully tested.

---

## 12. Open Questions

- Should Markdown links to local `.md` files be rewritten automatically?
- Should the app support full YAML frontmatter?
- Should build history rotate or be queryable through a command?
- Should custom themes be user-provided paths rather than fixed package names?
- Should the app provide a `--no-index` option for directory builds?
- Should failed directory builds still generate `index.html`?
- Should output include source maps or metadata comments for traceability?

---

## 13. Constitution Alignment

This app aligns well with the project constitution because it is:

- Authentic learner-scale architecture with clear boundaries.
- Appropriately scoped for a SysForge utility.
- More advanced than a single-file beginner script.
- Verifiable through function-level tests.
- Integrated with shared package infrastructure rather than copied helpers.
- Honest about limitations and future improvements.

The strongest engineering evidence is the separation between parsing, conversion, rendering, filesystem handling, and history logging. The main weakness is incomplete end-to-end testing around the full build workflow, which should be addressed before treating it as production-grade.
