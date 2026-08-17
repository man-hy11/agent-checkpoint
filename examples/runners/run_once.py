#!/usr/bin/env python3
"""Stub runner — consume `work status --json` and exit status only; never agent prose.

Exit codes:
  0  active work present, no terminal condition (running, ready, pending)
  1  stopped: failed, blocked, or no active package — recovery required
  2  complete: all units passed — run checkpoint-handoff
"""
import json
import subprocess
import sys
from pathlib import Path


def _work_status(project_root: Path, cli: list[str]) -> dict | None:
    """Return parsed work status JSON, or None if unavailable."""
    result = subprocess.run(
        cli + ["work", "status", "--json", "--root", str(project_root)],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def run_once(project_root: Path, cli: list[str]) -> int:
    """
    Inspect work status once and return a signal code.

    Returns:
      0  work is in progress (ready/running/pending) — invoke the next skill
      1  work is stopped (failed/blocked or no package) — recovery required
      2  work is complete (all units passed) — run checkpoint-handoff and exit
    """
    status = _work_status(project_root, cli)
    if status is None:
        print("runner: no active work package", file=sys.stderr)
        return 1

    next_skill_name = status.get("next_skill")
    state = status.get("state")
    print(
        f"runner: unit={status.get('current_unit')} state={state} next={next_skill_name}",
        file=sys.stderr,
    )

    if next_skill_name == "checkpoint-handoff":
        print("runner: work complete — invoke checkpoint-handoff", file=sys.stderr)
        return 2

    if state in ("failed", "blocked"):
        print(f"runner: stopping — unit is {state}, recovery required", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--cli", nargs="+", default=["agent-checkpoint"])
    args = parser.parse_args()
    sys.exit(run_once(args.root, args.cli))
