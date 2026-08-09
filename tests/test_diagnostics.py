"""Behavioral coverage for bounded checkpoint diagnostics."""

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from agent_checkpoint.config import ProjectConfig
from agent_checkpoint.diagnostics import (
    build_doctor,
    build_handoff,
    build_resume,
    build_status,
)
from agent_checkpoint.progress import render_entry
from tests.helpers import FIXED_TIME, VALID_BODY


class DiagnosticTests(unittest.TestCase):
    """Catch unsafe or unbounded status, resume, handoff, and doctor output."""

    def test_status_reports_absent_checkpoint_without_requiring_git(self):
        """Catches status assuming every initialized project has a Git worktree."""
        with tempfile.TemporaryDirectory() as directory:
            report = build_status(Path(directory), ProjectConfig())

        self.assertFalse(report["checkpoint_exists"])
        self.assertFalse(report["git"]["git_available"])

    def test_resume_obeys_explicit_budget_and_marks_truncation(self):
        """Catches resume output that can exceed a context budget without notice."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            write_progress(project_root, VALID_BODY + "\n" + ("x" * 500))

            resume = build_resume(project_root, ProjectConfig(), max_chars=80)

        self.assertEqual(len(resume), 80)
        self.assertTrue(resume.endswith("..."))

    def test_handoff_includes_safe_requested_context_within_budget(self):
        """Catches a handoff that omits a required field or expands beyond its budget."""
        with git_project() as project_root:
            write_file(project_root / "changed.py", "uncommitted-file-content")
            write_progress(project_root, VALID_BODY)

            handoff = build_handoff(
                project_root,
                ProjectConfig(),
                verification=("tests: pass",),
                max_chars=2_000,
            )

        self.assertIn("Root:", handoff)
        self.assertIn("Branch:", handoff)
        self.assertIn("Worktree:", handoff)
        self.assertIn("changed.py", handoff)
        self.assertIn("tests: pass", handoff)
        self.assertIn("Current Focus:", handoff)
        self.assertIn("Next Actions:", handoff)
        self.assertIn("Recent Decisions:", handoff)
        self.assertNotIn("uncommitted-file-content", handoff)
        self.assertLessEqual(len(handoff), 2_000)

    def test_language_setting_is_rendered_in_resume_and_handoff(self):
        """Catches a validated language option having no consumer-visible effect."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            config = ProjectConfig(language="Korean")
            write_progress(project_root, VALID_BODY)

            resume = build_resume(project_root, config, max_chars=2_000)
            handoff = build_handoff(project_root, config, max_chars=2_000)

        self.assertIn("Language: Korean", resume)
        self.assertIn("Language: Korean", handoff)

    def test_handoff_omits_git_hints_when_disabled(self):
        """Catches include_git_hints=false being parsed but ignored."""
        with git_project() as project_root:
            write_file(project_root / "changed.py", "uncommitted\n")
            write_progress(project_root, VALID_BODY)

            handoff = build_handoff(
                project_root,
                ProjectConfig(include_git_hints=False),
                max_chars=2_000,
            )

        self.assertNotIn("Branch:", handoff)
        self.assertNotIn("Worktree:", handoff)
        self.assertNotIn("Changed files:", handoff)
        self.assertNotIn("changed.py", handoff)

    def test_doctor_warns_for_already_tracked_progress_file(self):
        """Catches a doctor that recommends ignore rules while hiding tracked state."""
        with git_project() as project_root:
            write_file(project_root / "PROGRESS.md", "# Project Checkpoints\n")
            run_git(project_root, "add", "PROGRESS.md")
            run_git(project_root, "commit", "-m", "track progress")

            report = build_doctor(project_root, ProjectConfig(), adapter="codex")

        self.assertIn("already tracked", report["warnings"])
        self.assertEqual(report["capability"], "manual")

    def test_doctor_reports_archive_tracking_and_ignore_state(self):
        """Catches doctor inspecting only the live checkpoint Git state."""
        with git_project() as project_root:
            write_file(project_root / ".gitignore", "PROGRESS.md\n")
            write_file(project_root / "PROGRESS_ARCHIVE.md", "# Archive\n")
            run_git(project_root, "add", ".gitignore")
            run_git(project_root, "add", "PROGRESS_ARCHIVE.md")
            run_git(project_root, "commit", "-m", "track archive")

            report = build_doctor(project_root, ProjectConfig(), adapter="codex")

        self.assertIn("archive file is already tracked", report["warnings"])
        self.assertIn("archive file is not ignored", report["warnings"])

    def test_doctor_warns_when_project_root_is_inside_worktree(self):
        """Catches a branch/worktree mismatch that would otherwise be silently trusted."""
        with git_project() as project_root:
            nested_root = project_root / "nested"
            nested_root.mkdir()

            report = build_doctor(nested_root, ProjectConfig(), adapter="codex")

        self.assertIn("worktree mismatch", report["warnings"])

    def test_status_and_doctor_omit_probable_credentials_in_changed_filenames(self):
        """Catches raw Git metadata exposing a credential-shaped filename."""
        with git_project() as project_root:
            credential_filename = "sk-" + ("a" * 21)
            write_file(project_root / credential_filename, "metadata only\n")

            status = build_status(project_root, ProjectConfig())
            doctor = build_doctor(project_root, ProjectConfig(), adapter="codex")

        self.assertNotIn(credential_filename, json.dumps(status))
        self.assertNotIn(credential_filename, json.dumps(doctor))

    def test_handoff_omits_probable_credentials_in_branch_metadata(self):
        """Catches a branch name bypassing the handoff's content safety guard."""
        with git_project() as project_root:
            credential_branch = "sk-" + ("a" * 21)
            run_git(project_root, "checkout", "-qb", credential_branch)

            handoff = build_handoff(project_root, ProjectConfig(), max_chars=2_000)

        self.assertNotIn(credential_branch, handoff)

    def test_resume_rejects_diff_shaped_checkpoint_content(self):
        """Catches resume forwarding a stored patch into the next context window."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            diff_marker = "diff --git a/file b/file"
            write_progress(project_root, VALID_BODY + "\n" + diff_marker + "\n")

            resume = build_resume(project_root, ProjectConfig(), max_chars=2_000)

        self.assertNotIn(diff_marker, resume)
        self.assertIn("diff-shaped content", resume)

    def test_handoff_rejects_unified_diff_markers_in_checkpoint_content(self):
        """Catches handoff extracting a section that contains a unified patch marker."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            diff_marker = "@@ -1 +1 @@"
            body = VALID_BODY.replace("- Parser", f"- Parser\n{diff_marker}")
            write_progress(project_root, body)

            handoff = build_handoff(project_root, ProjectConfig(), max_chars=2_000)

        self.assertNotIn(diff_marker, handoff)
        self.assertIn("diff-shaped content", handoff)

    def test_resume_rejects_generic_unified_diff_file_markers(self):
        """Catches accepting unified diff filenames that omit Git's a/ and b/ prefixes."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            diff_marker = "--- old-file\n+++ new-file"
            write_progress(project_root, VALID_BODY + "\n" + diff_marker + "\n")

            resume = build_resume(project_root, ProjectConfig(), max_chars=2_000)

        self.assertNotIn(diff_marker, resume)
        self.assertIn("diff-shaped content", resume)

    def test_handoff_rejects_diff_shaped_verification_result(self):
        """Catches supplied verification forwarding a patch despite checkpoint gating."""
        with tempfile.TemporaryDirectory() as directory:
            diff_marker = "diff --git a/file b/file"

            with self.assertRaisesRegex(ValueError, "diff-shaped content"):
                build_handoff(
                    Path(directory),
                    ProjectConfig(),
                    verification=(diff_marker,),
                    max_chars=2_000,
                )

    def test_handoff_rejects_all_verification_line_boundaries(self):
        """Catches non-CR/LF line separators bypassing direct handoff validation."""
        for separator in ("\n", "\r", "\x0b", "\x0c", "\x85", "\u2028", "\u2029"):
            with self.subTest(separator=repr(separator)), tempfile.TemporaryDirectory() as directory:
                with self.assertRaisesRegex(ValueError, "single line"):
                    build_handoff(
                        Path(directory),
                        ProjectConfig(),
                        verification=(f"tests passed{separator}hidden instruction",),
                        max_chars=2_000,
                    )


class git_project:
    """A disposable Git worktree using real Git commands only in test setup."""

    def __enter__(self) -> Path:
        self._directory = tempfile.TemporaryDirectory()
        self.root = Path(self._directory.name)
        run_git(self.root, "init", "-q")
        run_git(self.root, "config", "user.email", "tests@example.invalid")
        run_git(self.root, "config", "user.name", "Checkpoint Tests")
        write_file(self.root / "README.md", "fixture\n")
        run_git(self.root, "add", "README.md")
        run_git(self.root, "commit", "-qm", "fixture")
        return self.root

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self._directory.cleanup()


def write_progress(project_root: Path, body: str) -> None:
    text = "# Project Checkpoints\n\n" + render_entry(body, FIXED_TIME, pinned=False)
    write_file(project_root / "PROGRESS.md", text)


def write_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_git(root: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
