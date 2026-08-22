"""Behavioral coverage for project-wide handoff report write/list/resolve primitives."""

from pathlib import Path
import tempfile
import unittest

from agent_checkpoint.config import ConfigError
from agent_checkpoint.handoff import (
    list_open_handoff_reports,
    resolve_handoff_report,
    write_handoff_report,
)


class HandoffReportTests(unittest.TestCase):
    """Catch handoff reports that clobber, mislocate, or crash on listing."""

    def test_write_creates_directory_on_first_use_only(self):
        """Catches the handoff directory being created eagerly instead of on first write."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            handoff_dir = project_root / ".agent-checkpoint" / "handoff"
            self.assertFalse(handoff_dir.exists())

            path = write_handoff_report(
                project_root, "current", "R5", "Found stale lock helper", "Body text."
            )

            self.assertTrue(handoff_dir.exists())
            self.assertTrue(path.exists())
            self.assertEqual(path.parent.name, "handoff")
            self.assertIn("current-R5-found-stale-lock-helper", path.name)

    def test_write_report_content_includes_work_and_unit_and_body(self):
        """Catches a report missing the context a future session needs to act on it."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)

            path = write_handoff_report(
                project_root, "current", "R5", "Title Here", "The discovered detail."
            )
            text = path.read_text(encoding="utf-8")

        self.assertIn("Title Here", text)
        self.assertIn("Work: current", text)
        self.assertIn("Unit: R5", text)
        self.assertIn("The discovered detail.", text)

    def test_write_never_silently_overwrites_a_colliding_report(self):
        """Catches a second report with the same slug clobbering the first."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)

            first = write_handoff_report(project_root, "current", "R5", "Same Title", "First.")
            second = write_handoff_report(project_root, "current", "R5", "Same Title", "Second.")

            self.assertNotEqual(first, second)
            self.assertEqual(first.read_text(encoding="utf-8").splitlines()[-1], "First.")
            self.assertEqual(second.read_text(encoding="utf-8").splitlines()[-1], "Second.")

    def test_list_returns_empty_when_directory_does_not_exist(self):
        """Catches list raising instead of treating absence as a normal, common state."""
        with tempfile.TemporaryDirectory() as directory:
            reports = list_open_handoff_reports(Path(directory))

        self.assertEqual(reports, [])

    def test_list_returns_every_written_report(self):
        """Catches list missing a report that write_handoff_report actually persisted."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            write_handoff_report(project_root, "current", "R5", "First Item", "Body.")
            write_handoff_report(project_root, "current", "R6", "Second Item", "Body.")

            reports = list_open_handoff_reports(project_root)

        self.assertEqual(len(reports), 2)
        names = {path.name for path in reports}
        self.assertTrue(any("first-item" in name for name in names))
        self.assertTrue(any("second-item" in name for name in names))

    def test_list_skips_symlinked_entries_without_crashing(self):
        """Catches a symlinked entry in handoff/ being followed or crashing the listing."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            write_handoff_report(project_root, "current", "R5", "Real Report", "Body.")
            handoff_dir = project_root / ".agent-checkpoint" / "handoff"
            target = project_root / "outside-target.md"
            target.write_text("elsewhere\n", encoding="utf-8")
            (handoff_dir / "sneaky-link.md").symlink_to(target)

            reports = list_open_handoff_reports(project_root)

        names = {path.name for path in reports}
        self.assertNotIn("sneaky-link.md", names)
        self.assertEqual(len(reports), 1)

    def test_resolve_removes_report_from_disk_and_from_listing(self):
        """Catches resolve leaving the file in place or list still showing it."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            path = write_handoff_report(project_root, "current", "R5", "Fixed Now", "Body.")

            resolve_handoff_report(project_root, path.name)

            self.assertFalse(path.exists())
            self.assertEqual(list_open_handoff_reports(project_root), [])

    def test_resolve_accepts_name_without_md_suffix(self):
        """Catches resolve requiring the caller to spell out the .md extension."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            path = write_handoff_report(project_root, "current", "R5", "Bare Name", "Body.")

            resolve_handoff_report(project_root, path.stem)

            self.assertFalse(path.exists())

    def test_resolve_nonexistent_report_raises_clearly(self):
        """Catches resolve silently no-op'ing on a name that was never written."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)

            with self.assertRaises(ConfigError):
                resolve_handoff_report(project_root, "never-written")

    def test_resolve_refuses_path_traversal(self):
        """Catches a traversal-shaped name reaching outside handoff/."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            write_handoff_report(project_root, "current", "R5", "Real Report", "Body.")
            outside_target = project_root / "outside.md"
            outside_target.write_text("secret\n", encoding="utf-8")

            with self.assertRaises(ConfigError):
                resolve_handoff_report(project_root, "../outside.md")

            self.assertTrue(outside_target.exists())
            self.assertEqual(outside_target.read_text(encoding="utf-8"), "secret\n")

    def test_resolve_refuses_symlinked_entry(self):
        """Catches resolve following a symlinked report and deleting its target."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            handoff_dir = project_root / ".agent-checkpoint" / "handoff"
            write_handoff_report(project_root, "current", "R5", "Real Report", "Body.")
            target = project_root / "outside-target.md"
            target.write_text("elsewhere\n", encoding="utf-8")
            link = handoff_dir / "sneaky-link.md"
            link.symlink_to(target)

            with self.assertRaises(ConfigError):
                resolve_handoff_report(project_root, "sneaky-link.md")

            self.assertTrue(link.is_symlink())
            self.assertTrue(target.exists())
