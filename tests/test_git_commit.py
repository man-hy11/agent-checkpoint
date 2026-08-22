"""Behavioral coverage for the opt-in auto-commit-on-handoff feature."""

from pathlib import Path
import subprocess
import tempfile
import unittest

from agent_checkpoint.config import ProjectConfig
from agent_checkpoint.git_commit import commit_work_package


class CommitWorkPackageTests(unittest.TestCase):
    """Catch auto-commit running when it should not, or crashing when it should skip."""

    def test_disabled_by_default_skips_without_touching_the_tree(self):
        """Catches auto_commit_on_handoff defaulting to on, an unsafe default."""
        with git_project() as project_root:
            write_file(project_root / "work.txt", "changed")

            result = commit_work_package(
                project_root, ProjectConfig(), "current", "feature"
            )

            self.assertFalse(result.committed)
            self.assertEqual(result.reason, "auto_commit_on_handoff is disabled")
            self.assertIn("work.txt", _status(project_root))

    def test_commits_dirty_tree_when_enabled(self):
        """Catches the happy path failing to stage and commit real changes."""
        with git_project() as project_root:
            write_file(project_root / "work.txt", "changed")
            config = ProjectConfig(auto_commit_on_handoff=True)

            result = commit_work_package(project_root, config, "current", "feature")

            self.assertTrue(result.committed)
            self.assertIsNotNone(result.commit_sha)
            self.assertEqual(_status(project_root), "")
            log = run_git(project_root, "log", "-1", "--format=%s")
            self.assertIn("current", log.stdout)
            self.assertIn("feature", log.stdout)

    def test_clean_tree_skips_without_committing(self):
        """Catches an empty commit being created when nothing changed."""
        with git_project() as project_root:
            config = ProjectConfig(auto_commit_on_handoff=True)
            before = run_git(project_root, "rev-parse", "HEAD").stdout

            result = commit_work_package(project_root, config, "current", "feature")

            self.assertFalse(result.committed)
            self.assertEqual(result.reason, "no changes to commit")
            after = run_git(project_root, "rev-parse", "HEAD").stdout
            self.assertEqual(before, after)

    def test_non_repository_skips_without_raising(self):
        """Catches raising instead of skipping when there is no Git repository."""
        with tempfile.TemporaryDirectory() as directory:
            config = ProjectConfig(auto_commit_on_handoff=True)

            result = commit_work_package(Path(directory), config, "current", "feature")

        self.assertFalse(result.committed)
        self.assertEqual(result.reason, "not a Git repository")

    def test_commit_hook_failure_skips_without_raising(self):
        """Catches a rejecting pre-commit hook crashing handoff instead of being skipped."""
        with git_project() as project_root:
            hooks_dir = project_root / ".git" / "hooks"
            hooks_dir.mkdir(parents=True, exist_ok=True)
            hook_path = hooks_dir / "pre-commit"
            hook_path.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            hook_path.chmod(0o755)
            write_file(project_root / "work.txt", "changed")
            config = ProjectConfig(auto_commit_on_handoff=True)

            result = commit_work_package(project_root, config, "current", "feature")

            self.assertFalse(result.committed)
            self.assertEqual(result.reason, "git commit failed")


def write_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_git(root: Path, *arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )


def _status(root: Path) -> str:
    return run_git(root, "status", "--porcelain").stdout


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


if __name__ == "__main__":
    unittest.main()
