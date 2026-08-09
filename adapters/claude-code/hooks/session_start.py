#!/usr/bin/env python3
"""Point a fresh Claude session at the template-backed work package."""

import json
import os
from pathlib import Path
import sys


_NEW_SESSION_GUIDANCE = """Checkpoint handoff available. Read PROGRESS.md first.
Then follow the work-package pointer recorded there. Execute only the Current
Target; do not rely on the prior session's compacted conversation history."""


def main() -> int:
    payload = _read_payload()
    if payload is None or payload.get("source") != "startup":
        return 0
    project_root = _project_root(payload)
    guidance = _workflow_guidance(project_root)
    if guidance is None:
        return 0
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": guidance,
            }
        },
        sys.stdout,
        sort_keys=True,
    )
    sys.stdout.write("\n")
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


def _workflow_guidance(project_root: Path) -> str | None:
    progress = project_root / "PROGRESS.md"
    try:
        text = progress.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    marker = "- Work package: .agent-checkpoint/work/"
    for line in text.splitlines():
        if line.startswith(marker):
            work_id = line.removeprefix(marker).strip().rstrip("/")
            if work_id and all(char.islower() or char.isdigit() or char == "-" for char in work_id):
                return (
                    f"{_NEW_SESSION_GUIDANCE}\nThen read "
                    f".agent-checkpoint/work/{work_id}/CURRENT.md and "
                    "CONTINUE_PROMPT.md."
                )
    return _NEW_SESSION_GUIDANCE


if __name__ == "__main__":
    raise SystemExit(main())
