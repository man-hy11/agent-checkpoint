"""Materialize bundled AI development templates for checkpoint handoffs."""

from dataclasses import dataclass
import os
from pathlib import Path
import re
import shutil
import stat
import uuid

from .config import ConfigError
from .work_renderer import RenderedPackage, render_final_package
from .work_state import BLOCK_BEGIN, initial_state, render_initial_block, render_state


_ASSET_ROOT = Path(__file__).with_name("assets") / "development-templates"
_WORK_TYPES = frozenset(
    {
        "project",
        "feature",
        "bugfix",
        "refactor",
        "upgrade",
        "migration",
        "performance",
        "integration",
        "release",
        "spike",
    }
)
_WORK_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")


@dataclass(frozen=True)
class WorkflowResult:
    """A materialized template package and its compact checkpoint pointer."""

    work_type: str
    work_id: str
    path: Path

    @property
    def progress_entry(self) -> str:
        relative = f".agent-checkpoint/work/{self.work_id}"
        return f"""## 1. Goal / Plan
- Workflow type: {self.work_type}
- Work package: {relative}

## 2. Progress
- Read {relative}/CURRENT.md for the verified current Step or Gate.

## 3. Current Focus
- Follow the selected workflow rather than relying on compacted conversation history.

## 4. Next Actions / TODO
- Read the root CONTINUE_PROMPT.md, then {relative}/CURRENT.md, then {relative}/CONTINUE_PROMPT.md.
- Execute only the Current Target and update its tracker after verified PASS.

## 5. Decisions / Constraints / Notes
- Detailed plan, evidence, and gates are stored in the work package.
"""


def workflow_types() -> tuple[str, ...]:
    """Return the stable supported template types."""
    return tuple(sorted(_WORK_TYPES))


def initialize_workflow(project_root: Path, work_type: str, work_id: str) -> WorkflowResult:
    """Copy one bundled workflow plus shared rules into a project safely."""
    if work_type not in _WORK_TYPES:
        raise ConfigError("Unknown workflow type")
    if not _WORK_ID.fullmatch(work_id):
        raise ConfigError("work id must use lowercase letters, digits, and hyphens")

    root = Path(project_root).resolve()
    work_root = root / ".agent-checkpoint" / "work"
    _reject_symlinked_path(root, work_root.relative_to(root))
    destination = work_root / work_id
    if destination.exists() or destination.is_symlink():
        raise ConfigError("work package already exists")

    source = _ASSET_ROOT / work_type
    shared = _ASSET_ROOT / "shared"
    if not source.is_dir() or not shared.is_dir():
        raise OSError("bundled development templates are unavailable")

    work_root.mkdir(parents=True, exist_ok=True)
    staged = work_root / f".staging-{uuid.uuid4().hex}"
    try:
        shutil.copytree(source, staged)
        shutil.copytree(shared, staged / "shared")
        _materialize_entrypoints(staged, work_id, work_type)
        os.replace(staged, destination)
    except BaseException:
        if staged.exists() and not staged.is_symlink():
            shutil.rmtree(staged)
        raise
    return WorkflowResult(work_type, work_id, destination)


def render_final_workflow(project_root: Path, work_type: str, work_id: str) -> RenderedPackage:
    """Materialize a revision-5 final-only package (manifest and RULES.md driven).

    This is the new, migration-path entrypoint for the ten manifest-driven
    families; `initialize_workflow` above remains the legacy copy-based path
    for consumers not yet migrated to it (R5-I10 handles that migration).
    """
    return render_final_package(project_root, work_type, work_id)


def discard_workflow(result: WorkflowResult, project_root: Path | None = None) -> None:
    """Remove a just-created work package after some later step in its creation fails.

    ``project_root`` is optional for backward compatibility with call sites
    that only ever discarded the package directory itself. When given, also
    clears the active pointer and root ``CONTINUE_PROMPT.md`` if they still
    name ``result.work_id`` — since the package they point to is being
    removed, leaving either in place would strand a pointer/root-file pair
    naming a work id that no longer exists (R4 Task 1's atomic-unit rollback
    requirement).
    """
    if result.path.is_symlink() or not result.path.is_dir():
        raise OSError("unable to discard unsafe work package")
    if project_root is not None:
        _discard_active_pointer_if_matching(project_root, result.work_id)
    shutil.rmtree(result.path)


def archive_completed_package(
    project_root: Path, work_id: str, package_path: Path, *, date_str: str
) -> Path:
    """Atomically relocate a completed package to ``work/archive/<id>-<date>/``.

    Called after a `pass` event leaves the package's ``WorkState`` complete
    (``WorkState.is_complete()``, chain-v1.md Row 4). ``date_str`` is supplied
    by the caller rather than read from a clock here, so tests control it
    (mirrors ``render_entry``'s existing pattern of taking a timestamp as a
    parameter). Refuses before touching the source directory if the
    destination already exists, so no partial-move state is ever reachable.
    After a successful move, clears the active pointer and root
    ``CONTINUE_PROMPT.md`` if either still names ``work_id`` — the same
    clear-both-together logic ``discard_workflow`` already uses at
    creation-time rollback, reused here at completion time instead.
    """
    if package_path.is_symlink() or not package_path.is_dir():
        raise ConfigError("unable to archive an unsafe work package")

    root = Path(project_root).resolve()
    archive_root = root / ".agent-checkpoint" / "work" / "archive"
    destination = archive_root / f"{work_id}-{date_str}"
    if destination.exists() or destination.is_symlink():
        raise ConfigError(f"archive destination already exists: {destination}")

    archive_root.mkdir(parents=True, exist_ok=True)
    if destination.exists() or destination.is_symlink():
        # Re-check after mkdir: a concurrent writer could have raced us here.
        raise ConfigError(f"archive destination already exists: {destination}")

    os.rename(package_path, destination)

    _discard_active_pointer_if_matching(root, work_id)
    return destination


def _discard_active_pointer_if_matching(project_root: Path, work_id: str) -> None:
    from .config import _read_raw_active_pointer  # local import avoids an import cycle

    root = Path(project_root).resolve()
    try:
        raw_id = _read_raw_active_pointer(root)
    except ConfigError:
        return
    if raw_id != work_id:
        return
    pointer_path = root / ".agent-checkpoint" / "active"
    prompt_path = root / "CONTINUE_PROMPT.md"
    for path in (pointer_path, prompt_path):
        try:
            if not path.is_symlink():
                path.unlink()
        except FileNotFoundError:
            pass


_ROOT_STOP_BLOCK = (
    "Rules:\n\n"
    "- one invocation = one Step or one Gate;\n"
    "- preserve the work-type evidence chain and hard rules;\n"
    "- no unrelated changes;\n"
    "- update CURRENT.md only after verified PASS;\n"
    "- FAIL does not advance;\n"
    "- write completion report and STOP.\n\n"
    "Advancing Current Target does not authorize beginning it in this invocation.\n"
)


def render_root_continue_prompt(active_id: str) -> str:
    """Render the repo-root CONTINUE_PROMPT.md naming the active work package.

    Points a session that starts from the root alone at the active package's
    own CONTINUE_PROMPT.md (R2 D2/D3), and carries the same explicit STOP /
    one-invocation-per-unit language as the per-package prompt so either entry
    point gives equivalent guidance.
    """
    relative = f".agent-checkpoint/work/{active_id}"
    return (
        f"# Continue: {active_id}\n\n"
        f"Active work package: `{relative}`.\n\n"
        f"1. Read `{relative}/CURRENT.md` for the authoritative work-state block.\n"
        f"2. Read `{relative}/RULES.md` for this package's hard rules, evidence "
        "requirements, and unit ID scheme.\n"
        f"3. Read `{relative}/PLAN.md` for the approved unit graph.\n"
        f"4. Then read `{relative}/CONTINUE_PROMPT.md` and act only on the "
        "current unit it names.\n\n"
        f"{_ROOT_STOP_BLOCK}"
    )


def write_root_continue_prompt(project_root: Path, active_id: str) -> None:
    """Atomically (re)write the repo-root CONTINUE_PROMPT.md for ``active_id``.

    The root file is always fully regenerated, never hand-edited or partially
    patched — it is a derived pointer, kept in sync with the active-pointer
    write (R2 D2) so the two can never observably drift apart. Reuses
    ``storage``'s atomic-write primitive and ``config``'s symlink rejection,
    mirroring ``config.write_active_work_id``'s reuse pattern exactly.
    """
    from .config import _reject_symlink  # local import avoids an import cycle
    from .storage import _atomic_write  # local import avoids an import cycle

    root = Path(project_root).resolve()
    prompt_path = root / "CONTINUE_PROMPT.md"
    _reject_symlink(prompt_path, "root CONTINUE_PROMPT.md")
    _atomic_write(root, prompt_path, render_root_continue_prompt(active_id))


def _reject_symlinked_path(root: Path, relative: Path) -> None:
    current = root
    for component in relative.parts:
        current /= component
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            return
        if stat.S_ISLNK(mode):
            raise ConfigError("work package path contains a symlinked component")
        if not stat.S_ISDIR(mode):
            raise ConfigError("work package path parent is not a directory")


def _materialize_entrypoints(work_package: Path, work_id: str, work_type: str) -> None:
    """Expose the tracker and continuation prompt at stable top-level paths.

    The tracker is not a plain copy: the bundled templates carry prose only, so
    the state block every `work` subcommand parses is inserted here. Without it
    a freshly created package is unreadable and `work status` reports no active
    package at all.
    """
    current_template = work_package / "templates" / "CURRENT_TEMPLATE.md"
    continue_prompt = work_package / "prompts" / "CONTINUE_PROMPT.md"
    if not current_template.is_file() or not continue_prompt.is_file():
        raise OSError("bundled workflow is missing required entrypoint templates")
    template_text = current_template.read_text(encoding="utf-8")
    (work_package / "CURRENT.md").write_text(
        _with_state_block(template_text, work_id, work_type), encoding="utf-8"
    )
    shutil.copy2(continue_prompt, work_package / "CONTINUE_PROMPT.md")


def _with_state_block(text: str, work_id: str, work_type: str) -> str:
    """Return the tracker text with a new package's state block in place.

    Inserted after the title so the block sits above the prose a reader scans.
    A template that already carries a block keeps its position, so this stays
    correct if the bundled templates ever gain one.
    """
    block = render_initial_block(work_id, work_type)
    if BLOCK_BEGIN in text:
        return render_state(text, initial_state(work_id, work_type))
    lines = text.split("\n")
    # Insert after the title and the blank line that follows it, keeping the
    # rest of the template byte-identical so migration can still recognize an
    # untouched scaffold by stripping exactly this block back out.
    head = 2 if len(lines) > 1 and lines[0].startswith("# ") and not lines[1] else 0
    return "\n".join(lines[:head] + [block, ""] + lines[head:])
