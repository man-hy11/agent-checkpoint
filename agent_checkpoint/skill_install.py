"""Install the canonical generic skill and optional agent-specific links."""

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import stat
import tempfile

from .config import ConfigError


_SKILL_NAME = "checkpoint"
_SOURCE_SKILL = Path(__file__).resolve().parents[1] / "skills" / _SKILL_NAME
_SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"
_AGENT_NAMES = frozenset({"claude-code", "codex", "opencode", "agent-compatible", "gemini-cli"})

SKILL_NAMES: tuple[str, ...] = (
    "checkpoint",
    "checkpoint-brainstorm",
    "checkpoint-claim",
    "checkpoint-diagnose",
    "checkpoint-evidence",
    "checkpoint-execute",
    "checkpoint-handoff",
    "checkpoint-inspect",
    "checkpoint-plan",
    "checkpoint-recover",
    "checkpoint-save",
    "checkpoint-select-workflow",
    "checkpoint-verify-gate",
)


@dataclass(frozen=True)
class SkillSuiteInstallResult:
    """All installed skill directories and their agent-specific links."""

    skills: tuple[Path, ...]
    links: tuple[Path, ...]


def install_skill_suite(
    destination: Path, link_roots: tuple[Path, ...]
) -> SkillSuiteInstallResult:
    """Copy all twelve skills atomically, then link each to every link root.

    The entire install is staged and swapped in atomically per-skill. On any
    error, already-installed skills and links are removed before re-raising,
    leaving the destination either complete or empty.
    """
    destination_root = _safe_directory_path(destination, "skill destination")

    # Check all targets before touching the filesystem
    for name in SKILL_NAMES:
        _reject_existing(destination_root / name, f"{name} skill")
    normalized_link_roots: tuple[Path, ...] = tuple(
        _safe_directory_path(lr, "skill link destination") for lr in link_roots
    )
    for name in SKILL_NAMES:
        for lr in normalized_link_roots:
            _reject_existing(lr / name, f"{name} skill link")

    destination_root.mkdir(parents=True, exist_ok=True)
    installed_skills: list[Path] = []
    created_links: list[Path] = []
    try:
        for name in SKILL_NAMES:
            source = _SKILLS_DIR / name
            if not (source / "SKILL.md").is_file():
                raise OSError(f"bundled skill {name!r} is unavailable")
            target = destination_root / name
            staged = Path(tempfile.mkdtemp(prefix=f".{name}-skill-", dir=destination_root))
            try:
                shutil.copytree(source, staged / name)
                os.replace(staged / name, target)
            finally:
                if staged.exists() and not staged.is_symlink():
                    shutil.rmtree(staged, ignore_errors=True)
            installed_skills.append(target)

        for lr in normalized_link_roots:
            lr.mkdir(parents=True, exist_ok=True)
            for name in SKILL_NAMES:
                target = destination_root / name
                link = lr / name
                os.symlink(target, link, target_is_directory=True)
                created_links.append(link)

    except BaseException:
        for link in created_links:
            if link.is_symlink():
                link.unlink(missing_ok=True)
        for skill_dir in installed_skills:
            if skill_dir.is_dir() and not skill_dir.is_symlink():
                shutil.rmtree(skill_dir, ignore_errors=True)
        raise

    return SkillSuiteInstallResult(
        skills=tuple(installed_skills),
        links=tuple(created_links),
    )


@dataclass(frozen=True)
class SkillInstallResult:
    """The canonical installed skill and links created for it."""

    skill: Path
    links: tuple[Path, ...]


def global_skill_destination() -> Path:
    """Return the stable user-owned canonical global skill directory."""
    return Path.home() / ".agent" / "skills"


def agent_skill_roots(agent_names: tuple[str, ...]) -> tuple[Path, ...]:
    """Map selected compatible agents to their documented global skill locations."""
    roots: list[Path] = []
    for name in agent_names:
        if name not in _AGENT_NAMES:
            raise ConfigError(f"Unknown agent: {name}")
        if name == "gemini-cli":
            raise ConfigError(
                "gemini-cli uses a native extension, not a generic SKILL.md link"
            )
        if name == "claude-code":
            roots.append(Path.home() / ".claude" / "skills")
        elif name == "codex":
            roots.append(Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "skills")
        elif name == "opencode":
            roots.append(Path.home() / ".config" / "opencode" / "skills")
        else:
            roots.append(Path.home() / ".agents" / "skills")
    return tuple(roots)


def install_skill(destination: Path, link_roots: tuple[Path, ...]) -> SkillInstallResult:
    """Copy the generic skill once, then link agent-specific directories to it."""
    source = _SOURCE_SKILL
    if not (source / "SKILL.md").is_file():
        raise OSError("bundled generic checkpoint skill is unavailable")

    destination_root = _safe_directory_path(destination, "skill destination")
    target = destination_root / _SKILL_NAME
    _reject_existing(target, "checkpoint skill")

    normalized_links = tuple(
        _safe_directory_path(link_root, "skill link destination") / _SKILL_NAME
        for link_root in link_roots
    )
    if len(set(normalized_links)) != len(normalized_links):
        raise ConfigError("skill link destinations must be distinct")
    if target in normalized_links:
        raise ConfigError("skill link destination cannot equal the canonical destination")
    for link in normalized_links:
        _reject_existing(link, "skill link")

    destination_root.mkdir(parents=True, exist_ok=True)
    staged = Path(tempfile.mkdtemp(prefix=".checkpoint-skill-", dir=destination_root))
    try:
        shutil.copytree(source, staged / _SKILL_NAME)
        os.replace(staged / _SKILL_NAME, target)
        staged.rmdir()
        for link in normalized_links:
            link.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(target, link, target_is_directory=True)
    except BaseException:
        for link in normalized_links:
            if link.is_symlink():
                link.unlink()
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        if staged.exists() and not staged.is_symlink():
            shutil.rmtree(staged)
        raise
    return SkillInstallResult(skill=target, links=normalized_links)


def _safe_directory_path(value: Path, label: str) -> Path:
    """Return an absolute directory path without traversal or symlinked ancestors."""
    raw = Path(value)
    if ".." in raw.parts:
        raise ConfigError(f"{label} cannot contain '..'")
    path = raw if raw.is_absolute() else Path.cwd() / raw
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current /= component
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            break
        if stat.S_ISLNK(mode):
            raise ConfigError(f"{label} contains a symlinked component")
        if not stat.S_ISDIR(mode):
            raise ConfigError(f"{label} parent is not a directory")
    return path


def _reject_existing(path: Path, label: str) -> None:
    if path.exists() or path.is_symlink():
        raise ConfigError(f"{label} already exists: {path}")
