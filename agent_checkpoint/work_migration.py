"""Classify and migrate legacy (`initialize_workflow`-created) work packages.

A legacy package is one materialized by the copy-based `workflows.initialize_workflow`
path: it carries `templates/CURRENT_TEMPLATE.md` and `prompts/CONTINUE_PROMPT.md`,
plus top-level `CURRENT.md`/`CONTINUE_PROMPT.md` copies of those two files. This
module distinguishes packages that are safe to migrate automatically from those
that must be refused, and performs the migration in place (same `work_id`, same
directory) so a project's `PROGRESS.md` pointer keeps resolving unchanged.

Filesystem mutation reuses `storage`'s atomic-write and locking primitives; no
atomic-write or locking logic is duplicated here.
"""

from dataclasses import dataclass
import filecmp
import os
from pathlib import Path
import re
import shutil
import stat
import uuid

from . import storage
from .storage import ValidationError
from .work_manifest import ManifestError, load_manifest
from .work_state import BLOCK_BEGIN, BLOCK_END, StateError, parse_state
from .work_renderer import _build_artifact_contents, _validate_targets

DEFAULT_LOCK_TIMEOUT_SECONDS = 10.0

# Categories, per the R5-I10 specification.
UNTOUCHED_SCAFFOLD = "untouched_scaffold"
USER_EDITED = "user_edited"
UNKNOWN_LAYOUT = "unknown_layout"
SYMLINK_HAZARD = "symlink_hazard"
PATH_CONFLICT = "path_conflict"

# The state block plus exactly the blank line creation pads each side with, so
# stripping it from an untouched tracker yields the template text byte for byte.
# The padding is matched precisely rather than greedily: swallowing every
# adjacent newline would also join the title to the section below it.
_BLOCK_WITH_PADDING = re.compile(
    re.escape(BLOCK_BEGIN) + r"\n.*?\n" + re.escape(BLOCK_END) + r"\n\n",
    re.S,
)
ALREADY_MIGRATED = "already_migrated"

_SAFE_TO_MIGRATE = frozenset({UNTOUCHED_SCAFFOLD})

_BACKUP_PREFIX = ".migration-backup-"


class MigrationError(ValidationError):
    """A migration operation could not complete safely."""


@dataclass(frozen=True)
class LegacyPackage:
    """One candidate directory under `.agent-checkpoint/work/` for migration."""

    work_id: str
    path: Path


@dataclass(frozen=True)
class Classification:
    """The classification of one legacy package, and why."""

    work_id: str
    category: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class MigrationAction:
    """One planned or applied action for a single package."""

    work_id: str
    classification: Classification
    will_migrate: bool
    backup_path: Path | None = None


@dataclass(frozen=True)
class MigrationReport:
    """The result of a dry-run or apply pass across all discovered packages."""

    applied: bool
    actions: tuple[MigrationAction, ...]

    @property
    def migrated_ids(self) -> tuple[str, ...]:
        return tuple(action.work_id for action in self.actions if action.will_migrate)


def discover_legacy_packages(project_root: Path) -> tuple[LegacyPackage, ...]:
    """Find directories under `.agent-checkpoint/work/` that look legacy-shaped.

    A directory qualifies as a discovery candidate when it contains the legacy
    signature (`templates/CURRENT_TEMPLATE.md` and `prompts/CONTINUE_PROMPT.md`)
    and has not already been migrated (a migrated package has no `templates/` or
    `prompts/` directory left). Already-migrated packages are excluded here so
    reruns are idempotent; `classify` handles every other disposition.
    """
    root = Path(project_root).resolve()
    work_root = root / ".agent-checkpoint" / "work"
    if not work_root.is_dir():
        return ()
    found = []
    for entry in sorted(work_root.iterdir()):
        if not entry.is_dir() or entry.is_symlink():
            continue
        if entry.name.startswith(".staging-") or entry.name.startswith(_BACKUP_PREFIX):
            continue
        legacy_current = entry / "templates" / "CURRENT_TEMPLATE.md"
        legacy_prompt = entry / "prompts" / "CONTINUE_PROMPT.md"
        if legacy_current.exists() or legacy_prompt.exists():
            found.append(LegacyPackage(work_id=entry.name, path=entry))
    return tuple(found)


def classify(package: LegacyPackage) -> Classification:
    """Classify one legacy candidate into a migration disposition.

    Never reads or echoes file contents beyond the byte-comparisons needed to
    tell scaffold from user-edited content; only file names and the resulting
    category are ever reported by the caller.
    """
    path = package.path
    work_id = package.work_id

    hazard = _find_symlink_hazard(path)
    if hazard is not None:
        return Classification(work_id, SYMLINK_HAZARD, (f"symlink found at {hazard}",))

    templates_dir = path / "templates"
    prompts_dir = path / "prompts"
    legacy_current = templates_dir / "CURRENT_TEMPLATE.md"
    legacy_prompt = prompts_dir / "CONTINUE_PROMPT.md"
    top_current = path / "CURRENT.md"
    top_prompt = path / "CONTINUE_PROMPT.md"

    if not (templates_dir.is_dir() and prompts_dir.is_dir()):
        return Classification(
            work_id, UNKNOWN_LAYOUT,
            ("expected legacy layout not found (templates/ or prompts/ missing)",),
        )
    if not (legacy_current.is_file() and legacy_prompt.is_file()):
        return Classification(
            work_id, UNKNOWN_LAYOUT,
            ("legacy entrypoint templates are missing or not regular files",),
        )
    if not (top_current.is_file() and top_prompt.is_file()):
        return Classification(
            work_id, UNKNOWN_LAYOUT,
            ("top-level CURRENT.md or CONTINUE_PROMPT.md is missing or not a regular file",),
        )

    try:
        work_type = _infer_work_type(path)
    except MigrationError as error:
        return Classification(work_id, UNKNOWN_LAYOUT, (str(error),))

    conflict = _find_path_conflict(path, work_type)
    if conflict is not None:
        return Classification(
            work_id, PATH_CONFLICT,
            (f"final artifact target already occupied by unexpected content: {conflict}",),
        )

    current_matches = _current_matches_template(top_current, legacy_current)
    prompt_matches = filecmp.cmp(top_prompt, legacy_prompt, shallow=False)
    if current_matches and prompt_matches:
        return Classification(work_id, UNTOUCHED_SCAFFOLD, ())

    reasons = []
    if not current_matches:
        reasons.append("CURRENT.md diverges from templates/CURRENT_TEMPLATE.md")
    if not prompt_matches:
        reasons.append("CONTINUE_PROMPT.md diverges from prompts/CONTINUE_PROMPT.md")
    return Classification(work_id, USER_EDITED, tuple(reasons))


def plan_migration(project_root: Path) -> MigrationReport:
    """Dry-run: classify every discovered package and report the planned action."""
    root = Path(project_root).resolve()
    actions = []
    for package in discover_legacy_packages(root):
        classification = classify(package)
        actions.append(
            MigrationAction(
                work_id=package.work_id,
                classification=classification,
                will_migrate=classification.category in _SAFE_TO_MIGRATE,
            )
        )
    return MigrationReport(applied=False, actions=tuple(actions))


def apply_migration(
    project_root: Path,
    *,
    lock_timeout_seconds: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
) -> MigrationReport:
    """Apply migration: only `untouched_scaffold` packages are migrated.

    Each package is migrated independently under its own lock. A failure while
    migrating one package does not roll back an already-committed migration of
    another package, and leaves the failing package's on-disk state exactly as
    it was before the attempt (backup-then-atomic-replace, never a partial
    write of the final layout).
    """
    root = Path(project_root).resolve()
    actions = []
    for package in discover_legacy_packages(root):
        classification = classify(package)
        if classification.category not in _SAFE_TO_MIGRATE:
            actions.append(
                MigrationAction(
                    work_id=package.work_id, classification=classification, will_migrate=False
                )
            )
            continue
        backup_path = _migrate_one_package(
            root, package, lock_timeout_seconds=lock_timeout_seconds
        )
        actions.append(
            MigrationAction(
                work_id=package.work_id,
                classification=classification,
                will_migrate=True,
                backup_path=backup_path,
            )
        )
    return MigrationReport(applied=True, actions=tuple(actions))


def rollback_migration(package_path: Path, backup_path: Path) -> None:
    """Restore a package from its migration backup, atomically, in place.

    `backup_path` must be a `.migration-backup-*` directory sibling of
    `package_path`, produced by `apply_migration`. After rollback, the package
    is byte-for-byte identical to its pre-migration state.
    """
    package_path = Path(package_path)
    backup_path = Path(backup_path)
    if not backup_path.is_dir() or backup_path.is_symlink():
        raise MigrationError("migration backup is missing or not a directory")
    if backup_path.parent != package_path.parent:
        raise MigrationError("migration backup must be a sibling of the package")
    if not backup_path.name.startswith(_BACKUP_PREFIX):
        raise MigrationError("path does not look like a migration backup")

    staged = package_path.parent / f".staging-{uuid.uuid4().hex}"
    try:
        shutil.copytree(backup_path, staged)
        _replace_directory(package_path, staged)
    except BaseException:
        if staged.exists() and not staged.is_symlink():
            shutil.rmtree(staged)
        raise


def _migrate_one_package(
    root: Path,
    package: LegacyPackage,
    *,
    lock_timeout_seconds: float,
) -> Path:
    """Back up, then atomically replace, one package's legacy layout in place."""
    lock_path = package.path / ".agent-checkpoint.lock"
    with storage._open_safe_parent(root, lock_path, create=True) as lock_parent:
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
                return _migrate_locked(package)
            finally:
                storage._release_lock(lock_file)


def _migrate_locked(package: LegacyPackage) -> Path:
    path = package.path
    # Re-classify under the lock: refuse if another writer changed the package
    # between the outer discovery pass and acquiring this lock.
    classification = classify(package)
    if classification.category not in _SAFE_TO_MIGRATE:
        raise MigrationError(
            f"package {package.work_id} is no longer untouched_scaffold; refusing to migrate"
        )

    work_type = _infer_work_type(path)
    manifest = load_manifest(work_type)
    contents = _build_artifact_contents(manifest, package.work_id)
    _validate_targets(contents)

    backup_path = path.parent / f"{_BACKUP_PREFIX}{uuid.uuid4().hex}"
    staged = path.parent / f".staging-{uuid.uuid4().hex}"
    try:
        shutil.copytree(path, backup_path)
        shutil.copytree(path, staged)
        _apply_final_layout(staged, contents)
        _replace_directory(path, staged)
    except BaseException:
        if staged.exists() and not staged.is_symlink():
            shutil.rmtree(staged)
        if backup_path.exists() and not backup_path.is_symlink():
            shutil.rmtree(backup_path)
        raise
    return backup_path


def _apply_final_layout(staged: Path, contents: dict) -> None:
    """Remove the legacy directories and write the manifest-driven final artifacts."""
    for legacy_dir in ("templates", "prompts", "shared"):
        candidate = staged / legacy_dir
        if candidate.is_dir() and not candidate.is_symlink():
            shutil.rmtree(candidate)
        elif candidate.exists() or candidate.is_symlink():
            raise MigrationError(f"unexpected non-directory at {legacy_dir}")
    for relative_name, text in contents.items():
        target = staged / relative_name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def _replace_directory(destination: Path, staged: Path) -> None:
    """Atomically swap `staged` into `destination`'s place, keeping the same id/path."""
    displaced = destination.parent / f".staging-displaced-{uuid.uuid4().hex}"
    os.replace(destination, displaced)
    try:
        os.replace(staged, destination)
    except BaseException:
        os.replace(displaced, destination)
        raise
    shutil.rmtree(displaced, ignore_errors=True)


def _infer_work_type(path: Path) -> str:
    """Infer the workflow family from the legacy package's templates directory.

    The legacy package does not itself record a machine-readable work_type, so
    this inspects which bundled family's assets the package's templates/
    contents originated from by matching template filenames unique to a
    family's CURRENT_TEMPLATE.md against the bundled asset root's siblings.
    """
    from .workflows import _ASSET_ROOT, _WORK_TYPES

    legacy_current = path / "templates" / "CURRENT_TEMPLATE.md"
    for work_type in sorted(_WORK_TYPES):
        bundled = _ASSET_ROOT / work_type / "templates" / "CURRENT_TEMPLATE.md"
        if bundled.is_file() and filecmp.cmp(legacy_current, bundled, shallow=False):
            try:
                load_manifest(work_type)
            except ManifestError as error:
                raise MigrationError(f"no usable manifest for inferred type: {error}") from error
            return work_type
    raise MigrationError("cannot infer workflow type: no bundled family matches this package")


def _find_symlink_hazard(path: Path) -> Path | None:
    """Return the first symlink found anywhere inside the package, or None."""
    for current, directories, files in os.walk(path, followlinks=False):
        current_path = Path(current)
        for name in list(directories) + list(files):
            candidate = current_path / name
            if candidate.is_symlink():
                return candidate
    return None


def _current_matches_template(top_current: Path, legacy_current: Path) -> bool:
    """Return whether CURRENT.md is still the untouched scaffold.

    Package creation inserts a state block into the tracker, so a byte compare
    against ``templates/CURRENT_TEMPLATE.md`` no longer holds for an untouched
    package. Strip the block before comparing: prose identical to the template
    means nobody has recorded work yet, which is what "untouched" is asking.

    A tracker whose state block records real progress — a confirmed brief, or
    any planned unit — is never untouched, whatever its prose looks like.
    """
    text = top_current.read_text(encoding="utf-8")
    template = legacy_current.read_text(encoding="utf-8")
    if BLOCK_BEGIN not in text:
        return text == template

    try:
        state = parse_state(text)
    except StateError:
        return False
    if state.brief_confirmed or state.units:
        return False

    stripped = _BLOCK_WITH_PADDING.sub("", text, count=1)
    return stripped == template


def _find_path_conflict(path: Path, work_type: str) -> str | None:
    """Return the name of a top-level entry that is neither part of the expected
    legacy scaffold nor a top-level file the legacy entrypoint materializes
    (`CURRENT.md`, `CONTINUE_PROMPT.md`), and that would collide with a final
    artifact target the migrated package is about to write, or None.

    Legacy packages carry `CURRENT.md` and `CONTINUE_PROMPT.md` from
    `workflows._materialize_entrypoints`, plus `PROGRESS.md`, which `cli.py`
    writes in the same `workflow` invocation. All three are the tool's own
    output and are not conflicts. Every other final artifact name (`BRIEF.md`,
    `PLAN.md`, `DESIGN.md`, ...) must not already exist as a top-level entry in
    a legacy package, since migration is about to write it — if one exists
    already, refuse rather than silently replace it.
    """
    try:
        manifest = load_manifest(work_type)
    except ManifestError:
        return None
    expected_legacy = {
        "templates", "prompts", "shared", "README.md", "workflow.json",
        "CURRENT.md", "CONTINUE_PROMPT.md",
        # Written by cli.py in the same `workflow` invocation that creates the
        # package, so it is the tool's own output rather than foreign content.
        "PROGRESS.md",
    }
    final_targets = set(manifest.artifacts) - {"CURRENT.md", "CONTINUE_PROMPT.md"}
    for entry in path.iterdir():
        if entry.name.startswith(".staging-") or entry.name.startswith(_BACKUP_PREFIX):
            continue
        if entry.name == ".agent-checkpoint.lock":
            continue
        if entry.name in final_targets:
            return entry.name
        if entry.name not in expected_legacy:
            return entry.name
    return None
