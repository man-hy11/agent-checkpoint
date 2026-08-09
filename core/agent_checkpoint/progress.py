"""Parse, validate, and render the portable PROGRESS.md format."""

from datetime import datetime
import re

from .models import CheckpointEntry, ProgressDocument


REQUIRED_SECTIONS = (
    "## 1. Goal / Plan",
    "## 2. Progress",
    "## 3. Current Focus",
    "## 4. Next Actions / TODO",
    "## 5. Decisions / Constraints / Notes",
)

_ENTRY_SEPARATOR = re.compile(r"(?m)^---\s*$")
_ENTRY_HEADING = re.compile(
    r"^## Checkpoint(?P<pinned> \[PINNED\])? (?P<created_at>.+)$"
)
_DIFF_MARKERS = (
    re.compile(r"(?m)^diff --git "),
    re.compile(r"(?m)^--- \S"),
    re.compile(r"(?m)^\+\+\+ \S"),
    re.compile(r"(?m)^@@ -\d"),
)
_QUOTED_GIT_DIFF_PATHS = re.compile(
    r'^"a/(?:[^"\\]|\\.)+" "b/(?:[^"\\]|\\.)+"$'
)
_LINE_BOUNDARIES = frozenset("\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029")


def validate_entry(body: str) -> list[str]:
    """Return required section headings absent from a checkpoint body."""
    return [heading for heading in REQUIRED_SECTIONS if heading not in body]


def contains_diff_content(text: str) -> bool:
    """Return whether text contains a Git or unified-diff structural marker."""
    if any(marker.search(text) is not None for marker in _DIFF_MARKERS):
        return True
    return _contains_indented_diff_sequence(text.splitlines())


def _contains_indented_diff_sequence(lines: list[str]) -> bool:
    """Recognize a complete indented patch while ignoring isolated examples."""
    normalized = [line.lstrip(" \t") for line in lines]
    for index, line in enumerate(lines):
        if line == normalized[index]:
            continue
        window = normalized[index : index + 12]
        if _is_git_diff_header(window[0]):
            if _contains_git_diff_header(window[1:]):
                return True
        elif window[0].startswith("--- "):
            if _ordered_markers(window, "--- ", "+++ ", "@@ -"):
                return True
    return False


def _is_git_diff_header(line: str) -> bool:
    prefix = "diff --git "
    if not line.startswith(prefix):
        return False
    paths = line[len(prefix) :]
    return (
        _is_unquoted_git_diff_paths(paths)
        or _QUOTED_GIT_DIFF_PATHS.fullmatch(paths) is not None
    )


def _is_unquoted_git_diff_paths(paths: str) -> bool:
    if not paths.startswith("a/"):
        return False
    separator = " b/"
    split = paths.rfind(separator)
    if split == -1:
        return False
    old_path = paths[2:split]
    new_path = paths[split + len(separator) :]
    return (
        bool(old_path)
        and bool(new_path)
        and not old_path[0].isspace()
        and not old_path[-1].isspace()
        and not new_path[0].isspace()
        and not new_path[-1].isspace()
    )


def _contains_git_diff_header(lines: list[str]) -> bool:
    if _ordered_markers(lines, "--- ", "+++ ", "@@ -"):
        return True
    return any(_is_git_diff_metadata(line) for line in lines)


def _is_git_diff_metadata(line: str) -> bool:
    return line.startswith(
        (
            "old mode ",
            "new mode ",
            "deleted file mode ",
            "new file mode ",
            "similarity index ",
            "dissimilarity index ",
            "rename from ",
            "rename to ",
            "copy from ",
            "copy to ",
            "index ",
            "GIT binary patch",
            "literal ",
            "delta ",
            "Binary files ",
        )
    )


def _ordered_markers(lines: list[str], *prefixes: str) -> bool:
    offset = 0
    for prefix in prefixes:
        try:
            offset = next(
                index + 1
                for index, line in enumerate(lines[offset:], start=offset)
                if line.startswith(prefix)
            )
        except StopIteration:
            return False
    return True


def contains_line_boundary(text: str) -> bool:
    """Return whether text contains a boundary recognized by ``str.splitlines``."""
    return any(character in _LINE_BOUNDARIES for character in text)


def render_entry(body: str, created_at: datetime, pinned: bool = False) -> str:
    """Render one checkpoint entry, including its Markdown separator."""
    pin_marker = " [PINNED]" if pinned else ""
    heading = f"## Checkpoint{pin_marker} {created_at.isoformat()}"
    body_suffix = "" if body.endswith("\n") else "\n"
    return f"{heading}\n\n{body}{body_suffix}---\n"


def parse_progress(text: str) -> ProgressDocument:
    """Parse a PROGRESS.md document while preserving its top-level header."""
    header, remainder = _split_header(text)
    entries = [_parse_entry(chunk) for chunk in _ENTRY_SEPARATOR.split(remainder)]
    return ProgressDocument(
        entries=[entry for entry in entries if entry is not None], header=header
    )


def _split_header(text: str) -> tuple[str, str]:
    first_line, separator, remainder = text.partition("\n")
    if not first_line.startswith("# "):
        return "# Project Checkpoints", text
    return first_line, remainder.lstrip("\n") if separator else ""


def _parse_entry(chunk: str) -> CheckpointEntry | None:
    chunk = chunk.lstrip("\n")
    if not chunk.strip():
        return None
    heading, separator, body = chunk.partition("\n")
    match = _ENTRY_HEADING.fullmatch(heading)
    if match is None:
        raise ValueError(f"Invalid checkpoint heading: {heading}")
    if separator and body.startswith("\n"):
        body = body[1:]
    return CheckpointEntry(
        heading=heading,
        body=body,
        pinned=match.group("pinned") is not None,
        created_at=datetime.fromisoformat(match.group("created_at")),
    )
