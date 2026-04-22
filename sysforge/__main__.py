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























def main() -> None:
    app()


if __name__ == "__main__":
    main()
