"""Optional auto-commit of a completed work package's changes at handoff.

Unlike ``git_state.py`` (strictly read-only), this module performs a real
Git mutation: staging and committing the working tree. It only runs when a
project has explicitly opted in via ``auto_commit_on_handoff`` in
``.agent-checkpoint.toml`` -- the default is off, since committing on the
project's behalf is a meaningfully different guarantee than the read-only
metadata the rest of the package exposes.

Every failure mode here is a soft skip, never an exception: an unavailable
Git binary, a non-repository root, a clean tree, or a failing ``git commit``
(e.g. a pre-commit hook rejecting the change) all resolve to a
``CommitResult`` the caller can report and move past. Handoff must still
complete when the commit does not happen.
"""

from dataclasses import dataclass
from pathlib import Path
import subprocess

from .config import ProjectConfig, resolve_checkpoint_paths


@dataclass(frozen=True)
class CommitResult:
    """Outcome of an attempted auto-commit; never raises on failure."""

    committed: bool
    reason: str
    commit_sha: str | None = None


def commit_work_package(
    project_root: Path,
    config: ProjectConfig,
    work_id: str,
    work_type: str,
) -> CommitResult:
    """Stage and commit the working tree, scoped to what the package touched.

    Returns a ``CommitResult`` describing what happened; never raises. The
    working tree at handoff time is treated as the work package's footprint
    -- there is no per-unit file tracking to scope against more narrowly.
    """
    root, _, _ = resolve_checkpoint_paths(project_root, config)

    if not config.auto_commit_on_handoff:
        return CommitResult(committed=False, reason="auto_commit_on_handoff is disabled")

    if _git(root, "rev-parse", "--show-toplevel") is None:
        return CommitResult(committed=False, reason="not a Git repository")

    status = _git(root, "status", "--porcelain")
    if status is None:
        return CommitResult(committed=False, reason="unable to read Git status")
    if not status.strip():
        return CommitResult(committed=False, reason="no changes to commit")

    add_result = _run(root, "add", "-A")
    if add_result is None or add_result.returncode != 0:
        return CommitResult(committed=False, reason="git add failed")

    # Staging can legitimately produce no diff (e.g. only ignored files were
    # dirty in a way `status` reported but `add -A` did not stage).
    staged = _git(root, "diff", "--cached", "--name-only")
    if staged is None or not staged.strip():
        return CommitResult(committed=False, reason="no changes staged")

    message = f"checkpoint: complete {work_type} work package {work_id}"
    commit_result = _run(root, "commit", "-m", message)
    if commit_result is None or commit_result.returncode != 0:
        return CommitResult(committed=False, reason="git commit failed")

    commit_sha = _git(root, "rev-parse", "--short", "HEAD")
    return CommitResult(
        committed=True,
        reason="committed",
        commit_sha=commit_sha.strip() if commit_sha else None,
    )


def _git(project_root: Path, *arguments: str) -> str | None:
    """Run a Git command, returning stdout on success or None on failure."""
    result = _run(project_root, *arguments)
    if result is None or result.returncode != 0:
        return None
    return result.stdout


def _run(project_root: Path, *arguments: str) -> subprocess.CompletedProcess | None:
    """Run a Git command, tolerating an unavailable or misbehaving Git binary."""
    try:
        return subprocess.run(
            ["git", "-C", str(project_root), *arguments],
            capture_output=True,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (FileNotFoundError, OSError):
        return None
