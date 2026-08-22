#!/usr/bin/env python3
"""Create an initial checkpoint before Claude compaction when needed."""

import json
import os
from pathlib import Path
import subprocess
import sys


_INITIAL_ENTRY = """## 1. Goal / Plan
- Bootstrap checkpoint created automatically by the Claude PreCompact hook.
- Replace this placeholder with the concrete task goal and plan in the next manual checkpoint.

## 2. Progress
- No prior checkpoint was available when compaction started.
- No task progress or verification was captured because the lifecycle hook cannot access conversation history.

## 3. Current Focus
- Reconstruct the active task context after compaction before making further changes.

## 4. Next Actions / TODO
- Write a manual checkpoint with the real goal, progress, focus, and decisions.
- Record concrete test or build results with the next checkpoint.

## 5. Decisions / Constraints / Notes
- This entry was created automatically because no checkpoint existed.
- Keep bootstrap entries free of secrets, diff content, and guessed conversation summaries.
- Do not treat this bootstrap entry as a substitute for a task-specific handoff.
"""


def main() -> int:
    payload = _read_payload()
    if payload is None:
        return 0
    project_root = _project_root(payload)
    status = _checkpoint_status(project_root)
    if status is None or status.get("checkpoint_exists") is not False:
        return 0
    if _write_initial_checkpoint(project_root):
        _emit_json(
            {
                "continue": False,
                "stopReason": (
                    "Checkpoint saved. Start a fresh Claude Code session in this "
                    "project, then read the root CONTINUE_PROMPT.md before "
                    "continuing."
                ),
            }
        )
        return 0

    _emit_json(
        {
            "decision": "block",
            "reason": (
                "No project checkpoint exists and the automatic initial checkpoint "
                "could not be written. Run /agent-checkpoint:checkpoint before "
                "compacting, then retry."
            ),
        }
    )
    return 0


def _read_payload() -> dict | None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError, UnicodeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _project_root(payload: dict) -> Path:
    cwd = payload.get("cwd")
    return Path(cwd) if isinstance(cwd, str) and cwd else Path(os.getcwd())


def _checkpoint_status(project_root: Path) -> dict | None:
    result = _run_launcher("status", "--root", str(project_root), "--json")
    if result is None or result.returncode != 0:
        return None
    try:
        status = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    return status if isinstance(status, dict) else None


def _write_initial_checkpoint(project_root: Path) -> bool:
    result = _run_launcher(
        "write", "--root", str(project_root), "--entry", "-", input_text=_INITIAL_ENTRY
    )
    return result is not None and result.returncode == 0


def _run_launcher(
    *arguments: str, input_text: str | None = None
) -> subprocess.CompletedProcess[str] | None:
    launcher = Path(__file__).resolve().parents[1] / "bin" / "agent-checkpoint"
    try:
        return subprocess.run(
            [sys.executable, str(launcher), *arguments],
            text=True,
            capture_output=True,
            input=input_text,
            check=False,
        )
    except OSError:
        return None


def _emit_json(payload: dict) -> None:
    json.dump(payload, sys.stdout, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
