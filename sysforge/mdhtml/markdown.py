from __future__ import annotations

import importlib
import os
import re
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, cast

import typer

from sysforge.common import (
    load_json_file,
    print_error,
    write_json_file,
    write_text_file,
)
from sysforge.logging_utils import get_logger
from sysforge.shared_config import load_shared_config
from sysforge.sysforge_paths import (
    ensure_home_layout,
    get_docs_history_file,
    get_markdown_template_path,
    get_theme_path,
)

app = typer.Typer(help="Convert Markdown files into styled HTML.")
logger = get_logger("sysforge.mdhtml")
IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\(\s*([^)]+?)\s*\)")


def _parse_markdown_image_target(raw: str) -> str | None:
    inner = raw.strip()
    if not inner or inner.lower().startswith("data:"):
        return None
    if inner.startswith("<"):
        end = inner.find(">")
        inner = inner[1:end].strip() if end != -1 else inner[1:].strip()
    else:
        inner = inner.split(None, 1)[0].strip()
    inner = inner.strip("\"'")
    return inner or None

def _replace_placeholder_once(template: str, key: str, value: str) -> str:
    marker = f"{{{{{key}}}}}"
    if marker not in template:
        raise ValueError(f"Template is missing placeholder: {marker}")
    before, sep, after = template.partition(marker)
    return before + value + after

def _apply_html_template(
    template: str,
    *,
    theme_css: str,
    pygments_css: str,
    title: str,
    generated_at: str,
    content: str,
) -> str:

    result = template
    result = _replace_placeholder_once(result, "theme_css", theme_css)
    result = _replace_placeholder_once(result, "pygments_css", pygments_css)
    result = _replace_placeholder_once(result, "title", title)
    result = _replace_placeholder_once(result, "generated_at", generated_at)
    result = _replace_placeholder_once(result, "content", content)
    return result

def load_markdown_dependency() -> Any:
    try:
        return importlib.import_module("markdown")
    except ModuleNotFoundError:
        print_error(
            "The markdown package is not installed. Run `pip install -e .` first.",
            exit_code=2,
        )


def load_pygments_formatter() -> Any:
    try:
        pygments_module = importlib.import_module("pygments.formatters")
        return pygments_module.HtmlFormatter
    except ModuleNotFoundError:
        print_error("Pygments is not installed. Run `pip install -e .` first.", exit_code=2)

def _strip_optional_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value

def parse_frontmatter(raw_text: str, source: Path) -> tuple[dict[str, str], str]:
    if not raw_text.startswith("---\n"):
        return {}, raw_text

    lines = raw_text.splitlines()
    frontmatter: dict[str, str] = {}
    last_key: str | None = None

    for line_number in range(1, len(lines)):
        line = lines[line_number]
        stripped = line.strip()
        if stripped == "---":
            body = "\n".join(lines[line_number + 1 :])
            return frontmatter, body
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in line:
            if last_key is None:
                raise ValueError(f"{source}: invalid frontmatter line {line_number + 1}")
            frontmatter[last_key] = f"{frontmatter[last_key]}\n{line.rstrip()}"
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = _strip_optional_quotes(value.strip())
        frontmatter[key] = value
        last_key = key

    raise ValueError(f"{source}: frontmatter was opened but not closed")

def guess_title(frontmatter: dict[str, str], body: str, source: Path) -> str:
    title = frontmatter.get("title", "").strip()
    if title:
        return title
    for line in body.splitlines():
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return source.stem.replace("_", " ").title()

def load_template(template_path: Path | None) -> str:
    if template_path is None:
        template_path = get_markdown_template_path()
    return template_path.read_text(encoding="utf-8")

def load_theme_css(theme_name: str) -> str:
    theme_path = get_theme_path(theme_name)
    if not theme_path.exists():
        print_error(f"Theme not found: {theme_name}")
    return theme_path.read_text(encoding="utf-8")

def build_pygments_css() -> str:
    formatter_class = load_pygments_formatter()
    return cast(str, formatter_class().get_style_defs(".codehilite"))

def render_html_document(
    body_html: str,
    *,
    title: str,
    generated_at: str,
    template_path: Path | None,
    theme_name: str,
) -> str:
    template = load_template(template_path)
    return _apply_html_template(
        template,
        theme_css=load_theme_css(theme_name),
        pygments_css=build_pygments_css(),
        title=escape(title),
        generated_at=escape(generated_at),
        content=body_html,
    )

def copy_relative_images(source_file: Path, destination_file: Path, markdown_text: str) -> None:
    for raw in IMAGE_PATTERN.findall(markdown_text):
        raw_path = _parse_markdown_image_target(raw)
        if raw_path is None:
            continue
        if raw_path.startswith("http://") or raw_path.startswith("https://"):
            continue

        image_source = (source_file.parent / raw_path).resolve()
        if not image_source.exists() or not image_source.is_file():
            continue

        image_destination = destination_file.parent / raw_path
        image_destination.parent.mkdir(parents=True, exist_ok=True)
        image_destination.write_bytes(image_source.read_bytes())


def collect_markdown_files(source: Path) -> list[Path]:
    paths = [
        path for path in source.rglob("*") if path.is_file() and path.suffix.casefold() == ".md"
    ]
    return sorted(paths, key=lambda p: str(p).casefold())

def convert_markdown_file(
    source_file: Path,
    destination_file: Path,
    *,
    theme_name: str,
    template_path: Path | None,
) -> dict[str, Any]:
    markdown_module = load_markdown_dependency()
    raw_text = source_file.read_text(encoding="utf-8")
    frontmatter, markdown_body = parse_frontmatter(raw_text, source_file)
    title = guess_title(frontmatter, markdown_body, source_file)
    html_body = markdown_module.markdown(
        markdown_body,
        extensions=["fenced_code", "tables", "toc", "codehilite"],
    )
    document = render_html_document(
        html_body,
        title=title,
        generated_at=datetime.now().isoformat(timespec="seconds"),
        template_path=template_path,
        theme_name=theme_name,
    )
    destination_file.parent.mkdir(parents=True, exist_ok=True)
    write_text_file(destination_file, document)
    copy_relative_images(source_file, destination_file, markdown_body)

    return {
        "source": str(source_file),
        "output": str(destination_file),
        "title": title,
        "date": frontmatter.get("date", ""),
    }


def _index_href_for_output(output_file: Path, output_dir: Path) -> str:
    out_abs = output_file.resolve()
    base_abs = output_dir.resolve()
    try:
        return out_abs.relative_to(base_abs).as_posix()
    except ValueError:
        return Path(os.path.relpath(str(out_abs), str(base_abs))).as_posix()

def build_index_page(
    output_dir: Path,
    items: list[dict[str, Any]],
    theme_name: str,
    template_path: Path | None,
) -> None:
    sorted_items = sorted(items, key=lambda item: item.get("date", ""), reverse=True)
    lines = ["<h2>Generated Pages</h2>", "<ul>"]
    for item in sorted_items:
        href = _index_href_for_output(Path(item["output"]), output_dir)
        date_text = item.get("date") or "No date"
        title = str(item.get("title", ""))
        link = f'<a href="{escape(href, quote=True)}">{escape(title)}</a>'
        lines.append(f"<li>{link} - {escape(str(date_text))}</li>")
    lines.append("</ul>")
    document = render_html_document(
        "\n".join(lines),
        title="SysForge Static Site",
        generated_at=datetime.now().isoformat(timespec="seconds"),
        template_path=template_path,
        theme_name=theme_name,
    )
    write_text_file(output_dir / "index.html", document)

def append_build_history(payload: dict[str, Any]) -> None:
    history_path = get_docs_history_file()
    history = load_json_file(history_path, default=[])
    history.append(payload)
    write_json_file(history_path, history, atomic=True)


def build_site(
    source: Path,
    output: Path,
    *,
    theme_name: str,
    template_path: Path | None,
) -> dict[str, Any]:
    ensure_home_layout()
    load_shared_config()

    if not source.exists():
        print_error(f"Source path not found: {source}")

    built_files: list[dict[str, Any]] = []
    errors: list[str] = []

    if source.is_file(): 
        destination = output if output.suffix.lower() == ".html" else output / f"{source.stem}.html"
        try:
            built_files.append(
                convert_markdown_file(
                    source,
                    destination,
                    theme_name=theme_name,
                    template_path=template_path,
                )
            )
        except BaseException as exc:
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            errors.append(str(exc))
    else:
        markdown_files = collect_markdown_files(source)
        for markdown_file in markdown_files:
            relative_path = markdown_file.relative_to(source).with_suffix(".html")
            destination = output / relative_path
            try:
                built_files.append(
                    convert_markdown_file(
                        markdown_file,
                        destination,
                        theme_name=theme_name,
                        template_path=template_path,
                    )
                )
            except BaseException as exc:
                if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                    raise
                errors.append(str(exc))
        build_index_page(output, built_files, theme_name, template_path)

    
    append_build_history(
        {
            "timestamp": datetime.now().isoformat(),
            "input_path": str(source),
            "output_path": str(output),
            "theme": theme_name,
            "files_built": len(built_files),
            "errors": errors,
        }
    )

    logger.info("Markdown build completed for %s", source)
    return {"built_files": built_files, "errors": errors}

@app.command()
def build(
    source: Path = typer.Argument(..., help="Markdown file or folder."),
    output: Path = typer.Option(..., "--output", help="HTML file or output folder."),
    theme: str = typer.Option(None, "--theme", help="light or dark"),
    template: Path | None = typer.Option(None, "--template", help="Optional HTML template file."),
) -> None:
    config = load_shared_config()
    chosen_theme = theme or config.get("markdown", {}).get("theme", "light")
    if chosen_theme not in {"light", "dark"}:
        print_error("--theme must be light or dark.")

    result = build_site(source, output, theme_name=chosen_theme, template_path=template)
    typer.echo(f"Built {len(result['built_files'])} HTML file(s).")
    if result["errors"]:
        typer.echo("")
        typer.echo("Errors")
        for error in result["errors"]:
            typer.echo(f"- {error}")
        raise typer.Exit(code=1)

    for item in result["built_files"]:
        typer.echo(f"{item['source']} -> {item['output']}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
