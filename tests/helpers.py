from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys


FIXED_TIME = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)
VALID_BODY = """## 1. Goal / Plan
- Build it

## 2. Progress
- Started

## 3. Current Focus
- Parser

## 4. Next Actions / TODO
- Test it

## 5. Decisions / Constraints / Notes
- Standard library only
"""

CONFIG_DEFAULTS = {
    "progress_path": "PROGRESS.md",
    "archive_path": "PROGRESS_ARCHIVE.md",
}


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = PROJECT_ROOT / "core"


def run_cli(*arguments: str, input_text: str | None = None) -> subprocess.CompletedProcess:
    """Run the public CLI module with the repository core on ``PYTHONPATH``."""
    environment = os.environ.copy()
    existing_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = os.pathsep.join(
        path
        for path in (str(CORE_ROOT), existing_pythonpath)
        if path
    )
    return subprocess.run(
        [sys.executable, "-m", "agent_checkpoint.cli", *arguments],
        cwd=PROJECT_ROOT,
        env=environment,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )
