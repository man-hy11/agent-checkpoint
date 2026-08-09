"""Project configuration and managed Git-ignore support."""

from dataclasses import dataclass
import errno
import math
import os
from pathlib import Path
import re
import stat
import tempfile
import tomllib


_CONFIG_FILENAME = ".agent-checkpoint.toml"
_BLOCK_START = "# >>> agent-checkpoint >>>"
_BLOCK_END = "# <<< agent-checkpoint <<<"
_GITIGNORE_MAGIC = frozenset(r"\*?[]")
_LANGUAGE_MAX_LENGTH = 40
_LANGUAGE_PATTERN = re.compile(
    r"[A-Za-z][A-Za-z0-9]{0,15}(?:[- ][A-Za-z0-9]{1,15}){0,4}"
)
_MAX_LOCK_TIMEOUT_SECONDS = 300.0
_ALLOWED_FIELDS = {
    "progress_path",
    "archive_path",
    "language",
    "max_live_chars",
    "resume_max_chars",
    "lock_timeout_seconds",
    "include_git_hints",
}
_RESERVED_COMPONENTS = {
    ".agent-checkpoint.lock",
    ".agent-checkpoint.toml",
    ".git",
    ".gitignore",
}
_WINDOWS_RESERVED_NAMES = {
    "aux",
    "con",
    "nul",
    "prn",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}


class ConfigError(ValueError):
    """Raised when project configuration is invalid."""


@dataclass(frozen=True)
class ProjectConfig:
    """Validated settings for a checkpoint project."""

    progress_path: Path = Path("PROGRESS.md")
    archive_path: Path = Path("PROGRESS_ARCHIVE.md")
    language: str = "English"
    max_live_chars: int = 12_000
    resume_max_chars: int = 6_000
    lock_timeout_seconds: float = 10.0
    include_git_hints: bool = True

    def __post_init__(self) -> None:
        _validate_language(self.language)
        _validate_lock_timeout(self.lock_timeout_seconds)


@dataclass(frozen=True)
class IgnoreResult:
    """The outcome of ensuring the checkpoint block in ``.gitignore``."""

    path: Path
    changed: bool


def load_config(project_root: Path) -> ProjectConfig:
    """Load and validate the optional project-local TOML configuration."""
    config_path = Path(project_root) / _CONFIG_FILENAME
    if not config_path.exists():
        config = ProjectConfig()
        resolve_checkpoint_paths(project_root, config)
        return config

    try:
        raw_config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ConfigError(f"Could not read {_CONFIG_FILENAME}: {error}") from error

    if not isinstance(raw_config, dict):
        raise ConfigError("Configuration must be a TOML table")
    unknown_fields = set(raw_config) - _ALLOWED_FIELDS
    if unknown_fields:
        names = ", ".join(sorted(unknown_fields))
        raise ConfigError(f"Unknown configuration field(s): {names}")

    defaults = ProjectConfig()
    values = {
        "progress_path": _path_value(raw_config, "progress_path", defaults.progress_path),
        "archive_path": _path_value(raw_config, "archive_path", defaults.archive_path),
        "language": _language_value(raw_config, "language", defaults.language),
        "max_live_chars": _integer_value(
            raw_config, "max_live_chars", defaults.max_live_chars
        ),
        "resume_max_chars": _integer_value(
            raw_config, "resume_max_chars", defaults.resume_max_chars
        ),
        "lock_timeout_seconds": _number_value(
            raw_config, "lock_timeout_seconds", defaults.lock_timeout_seconds
        ),
        "include_git_hints": _boolean_value(
            raw_config, "include_git_hints", defaults.include_git_hints
        ),
    }
    if values["max_live_chars"] < 1000:
        raise ConfigError("max_live_chars must be at least 1000")
    if values["resume_max_chars"] <= 0:
        raise ConfigError("resume_max_chars must be greater than zero")
    _validate_lock_timeout(values["lock_timeout_seconds"])
    config = ProjectConfig(**values)
    resolve_checkpoint_paths(project_root, config)
    return config


def resolve_checkpoint_paths(
    project_root: Path, config: ProjectConfig
) -> tuple[Path, Path, Path]:
    """Return canonical root/live/archive paths after containment validation."""
    root = Path(project_root).resolve()
    resolved_paths = []
    for name, configured_path in (
        ("progress_path", config.progress_path),
        ("archive_path", config.archive_path),
    ):
        relative_path = _validated_relative_path(configured_path, name)
        _reject_symlinked_components(root, relative_path, name)
        resolved_path = (root / relative_path).resolve()
        try:
            resolved_path.relative_to(root)
        except ValueError:
            raise ConfigError(f"{name} must remain within the project") from None
        resolved_paths.append(resolved_path)
    progress_path, archive_path = resolved_paths
    if _paths_overlap(progress_path, archive_path):
        raise ConfigError(
            "progress_path and archive_path must be distinct, non-overlapping files"
        )
    return root, progress_path, archive_path


def _paths_overlap(first: Path, second: Path) -> bool:
    try:
        if first.samefile(second):
            return True
    except (FileNotFoundError, OSError):
        pass
    try:
        first.relative_to(second)
        return True
    except ValueError:
        pass
    try:
        second.relative_to(first)
        return True
    except ValueError:
        return False


def ensure_gitignore(project_root: Path, config: ProjectConfig) -> IgnoreResult:
    """Add or replace only the checkpoint-owned block in ``.gitignore``."""
    root, _, _ = resolve_checkpoint_paths(project_root, config)
    gitignore_path = root / ".gitignore"
    _reject_symlink(gitignore_path, ".gitignore")
    original = _read_text_preserving_newlines(gitignore_path)
    newline = "\r\n" if "\r\n" in original else "\n"
    managed_block = _render_managed_block(config, newline)
    managed_blocks = _managed_block_spans(original)
    if managed_blocks:
        updated = _replace_managed_blocks(original, managed_blocks, managed_block)
    elif original:
        separator = "" if original.endswith(("\n", "\r")) else newline
        updated = f"{original}{separator}{managed_block}"
    else:
        updated = managed_block

    changed = updated != original
    if changed:
        _write_text_preserving_newlines(gitignore_path, updated)
    return IgnoreResult(path=gitignore_path, changed=changed)


def _managed_block_spans(text: str) -> list[tuple[int, int]]:
    """Return complete marker-block spans, rejecting malformed marker lines."""
    blocks = []
    block_start = None
    offset = 0
    for line in text.splitlines(keepends=True):
        marker = line.rstrip("\r\n")
        if marker == _BLOCK_START:
            if block_start is not None:
                raise ConfigError("Malformed agent-checkpoint block in .gitignore")
            block_start = offset
        elif marker == _BLOCK_END:
            if block_start is None:
                raise ConfigError("Malformed agent-checkpoint block in .gitignore")
            blocks.append((block_start, offset + len(line)))
            block_start = None
        offset += len(line)
    if block_start is not None:
        raise ConfigError("Malformed agent-checkpoint block in .gitignore")
    return blocks


def _replace_managed_blocks(
    text: str, blocks: list[tuple[int, int]], managed_block: str
) -> str:
    """Replace the first block and remove duplicate blocks without touching rules."""
    parts = []
    offset = 0
    for index, (start, end) in enumerate(blocks):
        parts.append(text[offset:start])
        if index == 0:
            parts.append(managed_block)
        offset = end
    parts.append(text[offset:])
    return "".join(parts)


def _path_value(raw_config: dict, name: str, default: Path) -> Path:
    value = raw_config.get(name, default)
    if isinstance(value, Path):
        return value
    if not isinstance(value, str):
        raise ConfigError(f"{name} must be a string")
    return _validated_relative_path(Path(value), name, raw_value=value)


def _validated_relative_path(
    path: Path | str, name: str, *, raw_value: str | None = None
) -> Path:
    try:
        path = Path(path)
    except TypeError:
        raise ConfigError(f"{name} must be a path") from None
    value = path.as_posix() if raw_value is None else raw_value
    if (
        not value
        or path == Path(".")
        or path.is_absolute()
        or ".." in path.parts
        or any(not character.isprintable() for character in value)
    ):
        raise ConfigError(f"{name} must be a safe relative path within the project")
    for component in path.parts:
        folded = component.casefold()
        device_name = folded.split(".", 1)[0]
        if (
            folded in _RESERVED_COMPONENTS
            or device_name in _WINDOWS_RESERVED_NAMES
            or component.endswith((" ", "."))
        ):
            raise ConfigError(f"{name} uses a reserved path")
    return path


def _reject_symlinked_components(root: Path, relative_path: Path, name: str) -> None:
    """Reject existing links below the canonical project root without following them."""
    current = root
    for component in relative_path.parts:
        current /= component
        try:
            mode = current.lstat().st_mode
        except (FileNotFoundError, NotADirectoryError):
            return
        if stat.S_ISLNK(mode):
            raise ConfigError(f"{name} contains a symlinked path component")


def _language_value(raw_config: dict, name: str, default: str) -> str:
    value = raw_config.get(name, default)
    _validate_language(value)
    return value


def _validate_language(value: object) -> None:
    if (
        not isinstance(value, str)
        or len(value) > _LANGUAGE_MAX_LENGTH
        or _LANGUAGE_PATTERN.fullmatch(value) is None
    ):
        raise ConfigError(
            "language must be a short language name or BCP-47-like tag"
        )


def _integer_value(raw_config: dict, name: str, default: int) -> int:
    value = raw_config.get(name, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"{name} must be an integer")
    return value


def _number_value(raw_config: dict, name: str, default: float) -> float:
    value = raw_config.get(name, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{name} must be a number")
    return float(value)


def _validate_lock_timeout(value: object) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) < 0
        or float(value) > _MAX_LOCK_TIMEOUT_SECONDS
    ):
        raise ConfigError(
            "lock_timeout_seconds must be finite and between 0 and 300 seconds"
        )


def _boolean_value(raw_config: dict, name: str, default: bool) -> bool:
    value = raw_config.get(name, default)
    if not isinstance(value, bool):
        raise ConfigError(f"{name} must be a boolean")
    return value


def _render_managed_block(config: ProjectConfig, newline: str) -> str:
    return newline.join(
        (
            _BLOCK_START,
            _gitignore_pattern(config.progress_path),
            _gitignore_pattern(config.archive_path),
            _BLOCK_END,
            "",
        )
    )


def _gitignore_pattern(path: Path) -> str:
    pattern = path.as_posix()
    return "".join(
        "\\" + character
        if character in _GITIGNORE_MAGIC
        or (index == 0 and character in ("#", "!"))
        else character
        for index, character in enumerate(pattern)
    )


def _read_text_preserving_newlines(path: Path) -> str:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError:
        return ""
    except OSError as error:
        if error.errno == errno.ELOOP:
            raise ConfigError(".gitignore must not be a symlink") from None
        raise
    with os.fdopen(descriptor, "r", encoding="utf-8", newline="") as file:
        return file.read()


def _write_text_preserving_newlines(path: Path, text: str) -> None:
    _reject_symlink(path, ".gitignore")
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            prefix=".agent-checkpoint-",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(text)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        _reject_symlink(path, ".gitignore")
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass


def _reject_symlink(path: Path, name: str) -> None:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return
    if stat.S_ISLNK(mode):
        raise ConfigError(f"{name} must not be a symlink")
