#!/usr/bin/env python3
"""Build a self-contained adapter bundle from a named adapter template."""

import argparse
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
from typing import Sequence


_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_ADAPTERS_ROOT = _PROJECT_ROOT / "adapters"
_CAPABILITIES_PATH = _ADAPTERS_ROOT / "capabilities.json"
_SOURCE_PACKAGE = _PROJECT_ROOT / "core" / "agent_checkpoint"
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


class BuildError(ValueError):
    """Raised for an adapter build request that cannot be fulfilled safely."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("adapter", help="adapter template to package")
    parser.add_argument("--output", type=Path, required=True, help="bundle directory")
    parser.add_argument(
        "--force", action="store_true", help="replace a nonempty output directory"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        capabilities = _load_capabilities()
        if arguments.adapter not in capabilities:
            raise BuildError(f"Unknown adapter: {arguments.adapter}")
        _build_bundle(arguments.adapter, arguments.output, arguments.force)
    except BuildError as error:
        print(str(error), file=sys.stderr)
        return 2
    except OSError:
        print("I/O error: unable to build adapter bundle", file=sys.stderr)
        return 5
    return 0


def _load_capabilities() -> dict[str, str]:
    try:
        data = json.loads(_CAPABILITIES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BuildError("Unable to read adapter capability metadata") from error
    if not isinstance(data, dict) or not all(
        isinstance(name, str) and isinstance(level, str) for name, level in data.items()
    ):
        raise BuildError("Invalid adapter capability metadata")
    return data


def _build_bundle(adapter: str, output: Path, force: bool) -> None:
    template = _ADAPTERS_ROOT / adapter
    if not template.is_dir():
        raise BuildError(f"Missing adapter template: adapters/{adapter}")
    if not _SOURCE_PACKAGE.is_dir():
        raise BuildError("Missing canonical core package")

    output = _validated_output(output, template, force)
    output.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlinked_ancestors(output)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}-staging-", dir=output.parent)
    )
    try:
        shutil.copytree(
            template,
            staging,
            dirs_exist_ok=True,
            ignore=_IGNORED_COPY_NAMES,
        )
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


def _validated_output(output: Path, template: Path, force: bool) -> Path:
    if ".." in output.parts:
        raise BuildError("Output path must not contain '..' traversal")
    output = Path(os.path.abspath(output))
    _reject_symlinked_ancestors(output)
    if output.is_symlink() or (output.exists() and not output.is_dir()):
        raise BuildError("Output path must be a directory, not a file or symlink")
    for source in (_ADAPTERS_ROOT, _SOURCE_PACKAGE):
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
