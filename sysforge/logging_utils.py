
from __future__ import annotations

import logging
import os
from pathlib import Path

from sysforge.sysforge_paths import ensure_home_layout, get_central_log_file


def _current_log_level() -> int:
    if os.environ.get("SYSFORGE_QUIET") == "1":
        return logging.WARNING
    if os.environ.get("SYSFORGE_VERBOSE") == "1":
        return logging.DEBUG
    return logging.INFO

def get_logger(name: str) -> logging.Logger:
    ensure_home_layout()
    logger = logging.getLogger(name)
    if getattr(logger, "_sysforge_ready", False):
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.setLevel(logging.DEBUG)
            else:
                handler.setLevel(_current_log_level())
        return logger

    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")

    file_handler = logging.FileHandler(get_central_log_file(), encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(_current_log_level())
    logger.addHandler(console_handler)

    logger.propagate = False
    logger._sysforge_ready = True  # type: ignore[attr-defined]
    return logger


def log_path_message(logger_name: str, action: str, path: Path) -> None:
    logger = get_logger(logger_name)
    logger.info("%s: %s", action, path)
