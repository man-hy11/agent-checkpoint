"""Atomic paired writes of CURRENT.md and EVIDENCE.md. Owns all filesystem mutation."""

import os
from pathlib import Path

from . import storage
from .work_state import StateError, WorkState, apply_event, parse_state, render_state

DEFAULT_LOCK_TIMEOUT_SECONDS = 10.0


class StoreError(StateError):
    """A store-level operation could not complete."""


def claim(
    project_root: Path,
    current_path: Path,
    evidence_path: Path,
    *,
    unit_id: str,
    event: str,
    plan_revision: int,
    evidence_text: str,
    lock_timeout_seconds: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
) -> WorkState:
    """Apply one legal transition and append evidence atomically, or raise unchanged."""
    lock_path = current_path.parent / ".agent-checkpoint.lock"
    with storage._open_safe_parent(project_root, lock_path, create=True) as lock_parent:
        descriptor = storage._open_at(
            lock_parent,
            lock_path.name,
            os.O_RDWR | os.O_CREAT | os.O_APPEND,
            0o600,
        )
        with os.fdopen(descriptor, "a+b") as lock_file:
            storage._ensure_lock_byte(lock_file)
            storage._acquire_lock(lock_file, lock_timeout_seconds)
            try:
                current_text = storage._read_text_no_follow(project_root, current_path)
                state = parse_state(current_text)
                updated = apply_event(state, unit_id, event, plan_revision)
                rendered_current = render_state(current_text, updated)
                rendered_evidence = _append_evidence(
                    _existing_evidence(project_root, evidence_path), evidence_text
                )
                storage._atomic_write_pair(
                    project_root,
                    current_path,
                    rendered_current,
                    evidence_path,
                    rendered_evidence,
                )
                return updated
            finally:
                storage._release_lock(lock_file)


def _existing_evidence(project_root: Path, evidence_path: Path) -> str:
    try:
        return storage._read_text_no_follow(project_root, evidence_path)
    except FileNotFoundError:
        return "# Evidence\n"


def _append_evidence(existing: str, entry: str) -> str:
    trimmed = entry.strip("\n")
    separator = "" if existing.endswith("\n") else "\n"
    return f"{existing}{separator}\n{trimmed}\n"
