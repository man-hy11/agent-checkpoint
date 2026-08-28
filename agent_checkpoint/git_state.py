"""Read-only Git metadata for checkpoint diagnostics."""

from dataclasses import dataclass
from pathlib import Path
import subprocess

from .config import ProjectConfig, resolve_checkpoint_paths
from .secrets import find_secret_kind


@dataclass(frozen=True)
class GitState:
    """Safe, content-free metadata about the project's Git worktree."""

    branch: str | None = None
    worktree: str | None = None
    changed_files: tuple[str, ...] = ()
    progress_tracked: bool = False
    progress_ignored: bool = False
    archive_tracked: bool = False
    archive_ignored: bool = False
    git_available: bool = False


def collect_git_state(project_root: Path, config: ProjectConfig) -> GitState:
    """Return safe Git metadata, tolerating unavailable Git and non-repositories."""
    root, _, _ = resolve_checkpoint_paths(project_root, config)
    top_level = _git(root, "rev-parse", "--show-toplevel")
    if top_level is None:
        return GitState()

    branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    status = _git(root, "status", "--porcelain")
    progress_path = config.progress_path.as_posix()
    progress_ignored = (
        _git_exit_code(root, "check-ignore", "-q", "--no-index", "--", progress_path)
        == 0
    )
    progress_tracked = (
        _git_exit_code(root, "ls-files", "--error-unmatch", "--", progress_path)
        == 0
    )
    archive_path = config.archive_path.as_posix()
    archive_ignored = (
        _git_exit_code(root, "check-ignore", "-q", "--no-index", "--", archive_path)
        == 0
    )
    archive_tracked = (
        _git_exit_code(root, "ls-files", "--error-unmatch", "--", archive_path)
        == 0
    )
    return GitState(
        branch=_safe_git_metadata(branch.strip()) if branch else None,
        worktree=_safe_git_metadata(top_level.strip()),
        changed_files=tuple(
            _safe_git_metadata(filename) for filename in _changed_files(status or "")
        ),
        progress_tracked=progress_tracked,
        progress_ignored=progress_ignored,
        archive_tracked=archive_tracked,
        archive_ignored=archive_ignored,
        git_available=True,
    )


def _git(project_root: Path, *arguments: str) -> str | None:
    """Run a successful read-only Git command, returning no output on failure."""
    try:
        result = subprocess.run(
            ["git", "-C", str(project_root), *arguments],
            capture_output=True,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (FileNotFoundError, OSError):
        return None
    return result.stdout if result.returncode == 0 else None


def _git_exit_code(project_root: Path, *arguments: str) -> int | None:
    """Run a read-only Git predicate and return its exit status."""
    try:
        result = subprocess.run(
            ["git", "-C", str(project_root), *arguments],
            capture_output=True,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (FileNotFoundError, OSError):
        return None
    return result.returncode


def _changed_files(porcelain: str) -> tuple[str, ...]:
    """Extract only porcelain filenames; never inspect blobs or diff output."""
    filenames = []
    for line in porcelain.splitlines():
        if len(line) >= 4:
            filenames.append(line[3:])
    return tuple(filenames)


def _safe_git_metadata(value: str) -> str:
    """Redact probable credentials before Git metadata reaches public state."""
    if find_secret_kind(value) is not None:
        return "[omitted metadata with probable credential]"
    return value
