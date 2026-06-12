from __future__ import annotations

import runpy
from pathlib import Path


CURRENT_FILE = Path(__file__).resolve()
SCRIPT_DIR = CURRENT_FILE.parent

candidates = sorted(
    [
        path
        for path in SCRIPT_DIR.glob("sync_templates_to_db*.py")
        if path.resolve() != CURRENT_FILE
    ],
    key=lambda path: path.stat().st_mtime,
    reverse=True,
)

if not candidates:
    raise RuntimeError("Missing sync_templates_to_db*.py implementation")

runpy.run_path(str(candidates[0]), run_name="__main__")
