"""Characterization and failure-mode coverage for the active-pointer contract.

These tests fix the R3 behavior change: PROGRESS.md moves from a single
project-root file to a per-work-package file at
``.agent-checkpoint/work/<active_id>/PROGRESS.md``, resolved via the active
pointer (R2 D1-D4). They cover the single-active-package case (unchanged in
effect, new path), the no-pointer / stale-pointer / symlinked-pointer failure
modes, and the multi-package coexistence isolation regression.
"""

from pathlib import Path
import tempfile
import unittest

from agent_checkpoint.config import (
    ConfigError,
    ProjectConfig,
    read_active_work_id,
    resolve_active_config,
    resolve_checkpoint_paths,
    work_scoped_config,
    write_active_work_id,
)
from agent_checkpoint.storage import CheckpointStore
from tests.helpers import VALID_BODY


def _make_work_dir(project_root: Path, work_id: str) -> Path:
    package = project_root / ".agent-checkpoint" / "work" / work_id
    package.mkdir(parents=True)
    return package


class ReadActivePointerTests(unittest.TestCase):
    def test_absent_pointer_returns_none(self):
        """Catches a missing pointer raising instead of degrading to None."""
        with tempfile.TemporaryDirectory() as directory:
            self.assertIsNone(read_active_work_id(Path(directory)))

    def test_valid_pointer_naming_existing_package_returns_id(self):
        """Catches the common single-package case failing to resolve."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            _make_work_dir(project_root, "current")
            write_active_work_id(project_root, "current")

            self.assertEqual(read_active_work_id(project_root), "current")

    def test_stale_pointer_returns_none(self):
        """Catches a pointer to a deleted package crashing instead of degrading."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            write_active_work_id(project_root, "ghost")

            self.assertIsNone(read_active_work_id(project_root))

    def test_symlinked_pointer_is_refused(self):
        """Catches a symlinked pointer being followed instead of rejected."""
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            project_root = base / "project"
            (project_root / ".agent-checkpoint").mkdir(parents=True)
            target = base / "external"
            target.write_text("current\n", encoding="utf-8")
            pointer = project_root / ".agent-checkpoint" / "active"
            try:
                pointer.symlink_to(target)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"symlinks unavailable: {error}")

            with self.assertRaisesRegex(ConfigError, "symlink"):
                read_active_work_id(project_root)

    def test_malformed_pointer_content_is_refused(self):
        """Catches a corrupted pointer being treated as a valid work id."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            (project_root / ".agent-checkpoint").mkdir(parents=True)
            (project_root / ".agent-checkpoint" / "active").write_text(
                "Not A Valid Id!\n", encoding="utf-8"
            )

            with self.assertRaisesRegex(ConfigError, "invalid work id"):
                read_active_work_id(project_root)

    def test_write_active_work_id_rejects_invalid_id(self):
        """Catches an invalid id being persisted as the active pointer."""
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ConfigError):
                write_active_work_id(Path(directory), "Bad Id")


class ResolveActiveConfigTests(unittest.TestCase):
    def test_resolves_work_scoped_paths_for_active_package(self):
        """Catches the resolved live/archive paths not landing under work/<id>/."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            _make_work_dir(project_root, "current")
            write_active_work_id(project_root, "current")

            work_config = resolve_active_config(project_root, ProjectConfig())
            _, progress_path, archive_path = resolve_checkpoint_paths(
                project_root, work_config
            )

            self.assertEqual(
                progress_path,
                (project_root / ".agent-checkpoint/work/current/PROGRESS.md").resolve(),
            )
            self.assertEqual(
                archive_path,
                (
                    project_root
                    / ".agent-checkpoint/work/current/PROGRESS_ARCHIVE.md"
                ).resolve(),
            )

    def test_no_pointer_raises_config_error_without_global_fallback(self):
        """Catches a silent fallback to the old project-root PROGRESS.md path."""
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ConfigError, "No active work package set"):
                resolve_active_config(Path(directory), ProjectConfig())

    def test_stale_pointer_raises_config_error_naming_stale_id(self):
        """Catches a stale pointer failing without naming the offending id."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            write_active_work_id(project_root, "ghost")

            with self.assertRaisesRegex(ConfigError, "ghost"):
                resolve_active_config(project_root, ProjectConfig())


class WorkScopedStoreTests(unittest.TestCase):
    def test_lock_path_is_per_work_package(self):
        """Catches the lock staying global instead of following progress_path."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            _make_work_dir(project_root, "current")
            store = CheckpointStore(project_root, work_scoped_config(ProjectConfig(), "current"))

            self.assertEqual(
                store.lock_path,
                (
                    project_root
                    / ".agent-checkpoint/work/current/.agent-checkpoint.lock"
                ).resolve(),
            )

    def test_single_active_package_write_targets_work_scoped_progress(self):
        """Catches the write landing anywhere but the active package's PROGRESS.md."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            _make_work_dir(project_root, "current")
            store = CheckpointStore(project_root, work_scoped_config(ProjectConfig(), "current"))

            store.write(VALID_BODY)

            scoped = project_root / ".agent-checkpoint/work/current/PROGRESS.md"
            self.assertTrue(scoped.is_file())
            self.assertIn("Build it", scoped.read_text(encoding="utf-8"))
            self.assertFalse((project_root / "PROGRESS.md").exists())

    def test_multi_package_write_isolates_to_active_package(self):
        """Catches a write touching a coexisting package's PROGRESS.md (Bug-2 class)."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            _make_work_dir(project_root, "current")
            _make_work_dir(project_root, "other-package")
            other_progress = (
                project_root / ".agent-checkpoint/work/other-package/PROGRESS.md"
            )
            other_progress.write_text("# Untouched\n", encoding="utf-8")
            other_before = other_progress.read_bytes()

            write_active_work_id(project_root, "current")
            work_config = resolve_active_config(project_root, ProjectConfig())
            CheckpointStore(project_root, work_config).write(VALID_BODY)

            current_progress = (
                project_root / ".agent-checkpoint/work/current/PROGRESS.md"
            )
            self.assertTrue(current_progress.is_file())
            self.assertEqual(other_progress.read_bytes(), other_before)


if __name__ == "__main__":
    unittest.main()
