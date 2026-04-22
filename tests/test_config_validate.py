from __future__ import annotations

import json
from pathlib import Path

import pytest

from sysforge.common import write_json_file
from sysforge.config.config import (
    apply_environment_overrides,
    diff_configs,
    load_config_file,
    validate_against_schema,
)

