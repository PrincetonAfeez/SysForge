from __future__ import annotations

import csv
import ctypes
import json
import os
import shutil
import stat
import sys
from ctypes import wintypes
from datetime import datetime
from pathlib import Path
from typing import Any, NoReturn

import typer

def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
