"""Safe, bounded checkpoint status, resume, handoff, and doctor output."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
from typing import Iterable

from .config import ProjectConfig, resolve_checkpoint_paths
from .git_state import GitState, collect_git_state
from .models import ProgressDocument
from .progress import contains_diff_content, contains_line_boundary, parse_progress
from .secrets import find_secret_kind


_STALE_AFTER = timedelta(days=7)
_CAPABILITIES = {
    "claude-code": "automatic",
    "codex": "manual",
    "gemini-cli": "advisory",
    "opencode": "manual",
}


def build_status(project_root: Path, config: ProjectConfig) -> dict:
    """Return content-free project status suitable for a JSON command response."""
    root, progress_path, _ = resolve_checkpoint_paths(project_root, config)
    state = collect_git_state(root, config)
    document, error = _read_document(progress_path)
    return {
        "root": _safe_metadata(str(root)),
        "checkpoint_exists": progress_path.is_file(),
        "checkpoint_entries": len(document.entries) if document is not None else 0,
        "checkpoint_error": error,
        "git_available": state.git_available,
        "git": _safe_git_state(state),
    }


def build_resume(
    project_root: Path, config: ProjectConfig, max_chars: int | None = None
) -> str:
    """Render the newest safe checkpoint entry within the requested context budget."""
    root, progress_path, _ = resolve_checkpoint_paths(project_root, config)
    document, error = _read_document(progress_path)
    language = _safe_metadata(config.language) or "unspecified"
    if error is not None:
        content = f"Checkpoint resume unavailable: {error}"
    elif document is None or not document.entries:
        content = "No checkpoint has been recorded."
    else:
        content = document.entries[0].body.rstrip()
    rendered = f"# Checkpoint Resume\nLanguage: {language}\n\n{content}\n"
    return _truncate(rendered, _budget(max_chars, config))


def build_handoff(
    project_root: Path,
    config: ProjectConfig,
    verification: Iterable[str] = (),
    max_chars: int | None = None,
) -> str:
    """Render only explicit checkpoint and Git metadata for the next agent."""
    root, progress_path, _ = resolve_checkpoint_paths(project_root, config)
    state = collect_git_state(root, config) if config.include_git_hints else GitState()
    document, error = _read_document(progress_path)
    entry_body = document.entries[0].body if document and document.entries else ""
    results = (
        *_stored_verification(entry_body),
        *_safe_verification(verification),
    )
    changed_files = "\n".join(
        f"- {_safe_filename(name)}" for name in state.changed_files
    ) or "- None"
    lines = [
        "# Checkpoint Handoff",
        f"Language: {_safe_metadata(config.language) or 'unspecified'}",
        f"Root: {_safe_metadata(str(root))}",
    ]
    if config.include_git_hints:
        lines.extend(
            (
                f"Branch: {_safe_metadata(state.branch) or 'unavailable'}",
                f"Worktree: {_safe_metadata(state.worktree) or 'unavailable'}",
                "Changed files:",
                changed_files,
            )
        )
    lines.extend(
        (
            "Verification results:",
            "\n".join(f"- {result}" for result in results) or "- None supplied",
            "Current Focus:",
            _section(entry_body, "## 3. Current Focus") or _availability(error),
            "Next Actions:",
            _section(entry_body, "## 4. Next Actions / TODO") or _availability(error),
            "Recent Decisions:",
            _section(entry_body, "## 5. Decisions / Constraints / Notes")
            or _availability(error),
            "",
        )
    )
    rendered = "\n".join(lines)
    return _truncate(rendered, _budget(max_chars, config))


def build_doctor(project_root: Path, config: ProjectConfig, adapter: str) -> dict:
    """Report non-blocking setup risks without mutating Git or project files."""
    root, progress_path, _ = resolve_checkpoint_paths(project_root, config)
    state = collect_git_state(root, config)
    document, error = _read_document(progress_path)
    warnings = []
    if not state.git_available:
        warnings.append("Git is unavailable or this path is not a Git repository")
    else:
        if state.progress_tracked:
            warnings.append(
                "progress file is already tracked: remove it from Git manually before relying on ignore rules"
            )
        if not state.progress_ignored:
            warnings.append("progress file is not ignored by Git")
        if state.archive_tracked:
            warnings.append(
                "archive file is already tracked: remove it from Git manually before relying on ignore rules"
            )
        if not state.archive_ignored:
            warnings.append("archive file is not ignored by Git")
        if state.worktree != str(root):
            warnings.append("worktree mismatch: project root is inside a different Git worktree")
    if error is not None:
        warnings.append(f"checkpoint is unreadable: {error}")
    elif document is None or not document.entries:
        warnings.append("checkpoint is stale: no checkpoint entry exists")
    elif _is_stale(document):
        warnings.append("checkpoint is stale: newest entry is older than seven days")

    return {
        "root": _safe_metadata(str(root)),
        "adapter": adapter,
        "capability": _CAPABILITIES.get(adapter, "manual"),
        "git_available": state.git_available,
        "warnings": "\n".join(warnings),
        "status": build_status(root, config),
    }


def _read_document(path: Path) -> tuple[ProgressDocument | None, str | None]:
    if not path.is_file():
        return None, None
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None, "checkpoint document cannot be read"
    if contains_diff_content(text):
        return None, "checkpoint content omitted because it contains diff-shaped content"
    secret_kind = find_secret_kind(text)
    if secret_kind is not None:
        return None, f"checkpoint content omitted because it contains a probable {secret_kind}"
    try:
        return parse_progress(text), None
    except ValueError:
        return None, "checkpoint document is invalid"


def _section(body: str, heading: str) -> str:
    if not body:
        return ""
    match = re.search(
        rf"(?ms)^{re.escape(heading)}\s*$\n?(.*?)(?=^##\s|^### Verification\s*$|\Z)",
        body,
    )
    return match.group(1).strip() if match else ""


def _stored_verification(body: str) -> tuple[str, ...]:
    section = _section(body, "## 6. Verification") or _section(
        body, "### Verification"
    )
    values = tuple(
        line[2:].strip() if line.startswith("- ") else line
        for line in (raw_line.strip() for raw_line in section.splitlines())
        if line
    )
    return _safe_verification(values)


def _safe_verification(verification: Iterable[str]) -> tuple[str, ...]:
    if isinstance(verification, str):
        raise ValueError("Verification results must be a sequence of text values")
    try:
        values = tuple(verification)
    except TypeError as error:
        raise ValueError("Verification results must be a sequence of text values") from error
    if any(not isinstance(value, str) for value in values):
        raise ValueError("Verification results must be text values")
    for value in values:
        if contains_line_boundary(value):
            raise ValueError("Verification results must each be a single line")
        if contains_diff_content(value):
            raise ValueError("Verification result contains diff-shaped content")
        if find_secret_kind(value) is not None:
            raise ValueError("Verification result contains a probable credential")
    return values


def _safe_filename(filename: str) -> str:
    return _safe_metadata(filename) or "[omitted filename with probable credential]"


def _safe_git_state(state: GitState) -> dict:
    """Serialize Git metadata after applying the same credential guard as text output."""
    return {
        "branch": _safe_metadata(state.branch),
        "worktree": _safe_metadata(state.worktree),
        "changed_files": [_safe_filename(name) for name in state.changed_files],
        "progress_tracked": state.progress_tracked,
        "progress_ignored": state.progress_ignored,
        "archive_tracked": state.archive_tracked,
        "archive_ignored": state.archive_ignored,
        "git_available": state.git_available,
    }


def _safe_metadata(value: str | None) -> str | None:
    if value is None:
        return None
    if find_secret_kind(value) is not None:
        return "[omitted metadata with probable credential]"
    return value


def _availability(error: str | None) -> str:
    return f"Not available ({error})." if error else "Not recorded."


def _is_stale(document: ProgressDocument) -> bool:
    created_at = document.entries[0].created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - created_at > _STALE_AFTER


def _budget(requested: int | None, config: ProjectConfig) -> int:
    budget = config.resume_max_chars if requested is None else requested
    if isinstance(budget, bool) or not isinstance(budget, int) or budget <= 0:
        raise ValueError("max_chars must be a positive integer")
    return budget


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    if max_chars <= 3:
        return "." * max_chars
    return text[: max_chars - 3] + "..."
