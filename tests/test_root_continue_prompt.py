"""Characterization tests for R4: root CONTINUE_PROMPT.md writer and STOP language.

Covers:
- Root CONTINUE_PROMPT.md is created after ``agent-checkpoint workflow``.
- Root file content names the active work id and carries explicit STOP language.
- Root file is atomically regenerated when a second package is activated.
- Symlinked root file is refused before overwrite.
- ``_render_continue_prompt`` (rev-5, work_renderer) carries STOP language for
  all ten work-type families.
- ``work_migration.py`` classification is unaffected by the new root file
  (verified structurally: migration only inspects paths under work/<id>/).
"""

from pathlib import Path
import tempfile
import unittest

from agent_checkpoint.config import ConfigError, write_active_work_id
from agent_checkpoint.work_manifest import load_manifest
from agent_checkpoint.work_renderer import render_final_package
from agent_checkpoint.workflows import (
    render_root_continue_prompt,
    write_root_continue_prompt,
)
from tests.helpers import run_cli


_FAMILIES = (
    "project",
    "feature",
    "bugfix",
    "refactor",
    "upgrade",
    "migration",
    "performance",
    "integration",
    "release",
    "spike",
)

_STOP_MARKERS = (
    "one invocation = one Step or one Gate",
    "STOP",
    "Advancing Current Target does not authorize beginning it in this invocation",
)


class RenderRootContinuePromptTests(unittest.TestCase):
    def test_content_names_active_work_id(self):
        """Catches the root prompt not naming the active package id."""
        text = render_root_continue_prompt("my-feature")

        self.assertIn("my-feature", text)
        self.assertIn(".agent-checkpoint/work/my-feature", text)

    def test_content_contains_stop_language(self):
        """Catches the root prompt missing the explicit STOP block."""
        text = render_root_continue_prompt("my-feature")

        for marker in _STOP_MARKERS:
            self.assertIn(marker, text, f"missing: {marker!r}")

    def test_content_has_no_unresolved_placeholders(self):
        """Catches a template substitution being skipped in the root prompt."""
        text = render_root_continue_prompt("demo")

        self.assertNotIn("{{", text)
        self.assertNotIn("}}", text)


class WriteRootContinuePromptTests(unittest.TestCase):
    def test_creates_root_file_with_active_id_and_stop_language(self):
        """Catches the atomic writer failing to produce a readable root file."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            write_root_continue_prompt(root, "current")

            prompt = root / "CONTINUE_PROMPT.md"
            self.assertTrue(prompt.is_file())
            text = prompt.read_text(encoding="utf-8")
            self.assertIn("current", text)
            for marker in _STOP_MARKERS:
                self.assertIn(marker, text, f"missing: {marker!r}")

    def test_second_write_overwrites_atomically_with_new_id(self):
        """Catches the root file retaining the old id after switching active packages."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            write_root_continue_prompt(root, "alpha")
            write_root_continue_prompt(root, "beta")

            text = (root / "CONTINUE_PROMPT.md").read_text(encoding="utf-8")
            self.assertIn("beta", text)
            self.assertNotIn("alpha", text)

    def test_symlinked_root_file_is_refused(self):
        """Catches the writer following a symlink instead of refusing it."""
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            project_root = base / "project"
            project_root.mkdir()
            target = base / "external.md"
            target.write_text("old content\n", encoding="utf-8")
            prompt_path = project_root / "CONTINUE_PROMPT.md"
            try:
                prompt_path.symlink_to(target)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"symlinks unavailable: {error}")

            with self.assertRaisesRegex(ConfigError, "symlink"):
                write_root_continue_prompt(project_root, "demo")

            self.assertEqual(target.read_text(encoding="utf-8"), "old content\n")


class WorkflowCommandRootFileTests(unittest.TestCase):
    def test_workflow_command_creates_root_continue_prompt(self):
        """Catches the workflow CLI command not producing a root CONTINUE_PROMPT.md."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)

            result = run_cli(
                "workflow",
                "--root", str(project_root),
                "--type", "bugfix",
                "--id", "current",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            prompt = project_root / "CONTINUE_PROMPT.md"
            self.assertTrue(prompt.is_file(), "root CONTINUE_PROMPT.md missing")
            text = prompt.read_text(encoding="utf-8")
            self.assertIn("current", text)
            for marker in _STOP_MARKERS:
                self.assertIn(marker, text, f"missing: {marker!r}")

    def test_workflow_command_updates_root_file_when_second_package_created(self):
        """Catches the root file retaining the first package id after creating a second."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)

            run_cli(
                "workflow",
                "--root", str(project_root),
                "--type", "bugfix",
                "--id", "fix-one",
            )
            run_cli(
                "workflow",
                "--root", str(project_root),
                "--type", "feature",
                "--id", "feat-two",
            )

            text = (project_root / "CONTINUE_PROMPT.md").read_text(encoding="utf-8")
            self.assertIn("feat-two", text)
            self.assertNotIn("fix-one", text)

    def test_root_file_is_never_written_without_a_work_package(self):
        """Catches a root CONTINUE_PROMPT.md being emitted when the workflow fails."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)

            # invalid work type should fail and leave no root file
            run_cli(
                "workflow",
                "--root", str(project_root),
                "--type", "not-a-type",
                "--id", "current",
            )

            self.assertFalse(
                (project_root / "CONTINUE_PROMPT.md").exists(),
                "root CONTINUE_PROMPT.md must not exist after a failed workflow call",
            )


class RevFiveContinuePromptStopLanguageTests(unittest.TestCase):
    def test_render_final_package_continue_prompt_has_stop_language_all_families(self):
        """Catches _render_continue_prompt (rev-5) missing STOP language for any family."""
        for work_type in _FAMILIES:
            with self.subTest(work_type=work_type):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    result = render_final_package(root, work_type, "testpkg")
                    prompt_path = result.path / "CONTINUE_PROMPT.md"
                    self.assertTrue(prompt_path.is_file(), "CONTINUE_PROMPT.md missing")
                    text = prompt_path.read_text(encoding="utf-8")
                    for marker in _STOP_MARKERS:
                        self.assertIn(marker, text, f"{work_type}: missing {marker!r}")


class WorkMigrationUnaffectedTests(unittest.TestCase):
    def test_root_continue_prompt_does_not_interfere_with_migration_scan(self):
        """Catches work_migration.py's classify() being confused by the new root file.

        ``discover_legacy_packages`` only scans ``.agent-checkpoint/work/*/``, never
        the project root, so a root ``CONTINUE_PROMPT.md`` must be invisible to it.
        """
        from agent_checkpoint.work_migration import discover_legacy_packages

        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            # Write a root CONTINUE_PROMPT.md to simulate what workflow now produces.
            (project_root / "CONTINUE_PROMPT.md").write_text(
                render_root_continue_prompt("demo"), encoding="utf-8"
            )
            # No work packages under .agent-checkpoint/work/ — discovery must return ().
            packages = discover_legacy_packages(project_root)
            self.assertEqual(packages, ())


if __name__ == "__main__":
    unittest.main()
