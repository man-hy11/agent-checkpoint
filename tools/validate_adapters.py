#!/usr/bin/env python3
"""Statically validate the common files in an adapter bundle."""

import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys
import tomllib
from typing import Sequence


_LAUNCHER_PATH = Path("bin") / "agent-checkpoint"
_CORE_MODULES = (
    "__init__.py",
    "cli.py",
    "config.py",
    "diagnostics.py",
    "git_state.py",
    "models.py",
    "progress.py",
    "secrets.py",
    "storage.py",
    "workflows.py",
    "skill_install.py",
)
_LAUNCHER_MARKERS = (
    "sys.path.insert(0, str(_bundle_root / \"lib\"))",
    "from agent_checkpoint.cli import main",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle_directory", type=Path, help="adapter bundle to check")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    bundle = build_parser().parse_args(argv).bundle_directory
    errors = validate_bundle(bundle)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 2
    return 0


def validate_bundle(bundle: Path) -> list[str]:
    """Return static common-bundle violations without executing bundle code."""
    if bundle.is_symlink() or not bundle.is_dir():
        return ["bundle directory is missing or is not a directory"]

    errors = _symlinked_bundle_paths(bundle)
    if errors:
        return errors
    launcher_error = _required_regular_file(
        bundle, _LAUNCHER_PATH, "missing required launcher: bin/agent-checkpoint"
    )
    if launcher_error:
        errors.append(launcher_error)
    else:
        errors.extend(_validate_launcher(bundle / _LAUNCHER_PATH))
    for module in _CORE_MODULES:
        relative_path = Path("lib") / "agent_checkpoint" / module
        relative_text = str(relative_path)
        module_error = _required_regular_file(
            bundle, relative_path, f"missing bundled core: {relative_text}"
        )
        if module_error:
            errors.append(module_error)
        else:
            errors.extend(_validate_python_source(bundle / relative_path, relative_text))
    errors.extend(_validate_template_assets(bundle))
    errors.extend(_validate_native_adapter(bundle))
    return errors


def _validate_template_assets(bundle: Path) -> list[str]:
    root = Path("lib/agent_checkpoint/assets/development-templates")
    required = (
        "README.md",
        "shared/EXECUTION_RULES.md",
        "feature/prompts/CONTINUE_PROMPT.md",
        "feature/templates/CURRENT_TEMPLATE.md",
    )
    errors: list[str] = []
    for relative in required:
        path = root / relative
        error = _required_regular_file(
            bundle, path, f"missing bundled template asset: {path}"
        )
        if error:
            errors.append(error)
    return errors


def _validate_native_adapter(bundle: Path) -> list[str]:
    if (bundle / ".claude-plugin").is_dir() or (
        bundle / "hooks" / "pre_compact.py"
    ).is_file():
        return _validate_claude(bundle)
    if (bundle / ".codex-plugin").is_dir():
        return _validate_codex(bundle)
    if (bundle / "gemini-extension.json").is_file() or (
        bundle / "hooks" / "pre_compress.py"
    ).is_file():
        return _validate_gemini(bundle)
    if (bundle / "commands" / "checkpoint.md").is_file():
        return _validate_opencode(bundle)
    return ["missing or unrecognized native adapter files"]


def _validate_claude(bundle: Path) -> list[str]:
    errors: list[str] = []
    manifest = _json_object(
        bundle, Path(".claude-plugin/plugin.json"), errors
    )
    if manifest is not None:
        errors.extend(
            _require_string_fields(
                manifest,
                ("name", "version", "description"),
                ".claude-plugin/plugin.json",
            )
        )
    for name, action in (
        ("checkpoint", '"${CLAUDE_PLUGIN_ROOT}/bin/agent-checkpoint" write --entry -'),
        ("resume", '"${CLAUDE_PLUGIN_ROOT}/bin/agent-checkpoint" resume'),
        ("handoff", '"${CLAUDE_PLUGIN_ROOT}/bin/agent-checkpoint" handoff'),
    ):
        errors.extend(
            _validate_markdown_command(
                bundle, Path("commands") / f"{name}.md", action
            )
        )
    hooks = _json_object(bundle, Path("hooks/hooks.json"), errors)
    if hooks is not None:
        registrations = hooks.get("hooks")
        if not isinstance(registrations, dict) or set(registrations) != {
            "PreCompact",
            "SessionStart",
        }:
            errors.append("invalid Claude hooks: hooks/hooks.json")
        else:
            expected = {
                "PreCompact": (
                    "hooks/pre_compact.py",
                    {"manual", "auto"},
                ),
                "SessionStart": ("hooks/session_start.py", None),
            }
            for event, (script, matchers) in expected.items():
                registration, matcher = _hook_registration(registrations[event])
                if not (
                    isinstance(registration, dict)
                    and registration.get("type") == "command"
                    and registration.get("command") == "python3"
                    and registration.get("args")
                    == [f"${{CLAUDE_PLUGIN_ROOT}}/{script}"]
                    and isinstance(registration.get("timeout"), int)
                    and registration["timeout"] > 0
                    and (
                        matchers is None
                        or isinstance(matcher, str)
                        and set(matcher.split("|")) == matchers
                    )
                ):
                    errors.append(f"invalid Claude {event} hook: hooks/hooks.json")
    for hook in ("pre_compact.py", "session_start.py"):
        relative = Path("hooks") / hook
        required = _required_regular_file(
            bundle, relative, f"missing Claude hook: {relative}"
        )
        if required:
            errors.append(required)
        else:
            errors.extend(_validate_python_source(bundle / relative, str(relative)))
    return errors


def _validate_codex(bundle: Path) -> list[str]:
    errors: list[str] = []
    manifest = _json_object(bundle, Path(".codex-plugin/plugin.json"), errors)
    if manifest is not None:
        errors.extend(
            _require_string_fields(
                manifest,
                ("name", "version", "description", "skills"),
                ".codex-plugin/plugin.json",
            )
        )
        interface = manifest.get("interface")
        default_prompt = (
            interface.get("defaultPrompt") if isinstance(interface, dict) else None
        )
        if not isinstance(default_prompt, list) or not default_prompt or not all(
            isinstance(prompt, str) and prompt for prompt in default_prompt
        ):
            errors.append(
                "invalid Codex defaultPrompt array: .codex-plugin/plugin.json"
            )
        if not isinstance(interface, dict) or _require_string_fields(
            interface,
            (
                "displayName",
                "shortDescription",
                "longDescription",
                "developerName",
                "category",
            ),
            ".codex-plugin/plugin.json interface",
        ):
            errors.append("invalid Codex interface: .codex-plugin/plugin.json")
        capabilities = interface.get("capabilities") if isinstance(interface, dict) else None
        if not isinstance(capabilities, list) or not all(
            isinstance(capability, str) and capability for capability in capabilities
        ):
            errors.append("invalid Codex capabilities: .codex-plugin/plugin.json")
    skill = Path("skills/checkpoint/SKILL.md")
    skill_error = _required_regular_file(
        bundle, skill, f"missing Codex skill: {skill}"
    )
    if skill_error:
        errors.append(skill_error)
    else:
        errors.extend(_validate_skill(bundle / skill, str(skill)))
    return errors


def _validate_opencode(bundle: Path) -> list[str]:
    errors: list[str] = []
    for name, action in (
        ("checkpoint", "agent-checkpoint write --entry -"),
        ("resume", "agent-checkpoint resume"),
        ("handoff", "agent-checkpoint handoff"),
    ):
        errors.extend(
            _validate_markdown_command(
                bundle, Path("commands") / f"{name}.md", action
            )
        )
    skill = Path("skills/checkpoint/SKILL.md")
    skill_error = _required_regular_file(
        bundle, skill, f"missing OpenCode skill: {skill}"
    )
    if skill_error:
        errors.append(skill_error)
    else:
        errors.extend(_validate_skill(bundle / skill, str(skill)))
    return errors


def _validate_gemini(bundle: Path) -> list[str]:
    errors: list[str] = []
    manifest = _json_object(bundle, Path("gemini-extension.json"), errors)
    if manifest is not None:
        errors.extend(
            _require_string_fields(
                manifest,
                ("name", "version", "description"),
                "gemini-extension.json",
            )
        )
    for name, action in (
        ("checkpoint", "agent-checkpoint write --entry -"),
        ("resume", "agent-checkpoint resume"),
        ("handoff", "agent-checkpoint handoff"),
    ):
        relative = Path("commands") / f"{name}.toml"
        path = bundle / relative
        required = _required_regular_file(
            bundle, relative, f"missing Gemini command: {relative}"
        )
        if required:
            errors.append(required)
            continue
        try:
            command = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, tomllib.TOMLDecodeError):
            errors.append(f"invalid Gemini command: {relative}")
            continue
        if not (
            isinstance(command.get("description"), str)
            and command["description"]
            and isinstance(command.get("prompt"), str)
            and action in command["prompt"]
        ):
            errors.append(f"invalid Gemini command: {relative}")
    hooks = _json_object(bundle, Path("hooks/hooks.json"), errors)
    registrations = hooks.get("hooks") if hooks is not None else None
    if not isinstance(registrations, dict) or set(registrations) != {"PreCompress"}:
        errors.append("invalid Gemini hooks: hooks/hooks.json")
    else:
        registration, matcher = _hook_registration(registrations["PreCompress"])
        if not (
            matcher == "*"
            and isinstance(registration, dict)
            and registration.get("name") == "agent-checkpoint-pre-compress"
            and registration.get("type") == "command"
            and registration.get("command")
            == 'python3 "${extensionPath}/hooks/pre_compress.py"'
            and isinstance(registration.get("timeout"), int)
            and registration["timeout"] > 0
        ):
            errors.append("invalid Gemini PreCompress hook: hooks/hooks.json")
    hook = Path("hooks/pre_compress.py")
    hook_error = _required_regular_file(
        bundle, hook, f"missing Gemini hook: {hook}"
    )
    if hook_error:
        errors.append(hook_error)
    else:
        errors.extend(_validate_python_source(bundle / hook, str(hook)))
    return errors


def _json_object(
    bundle: Path, relative: Path, errors: list[str]
) -> dict | None:
    required = _required_regular_file(
        bundle, relative, f"missing native manifest: {relative}"
    )
    if required:
        errors.append(required)
        return None
    try:
        value = json.loads((bundle / relative).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        errors.append(f"invalid native JSON: {relative}")
        return None
    if not isinstance(value, dict):
        errors.append(f"invalid native JSON object: {relative}")
        return None
    return value


def _require_string_fields(
    value: dict, fields: tuple[str, ...], relative: str
) -> list[str]:
    return [
        f"invalid native field {field}: {relative}"
        for field in fields
        if not isinstance(value.get(field), str) or not value[field]
    ]


def _validate_markdown_command(
    bundle: Path, relative: Path, expected_action: str
) -> list[str]:
    required = _required_regular_file(
        bundle, relative, f"missing native command: {relative}"
    )
    if required:
        return [required]
    try:
        text = (bundle / relative).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return [f"unreadable native command: {relative}"]
    metadata, remainder = _parse_frontmatter(text)
    if (
        metadata is None
        or not metadata.get("description")
        or expected_action not in remainder
    ):
        return [f"invalid native command: {relative}"]
    return []


def _validate_skill(path: Path, relative: str) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return [f"unreadable native skill: {relative}"]
    metadata, remainder = _parse_frontmatter(text)
    if (
        metadata is None
        or not metadata.get("name")
        or not metadata.get("description")
        or not remainder.strip()
    ):
        return [f"invalid native skill: {relative}"]
    return []


def _parse_frontmatter(text: str) -> tuple[dict[str, str] | None, str]:
    if not text.startswith("---\n"):
        return None, ""
    raw_metadata, separator, remainder = text[4:].partition("\n---\n")
    if not separator:
        return None, ""
    metadata: dict[str, str] = {}
    for line in raw_metadata.splitlines():
        if not line.strip():
            continue
        key, delimiter, raw_value = line.partition(":")
        if (
            not delimiter
            or key != key.strip()
            or not key
            or key in metadata
            or not all(character.isalnum() or character in "_-" for character in key)
        ):
            return None, ""
        value = raw_value.strip()
        string_value = _frontmatter_string(value)
        if string_value is None:
            return None, ""
        metadata[key] = string_value
    return metadata, remainder


def _frontmatter_string(value: str) -> str | None:
    """Accept only the string subset used by bundled native frontmatter."""
    if not value or value.startswith("#") or " #" in value:
        return None
    if value.startswith('"'):
        try:
            decoded = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return None
        return decoded if isinstance(decoded, str) and decoded else None
    if value.startswith("'"):
        if len(value) < 3 or not value.endswith("'"):
            return None
        decoded = value[1:-1].replace("''", "'")
        if not decoded or "'" in value[1:-1].replace("''", ""):
            return None
        return decoded
    if value.casefold() in {
        "false",
        "no",
        "null",
        "off",
        "on",
        "true",
        "yes",
        "~",
    }:
        return None
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9 _.,/()'-]*", value) is None:
        return None
    return value


def _hook_registration(value: object) -> tuple[dict | None, object]:
    if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], dict):
        return None, None
    group = value[0]
    hooks = group.get("hooks")
    if not isinstance(hooks, list) or len(hooks) != 1 or not isinstance(hooks[0], dict):
        return None, group.get("matcher")
    return hooks[0], group.get("matcher")


def _symlinked_bundle_paths(bundle: Path) -> list[str]:
    """Find links below a bundle without traversing them."""
    errors: list[str] = []
    directories = [bundle]
    while directories:
        directory = directories.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                path = Path(entry.path)
                mode = path.lstat().st_mode
                relative_path = path.relative_to(bundle)
                if stat.S_ISLNK(mode):
                    errors.append(f"symlinked bundle path: {relative_path}")
                elif stat.S_ISDIR(mode):
                    directories.append(path)
    return errors


def _required_regular_file(bundle: Path, relative_path: Path, missing: str) -> str | None:
    symlinked_component = _symlinked_component(bundle, relative_path)
    if symlinked_component is not None:
        return f"symlinked bundle path: {symlinked_component}"
    try:
        mode = (bundle / relative_path).lstat().st_mode
    except (FileNotFoundError, NotADirectoryError):
        return missing
    return None if stat.S_ISREG(mode) else missing


def _symlinked_component(bundle: Path, relative_path: Path) -> str | None:
    """Return the first linked component in a bundle-relative path, if any."""
    current = bundle
    for part in relative_path.parts:
        current /= part
        try:
            mode = current.lstat().st_mode
        except (FileNotFoundError, NotADirectoryError):
            return None
        if stat.S_ISLNK(mode):
            return str(current.relative_to(bundle))
    return None


def _validate_launcher(launcher: Path) -> list[str]:
    errors: list[str] = []
    try:
        source = launcher.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ["unreadable launcher: bin/agent-checkpoint"]
    if not launcher.stat().st_mode & stat.S_IXUSR:
        errors.append("launcher is not executable: bin/agent-checkpoint")
    if any(marker not in source for marker in _LAUNCHER_MARKERS):
        errors.append("invalid common launcher: bin/agent-checkpoint")
    try:
        compile(source, str(launcher), "exec")
    except SyntaxError:
        errors.append("invalid Python syntax: bin/agent-checkpoint")
    return errors


def _validate_python_source(path: Path, relative_path: str) -> list[str]:
    try:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
    except (OSError, UnicodeError, SyntaxError):
        return [f"invalid bundled core: {relative_path}"]
    return []


if __name__ == "__main__":
    raise SystemExit(main())
