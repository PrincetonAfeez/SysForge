from __future__ import annotations

import json
from pathlib import Path

import pytest

from sysforge.organizer.organizer import (
    choose_destination,
    resolve_relative_folder,
    run_organizer,
)

