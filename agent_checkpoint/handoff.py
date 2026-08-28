"""Project-wide handoff reports for work discovered mid-step and deferred.

A handoff report records something a step noticed but chose not to fold into
its own scope (per the size-judgment rule: small fixes fold in, size-judged-
large discoveries get a report here instead). Reports live under
``.agent-checkpoint/handoff/``, one markdown file per deferred item, and stay
"open" until resolved via ``resolve_handoff_report`` (or removed by hand) --
resolution deletes the report file outright rather than tracking a separate
closed state.
"""

from pathlib import Path
import re

from . import storage
from .config import ConfigError

_HANDOFF_DIRNAME = "handoff"
_CHECKPOINT_DIRNAME = ".agent-checkpoint"
_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


def _handoff_dir(project_root: Path) -> Path:
    return Path(project_root) / _CHECKPOINT_DIRNAME / _HANDOFF_DIRNAME


def _slugify(title: str) -> str:
    slug = _SLUG_PATTERN.sub("-", title.strip().lower()).strip("-")
    return slug or "untitled"


def write_handoff_report(
    project_root: Path,
    work_id: str,
    unit_id: str,
    title: str,
    body: str,
) -> Path:
    """Write a deferred-item report and return its path.

    Never silently overwrites an existing report: a filename collision gets a
    numeric suffix instead of clobbering the earlier report.
    """
    root = Path(project_root).resolve()
    handoff_dir = _handoff_dir(root)
    base_name = f"{work_id}-{unit_id}-{_slugify(title)}"

    text = _render_report(work_id, unit_id, title, body)
    suffix = 0
    while True:
        candidate_name = base_name if suffix == 0 else f"{base_name}-{suffix}"
        target_path = handoff_dir / f"{candidate_name}.md"
        if not target_path.exists():
            storage._atomic_write(root, target_path, text)
            return target_path
        suffix += 1


def _render_report(work_id: str, unit_id: str, title: str, body: str) -> str:
    return (
        f"# {title}\n\n"
        f"Work: {work_id}\n"
        f"Unit: {unit_id}\n\n"
        f"{body.rstrip()}\n"
    )


def list_open_handoff_reports(project_root: Path) -> list[Path]:
    """Return every report under ``.agent-checkpoint/handoff/``, sorted by name.

    Returns ``[]`` when the directory does not exist yet -- absence is a
    normal, common state (the directory is created on first write, not
    eagerly). A symlinked entry is skipped rather than followed.
    """
    handoff_dir = _handoff_dir(Path(project_root).resolve())
    if not handoff_dir.is_dir():
        return []
    reports: list[Path] = []
    for entry in sorted(handoff_dir.iterdir(), key=lambda path: path.name):
        if entry.is_symlink():
            continue
        if entry.is_file():
            reports.append(entry)
    return reports


def resolve_handoff_report(project_root: Path, name: str) -> None:
    """Remove a resolved report, once a session has acted on what it describes.

    ``name`` is a bare report filename (with or without the trailing
    ``.md``) -- never a path with directory components, so a traversal
    attempt (e.g. ``../../etc/passwd``) is refused before touching the
    filesystem, not merely resolved-and-rejected after the fact. Raises
    ``ConfigError`` when the name is empty, contains a path separator, does
    not exist under ``.agent-checkpoint/handoff/``, or names a symlink
    (never followed or deleted, matching ``list_open_handoff_reports``'s
    existing symlink-skip rigor).
    """
    root = Path(project_root).resolve()
    handoff_dir = _handoff_dir(root)

    candidate = name if name.endswith(".md") else f"{name}.md"
    if not candidate or candidate in (".md",) or "/" in candidate or "\\" in candidate:
        raise ConfigError(f"invalid handoff report name: {name!r}")
    if candidate in (".", ".."):
        raise ConfigError(f"invalid handoff report name: {name!r}")

    target_path = handoff_dir / candidate
    try:
        resolved = target_path.resolve()
    except OSError as error:
        raise ConfigError(f"unable to resolve handoff report path: {name!r}") from error
    try:
        resolved_dir = handoff_dir.resolve()
    except OSError as error:
        raise ConfigError("unable to resolve handoff directory") from error
    if resolved_dir not in resolved.parents:
        raise ConfigError(f"handoff report must remain within handoff/: {name!r}")

    if target_path.is_symlink():
        raise ConfigError(f"handoff report must not be a symlink: {name!r}")
    if not target_path.is_file():
        raise ConfigError(f"handoff report not found: {name!r}")

    target_path.unlink()
