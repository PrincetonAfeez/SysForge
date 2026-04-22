from __future__ import annotations

import importlib
import os
import subprocess
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_deprecated_markdown_import_emits_warning() -> None:
    code = (
        "import warnings\n"
        "warnings.simplefilter('always', DeprecationWarning)\n"
        "import sysforge.markdown.markdown as legacy\n"
        "import sysforge.mdhtml.markdown as current\n"
        "assert legacy is current\n"
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = (
        str(ROOT) if "PYTHONPATH" not in env else f"{ROOT}{os.pathsep}{env['PYTHONPATH']}"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
        env=env,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "deprecated" in proc.stderr.lower()
