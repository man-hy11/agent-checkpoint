#!/usr/bin/env python3
"""Advise Gemini CLI to checkpoint stale progress before compression."""

import json
import os
from pathlib import Path
import subprocess
import sys


_ADVISORY = (
    "The project checkpoint is missing or stale. Invoke /checkpoint now so "
    "current progress is available after context compression."
)


def main() -> int:
    payload = _read_payload()
    if payload is None:
        return 0
    project_root = _project_root(payload)
    status = _checkpoint_status(project_root)
    if status is None or not (
        _needs_checkpoint(status) or _checkpoint_is_stale(project_root)
    ):
        return 0
    json.dump({"systemMessage": _ADVISORY}, sys.stdout, sort_keys=True)
    sys.stdout.write("\n")
    return 0


def _read_payload() -> dict | None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError, UnicodeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _project_root(payload: dict) -> Path:
    for field in ("cwd", "workspacePath"):
        value = payload.get(field)
        if isinstance(value, str) and value:
            return Path(value)
    return Path(os.getcwd())


def _checkpoint_status(project_root: Path) -> dict | None:
    launcher = Path(__file__).resolve().parents[1] / "bin" / "agent-checkpoint"
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(launcher),
                "status",
                "--root",
                str(project_root),
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    try:
        status = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    return status if isinstance(status, dict) else None


def _needs_checkpoint(status: dict) -> bool:
    entries = status.get("checkpoint_entries")
    return (
        not isinstance(entries, int)
        or isinstance(entries, bool)
        or entries < 1
        or status.get("checkpoint_error") is not None
    )


def _checkpoint_is_stale(project_root: Path) -> bool:
    launcher = Path(__file__).resolve().parents[1] / "bin" / "agent-checkpoint"
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(launcher),
                "doctor",
                "--root",
                str(project_root),
                "--adapter",
                "gemini-cli",
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return False
    if result.returncode != 0:
        return False
    try:
        report = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError, ValueError):
        return False
    warnings = report.get("warnings") if isinstance(report, dict) else None
    return isinstance(warnings, str) and "checkpoint is stale:" in warnings


if __name__ == "__main__":
    raise SystemExit(main())
