"""Behavioral coverage for read-only Git state collection."""

from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from agent_checkpoint.config import ProjectConfig
from agent_checkpoint.git_state import collect_git_state


class GitStateTests(unittest.TestCase):
    """Catch Git inspection that leaks contents or misreports repository state."""

    def test_collects_changed_filenames_without_returning_file_content(self):
        """Catches replacing metadata inspection with a content-bearing Git command."""
        with git_project() as project_root:
            write_file(project_root / "secret.txt", "diff-only-content")

            state = collect_git_state(project_root, ProjectConfig())

            self.assertTrue(state.git_available)
            self.assertEqual(state.worktree, str(project_root.resolve()))
            self.assertIn("secret.txt", state.changed_files)
            self.assertNotIn("diff-only-content", json.dumps(asdict(state)))

    def test_reports_non_repository_as_unavailable_without_raising(self):
        """Catches a failed Git probe escaping from a normal no-Git project."""
        with tempfile.TemporaryDirectory() as directory:
            state = collect_git_state(Path(directory), ProjectConfig())

        self.assertFalse(state.git_available)
        self.assertEqual(state.changed_files, ())
        self.assertFalse(state.progress_tracked)
        self.assertFalse(state.progress_ignored)

    def test_reports_configured_progress_and_archive_as_tracked_and_ignored(self):
        """Catches probing only one configured checkpoint path."""
        with git_project() as project_root:
            write_file(
                project_root / ".gitignore",
                "state/PROGRESS.md\nstate/PROGRESS_ARCHIVE.md\n",
            )
            write_file(project_root / "state" / "PROGRESS.md", "# Project Checkpoints\n")
            write_file(
                project_root / "state" / "PROGRESS_ARCHIVE.md", "# Archive\n"
            )
            run_git(project_root, "add", ".gitignore")
            run_git(project_root, "add", "-f", "state/PROGRESS.md")
            run_git(project_root, "add", "-f", "state/PROGRESS_ARCHIVE.md")
            run_git(project_root, "commit", "-m", "track progress")

            state = collect_git_state(
                project_root,
                ProjectConfig(
                    progress_path=Path("state/PROGRESS.md"),
                    archive_path=Path("state/PROGRESS_ARCHIVE.md"),
                ),
            )

            self.assertTrue(state.progress_tracked)
            self.assertTrue(state.progress_ignored)
            self.assertTrue(getattr(state, "archive_tracked", False))
            self.assertTrue(getattr(state, "archive_ignored", False))

    def test_public_state_redacts_probable_credentials_in_git_metadata(self):
        """Catches callers bypassing diagnostics and receiving unsafe Git metadata."""
        with git_project() as project_root:
            credential = "sk-" + ("a" * 21)
            run_git(project_root, "checkout", "-qb", credential)
            write_file(project_root / credential, "metadata only\n")

            state = collect_git_state(project_root, ProjectConfig())

        self.assertNotIn(credential, json.dumps(asdict(state)))


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
