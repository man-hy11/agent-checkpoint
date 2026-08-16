"""Render final work-package artifacts, including RULES.md, from a manifest."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import stat
import uuid

from .storage import ValidationError
from .work_chain import next_skill
from .work_manifest import WorkflowManifest, load_manifest
from .work_state import BLOCK_BEGIN, BLOCK_END, WorkState

_WORK_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
_RESERVED_COMPONENTS = frozenset({"templates", "prompts", "shared"})

# Mirrors contracts/chain-v1.md rows 1-12 exactly. A test proves every row's
# next_skill matches work_chain.next_skill for a constructed state satisfying
# its condition, so RULES.md's rendered table can never silently drift from
# the engine (design decision D4's "generated fallback ... a test proves
# equivalent").
CHAIN_TABLE: tuple[tuple[str, str], ...] = (
    ("no state block exists", "checkpoint-select-workflow"),
    ("brief_confirmed is false", "checkpoint-brainstorm"),
    ("units is empty", "checkpoint-plan"),
    ("every unit is passed", "checkpoint-handoff"),
    ("current_unit names no member of units", "checkpoint-plan"),
    ("current unit state is superseded", "checkpoint-plan"),
    ("current unit state is blocked", "checkpoint-recover"),
    (
        "current unit state is failed and the current attempt has no "
        "root_cause_fingerprint",
        "checkpoint-diagnose",
    ),
    ("current unit state is failed", "checkpoint-recover"),
    ("current unit state is pending or ready", "checkpoint-claim"),
    ("current unit state is running and kind is gate", "checkpoint-verify-gate"),
    ("current unit state is running and kind is step", "checkpoint-execute"),
)


class RenderError(ValidationError):
    """A final work package could not be rendered safely."""


@dataclass(frozen=True)
class RenderedPackage:
    work_type: str
    work_id: str
    path: Path
    artifacts: tuple[str, ...]


def render_final_package(project_root: Path, work_type: str, work_id: str) -> RenderedPackage:
    """Materialize a final-only work package for one family, atomically."""
    if not _WORK_ID.fullmatch(work_id):
        raise RenderError("work id must use lowercase letters, digits, and hyphens")

    manifest = load_manifest(work_type)

    root = Path(project_root).resolve()
    work_root = root / ".agent-checkpoint" / "work"
    _reject_symlinked_path(root, work_root.relative_to(root))
    destination = work_root / work_id
    if destination.exists() or destination.is_symlink():
        raise RenderError("work package already exists")

    contents = _build_artifact_contents(manifest, work_id)
    _validate_targets(contents)

    work_root.mkdir(parents=True, exist_ok=True)
    staged = work_root / f".staging-{uuid.uuid4().hex}"
    try:
        staged.mkdir()
        for relative_name, text in contents.items():
            target = staged / relative_name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        os.replace(staged, destination)
    except BaseException:
        if staged.exists() and not staged.is_symlink():
            shutil.rmtree(staged)
        raise
    return RenderedPackage(
        work_type=work_type,
        work_id=work_id,
        path=destination,
        artifacts=tuple(sorted(contents)),
    )


def render_rules(manifest: WorkflowManifest) -> str:
    """Render RULES.md: hard rules, evidence requirements, unit IDs, chain table."""
    lines = ["# RULES.md", "", f"Workflow type: `{manifest.type}`", ""]

    lines.append("## Hard rules")
    lines.append("")
    for rule in manifest.hard_rules:
        lines.append(f"- {rule}")
    lines.append("")

    lines.append("## Evidence required")
    lines.append("")
    lines.append("### step")
    lines.append("")
    for key in manifest.evidence_required["step"]:
        lines.append(f"- `{key}`")
    lines.append("")
    lines.append("### gate")
    lines.append("")
    lines.append("The gate entry below is the gate criteria; there is no separate list.")
    lines.append("")
    for key in manifest.evidence_required["gate"]:
        lines.append(f"- `{key}`")
    lines.append("")

    lines.append("## Unit ID scheme")
    lines.append("")
    if manifest.grouped:
        lines.append(
            f"Units carry a group prefix: `{manifest.unit_prefix}<n>-S<m>` for a step, "
            f"`{manifest.unit_prefix}<n>-G` for that group's gate. Group state is "
            "derived from its member units and never stored."
        )
    else:
        lines.append(
            f"Units use the prefix `{manifest.unit_prefix}`, e.g. "
            f"`{manifest.unit_prefix}1`, `{manifest.unit_prefix}2`, one gate unit per plan."
        )
    lines.append("")

    lines.append("## Chain table")
    lines.append("")
    lines.append("| Condition | next_skill |")
    lines.append("|---|---|")
    for condition, skill in CHAIN_TABLE:
        lines.append(f"| {condition} | `{skill}` |")
    lines.append("")

    return "\n".join(lines) + "\n"


def _build_artifact_contents(manifest: WorkflowManifest, work_id: str) -> dict:
    contents: dict[str, str] = {}
    for name, policy in manifest.artifacts.items():
        if policy == "omitted":
            continue
        if name == "RULES.md":
            contents[name] = render_rules(manifest)
        elif name == "CURRENT.md":
            contents[name] = _render_initial_current(manifest, work_id)
        elif name == "EVIDENCE.md":
            contents[name] = "# Evidence\n"
        elif name == "CONTINUE_PROMPT.md":
            contents[name] = _render_continue_prompt(manifest, work_id)
        else:
            contents[name] = _render_generic_artifact(name, manifest, work_id)
    return contents


def _render_initial_current(manifest: WorkflowManifest, work_id: str) -> str:
    payload = {
        "schema_version": 1,
        "work_id": work_id,
        "work_type": manifest.type,
        "plan_revision": 1,
        "brief_confirmed": False,
        "current_unit": None,
        "max_attempts": manifest.max_attempts,
        "attempt_override": None,
        "units": [],
        "attempts": [],
    }
    body = json.dumps(payload, indent=2, sort_keys=True)
    block = f"{BLOCK_BEGIN}\n{body}\n{BLOCK_END}"
    return (
        f"# CURRENT.md\n\n{block}\n\n"
        f"Read `RULES.md` and `PLAN.md` before acting. This tracker's next skill "
        f"is `{next_skill(None)}` while no state block exists; once brief and plan "
        "are recorded, `next_skill` is derived from the state block above.\n"
    )


def _render_continue_prompt(manifest: WorkflowManifest, work_id: str) -> str:
    return (
        f"# Continue: {work_id}\n\n"
        f"1. Read `CURRENT.md` for the authoritative work-state block.\n"
        f"2. Read `RULES.md` for this `{manifest.type}` package's hard rules, "
        "evidence requirements, and unit ID scheme.\n"
        "3. Read `PLAN.md` for the approved unit graph.\n"
        "4. Act only on the current unit named by `CURRENT.md`.\n"
    )


def _render_generic_artifact(name: str, manifest: WorkflowManifest, work_id: str) -> str:
    title = Path(name).stem.replace("_", " ").title()
    return f"# {title}\n\nWork package: `{work_id}` ({manifest.type})\n\n<!-- TODO -->\n"


def _validate_targets(contents: dict) -> None:
    seen: dict[str, str] = {}
    for name in contents:
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            raise RenderError(f"artifact target escapes the package: {name}")
        reserved = _RESERVED_COMPONENTS.intersection(part.lower() for part in path.parts)
        if reserved:
            raise RenderError(f"artifact target uses a reserved directory name: {name}")
        normalized = str(path).lower()
        if normalized in seen:
            raise RenderError(f"duplicate artifact target: {name} collides with {seen[normalized]}")
        seen[normalized] = name
    for name, text in contents.items():
        if "{{" in text or "}}" in text:
            raise RenderError(f"artifact {name} has an unresolved placeholder")


def _reject_symlinked_path(root: Path, relative: Path) -> None:
    current = root
    for component in relative.parts:
        current /= component
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            return
        if stat.S_ISLNK(mode):
            raise RenderError("work package path contains a symlinked component")
        if not stat.S_ISDIR(mode):
            raise RenderError("work package path parent is not a directory")
