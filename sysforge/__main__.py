"""SysForge: a developer operations toolkit."""

from __future__ import annotations

import os
from pathlib import Path

import typer

from sysforge import __version__
from sysforge.briefing.briefing import app as briefing_app
from sysforge.config.config import app as config_app
from sysforge.logging_utils import get_logger
from sysforge.mdhtml.markdown import app as markdown_app
from sysforge.monitor.monitor import app as monitor_app
from sysforge.organizer.organizer import app as organizer_app
from sysforge.reporting import build_daily_report
from sysforge.shared_config import load_shared_config
from sysforge.sysforge_paths import ensure_home_layout
from sysforge.timetracker.timetracker import app as time_app

app = typer.Typer(help="SysForge: a developer operations toolkit.")


def version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def root(
    verbose: bool = typer.Option(False, "--verbose", help="Show extra logging."),
    quiet: bool = typer.Option(False, "--quiet", help="Show less logging."),
    config: Path | None = typer.Option(None, "--config", help="Path to shared sysforge config."),
    version: bool = typer.Option(
        False,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    if verbose and quiet:
        typer.secho(
            "Choose either --verbose or --quiet, not both.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    if verbose:
        os.environ["SYSFORGE_VERBOSE"] = "1"
    else:
        os.environ.pop("SYSFORGE_VERBOSE", None)

    if quiet:
        os.environ["SYSFORGE_QUIET"] = "1"
    else:
        os.environ.pop("SYSFORGE_QUIET", None)

    if config is not None:
        os.environ["SYSFORGE_CONFIG"] = str(config)

    ensure_home_layout()
    for logger_name in [
        "sysforge",
        "sysforge.organizer",
        "sysforge.mdhtml",
        "sysforge.briefing",
        "sysforge.timetracker",
        "sysforge.config",
        "sysforge.monitor",
    ]:
        get_logger(logger_name)
    logger = get_logger("sysforge")
    logger.debug("SysForge CLI started")


@app.command()
def report(
    format: str | None = typer.Option(None, "--format", help="text, markdown, or html"),
) -> None:
    config = load_shared_config()
    chosen_format = format or config.get("report", {}).get("default_format", "text")
    if chosen_format not in {"text", "markdown", "html"}:
        typer.secho("--format must be text, markdown, or html.", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    content, output_path = build_daily_report(chosen_format)
    typer.echo(content)
    typer.echo("")
    typer.echo(f"Saved report to {output_path}")


app.add_typer(organizer_app, name="organize")
app.add_typer(markdown_app, name="docs")
app.add_typer(briefing_app, name="briefing")
app.add_typer(time_app, name="time")
app.add_typer(config_app, name="config")
app.add_typer(monitor_app, name="health")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
