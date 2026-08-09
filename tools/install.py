#!/usr/bin/env python3
"""Install the dependency-free agent-checkpoint CLI into an explicit prefix."""

import argparse
import os
from pathlib import Path
import shutil
import stat
import sys
from typing import Sequence
import uuid


_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SOURCE_PACKAGE = _PROJECT_ROOT / "core" / "agent_checkpoint"
_SOURCE_LAUNCHER = _PROJECT_ROOT / "core" / "bin" / "agent-checkpoint"
_MARKER_NAME = ".agent-checkpoint-install"
_MARKER_CONTENT = "agent-checkpoint portable CLI\n"
_LAUNCHER_MARKER = "# agent-checkpoint portable launcher"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", type=Path, help="installation prefix")
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace a destination not owned by agent-checkpoint",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.prefix is None:
        if arguments.force:
            print("--force requires --prefix", file=sys.stderr)
            return 2
        _print_recommendation()
        return 0

    try:
        prefix = Path(os.path.abspath(arguments.prefix.expanduser()))
        _install(prefix, arguments.force)
    except DestinationRefused as error:
        print(str(error), file=sys.stderr)
        return 2
    except OSError:
        print("I/O error: unable to install agent-checkpoint", file=sys.stderr)
        return 5
    return 0


class DestinationRefused(ValueError):
    """Raised when installation would overwrite a foreign destination."""


def _print_recommendation() -> None:
    home = Path.home()
    package_path = home / ".local" / "share" / "agent-checkpoint"
    bin_path = home / ".local" / "bin"
    print(f"Recommended package path: {package_path}")
    print(f"Recommended launcher directory: {bin_path}")
    print("Run again with --prefix PATH to install; shell RC files are never edited.")


def _install(prefix: Path, force: bool) -> None:
    _reject_symlinked_install_ancestors(prefix)
    package_destination = prefix / "share" / "agent-checkpoint"
    launcher_destination = prefix / "bin" / "agent-checkpoint"
    marker = package_destination / _MARKER_NAME
    package_owned = (
        not package_destination.is_symlink() and _has_install_marker(marker)
    )
    launcher_owned = (
        not launcher_destination.is_symlink()
        and _is_agent_launcher(launcher_destination)
    )

    foreign_package = _destination_exists(package_destination) and not package_owned
    foreign_launcher = _destination_exists(launcher_destination) and not launcher_owned
    if (foreign_package or foreign_launcher) and not force:
        raise DestinationRefused(
            "Refusing to overwrite a non-agent-checkpoint destination"
        )

    package_destination.parent.mkdir(parents=True, exist_ok=True)
    launcher_destination.parent.mkdir(parents=True, exist_ok=True)
    staged_package = _stage_package(package_destination.parent)
    staged_launcher = _stage_launcher(launcher_destination.parent)
    try:
        _publish_staged_install(
            package_destination,
            staged_package,
            launcher_destination,
            staged_launcher,
        )
    finally:
        for staged_path in (staged_package, staged_launcher):
            if _destination_exists(staged_path):
                _remove_destination(staged_path)
    print(f"Installed package: {package_destination}", file=sys.stderr)
    print(f"Installed launcher: {launcher_destination}", file=sys.stderr)


def _reject_symlinked_install_ancestors(prefix: Path) -> None:
    """Reject links in the prefix itself and its share/bin destination parents."""
    for destination_parent in (prefix / "share", prefix / "bin"):
        current = Path(destination_parent.anchor)
        for component in destination_parent.parts[1:]:
            current /= component
            try:
                mode = current.lstat().st_mode
            except (FileNotFoundError, NotADirectoryError):
                break
            if stat.S_ISLNK(mode):
                raise DestinationRefused(
                    "Refusing installation through a symlinked destination ancestor"
                )


def _has_install_marker(marker: Path) -> bool:
    try:
        return (
            not marker.is_symlink()
            and marker.is_file()
            and marker.read_text(encoding="utf-8") == _MARKER_CONTENT
        )
    except (OSError, UnicodeError):
        return False


def _is_agent_launcher(path: Path) -> bool:
    try:
        return (
            not path.is_symlink()
            and path.is_file()
            and _LAUNCHER_MARKER in path.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError):
        return False


def _destination_exists(path: Path) -> bool:
    return path.is_symlink() or path.exists()


def _remove_destination(path: Path) -> None:
    if path.is_symlink() or not path.is_dir():
        path.unlink()
    else:
        shutil.rmtree(path)


def _stage_package(parent: Path) -> Path:
    staged_package = _unique_staging_path(parent, "package")
    try:
        staged_package.mkdir()
        shutil.copytree(
            _SOURCE_PACKAGE,
            staged_package / "agent_checkpoint",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        (staged_package / _MARKER_NAME).write_text(_MARKER_CONTENT, encoding="utf-8")
    except BaseException:
        if _destination_exists(staged_package):
            _remove_destination(staged_package)
        raise
    return staged_package


def _stage_launcher(parent: Path) -> Path:
    staged_launcher = _unique_staging_path(parent, "launcher")
    try:
        shutil.copy2(_SOURCE_LAUNCHER, staged_launcher)
        staged_launcher.chmod(
            staged_launcher.stat().st_mode
            | stat.S_IXUSR
            | stat.S_IXGRP
            | stat.S_IXOTH
        )
    except BaseException:
        if _destination_exists(staged_launcher):
            _remove_destination(staged_launcher)
        raise
    return staged_launcher


def _unique_staging_path(parent: Path, label: str) -> Path:
    for _ in range(100):
        candidate = parent / f".agent-checkpoint-{label}-{uuid.uuid4().hex}"
        if not _destination_exists(candidate):
            return candidate
    raise OSError("unable to allocate installation staging path")


def _publish_staged_install(
    package_destination: Path,
    staged_package: Path,
    launcher_destination: Path,
    staged_launcher: Path,
) -> None:
    package_backup = _move_existing_to_backup(package_destination)
    try:
        os.replace(staged_package, package_destination)
        launcher_backup = _move_existing_to_backup(launcher_destination)
        try:
            os.replace(staged_launcher, launcher_destination)
        except OSError:
            _restore_destination(launcher_destination, launcher_backup)
            raise
    except OSError:
        _restore_destination(package_destination, package_backup)
        raise
    else:
        _discard_backup(package_backup)
        _discard_backup(launcher_backup)


def _move_existing_to_backup(destination: Path) -> Path | None:
    if not _destination_exists(destination):
        return None
    backup = _unique_staging_path(destination.parent, "backup")
    os.replace(destination, backup)
    return backup


def _restore_destination(destination: Path, backup: Path | None) -> None:
    if _destination_exists(destination):
        _remove_destination(destination)
    if backup is not None and _destination_exists(backup):
        os.replace(backup, destination)


def _discard_backup(backup: Path | None) -> None:
    if backup is not None and _destination_exists(backup):
        _remove_destination(backup)


if __name__ == "__main__":
    raise SystemExit(main())
