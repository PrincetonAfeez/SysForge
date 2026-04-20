from __future__ import annotations

import os
from pathlib import Path
from typing import Any, cast

from sysforge.common import load_json_file
from sysforge.sysforge_paths import (
    ensure_home_layout,
    get_default_config_path,
    get_user_config_path,
)

