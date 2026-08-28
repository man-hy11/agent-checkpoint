#!/usr/bin/env python3
"""Build a self-contained adapter bundle by projecting single-source content.

Host-specific content is not stored per host. It is projected at build time
from the shared trees (``skills/``, ``commands/``, ``hooks/``) onto the profile
declared for the host in ``hosts.toml``.
"""

import argparse
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import tomllib
from typing import Any, Sequence


_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_HOSTS_PATH = _PROJECT_ROOT / "hosts.toml"
_PACKAGE_JSON = _PROJECT_ROOT / "package.json"
_SOURCE_PACKAGE = _PROJECT_ROOT / "agent_checkpoint"
_SKILLS_ROOT = _PROJECT_ROOT / "skills"
_COMMANDS_ROOT = _PROJECT_ROOT / "commands"
_HOOKS_ROOT = _PROJECT_ROOT / "hooks"
_IGNORED_COPY_NAMES = shutil.ignore_patterns("__pycache__", "*.pyc")
_LAUNCHER = '''#!/usr/bin/env python3
"""Run agent-checkpoint from this adapter bundle."""

from pathlib import Path
import sys


_bundle_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_bundle_root / "lib"))

from agent_checkpoint.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
'''

# Repo-only files that live beside shared sources but are never shipped.
_UNSHIPPED_NAMES = frozenset({"AGENTS.md", "README.md"})


class BuildError(ValueError):
    """Raised for an adapter build request that cannot be fulfilled safely."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("adapter", help="host to project a bundle for")
    parser.add_argument("--output", type=Path, required=True, help="bundle directory")
    parser.add_argument(
        "--force", action="store_true", help="replace a nonempty output directory"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        hosts = load_hosts()
        if arguments.adapter not in hosts["hosts"]:
            raise BuildError(f"Unknown adapter: {arguments.adapter}")
        _build_bundle(arguments.adapter, arguments.output, arguments.force)
    except BuildError as error:
        print(str(error), file=sys.stderr)
        return 2
    except OSError:
        print("I/O error: unable to build adapter bundle", file=sys.stderr)
        return 5
    return 0


def load_hosts() -> dict[str, Any]:
    """Read and shallowly validate hosts.toml."""
    try:
        with _HOSTS_PATH.open("rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise BuildError("Unable to read hosts.toml") from error
    hosts = data.get("hosts")
    if not isinstance(hosts, dict) or not hosts:
        raise BuildError("Invalid hosts.toml: missing [hosts] table")
    for name, profile in hosts.items():
        if not isinstance(profile, dict) or not isinstance(
            profile.get("capability"), str
        ):
            raise BuildError(f"Invalid host profile: {name}")
    return data


def capabilities() -> dict[str, str]:
    """Return the host -> capability map declared in hosts.toml."""
    return {
        name: profile["capability"]
        for name, profile in load_hosts()["hosts"].items()
    }


def _package_version() -> str:
    """Every generated manifest takes its version from package.json."""
    try:
        data = json.loads(_PACKAGE_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BuildError("Unable to read package.json") from error
    version = data.get("version")
    if not isinstance(version, str) or not version:
        raise BuildError("package.json declares no version")
    return version


# --------------------------------------------------------------------------
# JSON rendering
# --------------------------------------------------------------------------


def _render_json(value: Any, indent: int = 0) -> str:
    """Serialize with arrays of scalars kept inline.

    ``json.dumps(indent=2)`` explodes every array across multiple lines. The
    hand-authored manifests this projection reproduces keep short scalar arrays
    on one line, so matching that convention is what keeps generated output
    byte-identical to the baseline fixture.
    """
    pad = " " * indent
    inner = " " * (indent + 2)
    if isinstance(value, dict):
        if not value:
            return "{}"
        items = [
            f'{inner}{json.dumps(key)}: {_render_json(item, indent + 2)}'
            for key, item in value.items()
        ]
        return "{\n" + ",\n".join(items) + f"\n{pad}}}"
    if isinstance(value, list):
        if not value:
            return "[]"
        if all(not isinstance(item, (dict, list)) for item in value):
            return "[" + ", ".join(json.dumps(item) for item in value) + "]"
        items = [f"{inner}{_render_json(item, indent + 2)}" for item in value]
        return "[\n" + ",\n".join(items) + f"\n{pad}]"
    return json.dumps(value)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_json(value) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------
# Projection
# --------------------------------------------------------------------------


# Frontmatter keys emitted as quoted, ASCII-escaped JSON strings in bundled
# output. `name` is always left bare, `description` always quoted — including
# the one description that happens to be pure ASCII, so the rule is
# key-specific rather than driven by whether escaping is needed.
_QUOTED_FRONTMATTER_KEYS = frozenset({"description"})


def _render_skill(text: str) -> str:
    """Re-emit a canonical SKILL.md in the bundled frontmatter form.

    Canonical sources under ``skills/`` author frontmatter values as plain
    unquoted YAML. Bundled output quotes and ``\\uXXXX``-escapes the keys in
    ``_QUOTED_FRONTMATTER_KEYS`` — the form
    ``validate_adapters._frontmatter_string`` accepts and the baseline fixture
    records. Only those frontmatter values are touched; every other line and
    the whole body pass through byte-for-byte.
    """
    if not text.startswith("---\n"):
        return text
    closing = text.find("\n---\n", 4)
    if closing == -1:
        return text
    frontmatter = text[4:closing]
    body = text[closing + 5 :]

    lines = []
    for line in frontmatter.split("\n"):
        key, delimiter, raw_value = line.partition(":")
        value = raw_value.strip()
        if (
            not delimiter
            or key not in _QUOTED_FRONTMATTER_KEYS
            or not value
            or value.startswith(('"', "'"))
        ):
            lines.append(line)
            continue
        lines.append(f"{key}: {json.dumps(value)}")
    return "---\n" + "\n".join(lines) + "\n---\n" + body


def _project_skills(profile: dict[str, Any], staging: Path) -> None:
    """Project the canonical skills for hosts that ship them."""
    if not profile.get("ships_skills"):
        return
    if not _SKILLS_ROOT.is_dir():
        raise BuildError("Missing canonical skills/ source")
    target = staging / "skills"
    for entry in sorted(_SKILLS_ROOT.iterdir()):
        if not entry.is_dir() or entry.name.startswith("_"):
            continue
        source = entry / "SKILL.md"
        if not source.is_file():
            continue
        destination = target / entry.name / "SKILL.md"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            _render_skill(source.read_text(encoding="utf-8")), encoding="utf-8"
        )
    _project_shared_contract(target)


def _project_shared_contract(target: Path) -> None:
    """Copy the shared routing contract the router SKILL.md points at.

    ``_checkpoint-shared/`` is skipped by the loop above (underscore prefix,
    and it holds no SKILL.md), but every bundled router refers readers to
    ``_checkpoint-shared/chain-v1.md`` for the full routing table. It is
    copied verbatim: it is a contract document, not a skill, so it carries no
    skill frontmatter for ``_render_skill`` to rewrite.
    """
    source = _SKILLS_ROOT / "_checkpoint-shared" / "chain-v1.md"
    if not source.is_file():
        raise BuildError("Missing canonical skills/_checkpoint-shared/chain-v1.md")
    destination = target / "_checkpoint-shared" / "chain-v1.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes())


def _project_commands(profile: dict[str, Any], host: str, staging: Path) -> None:
    """Select this host's command body for each declared command name.

    R4 established that command bodies are authored per host rather than
    rendered from one template: the ``description`` strings differ per host and
    the prose structure differs by format. So this selects and copies; it does
    not substitute.
    """
    commands = profile.get("commands")
    if not commands:
        return
    extension = commands["format"]
    for name in commands["names"]:
        source = _COMMANDS_ROOT / name / f"{host}.{extension}"
        if not source.is_file():
            raise BuildError(f"Missing command source: {source.relative_to(_PROJECT_ROOT)}")
        destination = staging / "commands" / f"{name}.{extension}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)


def _hook_registration(hooks: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Build one hook entry, honoring this host's structural conventions."""
    path = f"{hooks['path_variable']}/hooks/{event['script']}"
    entry: dict[str, Any] = {}
    if hooks.get("entry_name"):
        entry["name"] = event["name"]
    entry["type"] = "command"
    if hooks["command_shape"] == "args_array":
        entry["command"] = "python3"
        entry["args"] = [path]
    else:
        entry["command"] = f'python3 "{path}"'
    entry["timeout"] = event["timeout"]

    registration: dict[str, Any] = {}
    # Matcher presence is itself a difference: SessionStart carries no matcher
    # key at all, which is not the same as an empty matcher.
    if "matcher" in event:
        registration["matcher"] = event["matcher"]
    registration["hooks"] = [entry]
    return registration


def _project_hooks(profile: dict[str, Any], staging: Path) -> None:
    """Copy each declared hook script and generate the host's hooks.json."""
    hooks = profile.get("hooks")
    if not hooks:
        return
    events = hooks["events"]

    manifest: dict[str, Any] = {}
    description = hooks.get("description")
    if description is not False:
        manifest["description"] = description
    manifest["hooks"] = {
        event["event"]: [_hook_registration(hooks, event)] for event in events
    }

    for event in events:
        source = _HOOKS_ROOT / event["script"]
        if not source.is_file():
            raise BuildError(f"Missing hook source: hooks/{event['script']}")
        destination = staging / "hooks" / event["script"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)

    _write_json(staging / hooks["manifest"], manifest)


def _manifest_body(kind: str, version: str) -> dict[str, Any]:
    """Return the install-manifest content for one declared manifest kind."""
    claude_description = (
        "Portable project checkpoints with automatic pre-compaction and "
        "session-resume support."
    )
    if kind == "claude_plugin":
        return {
            "name": "agent-checkpoint",
            "description": claude_description,
            "version": version,
        }
    if kind == "claude_marketplace":
        return {
            "name": "agent-checkpoint",
            "owner": {"name": "h_y_p", "email": "rodlfmaro@gmail.com"},
            "plugins": [
                {
                    "name": "agent-checkpoint",
                    "source": ".",
                    "description": claude_description,
                }
            ],
        }
    if kind == "codex_plugin":
        return {
            "name": "agent-checkpoint",
            "version": version,
            "description": (
                "Manual project checkpoints, resume context, and handoff summaries."
            ),
            "author": {"name": "Agent Checkpoint contributors"},
            "skills": "./skills/",
            "interface": {
                "displayName": "Agent Checkpoint",
                "shortDescription": "Save manual project checkpoints",
                "longDescription": (
                    "Save resumable project checkpoints and render manual resume "
                    "or handoff context."
                ),
                "developerName": "Agent Checkpoint contributors",
                "category": "Developer Tools",
                "capabilities": ["Read", "Write"],
                "defaultPrompt": ["Save a checkpoint for the current project."],
            },
        }
    if kind == "gemini_extension":
        return {
            "name": "agent-checkpoint",
            "version": version,
            "description": (
                "Portable project checkpoints with a pre-compression advisory "
                "and manual resume or handoff commands."
            ),
        }
    raise BuildError(f"Unknown manifest kind: {kind}")


def _project_manifests(profile: dict[str, Any], staging: Path) -> None:
    version = _package_version()
    for relative, kind in profile.get("manifests", {}).items():
        _write_json(staging / relative, _manifest_body(kind, version))


def _build_bundle(adapter: str, output: Path, force: bool) -> None:
    hosts = load_hosts()
    profile = hosts["hosts"][adapter]
    if not _SOURCE_PACKAGE.is_dir():
        raise BuildError("Missing canonical core package")

    output = _validated_output(output, force)
    output.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlinked_ancestors(output)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}-staging-", dir=output.parent)
    )
    try:
        _project_skills(profile, staging)
        _project_commands(profile, adapter, staging)
        _project_hooks(profile, staging)
        _project_manifests(profile, staging)
        shutil.copytree(
            _SOURCE_PACKAGE,
            staging / "lib" / "agent_checkpoint",
            ignore=_IGNORED_COPY_NAMES,
        )
        launcher = staging / "bin" / "agent-checkpoint"
        launcher.parent.mkdir(parents=True, exist_ok=True)
        launcher.write_text(_LAUNCHER, encoding="utf-8")
        launcher.chmod(
            launcher.stat().st_mode
            | stat.S_IXUSR
            | stat.S_IXGRP
            | stat.S_IXOTH
        )
        _replace_output(staging, output)
        staging = None
    finally:
        if staging is not None:
            shutil.rmtree(staging)


def _validated_output(output: Path, force: bool) -> Path:
    if ".." in output.parts:
        raise BuildError("Output path must not contain '..' traversal")
    output = Path(os.path.abspath(output))
    _reject_symlinked_ancestors(output)
    if output.is_symlink() or (output.exists() and not output.is_dir()):
        raise BuildError("Output path must be a directory, not a file or symlink")
    for source in (_SKILLS_ROOT, _COMMANDS_ROOT, _HOOKS_ROOT, _SOURCE_PACKAGE):
        if _paths_overlap(output, source.resolve()):
            raise BuildError("Output path must not overlap adapter or core sources")
    if output.is_dir() and any(output.iterdir()):
        if not force:
            raise BuildError("Refusing to write to a nonempty output directory")
    return output


def _paths_overlap(first: Path, second: Path) -> bool:
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


def _replace_output(staging: Path, output: Path) -> None:
    """Publish a complete staged bundle, restoring the prior output on failure."""
    if not output.exists():
        os.replace(staging, output)
        return

    backup = Path(
        tempfile.mkdtemp(prefix=f".{output.name}-backup-", dir=output.parent)
    )
    backup.rmdir()
    os.replace(output, backup)
    try:
        os.replace(staging, output)
    except OSError:
        os.replace(backup, output)
        raise
    shutil.rmtree(backup)


def _reject_symlinked_ancestors(output: Path) -> None:
    """Reject an output whose existing lexical path components contain links."""
    absolute_output = Path(os.path.abspath(output))
    current = Path(absolute_output.anchor)
    for part in absolute_output.parts[1:]:
        current /= part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            return
        if stat.S_ISLNK(mode):
            raise BuildError("Output path contains a symlinked ancestor")


if __name__ == "__main__":
    raise SystemExit(main())
