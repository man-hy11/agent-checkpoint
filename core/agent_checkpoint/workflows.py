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
- Read PROGRESS.md, then {relative}/CURRENT.md, then {relative}/prompts/CONTINUE_PROMPT.md.
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
        _materialize_entrypoints(staged)
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


def discard_workflow(result: WorkflowResult) -> None:
    """Remove a just-created work package after its pointer cannot be persisted."""
    if result.path.is_symlink() or not result.path.is_dir():
        raise OSError("unable to discard unsafe work package")
    shutil.rmtree(result.path)


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


def _materialize_entrypoints(work_package: Path) -> None:
    """Expose the tracker and continuation prompt at stable top-level paths."""
    current_template = work_package / "templates" / "CURRENT_TEMPLATE.md"
    continue_prompt = work_package / "prompts" / "CONTINUE_PROMPT.md"
    if not current_template.is_file() or not continue_prompt.is_file():
        raise OSError("bundled workflow is missing required entrypoint templates")
    shutil.copy2(current_template, work_package / "CURRENT.md")
    shutil.copy2(continue_prompt, work_package / "CONTINUE_PROMPT.md")
